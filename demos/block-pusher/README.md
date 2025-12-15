# Block Pusher - Phaser Demo

A Sokoban-style puzzle game demonstrating Rosh's multi-screen flow, text rendering, and game state management.

## Running the Demo

```bash
cd dist
python3 -m http.server 8000
# Open http://localhost:8000 in browser
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

## Transpiled With

Rosh Phaser Transpiler v0.1.7
