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

## Complete Syntax (25 Keywords)

```
print "text"                          # output ({var} interpolation)
print                                 # blank line (no arguments)
create object player                  # create object/number/string/list
set player.x to 0.5                   # assign value (arithmetic: score + 1)
set x to random                       # random 0.0–1.0 (or: random 0.1 0.9)
set x to clamp x 0.02 0.8             # constrain to [min, max]
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
else if score > 5                     # else-if chain (single end)
  print "close!"
else
  print "keep going"
end
use score label "Points"              # compose widget with config
go level2                             # scene navigation
look                                  # inspect scene
connect server wss://...              # register connection
destroy enemy                         # remove object
sprite ship "blue spaceship"          # procedural pixel art
sprite ship "https://example.com/ship.png"  # URL sprite (any image)
sound laser "laser shoot"             # procedural sound
play laser                            # play sound (once/loop/stop)
animate obj sheet "run.png" frames 4  # spritesheet animation
after 3 send timeout                  # delayed event
background "#1a1a2e"                  # canvas/scene background (colour or image)
create scene level1                   # scene definition
define fire_bullet                    # user-defined function
  set bullet._fire to 1
end
do fire_bullet                        # call a function
on keydown when key == " " do fire_bullet  # call from event
repeat 5                              # counted loop
  print "hello"
end
repeat 3 as i                         # loop with variable (1, 2, 3)
  print "Round {i}"
end
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
| `sprite` | string | Procedural sprite description or image URL |
| `visible` | int | 0 hides, any other shows (cascades to children) |
| `vx`, `vy` | float | Velocity (per second) |
| `text_color` | string | Text color (default #fff) |
| `font_size` | string | Font size (default 14px) |
| `_max_output` | int | Max console lines (excess trimmed from top) |

## Events

`start`, `update` (dt), `click` (x,y), `click_<name>` (x,y), `keydown` (key), `keyup` (key), `collision` (a,b), `scene_enter` (scene), `scene_exit` (scene), `destroy` (name), `timer_done` (name), `game_start`, `game_over`, `game_restart`.

Key-hold: `_keys.ArrowLeft == 1` inside `when update`.

## Game-Building Pattern

```
# Minimal game: player moves, shoots, scores
set _max_output to 3
use score
use lives count 3
use player speed 0.03 move x
sprite player "green spaceship"

use bullet count 3 vy -0.5 color "#ffff00"

create object enemy
set enemy.x to 0.45
set enemy.y to 0.1
set enemy.width to 0.08
set enemy.height to 0.06
sprite enemy "red alien"

sound laser "laser shoot"
sound hit "explosion hit"

on keydown when key == " " set bullet._x to player.x
on keydown when key == " " set bullet._y to player.y
on keydown when key == " " set bullet._fire to 1
on keydown when key == " " play laser

when collision bullet.* enemy
  set score.value to score.value + 1
  play hit
end

# game-over auto-fires when lives.count hits 0
when game-over
  print "GAME OVER — Score: {score.value}"
end
```

Run: `rosh game.rosh --target web --run`

## Widget Library (24 Widgets)

| Widget | Type | Config | Purpose |
|--------|------|--------|---------|
| `score` | .py | `anchor theme label x y bg text_color font_size` | Score display (HUD) |
| `player` | .py | `speed keys move x y width height color clamp_*` | Keyboard ship with auto-movement |
| `controller` | .py | `target keys touch touch_style speed move help fire fire_key fire_event clamp` | Universal input (keyboard + touch) |
| `counter` | .rosh | — | Click counter |
| `timer` | .py | `total running x y bg text_color font_size` | Auto-tick countdown (fires timer_done) |
| `health-bar` | .py | `max current x y bg text_color font_size` | Health display |
| `lives` | .py | `count auto_gameover x y bg text_color font_size` | Lives counter (auto game-over at 0) |
| `button` | .rosh | — | Clickable button |
| `label` | .py | `text x y bg text_color font_size` | Text label |
| `fps` | .py | `x y bg text_color font_size` | FPS counter |
| `message` | .py | `text x y bg text_color font_size` | Overlay message |
| `title-screen` | .py | `title subtitle bg text_color font_size` | Title screen |
| `coin` | .rosh | — | Collectible |
| `grid` | .py | `rows cols size gap color` | Cell grid |
| `enemy-grid` | .py | `rows cols size gap color` | Enemy formation |
| `starfield` | .py | `count` | Background stars |
| `bullet` | .py | `count vx vy color` | Pooled projectiles |
| `explosion` | .py | `count color` | Pooled explosions |
| `animation` | .py | `target sheet frames speed mode` | Spritesheet |
| `game-lifecycle` | .py | `title subtitle bg text_color font_size` | Title → playing → over flow |
| `ball` | .py | `x y size color vx vy walls` | Bouncing ball with wall bounce |
| `hazard` | .py | `count vx vy color width height sprite spawn_rate` | Auto-spawning obstacle pool |

Use: `use <widget> [key value ...]` — config pairs override defaults.

## Architecture

```
model.py          → 23 statement dataclasses + Programme
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

Two modes:

1. **Procedural** — description keywords generate 7×9 pixel art. Color keywords (red, blue, green, etc.) and shape keywords (spaceship, alien, ball, bullet, crystal, star). Example: `sprite ship "blue spaceship"`

2. **URL** — any `http://` or `https://` URL loads the image directly. Works on all targets (web, phaser, threejs). Example: `sprite ship "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72/1f680.png"`

URL sprites and procedural sprites can be mixed in the same program. If a URL fails to load, the object falls back to a colored rectangle.

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
