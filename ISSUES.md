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

## Resolved Issues

*None yet.*
