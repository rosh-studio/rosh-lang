# licence: Rosh-BSL
"""score — Python widget factory for a score display.

Creates a value number and a display object with configurable position,
background, text color, and font size.
"""

from __future__ import annotations

from rosh_lang.model import CreateStatement, SetStatement, Statement

METADATA = {
    "widget": "score",
    "version": "0.2",
    "description": "Score display with current value and label",
    "config": {
        "x": "0.02",
        "y": "0.02",
        "bg": "#333",
        "text_color": "#fff",
        "font_size": "14px",
    },
    "licence": "Rosh-BSL",
}


def generate(config: dict[str, str]) -> list[Statement]:
    """Return a list of unprefixed statements. Loader will prefix them."""
    x = config.get("x", "0.02")
    y = config.get("y", "0.02")
    bg = config.get("bg", "#333")
    text_color = config.get("text_color", "#fff")
    font_size = config.get("font_size", "14px")

    return [
        CreateStatement(kind="number", name="value"),
        SetStatement(target="value", value="0"),
        CreateStatement(kind="object", name="display"),
        SetStatement(target="display.label", value='"Score: {value}"'),
        SetStatement(target="display.x", value=x),
        SetStatement(target="display.y", value=y),
        SetStatement(target="display.width", value="0.15"),
        SetStatement(target="display.height", value="0.06"),
        SetStatement(target="display.color", value=bg),
        SetStatement(target="display.text_color", value=text_color),
        SetStatement(target="display.font_size", value=font_size),
    ]
