# MUD - Text Adventure Games

Multi-User Dungeon (MUD) style games - interactive fiction and text adventures.

## Quick Start

```bash
# Run the dungeon crawler
rosh examples/mud/dungeon-crawler.rosh

# Run with interactive mode
rosh -i examples/mud/dungeon-crawler.rosh
```

## Examples

### **dungeon-crawler.rosh** - Complete Adventure Game ⭐
A full-featured dungeon crawler with combat, inventory, NPCs, and quests!

**Features:**
- 6 interconnected rooms
- Turn-based combat system
- Inventory management
- NPC merchant with shop
- Item effects (weapons, armor, potions)
- Quest system (collect 3 gems)
- Locked doors and keys
- Boss fight with win/lose conditions

**How to play:**
```bash
rosh examples/mud/dungeon-crawler.rosh
```

**Commands:**
- Movement: `north`, `south`, `east`, `west`, `n`, `s`, `e`, `w`
- Look: `look`, `examine <item>`, `l`, `ex`
- Inventory: `inventory`, `i`
- Items: `take <item>`, `drop <item>`, `use <item>`
- Combat: `attack`, `fight`, `hit`
- NPC: `talk`, `buy <item>`, `buy all`
- Help: `help`

**Easter eggs:** Try `tickle merchant`, `jump`, `dance`, `sing`, `yell`

---

### **dungeon-events-demo.rosh** - Event System Demo
Demonstrates the event system using dungeon scenarios.

**Concepts:**
- Event handlers (`when ... then`)
- Triggers
- Event-driven gameplay
- State management

---

### **mud-demo-complete.rosh** - MUD Framework Demo
Basic MUD framework showing room navigation and object interaction.

---

### **mud-world.rosh** - World Building
Creating interconnected rooms and locations.

**Concepts:**
- Room creation
- Connections between rooms
- Navigation system
- World state

---

### **mud-helper.rosh** - Helper Functions
Utility functions for building MUDs.

**Concepts:**
- Function abstraction
- Code reuse
- Helper patterns

---

### **mud-with-library.rosh** - Library Usage
Using shared libraries to build MUDs.

**Concepts:**
- Code organization
- Library imports
- Modular design

---

## Key MUD Concepts

### Rooms
Rooms are the basic unit of space in a MUD:
```rosh
create room tavern
    set description to "A cozy tavern"
    set north to forest
    set south to village
end
```

### Objects
Items that can be taken, used, or examined:
```rosh
create object sword
    set description to "A sharp blade"
    set damage to 10
    set takeable to true
end
```

### NPCs
Non-player characters that can interact:
```rosh
create object merchant
    set description to "A friendly shopkeeper"
    set dialogue to "Welcome to my shop!"
end
```

### Combat
Turn-based combat systems:
```rosh
when attack then
    set enemy.health to enemy.health minus player.damage
    if enemy.health less_than 1 then
        print "Enemy defeated!"
    end
end
```

---

## Design Patterns

### Command Parser
Natural language understanding:
- Strip filler words: "the", "a", "at", "to", "with"
- Handle synonyms: "look" = "examine" = "inspect"
- Context-aware: check room first, then inventory

### State Management
Track game state:
- Player stats (health, inventory, location)
- World state (rooms, objects, NPCs)
- Quest progress

### Event System
Event-driven gameplay:
- User commands trigger events
- Events modify game state
- State changes trigger new events

---

## Learning Path

1. **mud-demo-complete.rosh** - Understand the basics
2. **mud-world.rosh** - Learn world building
3. **mud-helper.rosh** - Study helper functions
4. **dungeon-events-demo.rosh** - Master events
5. **dungeon-crawler.rosh** - See a complete game
6. **Build your own!** - Create your adventure

---

## Building Your Own MUD

### Step 1: Design Your World
- Sketch a map of rooms
- Plan connections (north, south, east, west)
- List items and NPCs

### Step 2: Create Rooms
```rosh
create room start
    set description to "You are in a dark cave"
    set north to treasure_room
end
```

### Step 3: Add Objects
```rosh
create object torch
    set description to "A flickering torch"
    set takeable to true
end
```

### Step 4: Implement Commands
```rosh
when take then
    # Add item to inventory
    print "Taken!"
end
```

### Step 5: Add Polish
- Detailed descriptions
- Easter eggs
- Helpful error messages
- Multiple ways to express commands

---

## Tips for Great MUDs

1. **Be forgiving** - Accept many command variations
2. **Give hints** - Help players when stuck
3. **Rich descriptions** - Make the world vivid
4. **Logical puzzles** - Fair and solvable challenges
5. **Reward exploration** - Hidden items and Easter eggs
6. **Test thoroughly** - Try every command combination

---

## Next Steps

- Study `dungeon-crawler.rosh` for a complete example
- Read `../DUNGEON-CRAWLER-NOTES.md` for design insights
- Check `../MUD-GUIDE.md` for detailed documentation
- Experiment with the event system
- Create your own adventure!
