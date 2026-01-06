# Rosh Adapter Interface

Adapters connect the shared `rosh-runtime.js` to specific game engines.

## Required Properties

| Property | Type | Description |
|----------|------|-------------|
| `platform` | string | Engine name shown in welcome message (e.g., "Three.js", "Phaser") |

## Required Methods (Core)

| Method | Returns | Description |
|--------|---------|-------------|
| `getSupportedTypes()` | string[] | List of primitive types this engine can create |
| `createObject(type, name, options)` | {success, name, object, color?, size?, knownType?, description?} | Create a new object |
| `deleteObject(name)` | {success, error?} | Remove an object |
| `getObjectNames()` | string[] | List all object names |
| `getObjects()` | [{name, object, type, visible}] | List all objects with details |
| `getObject(name)` | {name, object, type} \| null | Get single object |
| `getObjectDetails(name)` | {type, color, position, scale, visible, description?} \| null | Full object info |
| `getProperty(name, prop)` | any | Get object property value |
| `setProperty(name, prop, value)` | {success, error?} | Set object property |
| `setVisible(name, visible)` | {success} | Show/hide object |
| `moveObject(name, {x, y, z?})` | {success} | Set absolute position |
| `getPosition(name)` | {x, y, z?} \| null | Get object position |

## Optional Methods (Enhanced)

| Method | Returns | Description |
|--------|---------|-------------|
| `cloneObject(name)` | {success, name, object} | Duplicate an object |
| `restoreObject(name, state)` | {success} | Restore deleted object (undo) |
| `countObjects(type?)` | number | Count objects, optionally by type |
| `getObjectsByType(type)` | [{name, object}] | Get all objects of a type |
| `moveObjectRelative(name, dir, amount)` | {success} | Move forward/back/left/right/up/down |

## Optional Methods (Scenes)

| Method | Returns | Description |
|--------|---------|-------------|
| `getScenes()` | string[] | List available scenes |
| `getCurrentScene()` | string | Current scene name |
| `gotoScene(name)` | {success} | Switch to scene |

## Optional Methods (Selection/Edit)

| Method | Returns | Description |
|--------|---------|-------------|
| `selectByName(name)` | string \| null | Select object, return name |
| `deselect()` | {success} | Clear selection |
| `getSelectedObject()` | string \| null | Get selected object name |
| `enableEditMode()` | {success} | Enable click-to-select |
| `disableEditMode()` | {success} | Disable edit mode |
| `isEditMode()` | boolean | Check if edit mode active |

## Optional Methods (Physics - 3D)

These are Three.js-specific and can be omitted for 2D engines:

| Method | Description |
|--------|-------------|
| `enableGravity(strength)` | Enable gravity simulation |
| `disableGravity()` | Disable gravity |
| `setGroundLevel(y)` | Set ground plane |
| `enableClickToMove(player)` | Click-to-move navigation |
| `disableClickToMove()` | Disable click-to-move |
| `setPlayer(name)` | Set player object |
| `setMoveSpeed(speed)` | Set movement speed |
| `enablePlayerKeyboard(player)` | WASD/arrow controls |
| `disablePlayerKeyboard()` | Disable keyboard controls |

## Optional Methods (Persistence)

| Method | Returns | Description |
|--------|---------|-------------|
| `saveGame(slot)` | void | Save state to localStorage |
| `loadGame(slot)` | boolean | Load state from localStorage |

## Optional Methods (Advanced)

| Method | Returns | Description |
|--------|---------|-------------|
| `handleCustomCommand(cmd, parts)` | boolean | Handle engine-specific commands |
| `deepSearch(query)` | object[] | Semantic/fuzzy search |
| `getAllObjects()` | object[] | Get all objects (for twin sync) |

## createObject Options

```javascript
options = {
  name: string,        // Override auto-generated name
  modifiers: string[], // ['big', 'red', etc.]
  color: string,       // Direct color override
  size: number,        // Direct scale override
  x: number,           // Position
  y: number,
  z: number            // Optional for 2D
}
```

## Asset Fallback Cascade

Objects can have multiple representations. Adapters should implement this fallback:

### Three.js (3D)
1. **3D model** (GLB) - Full mesh
2. **2D sprite** (PNG) - Billboard facing camera
3. **3D primitive** (shape) - Box, sphere, etc.
4. **Placeholder** - Colored box with label

### Phaser (2D)
1. **2D sprite** (PNG) - Full sprite
2. **2D shape** - Rectangle, ellipse, etc.
3. **Placeholder** - Colored rect with label

### known_objects.toml structure

```toml
[orc]
description = "A fierce green orc warrior"  # Text fallback

[orc.2d]
sprite = "sprites/orc.png"   # Primary for 2D
color = "green"              # Fallback shape color
shape = "rectangle"

[orc.3d]
model = "3d_glb/orc.glb"     # Primary for 3D
sprite = "sprites/orc.png"   # Fallback: billboard
shape = "box"                # Fallback: primitive
color = 0x228b22
```

## 2D vs 3D Notes

- For 2D engines (Phaser), `z` can be ignored or used for depth/layer
- Physics methods are optional - Phaser has its own physics system
- `moveObjectRelative` directions: 2D uses left/right/up/down, 3D adds forward/back
