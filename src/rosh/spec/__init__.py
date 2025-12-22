"""
Rosh Specification Loader

Load and validate TOML specs for the Rosh language.

Usage:
    from rosh.spec import load_spec, get_command, get_all_commands

    spec = load_spec("cli")
    cmd = get_command("create")
    print(cmd.canonical, cmd.aliases, cmd.typos)
"""

from .loader import (
    load_spec,
    get_command,
    get_all_commands,
    get_commands_by_layer,
    SpecVersion,
    CommandSpec,
)

__all__ = [
    "load_spec",
    "get_command",
    "get_all_commands",
    "get_commands_by_layer",
    "SpecVersion",
    "CommandSpec",
]
