"""
Rosh Specification Loader

Load TOML spec files and provide structured access to command definitions.

WARNING: Rosh is experimental. This implementation may change.
"""

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any

# Spec version
SPEC_VERSION = "0.2.0"

# Default spec directory
SPEC_DIR = Path(__file__).parent.parent.parent.parent / "spec" / f"v{SPEC_VERSION}"


@dataclass
class CommandSpec:
    """Specification for a single command."""
    canonical: str
    aliases: List[str] = field(default_factory=list)
    typos: List[str] = field(default_factory=list)
    syntax: str = ""
    arg_style: str = "array"  # "array", "single", "joined", "cmd_array", "none"
    layer: str = "3d"
    description: str = ""
    behavior: Dict[str, Any] = field(default_factory=dict)
    examples: Dict[str, Any] = field(default_factory=dict)
    inference: Dict[str, Any] = field(default_factory=dict)
    modifiers: Dict[str, Any] = field(default_factory=dict)
    spellings: Dict[str, str] = field(default_factory=dict)

    @property
    def all_names(self) -> List[str]:
        """All valid names for this command (canonical + aliases)."""
        return [self.canonical] + self.aliases

    @property
    def all_corrections(self) -> Dict[str, str]:
        """Map of typos/spellings to canonical form."""
        corrections = {typo: self.canonical for typo in self.typos}
        corrections.update(self.spellings)
        return corrections


@dataclass
class SpecVersion:
    """Metadata about a spec file."""
    version: str
    description: str
    status: str = "draft"
    experimental: bool = True
    experimental_warning: str = ""


class SpecLoader:
    """Load and cache spec files."""

    def __init__(self, spec_dir: Path = None):
        self.spec_dir = spec_dir or SPEC_DIR
        self._cache: Dict[str, Dict] = {}
        self._commands: Dict[str, CommandSpec] = {}

    def load(self, spec_name: str) -> Dict:
        """Load a spec file by name (e.g., 'cli' → 'rosh-cli.toml')."""
        if spec_name in self._cache:
            return self._cache[spec_name]

        filename = f"rosh-{spec_name}.toml"
        filepath = self.spec_dir / filename

        if not filepath.exists():
            raise FileNotFoundError(f"Spec file not found: {filepath}")

        with open(filepath, "rb") as f:
            data = tomllib.load(f)

        self._cache[spec_name] = data
        self._parse_commands(data)

        return data

    def _parse_commands(self, data: Dict):
        """Parse command definitions from spec data."""
        commands_data = data.get("commands", {})

        for name, cmd_data in commands_data.items():
            if not isinstance(cmd_data, dict):
                continue

            # Extract main fields
            spec = CommandSpec(
                canonical=cmd_data.get("canonical", name),
                aliases=cmd_data.get("aliases", []),
                typos=cmd_data.get("typos", []),
                syntax=cmd_data.get("syntax", ""),
                arg_style=cmd_data.get("arg_style", "array"),
                layer=cmd_data.get("layer", "3d"),
                description=cmd_data.get("description", ""),
            )

            # Extract nested sections
            for key in ["behavior", "examples", "inference", "modifiers", "spellings"]:
                if key in cmd_data:
                    setattr(spec, key, cmd_data[key])

            self._commands[name] = spec

            # Also index by aliases
            for alias in spec.aliases:
                if alias not in self._commands:
                    self._commands[alias] = spec

    def get_command(self, name: str) -> Optional[CommandSpec]:
        """Get command spec by name or alias."""
        name = name.lower()

        # Check direct lookup
        if name in self._commands:
            return self._commands[name]

        # Check if it's a typo
        for cmd in self._commands.values():
            if name in cmd.typos:
                return cmd

        return None

    def get_all_commands(self) -> Dict[str, CommandSpec]:
        """Get all command specs (keyed by canonical name)."""
        return {
            name: spec for name, spec in self._commands.items()
            if spec.canonical == name
        }

    def get_commands_by_layer(self, layer: str) -> Dict[str, CommandSpec]:
        """Get commands for a specific layer."""
        return {
            name: spec for name, spec in self.get_all_commands().items()
            if spec.layer == layer
        }

    def get_meta(self) -> Optional[SpecVersion]:
        """Get spec metadata."""
        for data in self._cache.values():
            if "meta" in data:
                meta = data["meta"]
                return SpecVersion(
                    version=meta.get("version", SPEC_VERSION),
                    description=meta.get("description", ""),
                    status=meta.get("status", "draft"),
                    experimental=meta.get("experimental", True),
                    experimental_warning=meta.get("experimental_warning", ""),
                )
        return None

    def is_typo(self, word: str) -> Optional[str]:
        """Check if word is a known typo. Returns canonical form or None."""
        word = word.lower()
        for cmd in self._commands.values():
            if word in cmd.typos:
                return cmd.canonical
        return None

    def is_british_spelling(self, word: str) -> Optional[str]:
        """Check if word is a British spelling. Returns American form or None."""
        word = word.lower()
        for cmd in self._commands.values():
            if word in cmd.spellings:
                return cmd.spellings[word]
        return None


# =============================================================================
# Module-level API
# =============================================================================

_loader: Optional[SpecLoader] = None


def _get_loader() -> SpecLoader:
    """Get or create the global spec loader."""
    global _loader
    if _loader is None:
        _loader = SpecLoader()
        # Load CLI spec by default
        try:
            _loader.load("cli")
        except FileNotFoundError:
            pass
    return _loader


def load_spec(spec_name: str) -> Dict:
    """Load a spec file by name."""
    return _get_loader().load(spec_name)


def get_command(name: str) -> Optional[CommandSpec]:
    """Get command spec by name or alias."""
    return _get_loader().get_command(name)


def get_all_commands() -> Dict[str, CommandSpec]:
    """Get all command specs."""
    return _get_loader().get_all_commands()


def get_commands_by_layer(layer: str) -> Dict[str, CommandSpec]:
    """Get commands for a specific layer."""
    return _get_loader().get_commands_by_layer(layer)


# =============================================================================
# CLI for testing
# =============================================================================

if __name__ == "__main__":
    import sys

    loader = SpecLoader()

    try:
        loader.load("cli")
        print(f"Loaded spec from: {loader.spec_dir}")
        print()

        meta = loader.get_meta()
        if meta:
            print(f"Version: {meta.version}")
            print(f"Status: {meta.status}")
            print(f"Experimental: {meta.experimental}")
            print()

        commands = loader.get_all_commands()
        print(f"Commands ({len(commands)}):")
        for name, cmd in sorted(commands.items()):
            aliases = f" (aliases: {', '.join(cmd.aliases)})" if cmd.aliases else ""
            typos = f" (typos: {', '.join(cmd.typos)})" if cmd.typos else ""
            print(f"  {name}{aliases}{typos} [{cmd.layer}]")

    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
