"""
Rosh Command Definitions - SINGLE SOURCE OF TRUTH

This file defines all REPL commands and their aliases.
Both Python CLI and JS runtime are generated/validated from this.

DO NOT add commands to cli.py or JS files directly.
Add them here, then regenerate.

Usage:
    python -m rosh.emitters.runtime_js  # Generate JS command routing
    python -m rosh.commands --check     # Validate Python/JS match
"""

from dataclasses import dataclass, field
from typing import List, Optional

# =============================================================================
# Command Definitions
# =============================================================================

@dataclass
class Command:
    """A REPL command with its aliases and metadata."""
    name: str                          # Primary command name
    aliases: List[str] = field(default_factory=list)  # Alternative names
    needs_arg: bool = True             # Does it require an argument?
    arg_style: str = "array"           # "array", "single", "joined", "cmd_array"
    js_handler: str = ""               # JS method name (default: cmd{Name})
    layer: str = "3d"                  # Which layer: "core", "3d", or "adapter"
    description: str = ""              # Help text

    @property
    def all_names(self) -> List[str]:
        """All names including primary and aliases."""
        return [self.name] + self.aliases

    @property
    def handler_name(self) -> str:
        """JS handler method name."""
        if self.js_handler:
            return self.js_handler
        return f"cmd{self.name.capitalize()}"


# =============================================================================
# REPL Commands - Add new commands HERE
# =============================================================================

COMMANDS = [
    # --- Core Layer (rosh-core.js) ---
    Command("help", [], needs_arg=False, arg_style="array", layer="core"),
    Command("version", [], needs_arg=False, arg_style="none", layer="core"),
    Command("undo", ["oops"], needs_arg=False, arg_style="none", layer="core"),
    Command("redo", [], needs_arg=False, arg_style="none", layer="core"),
    Command("credits", [], needs_arg=False, arg_style="none", layer="core"),
    Command("meta", [], needs_arg=True, arg_style="array", layer="core",
            description="System settings (quiet, floor, grid, etc.)"),

    # --- 3D Layer (rosh-3d.js) ---
    # Object listing
    Command("list", ["ls", "objects"], needs_arg=False, arg_style="array", layer="3d"),

    # Object inspection - takes joined string "parts.slice(1).join(' ')"
    Command("look", ["l", "examine", "inspect", "x", "ex", "dump", "properties", "props"],
            needs_arg=False, arg_style="joined", layer="3d",
            description="Examine object properties"),

    # Object creation/deletion
    Command("create", [], arg_style="cmd_array", layer="3d"),  # (cmd, parts.slice(1))
    Command("delete", ["remove"], arg_style="array", layer="3d"),
    Command("clone", ["copy", "duplicate"], arg_style="joined", layer="3d"),  # joined string

    # Property manipulation
    Command("set", [], arg_style="cmd_array", layer="3d"),  # (cmd, parts.slice(1))
    Command("get", [], arg_style="array", layer="3d"),

    # Visibility - take single string (parts[1])
    Command("hide", [], arg_style="single", layer="3d"),
    Command("show", [], arg_style="single", layer="3d"),

    # Natural language
    Command("make", [], arg_style="cmd_array", layer="3d", description="Natural language modifications"),
    Command("move", [], arg_style="cmd_array", layer="3d", description="Move object to position"),

    # Counting - takes single string
    Command("count", [], arg_style="single", layer="3d"),
]


# =============================================================================
# Helper Functions
# =============================================================================

def get_commands_by_layer(layer: str) -> List[Command]:
    """Get all commands for a specific layer."""
    return [c for c in COMMANDS if c.layer == layer]


def get_all_command_names() -> List[str]:
    """Get all command names including aliases."""
    names = []
    for cmd in COMMANDS:
        names.extend(cmd.all_names)
    return sorted(set(names))


def find_command(name: str) -> Optional[Command]:
    """Find command by name or alias."""
    name = name.lower()
    for cmd in COMMANDS:
        if name in cmd.all_names:
            return cmd
    return None


# =============================================================================
# Validation
# =============================================================================

def check_js_sync(js_path: str, layer: Optional[str] = None) -> List[str]:
    """Check if JS file has all required commands. Returns list of missing.

    Args:
        js_path: Path to the JS file
        layer: If specified, only check commands for this layer
    """
    import re

    with open(js_path, 'r') as f:
        js_content = f.read()

    # Determine which commands to check
    if layer:
        commands_to_check = get_commands_by_layer(layer)
    else:
        commands_to_check = COMMANDS

    missing = []
    for cmd in commands_to_check:
        for name in cmd.all_names:
            # Look for parts[0] === 'name' pattern
            pattern = rf"parts\[0\] === '{name}'"
            if not re.search(pattern, js_content):
                missing.append(name)

    return missing


if __name__ == "__main__":
    import sys

    if "--check" in sys.argv:
        # Check sync with JS files (layer-specific)
        js_files = [
            ("src/rosh/runtime/rosh-core.js", "core"),
            ("src/rosh/runtime/rosh-3d.js", "3d"),
            ("src/rosh/runtime/rosh-runtime.js", None),  # All commands
        ]

        all_ok = True
        for js_file, layer in js_files:
            try:
                missing = check_js_sync(js_file, layer)
                if missing:
                    layer_str = f" [{layer}]" if layer else ""
                    print(f"MISSING in {js_file}{layer_str}: {', '.join(missing)}")
                    all_ok = False
                else:
                    print(f"OK: {js_file}")
            except FileNotFoundError:
                print(f"NOT FOUND: {js_file}")

        sys.exit(0 if all_ok else 1)
    else:
        # Print all commands
        print("Rosh Commands:")
        for cmd in COMMANDS:
            aliases = f" (aliases: {', '.join(cmd.aliases)})" if cmd.aliases else ""
            print(f"  {cmd.name}{aliases} [{cmd.layer}]")
