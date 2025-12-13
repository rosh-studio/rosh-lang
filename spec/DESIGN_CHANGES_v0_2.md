# Rosh Design Changes - v0.2

> **Date:** 2025-12-10
> **Status:** In Progress

## Overview

This document captures key design decisions made during early implementation that improve Rosh's usability, especially for spoken-first programming and IDE integration.

---

## 1. Indentation: Cosmetic, Not Structural

### Decision
**Indentation is purely cosmetic for readability. The lexer/parser do not enforce or require indentation.**

### Rationale
- Spoken-first design: When dictating code, specifying indentation is unnatural
- IDE responsibility: Modern editors should handle auto-indentation automatically
- Simplicity: Reduces parser complexity and error-prone INDENT/DEDENT token handling
- Flexibility: Developers can format code however they prefer

### Implementation
- Lexer does NOT emit INDENT/DEDENT tokens
- Parser relies solely on explicit keywords (`end`) or implied boundaries
- Indentation can be any amount of spaces/tabs for readability

### Example
```rosh
# All these are equivalent:
create object player
  set name to "Hero"
  set health to 100
end

create object player
set name to "Hero"
set health to 100
end

create object player
    set name to "Hero"
    set health to 100
end
```

---

## 2. Optional/Implied `end` Keywords

### Decision
**The `end` keyword can be implied at dedentation points or section boundaries.**

### Rationale
- Natural spoken flow: "create object player, set name to hero, set health to 100" (pause) "print player"
- Less verbose: Reduces boilerplate in simple cases
- IDE-friendly: Editor can auto-insert/highlight implied boundaries

### Implementation Rules
1. Explicit `end` always works (most explicit, recommended for complex blocks)
2. Dedenting to lower indentation level implies `end` for the current block
3. End of file implies `end` for any open blocks
4. New top-level statement implies `end` for previous block

### Example
```rosh
# Explicit end (clearest)
create object player
  set name to "Hero"
end
print player

# Implied end at dedent
create object player
  set name to "Hero"
  set health to 100

print player  # Dedent + new statement implies end

# Implied end at EOF
create object player
  set name to "Hero"
# EOF implies end
```

### IDE Support
- Syntax highlighter should show implied `end` boundaries (subtle line or indicator)
- Auto-formatter can optionally insert explicit `end` keywords
- Linter can warn if nesting is ambiguous

---

## 3. Use `print` Instead of `say`

### Decision
**The primary output command is `print`, not `say`.**

### Rationale
- **Standard terminology**: Every major language uses `print` (Python, Ruby, Go, etc.)
- **Generic/redirectable**: `print` can output to stdout, files, network, GUI, speech, etc.
- **Professional**: Better for production code, less whimsical
- **Spoken-friendly**: "print" is still easy to say and understand

### Migration
- Rename `say` → `print` throughout codebase
- Keep `say` as an alias initially for backwards compatibility
- Eventually `say` could be a higher-level command that uses speech synthesis

### Example
```rosh
print "Hello, World!"
print player
print player name
```

---

## 4. Stack-Based `get` Command

### Decision
**Add explicit `get` command that pushes values onto the data stack.**

### Rationale
- **Aligns with stack-based core**: Rosh is fundamentally stack-based
- **Powerful composition**: Enables functional-style data manipulation
- **Natural spoken flow**: "get player health, get player max health, divide, print"
- **Explicit data flow**: Makes stack operations visible and controllable

### Stack Semantics
```rosh
# Push values onto stack
get player              # Stack: [<player object>]
get health              # Get property from TOS, Stack: [100]
print                   # Pop and print TOS: "100"

# Stack arithmetic
get player health       # Stack: [100]
get player max-health   # Stack: [100, 150]
divide                  # Stack: [0.666...]
print                   # Prints: 0.666...

# Multiple results
get enemies             # If "enemies" is a list, pushes entire list
                        # Stack: [[enemy1, enemy2, enemy3]]
```

### Property Access
```rosh
# Chained property access
get player              # Push object
get health              # Access .health property from TOS

# Shorthand (parser expands to above)
get player health       # Equivalent to: get player, get health
```

### Variables
```rosh
# Variables are also accessed via get
create number x as 42
get x                   # Stack: [42]
print                   # Prints: 42
```

---

## 5. IDE Integration Plan

### Goals
1. **Auto-indentation**: Editor automatically indents after block-starting keywords
2. **Auto-completion**: Context-aware suggestions for variables, properties, keywords
3. **Syntax highlighting**: Keywords, literals, comments, implied boundaries
4. **Error detection**: Real-time parsing errors and warnings
5. **Auto-formatting**: Consistent code style (indentation, spacing)

### VS Code Extension Requirements

#### Language Server Protocol (LSP)
Implement a Rosh language server providing:
- **Syntax validation**: Parse code and report errors
- **Semantic tokens**: Rich syntax highlighting
- **Auto-completion**: Context-aware suggestions
- **Hover information**: Type info, documentation for symbols
- **Go to definition**: Jump to variable/function definitions
- **Formatting**: Auto-format code on save

#### TextMate Grammar
For basic syntax highlighting before LSP is ready:
- Keywords: `create`, `object`, `set`, `to`, `end`, `print`, `get`, `if`, `then`, `else`, `define`, `function`, `call`
- Operators: `plus`, `minus`, `times`, `divided`, `by`, `is`, `above`, `below`
- Literals: strings, numbers, booleans, null
- Comments: `#` to end of line

#### Auto-Indentation Rules
```json
{
  "indentationRules": {
    "increaseIndentPattern": "^\\s*(create object|if .* then|define function|else)\\s*$",
    "decreaseIndentPattern": "^\\s*(end|else)\\s*$"
  }
}
```

### Other IDEs
- **Neovim/Vim**: Tree-sitter grammar + LSP client
- **Emacs**: Major mode + LSP client
- **IntelliJ**: Plugin with PSI (Program Structure Interface)
- **Sublime Text**: Syntax definition + LSP client

---

## 6. Lexer Design for IDE Support

### Token Stream Design
The lexer should produce a rich token stream that IDEs can use for:

1. **Syntax highlighting**: Token types (keyword, identifier, literal, operator, comment)
2. **Error recovery**: Continue lexing after errors to highlight remaining code
3. **Semantic analysis**: Distinguish variable names, function names, property names
4. **Position tracking**: Line, column, byte offset for each token

### Example Token Structure
```python
@dataclass
class Token:
    type: TokenType
    value: any
    line: int
    column: int
    byte_offset: int  # For efficient file navigation
    length: int       # Token length in source
```

### Incremental Lexing
For IDE performance, support incremental re-lexing:
- Only re-lex changed regions of file
- Cache lexing results per line/block
- Fast path for single-line edits

---

## Next Steps

1. ✅ Archive v0.1 spec
2. 🔄 Refactor lexer (remove INDENT/DEDENT)
3. ⏳ Update parser (implied `end`, `get` command)
4. ⏳ Rename `say` → `print`
5. ⏳ Implement data stack
6. ⏳ Update examples
7. ⏳ Create VS Code extension skeleton
8. ⏳ Implement TextMate grammar
9. ⏳ Plan LSP server architecture

---

## Discussion Notes

### Should `print` with no argument pop from stack?
**Yes!** This enables concise stack-based programming:
```rosh
get player health
get player max-health
divide
print              # Pop and print TOS
```

### Should property access be stack-based or expression-based?
**Hybrid approach:**
- `get player health` is stack-based (pushes value)
- `set player health to 100` is expression-based (traditional assignment)
- Best of both worlds: simple assignments stay simple, complex operations use stack

### How to handle multiple return values?
Use the stack naturally:
```rosh
define function get-position player
  get player x
  get player y
end

call get-position player
# Stack now has: [x_value, y_value]
print  # Prints y_value
print  # Prints x_value
```

---

## See Also
- `rosh_full_spec_v0_1.md` (archived) - Original comprehensive spec
- `../README.md` - Project overview
- `../src/rosh/` - Python reference implementation
