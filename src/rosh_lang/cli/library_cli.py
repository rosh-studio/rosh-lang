"""rosh library — list and inspect bundled/local/global widgets.

Usage:
    rosh library list              # show all available widgets
    rosh library info <name>       # show widget metadata
"""

from __future__ import annotations

import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.theme import Theme

from rosh_lang.core.widgets import (
    DEFAULT_SEARCH_PATHS,
    _list_available,
    parse_metadata,
)

_THEME = Theme({
    "rosh.keyword": "bold cyan",
    "rosh.value": "green",
    "rosh.type": "dim",
    "rosh.error": "bold red",
    "rosh.warn": "yellow",
    "rosh.brand": "bold magenta",
    "rosh.muted": "dim",
    "rosh.key": "cyan",
    "rosh.heading": "bold underline",
})

console = Console(theme=_THEME)


def _source_label(widget_path: Path) -> str:
    """Return a human-readable source label for a widget path."""
    path_str = str(widget_path)
    if "/library/" in path_str and "rosh_lang" in path_str:
        return "bundled"
    home = str(Path.home())
    if path_str.startswith(home) and "/.rosh/" in path_str:
        return "global"
    return "local"


def library_list() -> None:
    """Show all available widgets with source labels."""
    available = _list_available(DEFAULT_SEARCH_PATHS)
    if not available:
        console.print("[rosh.muted]No widgets found.[/]")
        return

    table = Table(
        title="Available Widgets",
        title_style="rosh.heading",
        show_header=True,
        box=None,
        padding=(0, 2),
    )
    table.add_column("Widget", style="rosh.keyword")
    table.add_column("Version", style="rosh.type")
    table.add_column("Source", style="rosh.muted")
    table.add_column("Description", style="rosh.value")

    for name, path in sorted(available.items()):
        meta = parse_metadata(path)
        table.add_row(
            name,
            meta.get("version", ""),
            _source_label(path),
            meta.get("description", ""),
        )

    console.print(table)


def library_info(name: str) -> None:
    """Show detailed metadata for a specific widget."""
    available = _list_available(DEFAULT_SEARCH_PATHS)
    if name not in available:
        console.print(f"[rosh.error]Widget '{name}' not found.[/]")
        sys.exit(1)

    path = available[name]
    meta = parse_metadata(path)

    console.print(f"[rosh.heading]Widget: {name}[/]")
    console.print(f"  [rosh.key]Source:[/]      {_source_label(path)}")
    console.print(f"  [rosh.key]Path:[/]        {path}")
    console.print(f"  [rosh.key]Version:[/]     {meta.get('version', '—')}")
    console.print(f"  [rosh.key]Description:[/] {meta.get('description', '—')}")

    config = meta.get("config", {})
    if config:
        pairs = "  ".join(f"{k}={v}" for k, v in config.items())
        console.print(f"  [rosh.key]Config:[/]      {pairs}")
    else:
        console.print(f"  [rosh.key]Config:[/]      [rosh.muted](none)[/]")


def library_main(args: list[str]) -> None:
    """Route 'rosh library' subcommands."""
    if not args or args[0] == "list":
        library_list()
    elif args[0] == "info":
        if len(args) < 2:
            console.print("[rosh.error]Usage: rosh library info <name>[/]")
            sys.exit(1)
        library_info(args[1])
    else:
        console.print(f"[rosh.error]Unknown library command: {args[0]}[/]")
        console.print("[rosh.muted]Usage: rosh library list | rosh library info <name>[/]")
        sys.exit(1)
