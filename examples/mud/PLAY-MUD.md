# How to Play the Rosh MUD

## Quick Start

```bash
# Start Rosh REPL
rosh

# Load the MUD world
rosh> import "examples/mud/dungeon-crawler.rosh"

# Create convenient aliases
rosh> alias look call look
rosh> alias status call status
rosh> alias n set player.current-room to "courtyard"
rosh> alias s set player.current-room to "tavern"
rosh> alias e set player.current-room to "forest"
rosh> alias w set player.current-room to "well"

# Now play!
rosh> look
# → Shows tavern description

rosh> status
# → Shows your health, strength, location

rosh> n
# → Moves to courtyard

rosh> look
# → Shows courtyard

rosh> e
# → Moves to forest

rosh> look
# → "Something glints on the ground" (gem!)

# Save your progress
rosh> dump
# → Shows full world state as JSON

# Continue later
rosh> load "world.json"
```

## What the Alias Feature Does

**Before aliases:**
```rosh
rosh> call look
rosh> set player.current-room to "courtyard"
```

**After creating aliases:**
```rosh
rosh> alias look call look
rosh> alias n set player.current-room to "courtyard"

rosh> look              # Much more natural!
rosh> n                 # Just like a real MUD!
```

## Advanced: Movement System

Create a full compass:
```rosh
alias n set player.current-room to "tavern"
alias s set player.current-room to "courtyard"
alias e set player.current-room to "forest"
alias w set player.current-room to "well"
alias north set player.current-room to "tavern"
alias south set player.current-room to "courtyard"
alias east set player.current-room to "forest"
alias west set player.current-room to "well"
```

Now you can type `n`, `north`, `s`, `south`, etc. just like LPC/TinyMUD!

## Features Demonstrated

✅ **Persistent World** - All objects, rooms, items exist as Rosh objects
✅ **Interactive REPL** - Live exploration and commands
✅ **Inheritance** - Rooms inherit from room-template
✅ **Property Stacks** - Can push/pop temporary effects
✅ **Aliases** - Natural command shortcuts
✅ **Save/Load** - Entire world persists
✅ **Functions** - Commands are just Rosh functions
✅ **Extensible** - Add new rooms/items/commands anytime

## This is Real LPC/Forth-style Development! 🎮
