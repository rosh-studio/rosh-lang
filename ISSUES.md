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

### ISSUE-001: Three.js transpiler - 2D games use wrong coordinate system at runtime
**Status:** 🔶 Known limitation
**Target:** Three.js

2D games (designed for Phaser/Pygame) compile to Three.js but gameplay doesn't work correctly because runtime position updates use 2D pixel coordinates instead of 3D world coordinates.

**Workaround:** Use Three.js transpiler for native 3D scenes, not 2D game ports. The rosh-intro Three.js demo works correctly because it was designed for 3D.

**See:** rosh-dev/BUGS.md BUG-005 for full details.

---

## Resolved Issues

*None yet.*
