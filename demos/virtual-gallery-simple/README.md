# Virtual Gallery Demo

An interactive 3D museum exhibit where visitors can create and explore art using voice or text commands.

## Overview

This demo showcases Rosh's natural language interface for 3D scene creation. Built for Glasgow Life as a concept for interactive museum exhibits.

## Features

- **Voice Control**: Speak commands like "create a big red ball" or "make the sphere spin"
- **Text Commands**: Type in the console (press ` to toggle)
- **Save/Load**: Persist your creations across browser sessions
- **Natural Language**: Commands like "make it bigger" or "hide the cube" just work

## Commands

### Creating Objects
```
create ball                    # Create a ball
create big red sphere          # Create with modifiers
make a yellow cube             # Natural language variant
```

### Modifying Objects
```
set ball color to blue         # Change properties
make ball bigger               # Natural modifiers
hide sculpture                 # Toggle visibility
```

### Saving & Loading
```
save                           # Save to default slot
save mywork                    # Save to named slot
load                           # Load from default slot
load mywork                    # Load from named slot
reset scene                    # Clear saved data and reload
```

### Other Commands
```
list                           # Show all objects
look ball                      # Inspect an object
delete ball                    # Remove an object
undo / redo                    # Undo/redo changes
help                           # Show all commands
```

## Technical Notes

- **Target**: Three.js (WebGL)
- **Source**: `rosh-lang/demos/virtual-gallery/game.rosh`
- **Persistence**: Uses localStorage for save/load

## Museum Deployment Vision

For a real museum installation:
1. **Session Save** (localStorage) - instant, local, private
2. **Gallery Submission** - visitor chooses to submit their creation
3. **Curator Review** - museum staff reviews submissions
4. **Featured Works** - approved pieces appear in a public gallery

## Building

```bash
cd rosh-lang
uv run python -m rosh.cli build demos/virtual-gallery/game.rosh --target threejs --output build/
```
