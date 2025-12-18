"""
Rosh IR (Intermediate Representation)

The canonical, target-agnostic representation of a Rosh program.
Sits between AST (parser output) and emitters (target code generators).

See: rosh-dev/proposals/ROSH-IR-SPECIFICATION.md for full documentation.

Design Principles:
1. Normalized - All coordinates use 0.0-1.0, colors use 0xRRGGBB
2. Semantic - Represents game concepts, not syntax
3. Complete - Contains all info needed to emit target code
4. Stable - Objects have UUIDs that persist across save/load
5. Target-agnostic - No Phaser/Pygame/Unity specifics
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import uuid


# =============================================================================
# Values
# =============================================================================

@dataclass
class IR_Value:
    """Wrapper for typed values in IR.

    Types:
        - "number": int or float
        - "string": str
        - "boolean": bool
        - "percentage": float (0.0-1.0, already normalized)
        - "color": int (0xRRGGBB)
        - "list": List[IR_Value]
        - "null": None
    """
    type: str
    value: Any

    def __repr__(self):
        return f"IR_Value({self.type}, {self.value!r})"


# =============================================================================
# Expressions
# =============================================================================

@dataclass
class IR_Expression:
    """Evaluatable expression.

    Types:
        - "literal": value is IR_Value
        - "property_access": left=object_name, right=property_name
        - "comparison": operator in ["==", "!=", "<", ">", "<=", ">="]
        - "binary_op": operator in ["+", "-", "*", "/", "%", "and", "or"]
        - "unary_op": operator in ["not", "-"]
        - "function_call": left=function_name, right=args list
    """
    type: str
    operator: Optional[str] = None
    left: Any = None
    right: Any = None
    value: Optional[IR_Value] = None  # For literals

    def __repr__(self):
        if self.type == "literal":
            return f"IR_Expr(literal: {self.value})"
        elif self.type == "property_access":
            return f"IR_Expr({self.left}.{self.right})"
        else:
            return f"IR_Expr({self.type}: {self.left} {self.operator} {self.right})"


# =============================================================================
# Actions
# =============================================================================

@dataclass
class IR_Action:
    """A game action to perform.

    Canonical action types:
        - "set_property": target, property, value
        - "spawn": template, name, properties
        - "destroy": target
        - "play_sound": asset
        - "play_music": asset
        - "stop_music": (no params)
        - "trigger": event, params
        - "print": message
        - "save": slot
        - "load": slot
        - "return": value (optional)
        - "break": (no params)
        - "continue": (no params)
        - "goto": scene (optional), level (optional) - scene/level navigation
    """
    type: str
    params: Dict[str, Any] = field(default_factory=dict)

    def __repr__(self):
        return f"IR_Action({self.type}, {self.params})"


# =============================================================================
# Control Flow
# =============================================================================

@dataclass
class IR_Conditional:
    """If/else branching."""
    condition: IR_Expression
    then_actions: List[Any] = field(default_factory=list)  # List[IR_Action | IR_Conditional | IR_Loop]
    else_actions: List[Any] = field(default_factory=list)


@dataclass
class IR_Loop:
    """While/for loops.

    Types:
        - "while": condition-based loop
        - "for": numeric range loop (iterator, start, end, step)
        - "for_each": collection iteration (iterator, iterable)
    """
    type: str  # "while", "for", "for_each"
    condition: Optional[IR_Expression] = None  # For while
    iterator: Optional[str] = None  # Variable name for for/for_each
    start: Optional[IR_Expression] = None  # For numeric for
    end: Optional[IR_Expression] = None
    step: Optional[IR_Expression] = None
    iterable: Optional[IR_Expression] = None  # For for_each
    body: List[Any] = field(default_factory=list)


# =============================================================================
# Objects
# =============================================================================

@dataclass
class IR_Object:
    """A game object (sprite, text, shape, etc.).

    Properties use normalized values:
        - x, y: 0.0-1.0 (percentage of canvas)
        - width, height: 0.0-1.0 (percentage of canvas)
        - color: 0xRRGGBB
        - Other properties: native Python types

    Scene/Level (Roshonic "Dimensions, Not Modes"):
        - scene: Named area (None = always visible)
        - level: Numbered progression within scene (None = all levels)
        - Objects without scene/level are always visible (HUD, etc.)

    The UUID is stable across save/load and enables:
        - `get` command works by name OR UUID
        - Object identity preserved across targets/sessions
    """
    uuid: str
    name: str
    type: str = "shape"  # "sprite", "text", "shape", "group"
    parent_type: Optional[str] = None  # For inheritance ("player", "enemy")
    properties: Dict[str, IR_Value] = field(default_factory=dict)
    scene: Optional[str] = None  # Named scene (None = always visible)
    level: Optional[int] = None  # Level number (None = all levels)
    saveable: bool = True  # Whether object is saved (False for particles, etc.)

    @classmethod
    def create(cls, name: str, **kwargs) -> "IR_Object":
        """Factory method that auto-generates UUID."""
        return cls(
            uuid=str(uuid.uuid4()),
            name=name,
            **kwargs
        )

    def get_property(self, name: str, default: Any = None) -> Any:
        """Get property value, unwrapping IR_Value."""
        if name in self.properties:
            return self.properties[name].value
        return default

    def __repr__(self):
        props = {k: v.value for k, v in self.properties.items()}
        return f"IR_Object({self.name}, {self.type}, props={props})"


# =============================================================================
# Events
# =============================================================================

@dataclass
class IR_Event:
    """An event handler definition.

    Canonical trigger names:
        - "init": Program start
        - "update": Every frame
        - "keydown:{key}": Key pressed (e.g., "keydown:space")
        - "keyup:{key}": Key released
        - "collision:{a}:{b}": Objects collide
        - "custom:{name}": User-defined events
    """
    trigger: str
    target: Optional[str] = None  # Object UUID/name for object-specific events
    handler: List[Any] = field(default_factory=list)  # List of IR_Action, IR_Conditional, IR_Loop

    def __repr__(self):
        return f"IR_Event({self.trigger}, {len(self.handler)} actions)"


# =============================================================================
# Functions
# =============================================================================

@dataclass
class IR_Function:
    """User-defined function."""
    name: str
    params: List[str] = field(default_factory=list)
    body: List[Any] = field(default_factory=list)
    returns: bool = False  # Whether function has return statement


# =============================================================================
# Program Structure
# =============================================================================

@dataclass
class IR_Metadata:
    """Program-level metadata."""
    title: Optional[str] = None
    version: Optional[str] = None
    canvas_width: int = 800   # Logical canvas size (Rosh coordinates)
    canvas_height: int = 600
    # Scene/Level defaults (Roshonic "Dimensions, Not Modes")
    initial_scene: Optional[str] = None  # None = show all scenes
    initial_level: int = 1  # Default level
    # Additional metadata from _meta/project.toml
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IR_Program:
    """The root IR node containing the complete program.

    This is what emitters receive and transform to target code.
    """
    objects: List[IR_Object] = field(default_factory=list)
    events: List[IR_Event] = field(default_factory=list)
    functions: List[IR_Function] = field(default_factory=list)
    init_actions: List[Any] = field(default_factory=list)  # Top-level statements
    metadata: IR_Metadata = field(default_factory=IR_Metadata)

    def get_object_by_name(self, name: str) -> Optional[IR_Object]:
        """Find object by name (case-insensitive)."""
        name_lower = name.lower()
        for obj in self.objects:
            if obj.name.lower() == name_lower:
                return obj
        return None

    def get_object_by_uuid(self, uuid: str) -> Optional[IR_Object]:
        """Find object by UUID."""
        for obj in self.objects:
            if obj.uuid == uuid:
                return obj
        return None

    def __repr__(self):
        return (f"IR_Program({len(self.objects)} objects, "
                f"{len(self.events)} events, "
                f"{len(self.functions)} functions)")


# =============================================================================
# Utility Functions
# =============================================================================

def normalize_coordinate(value: Any, canvas_size: int) -> float:
    """Convert absolute coordinate to normalized 0-1.

    Args:
        value: Absolute pixel value or percentage
        canvas_size: Canvas dimension (width or height)

    Returns:
        Normalized value between 0.0 and 1.0
    """
    if isinstance(value, IR_Value):
        if value.type == "percentage":
            return value.value  # Already normalized
        else:
            return value.value / canvas_size
    elif isinstance(value, (int, float)):
        return value / canvas_size
    else:
        return 0.5  # Default to center


def denormalize_coordinate(ir_value: float, target_size: float,
                           origin: str = "top-left") -> float:
    """Convert normalized coordinate to target system.

    Args:
        ir_value: Normalized value (0.0-1.0)
        target_size: Target dimension
        origin: "top-left" (Phaser, Pygame) or "center" (Three.js, Unity)

    Returns:
        Coordinate in target system
    """
    if origin == "center":
        return (ir_value - 0.5) * target_size
    else:  # top-left
        return ir_value * target_size


def color_to_hex(color: Any) -> int:
    """Convert color to hex integer.

    Handles:
        - Already int: return as-is
        - String "#RRGGBB": parse hex
        - String "red", "blue", etc.: lookup CSS color
    """
    CSS_COLORS = {
        'white': 0xffffff, 'black': 0x000000, 'red': 0xff0000,
        'green': 0x00ff00, 'blue': 0x0000ff, 'yellow': 0xffff00,
        'cyan': 0x00ffff, 'magenta': 0xff00ff, 'orange': 0xff8800,
        'purple': 0x8800ff, 'pink': 0xff69b4, 'gray': 0x888888,
        'grey': 0x888888, 'gold': 0xffd700, 'silver': 0xc0c0c0,
    }

    if isinstance(color, int):
        return color
    elif isinstance(color, str):
        color = color.lower().strip()
        if color.startswith('#'):
            return int(color[1:], 16)
        elif color in CSS_COLORS:
            return CSS_COLORS[color]
    return 0x888888  # Default gray


# =============================================================================
# Serialization (for save/load)
# =============================================================================

def serialize_ir_program(program: IR_Program) -> dict:
    """Serialize IR program to JSON-compatible dict.

    Used for save/load functionality. Includes UUIDs and names
    so `get` command works across sessions.

    Objects with saveable=False are excluded from serialization.
    """
    return {
        "version": "0.1",
        "metadata": {
            "title": program.metadata.title,
            "version": program.metadata.version,
            "canvas_width": program.metadata.canvas_width,
            "canvas_height": program.metadata.canvas_height,
            "scene": program.metadata.initial_scene,
            "level": program.metadata.initial_level,
        },
        "objects": [
            {
                "uuid": obj.uuid,
                "name": obj.name,
                "type": obj.type,
                "parent_type": obj.parent_type,
                "scene": obj.scene,
                "level": obj.level,
                "properties": {
                    k: {"type": v.type, "value": v.value}
                    for k, v in obj.properties.items()
                }
            }
            for obj in program.objects
            if obj.saveable  # Only save objects with saveable=True
        ]
    }


def deserialize_ir_objects(data: dict) -> List[IR_Object]:
    """Deserialize objects from save data.

    Preserves UUIDs from save file.
    """
    objects = []
    for obj_data in data.get("objects", []):
        properties = {
            k: IR_Value(v["type"], v["value"])
            for k, v in obj_data.get("properties", {}).items()
        }
        objects.append(IR_Object(
            uuid=obj_data["uuid"],
            name=obj_data["name"],
            type=obj_data.get("type", "shape"),
            parent_type=obj_data.get("parent_type"),
            properties=properties,
            scene=obj_data.get("scene"),
            level=obj_data.get("level"),
        ))
    return objects
