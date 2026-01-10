"""
Spec Compliance Tests

Ensures that all command definitions come from the spec file
and that the spec is the single source of truth.
"""

import sys
from pathlib import Path

# Add parent directory to path to import rosh
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from rosh.spec import get_all_commands, get_command
from rosh.spec.loader import SPEC_VERSION
from rosh.commands import COMMANDS, find_command


class TestSpecLoading:
    """Test that spec loads correctly."""

    def test_spec_loads(self):
        """Spec file loads without error."""
        commands = get_all_commands()
        assert len(commands) > 0, "No commands loaded from spec"

    def test_spec_version(self):
        """Spec version is 0.3.0."""
        assert SPEC_VERSION == "0.3.0"

    def test_core_commands_present(self):
        """Core commands are in spec."""
        commands = get_all_commands()
        core_commands = ["help", "version", "undo", "redo"]
        for cmd in core_commands:
            assert cmd in commands, f"Missing core command: {cmd}"

    def test_3d_commands_present(self):
        """3D commands are in spec."""
        commands = get_all_commands()
        commands_3d = ["create", "delete", "set", "get", "look", "list"]
        for cmd in commands_3d:
            assert cmd in commands, f"Missing 3D command: {cmd}"


class TestCommandsModule:
    """Test that commands.py loads from spec."""

    def test_commands_loaded(self):
        """Commands list is populated."""
        assert len(COMMANDS) > 0, "No commands loaded"

    def test_commands_match_spec(self):
        """Commands module has same commands as spec."""
        spec_commands = set(get_all_commands().keys())
        module_commands = set(cmd.name for cmd in COMMANDS)
        assert spec_commands == module_commands, (
            f"Mismatch: spec={spec_commands}, module={module_commands}"
        )

    def test_aliases_work(self):
        """Aliases resolve to canonical command."""
        # Test some known aliases
        aliases = [
            ("ver", "version"),
            ("oops", "undo"),
            ("ls", "list"),
            ("l", "look"),
            ("remove", "delete"),
        ]
        for alias, canonical in aliases:
            cmd = find_command(alias)
            assert cmd is not None, f"Alias '{alias}' not found"
            assert cmd.name == canonical, (
                f"Alias '{alias}' resolved to '{cmd.name}', expected '{canonical}'"
            )

    def test_typos_resolve(self):
        """Typos resolve to canonical command."""
        typos = [
            ("creat", "create"),
            ("delte", "delete"),
            ("lok", "look"),
        ]
        for typo, canonical in typos:
            spec_cmd = get_command(typo)
            assert spec_cmd is not None, f"Typo '{typo}' not found"
            assert spec_cmd.canonical == canonical, (
                f"Typo '{typo}' resolved to '{spec_cmd.canonical}', expected '{canonical}'"
            )


class TestSpecStructure:
    """Test spec file structure."""

    def test_all_commands_have_layer(self):
        """All commands have a layer defined."""
        for name, cmd in get_all_commands().items():
            assert cmd.layer in ("core", "3d"), (
                f"Command '{name}' has invalid layer: {cmd.layer}"
            )

    def test_all_commands_have_arg_style(self):
        """All commands have an arg_style defined."""
        valid_styles = ("none", "single", "array", "joined", "cmd_array")
        for name, cmd in get_all_commands().items():
            assert cmd.arg_style in valid_styles, (
                f"Command '{name}' has invalid arg_style: {cmd.arg_style}"
            )


class TestSingleSourceOfTruth:
    """Test that spec is the single source of truth."""

    def test_adding_command_to_spec_appears_in_module(self):
        """
        This test documents the expected behavior:
        If you add a command to rosh-spec.toml, it should automatically
        appear in the commands module without any code changes.

        We can't test this dynamically, but we can verify the mechanism works
        by checking that the module loads from spec.
        """
        # Verify commands are loaded dynamically
        from rosh import commands
        assert hasattr(commands, '_load_commands'), "Missing _load_commands function"
        assert hasattr(commands, 'COMMANDS'), "Missing COMMANDS list"

        # Verify COMMANDS is the result of loading from spec
        spec_count = len(get_all_commands())
        module_count = len(COMMANDS)
        assert spec_count == module_count, (
            f"Spec has {spec_count} commands, module has {module_count}"
        )
