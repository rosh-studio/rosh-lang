# Virtual Gallery Demo

Interactive multi-room museum experience with voice/text console.

## Quick Test (from rosh-lang directory)

Build, validate, and open in browser:

```bash
uv run rosh build demos/virtual-gallery/game.rosh --target threejs --output /tmp/virtual-gallery-demo && node --check /tmp/virtual-gallery-demo/game.js && open /tmp/virtual-gallery-demo/index.html
```

## With Live Server (if you need console/network features)

```bash
uv run rosh build demos/virtual-gallery/game.rosh --target threejs --output /tmp/virtual-gallery-demo && cd /tmp/virtual-gallery-demo && python3 -m http.server 8000 &; sleep 1 && open http://localhost:8000
```

## Scenes

- **Lobby** - Welcome & instructions
- **Abstract** - Kinetic art with orbiting spheres
- **Sculpture** - Static forms on pedestals
- **Creative** - Visitor creation space

## Console Commands

Press `` ` `` (backtick) to open console.

- `go <scene>` - Navigate to a scene
- `scenes` - List available scenes
- `list` / `list all` / `list <scene>` - Show objects
- `create red sphere` - Create objects
- `help` - Full command list
