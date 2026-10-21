# licence: MIT
"""grid — Python widget factory for a grid of positioned cells."""

from __future__ import annotations

from rosh_lang.core.model import CreateStatement, SetStatement, Statement

METADATA = {
    "widget": "grid",
    "version": "0.2",
    "description": "Grid layout — creates N×M positioned cells",
    "config": {"rows": "3", "cols": "3", "spacing": "0.1", "color": "#333"},
    "provides": [],
    "requires": [],
    "exposes": [],
    "licence": "MIT",
}


def generate(config: dict[str, str]) -> list[Statement]:
    """Return a list of unprefixed statements. Loader will prefix them."""
    rows = int(config.get("rows", "3"))
    cols = int(config.get("cols", "3"))
    spacing = float(config.get("spacing", "0.1"))
    color = config.get("color", "#333")

    stmts: list[Statement] = []
    for r in range(rows):
        for c in range(cols):
            name = f"cell_{r}_{c}"
            stmts.append(CreateStatement(kind="object", name=name))
            stmts.append(SetStatement(target=f"{name}.x", value=str(round(0.05 + c * spacing, 4))))
            stmts.append(SetStatement(target=f"{name}.y", value=str(round(0.05 + r * spacing, 4))))
            stmts.append(SetStatement(target=f"{name}.width", value=str(round(spacing * 0.9, 4))))
            stmts.append(SetStatement(target=f"{name}.height", value=str(round(spacing * 0.9, 4))))
            stmts.append(SetStatement(target=f"{name}.color", value=color))
            stmts.append(SetStatement(target=f"{name}.label", value='""'))
    return stmts
