# Rosh Language — Agent Context

Everything an AI agent needs to write `.rosh` files and work on `rosh-lang/`.

## What Rosh Is

A plain-English language: `print "hello"` runs on terminal, browser, and game engine. Same source, different targets. "One script, many worlds."

## How to Run

```bash
rosh hello.rosh                        # terminal
rosh hello.rosh --target web --run     # browser
rosh hello.rosh --target phaser --run  # Phaser game
rosh                                   # REPL
rosh new game my-game                  # scaffold a starter file
```

## How to Test

```bash
cd rosh-lang && uv run pytest -q       # expect 567+ passed
```

After code changes, reinstall:
```bash
uv tool install --from /path/to/rosh-lang rosh-lang --force
```

## Complete Syntax (21 Keywords)

```
print "text"                          # output ({var} interpolation)
create object player                  # create object/number/string/list
set player.x to 0.5                   # assign value (arithmetic: score + 1)
get player                            # query state
say hello                             # broadcast text
when click                            # event handler block
  set count to count + 1
end                                   # end block
on update set x to x + 0.01          # one-line reactive listener
on keydown when key == " " play sfx  # conditional listener
event scored value                    # declare named event
send scored 10                        # emit event
if score > 10                         # branching
  print "win!"
else
  print "keep going"
end
use score label "Points"              # compose widget with config
go level2                             # scene navigation
look                                  # inspect scene
connect server wss://...              # register connection
destroy enemy                         # remove object
sprite ship "blue spaceship"          # procedural pixel art
sound laser "laser shoot"             # procedural sound
play laser                            # play sound (once/loop/stop)
animate obj sheet "run.png" frames 4  # spritesheet animation
after 3 send timeout                  # delayed event
create scene level1                   # scene definition
```

## Object Properties

| Property | Type | Description |
|----------|------|-------------|
| `x` | float | Position (0.0–1.0 = %, >1 = px) |
| `y` | float | Position (0.0–1.0 = %, >1 = px) |
| `width` | float | Size (default 0.1) |
| `height` | float | Size (default 0.1) |
| `color` | string | Hex or named color |
| `label` | string | Text on object (empty by default) |
| `sprite` | string | Triggers procedural sprite generation |
| `visible` | int | 0 hides, any other shows |
| `vx`, `vy` | float | Velocity (per second) |

## Events

`start`, `update` (dt), `click` (x,y), `click_<name>` (x,y), `keydown` (key), `keyup` (key), `collision` (a,b), `scene_enter` (scene), `scene_exit` (scene), `destroy` (name).

Key-hold: `_keys.ArrowLeft == 1` inside `when update`.

## Game-Building Pattern

```
# Minimal game: player moves, shoots, scores
use score
use player speed 0.03
sprite player.ship "green spaceship"

use bullet count 3 vy -0.5 color "#ffff00"

create object enemy
set enemy.x to 0.45
set enemy.y to 0.1
set enemy.width to 0.08
set enemy.height to 0.06
sprite enemy "red alien"

sound laser "laser shoot"
sound hit "explosion hit"

on keydown when key == " " set bullet._x to player.ship.x
on keydown when key == " " set bullet._y to player.ship.y
on keydown when key == " " set bullet._fire to 1
on keydown when key == " " play laser

when collision bullet.* enemy
  set score.value to score.value + 1
  play hit
end
```

Run: `rosh game.rosh --target web --run`

## Widget Library (19 Widgets)

| Widget | Type | Config | Purpose |
|--------|------|--------|---------|
| `score` | .rosh | `label max min` | Score display |
| `player` | .rosh | `speed` | Keyboard ship |
| `counter` | .rosh | — | Click counter |
| `timer` | .rosh | — | Countdown |
| `health-bar` | .rosh | — | Health display |
| `lives` | .rosh | — | Lives counter |
| `button` | .rosh | — | Clickable button |
| `label` | .rosh | — | Text label |
| `fps` | .rosh | — | FPS counter |
| `message` | .rosh | — | Overlay message |
| `title-screen` | .rosh | — | Title screen |
| `coin` | .rosh | — | Collectible |
| `grid` | .py | `rows cols size gap color` | Cell grid |
| `enemy-grid` | .py | `rows cols size gap color` | Enemy formation |
| `starfield` | .py | `count` | Background stars |
| `bullet` | .py | `count vx vy color` | Pooled projectiles |
| `explosion` | .py | `count color` | Pooled explosions |
| `animation` | .py | `target sheet frames speed mode` | Spritesheet |

Use: `use <widget> [key value ...]` — config pairs override defaults.

## Architecture

```
model.py          → 21 statement dataclasses + Programme
parser.py         → text → Programme
runtime.py        → execute Programme, state dict, events, if/else, scenes
widgets.py        → widget loader: find, namespace-prefix, configure
sprites.py        → name + description → data:image/png;base64 (7×9 grid)
sounds.py         → name + description → Web Audio synthesis params
sheets.py         → PNG spritesheet → list of frame data URIs
assets.py         → resolve asset file paths
scaffolder.py     → rosh new templates
library/          → 19 bundled widgets
targets/
  terminal.py     → print to stdout
  web.py          → self-contained HTML page (CSS divs + JS)
  phaser.py       → Phaser 3.70.0 game (canvas rendering)
  _js_runtime.py  → JS_RUNTIME_CORE (state, events) + JS_RUNTIME_DOM (CSS sync)
  _js_runtime_phaser.py → JS_RUNTIME_PHASER (Phaser renderer, replaces DOM)
  _js_codegen.py  → compile Programme → JavaScript
```

## Rules

1. **Don't add keywords** unless specced in `BUILDING-ROSH.md`
2. **Test after every change**: `cd rosh-lang && uv run pytest -q`
3. **Rebuild showcase** after completing build steps: `cd rosh-lang && uv run python tools/build_showcase.py`
4. **Licence**: Rosh-BSL. All widgets must declare `# licence: Rosh-BSL`
5. **Spec before code**: check `BUILDING-ROSH.md` before implementing
6. **Commits**: `type: Short description` + `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>`
7. **Reinstall after changes**: `uv tool install --from .../rosh-lang rosh-lang --force`

## Sprite Descriptions

Procedural sprites respond to color keywords (red, blue, green, etc.) and shape keywords (spaceship, alien, ball, bullet, crystal, star). Example: `sprite ship "blue spaceship"` generates a blue spaceship-shaped pixel art.

## Sound Families

9 preset families matched by keyword: `laser`, `explosion`, `coin`, `jump`, `hit`, `powerup`, `gameover`, `click`, `win`.

## Bullet Pool Pattern

```
use bullet count 3 vy -0.5 color "#ffff00"

# Fire: set position then flag
on keydown when key == " " set bullet._x to player.x
on keydown when key == " " set bullet._y to player.y
on keydown when key == " " set bullet._fire to 1

# Collision: bullet.* matches all pool members
when collision bullet.* enemy
  set score.value to score.value + 1
end
```

## Collision Wildcard

`when collision bullet.* enemy` — the `*` matches any suffix. Works in either position.
