# licence: Rosh-BSL
"""ball — Python widget factory for a bouncing ball with wall collisions.

Creates a ball object with velocity and on-statements for wall bouncing.
Supports wall modes: "all" (default), "top-sides" (no bottom), "sides" (horizontal only).
"""

from __future__ import annotations

from rosh_lang.core.model import (
    CreateStatement,
    OnStatement,
    SetStatement,
    SoundStatement,
    Statement,
)

METADATA = {
    "widget": "ball",
    "version": "0.1",
    "description": "Bouncing ball with configurable wall bounce",
    "config": {
        "x": "0.5",
        "y": "0.5",
        "size": "0.03",
        "color": "#ffffff",
        "vx": "0.25",
        "vy": "0.35",
        "walls": "all",
    },
    "provides": [],
    "requires": [],
    "exposes": ["ball"],
    "licence": "Rosh-BSL",
}


def generate(config: dict[str, str]) -> list[Statement]:
    """Return a list of unprefixed statements. Loader will prefix them."""
    x = config.get("x", "0.5")
    y = config.get("y", "0.5")
    size = config.get("size", "0.03")
    color = config.get("color", "#ffffff")
    vx = config.get("vx", "0.25")
    vy = config.get("vy", "0.35")
    walls = config.get("walls", "all")

    stmts: list[Statement] = []

    # Ball object — uses _self so `use ball` gives ball.x not ball.ball.x
    stmts.append(CreateStatement(kind="object", name="_self"))
    stmts.append(SetStatement(target="_self.x", value=x))
    stmts.append(SetStatement(target="_self.y", value=y))
    stmts.append(SetStatement(target="_self.width", value=size))
    stmts.append(SetStatement(target="_self.height", value=size))
    stmts.append(SetStatement(target="_self.color", value=color))
    stmts.append(SetStatement(target="_self.label", value='""'))
    stmts.append(SetStatement(target="_self.vx", value=vx))
    stmts.append(SetStatement(target="_self.vy", value=vy))

    # Bounce sound
    stmts.append(SoundStatement(name="bounce", description="click tap"))

    # Wall bounce — left wall (all modes)
    if walls in ("all", "top-sides", "sides"):
        stmts.append(OnStatement(
            event="update", action="set",
            args="_self.vx to _self.vx * -1",
            condition="_self.x < 0.01",
        ))
        stmts.append(OnStatement(
            event="update", action="set",
            args="_self.x to 0.01",
            condition="_self.x < 0.01",
        ))

    # Wall bounce — right wall (all modes)
    if walls in ("all", "top-sides", "sides"):
        stmts.append(OnStatement(
            event="update", action="set",
            args="_self.vx to _self.vx * -1",
            condition="_self.x > 0.97",
        ))
        stmts.append(OnStatement(
            event="update", action="set",
            args="_self.x to 0.97",
            condition="_self.x > 0.97",
        ))

    # Wall bounce — top wall (all, top-sides)
    if walls in ("all", "top-sides"):
        stmts.append(OnStatement(
            event="update", action="set",
            args="_self.vy to _self.vy * -1",
            condition="_self.y < 0.01",
        ))
        stmts.append(OnStatement(
            event="update", action="set",
            args="_self.y to 0.01",
            condition="_self.y < 0.01",
        ))

    # Wall bounce — bottom wall (all only)
    if walls == "all":
        stmts.append(OnStatement(
            event="update", action="set",
            args="_self.vy to _self.vy * -1",
            condition="_self.y > 0.97",
        ))
        stmts.append(OnStatement(
            event="update", action="set",
            args="_self.y to 0.97",
            condition="_self.y > 0.97",
        ))

    return stmts
