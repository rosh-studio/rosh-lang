"""Data model for parsed Rosh programmes.

A programme is a list of statements. Each statement is a dataclass
representing one line of Rosh code. The parser produces these;
the compose step consumes them.

Backward compatible with Rosh v0.1/v0.2 syntax:
  print "hello world"
  create object player
  set player health to 100
  when collision hero enemy then ... end
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ── Statements ─────────────────────────────────────────────────
#
# Each statement type corresponds to a Rosh keyword.
# We start small: print, create, set, when/end.
# More will be added as needed.


@dataclass
class PrintStatement:
    """print "hello world" or print "Score: {score}" """

    text: str  # the string content (without outer quotes)
    line: int = 0


@dataclass
class CreateStatement:
    """create object player / create number score as 0"""

    kind: str  # "object", "number", "string", "list"
    name: str
    parent: str = ""  # for "create object hero from player"
    count: int = 1  # for "create 5 objects as bullets"
    line: int = 0


@dataclass
class SetStatement:
    """set player health to 100 / set x to 50"""

    target: str  # "player.health" or "x" (dot-separated)
    value: str  # raw value string — parsed later
    line: int = 0


@dataclass
class EndStatement:
    """end — closes a block (create object, when, define function, if, etc.)"""

    line: int = 0


@dataclass
class WhenStatement:
    """when update then / when collision hero enemy then"""

    event: str  # "update", "collision", "space_pressed", etc.
    args: list[str] = field(default_factory=list)  # e.g. ["hero", "enemy"] for collision
    line: int = 0


@dataclass
class CommentStatement:
    """# this is a comment"""

    text: str
    line: int = 0


@dataclass
class BlankStatement:
    """Empty line — preserved for round-tripping."""

    line: int = 0


# Union of all statement types
Statement = (
    PrintStatement
    | CreateStatement
    | SetStatement
    | EndStatement
    | WhenStatement
    | CommentStatement
    | BlankStatement
)


@dataclass
class Programme:
    """A parsed Rosh programme — a list of statements."""

    statements: list[Statement] = field(default_factory=list)
    source: str = ""  # filename or "<string>"
