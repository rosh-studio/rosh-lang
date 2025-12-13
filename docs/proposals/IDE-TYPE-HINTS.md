# IDE Type Hints & Visualization

**Status:** Design Proposal for v0.0.6
**Last Updated:** 2024-12-12

## Philosophy

Type annotations in Rosh are **optional**, but the IDE should **always show** inferred types to help developers understand their code without cluttering the syntax.

## The Problem

When you write:
```rosh
create x to 42
set x to 100
```

The types ARE known (through inference), but they're invisible. New developers can't tell what type `x` is without running the code or reading docs.

## Proposed Solution: Inlay Hints

The IDE should show **inlay hints** (gray, italic, non-editable text) displaying inferred types:

### Type 1: Inline Type Hints (Recommended)

```rosh
create x to 42           # IDE shows: create x: number to 42
set x to 100             # IDE shows: set x: number to 100
create scores to [1,2,3] # IDE shows: create scores: list<number> to [1,2,3]
```

**Implementation:** VSCode inlay hints (like TypeScript/Rust)
- Gray, italic text
- Appears between variable name and `to`
- Format: `: <type>`
- Not part of the actual code
- Can be toggled on/off

### Type 2: End-of-Line Comments (Alternative)

```rosh
create x to 42           # :number
set x to 100             # :number
create scores to [1,2,3] # :list<number>
```

**Implementation:** Less intrusive, but harder to read

## Syntax Design

### Variable Creation

```rosh
# What you type:
create x to 42

# IDE shows (with inlay hint):
create x: number to 42
      ~~~~~~~~ (gray italic hint)

# With explicit annotation:
create x: number to 42
      ~~~~~~~~ (your code, not a hint)
```

### Variable Assignment

This is the KEY question: should `set` support type annotations?

#### Option A: No Annotations on `set` (Simpler)

```rosh
create x: number to 42   # Type declared here

# Later:
set x to 100             # IDE shows: set x: number to 100
                         #           ~~~~~~~~ (hint only, not syntax)
```

**Rationale:** Type is already known from creation, no need to re-annotate.

**IDE behavior:**
- Shows inferred type as hint
- Cannot add annotation to `set` (syntax error)
- Type checking happens automatically

#### Option B: Optional Annotations on `set` (More Flexible)

```rosh
create x: number to 42   # Type declared here

# Later:
set x to 100             # Works (type already known)
set x: number to 100     # Also works (redundant but allowed for clarity)
set x: string to "hi"    # ERROR: Can't change type!
```

**Rationale:** Allows documenting intent, catches type change attempts.

**IDE behavior:**
- Shows inferred type as hint
- CAN add annotation to `set` (validates consistency)
- Helps catch bugs where you accidentally change types

### Recommendation: **Option B**

Support annotations on `set` for consistency and error catching.

## Complete Examples

### Example 1: Game Variables

```rosh
# What developer types:
create health to 100
create player_name to "Hero"
set health to 90

# What IDE shows (inlay hints in gray):
create health: number to 100
create player_name: string to "Hero"
set health: number to 90
```

### Example 2: Lists

```rosh
# What developer types:
create scores to [95, 87, 92]
create inventory to []

# What IDE shows:
create scores: list<number> to [95, 87, 92]
create inventory: list<any> to []
                  ~~~~~~~~~~ (hint shows it's untyped)
```

### Example 3: Explicit Annotations

```rosh
# Developer provides annotation:
create inventory: list<string> to []

# IDE shows (no hint needed, already explicit):
create inventory: list<string> to []
```

## Hover Information

When hovering over a variable, show:

```
Variable: x
Type: number
Declared: line 5
Current value: 42
```

## Autocomplete

When typing:
```rosh
create inv|
```

IDE suggests:
```
create inventory: list<string> to []
create inventory to []
```

After typing `create x to 42`, when typing `set x`:
```
set x: number to ___
    ~~~~~~~~ (auto-suggests the type)
```

## Error Highlighting

### Type Mismatch at Creation

```rosh
create x: number to "hello"
                    ~~~~~~~
                    ❌ Type mismatch: expected number, got string
```

### Type Mismatch at Assignment

```rosh
create x: number to 42
set x to "hello"
         ~~~~~~~
         ❌ Cannot assign string to number variable 'x'
```

### List Type Mismatch

```rosh
create scores: list<number> to [1, 2, 3]
append "A" to scores
       ~~~
       ❌ Cannot append string to list<number>
```

## Settings

VSCode extension should provide settings:

```json
{
  "rosh.inlayHints.types": true,           // Show type hints
  "rosh.inlayHints.parameterTypes": true,  // Show function param types
  "rosh.typeChecking": "error"             // "error" | "warning" | "off"
}
```

## Final Syntax Specification

### Variable Creation

```rosh
# Syntax: create <name> [: <type>] to <value>
create x to 42                    # Type inferred
create x: number to 42            # Type annotated
```

### Variable Assignment

```rosh
# Syntax: set <name> [: <type>] to <value>
set x to 100                      # Type checked (must match)
set x: number to 100              # Type annotated & checked
```

### Lists

```rosh
# Syntax: create <name> [: list<<type>>] to <value>
create scores to [1, 2, 3]                # Infers list<number>
create scores: list<number> to [1, 2, 3]  # Explicit
```

## Implementation Priority

### Phase 1: Language Support (v0.0.6)
- ✅ Parse type annotations on `create`
- [ ] Parse type annotations on `set`
- ✅ Type inference
- ✅ Type checking at creation
- [ ] Type checking at assignment

### Phase 2: IDE Support (v0.0.7+)
- [ ] Inlay hints for inferred types
- [ ] Hover tooltips
- [ ] Error highlighting
- [ ] Autocomplete with types
- [ ] Settings for hint display

## Visual Design

### Inlay Hint Style

```
Color: #888888 (gray)
Font Style: italic
Font Weight: normal
Prefix: ": "
```

### Example in Editor

```rosh
create x to 42
      ~~~~~~~~
      : number   ← Gray, italic, barely visible until needed
```

### Error Style

```
Color: #ff0000 (red)
Underline: wavy
Severity: error
```

## Summary

**Key Decisions:**
1. Type annotations supported on BOTH `create` and `set`
2. IDE shows inferred types as inlay hints (gray, italic)
3. Explicit annotations override hints
4. Type checking happens at both creation and assignment
5. Clear error messages with line numbers

**Syntax:**
```rosh
create <name>: <type> to <value>    # Optional annotation
set <name>: <type> to <value>       # Optional annotation
```

**Types:**
- Simple: `number`, `string`, `boolean`, `null`, `object`, `any`
- Generic: `list<number>`, `list<string>`, `list<any>`
