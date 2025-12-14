# Rosh MUD Builder Edition

## What's New

The MUD now includes a complete item system with properties!

### Features Added

✅ **Item Properties**
- `portable: true/false` - Can items be picked up?
- `fixed: true` - Items that cannot be moved (furniture, fixtures)
- `location: "room-name"` - Where the item is in the world

✅ **Enhanced Commands**
- `look` - Shows room description + all items (with portable/fixed labels)
- `take` - Pick up portable items
- `put` - Drop items from inventory
- `examine` - Detailed examination of items
- `inventory` (alias: `inv`) - What you're carrying
- `status` - Health, strength, location, inventory

✅ **Pre-defined World**
- 5 connected rooms (tavern, courtyard, shop, forest, well)
- 3 portable items (sword, gem, potion)
- 2 fixed items (table, fireplace)
- Full descriptions for everything

✅ **Recommended Aliases**
- The game prints recommended aliases when loaded
- Just copy/paste them into the REPL!

## Example Session

```bash
rosh
```

```rosh
rosh> import "examples/mud/dungeon-crawler.rosh"
=== Loading Rosh MUD Builder ===
=== MUD Ready! ===

RECOMMENDED ALIASES (type these now):
  alias look call look
  alias status call status
  alias inv call inventory
  alias take call take "item"
  alias put call put "item"
  alias examine call examine "item"
  ...

# Set up aliases
rosh> alias look call look
rosh> alias inv call inventory
rosh> alias take call take "item"

# Start playing!
rosh> look
===
The Rusty Tankard Tavern
A cozy tavern with wooden tables and a roaring fireplace.

Items here:
  - Rusty Sword (portable)
  - Heavy Oak Table (fixed)
  - Stone Fireplace (fixed)
===

rosh> take
You pick up the Rusty Sword.

rosh> inv
=== Inventory ===
  - Rusty Sword

rosh> examine
=== Examining ===
Heavy Oak Table
A massive wooden table. Too heavy to move.
This cannot be moved.

# Move to another room
rosh> alias s set player.current-room to "courtyard"
rosh> s
rosh> look
===
Village Courtyard
The village courtyard. Cobblestones underfoot.
...
===
```

## Builder Commands

You can extend the world on-the-fly!

### Add a New Room with Items

```rosh
# Create a room
rosh> create object armory
...     set name to "Castle Armory"
...     set description to "Weapons and armor line the walls"
...     set north to "courtyard"
...   end

# Add a portable item
rosh> create object shield
...     set name to "Iron Shield"
...     set description to "A sturdy shield emblazoned with a lion"
...     set location to "armory"
...     set portable to true
...   end

# Add a fixed item
rosh> create object rack
...     set name to "Weapon Rack"
...     set description to "An enormous rack holding various weapons"
...     set location to "armory"
...     set portable to false
...     set fixed to true
...   end

# Connect it
rosh> set courtyard.south to "armory"

# Visit it!
rosh> alias armory set player.current-room to "armory"
rosh> armory
rosh> look
Items here:
  - Iron Shield (portable)
  - Weapon Rack (fixed)
```

## How It Works

### Item System

Every item is an object with these properties:

```rosh
create object sword
  set name to "Rusty Sword"
  set description to "An old but serviceable blade"
  set location to "tavern"     # Where it is
  set portable to true         # Can be picked up
end
```

Fixed items (cannot be moved):

```rosh
create object fireplace
  set name to "Stone Fireplace"
  set description to "A roaring fireplace"
  set location to "tavern"
  set portable to false        # Cannot pick up
  set fixed to true            # Permanent fixture
end
```

### Look Command

The `look` function checks each item's `location` property and shows:
- Portable items with label: `(portable)`
- Fixed items with label: `(fixed)`

### Take/Put System

- `take` checks if item is in current room AND `portable: true`
- If yes: moves item to inventory, updates player.inventory
- `put` drops item back into current room

### Examine System

- Shows detailed description
- Tells you if item can be picked up
- Shows if item is fixed

## Why This Rocks

This is **real LPC/MUD development**:

✅ Live world editing (add rooms/items anytime)
✅ Property-based system (portable, fixed, etc.)
✅ Object-oriented design
✅ Persistent state (dump/load)
✅ Natural commands via aliases
✅ Room-based location system
✅ Inventory management
✅ Interactive REPL

You're building a real MUD in Rosh! 🏰⚔️
