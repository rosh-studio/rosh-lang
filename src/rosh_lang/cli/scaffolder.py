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
        "A complete game with title screen, gameplay, and game over",
        '''\
# {name} — a Rosh game
# Run: rosh {name}.rosh --target web --run
#      rosh {name}.rosh --target phaser --run
#      rosh {name}.rosh --target threejs --run
# licence: Rosh-BSL

# ── Game lifecycle (title → playing → game over → restart) ──
use game-lifecycle title "{name}" subtitle "Press Space to start"

# ── HUD ──
use score
use lives count 3

# ── Player (controller handles keyboard + mobile touch) ──
create object player
set player.x to 0.45
set player.y to 0.8
set player.width to 0.08
set player.height to 0.08
set player.color to "#4ade80"
sprite player "green spaceship"

use controller target player speed 0.03 move x fire on

# ── Falling hazards ──
use hazard count 5 vy 0.4 color "#ef4444" width 0.06 height 0.06 spawn_rate 0.02 sprite "red asteroid"

# ── Bullet pool + explosion pool ──
use bullet count 3 vy -0.5 color "#facc15"
use explosion count 3

# ── Sound effects ──
sound laser "laser shoot"
sound boom "explosion hit"
sound ouch "hit damage"

# ── Fire: controller sends "fire" event, we launch a bullet ──
when fire
  set bullet._x to player.x
  set bullet._y to player.y
  set bullet._fire to 1
  play laser
end

# ── Bullet hits hazard: score + explosion ──
when collision bullet.* hazard.*
  set score.value to score.value + 10
  set explosion._x to b_x
  set explosion._y to b_y
  set explosion._fire to 1
  play boom
end

# ── Hazard hits player: lose a life ──
when collision hazard.* player
  set lives.count to lives.count - 1
  send check-lives
  set explosion._x to player.x
  set explosion._y to player.y
  set explosion._fire to 1
  play ouch
end

# ── Game over (auto-fired when lives hit 0) ──
when game_over
  print "GAME OVER — Score: {{score.value}}"
end

# ── Restart: reset state ──
when game_restart
  set score.value to 0
  set lives.count to 3
  set player.x to 0.45
  set player.y to 0.8
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
