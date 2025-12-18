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

    # CSS color names to hex values (for string color support)
    CSS_COLORS = {
        'white': 0xffffff,
        'black': 0x000000,
        'red': 0xff0000,
        'green': 0x00ff00,
        'blue': 0x0000ff,
        'yellow': 0xffff00,
        'cyan': 0x00ffff,
        'magenta': 0xff00ff,
        'orange': 0xff8800,
        'purple': 0x8800ff,
        'pink': 0xff69b4,
        'gray': 0x888888,
        'grey': 0x888888,
        'gold': 0xffd700,
        'silver': 0xc0c0c0,
        'lime': 0x00ff00,
        'navy': 0x000080,
        'teal': 0x008080,
        'aqua': 0x00ffff,
        'maroon': 0x800000,
        'olive': 0x808000,
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

    def __init__(self, meta: Dict[str, Any] = None):
        super().__init__(meta)
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
        # v0.1.10: Sound/music tracking
        self.sound_assets: list = []  # List of sound filenames to preload
        self.music_file: str = None  # Background music filename (if any)

        # Apply meta settings for canvas dimensions
        canvas_meta = self.meta.get('canvas', {})
        self.game_width = canvas_meta.get('width', self.GAME_WIDTH)
        self.game_height = canvas_meta.get('height', self.GAME_HEIGHT)

    def transpile(self, program: Program, enable_repl: bool = False) -> str:
        """Convert Rosh Program AST to Phaser JavaScript

        Args:
            program: Rosh Program AST node
            enable_repl: If True, inject in-game REPL for live coding (dev mode)

        Returns:
            Generated Phaser JavaScript code

        Raises:
            RoshRuntimeError: If program contains unsupported features
        """
        # Store REPL flag
        self.enable_repl = enable_repl

        # 1. Validate AST (fail fast on unsupported features)
        self.validate_ast(program)

        # 2. Detect event system features to generate
        self.detect_event_features(program)

        # 3. Generate header comment
        self.emit_comment("Auto-generated from Rosh code")
        self.emit_comment("Transpiled with Rosh Phaser Transpiler v0.1.10")
        self.emit_blank()

        # 4. Generate GameScene class
        self.emit("class GameScene extends Phaser.Scene {")
        self.indent_level += 1

        # 5. Generate constructor
        self.emit("constructor() {")
        self.indent_level += 1
        self.emit("super({ key: 'GameScene' });")
        # Initialize event handlers if events, player objects, or REPL are used
        if self.event_handlers or self.player_objects or self.enable_repl:
            self.emit("this.eventHandlers = {};")
        self.indent_level -= 1
        self.emit("}")
        self.emit_blank()

        # 5.5. Generate preload() method if sprites or sounds are used (v0.1.7+)
        if self.sprite_assets or self.sound_assets or self.music_file:
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

        # 8. Generate event system helper methods (if events, player objects, or REPL)
        # REPL needs event system for 'trigger' command
        if self.event_handlers or self.player_objects or self.enable_repl:
            self.emit_event_system_helpers()

        # 8.5. Generate user-defined functions as class methods (v0.2.1)
        for statement in program.statements:
            if isinstance(statement, FunctionDef):
                self.emit_blank()
                self.emit_function_def(statement)

        self.indent_level -= 1
        self.emit("}")
        self.emit_blank()

        # 9. Generate Phaser game config and initialization
        self.emit_game_config()

        # 10. Generate in-game REPL if enabled (v0.2.0)
        if self.enable_repl:
            self.emit_repl_code()

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
            # IfStatement now supported! (v0.2.1)
            # FunctionDef and FunctionCall now supported! (v0.2.1)
            (WhileLoop, "while loops"),
            (ForLoop, "for loops"),
            # WhenStatement and TriggerEvent now supported in v0.1.6!
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
                    if node.event_name in ['key_pressed', 'space_pressed', 'key_left', 'key_right', 'key_up', 'key_down', 'key_r']:
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

                # v0.1.10: Detect sound assets
                elif isinstance(node, PlaySound):
                    if node.filename not in self.sound_assets:
                        self.sound_assets.append(node.filename)

                elif isinstance(node, PlayMusic):
                    self.music_file = node.filename

                # Scan if/else bodies
                elif isinstance(node, IfStatement):
                    scan_statements(node.then_body)
                    if node.else_body:
                        scan_statements(node.else_body)

                # Scan function bodies for sounds
                elif isinstance(node, FunctionDef):
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
        elif isinstance(node, IfStatement):
            self.emit_if_statement(node)
        elif isinstance(node, FunctionCall):
            self.emit_function_call(node)
        elif isinstance(node, FunctionDef):
            # FunctionDef at statement level is handled separately in transpile()
            pass
        elif isinstance(node, PlaySound):
            # v0.1.10: Sound effects
            sound_key = node.filename.replace('.', '_').replace('/', '_')
            self.emit(f"this.sound.play('{sound_key}');")
        elif isinstance(node, PlayMusic):
            # v0.1.10: Background music (looping)
            music_key = node.filename.replace('.', '_').replace('/', '_')
            self.emit(f"if (!this.bgMusic || !this.bgMusic.isPlaying) {{")
            self.indent_level += 1
            self.emit(f"this.bgMusic = this.sound.add('{music_key}', {{ loop: true }});")
            self.emit(f"this.bgMusic.play();")
            self.indent_level -= 1
            self.emit(f"}}")
        elif isinstance(node, StopMusic):
            # v0.1.10: Stop background music
            self.emit(f"if (this.bgMusic) {{ this.bgMusic.stop(); }}")
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
                return (percent / 100.0) * self.game_width
            else:  # y or height
                return (percent / 100.0) * self.game_height
        return value

    def emit_create_object(self, node: CreateObject) -> None:
        """Convert: create object goblin ... end → Phaser rectangle/text/sprite

        Extracts properties from object body and generates appropriate Phaser object:
        - If 'text' property exists → Phaser text object
        - If 'sprite' property exists → Phaser image/sprite
        - Otherwise → Phaser colored rectangle

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
        # Convert string color names to hex integers
        if isinstance(color, str):
            color = self.CSS_COLORS.get(color.lower(), 0x888888)  # Default gray if unknown

        # Check if object has text (renders as Phaser text object)
        text = properties.get('text')
        if text is not None:
            self.emit_text_object(node.name, properties, x, y)
            self.emit_blank()
            self.object_counter += 1
            return

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
            # Set display size to match specified width/height
            self.emit(f"this.{node.name}.setDisplaySize({int(width)}, {int(height)});")
            self.indent_level -= 1
            self.emit("} else {")
            self.indent_level += 1
            self.emit(f"console.warn('Sprite not found: {sprite}, using colored rectangle');")
            self.emit(f"this.{node.name} = this.add.rectangle({int(x)}, {int(y)}, {int(width)}, {int(height)}, {hex(color)});")
            self.indent_level -= 1
            self.emit("}")
        else:
            # Check for shape property (circle, rectangle)
            shape = properties.get('shape', 'rectangle')
            if shape == 'circle':
                # Emit Phaser circle (use width as diameter, so radius = width/2)
                radius = int(width) // 2
                self.emit(
                    f"this.{node.name} = this.add.circle({int(x)}, {int(y)}, {radius}, {hex(color)});"
                )
            else:
                # Emit Phaser rectangle code (convert floats to ints for clean output)
                self.emit(
                    f"this.{node.name} = this.add.rectangle({int(x)}, {int(y)}, {int(width)}, {int(height)}, {hex(color)});"
                )

        # Store custom properties on the Phaser object
        # These are properties beyond the standard rendering ones (x, y, width, height, color, sprite, text)
        rendering_props = {'x', 'y', 'width', 'height', 'color', 'sprite', 'text', 'font_size', 'font', 'align', 'visible', 'shape'}
        for prop_name, prop_value in properties.items():
            if prop_name not in rendering_props:
                # Emit custom property assignment
                if isinstance(prop_value, bool):
                    val_js = 'true' if prop_value else 'false'
                elif isinstance(prop_value, str):
                    val_js = f'"{prop_value}"'
                else:
                    val_js = str(prop_value)
                self.emit(f"this.{node.name}.{prop_name} = {val_js};")

        # Handle visibility (use Phaser's setVisible method)
        if 'visible' in properties:
            visible_val = 'true' if properties['visible'] else 'false'
            self.emit(f"this.{node.name}.setVisible({visible_val});")

        # Assign UUID to object for REPL get command (#017)
        self.emit(f"this.{node.name}._rosh_uuid = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {{")
        self.indent_level += 1
        self.emit("const r = Math.random() * 16 | 0;")
        self.emit("return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);")
        self.indent_level -= 1
        self.emit("});")

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

        elif isinstance(node, UnaryOp):
            # Handle negative numbers (e.g., -50)
            operand = self.eval_constant_expression(node.operand)
            if node.operator in ['-', 'minus']:
                return -operand if operand is not None else None
            elif node.operator in ['not', '!']:
                return not operand if operand is not None else None
            else:
                raise RoshRuntimeError(
                    f"Unsupported unary operator in constant expression: {node.operator}"
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
          set title.visible to false          → this.title.setVisible(false);

        Args:
            node: SetProperty AST node
        """
        # Get target property reference
        if isinstance(node.target, PropertyAccess):
            # Object property mutation (e.g., set player.x to 100)
            obj_name = self.get_property_access_root(node.target)
            property_chain = self.get_property_chain(node.target)
            prop_name = property_chain[-1] if property_chain else ''

            # Evaluate value expression
            value_js = self.emit_expression(node.value)

            # Special handling for Phaser-specific properties that need method calls
            if prop_name == 'visible':
                # Phaser uses setVisible() method
                obj_path = f"this.{obj_name}" + (f".{'.'.join(property_chain[:-1])}" if len(property_chain) > 1 else "")
                self.emit(f"{obj_path}.setVisible({value_js});")
            elif prop_name == 'text' or prop_name == 'textContent':
                # Phaser text objects use setText() method
                obj_path = f"this.{obj_name}" + (f".{'.'.join(property_chain[:-1])}" if len(property_chain) > 1 else "")
                self.emit(f"{obj_path}.setText({value_js});")
            elif prop_name == 'font_size':
                # Phaser text objects use setFontSize() method
                # Also update our custom font_size property for reading back
                # Use block scope to avoid redeclaration in loops
                obj_path = f"this.{obj_name}" + (f".{'.'.join(property_chain[:-1])}" if len(property_chain) > 1 else "")
                self.emit(f"{{ const _fs = {value_js}; {obj_path}.font_size = _fs; {obj_path}.setFontSize(_fs); }}")
            elif prop_name == 'alpha':
                # Phaser uses setAlpha() method
                obj_path = f"this.{obj_name}" + (f".{'.'.join(property_chain[:-1])}" if len(property_chain) > 1 else "")
                self.emit(f"{obj_path}.setAlpha({value_js});")
            else:
                # Standard property assignment
                property_path = f"this.{obj_name}.{'.'.join(property_chain)}"
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

    def emit_if_statement(self, node: IfStatement) -> None:
        """Convert: if <condition> then ... end → JavaScript if statement

        Examples:
          if player.x is 100 then         → if (this.player.x === 100) {
              set player.y to 200              this.player.y = 200;
          end                               }

          if box.x is goal.x then         → if (this.box.x === this.goal.x) {
              trigger win                      this.triggerEvent('win', null);
          else                              } else {
              trigger miss                     this.triggerEvent('miss', null);
          end                               }

        Args:
            node: IfStatement AST node
        """
        # Emit condition
        condition_js = self.emit_expression(node.condition)
        self.emit(f"if ({condition_js}) {{")
        self.indent_level += 1

        # Emit then body
        for stmt in node.then_body:
            self.emit_statement(stmt)

        self.indent_level -= 1

        # Emit else body if present
        if node.else_body:
            self.emit("} else {")
            self.indent_level += 1
            for stmt in node.else_body:
                self.emit_statement(stmt)
            self.indent_level -= 1

        self.emit("}")

    def emit_function_call(self, node: FunctionCall) -> None:
        """Convert: call <name> → this.<name>()

        Examples:
          call check_win                    → this.check_win();
          call move_box with box1           → this.move_box(this.box1);

        Args:
            node: FunctionCall AST node
        """
        func_name = node.name

        # Build arguments list
        if node.arguments:
            args_js = ", ".join(self.emit_expression(arg) for arg in node.arguments)
            self.emit(f"this.{func_name}({args_js});")
        else:
            self.emit(f"this.{func_name}();")

    def emit_function_def(self, node: FunctionDef) -> None:
        """Convert: define <name> ... end → GameScene method

        Examples:
          define check_win                  → check_win() { ... }
              if box.x is equal to goal.x then
                  set win_text.visible to true
              end
          end

        Args:
            node: FunctionDef AST node
        """
        func_name = node.name

        # Build parameter list
        params = ", ".join(node.parameters) if node.parameters else ""

        self.emit(f"{func_name}({params}) {{")
        self.indent_level += 1

        # Emit function body
        for stmt in node.body:
            self.emit_statement(stmt)

        self.indent_level -= 1
        self.emit("}")

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

        elif isinstance(node, Comparison):
            left = self.emit_expression(node.left)
            right = self.emit_expression(node.right)

            # Map Rosh comparison operators to JavaScript
            comparison_map = {
                'equal': '===',
                'is': '===',
                'not_equal': '!==',
                'is_not': '!==',
                'below': '<',
                'less_than': '<',
                'above': '>',
                'greater_than': '>',
                'at_most': '<=',
                'less_than_or_equal': '<=',
                'at_least': '>=',
                'greater_than_or_equal': '>=',
            }

            js_op = comparison_map.get(node.operator, '===')
            return f"({left} {js_op} {right})"

        elif isinstance(node, UnaryOp):
            operand = self.emit_expression(node.operand)
            if node.operator in ['-', 'minus']:
                return f"(-{operand})"
            elif node.operator in ['not', '!']:
                return f"(!{operand})"
            else:
                raise RoshRuntimeError(
                    f"Unsupported unary operator: {node.operator}"
                )

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
        self.emit("space: this.input.keyboard.addKey(Phaser.Input.Keyboard.KeyCodes.SPACE),")
        self.emit("r: this.input.keyboard.addKey(Phaser.Input.Keyboard.KeyCodes.R)")
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
            self.emit(f"this.{obj_name}.x = {self.game_width};")
            self.indent_level -= 1
            self.emit("}")
            # Right edge
            self.emit(f"if (this.{obj_name}.x > {self.game_width}) {{")
            self.indent_level += 1
            self.emit(f"this.{obj_name}.x = 0;")
            self.indent_level -= 1
            self.emit("}")
            # Top edge
            self.emit(f"if (this.{obj_name}.y < 0) {{")
            self.indent_level += 1
            self.emit(f"this.{obj_name}.y = {self.game_height};")
            self.indent_level -= 1
            self.emit("}")
            # Bottom edge
            self.emit(f"if (this.{obj_name}.y > {self.game_height}) {{")
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
            self.emit(f"this.{obj_name}.x = Math.max(halfWidth, Math.min({self.game_width} - halfWidth, this.{obj_name}.x));")
            # Clamp y
            self.emit(f"this.{obj_name}.y = Math.max(halfHeight, Math.min({self.game_height} - halfHeight, this.{obj_name}.y));")
        self.emit_blank()

    def emit_text_object(self, name: str, properties: Dict[str, Any], x: float, y: float) -> None:
        """Generate Phaser text object for display/UI elements

        Creates a Phaser text object with configurable styling.
        Used for titles, labels, prompts, and any text-based UI.

        Args:
            name: Object name
            properties: Object properties including text, color, font_size, etc.
            x: X position (already converted from percentage)
            y: Y position (already converted from percentage)

        Text Properties:
            text: The text content to display
            color: Text color (CSS color name or hex, default: 'white')
            font_size: Font size in pixels (default: 16)
            font: Font family (default: 'Arial')
            align: Text alignment - 'left', 'center', 'right' (default: 'center')
            visible: Whether text is visible (default: true)
        """
        # Extract text properties with defaults
        text = properties.get('text', '')
        color = properties.get('color', 'white')
        font_size = properties.get('font_size', 16)
        font = properties.get('font', 'Arial')
        align = properties.get('align', 'center')
        visible = properties.get('visible', True)

        # Convert color to CSS format if it's a hex number
        if isinstance(color, int):
            color = f"#{color:06x}"
        elif isinstance(color, str) and not color.startswith('#'):
            # Keep CSS color names as-is
            pass

        # Escape text for JavaScript string
        escaped_text = str(text).replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n')

        # Build Phaser text style object
        style_parts = [
            f"fontFamily: '{font}'",
            f"fontSize: '{int(font_size)}px'",
            f"color: '{color}'",
            f"align: '{align}'"
        ]
        style_str = "{ " + ", ".join(style_parts) + " }"

        # Emit Phaser text creation
        self.emit(f"this.{name} = this.add.text({int(x)}, {int(y)}, '{escaped_text}', {style_str});")

        # Set origin based on alignment (center text on position for 'center' align)
        if align == 'center':
            self.emit(f"this.{name}.setOrigin(0.5, 0.5);")
        elif align == 'right':
            self.emit(f"this.{name}.setOrigin(1, 0.5);")
        else:  # left
            self.emit(f"this.{name}.setOrigin(0, 0.5);")

        # Handle visibility
        if not visible:
            self.emit(f"this.{name}.setVisible(false);")

        # Store custom properties for REPL access and dynamic updates
        self.emit(f"this.{name}.textContent = '{escaped_text}';")
        self.emit(f"this.{name}.font_size = {int(font_size)};")  # Track font_size for animations

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
        """Emit Phaser preload() method for loading sprites and sounds (v0.1.7+)

        Generates preload() method that loads all sprite images and audio files
        from assets/ folder. Includes error handling with fallback to colored rectangles.
        """
        self.emit("preload() {")
        self.indent_level += 1

        # Load sprites
        for obj_name, sprite_file in self.sprite_assets.items():
            self.emit(f"// Load sprite for {obj_name}")
            # Append .png extension if not already present
            if not sprite_file.endswith(('.png', '.jpg', '.jpeg', '.gif')):
                sprite_file = sprite_file + '.png'
            self.emit(f"this.load.image('{obj_name}_sprite', 'assets/{sprite_file}');")

        # v0.1.10: Load sound effects
        for sound_file in self.sound_assets:
            sound_key = sound_file.replace('.', '_').replace('/', '_')
            self.emit(f"// Load sound: {sound_file}")
            self.emit(f"this.load.audio('{sound_key}', 'assets/{sound_file}');")

        # v0.1.10: Load background music
        if self.music_file:
            music_key = self.music_file.replace('.', '_').replace('/', '_')
            self.emit(f"// Load background music")
            self.emit(f"this.load.audio('{music_key}', 'assets/{self.music_file}');")

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

            # Discrete arrow key events (for grid-based movement)
            self.emit("if (Phaser.Input.Keyboard.JustDown(this.cursors.left)) {")
            self.indent_level += 1
            self.emit("this.triggerEvent('key_left', null);")
            self.indent_level -= 1
            self.emit("}")
            self.emit("if (Phaser.Input.Keyboard.JustDown(this.cursors.right)) {")
            self.indent_level += 1
            self.emit("this.triggerEvent('key_right', null);")
            self.indent_level -= 1
            self.emit("}")
            self.emit("if (Phaser.Input.Keyboard.JustDown(this.cursors.up)) {")
            self.indent_level += 1
            self.emit("this.triggerEvent('key_up', null);")
            self.indent_level -= 1
            self.emit("}")
            self.emit("if (Phaser.Input.Keyboard.JustDown(this.cursors.down)) {")
            self.indent_level += 1
            self.emit("this.triggerEvent('key_down', null);")
            self.indent_level -= 1
            self.emit("}")
            self.emit_blank()

            # Continuous key events (for smooth movement - while_key_*)
            self.emit("if (this.cursors.left.isDown) {")
            self.indent_level += 1
            self.emit("this.triggerEvent('while_key_left', null);")
            self.indent_level -= 1
            self.emit("}")
            self.emit("if (this.cursors.right.isDown) {")
            self.indent_level += 1
            self.emit("this.triggerEvent('while_key_right', null);")
            self.indent_level -= 1
            self.emit("}")
            self.emit("if (this.cursors.up.isDown) {")
            self.indent_level += 1
            self.emit("this.triggerEvent('while_key_up', null);")
            self.indent_level -= 1
            self.emit("}")
            self.emit("if (this.cursors.down.isDown) {")
            self.indent_level += 1
            self.emit("this.triggerEvent('while_key_down', null);")
            self.indent_level -= 1
            self.emit("}")
            self.emit_blank()

            # Use this.keys.space (explicitly added in key setup)
            self.emit("if (Phaser.Input.Keyboard.JustDown(this.keys.space)) {")
            self.indent_level += 1
            self.emit("this.triggerEvent('space_pressed', null);")
            self.indent_level -= 1
            self.emit("}")

            self.emit("if (Phaser.Input.Keyboard.JustDown(this.keys.r)) {")
            self.indent_level += 1
            self.emit("this.triggerEvent('key_r', null);")
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

    def emit_repl_code(self) -> None:
        """Emit in-game REPL for live coding (v0.2.0)

        Generates:
        - DOM console overlay (HTML/CSS)
        - RoshREPL class with command parser and executor
        - Keyboard listener (backtick or F12 toggle)
        - 8 commands: set, create, get, trigger, list, describe, help, clear
        """
        self.emit_blank()
        self.emit_blank()
        self.emit_comment("=" * 70)
        self.emit_comment("⚠️  WARNING: DEVELOPMENT MODE - DO NOT SHIP TO PRODUCTION  ⚠️")
        self.emit_comment("=" * 70)
        self.emit_comment("IN-GAME REPL (v0.2.0) - LIVE CODING CONSOLE")
        self.emit_comment("")
        self.emit_comment("This code allows arbitrary command execution in the browser.")
        self.emit_comment("Only use this build for local development and trusted demos.")
        self.emit_comment("")
        self.emit_comment("To disable: Remove --repl flag from build command")
        self.emit_comment("=" * 70)
        self.emit_blank()

        # Emit DEV_MODE constant
        self.emit("const ROSH_DEV_MODE = true;")
        self.emit_blank()

        # 1. Inject DOM overlay CSS/HTML (wrapped in DEV_MODE check)
        self.emit("if (ROSH_DEV_MODE) {")
        self.indent_level += 1
        self.emit_repl_dom_overlay()

        # 2. Generate RoshREPL class
        self.emit_repl_class()

        # 3. Initialize REPL after game is ready
        self.emit_repl_initialization()

        # Close DEV_MODE guard
        self.indent_level -= 1
        self.emit("}")
        self.emit_blank()
        self.emit_comment("END DEV MODE")
        self.emit_blank()

    def emit_repl_dom_overlay(self) -> None:
        """Generate DOM overlay HTML/CSS for REPL console"""
        self.emit_comment("Inject DOM overlay for REPL console")
        self.emit("(function() {")
        self.indent_level += 1

        # CSS Styles
        self.emit_comment("CSS Styles")
        self.emit("const style = document.createElement('style');")
        self.emit("style.textContent = `")
        self.emit("#rosh-console {")
        self.emit("    position: fixed;")
        self.emit("    bottom: 0;")
        self.emit("    left: 0;")
        self.emit("    width: 100%;")
        self.emit("    height: 300px;")
        self.emit("    background: rgba(0, 0, 0, 0.95);")
        self.emit("    color: #00ff00;")
        self.emit("    font-family: 'Courier New', monospace;")
        self.emit("    font-size: 14px;")
        self.emit("    border-top: 2px solid #00ff00;")
        self.emit("    display: none;")
        self.emit("    flex-direction: column;")
        self.emit("    z-index: 10000;")
        self.emit("    overflow: hidden;")
        self.emit("}")
        self.emit("#rosh-console.visible {")
        self.emit("    display: flex;")
        self.emit("}")
        self.emit("#rosh-console-header {")
        self.emit("    padding: 8px 12px;")
        self.emit("    background: #1a1a1a;")
        self.emit("    border-bottom: 1px solid #00ff00;")
        self.emit("    display: flex;")
        self.emit("    justify-content: space-between;")
        self.emit("    align-items: center;")
        self.emit("}")
        self.emit("#rosh-console-header strong {")
        self.emit("    color: #00ff00;")
        self.emit("}")
        self.emit("#rosh-console-header small {")
        self.emit("    color: #888;")
        self.emit("}")
        self.emit("#rosh-console-output {")
        self.emit("    flex: 1;")
        self.emit("    overflow-y: auto;")
        self.emit("    padding: 10px;")
        self.emit("    font-size: 13px;")
        self.emit("    line-height: 1.4;")
        self.emit("    position: relative;")
        self.emit("}")
        self.emit("#rosh-console-output > div {")
        self.emit("    position: static;")
        self.emit("    margin: 2px 0;")
        self.emit("}")
        self.emit("#rosh-console-output .command { color: #ffff00; }")
        self.emit("#rosh-console-output .success { color: #33ff33; }")
        self.emit("#rosh-console-output .error { color: #ff3333; }")
        self.emit("#rosh-console-output .info { color: #00ffff; }")
        self.emit("#rosh-console-input {")
        self.emit("    padding: 10px;")
        self.emit("    border-top: 1px solid #00ff00;")
        self.emit("    display: flex;")
        self.emit("    gap: 8px;")
        self.emit("    align-items: center;")
        self.emit("}")
        self.emit("#rosh-console-input .prompt {")
        self.emit("    color: #00ff00;")
        self.emit("    font-weight: bold;")
        self.emit("}")
        self.emit("#rosh-console-input input {")
        self.emit("    flex: 1;")
        self.emit("    background: #1a1a1a;")
        self.emit("    border: 1px solid #00ff00;")
        self.emit("    color: #00ff00;")
        self.emit("    padding: 6px 8px;")
        self.emit("    font-family: 'Courier New', monospace;")
        self.emit("    font-size: 14px;")
        self.emit("    outline: none;")
        self.emit("}")
        self.emit("#rosh-console-input input:focus {")
        self.emit("    border-color: #33ff33;")
        self.emit("    box-shadow: 0 0 5px rgba(0, 255, 0, 0.3);")
        self.emit("}")
        self.emit("`;")
        self.emit("document.head.appendChild(style);")
        self.emit_blank()

        # HTML Structure (create programmatically for reliability)
        self.emit_comment("HTML Structure")
        self.emit("const consoleDiv = document.createElement('div');")
        self.emit("consoleDiv.id = 'rosh-console';")
        self.emit_blank()
        self.emit("// Header")
        self.emit("const headerDiv = document.createElement('div');")
        self.emit("headerDiv.id = 'rosh-console-header';")
        self.emit("headerDiv.innerHTML = '<strong>🎮 ROSH CONSOLE</strong><small>Press ` or F12 to toggle | Type \\'help\\' for commands</small>';")
        self.emit("consoleDiv.appendChild(headerDiv);")
        self.emit_blank()
        self.emit("// Output area")
        self.emit("const outputDiv = document.createElement('div');")
        self.emit("outputDiv.id = 'rosh-console-output';")
        self.emit("consoleDiv.appendChild(outputDiv);")
        self.emit_blank()
        self.emit("// Input area")
        self.emit("const inputDiv = document.createElement('div');")
        self.emit("inputDiv.id = 'rosh-console-input';")
        self.emit("inputDiv.innerHTML = '<span class=\"prompt\">rosh></span><input type=\"text\" id=\"rosh-input\" placeholder=\"Enter command...\">';")
        self.emit("consoleDiv.appendChild(inputDiv);")
        self.emit_blank()
        self.emit("document.body.appendChild(consoleDiv);")

        self.indent_level -= 1
        self.emit("})();")
        self.emit_blank()

    def emit_repl_class(self) -> None:
        """Generate RoshREPL JavaScript class with parser and executor"""
        self.emit_comment("RoshREPL Class")
        self.emit("class RoshREPL {")
        self.indent_level += 1

        # Constructor
        self.emit("constructor(scene) {")
        self.indent_level += 1
        self.emit("this.scene = scene;")
        self.emit("this.consoleVisible = false;")
        self.emit("this.commandHistory = [];")
        self.emit("this.historyIndex = -1;")
        self.emit("this.currentObject = null;")
        self.emit("this.currentObjectName = null;")
        self.emit("this.setupKeyboard();")
        self.emit("this.setupInput();")
        self.emit("this.log('🎮 Rosh Console ready! Type \"help\" for commands.', 'info');")
        self.indent_level -= 1
        self.emit("}")
        self.emit_blank()

        # Setup keyboard
        self.emit("setupKeyboard() {")
        self.indent_level += 1
        self.emit("document.addEventListener('keydown', (e) => {")
        self.indent_level += 1
        self.emit("// Block all game input when console is active")
        self.emit("if (this.consoleVisible && e.target.id !== 'rosh-input') {")
        self.indent_level += 1
        self.emit("// Don't block toggle keys")
        self.emit("if (e.key !== '`' && e.key !== 'F12') {")
        self.indent_level += 1
        self.emit("e.stopPropagation();")
        self.emit("e.preventDefault();")
        self.emit("// Focus console input")
        self.emit("document.getElementById('rosh-input').focus();")
        self.emit("return;")
        self.indent_level -= 1
        self.emit("}")
        self.indent_level -= 1
        self.emit("}")
        self.emit_blank()
        self.emit("// Toggle console with backtick or F12")
        self.emit("if (e.key === '`' || e.key === 'F12') {")
        self.indent_level += 1
        self.emit("e.preventDefault();")
        self.emit("this.toggleConsole();")
        self.indent_level -= 1
        self.emit("}")
        self.indent_level -= 1
        self.emit("});")
        self.indent_level -= 1
        self.emit("}")
        self.emit_blank()

        # Setup input
        self.emit("setupInput() {")
        self.indent_level += 1
        self.emit("const input = document.getElementById('rosh-input');")
        self.emit("input.addEventListener('keydown', (e) => {")
        self.indent_level += 1
        self.emit("if (e.key === 'Enter') {")
        self.indent_level += 1
        self.emit("const cmd = input.value.trim();")
        self.emit("if (cmd) {")
        self.indent_level += 1
        self.emit("this.executeCommand(cmd);")
        self.emit("this.commandHistory.push(cmd);")
        self.emit("this.historyIndex = this.commandHistory.length;")
        self.emit("input.value = '';")
        self.indent_level -= 1
        self.emit("}")
        self.indent_level -= 1
        self.emit("} else if (e.key === 'ArrowUp') {")
        self.indent_level += 1
        self.emit("e.preventDefault();")
        self.emit("if (this.historyIndex > 0) {")
        self.indent_level += 1
        self.emit("this.historyIndex--;")
        self.emit("input.value = this.commandHistory[this.historyIndex];")
        self.indent_level -= 1
        self.emit("}")
        self.indent_level -= 1
        self.emit("} else if (e.key === 'ArrowDown') {")
        self.indent_level += 1
        self.emit("e.preventDefault();")
        self.emit("if (this.historyIndex < this.commandHistory.length - 1) {")
        self.indent_level += 1
        self.emit("this.historyIndex++;")
        self.emit("input.value = this.commandHistory[this.historyIndex];")
        self.indent_level -= 1
        self.emit("} else {")
        self.indent_level += 1
        self.emit("this.historyIndex = this.commandHistory.length;")
        self.emit("input.value = '';")
        self.indent_level -= 1
        self.emit("}")
        self.indent_level -= 1
        self.emit("}")
        self.indent_level -= 1
        self.emit("});")
        self.indent_level -= 1
        self.emit("}")
        self.emit_blank()

        # Toggle console
        self.emit("toggleConsole() {")
        self.indent_level += 1
        self.emit("const console = document.getElementById('rosh-console');")
        self.emit("this.consoleVisible = !this.consoleVisible;")
        self.emit("console.classList.toggle('visible');")
        self.emit("if (this.consoleVisible) {")
        self.indent_level += 1
        self.emit("// Disable Phaser keyboard input when console opens")
        self.emit("this.scene.input.keyboard.enabled = false;")
        self.emit("document.getElementById('rosh-input').focus();")
        self.indent_level -= 1
        self.emit("} else {")
        self.indent_level += 1
        self.emit("// Re-enable Phaser keyboard input when console closes")
        self.emit("this.scene.input.keyboard.enabled = true;")
        self.indent_level -= 1
        self.emit("}")
        self.indent_level -= 1
        self.emit("}")
        self.emit_blank()

        # Log method
        self.emit("log(message, type = 'info') {")
        self.indent_level += 1
        self.emit("const output = document.getElementById('rosh-console-output');")
        self.emit("if (!output) {")
        self.indent_level += 1
        self.emit("console.error('[REPL Error] Console output div not found!');")
        self.emit("return;")
        self.indent_level -= 1
        self.emit("}")
        self.emit("const line = document.createElement('div');")
        self.emit("line.className = type;")
        self.emit("line.textContent = message;")
        self.emit("output.appendChild(line);")
        self.emit("output.scrollTop = output.scrollHeight;")
        self.indent_level -= 1
        self.emit("}")
        self.emit_blank()

        # Execute command
        self.emit("executeCommand(cmd) {")
        self.indent_level += 1
        self.emit("this.log(`> ${cmd}`, 'command');")
        self.emit("try {")
        self.indent_level += 1
        self.emit("// Parse command")
        self.emit("const lower = cmd.toLowerCase().trim();")
        self.emit("const firstWord = lower.split(' ')[0];")
        self.emit("console.log('[REPL Debug] Command:', cmd, '| Lower:', lower, '| FirstWord:', firstWord);")
        self.emit_blank()
        self.emit("// Help command")
        self.emit("if (lower === 'help' || lower === '?') {")
        self.indent_level += 1
        self.emit("this.cmdHelp();")
        self.indent_level -= 1
        self.emit("}")
        self.emit("// Clear command")
        self.emit("else if (lower === 'clear' || lower === 'cls') {")
        self.indent_level += 1
        self.emit("this.cmdClear();")
        self.indent_level -= 1
        self.emit("}")
        self.emit("// List objects command (aliases: list, look, show, objects, ls)")
        self.emit("else if (lower === 'list' || lower === 'list objects' || lower === 'look' || lower === 'show' || lower === 'objects' || lower === 'ls') {")
        self.indent_level += 1
        self.emit("this.cmdListObjects();")
        self.indent_level -= 1
        self.emit("}")
        self.emit("// Set command: set [object.]property [to] value")
        self.emit("else if (lower.startsWith('set ')) {")
        self.indent_level += 1
        self.emit("// Try 'set obj.prop to value' or 'set obj prop to value' or 'set prop to value' or 'set prop value'")
        self.emit("const cmdNorm = cmd.replace(/\\s+to\\s+/i, ' ');")
        self.emit("const setParts = cmdNorm.slice(4).trim().split(/[\\s.]+/);")
        self.emit("if (setParts.length >= 2) {")
        self.indent_level += 1
        self.emit("// Check if first part is an object name or a property")
        self.emit("const firstPart = setParts[0];")
        self.emit("if (this.scene[firstPart]) {")
        self.indent_level += 1
        self.emit("// obj.prop value or obj prop value")
        self.emit("const target = setParts.length >= 3 ? firstPart + '.' + setParts[1] : firstPart;")
        self.emit("const value = setParts.slice(setParts.length >= 3 ? 2 : 1).join(' ');")
        self.emit("this.cmdSet(target, value);")
        self.indent_level -= 1
        self.emit("} else if (this.currentObject) {")
        self.indent_level += 1
        self.emit("// prop value (use current object)")
        self.emit("const target = this.currentObjectName + '.' + firstPart;")
        self.emit("const value = setParts.slice(1).join(' ');")
        self.emit("this.cmdSet(target, value);")
        self.indent_level -= 1
        self.emit("} else {")
        self.indent_level += 1
        self.emit("throw new Error('Usage: set <property> <value> (after get <object>) or set <object>.<property> <value>');")
        self.indent_level -= 1
        self.emit("}")
        self.indent_level -= 1
        self.emit("} else {")
        self.indent_level += 1
        self.emit("throw new Error('Usage: set <property> <value>');")
        self.indent_level -= 1
        self.emit("}")
        self.indent_level -= 1
        self.emit("}")
        self.emit("// Get command: get object.property (alias: show)")
        self.emit("else if (lower.startsWith('get ') || lower.startsWith('show ')) {")
        self.indent_level += 1
        self.emit("const target = cmd.slice(firstWord.length + 1).trim();")
        self.emit("this.cmdGet(target);")
        self.indent_level -= 1
        self.emit("}")
        self.emit("// Create object command: create object name at x, y")
        self.emit("else if (lower.startsWith('create object ') || lower.startsWith('create ')) {")
        self.indent_level += 1
        self.emit("// Accept both 'at 200, 200' and 'at 200 200' (comma optional)")
        self.emit("const match = cmd.match(/^create(?:\\s+object)?\\s+(\\w+)(?:\\s+at\\s+(\\d+)(?:\\s*,\\s*|\\s+)(\\d+))?$/i);")
        self.emit("if (match) this.cmdCreateObject(match[1], match[2], match[3]);")
        self.emit("else throw new Error('Usage: create name at x y (or x, y)');")
        self.indent_level -= 1
        self.emit("}")
        self.emit("// Describe command: describe object (aliases: inspect, properties, info)")
        self.emit("else if (lower.startsWith('describe ') || lower.startsWith('inspect ') || lower.startsWith('properties ') || lower.startsWith('info ')) {")
        self.indent_level += 1
        self.emit("const target = cmd.slice(firstWord.length + 1).trim();")
        self.emit("this.cmdDescribe(target);")
        self.indent_level -= 1
        self.emit("}")
        self.emit("// Trigger command: trigger event (alias: fire)")
        self.emit("else if (lower.startsWith('trigger') || lower.startsWith('fire')) {")
        self.indent_level += 1
        self.emit("const event = cmd.slice(firstWord.length + 1).trim();")
        self.emit("if (!event) {")
        self.indent_level += 1
        self.emit("throw new Error('Usage: trigger <event_name> (e.g., trigger attack)');")
        self.indent_level -= 1
        self.emit("}")
        self.emit("this.cmdTrigger(event);")
        self.indent_level -= 1
        self.emit("}")
        self.emit("else {")
        self.indent_level += 1
        self.emit("// Fuzzy matching for typos")
        self.emit("const suggestions = this.getSuggestions(firstWord);")
        self.emit("if (suggestions.length > 0) {")
        self.indent_level += 1
        self.emit("throw new Error(`Unknown command: ${firstWord}. Did you mean: ${suggestions.join(', ')}?`);")
        self.indent_level -= 1
        self.emit("} else {")
        self.indent_level += 1
        self.emit("throw new Error(`Unknown command: ${firstWord}. Type 'help' for commands.`);")
        self.indent_level -= 1
        self.emit("}")
        self.indent_level -= 1
        self.emit("}")
        self.indent_level -= 1
        self.emit("} catch (error) {")
        self.indent_level += 1
        self.emit("this.log(`✗ ${error.message}`, 'error');")
        self.indent_level -= 1
        self.emit("}")
        self.indent_level -= 1
        self.emit("}")
        self.emit_blank()

        # Fuzzy matching helper
        self.emit("// Fuzzy matching for typos")
        self.emit("getSuggestions(word) {")
        self.indent_level += 1
        self.emit("const commands = ['help', 'clear', 'list', 'look', 'set', 'get', 'create', 'describe', 'properties', 'inspect', 'trigger', 'fire', 'show', 'info'];")
        self.emit("const levenshtein = (a, b) => {")
        self.indent_level += 1
        self.emit("const matrix = [];")
        self.emit("for (let i = 0; i <= b.length; i++) matrix[i] = [i];")
        self.emit("for (let j = 0; j <= a.length; j++) matrix[0][j] = j;")
        self.emit("for (let i = 1; i <= b.length; i++) {")
        self.indent_level += 1
        self.emit("for (let j = 1; j <= a.length; j++) {")
        self.indent_level += 1
        self.emit("if (b.charAt(i - 1) === a.charAt(j - 1)) {")
        self.indent_level += 1
        self.emit("matrix[i][j] = matrix[i - 1][j - 1];")
        self.indent_level -= 1
        self.emit("} else {")
        self.indent_level += 1
        self.emit("matrix[i][j] = Math.min(matrix[i - 1][j - 1] + 1, Math.min(matrix[i][j - 1] + 1, matrix[i - 1][j] + 1));")
        self.indent_level -= 1
        self.emit("}")
        self.indent_level -= 1
        self.emit("}")
        self.indent_level -= 1
        self.emit("}")
        self.emit("return matrix[b.length][a.length];")
        self.indent_level -= 1
        self.emit("};")
        self.emit("return commands.filter(cmd => levenshtein(word, cmd) <= 2).slice(0, 3);")
        self.indent_level -= 1
        self.emit("}")
        self.emit_blank()

        # Command implementations
        self.emit("// Command: help")
        self.emit("cmdHelp() {")
        self.indent_level += 1
        self.emit("this.log('🎮 ROSH CONSOLE - Available Commands:', 'info');")
        self.emit("this.log('', 'info');")
        self.emit("this.log('  list / look / ls              - Show all objects', 'info');")
        self.emit("this.log('  describe / properties / info  - Show object properties', 'info');")
        self.emit("this.log('  get <obj>                     - Get object (display)', 'info');")
        self.emit("this.log('  get <obj> <prop>              - Get property value', 'info');")
        self.emit("this.log('  get <uuid>                    - Get by UUID (8+ chars)', 'info');")
        self.emit("this.log('  set <obj.prop> to <value>     - Change property', 'info');")
        self.emit("this.log('  create <name> at <x> <y>      - Create new object', 'info');")
        self.emit("this.log('  trigger / fire <event>        - Fire event', 'info');")
        self.emit("this.log('  clear / cls                   - Clear console', 'info');")
        self.emit("this.log('  help / ?                      - Show this help', 'info');")
        self.emit("this.log('', 'info');")
        self.emit("this.log('💡 Tip: Commands are natural language friendly!', 'info');")
        self.indent_level -= 1
        self.emit("}")
        self.emit_blank()

        self.emit("// Command: clear")
        self.emit("cmdClear() {")
        self.indent_level += 1
        self.emit("document.getElementById('rosh-console-output').innerHTML = '';")
        self.emit("this.log('Console cleared', 'success');")
        self.indent_level -= 1
        self.emit("}")
        self.emit_blank()

        self.emit("// Command: list objects")
        self.emit("cmdListObjects() {")
        self.indent_level += 1
        self.emit("const objects = Object.keys(this.scene).filter(k => ")
        self.emit("    this.scene[k] && typeof this.scene[k] === 'object' && this.scene[k].x !== undefined")
        self.emit(");")
        self.emit("if (objects.length === 0) {")
        self.indent_level += 1
        self.emit("this.log('No objects found', 'info');")
        self.indent_level -= 1
        self.emit("} else {")
        self.indent_level += 1
        self.emit("this.log(`Found ${objects.length} object(s):`, 'info');")
        self.emit("objects.forEach(name => this.log(`  - ${name}`, 'info'));")
        self.indent_level -= 1
        self.emit("}")
        self.indent_level -= 1
        self.emit("}")
        self.emit_blank()

        self.emit("// Command: set")
        self.emit("cmdSet(target, value) {")
        self.indent_level += 1
        self.emit("const obj = this.getProperty(target, true);")
        self.emit("if (obj.error) throw new Error(obj.error);")
        self.emit_blank()
        self.emit("// Evaluate value (simple number/string/boolean parsing)")
        self.emit("let evaluatedValue = value.trim();")
        self.emit_blank()
        self.emit("// Handle 'middle' alias (converts to 50%)")
        self.emit("if (evaluatedValue.toLowerCase() === 'middle') {")
        self.indent_level += 1
        self.emit("evaluatedValue = '50%';")
        self.indent_level -= 1
        self.emit("}")
        self.emit_blank()
        self.emit("// Handle percentages (convert to pixels based on canvas size)")
        self.emit("if (evaluatedValue.endsWith('%')) {")
        self.indent_level += 1
        self.emit("const percent = parseFloat(evaluatedValue.slice(0, -1));")
        self.emit("const prop = target.split('.').pop();")
        self.emit("if (prop === 'x' || prop === 'width') {")
        self.indent_level += 1
        self.emit(f"evaluatedValue = (percent / 100) * {self.game_width};")
        self.indent_level -= 1
        self.emit("} else if (prop === 'y' || prop === 'height') {")
        self.indent_level += 1
        self.emit(f"evaluatedValue = (percent / 100) * {self.game_height};")
        self.indent_level -= 1
        self.emit("} else {")
        self.indent_level += 1
        self.emit("throw new Error('Percentages only work for x, y, width, height properties');")
        self.indent_level -= 1
        self.emit("}")
        self.indent_level -= 1
        self.emit("}")
        self.emit("// Handle boolean literals")
        self.emit("else if (evaluatedValue === 'true') evaluatedValue = true;")
        self.emit("else if (evaluatedValue === 'false') evaluatedValue = false;")
        self.emit("else if (evaluatedValue === 'null') evaluatedValue = null;")
        self.emit("// Handle numbers")
        self.emit("else if (!isNaN(evaluatedValue)) evaluatedValue = parseFloat(evaluatedValue);")
        self.emit("// Handle quoted strings")
        self.emit("else if (evaluatedValue.startsWith('\"') && evaluatedValue.endsWith('\"')) {")
        self.indent_level += 1
        self.emit("evaluatedValue = evaluatedValue.slice(1, -1);")
        self.indent_level -= 1
        self.emit("}")
        self.emit_blank()
        self.emit("// Set the value")
        self.emit("const parts = target.split('.');")
        self.emit("const prop = parts[parts.length - 1];")
        self.emit("obj.parent[prop] = evaluatedValue;")
        self.emit("this.log(`✓ Set ${target} = ${evaluatedValue}`, 'success');")
        self.indent_level -= 1
        self.emit("}")
        self.emit_blank()

        self.emit("// Command: get (unified - supports space syntax, dot syntax, and UUID)")
        self.emit("cmdGet(target) {")
        self.indent_level += 1
        self.emit("// Parse target - could be 'book', 'book color', 'book.color', or UUID")
        self.emit("const parts = target.trim().split(/[\\s.]+/);")
        self.emit("const objName = parts[0];")
        self.emit("const propName = parts[1] || null;")
        self.emit_blank()
        self.emit("// Find object by name or UUID")
        self.emit("let obj = this.scene[objName];")
        self.emit("let foundName = objName;")
        self.emit_blank()
        self.emit("// If not found by name, try UUID lookup (8+ chars)")
        self.emit("if (!obj && objName.length >= 8) {")
        self.indent_level += 1
        self.emit("for (const key of Object.keys(this.scene)) {")
        self.indent_level += 1
        self.emit("const sceneObj = this.scene[key];")
        self.emit("if (sceneObj && sceneObj._rosh_uuid && sceneObj._rosh_uuid.startsWith(objName)) {")
        self.indent_level += 1
        self.emit("obj = sceneObj;")
        self.emit("foundName = key;")
        self.emit("break;")
        self.indent_level -= 1
        self.emit("}")
        self.indent_level -= 1
        self.emit("}")
        self.indent_level -= 1
        self.emit("}")
        self.emit_blank()
        self.emit("if (!obj) {")
        self.indent_level += 1
        self.emit("// Suggest available objects")
        self.emit("const available = Object.keys(this.scene).filter(k => !k.startsWith('_') && typeof this.scene[k] === 'object');")
        self.emit("const suggestions = this.getSuggestions(objName);")
        self.emit("if (suggestions.length > 0) {")
        self.indent_level += 1
        self.emit("throw new Error(`Object '${objName}' not found. Did you mean: ${suggestions.join(', ')}?`);")
        self.indent_level -= 1
        self.emit("} else if (available.length > 0) {")
        self.indent_level += 1
        self.emit("throw new Error(`Object '${objName}' not found. Available: ${available.slice(0, 5).join(', ')}`);")
        self.indent_level -= 1
        self.emit("} else {")
        self.indent_level += 1
        self.emit("throw new Error(`Object '${objName}' not found`);")
        self.indent_level -= 1
        self.emit("}")
        self.indent_level -= 1
        self.emit("}")
        self.emit_blank()
        self.emit("// If no property requested, return the object and set as current")
        self.emit("if (!propName) {")
        self.indent_level += 1
        self.emit("this.currentObject = obj;")
        self.emit("this.currentObjectName = foundName;")
        self.emit("const objType = obj.type || 'object';")
        self.emit("this.log(`<${objType}: ${foundName}>`, 'success');")
        self.emit("return;")
        self.indent_level -= 1
        self.emit("}")
        self.emit_blank()
        self.emit("// Special case: uuid property")
        self.emit("if (propName.toLowerCase() === 'uuid') {")
        self.indent_level += 1
        self.emit("if (obj._rosh_uuid) {")
        self.indent_level += 1
        self.emit("this.log(obj._rosh_uuid, 'success');")
        self.indent_level -= 1
        self.emit("} else {")
        self.indent_level += 1
        self.emit("throw new Error(`Object '${foundName}' has no UUID`);")
        self.indent_level -= 1
        self.emit("}")
        self.emit("return;")
        self.indent_level -= 1
        self.emit("}")
        self.emit_blank()
        self.emit("// Get the property value")
        self.emit("const value = obj[propName];")
        self.emit("if (value === undefined) {")
        self.indent_level += 1
        self.emit("// Suggest available properties")
        self.emit("const props = Object.keys(obj).filter(k => !k.startsWith('_') && typeof obj[k] !== 'function');")
        self.emit("throw new Error(`Property '${propName}' not found on '${foundName}'. Available: ${props.slice(0, 5).join(', ')}`);")
        self.indent_level -= 1
        self.emit("}")
        self.emit_blank()
        self.emit("// Display the value")
        self.emit("const displayValue = typeof value === 'number' ? value.toFixed(2) : JSON.stringify(value);")
        self.emit("this.log(displayValue, 'success');")
        self.indent_level -= 1
        self.emit("}")
        self.emit_blank()

        self.emit("// Command: create object")
        self.emit("cmdCreateObject(name, x = '400', y = '300') {")
        self.indent_level += 1
        self.emit("if (this.scene[name]) {")
        self.indent_level += 1
        self.emit("throw new Error(`Object '${name}' already exists`);")
        self.indent_level -= 1
        self.emit("}")
        self.emit_blank()
        self.emit("// Handle 'middle' alias for coordinates")
        self.emit("if (x.toLowerCase() === 'middle') x = '50%';")
        self.emit("if (y.toLowerCase() === 'middle') y = '50%';")
        self.emit_blank()
        self.emit("// Handle percentage values")
        self.emit("let xPos = parseInt(x);")
        self.emit("let yPos = parseInt(y);")
        self.emit("if (typeof x === 'string' && x.endsWith('%')) {")
        self.indent_level += 1
        self.emit(f"xPos = (parseFloat(x.slice(0, -1)) / 100) * {self.game_width};")
        self.indent_level -= 1
        self.emit("}")
        self.emit("if (typeof y === 'string' && y.endsWith('%')) {")
        self.indent_level += 1
        self.emit(f"yPos = (parseFloat(y.slice(0, -1)) / 100) * {self.game_height};")
        self.indent_level -= 1
        self.emit("}")
        self.emit_blank()
        self.emit("this.scene[name] = this.scene.add.rectangle(xPos, yPos, 50, 50, 0xff00ff);")
        self.emit("// Assign UUID to console-created objects")
        self.emit("this.scene[name]._rosh_uuid = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {")
        self.indent_level += 1
        self.emit("const r = Math.random() * 16 | 0;")
        self.emit("return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);")
        self.indent_level -= 1
        self.emit("});")
        self.emit("this.log(`✓ Created object '${name}' at (${xPos}, ${yPos})`, 'success');")
        self.indent_level -= 1
        self.emit("}")
        self.emit_blank()

        self.emit("// Command: describe")
        self.emit("cmdDescribe(target) {")
        self.indent_level += 1
        self.emit("console.log('[cmdDescribe] Called with target:', target);")
        self.emit("console.log('[cmdDescribe] this.scene:', this.scene);")
        self.emit("const obj = this.scene[target];")
        self.emit("console.log('[cmdDescribe] Found obj:', obj);")
        self.emit("if (!obj) throw new Error(`Object '${target}' not found`);")
        self.emit_blank()
        self.emit("this.log(`Object: ${target}`, 'info');")
        self.emit("console.log('[cmdDescribe] Logged object header');")
        self.emit_blank()
        self.emit("// Show common game properties first")
        self.emit("const commonProps = ['x', 'y', 'width', 'height', 'displayWidth', 'displayHeight', 'lives', 'score', 'speed', 'health', 'alpha', 'rotation', 'scale', 'visible'];")
        self.emit("const found = [];")
        self.emit("commonProps.forEach(prop => {")
        self.indent_level += 1
        self.emit("if (obj[prop] !== undefined) {")
        self.indent_level += 1
        self.emit("const val = typeof obj[prop] === 'number' ? obj[prop].toFixed(2) : obj[prop];")
        self.emit("this.log(`  ${prop}: ${val}`, 'info');")
        self.emit("found.push(prop);")
        self.indent_level -= 1
        self.emit("}")
        self.indent_level -= 1
        self.emit("});")
        self.emit_blank()
        self.emit("// Show other custom properties (excluding Phaser internals)")
        self.emit("const otherProps = Object.keys(obj).filter(k => {")
        self.indent_level += 1
        self.emit("return !k.startsWith('_') && ")
        self.emit("       !found.includes(k) && ")
        self.emit("       typeof obj[k] !== 'function' && ")
        self.emit("       typeof obj[k] !== 'object';")
        self.indent_level -= 1
        self.emit("});")
        self.emit("if (otherProps.length > 0) {")
        self.indent_level += 1
        self.emit("this.log('  Other properties:', 'info');")
        self.emit("otherProps.forEach(prop => {")
        self.indent_level += 1
        self.emit("this.log(`    ${prop}: ${obj[prop]}`, 'info');")
        self.indent_level -= 1
        self.emit("});")
        self.indent_level -= 1
        self.emit("}")
        self.indent_level -= 1
        self.emit("}")
        self.emit_blank()

        self.emit("// Command: trigger")
        self.emit("cmdTrigger(event) {")
        self.indent_level += 1
        self.emit("if (typeof this.scene.triggerEvent === 'function') {")
        self.indent_level += 1
        self.emit("this.scene.triggerEvent(event, null);")
        self.emit("this.log(`✓ Triggered event: ${event}`, 'success');")
        self.indent_level -= 1
        self.emit("} else {")
        self.indent_level += 1
        self.emit("throw new Error('Event system not available in this game');")
        self.indent_level -= 1
        self.emit("}")
        self.indent_level -= 1
        self.emit("}")
        self.emit_blank()

        # Helper: getProperty
        self.emit("// Helper: get property by path (e.g., 'player.x')")
        self.emit("getProperty(path, returnParent = false) {")
        self.indent_level += 1
        self.emit("const parts = path.split('.');")
        self.emit("let obj = this.scene;")
        self.emit("let parent = null;")
        self.emit_blank()
        self.emit("for (let i = 0; i < parts.length; i++) {")
        self.indent_level += 1
        self.emit("parent = obj;")
        self.emit("obj = obj[parts[i]];")
        self.emit("if (obj === undefined) {")
        self.indent_level += 1
        self.emit("return { error: `Property '${parts.slice(0, i + 1).join('.')}' not found` };")
        self.indent_level -= 1
        self.emit("}")
        self.indent_level -= 1
        self.emit("}")
        self.emit_blank()
        self.emit("return returnParent ? { parent, value: obj } : { value: obj };")
        self.indent_level -= 1
        self.emit("}")

        self.indent_level -= 1
        self.emit("}")
        self.emit_blank()

    def emit_repl_initialization(self) -> None:
        """Initialize REPL after game is created"""
        self.emit_comment("Initialize REPL")
        self.emit("window.addEventListener('load', () => {")
        self.indent_level += 1
        self.emit("// Wait for game scene to be ready")
        self.emit("setTimeout(() => {")
        self.indent_level += 1
        self.emit("const scene = game.scene.scenes[0];")
        self.emit("if (scene) {")
        self.indent_level += 1
        self.emit("window.roshREPL = new RoshREPL(scene);")
        self.emit("console.log('🎮 Rosh Console initialized. Press ` or F12 to toggle.');")
        self.indent_level -= 1
        self.emit("}")
        self.indent_level -= 1
        self.emit("}, 100);")
        self.indent_level -= 1
        self.emit("});")
        self.emit_blank()
        self.emit_comment("END REPL")
