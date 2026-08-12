"""Full runtime — executes a Rosh Programme statement by statement.

Implements 17 keywords per BUILDING-ROSH.md Sections 5 & 7.
"""

from __future__ import annotations

import random
import re
import sys
import warnings
from typing import Any, TextIO

from rosh_lang.core.model import (
    AddStatement,
    AfterStatement,
    AnimateStatement,
    BackgroundStatement,
    BlankStatement,
    CommentStatement,
    ConnectStatement,
    CreateStatement,
    DefineStatement,
    DestroyStatement,
    DoStatement,
    EndStatement,
    EventStatement,
    ForEachStatement,
    GetStatement,
    ExtensionCommandStatement,
    GoStatement,
    IfStatement,
    LookStatement,
    OnStatement,
    PlayStatement,
    PrintStatement,
    Programme,
    RemoveStatement,
    RepeatStatement,
    SayStatement,
    SendStatement,
    SetStatement,
    SoundStatement,
    SpriteStatement,
    Statement,
    UseStatement,
    WhenStatement,
)

_INTERP_RE = re.compile(r"\{([^}]+)\}")

# Universal events — never need declaration
UNIVERSAL_EVENTS = frozenset({
    "start", "update", "collision", "click", "keydown",
    "keyup", "destroy", "message",
    "scene_exit", "scene_enter", "say",
})

# Max send depth to prevent infinite cascading
_MAX_SEND_DEPTH = 10


class Runtime:
    """Execute a Rosh programme."""

    # Shared with _try_arithmetic and _looks_like_expression — multi-char
    # before single-char to avoid ambiguous splits (>= before >, <= before <).
    _ARITHMETIC_OPS = (">=", "<=", "==", "!=", ">", "<", "+", "-", "*", "/")

    def __init__(
        self,
        output: TextIO = sys.stdout,
        search_paths: list[Any] | None = None,
    ) -> None:
        self.state: dict[str, Any] = {}
        self.handlers: dict[str, list[list[Statement]]] = {}
        self.listeners: dict[str, list[OnStatement]] = {}
        self.event_registry: dict[str, list[str]] = {}  # name → payload_fields
        self.scenes: dict[str, dict[str, Any]] = {}
        self.connections: dict[str, str] = {}
        self.audio_registry: dict[str, str] = {}  # sound_name → description
        self.animation_registry: dict[str, dict[str, Any]] = {}  # name → {sheet, frames, speed, mode}
        self.functions: dict[str, list[Statement]] = {}
        self._function_params: dict[str, list[str]] = {}
        self.output = output
        self.search_paths = search_paths
        self._send_depth = 0
        self._call_stack: set[str] = set()
        self._programme: Programme | None = None
        self._run_depth = 0
        # Tracks loaded components: namespace → {name, description, provides, exposes, alias}
        self.components: dict[str, dict[str, Any]] = {}

    # ── public API ────────────────────────────────────────────

    def run(self, programme: Programme) -> None:
        """Execute a programme statement by statement."""
        if self._run_depth == 0:
            self._programme = programme
        self._run_depth += 1
        try:
            stmts = programme.statements
            i = 0
            while i < len(stmts):
                stmt = stmts[i]
                if isinstance(stmt, WhenStatement):
                    body: list[Statement] = []
                    i += 1
                    while i < len(stmts) and not isinstance(stmts[i], EndStatement):
                        body.append(stmts[i])
                        i += 1
                    i += 1  # skip end
                    self.handlers.setdefault(stmt.event, []).append(body)
                    continue
                self.execute(stmt)
                i += 1
        finally:
            self._run_depth -= 1

    def execute(self, stmt: Statement) -> Any:
        """Execute a single statement. Returns result for get."""
        if isinstance(stmt, PrintStatement):
            self._exec_print(stmt)
        elif isinstance(stmt, CreateStatement):
            self._exec_create(stmt)
        elif isinstance(stmt, SetStatement):
            self._exec_set(stmt)
        elif isinstance(stmt, GetStatement):
            return self._exec_get(stmt)
        elif isinstance(stmt, SayStatement):
            self._exec_say(stmt)
        elif isinstance(stmt, SendStatement):
            self._exec_send_stmt(stmt)
        elif isinstance(stmt, EventStatement):
            self._exec_event(stmt)
        elif isinstance(stmt, OnStatement):
            self._exec_on(stmt)
        elif isinstance(stmt, GoStatement):
            self._exec_go(stmt)
        elif isinstance(stmt, LookStatement):
            return self._exec_look(stmt)
        elif isinstance(stmt, ConnectStatement):
            self._exec_connect(stmt)
        elif isinstance(stmt, DestroyStatement):
            self._exec_destroy(stmt)
        elif isinstance(stmt, SpriteStatement):
            self._exec_sprite(stmt)
        elif isinstance(stmt, SoundStatement):
            self._exec_sound(stmt)
        elif isinstance(stmt, PlayStatement):
            self._exec_play(stmt)
        elif isinstance(stmt, AnimateStatement):
            self._exec_animate(stmt)
        elif isinstance(stmt, IfStatement):
            self._exec_if(stmt)
        elif isinstance(stmt, UseStatement):
            self._exec_use(stmt)
        elif isinstance(stmt, AfterStatement):
            pass  # Terminal has no setTimeout — noop
        elif isinstance(stmt, BackgroundStatement):
            self.state["_background"] = stmt.value
        elif isinstance(stmt, DefineStatement):
            self.functions[stmt.name] = stmt.body
            self._function_params[stmt.name] = stmt.params
        elif isinstance(stmt, DoStatement):
            self._exec_do(stmt)
        elif isinstance(stmt, RepeatStatement):
            self._exec_repeat(stmt)
        elif isinstance(stmt, AddStatement):
            self._exec_add(stmt)
        elif isinstance(stmt, RemoveStatement):
            self._exec_remove(stmt)
        elif isinstance(stmt, ForEachStatement):
            self._exec_foreach(stmt)
        elif isinstance(stmt, (CommentStatement, BlankStatement, EndStatement)):
            pass
        elif isinstance(stmt, ExtensionCommandStatement):
            raise KeyError(f"Unknown command: '{stmt.verb}'")
        return None

    def send(self, event: str, **payload: Any) -> None:
        """Fire an event — runs all handlers and listeners."""
        has_handlers = event in self.handlers or event in self.listeners
        if event not in UNIVERSAL_EVENTS and event not in self.event_registry:
            if not has_handlers:
                raise KeyError(
                    f"Undeclared event: {event!r}. "
                    f"Use 'event {event}' to declare it first."
                )
            warnings.warn(
                f"Event {event!r} not declared. Consider adding: event {event}"
            )

        if self._send_depth >= _MAX_SEND_DEPTH:
            warnings.warn(f"Max event depth ({_MAX_SEND_DEPTH}) reached, skipping {event!r}")
            return

        self._send_depth += 1
        try:
            # Payload injection: save originals, inject, execute, restore
            originals: dict[str, Any] = {}
            missing_keys: list[str] = []
            for k, v in payload.items():
                if k in self.state:
                    originals[k] = self.state[k]
                else:
                    missing_keys.append(k)
                self.state[k] = v

            try:
                # Fire when/end handlers
                for body in self.handlers.get(event, []):
                    for stmt in body:
                        self.execute(stmt)

                # Fire on listeners
                for listener in self.listeners.get(event, []):
                    self._fire_listener(listener)
            finally:
                # Restore originals, remove injected keys
                for k in payload:
                    if k in originals:
                        self.state[k] = originals[k]
                    elif k in self.state:
                        del self.state[k]
        finally:
            self._send_depth -= 1

    def execute_get(self, target: str) -> list[dict[str, Any]]:
        """Public API for get — returns structured list."""
        return self._exec_get(GetStatement(target=target))

    def execute_send(self, event: str, **payload: Any) -> None:
        """Public API for send."""
        self.send(event, **payload)

    # ── private dispatch ──────────────────────────────────────

    def _exec_print(self, stmt: PrintStatement) -> None:
        text = self._interpolate(stmt.text)
        self.output.write(text + "\n")

    def _exec_create(self, stmt: CreateStatement) -> None:
        kind = stmt.kind.lower()
        if kind == "scene":
            # Register a scene — creates an empty scene definition
            self.scenes[stmt.name] = {}
            return
        if stmt.parent and stmt.parent in self.state:
            parent_val = self._resolve(stmt.parent)
            if isinstance(parent_val, dict):
                value: Any = dict(parent_val)
            else:
                value = parent_val
        elif kind == "object":
            value = {}
        elif kind == "number":
            value = 0
        elif kind == "string":
            value = ""
        elif kind == "list":
            value = []
        else:
            value = {}
        # Use dotted navigation (consistent with _exec_set)
        self._set_path(stmt.name, value)

    def _exec_set(self, stmt: SetStatement) -> None:
        value = self._eval_set_value(stmt.target, stmt.value)
        # Check if target is a scene property (e.g. "corridor.description")
        parts = stmt.target.split(".", 1)
        if len(parts) == 2 and parts[0] in self.scenes:
            scene_name, prop = parts
            if prop == "exits":
                # Parse exits as a list: "courtyard entrance" → ["courtyard", "entrance"]
                if isinstance(value, str):
                    self.scenes[scene_name]["exits"] = value.split()
                else:
                    self.scenes[scene_name]["exits"] = value
            else:
                self.scenes[scene_name][prop] = value
            return
        self._set_path(stmt.target, value)

    def _set_path(self, key: str, value: Any) -> None:
        """Set a value at a dotted key path, creating parent dicts as needed."""
        parts = key.split(".")
        if len(parts) == 1:
            self.state[parts[0]] = value
        else:
            obj = self.state
            for part in parts[:-1]:
                if part not in obj or not isinstance(obj[part], dict):
                    obj[part] = {}
                obj = obj[part]
            obj[parts[-1]] = value

    def _capture_result(
        self,
        into: str,
        result: list[dict[str, Any]],
        *,
        unwrap_single: bool = False,
    ) -> None:
        """Store a structured command result under `into` when requested."""
        if not into:
            return
        value: Any = result
        if unwrap_single and len(result) == 1 and "value" in result[0]:
            value = result[0]["value"]
        self.state[into] = value

    def _delete_path(self, key: str) -> None:
        """Delete a dotted key path if it exists."""
        parts = key.split(".")
        obj: Any = self.state
        for part in parts[:-1]:
            if not isinstance(obj, dict) or part not in obj:
                return
            obj = obj[part]
        if isinstance(obj, dict):
            obj.pop(parts[-1], None)

    def _exec_get(self, stmt: GetStatement) -> list[dict[str, Any]]:
        target = stmt.target.strip()

        # get count of <list>
        if target.startswith("count of "):
            list_name = target[len("count of "):].strip()
            lst = self._resolve(list_name)
            count = len(lst) if isinstance(lst, list) else 0
            self.state["_count"] = count
            result = [{"key": "_count", "value": count}]
            self._capture_result(stmt.into, result, unwrap_single=True)
            return result

        # get all / get all <type>
        if target.startswith("all"):
            parts = target.split(None, 1)
            type_filter = parts[1] if len(parts) > 1 else None
            results = []
            for k, v in self.state.items():
                if k.startswith("_"):
                    continue
                t = _type_name(v)
                if type_filter and t != type_filter:
                    continue
                results.append({"key": k, "value": v, "type": t})
            self._capture_result(stmt.into, results)
            return results

        # get specific key
        val = self._resolve(target)
        if val is None and target not in self.state:
            # Check nested
            parts = target.split(".")
            obj: Any = self.state
            found = True
            for part in parts:
                if isinstance(obj, dict) and part in obj:
                    obj = obj[part]
                else:
                    found = False
                    break
            if not found:
                raise KeyError(f"Unknown key: {target!r}")
            val = obj

        result = [{"key": target, "value": val, "type": _type_name(val)}]
        self._capture_result(stmt.into, result, unwrap_single=True)
        return result

    def _exec_say(self, stmt: SayStatement) -> None:
        text = self._interpolate(stmt.text)
        self.output.write(text + "\n")
        self.state["_last_said"] = text
        self.state["_say_count"] = self.state.get("_say_count", 0) + 1
        self.send("say", text=text)

    def _exec_send_stmt(self, stmt: SendStatement) -> None:
        payload = {k: self._coerce(v) for k, v in stmt.payload.items()}
        self.send(stmt.event, **payload)

    def _exec_event(self, stmt: EventStatement) -> None:
        # Idempotent: widgets may auto-declare events that the game also declares
        self.event_registry[stmt.name] = list(stmt.payload_fields)

    def _exec_on(self, stmt: OnStatement) -> None:
        self.listeners.setdefault(stmt.event, []).append(stmt)

    def _exec_go(self, stmt: GoStatement) -> None:
        target = stmt.target.strip()

        if target == "back":
            prev = self.state.get("_prev_scene")
            if not prev:
                raise KeyError("No previous scene to go back to")
            target = prev

        if target not in self.scenes:
            available = list(self.scenes.keys())
            raise KeyError(
                f"Scene {target!r} not found. Available: {available}"
            )

        current = self.state.get("_scene", "")

        # Check exits restriction
        if current and current in self.scenes:
            current_scene = self.scenes[current]
            exits = current_scene.get("exits")
            if exits is not None and target not in exits:
                raise KeyError(
                    f"Cannot go to {target!r} from {current!r}. "
                    f"Available exits: {exits}"
                )

        # Fire scene_exit
        if current:
            self.send("scene_exit", scene=current)

        # Update state
        self.state["_prev_scene"] = current
        self.state["_scene"] = target

        # Apply scene overrides
        scene_data = self.scenes[target]
        for k, v in scene_data.items():
            if k not in ("exits",):
                self.state[k] = v

        # Fire scene_enter
        self.send("scene_enter", scene=target)

    def _exec_look(self, stmt: LookStatement) -> list[dict[str, Any]]:
        target = stmt.target.strip() if stmt.target else ""

        if target == "programme":
            result = self._look_programme()
            self._capture_result(stmt.into, result)
            return result

        if target == "components":
            result = self._look_components()
            self._capture_result(stmt.into, result)
            return result

        if target:
            # Look at specific object/field
            val = self._resolve(target)
            if val is None:
                raise KeyError(f"Unknown: {target!r}")
            result = [{"key": target, "value": val, "type": _type_name(val)}]
            self._capture_result(stmt.into, result)
            return result

        # Full scene inspection
        result: list[dict[str, Any]] = []
        scene_name = self.state.get("_scene", "")
        if scene_name:
            result.append({"key": "_scene", "value": scene_name, "type": "str"})
            if scene_name in self.scenes:
                scene = self.scenes[scene_name]
                desc = scene.get("description") or scene.get("room_description", "")
                if desc:
                    result.append({"key": "description", "value": desc, "type": "str"})
                exits = scene.get("exits")
                if exits is not None:
                    result.append({"key": "exits", "value": exits, "type": "list"})

        # Non-internal state
        for k, v in self.state.items():
            if k.startswith("_"):
                continue
            result.append({"key": k, "value": v, "type": _type_name(v)})

        # Write scene info to output
        if scene_name:
            self.output.write(f"[{scene_name}]\n")
            if scene_name in self.scenes:
                desc = self.scenes[scene_name].get("description") or self.scenes[scene_name].get("room_description", "")
                if desc:
                    self.output.write(f"{desc}\n")
                exits = self.scenes[scene_name].get("exits")
                if exits:
                    self.output.write(f"Exits: {', '.join(exits)}\n")

        self._capture_result(stmt.into, result)
        return result

    def _look_programme(self) -> list[dict[str, Any]]:
        """Return the current programme's statements as structured data."""
        if self._programme is None:
            self.output.write("programme: no programme loaded\n")
            return []
        stmts = self._programme.statements
        result = [_stmt_to_dict(s) for s in stmts]
        semantic = [d for d in result if d["type"] not in ("blank", "comment")]
        self.output.write(f"programme ({len(stmts)} statements)\n")
        for i, rd in enumerate(result, 1):
            if rd["type"] in ("blank", "comment"):
                continue
            summary = _stmt_summary(rd)
            self.output.write(f"  {i:>3}  {rd['type']:<12}{summary}\n")
        return semantic

    def _look_components(self) -> list[dict[str, Any]]:
        """Return loaded component manifest — namespace, name, provides, exposes."""
        if not self.components:
            self.output.write("components: none loaded\n")
            return []
        self.output.write(f"components ({len(self.components)} loaded)\n")
        result: list[dict[str, Any]] = []
        for ns, info in sorted(self.components.items()):
            name = info["name"]
            alias_str = f" as {ns}" if info.get("alias") else ""
            desc = f" — {info['description']}" if info.get("description") else ""
            parts: list[str] = []
            if info.get("provides"):
                parts.append(f"provides: {' '.join(info['provides'])}")
            if info.get("exposes"):
                parts.append(f"exposes: {' '.join(info['exposes'])}")
            contract = f" [{', '.join(parts)}]" if parts else ""
            self.output.write(f"  {name}{alias_str}{desc}{contract}\n")
            result.append({"namespace": ns, **info})
        return result

    def _exec_connect(self, stmt: ConnectStatement) -> None:
        if not stmt.name:
            # List all connections
            return

        if stmt.url == "disconnect":
            if stmt.name not in self.connections:
                raise KeyError(f"Connection {stmt.name!r} not found")
            del self.connections[stmt.name]
        elif stmt.url:
            self.connections[stmt.name] = stmt.url
        # No url and not disconnect = list (name only, no-op for now)

    def _exec_destroy(self, stmt: DestroyStatement) -> None:
        name = stmt.name
        # Handle dotted paths (e.g. widget.object)
        parts = name.split(".")
        if len(parts) == 1:
            existed = name in self.state
            if existed:
                del self.state[name]
        else:
            obj = self.state
            existed = True
            for part in parts[:-1]:
                if isinstance(obj, dict) and part in obj:
                    obj = obj[part]
                else:
                    existed = False
                    break
            if existed and isinstance(obj, dict) and parts[-1] in obj:
                del obj[parts[-1]]
            else:
                existed = False
        # Fire destroy event (universal — no declaration needed)
        if existed:
            self.send("destroy", name=name)

    def _exec_sprite(self, stmt: SpriteStatement) -> None:
        # Navigate dotted names (e.g. "enemy-grid.e0_0") to the nested dict
        self._set_path(f"{stmt.name}.sprite", stmt.description)

    def _exec_sound(self, stmt: SoundStatement) -> None:
        # Store in audio registry
        self.audio_registry[stmt.name] = stmt.description

    def _exec_play(self, stmt: PlayStatement) -> None:
        # Stub — no-op without adapter. Sound must exist.
        if stmt.sound not in self.audio_registry:
            return  # no-op if sound doesn't exist

    def _exec_animate(self, stmt: AnimateStatement) -> None:
        """Record animation metadata for the web/phaser targets to pick up."""
        self.animation_registry[stmt.name] = {
            "sheet": stmt.sheet,
            "frames": stmt.frames,
            "speed": stmt.speed,
            "mode": stmt.mode,
        }

    def _exec_if(self, stmt: IfStatement) -> None:
        """Execute an if/else block."""
        if self._eval_condition(stmt.condition):
            for s in stmt.then_body:
                self.execute(s)
        else:
            for s in stmt.else_body:
                self.execute(s)

    def _exec_do(self, stmt: DoStatement) -> None:
        """Execute a user-defined function, binding named args as local state."""
        name = stmt.name
        if name not in self.functions:
            warnings.warn(f"Function {name!r} not defined")
            return
        if name in self._call_stack:
            raise RuntimeError(f"Recursive call to {name!r} is not allowed")

        # Bind params: save current state values, set to resolved arg values
        params = self._function_params.get(name, [])
        _MISSING = object()
        saved: dict[str, Any] = {}
        for param in params:
            saved[param] = self._resolve(param) if self._key_exists(param) else _MISSING
            if param in stmt.args:
                self._set_path(param, self._eval_set_value(param, stmt.args[param]))
            else:
                self._set_path(param, None)

        self._call_stack.add(name)
        try:
            for s in self.functions[name]:
                self.execute(s)
        finally:
            self._call_stack.discard(name)
            # Restore saved state
            for param, prev in saved.items():
                if prev is _MISSING:
                    self._delete_path(param)
                else:
                    self._set_path(param, prev)

    _MAX_REPEAT = 10_000

    def _exec_repeat(self, stmt: RepeatStatement) -> None:
        """Execute a counted repeat loop."""
        # Resolve count — literal int or state variable
        try:
            count = int(stmt.count)
        except ValueError:
            val = self._resolve(stmt.count)
            if isinstance(val, (int, float)):
                count = int(val)
            else:
                return  # non-numeric count — skip silently

        if count <= 0:
            return

        count = min(count, self._MAX_REPEAT)

        had_var = stmt.var in self.state if stmt.var else False
        old_val = self.state.get(stmt.var) if stmt.var else None

        try:
            for i in range(1, count + 1):
                if stmt.var:
                    self.state[stmt.var] = i
                for s in stmt.body:
                    self.execute(s)
        finally:
            if stmt.var:
                if had_var:
                    self.state[stmt.var] = old_val
                else:
                    self.state.pop(stmt.var, None)

    _MAX_FOREACH = 10_000

    def _exec_add(self, stmt: AddStatement) -> None:
        """Append an item to a list."""
        item = self._eval_set_value(stmt.item, stmt.item)
        lst = self._resolve(stmt.target)
        if not isinstance(lst, list):
            warnings.warn(f"add: {stmt.target!r} is not a list")
            return
        lst.append(item)

    def _exec_remove(self, stmt: RemoveStatement) -> None:
        """Remove first occurrence of an item from a list (no-op if not found)."""
        item = self._eval_set_value(stmt.item, stmt.item)
        lst = self._resolve(stmt.target)
        if not isinstance(lst, list):
            return
        try:
            lst.remove(item)
        except ValueError:
            pass

    def _exec_foreach(self, stmt: ForEachStatement) -> None:
        """Iterate over a list, binding each item to var."""
        lst = self._resolve(stmt.target)
        if not isinstance(lst, list):
            warnings.warn(f"for each: {stmt.target!r} is not a list")
            return
        _MISSING = object()
        saved = self.state.get(stmt.var, _MISSING)
        try:
            for item in list(lst)[: self._MAX_FOREACH]:
                self.state[stmt.var] = item
                for s in stmt.body:
                    self.execute(s)
        finally:
            if saved is _MISSING:
                self.state.pop(stmt.var, None)
            else:
                self.state[stmt.var] = saved

    def _exec_use(self, stmt: UseStatement) -> None:
        """Load a widget: find, namespace-prefix, apply config, execute."""
        from rosh_lang.core.widgets import find_widget, load_widget, parse_metadata

        stmts = load_widget(
            stmt.name,
            config=stmt.config if stmt.config else None,
            namespace=stmt.alias,
            search_paths=self.search_paths,
        )
        if not stmts:
            return

        # Register component in the loaded-components manifest.
        ns = stmt.alias or stmt.name
        path = find_widget(stmt.name, self.search_paths)
        if path is not None:
            meta = parse_metadata(path)
            self.components[ns] = {
                "name": stmt.name,
                "alias": stmt.alias,
                "description": meta.get("description", ""),
                "provides": meta.get("provides", []),
                "exposes": meta.get("exposes", []),
            }

        # Run the loaded statements as a mini-programme
        # (handles when/end block collection correctly)
        self.run(Programme(statements=stmts))

    # ── listener execution ────────────────────────────────────

    def _fire_listener(self, listener: OnStatement) -> None:
        """Execute a single on-listener."""
        # Check condition if present
        if listener.condition:
            if not self._eval_condition(listener.condition):
                return

        action = listener.action
        args = listener.args

        if action == "set":
            # Parse "target to value" from args
            if " to " in args:
                t, v = args.split(" to ", 1)
                target = t.strip()
                if "." not in target and " " in target:
                    target = ".".join(target.split())
                stmt = SetStatement(target=target, value=v.strip())
                self._exec_set(stmt)
            else:
                tokens = args.split()
                if len(tokens) >= 2:
                    stmt = SetStatement(target=tokens[0], value=tokens[-1])
                    self._exec_set(stmt)
        elif action == "send":
            event_name = args.strip().split()[0] if args.strip() else ""
            if event_name:
                self.send(event_name)
        elif action == "say":
            self._exec_say(SayStatement(text=args))
        elif action == "print":
            self._exec_print(PrintStatement(text=args))
        elif action == "destroy":
            name = args.strip()
            if name:
                self._exec_destroy(DestroyStatement(name=name))
        elif action == "do":
            func_name = args.strip().split()[0] if args.strip() else ""
            if func_name:
                self._exec_do(DoStatement(name=func_name))
        elif action == "play":
            sound = args.strip().split()[0] if args.strip() else ""
            if sound:
                self._exec_play(PlayStatement(sound=sound, mode=""))

    def _eval_condition(self, condition: str) -> bool:
        """Evaluate a simple condition: field op value."""
        parts = condition.split(None, 2)
        if len(parts) != 3:
            return False
        field, op, raw_value = parts[0], parts[1], parts[2]
        current = self._resolve(field)

        # nothing comparisons: work whether or not field is in state
        if raw_value.lower() in ("nothing", "none"):
            if op == "==":
                return current is None
            if op == "!=":
                return current is not None
            return False

        # All other comparisons: missing field means condition fails
        if current is None:
            return False

        target_val = self._coerce(raw_value)
        try:
            if op == ">":
                return current > target_val
            if op == "<":
                return current < target_val
            if op == ">=":
                return current >= target_val
            if op == "<=":
                return current <= target_val
            if op == "==":
                return current == target_val
            if op == "!=":
                return current != target_val
        except TypeError:
            return False
        return False

    # ── set value evaluation ──────────────────────────────────

    def _eval_set_value(self, target: str, raw: str) -> Any:
        """Evaluate the value for a set statement.

        Order: nothing → quoted string → count-of → random → clamp → arithmetic → int → float → raw string.
        """
        # nothing: explicit absence value
        if raw.lower() in ("nothing", "none"):
            return None

        # count of <list>: set n to count of visitors
        if raw.startswith("count of "):
            list_name = raw[len("count of "):].strip()
            lst = self._resolve(list_name)
            return len(lst) if isinstance(lst, list) else 0

        # Quoted string
        if (raw.startswith('"') and raw.endswith('"')) or \
           (raw.startswith("'") and raw.endswith("'")):
            return raw[1:-1]

        # Random: "random" or "random min max"
        if raw == "random":
            return random.random()
        if raw.startswith("random "):
            parts = raw.split()
            if len(parts) == 3:
                try:
                    lo, hi = float(parts[1]), float(parts[2])
                    return lo + random.random() * (hi - lo)
                except ValueError:
                    pass

        # Clamp: "clamp field min max"
        if raw.startswith("clamp "):
            parts = raw.split()
            if len(parts) == 4:
                val = self._resolve(parts[1])
                if isinstance(val, (int, float)):
                    try:
                        lo, hi = float(parts[2]), float(parts[3])
                        return max(lo, min(hi, val))
                    except ValueError:
                        pass

        # Expression: <atom> <op> <atom>
        arith = self._try_arithmetic(raw)
        if arith is not None:
            return arith

        # "ball.width * 1.25" (relative resize, etc.) looks like an
        # arithmetic expression but _try_arithmetic returned None because
        # an operand — typically a property that hasn't been explicitly
        # set yet — couldn't be resolved to a number. Falling through to
        # the raw-text fallback below would silently store the literal,
        # un-evaluated source ("ball.width * 1.25") as the property's
        # value instead of a number, with nothing signalling the failure.
        # Leave the target unchanged instead of corrupting it.
        if self._looks_like_expression(raw):
            return self._resolve(target)

        # Integer
        try:
            return int(raw)
        except ValueError:
            pass

        # Float
        try:
            return float(raw)
        except ValueError:
            pass

        # Boolean
        if raw.lower() == "true":
            return True
        if raw.lower() == "false":
            return False

        # Variable reference: resolve name or dotted name from state (scalars only)
        resolved = self._resolve(raw)
        if resolved is not None and not isinstance(resolved, dict):
            return resolved

        return raw

    def _resolve_atom(self, raw: str) -> Any | None:
        """Resolve a single expression atom to a Python value.

        Handles: quoted strings, booleans, integers, floats, state references.
        Returns None if the atom cannot be resolved (e.g. unknown state key).
        """
        if (raw.startswith('"') and raw.endswith('"')) or \
           (raw.startswith("'") and raw.endswith("'")):
            return raw[1:-1]
        if raw.lower() == "true":
            return True
        if raw.lower() == "false":
            return False
        try:
            return int(raw)
        except ValueError:
            pass
        try:
            return float(raw)
        except ValueError:
            pass
        return self._resolve(raw)

    def _try_arithmetic(self, raw: str) -> Any | None:
        """Evaluate a single binary expression: atom op atom.

        Operators tried in order — multi-char before single-char to avoid
        ambiguous splits (>= before >, <= before <):

          Comparisons: >= <= == !=  then  > <
          Arithmetic:  + - * /

        Arithmetic on non-numeric operands is a no-op (returns None).
        String concatenation: if either operand is a string, + joins them.
        Comparisons return Python bool (True/False).
        """
        for op in self._ARITHMETIC_OPS:
            sep = f" {op} "
            if sep not in raw:
                continue
            parts = raw.split(sep, 1)
            left_raw = parts[0].strip()
            right_raw = parts[1].strip()

            left_val = self._resolve_atom(left_raw)
            right_val = self._resolve_atom(right_raw)

            if op == "+":
                # String concatenation if either side is a string
                if isinstance(left_val, str) or isinstance(right_val, str):
                    if left_val is None or right_val is None:
                        continue
                    return str(left_val) + str(right_val)
                # Numeric addition
                if isinstance(left_val, (int, float)) and isinstance(right_val, (int, float)):
                    return left_val + right_val
                continue

            if op in ("-", "*", "/"):
                if not isinstance(left_val, (int, float)) or \
                   not isinstance(right_val, (int, float)):
                    continue
                if op == "-":
                    return left_val - right_val
                if op == "*":
                    return left_val * right_val
                if op == "/":
                    return None if right_val == 0 else left_val / right_val

            if op in ("==", "!=", "<", ">", "<=", ">="):
                if left_val is None or right_val is None:
                    continue
                try:
                    if op == "==":
                        return left_val == right_val
                    if op == "!=":
                        return left_val != right_val
                    if op == "<":
                        return left_val < right_val
                    if op == ">":
                        return left_val > right_val
                    if op == "<=":
                        return left_val <= right_val
                    if op == ">=":
                        return left_val >= right_val
                except TypeError:
                    continue

        return None

    def _looks_like_expression(self, raw: str) -> bool:
        """True if raw contains one of the recognised binary operators.

        Used to tell apart the two reasons _try_arithmetic can return
        None: "not an expression at all" vs. "was an expression attempt
        that failed to resolve" — only the latter should avoid the
        raw-text fallback in _eval_set_value.
        """
        return any(f" {op} " in raw for op in self._ARITHMETIC_OPS)

    # ── helpers ────────────────────────────────────────────────

    def _interpolate(self, text: str) -> str:
        """Replace {name} and {obj.prop} with values from state."""

        def _replace(match: re.Match[str]) -> str:
            key = match.group(1)
            val = self._resolve(key)
            if val is None:
                # Explicitly set to nothing → empty string
                # Genuinely missing → keep template text for error visibility
                return "" if self._key_exists(key) else match.group(0)
            return str(val)

        return _INTERP_RE.sub(_replace, text)

    def _key_exists(self, key: str) -> bool:
        """Return True if key exists in state (even if its value is None)."""
        parts = key.split(".")
        obj: Any = self.state
        for i, part in enumerate(parts):
            if isinstance(obj, dict) and part in obj:
                if i == len(parts) - 1:
                    return True
                obj = obj[part]
            else:
                return False
        return False

    def _resolve(self, key: str) -> Any | None:
        """Look up a dotted key in state. Returns None if missing."""
        parts = key.split(".")
        obj: Any = self.state
        for part in parts:
            if isinstance(obj, dict) and part in obj:
                obj = obj[part]
            else:
                return None
        return obj

    @staticmethod
    def _coerce(value: str) -> Any:
        """Coerce a raw value string to a Python type."""
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            return value[1:-1]
        try:
            return int(value)
        except ValueError:
            pass
        try:
            return float(value)
        except ValueError:
            pass
        if value.lower() == "true":
            return True
        if value.lower() == "false":
            return False
        return value


def _type_name(val: Any) -> str:
    """Return a Rosh type name for a Python value."""
    if isinstance(val, bool):
        return "bool"
    if isinstance(val, int):
        return "int"
    if isinstance(val, float):
        return "float"
    if isinstance(val, str):
        return "str"
    if isinstance(val, dict):
        return "object"
    if isinstance(val, list):
        return "list"
    return type(val).__name__


def _stmt_to_dict(stmt: Statement) -> dict[str, Any]:
    """Convert a statement to an inspectable dict for look programme."""
    if isinstance(stmt, SetStatement):
        return {"type": "set", "target": stmt.target, "value": stmt.value}
    if isinstance(stmt, CreateStatement):
        d: dict[str, Any] = {"type": "create", "kind": stmt.kind, "name": stmt.name}
        if stmt.parent:
            d["parent"] = stmt.parent
        return d
    if isinstance(stmt, PrintStatement):
        return {"type": "print", "text": stmt.text}
    if isinstance(stmt, SayStatement):
        return {"type": "say", "text": stmt.text}
    if isinstance(stmt, WhenStatement):
        d = {"type": "when", "event": stmt.event}
        if stmt.args:
            d["args"] = stmt.args
        return d
    if isinstance(stmt, OnStatement):
        d = {"type": "on", "event": stmt.event, "action": stmt.action, "args": stmt.args}
        if stmt.condition:
            d["condition"] = stmt.condition
        return d
    if isinstance(stmt, SendStatement):
        d = {"type": "send", "event": stmt.event}
        if stmt.payload:
            d["payload"] = stmt.payload
        return d
    if isinstance(stmt, EventStatement):
        return {"type": "event", "name": stmt.name, "fields": stmt.payload_fields}
    if isinstance(stmt, UseStatement):
        d = {"type": "use", "widget": stmt.name}
        if stmt.alias:
            d["alias"] = stmt.alias
        if stmt.config:
            d["config"] = stmt.config
        return d
    if isinstance(stmt, GoStatement):
        return {"type": "go", "target": stmt.target}
    if isinstance(stmt, LookStatement):
        d = {"type": "look"}
        if stmt.target:
            d["target"] = stmt.target
        if stmt.into:
            d["into"] = stmt.into
        return d
    if isinstance(stmt, GetStatement):
        d = {"type": "get", "target": stmt.target}
        if stmt.into:
            d["into"] = stmt.into
        return d
    if isinstance(stmt, DestroyStatement):
        return {"type": "destroy", "name": stmt.name}
    if isinstance(stmt, SpriteStatement):
        return {"type": "sprite", "name": stmt.name, "description": stmt.description}
    if isinstance(stmt, SoundStatement):
        return {"type": "sound", "name": stmt.name, "description": stmt.description}
    if isinstance(stmt, PlayStatement):
        d = {"type": "play", "name": stmt.sound}
        if stmt.mode:
            d["mode"] = stmt.mode
        return d
    if isinstance(stmt, BackgroundStatement):
        return {"type": "background", "value": stmt.value}
    if isinstance(stmt, AfterStatement):
        d = {"type": "after", "seconds": stmt.delay, "event": stmt.event}
        if stmt.payload:
            d["payload"] = stmt.payload
        return d
    if isinstance(stmt, AnimateStatement):
        return {"type": "animate", "name": stmt.name, "sheet": stmt.sheet,
                "frames": stmt.frames, "speed": stmt.speed, "mode": stmt.mode}
    if isinstance(stmt, IfStatement):
        return {"type": "if", "condition": stmt.condition}
    if isinstance(stmt, DefineStatement):
        d = {"type": "define", "name": stmt.name}
        if stmt.params:
            d["params"] = stmt.params
        return d
    if isinstance(stmt, DoStatement):
        d = {"type": "do", "name": stmt.name}
        if stmt.args:
            d["args"] = stmt.args
        return d
    if isinstance(stmt, RepeatStatement):
        d = {"type": "repeat", "count": stmt.count}
        if stmt.var:
            d["variable"] = stmt.var
        return d
    if isinstance(stmt, AddStatement):
        return {"type": "add", "item": stmt.item, "target": stmt.target}
    if isinstance(stmt, RemoveStatement):
        return {"type": "remove", "item": stmt.item, "target": stmt.target}
    if isinstance(stmt, ForEachStatement):
        return {"type": "foreach", "var": stmt.var, "target": stmt.target}
    if isinstance(stmt, EndStatement):
        return {"type": "end"}
    if isinstance(stmt, ConnectStatement):
        d = {"type": "connect", "name": stmt.name}
        if stmt.url:
            d["url"] = stmt.url
        return d
    if isinstance(stmt, (CommentStatement, BlankStatement)):
        return {"type": "comment" if isinstance(stmt, CommentStatement) else "blank"}
    if isinstance(stmt, ExtensionCommandStatement):
        return {"type": "extension", "keyword": stmt.verb, "args": stmt.args}
    return {"type": type(stmt).__name__.lower().replace("statement", "")}


def _stmt_summary(d: dict[str, Any]) -> str:
    """One-line human-readable summary of a statement dict."""
    t = d.get("type", "")
    if t == "set":
        return f"{d['target']} → {d['value']}"
    if t == "create":
        s = f"{d['kind']} {d['name']}"
        if d.get("parent"):
            s += f" from {d['parent']}"
        return s
    if t in ("print", "say"):
        return d.get("text", "")[:40]
    if t == "when":
        s = d["event"]
        if d.get("args"):
            s += " " + " ".join(str(a) for a in d["args"])
        return s
    if t == "on":
        s = f"{d['event']} → {d['action']} {d.get('args', '')}"
        if d.get("condition"):
            s += f" if {d['condition']}"
        return s
    if t == "send":
        s = d["event"]
        if d.get("payload"):
            s += " " + str(d["payload"])
        return s
    if t == "event":
        return d["name"]
    if t == "use":
        s = d["widget"]
        if d.get("alias"):
            s += f" as {d['alias']}"
        return s
    if t == "go":
        return d.get("target", "")
    if t in ("destroy", "define", "do"):
        return d.get("name", "")
    if t in ("sprite", "sound"):
        return f"{d['name']} \"{d.get('description', '')}\""
    if t == "play":
        s = d["name"]
        if d.get("mode"):
            s += f" {d['mode']}"
        return s
    if t == "look":
        s = d.get("target", "")
        if d.get("into"):
            s = f"{s} into {d['into']}".strip()
        return s
    if t == "get":
        s = d.get("target", "")
        if d.get("into"):
            s = f"{s} into {d['into']}".strip()
        return s
    if t == "background":
        return d.get("value", "")
    if t == "after":
        return f"{d['seconds']}s → {d['event']}"
    if t == "animate":
        return f"{d['name']} sheet={d['sheet']}"
    if t == "if":
        return d.get("condition", "")
    if t == "repeat":
        s = str(d.get("count", ""))
        if d.get("variable"):
            s += f" as {d['variable']}"
        return s
    if t == "connect":
        s = d.get("name", "")
        if d.get("url"):
            s += f" {d['url']}"
        return s
    if t == "extension":
        return f"{d.get('keyword', '')} {d.get('args', '')}".strip()
    return ""


def run(programme: Programme, output: TextIO = sys.stdout) -> Runtime:
    """Convenience: execute a programme and return the runtime."""
    rt = Runtime(output=output)
    rt.run(programme)
    return rt
