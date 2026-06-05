# licence: MIT
"""animation — Python widget factory for spritesheet animation.

Usage:
    use animation target player sheet "player-sheet.png" frames 4 speed 8
"""

from __future__ import annotations

from rosh_lang.core.model import AnimateStatement, Statement

METADATA = {
    "widget": "animation",
    "version": "0.1",
    "description": "Spritesheet animation — attach a looping animation to an object",
    "config": {
        "target": "player",
        "sheet": "player-sheet.png",
        "frames": "4",
        "speed": "8",
        "mode": "loop",
    },
    "provides": [],
    "requires": [],
    "exposes": [],
    "licence": "MIT",
}


def generate(config: dict[str, str]) -> list[Statement]:
    """Return an AnimateStatement. Loader will prefix names."""
    return [
        AnimateStatement(
            name=config.get("target", "player"),
            sheet=config.get("sheet", "player-sheet.png"),
            frames=int(config.get("frames", "4")),
            speed=int(config.get("speed", "8")),
            mode=config.get("mode", "loop"),
        ),
    ]
