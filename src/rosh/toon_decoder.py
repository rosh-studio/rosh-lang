"""TOON (Token-Oriented Object Notation) decoder for Rosh

Parses TOON format back into Python objects.

Version: v0.0.9 (decoder implementation)
Specification: https://github.com/toon-format/toon
"""

from typing import Any, List, Tuple, Optional
from .values import RoshObject


class TOONDecodeError(Exception):
    """Raised when TOON parsing fails"""
    pass


def decode_toon(toon_str: str) -> Any:
    """Decode a TOON-formatted string into a Rosh value

    Args:
        toon_str: TOON-formatted string

    Returns:
        Decoded value (dict, list, primitive, or RoshObject)

    Raises:
        TOONDecodeError: If the TOON format is invalid

    Examples:
        >>> decode_toon("null")
        None

        >>> decode_toon("value[3]: red,green,blue")
        ["red", "green", "blue"]

        >>> decode_toon("name: John\\nage: 30")
        {"name": "John", "age": 30}
    """
    lines = toon_str.strip().split('\n')
    if not lines or not lines[0].strip():
        return None

    # Parse the content
    result, _ = _parse_value(lines, 0, 0)
    return result


def _parse_value(lines: List[str], line_idx: int, base_indent: int) -> Tuple[Any, int]:
    """Parse a value starting at the given line

    Args:
        lines: All lines of the TOON content
        line_idx: Current line index
        base_indent: Expected indentation level

    Returns:
        (parsed_value, next_line_idx) tuple
    """
    if line_idx >= len(lines):
        return None, line_idx

    line = lines[line_idx]
    indent = _get_indent(line)
    content = line.strip()

    # Skip empty lines
    if not content:
        return _parse_value(lines, line_idx + 1, base_indent)

    # Check for RoshObject marker
    if content.startswith('# object:'):
        obj_type = content[9:].strip()
        return _parse_rosh_object(lines, line_idx + 1, indent, obj_type)

    # Check for array format: value[N]: items
    if content.startswith('value[') and ']:' in content:
        return _parse_array(lines, line_idx, indent)

    # Check if it's a quoted string (not a key-value pair)
    if content.startswith('"') and content.endswith('"') and ':' in content:
        # This is a quoted string, not a dict
        return _parse_primitive(content), line_idx + 1

    # Check for object (dict) format - has ':' but no value after it
    if ':' in content:
        # Might be start of dict
        return _parse_dict(lines, line_idx, indent)

    # Must be a primitive value
    return _parse_primitive(content), line_idx + 1


def _parse_dict(lines: List[str], start_idx: int, base_indent: int) -> Tuple[dict, int]:
    """Parse a TOON object/dict"""
    result = {}
    line_idx = start_idx

    while line_idx < len(lines):
        line = lines[line_idx]
        indent = _get_indent(line)
        content = line.strip()

        # Skip empty lines
        if not content:
            line_idx += 1
            continue

        # Stop if we encounter another RoshObject marker at the same level
        # (This happens in arrays of objects)
        if content.startswith('# object:') and indent == base_indent:
            # This is a new object, stop parsing current dict
            break

        # Skip other comments
        if content.startswith('#'):
            line_idx += 1
            continue

        # Stop if we've dedented back to parent level or below
        if content and indent < base_indent:
            break

        # Skip lines that are more indented (they'll be parsed as nested values)
        if indent > base_indent:
            line_idx += 1
            continue

        # Parse key: value or key: (nested)
        if ':' not in content:
            # Not a key-value line, might be end of object
            break

        key, value_part = content.split(':', 1)
        key = key.strip()
        value_part = value_part.strip()

        if value_part:
            # Inline value
            result[key] = _parse_primitive(value_part)
            line_idx += 1
        else:
            # Nested value on next line(s)
            # Find the expected indent for the nested value
            next_idx = line_idx + 1
            while next_idx < len(lines) and not lines[next_idx].strip():
                next_idx += 1

            if next_idx < len(lines):
                next_indent = _get_indent(lines[next_idx])
                nested_value, line_idx = _parse_value(lines, line_idx + 1, next_indent)
                result[key] = nested_value
            else:
                # No nested value found
                result[key] = None
                line_idx += 1

    return result, line_idx


def _parse_rosh_object(lines: List[str], start_idx: int, base_indent: int, obj_type: str) -> Tuple[RoshObject, int]:
    """Parse a RoshObject from TOON format

    The base_indent is the indent of the '# object:' line.
    Properties should be at the same indent level.
    """
    obj = RoshObject(obj_type)

    # Parse the properties as a dict
    # Properties are at the same indent as the '# object:' marker
    properties, line_idx = _parse_dict(lines, start_idx, base_indent)

    # Set all properties on the object
    for key, value in properties.items():
        obj.set(key, value)

    return obj, line_idx


def _parse_array(lines: List[str], start_idx: int, base_indent: int) -> Tuple[list, int]:
    """Parse a TOON array

    Handles two formats:
    1. CSV: value[3]: red,green,blue
    2. Multi-line with nested objects
    """
    line = lines[start_idx]
    content = line.strip()

    # Extract array declaration: value[N]:
    bracket_end = content.index(']')
    length_str = content[6:bracket_end]  # Between 'value[' and ']'

    try:
        expected_length = int(length_str)
    except ValueError:
        raise TOONDecodeError(f"Invalid array length: {length_str}")

    # Get the part after ']:'
    colon_idx = content.index(']:')
    value_part = content[colon_idx + 2:].strip()

    if value_part:
        # CSV format: value[3]: red,green,blue
        if expected_length == 0:
            return [], start_idx + 1

        items = _parse_csv_items(value_part)

        if len(items) != expected_length:
            raise TOONDecodeError(
                f"Array length mismatch: expected {expected_length}, got {len(items)}"
            )

        return items, start_idx + 1
    else:
        # Multi-line format with nested items
        items = []
        line_idx = start_idx + 1

        while line_idx < len(lines) and len(items) < expected_length:
            line = lines[line_idx]
            indent = _get_indent(line)

            # Skip empty lines
            if not line.strip():
                line_idx += 1
                continue

            # Stop if dedented back to array level or beyond
            if indent <= base_indent:
                break

            # Parse the nested value
            value, line_idx = _parse_value(lines, line_idx, indent)
            items.append(value)

        return items, line_idx


def _parse_csv_items(csv_str: str) -> List[Any]:
    """Parse comma-separated values from CSV string

    Handles quoted strings with escaped characters.
    """
    items = []
    current = ""
    in_quotes = False
    i = 0

    while i < len(csv_str):
        char = csv_str[i]

        if char == '"' and (i == 0 or csv_str[i-1] != '\\'):
            in_quotes = not in_quotes
            i += 1
            continue

        if char == ',' and not in_quotes:
            # End of item
            items.append(_parse_primitive(current.strip()))
            current = ""
            i += 1
            continue

        if char == '\\' and in_quotes and i + 1 < len(csv_str):
            # Escape sequence
            next_char = csv_str[i + 1]
            if next_char == '\\':
                current += '\\'
                i += 2
                continue
            elif next_char == '"':
                current += '"'
                i += 2
                continue
            elif next_char == 'n':
                current += '\n'
                i += 2
                continue
            elif next_char == 'r':
                current += '\r'
                i += 2
                continue
            elif next_char == 't':
                current += '\t'
                i += 2
                continue

        current += char
        i += 1

    # Add final item
    if current.strip():
        items.append(_parse_primitive(current.strip()))

    return items


def _parse_primitive(value_str: str) -> Any:
    """Parse a primitive value (null, bool, number, string)"""
    value_str = value_str.strip()

    # Handle null
    if value_str == "null":
        return None

    # Handle booleans
    if value_str == "true":
        return True
    if value_str == "false":
        return False

    # Handle quoted strings
    if value_str.startswith('"') and value_str.endswith('"'):
        # Remove quotes and unescape
        return _unescape_string(value_str[1:-1])

    # Try to parse as number
    try:
        if '.' in value_str:
            return float(value_str)
        else:
            return int(value_str)
    except ValueError:
        pass

    # Return as unquoted string
    return value_str


def _unescape_string(s: str) -> str:
    """Unescape a TOON string"""
    result = ""
    i = 0

    while i < len(s):
        if s[i] == '\\' and i + 1 < len(s):
            next_char = s[i + 1]
            if next_char == '\\':
                result += '\\'
            elif next_char == '"':
                result += '"'
            elif next_char == 'n':
                result += '\n'
            elif next_char == 'r':
                result += '\r'
            elif next_char == 't':
                result += '\t'
            else:
                result += next_char
            i += 2
        else:
            result += s[i]
            i += 1

    return result


def _get_indent(line: str) -> int:
    """Get the indentation level of a line (number of spaces)"""
    count = 0
    for char in line:
        if char == ' ':
            count += 1
        elif char == '\t':
            count += 2  # Treat tab as 2 spaces
        else:
            break
    return count


def load_from_toon(filepath: str) -> dict:
    """Load program state from a TOON file

    Args:
        filepath: Path to .toon file

    Returns:
        Dictionary containing program state

    Raises:
        TOONDecodeError: If the file cannot be parsed
        IOError: If the file cannot be read
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        toon_content = f.read()

    result = decode_toon(toon_content)

    # Result should be a dict for program state
    if not isinstance(result, dict):
        raise TOONDecodeError(
            f"Expected dict for program state, got {type(result).__name__}"
        )

    return result
