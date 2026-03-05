"""Rosh CLI — run programmes or start the REPL.

Usage:
    rosh                                # start REPL
    rosh <file.rosh>                    # run a programme (terminal)
    rosh <file.rosh> --target web --run # open in browser
    rosh --version                      # show version
    rosh --help                         # show this help
"""

from __future__ import annotations

import argparse
import sys

from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

from rosh_lang import __version__
from rosh_lang.model import GetStatement
from rosh_lang.parser import ParseError, parse_file, parse_string
from rosh_lang.runtime import Runtime

# ── Theme ──────────────────────────────────────────────────────

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

console = Console(theme=_THEME)

COPYRIGHT = "(c) Rosh Studio 2026 — rosh.cloud"

HELP = f"""\
[rosh.brand]rosh {__version__}[/] — one script, many worlds
{COPYRIGHT}

[rosh.heading]Usage[/]
  rosh                     Start the interactive REPL
  rosh <file.rosh>         Run a programme file
  rosh new [template] [name]  Scaffold a starter programme
  rosh library list        List available widgets
  rosh library info <name> Show widget details
  rosh create "desc"       AI-generate a .rosh programme
  rosh publish file.rosh   Upload to rosh.cloud
  rosh config --key KEY    Save your rosh.cloud API key
  rosh --version           Show version
  rosh --help              Show this help

[rosh.heading]Targets[/]
  --target terminal        Output to terminal (default)
  --target web             Render as HTML in browser
  --target phaser          Render as Phaser game in browser
  --target threejs         Render as Three.js 3D scene in browser
  --run                    Auto-open browser (web/phaser/threejs target)

[rosh.heading]REPL commands[/]
  state                    Show non-internal state
  list                     Show state (alias)
  list objects             Show all objects
  list events              Show declared events and handlers
  help                     Show available keywords
  quit / exit              Exit the REPL
"""


def _keywords_table() -> Table:
    """Build a Rich table of available keywords."""
    table = Table(
        show_header=False,
        box=None,
        padding=(0, 2),
        title="Available Keywords",
        title_style="rosh.heading",
    )
    table.add_column("Keyword", style="rosh.keyword", min_width=26)
    table.add_column("Description")
    rows = [
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
    ]
    for kw, desc in rows:
        table.add_row(kw, desc)
    return table


# ── REPL ───────────────────────────────────────────────────────


def repl() -> None:
    """Interactive Rosh REPL."""
    console.print(f"[rosh.brand]rosh {__version__}[/] — one script, many worlds")
    console.print(f"[rosh.muted]{COPYRIGHT}[/]")
    console.print("[rosh.muted]Type 'help' for commands, 'quit' to exit[/]")
    console.print()

    rt = Runtime()
    when_buffer: list[str] = []
    collecting = False

    while True:
        try:
            if collecting:
                prompt = Text("...   ", style="rosh.continuation")
            else:
                prompt = Text("rosh> ", style="rosh.prompt")
            line = console.input(prompt)
        except (EOFError, KeyboardInterrupt):
            console.print()
            break

        stripped = line.strip()
        lower = stripped.lower()

        if lower in ("quit", "exit"):
            break

        if lower == "state" or lower == "list":
            _show_state(rt)
            continue

        if lower == "list objects":
            _show_objects(rt)
            continue

        if lower == "list events":
            _show_events(rt)
            continue

        if lower == "help":
            console.print()
            console.print(_keywords_table())
            console.print()
            continue

        # Multi-line when/end blocks
        if collecting:
            when_buffer.append(line)
            if lower == "end":
                collecting = False
                text = "\n".join(when_buffer)
                when_buffer.clear()
                try:
                    programme = parse_string(text)
                    rt.run(programme)
                except ParseError as e:
                    console.print(f"[rosh.error]ParseError:[/] {e}")
                except Exception as e:
                    console.print(f"[rosh.error]Error:[/] {e}")
            continue

        if lower.startswith("when "):
            collecting = True
            when_buffer = [line]
            continue

        if not stripped or stripped.startswith("#"):
            continue

        try:
            programme = parse_string(line)
            rt.run(programme)

            # Special output for get
            stmt = programme.statements[0] if programme.statements else None
            if isinstance(stmt, GetStatement):
                result = rt.execute_get(stmt.target)
                for item in result:
                    console.print(
                        f"  [rosh.key]{item['key']}[/] = "
                        f"[rosh.value]{item['value']!r}[/] "
                        f"[rosh.type]({item['type']})[/]"
                    )
        except ParseError as e:
            console.print(f"[rosh.error]ParseError:[/] {e}")
        except Exception as e:
            console.print(f"[rosh.error]Error:[/] {e}")


# ── State display ──────────────────────────────────────────────


def _show_state(rt: Runtime) -> None:
    """Print current runtime state."""
    visible = {k: v for k, v in rt.state.items() if not k.startswith("_")}
    if not visible:
        console.print("  [rosh.muted](empty)[/]")
        return
    table = Table(show_header=True, box=None, padding=(0, 2))
    table.add_column("Name", style="rosh.key")
    table.add_column("Value", style="rosh.value")
    table.add_column("Type", style="rosh.type")
    for key, value in visible.items():
        table.add_row(key, repr(value), type(value).__name__)
    console.print(table)


def _show_objects(rt: Runtime) -> None:
    """Show all objects (dicts) in state."""
    objs = {k: v for k, v in rt.state.items()
            if not k.startswith("_") and isinstance(v, dict)}
    if not objs:
        console.print("  [rosh.muted](no objects)[/]")
        return
    for key, value in objs.items():
        console.print(f"  [rosh.key]{key}[/] = [rosh.value]{value!r}[/]")


def _show_events(rt: Runtime) -> None:
    """Show declared events and registered handlers."""
    has_content = False

    if rt.event_registry:
        has_content = True
        console.print("[rosh.heading]Declared events[/]")
        for name, fields in rt.event_registry.items():
            fields_str = f" [rosh.type]({', '.join(fields)})[/]" if fields else ""
            console.print(f"  [rosh.key]{name}[/]{fields_str}")

    if rt.handlers:
        has_content = True
        console.print("[rosh.heading]When handlers[/]")
        for event, bodies in rt.handlers.items():
            console.print(f"  [rosh.key]{event}[/]: {len(bodies)} handler(s)")

    if rt.listeners:
        has_content = True
        console.print("[rosh.heading]On listeners[/]")
        for event, listeners in rt.listeners.items():
            console.print(f"  [rosh.key]{event}[/]: {len(listeners)} listener(s)")

    if not has_content:
        console.print("  [rosh.muted](no events)[/]")


# ── CLI entry ──────────────────────────────────────────────────


def _build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser for the rosh CLI."""
    parser = argparse.ArgumentParser(
        prog="rosh",
        description="rosh — one script, many worlds",
        add_help=True,
    )
    parser.add_argument(
        "file",
        nargs="?",
        default=None,
        help="Rosh programme file to run",
    )
    parser.add_argument(
        "--version", "-V",
        action="version",
        version=f"rosh {__version__}",
    )
    parser.add_argument(
        "--target", "-t",
        choices=["terminal", "web", "phaser", "threejs"],
        default="terminal",
        help="Output target (default: terminal)",
    )
    parser.add_argument(
        "--run", "-r",
        action="store_true",
        help="Auto-open browser (web target only)",
    )
    return parser


def main() -> None:
    # No args at all → REPL (skip argparse to avoid help/version intercept)
    if len(sys.argv) < 2:
        repl()
        return

    # "rosh library ..." — handle before argparse
    if sys.argv[1] == "library":
        from rosh_lang.library_cli import library_main
        library_main(sys.argv[2:])
        return

    # "rosh new ..." — handle before argparse
    if sys.argv[1] == "new":
        from rosh_lang.scaffolder import scaffold
        scaffold(sys.argv[2:])
        return

    # "rosh create ..." — AI generation
    if sys.argv[1] == "create":
        from rosh_lang.cloud import cmd_create
        cmd_create(sys.argv[2:])
        return

    # "rosh publish ..." — upload to rosh.cloud
    if sys.argv[1] == "publish":
        from rosh_lang.cloud import cmd_publish
        cmd_publish(sys.argv[2:])
        return

    # "rosh config ..." — API key management
    if sys.argv[1] == "config":
        from rosh_lang.cloud import cmd_config
        cmd_config(sys.argv[2:])
        return

    parser = _build_parser()
    args = parser.parse_args()

    if args.file is None:
        repl()
        return

    from pathlib import Path

    path = Path(args.file)
    if not path.exists():
        console.print(f"[rosh.error]Error:[/] file not found: {args.file}")
        sys.exit(1)

    try:
        programme = parse_file(path)
    except ParseError as e:
        console.print(f"[rosh.error]ParseError:[/] {e}")
        sys.exit(1)

    if args.target == "web":
        from rosh_lang.targets.web import serve_web
        serve_web(programme, auto_open=args.run)
    elif args.target == "phaser":
        from rosh_lang.targets.phaser import serve_phaser
        serve_phaser(programme, auto_open=args.run)
    elif args.target == "threejs":
        from rosh_lang.targets.threejs import serve_threejs
        serve_threejs(programme, auto_open=args.run)
    else:
        from rosh_lang.targets.terminal import run_terminal
        run_terminal(programme)


if __name__ == "__main__":
    main()
