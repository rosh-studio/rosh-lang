"""Thin adapter between the terminal REPL and the runtime."""

from __future__ import annotations

import difflib
import re
from pathlib import Path
from typing import Any

from rosh_lang.model import GetStatement, LookStatement, Programme, WhenStatement
from rosh_lang.parser import ParseError, parse_file, parse_string
from rosh_lang.repl.contracts import ErrorInfo, EventSnapshot, ObjectItem, StateItem
from rosh_lang.runtime import Runtime

_COMMAND_CANDIDATES = (
    "state",
    "list",
    "list objects",
    "list events",
    "help",
    "quit",
    "exit",
    "print",
    "create",
    "set",
    "get",
    "say",
    "when",
    "end",
    "on",
    "event",
    "send",
    "go",
    "look",
    "examine",
    "inspect",
    "x",
    "connect",
    "destroy",
    "delete",
    "remove",
    "sprite",
    "sound",
    "play",
    "define",
    "do",
    "repeat",
    "ls",
    "objects",
    "?",
)


class RuntimeAdapter:
    """Provide a narrow, structured view over the current runtime."""

    def __init__(self, runtime: Runtime | None = None) -> None:
        self.runtime = runtime or Runtime()

    def run_source(
        self,
        text: str,
        *,
        source: str = "<repl>",
    ) -> tuple[Programme, str, list[StateItem]]:
        programme = parse_string(text, source=source)
        stmt = programme.statements[0] if programme.statements else None
        result: Any = None

        if len(programme.statements) == 1 and stmt is not None and not isinstance(stmt, WhenStatement):
            result = self.runtime.execute(stmt)
        else:
            self.runtime.run(programme)

        if isinstance(stmt, GetStatement):
            return programme, "get", self._state_items_from_result(result)
        if isinstance(stmt, LookStatement):
            view = "get" if stmt.target else "state"
            return programme, view, self._state_items_from_result(result)
        return programme, "none", []

    def run_file(self, path: Path | str) -> Programme:
        programme = parse_file(path)
        self.runtime.run(programme)
        return programme

    def get_state(self, *, include_internal: bool = False) -> list[StateItem]:
        items: list[StateItem] = []
        for key, value in self.runtime.state.items():
            internal = key.startswith("_")
            if internal and not include_internal:
                continue
            items.append(
                StateItem(
                    key=key,
                    value=value,
                    type=type(value).__name__,
                    internal=internal,
                )
            )
        return items

    def get_value(self, target: str) -> list[StateItem]:
        results = self.runtime.execute_get(target)
        return [
            StateItem(key=item["key"], value=item["value"], type=item["type"])
            for item in results
        ]

    def list_objects(self) -> list[ObjectItem]:
        objects: list[ObjectItem] = []
        for key, value in self.runtime.state.items():
            if key.startswith("_") or not isinstance(value, dict):
                continue
            fields = sorted(str(field) for field in value.keys())
            objects.append(
                ObjectItem(
                    name=key,
                    kind="object",
                    path=key,
                    fields=fields,
                    value=value,
                )
            )
        return objects

    def list_events(self) -> EventSnapshot:
        return EventSnapshot(
            declared_events={
                name: list(fields)
                for name, fields in self.runtime.event_registry.items()
            },
            handler_counts={
                event: len(bodies)
                for event, bodies in self.runtime.handlers.items()
            },
            listener_counts={
                event: len(listeners)
                for event, listeners in self.runtime.listeners.items()
            },
        )

    def complete(self, prefix: str) -> list[str]:
        candidates = set(_COMMAND_CANDIDATES)
        candidates.update(self.runtime.state.keys())
        lowered = prefix.lower()
        return sorted(name for name in candidates if name.lower().startswith(lowered))

    def format_error(self, exc: Exception) -> ErrorInfo:
        if isinstance(exc, ParseError):
            suggestions = self._keyword_suggestions(exc)
            return ErrorInfo(
                kind="parse",
                message=str(exc),
                line=exc.line,
                source=exc.source,
                suggestions=suggestions,
            )
        return ErrorInfo(
            kind="runtime",
            message=str(exc),
            suggestions=self._runtime_suggestions(exc),
        )

    def _state_items_from_result(self, result: Any) -> list[StateItem]:
        if not isinstance(result, list):
            return []
        items: list[StateItem] = []
        for item in result:
            if not isinstance(item, dict):
                continue
            items.append(
                StateItem(
                    key=str(item.get("key", "")),
                    value=item.get("value"),
                    type=str(item.get("type", type(item.get("value")).__name__)),
                    internal=str(item.get("key", "")).startswith("_"),
                )
            )
        return items

    def _keyword_suggestions(self, exc: ParseError) -> list[str]:
        match = re.search(r"Unknown keyword: '([^']+)'", str(exc))
        if not match:
            return []
        keyword = match.group(1)
        return difflib.get_close_matches(keyword, _COMMAND_CANDIDATES, n=3, cutoff=0.6)

    def _runtime_suggestions(self, exc: Exception) -> list[str]:
        match = re.search(r"Unknown(?: key)?: '([^']+)'", str(exc))
        if not match:
            return []
        target = match.group(1)
        candidates = [key for key in self.runtime.state.keys() if not key.startswith("_")]
        return difflib.get_close_matches(target, candidates, n=3, cutoff=0.6)
