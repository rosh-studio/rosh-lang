# Tests - Feature Testing Examples

Internal test files for validating transpiler and interpreter features.

## Purpose

These files are used for testing specific features during development. They demonstrate individual features in isolation but are not intended as learning examples.

## For Learning

Instead of these test files, check out the organized examples:

- **../basics/** - Learn Rosh fundamentals
- **../games/** - Build browser games
- **../mud/** - Create text adventures
- **../advanced/** - Master advanced features

## Test Files

These files test specific Phaser transpiler features:

- `test-collision.rosh` - Collision detection
- `test-edge-wrap.rosh` - Edge wrapping behavior
- `test-events-*.rosh` - Event system
- `test-explicit-hud.rosh` - HUD creation
- `test-inheritance.rosh` - Object inheritance
- `test-percentages.rosh` - Percentage positioning
- `test-player-*.rosh` - Player controls
- `test-property-mutations.rosh` - Property changes in events
- `test-trigger-events.rosh` - Event triggering

## Running Tests

```bash
# Build a test
rosh build examples/tests/TEST_NAME.rosh --target phaser --output /tmp/test/

# Verify JavaScript syntax
node --check /tmp/test/game.js

# Open in browser
open /tmp/test/index.html
```

## For Contributors

If you're contributing to Rosh, these test files are useful for:
- Validating new features work correctly
- Regression testing
- Understanding feature implementation
- Creating minimal reproduction cases for bugs

When adding new features, create a corresponding `test-FEATURE.rosh` file.
