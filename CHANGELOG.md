# Rosh Changelog

**Policy:** See docs/POLICIES.md for changelog guidelines

> Single chronological log of ALL changes. Never delete, only append.

---

## [Unreleased]

### Next Steps
- Multiline comments
- Type checking functions (is_number, is_string, etc.)
- List slicing

---

## [v0.0.6] - 2024-12-13

**Quality of Life Release** - Massive improvements to language usability based on real-world usage!

### New Features ✨

### Added
- **String interpolation** 🎉
  - Syntax: `"Hello {name}, you are {age} years old!"`
  - Works with any expression: `"{x plus y}"`
  - Works with object properties: `"{player.health}/{player.max_health}"`
  - Implemented via interpreter-level regex parsing
  - Added Section 28 to ROSH-MANUAL.rosh
  - Resolves issue #113 from dungeon crawler pain points

- **`input` command for user input** 🎮
  - Syntax: `input variable_name`
  - Reads line from stdin and stores in variable
  - Essential for interactive games
  - Added TOKEN type, parser support, interpreter eval_input
  - Added Section 29 to ROSH-MANUAL.rosh (commented examples)
  - Resolves issue #96 from dungeon crawler pain points

- **`else if` syntax support** 🌿
  - Natural conditional chaining without deep nesting
  - Works as syntactic sugar for nested if statements
  - Example: `if x then ... else if y then ... else ... end`
  - Parser modification to parse_if method
  - Updated Section 5 in ROSH-MANUAL.rosh
  - Resolves issue #132 from dungeon crawler pain points

- **Modulo operator** 🔢
  - Syntax: `set remainder to x modulo y`
  - Returns remainder after division
  - Includes division-by-zero protection
  - Example: `17 modulo 5` → `2`

- **Increment/Decrement shortcuts** ⚡
  - Syntax: `increment x` and `decrement x`
  - Much cleaner than `set x to x plus 1`
  - Works with both variables and object properties
  - Examples:
    - `increment score`
    - `decrement player.health`
    - `increment game.level`

### Fixed
- **`not` in compound boolean expressions** ✅
  - Fixed parser to allow: `if x and not y then`
  - Fixed parser to allow: `if not x or y then`
  - Fixed parser to allow: `if x is above 3 and not y is below 5 then`
  - Created `parse_condition_term()` helper for proper NOT handling
  - Updated Section 4 in ROSH-MANUAL.rosh with examples
  - Resolves issue #76 from dungeon crawler pain points

### Changed
- Updated feature summary in ROSH-MANUAL.rosh
  - Added string interpolation to feature list
  - Added input command to feature list
  - Updated conditionals entry to mention "else if"
  - Updated boolean logic entry to mention "NOT in compound expressions"
- Version bumped from v0.0.5 to v0.0.6 in pyproject.toml

### Documentation
- Updated ISSUES.md:
  - Moved 4 issues to Resolved (not, input, string interpolation, else if)
  - Updated "Active Issues" to show no critical blockers
  - Added detailed resolution information for each fix
- Updated IDEAS.md:
  - Marked all v0.0.6 features as ✅ DONE!
  - Updated pain points section with resolution date

### Testing
- Verified ROSH-MANUAL.rosh runs successfully with all new features
- Created and tested:
  - test_not_compound.rosh (NOT in compound expressions)
  - test_input.rosh (input command)
  - test_interpolation.rosh (string interpolation)
  - test_else_if.rosh (else if syntax)
- All tests passed successfully

### Impact
This release addresses the top pain points discovered while building the dungeon-crawler.rosh demo:
- String interpolation reduces message code from 5+ lines to 1 line
- `input` command enables truly interactive games
- `else if` eliminates deep nesting hell
- `not` in compounds allows natural boolean logic

Before v0.0.6, printing a formatted message required:
```rosh
print "Health: "
get player.health
print stack
print " / "
get player.max_health
print stack
```

After v0.0.6:
```rosh
print "Health: {player.health} / {player.max_health}"
```

**This makes Rosh actually usable for real game development!**

---

### Documentation (2024-12-12)
- Created comprehensive POLICIES.md
- Created ISSUES.md for bug tracking
- Created CHANGELOG.md (this file)
- Renamed rosh_ideas_direction.md to IDEAS.md
- Created docs/proposals/EVENT-SYSTEM.md specification
- Created docs/TRANSPILER-ROADMAP.md
- Created docs/HOSTING-PLATFORMS.md
- Updated PROJECT-PLAN.md with:
  - Transpiler priorities (JavaScript, Lua, GDScript, Python)
  - Rust migration strategy (v2.0+)
  - Event system (v0.0.7)
  - Hosting strategy (rosh.cloud)
  - Multi-user roadmap (v0.1.0)

---

## [v0.0.5] - 2024-12-12

### Added
- **Function return value assignment** (Commit: d32df9c)
  - Can now do: `set value to call double 15`
  - Parser supports `call` in expressions
  - Updated ROSH-MANUAL.rosh with examples

- **Stack operations** (Commit: d32df9c)
  - New `stack` command to view data stack
  - Non-destructive stack viewing
  - Updated ROSH-MANUAL.rosh Section 27

- **REPL improvements** (Commit: d32df9c)
  - Type variable name alone to see value
  - No need for `print` in REPL
  - Example: `rosh> x` shows value of x

- **Comprehensive help system** (Commit: d32df9c)
  - Help for all 45+ commands
  - Clear alias documentation (stop=exit, say=print, etc.)
  - Organized into categories

- **For loop list iteration** (v0.0.5 release)
  - Syntax: `for item in my_list then`
  - Iterate over list elements
  - Updated ROSH-MANUAL.rosh

- **String methods** (v0.0.5 release)
  - split: `split text by delimiter`
  - substring: `substring of text from start length len`
  - uppercase/lowercase: Case conversion
  - trim: Remove whitespace
  - indexOf/lastIndexOf: Search strings
  - Updated ROSH-MANUAL.rosh

### Changed
- Updated ROSH-MANUAL.rosh to v0.0.5
  - Added Section 27 (Stack Operations)
  - Updated feature summary
  - Added type annotations examples
  - All 756 lines run successfully

- Simplified README.md installation
  - Single installation path (uv tool install)
  - Removed duplication
  - Clear upgrade instructions

### Documentation
- Created QUICK-START.md
  - User-friendly installation
  - Developer setup separate
  - Easy upgrade path

- Updated PROJECT-PLAN.md
  - Testing policy added
  - Recent accomplishments tracked
  - Status reflects v0.0.5 features

- Testing policy established
  - All scratch files in scratches/ directory
  - Never commit test files to root
  - Use `trash` CLI for cleanup

### Fixed
- Parser now recognizes `call` in expressions
- Stack viewing without destructive pop
- REPL variable evaluation works
- Removed premature `stop` command from manual

---

## [v0.0.4] - 2024-11-30

### Added
- For loops (ranges and collections)
- Lists with bracket notation
- List indexing and modification
- Break and continue statements
- Object cloning and deletion
- Properties command
- Boolean operators (and/or/not)

---

## [v0.0.3] - 2024-11-15

### Added
- Single and multiple inheritance
- Property stacks (push/pop)
- While loops
- 13+ math functions (abs, min, max, round, floor, ceil, sqrt, pow, sin, cos, tan)
- Random numbers
- Alias system
- Command history
- Tab completion
- MUD builder system

---

## [v0.0.2] - 2024-11-01

### Added
- AI Integration
  - `prompt` command with context
  - `prompt exec` for code generation
  - `eval` for dynamic execution
  - AI-powered error recovery
- File I/O (read/write/import)
- OpenAI and Anthropic support

---

## [v0.0.1] - 2024-10-15

### Added
- Initial release
- Lexer, parser, AST interpreter
- Basic data types (number, string, boolean, null)
- Objects with properties
- Functions with parameters
- Conditionals (if/then/else)
- Stack operations (get, add, subtract, multiply, divide, dup, swap, drop)
- REPL with CLI
- VS Code extension (syntax highlighting, snippets)

---

## Version History

| Version | Date | Milestone | Key Features |
|---------|------|-----------|--------------|
| v0.0.5 | 2024-12-12 | String Operations | List iteration, string methods, function return assignment, stack viewing, REPL improvements |
| v0.0.4 | 2024-11-30 | Collections & Control Flow | For loops, lists, break/continue, object cloning |
| v0.0.3 | 2024-11-15 | Inheritance & Enhancement | Inheritance, while loops, math functions, random |
| v0.0.2 | 2024-11-01 | AI Integration | prompt, prompt exec, eval, file I/O |
| v0.0.1 | 2024-10-15 | Core Interpreter | Lexer, parser, objects, functions, REPL |

---

## Upcoming

### v0.0.6 (Planned - Q1 2025)
- Multiline comments (""" or ###)
- String interpolation ("Hello {name}")
- Type checking functions (is_number, is_string, etc.)
- List slicing (my_list[1:3])
- Modulo operator (x modulo y)
- else if / elif syntax
- Increment/decrement shortcuts

### v0.0.7 (Planned - Q1 2025)
- **Event system** (when/trigger syntax) - TOP PRIORITY
- Error handling (try/catch)
- Dictionary/map data structures
- List comprehensions
- Lambda functions

### v0.0.8 (Planned - Q2 2025)
- Package system with manifests
- Package manager commands
- Dependency resolution
- Module registry

### v0.1.0 (Planned - Q2 2025)
- Multi-user MUD support
- WebSocket server
- Sandboxing and security
- rosh.cloud deployment (docs.rosh.cloud, demo.rosh.cloud)

### v0.3.0+ (2026)
- Transpilers: JavaScript, Lua, GDScript, Python
- Multi-platform game development

### v2.0+ (2027+)
- Optional Rust core rewrite
- WASM compilation
- 10-100x performance

---

## Links

- [GitHub Repository](https://github.com/rdubar/rosh)
- [Documentation](docs/)
- [Issues](ISSUES.md)
- [Project Plan](PROJECT-PLAN.md)

---

*Format: Based on [Keep a Changelog](https://keepachangelog.com/)*
*Versioning: [Semantic Versioning](https://semver.org/)*
