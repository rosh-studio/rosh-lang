# licence: Rosh-BSL
"""fps — Python widget factory for an FPS counter.

Creates a frames number and a display object with configurable position,
background, text color, and font size.
"""

from __future__ import annotations

from rosh_lang.model import CreateStatement, SetStatement, Statement

METADATA = {
    "widget": "fps",
    "version": "0.2",
    "description": "FPS counter for game loop",
    "config": {
        "x": "0.90",
        "y": "0.95",
        "bg": "#222",
        "text_color": "#fff",
        "font_size": "14px",
    },
    "licence": "Rosh-BSL",
}


def generate(config: dict[str, str]) -> list[Statement]:
    """Return a list of unprefixed statements. Loader will prefix them."""
    x = config.get("x", "0.90")
    y = config.get("y", "0.95")
    bg = config.get("bg", "#222")
    text_color = config.get("text_color", "#fff")
    font_size = config.get("font_size", "14px")

    return [
        CreateStatement(kind="number", name="frames"),
        SetStatement(target="frames", value="0"),
        CreateStatement(kind="object", name="display"),
        SetStatement(target="display.label", value='"FPS: {frames}"'),
        SetStatement(target="display.x", value=x),
        SetStatement(target="display.y", value=y),
        SetStatement(target="display.width", value="0.10"),
        SetStatement(target="display.height", value="0.04"),
        SetStatement(target="display.color", value=bg),
        SetStatement(target="display.text_color", value=text_color),
        SetStatement(target="display.font_size", value=font_size),
    ]
