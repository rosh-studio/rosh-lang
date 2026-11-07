"""Who may do what in a room, as data (P-052 §8).

A person has a level in a room, 0–9: **0 look, 3 build, 5 edit, 9 own**.
Each action needs a level, and a room's preset says which. The numbers live in
`defaults.json` beside this file, so changing who may do something is a change
to data, not to the server's code.

This file decides *who* passes a check. *Whether* a check applies (is this
thing someone else's? did the room's code make it? is it locked?) is a fact
about the room, and each server works that out itself.

Pure: no I/O beyond reading `defaults.json` once, no framework types.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Optional

__all__ = ["LEVELS", "ACTIONS", "PRESETS", "level_named", "threshold", "allowed", "preset_named", "level_in",
           "room_rule_problem"]

_DEFAULTS = json.loads((Path(__file__).with_name("defaults.json")).read_text(encoding="utf-8"))

LEVELS: dict[str, int] = dict(_DEFAULTS["levels"])
ACTIONS: tuple[str, ...] = tuple(_DEFAULTS["actions"])
PRESETS: dict[str, dict[str, int]] = {name: dict(rows) for name, rows in _DEFAULTS["presets"].items()}
_FLOORS: dict[str, int] = dict(_DEFAULTS["floors"])

for _name, _rows in PRESETS.items():
    if set(_rows) != set(ACTIONS):
        raise ValueError(f"preset {_name!r} must give a level for every action, exactly once")
    # Every number is a level, so level 9 passes every row; servers rely on that.
    if any(not isinstance(v, int) or not 0 <= v <= 9 for v in _rows.values()):
        raise ValueError(f"preset {_name!r} must give each action a level from 0 to 9")


def level_named(name: str) -> int:
    """`look` → 0, `build` → 3, `edit` → 5, `own` → 9."""
    return LEVELS[name]


def threshold(action: str, room: Optional[Mapping[str, Any]] = None) -> int:
    """The level `action` needs in `room`.

    `room` says which preset it uses (`{"rules": "museum"}`; `shared` when it
    says nothing) and may change single rows (`{"rule": {"create_visible": 5}}`,
    from `set room.rule.create_visible to 5` in its code). An unknown action or
    preset is an error, not a default: a typo here must not quietly open or
    close a room. No row goes below its floor, however it is set.
    """
    if action not in ACTIONS:
        raise KeyError(f"unknown action {action!r}")
    room = room or {}
    preset = str(room.get("rules") or "shared")
    if preset not in PRESETS:
        raise KeyError(f"unknown preset {preset!r}")
    level = (room.get("rule") or {}).get(action, PRESETS[preset][action])
    return max(int(level), _FLOORS.get(action, 0))


def allowed(action: str, level: int, room: Optional[Mapping[str, Any]] = None) -> bool:
    """Whether someone at `level` may do `action` in `room`."""
    return level >= threshold(action, room)


def _said(value: Any) -> str:
    return str(value).strip().strip("\"'").strip()


# One reading of a rule's value, used by every server for checking it, comparing
# it and obeying it: a value two of those read differently is a way round them.
def preset_named(value: Any) -> Optional[str]:
    """The preset `set room.rules to <value>` names, or None."""
    name = _said(value).lower()
    return name if name in PRESETS else None


def level_in(value: Any) -> Optional[int]:
    """The level `set room.rule.<action> to <value>` gives (`5`, `05`), or None."""
    said = _said(value)
    if not (said.isascii() and said.isdigit()):
        return None
    digits = said.lstrip("0") or "0"
    return int(digits) if len(digits) == 1 else None    # never int() of a long number


def room_rule_problem(key: str, value: Any) -> Optional[str]:
    """What is wrong with a room's `set room.<key> to <value>`, if it is one of
    the room's rules (`rules`, `rule.<action>`), or None. Said so that the
    person who wrote it can fix it."""
    if key == "rules":
        if preset_named(value) is None:
            return f'There are no rules called "{_said(value)}". Try: {", ".join(PRESETS)}.'
        return None
    if not key.startswith("rule."):
        return None
    action = key[len("rule."):]
    if action not in ACTIONS:
        return f'There is no action called "{action}". Try one of: {", ".join(ACTIONS)}.'
    level = level_in(value)
    if level is None:
        return f"room.{key} must be a level from 0 to 9 (0 look, 3 build, 5 edit, 9 own)."
    floor = _FLOORS.get(action, 0)
    if level < floor:
        return f"room.{key} can't be below {floor}."
    return None
