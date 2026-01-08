"""
Rosh CLI - Command-line interface for running Rosh programs

=============================================================================
ARCHITECTURE POLICY - READ BEFORE MODIFYING
=============================================================================
This file is the SOURCE OF TRUTH for REPL command behavior.

Key documents:
- rosh-dev/proposals/IR-VERSIONING-POLICY.md - Version tracking and compliance
- rosh-dev/proposals/JS-RUNTIME-ARCHITECTURE.md - Runtime layer separation

The JS in-game REPL (rosh-runtime.js) should be GENERATED from this file.
DO NOT hand-code features in rosh-runtime.js - add them HERE first.

REPL features in this file:
- Command parsing (create, set, delete, look, list, etc.)
- Fuzzy matching for typos (_fuzzy_match_command)
- British/American spelling normalization (colour→color)
- Bulk operations (create N, delete all, set all)
- Smart object name resolution
- Property inference (unambiguous values only)
- Undo/redo support
- Multi-line block handling

When adding REPL features:
1. Implement here in Python first
2. Test in Python REPL
3. Regenerate rosh-runtime.js from this source
4. Engine adapters (threejs-adapter.js, phaser-adapter.js) remain thin
=============================================================================
"""

import sys
import argparse
import os
import re
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
    """Find closest matching command using spec-based typo correction + fuzzy matching.

    Uses the spec loader for:
    1. Known typos (exact correction from spec)
    2. Fuzzy matching against all known commands
    """
    import difflib

    word_lower = word.lower()

    # First: check known typos from spec (exact match)
    try:
        from .spec.loader import _get_loader
        loader = _get_loader()
        correction = loader.is_typo(word_lower)
        if correction:
            return correction
    except Exception:
        pass  # Fall back to fuzzy matching if spec unavailable

    # Build command list from spec + language keywords
    commands = []

    # Add commands from spec
    try:
        from .spec.loader import get_all_commands
        spec_commands = get_all_commands()
        for cmd in spec_commands.values():
            commands.extend(cmd.all_names)
    except Exception:
        pass

    # Add language keywords not in spec
    language_keywords = [
        'print', 'save', 'load', 'import', 'eval', 'read', 'write',
        'if', 'then', 'else', 'while', 'end',
        'define', 'function', 'call',
        'add', 'subtract', 'multiply', 'divide',
        'dup', 'swap', 'drop', 'push', 'pop',
        'goto', 'go', 'connect', 'link', 'prompt',
    ]
    for kw in language_keywords:
        if kw not in commands:
            commands.append(kw)

    # Add user-defined functions if interpreter available
    if interpreter:
        try:
            for name in interpreter.global_env.bindings.keys():
                from .values import RoshFunction
                if isinstance(interpreter.global_env.bindings[name], RoshFunction):
                    commands.append(name)
        except:
            pass

    # Find close matches (up to 1, with cutoff of 0.6)
    matches = difflib.get_close_matches(word_lower, commands, n=1, cutoff=0.6)

    return matches[0] if matches else None


def _get_all_scenes(interpreter):
    """Get all scenes (from objects + explicitly created)"""
    from .values import RoshObject, rosh_to_python

    scenes = set()

    # Get scenes from objects
    for name in interpreter.current_env.bindings.keys():
        try:
            value = interpreter.current_env.get(name)
            if isinstance(value, RoshObject) and value.has('scene'):
                scene = rosh_to_python(value.get('scene'))
                if scene:
                    scenes.add(scene)
        except:
            pass

    # Get explicitly created scenes (stored in _rosh_scenes variable)
    if interpreter.current_env.exists('_rosh_scenes'):
        explicit = interpreter.current_env.get('_rosh_scenes')
        if isinstance(explicit, list):
            scenes.update(explicit)

    return scenes


def _create_scene(interpreter, out, scene_name: str):
    """Create a scene explicitly (Universal REPL command)"""
    existing = _get_all_scenes(interpreter)

    # Check if scene already exists
    if scene_name in existing or scene_name.lower() in [s.lower() for s in existing]:
        out.warning(f"Scene '{scene_name}' already exists.")
        return

    # Store in _rosh_scenes list
    if interpreter.current_env.exists('_rosh_scenes'):
        scenes_list = interpreter.current_env.get('_rosh_scenes')
        if isinstance(scenes_list, list):
            scenes_list.append(scene_name)
        else:
            interpreter.current_env.set('_rosh_scenes', [scene_name])
    else:
        interpreter.current_env.define('_rosh_scenes', [scene_name])

    out.success(f"Created scene '{scene_name}'")
    out.dim(f"Use 'go {scene_name}' to navigate, or assign objects with 'set <obj> scene to {scene_name}'")


def _list_scenes(interpreter, out):
    """List all scenes defined in objects (Universal REPL command)"""
    scenes = _get_all_scenes(interpreter)

    if not scenes:
        out.dim("No scenes defined. Use 'create scene <name>' or 'set <object> scene to <name>'.")
        return

    # Get current scene if set
    current = None
    if interpreter.current_env.exists('current-scene'):
        current = interpreter.current_env.get('current-scene')

    out.print(f"Scenes ({len(scenes)}):", style="bold cyan")
    for scene in sorted(scenes):
        marker = " ← current" if scene == current else ""
        out.print(f"  {scene}{marker}", style="green")

    out.dim(f"\nUse 'go <scene>' to navigate, 'list <scene>' to see objects.")


def _list_objects(interpreter, out, max_display=10, scene_filter=None, group_by_scene=False):
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

    # Filter by scene if requested
    if scene_filter:
        filtered = []
        for name, obj in objects:
            obj_scene = rosh_to_python(obj.get('scene')) if obj.has('scene') else None
            if obj_scene and obj_scene.lower() == scene_filter.lower():
                filtered.append((name, obj))
        if not filtered:
            out.warning(f"No objects in scene '{scene_filter}'")
            # Suggest similar scenes
            scenes = set()
            for name, obj in objects:
                if obj.has('scene'):
                    scenes.add(rosh_to_python(obj.get('scene')))
            if scenes:
                out.dim(f"Available scenes: {', '.join(sorted(scenes))}")
            return
        objects = filtered
        out.print(f"Objects in '{scene_filter}' ({len(objects)}):", style="bold cyan")
    elif group_by_scene:
        # Group objects by scene
        by_scene = {}
        no_scene = []
        for name, obj in objects:
            obj_scene = rosh_to_python(obj.get('scene')) if obj.has('scene') else None
            if obj_scene:
                if obj_scene not in by_scene:
                    by_scene[obj_scene] = []
                by_scene[obj_scene].append((name, obj))
            else:
                no_scene.append((name, obj))

        # Display grouped
        total = len(objects)
        out.print(f"All Objects ({total}):", style="bold cyan")

        for scene in sorted(by_scene.keys()):
            out.print(f"\n  [{scene}]", style="bold yellow")
            for name, obj in by_scene[scene]:
                obj_type = obj.name if hasattr(obj, 'name') and obj.name else "object"
                out.print(f"    {name} ({obj_type})", style="green")

        if no_scene:
            out.print(f"\n  [global]", style="bold yellow")
            for name, obj in no_scene:
                obj_type = obj.name if hasattr(obj, 'name') and obj.name else "object"
                out.print(f"    {name} ({obj_type})", style="green")
        return
    else:
        total = len(objects)
        out.print(f"Objects ({total}):", style="bold cyan")

    # Show first max_display objects
    display_list = objects if max_display is None else objects[:max_display]
    for name, obj in display_list:
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
        if obj.has('scene') and not scene_filter:
            props.append(f"scene={rosh_to_python(obj.get('scene'))}")

        prop_str = f" ({', '.join(props)})" if props else ""
        out.print(f"  {name} ({obj_type}){prop_str}", style="green")

    # Show "and X more" if truncated
    if max_display is not None and len(objects) > max_display:
        remaining = len(objects) - max_display
        out.dim(f"  ... and {remaining} more (use 'list all' to see all)")


def _examine_object(interpreter, out, input_name: str):
    """Show properties of a specific object (Universal REPL command)"""
    from .values import RoshObject, rosh_to_python

    # Resolve with fuzzy matching
    value, obj_name, matches = _resolve_object_name(interpreter, input_name)

    # Show resolution message if name was fuzzy matched
    if value and obj_name and obj_name != input_name:
        out.dim(f'[resolved: "{input_name}" → "{obj_name}"]')

    if value is None:
        if matches:
            # Multiple matches - ask user to clarify
            out.print(f'Multiple matches for "{input_name}":', style="cyan")
            for name, _ in matches[:8]:
                out.dim(f"  {name}")
            if len(matches) > 8:
                out.dim(f"  ... and {len(matches) - 8} more")
            out.dim("Which one did you mean?")
        else:
            # No matches at all
            out.error(f"No matches found for '{input_name}'")
            # Show available objects
            all_objects = []
            for name in interpreter.current_env.bindings.keys():
                if name.startswith('_'):
                    continue
                try:
                    val = interpreter.current_env.get(name)
                    if isinstance(val, RoshObject):
                        all_objects.append(name)
                except:
                    pass
            if all_objects:
                out.dim(f"Available: {', '.join(all_objects[:10])}" + ("..." if len(all_objects) > 10 else ""))
        return

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
    'set': {
        'message': "Tell me what to set.",
        'examples': [
            "set <object>.<property> to <value>",
            "set <property> to <value>        # on current object",
            "set x to 100",
            "set ball.color to \"red\"",
        ],
    },
    'get': {
        'message': "Tell me what to get.",
        'examples': [
            "get <object>.<property>",
            "get ball.x",
            "get all <type>  # select all objects of type",
        ],
    },
    'print': {
        'message': "Tell me what to print.",
        'examples': [
            "print <expression>",
            "print ball.x",
            "print \"Hello, world!\"",
        ],
    },
    'create': {
        'message': "Tell me what to create.",
        'examples': [
            "create <name>              # create object (uses known type if available)",
            "create <type> <name>       # create named object of type",
            "create object <name> ... end",
        ],
    },
    'clone': {
        'message': "Tell me what to clone.",
        'examples': [
            "clone <object>             # auto-named copy",
            "clone <object> as <name>   # named copy",
        ],
    },
    'delete': {
        'message': "Tell me what to delete.",
        'examples': [
            "delete <object>",
            "delete <property> from <object>",
        ],
    },
    'move': {
        'message': "Tell me what to move.",
        'examples': [
            "move <object> to <x>, <y>",
            "move ball to 100, 200",
        ],
    },
    'count': {
        'message': "Count objects.",
        'examples': [
            "count              # count all objects",
            "count <type>       # count objects of type",
            "count ball",
        ],
    },
    'make': {
        'message': "Tell me what to adjust.",
        'examples': [
            "make <object> bigger",
            "make <object> smaller",
            "make <object> <color>",
            "make <object> visible/hidden",
        ],
    },
    'goto': {
        'message': "Tell me where to go.",
        'examples': [
            "goto <space>",
            "goto kitchen",
        ],
    },
    'connect': {
        'message': "Tell me what to connect.",
        'examples': [
            "connect <room1> to <room2>",
            "connect kitchen to garden",
        ],
    },
    'import': {
        'message': "Tell me what to import.",
        'examples': [
            "import <library>",
            "import mud",
            "import \"path/to/file.rosh\"",
        ],
    },
    'save': {
        'message': "Tell me where to save.",
        'examples': [
            "save <filename>",
            "save game.json",
        ],
    },
    'load': {
        'message': "Tell me what to load.",
        'examples': [
            "load <filename>",
            "load game.json",
        ],
    },
    'prompt': {
        'message': "Tell me what you want.",
        'examples': [
            "prompt <natural language request>",
            "prompt create a red ball",
            "prompt move player to the left",
        ],
    },
    'properties': {
        'message': "Show object properties.",
        'examples': [
            "properties <object>",
            "properties ball",
            "props player      # short form",
        ],
    },
    # Note: undo/redo/oops are valid with no args, so no usage hints needed
    'look': {
        'message': "Look around or at an object.",
        'examples': [
            "look              # list all objects",
            "look <object>     # examine object properties",
            "look ball",
            "l player          # short form",
        ],
    },
    'dump': {
        'message': "Dump debug info.",
        'examples': [
            "dump              # dump interpreter state",
            "dump <object>     # dump object details",
        ],
    },
    'go': {
        'message': "Execute buffered commands or go somewhere.",
        'examples': [
            "go                # execute pending commands",
            "go <place>        # same as 'goto <place>'",
            "go kitchen",
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


# Known colors and size modifiers for deep search
KNOWN_COLORS = {'red', 'blue', 'green', 'yellow', 'orange', 'purple', 'pink', 'white', 'black', 'gray', 'grey', 'cyan', 'magenta', 'brown', 'gold', 'silver'}
SIZE_MODIFIERS = {'big': 2.0, 'large': 2.0, 'huge': 3.0, 'giant': 4.0, 'small': 0.5, 'tiny': 0.25, 'little': 0.5}


def _deep_search(interpreter, words):
    """Deep search: find object by type + modifiers (color, size).

    Examples:
        _deep_search(interp, ['blue', 'sphere']) → finds sphere with color=blue
        _deep_search(interp, ['big', 'red', 'cube']) → finds cube with color=red, size>=2

    Returns: (obj, obj_name) or (None, None)
    """
    from .values import RoshObject, rosh_to_python

    # Parse modifiers and type from words
    colors = []
    sizes = []
    type_word = None

    for word in words:
        w = word.lower()
        if w in KNOWN_COLORS:
            colors.append(w)
        elif w in SIZE_MODIFIERS:
            sizes.append(w)
        else:
            type_word = w

    if not type_word:
        return None, None

    # Search for matching objects
    candidates = []
    for name in interpreter.current_env.bindings.keys():
        try:
            value = interpreter.current_env.get(name)
            if not isinstance(value, RoshObject):
                continue

            # Check type match
            obj_type = value.name if hasattr(value, 'name') and value.name else None
            # Also check if name contains the type word
            if obj_type and obj_type.lower() == type_word.lower():
                pass  # Type matches
            elif type_word.lower() in name.lower():
                pass  # Name contains type
            else:
                continue

            # Check color match
            color_match = True
            if colors:
                obj_color = rosh_to_python(value.get('color')) if value.has('color') else None
                if obj_color:
                    color_match = any(c in obj_color.lower() for c in colors)
                else:
                    color_match = False

            # Check size match
            size_match = True
            if sizes:
                obj_size = rosh_to_python(value.get('size')) if value.has('size') else None
                if obj_size is None:
                    obj_size = rosh_to_python(value.get('scale')) if value.has('scale') else 1.0
                if obj_size is not None:
                    # Check if size matches modifier
                    expected_size = SIZE_MODIFIERS.get(sizes[0], 1.0)
                    if expected_size > 1:
                        size_match = obj_size >= expected_size * 0.8  # Within 20%
                    else:
                        size_match = obj_size <= expected_size * 1.2
                else:
                    size_match = False

            if color_match and size_match:
                candidates.append((name, value))

        except:
            pass

    if len(candidates) == 1:
        return candidates[0][1], candidates[0][0]
    elif len(candidates) > 1:
        # Multiple matches - return first but could improve with scoring
        return candidates[0][1], candidates[0][0]

    return None, None


def _resolve_object_name(interpreter, identifier: str):
    """Resolve an object name with fuzzy matching.

    Supports:
    - Exact match: "ball" -> ball
    - UUID partial match: "abc123..." -> object with that UUID
    - Multi-word type/color/size: "red ball" -> ball with color red
    - Substring: "ba" -> ball

    Returns: (obj, resolved_name, matches) where:
    - obj: The resolved object (or None)
    - resolved_name: The actual object name found (or None)
    - matches: List of (name, obj) tuples if multiple matches found (or None)
    """
    from .values import RoshObject

    # First try exact match
    if interpreter.current_env.exists(identifier):
        obj = interpreter.current_env.get(identifier)
        return obj, identifier, None

    # Try the interpreter's fuzzy matching (handles type+color+size)
    if hasattr(interpreter, '_fuzzy_find_object'):
        matched = interpreter._fuzzy_find_object(identifier)
        if matched:
            obj = interpreter.current_env.get(matched)
            return obj, matched, None

    # Try UUID partial match (8+ chars)
    if len(identifier) >= 8:
        for name in interpreter.current_env.bindings.keys():
            try:
                value = interpreter.current_env.get(name)
                if isinstance(value, RoshObject):
                    if hasattr(value, 'uuid') and value.uuid:
                        if value.uuid.startswith(identifier) or value.uuid == identifier:
                            return value, name, None
            except:
                pass

    # Try singular/plural conversion
    singulars = _singularize(identifier)[1:]  # Skip original
    for singular in singulars:
        if interpreter.current_env.exists(singular):
            return interpreter.current_env.get(singular), singular, None

    # Try fuzzy substring matching as fallback
    lower_id = identifier.lower()
    matches = []
    for name in interpreter.current_env.bindings.keys():
        if name.startswith('_'):
            continue  # Skip internal names
        try:
            value = interpreter.current_env.get(name)
            if isinstance(value, RoshObject):
                lower_name = name.lower()
                # Check if search term is contained in name or vice versa
                if lower_id in lower_name or lower_name in lower_id:
                    matches.append((name, value))
        except:
            pass

    if len(matches) == 1:
        return matches[0][1], matches[0][0], None
    elif len(matches) > 1:
        return None, None, matches

    return None, None, None


def _get_command(interpreter, out, identifier: str, prop_name: str = None):
    """Unified get command - get object or property, push to stack, display.

    Supports:
    - get <name> - get object by name
    - get <uuid> - get object by UUID (partial match, 8+ chars)
    - get <obj> <prop> - get property value
    """
    from .values import RoshObject, rosh_to_python

    # Resolve the object name with fuzzy matching
    obj, obj_name_found, matches = _resolve_object_name(interpreter, identifier)

    # Show resolution message if name was fuzzy matched
    if obj and obj_name_found and obj_name_found != identifier:
        out.dim(f'[resolved: "{identifier}" → "{obj_name_found}"]')

    if obj is None:
        if matches:
            # Multiple matches - ask user to clarify
            out.print(f'Multiple matches for "{identifier}":', style="cyan")
            for name, _ in matches[:8]:
                out.dim(f"  {name}")
            if len(matches) > 8:
                out.dim(f"  ... and {len(matches) - 8} more")
            out.dim("Which one did you mean?")
        else:
            # No matches at all
            out.error(f"No matches found for '{identifier}'")
            # Show available objects
            all_objects = []
            for name in interpreter.current_env.bindings.keys():
                if name.startswith('_'):
                    continue
                try:
                    value = interpreter.current_env.get(name)
                    if isinstance(value, RoshObject):
                        all_objects.append(name)
                except:
                    pass
            if all_objects:
                out.dim(f"Available: {', '.join(all_objects[:10])}" + ("..." if len(all_objects) > 10 else ""))
        return

    # If no property requested, return the object itself
    if prop_name is None:
        # Push object to stack
        interpreter.data_stack.append(obj)
        # Display it
        if isinstance(obj, RoshObject):
            obj_type = obj.name if hasattr(obj, 'name') and obj.name else "object"
            # Build key props string (color, size)
            key_props = []
            if obj.has('color'):
                key_props.append(str(obj.get('color')))
            if obj.has('scale'):
                scale = obj.get('scale')
                if scale == 2:
                    key_props.append('big')
                elif scale == 3:
                    key_props.append('huge')
                elif scale == 0.5:
                    key_props.append('small')
                elif scale == 0.25:
                    key_props.append('tiny')
                elif scale != 1:
                    key_props.append(f'scale={scale}')
            props_str = f" ({', '.join(key_props)})" if key_props else ""
            out.print(f"<{obj_type}: {obj_name_found}>{props_str}", style="cyan")
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


def _singularize(word: str) -> list:
    """Return possible singular forms of a word.

    Returns list of candidates: [original, without 's', without 'es', 'ies'→'y']
    """
    candidates = [word]
    if word.endswith('ies'):
        candidates.append(word[:-3] + 'y')  # bodies → body
    if word.endswith('es'):
        candidates.append(word[:-2])  # boxes → box
    if word.endswith('s'):
        candidates.append(word[:-1])  # bananas → banana
    return candidates


def _find_all_matching(interpreter, obj_ref: str):
    """Find all objects matching a reference with optional modifiers.

    Args:
        interpreter: The interpreter instance
        obj_ref: Reference string like "blue balls", "big red cubes", "balls"

    Returns:
        tuple: (matching_objects, description, total_of_type, error_message)
        - matching_objects: list of matching RoshObject instances
        - description: human-readable description of what was searched (e.g., "blue ball")
        - total_of_type: total count of that type (for context)
        - error_message: error string if failed, None if success
    """
    # Known modifiers
    colors = {'red', 'green', 'blue', 'yellow', 'orange', 'purple', 'pink',
              'cyan', 'white', 'black', 'gray', 'grey', 'brown'}
    size_words = {'big': 2, 'large': 2, 'huge': 4, 'giant': 6, 'massive': 8,
                  'medium': 1, 'small': 0.5, 'tiny': 0.25}

    # Parse reference into modifiers and type
    ref_words = obj_ref.lower().split()
    filter_color = None
    filter_size = None
    type_name = None

    for word in ref_words:
        if word in colors:
            filter_color = word
        elif word in size_words:
            filter_size = word
        else:
            # Last non-modifier word is the type
            type_name = word

    if not type_name:
        return [], None, 0, f"No type specified in '{obj_ref}'"

    # Try singular forms of the type
    actual_type = None
    for candidate in _singularize(type_name):
        if candidate in interpreter.instances and len(interpreter.instances[candidate]) > 0:
            actual_type = candidate
            break

    if not actual_type:
        types = list(interpreter.instances.keys()) if interpreter.instances else []
        return [], None, 0, f"No instances of '{type_name}' found. Available: {', '.join(types) if types else 'none'}"

    # Get all instances and filter by modifiers
    all_instances = interpreter.instances[actual_type]
    matching = []

    for inst in all_instances:
        # Check color filter
        if filter_color:
            if inst.has('color'):
                obj_color = str(inst.get('color')).lower()
                if obj_color != filter_color:
                    continue
            else:
                continue  # No color property, skip

        # Check size filter
        if filter_size:
            obj_size_word = None
            if inst.has('scale'):
                scale = inst.get('scale')
                if isinstance(scale, (int, float)):
                    if scale >= 3:
                        obj_size_word = 'huge'
                    elif scale >= 2:
                        obj_size_word = 'big'
                    elif scale <= 0.25:
                        obj_size_word = 'tiny'
                    elif scale <= 0.5:
                        obj_size_word = 'small'
            if obj_size_word != filter_size:
                continue

        matching.append(inst)

    # Build description
    desc_parts = []
    if filter_color:
        desc_parts.append(filter_color)
    if filter_size:
        desc_parts.append(filter_size)
    desc_parts.append(actual_type)
    desc = ' '.join(desc_parts)

    return matching, desc, len(all_instances), None


def _format_obj_props(inst) -> str:
    """Format key properties (color, size) for display."""
    props = []
    if inst.has('color'):
        props.append(str(inst.get('color')))
    if inst.has('scale'):
        scale = inst.get('scale')
        if scale == 2:
            props.append('big')
        elif scale == 3:
            props.append('huge')
        elif scale == 0.5:
            props.append('small')
        elif scale == 0.25:
            props.append('tiny')
    return f" ({', '.join(props)})" if props else ""


def _get_all_command(interpreter, out, obj_ref: str):
    """Get all instances matching a reference with optional modifiers."""
    matching, desc, total, error = _find_all_matching(interpreter, obj_ref)

    if error:
        out.error(error)
        return

    if not matching:
        out.warning(f"No {desc} found (0 of {total} match)")
        return

    MAX_DISPLAY = 10
    out.print(f"All {desc} ({len(matching)}):", style="bold")
    for inst in matching[:MAX_DISPLAY]:
        inst_id = inst.id if hasattr(inst, 'id') and inst.id else inst.uuid[:8]
        out.print(f"  {inst_id}{_format_obj_props(inst)}", style="cyan")
    if len(matching) > MAX_DISPLAY:
        out.dim(f"  ...and {len(matching) - MAX_DISPLAY} more")

    # Push list to stack
    interpreter.data_stack.append(matching)


def _delete_all_command(interpreter, out, obj_ref: str) -> tuple:
    """Delete all instances matching a reference. Returns (count, desc) for confirmation."""
    matching, desc, total, error = _find_all_matching(interpreter, obj_ref)

    if error:
        out.error(error)
        return 0, None

    if not matching:
        out.warning(f"No {desc} found (0 of {total} match)")
        return 0, None

    # Return info for confirmation - actual deletion happens after confirm
    return matching, desc


def _execute_delete_all(interpreter, out, matching: list, desc: str):
    """Execute the deletion after confirmation."""
    deleted = 0
    for inst in matching:
        inst_id = inst.id if hasattr(inst, 'id') and inst.id else inst.uuid[:8]

        # Remove from environment (check both current_env and bindings)
        if inst_id in interpreter.current_env.bindings:
            # Detach from tracking structures
            interpreter._detach_object_instance(inst)
            del interpreter.current_env.bindings[inst_id]
            deleted += 1

    out.success(f"Deleted {deleted} {desc}(s)")
    return deleted


def _hide_all_command(interpreter, out, obj_ref: str) -> tuple:
    """Hide all instances matching a reference. Returns (matching, desc) for confirmation."""
    matching, desc, total, error = _find_all_matching(interpreter, obj_ref)

    if error:
        out.error(error)
        return [], None

    if not matching:
        out.warning(f"No {desc} found (0 of {total} match)")
        return [], None

    return matching, desc


def _execute_hide_all(interpreter, out, matching: list, desc: str):
    """Execute hiding after confirmation."""
    hidden = 0
    for inst in matching:
        if hasattr(inst, 'set'):
            inst.set('visible', False)
            hidden += 1
    out.success(f"Hid {hidden} {desc}(s)")
    return hidden


def _show_all_command(interpreter, out, obj_ref: str) -> tuple:
    """Show all instances matching a reference. Returns (matching, desc) for confirmation."""
    matching, desc, total, error = _find_all_matching(interpreter, obj_ref)

    if error:
        out.error(error)
        return [], None

    if not matching:
        out.warning(f"No {desc} found (0 of {total} match)")
        return [], None

    return matching, desc


def _execute_show_all(interpreter, out, matching: list, desc: str):
    """Execute showing after confirmation."""
    shown = 0
    for inst in matching:
        if hasattr(inst, 'set'):
            inst.set('visible', True)
            shown += 1
    out.success(f"Showed {shown} {desc}(s)")
    return shown


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

    # Start new undo group for this command (so entire command undoes together)
    interpreter.start_undo_group()

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

    from datetime import datetime
    build_time = datetime.now().strftime('%H:%M:%S')
    out.print(f"🤖 rosh v{__version__} | {build_time}", style="bold cyan")

    if interpreter:
        out.print("Interactive REPL (script state preserved)", style="dim green")
    else:
        out.print("Interactive REPL", style="dim")
    out.print()

    out.print("Quick Start:", style="bold yellow")
    out.print("  help              - Show all commands", style="dim")
    out.print("  help <command>    - Get help on specific command", style="dim")
    out.print("  create box        - Create an object", style="green")
    out.print("  set box x to 100  - Change a property", style="green")
    out.print("  list              - Show all objects", style="green")
    out.print("  undo              - Undo last action", style="green")
    out.print()

    out.print("Commands:", style="bold")
    out.print("  create, set, get, delete, clone, list, look, move, hide, show", style="cyan")
    out.print("  undo, redo, save, load, dump, prompt, import, properties", style="cyan")
    out.print()

    out.print("Type 'exit' to quit | 'credits' | 'license' | 'alias' for shortcuts", style="dim")
    if READLINE_AVAILABLE:
        out.print("History: ↑/↓ arrows | Tab completion enabled", style="dim")
    out.print()

    # Use provided interpreter or create new one
    if interpreter is None:
        interpreter = Interpreter(interactive=True)  # Enable feedback in REPL

    # Check for security flags (passed from main via global)
    if '_disable_remote_imports' in globals() and _disable_remote_imports:
        interpreter.allow_remote_imports = False
        out.print("🔒 Remote imports disabled (--no-remote-imports)", style="yellow")
        out.print()

    buffer = []
    aliases = {}  # Store command aliases
    blank_line_count = 0  # Track consecutive blank lines for triple-newline → go

    # === Project Twin: Shared World Connection State ===
    twin_sock = None  # TCP socket (preferred for localhost)
    twin_ws = None  # WebSocket connection (for remote)
    twin_user_id = None
    twin_world_id = None
    twin_world_state = {"objects": {}}
    twin_receiver_thread = None
    twin_stop_event = None
    twin_message_queue = []  # Messages from server to display
    twin_use_tcp = False  # True if using TCP, False if WebSocket
    TWIN_WS_SERVER = "wss://rosh.cloud/ws/world/"
    # TCP settings can be overridden via environment
    # For Railway: ROSH_TCP_HOST=viaduct.proxy.rlwy.net ROSH_TCP_PORT=12345
    TWIN_TCP_HOST = os.environ.get("ROSH_TCP_HOST", "localhost")
    TWIN_TCP_PORT = int(os.environ.get("ROSH_TCP_PORT", "4000"))

    def twin_send_tcp(payload: str):
        """Send a length-prefixed frame over TCP."""
        nonlocal twin_sock
        if twin_sock is None:
            return
        try:
            data = payload.encode('utf-8')
            frame = f"{len(data)}:".encode() + data + b"\n"
            twin_sock.sendall(frame)
        except Exception as e:
            out.dim(f"[twin] TCP send failed: {e}")

    def twin_recv_tcp_frame(sock, timeout=1.0) -> str:
        """Receive a single length-prefixed frame from TCP socket."""
        import select
        sock.setblocking(False)
        readable, _, _ = select.select([sock], [], [], timeout)
        if not readable:
            return None
        try:
            # Read length prefix
            length_bytes = b""
            while True:
                byte = sock.recv(1)
                if not byte:
                    return None
                if byte == b":":
                    break
                length_bytes += byte
                if len(length_bytes) > 10:
                    return None
            length = int(length_bytes.decode())
            # Read payload
            payload = b""
            while len(payload) < length:
                chunk = sock.recv(length - len(payload))
                if not chunk:
                    return None
                payload += chunk
            # Read trailing newline
            sock.recv(1)
            return payload.decode('utf-8')
        except (BlockingIOError, ValueError):
            return None

    def _parse_tcp_message(msg: str) -> dict:
        """Parse TCP server message into message queue format."""
        import json
        parts = msg.split(None, 1)
        cmd = parts[0] if parts else ""
        rest = parts[1] if len(parts) > 1 else ""

        if cmd == "JOINED":
            # JOINED <user_id>
            return {"type": "USER_JOINED", "user_id": rest.strip(), "user_count": 0}
        elif cmd == "LEFT":
            # LEFT <user_id>
            return {"type": "USER_LEFT", "user_id": rest.strip(), "user_count": 0}
        elif cmd == "CREATED":
            # CREATED <id> <type> <color> <x> <y> <z> by <user_id>
            try:
                # Parse: CREATED ball sphere red 0.0 0.0 0.0 by abc123
                match = re.match(r'(\S+)\s+(\S+)\s+(\S+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+by\s+(\S+)', rest)
                if match:
                    obj_id, obj_type, color, x, y, z, by_user = match.groups()
                    data = {"type": obj_type, "color": color, "x": float(x), "y": float(y), "z": float(z)}
                    return {"type": "OBJECT_CREATED", "id": obj_id, "data": data, "by": by_user}
            except:
                pass
        elif cmd == "DELETED":
            # DELETED <id> by <user_id>
            try:
                match = re.match(r'(\S+)\s+by\s+(\S+)', rest)
                if match:
                    obj_id, by_user = match.groups()
                    return {"type": "OBJECT_DELETED", "id": obj_id, "by": by_user}
            except:
                pass
        elif cmd == "MOVED":
            # MOVED <id> <x> <y> <z> by <user_id>
            try:
                match = re.match(r'(\S+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+by\s+(\S+)', rest)
                if match:
                    obj_id, x, y, z, by_user = match.groups()
                    return {"type": "OBJECT_MOVED", "id": obj_id, "x": float(x), "y": float(y), "z": float(z), "by": by_user}
            except:
                pass
        elif cmd == "SET":
            # SET <id> <prop> <value> by <user_id>
            try:
                match = re.match(r'(\S+)\s+(\S+)\s+(\S+)\s+by\s+(\S+)', rest)
                if match:
                    obj_id, prop, value, by_user = match.groups()
                    return {"type": "OBJECT_UPDATED", "id": obj_id, "changes": {prop: value}, "by": by_user}
            except:
                pass
        elif cmd == "CHAT":
            # CHAT <user_id> <message>
            try:
                match = re.match(r'(\S+)\s+(.*)', rest)
                if match:
                    user_id, message = match.groups()
                    return {"type": "CHAT", "user_id": user_id, "message": message}
            except:
                pass
        elif cmd == "WHO":
            # WHO <json> - New JSON format for who response
            try:
                data = json.loads(rest)
                return {
                    "type": "USERS_LIST",
                    "world_id": data.get("world", ""),
                    "count": data.get("count", 0),
                    "users": [{"id": u["id"], "is_you": u.get("is_you", False), "transport": u.get("transport", "?")} for u in data.get("users", [])]
                }
            except:
                pass
        elif cmd == "USERS":
            # USERS <world> <count> - Old format (just count header)
            try:
                parts = msg.split()
                world_id = parts[1] if len(parts) > 1 else ""
                count = int(parts[2]) if len(parts) > 2 else 0
                # This is now just the count header, users come in WHO format
                return None
            except:
                pass
        elif cmd == "RESET":
            # RESET <world> by <user_id> <count>
            try:
                match = re.match(r'(\S+)\s+by\s+(\S+)\s+(\d+)', rest)
                if match:
                    world_id, by_user, count = match.groups()
                    return {"type": "WORLD_RESET", "by": by_user, "deleted_count": int(count)}
            except:
                pass
        return None

    def twin_display_messages():
        """Display any pending messages from the twin server"""
        nonlocal twin_message_queue
        while twin_message_queue:
            msg = twin_message_queue.pop(0)
            if msg['type'] == 'USER_JOINED':
                out.print(f"\n[twin] User {msg.get('user_id', '?')} joined (total: {msg.get('user_count', '?')})", style="cyan")
            elif msg['type'] == 'USER_LEFT':
                out.dim(f"\n[twin] User {msg.get('user_id', '?')} left (total: {msg.get('user_count', '?')})")
            elif msg['type'] == 'OBJECT_CREATED':
                twin_world_state['objects'][msg['id']] = msg['data']
                if msg['by'] != twin_user_id:
                    out.print(f"\n[twin] + {msg['id']}: {msg['data']['type']} created by {msg['by']}", style="cyan")
            elif msg['type'] == 'OBJECT_DELETED':
                if msg['id'] in twin_world_state['objects']:
                    del twin_world_state['objects'][msg['id']]
                if msg['by'] != twin_user_id:
                    out.dim(f"\n[twin] - {msg['id']} deleted by {msg['by']}")
            elif msg['type'] == 'CHAT':
                out.print(f"\n[twin] [{msg.get('by', msg.get('user_id', '?'))}] {msg['message']}", style="cyan")
            elif msg['type'] == 'ERROR':
                out.error(f"[twin] {msg.get('message', 'Unknown error')}")
            elif msg['type'] == 'WORLD_RESET':
                twin_world_state['objects'] = {}
                out.warning(f"\n[twin] World reset by {msg['by']} ({msg.get('deleted_count', 0)} objects cleared)")
            elif msg['type'] == 'USERS_LIST':
                out.print(f"\n=== Users in '{msg['world_id']}' ({msg['count']}) ===", style="cyan")
                for user in msg['users']:
                    tag = " (you)" if user.get('is_you') else ""
                    transport = f" [{user.get('transport', '?')}]" if 'transport' in user else ""
                    style = "green" if user.get('is_you') else "dim"
                    out.print(f"  {user['id']}{tag}{transport}", style=style)
            elif msg['type'] == 'OBJECT_UPDATED':
                if msg['id'] in twin_world_state['objects']:
                    twin_world_state['objects'][msg['id']].update(msg.get('changes', {}))
                if msg.get('by') != twin_user_id:
                    out.print(f"\n[twin] ~ {msg['id']} updated by {msg['by']}: {msg.get('changes', {})}", style="cyan")
            elif msg['type'] == 'OBJECT_MOVED':
                if msg['id'] in twin_world_state['objects']:
                    obj = twin_world_state['objects'][msg['id']]
                    if 'x' in msg: obj['x'] = msg['x']
                    if 'y' in msg: obj['y'] = msg['y']
                    if 'z' in msg: obj['z'] = msg['z']
                if msg.get('by') != twin_user_id:
                    out.print(f"\n[twin] ~ {msg['id']} moved to ({msg.get('x')}, {msg.get('y')}, {msg.get('z')})", style="cyan")

    def twin_broadcast_create(obj_name, obj):
        """Broadcast object creation to connected world"""
        nonlocal twin_ws, twin_sock, twin_use_tcp
        if twin_ws is None and twin_sock is None:
            return
        try:
            from .values import rosh_to_python
            obj_type = obj.name if hasattr(obj, 'name') and obj.name else 'cube'
            color = rosh_to_python(obj.get('color')) if obj.has('color') else 'green'
            x = rosh_to_python(obj.get('x')) if obj.has('x') else 0
            y = rosh_to_python(obj.get('y')) if obj.has('y') else 0
            z = rosh_to_python(obj.get('z')) if obj.has('z') else 0
            size = rosh_to_python(obj.get('size')) if obj.has('size') else 1

            if twin_use_tcp and twin_sock:
                # TCP: CREATE <id> <type> <color> <x> <y> <z>
                twin_send_tcp(f"CREATE {obj_name} {obj_type} {color} {x} {y} {z}")
            elif twin_ws:
                import json
                twin_ws.send(json.dumps({
                    "type": "CREATE",
                    "id": obj_name,
                    "object_type": obj_type,
                    "color": color,
                    "x": x, "y": y, "z": z,
                    "size": size
                }))

            # Update local state immediately (don't wait for server echo)
            twin_world_state['objects'][obj_name] = {
                "type": obj_type,
                "color": color,
                "x": x, "y": y, "z": z,
                "size": size
            }
        except Exception as e:
            out.dim(f"[twin] broadcast failed: {e}")

    def twin_broadcast_delete(obj_name):
        """Broadcast object deletion to connected world"""
        nonlocal twin_ws, twin_sock, twin_use_tcp
        if twin_ws is None and twin_sock is None:
            return
        try:
            if twin_use_tcp and twin_sock:
                twin_send_tcp(f"DELETE {obj_name}")
            elif twin_ws:
                import json
                twin_ws.send(json.dumps({
                    "type": "DELETE",
                    "id": obj_name
                }))
            # Update local state immediately
            if obj_name in twin_world_state['objects']:
                del twin_world_state['objects'][obj_name]
        except Exception as e:
            out.dim(f"[twin] delete broadcast failed: {e}")

    def twin_broadcast_update(obj_name, **properties):
        """Broadcast property updates to connected world"""
        nonlocal twin_ws, twin_sock, twin_use_tcp
        if twin_ws is None and twin_sock is None:
            return
        try:
            if twin_use_tcp and twin_sock:
                # TCP: SET <id> <prop> <value> for each property
                for prop, value in properties.items():
                    twin_send_tcp(f"SET {obj_name} {prop} {value}")
            elif twin_ws:
                import json
                msg = {"type": "UPDATE", "id": obj_name}
                msg.update(properties)
                twin_ws.send(json.dumps(msg))
            # Update local state immediately
            if obj_name in twin_world_state['objects']:
                twin_world_state['objects'][obj_name].update(properties)
        except Exception as e:
            out.dim(f"[twin] update broadcast failed: {e}")

    def twin_broadcast_move(obj_name, x, y, z=0):
        """Broadcast object movement to connected world"""
        nonlocal twin_ws, twin_sock, twin_use_tcp
        if twin_ws is None and twin_sock is None:
            return
        try:
            if twin_use_tcp and twin_sock:
                twin_send_tcp(f"MOVE {obj_name} {x} {y} {z}")
            elif twin_ws:
                import json
                twin_ws.send(json.dumps({
                    "type": "MOVE",
                    "id": obj_name,
                    "x": x, "y": y, "z": z
                }))
            # Update local state immediately
            if obj_name in twin_world_state['objects']:
                twin_world_state['objects'][obj_name]['x'] = x
                twin_world_state['objects'][obj_name]['y'] = y
                twin_world_state['objects'][obj_name]['z'] = z
        except Exception as e:
            out.dim(f"[twin] move broadcast failed: {e}")

    def get_object_names():
        """Get set of current object names in interpreter"""
        from .values import RoshObject
        names = set()
        if interpreter and hasattr(interpreter, 'current_env'):
            for name in interpreter.current_env.bindings.keys():
                try:
                    value = interpreter.current_env.get(name)
                    if isinstance(value, RoshObject):
                        names.add(name)
                except:
                    pass
        return names

    def snapshot_object_states():
        """Snapshot all object states for change detection"""
        from .values import RoshObject, rosh_to_python
        snapshot = {}
        if interpreter and hasattr(interpreter, 'current_env'):
            for name in interpreter.current_env.bindings.keys():
                try:
                    obj = interpreter.current_env.get(name)
                    if isinstance(obj, RoshObject):
                        # Snapshot key properties
                        props = {}
                        for prop in ['x', 'y', 'z', 'color', 'size', 'scale', 'speed', 'visible', 'orbit']:
                            if obj.has(prop):
                                props[prop] = rosh_to_python(obj.get(prop))
                        snapshot[name] = props
                except:
                    pass
        return snapshot

    def broadcast_object_changes(before_state):
        """Check for new/deleted/changed objects and broadcast them"""
        if twin_ws is None and twin_sock is None:
            return
        from .values import rosh_to_python
        after_state = snapshot_object_states()
        before_names = set(before_state.keys())
        after_names = set(after_state.keys())

        # Broadcast new objects
        new_names = after_names - before_names
        for name in new_names:
            try:
                obj = interpreter.current_env.get(name)
                twin_broadcast_create(name, obj)
            except:
                pass

        # Broadcast deleted objects
        deleted_names = before_names - after_names
        for name in deleted_names:
            twin_broadcast_delete(name)

        # Broadcast property changes for existing objects
        for name in before_names & after_names:
            before_props = before_state.get(name, {})
            after_props = after_state.get(name, {})
            changes = {}

            # Check for position changes (use MOVE message)
            pos_changed = False
            for prop in ['x', 'y', 'z']:
                if before_props.get(prop) != after_props.get(prop):
                    pos_changed = True

            if pos_changed:
                twin_broadcast_move(
                    name,
                    after_props.get('x', 0),
                    after_props.get('y', 0),
                    after_props.get('z', 0)
                )

            # Check for other property changes (use UPDATE message)
            for prop in ['color', 'size', 'scale', 'speed', 'visible', 'orbit']:
                if before_props.get(prop) != after_props.get(prop) and prop in after_props:
                    changes[prop] = after_props[prop]

            if changes:
                twin_broadcast_update(name, **changes)

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
                out.print("Copyright (c) 2026 Rosh Studiosa", style="dim")
                out.print()
                out.print("\"Rosh\" and the Rosh logo are trademarks of the Rosh Project.", style="yellow")
                out.print("You may use the Rosh name to refer to this project, but you may not use")
                out.print("them in a way that suggests endorsement without permission.")
                out.print()
                out.print("See LICENSE file for full details.", style="dim")
                out.print()
                continue

            # Handle credits command
            if line.strip() in ('credits', 'help credits'):
                out.print()
                out.print(f"Rosh v{__version__}", style="cyan")
                out.print("Copyright (c) 2026 Roger Dubar")
                out.dim("https://rosh.cloud")
                out.print()
                continue

            # === Project Twin: connect/disconnect commands ===
            if line.strip().startswith('connect'):
                parts = line.strip().split()
                world = parts[1] if len(parts) > 1 else 'default'
                if twin_ws is not None or twin_sock is not None:
                    out.warning(f"Already connected to '{twin_world_id}'. Use 'disconnect' first.")
                    continue

                import json
                import threading
                import socket

                # Parse world name and optional mode
                # Syntax: connect <world>[@tcp|@ws]
                # Examples: connect testworld, connect testworld@tcp, connect testworld@ws
                force_tcp = False
                force_ws = False
                world_name = world

                if '@' in world:
                    parts_at = world.split('@')
                    world_name = parts_at[0]
                    mode = parts_at[1].lower()
                    if mode == "tcp":
                        force_tcp = True
                    elif mode == "ws":
                        force_ws = True

                # Use TCP for localhost (or if forced), WebSocket for remote (or if forced)
                use_tcp = (TWIN_TCP_HOST in ("localhost", "127.0.0.1") or force_tcp) and not force_ws
                if use_tcp:
                    try:
                        out.dim(f"Connecting to TCP {TWIN_TCP_HOST}:{TWIN_TCP_PORT}...")
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.connect((TWIN_TCP_HOST, TWIN_TCP_PORT))
                        sock.settimeout(5.0)

                        # Receive WELCOME message first
                        welcome = twin_recv_tcp_frame(sock, timeout=5.0)
                        if welcome and welcome.startswith("WELCOME"):
                            out.dim(f"Server: {welcome}")

                        # Send JOIN command
                        join_msg = f"JOIN {world_name}"
                        data = join_msg.encode('utf-8')
                        frame = f"{len(data)}:".encode() + data + b"\n"
                        sock.sendall(frame)

                        # Receive response
                        response = twin_recv_tcp_frame(sock, timeout=5.0)
                        if response:
                            if response.startswith("OK Joined") or response.startswith("OK "):
                                # Parse: OK Joined '<world>' as <user_id>
                                # Or: OK <user_id>
                                if " as " in response:
                                    twin_user_id = response.split(" as ")[-1].strip()
                                else:
                                    twin_user_id = response[3:].strip()
                                twin_sock = sock
                                twin_world_id = world_name
                                twin_use_tcp = True
                                out.success(f"Connected to world '{world_name}' as {twin_user_id} [TCP]")

                                # Server sends USERS and STATE automatically after JOIN
                                # Consume USERS message
                                users_response = twin_recv_tcp_frame(twin_sock, timeout=2.0)
                                if users_response and users_response.startswith("USERS "):
                                    try:
                                        user_count = int(users_response[6:].strip())
                                        out.dim(f"Users online: {user_count}")
                                    except:
                                        pass

                                # Consume STATE message
                                state_response = twin_recv_tcp_frame(twin_sock, timeout=2.0)
                                if state_response and state_response.startswith("STATE "):
                                    try:
                                        state_data = json.loads(state_response[6:])
                                        twin_world_state['objects'] = state_data
                                        if state_data:
                                            out.print(f"Objects in world: {len(state_data)}", style="cyan")
                                            for oid, odata in state_data.items():
                                                out.print(f"  {oid}: {odata.get('type', '?')} ({odata.get('color', '?')})", style="dim")
                                    except json.JSONDecodeError:
                                        pass

                                out.print()
                                out.dim("Objects you create will sync to the shared world.")
                                out.dim("Use 'disconnect' to leave, 'twin' to see world state.")

                                # Start background TCP receiver thread
                                twin_stop_event = threading.Event()

                                def tcp_receiver_loop():
                                    nonlocal twin_sock, twin_user_id, twin_world_id
                                    while not twin_stop_event.is_set() and twin_sock:
                                        try:
                                            msg = twin_recv_tcp_frame(twin_sock, timeout=0.5)
                                            if msg:
                                                # Parse TCP messages and convert to queue format
                                                parsed = _parse_tcp_message(msg)
                                                if parsed:
                                                    twin_message_queue.append(parsed)
                                        except Exception:
                                            break

                                twin_receiver_thread = threading.Thread(target=tcp_receiver_loop, daemon=True)
                                twin_receiver_thread.start()
                            elif response.startswith("ERROR "):
                                out.error(f"Connection failed: {response[6:]}")
                                sock.close()
                            else:
                                out.error(f"Unexpected response: {response}")
                                sock.close()
                        else:
                            out.error("No response from server")
                            sock.close()
                    except Exception as e:
                        out.error(f"TCP connection failed: {e}")
                        out.dim("Falling back to WebSocket...")
                        # Fall through to WebSocket
                        try:
                            import websocket
                            uri = f"{TWIN_WS_SERVER}{world_name}"
                            out.dim(f"Connecting to {uri}...")
                            twin_ws = websocket.create_connection(uri)
                            twin_world_id = world_name
                            twin_use_tcp = False

                            initial = json.loads(twin_ws.recv())
                            if initial['type'] == 'CONNECTED':
                                twin_user_id = initial['user_id']
                                twin_world_state.update(initial['state'])
                                out.success(f"Connected to world '{world_name}' as {twin_user_id} [WebSocket]")
                                out.dim(f"Users online: {initial['user_count']}")
                                if initial['state']['objects']:
                                    out.print(f"Objects in world: {len(initial['state']['objects'])}", style="cyan")
                                    for oid, odata in initial['state']['objects'].items():
                                        out.print(f"  {oid}: {odata['type']} ({odata.get('color', '?')})", style="dim")
                                out.print()
                                out.dim("Objects you create will sync to the shared world.")
                                out.dim("Use 'disconnect' to leave, 'twin' to see world state.")

                            twin_stop_event = threading.Event()

                            def ws_receiver_loop():
                                nonlocal twin_ws, twin_user_id, twin_world_id
                                while not twin_stop_event.is_set():
                                    try:
                                        twin_ws.settimeout(0.5)
                                        msg_str = twin_ws.recv()
                                        msg = json.loads(msg_str)
                                        twin_message_queue.append(msg)
                                    except websocket.WebSocketTimeoutException:
                                        continue
                                    except Exception:
                                        break

                            twin_receiver_thread = threading.Thread(target=ws_receiver_loop, daemon=True)
                            twin_receiver_thread.start()
                        except ImportError:
                            out.error("websocket-client package required. Install with: uv add websocket-client")
                        except Exception as e2:
                            out.error(f"WebSocket connection also failed: {e2}")
                            twin_ws = None
                            twin_world_id = None
                else:
                    # Remote host - use WebSocket
                    try:
                        import websocket
                        uri = f"{TWIN_WS_SERVER}{world_name}"
                        out.dim(f"Connecting to {uri}...")
                        twin_ws = websocket.create_connection(uri)
                        twin_world_id = world_name
                        twin_use_tcp = False

                        initial = json.loads(twin_ws.recv())
                        if initial['type'] == 'CONNECTED':
                            twin_user_id = initial['user_id']
                            twin_world_state.update(initial['state'])
                            out.success(f"Connected to world '{world_name}' as {twin_user_id} [WebSocket]")
                            out.dim(f"Users online: {initial['user_count']}")
                            if initial['state']['objects']:
                                out.print(f"Objects in world: {len(initial['state']['objects'])}", style="cyan")
                                for oid, odata in initial['state']['objects'].items():
                                    out.print(f"  {oid}: {odata['type']} ({odata.get('color', '?')})", style="dim")
                            out.print()
                            out.dim("Objects you create will sync to the shared world.")
                            out.dim("Use 'disconnect' to leave, 'twin' to see world state.")

                        twin_stop_event = threading.Event()

                        def ws_receiver_loop():
                            nonlocal twin_ws, twin_user_id, twin_world_id
                            while not twin_stop_event.is_set():
                                try:
                                    twin_ws.settimeout(0.5)
                                    msg_str = twin_ws.recv()
                                    msg = json.loads(msg_str)
                                    twin_message_queue.append(msg)
                                except websocket.WebSocketTimeoutException:
                                    continue
                                except Exception:
                                    break

                        twin_receiver_thread = threading.Thread(target=ws_receiver_loop, daemon=True)
                        twin_receiver_thread.start()
                    except ImportError:
                        out.error("websocket-client package required. Install with: uv add websocket-client")
                    except Exception as e:
                        out.error(f"Connection failed: {e}")
                        twin_ws = None
                        twin_world_id = None
                continue

            if line.strip() == 'disconnect':
                if twin_ws is None and twin_sock is None:
                    out.dim("Not connected to any world.")
                else:
                    try:
                        if twin_stop_event:
                            twin_stop_event.set()
                        if twin_sock:
                            # Send QUIT command
                            try:
                                quit_msg = "QUIT"
                                data = quit_msg.encode('utf-8')
                                frame = f"{len(data)}:".encode() + data + b"\n"
                                twin_sock.sendall(frame)
                            except:
                                pass
                            twin_sock.close()
                        if twin_ws:
                            twin_ws.close()
                    except:
                        pass
                    out.success(f"Disconnected from world '{twin_world_id}'")
                    twin_ws = None
                    twin_sock = None
                    twin_use_tcp = False
                    twin_user_id = None
                    twin_world_id = None
                    twin_world_state.clear()
                    twin_world_state['objects'] = {}
                continue

            if line.strip() == 'twin':
                if twin_ws is None and twin_sock is None:
                    out.dim("Not connected. Use 'connect <world>' to join a shared world.")
                else:
                    conn_type = "TCP" if twin_use_tcp else "WebSocket"
                    out.print(f"Connected to: {twin_world_id} [{conn_type}]", style="cyan")
                    out.print(f"Your ID: {twin_user_id}", style="dim")
                    if twin_world_state['objects']:
                        out.print(f"Objects ({len(twin_world_state['objects'])}):", style="cyan")
                        for oid, odata in twin_world_state['objects'].items():
                            out.print(f"  {oid}: {odata.get('type', '?')} ({odata.get('color', '?')})", style="dim")
                    else:
                        out.dim("No objects in world")
                continue

            if line.strip().startswith('say '):
                if twin_ws is None and twin_sock is None:
                    out.dim("Not connected. Use 'connect <world>' first.")
                else:
                    message = line.strip()[4:]
                    if twin_use_tcp and twin_sock:
                        twin_send_tcp(f"SAY {message}")
                    elif twin_ws:
                        import json
                        twin_ws.send(json.dumps({"type": "CHAT", "message": message}))
                continue

            if line.strip() == 'reset world':
                if twin_ws is None and twin_sock is None:
                    out.dim("Not connected. Use 'connect <world>' first.")
                else:
                    if twin_use_tcp and twin_sock:
                        twin_send_tcp("RESET")
                    elif twin_ws:
                        import json
                        twin_ws.send(json.dumps({"type": "RESET"}))
                    out.success(f"Reset sent to world '{twin_world_id}'")
                continue

            if line.strip() in ('users', 'who'):
                if twin_ws is None and twin_sock is None:
                    out.dim("Not connected. Use 'connect <world>' first.")
                else:
                    if twin_use_tcp and twin_sock:
                        twin_send_tcp("WHO")
                        # Wait briefly then display any queued messages (receiver thread handles response)
                        import time
                        time.sleep(0.3)
                        twin_display_messages()
                    elif twin_ws:
                        import json
                        twin_ws.send(json.dumps({"type": "USERS"}))
                        # For WebSocket, also wait and display
                        import time
                        time.sleep(0.3)
                        twin_display_messages()
                continue

            # Display any pending twin messages before processing commands
            twin_display_messages()

            # Handle move command for twin world objects (objects that exist remotely but not locally)
            cmd = line.strip()
            if cmd.lower().startswith('move ') and (twin_ws or twin_sock):
                # Parse: move <object_ref> <direction> [by] <amount>
                # object_ref can be multi-word like "red ball" or "ball-1"
                match = re.match(r'^move\s+(.+?)\s+(up|down|left|right|forward|back|backward)\s+(?:by\s+)?(\d+(?:\.\d+)?)$', cmd, re.IGNORECASE)
                if match:
                    obj_ref, direction, amount_str = match.groups()
                    amount = float(amount_str)

                    # Fuzzy match object reference against twin world objects
                    obj_name = None
                    objects = twin_world_state.get('objects', {})

                    # First try exact match
                    if obj_ref in objects:
                        obj_name = obj_ref
                    else:
                        # Try fuzzy matching: "red ball" -> find ball with color red
                        ref_words = obj_ref.lower().split()
                        best_match = None
                        best_score = 0

                        for name, data in objects.items():
                            score = 0
                            obj_type = data.get('type', '').lower()
                            obj_color = data.get('color', '').lower()
                            name_lower = name.lower()

                            # Check each word in reference
                            for word in ref_words:
                                if word == obj_type or word == obj_type + 's':  # "ball" or "balls"
                                    score += 10
                                if word == obj_color:
                                    score += 5
                                if word in name_lower:
                                    score += 3

                            if score > best_score:
                                best_score = score
                                best_match = name

                        if best_match and best_score > 0:
                            obj_name = best_match
                            out.dim(f"[matched '{obj_ref}' → '{obj_name}']")

                    if not obj_name:
                        out.error(f"No object matching '{obj_ref}' found in world")
                        continue

                    # Check if object exists in twin world but not locally
                    local_exists = interpreter and interpreter.current_env.exists(obj_name)
                    remote_exists = obj_name in objects

                    if remote_exists and not local_exists:
                        # Get current position from twin state
                        obj_data = twin_world_state['objects'][obj_name]
                        old_x = obj_data.get('x', 0)
                        old_y = obj_data.get('y', 0)
                        old_z = obj_data.get('z', 0)

                        # Calculate new position
                        direction = direction.lower()
                        new_x, new_y, new_z = old_x, old_y, old_z
                        if direction == 'right':
                            new_x = old_x + amount
                        elif direction == 'left':
                            new_x = old_x - amount
                        elif direction == 'up':
                            new_y = old_y - amount
                        elif direction == 'down':
                            new_y = old_y + amount
                        elif direction == 'forward':
                            new_z = old_z - amount
                        elif direction in ('back', 'backward'):
                            new_z = old_z + amount

                        # Broadcast the raw command (for semantic interpretation by other clients)
                        import json
                        twin_ws.send(json.dumps({
                            "type": "MOVE",
                            "id": obj_name,
                            "x": new_x, "y": new_y, "z": new_z,
                            "command": cmd  # Include raw command for other clients
                        }))

                        # Update local twin state
                        twin_world_state['objects'][obj_name]['x'] = new_x
                        twin_world_state['objects'][obj_name]['y'] = new_y
                        twin_world_state['objects'][obj_name]['z'] = new_z

                        out.success(f"Moved '{obj_name}' {direction} by {amount}")
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

            # ===== Voice Normalization =====
            # Normalize input using voice spec (typos, spellings, implied words)
            try:
                from .voice import normalize_input
                quiet_mode = getattr(interpreter, 'quiet_mode', False)
                normalized, messages = normalize_input(line, quiet=quiet_mode)
                if normalized != line:
                    line = normalized
                    for msg in messages:
                        out.dim(msg)
            except ImportError:
                # Fallback: basic spelling normalization
                line = re.sub(r'\bcolour\b', 'color', line, flags=re.IGNORECASE)
                line = re.sub(r'\bcentre\b', 'center', line, flags=re.IGNORECASE)

            # ===== Bulk Operations now handled by parser (BulkOperation node) =====
            # This ensures consistency between REPL and scripts

            # ===== Universal REPL Commands =====
            # "If it works somewhere, it should work everywhere"
            stripped = line.strip().lower()
            parts = line.strip().split()

            # Triple-newline → go (close all blocks and execute)
            if not stripped:
                blank_line_count += 1
                if blank_line_count >= 3 and buffer:
                    # Trigger 'go' behavior - auto-close blocks and execute
                    open_blocks = 0
                    for buf_line in buffer:
                        buf_stripped = buf_line.strip().lower()
                        # Only count block-opening keywords (not 'create <name>' one-liners)
                        if any(buf_stripped.startswith(kw) for kw in ['create object ', 'if ', 'define function', 'when ', 'while ', 'for ', 'do ']):
                            open_blocks += 1
                        if buf_stripped == 'end':
                            open_blocks = max(0, open_blocks - 1)

                    if open_blocks > 0:
                        out.dim(f"[auto-closing {open_blocks} block{'s' if open_blocks > 1 else ''}]")
                        for _ in range(open_blocks):
                            buffer.append('end')

                    source = '\n'.join(buffer)
                    buffer = []
                    blank_line_count = 0
                    try:
                        _before = snapshot_object_states()
                        interpreter = run_source(source, "<repl>", interpreter)
                        broadcast_object_changes(_before)
                    except RoshError as e:
                        out.error(str(e))
                    continue
                continue  # Skip empty line processing
            else:
                blank_line_count = 0  # Reset on non-blank line

            # version (no args) - show interpreter version
            if stripped == 'version':
                out.print(f"Rosh v{__version__}", style="cyan")
                continue

            # help create - list known objects that can be created
            if stripped in ('help create', 'help clone'):
                from .data import get_known_object_names
                names = sorted(get_known_object_names())
                out.print("create - Create objects", style="bold cyan")
                out.print()
                out.print("You can create any object:")
                out.print("  create thing           - Create empty object 'thing'")
                out.print("  create object ball     - Same, more explicit")
                out.print("  create car porsche     - Create 'porsche' of type 'car'")
                out.print("  clone ball             - Clone existing 'ball'")
                out.print()
                if names:
                    out.print("Known object types (with pre-defined properties):", style="cyan")
                    # Format in rows of 6
                    row_size = 6
                    for i in range(0, len(names), row_size):
                        row = names[i:i + row_size]
                        out.print("  " + ", ".join(row))
                continue

            # help make - explain the make command (REPL-only)
            if stripped == 'help make':
                out.print("make - Adjust object properties (REPL only)", style="bold cyan")
                out.print()
                out.print("Usage:")
                out.print("  make <obj> bigger    - Scale up by 1.5×")
                out.print("  make <obj> smaller   - Scale down by 1.5×")
                out.print("  make <obj> faster    - Speed up by 1.5×")
                out.print("  make <obj> slower    - Slow down by 1.5×")
                out.print("  make <obj> visible   - Show the object")
                out.print("  make <obj> hidden    - Hide the object")
                out.print("  make <obj> <color>   - Change color (red, blue, etc.)")
                out.print()
                out.dim("Note: 'make' is a REPL convenience command, not part of the Rosh language.")
                continue

            # help set - explain the set command
            if stripped == 'help set':
                out.print("set - Set object properties", style="bold cyan")
                out.print()
                out.print("Usage:")
                out.print("  set <obj> <prop> to <value>")
                out.print("  set ball color to red")
                out.print("  set cube x to 100")
                out.print("  set sphere scale to 2")
                out.print()
                out.print("Common properties: x, y, z, color, scale, visible,")
                out.dim("  rotation, opacity, speed, group")
                continue

            # help get - explain the get command
            if stripped == 'help get':
                out.print("get - Select/examine objects", style="bold cyan")
                out.print()
                out.print("Usage:")
                out.print("  get <name>            - Select single object")
                out.print("  get all cubes         - Select all of type")
                out.print("  get all red balls     - With color modifier")
                out.print("  get all big cubes     - With size modifier")
                out.print()
                out.dim("After selecting, use 'it' to reference the object.")
                continue

            # help delete - explain the delete command
            if stripped in ('help delete', 'help destroy', 'help remove'):
                out.print("delete - Remove objects", style="bold cyan")
                out.print()
                out.print("Usage:")
                out.print("  delete <name>         - Delete single object")
                out.print("  delete all cubes      - Delete all of type")
                out.print("  delete all red balls  - With color modifier")
                out.print()
                out.dim("Bulk deletes require confirmation (type 'go' or 'yes').")
                continue

            # help move - explain the move command
            if stripped == 'help move':
                out.print("move - Move objects", style="bold cyan")
                out.print()
                out.print("Relative movement:")
                out.print("  move <obj> up 5       - Move up by 5")
                out.print("  move <obj> left 10    - Move left by 10")
                out.print("  move <obj> forward 3  - Move forward by 3")
                out.print()
                out.print("Absolute position:")
                out.print("  move <obj> to 0 10 0  - Move to x=0, y=10, z=0")
                out.print()
                out.dim("Directions: up, down, left, right, forward, back")
                continue

            # help hide/show - explain visibility commands
            if stripped in ('help hide', 'help show'):
                out.print("hide/show - Toggle visibility", style="bold cyan")
                out.print()
                out.print("Usage:")
                out.print("  hide <name>           - Hide single object")
                out.print("  show <name>           - Show single object")
                out.print("  hide all cubes        - Hide all of type")
                out.print("  show all red balls    - Show with modifier")
                out.print()
                out.dim("Bulk operations require confirmation.")
                continue

            # help list - explain the list command
            if stripped in ('help list', 'help ls'):
                out.print("list - List objects", style="bold cyan")
                out.print()
                out.print("Usage:")
                out.print("  list                  - List all objects")
                out.print("  list cubes            - List objects of type")
                out.print("  list all              - Show all including hidden")
                out.print("  list <scene>          - List objects in scene")
                continue

            # help look - explain the look command
            if stripped in ('help look', 'help examine', 'help x'):
                out.print("look - Examine objects", style="bold cyan")
                out.print()
                out.print("Usage:")
                out.print("  look <name>           - Show object details")
                out.print("  look                  - Examine current object")
                out.print("  x <name>              - Short form")
                out.print()
                out.dim("Shows all properties and current values.")
                continue

            # help scenes - explain scene commands
            if stripped in ('help scenes', 'help go', 'help scene'):
                out.print("scenes - Scene management", style="bold cyan")
                out.print()
                out.print("Usage:")
                out.print("  scenes                - List all scenes")
                out.print("  go <scene>            - Go to scene")
                out.print("  create scene <name>   - Create new scene")
                out.print("  set <obj> scene to <name> - Move object to scene")
                continue

            # Provide friendlier guidance for commands missing arguments
            # Exception: commands that are valid with no arguments
            if len(parts) == 1 and parts[0].lower() not in ('go', 'confirm', 'yes', 'y', 'undo', 'redo', 'oops', 'repeat', 'look', 'l', 'list', 'ls'):
                if _show_command_usage(out, parts[0].lower()):
                    continue

            # create scene <name> - explicitly create a scene
            if stripped.startswith('create scene '):
                scene_name = line.strip().split(None, 2)[2] if len(line.strip().split()) > 2 else None
                if scene_name:
                    _create_scene(interpreter, out, scene_name)
                else:
                    out.warning("Usage: create scene <name>")
                continue

            # scenes / list scenes - show available scenes
            if stripped in ('scenes', 'list scenes', 'ls scenes'):
                _list_scenes(interpreter, out)
                continue

            # list <scene> - show objects in specific scene
            if stripped.startswith('list ') and stripped.split()[1] not in ('all', 'objects'):
                scene_name = stripped.split(None, 1)[1]
                _list_objects(interpreter, out, scene_filter=scene_name)
                continue

            # list / ls / objects (no args) - show all objects
            if stripped in ('list', 'ls', 'objects', 'list objects'):
                _list_objects(interpreter, out)
                continue

            # list all - show all objects grouped by scene
            if stripped in ('list all', 'ls all', 'objects all'):
                _list_objects(interpreter, out, max_display=None, group_by_scene=True)
                continue

            # look (no args) - same as list
            if stripped in ('look', 'l'):
                _list_objects(interpreter, out)
                continue

            # oops - natural language alias for single undo
            if stripped == 'oops':
                interpreter.perform_undo(1)
                continue

            # remove <x> - natural language alias for delete <x>
            if stripped.startswith('remove '):
                obj_name = stripped[7:].strip()
                if obj_name:
                    line = f"delete {obj_name}"
                    stripped = line
                    # Fall through to normal processing

            # copy/duplicate - aliases for clone
            if stripped.startswith('copy ') or stripped.startswith('duplicate '):
                rest = stripped.split(None, 1)[1] if ' ' in stripped else ''
                if rest:
                    line = f"clone {rest}"
                    stripped = line.lower()
                    parts = line.split()
                    out.dim(f"→ {line}")
                    # Fall through to normal processing

            # go <place> - navigate to scene or room (when not just "go" for confirm)
            if stripped.startswith('go ') and interpreter.pending_operation is None:
                place = stripped[3:].strip()
                if place:
                    # Check if this is a scene (including explicitly created ones)
                    available_scenes = _get_all_scenes(interpreter)
                    is_scene = place in available_scenes or place.lower() in [s.lower() for s in available_scenes]

                    if is_scene:
                        # Navigate to scene directly
                        line = f"goto scene {place}"
                        stripped = line
                        # Fall through to normal processing
                    elif available_scenes:
                        # Try fuzzy match against scenes
                        import difflib
                        matches = difflib.get_close_matches(place, available_scenes, n=1, cutoff=0.6)
                        if matches:
                            out.warning(f"Scene '{place}' not found. Did you mean '{matches[0]}'?")
                            out.dim(f"Type 'go {matches[0]}' to confirm.")
                            continue
                        else:
                            # Fall back to room navigation
                            line = f"goto {place}"
                            stripped = line
                    else:
                        # No scenes defined, try room navigation
                        line = f"goto {place}"
                        stripped = line
                    # Fall through to normal processing

            # move <obj> to <x> <y> [z] - set position with one command
            move_match = re.match(r'^move\s+(\w+)\s+to\s+(-?\d+(?:\.\d+)?)\s*,?\s*(-?\d+(?:\.\d+)?)(?:\s*,?\s*(-?\d+(?:\.\d+)?))?$', stripped, re.IGNORECASE)
            if move_match:
                input_name = move_match.group(1)
                x_val = float(move_match.group(2))
                y_val = float(move_match.group(3))
                z_val = move_match.group(4)

                # Resolve with fuzzy matching
                obj, obj_name, matches = _resolve_object_name(interpreter, input_name)
                if obj_name and obj_name != input_name:
                    out.dim(f'[resolved: "{input_name}" → "{obj_name}"]')

                if obj is None:
                    if matches:
                        out.print(f'Multiple matches for "{input_name}":', style="cyan")
                        for name, _ in matches[:8]:
                            out.dim(f"  {name}")
                        out.dim("Which one did you mean?")
                    else:
                        out.warning(f"Object '{input_name}' not found")
                    continue

                if hasattr(obj, 'set'):
                    obj.set('x', x_val)
                    obj.set('y', y_val)
                    if z_val:
                        obj.set('z', float(z_val))
                        out.success(f"{obj_name} moved to ({x_val}, {y_val}, {z_val})")
                    else:
                        out.success(f"{obj_name} moved to ({x_val}, {y_val})")
                    continue
                out.warning(f"Object '{obj_name}' cannot be moved")
                continue

            # make - "upsert" command: create if not exists, then modify
            # make <obj> → create if not exists, select if exists
            # make <obj> <color> → set <obj> color to <color>
            # make <obj> <prop> <value> → set <obj> <prop> to <value>
            # make <obj> visible/hidden → show/hide
            # make <obj> big/bigger → scale up
            # make <obj> faster/slower → adjust speed
            if stripped.startswith('make ') and len(parts) >= 2:
                input_name = parts[1]
                rest = parts[2:] if len(parts) >= 3 else []
                known_colors = {'red', 'green', 'blue', 'yellow', 'cyan', 'magenta', 'white', 'black', 'orange', 'purple', 'pink', 'gray', 'grey', 'gold', 'silver'}
                known_types = {'cube', 'box', 'sphere', 'ball', 'cylinder', 'cone', 'torus', 'plane', 'sprite', 'text'}

                # Try to resolve existing object with fuzzy matching
                resolved_obj, obj_name, matches = _resolve_object_name(interpreter, input_name)
                if resolved_obj and obj_name != input_name:
                    out.dim(f'[resolved: "{input_name}" → "{obj_name}"]')
                elif matches:
                    # Multiple matches - ask user to clarify
                    out.print(f'Multiple matches for "{input_name}":', style="cyan")
                    for name, _ in matches[:8]:
                        out.dim(f"  {name}")
                    out.dim("Which one did you mean?")
                    continue

                obj_exists = resolved_obj is not None
                if not obj_exists:
                    obj_name = input_name  # Use original name for creation

                # If object doesn't exist and name looks like a type, create it
                if not obj_exists:
                    # Check if this is a known type or known object
                    # Try to create it first
                    create_type = obj_name
                    create_modifiers = []

                    # Parse any modifiers from rest for creation
                    for word in rest:
                        if word.lower() in known_colors:
                            create_modifiers.append(word)
                        elif word.lower() in ('big', 'large', 'small', 'tiny', 'huge'):
                            create_modifiers.append(word)

                    # Build create command
                    create_cmd = f"create {' '.join(create_modifiers)} {create_type}" if create_modifiers else f"create {create_type}"
                    out.dim(f"[→ {create_cmd}]")

                    # Execute create
                    try:
                        lexer = Lexer(create_cmd)
                        tokens = lexer.tokenize()
                        parser = Parser(tokens)
                        ast = parser.parse()
                        interpreter.execute(ast)
                        # Now the object should exist with auto-generated name
                        # Find the newly created object (e.g., "banana" → "banana-1")
                        for name in interpreter.current_env.bindings.keys():
                            if name.lower().startswith(create_type.lower()):
                                obj_name = name
                                obj_exists = True
                                break
                    except Exception as e:
                        out.error(f"Failed to create {create_type}: {e}")
                        continue

                    # If only "make banana" with no further modifiers, we're done
                    remaining_rest = [w for w in rest if w.lower() not in known_colors and w.lower() not in ('big', 'large', 'small', 'tiny', 'huge')]
                    if not remaining_rest:
                        continue
                    rest = remaining_rest

                # Now handle modifications (object should exist)
                if not rest:
                    # Just "make <obj>" - select it if it exists
                    if obj_exists:
                        out.success(f"Selected: {obj_name}")
                    continue

                transformed = None

                # make <obj> visible → show <obj>
                if rest[0].lower() in ('visible', 'shown'):
                    transformed = f"show {obj_name}"
                # make <obj> invisible/hidden → hide <obj>
                elif rest[0].lower() in ('invisible', 'hidden', 'hide'):
                    transformed = f"hide {obj_name}"
                # make <obj> <color> → set <obj> color to <color>
                elif rest[0].lower() in known_colors:
                    transformed = f"set {obj_name} color to {rest[0]}"
                # make <obj> big/bigger → multiply scale by 1.5
                elif rest[0].lower() in ('big', 'bigger', 'large', 'larger'):
                    if interpreter and interpreter.current_env.exists(obj_name):
                        obj = interpreter.current_env.get(obj_name)
                        if hasattr(obj, 'get') and hasattr(obj, 'set'):
                            current_scale = obj.get('scale') if obj.has('scale') else 1
                            new_scale = current_scale * 1.5
                            obj.set('scale', new_scale)
                            out.success(f"{obj_name}.scale = {new_scale:.2f}")
                            continue
                    transformed = f"set {obj_name} scale to 1.5"  # Fallback
                # make <obj> small/smaller → divide scale by 1.5
                elif rest[0].lower() in ('small', 'smaller', 'tiny'):
                    if interpreter and interpreter.current_env.exists(obj_name):
                        obj = interpreter.current_env.get(obj_name)
                        if hasattr(obj, 'get') and hasattr(obj, 'set'):
                            current_scale = obj.get('scale') if obj.has('scale') else 1
                            new_scale = current_scale / 1.5
                            obj.set('scale', new_scale)
                            out.success(f"{obj_name}.scale = {new_scale:.2f}")
                            continue
                    transformed = f"set {obj_name} scale to 0.67"  # Fallback
                # make <obj> faster → multiply speed by 1.5
                elif rest[0].lower() in ('fast', 'faster', 'quick', 'quicker'):
                    if interpreter and interpreter.current_env.exists(obj_name):
                        obj = interpreter.current_env.get(obj_name)
                        if hasattr(obj, 'get') and hasattr(obj, 'set'):
                            current_speed = obj.get('speed') if obj.has('speed') else 1
                            new_speed = current_speed * 1.5
                            obj.set('speed', new_speed)
                            out.success(f"{obj_name}.speed = {new_speed:.2f}")
                            continue
                    transformed = f"set {obj_name} speed to 1.5"  # Fallback
                # make <obj> slower → divide speed by 1.5
                elif rest[0].lower() in ('slow', 'slower'):
                    if interpreter and interpreter.current_env.exists(obj_name):
                        obj = interpreter.current_env.get(obj_name)
                        if hasattr(obj, 'get') and hasattr(obj, 'set'):
                            current_speed = obj.get('speed') if obj.has('speed') else 1
                            new_speed = current_speed / 1.5
                            obj.set('speed', new_speed)
                            out.success(f"{obj_name}.speed = {new_speed:.2f}")
                            continue
                    transformed = f"set {obj_name} speed to 0.67"  # Fallback
                # make <obj> <prop> <value> → set <obj> <prop> to <value>
                elif len(rest) >= 2:
                    prop_name = rest[0]
                    value = ' '.join(rest[1:])
                    transformed = f"set {obj_name} {prop_name} to {value}"

                if transformed:
                    out.dim(f"→ {transformed}")
                    line = transformed
                    stripped = line.strip().lower()
                    parts = line.strip().split()
                # Fall through to normal processing

            if parts and parts[0].lower() == 'undo':
                if len(parts) >= 2 and parts[1].lower() == 'stack':
                    count = 5
                    if len(parts) >= 3:
                        try:
                            count = int(parts[2])
                        except ValueError:
                            out.warning("Usage: undo stack [count]")
                            count = 5
                    interpreter.describe_undo_stack(max(1, count))
                else:
                    steps = 1
                    if len(parts) >= 2:
                        try:
                            steps = int(parts[1])
                        except ValueError:
                            out.warning("Usage: undo [count]")
                            steps = 1
                    interpreter.perform_undo(max(1, steps))
                continue

            if parts and parts[0].lower() == 'redo':
                if len(parts) >= 2 and parts[1].lower() == 'stack':
                    count = 5
                    if len(parts) >= 3:
                        try:
                            count = int(parts[2])
                        except ValueError:
                            out.warning("Usage: redo stack [count]")
                            count = 5
                    interpreter.describe_redo_stack(max(1, count))
                else:
                    steps = 1
                    if len(parts) >= 2:
                        try:
                            steps = int(parts[1])
                        except ValueError:
                            out.warning("Usage: redo [count]")
                            steps = 1
                    interpreter.perform_redo(max(1, steps))
                continue

            # look <obj> / examine <obj> / inspect <obj> / x <obj> - show object properties
            # Supports multi-word references like "look red ball"
            if len(parts) >= 2 and parts[0].lower() in ('look', 'l', 'examine', 'ex', 'inspect', 'x'):
                obj_ref = ' '.join(parts[1:])  # Join all words after command
                _examine_object(interpreter, out, obj_ref)
                continue

            # show <obj> / unhide <obj> - make object visible
            # show all <type> - show all matching objects with confirmation
            # Supports multi-word references: show red ball, show all blue balls
            if len(parts) >= 2 and parts[0].lower() in ('show', 'unhide'):
                # Check for "show all <type>"
                if parts[1].lower() == 'all' and len(parts) >= 3:
                    obj_ref = ' '.join(parts[2:])
                    matching, desc = _show_all_command(interpreter, out, obj_ref)
                    if matching:
                        out.print(f"Show {len(matching)} {desc}(s)? (yes/no)", style="yellow")
                        interpreter.pending_operation = {
                            'type': 'bulk_show',
                            'matching': matching,
                            'desc': desc
                        }
                    continue

                obj_ref = ' '.join(parts[1:])  # Join all words after command
                obj, obj_name, _ = _resolve_object_name(interpreter, obj_ref)
                if obj and hasattr(obj, 'set'):
                    obj.set('visible', True)
                    out.success(f"Showed '{obj_name}'")
                elif obj:
                    out.warning(f"Cannot set visibility on '{obj_name}'")
                else:
                    out.warning(f"Object '{obj_ref}' not found")
                continue

            # hide <obj> - hide object
            # hide all <type> - hide all matching objects with confirmation
            # Supports multi-word references: hide red ball, hide all blue balls
            if len(parts) >= 2 and parts[0].lower() == 'hide':
                # Check for "hide all <type>"
                if parts[1].lower() == 'all' and len(parts) >= 3:
                    obj_ref = ' '.join(parts[2:])
                    matching, desc = _hide_all_command(interpreter, out, obj_ref)
                    if matching:
                        out.print(f"Hide {len(matching)} {desc}(s)? (yes/no)", style="yellow")
                        interpreter.pending_operation = {
                            'type': 'bulk_hide',
                            'matching': matching,
                            'desc': desc
                        }
                    continue

                obj_ref = ' '.join(parts[1:])  # Join all words after command
                obj, obj_name, _ = _resolve_object_name(interpreter, obj_ref)
                if obj and hasattr(obj, 'set'):
                    obj.set('visible', False)
                    out.success(f"Hid '{obj_name}'")
                elif obj:
                    out.warning(f"Cannot set visibility on '{obj_name}'")
                else:
                    out.warning(f"Object '{obj_ref}' not found")
                continue

            # delete all <type> - delete all matching objects with confirmation
            # Supports modifiers: delete all blue balls, delete all big red cubes
            if len(parts) >= 3 and parts[0].lower() == 'delete' and parts[1].lower() == 'all':
                obj_ref = ' '.join(parts[2:])
                matching, desc = _delete_all_command(interpreter, out, obj_ref)
                if matching:
                    out.print(f"Delete {len(matching)} {desc}(s)? (yes/no)", style="yellow")
                    interpreter.pending_operation = {
                        'type': 'bulk_delete',
                        'matching': matching,
                        'desc': desc
                    }
                continue

            # meta <setting> [<value>] - runtime settings
            if parts and parts[0].lower() == 'meta':
                if len(parts) == 1:
                    # Show all meta settings
                    out.print("Meta settings:", style="cyan")
                    quiet = getattr(interpreter, 'quiet_mode', False)
                    out.print(f"  quiet: {'on' if quiet else 'off'}", style="dim")
                else:
                    setting = parts[1].lower()
                    if setting in ('quiet', 'q'):
                        # Toggle or set quiet mode
                        if len(parts) >= 3:
                            value = parts[2].lower()
                            interpreter.quiet_mode = value in ('on', 'true', '1', 'yes')
                        else:
                            interpreter.quiet_mode = True
                        out.print(f"Quiet mode {'enabled' if interpreter.quiet_mode else 'disabled'}", style="cyan")
                    elif setting in ('verbose', 'v'):
                        interpreter.quiet_mode = False
                        out.print("Verbose mode enabled", style="cyan")
                    else:
                        out.warning(f"Unknown setting: {setting}")
                        out.dim("Available: quiet, verbose")
                continue

            # clear / cls - clear screen (simple version)
            if stripped in ('clear', 'cls'):
                import subprocess
                subprocess.run('clear' if sys.platform != 'win32' else 'cls', shell=True)
                continue

            # Handle corrected command confirmation BEFORE go/yes handling
            # This ensures block detection works (e.g., "creat object x" → "create object x")
            if stripped in ('go', 'confirm', 'yes', 'y') and interpreter.pending_operation is not None:
                op = interpreter.pending_operation
                if op.get('type') == 'corrected_command':
                    corrected = op['command']
                    interpreter.pending_operation = None
                    out.dim(f"→ {corrected}")
                    # Replace line with corrected command and continue through normal processing
                    line = corrected
                    stripped = line.strip().lower()
                    parts = line.strip().split()
                    # Fall through to normal processing (including block detection)

            # go/confirm/yes/y - confirm pending bulk operation OR auto-close blocks
            if stripped in ('go', 'confirm', 'yes', 'y'):
                # First check if there's a pending operation
                if interpreter.pending_operation is not None:
                    op = interpreter.pending_operation
                    op_type = op.get('type')

                    # Handle CLI-level bulk operations directly
                    if op_type == 'bulk_delete':
                        _execute_delete_all(interpreter, out, op['matching'], op['desc'])
                        interpreter.pending_operation = None
                        continue
                    elif op_type == 'bulk_hide':
                        _execute_hide_all(interpreter, out, op['matching'], op['desc'])
                        interpreter.pending_operation = None
                        continue
                    elif op_type == 'bulk_show':
                        _execute_show_all(interpreter, out, op['matching'], op['desc'])
                        interpreter.pending_operation = None
                        continue

                    # Execute as confirm command (parser-level bulk ops)
                    # Note: 'y' is CLI-only (conflicts with variable), so translate to 'yes'
                    confirm_cmd = 'yes' if stripped == 'y' else stripped
                    try:
                        interpreter = run_source(confirm_cmd, "<repl>", interpreter)
                    except RoshError as e:
                        out.error(str(e))
                    continue

            # no/n/cancel - cancel pending bulk operation
            if stripped in ('no', 'n', 'cancel') and interpreter.pending_operation is not None:
                op = interpreter.pending_operation
                op_type = op.get('type', '')
                if op_type.startswith('bulk_'):
                    out.dim("Cancelled")
                    interpreter.pending_operation = None
                    continue

            # Treat 'go' as buffer execution command
            if stripped == 'go':
                if not buffer:
                    out.dim("Nothing to run")
                    continue

                # Count open blocks that need closing
                source_so_far = '\n'.join(buffer)
                open_blocks = 0
                for buf_line in buffer:
                    buf_stripped = buf_line.strip().lower()
                    # Only count block-opening keywords (not 'create <name>' one-liners)
                    if any(buf_stripped.startswith(kw) for kw in ['create object ', 'if ', 'define function', 'when ', 'while ', 'for ', 'do ']):
                        open_blocks += 1
                    # 'end' closes a block
                    if buf_stripped == 'end':
                        open_blocks = max(0, open_blocks - 1)

                # Auto-close all open blocks
                if open_blocks > 0:
                    out.dim(f"[auto-closing {open_blocks} block{'s' if open_blocks > 1 else ''}]")
                    for _ in range(open_blocks):
                        buffer.append('end')

                # Execute the complete buffer
                source = '\n'.join(buffer)
                buffer = []
                try:
                    _before = snapshot_object_states()
                    interpreter = run_source(source, "<repl>", interpreter)
                    broadcast_object_changes(_before)
                except RoshError as e:
                    out.error(str(e))
                continue

            # get <obj> or get <obj> <prop> - unified get command (#017)
            # Also: get all <type>, get <type> <n>, get blue sphere (deep search)
            # Note: bulk get (get N type) handled by parser - skip this handler
            is_bulk_get = (len(parts) >= 3 and parts[0].lower() == 'get' and parts[1].isdigit())
            if len(parts) >= 2 and parts[0].lower() == 'get' and not is_bulk_get:
                # Handle "get all <type>" - list all instances
                # Supports modifiers: "get all blue balls", "get all big red cubes"
                if parts[1].lower() == 'all' and len(parts) >= 3:
                    obj_ref = ' '.join(parts[2:])  # Join all words after "all"
                    _get_all_command(interpreter, out, obj_ref)
                    continue

                identifier = parts[1]
                prop_name = parts[2] if len(parts) >= 3 else None

                # Handle "get <type> <n>" - get instance by number
                if prop_name and prop_name.isdigit():
                    instance_name = f"{identifier}-{prop_name}" if int(prop_name) > 1 else identifier
                    # Check if this is actually an instance, not a property
                    if interpreter.current_env.exists(instance_name):
                        _get_command(interpreter, out, instance_name, None)
                        continue
                    # Also try without suffix for instance 1
                    if prop_name == "1" and interpreter.current_env.exists(identifier):
                        _get_command(interpreter, out, identifier, None)
                        continue

                # Deep search: "get blue sphere", "get big red cube"
                # If identifier doesn't exist and we have multiple words, try deep search
                if not interpreter.current_env.exists(identifier) and len(parts) >= 3:
                    search_words = parts[1:]  # Everything after 'get'
                    obj, obj_name = _deep_search(interpreter, search_words)
                    if obj:
                        out.dim(f"→ found: {obj_name}")
                        _get_command(interpreter, out, obj_name, None)
                        continue

                _get_command(interpreter, out, identifier, prop_name)
                continue

            # Handle semicolon-separated statements ending with 'go'
            # e.g., "for x in 1 to 100 then; create banana; go"
            if ';' in line:
                parts = [p.strip() for p in line.split(';') if p.strip()]
                if parts and parts[-1].lower() in ('go', 'confirm', 'yes', 'y'):
                    # Add all parts except the last to buffer
                    for part in parts[:-1]:
                        buffer.append(part)
                    # Now trigger 'go' behavior on the buffer
                    # Count open blocks that need closing
                    open_blocks = 0
                    for buf_line in buffer:
                        buf_stripped = buf_line.strip().lower()
                        # Only count block-opening keywords (not 'create <name>' one-liners)
                        if any(buf_stripped.startswith(kw) for kw in ['create object ', 'if ', 'define function', 'when ', 'while ', 'for ', 'do ']):
                            open_blocks += 1
                        if buf_stripped == 'end':
                            open_blocks = max(0, open_blocks - 1)

                    if open_blocks > 0:
                        out.dim(f"[auto-closing {open_blocks} block{'s' if open_blocks > 1 else ''}]")
                        for _ in range(open_blocks):
                            buffer.append('end')

                    source = '\n'.join(buffer)
                    buffer = []
                    try:
                        _before = snapshot_object_states()
                        interpreter = run_source(source, "<repl>", interpreter)
                        broadcast_object_changes(_before)
                    except RoshError as e:
                        out.error(str(e))
                    continue

            # Add line to buffer
            buffer.append(line)

            # Check if we need more input (waiting for 'end')
            # Simple heuristic: if line contains block-opening keywords, wait for 'end'
            stripped = line.strip().lower()
            keywords_needing_end = ['create object', 'if ', 'define function', 'for ', 'while ', 'when ', 'do ']

            if any(stripped.startswith(kw) for kw in keywords_needing_end):
                # Wait for 'end'
                continue

            # If buffer has content and last line is 'end', execute
            if buffer and buffer[-1].strip().lower() == 'end':
                source = '\n'.join(buffer)
                buffer = []
                try:
                    _before = snapshot_object_states()
                    interpreter = run_source(source, "<repl>", interpreter)
                    broadcast_object_changes(_before)
                except RoshError as e:
                    out.error(str(e))
                continue

            # If we have a simple statement (no 'end' needed), execute immediately
            # unless we're in the middle of a block
            if not buffer or len(buffer) == 1:
                source = '\n'.join(buffer)
                buffer = []
                try:
                    _before = snapshot_object_states()
                    interpreter = run_source(source, "<repl>", interpreter)
                    broadcast_object_changes(_before)
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
                                # Build corrected command and stage it
                                corrected = source.strip().replace(word, suggestion, 1)
                                interpreter.pending_operation = {
                                    'type': 'corrected_command',
                                    'command': corrected
                                }
                                out.print(f"Did you mean: {suggestion}?", style="yellow")
                                out.info("Type 'yes' or 'go' to execute")
                            else:
                                out.dim("Type 'alias' to see available aliases, or use Rosh syntax")
                    elif "Incomplete command" in error_msg:
                        # Check if they started with a known command
                        first_word = source.strip().split()[0] if source.strip() else ""
                        if first_word in COMMAND_USAGE_HINTS:
                            hint = COMMAND_USAGE_HINTS[first_word]
                            out.warning(hint['message'])
                            out.print("Try one of these:", style="dim")
                            for ex in hint['examples']:
                                out.print(f"  {ex}", style="dim")
                        else:
                            out.error(str(e))
                    else:
                        out.error(str(e))

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


def copy_model_assets(source_path: Path, output_dir: Path, model_assets: set):
    """Copy 3D model assets (GLB files) that are used in the game.

    Searches for model files in these locations (in order):
    1. rosh-lang/assets/3d_glb/ (distributed assets)
    2. Same directory as source file
    3. ../assets/3d_glb/ relative to source file

    Args:
        source_path: Path to the source .rosh file
        output_dir: Output directory for the game
        model_assets: Set of model file paths (e.g., '3d_glb/linen_bank.glb')
    """
    import shutil
    from pathlib import Path

    if not model_assets:
        return

    # Find rosh-lang root (look for assets/3d_glb folder)
    source_dir = source_path.parent
    rosh_lang_root = source_dir
    for _ in range(5):  # Search up to 5 levels
        if (rosh_lang_root / 'assets' / '3d_glb').exists():
            break
        rosh_lang_root = rosh_lang_root.parent

    search_paths = [
        rosh_lang_root / 'assets',  # rosh-lang/assets/ (models are in 3d_glb/)
        source_dir / 'assets',  # Same dir as .rosh file
        source_dir.parent / 'assets',  # ../assets/
    ]

    copied_count = 0
    for model_path in model_assets:
        # model_path is like '3d_glb/linen_bank.glb'
        model_file = Path(model_path)

        # Try each search path
        for search_path in search_paths:
            full_path = search_path / model_file
            if full_path.exists():
                # Create destination directory (preserving structure like 3d_glb/)
                dest_path = output_dir / model_file
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(full_path, dest_path)
                print(f"  🎨 Copied 3D model: {model_file}", file=sys.stderr)
                copied_count += 1
                break
        else:
            # Model not found in any search path
            print(f"  ⚠️  3D model not found: {model_path}", file=sys.stderr)

    if copied_count > 0:
        print(f"✅ Copied {copied_count} 3D model(s)", file=sys.stderr)


def _minify_js_code(js_code: str) -> str:
    """Minify JavaScript source code using an optional dependency."""
    try:
        import rjsmin
        return rjsmin.jsmin(js_code)
    except ImportError:
        try:
            from jsmin import jsmin as _jsmin
            return _jsmin(js_code)
        except ImportError:
            print(
                "Error: --minify requires rjsmin (preferred) or jsmin. "
                "Install with: pip install rjsmin",
                file=sys.stderr
            )
            sys.exit(1)


def _obfuscate_js_file(file_path: Path):
    """Obfuscate a JavaScript file using javascript-obfuscator if available."""
    import shutil
    import subprocess

    tool = shutil.which("javascript-obfuscator")
    if tool:
        cmd = [tool, str(file_path), "--output", str(file_path)]
    else:
        npx = shutil.which("npx")
        if not npx:
            print(
                "Error: --obfuscate requires javascript-obfuscator. "
                "Install with: npm i -g javascript-obfuscator",
                file=sys.stderr
            )
            sys.exit(1)
        cmd = [npx, "--no-install", "javascript-obfuscator", str(file_path), "--output", str(file_path)]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("Error: JavaScript obfuscation failed.", file=sys.stderr)
        if result.stderr:
            print(result.stderr.strip(), file=sys.stderr)
        sys.exit(1)


def run_build(
    filepath: str,
    target: str,
    output_dir: str,
    copy_assets: bool = False,
    enable_repl: bool = False,
    minify_js: bool = False,
    obfuscate_js: bool = False,
):
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
    from datetime import datetime
    from .lexer import Lexer
    from .parser import Parser
    from .ir_transformer import transform_ast_to_ir
    from .emitters.phaser import PhaserEmitter
    from .emitters.pygame import PygameEmitter
    from .emitters.threejs import ThreeJSEmitter
    from .emitters.godot import GodotEmitter
    from .errors import RoshError

    # Generate build timestamp (shared between Python output and JS)
    build_time = datetime.now().strftime('%H:%M:%S')

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

        # Validate JS-only flags
        if (minify_js or obfuscate_js) and target not in ('phaser', 'threejs'):
            print("Error: --minify/--obfuscate are only supported for Phaser and Three.js builds.", file=sys.stderr)
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
                canvas_height=meta.get('canvas', {}).get('height', 600),
                project_root=project_dir
            )
            # Pass asset directory for spritesheet frame dimension calculation
            asset_dir = Path(project_dir) / 'assets' if project_dir else None
            emitter = PhaserEmitter(ir, meta=meta, asset_dir=asset_dir)
            js_code = emitter.emit()

            # TODO: Add REPL support to IR emitter
            if enable_repl:
                print(f"Warning: --repl not yet supported with IR emitter", file=sys.stderr)

            if minify_js:
                js_code = _minify_js_code(js_code)

            generate_phaser_output(js_code, output_dir)

            # Copy assets if requested
            if copy_assets and emitter.sprite_assets:
                copy_sprite_assets(path, Path(output_dir), emitter.sprite_assets)

            if obfuscate_js:
                _obfuscate_js_file(Path(output_dir) / "game.js")

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
                canvas_height=meta.get('canvas', {}).get('height', 600),
                project_root=project_dir
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
                canvas_height=meta.get('canvas', {}).get('height', 600),
                meta=meta,
                project_root=project_dir
            )
            emitter = ThreeJSEmitter(ir, meta=meta)
            js_code = emitter.emit()
            if minify_js:
                js_code = _minify_js_code(js_code)
            generate_threejs_output(js_code, output_dir, emitter.capability_manifest)

            # Copy assets if requested
            if copy_assets and emitter.sprite_assets:
                copy_sprite_assets(path, Path(output_dir), emitter.sprite_assets)

            # Always copy 3D model assets if they exist (essential for scene)
            if emitter.model_assets:
                copy_model_assets(path, Path(output_dir), emitter.model_assets)

            if obfuscate_js:
                _obfuscate_js_file(Path(output_dir) / "game.js")

            print(f"✅ Build successful!", file=sys.stderr)
            print(f"📁 Output: {output_dir}", file=sys.stderr)
            print(f"🎮 To run:", file=sys.stderr)
            print(f"   cd {output_dir} && python3 -m http.server 8000", file=sys.stderr)
            print(f"   open http://localhost:8000", file=sys.stderr)

        elif target == 'godot':
            # Transform AST to IR, then emit Godot GDScript
            ir = transform_ast_to_ir(
                program,
                canvas_width=meta.get('canvas', {}).get('width', 800),
                canvas_height=meta.get('canvas', {}).get('height', 600),
                project_root=project_dir
            )
            emitter = GodotEmitter(ir, meta=meta)
            gd_code = emitter.emit()
            project_godot = emitter.emit_project_godot()
            main_tscn = emitter.emit_main_tscn()
            generate_godot_output(gd_code, project_godot, main_tscn, output_dir)

            # Copy assets if requested
            if copy_assets and emitter.sprite_assets:
                copy_sprite_assets(path, Path(output_dir), emitter.sprite_assets)

            print(f"✅ Build successful!", file=sys.stderr)
            print(f"📁 Output: {output_dir}", file=sys.stderr)
            print(f"🎮 To run:", file=sys.stderr)
            print(f"   Open in Godot 4.x: godot {output_dir}/project.godot", file=sys.stderr)

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

    # Inject build timestamp into JS
    from datetime import datetime
    build_time = datetime.now().strftime('%H:%M:%S')
    js_code = js_code.replace('__BUILD_TIME__', build_time)

    # Write game.js
    with open(output_path / "game.js", "w") as f:
        f.write(js_code)

    print(f"🕐 Build time: {build_time}", file=sys.stderr)

    # Copy HTML template
    template_dir = Path(__file__).parent / "emitters" / "templates"
    shutil.copy(template_dir / "phaser_index.html", output_path / "index.html")

    # Copy network module for multiplayer support
    static_dir = Path(__file__).parent.parent.parent / "static"
    network_js = static_dir / "rosh-network.js"
    if network_js.exists():
        shutil.copy(network_js, output_path / "rosh-network.js")

    # Copy shared objects module for cross-engine sync
    objects_js = static_dir / "rosh-objects.js"
    if objects_js.exists():
        shutil.copy(objects_js, output_path / "rosh-objects.js")

    # Create assets directory
    (output_path / "assets").mkdir(exist_ok=True)


def generate_pygame_output(py_code: str, output_dir: str):
    """Generate Pygame output files

    Creates:
    - game.py (generated Pygame code, executable)
    - rosh_network.py (network module for Project Twin)
    - assets/ (placeholder directory)

    Args:
        py_code: Generated Python code
        output_dir: Directory for output files
    """
    from pathlib import Path
    import shutil

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Write game.py
    with open(output_path / "game.py", "w") as f:
        f.write(py_code)

    # Copy network module for Project Twin multiplayer support
    static_dir = Path(__file__).parent.parent.parent / "static"
    network_py = static_dir / "rosh_network.py"
    if network_py.exists():
        shutil.copy(network_py, output_path / "rosh_network.py")

    # Create assets directory
    (output_path / "assets").mkdir(exist_ok=True)


def generate_godot_output(gd_code: str, project_godot: str, main_tscn: str, output_dir: str):
    """Generate Godot output files

    Creates:
    - project.godot (Godot project file)
    - main.tscn (main scene file)
    - main.gd (generated GDScript)
    - assets/ (placeholder directory)

    Args:
        gd_code: Generated GDScript code
        project_godot: project.godot content
        main_tscn: main.tscn content
        output_dir: Directory for output files
    """
    from pathlib import Path

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Write project.godot
    with open(output_path / "project.godot", "w") as f:
        f.write(project_godot)

    # Write main.tscn
    with open(output_path / "main.tscn", "w") as f:
        f.write(main_tscn)

    # Write main.gd
    with open(output_path / "main.gd", "w") as f:
        f.write(gd_code)

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

    # Inject build timestamp into JS
    from datetime import datetime
    build_time = datetime.now().strftime('%H:%M:%S')
    js_code = js_code.replace('__BUILD_TIME__', build_time)

    # Write game.js
    with open(output_path / "game.js", "w") as f:
        f.write(js_code)

    print(f"🕐 Build time: {build_time}", file=sys.stderr)

    # Copy HTML template
    template_dir = Path(__file__).parent / "emitters" / "templates"
    shutil.copy(template_dir / "threejs_index.html", output_path / "index.html")

    # Create assets directory
    (output_path / "assets").mkdir(exist_ok=True)

    # Write capability manifest if provided
    if capabilities:
        with open(output_path / "capabilities.json", "w") as f:
            json.dump(capabilities, f, indent=2)


def run_tests(filepath: str, verbose: bool = False, fail_fast: bool = False,
              filter_pattern: str = None, level: str = 'standard'):
    """Run Rosh spec tests from a .rosh test file.

    Test files use this syntax:
        section "core"

        test "create simple object"
            create box
            expect box exists
            expect box.color is "green"
        end
    """
    from .lexer import Lexer, TokenType
    from .parser import Parser
    from .interpreter import Interpreter

    # Read test file
    try:
        with open(filepath, 'r') as f:
            source = f.read()
    except FileNotFoundError:
        print(f"Error: Test file not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    # Parse the test file to extract tests
    tests = _parse_test_file(source)

    if not tests:
        print(f"No tests found in {filepath}")
        sys.exit(0)

    # Filter tests by section/level
    section_order = {'core': 0, 'standard': 1, 'full': 2}
    level_threshold = section_order.get(level, 1)
    filtered_tests = [
        t for t in tests
        if section_order.get(t.get('section', 'core'), 0) <= level_threshold
    ]

    # Filter by pattern if provided
    if filter_pattern:
        import fnmatch
        filtered_tests = [t for t in filtered_tests if fnmatch.fnmatch(t['name'], filter_pattern)]

    if not filtered_tests:
        print(f"No tests match level '{level}'" + (f" and pattern '{filter_pattern}'" if filter_pattern else ""))
        sys.exit(0)

    print(f"\nRunning: {filepath}")
    passed = 0
    failed = 0
    skipped = 0
    todo_ok = 0      # Expected failures that failed (good)
    todo_fail = 0    # Expected failures that passed (bad - needs attention)

    for test in filtered_tests:
        if test.get('skip'):
            if verbose:
                print(f"  - {test['name']} (skipped: {test['skip']})")
            skipped += 1
            continue

        # Voice tests require normalizer - auto-skip with warning until implemented
        if test.get('voice'):
            print(f"  - {test['name']} (skipped: voice normalizer not implemented)")
            skipped += 1
            continue

        # Run the test
        result = _run_single_test(test, verbose)
        is_todo = test.get('todo', False)

        if is_todo:
            # TODO test: expected to fail
            if result['passed']:
                # Unexpectedly passed - this needs attention
                print(f"  ! {test['name']} (todo: unexpectedly passed)")
                todo_fail += 1
            else:
                # Failed as expected
                if verbose:
                    print(f"  ~ {test['name']} (todo: expected failure)")
                else:
                    print(f"  ~ {test['name']}")
                todo_ok += 1
        elif result['passed']:
            print(f"  \u2713 {test['name']}")
            passed += 1
        else:
            print(f"  \u2717 {test['name']}")
            if result.get('error'):
                print(f"    Error: {result['error']}")
            if result.get('expected') and result.get('actual'):
                print(f"    Expected: {result['expected']}")
                print(f"    Actual:   {result['actual']}")
            failed += 1
            if fail_fast:
                break

    # Summary
    summary_parts = [f"{passed} passed", f"{failed} failed"]
    if skipped:
        summary_parts.append(f"{skipped} skipped")
    if todo_ok:
        summary_parts.append(f"{todo_ok} todo")
    if todo_fail:
        summary_parts.append(f"{todo_fail} todo-passed")
    print(f"\nResults: {', '.join(summary_parts)}")

    if failed > 0 or todo_fail > 0:
        sys.exit(1)


def _parse_test_file(source: str) -> list:
    """Parse a test file and extract test definitions.

    Returns list of test dicts:
        {
            'name': 'test name',
            'section': 'core',
            'commands': ['create box', 'set box x to 5'],
            'expects': [{'type': 'exists', 'target': 'box'}, ...],
            'skip': None or 'reason',
            'todo': False,
            'voice': False
        }
    """
    from .lexer import Lexer, TokenType

    # Use test_mode=True to enable test keywords without polluting user namespace
    lexer = Lexer(source, test_mode=True)
    tokens = lexer.tokenize()

    tests = []
    current_section = 'core'
    i = 0

    while i < len(tokens):
        token = tokens[i]

        # Skip newlines
        if token.type == TokenType.NEWLINE:
            i += 1
            continue

        # Section declaration
        if token.type == TokenType.SECTION:
            i += 1
            if i < len(tokens) and tokens[i].type == TokenType.STRING:
                current_section = tokens[i].value
            i += 1
            continue

        # Test declaration
        if token.type == TokenType.TEST:
            test = {
                'name': '',
                'section': current_section,
                'commands': [],
                'expects': [],
                'skip': None,
                'todo': False,
                'voice': False
            }

            i += 1

            # Test name (string)
            if i < len(tokens) and tokens[i].type == TokenType.STRING:
                test['name'] = tokens[i].value
                i += 1

            # Optional modifiers: skip, todo, with voice
            while i < len(tokens) and tokens[i].type not in (TokenType.NEWLINE, TokenType.EOF):
                if tokens[i].type == TokenType.SKIP:
                    i += 1
                    if i < len(tokens) and tokens[i].type == TokenType.STRING:
                        test['skip'] = tokens[i].value
                        i += 1
                elif tokens[i].type == TokenType.TODO:
                    test['todo'] = True
                    i += 1
                elif tokens[i].type == TokenType.WITH:
                    i += 1
                    if i < len(tokens) and tokens[i].type == TokenType.VOICE:
                        test['voice'] = True
                        i += 1
                elif tokens[i].type == TokenType.VOICE:
                    # Also support just "voice" without "with"
                    test['voice'] = True
                    i += 1
                else:
                    i += 1

            # Skip newline after test declaration
            while i < len(tokens) and tokens[i].type == TokenType.NEWLINE:
                i += 1

            # Parse test body until ENDTEST (allows nested end in test bodies)
            body_tokens = []
            while i < len(tokens) and tokens[i].type != TokenType.ENDTEST:
                body_tokens.append(tokens[i])
                i += 1

            # Parse body into commands and expects
            test['commands'], test['expects'] = _parse_test_body(body_tokens)

            # Skip ENDTEST token
            if i < len(tokens) and tokens[i].type == TokenType.ENDTEST:
                i += 1

            tests.append(test)
            continue

        i += 1

    return tests


def _parse_test_body(tokens: list) -> tuple:
    """Parse test body tokens into commands and expect statements."""
    from .lexer import TokenType

    commands = []
    expects = []
    i = 0

    while i < len(tokens):
        # Skip newlines
        if tokens[i].type == TokenType.NEWLINE:
            i += 1
            continue

        # Expect statement
        if tokens[i].type == TokenType.EXPECT:
            i += 1
            expect = {'type': 'unknown'}

            # Collect tokens until newline
            expect_tokens = []
            while i < len(tokens) and tokens[i].type != TokenType.NEWLINE:
                expect_tokens.append(tokens[i])
                i += 1

            if expect_tokens:
                expect = _parse_expect(expect_tokens)
            expects.append(expect)
            continue

        # Try statement (for error testing)
        if tokens[i].type == TokenType.TRY:
            i += 1
            # Collect command tokens until newline
            cmd_tokens = []
            while i < len(tokens) and tokens[i].type != TokenType.NEWLINE:
                cmd_tokens.append(tokens[i])
                i += 1
            if cmd_tokens:
                cmd_str = _tokens_to_string(cmd_tokens)
                commands.append({'cmd': cmd_str, 'try': True})
            continue

        # Regular command
        cmd_tokens = []
        while i < len(tokens) and tokens[i].type != TokenType.NEWLINE:
            cmd_tokens.append(tokens[i])
            i += 1
        if cmd_tokens:
            cmd_str = _tokens_to_string(cmd_tokens)
            commands.append({'cmd': cmd_str, 'try': False})

        i += 1

    return commands, expects


def _tokens_to_string(tokens: list) -> str:
    """Convert tokens back to string for execution."""
    from .lexer import TokenType

    result = []
    prev_was_dot = False

    for t in tokens:
        if t.type == TokenType.DOT:
            # Remove trailing space from previous token and add dot without space
            if result and result[-1] == ' ':
                result.pop()
            result.append('.')
            prev_was_dot = True
        elif t.value is not None:
            if prev_was_dot:
                # Don't add space after dot
                prev_was_dot = False
            elif result and result[-1] not in ('.', ' ', ''):
                result.append(' ')

            if t.type == TokenType.STRING:
                result.append(f'"{t.value}"')
            else:
                result.append(str(t.value))
        else:
            # Token with no value (like a keyword)
            if prev_was_dot:
                prev_was_dot = False
            elif result and result[-1] not in ('.', ' ', ''):
                result.append(' ')
            result.append(t.type.name.lower())

    return ''.join(result)


def _parse_expect(tokens: list) -> dict:
    """Parse expect tokens into an expect dict."""
    from .lexer import TokenType

    if not tokens:
        return {'type': 'unknown'}

    # expect <object> not exists (check FIRST before "exists")
    if len(tokens) >= 3 and tokens[-2].type == TokenType.NOT and tokens[-1].type == TokenType.EXISTS:
        return {
            'type': 'not_exists',
            'target': tokens[0].value if tokens[0].value else str(tokens[0].type.name)
        }

    # expect <object> exists
    if len(tokens) >= 2 and tokens[-1].type == TokenType.EXISTS:
        return {
            'type': 'exists',
            'target': tokens[0].value if tokens[0].value else str(tokens[0].type.name)
        }

    # expect <object>.<prop> is <value>
    # Look for IS token
    is_idx = None
    for idx, t in enumerate(tokens):
        if t.type == TokenType.IS:
            is_idx = idx
            break

    if is_idx is not None:
        # Target is everything before IS
        target_tokens = tokens[:is_idx]
        value_tokens = tokens[is_idx + 1:]

        target = _tokens_to_string(target_tokens)
        value = _tokens_to_string(value_tokens)

        # Track if value was quoted (for type coercion decision)
        # Quoted values like "True" or "42" should stay as strings
        was_quoted = value.startswith('"') and value.endswith('"')
        if was_quoted:
            value = value[1:-1]

        return {
            'type': 'equals',
            'target': target,
            'value': value,
            'quoted': was_quoted  # If True, skip type coercion
        }

    # expect error - check that last command produced an error
    if len(tokens) >= 1 and tokens[0].type == TokenType.ERROR:
        # expect error contains "message"
        if len(tokens) >= 2:
            # Look for CONTAINS or a string
            for idx, t in enumerate(tokens[1:], 1):
                if t.type == TokenType.STRING:
                    return {
                        'type': 'error_contains',
                        'pattern': t.value
                    }
        # Just "expect error" - any error is fine
        return {'type': 'error'}

    # expect no error
    if len(tokens) >= 2 and tokens[0].type == TokenType.NO and tokens[1].type == TokenType.ERROR:
        return {'type': 'no_error'}

    # expect no correction
    if len(tokens) >= 2 and tokens[0].type == TokenType.NO and tokens[1].type == TokenType.CORRECTION:
        return {'type': 'no_correction'}

    # expect correction "x" to "y"
    if len(tokens) >= 1 and tokens[0].type == TokenType.CORRECTION:
        # Find string values
        strings = [t.value for t in tokens if t.type == TokenType.STRING]
        if len(strings) >= 2:
            return {
                'type': 'correction',
                'from': strings[0],
                'to': strings[1]
            }

    return {'type': 'unknown', 'tokens': [t.value for t in tokens]}


def _run_single_test(test: dict, verbose: bool) -> dict:
    """Run a single test and return result."""
    from .interpreter import Interpreter
    from .lexer import Lexer
    from .parser import Parser

    result = {'passed': True}
    interpreter = Interpreter()
    last_error = None

    # Run commands
    for cmd_info in test['commands']:
        cmd = cmd_info['cmd']
        is_try = cmd_info['try']

        try:
            lexer = Lexer(cmd)
            tokens = lexer.tokenize()
            parser = Parser(tokens)
            ast = parser.parse()
            interpreter.execute(ast)
            last_error = None
        except Exception as e:
            last_error = str(e)
            if not is_try:
                result['passed'] = False
                result['error'] = f"Command failed: {cmd}\n{e}"
                return result

    # Check expects
    for expect in test['expects']:
        expect_result = _check_expect(expect, interpreter, last_error)
        if not expect_result['passed']:
            result['passed'] = False
            result['expected'] = expect_result.get('expected')
            result['actual'] = expect_result.get('actual')
            return result

    return result


def _check_expect(expect: dict, interpreter, last_error: str) -> dict:
    """Check a single expect statement against interpreter state."""
    from .values import RoshObject

    expect_type = expect.get('type')

    def get_var(name: str):
        """Get a variable from interpreter, returning None if not found."""
        try:
            return interpreter.global_env.get(name)
        except:
            return None

    if expect_type == 'exists':
        target = expect['target']
        obj = get_var(target)
        if obj is None:
            return {'passed': False, 'expected': f'{target} exists', 'actual': f'{target} not found'}
        return {'passed': True}

    if expect_type == 'not_exists':
        target = expect['target']
        obj = get_var(target)
        if obj is not None:
            return {'passed': False, 'expected': f'{target} not exists', 'actual': f'{target} exists'}
        return {'passed': True}

    if expect_type == 'equals':
        target = expect['target']
        expected_value = expect['value']

        # Parse target (object.property or object property)
        if '.' in target:
            parts = target.split('.')
            obj_name = parts[0]
            prop = '.'.join(parts[1:])
        else:
            parts = target.split()
            if len(parts) >= 2:
                obj_name = parts[0]
                prop = parts[1]
            else:
                obj_name = target
                prop = None

        obj = get_var(obj_name)
        if obj is None:
            return {'passed': False, 'expected': f'{target} is {expected_value}', 'actual': f'{obj_name} not found'}

        if prop:
            if isinstance(obj, RoshObject):
                actual_value = obj.get(prop)  # RoshObject uses .get() method
            else:
                actual_value = None
        else:
            actual_value = obj

        # Type-aware comparison
        def normalize_value(val):
            """Convert value to comparable form, preserving type info."""
            if val is None:
                return None, 'None'
            # Handle booleans (Python's bool is subclass of int)
            if isinstance(val, bool):
                return val, str(val)
            # Handle numbers
            if isinstance(val, (int, float)):
                return val, str(val)
            # Handle strings
            return str(val), str(val)

        def parse_expected(val_str):
            """Parse expected value string to typed value."""
            if val_str in ('True', 'true'):
                return True
            if val_str in ('False', 'false'):
                return False
            if val_str == 'None':
                return None
            # Try as number
            try:
                if '.' in val_str:
                    return float(val_str)
                return int(val_str)
            except (ValueError, TypeError):
                pass
            return val_str

        actual_typed, actual_str = normalize_value(actual_value)
        expected_str = str(expected_value)

        # If value was quoted, require actual value to BE a string (type check)
        # This ensures `expect x is "42"` fails if x is integer 42
        was_quoted = expect.get('quoted', False)
        if was_quoted:
            # Quoted means: actual must be a string AND match the expected string
            if not isinstance(actual_value, str):
                actual_type = type(actual_value).__name__
                return {'passed': False, 'expected': f'{target} is "{expected_str}" (string)', 'actual': f'{target} is {actual_str} ({actual_type})'}
            if actual_value != expected_value:
                return {'passed': False, 'expected': f'{target} is "{expected_str}"', 'actual': f'{target} is "{actual_str}"'}
        else:
            # Type-aware comparison for unquoted values
            expected_typed = parse_expected(expected_value)
            if actual_typed != expected_typed:
                return {'passed': False, 'expected': f'{target} is {expected_str}', 'actual': f'{target} is {actual_str}'}

        return {'passed': True}

    if expect_type == 'error':
        # Expect an error occurred
        # TODO: When interpreter moves to error-stack semantics (Go-style .error property),
        # wire last_error to interpreter.error_stack or equivalent state instead of
        # relying solely on Python exceptions. See ROSH-SPEC-FORMALIZATION.md.
        if last_error is None:
            return {'passed': False, 'expected': 'an error', 'actual': 'no error'}
        return {'passed': True}

    if expect_type == 'error_contains':
        # Expect error message contains a pattern
        # TODO: Same error-stack integration needed here
        pattern = expect.get('pattern', '')
        if last_error is None:
            return {'passed': False, 'expected': f'error containing "{pattern}"', 'actual': 'no error'}
        if pattern not in last_error:
            return {'passed': False, 'expected': f'error containing "{pattern}"', 'actual': f'error: {last_error}'}
        return {'passed': True}

    if expect_type == 'no_error':
        # Expect no error occurred
        if last_error is not None:
            return {'passed': False, 'expected': 'no error', 'actual': f'error: {last_error}'}
        return {'passed': True}

    if expect_type == 'no_correction':
        # TODO: Implement correction tracking
        return {'passed': True}

    if expect_type == 'correction':
        # TODO: Implement correction tracking
        return {'passed': True}

    # Unknown expect type
    return {'passed': True}


def main():
    """Main entry point for the Rosh CLI"""
    parser = argparse.ArgumentParser(
        description="Rosh - A spoken-language-first programming language",
        prog="rosh"
    )

    # Check if using subcommand (peek at args)
    import sys
    using_subcommand = len(sys.argv) > 1 and sys.argv[1] in ('build', 'test')

    if using_subcommand:
        # Add subparsers for commands
        subparsers = parser.add_subparsers(dest='subcommand', help='Commands')

        # Build subcommand
        build_parser = subparsers.add_parser('build', help='Transpile Rosh code to target platform')
        build_parser.add_argument('file', help='Rosh file to transpile')
        build_parser.add_argument('--target', required=True, choices=['phaser', 'pygame', 'threejs', 'godot'],
                                  help='Target platform (phaser, pygame, threejs, godot)')
        build_parser.add_argument('--output', default='dist/',
                                  help='Output directory (default: dist/)')
        build_parser.add_argument('--copy-assets', action='store_true',
                                  help='Automatically copy required sprite assets to output')
        build_parser.add_argument('--repl', action='store_true',
                                  help='🔧 DEV MODE: Enable in-game REPL (press ` or F12 to toggle console)')
        build_parser.add_argument('--minify', action='store_true',
                                  help='Minify JavaScript output (Phaser/Three.js only)')
        build_parser.add_argument('--obfuscate', action='store_true',
                                  help='Obfuscate JavaScript output (Phaser/Three.js only)')

        # Test subcommand
        test_parser = subparsers.add_parser('test', help='Run Rosh spec tests')
        test_parser.add_argument('file', help='Test file (.rosh) to run')
        test_parser.add_argument('-v', '--verbose', action='store_true',
                                 help='Verbose output (show all test details)')
        test_parser.add_argument('--fail-fast', action='store_true',
                                 help='Stop on first test failure')
        test_parser.add_argument('--filter', metavar='PATTERN',
                                 help='Only run tests matching pattern')
        test_parser.add_argument('--level', choices=['core', 'standard', 'full'],
                                 default='standard',
                                 help='Compliance level to check (default: standard)')

        # Note: Project Twin is now integrated into the REPL via 'connect <world>' command
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
        run_build(
            args.file,
            args.target,
            args.output,
            copy_assets,
            enable_repl,
            minify_js=getattr(args, 'minify', False),
            obfuscate_js=getattr(args, 'obfuscate', False),
        )
        return

    # Handle test subcommand
    if hasattr(args, 'subcommand') and args.subcommand == 'test':
        run_tests(
            args.file,
            verbose=args.verbose,
            fail_fast=args.fail_fast,
            filter_pattern=args.filter,
            level=args.level
        )
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
