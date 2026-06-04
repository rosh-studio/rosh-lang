# Rosh

**One script, many worlds.** A plain-English language that runs on terminal, browser, and game engine.

```
print "hello world"
```

That's a complete programme. Run it targeting the terminal, it prints. Target the web, it opens a browser. Target Phaser, it renders in a game engine. Deploy it, it uploads to your Rosh account. Same source, different worlds.

## Install

Requires Python 3.10+ and [uv](https://docs.astral.sh/uv/).

```bash
# From GitHub (current pre-release)
uv tool install git+https://github.com/rosh-studio/rosh-lang

# From PyPI (after public package release)
uv tool install rosh-lang

# With Anthropic support (after public package release)
uv tool install "rosh-lang[ai]"
```

## Documentation

- Full docs: [rosh.cloud/docs](https://rosh.cloud/docs)
- Getting started: [rosh.cloud/docs/getting-started](https://rosh.cloud/docs/getting-started)
- Syntax reference: [rosh.cloud/docs/syntax](https://rosh.cloud/docs/syntax)

The documentation is public and does not require a Rosh account.

## Getting Started

### 1. Register

```bash
rosh register
```

Opens [rosh.cloud/register](https://rosh.cloud/register) in your browser. Create an account with email or GitHub. A verification link is sent to your email — click it to activate.

### 2. Log In

```bash
rosh login
```

Opens [rosh.cloud/login](https://rosh.cloud/login) in your browser. After logging in, create an API key from Settings > API Keys.

### 3. Configure

To use API-backed commands such as `rosh create` or `rosh publish`, save that key locally:

```bash
rosh config --key rosh_k1_your_key_here
```

Saves your rosh.cloud API key to `~/.rosh/config.json`. You stay configured until you run `rosh logout`.

### 4. Write and Run

```bash
echo 'print "hello world"' > hello.rosh
rosh hello.rosh                          # terminal
rosh hello.rosh --target web --run       # browser
rosh hello.rosh --target phaser --run    # Phaser game
rosh hello.rosh --target threejs --run   # Three.js 3D
```

### 5. AI-Generate a Programme

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

Rosh has two AI-backed surfaces:

- `rosh create "..."` generates a new programme from a prompt.
- the optional REPL intent planner can turn broad live-session intent into strict Rosh when ordinary parsing and deterministic natural lowering cannot handle it.

Both surfaces keep Rosh code inspectable: AI output is compiled or parsed back into normal `.rosh` before it is accepted.

### `rosh create`

`rosh create` needs a rosh.cloud API key for the language reference plus an AI engine for generation. Run `rosh config --key ...`, then configure an AI provider with environment variables:

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Anthropic (Claude) — default engine |
| `OPENAI_API_KEY` | OpenAI (GPT) |

Rosh also supports any **OpenAI-compatible API** endpoint:

```bash
export ROSH_AI_BASE_URL=https://your-provider.com/v1
export ROSH_AI_API_KEY=your_key
export ROSH_AI_MODEL=model-name
```

This covers providers like OpenRouter, Ollama, Together, Groq, and any other service that implements the OpenAI chat completions protocol.

### REPL Intent Planner

The terminal REPL can optionally fall back to an AI intent planner for broad commands such as:

```text
rosh> imagine a moonlit clearing with a campfire
```

The planner is deliberately above the parser/runtime:

1. strict Rosh runs first
2. deterministic natural phrases run next
3. only broad unknown input can call the planner
4. generated text must parse as normal Rosh before execution

It is off unless an AI provider, model, and API key are configured:

```bash
export ROSH_AI=1
export ROSH_AI_PROVIDER=anthropic
export ROSH_AI_MODEL=claude-sonnet-4-20250514
export ANTHROPIC_API_KEY=sk-ant-...
```

You can also set planner preferences inside a REPL session using ordinary Rosh state:

```rosh
set _ai.enabled to true
set _ai.provider to anthropic
set _ai.model to claude-sonnet-4-20250514
```

Keep API keys in environment variables rather than `.rosh` files. The planner
currently runs in the terminal REPL only. The portal's authenticated browser
`prompt` command is a separate AI generation surface; the shared homepage
world continues to use its deterministic command pipeline.

### Trusted Native Components

Bundled and locally installed `.py` component factories are native extensions:
loading one executes trusted Python with the permissions of the `rosh` process.
Do not install or generate Python factories from untrusted input. Native `.rosh`
components are the safe, inspectable default for AI planning and composition.

## Interactive REPL

```bash
rosh
rosh -c 'create object player'
rosh -i examples/hello.rosh
```

The terminal REPL accepts a small amount of interactive sugar and lowers it into normal Rosh before execution. That keeps the language itself strict while making the shell more forgiving. Files and `rosh -c` use strict Rosh syntax; these natural phrases are for live REPL sessions.

Examples:

```text
rosh> create a big red ball
rosh> make it blue
rosh> make it smaller
rosh> move it left
rosh> put the ball at 40 60
rosh> examine ball
```

Current REPL-only conveniences include:
- natural create phrases like `create a big red ball`
- pronoun-based follow-ups like `make it blue`
- simple relative size edits like `make it smaller` / `make it bigger`
- simple movement phrases like `move it left` and `put the ball at 40 60`
- aliases like `examine`, `inspect`, `x`, `ls`, and `remove`
- typo suggestions for misspelled commands
- tab completion, history, and multiline blocks for `when`, `define`, and `repeat`
- optional AI intent planning for broad unknown commands when `ROSH_AI`, provider, model, and API key are configured

## VS Code

The repository includes the official Rosh VS Code extension in
[`editor/vscode/`](editor/vscode/). It provides syntax highlighting, folding,
bracket matching, and snippets for current Rosh syntax.

Install it from a source checkout:

```bash
cd editor/vscode
./install.sh
```

Reload VS Code after installation.

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
| `sprite` | string | Sprite description or image URL | none |
| `rotation` | float | Rotation in degrees (0=up, clockwise) | 0 |
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
| `game_over` | — | Lives reached zero; `game-lifecycle` enters its game-over phase |
| `game_restart` | — | Game restarted (via game-lifecycle widget) |

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

Native `.rosh` widgets declare defaults in their header and read them through
instance-owned `config.*` state:

```rosh
# widget: label
# config: text=Hello x=0.5

create object display
set display.label to config.text
set display.x to config.x
```

`use label as title text "Welcome home"` binds `title.config.text` before the
component runs. Named instances therefore receive independent config.

### Available Widgets (22)

| Widget | Type | Config | Description |
|--------|------|--------|-------------|
| `score` | .py | `anchor theme label x y bg text_color font_size` | Score display (HUD) |
| `player` | .py | `speed keys move x y width height color clamp_x_min clamp_x_max` | Keyboard-controlled ship |
| `controller` | .py | `target keys touch touch_style speed move help fire fire_key fire_event clamp` | Universal input (keyboard + touch) |
| `counter` | .rosh | — | Click counter |
| `timer` | .py | `total running x y bg text_color font_size` | Auto-tick countdown (fires timer_done) |
| `health-bar` | .py | `max current x y bg text_color font_size` | Health display |
| `lives` | .py | `count auto_gameover x y bg text_color font_size` | Lives counter |
| `button` | .rosh | — | Clickable button |
| `label` | .rosh | `text x y bg text_color font_size` | Text label with interpolation |
| `fps` | .py | `x y bg text_color font_size` | FPS counter |
| `message` | .rosh | `text x y bg text_color font_size` | Overlay message box |
| `title-screen` | .rosh | `title subtitle bg text_color font_size` | Title screen |
| `coin` | .rosh | — | Collectible with sprite + sound |
| `grid` | .py | `rows cols size gap color` | Configurable cell grid |
| `enemy-grid` | .py | `rows cols size gap color` | Enemy formation with drift |
| `starfield` | .py | `count` | Randomised background stars |
| `bullet` | .py | `count vx vy color` | Pooled projectiles |
| `explosion` | .py | `count color` | Pooled explosion effects |
| `animation` | .py | `target sheet frames speed mode` | Spritesheet animation |
| `game-lifecycle` | .rosh | `title subtitle bg text_color font_size` | Title -> playing -> over flow |
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
| Scratch | `--target scratch` | Scratch 3 `.sb3` export (open in Scratch or TurboWarp) |

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
rosh <file.rosh> --target web      Render as HTML
rosh <file.rosh> --target phaser   Render as Phaser game
rosh <file.rosh> --target threejs  Render as Three.js 3D scene
rosh <file.rosh> --target scratch  Export as Scratch .sb3
rosh <file.rosh> --run            Auto-open browser
rosh new [template] [name]        Scaffold a starter programme
rosh library list                 List available widgets
rosh library info <name>          Show widget details
rosh register                     Open registration page
rosh login                        Open login page and API-key instructions
rosh logout                       Clear local API key
rosh config --key KEY             Save rosh.cloud API key
rosh create "description"         AI-generate a programme
rosh publish file.rosh            Upload to rosh.cloud
rosh --version                    Show version
rosh --help                       Show help
```

## MCP Server

Rosh has a separate MCP server package for AI tools that can compile, publish, browse, and moderate programmes through the rosh.cloud API.

Install and run it with `uvx`:

```bash
ROSH_API_KEY=rosh_k1_your_key_here uvx rosh-mcp
```

Example MCP config:

```json
{
  "mcpServers": {
    "rosh": {
      "command": "uvx",
      "args": ["rosh-mcp"],
      "env": {
        "ROSH_API_KEY": "rosh_k1_your_key_here"
      }
    }
  }
}
```

Canonical MCP package: [github.com/rosh-studio/rosh-mcp](https://github.com/rosh-studio/rosh-mcp)

## Project Structure

```
rosh-lang/
  src/rosh_lang/
    core/
      model.py        # Data model (32 statement types)
      parser.py       # Text -> Programme
      runtime.py      # Execute programmes, manage state
      widgets.py      # Widget loader and composition
    cli/
      cloud.py        # rosh.cloud commands
      scaffolder.py   # rosh new templates
      library_cli.py  # rosh library CLI
    media/
      assets.py       # Asset file resolver
      sprites.py      # Procedural pixel-art generator
      sounds.py       # Procedural sound generator
      sheets.py       # Spritesheet slicer
      assets/         # Bundled media assets
    library/          # 22 bundled widgets
    targets/
      terminal.py     # Terminal target
      web.py          # Web target (HTML + CSS + JS)
      phaser.py       # Phaser 3 game target
      _js_runtime.py  # JS runtime (core + DOM)
      _js_runtime_phaser.py  # JS runtime (Phaser layer)
      _js_codegen.py  # AST -> JavaScript compiler
      threejs.py      # Three.js 3D target
      _js_runtime_threejs.py  # JS runtime (Three.js layer)
      scratch.py      # Scratch 3 .sb3 export target
    repl/             # Interactive shell kernel and natural command lowering
    intent/           # Optional AI-backed intent planning
    model.py          # Compatibility shim for rosh_lang.core.model
    parser.py         # Compatibility shim for rosh_lang.core.parser
    __main__.py       # CLI entry point + REPL
  examples/           # Example programmes
  tests/              # Test suite (1,197 tests)
  editor/vscode/      # Official VS Code language extension
  tools/              # Build tools (showcase generator)
  dist/               # Generated output (showcase.html)
```

## Licence

**[Rosh Business Source License v0.2 (Rosh-BSL)](LICENSE)**  
Copyright 2026 Roger Dubar / Rosh Studio

Free for personal use, education, open-source projects, and non-commercial research.
Commercial use (SaaS, products, paid services) requires a separate licence — contact
[rosh.cloud](https://rosh.cloud) or read the [LICENSE](LICENSE) file for full terms.

Converts automatically to **Apache 2.0 on 2029-05-02**.
