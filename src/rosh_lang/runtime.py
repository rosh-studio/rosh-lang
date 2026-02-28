"""Full runtime — executes a Rosh Programme statement by statement.

Implements 17 keywords per BUILDING-ROSH.md Sections 5 & 7.
"""

from __future__ import annotations

import re
import sys
import warnings
from typing import Any, TextIO

from rosh_lang.model import (
    BlankStatement,
    CommentStatement,
    ConnectStatement,
    CreateStatement,
    DestroyStatement,
    EndStatement,
    EventStatement,
    GetStatement,
    GoStatement,
    LookStatement,
    OnStatement,
    PlayStatement,
    PrintStatement,
    Programme,
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
    "keyup", "destroy", "timer", "message",
    "scene_exit", "scene_enter",
})

# Max send depth to prevent infinite cascading
_MAX_SEND_DEPTH = 10


class Runtime:
    """Execute a Rosh programme."""

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
        self.output = output
        self.search_paths = search_paths
        self._send_depth = 0

    # ── public API ────────────────────────────────────────────

    def run(self, programme: Programme) -> None:
        """Execute a programme statement by statement."""
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
        elif isinstance(stmt, UseStatement):
            self._exec_use(stmt)
        elif isinstance(stmt, (CommentStatement, BlankStatement, EndStatement)):
            pass
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

    def _exec_get(self, stmt: GetStatement) -> list[dict[str, Any]]:
        target = stmt.target.strip()

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

        return [{"key": target, "value": val, "type": _type_name(val)}]

    def _exec_say(self, stmt: SayStatement) -> None:
        text = self._interpolate(stmt.text)
        self.output.write(text + "\n")
        self.state["_last_said"] = text
        self.state["_say_count"] = self.state.get("_say_count", 0) + 1

    def _exec_send_stmt(self, stmt: SendStatement) -> None:
        payload = {k: self._coerce(v) for k, v in stmt.payload.items()}
        self.send(stmt.event, **payload)

    def _exec_event(self, stmt: EventStatement) -> None:
        if stmt.name in self.event_registry:
            raise ValueError(f"Event {stmt.name!r} already declared")
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

        if target:
            # Look at specific object/field
            val = self._resolve(target)
            if val is None:
                raise KeyError(f"Unknown: {target!r}")
            return [{"key": target, "value": val, "type": _type_name(val)}]

        # Full scene inspection
        result: list[dict[str, Any]] = []
        scene_name = self.state.get("_scene", "")
        if scene_name:
            result.append({"key": "_scene", "value": scene_name, "type": "str"})
            if scene_name in self.scenes:
                scene = self.scenes[scene_name]
                if "room_description" in scene:
                    result.append({"key": "description", "value": scene["room_description"], "type": "str"})
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
                desc = self.scenes[scene_name].get("room_description", "")
                if desc:
                    self.output.write(f"{desc}\n")
                exits = self.scenes[scene_name].get("exits")
                if exits:
                    self.output.write(f"Exits: {', '.join(exits)}\n")

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

    def _exec_use(self, stmt: UseStatement) -> None:
        """Load a widget: find, namespace-prefix, apply config, execute."""
        from rosh_lang.widgets import load_widget

        stmts = load_widget(
            stmt.name,
            config=stmt.config if stmt.config else None,
            search_paths=self.search_paths,
        )
        if not stmts:
            return
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

    def _eval_condition(self, condition: str) -> bool:
        """Evaluate a simple condition: field op value."""
        parts = condition.split()
        if len(parts) != 3:
            return False
        field, op, raw_value = parts
        current = self._resolve(field)
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

        Order: quoted string → arithmetic → int → float → raw string.
        """
        # Quoted string
        if (raw.startswith('"') and raw.endswith('"')) or \
           (raw.startswith("'") and raw.endswith("'")):
            return raw[1:-1]

        # Arithmetic: <left> <op> <right>
        arith = self._try_arithmetic(raw)
        if arith is not None:
            return arith

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

        return raw

    def _try_arithmetic(self, raw: str) -> Any | None:
        """Try to parse 'left op right' arithmetic expression.

        Supports variable references on both sides:
        - set x to x + 1       (self-ref left, literal right)
        - set x to x + drift   (self-ref left, variable right)
        - set x to y + 1       (cross-ref left, literal right)
        - set x to y + z       (both variable)
        """
        for op in ("+", "-", "*", "/"):
            if f" {op} " in raw:
                parts = raw.split(f" {op} ", 1)
                left = parts[0].strip()
                right = parts[1].strip()

                # Right operand: literal number or variable reference
                try:
                    right_val: int | float = int(right)
                except ValueError:
                    try:
                        right_val = float(right)
                    except ValueError:
                        resolved = self._resolve(right)
                        if isinstance(resolved, (int, float)):
                            right_val = resolved
                        else:
                            continue

                # Left operand: resolve from state
                current = self._resolve(left)
                if current is None or not isinstance(current, (int, float)):
                    continue

                if op == "+":
                    return current + right_val
                if op == "-":
                    return current - right_val
                if op == "*":
                    return current * right_val
                if op == "/":
                    if right_val == 0:
                        return None
                    return current / right_val
        return None

    # ── helpers ────────────────────────────────────────────────

    def _interpolate(self, text: str) -> str:
        """Replace {name} and {obj.prop} with values from state."""

        def _replace(match: re.Match[str]) -> str:
            key = match.group(1)
            val = self._resolve(key)
            if val is None:
                return match.group(0)
            return str(val)

        return _INTERP_RE.sub(_replace, text)

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


def run(programme: Programme, output: TextIO = sys.stdout) -> Runtime:
    """Convenience: execute a programme and return the runtime."""
    rt = Runtime(output=output)
    rt.run(programme)
    return rt
