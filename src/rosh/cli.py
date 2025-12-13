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
        # MUD commands
        'goto', 'go', 'look', 'l', 'examine', 'ex', 'connect', 'link',
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


def run_file(filepath: str):
    """Run a Rosh program from a file

    Returns:
        Interpreter: The interpreter with the script's final state
    """
    try:
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
        interpreter = run_source(source, filepath)
        return interpreter

    except RoshError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


def run_source(source: str, filename: str = "<stdin>", interpreter: Interpreter = None):
    """Run Rosh source code"""
    from .errors import StopExecution

    # Lex
    lexer = Lexer(source)
    tokens = lexer.tokenize()

    # Parse
    parser = Parser(tokens)
    program = parser.parse()

    # Interpret (use provided interpreter or create new one)
    if interpreter is None:
        interpreter = Interpreter()

    try:
        interpreter.execute(program)
    except StopExecution:
        # Program was stopped with 'stop' or 'exit' command - this is normal
        pass

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


def main():
    """Main entry point for the Rosh CLI"""
    parser = argparse.ArgumentParser(
        description="Rosh - A spoken-language-first programming language",
        prog="rosh"
    )

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

    args = parser.parse_args()

    # Set global flag for REPL
    global _disable_remote_imports
    _disable_remote_imports = args.no_remote_imports

    if args.command:
        # Execute inline code
        try:
            interpreter = run_source(args.command, "<command>")
            # If -i flag, enter REPL with command's state
            if args.interactive:
                run_repl(interpreter)
        except RoshError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.file:
        # Run file and optionally enter interactive mode
        interpreter = run_file(args.file)
        if args.interactive:
            run_repl(interpreter)
    else:
        # No file or command - start REPL
        run_repl()


if __name__ == "__main__":
    main()
