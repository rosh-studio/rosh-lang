# Rosh Language Support for VS Code

Syntax highlighting, snippets, and language support for the Rosh programming language (v0.0.6).

## Features

- **Syntax Highlighting**: All Rosh keywords including new v0.0.6 features
- **Code Snippets**: Quick templates for common patterns
- **Auto-closing**: Automatic closing of quotes and brackets
- **Comment Toggle**: Cmd+/ (Mac) or Ctrl+/ (Windows/Linux) to toggle comments
- **Code Folding**: Fold object/function/if/while/for blocks
- **NEW in v0.6.0**: Support for `stop`, `exit`, type annotations (`:` and `as`), semicolons

## Installation

### Development Installation

1. Copy the `editor/vscode` folder to your VS Code extensions directory:

```bash
# macOS/Linux
cp -r editor/vscode ~/.vscode/extensions/rosh-0.6.0

# Windows
xcopy /E /I editor\vscode %USERPROFILE%\.vscode\extensions\rosh-0.6.0
```

2. Reload VS Code (Cmd+Shift+P > "Developer: Reload Window")

3. Open any `.rosh` file - syntax highlighting will activate automatically!

### From Marketplace (Coming Soon)

```
ext install rosh
```

## Snippets

Type these prefixes and press Tab:

### New in v0.6.0
- `set` - Set variable (create or update)
- `setas` - Set variable with `as` type annotation
- `settype` - Set variable with `:` type annotation
- `while` - While loop
- `for` - For range loop
- `forstep` - For loop with step
- `stop` - Stop program
- `exit` - Exit program

### General
- `object` - Create an object with properties
- `if` - If statement
- `ifelse` - If-else statement
- `function` - Define a function
- `print` - Print a value
- `getprint` - Get and print from stack
- `stackmath` - Stack-based math operation
- `dump` - Dump state
- `load` - Load state

## Example

```rosh
# v0.0.6 syntax with type annotations
set name as string to "Hero"
set health: number to 100
set inventory as list<string> to []

# Create an object
create object player
  set name to "Hero"
  set health to 100
end

# Semicolons for compact code
set x to 1; set y to 2; print x; print y

# Conditional stop
if health is below 10 then
  print "Critical health!"
  stop
end

# Stack operations
get player.health
print stack
```

## Language Features

### Control Flow (v0.0.6)
- Conditionals: `if`, `then`, `else`, `end`
- Loops: `while`, `for`, `in`, `step`
- Loop control: `break`, `continue`
- Program control: `stop`, `exit`, `return`

### Variables (v0.0.6)
- Declaration: `set` (replaces `create number/string`)
- Type annotations: `set x: number to 42` or `set x as number to 42`
- Types: `number`, `string`, `boolean`, `list<T>`, `object`, `any`

### Objects
- Creation: `create object`
- Operations: `clone`, `delete`, `properties`

### I/O
- Output: `print`, `print stack`, `dump`
- Input: `get`, `prompt`, `read`
- State: `save`, `load`

### Lists
- Operations: `append`, `remove`, `contains`
- Utility: `length of`

### Strings
- Manipulation: `split`, `substring`, `trim`
- Case: `lowercase`, `uppercase`
- Search: `indexOf`, `lastIndexOf`

### Math
- Functions: `random`, `abs`, `min`, `max`, `round`, `floor`, `ceil`
- Operators: `plus`, `minus`, `times`, `divided by`

### Stack Operations
- Math: `add`, `subtract`, `multiply`, `divide`
- Manipulation: `dup`, `swap`, `drop`, `push`, `pop`

### Operators
- Comparison: `is`, `equal`, `not`, `below`, `above`
- Logical: `and`, `or`, `not`
- Syntax: `;` (statement separator), `:` (type annotation), `as` (type annotation)

### Comments
```rosh
# This is a comment
```

## Development

To modify this extension:

1. Edit files in `editor/vscode/`
2. Copy to extensions directory (see Installation)
3. Reload VS Code

## Contributing

Issues and pull requests welcome!

## License

TBD
