# Rosh Edit Mode

## Overview

Edit mode enables interactive object selection and control. When OFF (default), the scene is view-only. When ON, users can click to select objects and control them.

**ThreeJS-first feature.** Other emitters do not yet implement this.

## Commands

```
edit on              # Enable edit mode
edit off             # Disable edit mode (view only)
edit                 # Show current status
```

## Selection

When edit mode is ON:

```
[click object]       # Select it (highlights with glow)
[click empty space]  # Deselect
select ball          # Select by name
sel ball             # Short form
deselect             # Clear selection
desel                # Short form
```

## Control

Control an object with arrow keys:

```
control ball         # Control the named object
control              # Control selected object (if one is selected)
player ball          # Alias for backwards compatibility
```

### Control Keys

| Key | Action |
|-----|--------|
| Arrow Up | Move forward (-Z) |
| Arrow Down | Move backward (+Z) |
| Arrow Left | Move left (-X) |
| Arrow Right | Move right (+X) |
| `/` | Move up (+Y) |
| `.` | Move down (-Y) |

## Commands Using Selection

These commands use the selected object when no name is given:

```
set color red        # Set property on selected object
delete               # Delete selected object
look                 # Examine selected object
control              # Control selected object
```

## API (Adapter Methods)

```javascript
// Edit mode
adapter.enableEditMode()      // Enable selection/control
adapter.disableEditMode()     // Disable (view only)
adapter.isEditMode()          // Returns boolean

// Selection
adapter.getSelectedObject()   // Returns name or null
adapter.getSelectedObjectData()  // Returns full object data
adapter.selectByName(name)    // Select by name
adapter.deselect()            // Clear selection
```

## Emitter Support

| Emitter | Edit Mode | Selection | Control |
|---------|-----------|-----------|---------|
| ThreeJS | ✅ | ✅ | ✅ |
| Phaser | ❌ | ❌ | ❌ |
| Pygame | ❌ | ❌ | ❌ |
| Godot | ❌ | ❌ | ❌ |

## Use Cases

### Interactive Exploration
```
edit on
[click objects to learn about them]
look                 # See details of selected
```

### Shared World Editing
```
connect myworld
edit on
create red ball
control              # Move the ball around
```

### Scene Building
```
edit on
create blue cube
set size 2
set x 5
create red sphere
control              # Position it with arrow keys
edit off             # Lock scene from changes
```

---

*Last updated: 2025-12-31*
