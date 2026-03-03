# licence: Rosh-BSL
"""game-lifecycle — Python widget factory for title → playing → over game flow.

Creates phase state, title/over UI objects, and event handlers for
game-start, game-over, and game-restart transitions. Handles click
and Space key to start/restart.
"""

from __future__ import annotations

from rosh_lang.model import (
    CreateStatement,
    OnStatement,
    SetStatement,
    Statement,
)

METADATA = {
    "widget": "game-lifecycle",
    "version": "0.1",
    "description": "Title → playing → game-over lifecycle with events",
    "config": {
        "title": "My Game",
        "subtitle": "Press Space to start",
        "bg": "#222",
        "text_color": "#fff",
        "font_size": "14px",
    },
    "licence": "Rosh-BSL",
}


def generate(config: dict[str, str]) -> list[Statement]:
    """Return a list of unprefixed statements. Loader will prefix them."""
    title = config.get("title", "My Game")
    subtitle = config.get("subtitle", "Press Space to start")
    bg = config.get("bg", "#222")
    text_color = config.get("text_color", "#fff")
    font_size = config.get("font_size", "14px")

    stmts: list[Statement] = []

    # ── Phase state ──
    stmts.append(CreateStatement(kind="string", name="phase"))
    stmts.append(SetStatement(target="phase", value='"title"'))

    # ── Title objects ──
    stmts.append(CreateStatement(kind="object", name="title_heading"))
    stmts.append(SetStatement(target="title_heading.x", value="0.15"))
    stmts.append(SetStatement(target="title_heading.y", value="0.25"))
    stmts.append(SetStatement(target="title_heading.width", value="0.7"))
    stmts.append(SetStatement(target="title_heading.height", value="0.12"))
    stmts.append(SetStatement(target="title_heading.color", value=bg))
    stmts.append(SetStatement(target="title_heading.label", value=f'"{title}"'))
    stmts.append(SetStatement(target="title_heading.text_color", value=text_color))
    stmts.append(SetStatement(target="title_heading.font_size", value="24px"))

    stmts.append(CreateStatement(kind="object", name="title_sub"))
    stmts.append(SetStatement(target="title_sub.x", value="0.2"))
    stmts.append(SetStatement(target="title_sub.y", value="0.40"))
    stmts.append(SetStatement(target="title_sub.width", value="0.6"))
    stmts.append(SetStatement(target="title_sub.height", value="0.06"))
    stmts.append(SetStatement(target="title_sub.color", value="#333"))
    stmts.append(SetStatement(target="title_sub.label", value=f'"{subtitle}"'))
    stmts.append(SetStatement(target="title_sub.text_color", value=text_color))
    stmts.append(SetStatement(target="title_sub.font_size", value=font_size))

    # ── Game-over objects (hidden initially) ──
    stmts.append(CreateStatement(kind="object", name="over_heading"))
    stmts.append(SetStatement(target="over_heading.x", value="0.15"))
    stmts.append(SetStatement(target="over_heading.y", value="0.30"))
    stmts.append(SetStatement(target="over_heading.width", value="0.7"))
    stmts.append(SetStatement(target="over_heading.height", value="0.12"))
    stmts.append(SetStatement(target="over_heading.color", value="#660000"))
    stmts.append(SetStatement(target="over_heading.label", value='"GAME OVER"'))
    stmts.append(SetStatement(target="over_heading.text_color", value=text_color))
    stmts.append(SetStatement(target="over_heading.font_size", value="24px"))
    stmts.append(SetStatement(target="over_heading.visible", value="0"))

    stmts.append(CreateStatement(kind="object", name="over_restart"))
    stmts.append(SetStatement(target="over_restart.x", value="0.25"))
    stmts.append(SetStatement(target="over_restart.y", value="0.48"))
    stmts.append(SetStatement(target="over_restart.width", value="0.5"))
    stmts.append(SetStatement(target="over_restart.height", value="0.06"))
    stmts.append(SetStatement(target="over_restart.color", value="#444"))
    stmts.append(SetStatement(target="over_restart.label", value='"Press Space to restart"'))
    stmts.append(SetStatement(target="over_restart.text_color", value=text_color))
    stmts.append(SetStatement(target="over_restart.font_size", value=font_size))
    stmts.append(SetStatement(target="over_restart.visible", value="0"))

    # ── Handlers ──
    # Space key: start game from title, restart from over
    stmts.append(OnStatement(
        event="keydown",
        action="set",
        args='phase to "playing"',
        condition='phase == "title"',
    ))
    stmts.append(OnStatement(
        event="keydown",
        action="set",
        args="title_heading.visible to 0",
        condition='phase == "playing"',
    ))
    stmts.append(OnStatement(
        event="keydown",
        action="set",
        args="title_sub.visible to 0",
        condition='phase == "playing"',
    ))
    stmts.append(OnStatement(
        event="keydown",
        action="send",
        args="game_start",
        condition='phase == "playing"',
    ))

    # game_over event: switch to over phase
    stmts.append(OnStatement(
        event="game_over",
        action="set",
        args='phase to "over"',
    ))
    stmts.append(OnStatement(
        event="game_over",
        action="set",
        args="over_heading.visible to 1",
    ))
    stmts.append(OnStatement(
        event="game_over",
        action="set",
        args="over_restart.visible to 1",
    ))

    # Restart from over phase
    stmts.append(OnStatement(
        event="keydown",
        action="set",
        args='phase to "title"',
        condition='phase == "over"',
    ))
    stmts.append(OnStatement(
        event="keydown",
        action="set",
        args="over_heading.visible to 0",
        condition='phase == "title"',
    ))
    stmts.append(OnStatement(
        event="keydown",
        action="set",
        args="over_restart.visible to 0",
        condition='phase == "title"',
    ))
    stmts.append(OnStatement(
        event="keydown",
        action="set",
        args="title_heading.visible to 1",
        condition='phase == "title"',
    ))
    stmts.append(OnStatement(
        event="keydown",
        action="set",
        args="title_sub.visible to 1",
        condition='phase == "title"',
    ))
    stmts.append(OnStatement(
        event="keydown",
        action="send",
        args="game_restart",
        condition='phase == "title"',
    ))

    return stmts
