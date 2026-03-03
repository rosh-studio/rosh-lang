# licence: Rosh-BSL
"""label — Python widget factory for a positioned text label.

Creates a display object with configurable text, position, background,
text color, and font size.
"""

from __future__ import annotations

from rosh_lang.model import CreateStatement, SetStatement, Statement

METADATA = {
    "widget": "label",
    "version": "0.2",
    "description": "Positioned text label",
    "config": {
        "text": "Hello",
        "x": "0.5",
        "y": "0.5",
        "bg": "#555",
        "text_color": "#fff",
        "font_size": "14px",
    },
    "licence": "Rosh-BSL",
}


def generate(config: dict[str, str]) -> list[Statement]:
    """Return a list of unprefixed statements. Loader will prefix them."""
    text = config.get("text", "Hello")
    x = config.get("x", "0.5")
    y = config.get("y", "0.5")
    bg = config.get("bg", "#555")
    text_color = config.get("text_color", "#fff")
    font_size = config.get("font_size", "14px")

    return [
        CreateStatement(kind="object", name="display"),
        SetStatement(target="display.label", value=f'"{text}"'),
        SetStatement(target="display.x", value=x),
        SetStatement(target="display.y", value=y),
        SetStatement(target="display.width", value="0.20"),
        SetStatement(target="display.height", value="0.06"),
        SetStatement(target="display.color", value=bg),
        SetStatement(target="display.text_color", value=text_color),
        SetStatement(target="display.font_size", value=font_size),
    ]
