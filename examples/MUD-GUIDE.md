# Rosh MUD Complete Guide

## Quick Start

```bash
rosh
```

```rosh
# Load the world
rosh> import "examples/mud-game.rosh"

# The game will show recommended aliases - type them!
rosh> alias look call look
rosh> alias status call status
rosh> alias inv call inventory
rosh> alias take call take "item"
rosh> alias put call put "item"

# Play!
rosh> look
# You see items: Rusty Sword (portable), Heavy Oak Table (fixed)

rosh> take
# You pick up the Rusty Sword.

rosh> inv
# Shows: Rusty Sword

rosh> status
```

---

## New Features: Items & Properties

### Items in the World

Items now have properties:
- `portable: true` - Can be picked up (swords, gems, potions)
- `portable: false, fixed: true` - Cannot be moved (furniture, fixtures)

```rosh
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
```

### Available Commands

- `look` - See room description + items
- `status` - Health, strength, location, inventory
- `inv` (inventory) - What you're carrying
- `take` - Pick up portable items
- `put` - Drop items you're carrying
- `examine` - Detailed look at items
- Movement: `n`, `s`, `e`, `w` (with aliases)

---

## Common Questions (From Real Use!)

### Q: "How do I add another room?"

**Answer: Create an object with room properties!**

```rosh
# 1. Create the room
rosh> create object library
...     set name to "Grand Library"
...     set description to "Towering bookshelves line the walls"
...     set north to "courtyard"
...     set south to null
...     set east to null
...     set west to null
...   end

# 2. Connect to existing room
rosh> set courtyard.south to "library"

# 3. Create alias for movement
rosh> alias lib set player.current-room to "library"

# 4. Test it!
rosh> lib
rosh> look
```

### Q: "How do I add items with properties?"

**Answer: Create objects with `portable` and `fixed` properties!**

```rosh
# Create a portable item (can be picked up)
rosh> create object book
...     set name to "Ancient Tome"
...     set description to "A dusty book with arcane symbols"
...     set location to "library"
...     set portable to true
...   end

# Create a fixed item (furniture/fixture)
rosh> create object statue
...     set name to "Stone Guardian"
...     set description to "An imposing statue carved from marble"
...     set location to "library"
...     set portable to false
...     set fixed to true
...   end

# Now go look!
rosh> lib
rosh> look
Items here:
  - Ancient Tome (portable)
  - Stone Guardian (fixed)

rosh> take
You pick up the Ancient Tome.
```

**Or load the pre-made example:**
```rosh
rosh> import "examples/add-room-live.rosh"
```

### Q: "I made a typo (like 'lool' instead of 'look')"

**Answer: Just type it again!** Rosh will show syntax errors for undefined commands, but you can immediately correct it. The REPL is forgiving.

### Q: "Can I ask the AI for help?"

**Yes!** Use `prompt` with quotes:

```rosh
# Generic AI help (not Rosh-specific)
rosh> prompt "how do i add another room"

# Better: Load the helper
rosh> import "examples/mud-helper.rosh"
rosh> call ask "rooms"
# → Shows Rosh-specific instructions
```

**Note:** Questions with `?` won't work directly - use `prompt "question"` instead.

---

## How Rosh MUDs Work (LPC-Style!)

### Everything is an Object

```rosh
# Rooms are objects
create object tavern
  set name to "Tavern"
  set description to "A cozy place"
  set north to "courtyard"
end

# Items are objects
create object sword
  set name to "Rusty Sword"
  set location to "tavern"
end

# Player is an object!
create object player
  set current-room to "tavern"
  set health to 100
end
```

### Commands are Functions

```rosh
define function look
  # Your logic here
  print "You look around..."
end

# Call it
call look

# Or create an alias
alias look call look
look
```

### State is Persistent

```rosh
# Save entire world
rosh> dump
# → Shows JSON

# Or save to file (in your own code)
# write <state> to "world.json"

# Load later
rosh> load "world.json"
```

---

## Advanced: Live World Building

### Add Room During Play

You don't need to restart - just add objects!

```rosh
# Player is in courtyard
rosh> look
Village Courtyard

# Add a new room RIGHT NOW
rosh> create object garden
...     set name to "Secret Garden"
...     set description to "Hidden behind ivy"
...     set west to "courtyard"
...   end

# Connect it
rosh> set courtyard.east to "garden"

# Go there immediately!
rosh> set player.current-room to "garden"
rosh> look
Secret Garden
Hidden behind ivy
```

### Add Items On-The-Fly

```rosh
# Create a treasure
rosh> create object treasure
...     set name to "Golden Crown"
...     set description to "Encrusted with gems"
...     set location to "garden"
...   end

# Now it exists in the world!
```

### Use Property Stacks (LPC Shadowing!)

```rosh
# Temporary buff
rosh> push player.health 150
rosh> print player.health
150

# Remove buff
rosh> pop player.health
rosh> print player.health
100
```

---

## Tips from Real Use

1. **Aliases are essential** - Create them for common commands:
   ```rosh
   alias l call look
   alias s call status
   alias n set player.current-room to "north-room"
   ```

2. **Use import for complex setups** - Don't type everything manually
   ```rosh
   import "examples/mud-game.rosh"
   ```

3. **dump frequently** - Save your progress!
   ```rosh
   dump
   ```

4. **Experiment!** - The world is live-editable. Try things:
   ```rosh
   set player.strength to 999
   set tavern.description to "Now it's a disco!"
   ```

5. **Check what exists**:
   ```rosh
   print player
   print tavern.description
   dump  # See everything
   ```

---

## This IS Real LPC/Forth Development!

✅ Interactive REPL
✅ Live world modification
✅ Persistent state
✅ Object-oriented
✅ Prototype inheritance
✅ Property shadowing (push/pop)
✅ Aliases for natural commands

**You're building a real MUD in Rosh!** 🎮
