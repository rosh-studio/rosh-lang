# licence: Rosh-BSL
"""hazard — Python widget factory for a pool of falling/approaching obstacles.

Same pool pattern as bullet.py but for hazards (enemies, rocks, etc.).
Supports auto-spawn via _spawn_rate: the JS runtime tickPools() fires
a new hazard at a random x position every _spawn_rate seconds.
"""

from __future__ import annotations

from rosh_lang.model import (
    CreateStatement,
    SetStatement,
    SpriteStatement,
    Statement,
)

METADATA = {
    "widget": "hazard",
    "version": "0.1",
    "description": "Pooled falling obstacles with auto-spawn",
    "config": {
        "count": "5",
        "vx": "0",
        "vy": "0.3",
        "color": "#e94560",
        "width": "0.08",
        "height": "0.08",
        "sprite": "",
        "spawn_rate": "0.8",
    },
    "licence": "Rosh-BSL",
}


def generate(config: dict[str, str]) -> list[Statement]:
    """Return a list of unprefixed statements. Loader will prefix them."""
    count = int(config.get("count", "5"))
    vx = float(config.get("vx", "0"))
    vy = float(config.get("vy", "0.3"))
    color = config.get("color", "#e94560")
    width = config.get("width", "0.08")
    height = config.get("height", "0.08")
    sprite_desc = config.get("sprite", "")
    spawn_rate = config.get("spawn_rate", "0.8")

    stmts: list[Statement] = []

    # ── Pool metadata (same convention as bullet.py) ──
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
    stmts.append(SetStatement(target="_y", value="-0.05"))
    stmts.append(CreateStatement(kind="number", name="_vx"))
    stmts.append(SetStatement(target="_vx", value=str(vx)))
    stmts.append(CreateStatement(kind="number", name="_vy"))
    stmts.append(SetStatement(target="_vy", value=str(vy)))

    # Auto-spawn timer
    stmts.append(CreateStatement(kind="number", name="_spawn_rate"))
    stmts.append(SetStatement(target="_spawn_rate", value=spawn_rate))
    stmts.append(CreateStatement(kind="number", name="_spawn_timer"))
    stmts.append(SetStatement(target="_spawn_timer", value="0"))

    # ── Hazard objects ──
    for i in range(count):
        name = f"b{i}"
        stmts.append(CreateStatement(kind="object", name=name))
        stmts.append(SetStatement(target=f"{name}.x", value="-1"))
        stmts.append(SetStatement(target=f"{name}.y", value="-1"))
        stmts.append(SetStatement(target=f"{name}.width", value=width))
        stmts.append(SetStatement(target=f"{name}.height", value=height))
        stmts.append(SetStatement(target=f"{name}.color", value=color))
        stmts.append(SetStatement(target=f"{name}.label", value='""'))
        stmts.append(SetStatement(target=f"{name}.vx", value="0"))
        stmts.append(SetStatement(target=f"{name}.vy", value="0"))
        if sprite_desc:
            stmts.append(SpriteStatement(name=name, description=sprite_desc))

    return stmts
