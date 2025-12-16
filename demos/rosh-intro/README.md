# Rosh Intro Demo

Date: 2025-12-16
Author: Claude Opus 4.5
Project Lead: rdubar

Animated loading screen showing the "Rosh" logo.

**Works in Phaser (2D browser), Pygame (2D native), and Three.js (3D browser)!**

## Features

- "Rosh" text zooms from 8px to 96px font size
- "Happy coding" tagline fades in after logo zoom
- Decorative pulsing dot
- Demonstrates dynamic `font_size` animation

## Run in Phaser (Browser)

```bash
cd demos/rosh-intro/phaser
python3 -m http.server 8000
# Open http://localhost:8000
```

## Run in Pygame (Native)

```bash
cd demos/rosh-intro/pygame
python3 game.py
```

## Run in Three.js (3D Browser)

```bash
cd demos/rosh-intro/threejs
python3 -m http.server 8000
# Open http://localhost:8000
```

Controls:
- WASD: Move camera
- Q/E: Move up/down
- Arrow keys: Rotate view
- Mouse drag: Orbit camera
- Scroll: Zoom
- Backtick (`): Open REPL console

## Rebuild

**Phaser:**
```bash
rosh build demos/rosh-intro/game.rosh --target phaser --output demos/rosh-intro/phaser/
```

**Pygame:**
```bash
rosh build demos/rosh-intro/game.rosh --target pygame --output demos/rosh-intro/pygame/
```

**Three.js:**
```bash
rosh build demos/rosh-intro/game.rosh --target threejs --output demos/rosh-intro/threejs/
```

## Technical Notes

- Phaser: Uses `setFontSize()` method for runtime font changes
- Pygame: Uses `set_font_size()` method that recreates the font object
- Three.js: Uses canvas-based text sprites with OrbitControls navigation

All three transpilers demonstrate "one language, many worlds" - the same Rosh source runs on 2D web, 2D native, and 3D web.
