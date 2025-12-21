"""
Environment for variable bindings with type inference
"""

from typing import Any, Optional, Dict, Tuple, Union
from .errors import RoshNameError


def infer_type(value: Any) -> Union[str, Tuple[str, str]]:
    """
    Infer the type of a value.

    Returns:
        - Simple types: 'null', 'boolean', 'number', 'string', 'object'
        - List types: ('list', element_type) where element_type is 'number', 'string', 'any', etc.
    """
    if value is None:
        return 'null'
    elif isinstance(value, bool):
        return 'boolean'
    elif isinstance(value, (int, float)):
        return 'number'
    elif isinstance(value, str):
        return 'string'
    elif isinstance(value, list):
        if not value:
            # Empty list: type is list<any> until first append
            return ('list', 'any')

        # Check if all elements are the same type
        first_type = infer_type(value[0])

        # For nested lists, just use first element's type
        if isinstance(first_type, tuple):
            # All elements are lists
            if all(isinstance(infer_type(v), tuple) for v in value):
                return ('list', 'list')
            else:
                return ('list', 'any')

        # Check if homogeneous
        if all(infer_type(v) == first_type for v in value):
            return ('list', first_type)
        else:
            return ('list', 'any')
    else:
        # Objects, functions, etc.
        return 'object'


class Environment:
    """
    Manages variable bindings with support for nested scopes and type inference.

    Each binding stores: {'value': <value>, 'type': <inferred_type>}

    Variable names are case-insensitive (for voice-friendly input).
    """

    def __init__(self, parent: Optional['Environment'] = None):
        self.parent = parent
        self.bindings: Dict[str, Dict[str, Any]] = {}
        # Lowercase -> original case mapping for case-insensitive lookup
        self._name_map: Dict[str, str] = {}

    def _find_key(self, name: str) -> Optional[str]:
        """Find the actual key for a case-insensitive name lookup."""
        name_lower = name.lower()
        if name_lower in self._name_map:
            return self._name_map[name_lower]
        return None

    def define(self, name: str, value: Any):
        """Define a new variable in the current scope with inferred type"""
        inferred_type = infer_type(value)
        # Store with the provided case, but map lowercase for lookup
        self.bindings[name] = {
            'value': value,
            'type': inferred_type
        }
        self._name_map[name.lower()] = name

    def get(self, name: str) -> Any:
        """Get a variable value, checking parent scopes if needed (case-insensitive)"""
        actual_key = self._find_key(name)
        if actual_key and actual_key in self.bindings:
            return self.bindings[actual_key]['value']
        elif self.parent:
            return self.parent.get(name)
        else:
            raise RoshNameError(f"Undefined variable: {name}")

    def get_type(self, name: str) -> Union[str, Tuple[str, str]]:
        """Get a variable's type (case-insensitive)"""
        actual_key = self._find_key(name)
        if actual_key and actual_key in self.bindings:
            return self.bindings[actual_key]['type']
        elif self.parent:
            return self.parent.get_type(name)
        else:
            raise RoshNameError(f"Undefined variable: {name}")

    def set(self, name: str, value: Any):
        """Set a variable value with type checking (must already exist, case-insensitive)"""
        actual_key = self._find_key(name)
        if actual_key and actual_key in self.bindings:
            # Get the declared type
            declared_type = self.bindings[actual_key]['type']
            new_type = infer_type(value)

            # Check type compatibility
            if not self._types_compatible(declared_type, new_type):
                # For now, just set it (type enforcement comes in v0.0.7)
                # In the future, this will raise a TypeError
                pass

            self.bindings[actual_key]['value'] = value
            # Note: Type doesn't change after initial assignment

        elif self.parent:
            self.parent.set(name, value)
        else:
            raise RoshNameError(f"Cannot set undefined variable: {name}")

    def _types_compatible(self, declared: Union[str, Tuple], new: Union[str, Tuple]) -> bool:
        """Check if a new value's type is compatible with the declared type"""
        # Handle simple types
        if isinstance(declared, str) and isinstance(new, str):
            if declared == 'any':
                return True
            return declared == new

        # Handle list types
        if isinstance(declared, tuple) and isinstance(new, tuple):
            if declared[0] != 'list' or new[0] != 'list':
                return False

            declared_elem = declared[1]
            new_elem = new[1]

            # list<any> accepts anything
            if declared_elem == 'any':
                return True

            return declared_elem == new_elem

        # Mismatched type categories (e.g., simple vs list)
        return False

    def exists(self, name: str) -> bool:
        """Check if a variable exists (case-insensitive)"""
        actual_key = self._find_key(name)
        if actual_key and actual_key in self.bindings:
            return True
        elif self.parent:
            return self.parent.exists(name)
        else:
            return False

    def __repr__(self):
        return f"Environment({list(self.bindings.keys())})"
