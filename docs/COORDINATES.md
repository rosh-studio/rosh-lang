# Rosh Coordinate System

## Overview

Rosh uses a **normalized coordinate system** that adapts to different engines.

## 2D Coordinates (Phaser, Pygame)

- Origin: Top-left (0, 0)
- X increases rightward
- Y increases downward
- Default canvas: 800 x 600

```
(0,0) ──────────────► X (800)
  │
  │
  │
  ▼
  Y (600)
```

## 3D Coordinates (ThreeJS, Godot)

- Origin: Center of scene
- X increases rightward
- Y increases upward (ThreeJS) / downward (Godot - converted)
- Z increases toward camera (ThreeJS)

## Position Syntax

```rosh
# Absolute (pixels)
set ball x to 100px
set ball position to 100px, 200px

# Percentage of canvas
set ball x to 50%
set ball position to center  # alias for 50%, 50%

# Relative
move ball by 10, 0
```

## Units

| Unit | Meaning | Example |
|------|---------|---------|
| (none) | Pixels (default in 2D) | `100` |
| `px` | Explicit pixels | `100px` |
| `%` | Percentage of canvas | `50%` |

## Engine Differences

| Feature | ThreeJS | Phaser | Pygame | Godot |
|---------|---------|--------|--------|-------|
| Y direction | Up | Down | Down | Down (2D) / Up (3D) |
| Origin | Center | Top-left | Top-left | Top-left (2D) |
| Default units | World units | Pixels | Pixels | Pixels |

## Future: 3D Extensions

For ThreeJS/Godot 3D:
- `z` property for depth
- `rotation` with x, y, z components
- Camera-relative positioning
