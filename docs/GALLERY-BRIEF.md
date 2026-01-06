# Rosh Object Showcase - Cross-Platform Gallery Brief

## Goal
Create a simple virtual gallery that demonstrates the same Rosh code running on multiple platforms:
- **Three.js** (3D first-person view)
- **Phaser** (2D top-down view)
- **CLI** (text descriptions)

## Key Demo Points
1. Same object definitions work across all platforms
2. Objects render appropriately for each platform (3D models, 2D shapes, text)
3. Interactive console works identically everywhere
4. Real-time sync between viewers (Project Twin)

## Gallery Layout
Simple rectangular room with:
- 4 walls
- 3-5 pedestals displaying objects
- Text labels for each object
- Entry point

```
+---------------------------+
|                           |
|   [pedestal]  [pedestal]  |
|      orc        banana    |
|                           |
|        [pedestal]         |
|          ball             |
|                           |
|   [pedestal]  [pedestal]  |
|     tree        coin      |
|                           |
+-----+     entry     +-----+
```

## Objects to Display
From `known_objects.toml`:
- **orc** - Character (has 3D model)
- **banana** - Food item (has 3D model)
- **ball** - Simple shape
- **tree** - Nature (has 3D model)
- **coin** - Collectible

Each has: 3D model/shape, 2D shape+color, text description

## Technical Requirements
- Single `gallery.rosh` source file
- Compiles to all three targets
- Objects defined in `known_objects.toml` (easy to add more)
- Console overlay for live interaction

## Success Criteria
- Visitor can walk through in 3D
- Visitor can see top-down in 2D
- `look orc` shows description on all platforms
- `create apple` adds new object in real-time
- Changes sync between connected viewers

## Questions for Review
1. Is this scope right for a demo? Too simple? Too complex?
2. Any objects that would showcase the platform differences better?
3. Should we add any interactive elements beyond the console?
4. What about lighting/atmosphere differences between 2D and 3D?
