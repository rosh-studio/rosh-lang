"""
AST node definitions for Rosh
"""

from dataclasses import dataclass
from typing import Any, List, Optional


@dataclass
class ASTNode:
    """Base class for all AST nodes"""
    pass


@dataclass
class Program(ASTNode):
    """Root node containing all statements"""
    statements: List[ASTNode]
    line: int = 0


@dataclass
class Literal(ASTNode):
    """Literal value (number, string, boolean, null)"""
    value: Any
    type_name: str  # 'number', 'string', 'boolean', 'null'
    line: int = 0


@dataclass
class Random(ASTNode):
    """Random number generation: random or random 1 to 6"""
    min_val: Optional[ASTNode] = None  # Minimum value (inclusive)
    max_val: Optional[ASTNode] = None  # Maximum value (inclusive)
    line: int = 0


@dataclass
class Length(ASTNode):
    """Get length of string or list: length of text"""
    target: ASTNode  # The expression to get length of
    line: int = 0


@dataclass
class StringMethod(ASTNode):
    """String manipulation methods:
    - split text by delimiter
    - substring of text from start length len
    - lowercase of text
    - uppercase of text
    - trim text
    - indexOf search in text
    - lastIndexOf search in text
    """
    method: str  # 'split', 'substring', 'lowercase', 'uppercase', 'trim', 'indexOf', 'lastIndexOf'
    target: ASTNode  # The string expression
    args: List[ASTNode]  # Additional arguments (delimiter, start, length, search)
    line: int = 0


@dataclass
class ListLiteral(ASTNode):
    """List literal: [1, 2, 3]"""
    elements: List[ASTNode]
    line: int = 0


@dataclass
class ListIndex(ASTNode):
    """List indexing: mylist[0] or list slicing: mylist[1:3]"""
    list_expr: ASTNode  # The list expression
    index_expr: Optional[ASTNode] = None  # The index expression (for single index)
    start_expr: Optional[ASTNode] = None  # Start of slice (for slicing)
    end_expr: Optional[ASTNode] = None    # End of slice (for slicing)
    is_slice: bool = False  # True if this is a slice operation
    line: int = 0


@dataclass
class Identifier(ASTNode):
    """Variable or object reference"""
    name: str
    line: int = 0


@dataclass
class CreateObject(ASTNode):
    """create object <name> [from <parent1>, <parent2>...] ... end"""
    name: str
    body: List[ASTNode]
    parents: Optional[List[str]] = None  # List of parent object names
    line: int = 0


@dataclass
class CreateValue(ASTNode):
    """create x to 5  OR  create x: number to 5"""
    name: str = None
    value: ASTNode = None  # expression for the value
    annotated_type: any = None  # Optional type annotation: 'number' or ('list', 'string')
    type_name: str = None  # Legacy field (deprecated, ignored)
    line: int = 0


@dataclass
class SetProperty(ASTNode):
    """set <target> to <value>"""
    target: ASTNode  # Identifier or PropertyAccess
    value: ASTNode
    line: int = 0


@dataclass
class SetAll(ASTNode):
    """set all <type> <property> to <value> - bulk set requiring confirm"""
    type_name: str  # The type of objects (e.g., 'banana')
    property_name: str  # The property to set
    value: ASTNode  # The value to set
    line: int = 0


@dataclass
class Confirm(ASTNode):
    """confirm/yes/go - execute pending bulk operation"""
    line: int = 0


@dataclass
class Repeat(ASTNode):
    """repeat/:repeat/:r - repeat last substantive command"""
    line: int = 0


@dataclass
class BulkOperation(ASTNode):
    """Bulk operation: create/delete/get/set N [modifiers] type [property to value]

    Examples:
    - create 100 balls
    - create 50 green balls
    - delete 20 balls
    - get 10 balls
    - set 30 balls color to red
    - create 100 balls go  (auto-confirm with trailing 'go')
    """
    operation: str  # 'create', 'delete', 'get', 'set'
    count: int  # Number of objects
    type_name: str  # Object type (singularized)
    modifiers: List[str]  # Color/size modifiers for create
    property_name: Optional[str] = None  # For set operations
    property_value: Optional[ASTNode] = None  # For set operations
    auto_confirm: bool = False  # If True, skip confirmation prompt (trailing 'go'/'confirm')
    line: int = 0


@dataclass
class Append(ASTNode):
    """append <item> to <list>"""
    item: ASTNode  # The item to append
    target: ASTNode  # The list to append to
    line: int = 0


@dataclass
class Remove(ASTNode):
    """remove <item> from <list>"""
    item: ASTNode  # The item to remove
    target: ASTNode  # The list to remove from
    line: int = 0


@dataclass
class PushProperty(ASTNode):
    """push <target> <value> - Push value onto property stack"""
    target: ASTNode  # Identifier or PropertyAccess
    value: ASTNode
    line: int = 0


@dataclass
class PopProperty(ASTNode):
    """pop <target> - Pop value from property stack"""
    target: ASTNode  # Identifier or PropertyAccess
    line: int = 0


@dataclass
class StackCommand(ASTNode):
    """stack - Display the data stack contents"""
    line: int = 0


@dataclass
class PropertyAccess(ASTNode):
    """object.property or nested object.prop1.prop2"""
    object: ASTNode  # Identifier or another PropertyAccess
    property: str
    line: int = 0


@dataclass
class Print(ASTNode):
    """print <expression>"""
    expression: Optional[ASTNode]
    line: int = 0


@dataclass
class PrintStack(ASTNode):
    """print stack - pops from stack and prints"""
    line: int = 0


@dataclass
class Input(ASTNode):
    """input <variable_name> [prompt <string>] - reads line from stdin and stores in variable"""
    variable_name: str
    prompt: Optional[str] = None
    line: int = 0


@dataclass
class Get(ASTNode):
    """get <target> - pushes value onto stack
    Supports:
      - get ball         → gets first/single instance
      - get ball 5       → gets instance #5
      - get all ball     → gets all instances
    """
    target: ASTNode  # Identifier or PropertyAccess
    instance_index: Optional[int] = None  # For: get ball 5
    get_all: bool = False  # For: get all ball
    line: int = 0


@dataclass
class Dump(ASTNode):
    """dump - outputs entire state as JSON"""
    line: int = 0


@dataclass
class Save(ASTNode):
    """save [as toon|json] [filepath] - saves state to file (default: rosh-state.json)"""
    filepath: Optional[ASTNode] = None  # expression that evaluates to a string path
    format: Optional[str] = None  # 'toon' or 'json' (default: json)
    line: int = 0


@dataclass
class Load(ASTNode):
    """load <filepath> - restores state from JSON file"""
    filepath: ASTNode  # expression that evaluates to a string path
    line: int = 0


@dataclass
class Prompt(ASTNode):
    """prompt [exec] <message> [using <vars>] into <target>"""
    message: ASTNode  # expression for prompt text
    context_vars: Optional[List[str]] = None  # variables to include in context
    target: Optional[str] = None  # variable name to store result
    exec_mode: bool = False  # if True, execute AI response as Rosh code
    line: int = 0


@dataclass
class Eval(ASTNode):
    """eval <code_string> - Execute Rosh code from a string"""
    code_expr: ASTNode  # expression that evaluates to a string of Rosh code
    line: int = 0


@dataclass
class Read(ASTNode):
    """read [json] <filepath> into <target> - Read file contents"""
    filepath: ASTNode  # expression that evaluates to filepath string
    target: str  # variable name to store result
    parse_json: bool = False  # if True, parse as JSON
    line: int = 0


@dataclass
class Write(ASTNode):
    """write <value> to <filepath> - Write value to file"""
    value_expr: ASTNode  # expression to evaluate and write
    filepath: ASTNode  # expression that evaluates to filepath string
    line: int = 0


@dataclass
class Import(ASTNode):
    """import <module_path> - Import a Rosh module"""
    module_path: ASTNode  # string expression: "math", "https://...", etc.
    line: int = 0


@dataclass
class StackOp(ASTNode):
    """Stack-based operations: add, subtract, multiply, divide, dup, swap, drop

    Math ops: Pop two values from stack, perform operation, push result
    Manipulation: dup (duplicate TOS), swap (swap top 2), drop (remove TOS)
    """
    operator: str  # 'add', 'subtract', 'multiply', 'divide', 'dup', 'swap', 'drop'
    line: int = 0


@dataclass
class IfStatement(ASTNode):
    """if <condition> then ... end"""
    condition: ASTNode
    then_body: List[ASTNode]
    else_body: Optional[List[ASTNode]] = None
    line: int = 0


@dataclass
class WhileLoop(ASTNode):
    """while <condition> then ... end"""
    condition: ASTNode
    body: List[ASTNode]
    line: int = 0


@dataclass
class ForLoop(ASTNode):
    """for <var> in <start> to <end> [step <step>] then ... end

    Examples:
        for i in 1 to 10 then ... end
        for i in 1 to 10 step 2 then ... end
        for item in all items then ... end
    """
    variable: str  # Loop variable name
    start: ASTNode  # Start value (or collection for 'all')
    end: Optional[ASTNode]  # End value (None for 'all' variant)
    step: Optional[ASTNode]  # Step value (default 1)
    body: List[ASTNode]
    is_collection: bool = False  # True for "for x in all <collection>"
    line: int = 0


@dataclass
class Comparison(ASTNode):
    """Comparison operations: is equal to, is below, etc."""
    left: ASTNode
    operator: str  # 'equal', 'below', 'above', etc.
    right: ASTNode
    line: int = 0


@dataclass
class Contains(ASTNode):
    """Contains operation: text contains "hello" or list contains 5"""
    container: ASTNode  # The string or list to search in
    item: ASTNode  # The item to search for
    line: int = 0


@dataclass
class LogicalOp(ASTNode):
    """Logical operations: AND, OR, NOT"""
    operator: str  # 'and', 'or', 'not'
    left: Optional[ASTNode] = None  # Left operand (None for NOT)
    right: Optional[ASTNode] = None  # Right operand
    line: int = 0


@dataclass
class BinaryOp(ASTNode):
    """Binary operations: plus, minus, times, divided by"""
    left: ASTNode
    operator: str
    right: ASTNode
    line: int = 0


@dataclass
class UnaryOp(ASTNode):
    """Unary operations: -x (negation)"""
    operator: str  # Currently just 'minus'
    operand: ASTNode
    line: int = 0


@dataclass
class PlaySound(ASTNode):
    """play sound 'filename' - Play a sound effect"""
    filename: str
    line: int = 0


@dataclass
class PlayMusic(ASTNode):
    """play music 'filename' - Play background music (looping)"""
    filename: str
    line: int = 0


@dataclass
class StopMusic(ASTNode):
    """stop music - Stop background music"""
    line: int = 0


@dataclass
class FunctionDef(ASTNode):
    """define function <name> <params> ... end"""
    name: str
    parameters: List[str]
    body: List[ASTNode]
    line: int = 0


@dataclass
class FunctionCall(ASTNode):
    """call <name> <args>"""
    name: str
    arguments: List[ASTNode]
    line: int = 0


@dataclass
class Return(ASTNode):
    """return <expression> - Return a value from a function"""
    value: Optional[ASTNode] = None  # Expression to return (None for no value)
    line: int = 0


@dataclass
class Break(ASTNode):
    """break - Exit from a loop"""
    line: int = 0


@dataclass
class Continue(ASTNode):
    """continue - Skip to next iteration of a loop"""
    line: int = 0


@dataclass
class Stop(ASTNode):
    """stop - Terminate program execution immediately"""
    line: int = 0


@dataclass
class CloneObject(ASTNode):
    """clone <source> as <target> - Deep copy an object
    If target is None, creates anonymous instance (auto-numbered)
    """
    source: str  # Name of object to clone
    target: Optional[str] = None  # Name of new object (None = anonymous)
    line: int = 0


@dataclass
class DeleteObject(ASTNode):
    """delete <name> - Remove an object"""
    name: str  # Name of object to delete
    line: int = 0


@dataclass
class ResetObject(ASTNode):
    """reset <name> - Revert object to template defaults"""
    name: str  # Name of object to reset
    line: int = 0


@dataclass
class HideObject(ASTNode):
    """hide <name> - Set object visible to false"""
    name: str  # Name of object to hide
    line: int = 0


@dataclass
class ShowObject(ASTNode):
    """show <name> - Set object visible to true"""
    name: str  # Name of object to show
    line: int = 0


@dataclass
class CountObjects(ASTNode):
    """count [type] - Count objects, optionally by type"""
    object_type: Optional[str] = None  # None = count all
    line: int = 0


@dataclass
class MoveObject(ASTNode):
    """move <name> to x,y[,z] - Move object to coordinates"""
    name: str  # Name of object to move
    x: any  # Can be number or expression
    y: any  # Can be number or expression
    z: any = None  # Optional z coordinate
    line: int = 0


@dataclass
class PropertiesCommand(ASTNode):
    """properties <target> - List all properties of an object"""
    target: str  # Name of object
    line: int = 0


@dataclass
class GotoRoom(ASTNode):
    """goto <room> - Move to a room (updates current location)"""
    room: str  # Name of room to go to
    line: int = 0


@dataclass
class GotoScene(ASTNode):
    """goto scene <name> [level <n>] - Navigate to scene and/or level

    Roshonic "Dimensions, Not Modes" - scene/level are coordinates.
    Examples:
        goto scene shop           # change scene, level resets to 1
        goto level 2              # change level within current scene
        goto scene game level 2   # change both
    """
    scene: Optional[str] = None  # Scene name (None = don't change)
    level: Optional[int] = None  # Level number (None = don't change)
    line: int = 0


@dataclass
class SaveGame(ASTNode):
    """save game [slot_name] - Save game state

    Roshonic "Save Everything by Default" - all saveable objects serialized.
    Objects with saveable=false are excluded.

    Examples:
        save game                  # saves to default slot
        save game "adventure1"     # saves to named slot
    """
    slot: Optional[str] = None  # Slot name (None = default slot)
    line: int = 0


@dataclass
class LoadGame(ASTNode):
    """load game [slot_name] - Load game state

    Restores all object properties from saved state.

    Examples:
        load game                  # loads from default slot
        load game "adventure1"     # loads from named slot
    """
    slot: Optional[str] = None  # Slot name (None = default slot)
    line: int = 0


@dataclass
class LookCommand(ASTNode):
    """look [object] - Display current room or examine object"""
    target: Optional[str] = None  # Object to examine (None = look at room)
    line: int = 0


@dataclass
class ConnectRooms(ASTNode):
    """connect <room1> <direction> <room2> - Connect two rooms"""
    room1: str
    direction: str
    room2: str
    line: int = 0


@dataclass
class Help(ASTNode):
    """help [topic] - Display help for commands or objects"""
    topic: Optional[str] = None  # Optional topic to get help about
    line: int = 0


@dataclass
class Increment(ASTNode):
    """increment <target> - Increment a variable by 1"""
    target: ASTNode  # Identifier or PropertyAccess
    line: int = 0


@dataclass
class Decrement(ASTNode):
    """decrement <target> - Decrement a variable by 1"""
    target: ASTNode  # Identifier or PropertyAccess
    line: int = 0


@dataclass
class WhenStatement(ASTNode):
    """when <event_name> [parameters] then ... end - Define event handler"""
    event_name: str
    parameters: list[str]  # Parameter names for event arguments
    body: list[ASTNode]
    line: int = 0


@dataclass
class TriggerEvent(ASTNode):
    """trigger <event_name> [with <args>] - Trigger an event"""
    event_name: str
    arguments: list[ASTNode]  # Expressions to evaluate as arguments
    line: int = 0


@dataclass
class Metadata(ASTNode):
    """meta [.scope] ... end - Program metadata declaration

    Scopes:
        - None (default): Core metadata (version, author, license, etc.)
        - 'generated': Auto-generated metadata (uuid, checksum, security_key, timestamps)
        - 'game': Game-specific metadata (type, engine, multiplayer, etc.)

    Examples:
        meta
            version "1.0.0"
            author "rdubar"
        end

        meta.generated
            uuid "550e8400-e29b-41d4-a716-446655440000"
            checksum "sha256:abc123..."
        end

        meta.game
            type "2D"
            engine "phaser"
        end
    """
    scope: Optional[str] = None  # None = core, 'generated', 'game', etc.
    fields: dict = None  # key-value pairs from the meta block
    line: int = 0

    def __post_init__(self):
        if self.fields is None:
            self.fields = {}
