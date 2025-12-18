"""
Meta configuration loader for Rosh projects.

Loads settings from _meta/ folder in project directories.
"""

import os
from typing import Dict, Any, Optional


def load_meta(project_dir: str, target: Optional[str] = None) -> Dict[str, Any]:
    """Load meta settings from _meta/ folder.

    Settings are loaded in order (later overrides earlier):
    1. _meta/project.toml - General project settings
    2. _meta/{target}.toml - Target-specific settings (e.g., phaser.toml)

    Args:
        project_dir: Path to the project directory
        target: Optional target platform (phaser, pygame, threejs)

    Returns:
        Merged dict of settings, empty dict if no _meta/ folder
    """
    # Use tomllib (Python 3.11+) or fall back to tomli
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib
        except ImportError:
            # No TOML support available - return empty settings
            return {}

    meta_dir = os.path.join(project_dir, "_meta")
    settings: Dict[str, Any] = {}

    if not os.path.isdir(meta_dir):
        return settings

    # Load project.toml (general settings)
    project_file = os.path.join(meta_dir, "project.toml")
    if os.path.exists(project_file):
        with open(project_file, "rb") as f:
            settings.update(tomllib.load(f))

    # Load target-specific settings (e.g., phaser.toml)
    if target:
        target_file = os.path.join(meta_dir, f"{target}.toml")
        if os.path.exists(target_file):
            with open(target_file, "rb") as f:
                target_settings = tomllib.load(f)
                # Deep merge target settings
                _deep_merge(settings, target_settings)

    return settings


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> None:
    """Deep merge override dict into base dict (mutates base).

    Nested dicts are merged recursively, other values are replaced.

    Args:
        base: Base dict to merge into
        override: Dict with values to merge/override
    """
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
