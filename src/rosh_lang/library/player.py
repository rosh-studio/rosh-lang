# licence: MIT
"""player — Python widget factory for a keyboard-controlled player ship.

Creates a ship object with arrow-key (or WASD) movement handlers and
boundary clamping. Replaces the common 8-line boilerplate pattern.
"""

from __future__ import annotations

from rosh_lang.core.model import (
    CreateStatement,
    EndStatement,
    IfStatement,
    OnStatement,
    SetStatement,
    Statement,
    WhenStatement,
)

METADATA = {
    "widget": "player",
    "version": "0.2",
    "description": "Keyboard-controlled ship with movement and clamping",
    "config": {
        "speed": "0.02",
        "keys": "arrows",
        "move": "xy",
        "x": "0.5",
        "y": "0.9",
        "width": "0.12",
        "height": "0.05",
        "color": "#00ff88",
        "clamp_x_min": "0.02",
        "clamp_x_max": "0.88",
        "clamp_y_min": "0.02",
        "clamp_y_max": "0.92",
    },
    "provides": [],
    "requires": [],
    "exposes": ["ship"],
    "licence": "MIT",
}


def generate(config: dict[str, str]) -> list[Statement]:
    """Return a list of unprefixed statements. Loader will prefix them."""
    speed = config.get("speed", "0.02")
    keys = config.get("keys", "arrows")
    move = config.get("move", "xy")
    x = config.get("x", "0.5")
    y = config.get("y", "0.9")
    width = config.get("width", "0.12")
    height = config.get("height", "0.05")
    color = config.get("color", "#00ff88")
    cx_min = config.get("clamp_x_min", "0.02")
    cx_max = config.get("clamp_x_max", "0.88")
    cy_min = config.get("clamp_y_min", "0.02")
    cy_max = config.get("clamp_y_max", "0.92")

    stmts: list[Statement] = []

    # Ship object — uses _self so `use player` gives player.x not player.ship.x
    stmts.append(CreateStatement(kind="object", name="_self"))
    stmts.append(SetStatement(target="_self.x", value=x))
    stmts.append(SetStatement(target="_self.y", value=y))
    stmts.append(SetStatement(target="_self.width", value=width))
    stmts.append(SetStatement(target="_self.height", value=height))
    stmts.append(SetStatement(target="_self.color", value=color))
    stmts.append(SetStatement(target="_self.label", value='""'))

    # Speed value
    stmts.append(CreateStatement(kind="number", name="speed"))
    stmts.append(SetStatement(target="speed", value=speed))

    # Movement handlers — when update + if _keys checks
    if move != "none":
        key_map = _get_key_map(keys, speed, move)
        if key_map:
            stmts.append(WhenStatement(event="update", args=[]))
            for key_name, target_prop, delta in key_map:
                stmts.append(IfStatement(
                    condition=f"_keys.{key_name} == 1",
                    then_body=[SetStatement(target=f"_self.{target_prop}", value=f"_self.{target_prop} {delta}")],
                    else_body=[],
                ))
            stmts.append(EndStatement())

    # Boundary clamping
    if move in ("xy", "x"):
        stmts.append(OnStatement(
            event="update", action="set",
            args=f"_self.x to clamp _self.x {cx_min} {cx_max}",
        ))
    if move in ("xy", "y"):
        stmts.append(OnStatement(
            event="update", action="set",
            args=f"_self.y to clamp _self.y {cy_min} {cy_max}",
        ))

    return stmts


def _get_key_map(keys: str, speed: str, move: str) -> list[tuple[str, str, str]]:
    """Return (key_name, target_property, delta_expr) tuples for each direction.

    move: "xy" (both axes), "x" (horizontal only), "y" (vertical only).
    """
    result: list[tuple[str, str, str]] = []

    if keys in ("arrows", "both"):
        if move in ("xy", "x"):
            result.extend([
                ("ArrowLeft", "x", f"- {speed}"),
                ("ArrowRight", "x", f"+ {speed}"),
            ])
        if move in ("xy", "y"):
            result.extend([
                ("ArrowUp", "y", f"- {speed}"),
                ("ArrowDown", "y", f"+ {speed}"),
            ])

    if keys in ("wasd", "both"):
        if move in ("xy", "x"):
            result.extend([
                ("a", "x", f"- {speed}"),
                ("d", "x", f"+ {speed}"),
            ])
        if move in ("xy", "y"):
            result.extend([
                ("w", "y", f"- {speed}"),
                ("s", "y", f"+ {speed}"),
            ])

    return result
