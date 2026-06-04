# licence: Rosh-BSL
"""message — Python widget factory for a text overlay message.

Creates a box object with configurable text, position, background,
text color, and font size.
"""

from __future__ import annotations

from rosh_lang.core.model import CreateStatement, SetStatement, Statement

METADATA = {
    "widget": "message",
    "version": "0.2",
    "description": "Text overlay with configurable position, color, and content",
    "config": {
        "text": "Hello",
        "x": "0.3",
        "y": "0.4",
        "bg": "#333",
        "text_color": "#fff",
        "font_size": "14px",
    },
    "provides": [],
    "requires": [],
    "exposes": [],
    "licence": "Rosh-BSL",
}


def generate(config: dict[str, str]) -> list[Statement]:
    """Return a list of unprefixed statements. Loader will prefix them."""
    text = config.get("text", "Hello")
    x = config.get("x", "0.3")
    y = config.get("y", "0.4")
    bg = config.get("bg", "#333")
    text_color = config.get("text_color", "#fff")
    font_size = config.get("font_size", "14px")

    return [
        CreateStatement(kind="object", name="box"),
        SetStatement(target="box.x", value=x),
        SetStatement(target="box.y", value=y),
        SetStatement(target="box.width", value="0.4"),
        SetStatement(target="box.height", value="0.08"),
        SetStatement(target="box.color", value=bg),
        SetStatement(target="box.label", value=f'"{text}"'),
        SetStatement(target="box.text_color", value=text_color),
        SetStatement(target="box.font_size", value=font_size),
    ]
