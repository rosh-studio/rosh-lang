# Rosh Three.js Demo - AI Prompt Demo

**Version:** 0.1.0
**Date:** 2025-12-17
**Status:** Video-ready demo

## Quick Start

```bash
cd /Users/rdubar/dev/rosh/rosh-lang/demos/rosh-intro/threejs/
python3 -m http.server 8000
# Open http://localhost:8000
```

## The "Wow" Demo

Press backtick (`) to open the console, then:

```
> prompt create a big blue ball
🤖 Thinking...
→ create object ball with type sphere color blue radius 2
✓ Created sphere 'ball'

> set color red
✓ ball.color = red

> prompt make a green cube
🤖 Thinking...
→ create object cube with type cube color green
✓ Created cube 'cube'
```

## Console Commands

| Command | Description |
|---------|-------------|
| `help` | Show all commands |
| `list` | Show all objects in scene |
| `get <obj>` | Select object (sets current context) |
| `get <obj> <prop>` | Get property value |
| `set <prop> <val>` | Set property on current object |
| `set <obj> <prop> <val>` | Set property (explicit object) |
| `create object <name>` | Create cube (default) |
| `create object <name> with type sphere color blue` | Create with properties |
| `prompt <description>` | AI creates object from description |
| `inspect <obj>` | Show object properties |
| `camera reset` | Reset camera view |
| `clear` | Clear console |

## Supported Prompts (Phase 1 - Hardcoded)

- `prompt create a big blue ball` → blue sphere radius 2
- `prompt red ball` → red sphere
- `prompt green cube` → green cube
- `prompt sphere` → orange sphere
- `prompt box` → purple cube

## Controls

- **Mouse drag:** Rotate camera
- **Scroll:** Zoom in/out
- **WASD:** Move camera
- **Q/E:** Move up/down
- **Arrow keys:** Rotate view
- **Backtick (`):** Toggle console

## Files

- `index.html` - HTML template with Three.js r128
- `game.js` - Auto-generated from `game.rosh`
- `assets/` - Asset folder (currently empty)

## Rebuild

```bash
rosh build /Users/rdubar/dev/rosh/rosh-lang/demos/rosh-intro/game.rosh \
    --target threejs \
    --output /Users/rdubar/dev/rosh/rosh-lang/demos/rosh-intro/threejs/
```

## Technical Notes

- Three.js r128 (stable, non-module version for compatibility)
- OrbitControls for camera navigation
- Console uses template literals for HTML injection
- Objects created at runtime get auto-generated UUIDs
- `currentObject` tracks context for `set` commands

## Phase 2 (Future)

- WebSocket connection to Python server
- Real AI integration (Claude/GPT via `prompt exec`)
- Voice input via Web Speech API

---

*This demo proves the "AI-native language for live worlds" vision.*
