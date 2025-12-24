# Rosh Godot Emitter

**Version:** v0.2.1 (2025-12-24)
**Status:** Working - 2D arcade mode + 3D world mode

The Godot emitter transpiles Rosh source code to GDScript for Godot Engine 4.x.

---

## Quick Start

### Build a Rosh game for Godot

```bash
cd rosh-lang

# Build with CLI (recommended)
uv run rosh build demos/space-shooter/game.rosh \
    --target godot \
    --output /tmp/my-godot-game/ \
    --copy-assets

# Or use the deploy script for all demos
./scripts/deploy-demos.sh
```

### Run in Godot

```bash
# Option 1: Open in Godot Editor
open -a Godot /tmp/my-godot-game/project.godot

# Option 2: Run from command line (macOS)
/Applications/Godot.app/Contents/MacOS/Godot --path /tmp/my-godot-game/
```

Then press **F5** or click **Play** in the Godot editor.

---

## Requirements

- **Godot 4.2+** (tested with 4.5.1)
- Download from: https://godotengine.org/download
- **Python 3.11+** with uv for building

---

## Generated Output

The emitter produces a complete Godot project:

```
output-folder/
├── main.gd          # GDScript game logic
├── main.tscn        # Godot scene file
├── project.godot    # Project configuration
└── assets/          # Copied sprites, sounds (if --copy-assets)
```

**Note:** This is a Godot *project* (source code), not a compiled executable. To create a standalone app, use Godot's export feature.

---

## Modes

### 2D Arcade Mode

Set in your .rosh file:
```rosh
config mode is "arcade"
config canvas_width is 800
config canvas_height is 600
```

Features:
- 2D coordinate system (0,0 at top-left)
- Sprite rendering via `draw_texture()`
- Rectangle primitives for objects without sprites
- Text rendering with alignment

### 3D World Mode (default)

```rosh
config mode is "world"
```

Features:
- 3D coordinate system
- Primitive shapes (box, sphere, cylinder)
- WASD + mouse camera controls
- Label3D text with billboard mode

---

## Console Commands

All emitters implement the same console commands (spec: `spec/v0.2.0/rosh-console.toml`):

| Command | Example | Description |
|---------|---------|-------------|
| `list` | `list` | Show all objects |
| `look` | `look player` | Inspect object properties |
| `set` | `set player x to 100` | Modify property |
| `create` | `create big blue sphere` | Create object with modifiers |
| `delete` | `delete box-1` | Remove object |
| `hide` | `hide player` | Set visible = false |
| `show` | `show player` | Set visible = true |
| `move` | `move player to 100 200` | Set x, y position |
| `help` | `help` | Show available commands |

Toggle console: **Backtick (`)** key

---

## Sprite Support

Objects with a `sprite` property render as textures:

```rosh
define player
    set x to 400
    set y to 500
    set w to 64
    set h to 64
    set sprite to "player.png"
end
```

The emitter:
1. Detects `sprite` property during IR analysis
2. Declares texture variables: `var _tex_player_png: Texture2D`
3. Loads textures in `_ready()`: `_tex_player_png = load("res://player.png")`
4. Renders in `_draw()`: `draw_texture(_tex_player_png, Vector2(x, y))`

**Asset location:** Sprites must be in the Godot project root (copied via `--copy-assets`).

---

## Input Handling

### Continuous Keys (held down)
```rosh
on key "left" held
    change player x by -5
end
```

### Key Press Events (single press)
```rosh
on key "space" pressed
    call fire_bullet
end
```

### Supported Keys
- Arrow keys: `left`, `right`, `up`, `down`
- Letters: `a`-`z`
- Special: `space`, `enter`, `escape`, `tab`

---

## Functions

```rosh
define function fire_bullet
    create bullet
    set bullet x to player x
    set bullet y to player y minus 20
end
```

Emits as GDScript:
```gdscript
func fire_bullet():
    # ... implementation
```

---

## Conditionals

```rosh
if player x is less than 0 then
    set player x to 0
end

if score is greater than high_score then
    set high_score to score
    call show_message with "New high score!"
end
```

---

## Known Limitations

### Not Implemented
- Animation/tweening
- Sound playback (assets can be included but not wired up)
- Physics/collision detection (handled in game logic, not engine)
- `create text name` syntax (workaround: `create object` + `set text`)

### Known Issues
- Console anchor warnings on startup (cosmetic, non-blocking)
- 3D mode camera requires right-click to rotate

### Godot Version
- Tested with Godot 4.5.1
- Should work with any Godot 4.2+
- Godot 3.x is **not supported** (different API)

---

## Architecture

```
┌─────────────────┐
│  game.rosh      │  Rosh source code
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Lexer + Parser │  Tokenize and parse
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  IR Transformer │  AST → IR (target-agnostic)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  GodotEmitter   │  IR → GDScript
│  (godot.py)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  main.gd        │  GDScript output
│  main.tscn      │  Scene file
│  project.godot  │  Project config
└─────────────────┘
```

The emitter is in `src/rosh/emitters/godot.py` (~1400 lines).

---

## Example: Space Shooter

**Source:** `demos/space-shooter/game.rosh` (~865 lines)
**Output:** `rosh.cloud/projects/space-shooter-godot/`

Features demonstrated:
- Sprite rendering (player, enemies, bullets)
- Keyboard input (O/P to move, Space to fire)
- Collision detection (game logic)
- Score tracking and display
- Game states (title, playing, game over)
- REPL console for debugging

### Controls

| Key | Action |
|-----|--------|
| O / P | Move left / right |
| Space | Fire / Start game |
| R | Restart after game over |
| Arrow keys | Alternative movement |
| Backtick | Toggle REPL console |

---

## Exporting to Standalone App

To create an executable (no Godot required to run):

1. Open project in Godot Editor
2. **Editor → Manage Export Templates → Download**
3. **Project → Export → Add** (macOS/Windows/Linux)
4. **Export Project**

This creates a standalone binary users can run without installing Godot.

---

## Troubleshooting

### "Can't open project"
- Ensure Godot 4.2+ is installed
- Check that `project.godot` exists in the output folder

### Console not appearing
- Press backtick (`) to toggle
- Check that the game window has focus

### Sprites not showing
- Verify sprite files are in the project root
- Check file names match exactly (case-sensitive)
- Ensure `--copy-assets` was used during build

### "Error: Invalid call"
- Check Godot version (must be 4.x, not 3.x)
- Look at the specific line number in the error

---

## Related Documentation

- `ARCHITECTURE.md` - Overall Rosh system design
- `SPEC-AUDIT-FULL.md` - Complete command specification
- `../spec/v0.2.0/rosh-console.toml` - Console command spec
- `proposals/Rosh_Godot_Consultancy_Proposal.md` - Business/consultancy context

---

*Generated by Rosh Godot Emitter v0.2.1 | December 2025*
