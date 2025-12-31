# Rosh Physics System

## Overview

ThreeJS-first physics features. These are reference implementations that other emitters can follow.

## Gravity

Enable/disable gravity on objects. Objects fall until they hit the ground level.

### Commands

```
gravity on           # Enable with default strength (9.8)
gravity off          # Disable gravity
gravity 20           # Enable with custom strength
ground 0             # Set ground Y level (default: 0)
```

### Per-Object Control

Objects can opt out of gravity:
```
set ball gravity to false   # This object won't fall
```

## Click-to-Move

Click on the ground to move a designated "player" object to that position.

### Commands

```
clickmove on ball    # Enable, set 'ball' as player
clickmove off        # Disable
player ball          # Change player object
speed 10             # Set move speed (units/second)
```

### How It Works

1. Enable click-to-move with a player object
2. Click anywhere on the ground plane
3. Player object smoothly moves to that position

## API (Adapter Methods)

```javascript
// Gravity
adapter.enableGravity(strength)   // Enable, optional strength
adapter.disableGravity()          // Disable
adapter.setGroundLevel(y)         // Set ground Y
adapter.setObjectGravity(name, enabled)  // Per-object

// Click-to-move
adapter.enableClickToMove(playerName)
adapter.disableClickToMove()
adapter.setPlayer(name)
adapter.setMoveSpeed(speed)

// Must call in animation loop:
adapter.update(deltaTime)
```

## Emitter Support

| Emitter | Gravity | Click-to-Move |
|---------|---------|---------------|
| ThreeJS | ✅ | ✅ |
| Phaser | ❌ | ❌ |
| Pygame | ❌ | ❌ |
| Godot | ❌ | ❌ |

---

*Last updated: 2025-12-31*
