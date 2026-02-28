# licence: Rosh-BSL
"""starfield — Python widget factory for random background dots."""

from __future__ import annotations

import hashlib
import random

from rosh_lang.model import CreateStatement, SetStatement, Statement

METADATA = {
    "widget": "starfield",
    "version": "0.1",
    "description": "Random positioned background dots for visual polish",
    "config": {"count": "15"},
    "licence": "Rosh-BSL",
}

_DIM_COLORS = ["#444", "#555", "#666", "#777", "#888", "#555"]


def generate(config: dict[str, str]) -> list[Statement]:
    """Return a list of unprefixed statements. Loader will prefix them."""
    count = int(config.get("count", "15"))

    # Deterministic seed from "starfield"
    seed = int(hashlib.md5(b"starfield").hexdigest(), 16)
    rng = random.Random(seed)

    stmts: list[Statement] = []
    for i in range(count):
        name = f"s{i}"
        stmts.append(CreateStatement(kind="object", name=name))
        stmts.append(SetStatement(target=f"{name}.x", value=str(round(rng.random(), 4))))
        stmts.append(SetStatement(target=f"{name}.y", value=str(round(rng.random(), 4))))
        size = round(rng.uniform(0.004, 0.01), 4)
        stmts.append(SetStatement(target=f"{name}.width", value=str(size)))
        stmts.append(SetStatement(target=f"{name}.height", value=str(size)))
        stmts.append(SetStatement(target=f"{name}.color", value=rng.choice(_DIM_COLORS)))
        stmts.append(SetStatement(target=f"{name}.label", value='""'))
    return stmts
