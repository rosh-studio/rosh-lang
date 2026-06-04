"""AST → JavaScript codegen for interactive Rosh programmes.

Walks a Programme and emits calls into the rosh.* JS API — never raw JS.
One emitter per statement type. Pure functions, no side effects.
"""

from __future__ import annotations

from dataclasses import dataclass

from rosh_lang.core.model import (
    AddStatement,
    AfterStatement,
    AnimateStatement,
    BackgroundStatement,
    BlankStatement,
    CommentStatement,
    CreateStatement,
    DefineStatement,
    DestroyStatement,
    DoStatement,
    EndStatement,
    EventStatement,
    ForEachStatement,
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
from rosh_lang.media.sounds import generate_sound_params


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
    target: str = "web",
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
            from rosh_lang.core.widgets import load_widget

            widget_config = dict(stmt.config) if stmt.config else {}
            # Note: controller mode 3d must be set explicitly by the user.
            # 2D games running on threejs target use the 2D-in-3D auto-mapping.
            widget_stmts = load_widget(
                stmt.name,
                config=widget_config or None,
                namespace=stmt.alias,
                search_paths=search_paths,
            )
            if widget_stmts:
                sub = compile_programme(
                    Programme(statements=widget_stmts),
                    search_paths=search_paths,
                    target=target,
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
        elif isinstance(stmt, DefineStatement):
            fn_js = _emit_define(stmt)
            if fn_js:
                init_lines.append(fn_js)
            i += 1
            continue
        elif isinstance(stmt, (CommentStatement, BlankStatement, EndStatement, EventStatement)):
            i += 1
            continue
        else:
            # AnimateStatement requires a game loop for tickAnimations
            if isinstance(stmt, AnimateStatement):
                needs_loop = True
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
    if isinstance(stmt, AnimateStatement):
        return _emit_animate(stmt)
    if isinstance(stmt, AfterStatement):
        return _emit_after(stmt)
    if isinstance(stmt, BackgroundStatement):
        return _emit_background(stmt)
    if isinstance(stmt, DoStatement):
        return _emit_do(stmt)
    if isinstance(stmt, DefineStatement):
        return _emit_define(stmt)
    if isinstance(stmt, RepeatStatement):
        return _emit_repeat(stmt)
    if isinstance(stmt, AddStatement):
        return _emit_add(stmt)
    if isinstance(stmt, RemoveStatement):
        return _emit_remove(stmt)
    if isinstance(stmt, ForEachStatement):
        return _emit_foreach(stmt)
    if isinstance(stmt, LookStatement):
        return "/* look: terminal-only, no-op in JS */"
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
    return f'rosh.say(rosh.interpolate("{_escape_js(stmt.text)}"));'


def _emit_play(stmt: PlayStatement) -> str:
    mode = stmt.mode or "once"
    return f'rosh.playAudio("{_escape_js(stmt.sound)}", "{_escape_js(mode)}");'


def _emit_sound(stmt: SoundStatement) -> str:
    import json

    params = generate_sound_params(stmt.name, stmt.description)
    params_json = json.dumps(params, separators=(",", ":"))
    return f'rosh.registerSound("{_escape_js(stmt.name)}", {params_json});'


def _emit_sprite(stmt: SpriteStatement) -> str:
    # Ensure the object exists — sprite implies create object
    return (
        f'rosh.create("object", "{_escape_js(stmt.name)}"); '
        f'rosh.set("{_escape_js(stmt.name)}.sprite", '
        f'"{_escape_js(stmt.description)}");'
    )


def _emit_go(stmt: GoStatement) -> str:
    return f'rosh.goScene("{_escape_js(stmt.target)}");'


def _emit_animate(stmt: AnimateStatement) -> str:
    import json
    config = {"frames": stmt.frames, "speed": stmt.speed, "mode": stmt.mode}
    config_json = json.dumps(config, separators=(",", ":"))
    return f'rosh.registerAnimation("{_escape_js(stmt.name)}", {config_json});'


def _emit_after(stmt: AfterStatement) -> str:
    delay_ms = int(stmt.delay * 1000)
    return f'setTimeout(function() {{ rosh.send("{_escape_js(stmt.event)}", {{}}); }}, {delay_ms});'


def _emit_background(stmt: BackgroundStatement) -> str:
    return f'rosh.setBackground("{_escape_js(stmt.value)}");'


def _emit_define(stmt: DefineStatement) -> str:
    """Emit a JS function declaration from a define block."""
    body_js = _emit_body(stmt.body)
    name = _safe_fn_name(stmt.name)
    if not stmt.params:
        return f"function {name}() {{\n{body_js}}}"
    # Parameterised function: save/bind/restore state around body
    param_keys = [_escape_js(p) for p in stmt.params]
    save_lines = "\n".join(
        f'  _sv["{k}"] = {{had: rosh.has("{k}"), value: rosh.get("{k}")}}; '
        f'rosh.set("{k}", (_a["{k}"] !== undefined ? _a["{k}"] : null));'
        for k in param_keys
    )
    restore_expr = ", ".join(f'"{k}"' for k in param_keys)
    return (
        f"function {name}(_a) {{\n"
        f"  _a = _a || {{}}; var _sv = {{}};\n"
        f"{save_lines}\n"
        f"{body_js}"
        f"  [{restore_expr}].forEach(function(k) {{\n"
        f"    var p = _sv[k]; if (p.had) {{ rosh.set(k, p.value); }} else {{ rosh.unset(k); }}\n"
        f"  }});\n"
        f"}}"
    )


def _emit_do(stmt: DoStatement) -> str:
    """Emit a JS function call, passing resolved arg values."""
    name = _safe_fn_name(stmt.name)
    if not stmt.args:
        return f"{name}();"
    arg_pairs = ", ".join(
        f'"{_escape_js(k)}": rosh.evalSetValue("{_escape_js(k)}", "{_escape_js(v)}")'
        for k, v in stmt.args.items()
    )
    return f"{name}({{{arg_pairs}}});"


def _emit_repeat(stmt: RepeatStatement) -> str:
    """Emit a JS for loop from a repeat block."""
    body_js = _emit_body(stmt.body)
    count_expr = _escape_js(stmt.count)
    # If count is a literal int, use directly; otherwise resolve from state
    try:
        int(stmt.count)
        count_js = count_expr
    except ValueError:
        count_js = f'(rosh.get("{count_expr}") || 0)'

    if stmt.var:
        var = _escape_js(stmt.var)
        return (
            f"for (var _ri = 1; _ri <= Math.min({count_js}, 10000); _ri++) {{\n"
            f'  rosh.set("{var}", _ri);\n'
            f"{body_js}"
            f"}}\n"
            f'rosh.unset("{var}");'
        )
    else:
        return (
            f"for (var _ri = 0; _ri < Math.min({count_js}, 10000); _ri++) {{\n"
            f"{body_js}"
            f"}}"
        )


def _emit_add(stmt: AddStatement) -> str:
    return (
        f'rosh.addToList("{_escape_js(stmt.target)}", '
        f'rosh.evalSetValue("{_escape_js(stmt.item)}", "{_escape_js(stmt.item)}"));'
    )


def _emit_remove(stmt: RemoveStatement) -> str:
    return (
        f'rosh.removeFromList("{_escape_js(stmt.target)}", '
        f'rosh.evalSetValue("{_escape_js(stmt.item)}", "{_escape_js(stmt.item)}"));'
    )


def _emit_foreach(stmt: ForEachStatement) -> str:
    body_js = _emit_body(stmt.body)
    var = _escape_js(stmt.var)
    target = _escape_js(stmt.target)
    return (
        f'rosh.forEach("{target}", "{var}", function() {{\n'
        f"{body_js}"
        f"}});"
    )


def _safe_fn_name(name: str) -> str:
    """Convert a Rosh function name to a safe JS identifier."""
    safe = name.replace("-", "_").replace(".", "_")
    return f"rosh_fn_{safe}"


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
    elif action == "say":
        text = args.strip()
        if (text.startswith('"') and text.endswith('"')) or \
           (text.startswith("'") and text.endswith("'")):
            text = text[1:-1]
        body = f'rosh.say(rosh.interpolate("{_escape_js(text)}"));'
    elif action == "print":
        text = args.strip()
        if (text.startswith('"') and text.endswith('"')) or \
           (text.startswith("'") and text.endswith("'")):
            text = text[1:-1]
        body = f'rosh.appendOutput(rosh.interpolate("{_escape_js(text)}"));'
    elif action == "destroy":
        body = f'rosh.destroy("{_escape_js(args.strip())}");'
    elif action == "do":
        func_name = args.strip().split()[0] if args.strip() else ""
        if not func_name:
            return ""
        body = f"{_safe_fn_name(func_name)}();"
    else:
        return ""

    # Wrap in condition check if present
    if stmt.condition:
        field, op, val = _parse_condition(stmt.condition)
        if field:
            if val.lower() in ("nothing", "none") and op in ("=", "==", "!="):
                condition_js = f"_v {'!=' if op == '!=' else '=='} null"
            else:
                js_op = {"=": "===", "==": "===", "!=": "!==", ">": ">", "<": "<", ">=": ">=", "<=": "<="}.get(op, op)
                condition_js = f"_v {js_op} {val}"
            body = (
                f'var _v = rosh.get("{_escape_js(field)}"); '
                f"if ({condition_js}) {{ {body} }}"
            )

    return (
        f'rosh.on("{_escape_js(event)}", [], function(payload) {{\n'
        f"  {body}\n"
        f"}});"
    )


# ── Helpers ───────────────────────────────────────────────────────


def _parse_condition(condition: str) -> tuple[str, str, str]:
    """Parse 'field op value' condition, handling quoted values with spaces.

    Returns (field, op, val) or ("", "", "") if unparseable.
    """
    parts = condition.split(None, 2)
    if len(parts) < 3:
        return ("", "", "")
    field, op, val = parts[0], parts[1], parts[2]
    # Handle quoted values: key == " " → val is '" "'
    # Rejoin if the value is a quoted string that was split
    if val.startswith('"') and not val.endswith('"'):
        val = val  # already joined by split(None, 2)
    return (field, op, val)


def _emit_if(stmt: IfStatement, indent: str = "") -> str:
    """Emit JS for an if/else block."""
    field, op, val = _parse_condition(stmt.condition)
    if not field:
        return ""
    if val.lower() in ("nothing", "none") and op in ("=", "==", "!="):
        js_op = "!=" if op == "!=" else "=="
    else:
        js_op = {"=": "===", "==": "===", "!=": "!==", ">": ">", "<": "<", ">=": ">=", "<=": "<="}.get(op, op)

    # Coerce value: try number first, then string comparison
    try:
        float(val)
        js_val = val
    except ValueError:
        if val.lower() in ("nothing", "none"):
            js_val = "null"
        elif val.lower() == "true":
            js_val = "true"
        elif val.lower() == "false":
            js_val = "false"
        else:
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


def _collision_match_expr(pattern: str, field: str) -> str:
    """Return a JS expression that matches a collision name against a pattern.

    Supports wildcards: "bullet.*" matches any name starting with "bullet.".
    """
    if pattern.endswith(".*"):
        prefix = pattern[:-1]  # "bullet.*" → "bullet."
        return f'{field}.startsWith("{_escape_js(prefix)}")'
    return f'{field} === "{_escape_js(pattern)}"'


def _wrap_collision_filter(a: str, b: str, body_js: str) -> str:
    """Wrap body JS in a collision name filter.

    Supports wildcard patterns: "bullet.*" matches bullet.b0, bullet.b1, etc.
    When wildcards match, automatically recycles matched objects (y=-1, vx=vy=0)
    so they visually disappear. Works for pool objects and regular objects alike.
    """
    a_match = _collision_match_expr(a, "payload.a")
    b_match = _collision_match_expr(b, "payload.b")
    a_match_rev = _collision_match_expr(a, "payload.b")
    b_match_rev = _collision_match_expr(b, "payload.a")

    # After filtering, recycle any wildcard-matched objects
    recycle_lines = ""
    if a.endswith(".*") or b.endswith(".*"):
        # Determine which payload field holds each pattern's match
        recycle_lines = (
            '  var _ma = ({a_fwd}) ? payload.a : payload.b;\n'
            '  var _mb = ({a_fwd}) ? payload.b : payload.a;\n'
        ).format(a_fwd=a_match)
        # Recycle all wildcard-matched objects (move off-screen)
        for pat, var in [(a, "_ma"), (b, "_mb")]:
            if pat.endswith(".*"):
                recycle_lines += (
                    f'  rosh.set({var} + ".x", -1);\n'
                    f'  rosh.set({var} + ".y", -1);\n'
                    f'  rosh.set({var} + ".vx", 0);\n'
                    f'  rosh.set({var} + ".vy", 0);\n'
                )

    return (
        f"  if (!(({a_match} && {b_match}) ||\n"
        f"        ({a_match_rev} && {b_match_rev}))) return;\n"
        f"{recycle_lines}"
        f"{body_js}"
    )


def _wrap_key_filter(key: str, body_js: str) -> str:
    """Wrap body JS in a key name filter for keydown/keyup events."""
    return (
        f'  if (payload.key !== "{_escape_js(key)}") return;\n'
        f"{body_js}"
    )


def _escape_js(s: str) -> str:
    """Escape a string for embedding in a JS string literal inside a <script> block.

    '</' is replaced with '<\\/' so that '</script>' in a string value
    cannot break out of the enclosing <script> tag (XSS vector).
    """
    return (
        s.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("'", "\\'")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("</", "<\\/")
    )
