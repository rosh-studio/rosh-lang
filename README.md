# 🤖 Rosh Programming Language

**v0.0.8** - A spoken-language-first, stack-based, AI-native programming language for interactive storytelling and MUDs.

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

## Project Status & Roadmap

**Current Version:** v0.0.8 (In Progress)
**Latest Complete:** v0.0.9 TOON encoder (2025-12-14)

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
- ✅ BACKLOG.md for deferred features

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

### What's Next

**v0.1.0 - Transpiler Foundation** (Planned Q2-Q3 2026)
- JavaScript/Phaser transpiler
- Browser deployment (zero install)
- Same code: terminal ASCII + browser graphics

**v0.2.0 - Voice Demo** (Planned Q3 2026)
- Voice input → AI → playable game
- Phaser transpiler MVP
- Demo video

See **[ROADMAP.md](ROADMAP.md)** for detailed technical milestones and **[BACKLOG.md](BACKLOG.md)** for deferred features.

**Key Documents:**
- `ROSH-MANUAL.rosh` - THE comprehensive Rosh manual (start here!)
- `ROADMAP.md` - Technical milestones and releases
- `BACKLOG.md` - Deferred features and future work
- `docs/POLICIES.md` - Project governance, standards, workflows
- `docs/DEVELOPMENT.md` - Development setup and workflow
- `docs/AI_SETUP.md` - AI integration guide
- `docs/EVAL-SAFETY.md` - Understanding eval in single-user vs multi-user

## Directory Structure

```
rosh-lang/
├── ROSH-MANUAL.rosh    # ⭐ THE comprehensive Rosh manual (START HERE!)
├── ROADMAP.md          # Technical milestones (public-friendly)
├── README.md           # This file (quick start)
├── LICENSE             # MIT License
├── src/rosh/           # Python interpreter implementation
│   ├── lexer.py        # Tokenization
│   ├── parser.py       # AST generation
│   ├── interpreter.py  # Execution engine
│   ├── ast_nodes.py    # AST node definitions
│   └── cli.py          # Command-line interface
├── examples/           # Example .rosh programs (MUDs, games, demos)
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
