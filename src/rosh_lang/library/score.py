# licence: MIT
"""score — Python widget factory for a score display.

Creates a value number and a display object with configurable position,
background, text color, and font size. Supports anchor and theme config.
"""

from __future__ import annotations

from rosh_lang.core.model import CreateStatement, SetStatement, Statement
from rosh_lang.core.widgets import compute_hud_position

METADATA = {
    "widget": "score",
    "version": "0.3",
    "description": "Score display with current value and label",
    "config": {
        "x": "0.02",
        "y": "0.02",
        "bg": "#333",
        "text_color": "#fff",
        "font_size": "14px",
        "anchor": "",
        "theme": "",
        "label": "Score:",
    },
    "provides": [],
    "requires": [],
    "exposes": ["value"],
    "licence": "MIT",
}


def generate(config: dict[str, str], user_config: dict[str, str] | None = None) -> list[Statement]:
    """Return a list of unprefixed statements. Loader will prefix them."""
    x, y, bg, text_color, font_size = compute_hud_position(config, user_config)
    label_text = config.get("label", "Score:")

    return [
        CreateStatement(kind="number", name="value"),
        SetStatement(target="value", value="0"),
        CreateStatement(kind="object", name="display"),
        SetStatement(target="display.label", value=f'"{label_text} {{value}}"'),
        SetStatement(target="display.x", value=x),
        SetStatement(target="display.y", value=y),
        SetStatement(target="display.width", value="0.15"),
        SetStatement(target="display.height", value="0.06"),
        SetStatement(target="display.color", value=bg),
        SetStatement(target="display.text_color", value=text_color),
        SetStatement(target="display.font_size", value=font_size),
    ]
