"""
Rosh CLI - Command-line interface for running Rosh programs
"""

import sys
import argparse
import os
from pathlib import Path
from .lexer import Lexer
from .parser import Parser
from .interpreter import Interpreter
from .errors import RoshError
from .color import get_color_output
from . import __version__

# Try to import readline for command history and tab completion
try:
    import readline
    READLINE_AVAILABLE = True
except ImportError:
    READLINE_AVAILABLE = False


def resolve_rosh_path(path: str) -> str:
    """Resolve a path to a .rosh file.

    If path is a directory, looks for main.rosh inside it.
    Otherwise returns the path as-is.

    Args:
        path: File or directory path

    Returns:
        Resolved path to .rosh file

    Raises:
        FileNotFoundError: If directory has no main.rosh
    """
    from pathlib import Path

    p = Path(path)
    if p.is_dir():
        main_path = p / "main.rosh"
        if main_path.exists():
            return str(main_path)
        else:
            raise FileNotFoundError(
                f"No main.rosh found in {path}. "
                f"Create {main_path} or specify a .rosh file directly."
            )
    return path


def _parse_test_input(input_string: str) -> list:
    """Parse comma-separated test inputs with escape support

    Args:
        input_string: Comma-separated inputs (supports \\, for literal commas)

    Returns:
        List of input strings

    Examples:
        "foo,bar,baz" -> ["foo", "bar", "baz"]
        "foo\\,bar,baz" -> ["foo,bar", "baz"]
    """
    inputs = []
    current = []
    i = 0
    while i < len(input_string):
        if input_string[i] == '\\' and i + 1 < len(input_string) and input_string[i + 1] == ',':
            # Escaped comma
            current.append(',')
            i += 2
        elif input_string[i] == ',':
            # Un-escaped comma - end of input
            inputs.append(''.join(current))
            current = []
            i += 1
        else:
            current.append(input_string[i])
            i += 1

    # Add final input
    if current or inputs:  # Handle empty string case
        inputs.append(''.join(current))

    return inputs


def output_toml(interpreter: Interpreter):
    """Output final stack value as TOML

    Args:
        interpreter: The interpreter with final state
    """
    try:
        # Use tomli-w for writing TOML
        import tomli_w
    except ImportError:
        print("Error: tomli-w not installed. Run: pip install tomli-w", file=sys.stderr)
        sys.exit(1)

    from .values import rosh_to_python

    # Get final stack value
    if not interpreter.data_stack:
        # Empty stack - output comment
        print("# (empty)")
        return

    value = interpreter.data_stack[-1]

    # Convert to Python dict/list (TOML-compatible)
    python_value = rosh_to_python(value)

    # Handle different value types
    if python_value is None or python_value == "null":
        # Null values - output comment (TOML doesn't have null)
        print("# (null)")
    elif isinstance(python_value, dict):
        # Object - output as TOML table
        # Remove internal fields (_uuid, _name, _id)
        filtered = {k: v for k, v in python_value.items() if not k.startswith('_')}
        if filtered:
            toml_str = tomli_w.dumps(filtered)
            print(toml_str, end='')
        else:
            print("# (empty object)")
    elif isinstance(python_value, list):
        # List - wrap in a table for valid TOML
        toml_str = tomli_w.dumps({"value": python_value})
        print(toml_str, end='')
    elif isinstance(python_value, str) and python_value.startswith('<function'):
        # Function - output comment
        print(f"# {python_value}")
    else:
        # Primitive value - wrap in table
        toml_str = tomli_w.dumps({"value": python_value})
        print(toml_str, end='')


def output_toon(interpreter: Interpreter):
    """Output final stack value as TOON format

    Args:
        interpreter: The interpreter with final state
    """
    from .toon_encoder import toon_output

    # Get final stack value
    if not interpreter.data_stack:
        # Empty stack - output comment
        print("# (empty)")
        return

    value = interpreter.data_stack[-1]

    # Convert to TOON format
    toon_str = toon_output(value)
    print(toon_str)


def _fuzzy_match_command(word: str, interpreter=None):
    """Find closest matching command using fuzzy string matching"""
    import difflib

    # List of all available commands
    commands = [
        # Core commands
        'create', 'set', 'get', 'print', 'dump', 'save', 'load',
        'import', 'eval', 'read', 'write',
        'if', 'then', 'else', 'while', 'end',
        'define', 'function', 'call',
        # Stack operations
        'add', 'subtract', 'multiply', 'divide',
        'dup', 'swap', 'drop',
        'push', 'pop',
        # Object management
        'clone', 'delete', 'properties', 'props',
        # Universal REPL commands
        'list', 'ls', 'objects', 'look', 'l', 'examine', 'ex', 'inspect', 'x',
        # MUD commands
        'goto', 'go', 'connect', 'link',
        # AI commands
        'prompt',
        # Help
        'help',
    ]

    # Add user-defined functions if interpreter available
    if interpreter:
        try:
            for name in interpreter.global_env.bindings.keys():
                from .values import RoshFunction
                if isinstance(interpreter.global_env.bindings[name], RoshFunction):
                    commands.append(name)
        except:
            pass

    # Find close matches (up to 3, with cutoff of 0.6)
    matches = difflib.get_close_matches(word.lower(), commands, n=1, cutoff=0.6)

    return matches[0] if matches else None


def _list_objects(interpreter, out):
    """List all objects in the current environment (Universal REPL command)"""
    from .values import RoshObject, rosh_to_python

    objects = []
    for name in interpreter.current_env.bindings.keys():
        try:
            value = interpreter.current_env.get(name)
            if isinstance(value, RoshObject):
                objects.append((name, value))
        except:
            pass

    if not objects:
        out.dim("No objects defined. Use 'create object <name>' to create one.")
        return

    out.print("Objects:", style="bold cyan")
    for name, obj in objects:
        # Get type (object name)
        obj_type = obj.name if hasattr(obj, 'name') and obj.name else "object"
        # Get position if available
        props = []
        if obj.has('x'):
            x = rosh_to_python(obj.get('x'))
            y = rosh_to_python(obj.get('y')) if obj.has('y') else 0
            props.append(f"at [{x}, {y}]")
        if obj.has('color'):
            props.append(f"color={rosh_to_python(obj.get('color'))}")

        prop_str = f" ({', '.join(props)})" if props else ""
        out.print(f"  {name} ({obj_type}){prop_str}", style="green")


def _examine_object(interpreter, out, obj_name: str):
    """Show properties of a specific object (Universal REPL command)"""
    from .values import RoshObject, rosh_to_python
    import difflib

    # Check if object exists
    if not interpreter.current_env.exists(obj_name):
        # Object not found - suggest alternatives
        all_objects = []
        for name in interpreter.current_env.bindings.keys():
            try:
                value = interpreter.current_env.get(name)
                if isinstance(value, RoshObject):
                    all_objects.append(name)
            except:
                pass

        out.error(f"Object '{obj_name}' not found.")

        if all_objects:
            # Fuzzy match
            matches = difflib.get_close_matches(obj_name, all_objects, n=3, cutoff=0.4)
            if matches:
                out.print(f"Did you mean: {', '.join(matches)}?", style="yellow")
            else:
                out.print(f"Available: {', '.join(all_objects)}", style="dim")
        else:
            out.dim("No objects defined yet.")
        return

    value = interpreter.current_env.get(obj_name)

    if not isinstance(value, RoshObject):
        # Not an object, just show its value
        out.print(f"{obj_name} = {rosh_to_python(value)}", style="cyan")
        return

    # Show object details
    out.print()
    out.print(f"=== {obj_name} ===", style="bold cyan")
    obj_type = value.name if hasattr(value, 'name') and value.name else "object"
    out.print(f"Type: {obj_type}", style="dim")
    if hasattr(value, 'uuid') and value.uuid:
        out.print(f"UUID: {value.uuid}", style="dim")
    if hasattr(value, 'id') and value.id:
        out.print(f"ID: {value.id}", style="dim")
    out.print()

    # Get all properties from the object
    if hasattr(value, 'property_stacks') and value.property_stacks:
        for prop_name in value.property_stacks:
            prop_value = value.get(prop_name)
            py_value = rosh_to_python(prop_value)
            out.print(f"  {prop_name}: {repr(py_value)}", style="green")
    else:
        out.dim("  (no properties)")
    out.print()


def _fuzzy_match_object(interpreter, obj_name: str) -> str:
    """Find closest matching object name"""
    from .values import RoshObject
    import difflib

    all_objects = []
    for name in interpreter.current_env.bindings.keys():
        try:
            value = interpreter.current_env.get(name)
            if isinstance(value, RoshObject):
                all_objects.append(name)
        except:
            pass

    matches = difflib.get_close_matches(obj_name, all_objects, n=1, cutoff=0.4)
    return matches[0] if matches else None


COMMAND_USAGE_HINTS = {
    'create': {
        'message': "Tell me what to create.",
        'examples': [
            "create object <name> ... end",
            "create <name> to <value>",
            "create number <name> as <value>",
            "create string <name> as <value>",
            "create <template> <name>  # clone template with custom name",
            "create <template>         # clone template with auto name",
        ],
    },
    'clone': {
        'message': "Tell me what to clone.",
        'examples': [
            "clone <source> as <target>",
            "clone <source>  # auto-named copy",
        ],
    },
    'delete': {
        'message': "Tell me what to delete.",
        'examples': [
            "delete <object name>",
            "delete <property> from <object>",
        ],
    },
}


def _show_command_usage(out, command: str) -> bool:
    """Display friendly guidance when a command is missing its arguments."""
    info = COMMAND_USAGE_HINTS.get(command)
    if not info:
        return False

    out.warning(info.get('message', f"{command.title()} needs details."))
    examples = info.get('examples', [])
    if examples:
        out.print("Try one of these:", style="bold cyan")
        for example in examples:
            out.print(f"  {example}", style="green")
    return True


def _get_command(interpreter, out, identifier: str, prop_name: str = None):
    """Unified get command - get object or property, push to stack, display.

    Supports:
    - get <name> - get object by name
    - get <uuid> - get object by UUID (partial match, 8+ chars)
    - get <obj> <prop> - get property value
    """
    from .values import RoshObject, rosh_to_python
    import difflib

    # First, try to find the object by name
    obj = None
    obj_name_found = None

    if interpreter.current_env.exists(identifier):
        obj = interpreter.current_env.get(identifier)
        obj_name_found = identifier
    else:
        # Try to find by UUID (partial match, 8+ chars)
        if len(identifier) >= 8:
            for name in interpreter.current_env.bindings.keys():
                try:
                    value = interpreter.current_env.get(name)
                    if isinstance(value, RoshObject):
                        if hasattr(value, 'uuid') and value.uuid:
                            if value.uuid.startswith(identifier) or value.uuid == identifier:
                                obj = value
                                obj_name_found = name
                                break
                except:
                    pass

    if obj is None:
        # Object not found - suggest alternatives
        all_objects = []
        for name in interpreter.current_env.bindings.keys():
            try:
                value = interpreter.current_env.get(name)
                if isinstance(value, RoshObject):
                    all_objects.append(name)
            except:
                pass

        out.error(f"Object '{identifier}' not found.")

        if all_objects:
            matches = difflib.get_close_matches(identifier, all_objects, n=3, cutoff=0.4)
            if matches:
                out.print(f"Did you mean: {', '.join(matches)}?", style="yellow")
            else:
                out.print(f"Available: {', '.join(all_objects)}", style="dim")
        else:
            out.dim("No objects defined yet.")
        return

    # If no property requested, return the object itself
    if prop_name is None:
        # Push object to stack
        interpreter.data_stack.append(obj)
        # Display it
        if isinstance(obj, RoshObject):
            obj_type = obj.name if hasattr(obj, 'name') and obj.name else "object"
            out.print(f"<{obj_type}: {obj_name_found}>", style="cyan")
        else:
            out.print(f"{rosh_to_python(obj)}", style="cyan")
        return

    # Property requested - get it from the object
    if not isinstance(obj, RoshObject):
        out.error(f"'{identifier}' is not an object, cannot get property '{prop_name}'")
        return

    # Special case: uuid property
    if prop_name.lower() == 'uuid':
        if hasattr(obj, 'uuid') and obj.uuid:
            interpreter.data_stack.append(obj.uuid)
            out.print(f"{obj.uuid}", style="cyan")
        else:
            out.error(f"Object '{obj_name_found}' has no UUID")
        return

    # Check if property exists
    if not obj.has(prop_name):
        # Property not found - suggest alternatives
        available_props = list(obj.property_stacks.keys()) if hasattr(obj, 'property_stacks') else []
        out.error(f"Property '{prop_name}' not found on '{obj_name_found}'")
        if available_props:
            matches = difflib.get_close_matches(prop_name, available_props, n=3, cutoff=0.4)
            if matches:
                out.print(f"Did you mean: {', '.join(matches)}?", style="yellow")
            else:
                out.print(f"Available: {', '.join(available_props)}", style="dim")
        return

    # Get the property value
    prop_value = obj.get(prop_name)
    py_value = rosh_to_python(prop_value)

    # Push to stack
    interpreter.data_stack.append(prop_value)

    # Display it
    out.print(f"{py_value}", style="cyan")


def run_file(filepath: str, toml_output: bool = False, toon_output: bool = False, test_inputs: list = None):
    """Run a Rosh program from a file

    Args:
        filepath: Path to the Rosh file
        toml_output: If True, output final stack value as TOML
        toon_output: If True, output final stack value as TOON
        test_inputs: Optional list of test inputs for test mode

    Returns:
        Interpreter: The interpreter with the script's final state
    """
    try:
        # Resolve directory to main.rosh if needed
        filepath = resolve_rosh_path(filepath)

        path = Path(filepath)
        if not path.exists():
            print(f"Error: File not found: {filepath}", file=sys.stderr)
            sys.exit(1)

        # Check for common wrong file types
        extension = path.suffix.lower()
        if extension == '.md':
            print(f"Error: Can't run a Markdown file! 📝", file=sys.stderr)
            print(f"", file=sys.stderr)
            print(f"You tried to run: {filepath}", file=sys.stderr)
            print(f"", file=sys.stderr)
            print(f"Did you mean to:", file=sys.stderr)
            print(f"  - Read it? Try: cat {filepath}", file=sys.stderr)
            print(f"  - Run the manual? Try: rosh ROSH-MANUAL.rosh", file=sys.stderr)
            print(f"  - Run an example? Try: rosh examples/dungeon-crawler.rosh", file=sys.stderr)
            print(f"", file=sys.stderr)
            print(f"Rosh files end in .rosh", file=sys.stderr)
            sys.exit(1)
        elif extension in ['.txt', '.py', '.js', '.json', '.toml', '.yaml', '.yml']:
            print(f"Error: '{extension}' files aren't Rosh programs!", file=sys.stderr)
            print(f"", file=sys.stderr)
            print(f"Rosh programs use the .rosh extension", file=sys.stderr)
            print(f"Try: rosh ROSH-MANUAL.rosh", file=sys.stderr)
            sys.exit(1)

        source = path.read_text()
        interpreter = run_source(source, filepath, toml_output=toml_output, toon_output=toon_output, test_inputs=test_inputs)
        return interpreter

    except RoshError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


def run_source(source: str, filename: str = "<stdin>", interpreter: Interpreter = None, toml_output: bool = False, toon_output: bool = False, test_inputs: list = None):
    """Run Rosh source code

    Args:
        source: The Rosh source code
        filename: Name of the file (for error messages)
        interpreter: Optional existing interpreter to reuse
        toml_output: If True, output final stack value as TOML
        toon_output: If True, output final stack value as TOON
        test_inputs: Optional list of test inputs for test mode
    """
    from .errors import StopExecution

    # Lex
    lexer = Lexer(source)
    tokens = lexer.tokenize()

    # Parse
    parser = Parser(tokens)
    program = parser.parse()

    # Interpret (use provided interpreter or create new one)
    if interpreter is None:
        test_mode = bool(test_inputs)
        interpreter = Interpreter(test_mode=test_mode, test_inputs=test_inputs or [])

    # Set source code for checksum calculation (metadata system)
    interpreter.source_code = source

    try:
        interpreter.execute(program)
    except StopExecution:
        # Program was stopped with 'stop' or 'exit' command - this is normal
        pass

    # Handle format-specific output if requested
    if toml_output:
        output_toml(interpreter)
    elif toon_output:
        output_toon(interpreter)

    return interpreter


def run_repl(interpreter: Interpreter = None):
    """Run Rosh in interactive REPL mode

    Args:
        interpreter: Optional interpreter with pre-loaded state (for -i mode)
    """
    out = get_color_output()

    out.print(f"🤖 rosh v{__version__}", style="bold cyan")

    if interpreter:
        out.print("Interactive REPL (script state preserved)", style="dim green")
    else:
        out.print("Interactive REPL", style="dim")
    out.print()

    out.print("Quick Start:", style="bold yellow")
    out.print("  help              - Show all commands", style="dim")
    out.print("  help <command>    - Get help on specific command", style="dim")
    out.print("  import mud        - Load MUD standard library", style="green")
    out.print("  create thing      - Create an object instance", style="green")
    out.print("  look              - Look around current room", style="green")
    out.print()

    out.print("Commands:", style="bold")
    out.print("  create, get, set, print, clone, delete, properties", style="cyan")
    out.print("  look, goto, connect, prompt, import, save, load, dump", style="cyan")
    out.print()

    out.print("Type 'exit' to quit | 'license' for license info | 'alias' for shortcuts", style="dim")
    if READLINE_AVAILABLE:
        out.print("History: ↑/↓ arrows | Tab completion enabled", style="dim")
    out.print()

    # Use provided interpreter or create new one
    if interpreter is None:
        interpreter = Interpreter()

    # Check for security flags (passed from main via global)
    if '_disable_remote_imports' in globals() and _disable_remote_imports:
        interpreter.allow_remote_imports = False
        out.print("🔒 Remote imports disabled (--no-remote-imports)", style="yellow")
        out.print()

    buffer = []
    aliases = {}  # Store command aliases

    # Set up readline for command history and tab completion
    if READLINE_AVAILABLE:
        # History file location
        history_file = os.path.expanduser('~/.rosh_history')

        # Load history if it exists
        if os.path.exists(history_file):
            try:
                readline.read_history_file(history_file)
            except:
                pass

        # Set history length
        readline.set_history_length(1000)

        # Tab completion function
        def completer(text, state):
            # List of Rosh keywords and common commands
            options = [
                'create', 'object', 'set', 'to', 'print', 'if', 'then', 'else', 'end',
                'define', 'function', 'call', 'import', 'from', 'while', 'push', 'pop',
                'get', 'dup', 'swap', 'drop', 'dump', 'save', 'load', 'prompt', 'eval', 'using',
                'exec', 'is', 'equal', 'not', 'and', 'or', 'true', 'false', 'null',
                'clone', 'delete', 'properties', 'props', 'goto', 'go', 'look', 'l',
                'examine', 'ex', 'connect', 'link', 'help',
                'alias', 'exit', 'quit'
            ]

            # Add all defined aliases
            options.extend(aliases.keys())

            # Filter options that start with text
            matches = [opt for opt in options if opt.startswith(text)]

            if state < len(matches):
                return matches[state]
            return None

        # Set up tab completion
        readline.set_completer(completer)
        readline.parse_and_bind('tab: complete')

    while True:
        try:
            # Determine prompt (>>> for new statement, ... for continuation)
            prompt = "rosh> " if not buffer else "...   "
            line = input(prompt)

            # Handle exit command
            if line.strip() in ('exit', 'quit'):
                break

            # Handle license/copyright command (like Python)
            if line.strip() in ('license', 'copyright', 'help license'):
                out.print()
                out.print("MIT License", style="bold cyan")
                out.print()
                out.print("Copyright (c) 2024 Rosh Project", style="dim")
                out.print()
                out.print("Permission is hereby granted, free of charge, to any person obtaining a copy")
                out.print("of this software and associated documentation files (the \"Software\"), to deal")
                out.print("in the Software without restriction, including without limitation the rights")
                out.print("to use, copy, modify, merge, publish, distribute, sublicense, and/or sell")
                out.print("copies of the Software, and to permit persons to whom the Software is")
                out.print("furnished to do so, subject to the following conditions:")
                out.print()
                out.print("The above copyright notice and this permission notice shall be included in all")
                out.print("copies or substantial portions of the Software.")
                out.print()
                out.print("THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR")
                out.print("IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,")
                out.print("FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE")
                out.print("AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER")
                out.print("LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,")
                out.print("OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE")
                out.print("SOFTWARE.")
                out.print()
                out.rule("TRADEMARK NOTICE", style="yellow")
                out.print()
                out.print("\"Rosh\" and the Rosh logo are trademarks of the Rosh Project.", style="yellow")
                out.print("You may use the Rosh name to refer to this project, but you may not use")
                out.print("them in a way that suggests endorsement without permission.")
                out.print()
                out.print("See LICENSE file for full details.", style="dim")
                out.print()
                continue

            # Handle alias command: alias <name> <expansion>
            if line.strip() == 'alias' or line.strip().startswith('alias '):
                parts = line.strip().split(None, 2)  # Split into: ['alias', name, expansion]
                if len(parts) >= 3:
                    alias_name = parts[1]
                    alias_expansion = parts[2]
                    aliases[alias_name] = alias_expansion
                    out.success(f"Alias created: {alias_name} → {alias_expansion}")
                elif len(parts) == 2 and parts[1] in aliases:
                    # Show existing alias
                    out.print(f"{parts[1]} → {aliases[parts[1]]}", style="cyan")
                elif len(parts) == 1:
                    # List all aliases
                    if aliases:
                        out.print("Current aliases:", style="bold")
                        for name, expansion in aliases.items():
                            out.print(f"  {name} → {expansion}", style="cyan")
                    else:
                        out.dim("No aliases defined")
                else:
                    out.print("Usage: alias <name> <expansion>", style="yellow")
                continue

            # Expand aliases if line starts with an alias
            first_word = line.strip().split()[0] if line.strip() else ""
            if first_word in aliases:
                # Expand the alias
                expanded = aliases[first_word]
                # If there are additional arguments, append them
                rest = line.strip().split(None, 1)[1] if len(line.strip().split()) > 1 else ""
                if rest:
                    line = f"{expanded} {rest}"
                else:
                    line = expanded
                out.dim(f"→ {line}")  # Show expansion

            # ===== Universal REPL Commands =====
            # "If it works somewhere, it should work everywhere"
            stripped = line.strip().lower()
            parts = line.strip().split()

            # version (no args) - show interpreter version
            if stripped == 'version':
                out.print(f"Rosh v{__version__}", style="cyan")
                continue

            # Provide friendlier guidance for commands missing arguments
            if len(parts) == 1 and _show_command_usage(out, parts[0].lower()):
                continue

            # list / ls / objects (no args) - show all objects
            if stripped in ('list', 'ls', 'objects', 'list objects'):
                _list_objects(interpreter, out)
                continue

            # look (no args) - same as list
            if stripped in ('look', 'l'):
                _list_objects(interpreter, out)
                continue

            # look <obj> / examine <obj> / inspect <obj> / x <obj> - show object properties
            if len(parts) >= 2 and parts[0].lower() in ('look', 'l', 'examine', 'ex', 'inspect', 'x'):
                obj_name = parts[1]
                _examine_object(interpreter, out, obj_name)
                continue

            # clear / cls - clear screen (simple version)
            if stripped in ('clear', 'cls'):
                import subprocess
                subprocess.run('clear' if sys.platform != 'win32' else 'cls', shell=True)
                continue

            # get <obj> or get <obj> <prop> - unified get command (#017)
            if len(parts) >= 2 and parts[0].lower() == 'get':
                identifier = parts[1]
                prop_name = parts[2] if len(parts) >= 3 else None
                _get_command(interpreter, out, identifier, prop_name)
                continue

            # Add line to buffer
            buffer.append(line)

            # Check if we need more input (waiting for 'end')
            # Simple heuristic: if line contains 'create object', 'if', 'define function', etc.
            # we need to wait for 'end'
            stripped = line.strip().lower()
            keywords_needing_end = ['create object', 'if ', 'define function']

            if any(stripped.startswith(kw) for kw in keywords_needing_end):
                # Wait for 'end'
                continue

            # If buffer has content and last line is 'end', execute
            if buffer and buffer[-1].strip().lower() == 'end':
                source = '\n'.join(buffer)
                buffer = []
                try:
                    interpreter = run_source(source, "<repl>", interpreter)
                except RoshError as e:
                    out.error(str(e))
                    # Try to get AI suggestion if available
                    if interpreter:
                        suggestion = interpreter._suggest_fix_with_ai(str(e), source)
                        if suggestion:
                            out.print(f"\n💡 AI Suggestion: {suggestion}", style="yellow")
                continue

            # If we have a simple statement (no 'end' needed), execute immediately
            # unless we're in the middle of a block
            if not buffer or len(buffer) == 1:
                source = '\n'.join(buffer)
                buffer = []
                try:
                    interpreter = run_source(source, "<repl>", interpreter)
                except RoshError as e:
                    error_msg = str(e)

                    # Simplify common errors for REPL
                    # "Syntax error: Unexpected token: IDENTIFIER" → Try to evaluate as variable
                    if "Unexpected token: IDENTIFIER" in error_msg or "Unexpected token in expression: IDENTIFIER" in error_msg:
                        # Extract the word - might be a variable name
                        word = source.strip().split()[0] if source.strip() else "???"

                        # Try to evaluate it as a variable reference
                        if interpreter and interpreter.current_env.exists(word):
                            # It's a variable! Print its value
                            value = interpreter.current_env.get(word)
                            from .values import rosh_to_python
                            output = rosh_to_python(value)
                            out.print(output, style="cyan")
                        else:
                            out.error(f"Unknown command: {word}")

                            # Fuzzy match against available commands
                            suggestion = _fuzzy_match_command(word, interpreter)
                            if suggestion:
                                out.print(f"Did you mean: {suggestion}?", style="yellow")
                            else:
                                out.dim("Type 'alias' to see available aliases, or use Rosh syntax")
                    else:
                        out.error(str(e))
                        # Only show AI suggestion for non-trivial errors
                        if interpreter and "Unknown command" not in error_msg:
                            suggestion = interpreter._suggest_fix_with_ai(str(e), source)
                            if suggestion:
                                out.print(f"\n💡 AI Suggestion: {suggestion}", style="yellow")

        except KeyboardInterrupt:
            print("\nKeyboardInterrupt")
            buffer = []
            continue
        except EOFError:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")
            buffer = []

    # Save history on exit
    if READLINE_AVAILABLE:
        try:
            readline.write_history_file(history_file)
        except:
            pass


def copy_sprite_assets(source_path: Path, output_dir: Path, sprite_assets: dict):
    """Copy only the sprite assets that are actually used in the game (v0.1.7)

    Searches for sprite files in these locations (in order):
    1. Same directory as source file
    2. ../assets/ relative to source file
    3. rosh-lang/assets/ (distributed assets)
    4. examples/games/assets/ (DEPRECATED - will be removed in v0.2.0)

    Args:
        source_path: Path to the source .rosh file
        output_dir: Output directory for the game
        sprite_assets: Dict of {object_name: sprite_filename} from transpiler
    """
    import shutil
    from pathlib import Path

    # Create assets directory in output
    assets_dir = output_dir / 'assets'
    assets_dir.mkdir(parents=True, exist_ok=True)

    # Search paths for assets
    source_dir = source_path.parent

    # Find rosh-lang root (look for assets/ folder)
    rosh_lang_root = source_dir
    for _ in range(5):  # Search up to 5 levels
        if (rosh_lang_root / 'assets' / 'sprites').exists():
            break
        rosh_lang_root = rosh_lang_root.parent

    search_paths = [
        source_dir / 'assets',  # Same dir as .rosh file
        source_dir.parent / 'assets',  # ../assets/
        rosh_lang_root / 'assets' / 'sprites',  # rosh-lang/assets/sprites/
        rosh_lang_root / 'assets' / 'sounds',  # rosh-lang/assets/sounds/
        source_dir.parent / 'games' / 'assets',  # For examples (deprecated)
        Path('examples/games/assets'),  # Absolute fallback (deprecated)
    ]

    # Track if we used deprecated paths
    deprecated_path_used = False

    copied_count = 0
    deprecated_paths = [
        source_dir.parent / 'games' / 'assets',
        Path('examples/games/assets'),
    ]

    # Handle both dict (old transpilers) and set (new emitters)
    if isinstance(sprite_assets, dict):
        files_to_copy = sprite_assets.values()
    else:
        files_to_copy = sprite_assets

    for sprite_file in files_to_copy:
        if not sprite_file:
            continue
        # Try each search path
        for search_path in search_paths:
            sprite_path = search_path / sprite_file
            if sprite_path.exists():
                dest_path = assets_dir / sprite_file
                shutil.copy2(sprite_path, dest_path)
                print(f"  📦 Copied: {sprite_file}", file=sys.stderr)
                copied_count += 1
                # Check if this was a deprecated path
                if search_path in deprecated_paths:
                    deprecated_path_used = True
                break
        else:
            # Sprite not found in any search path
            print(f"  ⚠️  Not found: {sprite_file} (will use fallback rectangle)", file=sys.stderr)

    if copied_count > 0:
        print(f"✅ Copied {copied_count} sprite(s) to {assets_dir}", file=sys.stderr)

    if deprecated_path_used:
        print(f"⚠️  DEPRECATION WARNING: Assets found in examples/games/assets/", file=sys.stderr)
        print(f"   This path will be removed in v0.2.0. Move assets to assets/sprites/ or assets/sounds/", file=sys.stderr)


def run_build(filepath: str, target: str, output_dir: str, copy_assets: bool = False, enable_repl: bool = False):
    """Transpile Rosh code to target platform

    Args:
        filepath: Path to Rosh file to transpile
        target: Target platform (phaser, etc.)
        output_dir: Directory for output files
        copy_assets: If True, automatically copy required sprite assets
        enable_repl: If True, inject in-game REPL for live coding (dev mode only)

    Exits:
        0 on success
        1 on error
    """
    from pathlib import Path
    import shutil
    from .lexer import Lexer
    from .parser import Parser
    from .ir_transformer import transform_ast_to_ir
    from .emitters.phaser import PhaserEmitter
    from .emitters.pygame import PygameEmitter
    from .emitters.threejs import ThreeJSEmitter
    from .errors import RoshError

    try:
        # Resolve directory to main.rosh if needed
        filepath = resolve_rosh_path(filepath)

        # Read source file
        path = Path(filepath)
        if not path.exists():
            print(f"Error: File not found: {filepath}", file=sys.stderr)
            sys.exit(1)

        source = path.read_text()

        # Validate REPL flag (only supported for Phaser)
        if enable_repl and target != 'phaser':
            print(f"Error: --repl flag is only supported for Phaser target", file=sys.stderr)
            print(f"       Current target: {target}", file=sys.stderr)
            print(f"       To use REPL: rosh build {filepath} --target phaser --repl", file=sys.stderr)
            sys.exit(1)

        # Load meta settings from project directory
        from .meta import load_meta
        project_dir = str(path.parent)
        meta = load_meta(project_dir, target=target)

        # Lex and parse
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        program = parser.parse()

        # Emit based on target (IR-based architecture)
        if target == 'phaser':
            # Transform AST to IR, then emit Phaser code
            ir = transform_ast_to_ir(
                program,
                canvas_width=meta.get('canvas', {}).get('width', 800),
                canvas_height=meta.get('canvas', {}).get('height', 600)
            )
            emitter = PhaserEmitter(ir, meta=meta)
            js_code = emitter.emit()

            # TODO: Add REPL support to IR emitter
            if enable_repl:
                print(f"Warning: --repl not yet supported with IR emitter", file=sys.stderr)

            generate_phaser_output(js_code, output_dir)

            # Copy assets if requested
            if copy_assets and emitter.sprite_assets:
                copy_sprite_assets(path, Path(output_dir), emitter.sprite_assets)

            print(f"✅ Build successful!", file=sys.stderr)
            print(f"📁 Output: {output_dir}", file=sys.stderr)

            # Show dev mode warning if REPL enabled
            if enable_repl:
                print(f"🔧 DEV MODE: REPL enabled (press ` or F12 to toggle)", file=sys.stderr)
                print(f"⚠️  WARNING: Do not ship REPL to production!", file=sys.stderr)

            # Show how to run (always recommend server for Phaser - animations need it)
            print(f"🎮 To run:", file=sys.stderr)
            print(f"   cd {output_dir} && python3 -m http.server 8000", file=sys.stderr)
            print(f"   open http://localhost:8000", file=sys.stderr)

        elif target == 'pygame':
            # Transform AST to IR, then emit Pygame code
            ir = transform_ast_to_ir(
                program,
                canvas_width=meta.get('canvas', {}).get('width', 800),
                canvas_height=meta.get('canvas', {}).get('height', 600)
            )
            emitter = PygameEmitter(ir, meta=meta)
            py_code = emitter.emit()
            generate_pygame_output(py_code, output_dir)

            # Copy assets if requested
            if copy_assets:
                all_assets = set()
                if emitter.sprite_assets:
                    all_assets.update(emitter.sprite_assets)
                if emitter.sound_assets:
                    all_assets.update(emitter.sound_assets)
                if all_assets:
                    copy_sprite_assets(path, Path(output_dir), all_assets)

            print(f"✅ Build successful!", file=sys.stderr)
            print(f"📁 Output: {output_dir}", file=sys.stderr)
            print(f"🎮 To run:", file=sys.stderr)
            print(f"   python3 {output_dir}/game.py", file=sys.stderr)

        elif target == 'threejs':
            # Transform AST to IR, then emit Three.js code
            ir = transform_ast_to_ir(
                program,
                canvas_width=meta.get('canvas', {}).get('width', 800),
                canvas_height=meta.get('canvas', {}).get('height', 600)
            )
            emitter = ThreeJSEmitter(ir, meta=meta)
            js_code = emitter.emit()
            generate_threejs_output(js_code, output_dir, emitter.capability_manifest)

            # Copy assets if requested
            if copy_assets and emitter.sprite_assets:
                copy_sprite_assets(path, Path(output_dir), emitter.sprite_assets)

            print(f"✅ Build successful!", file=sys.stderr)
            print(f"📁 Output: {output_dir}", file=sys.stderr)
            print(f"🎮 To run:", file=sys.stderr)
            print(f"   cd {output_dir} && python3 -m http.server 8000", file=sys.stderr)
            print(f"   open http://localhost:8000", file=sys.stderr)

        else:
            print(f"Error: Unknown target: {target}", file=sys.stderr)
            sys.exit(1)

    except RoshError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def generate_phaser_output(js_code: str, output_dir: str):
    """Generate Phaser output files

    Creates:
    - game.js (generated Phaser code)
    - index.html (HTML boilerplate)
    - assets/ (placeholder directory)

    Args:
        js_code: Generated JavaScript code
        output_dir: Directory for output files
    """
    from pathlib import Path
    import shutil

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Write game.js
    with open(output_path / "game.js", "w") as f:
        f.write(js_code)

    # Copy HTML template
    template_dir = Path(__file__).parent / "emitters" / "templates"
    shutil.copy(template_dir / "phaser_index.html", output_path / "index.html")

    # Create assets directory
    (output_path / "assets").mkdir(exist_ok=True)


def generate_pygame_output(py_code: str, output_dir: str):
    """Generate Pygame output files

    Creates:
    - game.py (generated Pygame code, executable)
    - assets/ (placeholder directory)

    Args:
        py_code: Generated Python code
        output_dir: Directory for output files
    """
    from pathlib import Path

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Write game.py
    with open(output_path / "game.py", "w") as f:
        f.write(py_code)

    # Create assets directory
    (output_path / "assets").mkdir(exist_ok=True)


def generate_threejs_output(js_code: str, output_dir: str, capabilities: dict | None = None):
    """Generate Three.js output files

    Creates:
    - game.js (generated Three.js code, ES modules)
    - index.html (HTML boilerplate)
    - assets/ (placeholder directory)

    Args:
        js_code: Generated JavaScript code
        output_dir: Directory for output files
    """
    from pathlib import Path
    import shutil
    import json

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Write game.js
    with open(output_path / "game.js", "w") as f:
        f.write(js_code)

    # Copy HTML template
    template_dir = Path(__file__).parent / "emitters" / "templates"
    shutil.copy(template_dir / "threejs_index.html", output_path / "index.html")

    # Create assets directory
    (output_path / "assets").mkdir(exist_ok=True)

    # Write capability manifest if provided
    if capabilities:
        with open(output_path / "capabilities.json", "w") as f:
            json.dump(capabilities, f, indent=2)


def main():
    """Main entry point for the Rosh CLI"""
    parser = argparse.ArgumentParser(
        description="Rosh - A spoken-language-first programming language",
        prog="rosh"
    )

    # Check if using build subcommand (peek at args)
    import sys
    using_subcommand = len(sys.argv) > 1 and sys.argv[1] == 'build'

    if using_subcommand:
        # Add subparsers for commands
        subparsers = parser.add_subparsers(dest='subcommand', help='Commands')

        # Build subcommand
        build_parser = subparsers.add_parser('build', help='Transpile Rosh code to target platform')
        build_parser.add_argument('file', help='Rosh file to transpile')
        build_parser.add_argument('--target', required=True, choices=['phaser', 'pygame', 'threejs'],
                                  help='Target platform (phaser, pygame, threejs)')
        build_parser.add_argument('--output', default='dist/',
                                  help='Output directory (default: dist/)')
        build_parser.add_argument('--copy-assets', action='store_true',
                                  help='Automatically copy required sprite assets to output')
        build_parser.add_argument('--repl', action='store_true',
                                  help='🔧 DEV MODE: Enable in-game REPL (press ` or F12 to toggle console)')
    else:
        # Default behavior (run/REPL) - preserve existing arguments
        parser.add_argument(
            "file",
            nargs="?",
            help="Rosh file to execute (.rosh)"
        )

    parser.add_argument(
        "-c", "--command",
        metavar="CODE",
        help="Execute Rosh code from command line"
    )

    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Run file then enter interactive REPL with script state preserved"
    )

    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"Rosh {__version__}"
    )

    parser.add_argument(
        "--no-remote-imports",
        action="store_true",
        help="Disable remote HTTP/HTTPS imports (security: blocks untrusted code)"
    )

    parser.add_argument(
        "--toml",
        action="store_true",
        help="Output as TOML format (final stack value)"
    )

    parser.add_argument(
        "--toon",
        action="store_true",
        help="Output as TOON format (Token-Oriented Object Notation, optimized for LLMs)"
    )

    parser.add_argument(
        "--test",
        metavar="INPUT_FILE",
        help="Test mode: read inputs from file (one per line)"
    )

    parser.add_argument(
        "--test-input",
        metavar="INPUTS",
        help="Test mode: comma-separated inline inputs"
    )

    args = parser.parse_args()

    # Validate output format flags
    if args.toml and args.toon:
        print("Error: Cannot specify both --toml and --toon", file=sys.stderr)
        sys.exit(2)

    # Validate test mode flags
    if args.test and args.test_input:
        print("Error: Cannot specify both --test and --test-input", file=sys.stderr)
        sys.exit(2)

    # Parse test inputs
    test_inputs = []
    if args.test:
        try:
            with open(args.test, 'r') as f:
                # Read lines and strip trailing newlines
                test_inputs = [line.rstrip('\n\r') for line in f.readlines()]
        except FileNotFoundError:
            print(f"Error: Test input file not found: {args.test}", file=sys.stderr)
            sys.exit(1)
    elif args.test_input:
        # Parse comma-separated inputs with escape support
        test_inputs = _parse_test_input(args.test_input)

    # Set global flag for REPL
    global _disable_remote_imports
    _disable_remote_imports = args.no_remote_imports

    # Handle build subcommand
    if hasattr(args, 'subcommand') and args.subcommand == 'build':
        copy_assets = getattr(args, 'copy_assets', False)
        enable_repl = getattr(args, 'repl', False)
        run_build(args.file, args.target, args.output, copy_assets, enable_repl)
        return

    if args.command:
        # Execute inline code
        try:
            interpreter = run_source(args.command, "<command>", toml_output=args.toml, toon_output=args.toon, test_inputs=test_inputs)
            # If -i flag, enter REPL with command's state
            if args.interactive:
                run_repl(interpreter)
        except RoshError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.file:
        # Run file and optionally enter interactive mode
        interpreter = run_file(args.file, toml_output=args.toml, toon_output=args.toon, test_inputs=test_inputs)
        if args.interactive:
            run_repl(interpreter)
    else:
        # No file or command - start REPL
        run_repl()


if __name__ == "__main__":
    main()
