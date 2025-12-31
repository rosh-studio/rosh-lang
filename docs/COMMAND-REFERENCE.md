# Rosh Command Reference

Complete list of console commands for Rosh v0.2.6.

---

## Object Creation

| Command | Description | Example |
|---------|-------------|---------|
| `create <type>` | Create an object | `create ball` |
| `create <color> <type>` | Create with color | `create red cube` |
| `create <size> <color> <type>` | Create with size and color | `create big blue sphere` |
| `create <count> <type>s` | Create multiple | `create 10 balls` |
| `clone <name>` | Duplicate an object | `clone ball-1` |
| `delete <name>` | Remove an object | `delete ball-1` |
| `delete` | Remove selected object | (requires edit mode) |

**Size modifiers:** tiny, small, medium, big, large, huge, giant

**Colors:** red, green, blue, yellow, cyan, magenta, white, black, orange, purple, pink, gray, gold, silver

**Types:** ball, sphere, cube, box, cylinder, cone, torus, plane

---

## Object Properties

| Command | Description | Example |
|---------|-------------|---------|
| `set <obj> <prop> to <value>` | Set a property | `set ball color to red` |
| `set <prop> to <value>` | Set on selected object | `set color to blue` |
| `get <name>` | Get object reference | `get ball-1` |
| `look <name>` | Examine object details | `look ball-1` |
| `look` | Examine selected object | (requires edit mode) |
| `x <name>` | Short for look | `x ball-1` |

**Common properties:**
- `color` - red, blue, #ff0000, etc.
- `size` - scale factor (1 = normal)
- `x`, `y`, `z` - position
- `visible` - true/false
- `fixed` - true/false (gravity immunity)
- `spin` - "x y z" rotation speeds
- `bounce`, `pulse`, `orbit` - animations

---

## Edit Mode & Selection

| Command | Description |
|---------|-------------|
| `edit on` | Enable edit mode (allows selection/control) |
| `edit off` | Disable edit mode (view only) |
| `edit` | Show current edit mode status |
| `select <name>` | Select object by name |
| `sel <name>` | Short for select |
| `deselect` | Clear selection |
| `desel` | Short for deselect |

**Mouse interactions (edit mode on):**
- Click object → select it (glows)
- Click empty space → deselect

---

## Object Control

| Command | Description |
|---------|-------------|
| `control <name>` | Control object with keyboard |
| `control` | Control selected object |
| `player <name>` | Alias for control |
| `speed <n>` | Set movement speed |

**Control keys:**
| Key | Action |
|-----|--------|
| Arrow Up | Move forward (-Z) |
| Arrow Down | Move backward (+Z) |
| Arrow Left | Move left (-X) |
| Arrow Right | Move right (+X) |
| `/` | Move up (+Y) |
| `.` | Move down (-Y) |

---

## Physics

| Command | Description | Example |
|---------|-------------|---------|
| `gravity on` | Enable gravity | |
| `gravity off` | Disable gravity | |
| `gravity <n>` | Set gravity strength | `gravity 20` |
| `ground <y>` | Set ground level | `ground -5` |

**Gravity rules:**
- Scene objects are `fixed` by default (don't fall)
- Console-created objects fall when gravity is on
- Text, HUD, sprites never fall
- Override with `set ball fixed to false`

---

## Scenes & Navigation

| Command | Description | Example |
|---------|-------------|---------|
| `scenes` | List all scenes | |
| `go <scene>` | Navigate to scene | `go glasgow` |
| `list` | List objects in current scene | |
| `list all` | List all objects (all scenes) | |
| `list <scene>` | List objects in specific scene | `list lobby` |

---

## Persistence

| Command | Description | Example |
|---------|-------------|---------|
| `save <slot>` | Save to browser storage | `save myworld` |
| `load <slot>` | Load from browser storage | `load myworld` |
| `save` | Save to default slot | |
| `load` | Load from default slot | |

---

## Shared Worlds (Project Twin)

| Command | Description | Example |
|---------|-------------|---------|
| `connect <world>` | Join a shared world | `connect demo` |
| `disconnect` | Leave shared world | |
| `say <message>` | Chat with other users | `say hello` |

When connected:
- Objects you create appear for all users
- Other users' creations appear for you
- `list` shows shared objects

---

## History & Undo

| Command | Description |
|---------|-------------|
| `undo` | Undo last action |
| `redo` | Redo undone action |
| `undo <n>` | Undo n actions |
| `repeat` | Repeat last command |
| `:r` | Short for repeat |

---

## Visibility

| Command | Description | Example |
|---------|-------------|---------|
| `hide <name>` | Hide object | `hide ball-1` |
| `show <name>` | Show object | `show ball-1` |
| `hide` | Hide selected object | |
| `show` | Show selected object | |

---

## Camera (ThreeJS)

| Command | Description |
|---------|-------------|
| `camera reset` | Reset camera to default |

**Camera controls:**
- WASD - move camera
- Q/E - up/down
- Mouse drag - rotate view

---

## Utility

| Command | Description |
|---------|-------------|
| `help` | Show help |
| `clear` | Clear console output |
| `credits` | Show credits |
| `count` | Count all objects |
| `count <type>` | Count objects of type |

---

## Voice Input (Browser)

Hold **Ctrl+Space** and speak. Release to execute.

Examples:
- "create red ball"
- "go to the lobby"
- "make it bigger"

---

## AI Prompt

| Command | Description | Example |
|---------|-------------|---------|
| `prompt <request>` | Ask AI for help | `prompt make a solar system` |

---

*Rosh v0.2.6 - "Changing Worlds"*
