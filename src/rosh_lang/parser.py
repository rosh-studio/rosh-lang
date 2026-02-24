"""Line-oriented parser for Rosh programmes.

Reads .rosh files and produces a Programme (list of Statements).
Backward compatible with Rosh v0.1/v0.2 syntax.

Grammar is keyword-driven. Each line starts with a keyword:
  print, create, set, when, end, #, (blank)

More keywords will be added incrementally as the compose system
needs them. The parser is deliberately simple — no AST, no
expression trees, no nested structures. Just lines → statements.
"""

from __future__ import annotations

from pathlib import Path

from rosh_lang.model import (
    BlankStatement,
    CommentStatement,
    CreateStatement,
    EndStatement,
    PrintStatement,
    Programme,
    SetStatement,
    Statement,
    WhenStatement,
)


class ParseError(Exception):
    """Raised when a programme line cannot be parsed."""

    def __init__(self, message: str, line: int = 0, source: str = "") -> None:
        loc = f"{source}:{line}" if source else f"line {line}"
        super().__init__(f"{loc}: {message}")
        self.line = line
        self.source = source


def parse_file(path: Path | str) -> Programme:
    """Parse a .rosh file into a Programme."""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    return parse_string(text, source=str(path))


def parse_string(text: str, source: str = "<string>") -> Programme:
    """Parse a string of Rosh code into a Programme."""
    statements: list[Statement] = []
    for i, raw_line in enumerate(text.splitlines(), start=1):
        stmt = _parse_line(raw_line, line=i, source=source)
        statements.append(stmt)
    return Programme(statements=statements, source=source)


def _parse_line(raw: str, line: int, source: str) -> Statement:
    """Parse a single line of Rosh code."""
    stripped = raw.strip()

    # Blank line
    if not stripped:
        return BlankStatement(line=line)

    # Comment
    if stripped.startswith("#"):
        return CommentStatement(text=stripped[1:].strip(), line=line)

    # Keyword dispatch — case insensitive
    keyword = stripped.split()[0].lower()

    if keyword == "print":
        return _parse_print(stripped, line, source)
    if keyword == "create":
        return _parse_create(stripped, line, source)
    if keyword == "set":
        return _parse_set(stripped, line, source)
    if keyword == "when":
        return _parse_when(stripped, line, source)
    if keyword == "end":
        return EndStatement(line=line)

    raise ParseError(f"Unknown keyword: {keyword!r}", line=line, source=source)


# ── Keyword parsers ────────────────────────────────────────────


def _parse_print(line_text: str, line: int, source: str) -> PrintStatement:
    """Parse: print "hello world" or print "Score: {score}" """
    rest = line_text[len("print"):].strip()

    # Extract quoted string
    if rest.startswith('"') and rest.endswith('"'):
        text = rest[1:-1]
    elif rest.startswith("'") and rest.endswith("'"):
        text = rest[1:-1]
    else:
        # Unquoted — treat the rest of the line as text
        # This supports: print hello world (speech-friendly)
        text = rest

    if not text:
        raise ParseError("print requires text", line=line, source=source)

    return PrintStatement(text=text, line=line)


def _parse_create(line_text: str, line: int, source: str) -> CreateStatement:
    """Parse: create object player / create number score as 0 / create 5 objects as bullets"""
    tokens = line_text.split()
    # tokens[0] is "create"

    if len(tokens) < 3:
        raise ParseError(
            "create requires at least: create <kind> <name>",
            line=line, source=source,
        )

    idx = 1  # start after "create"

    # Check for count: "create 5 objects as bullets"
    count = 1
    if tokens[idx].isdigit():
        count = int(tokens[idx])
        idx += 1

    kind = tokens[idx].lower()
    idx += 1

    # Normalize "objects" → "object"
    if kind == "objects":
        kind = "object"

    # For "create 5 objects as bullets" — name comes after "as"
    if idx < len(tokens) and tokens[idx].lower() == "as":
        idx += 1
        if idx >= len(tokens):
            raise ParseError("Expected name after 'as'", line=line, source=source)
        name = tokens[idx]
        idx += 1
    else:
        if idx >= len(tokens):
            raise ParseError(
                "create requires a name",
                line=line, source=source,
            )
        name = tokens[idx]
        idx += 1

    # Check for "from parent"
    parent = ""
    if idx < len(tokens) and tokens[idx].lower() == "from":
        idx += 1
        if idx >= len(tokens):
            raise ParseError("Expected parent name after 'from'", line=line, source=source)
        parent = tokens[idx]

    return CreateStatement(kind=kind, name=name, parent=parent, count=count, line=line)


def _parse_set(line_text: str, line: int, source: str) -> SetStatement:
    """Parse: set player health to 100 / set x to 50 / set player.health to 75

    v0.2 also allows: set x 100 (without 'to')
    """
    rest = line_text[len("set"):].strip()
    if not rest:
        raise ParseError("set requires target and value", line=line, source=source)

    # Split on " to " to find target and value
    if " to " in rest:
        parts = rest.split(" to ", 1)
        target_str = parts[0].strip()
        value_str = parts[1].strip()
    else:
        # v0.2 shorthand: "set x 100" — last token is value, rest is target
        tokens = rest.split()
        if len(tokens) < 2:
            raise ParseError("set requires target and value", line=line, source=source)
        value_str = tokens[-1]
        target_str = " ".join(tokens[:-1])

    # Normalize target: "player health" → "player.health"
    # But preserve existing dot notation
    if "." not in target_str and " " in target_str:
        target = ".".join(target_str.split())
    else:
        target = target_str

    return SetStatement(target=target, value=value_str, line=line)


def _parse_when(line_text: str, line: int, source: str) -> WhenStatement:
    """Parse: when update then / when collision hero enemy then / when space_pressed then"""
    rest = line_text[len("when"):].strip()

    # Remove trailing "then" if present
    if rest.lower().endswith(" then"):
        rest = rest[:-5].strip()
    elif rest.lower() == "then":
        rest = ""

    if not rest:
        raise ParseError("when requires an event name", line=line, source=source)

    tokens = rest.split()
    event = tokens[0]
    args = tokens[1:]

    return WhenStatement(event=event, args=args, line=line)
