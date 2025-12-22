"""
JS Runtime Generator

Generates JavaScript command routing from the canonical command definitions.
This ensures Python CLI and JS runtime always have matching commands.

Usage:
    python -m rosh.emitters.runtime_js              # Print generated code
    python -m rosh.emitters.runtime_js --apply      # Update JS files in place
    python -m rosh.emitters.runtime_js --check      # Check if files need update

The generator produces command routing code blocks that can be inserted into:
    - src/rosh/runtime/rosh-core.js (core layer commands)
    - src/rosh/runtime/rosh-3d.js (3D layer commands)
    - src/rosh/runtime/rosh-runtime.js (standalone fallback)
"""

import sys
import re
from pathlib import Path
from datetime import datetime

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from rosh.commands import COMMANDS, get_commands_by_layer, Command


# =============================================================================
# Code Generation
# =============================================================================

def generate_condition(cmd: Command) -> str:
    """Generate the if/else-if condition for a command."""
    names = cmd.all_names
    if len(names) == 1:
        return f"parts[0] === '{names[0]}'"
    else:
        conditions = " || ".join(f"parts[0] === '{n}'" for n in names)
        return conditions


def generate_routing_block(commands: list, indent: str = "                ", fallback: str = "error") -> str:
    """Generate the command routing if/else-if block.

    Args:
        commands: List of Command objects
        indent: Indentation string
        fallback: What to do for unknown commands:
            - "error": Show error message
            - "delegate": Call this.execObjectCommand(cmd, parts)
            - "none": No else block
    """
    lines = []

    for i, cmd in enumerate(commands):
        condition = generate_condition(cmd)
        keyword = "if" if i == 0 else "} else if"

        # Generate the handler call based on arg_style
        handler = cmd.handler_name

        # Special cases for core commands
        if cmd.name == "undo":
            call = "const count = parseInt(parts[1]) || 1; this.performUndo(count);"
        elif cmd.name == "redo":
            call = "const count = parseInt(parts[1]) || 1; this.performRedo(count);"
        elif cmd.name == "version":
            call = "this.log('Rosh v' + ROSH_CORE_VERSION + ' (IR ' + IMPLEMENTS_IR_VERSION + ')', 'cyan');"
        elif cmd.name == "credits":
            call = "this.cmdCredits();"
        # Generate based on arg_style
        elif cmd.arg_style == "joined":
            call = f"this.{handler}(parts.slice(1).join(' '));"
        elif cmd.arg_style == "cmd_array":
            call = f"this.{handler}(cmd, parts.slice(1));"
        elif cmd.arg_style == "single":
            call = f"this.{handler}(parts[1]);"
        elif cmd.arg_style == "array":
            call = f"this.{handler}(parts.slice(1));"
        else:  # "none" or default
            call = f"this.{handler}();"

        lines.append(f"{indent}{keyword} ({condition}) {{")
        for call_line in call.split('\n'):
            lines.append(f"{indent}    {call_line}")

    # Add fallback
    if fallback == "error":
        lines.append(f"{indent}}} else {{")
        lines.append(f"{indent}    this.log('Unknown command: ' + parts[0] + \". Type 'help' for commands.\", 'err');")
        lines.append(f"{indent}}}")
    elif fallback == "delegate":
        lines.append(f"{indent}}} else {{")
        lines.append(f"{indent}    this.execObjectCommand(cmd, parts);")
        lines.append(f"{indent}}}")
    else:
        lines.append(f"{indent}}}")

    return '\n'.join(lines)


def generate_core_routing() -> str:
    """Generate routing for core layer (rosh-core.js)."""
    commands = get_commands_by_layer("core")
    # Core layer delegates unknown commands to subclass
    return generate_routing_block(commands, fallback="delegate")


def generate_3d_routing() -> str:
    """Generate routing for 3D layer (rosh-3d.js)."""
    commands = get_commands_by_layer("3d")
    return generate_routing_block(commands, indent="        ")


def generate_standalone_routing() -> str:
    """Generate routing for standalone runtime (all commands)."""
    return generate_routing_block(COMMANDS)


# =============================================================================
# File Operations
# =============================================================================

GENERATED_MARKER_START = "// === GENERATED COMMAND ROUTING START ==="
GENERATED_MARKER_END = "// === GENERATED COMMAND ROUTING END ==="


def update_file(filepath: str, new_routing: str, dry_run: bool = True) -> bool:
    """Update a JS file with new routing code. Returns True if changed."""
    path = Path(filepath)
    if not path.exists():
        print(f"File not found: {filepath}")
        return False

    content = path.read_text()

    # Check if markers exist
    if GENERATED_MARKER_START not in content:
        print(f"No generation markers in {filepath}")
        print(f"Add these markers around the command routing:")
        print(f"  {GENERATED_MARKER_START}")
        print(f"  ... routing code ...")
        print(f"  {GENERATED_MARKER_END}")
        return False

    # Extract and replace
    pattern = re.compile(
        re.escape(GENERATED_MARKER_START) + r'.*?' + re.escape(GENERATED_MARKER_END),
        re.DOTALL
    )

    new_block = f"{GENERATED_MARKER_START}\n{new_routing}\n{GENERATED_MARKER_END}"
    new_content = pattern.sub(new_block, content)

    if new_content == content:
        print(f"No changes needed: {filepath}")
        return False

    if dry_run:
        print(f"Would update: {filepath}")
        print("--- New routing ---")
        print(new_routing)
        print("-------------------")
    else:
        path.write_text(new_content)
        print(f"Updated: {filepath}")

    return True


# =============================================================================
# Main
# =============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate JS command routing")
    parser.add_argument("--apply", action="store_true", help="Update JS files in place")
    parser.add_argument("--check", action="store_true", help="Check if files need update")
    parser.add_argument("--core", action="store_true", help="Show core routing only")
    parser.add_argument("--3d", dest="layer_3d", action="store_true", help="Show 3D routing only")
    args = parser.parse_args()

    if args.core:
        print("// Core layer routing (rosh-core.js)")
        print(generate_core_routing())
    elif args.layer_3d:
        print("// 3D layer routing (rosh-3d.js)")
        print(generate_3d_routing())
    elif args.apply or args.check:
        # Update actual files
        base = Path(__file__).parent.parent / "runtime"
        files = [
            (base / "rosh-core.js", generate_core_routing()),
            (base / "rosh-3d.js", generate_3d_routing()),
            (base / "rosh-runtime.js", generate_standalone_routing()),
        ]

        changed = False
        for filepath, routing in files:
            if update_file(str(filepath), routing, dry_run=not args.apply):
                changed = True

        if args.check and changed:
            print("\nFiles need regeneration. Run with --apply to update.")
            sys.exit(1)
    else:
        # Print all routing
        print("// === CORE LAYER (rosh-core.js) ===")
        print(generate_core_routing())
        print()
        print("// === 3D LAYER (rosh-3d.js) ===")
        print(generate_3d_routing())
        print()
        print("// === STANDALONE (rosh-runtime.js) ===")
        print(generate_standalone_routing())
        print()
        print(f"// Generated: {datetime.now().isoformat()}")
        print("// Run with --apply to update JS files")


if __name__ == "__main__":
    main()
