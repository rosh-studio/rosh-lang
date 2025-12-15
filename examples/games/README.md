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

---

## 🎮 Live Coding with the Rosh Console

**⚠️ DEV ONLY - Do not ship to production!**

The Rosh Console allows you to modify running games in real-time without rebuilding. This is perfect for rapid prototyping, debugging, and live demos.

### Enabling the Console

Build with the `--repl` flag:

```bash
rosh build examples/games/sprite-demo.rosh --target phaser --repl --copy-assets --output dist/
cd dist && python3 -m http.server 8000
open http://localhost:8000
```

### Opening the Console

Press **backtick** (`` ` ``) or **F12** to toggle the console overlay.

You'll see a green-on-black terminal interface appear over your game:

```
🎮 ROSH CONSOLE
Press ` or F12 to toggle | Type 'help' for commands

rosh>
```

### Available Commands

The console supports natural language commands with multiple aliases:

| Command | Aliases | Example |
|---------|---------|---------|
| **list** | look, ls, show, objects | `list` |
| **properties** | describe, info, inspect | `properties hero` |
| **get** | - | `get hero.x` |
| **set** | - | `set hero.x to 400` |
| **create** | - | `create bomb at 200 300` |
| **trigger** | fire | `trigger attack` |
| **clear** | cls | `clear` |
| **help** | ? | `help` |

### Command Examples

**List all objects:**
```
list
```
Output: `hero, goblin1, goblin2, coin1, coin2`

**Inspect an object:**
```
properties hero
```
Output shows all properties (x, y, width, height, sprite, etc.)

**Get a specific property:**
```
get hero.x
```
Output: `hero.x = 100`

**Modify properties (watch it move!):**
```
set hero.x to 400
set hero.y to 300
```

**Create new objects live:**
```
create dragon at 200 400
create treasure at 500 300
```

**Trigger custom events:**
```
trigger attack
trigger damage with 50
```

**Clear the console:**
```
clear
```

### Natural Language Support

The console understands natural variations:

```
# All of these work:
list
look
show objects
ls

# Properties can be checked multiple ways:
properties hero
describe hero
info hero
inspect hero
```

### Typo Tolerance

The console uses fuzzy matching to suggest corrections:

```
rosh> properies hero
Did you mean: properties?
```

### Shorthand Syntax

The console and source files support comma-optional position syntax:

```rosh
create bomb at 200, 300    # Both work
create bomb at 200 300
```

**⚠️ Important:** The `at` keyword is now **reserved** and cannot be used as a variable name.

**Limitations:**
- Only accepts numeric literals (not expressions or percentages)
- Must be used with `create object` statements
- Example: `create hero at 100 300` ✅
- Invalid: `create hero at 50% middle` ❌ (use explicit set x/y instead)

**If you need expressions:**
```rosh
create object hero
    set x to 50%
    set y to middle
end
```

### Use Cases

**Rapid Prototyping:**
- Test different positions without rebuilding: `set enemy.x to 500`
- Try new objects on the fly: `create powerup at 300 300`

**Debugging:**
- Check current state: `get player.health`
- List all objects: `list`
- Inspect properties: `properties enemy`

**Live Demos:**
- Modify games during client presentations
- Show real-time adjustments without code changes
- Perfect for VR/AR consulting pitches

**Iteration Speed:**
- Traditional: Edit code → Rebuild → Refresh → Test (10 seconds)
- With console: Press backtick → Type command → See result (1 second)

### Security Warning

**⚠️ The Rosh Console is for development only:**

- **Never deploy with `--repl` to production**
- Build warnings show when REPL is enabled
- The console allows arbitrary code execution
- Only use for local development and trusted demos

**For production builds, omit the `--repl` flag:**
```bash
rosh build game.rosh --target phaser --output dist/  # No REPL
```

### Demo

See `demos/repl-demo/` for a polished example demonstrating the Rosh Console with professional graphics.

### Limitations (Phase 1)

- Limited command set (no if/while/functions)
- Single player only (dev tool)
- No state persistence across sessions
- Commands must match exact formats

For full Rosh syntax support, see Phase 2 (coming soon).

---
