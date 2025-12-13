# Rosh Architecture Decisions

## Core Language vs Domain Libraries

### Philosophy

Rosh is designed as a **general-purpose**, **minimal-core** language with domain-specific functionality provided through **standard libraries**.

### Core Language Features

The core language (built-in keywords and commands) includes:

**Data & Variables:**
- `create`, `set`, `get`, `print`
- `clone`, `delete`, `properties`

**Control Flow:**
- `if`, `then`, `else`, `end`
- `while`, `then`, `end`

**Functions:**
- `define function`, `call`

**Stack Operations:**
- `add`, `subtract`, `multiply`, `divide`
- `dup`, `swap`, `drop`
- `push`, `pop`

**I/O & State:**
- `dump`, `save`, `load`
- `read`, `write`
- `import`

**AI Integration:**
- `prompt`, `eval`

**Introspection:**
- `help`

### Domain-Specific Libraries

Domain-specific concepts are provided through **importable libraries**:

#### MUD Standard Library (`import mud`)

The MUD (Multi-User Dungeon) library provides game-specific functionality:

**Spatial Commands:**
- `goto <room>` - Move to a room
- `look [object]` - Examine current room or object
- `connect <room1> <direction> <room2>` - Link rooms

**Templates:**
- `room` - Locations with exits (north, south, east, west, up, down)
- `thing` - Movable objects
- `character`, `player`, `npc` - Living entities
- `weapon`, `armor`, `container`, `door` - Game items

### Design Rationale

**Why rooms are NOT core language features:**

1. **General Purpose**: Rosh can be used for:
   - Data processing and transformation
   - AI scripting and automation
   - Configuration management
   - Interactive fiction (non-spatial)
   - Math and computation
   - Web scraping and APIs

   None of these need spatial concepts like rooms.

2. **Minimal Core**: Keep the language small and learnable
   - Core language: ~30 keywords
   - Domain libraries add features as needed
   - Easier to learn, easier to implement

3. **Extensibility**: Libraries can be:
   - Created by the community
   - Imported selectively
   - Versioned independently
   - Domain-optimized

4. **Precedent**: Similar to other languages:
   - Python: `numpy`, `pandas`, `flask` are libraries
   - JavaScript: `express`, `react` are libraries
   - Rust: Game engines are crates, not core language

### Example Usage

```rosh
# General-purpose Rosh (no imports)
create number x as 42
get x
dup
multiply
print  # 1764

# MUD-specific Rosh (with import)
import mud
create room tavern
set tavern.name to "The Rusty Tankard"
goto tavern
look
```

### Future Libraries

Potential future domain libraries:

- **web** - HTTP requests, JSON parsing, API integration
- **math** - Advanced mathematical functions
- **data** - CSV/JSON/XML processing
- **ai** - Additional AI/ML utilities
- **game** - 2D/3D game primitives (separate from MUD)

## Conclusion

**Rooms are intentionally MUD-specific**, not core Rosh. This keeps the language general-purpose, minimal, and extensible through a rich library ecosystem.

---

**Version:** 0.0.4
**Last Updated:** 2024-12-11
**Status:** ✅ Architectural Decision Confirmed
