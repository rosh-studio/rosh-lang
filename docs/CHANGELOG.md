# Changelog

All notable changes to the Rosh programming language will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
