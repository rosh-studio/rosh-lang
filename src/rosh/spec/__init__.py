"""
Rosh Specification Loader

Load and validate TOML specs for the Rosh language.

Usage:
    from rosh.spec import load_spec, get_command, get_all_commands
    from rosh.spec import get_colors, get_sizes, get_object_types

    spec = load_spec("spec")
    cmd = get_command("create")
    colors = get_colors()  # {"red": 0xff0000, ...}
"""

from .loader import (
    load_spec,
    get_command,
    get_all_commands,
    get_commands_by_layer,
    get_colors,
    get_sizes,
    get_object_types,
    get_repl_commands,
    get_protocol,
    get_properties,
    SpecVersion,
    CommandSpec,
    SPEC_VERSION,
)

__all__ = [
    "load_spec",
    "get_command",
    "get_all_commands",
    "get_commands_by_layer",
    "get_colors",
    "get_sizes",
    "get_object_types",
    "get_repl_commands",
    "get_protocol",
    "get_properties",
    "SpecVersion",
    "CommandSpec",
    "SPEC_VERSION",
]
