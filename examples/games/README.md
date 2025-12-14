# Browser Games (Phaser Transpiler)

Interactive games that compile to JavaScript using the Phaser 3 game framework.

## Quick Start

```bash
# Build any game with automatic asset copying
rosh build examples/games/GAME_NAME.rosh --target phaser --output dist/ --copy-assets

# Run with Python web server (required for sprites)
cd dist/
python3 -m http.server 8000

# Open in browser
open http://localhost:8000
```

**Why web server?** Browsers block local file access for security. The Python web server (built into Python 3) allows sprites to load properly.

## Examples (Ordered by Complexity)

### 1. **simple-game.rosh** - Getting Started
Your first Phaser game. Creates two static objects and demonstrates basic transpilation.

**What you'll learn:**
- Creating game objects
- Setting positions
- String interpolation
- Basic Phaser output

**Run it:**
```bash
rosh build examples/games/simple-game.rosh --target phaser --output dist/
```

---

### 2. **hero-game.rosh** - Player Controls
Adds player controls and event handling.

**What you'll learn:**
- Object inheritance (`create object X from player`)
- Automatic keyboard controls (arrow keys + space)
- Event handlers (`when fire then...`)
- Property mutations
- Event triggering

**Run it:**
```bash
rosh build examples/games/hero-game.rosh --target phaser --output dist/
```

---

### 3. **demo-percentages-hud.rosh** - Layout & UI
Demonstrates percentage positioning and HUD display.

**What you'll learn:**
- Percentage-based positioning (50% = center)
- Explicit HUD creation (`set target to hero`)
- Automatic lives/score display
- Fixed objects (immovable)

**Run it:**
```bash
rosh build examples/games/demo-percentages-hud.rosh --target phaser --output dist/
```

---

### 4. **mvp-demo.rosh** - Complete Feature Showcase ⭐
The full MVP with all features working together.

**What you'll learn:**
- Everything from the above examples, plus:
- Edge behavior (wrap/clamp)
- Collision detection
- Multiple collision handlers
- Object interactions

**Run it:**
```bash
rosh build examples/games/mvp-demo.rosh --target phaser --output dist/
```

---

### 5. **sprite-demo.rosh** - Using Real Graphics (v0.1.7) 🎨
Replace colored rectangles with actual sprite images!

**What you'll learn:**
- Loading sprite images from `assets/` folder
- Automatic fallback to rectangles if sprites missing
- Mixing sprites and rectangles
- Setting up game assets

**Run it:**
```bash
rosh build examples/games/sprite-demo.rosh --target phaser --output dist/
# Then add your PNG files to: dist/assets/
```

**Asset setup:**
```
dist/
├── index.html
├── game.js
└── assets/
    ├── hero.png
    ├── enemy.png
    └── coin.png
```

---

## Key Concepts

### Object Types
- **player** - Automatically controllable (arrow keys + space)
- **object** - Base type (no auto-controls)
- **hud** - UI element (set `target` property)

### Positioning
- Absolute: `set x to 400` (pixels)
- Percentage: `set x to 50%` (responsive)

### Events
- `when fire then` - Triggered by space bar
- `when collision objA objB then` - Triggered by overlap
- `trigger event_name` - Manually trigger events

### Edge Behavior
- `set wrap_edges to true` - Pac-man style (teleport to opposite edge)
- `set wrap_edges to false` - Clamp (stop at boundaries)

### Sprites (v0.1.7)
- `set sprite to "hero.png"` - Load image from `assets/` folder
- **Sprite names must be literal strings** (not variables or expressions)
- Automatic fallback to colored rectangles if sprite missing
- Mix sprites and rectangles in the same game
- Place sprites in: `dist/assets/hero.png`
- Missing sprites show console warnings but don't crash the game

**Example:**
```rosh
create object hero from player
    set x to 50%
    set y to 50%
    set sprite to "hero.png"  # ✅ Literal string - works!
end

# ❌ These won't work (sprite detection is compile-time):
# set sprite to player_sprite  # Variable - won't be detected
# set sprite to "hero" plus ".png"  # Expression - won't be detected
```

---

## Phaser Canvas Size
All games use an 800x600 pixel canvas by default.

- 50% = 400, 300 (center)
- 25% = 200, 150 (top-left quadrant)
- 75% = 600, 450 (bottom-right quadrant)

---

## Next Steps

1. Start with **simple-game.rosh** to understand the basics
2. Try **hero-game.rosh** to add interactivity
3. Explore **demo-percentages-hud.rosh** for UI
4. Study **mvp-demo.rosh** to see everything together
5. Modify the examples to create your own game!

---

## Phaser Transpiler Limitations

The Phaser transpiler supports a **subset of Rosh** focused on browser-based games. Some interpreter features are not available:

**❌ Not Supported in Phaser:**
- `import` - No file imports (Phaser games are self-contained)
- `load`/`save` - No save state commands (use browser localStorage instead)
- `input` - No command-line input (use event handlers for interactivity)
- `if`/`while`/`for` - No control flow yet (planned for future versions)
- Dynamic sprite names - Sprites must be literal strings: `set sprite to "hero.png"`

**✅ Fully Supported:**
- Object creation and properties
- Event handlers (`when ... then`)
- Player controls (automatic for `player` objects)
- Collision detection
- HUD display
- Sprites (literal filenames only)
- Print statements (console.log)
- String interpolation

**Important:** Do not try to transpile MUD examples (from `examples/mud/`) to Phaser. They use `import`, `load`, and `save` commands which are interpreter-only features. MUD examples are designed to run with `rosh run`, not `rosh build --target phaser`.

---

## Troubleshooting

**JavaScript syntax errors?**
```bash
node --check dist/game.js
```

**Need to see the output?**
Check `dist/game.js` to see the generated JavaScript.

**Game not working?**
Open browser console (F12) to see error messages and print statements.

**Sprites not loading?**
- Use Python web server: `cd dist/ && python3 -m http.server 8000`
- Check browser console (F12) for "Sprite not found" warnings
- Verify sprite files exist in `dist/assets/`
- Sprite names must be literal strings: `set sprite to "file.png"` (not variables)
