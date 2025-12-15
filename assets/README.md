# Rosh Game Assets

This folder contains game assets (sprites, sounds) for Rosh demos and examples.

## Structure

```
assets/
├── sprites/        # Image files (.png) - DISTRIBUTED
├── sounds/         # Sound effects (.ogg, .wav) - DISTRIBUTED
├── _library/       # Full asset packs - NOT DISTRIBUTED (gitignored)
├── CREDITS.md      # Attribution for all assets
└── README.md       # This file
```

## Distributed Assets

The `sprites/` and `sounds/` folders contain minimal assets needed to run Rosh demos:

**Sprites:**
- `hero.png`, `enemy.png`, `coin.png` - Basic game sprites
- `player.png`, `enemyShip.png`, `laserGreen.png` - Space shooter sprites
- `space-invader-32x32-6f.png` - Example sprite sheet

**Sounds:**
- `laser1.ogg` - Firing sound
- `lose1.ogg`, `lose3.ogg` - Hit/explosion sounds

All from [Kenney.nl](https://kenney.nl) (CC0 Public Domain).

## Getting More Assets

For additional assets, download directly from:

- **Kenney Game Assets**: https://kenney.nl/assets
  - Free, CC0 licensed (public domain)
  - 40,000+ game assets
  - Sprites, sounds, music, UI elements

- **OpenGameArt**: https://opengameart.org
  - Community-contributed assets
  - Various licenses (check each asset)

Place downloaded assets in the `_library/` folder (gitignored) or directly in your game's local `assets/` folder.

## Using Assets in Your Games

```rosh
# Sprites
create object player
    set sprite to "hero.png"
end

# The CLI will search for assets in:
# 1. Your game's local assets/ folder
# 2. rosh-lang/assets/sprites/ and assets/sounds/
```

Build with `--copy-assets` to automatically copy required assets to your output folder:

```bash
rosh build game.rosh --target phaser --output dist/ --copy-assets
```

## License

All distributed assets are CC0 (Public Domain) from Kenney.nl.
See `CREDITS.md` for full attribution.
