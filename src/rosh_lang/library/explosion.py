# licence: Rosh-BSL
"""explosion — Python widget factory for a pool of reusable explosion effects.

Creates N flash objects parked off-screen. When _fire flag is set, positions
a flash and starts the grow-then-shrink animation via on-statement conditions.
Reuses the same tickPools() mechanism as bullet.
"""

from __future__ import annotations

from rosh_lang.model import (
    CreateStatement,
    OnStatement,
    SetStatement,
    SoundStatement,
    SpriteStatement,
    Statement,
)

METADATA = {
    "widget": "explosion",
    "version": "0.2",
    "description": "Pooled explosion effect with configurable count and color",
    "config": {
        "count": "3",
        "color": "#ff4444",
    },
    "licence": "Rosh-BSL",
}


def generate(config: dict[str, str]) -> list[Statement]:
    """Return a list of unprefixed statements. Loader will prefix them."""
    count = int(config.get("count", "3"))
    color = config.get("color", "#ff4444")

    stmts: list[Statement] = []

    # ── Pool metadata (reuses tickPools convention) ──
    stmts.append(CreateStatement(kind="number", name="_pool_count"))
    stmts.append(SetStatement(target="_pool_count", value=str(count)))
    stmts.append(CreateStatement(kind="number", name="_pool_vx"))
    stmts.append(SetStatement(target="_pool_vx", value="0"))
    stmts.append(CreateStatement(kind="number", name="_pool_vy"))
    stmts.append(SetStatement(target="_pool_vy", value="0"))
    stmts.append(CreateStatement(kind="number", name="_next"))
    stmts.append(SetStatement(target="_next", value="0"))
    stmts.append(CreateStatement(kind="number", name="_fire"))
    stmts.append(SetStatement(target="_fire", value="0"))
    stmts.append(CreateStatement(kind="number", name="_active"))
    stmts.append(SetStatement(target="_active", value="0"))
    stmts.append(CreateStatement(kind="number", name="_x"))
    stmts.append(SetStatement(target="_x", value="0"))
    stmts.append(CreateStatement(kind="number", name="_y"))
    stmts.append(SetStatement(target="_y", value="0"))
    stmts.append(CreateStatement(kind="number", name="_vx"))
    stmts.append(SetStatement(target="_vx", value="0"))
    stmts.append(CreateStatement(kind="number", name="_vy"))
    stmts.append(SetStatement(target="_vy", value="0"))

    # ── Flash objects ──
    for i in range(count):
        name = f"b{i}"
        stmts.append(CreateStatement(kind="object", name=name))
        stmts.append(SetStatement(target=f"{name}.x", value="-1"))
        stmts.append(SetStatement(target=f"{name}.y", value="-1"))
        stmts.append(SetStatement(target=f"{name}.width", value="0.01"))
        stmts.append(SetStatement(target=f"{name}.height", value="0.01"))
        stmts.append(SetStatement(target=f"{name}.color", value=color))
        stmts.append(SetStatement(target=f"{name}.label", value='""'))
        stmts.append(SetStatement(target=f"{name}.vx", value="0"))
        stmts.append(SetStatement(target=f"{name}.vy", value="0"))
        stmts.append(SpriteStatement(name=name, description="orange explosion"))

        # Grow while on-screen (y > -1 means active)
        stmts.append(OnStatement(
            event="update",
            action="set",
            args=f"{name}.width to {name}.width + 0.008",
            condition=f"{name}.y > -0.5",
        ))
        stmts.append(OnStatement(
            event="update",
            action="set",
            args=f"{name}.height to {name}.height + 0.008",
            condition=f"{name}.y > -0.5",
        ))

        # When flash gets big enough, reset to off-screen
        stmts.append(OnStatement(
            event="update",
            action="set",
            args=f"{name}.x to -1",
            condition=f"{name}.width > 0.12",
        ))
        stmts.append(OnStatement(
            event="update",
            action="set",
            args=f"{name}.y to -1",
            condition=f"{name}.width > 0.12",
        ))
        stmts.append(OnStatement(
            event="update",
            action="set",
            args=f"{name}.width to 0.01",
            condition=f"{name}.width > 0.12",
        ))
        stmts.append(OnStatement(
            event="update",
            action="set",
            args=f"{name}.height to 0.01",
            condition=f"{name}.height > 0.12",
        ))

    # ── Sound ──
    stmts.append(SoundStatement(name="boom", description="explosion blast"))

    return stmts
