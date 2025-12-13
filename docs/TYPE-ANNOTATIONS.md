# Type Annotations in Rosh

**Version:** v0.0.6
**Status:** Implemented and Documented

## Overview

Rosh supports **optional type annotations** with automatic type inference. You can write code without any type annotations (they're inferred), or add them for documentation and safety.

## Syntax

### Type Inference (No Annotations)

```rosh
create x to 42                    # Infers: number
create name to "Alice"            # Infers: string
create active to true             # Infers: boolean
create scores to [95, 87, 92]     # Infers: list<number>
create words to ["a", "b"]        # Infers: list<string>
```

### Type Annotations (Optional)

```rosh
create x: number to 42
create name: string to "Alice"
create active: boolean to true
create scores: list<number> to [95, 87, 92]
create words: list<string> to ["a", "b"]
```

## Supported Types

### Simple Types
- `number` - Integers and floats
- `string` - Text values
- `boolean` - true/false
- `null` - Null value
- `object` - Rosh objects
- `any` - Any type (no checking)

### Generic Types
- `list<number>` - List of numbers
- `list<string>` - List of strings
- `list<boolean>` - List of booleans
- `list<any>` - List of mixed types
- `list<object>` - List of objects

## Examples

### Empty Lists with Annotations

Type annotations are especially useful for empty lists:

```rosh
# Without annotation - unclear what goes in the list
create inventory to []

# With annotation - clear intent!
create inventory: list<string> to []
```

### Type Validation

Annotations catch errors at creation time:

```rosh
# This works
create age: number to 25

# This fails - type mismatch!
create age: number to "twenty-five"
# Error: Type mismatch for variable 'age': annotated as number, but value is string
```

### List Type Validation

```rosh
# This works
create scores: list<number> to [95, 87, 92]

# This fails - element type mismatch!
create scores: list<number> to ["A", "B", "C"]
# Error: Type mismatch for variable 'scores': annotated as list<number>, but value is list<string>
```

## When to Use Annotations

### ✅ Use Annotations For:
- **Empty collections** - Documents what goes in them
- **Function parameters** - Makes intent clear (coming soon)
- **Public APIs** - Helps users understand interface
- **Complex data** - Reduces ambiguity

### ⏭️ Skip Annotations When:
- **Type is obvious** - `create x to 42` is clearly a number
- **Quick prototyping** - Speed over safety
- **Internal variables** - Short-lived, obvious usage

## Type Inference Rules

### Simple Values
```rosh
42          → number
"hello"     → string
true/false  → boolean
null        → null
```

### Lists
```rosh
[1, 2, 3]           → list<number>
["a", "b"]          → list<string>
[true, false]       → list<boolean>
[1, "a", true]      → list<any> (mixed types)
[]                  → list<any> (empty)
```

### Objects
```rosh
create object player
    set name to "Hero"     # property 'name': string
    set health to 100      # property 'health': number
end
# → object
```

## Error Messages

Rosh provides clear error messages for type mismatches:

```
Type mismatch for variable 'x': annotated as number, but value is string
Type mismatch for variable 'scores': annotated as list<number>, but value is list<string>
```

## Backward Compatibility

The old explicit type syntax still works but is deprecated:

```rosh
# OLD (deprecated - type is ignored)
create number x to 42
create number scores to [1, 2, 3]  # Confusing!

# NEW (recommended)
create x to 42
create scores to [1, 2, 3]

# NEW with annotation (best for documentation)
create x: number to 42
create scores: list<number> to [1, 2, 3]
```

## IDE Support (Future)

Type annotations enable IDE features:
- **Autocomplete** - IDE knows what methods are available
- **Error highlighting** - Type mismatches shown in editor
- **Hover tooltips** - See variable types without running code
- **Refactoring** - Safe rename with type checking

## Examples

See these files for examples:
- `ROSH-MANUAL.rosh` - Section 26: Type Annotations
- `examples/type-annotations-demo.rosh` - Complete demonstration
- `examples/type-errors-demo.rosh` - Error examples

## Try It Out

```bash
# Run the demo
rosh examples/type-annotations-demo.rosh

# Test type checking
rosh -c "create x: number to 42; print x"
rosh -c "create x: number to \"hello\""  # See the error!

# Run the full manual
rosh ROSH-MANUAL.rosh
```

## Design Philosophy

**Optional, not mandatory**
Type annotations are a tool, not a requirement. Use them when they help, skip them when they don't.

**Inferred by default**
Rosh always knows types (through inference), annotations just make them explicit.

**Errors at creation**
Type mismatches fail fast at variable creation, not later when used.

**Clear error messages**
When types don't match, Rosh tells you exactly what's wrong and where.
