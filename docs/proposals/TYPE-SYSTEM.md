# Rosh Type System Design

**Status:** Approved for v0.0.6
**Last Updated:** 2024-12-12

## Philosophy

Rosh uses **type inference with enforcement**:
- Types are inferred at creation time (natural syntax)
- Types are enforced at assignment time (safety)
- No explicit type annotations required (spoken-language-friendly)

## Core Principle

```rosh
create x to 42              # Infers type: number
set x to 100                # ✅ OK: number → number
set x to "hello"            # ❌ ERROR: can't assign string to number variable
```

## Creation Rules

### Basic Values

```rosh
create x to 42              # type: number
create name to "Alice"      # type: string
create flag to true         # type: boolean
create empty to null        # type: null
```

### Lists

```rosh
create nums to [1, 2, 3]           # type: list<number>
create words to ["a", "b"]         # type: list<string>
create mixed to [1, "a", true]     # type: list<any>
create empty to []                 # type: list<any> (until first append)
```

**Empty list behavior:**
```rosh
create items to []          # type: list<any>
append 42 to items          # Now: list<number>
append "hi" to items        # ❌ ERROR: can't append string to list<number>
```

### Objects

```rosh
create object player
    set name to "Hero"      # property 'name' type: string
    set health to 100       # property 'health' type: number
end

set player.health to 90     # ✅ OK: number → number
set player.health to "high" # ❌ ERROR: can't assign string to number property
```

## Current Syntax (v0.0.5)

Currently, Rosh requires explicit type declarations:

```rosh
create number x to 42
create string name to "Alice"
create number scores to [95, 87, 92]  # Confusing! Says "number" but creates list
```

**The Problem:** The explicit type is misleading when creating lists. `create number scores` suggests a single number, but assigns a list.

## Implementation Plan (v0.0.6)

### Phase 1: Infer Types, Keep Syntax

**Keep the current syntax** (parser limitation), but:
- Interpreter **ignores** the declared type
- Interpreter **infers** the actual type from the value
- Inferred type becomes the variable's declared type

```rosh
create number x to 42           # Ignores "number", infers: number (correct!)
create number scores to [1,2,3] # Ignores "number", infers: list<number> (correct!)
create string items to ["a","b"]# Ignores "string", infers: list<string> (correct!)
```

### Phase 2: New Syntax (Future)

Once type inference is stable, add **optional** typeless syntax:

```rosh
# Future: Optional typeless syntax
create x to 42              # Infers: number
create scores to [1, 2, 3]  # Infers: list<number>
create name to "Alice"      # Infers: string
```

Both syntaxes would work (backwards compatibility).

## Type Enforcement

### Assignment

```rosh
create x to 42
set x to 100                # ✅ OK
set x to "hello"            # ❌ TypeError: Cannot assign string to number variable 'x'
```

### List Operations

```rosh
create nums to [1, 2, 3]    # list<number>
append 4 to nums            # ✅ OK
append "5" to nums          # ❌ TypeError: Cannot append string to list<number>

create mixed to [1, "a"]    # list<any>
append true to mixed        # ✅ OK (list<any> accepts anything)
```

### Property Updates

```rosh
create object player
    set name to "Hero"
    set health to 100
end

set player.name to "Alice"  # ✅ OK: string → string
set player.name to 42       # ❌ TypeError: Cannot assign number to string property 'name'
```

## Special Cases

### Type Widening for Clones

```rosh
create object base
    set value to 42         # type: number
end

clone base as copy
set copy.value to 100       # ✅ OK: inherits type from base
set copy.value to "hi"      # ❌ ERROR: type enforced
```

### Function Parameters

```rosh
# Parameters with defaults get inferred types
define function greet name="World"
    print "Hello, " plus name
end

call greet "Alice"          # ✅ OK: string
call greet 42               # ❌ TypeError: Expected string, got number
```

### Dynamic Code

```rosh
# prompt exec / eval / import: infer from first assignment
eval "create x to 42"       # x type: number (inferred)
set x to 100                # ✅ OK
set x to "hi"               # ❌ ERROR: type enforced even for eval'd variables
```

## Type Hierarchy

```
any
├── null
├── boolean
├── number
├── string
├── list<T>
│   ├── list<any>
│   ├── list<number>
│   ├── list<string>
│   └── list<object>
└── object
    └── <custom objects>
```

## Implementation Details

### Environment Storage

Each variable in the environment stores:
```python
{
    'name': 'x',
    'value': 42,
    'declared_type': 'number',
    'line': 10  # For error messages
}
```

For lists:
```python
{
    'name': 'nums',
    'value': [1, 2, 3],
    'declared_type': 'list',
    'element_type': 'number',  # or 'any' for mixed/empty
    'line': 15
}
```

For objects:
```python
{
    'name': 'player',
    'value': RoshObject(...),
    'declared_type': 'object',
    'properties': {
        'name': {'value': 'Hero', 'type': 'string'},
        'health': {'value': 100, 'type': 'number'}
    }
}
```

### Type Inference Algorithm

```python
def infer_type(value):
    if value is None:
        return 'null'
    elif isinstance(value, bool):
        return 'boolean'
    elif isinstance(value, (int, float)):
        return 'number'
    elif isinstance(value, str):
        return 'string'
    elif isinstance(value, list):
        if not value:
            return ('list', 'any')  # Empty list

        # Check if all elements are the same type
        first_type = infer_type(value[0])
        if all(infer_type(v) == first_type for v in value):
            return ('list', first_type)
        else:
            return ('list', 'any')  # Mixed types
    elif isinstance(value, RoshObject):
        return 'object'
    else:
        return 'any'
```

### Type Checking Algorithm

```python
def check_type_compatible(declared_type, new_value):
    """Check if new_value can be assigned to variable with declared_type"""
    inferred_type = infer_type(new_value)

    # any accepts anything
    if declared_type == 'any':
        return True

    # null can only be assigned null
    if declared_type == 'null':
        return inferred_type == 'null'

    # Lists need element type checking
    if declared_type[0] == 'list':
        if inferred_type[0] != 'list':
            return False

        declared_elem = declared_type[1]
        inferred_elem = inferred_type[1]

        # list<any> accepts any list
        if declared_elem == 'any':
            return True

        # Otherwise element types must match
        return declared_elem == inferred_elem

    # Simple types must match exactly
    return declared_type == inferred_type
```

## Error Messages

Clear, helpful error messages:

```rosh
create x to 42
set x to "hello"
```

**Error:**
```
TypeError at line 2: Cannot assign string to number variable 'x'
  Variable 'x' was created as type 'number' at line 1
  Attempted to assign value: "hello" (type: string)

  Hint: Create a new variable if you need to store a different type
```

```rosh
create nums to [1, 2, 3]
append "4" to nums
```

**Error:**
```
TypeError at line 2: Cannot append string to list<number>
  List 'nums' contains numbers
  Attempted to append: "4" (type: string)

  Hint: Convert the value to a number or create a mixed list: [1, "a"]
```

## Migration Path

### v0.0.6: Inference Only (Warning)

- Infer types but only warn on mismatches
- Log warnings to help users find issues
- Don't break existing code

### v0.0.7: Enforcement (Errors)

- Type mismatches raise errors
- All existing code updated
- Breaking change (with clear migration guide)

## Future Extensions

### Type Annotations (Optional)

For documentation/clarity:
```rosh
create x: number to 42      # Explicit type annotation
create nums: list<string> to []  # Annotated empty list
```

### Type Guards

```rosh
if x is number then
    # x is guaranteed to be a number here
end
```

### Generic Functions

```rosh
define function first<T> list: list<T> returns T
    return list[0]
end
```

## Implementation Checklist (v0.0.6)

### Phase 1: Type Inference (Keep Current Syntax)
- [ ] Update Environment class to store `declared_type` for each variable
- [ ] Implement `infer_type(value)` function
- [ ] Update `create` command to:
  - Ignore the explicit type declaration
  - Infer type from the value
  - Store inferred type as `declared_type`
- [ ] Update `set` command to:
  - Check type compatibility
  - Emit WARNING (not error) on type mismatch
- [ ] Update `append` command to check list element types
- [ ] Update property assignments to check property types
- [ ] Add helpful warning messages with line numbers

### Phase 2: Testing
- [ ] Create `tests/test_type_inference.py` - Test type inference algorithm
- [ ] Create `tests/test_type_warnings.py` - Test warning messages
- [ ] Add tests for list element type inference
- [ ] Add tests for empty list behavior

### Phase 3: Parser Support (Future)
- [ ] Add support for `create <name> to <value>` syntax (typeless)
- [ ] Keep backward compatibility with `create <type> <name> to <value>`
- [ ] Both syntaxes work identically (type always inferred)

## Testing

Unit tests for type system:
- `tests/test_type_inference.py` - Inference tests
- `tests/test_type_checking.py` - Enforcement tests (v0.0.7)
- `tests/test_type_errors.py` - Error message tests (v0.0.7)

## References

- **TypeScript**: Structural typing, type inference
- **Python 3.5+**: Type hints (optional, gradual)
- **Crystal**: Type inference + static checking
- **Raku**: Gradual typing

---

**Status:** This design is approved for implementation in v0.0.6.
