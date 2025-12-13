# Rosh Syntax Summary (v0.0.6)

**Date:** 2024-12-12
**Status:** ✅ IMPLEMENTED AND RELEASED

## Core Design Decision

**`set` for variables, `create` for objects**

This makes the language more intuitive and semantically clear.

---

## Complete Syntax

### Variables (Values)

```rosh
# Basic syntax
set <name> to <value>
set <name>: <type> to <value>
set <name> as <type> to <value>

# Examples
set x to 42
set name to "Alice"
set scores to [1, 2, 3]

# With type annotations (two syntaxes!)
set x: number to 42                # Using colon
set name as string to "Alice"      # Using 'as' (more natural!)
set scores as list<number> to [1, 2, 3]
```

**Behavior:**
- First `set` → creates the variable
- Subsequent `set` → updates the variable
- Type is inferred or annotated
- Type is checked on every assignment
- Both `:` and `as` work for annotations

### Objects (Entities)

```rosh
# Object creation
create object <name>
    set <property> to <value>
end

# Example
create object player
    set name to "Hero"
    set health to 100
    set inventory to []
end

# Clone object
clone player as enemy
set enemy.name to "Goblin"
```

---

## Type System

### Type Inference

Automatic - no annotations needed:

```rosh
set x to 42                    # Inferred: number
set name to "Alice"            # Inferred: string
set active to true             # Inferred: boolean
set scores to [1, 2, 3]        # Inferred: list<number>
set words to ["a", "b"]        # Inferred: list<string>
set mixed to [1, "a"]          # Inferred: list<any>
set empty to []                # Inferred: list<any>
```

### Type Annotations

Optional - for documentation and safety:

```rosh
set x: number to 42
set name: string to "Alice"
set scores: list<number> to [1, 2, 3]
set inventory: list<string> to []      # Useful for empty lists!
```

### Supported Types

**Simple:**
- `number` - Integers and floats
- `string` - Text
- `boolean` - true/false
- `null` - Null value
- `object` - Rosh objects
- `any` - No type checking

**Generic:**
- `list<number>` - List of numbers
- `list<string>` - List of strings
- `list<boolean>` - List of booleans
- `list<any>` - Mixed types
- `list<object>` - List of objects

---

## IDE Experience

### Inlay Hints

When you type code without annotations, the IDE shows inferred types:

```rosh
# What you type:
set x to 42

# What IDE shows (gray italic hints):
set x: number to 42
     ~~~~~~~ (hint)
```

### Type Errors

Clear, immediate feedback:

```rosh
set x: number to "hello"
                 ~~~~~~~ (red wavy underline)

Error: Type mismatch for variable 'x':
       annotated as number, but value is string
```

### Hover Tooltips

Hover over any variable to see:
- Variable name
- Type
- Current value
- Line declared

### Autocomplete

Type-aware suggestions:
```rosh
set inv|          → suggests: set inventory: list<string> to []
set x: num|       → suggests: set x: number to ___
```

---

## New Features in v0.0.6

### Semicolons for Command Separation

```rosh
# Multiple commands on one line
set x to 1; set y to 2; set z to 3

# Mix with newlines
set a to 10; set b to 20
print a
print b

# Quick operations
get player.health; print stack
```

### Updated Print Behavior

```rosh
print            # Prints blank line (NEW)
print "hello"    # Prints "hello" (unchanged)
print ""         # Also prints blank line
print stack      # Pops from stack and prints (NEW)
```

**Stack operations:**
```rosh
get numbers[0]   # Push value to stack
print stack      # Pop and print from stack
```

### Clone with 'as' keyword

```rosh
clone player as enemy     # More natural!
clone player to enemy     # Also works (backward compatible)
```

---

## Examples

### Game Stats

```rosh
# Without annotations
set health to 100
set mana to 50
set level to 1

# With annotations (both syntaxes work!)
set health as number to 100      # Using 'as'
set mana: number to 50            # Using ':'
set level to 1                    # Inferred
```

### Inventory System

```rosh
# Empty inventory with type
set inventory as list<string> to []

# Add items
append "sword" to inventory
append "shield" to inventory

# Items list inferred
set items to ["sword", "shield", "potion"]

# Quick check (semicolons!)
print "Inventory:"; print inventory
```

### Player State

```rosh
# Create player object
create object player
    set name to "Hero"
    set health to 100
    set inventory to []
end

# Update player
set player.health to 90
```

---

## Type Checking Examples

### Correct Usage

```rosh
set x: number to 42          # ✅ OK
set x to 100                 # ✅ OK (type matches)
set y: list<number> to [1,2] # ✅ OK
set z: list<string> to []    # ✅ OK (empty list with type)
```

### Type Errors

```rosh
set x: number to "hello"     # ❌ Type mismatch at creation
set x: number to 42
set x to "hello"             # ❌ Cannot change type
set y: list<number> to ["a"] # ❌ List element type mismatch
```

---

## Comparison with Old Syntax

### Old (Confusing)

```rosh
create number x to 42
create string name to "Alice"
create number scores to [1, 2, 3]  # Says "number" but is a list!
create object player
    create string name to "Hero"
end
```

**Problems:**
- `create` used for both values and objects
- Type declarations on values were confusing
- `create number scores` to a list was semantic nonsense

### New (Clear)

```rosh
set x to 42
set name to "Alice"
set scores to [1, 2, 3]
create object player
    set name to "Hero"
end
```

**Benefits:**
- ✅ `set` for values, `create` for objects
- ✅ Types are inferred, not declared
- ✅ Annotations are optional and validated
- ✅ Reads like natural English

---

## Migration Guide

### For Users

**Old Code:**
```rosh
create number x to 42
create number y to 100
```

**New Code:**
```rosh
set x to 42
set y to 100
```

**With Annotations (Optional):**
```rosh
set x: number to 42
set y: number to 100
```

### For Implementers

1. **Parser Changes:**
   - Support `set <name>: <type> to <value>` syntax
   - Keep `create object` working
   - Deprecate `create <type> <name>` with warning

2. **Type Inference:**
   - Infer types from values automatically
   - Store inferred type with variable
   - Check type on every assignment

3. **IDE Support:**
   - Implement inlay hints provider
   - Show inferred types in gray italic
   - Provide type error diagnostics

---

## Summary

**Key Principle:** `set` for variables, `create` for objects

**Syntax:**
```rosh
set <name>: <type> to <value>    # Optional type annotation
```

**Benefits:**
- More intuitive ("set x to 42" reads naturally)
- Clearer separation (values vs entities)
- Optional type annotations for safety
- Great IDE experience with inlay hints

**Status:** Documented and ready for implementation! 🎉
