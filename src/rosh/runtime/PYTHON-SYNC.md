# Python REPL Sync List

⚠️ **THIS FILE IS TECHNICAL DEBT** - Manual sync causes bugs (e.g., `dump` was missing).
See JS-RUNTIME-ARCHITECTURE.md - generator is MANDATORY before new features.

**Last sync: 2025-12-21**

---

## Key Documents

- **rosh-dev/proposals/IR-VERSIONING-POLICY.md** - Python is source of truth
- **rosh-dev/proposals/JS-RUNTIME-ARCHITECTURE.md** - Three-layer JS structure
- **src/rosh/cli.py** - Python REPL implementation (SOURCE OF TRUTH)
- **src/rosh/runtime/rosh-core.js** - Layer 1: Base REPL shell
- **src/rosh/runtime/rosh-3d.js** - Layer 2: 3D object commands
- **src/rosh/runtime/threejs-adapter.js** - Layer 3: Three.js adapter

---

## Command Sync Status

Commands in Python CLI that should be in JS runtime:

| Command | Python | JS | Notes |
|---------|--------|-----|-------|
| `create` | ✅ | ✅ | Core command |
| `set` | ✅ | ✅ | Core command |
| `get` | ✅ | ✅ | Core command |
| `delete` / `remove` | ✅ | ✅ | Both aliases work |
| `list` | ✅ | ✅ | Show all objects |
| `look` / `examine` / `inspect` / `x` / `ex` | ✅ | ✅ | Examine object |
| `dump` | ✅ | ✅ | Fixed 2025-12-21 |
| `clone` / `copy` / `duplicate` | ✅ | ✅ | All aliases work |
| `move ... to x y` | ✅ | ✅ | Position shorthand |
| `make ... bigger/smaller` | ✅ | ✅ | Scale modifiers |
| `make ... faster/slower` | ✅ | ✅ | Speed modifiers |
| `hide` / `show` | ✅ | ✅ | Visibility |
| `count` | ✅ | ✅ | Count objects by type |
| `undo` / `oops` | ✅ | ✅ | Both aliases work |
| `redo` | ✅ | ✅ | Redo last undo |
| `help` | ✅ | ✅ | Show commands |
| `ls` / `objects` | ✅ | ✅ | Fixed 2025-12-21 |
| `l` | ✅ | ✅ | Fixed 2025-12-21 |
| `properties` / `props` | ✅ | ✅ | Fixed 2025-12-21 |
| `print` | ✅ | ❌ | Print expression value |
| `version` | ✅ | ✅ | Fixed 2025-12-21 |
| `credits` | ✅ | ✅ | Show credits |
| `goto` / `go` | ✅ | ❌ | MUD navigation (n/a for 3D) |
| `connect` / `link` | ✅ | ❌ | MUD rooms (n/a for 3D) |
| `save` / `load` | ✅ | ❌ | Persistence (future) |
| `import` | ✅ | ❌ | Import modules (future) |

**Remaining:** `print` (needs expression evaluation)

### ⚠️ MANDATORY: Generator Required

**DO NOT add more commands manually.** Build the generator first.

See `JS-RUNTIME-ARCHITECTURE.md` → "MANDATORY: Before Any New Features"

The generator (`src/rosh/emitters/runtime_js.py`) will:
1. Parse command patterns from cli.py
2. Generate JS command routing code
3. Run as part of build process
4. Make this file obsolete

---

## Feature Commands
- [x] `make <obj> bigger/smaller/faster/slower` - relative modifiers (added faster/slower)
- [x] `move <obj> to <x> <y> [z]` - set position with one command
- [x] `clone <obj>` / `copy` / `duplicate` - duplicate an object (copy/duplicate aliases added)
- [x] ~~`p` as alias for `look`/`inspect`~~ REMOVED - conflicts with `print` semantics
- [ ] Extended property list: text, name, width, height, size, font_size, opacity, alpha
- [x] Sequential object naming: box-1, box-2 instead of timestamps (already works)

## Bulk Operations (now in JS)
- [x] `create N <type>` - create multiple objects (arranges in circle)
- [x] `delete all <type>` - delete all objects of a type
- [x] `set all <type> <prop> to <value>` - set property on all of a type
- [x] Confirmation for bulk ops > threshold

## Fuzzy Correction
- [x] Command typos: creat→create, delte→delete, lst→list, etc. (already in Python)
- [x] British spellings: colour→color, centre→center (already in Python)
- [x] Apply fuzzy correction BEFORE block detection (so "creat object X" enters multiline mode)

## Smart Resolution
- [ ] Object name resolution: "red box" → "redbox"
- [ ] Type+modifier matching: "red" + "box" → find box with red in name
- [ ] Partial name matching

## Property Inference
- [ ] Infer `color` from color names and hex values
- [ ] Infer `visible` from visible/hidden/invisible keywords
- [ ] Return error for ambiguous values (numbers) - require explicit property

## Multi-line Blocks
- [x] Properties not applying in `create object X ... end` blocks (fixed - tested with set x color red)

## General
- [ ] Consistent version display in console header
- [ ] `50%` percentage syntax for position values
- [ ] Percentages stored with original intent, resolved to pixels by adapter
- [x] Objects visible by default (already true in most cases)

## Text Objects
- [ ] `set text to "..."` creates renderable text, not just data
- [ ] Text objects respond to: text, font_size, color, x, y, visible
- [ ] Each adapter implements text rendering natively (Phaser: Text, Three.js: Sprite, Pygame: font.render)

---

## Architecture Notes

**Three-Layer JS Architecture (see JS-RUNTIME-ARCHITECTURE.md):**

```
Layer 1: rosh-core.js (~420 lines)
  - Console UI, command history, undo/redo
  - Fuzzy correction, command routing
  - NO object commands

Layer 2: rosh-3d.js (~620 lines) extends RoshCore
  - All object commands (create, set, get, etc.)
  - Value parsing, object resolution
  - Shared by Three.js, Babylon.js, etc.

Layer 3: threejs-adapter.js (~410 lines)
  - Three.js-specific rendering
  - Implements adapter interface
```

**The proper approach (per IR-VERSIONING-POLICY.md):**
1. Add features to Python CLI (cli.py) first
2. Regenerate rosh-runtime.js from Python source
3. Engine adapters remain thin (~200-300 lines)

**Current state:** Manual sync until the JS generator is built.
Backward compatibility maintained via rosh-runtime.js wrapper.
