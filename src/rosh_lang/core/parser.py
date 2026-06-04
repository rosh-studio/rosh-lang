"""Line-oriented parser for Rosh programmes.

Reads .rosh files and produces a Programme (list of Statements).
All 16 keywords per BUILDING-ROSH.md Section 3.

The parser ONLY produces data — no logic, no execution, no side effects.
"""

from __future__ import annotations

import re
import shlex
from pathlib import Path

from rosh_lang.core.model import (
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
    ElseStatement,
    EndStatement,
    EventStatement,
    ExtensionCommandStatement,
    GetStatement,
    GoStatement,
    IfStatement,
    LookStatement,
    OnStatement,
    PlayStatement,
    PrintStatement,
    Programme,
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


class ParseError(Exception):
    """Raised when a programme line cannot be parsed."""

    def __init__(self, message: str, line: int = 0, source: str = "") -> None:
        loc = f"{source}:{line}" if source else f"line {line}"
        super().__init__(f"{loc}: {message}")
        self.line = line
        self.source = source


def parse_file(path: Path | str, *, allow_extensions: bool = False) -> Programme:
    """Parse a .rosh file into a Programme."""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    return parse_string(text, source=str(path), allow_extensions=allow_extensions)


def parse_string(text: str, source: str = "<string>", *, allow_extensions: bool = False) -> Programme:
    """Parse a string of Rosh code into a Programme."""
    from rosh_lang.core.normalise import normalise
    # Normalise each line; a single line may expand to multiple canonical lines
    expanded_lines: list[tuple[int, str]] = []
    for i, raw_line in enumerate(text.splitlines(), start=1):
        result = normalise(raw_line)
        parts = result.splitlines()
        if parts:
            for expanded in parts:
                expanded_lines.append((i, expanded))
        else:
            expanded_lines.append((i, raw_line))

    statements: list[Statement] = []
    for i, raw_line in expanded_lines:
        stripped = raw_line.strip()
        # "else if ..." → ElseStatement + IfStatement (same line number)
        if stripped.lower().startswith("else ") and stripped[5:].strip().lower().startswith("if "):
            statements.append(ElseStatement(line=i))
            if_part = stripped[5:].strip()
            statements.append(_parse_line(if_part, line=i, source=source, allow_extensions=allow_extensions))
        else:
            stmt = _parse_line(raw_line, line=i, source=source, allow_extensions=allow_extensions)
            statements.append(stmt)
    # Post-pass: collect if/else/end blocks into IfStatement trees
    statements = _collect_if_blocks(statements, source=source)
    # Post-pass: collect define...end blocks into DefineStatement.body
    statements = _collect_define_blocks(statements, source=source)
    # Post-pass: collect repeat...end blocks into RepeatStatement.body
    statements = _collect_repeat_blocks(statements, source=source)
    return Programme(statements=statements, source=source)


def _parse_line(raw: str, line: int, source: str, *, allow_extensions: bool = False) -> Statement:
    """Parse a single line of Rosh code."""
    stripped = raw.strip()

    if not stripped:
        return BlankStatement(line=line)

    if stripped.startswith("#"):
        return CommentStatement(text=stripped[1:].strip(), line=line)

    keyword = stripped.split()[0].lower()

    dispatch = {
        "print": _parse_print,
        "create": _parse_create,
        "set": _parse_set,
        "when": _parse_when,
        "end": lambda _s, _l, _src: EndStatement(line=_l),
        "if": _parse_if,
        "else": lambda _s, _l, _src: ElseStatement(line=_l),
        "get": _parse_get,
        "say": _parse_say,
        "send": _parse_send,
        "event": _parse_event,
        "on": _parse_on,
        "go": _parse_go,
        "look": _parse_look,
        "connect": _parse_connect,
        "destroy": _parse_destroy,
        "sprite": _parse_sprite,
        "sound": _parse_sound,
        "play": _parse_play,
        "animate": _parse_animate,
        "use": _parse_use,
        "after": _parse_after,
        "background": _parse_background,
        "define": _parse_define,
        "do": _parse_do,
        "repeat": _parse_repeat,
    }

    handler = dispatch.get(keyword)
    if handler is None:
        if allow_extensions:
            rest = stripped[len(keyword):].strip()
            return ExtensionCommandStatement(verb=keyword, args=rest, line=line)
        raise ParseError(f"Unknown keyword: '{keyword}'", line=line, source=source)
    return handler(stripped, line, source)


# ── Keyword parsers ────────────────────────────────────────────


def _parse_print(line_text: str, line: int, source: str) -> PrintStatement:
    rest = line_text[len("print"):].strip()
    if not rest:
        return PrintStatement(text="", line=line)
    if rest.startswith('"') and rest.endswith('"'):
        text = rest[1:-1]
    elif rest.startswith("'") and rest.endswith("'"):
        text = rest[1:-1]
    else:
        text = rest
    return PrintStatement(text=text, line=line)


def _parse_create(line_text: str, line: int, source: str) -> CreateStatement:
    tokens = line_text.split()
    if len(tokens) < 3:
        raise ParseError(
            "create requires at least: create <kind> <name>",
            line=line, source=source,
        )
    idx = 1
    count = 1
    if tokens[idx].isdigit():
        count = int(tokens[idx])
        idx += 1
    kind = tokens[idx].lower()
    idx += 1
    if kind == "objects":
        kind = "object"
    if idx < len(tokens) and tokens[idx].lower() == "as":
        idx += 1
        if idx >= len(tokens):
            raise ParseError("Expected name after 'as'", line=line, source=source)
        name = tokens[idx]
        idx += 1
    else:
        if idx >= len(tokens):
            raise ParseError("create requires a name", line=line, source=source)
        name = tokens[idx]
        idx += 1
    parent = ""
    if idx < len(tokens) and tokens[idx].lower() == "from":
        idx += 1
        if idx >= len(tokens):
            raise ParseError("Expected parent name after 'from'", line=line, source=source)
        parent = tokens[idx]
    return CreateStatement(kind=kind, name=name, parent=parent, count=count, line=line)


def _parse_set(line_text: str, line: int, source: str) -> SetStatement:
    rest = line_text[len("set"):].strip()
    if not rest:
        raise ParseError("set requires target and value", line=line, source=source)
    if " to " in rest:
        parts = rest.split(" to ", 1)
        target_str = parts[0].strip()
        value_str = parts[1].strip()
    else:
        tokens = rest.split()
        if len(tokens) < 2:
            raise ParseError("set requires target and value", line=line, source=source)
        value_str = tokens[-1]
        target_str = " ".join(tokens[:-1])
    if "." not in target_str and " " in target_str:
        target = ".".join(target_str.split())
    else:
        target = target_str
    return SetStatement(target=target, value=value_str, line=line)


def _parse_when(line_text: str, line: int, source: str) -> WhenStatement:
    rest = line_text[len("when"):].strip()
    if rest.lower().endswith(" then"):
        rest = rest[:-5].strip()
    elif rest.lower() == "then":
        rest = ""
    if not rest:
        raise ParseError("when requires an event name", line=line, source=source)
    try:
        tokens = shlex.split(rest)
    except ValueError:
        tokens = rest.split()
    event = tokens[0]
    args = tokens[1:]
    return WhenStatement(event=event, args=args, line=line)


def _parse_get(line_text: str, line: int, source: str) -> GetStatement:
    rest = line_text[len("get"):].strip()
    if not rest:
        raise ParseError("get requires a target", line=line, source=source)
    return GetStatement(target=rest, line=line)


def _parse_say(line_text: str, line: int, source: str) -> SayStatement:
    rest = line_text[len("say"):].strip()
    if rest.startswith('"') and rest.endswith('"'):
        text = rest[1:-1]
    elif rest.startswith("'") and rest.endswith("'"):
        text = rest[1:-1]
    else:
        text = rest
    if not text:
        raise ParseError("say requires text", line=line, source=source)
    return SayStatement(text=text, line=line)


def _parse_send(line_text: str, line: int, source: str) -> SendStatement:
    rest = line_text[len("send"):].strip()
    if not rest:
        raise ParseError("send requires an event name", line=line, source=source)
    tokens = rest.split()
    event = tokens[0]
    payload: dict[str, str] = {}
    for tok in tokens[1:]:
        if "=" in tok:
            k, v = tok.split("=", 1)
            payload[k] = v
    return SendStatement(event=event, payload=payload, line=line)


def _parse_event(line_text: str, line: int, source: str) -> EventStatement:
    rest = line_text[len("event"):].strip()
    if not rest:
        raise ParseError("event requires a name", line=line, source=source)
    tokens = rest.split()
    name = tokens[0]
    payload_fields = tokens[1:]
    return EventStatement(name=name, payload_fields=payload_fields, line=line)


def _parse_on(line_text: str, line: int, source: str) -> OnStatement:
    rest = line_text[len("on"):].strip()
    if not rest:
        raise ParseError("on requires an event and action", line=line, source=source)
    tokens = rest.split()
    event = tokens[0]
    remaining = tokens[1:]

    # Check for conditional form: on <event> when <field> <op> <value> <action...>
    condition = ""
    if remaining and remaining[0].lower() == "when":
        # on check when level > 3 set message to "high"
        # Parse condition: field op value
        if len(remaining) < 4:
            raise ParseError("on ... when requires: field op value action", line=line, source=source)
        cond_field = remaining[1]
        cond_op = remaining[2]
        # Handle quoted condition values (e.g., when key == " ")
        # .split() breaks quoted strings with spaces into multiple tokens
        if remaining[3].startswith('"') or remaining[3].startswith("'"):
            quote_char = remaining[3][0]
            if remaining[3].endswith(quote_char) and len(remaining[3]) > 1:
                # Single-token quoted value like "ArrowUp"
                cond_value = remaining[3]
                remaining = remaining[4:]
            else:
                # Multi-token quoted value — rejoin until closing quote
                end_idx = 4
                joined = remaining[3]
                while end_idx < len(remaining):
                    joined += " " + remaining[end_idx]
                    if remaining[end_idx].endswith(quote_char):
                        end_idx += 1
                        break
                    end_idx += 1
                cond_value = joined
                remaining = remaining[end_idx:]
        else:
            cond_value = remaining[3]
            remaining = remaining[4:]
        condition = f"{cond_field} {cond_op} {cond_value}"

    if not remaining:
        raise ParseError("on requires an action (set, send, say, print)", line=line, source=source)

    action = remaining[0].lower()
    args = " ".join(remaining[1:])

    return OnStatement(event=event, action=action, args=args, condition=condition, line=line)


def _parse_go(line_text: str, line: int, source: str) -> GoStatement:
    rest = line_text[len("go"):].strip()
    if not rest:
        raise ParseError("go requires a scene name", line=line, source=source)
    return GoStatement(target=rest, line=line)


def _parse_look(line_text: str, line: int, source: str) -> LookStatement:
    rest = line_text[len("look"):].strip()
    return LookStatement(target=rest, line=line)


def _parse_connect(line_text: str, line: int, source: str) -> ConnectStatement:
    rest = line_text[len("connect"):].strip()
    if not rest:
        return ConnectStatement(name="", url="", line=line)
    tokens = rest.split()
    name = tokens[0]
    url = tokens[1] if len(tokens) > 1 else ""
    return ConnectStatement(name=name, url=url, line=line)


def _parse_destroy(line_text: str, line: int, source: str) -> DestroyStatement:
    rest = line_text[len("destroy"):].strip()
    if not rest:
        raise ParseError("destroy requires an object name", line=line, source=source)
    return DestroyStatement(name=rest, line=line)


def _parse_sprite(line_text: str, line: int, source: str) -> SpriteStatement:
    rest = line_text[len("sprite"):].strip()
    if not rest:
        raise ParseError("sprite requires a name and description", line=line, source=source)
    tokens = rest.split(None, 1)
    name = tokens[0]
    desc = ""
    if len(tokens) > 1:
        desc = tokens[1]
        if desc.startswith('"') and desc.endswith('"'):
            desc = desc[1:-1]
        elif desc.startswith("'") and desc.endswith("'"):
            desc = desc[1:-1]
    return SpriteStatement(name=name, description=desc, line=line)


def _parse_sound(line_text: str, line: int, source: str) -> SoundStatement:
    rest = line_text[len("sound"):].strip()
    if not rest:
        raise ParseError("sound requires a name and description", line=line, source=source)
    tokens = rest.split(None, 1)
    name = tokens[0]
    desc = ""
    if len(tokens) > 1:
        desc = tokens[1]
        if desc.startswith('"') and desc.endswith('"'):
            desc = desc[1:-1]
        elif desc.startswith("'") and desc.endswith("'"):
            desc = desc[1:-1]
    return SoundStatement(name=name, description=desc, line=line)


def _parse_play(line_text: str, line: int, source: str) -> PlayStatement:
    rest = line_text[len("play"):].strip()
    if not rest:
        raise ParseError("play requires a sound name", line=line, source=source)
    tokens = rest.split()
    sound = tokens[0]
    mode = tokens[1].lower() if len(tokens) > 1 else ""
    return PlayStatement(sound=sound, mode=mode, line=line)


def _parse_use(line_text: str, line: int, source: str) -> UseStatement:
    rest = line_text[len("use"):].strip()
    if not rest:
        raise ParseError("use requires a widget name", line=line, source=source)
    tokens = rest.split()
    name = tokens[0]
    # Detect optional alias: use <name> as <alias> [config...]
    alias: str | None = None
    i = 1
    if i + 1 < len(tokens) and tokens[i].lower() == "as":
        alias = tokens[i + 1]
        i += 2
    # Parse config: key value pairs after name (and optional alias)
    config: dict[str, str] = {}
    while i < len(tokens):
        key = tokens[i]
        if i + 1 < len(tokens):
            config[key] = tokens[i + 1]
            i += 2
        else:
            # Odd trailing token — treat as flag with empty value
            config[key] = ""
            i += 1
    return UseStatement(name=name, alias=alias, config=config, line=line)


def _parse_after(line_text: str, line: int, source: str) -> AfterStatement:
    """Parse 'after <seconds> send <event>'."""
    rest = line_text[len("after"):].strip()
    if not rest:
        raise ParseError("after requires: after <seconds> send <event>", line=line, source=source)
    tokens = rest.split()
    if len(tokens) < 3:
        raise ParseError("after requires: after <seconds> send <event>", line=line, source=source)
    # Parse delay
    try:
        delay = float(tokens[0])
    except ValueError:
        raise ParseError(f"after delay must be a number, got: {tokens[0]!r}", line=line, source=source)
    # Expect "send"
    if tokens[1].lower() != "send":
        raise ParseError("after requires 'send' keyword: after <seconds> send <event>", line=line, source=source)
    event = tokens[2]
    return AfterStatement(delay=delay, event=event, line=line)


def _parse_animate(line_text: str, line: int, source: str) -> AnimateStatement:
    """Parse 'animate player sheet "player-sheet.png" frames 4 [speed 8] [mode loop]'."""
    rest = line_text[len("animate"):].strip()
    if not rest:
        raise ParseError("animate requires an object name", line=line, source=source)

    # Extract the object name (first token)
    tokens = rest.split()
    name = tokens[0]

    # Extract sheet path (must be quoted)
    if "sheet" not in rest.lower():
        raise ParseError("animate requires: sheet \"path\"", line=line, source=source)

    # Find sheet "..." — extract quoted path
    sheet_match = re.search(r'sheet\s+"([^"]+)"', rest, re.IGNORECASE)
    if not sheet_match:
        sheet_match = re.search(r"sheet\s+'([^']+)'", rest, re.IGNORECASE)
    if not sheet_match:
        raise ParseError('animate sheet requires a quoted path: sheet "file.png"', line=line, source=source)
    sheet = sheet_match.group(1)

    # Extract frames N (required)
    frames_match = re.search(r'frames\s+(\d+)', rest, re.IGNORECASE)
    if not frames_match:
        raise ParseError("animate requires: frames <N>", line=line, source=source)
    frames = int(frames_match.group(1))

    # Extract optional speed N (default 8)
    speed = 8
    speed_match = re.search(r'speed\s+(\d+)', rest, re.IGNORECASE)
    if speed_match:
        speed = int(speed_match.group(1))

    # Extract optional mode (default "loop")
    mode = "loop"
    mode_match = re.search(r'mode\s+(loop|once|bounce)', rest, re.IGNORECASE)
    if mode_match:
        mode = mode_match.group(1).lower()

    return AnimateStatement(
        name=name, sheet=sheet, frames=frames, speed=speed, mode=mode, line=line,
    )


def _parse_background(line_text: str, line: int, source: str) -> BackgroundStatement:
    """Parse 'background "#1a1a2e"' or 'background "sky.png"'."""
    rest = line_text[len("background"):].strip()
    if not rest:
        raise ParseError("background requires a colour or image path", line=line, source=source)
    if rest.startswith('"') and rest.endswith('"'):
        value = rest[1:-1]
    elif rest.startswith("'") and rest.endswith("'"):
        value = rest[1:-1]
    else:
        value = rest
    if not value:
        raise ParseError("background requires a colour or image path", line=line, source=source)
    return BackgroundStatement(value=value, line=line)


def _parse_if(line_text: str, line: int, source: str) -> IfStatement:
    """Parse 'if <field> <op> <value>' — body collected in post-pass."""
    rest = line_text[len("if"):].strip()
    # Strip optional trailing "then"
    if rest.lower().endswith(" then"):
        rest = rest[:-5].strip()
    if not rest:
        raise ParseError("if requires a condition (field op value)", line=line, source=source)
    tokens = rest.split()
    if len(tokens) < 3:
        raise ParseError(
            "if condition must be: field op value",
            line=line, source=source,
        )
    condition = " ".join(tokens[:3])
    return IfStatement(condition=condition, line=line)


def _collect_if_blocks(
    stmts: list[Statement], source: str = ""
) -> list[Statement]:
    """Post-pass: collect if/else/end into IfStatement with then_body/else_body.

    Handles nesting: if blocks inside if blocks, if blocks inside when blocks.
    Does NOT consume end statements that belong to when blocks — only those
    that match an open if.
    """
    result: list[Statement] = []
    i = 0
    while i < len(stmts):
        stmt = stmts[i]
        if isinstance(stmt, IfStatement):
            if_stmt, i = _collect_one_if(stmts, i, source)
            result.append(if_stmt)
        else:
            result.append(stmt)
            i += 1
    return result


def _collect_one_if(
    stmts: list[Statement], start: int, source: str
) -> tuple[IfStatement, int]:
    """Collect a single if/else/end block starting at index `start`.

    Returns (populated IfStatement, next index after the closing end).
    """
    if_stmt = stmts[start]
    assert isinstance(if_stmt, IfStatement)
    then_body: list[Statement] = []
    else_body: list[Statement] = []
    in_else = False
    i = start + 1

    while i < len(stmts):
        s = stmts[i]

        # Nested if — recurse
        if isinstance(s, IfStatement):
            nested, i = _collect_one_if(stmts, i, source)
            if in_else:
                else_body.append(nested)
            else:
                then_body.append(nested)
            continue

        # Else — switch to else branch
        if isinstance(s, ElseStatement):
            in_else = True
            i += 1
            # else-if chain: if next stmt is IfStatement on the SAME line,
            # it came from "else if ..." and shares the closing end
            if i < len(stmts) and isinstance(stmts[i], IfStatement) and stmts[i].line == s.line:
                nested_if, i = _collect_one_if(stmts, i, source)
                else_body.append(nested_if)
                return IfStatement(
                    condition=if_stmt.condition,
                    then_body=then_body,
                    else_body=else_body,
                    line=if_stmt.line,
                ), i
            continue

        # End — closes this if block
        if isinstance(s, EndStatement):
            return IfStatement(
                condition=if_stmt.condition,
                then_body=then_body,
                else_body=else_body,
                line=if_stmt.line,
            ), i + 1

        # Regular statement — add to current branch
        if in_else:
            else_body.append(s)
        else:
            then_body.append(s)
        i += 1

    raise ParseError(
        "if block has no matching end",
        line=if_stmt.line, source=source,
    )


def _parse_define(line_text: str, line: int, source: str) -> DefineStatement:
    rest = line_text[len("define"):].strip()
    if not rest:
        raise ParseError("define requires a function name", line=line, source=source)
    name = rest.split()[0]
    return DefineStatement(name=name, line=line)


def _parse_do(line_text: str, line: int, source: str) -> DoStatement:
    rest = line_text[len("do"):].strip()
    if not rest:
        raise ParseError("do requires a function name", line=line, source=source)
    name = rest.split()[0]
    return DoStatement(name=name, line=line)


def _parse_repeat(line_text: str, line: int, source: str) -> RepeatStatement:
    """Parse 'repeat <count>' or 'repeat <count> as <var>'."""
    rest = line_text[len("repeat"):].strip()
    if not rest:
        raise ParseError("repeat requires a count", line=line, source=source)
    tokens = rest.split()
    count = tokens[0]
    var = ""
    if len(tokens) >= 3 and tokens[1].lower() == "as":
        var = tokens[2]
    return RepeatStatement(count=count, var=var, line=line)


def _collect_repeat_blocks(
    stmts: list[Statement], source: str = ""
) -> list[Statement]:
    """Post-pass: collect repeat...end into RepeatStatement with body."""
    result: list[Statement] = []
    i = 0
    while i < len(stmts):
        stmt = stmts[i]
        if isinstance(stmt, RepeatStatement):
            repeat_stmt, i = _collect_one_repeat(stmts, i, source)
            result.append(repeat_stmt)
        else:
            result.append(stmt)
            i += 1
    return result


def _collect_one_repeat(
    stmts: list[Statement], start: int, source: str
) -> tuple[RepeatStatement, int]:
    """Collect a single repeat...end block starting at index `start`."""
    repeat_stmt = stmts[start]
    assert isinstance(repeat_stmt, RepeatStatement)
    body: list[Statement] = []
    i = start + 1

    while i < len(stmts):
        s = stmts[i]

        if isinstance(s, EndStatement):
            return RepeatStatement(
                count=repeat_stmt.count,
                var=repeat_stmt.var,
                body=body,
                line=repeat_stmt.line,
            ), i + 1

        # Nested repeat — recurse
        if isinstance(s, RepeatStatement):
            nested, i = _collect_one_repeat(stmts, i, source)
            body.append(nested)
            continue

        body.append(s)
        i += 1

    raise ParseError(
        "repeat block has no matching end",
        line=repeat_stmt.line, source=source,
    )


def _collect_define_blocks(
    stmts: list[Statement], source: str = ""
) -> list[Statement]:
    """Post-pass: collect define...end into DefineStatement with body.

    Runs after _collect_if_blocks so if blocks inside define bodies
    are already nested. Only consumes EndStatements that match a define.
    """
    result: list[Statement] = []
    i = 0
    while i < len(stmts):
        stmt = stmts[i]
        if isinstance(stmt, DefineStatement):
            define_stmt, i = _collect_one_define(stmts, i, source)
            result.append(define_stmt)
        else:
            result.append(stmt)
            i += 1
    return result


def _collect_one_define(
    stmts: list[Statement], start: int, source: str
) -> tuple[DefineStatement, int]:
    """Collect a single define...end block starting at index `start`."""
    define_stmt = stmts[start]
    assert isinstance(define_stmt, DefineStatement)
    body: list[Statement] = []
    i = start + 1

    while i < len(stmts):
        s = stmts[i]

        if isinstance(s, EndStatement):
            return DefineStatement(
                name=define_stmt.name,
                body=body,
                line=define_stmt.line,
            ), i + 1

        # Nested define — recurse
        if isinstance(s, DefineStatement):
            nested, i = _collect_one_define(stmts, i, source)
            body.append(nested)
            continue

        body.append(s)
        i += 1

    raise ParseError(
        "define block has no matching end",
        line=define_stmt.line, source=source,
    )
