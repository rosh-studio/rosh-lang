"""Data model for parsed Rosh programmes.

A programme is a list of statements. Each statement is a dataclass
representing one line of Rosh code. The parser produces these;
the runtime consumes them.

24 keywords + comments + blanks, per BUILDING-ROSH.md Sections 4 & 7.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ── Statements ─────────────────────────────────────────────────


@dataclass
class PrintStatement:
    """print "hello world" or print "Score: {score}" """

    text: str
    line: int = 0


@dataclass
class CreateStatement:
    """create object player / create number score"""

    kind: str
    name: str
    parent: str = ""
    count: int = 1
    line: int = 0


@dataclass
class SetStatement:
    """set player health to 100 / set score to score + 1"""

    target: str
    value: str  # raw — may be literal or arithmetic expression
    line: int = 0


@dataclass
class WhenStatement:
    """when start then / when collision hero enemy then"""

    event: str
    args: list[str] = field(default_factory=list)
    line: int = 0


@dataclass
class EndStatement:
    """end — closes a when block."""

    line: int = 0


@dataclass
class GetStatement:
    """get score / get all / get all bool"""

    target: str
    line: int = 0


@dataclass
class SayStatement:
    """say Welcome to the dungeon"""

    text: str
    line: int = 0


@dataclass
class SendStatement:
    """send timer_expired / send score_changed old=50 new=100"""

    event: str
    payload: dict[str, str] = field(default_factory=dict)
    line: int = 0


@dataclass
class EventStatement:
    """event timer_expired / event score_changed old new"""

    name: str
    payload_fields: list[str] = field(default_factory=list)
    line: int = 0


@dataclass
class OnStatement:
    """on alarm set status to "triggered" """

    event: str
    action: str
    args: str
    condition: str = ""
    line: int = 0


@dataclass
class GoStatement:
    """go corridor / go back"""

    target: str
    line: int = 0


@dataclass
class LookStatement:
    """look / look player"""

    target: str = ""
    line: int = 0


@dataclass
class ConnectStatement:
    """connect api https://example.com / connect api disconnect"""

    name: str
    url: str = ""
    line: int = 0


@dataclass
class DestroyStatement:
    """destroy bullet_7"""

    name: str
    line: int = 0


@dataclass
class SpriteStatement:
    """sprite player "pixel art spaceship" """

    name: str
    description: str
    line: int = 0


@dataclass
class SoundStatement:
    """sound laser "short sci-fi laser blast" """

    name: str
    description: str
    line: int = 0


@dataclass
class PlayStatement:
    """play explosion / play music loop / play music stop"""

    sound: str
    mode: str = ""
    line: int = 0


@dataclass
class IfStatement:
    """if score > 10 ... else ... end"""

    condition: str  # "field op value"
    then_body: list[Statement] = field(default_factory=list)
    else_body: list[Statement] = field(default_factory=list)
    line: int = 0


@dataclass
class ElseStatement:
    """else — used during parsing to separate if/else branches."""

    line: int = 0


@dataclass
class AnimateStatement:
    """animate player sheet "player-sheet.png" frames 4 speed 8 mode loop"""

    name: str  # object name
    sheet: str  # path to spritesheet
    frames: int  # number of frames
    speed: int = 8  # fps
    mode: str = "loop"  # loop | once | bounce
    line: int = 0


@dataclass
class AfterStatement:
    """after 2 send wave_2 — schedule a delayed event."""

    delay: float
    event: str
    line: int = 0


@dataclass
class UseStatement:
    """use score / use player speed 0.02 / use enemy-grid rows 2 cols 5"""

    name: str
    config: dict[str, str] = field(default_factory=dict)
    line: int = 0


@dataclass
class BackgroundStatement:
    """background "#1a1a2e" / background "sky.png" """

    value: str  # colour string or image path/URL
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


@dataclass
class DefineStatement:
    """define fire_bullet ... end — user-defined function."""

    name: str
    body: list[Statement] = field(default_factory=list)
    line: int = 0


@dataclass
class DoStatement:
    """do fire_bullet — call a user-defined function."""

    name: str
    line: int = 0


@dataclass
class RepeatStatement:
    """repeat 5 / repeat 3 as i — counted loop."""

    count: str  # literal int or state variable name
    var: str = ""  # optional loop variable ("" = none)
    body: list[Statement] = field(default_factory=list)
    line: int = 0


# Union of all statement types
Statement = (
    PrintStatement
    | CreateStatement
    | SetStatement
    | WhenStatement
    | EndStatement
    | GetStatement
    | SayStatement
    | SendStatement
    | EventStatement
    | OnStatement
    | GoStatement
    | LookStatement
    | ConnectStatement
    | DestroyStatement
    | SpriteStatement
    | SoundStatement
    | PlayStatement
    | IfStatement
    | ElseStatement
    | AnimateStatement
    | AfterStatement
    | UseStatement
    | BackgroundStatement
    | CommentStatement
    | BlankStatement
    | DefineStatement
    | DoStatement
    | RepeatStatement
)


@dataclass
class Programme:
    """A parsed Rosh programme — a list of statements."""

    statements: list[Statement] = field(default_factory=list)
    source: str = ""
