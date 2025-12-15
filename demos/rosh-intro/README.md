# Rosh Intro Demo

Animated loading screen showing the "Rosh" logo zooming from small to large.

**Works in both Phaser (browser) and Pygame (native)!**

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

## Rebuild

**Phaser:**
```bash
rosh build demos/rosh-intro/game.rosh --target phaser --output demos/rosh-intro/phaser/
```

**Pygame:**
```bash
rosh build demos/rosh-intro/game.rosh --target pygame --output demos/rosh-intro/pygame/
```

## Technical Notes

This demo showcases the dynamic `font_size` support added in v0.1.10:

- Phaser: Uses `setFontSize()` method for runtime font changes
- Pygame: Uses `set_font_size()` method that recreates the font object

Both transpilers now support changing font size in `when update then` loops.
