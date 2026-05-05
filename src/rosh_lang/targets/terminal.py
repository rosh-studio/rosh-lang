"""Terminal target — run a Rosh programme with stdout output."""

from __future__ import annotations

from rosh_lang.core.model import Programme
from rosh_lang.core.runtime import Runtime


def run_terminal(programme: Programme) -> Runtime:
    """Execute a programme, printing to stdout."""
    rt = Runtime()
    rt.run(programme)
    return rt
