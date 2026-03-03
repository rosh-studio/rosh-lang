# licence: Rosh-BSL
"""timer — Python widget factory for an auto-decrementing countdown timer.

Creates a seconds number, _timer_total marker, _timer_running flag,
and a display object. The JS runtime tickTimers() auto-decrements
seconds each frame and fires timer_done when it reaches zero.
"""

from __future__ import annotations

from rosh_lang.model import CreateStatement, SetStatement, Statement

METADATA = {
    "widget": "timer",
    "version": "0.2",
    "description": "Countdown timer with auto-tick and done event",
    "config": {
        "total": "60",
        "running": "1",
        "x": "0.80",
        "y": "0.02",
        "bg": "#444",
        "text_color": "#fff",
        "font_size": "14px",
    },
    "licence": "Rosh-BSL",
}


def generate(config: dict[str, str]) -> list[Statement]:
    """Return a list of unprefixed statements. Loader will prefix them."""
    total = config.get("total", "60")
    running = config.get("running", "1")
    x = config.get("x", "0.80")
    y = config.get("y", "0.02")
    bg = config.get("bg", "#444")
    text_color = config.get("text_color", "#fff")
    font_size = config.get("font_size", "14px")

    return [
        # Timer state
        CreateStatement(kind="number", name="seconds"),
        SetStatement(target="seconds", value=total),
        CreateStatement(kind="number", name="_timer_total"),
        SetStatement(target="_timer_total", value=total),
        CreateStatement(kind="number", name="_timer_running"),
        SetStatement(target="_timer_running", value=running),
        # Display
        CreateStatement(kind="object", name="display"),
        SetStatement(target="display.label", value='"Time: {seconds}"'),
        SetStatement(target="display.x", value=x),
        SetStatement(target="display.y", value=y),
        SetStatement(target="display.width", value="0.18"),
        SetStatement(target="display.height", value="0.06"),
        SetStatement(target="display.color", value=bg),
        SetStatement(target="display.text_color", value=text_color),
        SetStatement(target="display.font_size", value=font_size),
    ]
