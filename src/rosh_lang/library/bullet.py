# licence: Rosh-BSL
"""bullet — Python widget factory for a pool of reusable bullet objects.

Creates N bullet objects (b0..bN-1) parked off-screen at (-1, -1).
Pool metadata in state enables fire-on-flag via JS runtime tickPools().
Boundary cleanup on-statements recycle bullets that leave the canvas.
"""

from __future__ import annotations

from rosh_lang.core.model import (
    CreateStatement,
    SetStatement,
    SoundStatement,
    Statement,
)

METADATA = {
    "widget": "bullet",
    "version": "0.3",
    "description": "Pooled projectile with configurable count, direction via vx/vy velocity",
    "config": {
        "count": "3",
        "vx": "0",
        "vy": "-0.5",
        "color": "#ffff00",
    },
    "licence": "Rosh-BSL",
}


def generate(config: dict[str, str]) -> list[Statement]:
    """Return a list of unprefixed statements. Loader will prefix them."""
    count = int(config.get("count", "3"))
    vx = float(config.get("vx", "0"))
    vy = float(config.get("vy", "-0.5"))
    color = config.get("color", "#ffff00")

    stmts: list[Statement] = []

    # ── Pool metadata ──
    stmts.append(CreateStatement(kind="number", name="_pool_count"))
    stmts.append(SetStatement(target="_pool_count", value=str(count)))
    stmts.append(CreateStatement(kind="number", name="_pool_vx"))
    stmts.append(SetStatement(target="_pool_vx", value=str(vx)))
    stmts.append(CreateStatement(kind="number", name="_pool_vy"))
    stmts.append(SetStatement(target="_pool_vy", value=str(vy)))
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
    stmts.append(SetStatement(target="_vx", value=str(vx)))
    stmts.append(CreateStatement(kind="number", name="_vy"))
    stmts.append(SetStatement(target="_vy", value=str(vy)))

    # ── Bullet objects ──
    for i in range(count):
        name = f"b{i}"
        stmts.append(CreateStatement(kind="object", name=name))
        stmts.append(SetStatement(target=f"{name}.x", value="-1"))
        stmts.append(SetStatement(target=f"{name}.y", value="-1"))
        stmts.append(SetStatement(target=f"{name}.width", value="0.02"))
        stmts.append(SetStatement(target=f"{name}.height", value="0.04"))
        stmts.append(SetStatement(target=f"{name}.color", value=color))
        stmts.append(SetStatement(target=f"{name}.label", value='""'))
        stmts.append(SetStatement(target=f"{name}.vx", value="0"))
        stmts.append(SetStatement(target=f"{name}.vy", value="0"))

    # Boundary cleanup is handled by tickPools() in the JS runtime —
    # no on-statements needed. This avoids race conditions between
    # boundary resets and pool firing on the same tick.

    # ── Sound ──
    stmts.append(SoundStatement(name="pew", description="short laser shot"))

    return stmts
