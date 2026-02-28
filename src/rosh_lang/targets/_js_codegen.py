"""AST → JavaScript codegen for interactive Rosh programmes.

Walks a Programme and emits calls into the rosh.* JS API — never raw JS.
One emitter per statement type. Pure functions, no side effects.
"""

from __future__ import annotations

from dataclasses import dataclass

from rosh_lang.model import (
    BlankStatement,
    CommentStatement,
    CreateStatement,
    DestroyStatement,
    EndStatement,
    EventStatement,
    GoStatement,
    IfStatement,
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
from rosh_lang.sounds import generate_sound_params


@dataclass
class CompiledProgramme:
    """Result of compiling a Rosh programme to JS."""

    init_code: str  # Top-level statements (create, set, print)
    handler_code: str  # rosh.on() registrations
    needs_loop: bool  # True if when update / when collision
    has_handlers: bool  # True if any when blocks


def compile_programme(
    programme: Programme,
    search_paths: list | None = None,
) -> CompiledProgramme:
    """Compile a full Rosh programme into JS code segments."""
    init_lines: list[str] = []
    handler_lines: list[str] = []
    needs_loop = False
    has_handlers = False

    stmts = programme.statements
    i = 0
    while i < len(stmts):
        stmt = stmts[i]

        if isinstance(stmt, UseStatement):
            # Expand widget and compile its statements
            # Nested use is resolved inside load_widget via _loading guard
            from rosh_lang.widgets import load_widget

            widget_stmts = load_widget(
                stmt.name,
                config=stmt.config if stmt.config else None,
                search_paths=search_paths,
            )
            if widget_stmts:
                sub = compile_programme(
                    Programme(statements=widget_stmts),
                    search_paths=search_paths,
                )
                if sub.init_code:
                    init_lines.append(sub.init_code)
                if sub.handler_code:
                    handler_lines.append(sub.handler_code)
                    has_handlers = True
                if sub.needs_loop:
                    needs_loop = True
            i += 1
            continue

        if isinstance(stmt, WhenStatement):
            has_handlers = True
            event = stmt.event
            args = stmt.args

            if event in ("update", "collision"):
                needs_loop = True

            # Collect body
            body: list[Statement] = []
            i += 1
            while i < len(stmts) and not isinstance(stmts[i], EndStatement):
                body.append(stmts[i])
                i += 1
            i += 1  # skip end

            # Emit body lines
            body_js = _emit_body(body)

            # Choose event name — "click <name>" → "click_<name>"
            if event == "click" and args:
                js_event = f"click_{args[0]}"
            elif event == "collision" and len(args) >= 2:
                # Collision handlers register for "collision" and
                # filter inside the callback by checking a/b names
                js_event = "collision"
                body_js = _wrap_collision_filter(args[0], args[1], body_js)
            elif event in ("keydown", "keyup") and args:
                # Per-key filtering: when keydown ArrowRight → only fires on that key
                js_event = event
                body_js = _wrap_key_filter(args[0], body_js)
            else:
                js_event = event

            args_js = _emit_args_array(args)
            handler_lines.append(
                f'rosh.on("{_escape_js(js_event)}", {args_js}, function(payload) {{\n'
                f"{body_js}"
                f"}});"
            )
        elif isinstance(stmt, OnStatement):
            # One-line event reactor: on <event> <action> <args>
            has_handlers = True
            on_js = _emit_on(stmt)
            if on_js:
                handler_lines.append(on_js)
            i += 1
            continue
        elif isinstance(stmt, (CommentStatement, BlankStatement, EndStatement, EventStatement)):
            i += 1
            continue
        else:
            line = _emit_statement(stmt)
            if line:
                init_lines.append(line)
            i += 1

    return CompiledProgramme(
        init_code="\n".join(init_lines),
        handler_code="\n".join(handler_lines),
        needs_loop=needs_loop,
        has_handlers=has_handlers,
    )


# ── Statement emitters ────────────────────────────────────────────


def _emit_statement(stmt: Statement) -> str:
    """Emit JS for a single top-level statement."""
    if isinstance(stmt, PrintStatement):
        return _emit_print(stmt)
    if isinstance(stmt, CreateStatement):
        return _emit_create(stmt)
    if isinstance(stmt, SetStatement):
        return _emit_set(stmt)
    if isinstance(stmt, DestroyStatement):
        return _emit_destroy(stmt)
    if isinstance(stmt, SendStatement):
        return _emit_send(stmt)
    if isinstance(stmt, SayStatement):
        return _emit_say(stmt)
    if isinstance(stmt, SpriteStatement):
        return _emit_sprite(stmt)
    if isinstance(stmt, SoundStatement):
        return _emit_sound(stmt)
    if isinstance(stmt, PlayStatement):
        return _emit_play(stmt)
    if isinstance(stmt, IfStatement):
        return _emit_if(stmt)
    if isinstance(stmt, GoStatement):
        return _emit_go(stmt)
    return ""


def _emit_print(stmt: PrintStatement) -> str:
    return f'rosh.appendOutput(rosh.interpolate("{_escape_js(stmt.text)}"));'


def _emit_create(stmt: CreateStatement) -> str:
    if stmt.kind.lower() == "scene":
        return f'rosh.createScene("{_escape_js(stmt.name)}");'
    return f'rosh.create("{_escape_js(stmt.kind)}", "{_escape_js(stmt.name)}");'


def _emit_set(stmt: SetStatement) -> str:
    return (
        f'rosh.set("{_escape_js(stmt.target)}", '
        f'rosh.evalSetValue("{_escape_js(stmt.target)}", "{_escape_js(stmt.value)}"));'
    )


def _emit_destroy(stmt: DestroyStatement) -> str:
    return f'rosh.destroy("{_escape_js(stmt.name)}");'


def _emit_send(stmt: SendStatement) -> str:
    if stmt.payload:
        pairs = ", ".join(
            f'"{_escape_js(k)}": "{_escape_js(v)}"'
            for k, v in stmt.payload.items()
        )
        return f'rosh.send("{_escape_js(stmt.event)}", {{{pairs}}});'
    return f'rosh.send("{_escape_js(stmt.event)}");'


def _emit_say(stmt: SayStatement) -> str:
    return f'rosh.appendOutput(rosh.interpolate("{_escape_js(stmt.text)}"));'


def _emit_play(stmt: PlayStatement) -> str:
    mode = stmt.mode or "once"
    return f'rosh.playAudio("{_escape_js(stmt.sound)}", "{_escape_js(mode)}");'


def _emit_sound(stmt: SoundStatement) -> str:
    import json

    params = generate_sound_params(stmt.name, stmt.description)
    params_json = json.dumps(params, separators=(",", ":"))
    return f'rosh.registerSound("{_escape_js(stmt.name)}", {params_json});'


def _emit_sprite(stmt: SpriteStatement) -> str:
    return (
        f'rosh.set("{_escape_js(stmt.name)}.sprite", '
        f'"{_escape_js(stmt.description)}");'
    )


def _emit_go(stmt: GoStatement) -> str:
    return f'rosh.goScene("{_escape_js(stmt.target)}");'


def _emit_on(stmt: OnStatement) -> str:
    """Emit JS for an on-statement — one-line event reactor.

    on <event> <action> <args>
    Actions: set, send, say, print, destroy
    """
    action = stmt.action.lower()
    args = stmt.args
    event = stmt.event

    # Build the body JS based on action type
    if action == "set" and " to " in args:
        target, value = args.split(" to ", 1)
        target = target.strip()
        value = value.strip()
        body = (
            f'rosh.set("{_escape_js(target)}", '
            f'rosh.evalSetValue("{_escape_js(target)}", "{_escape_js(value)}"));'
        )
    elif action == "send":
        body = f'rosh.send("{_escape_js(args.strip())}");'
    elif action in ("say", "print"):
        text = args.strip()
        if (text.startswith('"') and text.endswith('"')) or \
           (text.startswith("'") and text.endswith("'")):
            text = text[1:-1]
        body = f'rosh.appendOutput(rosh.interpolate("{_escape_js(text)}"));'
    elif action == "destroy":
        body = f'rosh.destroy("{_escape_js(args.strip())}");'
    else:
        return ""

    # Wrap in condition check if present
    if stmt.condition:
        parts = stmt.condition.split()
        if len(parts) == 3:
            field, op, val = parts
            js_op = {"=": "===", "==": "===", "!=": "!==", ">": ">", "<": "<", ">=": ">=", "<=": "<="}.get(op, op)
            body = (
                f'var _v = rosh.get("{_escape_js(field)}"); '
                f'if (_v {js_op} {val}) {{ {body} }}'
            )

    return (
        f'rosh.on("{_escape_js(event)}", [], function(payload) {{\n'
        f"  {body}\n"
        f"}});"
    )


# ── Helpers ───────────────────────────────────────────────────────


def _emit_if(stmt: IfStatement, indent: str = "") -> str:
    """Emit JS for an if/else block."""
    parts = stmt.condition.split()
    if len(parts) != 3:
        return ""
    field, op, val = parts
    js_op = {"=": "===", "==": "===", "!=": "!==", ">": ">", "<": "<", ">=": ">=", "<=": "<="}.get(op, op)

    # Coerce value: try number first, then string comparison
    try:
        float(val)
        js_val = val
    except ValueError:
        # String comparison — quote the value
        js_val = f'"{_escape_js(val)}"'

    lines = [f'{indent}if (rosh.get("{_escape_js(field)}") {js_op} {js_val}) {{']
    for s in stmt.then_body:
        line = _emit_statement(s)
        if line:
            # If it's a multi-line block (nested if), re-indent each line
            for sub in line.split("\n"):
                lines.append(f"{indent}  {sub}")
    if stmt.else_body:
        lines.append(f"{indent}}} else {{")
        for s in stmt.else_body:
            line = _emit_statement(s)
            if line:
                for sub in line.split("\n"):
                    lines.append(f"{indent}  {sub}")
    lines.append(f"{indent}}}")
    return "\n".join(lines)


def _emit_body(stmts: list[Statement]) -> str:
    """Emit JS for a list of body statements (inside a handler)."""
    lines: list[str] = []
    for stmt in stmts:
        line = _emit_statement(stmt)
        if line:
            # Multi-line (if blocks) — indent each line
            for sub in line.split("\n"):
                lines.append(f"  {sub}")
    return "\n".join(lines) + "\n" if lines else ""


def _emit_args_array(args: list[str]) -> str:
    """Emit a JS array literal from a list of strings."""
    if not args:
        return "[]"
    items = ", ".join(f'"{_escape_js(a)}"' for a in args)
    return f"[{items}]"


def _wrap_collision_filter(a: str, b: str, body_js: str) -> str:
    """Wrap body JS in a collision name filter."""
    return (
        f'  if (!((payload.a === "{_escape_js(a)}" && payload.b === "{_escape_js(b)}") ||\n'
        f'        (payload.a === "{_escape_js(b)}" && payload.b === "{_escape_js(a)}"))) return;\n'
        f"{body_js}"
    )


def _wrap_key_filter(key: str, body_js: str) -> str:
    """Wrap body JS in a key name filter for keydown/keyup events."""
    return (
        f'  if (payload.key !== "{_escape_js(key)}") return;\n'
        f"{body_js}"
    )


def _escape_js(s: str) -> str:
    """Escape a string for embedding in a JS string literal."""
    return (
        s.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("'", "\\'")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )
