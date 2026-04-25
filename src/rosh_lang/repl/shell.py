"""Rich-powered terminal REPL shell."""

from __future__ import annotations

import atexit
from pathlib import Path

try:
    import readline
except ImportError:  # pragma: no cover - platform dependent
    readline = None

from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

from rosh_lang import __version__
from rosh_lang.repl.contracts import KernelResponse
from rosh_lang.repl.kernel import (
    ReplKernel,
    block_delta,
    help_rows_for_topic,
    help_topic,
    starts_multiline_block,
)
from rosh_lang.repl.runtime_adapter import RuntimeAdapter
from rosh_lang.runtime import Runtime

_THEME = Theme({
    "rosh.keyword": "bold cyan",
    "rosh.value": "green",
    "rosh.type": "dim",
    "rosh.error": "bold red",
    "rosh.warn": "yellow",
    "rosh.prompt": "bold white",
    "rosh.continuation": "dim white",
    "rosh.brand": "bold magenta",
    "rosh.muted": "dim",
    "rosh.key": "cyan",
    "rosh.heading": "bold underline",
})

COPYRIGHT = "(c) Rosh Studio 2026 — rosh.cloud"
_HISTORY_FILE = Path.home() / ".rosh_history"
_HISTORY_LOADED = False
_HISTORY_SAVE_REGISTERED = False


def _readline_bind_instruction(doc: str | None) -> str:
    """Return the correct completion binding for GNU readline vs libedit."""
    if doc and "libedit" in doc.lower():
        return "bind ^I rl_complete"
    return "tab: complete"


def _completion_matches(
    adapter: RuntimeAdapter,
    text: str,
    line_buffer: str,
    begidx: int,
) -> list[str]:
    """Return completion candidates for the current readline buffer."""
    prefix = line_buffer[:begidx]
    stripped_prefix = prefix.strip()

    if not stripped_prefix:
        return adapter.complete(line_buffer)

    if stripped_prefix == "help":
        keywords = sorted({row[0].split()[0] for row in help_rows_for_topic(None)})
        return [kw for kw in keywords if kw.startswith(text.lower())]

    if stripped_prefix == "list":
        return [item for item in ("objects", "events") if item.startswith(text.lower())]

    return adapter.complete(text)


def _setup_readline(adapter: RuntimeAdapter) -> None:
    global _HISTORY_LOADED, _HISTORY_SAVE_REGISTERED
    if readline is None:
        return

    def completer(text: str, state: int) -> str | None:
        line_buffer = readline.get_line_buffer()
        begidx = readline.get_begidx()
        matches = _completion_matches(adapter, text, line_buffer, begidx)
        if state < len(matches):
            return matches[state]
        return None

    if not _HISTORY_LOADED:
        try:
            readline.read_history_file(_HISTORY_FILE)
        except FileNotFoundError:
            pass
        except OSError:
            pass
        readline.set_history_length(1000)
        _HISTORY_LOADED = True

    if not _HISTORY_SAVE_REGISTERED:
        def _save_history() -> None:
            try:
                readline.write_history_file(_HISTORY_FILE)
            except OSError:
                pass

        atexit.register(_save_history)
        _HISTORY_SAVE_REGISTERED = True

    readline.set_completer(completer)
    readline.parse_and_bind(_readline_bind_instruction(getattr(readline, "__doc__", None)))


def _keywords_table(topic: str | None = None) -> Table:
    table = Table(
        show_header=False,
        box=None,
        padding=(0, 2),
        title="Available Keywords" if topic is None else f"Help: {topic}",
        title_style="rosh.heading",
    )
    table.add_column("Keyword", style="rosh.keyword", min_width=26)
    table.add_column("Description")
    rows = help_rows_for_topic(topic)
    for kw, desc in rows:
        table.add_row(kw, desc)
    return table


def _render_help_topic(console: Console, topic: str | None) -> None:
    entry = help_topic(topic)
    console.print(_keywords_table(topic))
    if entry is None:
        return
    if entry.aliases:
        console.print(f"[rosh.muted]Aliases:[/] {', '.join(entry.aliases)}")
    if entry.examples:
        console.print("[rosh.heading]Examples[/]")
        for example in entry.examples:
            console.print(f"  [rosh.keyword]{example}[/]")


def _render_response(console: Console, response: KernelResponse) -> None:
    if response.status == "error" and response.error is not None:
        console.print(f"[rosh.error]{response.error.kind.title()}Error:[/] {response.error.message}")
        if response.error.suggestions:
            console.print(
                "  [rosh.warn]Did you mean:[/] "
                + ", ".join(response.error.suggestions)
            )
        if response.error.guidance:
            console.print("  [rosh.muted]Try:[/]")
            for line in response.error.guidance:
                console.print(f"    [rosh.keyword]{line}[/]")
        return

    if response.view == "help":
        console.print()
        _render_help_topic(console, response.help_topic)
        console.print()
        return

    if response.view == "state":
        if not response.state_items:
            console.print("  [rosh.muted](empty)[/]")
            return
        table = Table(show_header=True, box=None, padding=(0, 2))
        table.add_column("Name", style="rosh.key")
        table.add_column("Value", style="rosh.value")
        table.add_column("Type", style="rosh.type")
        for item in response.state_items:
            table.add_row(item.key, repr(item.value), item.type)
        console.print(table)
        return

    if response.view == "objects":
        if not response.object_items:
            console.print("  [rosh.muted](no objects)[/]")
            return
        for item in response.object_items:
            console.print(f"  [rosh.key]{item.name}[/] = [rosh.value]{item.value!r}[/]")
        return

    if response.view == "events":
        snapshot = response.event_snapshot
        if snapshot is None:
            console.print("  [rosh.muted](no events)[/]")
            return

        has_content = False
        if snapshot.declared_events:
            has_content = True
            console.print("[rosh.heading]Declared events[/]")
            for name, fields in snapshot.declared_events.items():
                fields_str = f" [rosh.type]({', '.join(fields)})[/]" if fields else ""
                console.print(f"  [rosh.key]{name}[/]{fields_str}")

        if snapshot.handler_counts:
            has_content = True
            console.print("[rosh.heading]When handlers[/]")
            for event, count in snapshot.handler_counts.items():
                console.print(f"  [rosh.key]{event}[/]: {count} handler(s)")

        if snapshot.listener_counts:
            has_content = True
            console.print("[rosh.heading]On listeners[/]")
            for event, count in snapshot.listener_counts.items():
                console.print(f"  [rosh.key]{event}[/]: {count} listener(s)")

        if not has_content:
            console.print("  [rosh.muted](no events)[/]")
        return

    if response.view == "get":
        for item in response.state_items:
            console.print(
                f"  [rosh.key]{item.key}[/] = "
                f"[rosh.value]{item.value!r}[/] "
                f"[rosh.type]({item.type})[/]"
            )


def start_repl(runtime: Runtime | None = None) -> None:
    """Run the Rich-powered terminal REPL."""
    console = Console(theme=_THEME)
    adapter = RuntimeAdapter(runtime=runtime)
    kernel = ReplKernel(adapter)
    _setup_readline(adapter)

    console.print(f"[rosh.brand]rosh {__version__}[/] — one script, many worlds")
    console.print(f"[rosh.muted]{COPYRIGHT}[/]")
    console.print("[rosh.muted]Type 'help' for commands, 'quit' to exit[/]")
    console.print()

    buffer: list[str] = []
    depth = 0

    while True:
        try:
            if readline is not None:
                prompt = (
                    "\x1b[2;37m...   \x1b[0m"
                    if buffer else
                    "\x1b[1;37mrosh> \x1b[0m"
                )
                line = input(prompt)
            else:
                prompt = Text("...   " if buffer else "rosh> ",
                              style="rosh.continuation" if buffer else "rosh.prompt")
                line = console.input(prompt)
        except (EOFError, KeyboardInterrupt):
            console.print()
            break

        stripped = line.strip()

        if buffer:
            buffer.append(line)
            depth += block_delta(stripped)
            if depth <= 0:
                response = kernel.process_line("\n".join(buffer))
                buffer.clear()
                depth = 0
                if response.status == "exit":
                    break
                _render_response(console, response)
            continue

        if starts_multiline_block(stripped):
            buffer = [line]
            depth = 1
            continue

        response = kernel.process_line(line)
        if response.status == "exit":
            break
        _render_response(console, response)
