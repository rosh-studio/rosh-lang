"""Structured contracts for the terminal REPL."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(slots=True)
class StateItem:
    key: str
    value: Any
    type: str
    internal: bool = False


@dataclass(slots=True)
class ObjectItem:
    name: str
    kind: str
    path: str
    fields: list[str] = field(default_factory=list)
    value: Any = None


@dataclass(slots=True)
class EventSnapshot:
    declared_events: dict[str, list[str]] = field(default_factory=dict)
    handler_counts: dict[str, int] = field(default_factory=dict)
    listener_counts: dict[str, int] = field(default_factory=dict)


@dataclass(slots=True)
class ErrorInfo:
    kind: Literal["parse", "runtime", "shell"]
    message: str
    line: int | None = None
    source: str | None = None
    suggestions: list[str] = field(default_factory=list)
    guidance: list[str] = field(default_factory=list)


@dataclass(slots=True)
class KernelResponse:
    status: Literal["ok", "noop", "exit", "error"] = "ok"
    view: Literal["none", "state", "objects", "events", "help", "get"] = "none"
    state_items: list[StateItem] = field(default_factory=list)
    object_items: list[ObjectItem] = field(default_factory=list)
    event_snapshot: EventSnapshot | None = None
    help_topic: str | None = None
    error: ErrorInfo | None = None
