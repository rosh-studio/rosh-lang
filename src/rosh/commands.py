"""
Rosh Command Definitions - Loaded from Spec

Commands are defined in spec/v0.3.0/rosh-spec.toml (SINGLE SOURCE OF TRUTH).
This module loads them and provides the Command dataclass for compatibility.

DO NOT add commands here. Add them to the spec file.
"""

from dataclasses import dataclass, field
from typing import List, Optional

from rosh.spec import get_all_commands, get_command as spec_get_command, CommandSpec


# =============================================================================
# Command Dataclass (for compatibility with existing code)
# =============================================================================

@dataclass
class Command:
    """A REPL command with its aliases and metadata."""
    name: str
    aliases: List[str] = field(default_factory=list)
    needs_arg: bool = True
    arg_style: str = "array"  # "array", "single", "joined", "cmd_array", "none"
    js_handler: str = ""
    layer: str = "3d"
    description: str = ""

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
# Load Commands from Spec
# =============================================================================

def _spec_to_command(spec_cmd: CommandSpec) -> Command:
    """Convert a CommandSpec to a Command for compatibility."""
    return Command(
        name=spec_cmd.canonical,
        aliases=spec_cmd.aliases,
        needs_arg=spec_cmd.arg_style not in ("none",),
        arg_style=spec_cmd.arg_style,
        layer=spec_cmd.layer,
        description=spec_cmd.description,
    )


def _load_commands() -> List[Command]:
    """Load all commands from the spec."""
    spec_cmds = get_all_commands()
    return [_spec_to_command(cmd) for cmd in spec_cmds.values()]


# Commands list - loaded from spec
COMMANDS = _load_commands()


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
    spec_cmd = spec_get_command(name)
    if spec_cmd:
        return _spec_to_command(spec_cmd)
    return None


# =============================================================================
# CLI (for debugging)
# =============================================================================

if __name__ == "__main__":
    print("Rosh Commands (loaded from spec):")
    for cmd in COMMANDS:
        aliases = f" (aliases: {', '.join(cmd.aliases)})" if cmd.aliases else ""
        print(f"  {cmd.name}{aliases} [{cmd.layer}]")
