# licence: Rosh-BSL
"""enemy-grid — Python widget factory for a grid of enemy objects.

Supports optional side-to-side drift movement via `drift` config.
When drift > 0, generates drift state + edge-reversal + per-enemy movement.
"""

from __future__ import annotations

from rosh_lang.core.model import (
    CreateStatement,
    OnStatement,
    SetStatement,
    SpriteStatement,
    Statement,
)

METADATA = {
    "widget": "enemy-grid",
    "version": "0.2",
    "description": "Grid of enemy objects with configurable rows, cols, spacing, color, sprite, drift",
    "config": {
        "rows": "2",
        "cols": "5",
        "spacing": "0.12",
        "color": "#e74c3c",
        "sprite": "",
        "drift": "0",
    },
    "provides": [],
    "requires": [],
    "exposes": [],
    "licence": "Rosh-BSL",
}


def generate(config: dict[str, str]) -> list[Statement]:
    """Return a list of unprefixed statements. Loader will prefix them."""
    rows = int(config.get("rows", "2"))
    cols = int(config.get("cols", "5"))
    spacing = float(config.get("spacing", "0.12"))
    color = config.get("color", "#e74c3c")
    sprite_desc = config.get("sprite", "")
    drift_speed = float(config.get("drift", "0"))

    # When drift is active and no explicit sprite, default to game-look
    if drift_speed > 0 and not sprite_desc:
        sprite_desc = "alien invader"

    stmts: list[Statement] = []

    # ── Drift state (only when movement enabled) ──
    if drift_speed > 0:
        stmts.append(CreateStatement(kind="number", name="drift"))
        stmts.append(SetStatement(target="drift", value=str(drift_speed)))

    # ── Enemy objects ──
    enemy_names: list[str] = []
    for r in range(rows):
        for c in range(cols):
            name = f"e{r}_{c}"
            enemy_names.append(name)
            stmts.append(CreateStatement(kind="object", name=name))
            stmts.append(SetStatement(target=f"{name}.x", value=str(round(0.1 + c * spacing, 4))))
            stmts.append(SetStatement(target=f"{name}.y", value=str(round(0.08 + r * spacing, 4))))
            stmts.append(SetStatement(target=f"{name}.width", value="0.08"))
            stmts.append(SetStatement(target=f"{name}.height", value="0.06"))
            stmts.append(SetStatement(target=f"{name}.color", value=color))
            stmts.append(SetStatement(target=f"{name}.label", value='""'))
            if sprite_desc:
                stmts.append(SpriteStatement(name=name, description=sprite_desc))

    # ── Movement (only when drift > 0) ──
    if drift_speed > 0:
        # Edge reversal: rightmost enemy in top row hits right edge
        rightmost = f"e0_{cols - 1}"
        leftmost = "e0_0"
        stmts.append(OnStatement(
            event="update",
            action="set",
            args=f"drift to {-drift_speed}",
            condition=f"{rightmost}.x > 0.88",
        ))
        stmts.append(OnStatement(
            event="update",
            action="set",
            args=f"drift to {drift_speed}",
            condition=f"{leftmost}.x < 0.05",
        ))

        # Per-enemy movement
        for name in enemy_names:
            stmts.append(OnStatement(
                event="update",
                action="set",
                args=f"{name}.x to {name}.x + drift",
            ))

    return stmts
