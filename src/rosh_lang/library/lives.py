# licence: MIT
"""lives — Python widget factory for a lives display.

Creates a count number and a display object with configurable position,
background, text color, and font size. Supports anchor and theme config.
"""

from __future__ import annotations

from rosh_lang.core.model import (
    CreateStatement,
    EventStatement,
    OnStatement,
    SetStatement,
    Statement,
)
from rosh_lang.core.widgets import compute_hud_position

METADATA = {
    "widget": "lives",
    "version": "0.3",
    "description": "Lives display with count",
    "config": {
        "count": "3",
        "auto_gameover": "1",
        "x": "0.02",
        "y": "0.18",
        "bg": "#663333",
        "text_color": "#fff",
        "font_size": "14px",
        "anchor": "",
        "theme": "",
    },
    "provides": ["game_over"],
    "requires": [],
    "exposes": ["count"],
    "licence": "MIT",
}


def generate(config: dict[str, str], user_config: dict[str, str] | None = None) -> list[Statement]:
    """Return a list of unprefixed statements. Loader will prefix them."""
    count = config.get("count", "3")
    auto_gameover = config.get("auto_gameover", "1")
    x, y, bg, text_color, font_size = compute_hud_position(config, user_config)

    stmts: list[Statement] = [
        CreateStatement(kind="number", name="count"),
        SetStatement(target="count", value=count),
        CreateStatement(kind="object", name="display"),
        SetStatement(target="display.label", value='"Lives: {count}"'),
        SetStatement(target="display.x", value=x),
        SetStatement(target="display.y", value=y),
        SetStatement(target="display.width", value="0.15"),
        SetStatement(target="display.height", value="0.06"),
        SetStatement(target="display.color", value=bg),
        SetStatement(target="display.text_color", value=text_color),
        SetStatement(target="display.font_size", value=font_size),
    ]

    # Auto game-over: when count hits 0, send game_over event
    if auto_gameover == "1":
        stmts.append(EventStatement(name="check-lives", payload_fields=[]))
        stmts.append(OnStatement(
            event="check-lives", action="send", args="game_over",
            condition="count <= 0",
        ))

    return stmts
