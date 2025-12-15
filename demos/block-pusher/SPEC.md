# Block Pusher - Multi-Screen Puzzle Game Spec

**Project:** Sokoban-style puzzle game with multi-screen support
**Goal:** Prove Rosh can handle screen transitions, UI text, and level management
**Status:** DRAFT - Spec in progress
**Created:** 2025-12-15
**Authors:** rdubar (vision), claude-opus-4-5 (spec)

---

## Overview

Build a simple Sokoban (block-pushing puzzle) game that demonstrates:
1. **Multi-screen flow** - Title → Level 1 → Level 2 → Victory
2. **Display objects** - Text/UI as first-class objects with properties
3. **Level data** - Clean way to define and load puzzle layouts
4. **State transitions** - How screens change, what persists

This is a **proof of concept** for patterns that will apply to all game types.

---

## Screen Flow

```
┌─────────────────┐
│   TITLE SCREEN  │
│                 │
│  "Block Pusher" │
│                 │
│  [Instructions] │
│                 │
│ "Press SPACE"   │
└────────┬────────┘
         │ SPACE
         ▼
┌─────────────────┐
│    LEVEL 1      │
│                 │
│  Simple puzzle  │
│  (2 boxes)      │
│                 │
│  "Level 1"      │
└────────┬────────┘
         │ All boxes on goals
         ▼
┌─────────────────┐
│    LEVEL 2      │
│                 │
│  Harder puzzle  │
│  (3 boxes)      │
│                 │
│  "Level 2"      │
└────────┬────────┘
         │ All boxes on goals
         ▼
┌─────────────────┐
│ VICTORY SCREEN  │
│                 │
│  "You Win!"     │
│                 │
│ "Press R to     │
│  restart"       │
└─────────────────┘
```

---

## Display Objects - Proposed Syntax

### The Vision

Treat text/UI elements as objects with the same syntax as game entities:

```rosh
create object title
    set x to 50%
    set y to 20%
    set text to "Block Pusher"
    set color to "white"
    set font_size to 48
end

create object instructions
    set x to 50%
    set y to 50%
    set text to "Push boxes onto goals"
    set color to "gray"
    set font_size to 24
end

create object prompt
    set x to 50%
    set y to 80%
    set text to "Press SPACE to start"
    set color to "yellow"
    set font_size to 20
end
```

### Display Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `text` | string | (none) | The text to display. If set, object renders as text |
| `x` | number/percent | 0 | Horizontal position (px or % of screen) |
| `y` | number/percent | 0 | Vertical position (px or % of screen) |
| `color` | string | "white" | Text color (CSS color names or hex) |
| `font_size` | number | 16 | Font size in pixels |
| `font` | string | "Arial" | Font family |
| `align` | string | "center" | Text alignment: "left", "center", "right" |
| `visible` | boolean | true | Whether to render |

### Display Commands

```rosh
print title              # Make 'title' object visible on screen
clear title              # Remove 'title' from screen (set visible to false? or destroy?)
clear all                # Remove ALL objects from screen
```

### Open Questions

1. **`print` vs implicit visibility**
   - Option A: Objects are invisible until `print <name>`
   - Option B: Objects are visible by default, `clear` hides them
   - Option C: `visible` property controls it, `print`/`clear` are shortcuts

   **Recommendation:** Option C - explicit is better

2. **`clear` semantics**
   - Does `clear title` destroy the object or just hide it?
   - If hidden, can you `print title` again later?
   - **Recommendation:** `clear` = hide (set visible to false), `destroy` = remove entirely

3. **Text vs Sprite objects**
   - How does transpiler know if object is text or sprite?
   - **Recommendation:** If `text` property is set, render as text. If `sprite` property is set, render as sprite. Both = error or sprite wins?

---

## Level Data Format

### Option A: Inline Rosh Code

Each level is defined in the main file or imported:

```rosh
# Level 1 definition
define level_1
    create object player
        set x to 100
        set y to 100
        set sprite to "player.png"
    end

    create object box
        set x to 150
        set y to 100
        set sprite to "box.png"
        set pushable to true
    end

    create object goal
        set x to 200
        set y to 100
        set sprite to "goal.png"
    end
end
```

**Pros:** Pure Rosh, no new concepts
**Cons:** Verbose, hard to visualize level layout

### Option B: Grid String (ASCII Art)

```rosh
create level level_1
    set grid to """
    ########
    #......#
    #.P.B..#
    #...B.G#
    #....G.#
    ########
    """
    set tile_size to 50
end

# Legend:
# # = wall
# . = floor
# P = player start
# B = box
# G = goal
```

**Pros:** Visual, compact, easy to edit
**Cons:** New syntax, needs grid parser

### Option C: TOON Data File

`levels/level1.toon`:
```toon
level:
  name: "Level 1"
  width: 8
  height: 6
  tile_size: 50

objects:
  - type: player
    x: 2
    y: 2
  - type: box
    x: 3
    y: 2
  - type: box
    x: 4
    y: 3
  - type: goal
    x: 5
    y: 2
  - type: goal
    x: 5
    y: 3
```

```rosh
load level from "levels/level1.toon"
```

**Pros:** Data separate from code, clean
**Cons:** Needs TOON loader for level structure, more infrastructure

### Option D: Simple Object List (Pragmatic)

For the POC, just use coordinates:

```rosh
# Level 1 - Simple: 2 boxes, 2 goals
set level to 1
clear all

create object player from player
    set x to 100
    set y to 100
end

create object box1 from box
    set x to 150
    set y to 100
end

create object box2 from box
    set x to 150
    set y to 150
end

create object goal1 from goal
    set x to 250
    set y to 100
end

create object goal2 from goal
    set x to 250
    set y to 150
end
```

**Pros:** Works with current Rosh, no new features needed
**Cons:** Verbose, no visual layout

### Recommendation for POC

**Start with Option D** (simple object list) to prove the multi-screen flow works.

Then evaluate: Is the verbosity painful enough to justify Option B (grid strings) or Option C (TOON levels)?

---

## Screen/State Management

### The Core Problem

How do we represent "screens" or "scenes" in Rosh?

**Current state:** Rosh has no concept of screens. All objects exist in one flat space.

### Proposed Approach: Functions as Screens

```rosh
define show_title_screen
    clear all

    create object title
        set x to 50%
        set y to 20%
        set text to "Block Pusher"
        set font_size to 48
    end

    create object prompt
        set x to 50%
        set y to 80%
        set text to "Press SPACE to start"
    end

    print title
    print prompt
end

define show_level_1
    clear all

    # Create level 1 objects...
    create object player from player
        set x to 100
        set y to 100
    end
    # ... more objects
end

define show_victory
    clear all

    create object win_text
        set x to 50%
        set y to 50%
        set text to "You Win!"
        set font_size to 64
        set color to "gold"
    end

    print win_text
end
```

### Screen Transitions via Events

```rosh
# Global state
set current_screen to "title"

# Title screen: SPACE starts game
when key_space then
    if current_screen is "title" then
        set current_screen to "level_1"
        call show_level_1
    end
end

# Level complete detection
when level_complete then
    if current_screen is "level_1" then
        set current_screen to "level_2"
        call show_level_2
    else if current_screen is "level_2" then
        set current_screen to "victory"
        call show_victory
    end
end

# Win condition check (called on every box move?)
define check_win
    # Count boxes on goals
    # If all boxes on goals, trigger level_complete
end
```

### Open Questions

1. **When to check win condition?**
   - After every move?
   - After every box push?
   - Continuous check in game loop?

2. **How does `clear all` work in transpiler?**
   - Phaser: Destroy all game objects in scene?
   - Need to preserve event handlers?

3. **State that persists between screens?**
   - Score? (not needed for Sokoban POC)
   - Moves count?
   - For POC: Nothing persists, keep it simple

---

## Collision & Movement

### Grid-Based Movement

Sokoban uses grid movement, not pixel movement:

```rosh
set tile_size to 50

when key_right then
    # Move player one tile right
    set player.x to player.x plus tile_size
end
```

### Box Pushing Logic

When player moves into a box:
1. Check if space behind box is empty
2. If yes: move box, then move player
3. If no: block movement

```rosh
when collision player box then
    # Determine push direction based on player movement
    # Check if box can move
    # Move box if possible
    # This is complex - may need helper logic
end
```

### Collision Detection Approach

**Option A: Pixel-based (Phaser default)**
- Check sprite overlaps
- More complex for grid games

**Option B: Grid-based (Sokoban natural)**
- Track grid positions, not pixel positions
- Check grid cell occupancy
- Simpler logic

**Recommendation:** Use grid coordinates internally, convert to pixels for rendering:
```rosh
# Internal: grid position
set player.grid_x to 2
set player.grid_y to 3

# Rendering: pixel position (computed)
set player.x to player.grid_x times tile_size
set player.y to player.grid_y times tile_size
```

---

## What Rosh Already Has vs What's New

### Already Exists (should work)
- [x] `create object` with properties
- [x] `set` property values
- [x] `when <event> then` handlers
- [x] `trigger <event>`
- [x] `if/else` conditionals
- [x] `define` functions
- [x] `call` functions
- [x] String interpolation
- [x] Keyboard events (arrow keys, space)
- [x] `from player` inheritance (auto-controls)
- [x] Sprite rendering

### Verified Working (2025-12-15)
- [x] `x to 50%` percentage positioning - ✅ WORKS
- [x] Text rendering - ✅ WORKS (`set text to "..."` creates Phaser text object)
- [x] `visible` property - ✅ WORKS (`set visible to false` → `setVisible(false)`)
- [x] Screen transitions via visibility - ✅ WORKS (hide title, show game objects)
- [x] `set object.visible to true/false` - ✅ WORKS (uses Phaser `setVisible()`)
- [x] `set object.text to "..."` - ✅ WORKS (uses Phaser `setText()`)

### Still Needs Work
- [ ] `clear all` command - hide all objects at once (workaround: set each visible to false)
- [ ] `destroy <object>` - actually delete object (not just hide)
- [ ] Multiple objects of same type (box1, box2) - collision handling
- [ ] Grid-based movement helpers
- [ ] Win condition detection pattern

---

## Implementation Plan

### Phase 1: Verify Foundations ✅ COMPLETE (2025-12-15)
1. ✅ Text rendering works (`set text to "..."` → Phaser text object)
2. ✅ Percentage positioning works (`50%` → 400px)
3. ✅ Visibility control works (`set visible to false` → `setVisible(false)`)
4. ✅ Built test: `test-screens.rosh` - title screen → game transition with SPACE key

**Test files created:**
- `working/puzzle-game/test-text.rosh` - Basic text rendering test
- `working/puzzle-game/test-screens.rosh` - Screen transition test

### Phase 2: Title Screen ✅ COMPLETE (2025-12-15)
1. ✅ Title screen with text objects (title, subtitle, instructions, start prompt)
2. ✅ SPACE key triggers transition (hides title, shows game objects)
3. Note: `clear all` not implemented yet - using individual `set visible to false` instead

### Phase 3: Single Level ✅ COMPLETE
1. ✅ Player, box, goal objects
2. ✅ Grid-based movement (arrow keys)
3. ✅ Box pushing on collision

### Phase 4: Win Condition ✅ COMPLETE
1. ✅ Detect box on goal
2. ✅ Show "Level Complete" message
3. ✅ SPACE to continue

### Phase 5: Two Levels ✅ COMPLETE
1. ✅ Level 2 with different layout
2. ✅ Level 1 complete → Level 2
3. ✅ Level 2 complete → Victory

### Phase 6: Polish ✅ COMPLETE
1. ✅ Move counter tracking
2. ✅ Restart level (R key)
3. ⏳ Visual feedback (box on goal color) - skipped for now

---

## File Structure

```
working/puzzle-game/
├── SPEC.md              # This file
├── game.rosh            # Main game code
├── assets/
│   ├── player.png       # Player sprite
│   ├── box.png          # Box sprite
│   ├── box-done.png     # Box on goal sprite (optional)
│   ├── goal.png         # Goal marker sprite
│   └── wall.png         # Wall sprite (optional, could use rectangles)
├── dist/                # Build output (gitignored)
└── notes/               # Working notes, experiments
    └── experiments.rosh # Throwaway test code
```

---

## Success Criteria

**This POC is successful when:**

1. **Multi-screen works**
   - Title screen displays
   - SPACE transitions to Level 1
   - Level complete transitions to Level 2
   - Level 2 complete shows victory

2. **Text rendering works**
   - Title, instructions, prompts display correctly
   - Text uses object properties (x, y, text, color, font_size)

3. **Gameplay works**
   - Player moves on grid (arrow keys)
   - Boxes push when player walks into them
   - Boxes stop at walls/other boxes
   - Win detected when all boxes on goals

4. **Code is clean**
   - Readable Rosh that demonstrates the language well
   - Patterns that transfer to other game types
   - Could be shown to clients/users as example

---

## Open Questions (To Resolve)

1. **Text rendering in Phaser transpiler** - Does it exist? What's the syntax?

2. **`clear` semantics** - Hide vs destroy? Need both?

3. **Grid vs pixel coordinates** - Store grid positions and compute pixels? Or just use pixels with tile_size math?

4. **Box-on-goal detection** - Continuous overlap check? Or check after each move?

5. **Multiple boxes** - How to iterate over "all boxes"? Do we need groups/collections?

6. **Level data format** - Inline code for POC, but what's the long-term vision?

---

## New Notes & Decisions

- **rdubar:** `print` should set `visible` true without deleting; `clear` should hide but keep the object so it can be printed again.
- **rdubar:** Favors ASCII maps long term (worth the effort) but fine with coordinate-based levels for the demo.
- **rdubar:** Wants a reusable `level`/`screen_object` base that levels inherit from; could also track score/state there.
- **rdubar:** Win detection should run after each box push (validate this timing).
- **rdubar:** Score can simply be move count so something is always displayed.
- **rdubar:** Provide a helper to move in grid-sized chunks so any object can reuse it.
- **Codex:** Keep POC on Option D (coords) but add a small ASCII parser spike to evaluate Option B without committing.
- **Codex:** Model `print`/`clear` as `visible` toggles; add `destroy` for actual deletion to keep semantics distinct.
- **Codex:** Implement `LevelBase` (or `ScreenObject`) holding metadata (name, move_count, maybe start_time) and inherit per-level objects from it.
- **Codex:** Run win detection immediately after a successful push; skip when push blocked to keep checks cheap and aligned to state changes.
- **Codex:** Extract `move_in_grid(object, dx, dy, tile_size)` helper to centralize clamping, collisions, and box-push chaining.

---

## Next Steps

1. **Review this spec** - Does vision align? Anything missing?
2. **Check Phaser transpiler** - What text/UI support exists?
3. **Phase 1 experiment** - Minimal test of text + screen transition
4. **Iterate** - Update spec as we learn

---

## Changelog

- **2025-12-15:** Initial spec draft (claude-opus-4-5)
  - Defined screen flow
  - Proposed display object syntax
  - Outlined level data options
  - Listed open questions

---

*This spec is a living document. Update as decisions are made and understanding evolves.*
