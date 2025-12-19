# Changelog

All notable changes to the Rosh programming language will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.11] - 2025-12-16

### 🧠 Builder UX
- **Three.js undo** - In-game console now supports `undo` / `undo N` across creates, deletes, clones, and property edits
- **Undo stack inspector** - `undo stack` previews the most recent reversible steps for confidence while experimenting
- **CLI undo** - Core interpreter + REPL gained `undo`, `undo N`, and `undo stack` so typed workflows mirror the Three.js console

### ⚙️ Engine Capabilities
- **Capability rollbacks** - `color`, `font`, `font_size`, `text`, `scale`, `spin`, `bounce`, `pulse`, and `orbit` expose inverse handlers so capability bridge actions participate in undo
- **Passthrough safety** - Manual `set` passthroughs to `userData` now capture their previous values for precise undos

## [0.1.10] - 2025-12-15

### ✨ Demo & Polish
- **Dynamic font_size** - Animate text size in both Phaser and Pygame transpilers
- **Pygame CLI** - Full CLI support (`rosh build --target pygame`)
- **Rosh intro demo** - Animated loading screen works in both targets
- **Asset reorganization** - Distributed sprites/sounds in `assets/` folder

### 🔧 Fixes
- Fixed Phaser font_size double-increment bug (block-scoped const)
- Fixed CLI output message (always show server instructions for Phaser)

## [0.1.9] - 2025-12-15

### 🎵 Sound Support
- **Sound effects** - `play sound "laser.wav"` in both transpilers
- **Background music** - `play music "theme.ogg"` / `stop music`
- **Asset caching** - Automatic preloading and caching
- Works in Phaser (Web Audio) and Pygame (mixer)

## [0.1.8] - 2025-12-14

### 🎮 Pygame Transpiler
- **Native desktop games** - `rosh build --target pygame` (Phase 2)
- **Full feature parity** - Objects, text, key events, update loops
- **Grid-based collision** - Coordinate math like Block Pusher
- **Input parity** - Fires once per press (matches Phaser JustDown)
- **No browser needed** - Run with `python3 game.py`

## [0.1.7] - 2025-12-14

### 🖼️ Sprite System
- **Sprite support** - `set sprite to "hero.png"` in Phaser transpiler
- **Asset copying** - `--copy-assets` flag copies only used sprites
- **Graceful fallback** - Missing sprites show colored rectangles
- 6300+ free game assets included (Kenney collection)

## [0.1.6] - 2025-12-14

### ⌨️ Input & Events in Phaser
- **Event system** - `when/trigger` in Phaser transpiler
- **Object inheritance** - `create object hero from player`
- **Auto-controls** - Arrow keys + space for player objects
- **Smart defaults** - lives, score, speed properties
- **Auto HUD** - Lives/score display

## [0.1.5] - 2025-12-14

### 🌐 Phaser Transpiler MVP
- **Browser games** - `rosh build --target phaser`
- **Objects** - Colored rectangles with position/size
- **Print** - console.log with string interpolation
- **Fail-fast** - Clear errors for unsupported features

## [0.0.9] - 2025-12-14

### 📦 TOON Format
- **TOON encoder/decoder** - 40% fewer tokens than JSON
- **File operations** - Save/load `.toon` files
- **Round-trip support** - All Rosh types preserved
- 37 comprehensive tests

## [0.0.8] - 2025-12-13

### 🔧 Infrastructure & Tooling
- **TOML support** - `--toml` flag, import `.toml` files
- **Test mode** - `--test`, `--test-input` flags for CI/CD
- **Program metadata** - `meta` keyword with UUID/checksum

## [0.0.7] - 2025-12-14

### ⚡ Event System
- **Event-driven programming** - `when <event> then ... end`
- **Trigger with params** - `trigger player_damaged with 15`
- **Lexical scoping** - Event handlers have proper scope
- **Event loop stdlib** - `every()`, `stop_loop()` helpers

## [0.0.6] - 2025-12-13

### 🎨 Quality of Life
- **String interpolation** - `"Hello {name}!"`
- **User input** - `input username prompt "Enter name:"`
- **else if** - Chained conditionals
- **NOT** - In compound expressions
- **Multiline comments** - `"""` or `###`
- **Type checking** - Type checking functions
- **List slicing** - Slice syntax
- **Interactive mode** - `-i` flag

## [0.0.5] - 2025-12-12

### 📚 Documentation & Cleanup
- Repository reorganization
- Numbered ticket system
- Strategic planning documents

## [0.0.4] - 2024-12-11

### 🔧 Critical Fixes
- **Version Consistency** - All version references now 0.0.4 (was inconsistent)
- **Duplicate Code** - Removed duplicate `eval_connect` definition
- **delete Cleanup** - Now properly removes from instance tracking (`uuid_map`, `instances`)
- **Cycle Protection** - Added cycle detection in inheritance chain to prevent infinite recursion
- **Security Documentation** - Created `SECURITY.md` with comprehensive warnings

### ✨ New Features
- **save Command** - Save state to file (default: `rosh-state.json`)
- **license Command** - Display license in REPL (`license`, `help license`, `copyright`)
- **Rich Colors** - Beautiful colored output throughout REPL and commands
- **examine/ex Aliases** - Built-in aliases for `look` command

### 📚 Documentation
- `SECURITY.md` - Security risks and best practices
- `ARCHITECTURE.md` - Design decisions (rooms are MUD-specific, not core)
- `LICENSE-INFO.md` - Detailed license and trademark explanation
- `FIXES-v0.0.4.md` - Implementation summary

### ⚠️ Known Issues (Documented)
- State persistence doesn't save instance tracking
- Functions cannot be serialized
- Import cache never clears (no reload mechanism)
- HTTP imports lack security hardening
- No automated test suite

## [0.0.3] - 2024-12-10

### 🎉 Major Features

#### Inheritance System
- **Prototype-Based Inheritance** - `create object warrior from character`
- **Multiple Inheritance** - `create object paladin from warrior, healer`
- **Left-to-Right Resolution** - Clear, predictable property lookup (Python MRO style)
- **Property Stacks** - Time-travel debugging with `push`/`pop`
  - `push player.health 150` - Shadow values temporarily
  - `pop player.health` - Reveal previous values
  - Perfect for buffs/debuffs, undo systems, debugging
- **Simpler than C++/Python** - No diamond problem, explicit shadowing
- **Compiler-Friendly** - Stack operations are CPU-friendly

### Examples
- `inheritance-single.rosh` - Basic inheritance
- `inheritance-multiple.rosh` - Multiple parents with resolution
- `property-stacks.rosh` - Push/pop demonstration
- `inheritance-complete.rosh` - Full paladin scenario

### Implementation
- ~160 lines of elegant code across 5 files
- RoshObject rewrite with property_stacks and parents
- Parser support for `from parent1, parent2` syntax
- Interpreter with parent lookup and stack operations

## [0.0.2] - 2024-12-10

### 🎉 Major Features

#### AI Integration - Revolutionary!
- **AI Code Generation** (`prompt exec`) - AI writes and executes Rosh code in your environment
- **AI Error Recovery** - Automatic suggestions when you make mistakes
- **Text Generation** (`prompt`) - AI assistance with context passing
- Provider-agnostic design (OpenAI, Anthropic)
- User's own API keys (no centralized billing)

#### File I/O
- `read <file> into <var>` - Read files to strings
- `read json <file> into <var>` - Read and parse JSON automatically
- `write <value> to <file>` - Write values to files

#### Package System
- `import <path>` - Import Rosh modules
- URL-based imports with automatic caching
- Multiple package directories (~/.rosh/packages/, current dir)
- Import deduplication (modules imported once)
- Zero-config package management

#### Code Execution
- `eval <code_string>` - Execute Rosh code from strings
- Dynamic code generation and execution
- Markdown fence stripping for AI-generated code

### Enhanced Features
- Beautiful error messages with setup instructions
- AI-powered error suggestions in REPL
- Improved system prompts for code generation
- Smart code parsing (handles AI formatting)

### Developer Tools
- VS Code extension with syntax highlighting and snippets
- Professional packaging (`pip install -e ".[ai]"`)
- MIT License with trademark protection
- Comprehensive documentation (AI_SETUP.md, ROADMAP.md)

### Examples
- 13 example programs demonstrating all features
- AI code generation examples
- Module system examples
- File I/O examples

## [0.1.0] - 2024-12-09

### Initial Release

#### Core Language Features
- **Lexer** - Tokenization with cosmetic indentation
- **Parser** - Recursive descent with natural syntax
- **Interpreter** - AST-based execution
- **Data types** - Numbers, strings, booleans, null, objects
- **Control flow** - if/then/else statements
- **Functions** - define/call with closures
- **Objects** - Create and manipulate with properties

#### Stack-Based Operations
- Explicit data stack (`self.data_stack`)
- Math operators: add, subtract, multiply, divide
- Stack manipulation: dup, swap, drop
- `get` command - Push values onto stack
- `print` (no args) - Pop and print from stack

#### State Management
- `dump` - Serialize state to JSON
- `load <file>` - Restore state from JSON
- Full state persistence (variables, stack, objects)

#### CLI Features
- File execution: `rosh file.rosh`
- Interactive REPL with persistent state
- Inline code: `rosh -c "code"`
- Multi-line support in REPL
- Error recovery (Ctrl+C, exceptions)

#### Language Design
- Spoken-language-first syntax
- Cosmetic indentation (no INDENT/DEDENT tokens)
- Explicit `end` keywords
- Natural language operators ("is below", "is equal to")
- Space-separated property access (`get player health`)

### Breaking Changes from v0.0.x
- Renamed `say` → `print` (keeping `say` as alias)
- Removed INDENT/DEDENT tokens (indentation now cosmetic)
- Changed to explicit `end` keywords for all blocks

## [0.0.1] - 2024-12-08

### Prototype
- Initial proof of concept
- Basic lexer and parser
- Hello world example
- `say` command for output

---

**Legend:**
- 🎉 Major new features
- ✨ Enhancements
- 🐛 Bug fixes
- 💥 Breaking changes
- 📝 Documentation
- 🔧 Internal changes
