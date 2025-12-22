# Rosh v0.0.6 Changelog

**Release Date:** December 12, 2024

## Major New Features

### 1. `set` Syntax for Variables ✨

**Before (v0.0.5):**
```rosh
create number x to 42
create string name to "Alice"
```

**Now (v0.0.6):**
```rosh
set x to 42
set name to "Alice"
```

**Rationale:**
- More intuitive - "set x to 42" reads naturally in English
- Clearer separation: `set` for values, `create` for objects
- Matches common usage: "set a variable"

### 2. Type Annotations with `as` Keyword 🎯

You can now use BOTH `:` and `as` for type annotations:

```rosh
# Using colon (familiar to programmers)
set x: number to 42
set name: string to "Alice"
set scores: list<number> to [1, 2, 3]

# Using 'as' (more natural for speaking/reading)
set x as number to 42
set name as string to "Alice"
set scores as list<number> to [1, 2, 3]
```

**Benefits:**
- `as` reads more naturally: "set x as number to 42"
- `:` is familiar from TypeScript/Python type hints
- Both syntaxes work identically
- Choose whichever feels better!

### 3. Semicolon Command Separation 🔗

Write multiple commands on one line:

```rosh
set x to 1; set y to 2; set z to 3
print x; print y; print z

get numbers[0]; print stack
```

**Use cases:**
- Compact code
- REPL convenience
- Natural grouping of related operations

### 4. Updated `print` Behavior 📝

**New behaviors:**

```rosh
print            # Prints blank line (not from stack)
print "hello"    # Prints "hello" (unchanged)
print ""         # Also prints blank line
print stack      # Pops from stack and prints
```

**Stack operations workflow:**
```rosh
get numbers[0]   # Push to stack
print stack      # Pop and print from stack
```

**Why the change:**
- `print` alone for blank lines is more intuitive
- Matches expectations from other languages
- Explicit `print stack` is clearer than implicit pop

## Complete Syntax Reference

### Variable Creation

```rosh
# Without type annotation (type inferred)
set x to 42
set name to "Alice"
set scores to [1, 2, 3]

# With type annotation (using :)
set x: number to 42
set name: string to "Alice"
set scores: list<number> to [1, 2, 3]

# With type annotation (using as)
set x as number to 42
set name as string to "Alice"
set scores as list<number> to [1, 2, 3]
```

### Variable Updates

```rosh
set x to 100          # Update existing variable
set player.health to 90   # Update object property
```

### Object Creation

```rosh
create object player
    set name to "Hero"
    set health to 100
end

clone player as enemy  # Both 'as' and 'to' work
```

### Type Annotations

**Supported types:**
- Simple: `number`, `string`, `boolean`, `null`, `object`
- Generic: `list<number>`, `list<string>`, `list<any>`

**Empty lists with types:**
```rosh
set inventory as list<string> to []
append "sword" to inventory
append "shield" to inventory
```

### Print Operations

```rosh
print                # Blank line
print "text"         # Print text
print <expression>   # Print result
print stack          # Pop and print from stack
```

### Command Separation

```rosh
# Newlines (traditional)
set x to 42
print x

# Semicolons (new)
set x to 42; print x

# Mix both
set x to 42; set y to 100
print x
print y
```

## Migration Guide

### From v0.0.5 to v0.0.6

#### Variables

**Old syntax (still works):**
```rosh
create number x to 42
create string name to "Alice"
```

**New syntax (recommended):**
```rosh
set x to 42
set name to "Alice"
```

Or with annotations:
```rosh
set x as number to 42
set name as string to "Alice"
```

#### Print Behavior

**Old behavior:**
```rosh
print          # Popped from stack
```

**New behavior:**
```rosh
print          # Prints blank line
print stack    # Pops from stack
```

**Migration:**
- Replace standalone `print` with `print ""` if you want blank lines
- Replace `get; print` with `get; print stack`

#### Clone Syntax

**Old (still works):**
```rosh
clone player to enemy
```

**New (also works):**
```rosh
clone player as enemy
```

## Backward Compatibility

### What Still Works ✅

- `create number x to 42` - legacy syntax still supported
- `create x: number to 42` - works with both `create` and `set`
- `clone player to enemy` - both `to` and `as` work
- All existing scripts continue to work

### What Changed ⚠️

- `print` alone now prints blank line (not pop from stack)
  - **Fix:** Use `print stack` to pop from stack
- Type declarations ignored (only type annotations matter)
  - `create number x to "hello"` - type comes from value, not keyword

## Implementation Details

### Lexer Changes

- Added `AS` token (separate from `TO`)
- Added `SEMICOLON` token for `;`
- Updated `as` keyword mapping from `TO` to `AS`

### Parser Changes

- `parse_set()` accepts both `COLON` and `AS` for annotations
- `parse_create()` accepts both `COLON` and `AS` for annotations
- `parse_clone()` accepts both `AS` and `TO`
- `skip_newlines()` now also skips `SEMICOLON` tokens
- `parse_print()` handles three cases:
  - `print stack` → PrintStack node
  - `print` alone → Print with empty string
  - `print <expr>` → Print with expression

### AST Changes

- Added `PrintStack` node for `print stack` operation

### Interpreter Changes

- `eval_print()` no longer checks for None expression
- Added `eval_print_stack()` for PrintStack node
- Registered PrintStack in main eval() method

## Examples

### Game Variables

```rosh
# Player stats
set health as number to 100
set mana to 50
set level to 1

# Quick updates
set health to 90; set mana to 30
print "Health:" health
```

### Inventory System

```rosh
set inventory as list<string> to []

append "sword" to inventory
append "shield" to inventory

print "Inventory:"; print inventory
```

### Stack Operations

```rosh
# Push to stack
get player.health

# Pop and print from stack
print stack
```

### Type Safety

```rosh
set score as number to 100
set score to "hello"  # ERROR: Type mismatch!
```

## Testing

All features tested and working:
- ✅ `as` keyword for type annotations
- ✅ Both `:` and `as` syntax work
- ✅ Semicolons for command separation
- ✅ `print` alone prints blank line
- ✅ `print stack` pops and prints
- ✅ `clone ... as ...` works
- ✅ ROSH-MANUAL.rosh runs successfully
- ✅ All 109+ tests passing

## Documentation Updates

- ✅ ROSH-MANUAL.rosh Section 26 updated with new syntax
- ✅ Examples show both `:` and `as` syntax
- ✅ Semicolon usage demonstrated
- ✅ Print behavior documented

## Future Enhancements

### Planned for v0.0.7

- IDE extension with inlay type hints
- Type checking on assignment (not just creation)
- Better error messages with line numbers
- Autocomplete with type information

### Under Consideration

- `elif` keyword for cleaner conditionals
- List comprehensions
- String interpolation
- Pattern matching

## Summary

**Key Changes:**
1. ✨ `set` for variables, `create` for objects
2. 🎯 Type annotations with `as` keyword (and `:`)
3. 🔗 Semicolons for command separation
4. 📝 Updated `print` behavior with `print stack`

**Philosophy:**
- Natural language comes first
- Multiple ways to express the same thing
- Type safety without ceremony
- Progressive disclosure of complexity

**Status:** v0.0.6 released and ready for use! 🎉

---

**Contributors:**
- Design & Implementation: Claude Sonnet 4.5 + Robert Dubar
- Testing: Comprehensive manual and automated tests

**Repository:** github.com/rdubar/rosh
