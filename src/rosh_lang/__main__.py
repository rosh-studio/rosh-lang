"""Rosh CLI — run programmes or start the REPL."""

from __future__ import annotations

import argparse
import sys

from rich.console import Console
from rich.theme import Theme

from rosh_lang import __version__
from rosh_lang.core.parser import ParseError, parse_file
from rosh_lang.repl import start_repl
from rosh_lang.repl.runtime_adapter import RuntimeAdapter

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
        "-c", "--command",
        help="Execute inline Rosh code",
    )
    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Run file or command, then enter the REPL with state preserved",
    )
    parser.add_argument(
        "--version", "-V",
        action="version",
        version=f"rosh {__version__}",
    )
    parser.add_argument(
        "--target", "-t",
        choices=["terminal", "web", "phaser", "threejs", "scratch"],
        default="terminal",
        help="Output target (default: terminal)",
    )
    parser.add_argument(
        "--run", "-r",
        action="store_true",
        help="Auto-open browser (web target only)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv

    # No args at all → REPL (skip argparse to avoid help/version intercept)
    if not argv:
        start_repl()
        return 0

    # "rosh library ..." — handle before argparse
    if argv[0] == "library":
        from rosh_lang.cli.library_cli import library_main
        library_main(argv[1:])
        return 0

    # "rosh new ..." — handle before argparse
    if argv[0] == "new":
        from rosh_lang.cli.scaffolder import scaffold
        scaffold(argv[1:])
        return 0

    # "rosh register" — open registration page
    if argv[0] == "register":
        from rosh_lang.cli.cloud import cmd_register
        cmd_register(argv[1:])
        return 0

    # "rosh login" — authenticate with rosh.cloud
    if argv[0] == "login":
        from rosh_lang.cli.cloud import cmd_login
        cmd_login(argv[1:])
        return 0

    # "rosh logout" — clear local session
    if argv[0] == "logout":
        from rosh_lang.cli.cloud import cmd_logout
        cmd_logout(argv[1:])
        return 0

    # "rosh create ..." — AI generation
    if argv[0] == "create":
        from rosh_lang.cli.cloud import cmd_create
        cmd_create(argv[1:])
        return 0

    # "rosh publish ..." — upload to rosh.cloud
    if argv[0] == "publish":
        from rosh_lang.cli.cloud import cmd_publish
        cmd_publish(argv[1:])
        return 0

    # "rosh config ..." — API key management
    if argv[0] == "config":
        from rosh_lang.cli.cloud import cmd_config
        cmd_config(argv[1:])
        return 0

    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.file and args.command:
        console.print("[rosh.error]Error:[/] cannot use both a file and --command")
        return 2

    if args.interactive and args.target != "terminal":
        console.print("[rosh.error]Error:[/] --interactive only works with --target terminal")
        return 2

    if args.command:
        adapter = RuntimeAdapter()
        try:
            adapter.run_source(args.command, source="<command>")
        except Exception as exc:
            error = adapter.format_error(exc)
            console.print(f"[rosh.error]{error.kind.title()}Error:[/] {error.message}")
            return 1
        if args.interactive:
            start_repl(runtime=adapter.runtime)
        return 0

    if args.file is None:
        start_repl()
        return 0

    from pathlib import Path

    path = Path(args.file)
    if not path.exists():
        console.print(f"[rosh.error]Error:[/] file not found: {args.file}")
        return 1

    if args.interactive:
        adapter = RuntimeAdapter()
        try:
            adapter.run_file(path)
        except ParseError as e:
            console.print(f"[rosh.error]ParseError:[/] {e}")
            return 1
        start_repl(runtime=adapter.runtime)
        return 0

    try:
        programme = parse_file(path)
    except ParseError as e:
        console.print(f"[rosh.error]ParseError:[/] {e}")
        return 1

    if args.target == "web":
        from rosh_lang.targets.web import serve_web
        serve_web(programme, auto_open=args.run)
    elif args.target == "phaser":
        from rosh_lang.targets.phaser import serve_phaser
        serve_phaser(programme, auto_open=args.run)
    elif args.target == "threejs":
        from rosh_lang.targets.threejs import serve_threejs
        serve_threejs(programme, auto_open=args.run)
    elif args.target == "scratch":
        from rosh_lang.targets.scratch import render_scratch_sb3
        out_path = path.with_suffix(".sb3")
        out_path.write_bytes(render_scratch_sb3(programme))
        console.print(f"[rosh.brand]Wrote Scratch project:[/] {out_path}")
    else:
        from rosh_lang.targets.terminal import run_terminal
        run_terminal(programme)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
