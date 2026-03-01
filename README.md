# Rosh

**One script, many worlds.** A plain-English language that runs on terminal, browser, and game engine.

```
print "hello world"
```

That's a complete programme. Run it targeting the terminal, it prints. Target the web, it opens a browser. Target Phaser, it renders in a game engine. Same source, different worlds.

## Quick Start

### Install

```bash
# Requires Python 3.10+ and uv
uv tool install rosh-lang
```

### Hello World

```bash
echo 'print "hello world"' > hello.rosh
rosh hello.rosh                          # terminal
rosh hello.rosh --target web --run       # browser
```

### Interactive REPL

```bash
rosh
```

### Scaffold a Project

```bash
rosh new              # choose a template interactively
rosh new game         # creates my-game.rosh
rosh new game pong    # creates pong.rosh
```

## Language Reference

### Keywords

| Keyword | Syntax | Example |
|---------|--------|---------|
| `print` | `print "text"` | `print "hello {name}"` |
| `create` | `create <kind> <name>` | `create object player` |
| `set` | `set <target> to <value>` | `set score to score + 1` |
| `get` | `get <target>` | `get player` |
| `say` | `say <text>` | `say hello everyone` |
| `when` | `when <event> [then]` ... `end` | `when click` ... `end` |
| `on` | `on <event> <action>` | `on click set count to count + 1` |
| `event` | `event <name> [fields]` | `event score_changed value` |
| `send` | `send <event> [payload]` | `send score_changed 10` |
| `if` | `if <field> <op> <value>` | `if score > 10` |
| `else` | `else` | `else` |
| `end` | `end` | `end` |
| `use` | `use <widget> [config]` | `use score label "Points"` |
| `go` | `go <scene>` | `go level2` |
| `look` | `look [target]` | `look` |
| `connect` | `connect <name> <url>` | `connect server wss://...` |
| `destroy` | `destroy <name>` | `destroy enemy` |
| `sprite` | `sprite <name> "desc"` | `sprite ship "blue spaceship"` |
| `sound` | `sound <name> "desc"` | `sound laser "laser shoot"` |
| `play` | `play <sound> [mode]` | `play laser` |
| `animate` | `animate <obj> sheet "path" frames N` | `animate player sheet "run.png" frames 4` |
| `after` | `after <seconds> send <event>` | `after 3 send timeout` |
| `create scene` | `create scene <name>` | `create scene level1` |

### Object Properties

Objects are created with `create object <name>` and configured with `set`:

| Property | Type | Description | Default |
|----------|------|-------------|---------|
| `x` | float | Horizontal position (0.0–1.0 = %, >1 = px) | none |
| `y` | float | Vertical position (0.0–1.0 = %, >1 = px) | none |
| `width` | float | Width | 0.1 |
| `height` | float | Height | 0.1 |
| `color` | string | Background color (hex or name) | #444 |
| `label` | string | Text displayed on the object | (none) |
| `sprite` | string | Sprite description for procedural generation | none |
| `visible` | int | 0 hides the object, any other value shows it | 1 |
| `vx` | float | Horizontal velocity (per second) | none |
| `vy` | float | Vertical velocity (per second) | none |

Coordinates: `0.0`–`1.0` maps to percentage of the canvas. Values `>1.0` are treated as pixels.

### Events

| Event | Payload | Trigger |
|-------|---------|---------|
| `start` | — | Programme starts |
| `update` | `dt` | Every frame (~60fps) |
| `click` | `x, y` | Canvas click |
| `click_<name>` | `x, y` | Object click |
| `keydown` | `key` | Key pressed |
| `keyup` | `key` | Key released |
| `collision` | `a, b` | Two objects overlap (edge-triggered) |
| `scene_enter` | `scene` | Entered a scene |
| `scene_exit` | `scene` | Left a scene |
| `destroy` | `name` | Object destroyed |

### Control Flow

```
# If/else
if score > 10
  print "high score!"
else
  print "keep going"
end

# Event handler block
when click
  set count to count + 1
end

# One-line reactive listener
on update set x to x + 0.01

# Conditional listener
on keydown when key == " " play laser
```

### Key-Hold State

The `_keys` dict tracks which keys are currently held. Use in `if` blocks inside `when update`:

```
when update
  if _keys.ArrowLeft == 1
    set player.x to player.x - 0.02
  end
end
```

## Widgets

Widgets are reusable `.rosh` components composed with `use`:

```
use score label "Points" max 999
use player speed 0.03
use bullet count 3 vy -0.5
```

### Available Widgets

| Widget | Type | Config | Description |
|--------|------|--------|-------------|
| `score` | .rosh | `label max min` | Score display |
| `player` | .rosh | `speed` | Keyboard-controlled ship |
| `counter` | .rosh | — | Click counter |
| `timer` | .rosh | — | Countdown timer |
| `health-bar` | .rosh | — | Health display |
| `lives` | .rosh | — | Lives counter |
| `button` | .rosh | — | Clickable button |
| `label` | .rosh | — | Text label with interpolation |
| `fps` | .rosh | — | FPS counter |
| `message` | .rosh | — | Overlay message box |
| `title-screen` | .rosh | — | Title screen |
| `coin` | .rosh | — | Collectible with sprite + sound |
| `grid` | .py | `rows cols size gap color` | Configurable cell grid |
| `enemy-grid` | .py | `rows cols size gap color` | Enemy formation with drift |
| `starfield` | .py | `count` | Randomised background stars |
| `bullet` | .py | `count vx vy color` | Pooled projectiles |
| `explosion` | .py | `count color` | Pooled explosion effects |
| `animation` | .py | `target sheet frames speed mode` | Spritesheet animation |

List widgets from the CLI:

```bash
rosh library list
rosh library info bullet
```

## Targets

| Target | Flag | Output |
|--------|------|--------|
| Terminal | `--target terminal` (default) | Print to stdout |
| Web | `--target web` | Self-contained HTML page with CSS divs |
| Phaser | `--target phaser` | Phaser 3.70.0 game with canvas rendering |

Add `--run` to auto-open the browser:

```bash
rosh game.rosh --target web --run
rosh game.rosh --target phaser --run
```

## Example: Space Shooter

```
# Score and player
use score
use player speed 0.03
sprite player.ship "green spaceship"

# Bullet pool
use bullet count 3 vy -0.5 color "#ffff00"

# Enemy
create object enemy
set enemy.x to 0.45
set enemy.y to 0.1
set enemy.width to 0.08
set enemy.height to 0.06
sprite enemy "red alien"

# Sound
sound laser "laser shoot"
sound hit "explosion hit"

# Controls: space to shoot
on keydown when key == " " set bullet._x to player.ship.x
on keydown when key == " " set bullet._y to player.ship.y
on keydown when key == " " set bullet._fire to 1
on keydown when key == " " play laser

# Collision: bullet hits enemy
when collision bullet.* enemy
  set score.value to score.value + 1
  play hit
end
```

Run: `rosh shooter.rosh --target web --run`

## CLI Reference

```
rosh                              Start REPL
rosh <file.rosh>                  Run programme (terminal)
rosh <file.rosh> --target web     Render as HTML
rosh <file.rosh> --target phaser  Render as Phaser game
rosh <file.rosh> --run            Auto-open browser
rosh new [template] [name]        Scaffold a starter programme
rosh library list                 List available widgets
rosh library info <name>          Show widget details
rosh --version                    Show version
rosh --help                       Show help
```

## Project Structure

```
rosh-lang/
  src/rosh_lang/
    model.py          # Data model (21 statement types)
    parser.py         # Text → Programme
    runtime.py        # Execute programmes, manage state
    widgets.py        # Widget loader and composition
    sprites.py        # Procedural pixel-art generator
    sounds.py         # Procedural sound generator
    sheets.py         # Spritesheet slicer
    assets.py         # Asset file resolver
    scaffolder.py     # rosh new templates
    library/          # 19 bundled widgets
    library_cli.py    # rosh library CLI
    targets/
      terminal.py     # Terminal target
      web.py          # Web target (HTML + CSS + JS)
      phaser.py       # Phaser 3 game target
      _js_runtime.py  # JS runtime (core + DOM)
      _js_runtime_phaser.py  # JS runtime (Phaser layer)
      _js_codegen.py  # AST → JavaScript compiler
    __main__.py       # CLI entry point + REPL
  examples/           # Example programmes
  tests/              # Test suite (567 tests)
  tools/              # Build tools (showcase generator)
  dist/               # Generated output (showcase.html)
```

## Licence

Rosh Business Source License (Rosh-BSL). See [LICENSE](../LICENSE).
