"""
Phaser 3 Transpiler

Transpile Rosh code to Phaser 3 JavaScript for browser-based games
"""

from typing import Dict, Any
from .base import BaseTranspiler
from ..ast_nodes import *
from ..errors import RoshRuntimeError


class PhaserTranspiler(BaseTranspiler):
    """Transpile Rosh code to Phaser 3 JavaScript

    MVP Features (v0.1.5):
    - Objects (create object ... end) → Phaser rectangles
    - Properties (set x to 100) → Object initialization
    - Print statements → console.log
    - String interpolation → Template literals

    Deferred Features (v0.1.6+):
    - Events (when/trigger)
    - Control flow (if/while/for)
    - Functions
    - User input
    """

    # Auto-assigned colors for objects (rotates through these)
    DEFAULT_COLORS = {
        0: 0x00ff00,  # Green
        1: 0x0000ff,  # Blue
        2: 0xff0000,  # Red
        3: 0xffff00,  # Yellow
        4: 0xff00ff,  # Magenta
        5: 0x00ffff,  # Cyan
        6: 0xff8800,  # Orange
        7: 0x8800ff,  # Purple
    }

    # Game canvas dimensions (used for percentage calculations)
    GAME_WIDTH = 800
    GAME_HEIGHT = 600

    # Base type templates for inheritance (v0.1.6)
    BASE_TYPES = {
        'player': {
            'lives': 3,
            'score': 0,
            'speed': 5,
            'width': 30,
            'height': 30,
            'color': 0x00ff00,  # Green
            '_auto_control': True  # Flag for auto-controls
        },
        'character': {
            # Same as object for now (can expand in v0.1.7)
        },
        'object': {
            # Base type - minimal defaults
        }
    }

    def __init__(self):
        super().__init__()
        self.object_counter = 0
        self.object_properties: Dict[str, Dict[str, Any]] = {}
        # v0.1.6: Event system tracking
        self.event_handlers: Dict[str, list] = {}  # event_name -> [WhenStatement, ...]
        self.needs_update_loop = False
        self.needs_keyboard_input = False
        self.player_objects = []  # Track player objects for auto-controls
        self.hud_objects = []  # Track HUD objects for display/updates
        # v0.1.7: Sprite/asset tracking
        self.sprite_assets: Dict[str, str] = {}  # object_name -> sprite_filename

    def transpile(self, program: Program) -> str:
        """Convert Rosh Program AST to Phaser JavaScript

        Args:
            program: Rosh Program AST node

        Returns:
            Generated Phaser JavaScript code

        Raises:
            RoshRuntimeError: If program contains unsupported features
        """
        # 1. Validate AST (fail fast on unsupported features)
        self.validate_ast(program)

        # 2. Detect event system features to generate
        self.detect_event_features(program)

        # 3. Generate header comment
        self.emit_comment("Auto-generated from Rosh code")
        self.emit_comment("Transpiled with Rosh Phaser Transpiler v0.1.7")
        self.emit_blank()

        # 4. Generate GameScene class
        self.emit("class GameScene extends Phaser.Scene {")
        self.indent_level += 1

        # 5. Generate constructor
        self.emit("constructor() {")
        self.indent_level += 1
        self.emit("super({ key: 'GameScene' });")
        # Initialize event handlers if events or player objects are used
        if self.event_handlers or self.player_objects:
            self.emit("this.eventHandlers = {};")
        self.indent_level -= 1
        self.emit("}")
        self.emit_blank()

        # 5.5. Generate preload() method if sprites are used (v0.1.7)
        if self.sprite_assets:
            self.emit_preload_method()

        # 6. Generate create() method with game logic
        self.emit("create() {")
        self.indent_level += 1

        # Set up keyboard input if needed (player objects or keyboard events)
        if self.player_objects or self.needs_keyboard_input:
            self.emit_keyboard_setup()

        # Process all statements (skip WhenStatement - handled separately)
        for statement in program.statements:
            if not isinstance(statement, WhenStatement):
                self.emit_statement(statement)

        # Emit event handler registrations
        self.emit_event_handlers()

        # Emit auto-controls for player objects (Phase 4)
        if self.player_objects:
            self.needs_keyboard_input = True  # Force keyboard setup
            self.needs_update_loop = True  # Need update loop for controls
            self.emit_player_auto_controls()

        self.indent_level -= 1
        self.emit("}")

        # 7. Generate update() method if needed (for events)
        if self.needs_update_loop or self.event_handlers:
            self.emit_update_method()

        # 8. Generate event system helper methods (if events or player objects)
        if self.event_handlers or self.player_objects:
            self.emit_event_system_helpers()

        self.indent_level -= 1
        self.emit("}")
        self.emit_blank()

        # 9. Generate Phaser game config and initialization
        self.emit_game_config()

        return self.get_code()

    def validate_ast(self, program: Program) -> None:
        """Validate AST contains only supported features for MVP

        Checks recursively through program for unsupported node types.
        Provides clear, actionable error messages for unsupported features.

        Args:
            program: Rosh Program AST node to validate

        Raises:
            RoshRuntimeError: If unsupported features are found
        """
        # List of unsupported node types for v0.1.6
        unsupported_types = [
            (IfStatement, "if/else statements"),
            (WhileLoop, "while loops"),
            (ForLoop, "for loops"),
            # WhenStatement and TriggerEvent now supported in v0.1.6!
            (FunctionDef, "function definitions"),
            (FunctionCall, "function calls"),
            (Input, "user input"),
            (Import, "imports"),
            (Eval, "eval"),
            (Load, "load"),
            (Save, "save"),
        ]

        def check_node(node: ASTNode, path: str = "top level") -> None:
            """Recursively check node and children for unsupported features"""
            for unsupported_type, feature_name in unsupported_types:
                if isinstance(node, unsupported_type):
                    raise RoshRuntimeError(
                        f"❌ Transpiler does not support '{feature_name}' yet\n"
                        f"\n"
                        f"Location: {path}\n"
                        f"Feature: {feature_name}\n"
                        f"Status: Planned for v0.1.6\n"
                        f"\n"
                        f"Supported in v0.1.5 (MVP):\n"
                        f"  ✅ create object\n"
                        f"  ✅ set property (inside objects)\n"
                        f"  ✅ print (→ console.log)\n"
                        f"  ✅ String interpolation\n"
                        f"\n"
                        f"Coming in v0.1.6:\n"
                        f"  ⏳ when/trigger events\n"
                        f"  ⏳ User input\n"
                        f"  ⏳ Control flow (if/while/for)\n"
                    )

            # Recursively check nested nodes
            if isinstance(node, CreateObject):
                for stmt in node.body:
                    check_node(stmt, f"{path}.{node.name}")
            elif isinstance(node, Program):
                for stmt in node.statements:
                    check_node(stmt, path)

        check_node(program)

    def detect_event_features(self, program: Program) -> None:
        """Scan program for events/input to determine what to generate

        Populates:
        - self.event_handlers: Dict of event_name -> list of WhenStatements
        - self.needs_keyboard_input: True if keyboard events detected
        - self.needs_update_loop: True if update event detected
        - self.player_objects: List of player object names (for auto-controls)

        Args:
            program: Rosh Program AST node to scan
        """
        def scan_statements(statements):
            """Recursively scan for WhenStatement and CreateObject nodes"""
            for node in statements:
                if isinstance(node, WhenStatement):
                    # Track event handler
                    # For collision events, create unique event name with object pairs
                    event_key = node.event_name
                    if node.event_name == 'collision' and node.parameters and len(node.parameters) >= 2:
                        # Create unique event name: collision_objA_objB
                        event_key = f"collision_{node.parameters[0]}_{node.parameters[1]}"

                    if event_key not in self.event_handlers:
                        self.event_handlers[event_key] = []
                    self.event_handlers[event_key].append(node)

                    # Check if needs keyboard
                    if node.event_name in ['key_pressed', 'space_pressed']:
                        self.needs_keyboard_input = True

                    # Check if needs update loop
                    if node.event_name == 'update':
                        self.needs_update_loop = True

                    # Recursively scan handler body for triggers
                    scan_statements(node.body)

                elif isinstance(node, TriggerEvent):
                    # If we trigger events, we need the update loop
                    self.needs_update_loop = True

                # Scan for player objects (Phase 4: pre-detect for keyboard setup)
                elif isinstance(node, CreateObject):
                    # Check if this inherits from 'player'
                    if node.parents and 'player' in node.parents:
                        self.player_objects.append(node.name)
                        self.needs_keyboard_input = True  # Player objects need keyboard
                        self.needs_update_loop = True  # Player objects need update loop

                    # v0.1.7: Detect sprite assets
                    for stmt in node.body:
                        if isinstance(stmt, SetProperty) and isinstance(stmt.target, Identifier):
                            if stmt.target.name == 'sprite':
                                # Extract sprite filename
                                sprite_value = self.eval_constant_expression(stmt.value)
                                if isinstance(sprite_value, str):
                                    self.sprite_assets[node.name] = sprite_value

                    # Scan nested structures
                    scan_statements(node.body)

        scan_statements(program.statements)

    def emit_statement(self, node: ASTNode) -> None:
        """Emit JavaScript for a statement node

        Dispatches to specific emit methods based on node type.

        Args:
            node: AST statement node to emit

        Raises:
            RoshRuntimeError: If node type is unsupported
        """
        if isinstance(node, CreateObject):
            self.emit_create_object(node)
        elif isinstance(node, SetProperty):
            self.emit_set_property(node)
        elif isinstance(node, Print):
            self.emit_print(node)
        elif isinstance(node, TriggerEvent):
            self.emit_trigger_event(node)
        else:
            # Should be caught by validate_ast, but defensive programming
            raise RoshRuntimeError(
                f"Unsupported statement type: {type(node).__name__}\n"
                f"This should have been caught by validation."
            )

    def convert_percentage_to_pixels(self, value: Any, dimension: str) -> float:
        """Convert percentage value to pixels

        Args:
            value: Either a number or a dict with {'type': 'percentage', 'value': float}
            dimension: 'x' or 'y' to determine which canvas dimension to use

        Returns:
            Pixel value as float
        """
        if isinstance(value, dict) and value.get('type') == 'percentage':
            percent = value['value']
            if dimension in ['x', 'width']:
                return (percent / 100.0) * self.GAME_WIDTH
            else:  # y or height
                return (percent / 100.0) * self.GAME_HEIGHT
        return value

    def emit_create_object(self, node: CreateObject) -> None:
        """Convert: create object goblin ... end → Phaser rectangle

        Extracts properties from object body and generates Phaser
        rectangle with position, size, and color.

        Special handling for HUD objects with 'target' property.
        Supports percentage positioning: set x to 50% → 400px (50% of 800px)

        Args:
            node: CreateObject AST node
        """
        # Collect properties from object body (with inheritance)
        properties = self.extract_object_properties(node)
        self.object_properties[node.name] = properties

        # Check if this is a HUD object (has 'target' property)
        if 'target' in properties:
            self.emit_hud_object(node.name, properties)
            self.hud_objects.append(node.name)
            return

        # Emit comment for clarity
        self.emit_comment(f"{node.name.capitalize()} object")

        # Note: Player object tracking is done in detect_event_features() pre-scan

        # Get rendering properties (with defaults) and convert percentages
        x = self.convert_percentage_to_pixels(properties.get('x', 100), 'x')
        y = self.convert_percentage_to_pixels(properties.get('y', 100), 'y')
        width = self.convert_percentage_to_pixels(properties.get('width', 50), 'width')
        height = self.convert_percentage_to_pixels(properties.get('height', 50), 'height')
        color = properties.get('color', self.DEFAULT_COLORS[self.object_counter % 8])

        # Check if object has a sprite
        sprite = properties.get('sprite')

        if sprite:
            # v0.1.7: Use sprite image
            # Track sprite for preloading
            self.sprite_assets[node.name] = sprite

            # Emit image with error handling
            self.emit(f"// Try to load sprite, fallback to rectangle if missing")
            self.emit(f"if (this.textures.exists('{node.name}_sprite')) {{")
            self.indent_level += 1
            self.emit(f"this.{node.name} = this.add.image({int(x)}, {int(y)}, '{node.name}_sprite');")
            self.indent_level -= 1
            self.emit("} else {")
            self.indent_level += 1
            self.emit(f"console.warn('Sprite not found: {sprite}, using colored rectangle');")
            self.emit(f"this.{node.name} = this.add.rectangle({int(x)}, {int(y)}, {int(width)}, {int(height)}, {hex(color)});")
            self.indent_level -= 1
            self.emit("}")
        else:
            # Emit Phaser rectangle code (convert floats to ints for clean output)
            self.emit(
                f"this.{node.name} = this.add.rectangle({int(x)}, {int(y)}, {int(width)}, {int(height)}, {hex(color)});"
            )

        # Store special properties on the Phaser object (Phases 5-6)
        if 'lives' in properties:
            self.emit(f"this.{node.name}.lives = {properties['lives']};")
        if 'score' in properties:
            self.emit(f"this.{node.name}.score = {properties['score']};")
        if 'speed' in properties:
            self.emit(f"this.{node.name}.speed = {properties['speed']};")
        if 'fixed' in properties:
            # Fixed property for immovable objects (Phase 6)
            fixed_val = 'true' if properties['fixed'] else 'false'
            self.emit(f"this.{node.name}.fixed = {fixed_val};")
        if 'wrap_edges' in properties:
            wrap_val = 'true' if properties['wrap_edges'] else 'false'
            self.emit(f"this.{node.name}.wrap_edges = {wrap_val};")

        self.emit_blank()
        self.object_counter += 1

    def extract_object_properties(self, node: CreateObject) -> Dict[str, Any]:
        """Extract property values from object body

        Walks through object body statements and collects all property
        assignments (set property to value).

        v0.1.6: Now supports inheritance! If the object has parents (base types),
        starts with defaults from those types and overrides with user properties.

        Args:
            node: CreateObject AST node

        Returns:
            Dictionary mapping property names to values
        """
        # Start with base type defaults if object has parents
        properties = {}
        if node.parents:
            # For now, only use first parent (multiple inheritance in future)
            base_type = node.parents[0]
            if base_type in self.BASE_TYPES:
                properties = self.BASE_TYPES[base_type].copy()
            # If base type not recognized, ignore (custom types in future)

        # Override with user-specified properties
        for statement in node.body:
            if isinstance(statement, SetProperty):
                target = statement.target

                # Only handle simple properties (set x to 100)
                if isinstance(target, Identifier):
                    prop_name = target.name
                    prop_value = self.eval_constant_expression(statement.value)
                    properties[prop_name] = prop_value

        return properties

    def eval_constant_expression(self, node: ASTNode) -> Any:
        """Evaluate constant expressions at transpile time

        For MVP, only supports literals and simple arithmetic.
        Complex expressions requiring runtime evaluation will raise errors.

        Args:
            node: Expression AST node

        Returns:
            Evaluated constant value

        Raises:
            RoshRuntimeError: If expression cannot be evaluated at transpile time
        """
        if isinstance(node, Literal):
            return node.value

        elif isinstance(node, BinaryOp):
            left = self.eval_constant_expression(node.left)
            right = self.eval_constant_expression(node.right)

            if node.operator == 'plus':
                return left + right
            elif node.operator == 'minus':
                return left - right
            elif node.operator == 'times':
                return left * right
            elif node.operator == 'divided_by':
                return left / right
            elif node.operator == 'modulo':
                return left % right
            else:
                raise RoshRuntimeError(
                    f"Unsupported binary operator in constant expression: {node.operator}"
                )

        elif isinstance(node, Identifier):
            # Check for percentage values (e.g., "50%")
            if node.name.endswith('%'):
                try:
                    percent_value = float(node.name[:-1])
                    # Return as a dict to mark this as a percentage
                    return {'type': 'percentage', 'value': percent_value}
                except ValueError:
                    pass

            # For MVP, identifiers in property values are treated as strings
            # (e.g., set name to identifier → name: "identifier")
            return node.name

        else:
            raise RoshRuntimeError(
                f"Cannot evaluate expression at transpile time: {type(node).__name__}\n"
                f"Only literals and simple arithmetic are supported for object properties."
            )

    def emit_set_property(self, node: SetProperty) -> None:
        """Convert: set object.property to value → Property mutation

        Phase 7: Now supports property mutations in event handlers!

        Examples:
          set player.x to player.x minus 5    → this.player.x = this.player.x - 5;
          set player.lives to 3                → this.player.lives = 3;

        Args:
            node: SetProperty AST node
        """
        # Get target property reference
        if isinstance(node.target, PropertyAccess):
            # Object property mutation (e.g., set player.x to 100)
            obj_name = self.get_property_access_root(node.target)
            property_chain = self.get_property_chain(node.target)
            property_path = f"this.{obj_name}.{'.'.join(property_chain)}"

            # Evaluate value expression
            value_js = self.emit_expression(node.value)

            # Emit assignment
            self.emit(f"{property_path} = {value_js};")

        elif isinstance(node.target, Identifier):
            # Simple property (only allowed inside object definitions)
            raise RoshRuntimeError(
                f"❌ Cannot set property '{node.target.name}' outside object definition\n"
                f"\n"
                f"Did you mean to set an object property?\n"
                f"  set object.{node.target.name} to value  ✅ Correct syntax\n"
            )
        else:
            raise RoshRuntimeError(
                f"Unsupported property target type: {type(node.target).__name__}"
            )

    def emit_print(self, node: Print) -> None:
        """Convert: print "text" → console.log("text")

        Handles simple prints and string interpolation.

        Args:
            node: Print AST node
        """
        # Evaluate expression to JavaScript
        expr_js = self.emit_expression(node.expression)

        self.emit_comment("Print statement")
        self.emit(f"console.log({expr_js});")
        self.emit_blank()

    def emit_trigger_event(self, node: TriggerEvent) -> None:
        """Convert: trigger event_name with value → this.triggerEvent(...)

        Phase 8: Event parameter support

        Examples:
          trigger game_over                  → this.triggerEvent('game_over', null);
          trigger hit with player            → this.triggerEvent('hit', this.player);
          trigger damage with 15             → this.triggerEvent('damage', 15);

        Args:
            node: TriggerEvent AST node
        """
        event_name = node.event_name

        # Evaluate parameter expression if provided
        # Note: For now, only support first argument (multi-arg in future)
        if node.arguments and len(node.arguments) > 0:
            params_js = self.emit_expression(node.arguments[0])
        else:
            params_js = 'null'

        self.emit(f"this.triggerEvent('{event_name}', {params_js});")

    def emit_expression(self, node: ASTNode) -> str:
        """Convert expression AST to JavaScript expression string

        Args:
            node: Expression AST node

        Returns:
            JavaScript expression as string

        Raises:
            RoshRuntimeError: If expression type is unsupported
        """
        if isinstance(node, Literal):
            value = node.value

            # Handle string interpolation
            if isinstance(value, str) and '{' in value:
                return self.emit_interpolated_string(value)

            # Emit literal values
            if isinstance(value, str):
                return f'"{value}"'
            elif value is None:
                return 'null'
            elif isinstance(value, bool):
                return 'true' if value else 'false'
            else:
                return str(value)

        elif isinstance(node, Identifier):
            # For MVP, identifiers are treated as strings
            return f'"{node.name}"'

        elif isinstance(node, PropertyAccess):
            # goblin.x → this.goblin.x
            obj_name = self.get_property_access_root(node)
            property_chain = self.get_property_chain(node)
            return f"this.{obj_name}.{'.'.join(property_chain)}"

        elif isinstance(node, BinaryOp):
            left = self.emit_expression(node.left)
            right = self.emit_expression(node.right)

            op_map = {
                'plus': '+',
                'minus': '-',
                'times': '*',
                'divided_by': '/',
                'modulo': '%',
            }

            js_op = op_map.get(node.operator, node.operator)
            return f"({left} {js_op} {right})"

        else:
            raise RoshRuntimeError(
                f"Unsupported expression type in transpiler: {type(node).__name__}"
            )

    def emit_interpolated_string(self, string_value: str) -> str:
        """Convert Rosh string interpolation to JavaScript template literal

        Input:  "Goblin at ({goblin.x}, {goblin.y})"
        Output: `Goblin at (${this.goblin.x}, ${this.goblin.y})`

        Args:
            string_value: String with {expression} patterns

        Returns:
            JavaScript template literal with ${...} patterns
        """
        import re
        from ..lexer import Lexer
        from ..parser import Parser

        # Pattern to match {expression}
        pattern = r'\{([^}]+)\}'

        def replace_match(match):
            expr_str = match.group(1).strip()

            # Parse the expression
            lexer = Lexer(expr_str)
            tokens = lexer.tokenize()
            parser = Parser(tokens)
            expr_node = parser.parse_expression()

            # Convert to JavaScript
            js_expr = self.emit_expression(expr_node)

            # Wrap in ${}
            return f"${{{js_expr}}}"

        # Replace all {expr} with ${expr}
        js_string = re.sub(pattern, replace_match, string_value)

        # Return as template literal
        return f"`{js_string}`"

    def get_property_access_root(self, node: PropertyAccess) -> str:
        """Get root object name from property access chain

        Args:
            node: PropertyAccess AST node

        Returns:
            Root object name
        """
        if isinstance(node.object, Identifier):
            return node.object.name
        elif isinstance(node.object, PropertyAccess):
            return self.get_property_access_root(node.object)
        else:
            raise RoshRuntimeError("Invalid property access")

    def get_property_chain(self, node: PropertyAccess) -> list:
        """Get property chain from property access node

        Args:
            node: PropertyAccess AST node

        Returns:
            List of property names in order
        """
        chain = []
        current = node

        while isinstance(current, PropertyAccess):
            chain.insert(0, current.property)
            current = current.object

        return chain

    def emit_keyboard_setup(self) -> None:
        """Emit keyboard input setup in create() method

        Generates Phaser keyboard input initialization:
        - Cursor keys (arrow keys)
        - Space bar key
        """
        self.emit_comment("Keyboard setup")
        self.emit("this.cursors = this.input.keyboard.createCursorKeys();")
        self.emit("this.keys = {")
        self.indent_level += 1
        self.emit("space: this.input.keyboard.addKey(Phaser.Input.Keyboard.KeyCodes.SPACE)")
        self.indent_level -= 1
        self.emit("};")
        self.emit_blank()

    def emit_player_auto_controls(self) -> None:
        """Generate automatic keyboard controls for player objects

        Auto-generates event handlers for:
        - Arrow key movement (triggered every frame in update loop)
        - Edge behavior (wrap or stop at boundaries)
        - Space bar fire event

        This makes player objects controllable with zero manual event handlers!
        """
        if not self.player_objects:
            return

        self.emit_comment("Auto-generated player controls")
        self.emit("this.registerEventHandler('update', (params) => {")
        self.indent_level += 1

        for player_name in self.player_objects:
            properties = self.object_properties.get(player_name, {})
            speed = properties.get('speed', 5)
            wrap_edges = properties.get('wrap_edges', False)

            self.emit_comment(f"{player_name.capitalize()} movement")

            # Left arrow
            self.emit("if (this.cursors.left.isDown) {")
            self.indent_level += 1
            self.emit(f"this.{player_name}.x -= {speed};")
            self.indent_level -= 1
            self.emit("}")

            # Right arrow
            self.emit("if (this.cursors.right.isDown) {")
            self.indent_level += 1
            self.emit(f"this.{player_name}.x += {speed};")
            self.indent_level -= 1
            self.emit("}")

            # Up arrow
            self.emit("if (this.cursors.up.isDown) {")
            self.indent_level += 1
            self.emit(f"this.{player_name}.y -= {speed};")
            self.indent_level -= 1
            self.emit("}")

            # Down arrow
            self.emit("if (this.cursors.down.isDown) {")
            self.indent_level += 1
            self.emit(f"this.{player_name}.y += {speed};")
            self.indent_level -= 1
            self.emit("}")
            self.emit_blank()

            # Edge behavior (wrap or stop)
            self.emit_edge_behavior(player_name, wrap_edges)

        self.indent_level -= 1
        self.emit("});")
        self.emit_blank()

        # Space bar fire handler
        self.emit_comment("Auto-generated fire control")
        self.emit("this.registerEventHandler('space_pressed', (params) => {")
        self.indent_level += 1

        for player_name in self.player_objects:
            self.emit(f"this.triggerEvent('fire', this.{player_name});")

        self.indent_level -= 1
        self.emit("});")
        self.emit_blank()

    def emit_edge_behavior(self, obj_name: str, wrap_edges: bool) -> None:
        """Emit edge boundary handling for objects

        Args:
            obj_name: Name of the object
            wrap_edges: If True, wrap around edges. If False, stop at edges.
        """
        if wrap_edges:
            # Wrap around edges (pac-man style)
            self.emit_comment("Wrap around edges")
            # Left edge
            self.emit(f"if (this.{obj_name}.x < 0) {{")
            self.indent_level += 1
            self.emit(f"this.{obj_name}.x = {self.GAME_WIDTH};")
            self.indent_level -= 1
            self.emit("}")
            # Right edge
            self.emit(f"if (this.{obj_name}.x > {self.GAME_WIDTH}) {{")
            self.indent_level += 1
            self.emit(f"this.{obj_name}.x = 0;")
            self.indent_level -= 1
            self.emit("}")
            # Top edge
            self.emit(f"if (this.{obj_name}.y < 0) {{")
            self.indent_level += 1
            self.emit(f"this.{obj_name}.y = {self.GAME_HEIGHT};")
            self.indent_level -= 1
            self.emit("}")
            # Bottom edge
            self.emit(f"if (this.{obj_name}.y > {self.GAME_HEIGHT}) {{")
            self.indent_level += 1
            self.emit(f"this.{obj_name}.y = 0;")
            self.indent_level -= 1
            self.emit("}")
        else:
            # Stop at edges (clamp to boundaries)
            self.emit_comment("Stop at edges")
            # Get object dimensions (assume stored or use defaults)
            self.emit(f"const halfWidth = (this.{obj_name}.width || 50) / 2;")
            self.emit(f"const halfHeight = (this.{obj_name}.height || 50) / 2;")
            # Clamp x
            self.emit(f"this.{obj_name}.x = Math.max(halfWidth, Math.min({self.GAME_WIDTH} - halfWidth, this.{obj_name}.x));")
            # Clamp y
            self.emit(f"this.{obj_name}.y = Math.max(halfHeight, Math.min({self.GAME_HEIGHT} - halfHeight, this.{obj_name}.y));")
        self.emit_blank()

    def emit_hud_object(self, hud_name: str, properties: Dict[str, Any]) -> None:
        """Generate HUD display object

        Creates text objects for displaying target object's lives/score.
        Now requires explicit creation with 'target' property.

        Args:
            hud_name: Name of the HUD object
            properties: HUD properties including 'target', 'x', 'y'
        """
        self.emit_comment(f"{hud_name.capitalize()} HUD")

        target = properties.get('target', 'unknown')
        x = self.convert_percentage_to_pixels(properties.get('x', 10), 'x')
        y = self.convert_percentage_to_pixels(properties.get('y', 10), 'y')

        # Check if target object has lives/score properties
        target_props = self.object_properties.get(target, {})

        y_offset = int(y)

        # Lives display
        if 'lives' in target_props:
            self.emit(
                f"this.{hud_name}_lives = this.add.text({int(x)}, {y_offset}, "
                f"'Lives: ' + (this.{target}.lives || {target_props['lives']}), "
                f"{{ fontSize: '16px', fill: '#fff' }});"
            )
            y_offset += 25

        # Score display
        if 'score' in target_props:
            self.emit(
                f"this.{hud_name}_score = this.add.text({int(x)}, {y_offset}, "
                f"'Score: ' + (this.{target}.score || {target_props['score']}), "
                f"{{ fontSize: '16px', fill: '#fff' }});"
            )
            y_offset += 25

        self.emit_blank()

    def emit_event_handlers(self) -> None:
        """Emit event handler registrations in create() method

        Generates registerEventHandler() calls for all WhenStatement nodes.
        """
        if not self.event_handlers:
            return

        self.emit_blank()
        self.emit_comment("Event handler registrations")

        for event_name, handlers in self.event_handlers.items():
            for handler in handlers:
                self.emit_event_handler(event_name, handler)

    def emit_event_handler(self, event_name: str, handler: WhenStatement) -> None:
        """Emit a single event handler registration

        Generates JavaScript closure that captures handler body.

        Args:
            event_name: Name of the event (e.g., 'start', 'key_pressed')
            handler: WhenStatement AST node containing handler body
        """
        self.emit(f"this.registerEventHandler('{event_name}', (params) => {{")
        self.indent_level += 1

        # Emit handler body statements
        for stmt in handler.body:
            self.emit_statement(stmt)

        self.indent_level -= 1
        self.emit("});")
        self.emit_blank()

    def emit_preload_method(self) -> None:
        """Emit Phaser preload() method for loading sprite assets (v0.1.7)

        Generates preload() method that loads all sprite images from assets/ folder.
        Includes error handling with fallback to colored rectangles.
        """
        self.emit("preload() {")
        self.indent_level += 1

        for obj_name, sprite_file in self.sprite_assets.items():
            self.emit(f"// Load sprite for {obj_name}")
            self.emit(f"this.load.image('{obj_name}_sprite', 'assets/{sprite_file}');")

        self.indent_level -= 1
        self.emit("}")
        self.emit_blank()

    def emit_update_method(self) -> None:
        """Emit Phaser update() method with event triggering

        Generates update loop that triggers 'update' event every frame.
        Also handles keyboard event detection and HUD updates if needed.
        """
        self.emit_blank()
        self.emit("update() {")
        self.indent_level += 1

        # Always trigger 'update' event (for auto-controls or manual handlers)
        if self.needs_update_loop or self.event_handlers or self.player_objects:
            self.emit("this.triggerEvent('update', null);")
            self.emit_blank()

        # Keyboard event detection (Phase 4)
        if self.needs_keyboard_input or self.player_objects:
            self.emit_comment("Keyboard event detection")
            self.emit("if (this.cursors.left.isDown || this.cursors.right.isDown ||")
            self.emit("    this.cursors.up.isDown || this.cursors.down.isDown) {")
            self.indent_level += 1
            self.emit("this.triggerEvent('key_pressed', null);")
            self.indent_level -= 1
            self.emit("}")
            self.emit_blank()

            self.emit("if (Phaser.Input.Keyboard.JustDown(this.keys.space)) {")
            self.indent_level += 1
            self.emit("this.triggerEvent('space_pressed', null);")
            self.indent_level -= 1
            self.emit("}")
            self.emit_blank()

        # HUD updates (Phase 5)
        self.emit_hud_updates()

        # Collision detection
        self.emit_collision_detection()

        self.indent_level -= 1
        self.emit("}")

    def emit_hud_updates(self) -> None:
        """Emit HUD update code in update() method

        Updates text displays for explicit HUD objects only.
        """
        if not self.hud_objects:
            return

        self.emit_comment("Update HUD")
        for hud_name in self.hud_objects:
            properties = self.object_properties.get(hud_name, {})
            target = properties.get('target', 'unknown')
            target_props = self.object_properties.get(target, {})

            if 'lives' in target_props:
                self.emit(
                    f"this.{hud_name}_lives.setText('Lives: ' + this.{target}.lives);"
                )
            if 'score' in target_props:
                self.emit(
                    f"this.{hud_name}_score.setText('Score: ' + this.{target}.score);"
                )

    def emit_collision_detection(self) -> None:
        """Emit collision detection code in update() method

        Detects collision event handlers and generates overlap checking.
        Syntax: when collision objA objB then ...
        """
        # Find collision event handlers (stored with unique keys like 'collision_objA_objB')
        collision_handlers = []
        for event_name, handlers in self.event_handlers.items():
            if event_name.startswith('collision_'):
                # Extract object names from event name
                parts = event_name.split('_')
                if len(parts) >= 3:
                    obj_a = parts[1]
                    obj_b = parts[2]
                    collision_handlers.append((obj_a, obj_b, event_name))

        if not collision_handlers:
            return

        self.emit_comment("Collision detection")
        for obj_a, obj_b, event_name in collision_handlers:
            # Generate AABB (rectangle) overlap check
            self.emit(f"// Check collision: {obj_a} with {obj_b}")
            self.emit(f"if (this.{obj_a} && this.{obj_b}) {{")
            self.indent_level += 1

            # Simple rectangle overlap test
            self.emit(f"const a = this.{obj_a};")
            self.emit(f"const b = this.{obj_b};")
            self.emit("const aLeft = a.x - (a.width || 50) / 2;")
            self.emit("const aRight = a.x + (a.width || 50) / 2;")
            self.emit("const aTop = a.y - (a.height || 50) / 2;")
            self.emit("const aBottom = a.y + (a.height || 50) / 2;")
            self.emit("const bLeft = b.x - (b.width || 50) / 2;")
            self.emit("const bRight = b.x + (b.width || 50) / 2;")
            self.emit("const bTop = b.y - (b.height || 50) / 2;")
            self.emit("const bBottom = b.y + (b.height || 50) / 2;")
            self.emit_blank()

            self.emit("if (aLeft < bRight && aRight > bLeft &&")
            self.emit("    aTop < bBottom && aBottom > bTop) {")
            self.indent_level += 1
            self.emit(f"this.triggerEvent('{event_name}', null);")
            self.indent_level -= 1
            self.emit("}")

            self.indent_level -= 1
            self.emit("}")

        self.emit_blank()

    def emit_event_system_helpers(self) -> None:
        """Emit registerEventHandler and triggerEvent helper methods

        Generates two helper methods:
        - registerEventHandler(): Register event callbacks
        - triggerEvent(): Execute all handlers for an event
        """
        self.emit_blank()
        self.emit_comment("Event system helpers")

        # registerEventHandler method
        self.emit("registerEventHandler(eventName, handler) {")
        self.indent_level += 1
        self.emit("if (!this.eventHandlers[eventName]) {")
        self.indent_level += 1
        self.emit("this.eventHandlers[eventName] = [];")
        self.indent_level -= 1
        self.emit("}")
        self.emit("this.eventHandlers[eventName].push(handler);")
        self.indent_level -= 1
        self.emit("}")
        self.emit_blank()

        # triggerEvent method
        self.emit("triggerEvent(eventName, params) {")
        self.indent_level += 1
        self.emit("if (this.eventHandlers[eventName]) {")
        self.indent_level += 1
        self.emit("this.eventHandlers[eventName].forEach(handler => handler(params || null));")
        self.indent_level -= 1
        self.emit("}")
        self.indent_level -= 1
        self.emit("}")

    def emit_game_config(self) -> None:
        """Emit Phaser game configuration and initialization

        Generates:
        - Game config object (type, width, height, scene)
        - Game instance creation
        """
        self.emit_comment("Phaser game configuration")
        self.emit("const config = {")
        self.indent_level += 1
        self.emit("type: Phaser.AUTO,")
        self.emit("width: 800,")
        self.emit("height: 600,")
        self.emit("backgroundColor: '#2d2d2d',")
        self.emit("scene: GameScene")
        self.indent_level -= 1
        self.emit("};")
        self.emit_blank()

        self.emit_comment("Create and start the game")
        self.emit("const game = new Phaser.Game(config);")
