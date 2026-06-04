"""Shell-independent command routing for the terminal REPL."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

from rosh_lang.intent.planner import IntentPlanner
from rosh_lang.repl.contracts import ErrorInfo, KernelResponse
from rosh_lang.repl.natural import lower_shell_input
from rosh_lang.repl.runtime_adapter import RuntimeAdapter

@dataclass(frozen=True, slots=True)
class HelpTopic:
    command: str
    summary: str
    usage: str
    examples: tuple[str, ...] = field(default_factory=tuple)
    aliases: tuple[str, ...] = field(default_factory=tuple)
    accepts_no_args: bool = False


_HELP_TOPICS: Final[dict[str, HelpTopic]] = {
    "help": HelpTopic(
        command="help",
        summary="Show available commands or detailed help",
        usage="help [command]",
        examples=("help", "help set", "help look"),
        aliases=("?",),
        accepts_no_args=True,
    ),
    "state": HelpTopic(
        command="state",
        summary="Show current top-level state",
        usage="state",
        examples=("state",),
        accepts_no_args=True,
    ),
    "list": HelpTopic(
        command="list",
        summary="Show state, objects, or events",
        usage="list | list objects | list events",
        examples=("list", "list objects", "list events"),
        aliases=("ls", "objects"),
        accepts_no_args=True,
    ),
    "print": HelpTopic(
        command="print",
        summary="Output text ({var} interpolation)",
        usage='print "text"',
        examples=('print "hello"', 'print "score: {score}"'),
        accepts_no_args=True,
    ),
    "create": HelpTopic(
        command="create",
        summary="Create object, number, string, list, or scene",
        usage="create <kind> <name>",
        examples=("create object player", "create scene intro"),
    ),
    "set": HelpTopic(
        command="set",
        summary="Set a value (arithmetic: score + 1)",
        usage="set <target> to <value>",
        examples=("set player.color to red", "set score to score + 1"),
    ),
    "get": HelpTopic(
        command="get",
        summary="Query state or object fields",
        usage="get <target>",
        examples=("get player", "get player.color"),
    ),
    "say": HelpTopic(
        command="say",
        summary="Broadcast text to all sessions",
        usage='say "text"',
        examples=('say "welcome"',),
    ),
    "when": HelpTopic(
        command="when",
        summary="Start event handler block",
        usage="when <event> [then]",
        examples=("when click", "when timer then"),
    ),
    "end": HelpTopic(
        command="end",
        summary="End handler or block",
        usage="end",
        examples=("end",),
        accepts_no_args=True,
    ),
    "on": HelpTopic(
        command="on",
        summary="One-line reactive listener",
        usage="on <event> <action>",
        examples=("on click say \"clicked\"", "on update set player.x to player.x + 1"),
    ),
    "event": HelpTopic(
        command="event",
        summary="Declare a named event",
        usage="event <name> [fields]",
        examples=("event opened", "event damage amount target"),
    ),
    "send": HelpTopic(
        command="send",
        summary="Emit an event",
        usage="send <event> [payload]",
        examples=("send opened", "send damage amount=10 target=player"),
    ),
    "go": HelpTopic(
        command="go",
        summary="Navigate to scene",
        usage="go <scene>",
        examples=("go intro", "go back"),
    ),
    "look": HelpTopic(
        command="look",
        summary="Inspect scene or object",
        usage="look [target]",
        examples=("look", "look player", "look player.color"),
        aliases=("examine", "inspect", "x"),
        accepts_no_args=True,
    ),
    "connect": HelpTopic(
        command="connect",
        summary="Register a connection",
        usage="connect <name> <url>",
        examples=("connect world https://rosh.cloud/ws/world/demo",),
    ),
    "destroy": HelpTopic(
        command="destroy",
        summary="Remove object from state",
        usage="destroy <name>",
        examples=("destroy player",),
        aliases=("delete", "remove"),
    ),
    "sprite": HelpTopic(
        command="sprite",
        summary="Attach sprite to object",
        usage='sprite <name> "desc"',
        examples=('sprite enemy "red alien"',),
    ),
    "sound": HelpTopic(
        command="sound",
        summary="Register sound asset",
        usage='sound <name> "desc"',
        examples=('sound click "soft click"',),
    ),
    "play": HelpTopic(
        command="play",
        summary="Play a sound",
        usage="play <sound> [loop|stop]",
        examples=("play click", "play music loop"),
    ),
    "define": HelpTopic(
        command="define",
        summary="Define a reusable function block",
        usage="define <name>",
        examples=("define greet",),
    ),
    "do": HelpTopic(
        command="do",
        summary="Execute a function",
        usage="do <name>",
        examples=("do greet",),
    ),
    "repeat": HelpTopic(
        command="repeat",
        summary="Repeat a block multiple times",
        usage="repeat <count> [as var]",
        examples=("repeat 3", "repeat 3 as i"),
    ),
    "quit": HelpTopic(
        command="quit",
        summary="Exit the REPL",
        usage="quit",
        examples=("quit",),
        aliases=("exit",),
        accepts_no_args=True,
    ),
}

_HELP_ROWS: Final[list[tuple[str, str]]] = [
    (topic.usage, topic.summary)
    for topic in _HELP_TOPICS.values()
]

_EXACT_ALIASES: Final[dict[str, str]] = {
    "?": "help",
    "ls": "list objects",
    "objects": "list objects",
}

_PREFIX_ALIASES: Final[tuple[tuple[str, str], ...]] = (
    ("examine ", "look "),
    ("inspect ", "look "),
    ("x ", "look "),
    ("delete ", "destroy "),
    ("remove ", "destroy "),
)


class ReplKernel:
    """Route terminal REPL input to builtins or the runtime adapter."""

    def __init__(self, adapter: RuntimeAdapter) -> None:
        self.adapter = adapter
        self.current_subject: str | None = None

    def process_line(self, line: str) -> KernelResponse:
        stripped = line.strip()

        if not stripped or stripped.startswith("#"):
            return KernelResponse(status="noop")

        lowered = lower_shell_input(stripped, current_subject=self.current_subject)
        stripped = lowered.text

        stripped = _apply_aliases(stripped)
        lower = stripped.lower()

        if lower in ("quit", "exit"):
            return KernelResponse(status="exit")

        if lower in ("state", "list"):
            return KernelResponse(
                status="ok",
                view="state",
                state_items=self.adapter.get_state(),
            )

        if lower == "list objects":
            return KernelResponse(
                status="ok",
                view="objects",
                object_items=self.adapter.list_objects(),
            )

        if lower == "list events":
            return KernelResponse(
                status="ok",
                view="events",
                event_snapshot=self.adapter.list_events(),
            )

        if lower == "help":
            return KernelResponse(status="ok", view="help")

        if lower.startswith("help "):
            requested_topic = stripped.split(None, 1)[1].strip().lower()
            canonical = canonical_help_topic(requested_topic)
            return KernelResponse(
                status="ok",
                view="help",
                help_topic=canonical,
            )

        # REPL-only convenience: bare identifier behaves like get <identifier>.
        tokens = stripped.split()
        if len(tokens) == 1:
            usage_error = usage_error_for_command(tokens[0])
            if usage_error is not None:
                return KernelResponse(status="error", error=usage_error)

        if len(tokens) == 1 and tokens[0] in self.adapter.runtime.state:
            try:
                self.current_subject = tokens[0]
                return KernelResponse(
                    status="ok",
                    view="get",
                    state_items=self.adapter.get_value(tokens[0]),
                )
            except Exception as exc:  # pragma: no cover - defensive
                return KernelResponse(
                    status="error",
                    error=self.adapter.format_error(exc),
                )

        try:
            _programme, view, items = self.adapter.run_source(stripped)
        except Exception as exc:
            error = self.adapter.format_error(exc)
            planned = self._try_intent_fallback(line, stripped, error)
            if planned is not None:
                return planned
            return KernelResponse(status="error", error=error)

        self._remember_subject(stripped, lowered.subject)

        if items:
            return KernelResponse(status="ok", view=view, state_items=items)
        return KernelResponse(status="ok")

    def _try_intent_fallback(
        self,
        original: str,
        stripped: str,
        error: ErrorInfo,
    ) -> KernelResponse | None:
        if not _should_try_intent(stripped, error):
            return None

        planner = IntentPlanner.from_state(self.adapter.runtime.state)
        if not planner.available:
            return None

        plan = planner.plan(
            original.strip(),
            state=self.adapter.runtime.state,
            target="terminal",
        )
        if plan is None:
            return None

        try:
            _programme, view, items = self.adapter.run_source(plan.rosh, source="<intent>")
        except Exception:
            return None

        self._remember_subject(plan.rosh, None)
        return KernelResponse(
            status="ok",
            view=view,
            state_items=items,
            planned_rosh=plan.rosh,
            planner_notes=plan.notes,
        )

    def _remember_subject(self, stripped: str, lowered_subject: str | None) -> None:
        if lowered_subject is not None:
            self.current_subject = lowered_subject
            return
        inferred = _infer_subject(stripped)
        if inferred is not None:
            self.current_subject = inferred


def help_rows_for_topic(topic: str | None) -> list[tuple[str, str]]:
    """Filter help rows for a specific topic."""
    if not topic:
        return _HELP_ROWS
    canonical = canonical_help_topic(topic)
    if canonical is None or canonical not in _HELP_TOPICS:
        return []
    entry = _HELP_TOPICS[canonical]
    return [(entry.usage, entry.summary)]


def help_topic(topic: str | None) -> HelpTopic | None:
    """Return the canonical help topic for a specific command."""
    if topic is None:
        return None
    canonical = canonical_help_topic(topic)
    if canonical is None:
        return None
    return _HELP_TOPICS.get(canonical)


def canonical_help_topic(topic: str | None) -> str | None:
    """Map aliases like 'inspect' to their canonical help topic."""
    if topic is None:
        return None
    lowered = topic.strip().lower()
    if not lowered:
        return None
    if lowered in _HELP_TOPICS:
        return lowered
    for canonical, entry in _HELP_TOPICS.items():
        if lowered in entry.aliases:
            return canonical
    return lowered


def usage_error_for_command(command: str) -> ErrorInfo | None:
    """Return a shell-level usage error for single-word incomplete commands."""
    canonical = canonical_help_topic(command)
    if canonical is None:
        return None
    entry = _HELP_TOPICS.get(canonical)
    if entry is None or entry.accepts_no_args:
        return None
    return ErrorInfo(
        kind="shell",
        message=f"{entry.command} needs more information.",
        guidance=[entry.usage, *entry.examples],
    )


def block_delta(stripped: str) -> int:
    """Return block nesting delta for a single line."""
    lower = stripped.lower()
    if lower == "end":
        return -1
    if lower.startswith("else if "):
        return 0
    if lower.startswith(("when ", "define ", "repeat ", "if ")):
        return 1
    return 0


def starts_multiline_block(stripped: str) -> bool:
    """Whether a line should begin multiline collection in the terminal shell."""
    lower = stripped.lower()
    return lower.startswith(("when ", "define ", "repeat "))


def _apply_aliases(stripped: str) -> str:
    lower = stripped.lower()
    if lower in _EXACT_ALIASES:
        return _EXACT_ALIASES[lower]

    for prefix, replacement in _PREFIX_ALIASES:
        if lower.startswith(prefix):
            suffix = stripped[len(prefix):].strip()
            return replacement + suffix
    return stripped


def _infer_subject(stripped: str) -> str | None:
    tokens = stripped.split()
    if len(tokens) >= 3 and tokens[0].lower() == "create" and tokens[1].lower() in {"object", "number", "string", "list", "scene"}:
        return tokens[2]
    if len(tokens) >= 2 and tokens[0].lower() in {"look", "get", "sprite", "sound", "destroy"}:
        return tokens[1].split(".", 1)[0]
    if len(tokens) >= 2 and tokens[0].lower() == "set":
        return tokens[1].split(".", 1)[0]
    return None


def _should_try_intent(stripped: str, error: ErrorInfo) -> bool:
    if "\n" in stripped:
        return False
    if error.kind != "parse":
        return False
    if error.guidance:
        return False
    if error.suggestions:
        return False
    lower = stripped.lower()
    if lower.startswith(("help", "list", "state", "quit", "exit")):
        return False
    return "unknown keyword" in error.message.lower()
