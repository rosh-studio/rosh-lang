"""
Rosh Data Module - Shared data files for emitters

This module provides access to shared data like known_objects.toml
that can be used across different emitters (text, 2D, 3D).
"""

import tomllib
from pathlib import Path
from typing import Dict, Any

_DATA_DIR = Path(__file__).parent
_known_objects_cache = None


def load_known_objects() -> Dict[str, Any]:
    """Load known objects from TOML file.

    Returns a dict of object_name -> object_definition.
    Each definition has:
        - description: str (for text adventures)
        - category: str (food, nature, collectible, etc.)
        - 2d: dict (color, shape, scale, etc.)
        - 3d: dict (shape, color, scaleX/Y/Z, etc.)
    """
    global _known_objects_cache
    if _known_objects_cache is not None:
        return _known_objects_cache

    toml_path = _DATA_DIR / "known_objects.toml"
    if not toml_path.exists():
        return {}

    with open(toml_path, 'rb') as f:
        _known_objects_cache = tomllib.load(f)

    return _known_objects_cache


def get_known_objects_3d() -> Dict[str, Dict[str, Any]]:
    """Get known objects formatted for 3D emitters (Three.js).

    Returns dict of name -> {shape, color, scaleX, scaleY, scaleZ}
    """
    all_objects = load_known_objects()
    result = {}

    for name, obj in all_objects.items():
        if isinstance(obj, dict) and '3d' in obj:
            props = obj['3d'].copy()
            # Ensure required fields
            props.setdefault('shape', 'box')
            props.setdefault('color', 0x00ff00)
            result[name] = props

    return result


def get_known_objects_2d() -> Dict[str, Dict[str, Any]]:
    """Get known objects formatted for 2D emitters (Phaser, Pygame).

    Returns dict of name -> {color, shape, width, height, scale}
    """
    all_objects = load_known_objects()
    result = {}

    for name, obj in all_objects.items():
        if isinstance(obj, dict) and '2d' in obj:
            props = obj['2d'].copy()
            props.setdefault('shape', 'rectangle')
            props.setdefault('color', 'green')
            result[name] = props

    return result


def get_known_objects_text() -> Dict[str, str]:
    """Get known objects formatted for text emitters.

    Returns dict of name -> description
    """
    all_objects = load_known_objects()
    result = {}

    for name, obj in all_objects.items():
        if isinstance(obj, dict) and 'description' in obj:
            result[name] = obj['description']

    return result


def get_known_object_names() -> list:
    """Get list of all known object names."""
    return list(load_known_objects().keys())


def get_known_objects_by_category() -> Dict[str, list]:
    """Get known objects grouped by category.

    Returns dict of category -> [object_names]
    """
    all_objects = load_known_objects()
    result = {}

    for name, obj in all_objects.items():
        if isinstance(obj, dict):
            category = obj.get('category', 'other')
            if category not in result:
                result[category] = []
            result[category].append(name)

    return result
