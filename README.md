# 🤖 Rosh Programming Language

**v0.1.10** - A spoken-language-first, stack-based, AI-native programming language for games and interactive storytelling.

> 🤖 **Rosh** - Programming that sounds like talking to a person!

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

## Overview

Rosh is designed to be:
- **Spoken-friendly**: Optimized for dictation with minimal punctuation
- **Stack-based**: Powerful compositional semantics
- **Format-flexible**: JSON, TOML, and TOON support for state serialization
- **AI-native**: First-class `prompt` primitive for AI integration
- **Event-driven**: Reactive programming with `when/trigger` for game logic
- **MUD-focused**: Built-in primitives for interactive worlds & storytelling

## Installation

```bash
# Install uv (modern Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and install Rosh
git clone https://github.com/rdubar/rosh.git
cd rosh
uv tool install .

# Run it!
rosh examples/hello.rosh
```

**Upgrade:** `cd rosh && git pull && uv tool install --reinstall .`

**Developers:** See [QUICK-START.md](QUICK-START.md) for `uv sync` setup or [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for details.

## ⚠️ Security Note

**Rosh is for single-user, local development.** Not ready for production or multi-user use:

- **Remote imports are trust-based** - No hash/signature verification yet. Only import from sources you trust.
- **Full filesystem access** - Code runs with your user permissions
- **AI code requires confirmation** - But runs unrestricted after approval

See [docs/proposals/SECURITY-PLAN.md](docs/proposals/SECURITY-PLAN.md) for details and [docs/EVAL-SAFETY.md](docs/EVAL-SAFETY.md) for why this is safe for single-user.

## Quick Start

```bash
# Run a Rosh program
rosh examples/hello.rosh

# Execute inline code
rosh -c "print 'Hello, World!'"

# Multi-line inline code
rosh -c "create x to 42
get x
dup
multiply
print"

# Start interactive REPL
rosh

# Run script then enter REPL with state preserved
rosh -i examples/hello.rosh

# Check version
rosh --version
```

### REPL Example
```rosh
rosh> set x to 42
rosh> x                          # Type variable name to see value!
42

rosh> set result to call double 15    # Assign function results
rosh> result
30

rosh> get x
rosh> get x
rosh> multiply
rosh> print stack                # Pop and print from stack
1764
rosh> exit
```

## AI Integration

Rosh is **AI-native** with three revolutionary features:

### 1. AI Code Generation (`prompt exec`)
**The killer feature** - AI writes code with your approval:

```bash
rosh -c 'prompt exec "Create a player with health 100 and name Hero"'
# → AI generates valid Rosh code
# → Shows you the code for review
# → Asks for confirmation before executing
# → You can save without executing for later review
```

### 2. AI Error Recovery
Get helpful suggestions when you make mistakes:

```rosh
rosh> crate number x as 42  # Typo!
Error: Unknown command 'crate'

💡 AI Suggestion: You meant to use 'create' instead of 'crate'.
   Try: create number x as 42
```

### 3. Text Generation (`prompt`)
```rosh
prompt "Explain this code" using player into explanation
```

**Quick Setup:**
```bash
# 1. Install AI support
pip install -e ".[ai]"

# 2. Set API key
export OPENAI_API_KEY="sk-your-key-here"

# 3. Try it!
rosh -c 'prompt exec "Create a game character"'
```

**See full guide:** [AI_SETUP.md](AI_SETUP.md)

## Learning Rosh

**Start here:** Run the comprehensive Rosh manual:
```bash
rosh ROSH-MANUAL.rosh
```

This executable tutorial demonstrates **ALL working features** of Rosh with hands-on examples!

## Project Status

**Current Version:** v0.1.10 (Transpiler Demo & Polish)
**Interpreter:** v0.0.9 (TOON format support)

> **For detailed roadmap:** See `../rosh-dev/ROADMAP.md` (private planning repo)

### Recent Releases

**v0.0.9 - TOON Format Support** ✅ (2025-12-14)
- ✅ Full TOON encoder and decoder implementation
- ✅ Save and load `.toon` files (40% fewer tokens than JSON!)
- ✅ Round-trip support for all Rosh types
- ✅ 37 comprehensive unit tests (encoder, decoder, round-trip, file ops)
- JSON remains default - TOON is opt-in via explicit `.toon` extension

**v0.0.8 - Infrastructure & Tooling** 🔄 (In Progress)
- ✅ TOML support (`--toml` flag, import `.toml` files)
- ✅ Test mode for CI/CD (`--test`, `--test-input` flags)
- ✅ Program metadata system (`meta` keyword with UUID/checksum generation)
- ✅ AI ticket/review/documentation system
- ✅ Development planning reorganization (ROADMAP, tickets moved to private repo)

**v0.0.7 - Event System** ✅ (2025-12-14)
- ✅ Event-driven programming (`when <event> then ... end`)
- ✅ Trigger events with parameters (`trigger player_damaged with 15`)
- ✅ Lexical scoping for event handlers
- ✅ Event loop stdlib helpers (`every()`, `stop_loop()`)
- ✅ 21 comprehensive event tests

**v0.0.6 - Quality of Life** ✅ (2025-12-13)
- ✅ String interpolation (`"Hello {name}, you have {score} points!"`)
- ✅ User input command (`input username prompt "Enter name:"`)
- ✅ else if conditionals
- ✅ NOT in compound expressions
- ✅ Multiline comments (`"""` or `###`)
- ✅ Type checking functions
- ✅ List slicing
- ✅ Interactive mode (`-i` flag)

**v0.1.5 - Phaser Transpiler MVP** ✅ (2025-12-14)
- ✅ JavaScript/Phaser transpiler (`rosh build --target phaser`)
- ✅ Browser deployment (zero-install, runs in any browser)
- ✅ Objects → Phaser colored rectangles
- ✅ Print statements → console.log with string interpolation
- ✅ Fail-fast error handling for unsupported features
- ✅ 22 comprehensive tests (15 unit + 7 integration)

**Example:**
```bash
# Write Rosh code
create object goblin
    set x to 100
    set y to 200
end

# Transpile to Phaser
rosh build game.rosh --target phaser --output dist/

# Open in browser → See colored rectangle at (100, 200)!
```

**v0.1.6 - Input + Events in Phaser** ✅ (2025-12-14)
- ✅ Event system (`when/trigger`) in Phaser transpiler
- ✅ Object inheritance (`create object hero from player`)
- ✅ Player auto-controls (arrow keys + space = automatic movement & fire)
- ✅ Smart defaults (lives, score, speed properties)
- ✅ Auto-generated HUD (lives/score display)
- ✅ Property mutations in event handlers
- ✅ Trigger statements with parameters
- ✅ Special properties (fixed, speed, etc.)
- ✅ 24 comprehensive tests (15 unit + 9 v0.1.6 features)

**Example:**
```rosh
# Just this code gives you a fully controllable game!
create object hero from player
    set x to 400
    set y to 300
end

# Auto-generated:
# - Arrow key movement (uses speed property)
# - Space bar fires
# - Lives/score HUD display
# - Keyboard event system
```

**v0.1.7 - Sprite System** ✅ (2025-12-14)
- ✅ Sprite/image support in Phaser transpiler (`set sprite to "hero.png"`)
- ✅ Automatic asset preloading (Phaser `preload()` method generation)
- ✅ Graceful fallback to colored rectangles when sprites missing
- ✅ Smart asset copying (`--copy-assets` flag - only copies used sprites)
- ✅ Python web server workflow (always shown to avoid CORS issues)
- ✅ Comprehensive documentation (limitations, troubleshooting, examples)
- ✅ 6300+ free game assets included (selection of Kenney's collection)
- ✅ 32 comprehensive tests (24 existing + 8 sprite tests)

**Example:**
```bash
# Build game with automatic asset copying
rosh build examples/games/sprite-demo.rosh --target phaser --output dist/ --copy-assets

# Output shows:
#   📦 Copied: hero.png
#   📦 Copied: enemy.png
#   📦 Copied: coin.png
#   ✅ Copied 3 sprite(s) to dist/assets
#   🎮 To run with sprites:
#      cd dist/ && python3 -m http.server 8000
#      Then open: http://localhost:8000

# Run and see real game graphics instead of colored rectangles!
```

**Impact:** Transforms Rosh from "toy examples with colored boxes" to "real games with professional graphics."

**v0.1.8 - Pygame Transpiler** ✅ (2025-12-14)
- ✅ Native desktop game output (`rosh build --target pygame`)
- ✅ Zero browser dependency - runs with `python3 game.py`
- ✅ Full parity with Phaser: objects, text, key events, update loops
- ✅ Grid-based collision support (coordinate math)
- ✅ Input fires once per press (matches Phaser JustDown)

**v0.1.9 - Sound Support** ✅ (2025-12-15)
- ✅ Sound effects: `play sound "laser.wav"`
- ✅ Background music: `play music "theme.ogg"` / `stop music`
- ✅ Automatic asset caching and preloading
- ✅ Works in both Phaser (Web Audio) and Pygame (mixer)

**v0.1.10 - Demo & Polish** ✅ (2025-12-15)
- ✅ Dynamic `font_size` animation support
- ✅ Pygame CLI integration (`rosh build --target pygame`)
- ✅ Rosh intro demo (works in both Phaser and Pygame)
- ✅ Asset reorganization (distributed sprites/sounds)

**Example (works in both targets!):**
```rosh
create object logo
    set text to "rosh"
    set font_size to 8
    set color to "cyan"
end

when update then
    if logo.font_size is below 96 then
        set logo.font_size to logo.font_size plus 2
    end
end
```

### What's Next

**v0.2.0 - Voice Demo** (Planned)
- Voice input → AI → playable game
- AI-generated sprites (DALL-E integration)
- Demo video

**Key Documents:**
- `ROSH-MANUAL.rosh` - THE comprehensive Rosh manual (start here!)
- `CHANGELOG.md` - Version history and release notes
- `QUICK-START.md` - Fast installation and basic usage
- `docs/ARCHITECTURE.md` - System architecture and design decisions
- `docs/DEVELOPMENT.md` - Development setup and workflow
- `docs/CONTRIBUTING.md` - Contribution guidelines
- `docs/AI_SETUP.md` - AI integration guide
- `docs/EVAL-SAFETY.md` - Understanding eval in single-user vs multi-user

**For strategic planning:** See `../rosh-dev/ROADMAP.md` (private repo)

## Directory Structure

```
rosh-lang/
├── ROSH-MANUAL.rosh    # ⭐ THE comprehensive Rosh manual (START HERE!)
├── README.md           # This file (quick start)
├── CHANGELOG.md        # Version history and release notes
├── QUICK-START.md      # Fast installation guide
├── LICENSE             # MIT License
├── src/rosh/           # Python interpreter implementation
│   ├── lexer.py        # Tokenization
│   ├── parser.py       # AST generation
│   ├── interpreter.py  # Execution engine
│   ├── ast_nodes.py    # AST node definitions
│   └── cli.py          # Command-line interface
├── examples/           # Example .rosh programs
│   ├── games/          # Phaser browser games (sprite-demo, mvp-demo, etc.)
│   ├── mud/            # Interactive MUD examples
│   └── basics/         # Core language features
├── stdlib/             # Standard library
│   └── mud.rosh        # MUD templates (rooms, NPCs, items)
├── docs/               # Documentation
│   ├── proposals/      # Vision documents for future features
│   └── archive/        # Historical documents
├── editor/             # Editor extensions
│   └── vscode/         # VS Code extension
├── spec/               # Language specification
├── tests/              # Test suite
└── scratch/            # Development scratch (gitignored)
```

## Features

- **AI-native programming**: `prompt` command with OpenAI/Anthropic integration
- **Browser game development**: Phaser 3 transpiler with sprite support (`rosh build --target phaser`)
- **Event-driven**: Reactive programming with `when/trigger` for game logic
- **Multi-format**: JSON, TOML, and TOON support for state serialization
- **Testing support**: `--test` mode for CI/CD with mock inputs
- **Program metadata**: Auto-generated UUIDs and checksums with `meta` keyword
- **Context-aware help**: Self-documenting with `help` command
- **Stack-based operations**: `get`, `add`, `multiply`, `dup`, `swap`, `drop`
- **Object system**: Create and manipulate objects with properties
- **String interpolation**: `"Hello {name}, you have {score} points!"`
- **Control flow**: `if`/`else if`/`else` with natural language comparisons
- **Functions**: Define and call custom functions with return values
- **Interactive REPL**: Persistent state, history, tab completion, and aliases
- **VS Code support**: Syntax highlighting, snippets, and code folding

## VS Code Extension

Get full IDE support with syntax highlighting and snippets:

```bash
cd editor/vscode && ./install.sh
```

Then reload VS Code (Cmd+Shift+P → "Reload Window") and open any `.rosh` file!

**Features:**
- Syntax highlighting for all keywords and operators
- Code snippets (type `object`, `if`, `function` + Tab)
- Auto-closing quotes and brackets
- Comment toggling (Cmd+/)
- Code folding

## Development

```bash
# Install dependencies
pip install -e .

# Run all examples
for file in examples/*.rosh; do rosh "$file"; done

# Run test suite
python tests/run_tests.py

# Scratch folder for temporary test files
# (automatically gitignored)
touch scratch/my-test.rosh
```

## License

Rosh is released under the [MIT License](LICENSE).

**What this means:**
- ✅ Free for commercial use
- ✅ No usage fees ever
- ✅ Modify and distribute freely
- ✅ Private use allowed
- ✅ Patent grant included

**Trademark Notice:**
"Rosh" and the Rosh logo are trademarks of the Rosh Project. You can use the name to refer to this project, but not in ways that suggest official endorsement without permission. Similar to how Python, Rust, and other open-source projects protect their brands.

Type `license` in the REPL to view the full license and trademark information, or see [LICENSE](LICENSE) for details.
