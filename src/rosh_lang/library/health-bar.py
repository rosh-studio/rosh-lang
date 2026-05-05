# licence: Rosh-BSL
"""health-bar — Python widget factory for a health display.

Creates max, current numbers and a display object with configurable position,
background, text color, and font size. Supports anchor and theme config.
"""

from __future__ import annotations

from rosh_lang.core.model import CreateStatement, SetStatement, Statement
from rosh_lang.core.widgets import compute_hud_position

METADATA = {
    "widget": "health-bar",
    "version": "0.3",
    "description": "Health display with current and max values",
    "config": {
        "max": "100",
        "current": "100",
        "x": "0.02",
        "y": "0.10",
        "bg": "#2a6e2a",
        "text_color": "#fff",
        "font_size": "14px",
        "anchor": "",
        "theme": "",
    },
    "licence": "Rosh-BSL",
}


def generate(config: dict[str, str], user_config: dict[str, str] | None = None) -> list[Statement]:
    """Return a list of unprefixed statements. Loader will prefix them."""
    max_val = config.get("max", "100")
    current = config.get("current", "100")
    x, y, bg, text_color, font_size = compute_hud_position(config, user_config)

    return [
        CreateStatement(kind="number", name="max"),
        SetStatement(target="max", value=max_val),
        CreateStatement(kind="number", name="current"),
        SetStatement(target="current", value=current),
        CreateStatement(kind="object", name="display"),
        SetStatement(target="display.label", value='"HP: {current}/{max}"'),
        SetStatement(target="display.x", value=x),
        SetStatement(target="display.y", value=y),
        SetStatement(target="display.width", value="0.20"),
        SetStatement(target="display.height", value="0.06"),
        SetStatement(target="display.color", value=bg),
        SetStatement(target="display.text_color", value=text_color),
        SetStatement(target="display.font_size", value=font_size),
    ]
