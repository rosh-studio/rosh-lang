# Rosh Architecture

## Source of Truth Hierarchy

As of v0.2.5 (December 2025), Rosh uses a **JS-first architecture** for graphics:

```
Language & CLI:
├── rosh-lang/           # Parser, IR, language spec (Python)
├── Python interpreter   # CLI reference implementation
└── rosh-runtime.js      # Console commands (JS reference)

Graphics (Source of Truth):
├── ThreeJS emitter      # 3D reference implementation
└── Phaser emitter       # 2D reference implementation

Ports (follow, don't lead):
├── Pygame               # 2D port
├── Godot                # 3D port
└── Future engines       # Follow ThreeJS/Phaser behavior
```

## Rationale

1. **Web is where demos happen** - Customers see ThreeJS in browsers
2. **Shared JS runtime** - ThreeJS and Phaser share `rosh-runtime.js` for console commands
3. **Focus over parity** - Better to ship excellent ThreeJS than mediocre everything
4. **Clear hierarchy** - New 3D features land in ThreeJS first, ports follow

## What This Means

### For New Features

1. Implement in ThreeJS (3D) or Phaser (2D) first
2. The implementation IS the spec
3. Document behavior in `docs/`
4. Ports (Pygame, Godot) can follow when resources allow

**Clarification:** This is a hierarchy, not competing sources. Spec/IR + Python CLI define core behavior; ThreeJS (3D) and Phaser (2D) define graphics behavior. Ports follow and may lag until parity tests catch up.

### For Existing Code

- ThreeJS and Phaser: First-class, kept in sync via shared runtime
- Pygame: Maintained, but follows Phaser for 2D behavior
- Godot: Maintained, but follows ThreeJS for 3D behavior

### For the "Multi-Engine" Story

**Old framing:** "Rosh targets all engines equally"

**New framing:** "Rosh runs on the web (ThreeJS/Phaser) and can export to native engines like Godot and Pygame"

## Shared JS Runtime

```
static/
├── rosh-runtime.js         # Console, commands, undo/redo (shared)
├── rosh-adapter-threejs.js # ThreeJS bindings
└── rosh-adapter-phaser.js  # Phaser bindings
```

The shared runtime ensures console command parity between JS targets automatically.

## Version Parity

| Component | Version | Role |
|-----------|---------|------|
| Python interpreter | v0.2.4 | CLI reference |
| ThreeJS emitter | v0.2.4 | 3D reference |
| Phaser emitter | v0.2.4 | 2D reference |
| Pygame emitter | v0.2.0 | 2D port |
| Godot emitter | v0.2.1 | 3D port |

Ports may lag behind reference implementations. This is acceptable.

## JS/Python Parity Tracking (v0.2.10)

The JS runtime and Python interpreter have different architectures but must produce identical behavior for shared features. We use **@parity version tags** to track this.

### Architecture Difference

| Aspect | Python | JS |
|--------|--------|-----|
| Parsing | Lexer → Parser → AST | Regex in execCommand() |
| Execution | AST evaluation (eval_*) | Direct handlers (handle*) |
| Structure | Multiple files | Single file (rosh-runtime.js) |

**Why different:** Python is a full language interpreter (loops, functions, events). JS is an interactive console for 3D manipulation. Simpler needs = simpler architecture.

### Parity System

**@parity tags** mark functions that must stay in sync:

```javascript
// JS: @parity push_undo v1
function pushUndo(description, undoFn, redoFn) { ... }
```

```python
# Python: @parity push_undo v1
def push_undo(self, description, inverse, redo=None): ...
```

**Naming convention:** Same names, case differs (camelCase in JS, snake_case in Python).

**Tools:**
- `spec/parity-tracker.toml` - Documents all paired functions
- `scripts/check-parity.sh` - Compares @parity tags, finds mismatches

### Currently Tracked (v1)

| Function | JS | Python |
|----------|-----|--------|
| push_undo | pushUndo() | push_undo() |
| perform_undo | performUndo() | perform_undo() |
| perform_redo | performRedo() | perform_redo() |
| fuzzy_find_with_confirmation | fuzzyMatchObject() | _fuzzy_find_with_confirmation() |
| execute_pending_cross_scene | executePendingCrossScene() | execute_pending_cross_scene() |
| cancel_pending_cross_scene | cancelPendingCrossScene() | cancel_pending_cross_scene() |
| do_delete | doDelete() | do_delete() |
| do_clone | doClone() | do_clone() |
| do_set | doSet() | do_set() |
| do_hide | doHide() | do_hide() |
| do_show | doShow() | do_show() |
| do_move | doMove() | do_move() |

### Future Options

If tighter alignment is needed:

1. **Extract parity-critical code** - Pull shared logic into `rosh-core.js`
2. **Full structural alignment** - Split JS into lexer/parser/interpreter (significant effort)
3. **Code generation** - Generate both from shared spec (highest effort, highest consistency)

Current approach (parity tags) is sufficient for maintenance. Revisit if drift becomes problematic.

---

## Decision History

- **v0.1.x**: All emitters developed independently
- **v0.2.0**: IR becomes contract, emitters are translators
- **v0.2.5**: Shared JS runtime extracted for ThreeJS/Phaser
- **v0.2.5**: Architecture decision - JS as graphics source of truth
- **v0.2.10**: Parity tracking system added (@parity tags, check script)
