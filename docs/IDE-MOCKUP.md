# Rosh IDE Experience - Visual Mockup

This document shows exactly what the IDE should display when working with Rosh code.

## Color Legend

- **Black text** = What you type
- *Gray italic text* = IDE inlay hints (not editable)
- **Red wavy underline** = Type error

---

## Example 1: Basic Variables

### What You Type:
```rosh
set x to 42
set name to "Alice"
set x to 100
```

### What IDE Shows:
```rosh
set x: number to 42
     ~~~~~~~ (gray italic)
set name: string to "Alice"
       ~~~~~~~ (gray italic)
set x: number to 100
     ~~~~~~~ (gray italic)
```

---

## Example 2: Lists

### What You Type:
```rosh
set scores to [95, 87, 92]
set words to ["hello", "world"]
set items to []
```

### What IDE Shows:
```rosh
set scores: list<number> to [95, 87, 92]
          ~~~~~~~~~~~~~ (gray italic)
set words: list<string> to ["hello", "world"]
         ~~~~~~~~~~~~~ (gray italic)
set items: list<any> to []
         ~~~~~~~~~~ (gray italic - warns it's untyped!)
```

---

## Example 3: Explicit Annotations

### What You Type:
```rosh
set inventory: list<string> to []
set inventory to ["sword", "shield"]
```

### What IDE Shows:
```rosh
set inventory: list<string> to []
                 ~~~~~~~~~~~~~ (your code, black text - no hint needed!)
set inventory: list<string> to ["sword", "shield"]
             ~~~~~~~~~~~~~ (gray italic)
```

---

## Example 4: Type Errors

### What You Type:
```rosh
set x: number to "hello"
```

### What IDE Shows:
```rosh
set x: number to "hello"
                    ~~~~~~~ (red wavy underline)
```

**Error Tooltip:**
```
Type mismatch for variable 'x': annotated as number, but value is string
```

---

## Example 5: List Type Errors

### What You Type:
```rosh
set scores: list<number> to ["A", "B", "C"]
```

### What IDE Shows:
```rosh
set scores: list<number> to ["A", "B", "C"]
                               ~~~~~~~~~~~~~~~~ (red wavy underline)
```

**Error Tooltip:**
```
Type mismatch for variable 'scores': annotated as list<number>, but value is list<string>
```

---

## Example 6: Assignment Type Error

### What You Type:
```rosh
set x: number to 42
set x to "hello"
```

### What IDE Shows:
```rosh
set x: number to 42
set x: number to "hello"
     ~~~~~~~ (gray italic)
                 ~~~~~~~ (red wavy underline)
```

**Error Tooltip:**
```
Cannot assign string to number variable 'x'
Declared as number at line 1
```

---

## Example 7: Hover Information

### When You Hover Over Variable:

**Hover over `x` in this code:**
```rosh
set x to 42
```

**Tooltip Shows:**
```
Variable: x
Type: number
Value: 42
Declared: line 1
```

---

## Example 8: Autocomplete

### When Typing:

**You type:** `set inv`

**IDE Suggests:**
```
set inventory: list<string> to []
set inventory to []
```

**You type:** `set x`

**IDE Suggests:**
```
set x: number to ___
     ~~~~~~~ (shows the type!)
```

---

## Example 9: Function Parameters (Future)

### What You Type:
```rosh
define function greet name
    print "Hello " plus name
end
```

### What IDE Shows:
```rosh
define function greet name: any
                          ~~~~ (gray italic - inferred from usage)
    print "Hello " plus name
end
```

### With Explicit Annotation:
```rosh
define function greet name: string
    print "Hello " plus name
end
```

---

## Settings

### VS Code Settings:

```json
{
  // Show type hints as inlay hints
  "rosh.inlayHints.types": true,

  // Show parameter types in function definitions
  "rosh.inlayHints.parameterTypes": true,

  // Type checking mode
  "rosh.typeChecking": "error",  // "error" | "warning" | "off"

  // Color for inlay hints
  "rosh.inlayHints.color": "#888888",

  // Font style for inlay hints
  "rosh.inlayHints.fontStyle": "italic"
}
```

---

## Implementation Notes

### For VS Code Extension:

1. **Inlay Hints API**
   - Use `vscode.languages.registerInlayHintsProvider`
   - Parse Rosh code to find all `create` and `set` statements
   - For each variable, infer type and show as inlay hint

2. **Diagnostics API**
   - Use `vscode.languages.createDiagnosticCollection`
   - Run type checker on save
   - Show errors as red wavy underlines

3. **Hover Provider**
   - Use `vscode.languages.registerHoverProvider`
   - Show variable type, value, and declaration location

4. **Completion Provider**
   - Use `vscode.languages.registerCompletionItemProvider`
   - Suggest variable names with their types
   - Suggest type annotations based on inferred types

---

## Typography Specs

### Inlay Hints
- **Font**: Same as editor
- **Size**: Same as editor (or 90%)
- **Color**: `#888888` (gray)
- **Style**: Italic
- **Opacity**: 70%

### Error Underlines
- **Color**: `#ff0000` (red)
- **Style**: Wavy
- **Thickness**: 2px

### Hover Tooltips
- **Background**: `#1e1e1e` (dark) or `#ffffff` (light)
- **Border**: `#3c3c3c` (dark) or `#cccccc` (light)
- **Padding**: 8px
- **Font**: Monospace

---

## User Experience Goals

1. **Non-intrusive**: Hints appear in gray, easy to ignore
2. **Informative**: Always know what type a variable is
3. **Helpful**: Errors shown immediately, not at runtime
4. **Toggleable**: Can turn off hints if desired
5. **Fast**: No lag when typing

---

## Comparison with Other Languages

### TypeScript Inlay Hints
```typescript
const x = 42          // Shows: const x: number = 42
function add(a, b) {  // Shows: function add(a: any, b: any)
```

### Rust Inlay Hints
```rust
let x = 42;           // Shows: let x: i32 = 42;
let items = vec![];   // Shows: let items: Vec<_> = vec![];
```

### Rosh Inlay Hints (Proposed)
```rosh
set x to 42        # Shows: set x: number to 42
set items to []    # Shows: set items: list<any> to []
```

Same concept, Rosh-style syntax!
