# Rosh Demo Walkthrough

A guided tour for showing Rosh to clients and partners.

**Time:** 5-10 minutes
**Demo:** Virtual Gallery (rosh.cloud)

---

## Setup

1. Open [rosh.cloud](https://rosh.cloud) in Chrome/Edge
2. Click **Virtual Gallery** demo
3. Wait for 3D scene to load
4. Have a second browser tab ready (for shared world demo)

---

## Part 1: The Console (1 min)

**Say:** "Rosh lets you control 3D worlds with simple text commands."

Press **backtick** ( ` ) to open the console.

```
create red ball
```

**Say:** "Natural language. No code syntax to learn."

```
create big blue cube
```

**Say:** "Modifiers just work - big, small, colors."

```
list
```

**Say:** "You can always see what's in your world."

---

## Part 2: Edit Mode (2 min)

**Say:** "By default, the scene is view-only. Let's enable editing."

```
edit on
```

**Click on the red ball.** It glows.

**Say:** "Click to select. Now commands work on the selection."

```
set color green
```

**Say:** "No need to type the object name."

```
set size 2
```

**Say:** "Resize, recolor, reposition - all with simple commands."

---

## Part 3: Object Control (2 min)

**Say:** "You can take direct control of any object."

```
control
```

**Use arrow keys to move the ball around.**

**Say:** "Arrow keys move in the horizontal plane. Slash and period for up and down."

**Press `/` to rise, `.` to descend.**

**Say:** "This is how visitors could navigate a museum exhibit, or students could explore a 3D model."

---

## Part 4: Physics (1 min)

**Say:** "Let's add some physics."

```
gravity on
```

```
create yellow sphere
```

**The sphere falls and lands on the ground.**

**Say:** "New objects are affected by gravity. The original scene stays fixed."

```
set ball-1 fixed to false
```

**The green ball now falls too.**

**Say:** "You can control what's affected and what isn't."

---

## Part 5: Scenes (1 min)

**Say:** "Rosh supports multiple scenes in one world."

```
scenes
```

**Say:** "This gallery has several rooms."

```
go glasgow
```

**Say:** "Navigate with natural language. These are 3D scanned historical artifacts."

```
go creative
```

**Say:** "Different rooms for different purposes."

---

## Part 6: Shared Worlds (2 min)

**Say:** "Now the really interesting part - shared worlds."

```
connect demo
```

**Open a second browser tab to the same demo.**

In the second tab:
```
connect demo
```

**Say:** "Both clients are now connected to the same world."

In tab 1:
```
create purple cube
```

**Point to tab 2.**

**Say:** "See? It appeared in both. Real-time synchronization."

In tab 2:
```
delete purple-cube-1
```

**Say:** "And deletions sync too. Multiple users, one shared world."

---

## Part 7: Persistence (1 min)

**Say:** "Everything can be saved."

```
save gallery-demo
```

**Reload the page.**

```
load gallery-demo
```

**Say:** "Browser storage for now. Cloud persistence is coming."

---

## Closing

**Say:** "Rosh is a control language for 3D worlds. Same commands work across:"

- **Web** (Three.js, Phaser)
- **Desktop** (Pygame, Godot)
- **VR** (Unity - coming soon)

**Say:** "The vision: speak or type to create, share worlds in real-time, deploy anywhere."

---

## Key Talking Points

### For Museums/Galleries
- "Visitors create art with voice or touch"
- "Curator has admin control from a separate station"
- "Real-time collaboration between stations"

### For Education
- "Students learn programming through natural language"
- "Teacher sees all student work in one shared world"
- "Works on any device with a browser"

### For Enterprise
- "3D training environments built with text commands"
- "Non-technical staff can create and modify content"
- "Deploys to web, desktop, or VR from same source"

---

## If Things Go Wrong

| Problem | Solution |
|---------|----------|
| Console won't open | Try clicking on the canvas first, then ` |
| Commands not recognized | Check spelling, try `help` |
| Objects not appearing | Check `list`, might be in different scene |
| Connect fails | Server might be offline - "You can work offline and save locally" |
| Camera stuck | Click the canvas, use WASD to move |

---

*Rosh v0.2.6 - "Changing Worlds"*
