# Rosh Issues

This file tracks user-reported issues and bugs for the Rosh language.

**Note:** This tracker will be active when Rosh goes public. For now, see development issues in the internal repository.

---

## Reporting an Issue

When reporting an issue, please include:

1. **Rosh version:** `rosh --version`
2. **Minimal code** to reproduce the issue
3. **Expected behavior** vs **actual behavior**
4. **Target platform** (if applicable): Phaser, Pygame, Three.js

---

## Open Issues

### ISSUE-002: No way to configure engine-specific input controls
**Status:** 🔶 Enhancement request
**Target:** All (Three.js, Phaser, Pygame)

**Problem:** Input controls (keyboard mappings) are hardcoded in each emitter. Users cannot customize which keys control player movement, camera, or other actions.

**Current defaults:**

| Engine | Player Movement | Rise/Fall | Camera | Console |
|--------|-----------------|-----------|--------|---------|
| Three.js | Arrow keys | . / | WASD + QE | ` |
| Phaser | Arrow keys | N/A (2D) | N/A | N/A |
| Pygame | Arrow keys | N/A (2D) | N/A | N/A |

**Desired:** Allow configuration in Rosh code, e.g.:
```rosh
config threejs
    set player_rise_key to "r"
    set camera_enabled to false
end
```

**Architecture note:** The IR is intentionally target-agnostic. Engine-specific config should go in `_meta/` or a `config` block, not pollute the core IR.

**Workaround:** Edit generated code, or modify emitter source.

**Priority:** Low - current defaults work well for demos.

---

### ISSUE-001: Three.js transpiler - 2D games use wrong coordinate system at runtime
**Status:** 🔶 Known limitation
**Target:** Three.js

2D games (designed for Phaser/Pygame) compile to Three.js but gameplay doesn't work correctly because runtime position updates use 2D pixel coordinates instead of 3D world coordinates.

**Workaround:** Use Three.js transpiler for native 3D scenes, not 2D game ports. The rosh-intro Three.js demo works correctly because it was designed for 3D.

**See:** rosh-dev/BUGS.md BUG-005 for full details.

---

## Enhancement Ideas (2025-12-18)

Logged for future tinkering:

### ISSUE-005: Add animation commands
**Status:** 📋 Planned
**Target:** Three.js
**Effort:** Medium

Simple animation verbs:
```
> spin ball
> pulse logo
> bounce cube
```

---

### ISSUE-006: Save hidden object state
**Status:** 📋 Planned
**Target:** All
**Effort:** Low

Currently save/load only captures scene objects, not hidden objects like `_state.phase`, `_state.score` etc. Hidden objects (names starting with `_`) should be included in save/load.

---

### ISSUE-007: Relative positioning commands
**Status:** 📋 Planned
**Target:** All
**Effort:** Low

Move objects relative to current position:
```
> move ball up 2
> move ball left 5
```

---

### ISSUE-009: Screenshot command
**Status:** 📋 Planned
**Target:** Three.js
**Effort:** Medium

Export current view as PNG:
```
> screenshot
```

---

## Design Notes

### Core Language Commands

These commands work in `.rosh` scripts AND all REPLs:

| Command | Description | Added |
|---------|-------------|-------|
| `create <name>` | Create object (uses known type if available) | v0.1.13 |
| `create <type> <name>` | Create named object of type | v0.1.13 |
| `clone <obj>` | Clone existing object | v0.1.11 |
| `clone <obj> as <name>` | Clone with custom name | v0.1.11 |
| `count` | Count all objects | v0.1.13 |
| `count <type>` | Count objects of type | v0.1.13 |
| `move <obj> to x, y` | Move to coordinates | v0.1.13 |
| `delete <obj>` | Delete object | v0.1.11 |
| `set <obj>.<prop> to <val>` | Set property | v0.1.0 |
| `get <obj>.<prop>` | Get property | v0.1.0 |
| `print <expr>` | Print value | v0.1.0 |

### REPL-Only Commands

Some commands are only available in interactive REPLs, not in `.rosh` script files:

| Command | Description | Available In |
|---------|-------------|--------------|
| `make <obj> bigger` | Scale object up by 1.5× | CLI REPL, Three.js console |
| `make <obj> smaller` | Scale object down by 1.5× | CLI REPL, Three.js console |
| `make <obj> visible` | Show object | CLI REPL, Three.js console |
| `make <obj> hidden` | Hide object | CLI REPL, Three.js console |
| `make <obj> <color>` | Change object color | CLI REPL, Three.js console |
| `help create` | Show create syntax and known object types | CLI REPL, Three.js console |
| `help make` | Show make command usage | CLI REPL, Three.js console |

**Why REPL-only?** These are natural-language convenience commands for interactive exploration. In scripts, use explicit commands like `set ball.scale to 2` for precision and reproducibility.

**Tip:** Use `help make` in the REPL to see usage examples.

---

## Resolved Issues

### ISSUE-003: Add `text` command to console ✅
**Resolved:** 2025-12-18
**Target:** Three.js

Changed text sprite content at runtime via `set logo text to "hello"`.

---

### ISSUE-004: Add `delete` command to console ✅
**Resolved:** 2025-12-18
**Target:** Three.js, Main REPL

Remove objects at runtime with confirmation.

---

### ISSUE-008: Object duplication (clone) ✅
**Resolved:** 2025-12-18
**Target:** Three.js, Main REPL

Clone objects with `clone ball` (auto-name) or `clone ball as newball`.

---

### ISSUE-010: Three.js REPL - Confirmation for bulk operations ✅
**Resolved:** 2025-12-21
**Target:** Three.js REPL

Three.js REPL now has confirmation for bulk operations with >= 10 objects, matching CLI behavior:
- `create 100 balls` → "⚠ Create 100 ball(s)?" → type `go` to execute
- `delete all orcs` → "⚠ Delete all 50 orc(s)?" → type `confirm` to execute
- `make all balls bigger` → "⚠ Modify 20 ball(s)?" → type `yes` to execute
