"""rosh new — scaffold starter .rosh files.

Usage:
    rosh new              → prompt for template
    rosh new game         → creates my-game.rosh
    rosh new game pong    → creates pong.rosh
"""

from __future__ import annotations

import sys
from pathlib import Path

from rich.console import Console
from rich.theme import Theme

_THEME = Theme({
    "rosh.brand": "bold magenta",
    "rosh.error": "bold red",
    "rosh.value": "green",
    "rosh.muted": "dim",
    "rosh.key": "cyan",
})

console = Console(theme=_THEME)


# ── Templates ────────────────────────────────────────────────

_TEMPLATES: dict[str, tuple[str, str]] = {
    "hello": (
        "A minimal hello-world programme",
        '''\
# {name} — a Rosh programme
# licence: Rosh-BSL

print "hello from {name}!"
print "edit this file and run: rosh {name}.rosh"
''',
    ),
    "game": (
        "A playable game with player, score, and shooting",
        '''\
# {name} — a Rosh game
# Run with: rosh {name}.rosh --target web --run
# licence: Rosh-BSL

# ── Score ──
use score

# ── Player ──
use player speed 0.03
sprite player.ship "green spaceship"

# ── Bullet pool ──
use bullet count 3 vy -0.5 color "#ffff00"

# ── Enemy ──
create object enemy
set enemy.x to 0.45
set enemy.y to 0.1
set enemy.width to 0.08
set enemy.height to 0.06
set enemy.color to "#ff4444"
sprite enemy "red alien"

# ── Sound effects ──
sound laser "laser shoot"
sound hit "explosion hit"

# ── Shooting ──
on keydown when key == " " set bullet._x to player.ship.x
on keydown when key == " " set bullet._y to player.ship.y
on keydown when key == " " set bullet._fire to 1
on keydown when key == " " play laser

# ── Collision ──
when collision bullet.* enemy
  set score.value to score.value + 1
  play hit
end
''',
    ),
    "app": (
        "An interactive web app with header and click counter",
        '''\
# {name} — a Rosh app
# Run with: rosh {name}.rosh --target web --run
# licence: Rosh-BSL

# ── Header ──
create object header
set header.width to 1.0
set header.height to 60
set header.color to "#0f3460"
set header.label to "{name}"

# ── Click counter ──
use counter

print "click anywhere to count!"
''',
    ),
}


# ── Public API ────────────────────────────────────────────────


def scaffold(args: list[str]) -> None:
    """Handle `rosh new [template] [name]`."""
    template_name: str | None = None
    project_name: str | None = None

    if len(args) >= 1:
        template_name = args[0]
    if len(args) >= 2:
        project_name = args[1]

    # Prompt for template if not given
    if template_name is None:
        console.print("[rosh.brand]rosh new[/] — create a starter programme\n")
        console.print("Templates:")
        for key, (desc, _) in _TEMPLATES.items():
            console.print(f"  [rosh.key]{key:8s}[/]  {desc}")
        console.print()
        try:
            template_name = console.input("[rosh.muted]Choose a template: [/]").strip()
        except (EOFError, KeyboardInterrupt):
            console.print()
            return

    if template_name not in _TEMPLATES:
        console.print(f"[rosh.error]Unknown template: {template_name}[/]")
        console.print(f"[rosh.muted]Available: {', '.join(_TEMPLATES)}[/]")
        sys.exit(1)

    # Default project name
    if project_name is None:
        project_name = f"my-{template_name}"

    # Strip .rosh extension if given
    if project_name.endswith(".rosh"):
        project_name = project_name[:-5]

    filename = f"{project_name}.rosh"
    path = Path(filename)

    if path.exists():
        console.print(f"[rosh.error]File already exists: {filename}[/]")
        sys.exit(1)

    _, template = _TEMPLATES[template_name]
    content = template.replace("{name}", project_name)

    path.write_text(content)
    console.print(f"[rosh.value]Created {filename}[/]")

    if template_name == "hello":
        console.print(f"[rosh.muted]Run it:  rosh {filename}[/]")
    else:
        console.print(f"[rosh.muted]Run it:  rosh {filename} --target web --run[/]")
