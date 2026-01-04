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

## Decision History

- **v0.1.x**: All emitters developed independently
- **v0.2.0**: IR becomes contract, emitters are translators
- **v0.2.5**: Shared JS runtime extracted for ThreeJS/Phaser
- **v0.2.5**: Architecture decision - JS as graphics source of truth
