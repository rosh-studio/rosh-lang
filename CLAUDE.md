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
cd rosh-lang && uv run pytest -q       # expect the full suite to pass
```

After code changes, reinstall:
```bash
uv tool install --from /path/to/rosh-lang rosh-lang --force
```

Full syntax reference (all statement forms, object properties): see
`rosh-portal/docs/reference/syntax.md` (also served live at rosh.cloud/docs/syntax) — this is the
canonical spec Rule 5 below points to; don't let this file's copy drift out of sync with it, so
it's not duplicated here.

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

# game_over auto-fires when lives.count hits 0
when game_over
  print "GAME OVER — Score: {score.value}"
end
```

Run: `rosh game.rosh --target web --run`

Widget list and config options: see `rosh-portal/docs/reference/syntax.md` (same reasoning as
above — don't duplicate it here). Repo layout (`core/`, `media/`, `cli/`, `library/`, `targets/`)
is a plain `ls`/`find` away and not reproduced here either.

## Rules

1. **Don't add keywords** unless they are documented in the public syntax reference or agreed in an issue first
2. **Test after every change**: `cd rosh-lang && uv run pytest -q`
3. **Rebuild showcase** after completing build steps: `cd rosh-lang && uv run python tools/build_showcase.py`
4. **Licence**: MIT. All widgets must declare `# licence: MIT`
5. **Spec before code**: check the README and https://rosh.cloud/docs/syntax before implementing language behavior
6. **Commits**: use `type: Short description`, with types like `feat`, `fix`, `docs`, `test`, `refactor`, or `chore`
7. **Reinstall after changes**: `uv tool install --from .../rosh-lang rosh-lang --force`

## Sprite Descriptions

Two modes:

1. **Procedural** — description keywords generate 7×9 pixel art. Color keywords (red, blue, green, etc.) and shape keywords (spaceship, alien, ball, bullet, crystal, star). Example: `sprite ship "blue spaceship"`

2. **URL** — any `http://` or `https://` URL loads the image directly. Works on all targets (web, phaser, threejs). Example: `sprite ship "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72/1f680.png"`

URL sprites and procedural sprites can be mixed in the same program. If a URL fails to load, the object falls back to a colored rectangle.

**Rendering differences:**
- Procedural sprites: fill the entire width×height box, pixelated upscaling (crisp edges)
- URL sprites: `contain` fit (preserves aspect ratio), smooth rendering
- `rotation` property: degrees, 0=up, clockwise positive (all targets)

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
