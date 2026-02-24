"""Run a Rosh programme from the command line.

Usage:
    uv run python -m rosh_lang <file.rosh>
"""

import sys

from rosh_lang.parser import parse_file
from rosh_lang.runtime import Runtime


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m rosh_lang <file.rosh>", file=sys.stderr)
        sys.exit(1)

    path = sys.argv[1]
    programme = parse_file(path)
    rt = Runtime()
    rt.run(programme)


main()
