# Block Pusher Demo

A Sokoban-style puzzle game demonstrating Rosh's multi-screen flow, text rendering, and game state management.

**Works in both Phaser (browser) and Pygame (native)!**

## Running the Demo

**Phaser (Browser):**
```bash
cd demos/block-pusher/dist && python3 -m http.server 8000
# Open http://localhost:8000
```

**Pygame (Native):**
```bash
python demos/block-pusher/pygame/game.py
```

## Features Demonstrated

- Multi-screen flow (title → level 1 → level 2 → victory)
- Text objects with properties (font_size, color, visible)
- Circle shapes (`set shape to "circle"`)
- Wall/obstacle collision
- State management across levels
- String interpolation (`"Moves: {state.moves}"`)
- Discrete key events (arrow keys, space, R)
- Function definitions and calls
- Sprite loading with fallback

## Controls

- **Arrow keys**: Move player
- **Space**: Start game / Next level
- **R**: Restart current level

## Files

- `game.rosh` - Rosh source code
- `dist/game.js` - Generated Phaser JavaScript
- `dist/index.html` - HTML wrapper
- `assets/player.png` - Player sprite
- `levels.txt` - ASCII level documentation
- `SPEC.md` - Full game specification

## Rebuild

**Phaser:**
```bash
rosh build demos/block-pusher/game.rosh --target phaser --output demos/block-pusher/dist/ --copy-assets
```

**Pygame:**
```bash
rosh build demos/block-pusher/game.rosh --target pygame --output demos/block-pusher/pygame/
```

## Transpiled With

Rosh Phaser Transpiler v0.1.10 / Pygame Transpiler v0.1.10
