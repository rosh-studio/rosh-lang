"""
Spec Compliance Tests

Ensures that all command definitions come from the spec file
and that the spec is the single source of truth.
"""

import sys
from pathlib import Path

# Add parent directory to path to import rosh
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from rosh.spec import (
    get_all_commands, get_command, get_colors, get_sizes,
    get_object_types, get_repl_commands, get_protocol, get_properties
)
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


class TestColorsSpec:
    """Test colors defined in spec."""

    def test_colors_loaded(self):
        """Colors section loads from spec."""
        colors = get_colors()
        assert len(colors) > 0, "No colors loaded from spec"

    def test_core_colors_present(self):
        """Core colors are defined."""
        colors = get_colors()
        core_colors = ["red", "green", "blue", "yellow", "white", "black"]
        for color in core_colors:
            assert color in colors, f"Missing core color: {color}"

    def test_colors_are_hex_values(self):
        """All colors are valid hex values."""
        colors = get_colors()
        for name, value in colors.items():
            assert isinstance(value, int), f"Color '{name}' is not an int: {value}"
            assert 0 <= value <= 0xffffff, f"Color '{name}' out of range: {value}"


class TestSizesSpec:
    """Test sizes defined in spec."""

    def test_sizes_loaded(self):
        """Sizes section loads from spec."""
        sizes = get_sizes()
        assert len(sizes) > 0, "No sizes loaded from spec"

    def test_core_sizes_present(self):
        """Core sizes are defined."""
        sizes = get_sizes()
        core_sizes = ["tiny", "small", "medium", "big", "large", "huge"]
        for size in core_sizes:
            assert size in sizes, f"Missing core size: {size}"

    def test_sizes_are_numeric(self):
        """All sizes are positive numbers."""
        sizes = get_sizes()
        for name, value in sizes.items():
            assert isinstance(value, (int, float)), f"Size '{name}' is not numeric: {value}"
            assert value > 0, f"Size '{name}' must be positive: {value}"


class TestObjectTypesSpec:
    """Test object types defined in spec."""

    def test_object_types_loaded(self):
        """Object types section loads from spec."""
        types = get_object_types()
        assert len(types) > 0, "No object types loaded from spec"

    def test_primitives_present(self):
        """Primitive object types are defined."""
        types = get_object_types()
        assert "primitives" in types, "Missing primitives list"
        primitives = types["primitives"]
        assert "cube" in primitives, "Missing cube primitive"
        assert "sphere" in primitives, "Missing sphere primitive"

    def test_type_aliases_defined(self):
        """Object type aliases are defined."""
        types = get_object_types()
        assert "aliases" in types, "Missing type aliases"
        aliases = types["aliases"]
        assert aliases.get("box") == "cube", "box should alias to cube"
        assert aliases.get("ball") == "sphere", "ball should alias to sphere"


class TestReplCommandsSpec:
    """Test REPL commands defined in spec."""

    def test_repl_commands_loaded(self):
        """REPL commands section loads from spec."""
        repl = get_repl_commands()
        assert len(repl) > 0, "No REPL commands loaded from spec"

    def test_twin_command_defined(self):
        """twin command is defined in REPL spec."""
        repl = get_repl_commands()
        assert "twin" in repl, "Missing twin REPL command"
        twin = repl["twin"]
        assert "connect" in twin.get("aliases", []), "twin should have connect alias"

    def test_disconnect_command_defined(self):
        """disconnect command is defined in REPL spec."""
        repl = get_repl_commands()
        assert "disconnect" in repl, "Missing disconnect REPL command"


class TestProtocolSpec:
    """Test network protocol defined in spec."""

    def test_protocol_loaded(self):
        """Protocol section loads from spec."""
        protocol = get_protocol()
        assert len(protocol) > 0, "No protocol loaded from spec"

    def test_client_messages_defined(self):
        """Client messages are defined."""
        protocol = get_protocol()
        assert "client_messages" in protocol, "Missing client_messages"
        client = protocol["client_messages"]
        assert "REQUEST_CREATE" in client, "Missing REQUEST_CREATE"
        assert "REQUEST_MOVE" in client, "Missing REQUEST_MOVE"
        assert "REQUEST_DELETE" in client, "Missing REQUEST_DELETE"

    def test_server_messages_defined(self):
        """Server messages are defined."""
        protocol = get_protocol()
        assert "server_messages" in protocol, "Missing server_messages"
        server = protocol["server_messages"]
        assert "CONFIRMED_CREATE" in server, "Missing CONFIRMED_CREATE"
        assert "REJECTED" in server, "Missing REJECTED"
        assert "CONNECTED" in server, "Missing CONNECTED"


class TestPropertiesSpec:
    """Test object properties defined in spec."""

    def test_properties_loaded(self):
        """Properties section loads from spec."""
        props = get_properties()
        assert len(props) > 0, "No properties loaded from spec"

    def test_transform_properties(self):
        """Transform properties are defined."""
        props = get_properties()
        assert "transform" in props, "Missing transform properties"
        transform = props["transform"]
        assert "position" in transform, "Missing position property"
        assert "rotation" in transform, "Missing rotation property"
        assert "scale" in transform, "Missing scale property"

    def test_animation_properties(self):
        """Animation properties are defined."""
        props = get_properties()
        assert "animation" in props, "Missing animation properties"
        animation = props["animation"]
        assert "spin" in animation, "Missing spin property"
        assert "pulse" in animation, "Missing pulse property"
