"""Shell-independent command routing for the terminal REPL."""

from __future__ import annotations

from typing import Final

from rosh_lang.repl.contracts import KernelResponse
from rosh_lang.repl.natural import lower_shell_input
from rosh_lang.repl.runtime_adapter import RuntimeAdapter

HELP_ROWS = [
    ('print "text"', "Output text ({var} interpolation)"),
    ("create <kind> <name>", "Create object/number/string/list"),
    ("set <target> to <value>", "Set a value (arithmetic: score + 1)"),
    ("get <target>", "Query state"),
    ("say <text>", "Broadcast text to all sessions"),
    ("when <event> [then]", "Start event handler block"),
    ("end", "End handler block"),
    ("on <event> <action>", "One-line reactive listener"),
    ("event <name> [fields]", "Declare a named event"),
    ("send <event> [payload]", "Emit an event"),
    ("go <scene>", "Navigate to scene"),
    ("look [target]", "Inspect scene or object"),
    ("connect <name> <url>", "Register connection"),
    ("destroy <name>", "Remove object from state"),
    ('sprite <name> "desc"', "Attach sprite to object"),
    ('sound <name> "desc"', "Register sound asset"),
    ("play <sound> [loop|stop]", "Play a sound"),
    ("define <name>", "Define a reusable function block"),
    ("do <name>", "Execute a function"),
    ("repeat <count> [as var]", "Repeat a block multiple times"),
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
            return KernelResponse(
                status="ok",
                view="help",
                help_topic=stripped.split(None, 1)[1].strip().lower(),
            )

        # REPL-only convenience: bare identifier behaves like get <identifier>.
        tokens = stripped.split()
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
            return KernelResponse(status="error", error=error)

        self._remember_subject(stripped, lowered.subject)

        if items:
            return KernelResponse(status="ok", view=view, state_items=items)
        return KernelResponse(status="ok")

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
        return HELP_ROWS
    return [
        row for row in HELP_ROWS
        if row[0].split()[0].lower() == topic
    ]


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
