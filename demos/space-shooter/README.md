# Space Shooter Demo

A classic arcade space shooter demonstrating Rosh's real-time game loop, smooth movement, object pools, collision detection, and sound effects.

**Works in both Phaser (browser) and Pygame (native)!**

## Running the Demo

**Pygame (Native):**
```bash
python demos/space-shooter/pygame/game.py
```

**Phaser (Browser):**
```bash
cd demos/space-shooter/phaser && python3 -m http.server 8000
# Open http://localhost:8000
```

## Features Demonstrated

- **Per-frame updates** (`when update then`) - continuous game loop
- **Smooth movement** (`when while_key_left/right then`) - held key detection
- **Object pools** - 5 bullets and 4 enemies managed efficiently
- **Collision detection** - bullet-enemy and enemy-player
- **Negative coordinates** (`set y to -50`) - off-screen spawning
- **Sprites** with colored shape fallback
- **Sound effects** (`play sound "file.ogg"`) - cached playback
- **Score and lives system**
- **Game over and restart flow**

## Controls

- **Left/Right arrows**: Move player (smooth continuous)
- **Space**: Fire bullet / Start game
- **R**: Restart after game over

## Files

- `game.rosh` - Rosh source code (~540 lines)
- `pygame/game.py` - Generated Pygame Python (~500 lines)
- `pygame/assets/` - Kenney space shooter sprites and sounds

## Assets

Sprites and sounds from [Kenney.nl](https://kenney.nl) (CC0):
- `player.png` - Player ship
- `enemyShip.png` - Enemy ships
- `laserGreen.png` - Bullet/laser
- `laser1.ogg` - Firing sound
- `lose1.ogg` - Enemy destroyed
- `lose3.ogg` - Player hit

## New Rosh Syntax

```rosh
# Per-frame game loop
when update then
    # runs every frame (60fps)
    set bullet.y to bullet.y minus 10
end

# Smooth continuous movement (key held)
when while_key_left then
    set player.x to player.x minus 5
end

# Sound effects
play sound "laser1.ogg"
```

## Rebuild

**Phaser:**
```bash
rosh build demos/space-shooter/game.rosh --target phaser --output demos/space-shooter/phaser/ --copy-assets
# Note: Sound files need to be copied manually for now
cp demos/space-shooter/pygame/assets/*.ogg demos/space-shooter/phaser/assets/
```

**Pygame:**
```bash
rosh build demos/space-shooter/game.rosh --target pygame --output demos/space-shooter/pygame/
```

## Transpiled With

Rosh Phaser Transpiler v0.1.10 / Pygame Transpiler v0.1.10
