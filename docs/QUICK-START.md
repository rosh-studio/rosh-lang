# Rosh Quick Start Guide

**Get creating in 5 minutes.**

## 1. Open a Demo

Visit [rosh.cloud](https://rosh.cloud) and click on **Virtual Gallery** (or any Three.js demo).

## 2. Open the Console

Press the **backtick key** ( ` ) to open the command console.

You'll see a dark panel at the bottom of the screen with a text input.

## 3. Try Some Commands

Type these commands and press Enter:

```
create red ball
```
A red sphere appears in the scene.

```
create blue cube
```
A blue cube appears.

```
list
```
Shows all objects in the current scene.

## 4. Enable Edit Mode

By default, you're in **view-only mode**. To select and control objects:

```
edit on
```

Now you can:
- **Click any object** to select it (it glows)
- **Click empty space** to deselect

## 5. Control an Object

With edit mode on:

```
control ball
```

Or just click an object and type:
```
control
```

Now use the keyboard:
| Key | Action |
|-----|--------|
| ↑ | Move forward |
| ↓ | Move backward |
| ← | Move left |
| → | Move right |
| `/` | Move up |
| `.` | Move down |

## 6. Modify Objects

Select an object (click it or use `select ball`), then:

```
set color green
```

```
set size 2
```

```
delete
```

## 7. Try Gravity

```
gravity on
```

Create a new ball - it falls!

```
create yellow ball
```

Scene objects don't fall (they're fixed by default). Only objects you create in the console are affected.

## 8. Save Your Work

```
save myworld
```

Reload the page, then:

```
load myworld
```

Your objects are restored.

## 9. Explore Scenes

```
scenes
```

Lists available scenes. Then:

```
go glasgow
```

Navigates to that scene.

## 10. Connect to Shared World

```
connect demo
```

Now any objects you create are shared with other connected users in real-time!

---

## What's Next?

- See [COMMAND-REFERENCE.md](COMMAND-REFERENCE.md) for all commands
- See [DEMO-WALKTHROUGH.md](DEMO-WALKTHROUGH.md) for a guided tour
- See [KNOWN-LIMITATIONS.md](KNOWN-LIMITATIONS.md) for current constraints

---

*Rosh v0.2.6 - "Changing Worlds"*
