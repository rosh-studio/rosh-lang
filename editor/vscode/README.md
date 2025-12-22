# Rosh Language Support for VS Code

Syntax highlighting and language support for Rosh v0.2.0.

## Features

- **Syntax Highlighting**: All Rosh keywords and commands
- **Code Snippets**: Quick templates for common patterns
- **Auto-closing**: Automatic closing of quotes and brackets
- **Comment Toggle**: Cmd+/ (Mac) or Ctrl+/ (Windows/Linux)
- **Code Folding**: Fold object/function/if/while/for blocks

## Installation

### Quick Install

```bash
cd rosh-lang/editor/vscode
./install.sh
```

### Manual Installation

Copy to your VS Code extensions directory:

```bash
# macOS/Linux
cp -r editor/vscode ~/.vscode/extensions/rosh-0.2.0

# Windows
xcopy /E /I editor\vscode %USERPROFILE%\.vscode\extensions\rosh-0.2.0
```

Then reload VS Code (Cmd+Shift+P > "Developer: Reload Window").

## Snippets

Type these prefixes and press Tab:

- `object` - Create an object with properties
- `if` - If statement
- `ifelse` - If-else statement
- `when` - Event handler
- `while` - While loop
- `for` - For loop
- `function` - Define a function
- `print` - Print a value

## Example

```rosh
# Create objects
create object player
    set name to "Hero"
    set health to 100
    set x to 400
    set y to 300
end

# Event handlers
when start then
    print "Game started!"
end

when update then
    if player.health is below 0 then
        trigger game_over
    end
end

# Functions
define heal amount
    set player.health to player.health + amount
end
```

## Language Features

### Core Commands
- Objects: `create`, `set`, `get`, `delete`, `clone`
- Inspection: `look`, `examine`, `list`, `dump`, `count`
- Visibility: `hide`, `show`
- Movement: `move`, `reset`

### Control Flow
- Conditionals: `if`, `then`, `else`, `end`
- Loops: `while`, `for`, `in`, `step`
- Events: `when`, `trigger`
- Control: `break`, `continue`, `stop`, `return`

### I/O
- Output: `print`, `say`
- Input: `input`, `prompt`
- State: `save`, `load`

### Operators
- Comparison: `is`, `equal`, `below`, `above`
- Logical: `and`, `or`, `not`
- Arithmetic: `plus`, `minus`, `times`, `divided by`

### Stack Operations
- `push`, `pop`, `peek`, `dup`, `swap`, `drop`, `clear`

## Development

To modify this extension:

1. Edit files in `editor/vscode/`
2. Run `./install.sh` or copy manually
3. Reload VS Code

## License

MIT (pending open-source release)
