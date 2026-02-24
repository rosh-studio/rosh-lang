"""Minimal runtime — executes a Rosh Programme statement by statement.

Walks the statement list, dispatches by type:
  print   → writes to output stream (with {var} interpolation)
  create  → stores named values/objects in state
  set     → updates values in state (dot notation for nested)
  when/end → registers event handlers (executed on send())
  comment/blank → skipped
"""

from __future__ import annotations

import re
import sys
from typing import Any, TextIO

from rosh_lang.model import (
    BlankStatement,
    CommentStatement,
    CreateStatement,
    EndStatement,
    PrintStatement,
    Programme,
    SetStatement,
    Statement,
    WhenStatement,
)

_INTERP_RE = re.compile(r"\{([^}]+)\}")


class Runtime:
    """Execute a Rosh programme."""

    def __init__(self, output: TextIO = sys.stdout) -> None:
        self.state: dict[str, Any] = {}
        self.handlers: dict[str, list[list[Statement]]] = {}
        self.output = output

    # ── public API ────────────────────────────────────────────

    def run(self, programme: Programme) -> None:
        """Execute a programme statement by statement."""
        stmts = programme.statements
        i = 0
        while i < len(stmts):
            stmt = stmts[i]

            # when/end blocks: collect the body, register handler
            if isinstance(stmt, WhenStatement):
                body: list[Statement] = []
                i += 1
                while i < len(stmts) and not isinstance(stmts[i], EndStatement):
                    body.append(stmts[i])
                    i += 1
                # skip the end statement
                i += 1
                self.handlers.setdefault(stmt.event, []).append(body)
                continue

            self.execute(stmt)
            i += 1

    def execute(self, stmt: Statement) -> None:
        """Execute a single statement."""
        if isinstance(stmt, PrintStatement):
            self._exec_print(stmt)
        elif isinstance(stmt, CreateStatement):
            self._exec_create(stmt)
        elif isinstance(stmt, SetStatement):
            self._exec_set(stmt)
        elif isinstance(stmt, (CommentStatement, BlankStatement, EndStatement)):
            pass  # skip

    def send(self, event: str, **payload: Any) -> None:
        """Fire an event — runs all registered handlers for it."""
        for body in self.handlers.get(event, []):
            for stmt in body:
                self.execute(stmt)

    # ── private dispatch ──────────────────────────────────────

    def _exec_print(self, stmt: PrintStatement) -> None:
        text = self._interpolate(stmt.text)
        self.output.write(text + "\n")

    def _exec_create(self, stmt: CreateStatement) -> None:
        kind = stmt.kind.lower()
        if stmt.parent and stmt.parent in self.state:
            # copy parent — shallow copy of dict, or plain value
            parent_val = self.state[stmt.parent]
            if isinstance(parent_val, dict):
                self.state[stmt.name] = dict(parent_val)
            else:
                self.state[stmt.name] = parent_val
        elif kind == "object":
            self.state[stmt.name] = {}
        elif kind == "number":
            self.state[stmt.name] = 0
        elif kind == "string":
            self.state[stmt.name] = ""
        elif kind == "list":
            self.state[stmt.name] = []
        else:
            # unknown kind — default to empty dict
            self.state[stmt.name] = {}

    def _exec_set(self, stmt: SetStatement) -> None:
        value = self._coerce(stmt.value)
        parts = stmt.target.split(".")
        if len(parts) == 1:
            self.state[parts[0]] = value
        else:
            # traverse nested dicts, creating intermediates as needed
            obj = self.state
            for part in parts[:-1]:
                if part not in obj or not isinstance(obj[part], dict):
                    obj[part] = {}
                obj = obj[part]
            obj[parts[-1]] = value

    # ── helpers ────────────────────────────────────────────────

    def _interpolate(self, text: str) -> str:
        """Replace {name} and {obj.prop} with values from state."""

        def _replace(match: re.Match[str]) -> str:
            key = match.group(1)
            val = self._resolve(key)
            if val is None:
                return match.group(0)  # leave {key} as-is
            return str(val)

        return _INTERP_RE.sub(_replace, text)

    def _resolve(self, key: str) -> Any | None:
        """Look up a dotted key in state. Returns None if missing."""
        parts = key.split(".")
        obj: Any = self.state
        for part in parts:
            if isinstance(obj, dict) and part in obj:
                obj = obj[part]
            else:
                return None
        return obj

    @staticmethod
    def _coerce(value: str) -> Any:
        """Coerce a raw value string to a Python type."""
        # quoted string → keep as string
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            return value[1:-1]
        # integer
        try:
            return int(value)
        except ValueError:
            pass
        # float
        try:
            return float(value)
        except ValueError:
            pass
        # fallback — raw string
        return value


def run(programme: Programme, output: TextIO = sys.stdout) -> Runtime:
    """Convenience: execute a programme and return the runtime."""
    rt = Runtime(output=output)
    rt.run(programme)
    return rt
