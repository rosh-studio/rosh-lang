"""
Rosh value types and runtime representations
"""

import uuid
from typing import Any, Dict, List, Optional


class RoshObject:
    """
    Represents a Rosh object with:
    - Property stacks (each property is a stack of values)
    - Prototype-based inheritance (multiple parents)
    - Left-to-right lookup resolution
    - Unique UUID for multi-user support
    - Display ID for human-readable references
    """

    def __init__(self, name: str = "object", parents: Optional[List['RoshObject']] = None):
        self.name = name
        self.parents = parents or []  # List of parent RoshObjects
        self.property_stacks: Dict[str, List[Any]] = {}  # Property -> stack of values
        self.uuid = str(uuid.uuid4())  # Unique identifier for multi-user support
        self.id = None  # Display ID (e.g., "ball-1") - set by interpreter

    def get(self, key: str) -> Any:
        """Get a property value (checks own stack, then parents left-to-right)"""
        # Check own property stack first
        if key in self.property_stacks and self.property_stacks[key]:
            return self.property_stacks[key][-1]  # Top of stack

        # Check parents left-to-right
        for parent in self.parents:
            if parent.has(key):
                return parent.get(key)

        return None

    def set(self, key: str, value: Any):
        """Set a property value (replaces entire stack with single value)"""
        self.property_stacks[key] = [value]

    def push(self, key: str, value: Any):
        """Push a value onto property stack (shadows previous values)"""
        if key not in self.property_stacks:
            self.property_stacks[key] = []
        self.property_stacks[key].append(value)

    def pop(self, key: str) -> Optional[Any]:
        """Pop a value from property stack (reveals previous value)"""
        if key in self.property_stacks and self.property_stacks[key]:
            return self.property_stacks[key].pop()
        return None

    def has(self, key: str) -> bool:
        """Check if property exists (own or inherited)"""
        # Check own properties
        if key in self.property_stacks and self.property_stacks[key]:
            return True

        # Check parents
        for parent in self.parents:
            if parent.has(key):
                return True

        return False

    def to_json(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict (flattens stacks, includes inherited)"""
        result = {
            "_uuid": self.uuid,  # Include UUID for identity
            "_name": self.name,  # Include object name
        }

        # Add display ID if set
        if self.id:
            result["_id"] = self.id

        # Get all properties (own + inherited)
        # Start with parents (so own properties override)
        for parent in self.parents:
            parent_json = parent.to_json()
            # Don't inherit metadata fields
            for key in ["_uuid", "_name", "_id"]:
                parent_json.pop(key, None)
            result.update(parent_json)

        # Add own properties (top of each stack)
        for key, stack in self.property_stacks.items():
            if stack:
                value = stack[-1]
                # Recursively convert RoshObjects
                if isinstance(value, RoshObject):
                    result[key] = value.to_json()
                else:
                    result[key] = value

        return result

    def __repr__(self):
        parent_names = [p.name for p in self.parents]
        id_str = f", id={self.id}" if self.id else ""
        return f"RoshObject({self.name}, uuid={self.uuid[:8]}...{id_str}, parents={parent_names}, stacks={self.property_stacks})"


class RoshFunction:
    """
    Represents a user-defined Rosh function
    """

    def __init__(self, name: str, parameters: List[str], body: List[Any], closure_env):
        self.name = name
        self.parameters = parameters
        self.body = body
        self.closure_env = closure_env  # Environment where function was defined

    def __repr__(self):
        return f"RoshFunction({self.name}, params={self.parameters})"


def rosh_to_python(value: Any) -> Any:
    """Convert Rosh value to Python value for display"""
    if isinstance(value, RoshObject):
        return value.to_json()
    elif isinstance(value, RoshFunction):
        return f"<function {value.name}>"
    elif value is None:
        return "null"
    elif isinstance(value, bool):
        return "true" if value else "false"
    else:
        return value


def is_truthy(value: Any) -> bool:
    """Determine if a value is truthy in Rosh"""
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return len(value) > 0
    return True
