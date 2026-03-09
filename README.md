# Rosh

**One script, many worlds.** A plain-English language that runs on terminal, browser, and game engine.

```
print "hello world"
```

That's a complete programme. Run it targeting the terminal, it prints. Target the web, it opens a browser. Target Phaser, it renders in a game engine. Deploy it, it uploads to your Rosh account. Same source, different worlds.

## Install

Requires Python 3.10+ and [uv](https://docs.astral.sh/uv/).

```bash
# From PyPI (when published)
uv tool install rosh-lang

# From GitHub (available now)
uv tool install git+https://github.com/roshstudio/rosh-lang

# With AI generation support
uv tool install "rosh-lang[ai]"
```

## Getting Started

### 1. Register (*planned*)

```bash
rosh register
```

Opens [rosh.cloud/register](https://rosh.cloud/register) in your browser. Create an account with email or GitHub. A verification link is sent to your email — click it to activate.

### 2. Log In (*planned*)

```bash
rosh login
```

Opens [rosh.cloud/login](https://rosh.cloud/login) in your browser. Once authenticated, a session token is saved locally to `~/.rosh/config.json`. You stay logged in until you run `rosh logout`.

### 3. Configure

To deploy to `rosh.cloud` from your command line, you must generate an API key and register it as follows:

```bash
rosh config --key rosh_k1_your_key_here
```

Saves your rosh.cloud API key to `~/.rosh/config.json`.

### 4. Write and Run

```bash
echo 'print "hello world"' > hello.rosh
rosh hello.rosh                          # terminal
rosh hello.rosh --target web --run       # browser
rosh hello.rosh --target phaser --run    # Phaser game
rosh hello.rosh --target threejs --run   # Three.js 3D
```

### 5. AI-Generate a Programme (*planned*)

```bash
rosh create "space invaders with power-ups"
rosh create "space invaders with power-ups" --target phaser --publish
```

Fetches the Rosh language reference from the API, builds a prompt, sends it to an AI engine, compiles to verify, and optionally publishes to rosh.cloud.

### 6. Publish

```bash
rosh publish my-game.rosh --target web --title "My Game"
```

Compiles locally via the API and uploads to rosh.cloud as a published programme.

## AI Engine Configuration

`rosh create` needs an AI engine to generate programmes. Configure one with environment variables:

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Anthropic (Claude) — default engine |
| `OPENAI_API_KEY` | OpenAI (GPT) |

Rosh also supports any **OpenAI-compatible API** endpoint (*planned*):

```bash
export ROSH_AI_BASE_URL=https://your-provider.com/v1
export ROSH_AI_API_KEY=your_key
export ROSH_AI_MODEL=model-name
```

This covers providers like OpenRouter, Ollama, Together, Groq, and any other service that implements the OpenAI chat completions protocol.

## Interactive REPL

```bash
rosh
```

## Scaffold a Project

```bash
rosh new              # choose a template interactively
rosh new game         # creates my-game.rosh
rosh new game pong    # creates pong.rosh
```

## Language Reference

### Keywords

| Keyword | Syntax | Example |
|---------|--------|---------|
| `print` | `print "text"` or bare `print` | `print "hello {name}"` / `print` (blank line) |
| `create` | `create <kind> <name>` | `create object player` |
| `set` | `set <target> to <value>` | `set score to score + 1` / `set x to random` / `set x to clamp x 0 1` |
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
| `background` | `background "<colour_or_image>"` | `background "#0a0a1e"` |
| `define` | `define <name>` ... `end` | `define fire_bullet` ... `end` |
| `do` | `do <name>` | `do fire_bullet` |
| `repeat` | `repeat <count> [as <var>]` ... `end` | `repeat 5 as i` ... `end` |
| `create scene` | `create scene <name>` | `create scene level1` |

### Object Properties

Objects are created with `create object <name>` and configured with `set`:

| Property | Type | Description | Default |
|----------|------|-------------|---------|
| `x` | float | Horizontal position (0.0-1.0 = %, >1 = px) | none |
| `y` | float | Vertical position (0.0-1.0 = %, >1 = px) | none |
| `width` | float | Width | 0.1 |
| `height` | float | Height | 0.1 |
| `color` | string | Background color (hex or name) | #444 |
| `label` | string | Text displayed on the object | (none) |
| `sprite` | string | Sprite description for procedural generation | none |
| `visible` | int | 0 hides the object, any other shows | 1 |
| `vx` | float | Horizontal velocity (per second) | none |
| `vy` | float | Vertical velocity (per second) | none |
| `text_color` | string | Text color for labels | #fff |
| `font_size` | string | Font size for labels | 14px |
| `_max_output` | int | Max console lines (excess trimmed from top) | unlimited |

Coordinates: `0.0`-`1.0` maps to percentage of the canvas. Values `>1.0` are treated as pixels.

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
| `timer_done` | `name` | Timer widget finished |
| `game_start` | — | Game started (via game-lifecycle widget) |
| `game_over` | — | Game over (via lives widget at 0) |
| `game_restart` | — | Game restarted |

### Control Flow

```
# If/else/else-if (single end for chains)
if score > 10
  print "high score!"
else if score > 5
  print "getting close!"
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

# User-defined functions
define fire_bullet
  set bullet._fire to 1
end
do fire_bullet

# Counted loop
repeat 5 as i
  print "Round {i}"
end
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

Widgets are reusable components composed with `use`:

```
use score x 0.5 text_color "#ffcc00" font_size "20px"
use player speed 0.03
use bullet count 3 vy -0.5
use timer total 30 running 1
use ball walls top-sides
use hazard count 5 vy 0.3 spawn_rate 0.8
```

### Available Widgets (25)

| Widget | Type | Config | Description |
|--------|------|--------|-------------|
| `score` | .py | `anchor theme label x y bg text_color font_size` | Score display (HUD) |
| `player` | .py | `speed keys move x y width height color clamp_x_min clamp_x_max` | Keyboard-controlled ship |
| `controller` | .py | `target keys touch touch_style speed move help fire fire_key fire_event clamp` | Universal input (keyboard + touch) |
| `counter` | .rosh | — | Click counter |
| `timer` | .py | `total running x y bg text_color font_size` | Auto-tick countdown (fires timer_done) |
| `health-bar` | .py | `max current x y bg text_color font_size` | Health display |
| `lives` | .py | `count x y bg text_color font_size` | Lives counter |
| `button` | .rosh | — | Clickable button |
| `label` | .py | `text x y bg text_color font_size` | Text label with interpolation |
| `fps` | .py | `x y bg text_color font_size` | FPS counter |
| `message` | .py | `text x y bg text_color font_size` | Overlay message box |
| `title-screen` | .py | `title subtitle bg text_color font_size` | Title screen |
| `coin` | .rosh | — | Collectible with sprite + sound |
| `grid` | .py | `rows cols size gap color` | Configurable cell grid |
| `enemy-grid` | .py | `rows cols size gap color` | Enemy formation with drift |
| `starfield` | .py | `count` | Randomised background stars |
| `bullet` | .py | `count vx vy color` | Pooled projectiles |
| `explosion` | .py | `count color` | Pooled explosion effects |
| `animation` | .py | `target sheet frames speed mode` | Spritesheet animation |
| `game-lifecycle` | .py | `title subtitle bg text_color font_size` | Title -> playing -> over flow |
| `ball` | .py | `x y size color vx vy walls` | Bouncing ball with wall bounce |
| `hazard` | .py | `count vx vy color width height sprite spawn_rate` | Auto-spawning obstacle pool |

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
| Three.js | `--target threejs` | Three.js 3D scene with orbit camera and lighting |

Add `--run` to auto-open the browser:

```bash
rosh game.rosh --target web --run
rosh game.rosh --target phaser --run
```

## Example: Space Shooter

```
# Score and player (auto-movement + clamp)
use score
use lives count 3
use player speed 0.03 move x
sprite player "green spaceship"

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
on keydown when key == " " set bullet._x to player.x
on keydown when key == " " set bullet._y to player.y
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
rosh register                     Open registration page (planned)
rosh login                        Authenticate with rosh.cloud (planned)
rosh logout                       Clear local session (planned)
rosh config --key KEY             Save rosh.cloud API key
rosh create "description"         AI-generate a programme (planned)
rosh publish file.rosh            Upload to rosh.cloud
rosh --version                    Show version
rosh --help                       Show help
```

## MCP Server (AI Tool Integration)

Rosh includes an MCP (Model Context Protocol) server that lets AI tools like Claude Code, Cursor, and Windsurf compile, publish, and manage Rosh programs directly.

### Prerequisites

1. A [rosh.cloud](https://rosh.cloud) account with an API key
2. Python 3.10+ and [uv](https://docs.astral.sh/uv/)

### Setup

**1. Get the MCP server script**

Clone the repo (if you haven't already):

```bash
git clone https://github.com/roshstudio/rosh-lang.git
```

The server script is at `rosh-dev/mcp/rosh_mcp.py`.

**2. Get your API key**

Log in to [rosh.cloud](https://rosh.cloud), go to your profile, and generate an API key.

**3. Configure your AI tool**

Add the following to your tool's MCP config:

**Claude Code** (`<project>/.claude/mcp.json`):

```json
{
  "mcpServers": {
    "rosh": {
      "command": "uv",
      "args": [
        "run", "--with", "mcp[cli]", "--with", "httpx",
        "python", "/path/to/rosh-dev/mcp/rosh_mcp.py"
      ],
      "env": {
        "ROSH_API_KEY": "rosh_k1_your_key_here"
      }
    }
  }
}
```

**Cursor / Other MCP clients** (check your tool's MCP config location):

```json
{
  "mcpServers": {
    "rosh": {
      "command": "python",
      "args": ["/path/to/rosh-dev/mcp/rosh_mcp.py"],
      "env": {
        "ROSH_API_KEY": "rosh_k1_your_key_here",
        "ROSH_API_BASE": "https://rosh.cloud"
      }
    }
  }
}
```

For Cursor and similar tools, install the dependencies first: `uv pip install "mcp[cli]" httpx` (or `pip install "mcp[cli]" httpx`)

**4. Restart your AI tool** to pick up the new MCP server.

### Available Tools

| Tool | Description |
|------|-------------|
| `rosh_docs` | Get the full Rosh language reference |
| `rosh_compile` | Compile Rosh code without publishing |
| `rosh_publish` | Compile and publish a program to rosh.cloud |
| `rosh_list_programs` | List your published programs |
| `rosh_get_program` | Get details of a specific program |
| `rosh_update_program` | Update an existing program |
| `rosh_delete_program` | Delete a program |
| `rosh_hide_program` | Hide a program from public view |
| `rosh_show_program` | Make a hidden program visible again |

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ROSH_API_KEY` | Yes | Your rosh.cloud API key |
| `ROSH_API_BASE` | No | API base URL (default: `https://rosh.cloud`) |

The server also reads from a `.env` file in the project root if present.

## Project Structure

```
rosh-lang/
  src/rosh_lang/
    model.py          # Data model (23 statement types)
    parser.py         # Text -> Programme
    runtime.py        # Execute programmes, manage state
    widgets.py        # Widget loader and composition
    sprites.py        # Procedural pixel-art generator
    sounds.py         # Procedural sound generator
    sheets.py         # Spritesheet slicer
    assets.py         # Asset file resolver
    scaffolder.py     # rosh new templates
    library/          # 25 bundled widgets
    library_cli.py    # rosh library CLI
    targets/
      terminal.py     # Terminal target
      web.py          # Web target (HTML + CSS + JS)
      phaser.py       # Phaser 3 game target
      _js_runtime.py  # JS runtime (core + DOM)
      _js_runtime_phaser.py  # JS runtime (Phaser layer)
      _js_codegen.py  # AST -> JavaScript compiler
      threejs.py      # Three.js 3D target
      _js_runtime_threejs.py  # JS runtime (Three.js layer)
    __main__.py       # CLI entry point + REPL
  examples/           # Example programmes
  tests/              # Test suite (747 tests)
  tools/              # Build tools (showcase generator)
  dist/               # Generated output (showcase.html)
```

## Licence

Rosh Source-Available Licence (Rosh-SAL). Free to use, modify, and distribute for any purpose. Forking to create a competing language is not permitted. Similar in spirit to the [Functional Source License (FSL)](https://fsl.software/).

See [LICENSE](LICENSE).
