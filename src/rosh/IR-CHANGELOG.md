# IR Changelog

All notable changes to the Rosh IR specification.

Format: [Semantic Versioning](https://semver.org/)
- MAJOR: Breaking changes (removed features, changed semantics)
- MINOR: New features (backward compatible)
- PATCH: Bug fixes only

---

## v0.1.0 (2025-12-21)

Initial versioned release (pre-v1).

### Core Commands
- `create` - Object and value creation
- `set` / `set all` - Property assignment (with bulk confirmation)
- `get` - Property retrieval
- `delete` - Object removal
- `look` / `examine` - Object inspection
- `move` - Object positioning
- `clone` - Object duplication
- `reset` - Property restoration
- `hide` / `show` - Visibility control

### Control Flow
- `if` / `else` - Conditionals
- `while` - Loops
- `for` - Iteration
- `when` - Event handlers
- `break` / `continue` / `stop` - Flow control

### Functions
- `define` - Function definitions
- `return` - Return values
- Function calls with arguments

### Utility Commands
- `help` - Context-sensitive help
- `confirm` / `yes` / `go` - Bulk operation confirmation
- `repeat` - Re-execute last substantive command
- `print` / `say` - Output
- `count` - Instance counting
- `save` / `load` - State persistence

### Stack Operations
- `push` / `pop` / `peek` / `dup` / `swap` / `drop` / `clear`

### Metadata
- `meta` - Program metadata declarations

---

## Future Versions

### v0.2.0 (planned)
- TBD based on parser/IR work

### v1.0.0 (planned)
- Stable baseline for production use
- All emitters must implement before release
