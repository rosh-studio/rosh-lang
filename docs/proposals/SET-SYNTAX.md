# Using `set` for Variables (Not `create`)

**Status:** Design Decision for v0.0.6
**Date:** 2024-12-12

## The Problem

Current syntax is confusing:
```rosh
create x to 42           # Creating a variable
create object player     # Creating an object
```

Both use `create`, but they're conceptually different!

## The Solution

**`create` is for objects, `set` is for variables:**

```rosh
# Variables (values)
set x to 42
set name to "Alice"
set scores to [1, 2, 3]

# Objects (entities)
create object player
    set name to "Hero"
    set health to 100
end
```

## Rationale

### 1. Semantic Clarity

**Objects** are entities you create:
- Players, rooms, items, NPCs
- Have properties and methods
- Persist in the game world
- Use: `create object <name>`

**Variables** are values you set:
- Numbers, strings, booleans, lists
- Temporary or configuration values
- Use: `set <name> to <value>`

### 2. Natural Language

Which reads better?

```rosh
# Before (awkward):
create x to 42
create name to "Alice"

# After (natural):
set x to 42
set name to "Alice"
```

"Set x to 42" is how you'd say it in English!

### 3. Simpler Mental Model

**Before:** Two keywords doing similar things
- `create` for initial assignment
- `set` for updates
- Hard to remember which to use

**After:** One keyword per concept
- `create` → objects only
- `set` → all variables
- Clear and simple!

## Complete Syntax

### Variable Creation (First Time)

```rosh
# Without type annotation (inferred)
set x to 42
set name to "Alice"
set scores to [1, 2, 3]

# With type annotation (validated)
set x: number to 42
set name: string to "Alice"
set scores: list<number> to [1, 2, 3]
```

### Variable Updates (Subsequent Times)

```rosh
# Without annotation (type checked against original)
set x to 100
set name to "Bob"

# With annotation (validates type hasn't changed)
set x: number to 100
set name: string to "Bob"
```

### Object Creation

```rosh
# Objects use 'create'
create object player
    set name to "Hero"
    set health to 100
    set inventory to []
end

# Clone objects
clone player as enemy
set enemy.name to "Goblin"
```

## Behavior

### First `set` - Creates Variable

```rosh
set x to 42              # Variable doesn't exist → creates it
                         # Type inferred: number
```

### Subsequent `set` - Updates Variable

```rosh
set x to 100             # Variable exists → updates it
                         # Type checked: must still be number
```

### Type Errors

```rosh
set x: number to 42      # OK: creates x as number
set x to "hello"         # ERROR: type mismatch
```

## Migration from Current Syntax

### Old Syntax (Deprecated)

```rosh
create number x to 42
create string name to "Alice"
create number scores to [1, 2, 3]   # Confusing!
```

### New Syntax (Recommended)

```rosh
set x to 42
set name to "Alice"
set scores to [1, 2, 3]
```

### Legacy Support

Keep old syntax working but show deprecation warning:

```
Warning: 'create <type> <name>' is deprecated
Use: 'set <name>' instead
```

## IDE Experience

```rosh
# What you type:
set x to 42

# What IDE shows (with inlay hint):
set x: number to 42
     ~~~~~~~ (gray italic hint)
```

## Examples

### Game Variables

```rosh
# Player stats
set health: number to 100
set mana to 50
set level to 1

# Game state
set current_room to "tavern"
set quest_active to true
set inventory: list<string> to []
```

### Object Properties

```rosh
create object room
    set name to "Tavern"
    set description to "A cozy tavern"
    set exits to ["north", "south"]
end
```

### Functions

```rosh
define function calculate_damage base_damage
    set modifier to random 1 to 6
    set total to base_damage plus modifier
    return total
end
```

## Summary

**Decision:** Use `set` for all variables, reserve `create` for objects.

**Benefits:**
- ✅ More intuitive ("set x to 42" reads naturally)
- ✅ Clearer separation (create objects, set values)
- ✅ Simpler to learn (one keyword per concept)
- ✅ Consistent with property syntax (`set player.health to 100`)

**Syntax:**
```rosh
set <name>: <type> to <value>    # Optional type annotation
```

**Applies to:**
- Variable creation (first time)
- Variable updates (subsequent times)
- With or without type annotations
