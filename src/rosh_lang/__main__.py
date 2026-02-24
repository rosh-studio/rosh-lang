"""Rosh CLI — run programmes or start the REPL.

Usage:
    rosh                     # start REPL
    rosh <file.rosh>         # run a programme
    rosh --version           # show version
    rosh --help              # show this help
"""

from __future__ import annotations

import sys

from rosh_lang import __version__
from rosh_lang.parser import parse_file, parse_string
from rosh_lang.runtime import Runtime

HELP = f"""\
rosh {__version__} — one script, many worlds

Usage:
  rosh                     Start the interactive REPL
  rosh <file.rosh>         Run a programme file
  rosh --version           Show version
  rosh --help              Show this help
"""


def repl() -> None:
    """Interactive Rosh REPL."""
    print(f"rosh {__version__} — type 'quit' to exit")
    rt = Runtime()
    when_buffer: list[str] = []
    collecting = False

    while True:
        try:
            prompt = "...   " if collecting else "rosh> "
            line = input(prompt)
        except (EOFError, KeyboardInterrupt):
            print()
            break

        stripped = line.strip().lower()
        if stripped in ("quit", "exit"):
            break

        if stripped == "state":
            _show_state(rt)
            continue

        # Handle multi-line when/end blocks
        if collecting:
            when_buffer.append(line)
            if stripped == "end":
                collecting = False
                text = "\n".join(when_buffer)
                when_buffer.clear()
                try:
                    programme = parse_string(text)
                    rt.run(programme)
                except Exception as e:
                    print(f"  Error: {e}")
            continue

        if stripped.startswith("when "):
            collecting = True
            when_buffer = [line]
            continue

        if not stripped or stripped.startswith("#"):
            continue

        try:
            programme = parse_string(line)
            rt.run(programme)
        except Exception as e:
            print(f"  Error: {e}")


def _show_state(rt: Runtime) -> None:
    """Print current runtime state."""
    if not rt.state:
        print("  (empty)")
        return
    for key, value in rt.state.items():
        if key.startswith("_"):
            continue
        print(f"  {key} = {value!r}")


def main() -> None:
    if len(sys.argv) < 2:
        repl()
        return

    arg = sys.argv[1]

    if arg in ("--version", "-V"):
        print(f"rosh {__version__}")
        return

    if arg in ("--help", "-h"):
        print(HELP)
        return

    programme = parse_file(arg)
    rt = Runtime()
    rt.run(programme)


if __name__ == "__main__":
    main()
