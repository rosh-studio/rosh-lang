# licence: Rosh-BSL
"""title-screen — Python widget factory for a title + subtitle + prompt overlay.

Creates three stacked objects (heading, sub, prompt) with configurable
title, subtitle, background, text color, and font size.
"""

from __future__ import annotations

from rosh_lang.core.model import CreateStatement, SetStatement, Statement

METADATA = {
    "widget": "title-screen",
    "version": "0.2",
    "description": "Title + subtitle + prompt — three stacked objects",
    "config": {
        "title": "Rosh",
        "subtitle": "Press any key",
        "bg": "#222",
        "text_color": "#fff",
        "font_size": "14px",
    },
    "licence": "Rosh-BSL",
}


def generate(config: dict[str, str]) -> list[Statement]:
    """Return a list of unprefixed statements. Loader will prefix them."""
    title = config.get("title", "Rosh")
    subtitle = config.get("subtitle", "Press any key")
    bg = config.get("bg", "#222")
    text_color = config.get("text_color", "#fff")
    font_size = config.get("font_size", "14px")

    return [
        # Heading
        CreateStatement(kind="object", name="heading"),
        SetStatement(target="heading.x", value="0.2"),
        SetStatement(target="heading.y", value="0.25"),
        SetStatement(target="heading.width", value="0.6"),
        SetStatement(target="heading.height", value="0.1"),
        SetStatement(target="heading.color", value=bg),
        SetStatement(target="heading.label", value=f'"{title}"'),
        SetStatement(target="heading.text_color", value=text_color),
        SetStatement(target="heading.font_size", value=font_size),
        # Subtitle
        CreateStatement(kind="object", name="sub"),
        SetStatement(target="sub.x", value="0.25"),
        SetStatement(target="sub.y", value="0.38"),
        SetStatement(target="sub.width", value="0.5"),
        SetStatement(target="sub.height", value="0.06"),
        SetStatement(target="sub.color", value="#333"),
        SetStatement(target="sub.label", value=f'"{subtitle}"'),
        SetStatement(target="sub.text_color", value=text_color),
        SetStatement(target="sub.font_size", value=font_size),
        # Prompt
        CreateStatement(kind="object", name="prompt"),
        SetStatement(target="prompt.x", value="0.3"),
        SetStatement(target="prompt.y", value="0.55"),
        SetStatement(target="prompt.width", value="0.4"),
        SetStatement(target="prompt.height", value="0.05"),
        SetStatement(target="prompt.color", value="#444"),
        SetStatement(target="prompt.label", value='"Click to start"'),
        SetStatement(target="prompt.text_color", value=text_color),
        SetStatement(target="prompt.font_size", value=font_size),
    ]
