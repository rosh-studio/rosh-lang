# Rosh Examples

This directory contains 21+ example Rosh programs demonstrating various features.

## Documentation Guides

- **PLAY-MUD.md** - Quick start guide for the MUD game
- **MUD-GUIDE.md** - Complete guide based on real usage
- **MUD-BUILDER.md** - Builder edition with items & properties
- **REPL-IMPROVEMENTS.md** - Error message improvements
- **REPL-HISTORY.md** - Command history & tab completion (NEW!)

## Example Categories

### Basic Features (5)
- `hello.rosh` - Hello World
- `counter.rosh` - Variables and operations
- `player.rosh` - Object creation
- `math.rosh` - Binary operators
- `conditional.rosh` - If/else statements

### Stack Operations (5)
- `stack.rosh` - Basic LIFO stack
- `stack-math.rosh` - Stack-based calculations
- `stack-manipulation.rosh` - dup/swap/drop
- `stack-objects.rosh` - Stack with object properties
- `state-dump.rosh` - State serialization

### Persistence (1)
- `save-load.rosh` - Save and load state

### AI Integration (4)
- `ai-hello.rosh` - Simple AI prompts
- `ai-context.rosh` - Context passing with `using`
- `ai-codegen.rosh` - AI code generation with `prompt exec`
- `eval-demo.rosh` - Dynamic code execution
- `ai-help.rosh` - AI assistance

### Inheritance (v0.0.3) (4)
- `inheritance-single.rosh` - Basic inheritance
- `inheritance-multiple.rosh` - Multiple parents
- `property-stacks.rosh` - Push/pop for time-travel
- `inheritance-complete.rosh` - Full paladin example

### Built-in Functions (v0.0.3) (1)
- `stdlib-math.rosh` - 13 native math functions

### Loops (v0.0.3) (2)
- `loop-basic.rosh` - Count from 1 to 5 with while loop
- `loop-factorial.rosh` - Calculate 5! using iteration

### MUD/Interactive World (v0.0.3+) (4)
- `mud-game.rosh` - **Builder Edition** with items & properties! 🆕
- `mud-demo.rosh` - Demo of item system (take/put/examine) 🆕
- `add-room-live.rosh` - Adding rooms during runtime
- `mud-helper.rosh` - Context-aware helper for Rosh MUD

### Modules (1)
- `modules/math.rosh` - Importable math utilities

### Package Manifests (v0.0.8 Preview) (2)
- `adventure-game.manifest.json` - Complete game package example
- `combat-system.manifest.json` - Reusable library/module example

See [Package Manifest System](#package-manifest-system) below for details.

## Running Examples

### Execute a file:
```bash
python -m rosh examples/hello.rosh
```

### Interactive REPL:
```bash
python -m rosh
```

The REPL supports:
- **Single-line statements**: Execute immediately
- **Multi-line blocks**: Automatically waits for `end` keyword
- **Persistent state**: Variables and objects persist between commands
- **Stack operations**: Use `get`, stack operators, and `print` interactively
- **State inspection**: Use `dump` to see all variables and stack contents

### REPL Example Session:
```
rosh> create number x as 10
rosh> print x
10
rosh> create object player
...   set name to "Hero"
...   set health to 100
...   end
rosh> print player.name
Hero
rosh> dump
{
  "variables": {
    "x": 10,
    "player": {
      "_type": "object",
      "_name": "player",
      "name": "Hero",
      "health": 100
    }
  },
  "stack": []
}
rosh> exit
```

## Example Files

- **hello.rosh** - Basic print statement
- **counter.rosh** - Variable reassignment
- **player.rosh** - Object creation with properties
- **math.rosh** - Arithmetic operations
- **conditional.rosh** - If/else statements
- **stack.rosh** - Basic stack operations (get/print)
- **stack-math.rosh** - Stack-based math operators
- **stack-manipulation.rosh** - Stack manipulation (dup/swap/drop)
- **stack-objects.rosh** - Stack operations with objects
- **state-dump.rosh** - State serialization with dump
- **save-load.rosh** - State persistence example

## Package Manifest System

**Status:** Specification complete, implementation planned for v0.0.8

Package manifests enable reproducible sharing and distribution of Rosh games and modules.

### Example Manifests

This directory includes two example manifests:

#### `adventure-game.manifest.json` - Complete Game Package
```json
{
  "name": "fantasy-adventure",
  "version": "1.0.0",
  "description": "A classic fantasy adventure game",
  "main": "game.rosh",
  "dependencies": {
    "rosh-stdlib-mud": "^1.0.0",
    "rosh-combat-system": "~2.1.0"
  },
  "checksums": {
    "algorithm": "sha256",
    "files": {
      "game.rosh": "abc123..."
    }
  }
}
```

#### `combat-system.manifest.json` - Reusable Library
```json
{
  "name": "rosh-combat-system",
  "version": "2.1.0",
  "description": "A flexible turn-based combat system",
  "main": "combat.rosh",
  "exports": {
    "initCombat": "combat.rosh#initCombat",
    "processTurn": "combat.rosh#processTurn"
  }
}
```

### Future Usage (v0.0.8+)

```bash
# Install a game
rosh install fantasy-adventure

# Verify checksums
rosh verify fantasy-adventure

# Publish your own game
rosh publish

# Search for games
rosh search fantasy
```

### Creating Your Own Manifest

1. Copy a template:
   ```bash
   cp examples/adventure-game.manifest.json my-game.manifest.json
   ```

2. Edit required fields:
   - `name` - Package name (lowercase-with-hyphens)
   - `version` - Semantic version (e.g., "1.0.0")
   - `description` - One-line summary
   - `author` - Your name
   - `main` - Entry point file

3. Add dependencies and metadata as needed

### Documentation

See [docs/proposals/PACKAGE-MANIFEST.md](../docs/proposals/PACKAGE-MANIFEST.md) for:
- Complete specification
- All available fields
- Version range syntax
- Checksum generation
- Security considerations
- Implementation roadmap
