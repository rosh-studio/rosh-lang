"""TOON (Token-Oriented Object Notation) encoder for Rosh

TOON is a compact, LLM-optimized format that uses:
- YAML-style indentation for objects
- CSV-style tables for uniform arrays
- Explicit length declarations for arrays

Benefits over JSON:
- 40% fewer tokens
- 73.9% LLM parsing accuracy (vs 69.7% for JSON)
- Human-readable
- Compact for VR/AR memory constraints

Version: v0.0.9 (encoder only, minimal implementation)
Specification: https://github.com/toon-format/toon
"""

from typing import Any, List
from .values import RoshObject


def encode_toon(value: Any, indent: int = 0) -> str:
    """Encode a Rosh value as TOON format

    Args:
        value: The value to encode (RoshObject, list, primitive)
        indent: Current indentation level (for nested objects)

    Returns:
        TOON-formatted string

    Examples:
        >>> encode_toon({"name": "John", "age": 30})
        "name: John\\nage: 30"

        >>> encode_toon(["red", "green", "blue"])
        "value[3]: red,green,blue"

        >>> encode_toon(RoshObject("game"))
        "# object: game"
    """

    if value is None:
        return "null"

    elif isinstance(value, bool):
        return "true" if value else "false"

    elif isinstance(value, (int, float)):
        return str(value)

    elif isinstance(value, str):
        # Escape special characters for TOON
        return _escape_string(value)

    elif isinstance(value, list):
        return _encode_array(value, indent)

    elif isinstance(value, dict):
        return _encode_dict(value, indent)

    elif isinstance(value, RoshObject):
        return _encode_rosh_object(value, indent)

    else:
        # Fallback: convert to string
        return str(value)


def _escape_string(s: str) -> str:
    """Escape special characters in TOON strings

    TOON uses commas and colons as delimiters, so we need to quote
    strings that contain these characters.
    """
    # Check if string needs quoting
    needs_quoting = any(c in s for c in [',', ':', '\n', '\r', '"'])

    if needs_quoting:
        # Escape double quotes and backslashes
        escaped = s.replace('\\', '\\\\').replace('"', '\\"')
        return f'"{escaped}"'
    else:
        return s


def _encode_array(arr: List[Any], indent: int) -> str:
    """Encode a list as TOON array

    TOON supports two array formats:
    1. Simple CSV: colors[3]: red,green,blue
    2. Tabular: users[2]{id,name}: 1,alice / 2,bob

    For v0.0.9, we only implement simple CSV for uniform primitives.
    """
    if not arr:
        return "value[0]:"

    # Check if all elements are primitives (not nested objects/arrays)
    all_primitives = all(
        isinstance(item, (str, int, float, bool, type(None)))
        for item in arr
    )

    if all_primitives:
        # Simple CSV format: value[N]: item1,item2,item3
        length = len(arr)
        items = ','.join(_escape_string(str(item)) if isinstance(item, str) else str(item)
                        for item in arr)
        return f"value[{length}]: {items}"
    else:
        # Complex arrays with nested objects - fall back to multi-line format
        lines = [f"value[{len(arr)}]:"]
        indent_str = "  " * (indent + 1)
        for item in arr:
            item_str = encode_toon(item, indent + 1)
            # Add indentation to each line of the item
            item_lines = item_str.split('\n')
            for line in item_lines:
                lines.append(f"{indent_str}{line}")
        return '\n'.join(lines)


def _encode_dict(obj: dict, indent: int) -> str:
    """Encode a Python dict as TOON object

    TOON format:
        key1: value1
        key2: value2
        nested:
          subkey: subvalue
    """
    if not obj:
        return ""

    lines = []
    indent_str = "  " * indent

    for key, value in obj.items():
        key_str = _escape_string(str(key))

        # Check if value is nested object/array
        if isinstance(value, (dict, RoshObject, list)):
            # Nested value - put on next line with increased indentation
            lines.append(f"{indent_str}{key_str}:")
            value_str = encode_toon(value, indent + 1)
            # Add indentation to each line
            value_lines = value_str.split('\n')
            for line in value_lines:
                if line:  # Skip empty lines
                    lines.append(f"  {indent_str}{line}")
        else:
            # Simple value - put on same line
            value_str = encode_toon(value, indent)
            lines.append(f"{indent_str}{key_str}: {value_str}")

    return '\n'.join(lines)


def _encode_rosh_object(obj: RoshObject, indent: int) -> str:
    """Encode a RoshObject as TOON object

    RoshObject has property_stacks and we use to_json() to get all properties.

    TOON format:
        # object: <name>
        property1: value1
        property2: value2
    """
    lines = []
    indent_str = "  " * indent

    # Convert to JSON dict to get all properties (flattened)
    obj_dict = obj.to_json()

    # Add object name as comment if it exists
    if hasattr(obj, 'name') and obj.name:
        lines.append(f"{indent_str}# object: {obj.name}")

    # Encode all properties from the dictionary
    for key, value in obj_dict.items():
        key_str = _escape_string(str(key))

        # Check if value is nested
        if isinstance(value, (dict, RoshObject, list)):
            lines.append(f"{indent_str}{key_str}:")
            value_str = encode_toon(value, indent + 1)
            value_lines = value_str.split('\n')
            for line in value_lines:
                if line:
                    lines.append(f"  {indent_str}{line}")
        else:
            value_str = encode_toon(value, indent)
            lines.append(f"{indent_str}{key_str}: {value_str}")

    return '\n'.join(lines)


def toon_output(value: Any) -> str:
    """Format a value as TOON for output (top-level function for CLI)

    This is the main entry point for --toon flag output.

    Args:
        value: The value to format

    Returns:
        TOON-formatted string suitable for printing
    """
    return encode_toon(value, indent=0)


def save_as_toon(filepath: str, state: dict) -> None:
    """Save program state as TOON file

    Args:
        filepath: Path to .toon file
        state: State dictionary to save

    Raises:
        IOError: If file cannot be written
    """
    toon_str = encode_toon(state, indent=0)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(toon_str)
        f.write('\n')  # Trailing newline for POSIX compliance
