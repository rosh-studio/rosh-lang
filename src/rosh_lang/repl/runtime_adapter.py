"""Thin adapter between the terminal REPL and the runtime."""

from __future__ import annotations

import difflib
import re
from pathlib import Path
from typing import Any

from rosh_lang.core.model import GetStatement, LookStatement, Programme, SayStatement, WhenStatement
from rosh_lang.core.parser import ParseError, parse_file, parse_string
from rosh_lang.repl.contracts import ErrorInfo, EventSnapshot, ObjectItem, StateItem
from rosh_lang.core.runtime import Runtime

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
        if isinstance(stmt, SayStatement):
            said = self.runtime.state.get("_last_said", "")
            return programme, "say", [StateItem(key="_said", value=said, type="string")]
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
                guidance=self._parse_guidance(exc),
            )
        return ErrorInfo(
            kind="runtime",
            message=str(exc),
            suggestions=self._runtime_suggestions(exc),
            guidance=self._runtime_guidance(exc),
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
            match = re.search(r"Unknown: '([^']+)'", str(exc))
        if not match:
            return []
        target = match.group(1)
        candidates = [key for key in self.runtime.state.keys() if not key.startswith("_")]
        if "." in target:
            root, _, leaf = target.partition(".")
            obj = self.runtime.state.get(root)
            if isinstance(obj, dict):
                prop_candidates = [f"{root}.{key}" for key in obj.keys()]
                prop_matches = difflib.get_close_matches(target, prop_candidates, n=3, cutoff=0.6)
                if prop_matches:
                    return prop_matches
                leaf_matches = difflib.get_close_matches(leaf, list(obj.keys()), n=3, cutoff=0.6)
                if leaf_matches:
                    return [f"{root}.{match}" for match in leaf_matches]
        return difflib.get_close_matches(target, candidates, n=3, cutoff=0.6)

    def _parse_guidance(self, exc: ParseError) -> list[str]:
        message = str(exc)
        guidance_map = {
            "create requires": [
                "create <kind> <name>",
                "create object player",
                "create scene intro",
            ],
            "set requires": [
                "set <target> to <value>",
                "set player.color to red",
                "set score to score + 1",
            ],
            "get requires": [
                "get <target>",
                "get player",
                "get player.color",
            ],
            "say requires": [
                'say "text"',
                'say "welcome"',
            ],
            "send requires": [
                "send <event> [payload]",
                "send opened",
                "send damage amount=10 target=player",
            ],
            "event requires": [
                "event <name> [fields]",
                "event damage amount target",
            ],
            "on requires": [
                "on <event> <action>",
                'on click say "clicked"',
            ],
            "go requires": [
                "go <scene>",
                "go intro",
            ],
            "destroy requires": [
                "destroy <name>",
                "destroy player",
            ],
            "sprite requires": [
                'sprite <name> "desc"',
                'sprite enemy "red alien"',
            ],
            "sound requires": [
                'sound <name> "desc"',
                'sound click "soft click"',
            ],
            "play requires": [
                "play <sound> [loop|stop]",
                "play click",
            ],
            "define requires": [
                "define <name>",
                "define greet",
            ],
            "do requires": [
                "do <name>",
                "do greet",
            ],
            "repeat requires": [
                "repeat <count> [as var]",
                "repeat 3",
                "repeat 3 as i",
            ],
            "when requires": [
                "when <event> [then]",
                "when click",
            ],
        }
        for prefix, guidance in guidance_map.items():
            if prefix in message:
                return guidance
        return []

    def _runtime_guidance(self, exc: Exception) -> list[str]:
        message = str(exc)
        if "Unknown key:" in message or "Unknown:" in message:
            return [
                "list objects",
                "look <object>",
                "get <object>",
            ]
        return []
