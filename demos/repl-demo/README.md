# 🎮 Rosh Console Demo

**Live coding inside running games - the killer feature for VR/AR consulting**

## Quick Start

```bash
# Build
rosh build demos/repl-demo/game.rosh --target phaser --repl --copy-assets --output demos/repl-demo/dist/

# Run
cd demos/repl-demo/dist && python3 -m http.server 8000

# Open
open http://localhost:8000
```

## Try These Commands

Press ` (backtick) or F12 to open the console, then try:

```
list                     # See all objects
set hero.x to middle     # Move hero to center
set hero.x to 50%        # Same as middle
create dragon at 200 400 # Create new object
properties hero          # Inspect hero
help                     # See all commands
```

## Why This Matters

**Speed:** 1-second iteration (console) vs 10-second iteration (edit-rebuild-refresh)

**Perfect for:**
- Museums: Curators adjust exhibits live during reviews
- VR Training: Trainers modify scenarios mid-session
- Architecture: Designers move furniture while client is in VR

**This is Rosh's unique value proposition vs Unity/Unreal.**

See [full documentation](../../examples/games/README.md#-live-coding-with-the-rosh-console) for details.
