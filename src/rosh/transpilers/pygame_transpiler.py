"""
Pygame Transpiler

Transpile Rosh code to Pygame Python for native desktop games.

This transpiler generates standalone Python scripts that use Pygame
for rendering, input, and game loop. No server required - just run
with `python game.py`.

Scope (Phase 2 - v0.1.9):
- Grid-based collision only (coordinate math like Block Pusher)
- Physics-based sprite collision deferred to Phase 3+
- Input fires once per press (matches Phaser JustDown behavior)
- Sound effects: play sound "file.wav"
- Background music: play music "file.ogg" / stop music
"""

from typing import Dict, Any, List, Optional
from .base import BaseTranspiler
from ..ast_nodes import *
from ..errors import RoshRuntimeError


class PygameTranspiler(BaseTranspiler):
    """Transpile Rosh code to Pygame Python

    Phase 2 Features (v0.1.9):
    - Objects (create object ... end) → Pygame rectangles/circles
    - Properties (set x to 100) → Object initialization
    - Text objects → Pygame font rendering
    - Key events (key_left, key_right, etc.) → KEYDOWN handling
    - Continuous movement (while_key_left, etc.) → held key polling
    - Per-frame updates (when update then) → game loop integration
    - Functions (define function ... end) → Python methods
    - If/else statements → Python conditionals
    - Sprites (set sprite to "file.png") → Image loading
    - Sound effects (play sound "file.wav") → Cached playback
    - Background music (play music "file.ogg") → Looped playback

    Limitations:
    - Grid-based collision only (no physics)
    - No sprite animation
    """

    # Auto-assigned colors for objects (RGB tuples for Pygame)
    DEFAULT_COLORS = {
        0: (0, 255, 0),    # Green
        1: (0, 0, 255),    # Blue
        2: (255, 0, 0),    # Red
        3: (255, 255, 0),  # Yellow
        4: (255, 0, 255),  # Magenta
        5: (0, 255, 255),  # Cyan
        6: (255, 136, 0),  # Orange
        7: (136, 0, 255),  # Purple
    }

    # Game canvas dimensions
    GAME_WIDTH = 800
    GAME_HEIGHT = 600

    # Base type templates for inheritance
    BASE_TYPES = {
        'player': {
            'lives': 3,
            'score': 0,
            'speed': 5,
            'width': 30,
            'height': 30,
            'color': (0, 255, 0),  # Green
        },
        'character': {},
        'object': {}
    }

    def __init__(self):
        super().__init__()
        self.object_counter = 0
        self.object_properties: Dict[str, Dict[str, Any]] = {}
        self.event_handlers: Dict[str, list] = {}
        self.needs_keyboard_input = False
        self.player_objects = []
        self.sprite_assets: Dict[str, str] = {}
        self.functions: List[FunctionDef] = []
        self.text_objects: List[str] = []
        self.uses_sound = False
        self.uses_music = False
        self.sound_files: List[str] = []

    def emit_comment(self, comment: str) -> None:
        """Override for Python-style comments"""
        self.emit(f"# {comment}")

    def transpile(self, program: Program) -> str:
        """Convert Rosh Program AST to Pygame Python

        Args:
            program: Rosh Program AST node

        Returns:
            Generated Python code
        """
        # 1. Validate AST
        self.validate_ast(program)

        # 2. Detect features
        self.detect_features(program)

        # 3. Generate header
        self.emit("#!/usr/bin/env python3")
        self.emit_comment("Auto-generated from Rosh code")
        self.emit_comment("Transpiled with Rosh Pygame Transpiler v0.1.10")
        self.emit_blank()

        # 4. Imports
        self.emit("import pygame")
        self.emit("import sys")
        self.emit("from pathlib import Path")
        self.emit_blank()

        # 5. Asset path helper
        self.emit_comment("Asset path resolution (relative to script)")
        self.emit("SCRIPT_DIR = Path(__file__).parent")
        self.emit("ASSETS_DIR = SCRIPT_DIR / 'assets'")
        self.emit_blank()

        # 6. Initialize Pygame
        self.emit_comment("Initialize Pygame")
        self.emit("pygame.init()")
        # Initialize mixer for sound/music support
        if self.uses_sound or self.uses_music:
            self.emit("pygame.mixer.init()")
        self.emit(f"screen = pygame.display.set_mode(({self.GAME_WIDTH}, {self.GAME_HEIGHT}))")
        self.emit("pygame.display.set_caption('Rosh Game')")
        self.emit("clock = pygame.time.Clock()")
        self.emit_blank()

        # 6.5. Sound helpers (if needed)
        if self.uses_sound:
            self.emit_sound_helpers()

        # 7. Disable key repeat for input parity with Phaser JustDown
        self.emit_comment("Disable key repeat (input parity with Phaser JustDown)")
        self.emit("pygame.key.set_repeat(0)")
        self.emit_blank()

        # 8. Font setup for text objects (pygame.init() already initializes fonts)
        # Note: Removed explicit pygame.font.init() for Python 3.14 compatibility

        # 9. Game object class
        self.emit_game_object_class()

        # 10. Text object class if needed
        if self.text_objects:
            self.emit_text_object_class()

        # 11. Game state class
        self.emit_game_state_class()

        # 12. Create objects
        self.emit_comment("Create game objects")
        for statement in program.statements:
            if isinstance(statement, CreateObject):
                self.emit_create_object(statement)
        self.emit_blank()

        # 13. Emit user-defined functions
        if self.functions:
            self.emit_comment("User-defined functions")
            for func in self.functions:
                self.emit_function_def(func)
            self.emit_blank()

        # 14. Event handler functions
        self.emit_event_handler_functions(program)

        # 15. Main game loop
        self.emit_game_loop()

        return self.get_code()

    def validate_ast(self, program: Program) -> None:
        """Validate AST contains only supported features"""
        unsupported_types = [
            (WhileLoop, 'while loops'),
            (ForLoop, 'for loops'),
            (Import, 'imports'),
        ]

        def check_node(node: ASTNode, path: str = "top level") -> None:
            for unsupported_type, feature_name in unsupported_types:
                if isinstance(node, unsupported_type):
                    raise RoshRuntimeError(
                        f"Pygame transpiler does not support '{feature_name}' yet\n"
                        f"Location: {path}"
                    )

            if isinstance(node, CreateObject):
                for stmt in node.body:
                    check_node(stmt, f"{path}.{node.name}")
            elif isinstance(node, Program):
                for stmt in node.statements:
                    check_node(stmt, path)

        check_node(program)

    def detect_features(self, program: Program) -> None:
        """Scan program for features to generate"""
        def scan_statements(statements):
            for node in statements:
                if isinstance(node, WhenStatement):
                    event_key = node.event_name
                    if event_key not in self.event_handlers:
                        self.event_handlers[event_key] = []
                    self.event_handlers[event_key].append(node)

                    if node.event_name in ['key_pressed', 'space_pressed', 'key_left',
                                           'key_right', 'key_up', 'key_down', 'key_r']:
                        self.needs_keyboard_input = True

                    scan_statements(node.body)

                elif isinstance(node, FunctionDef):
                    self.functions.append(node)

                elif isinstance(node, CreateObject):
                    # Check for text objects
                    for stmt in node.body:
                        if isinstance(stmt, SetProperty) and isinstance(stmt.target, Identifier):
                            if stmt.target.name == 'text':
                                self.text_objects.append(node.name)
                            elif stmt.target.name == 'sprite':
                                sprite_val = self.eval_constant_expression(stmt.value)
                                if isinstance(sprite_val, str):
                                    self.sprite_assets[node.name] = sprite_val

                    if node.parents and 'player' in node.parents:
                        self.player_objects.append(node.name)

                    scan_statements(node.body)

                elif isinstance(node, PlaySound):
                    self.uses_sound = True
                    if node.filename not in self.sound_files:
                        self.sound_files.append(node.filename)

                elif isinstance(node, PlayMusic):
                    self.uses_music = True

                elif isinstance(node, IfStatement):
                    scan_statements(node.then_body)
                    if node.else_body:
                        scan_statements(node.else_body)

        scan_statements(program.statements)

    def emit_game_object_class(self) -> None:
        """Emit the GameObject class for rectangles/sprites"""
        self.emit("class GameObject:")
        self.indent_level += 1
        self.emit('"""Basic game object with position, size, color, and visibility"""')
        self.emit_blank()

        self.emit("def __init__(self, x, y, width, height, color, shape='rectangle'):")
        self.indent_level += 1
        self.emit("self.x = x")
        self.emit("self.y = y")
        self.emit("self.width = width")
        self.emit("self.height = height")
        self.emit("self.color = color")
        self.emit("self.shape = shape")
        self.emit("self.visible = True")
        self.emit("self.sprite = None")
        self.indent_level -= 1
        self.emit_blank()

        self.emit("def draw(self, surface):")
        self.indent_level += 1
        self.emit("if not self.visible:")
        self.indent_level += 1
        self.emit("return")
        self.indent_level -= 1
        self.emit("if self.sprite:")
        self.indent_level += 1
        self.emit("surface.blit(self.sprite, (self.x - self.width // 2, self.y - self.height // 2))")
        self.indent_level -= 1
        self.emit("elif self.shape == 'circle':")
        self.indent_level += 1
        self.emit("pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), self.width // 2)")
        self.indent_level -= 1
        self.emit("else:")
        self.indent_level += 1
        self.emit("rect = pygame.Rect(self.x - self.width // 2, self.y - self.height // 2, self.width, self.height)")
        self.emit("pygame.draw.rect(surface, self.color, rect)")
        self.indent_level -= 1
        self.indent_level -= 1

        self.indent_level -= 1
        self.emit_blank()

    def emit_text_object_class(self) -> None:
        """Emit the TextObject class for text rendering"""
        self.emit("class TextObject:")
        self.indent_level += 1
        self.emit('"""Text display object with font rendering"""')
        self.emit_blank()

        self.emit("def __init__(self, x, y, text, color=(255, 255, 255), font_size=16):")
        self.indent_level += 1
        self.emit("self.x = x")
        self.emit("self.y = y")
        self.emit("self.text = text")
        self.emit("self.color = color")
        self.emit("self.font_size = font_size")
        self.emit("self.visible = True")
        self.emit("self.font = None")
        self.emit("try:")
        self.indent_level += 1
        self.emit("self.font = pygame.font.SysFont('Arial', font_size)")
        self.indent_level -= 1
        self.emit("except Exception as e:")
        self.indent_level += 1
        self.emit("print(f'Warning: Font init failed: {e}')")
        self.indent_level -= 1
        self.indent_level -= 1
        self.emit_blank()

        self.emit("def set_text(self, text):")
        self.indent_level += 1
        self.emit("self.text = text")
        self.indent_level -= 1
        self.emit_blank()

        self.emit("def set_font_size(self, size):")
        self.indent_level += 1
        self.emit("self.font_size = size")
        self.emit("try:")
        self.indent_level += 1
        self.emit("self.font = pygame.font.SysFont('Arial', int(size))")
        self.indent_level -= 1
        self.emit("except Exception as e:")
        self.indent_level += 1
        self.emit("print(f'Warning: Font resize failed: {e}')")
        self.indent_level -= 1
        self.indent_level -= 1
        self.emit_blank()

        self.emit("def draw(self, surface):")
        self.indent_level += 1
        self.emit("if not self.visible:")
        self.indent_level += 1
        self.emit("return")
        self.indent_level -= 1
        self.emit("if self.font:")
        self.indent_level += 1
        self.emit("rendered = self.font.render(str(self.text), True, self.color)")
        self.emit("rect = rendered.get_rect(center=(self.x, self.y))")
        self.emit("surface.blit(rendered, rect)")
        self.indent_level -= 1
        self.emit("else:")
        self.indent_level += 1
        self.emit_comment("Fallback: draw text position marker if font unavailable")
        self.emit("pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), 5)")
        self.indent_level -= 1
        self.indent_level -= 1

        self.indent_level -= 1
        self.emit_blank()

    def emit_game_state_class(self) -> None:
        """Emit simple game state container"""
        self.emit("class GameState:")
        self.indent_level += 1
        self.emit('"""Container for custom game state properties"""')
        self.emit("pass")
        self.indent_level -= 1
        self.emit_blank()

    def emit_sound_helpers(self) -> None:
        """Emit sound caching and playback helper"""
        self.emit_comment("Sound cache and helper")
        self.emit("_sounds = {}")
        self.emit_blank()
        self.emit("def play_sound(filename):")
        self.indent_level += 1
        self.emit('"""Play a sound effect with caching"""')
        self.emit("if filename not in _sounds:")
        self.indent_level += 1
        self.emit("try:")
        self.indent_level += 1
        self.emit("_sounds[filename] = pygame.mixer.Sound(str(ASSETS_DIR / filename))")
        self.indent_level -= 1
        self.emit("except Exception as e:")
        self.indent_level += 1
        self.emit("print(f'Warning: Could not load sound {filename}: {e}')")
        self.emit("return")
        self.indent_level -= 1
        self.indent_level -= 1
        self.emit("_sounds[filename].play()")
        self.indent_level -= 1
        self.emit_blank()

    def emit_create_object(self, node: CreateObject) -> None:
        """Convert create object to Pygame object"""
        properties = self.extract_object_properties(node)
        self.object_properties[node.name] = properties

        x = self.convert_percentage_to_pixels(properties.get('x', 100), 'x')
        y = self.convert_percentage_to_pixels(properties.get('y', 100), 'y')
        width = int(properties.get('width', 50))
        height = int(properties.get('height', 50))
        color = properties.get('color', self.DEFAULT_COLORS[self.object_counter % 8])
        shape = properties.get('shape', 'rectangle')
        text = properties.get('text')

        # Convert hex color to RGB tuple if needed
        if isinstance(color, int):
            color = self.hex_to_rgb(color)
        elif isinstance(color, str):
            color = self.color_name_to_rgb(color)

        if text is not None:
            # Text object
            font_size = int(properties.get('font_size', 16))
            text_color = properties.get('color', (255, 255, 255))
            if isinstance(text_color, str):
                text_color = self.color_name_to_rgb(text_color)
            elif isinstance(text_color, int):
                text_color = self.hex_to_rgb(text_color)

            self.emit(f'{node.name} = TextObject({int(x)}, {int(y)}, "{text}", {text_color}, {font_size})')
        else:
            # Game object (rectangle/circle/sprite)
            self.emit(f"{node.name} = GameObject({int(x)}, {int(y)}, {width}, {height}, {color}, '{shape}')")

            # Handle sprite
            sprite = properties.get('sprite')
            if sprite:
                self.emit(f"try:")
                self.indent_level += 1
                self.emit(f"_sprite_path = ASSETS_DIR / '{sprite}'")
                self.emit(f"{node.name}.sprite = pygame.image.load(str(_sprite_path))")
                self.emit(f"{node.name}.sprite = pygame.transform.scale({node.name}.sprite, ({width}, {height}))")
                self.indent_level -= 1
                self.emit("except:")
                self.indent_level += 1
                self.emit(f"print(f'Warning: Could not load sprite {sprite}, using colored shape')")
                self.indent_level -= 1

        # Handle visibility
        if 'visible' in properties and not properties['visible']:
            self.emit(f"{node.name}.visible = False")

        # Handle custom properties
        rendering_props = {'x', 'y', 'width', 'height', 'color', 'sprite', 'text',
                          'font_size', 'font', 'align', 'visible', 'shape'}
        for prop_name, prop_value in properties.items():
            if prop_name not in rendering_props:
                if isinstance(prop_value, bool):
                    val_py = 'True' if prop_value else 'False'
                elif isinstance(prop_value, str):
                    val_py = f'"{prop_value}"'
                else:
                    val_py = str(prop_value)
                self.emit(f"{node.name}.{prop_name} = {val_py}")

        self.emit_blank()
        self.object_counter += 1

    def extract_object_properties(self, node: CreateObject) -> Dict[str, Any]:
        """Extract property values from object body"""
        properties = {}
        if node.parents:
            base_type = node.parents[0]
            if base_type in self.BASE_TYPES:
                properties = self.BASE_TYPES[base_type].copy()

        for statement in node.body:
            if isinstance(statement, SetProperty):
                if isinstance(statement.target, Identifier):
                    prop_name = statement.target.name
                    prop_value = self.eval_constant_expression(statement.value)
                    properties[prop_name] = prop_value

        return properties

    def eval_constant_expression(self, node: ASTNode) -> Any:
        """Evaluate constant expression to Python value"""
        if isinstance(node, Literal):
            # Check if it's a percentage (stored in Literal with type)
            if hasattr(node, 'is_percentage') and node.is_percentage:
                return {'type': 'percentage', 'value': node.value}
            return node.value
        elif isinstance(node, Identifier):
            # Check for percentage values (e.g., "50%")
            if node.name.endswith('%'):
                try:
                    percent_value = float(node.name[:-1])
                    return {'type': 'percentage', 'value': percent_value}
                except ValueError:
                    pass
            return node.name
        elif isinstance(node, BinaryOp):
            left = self.eval_constant_expression(node.left)
            right = self.eval_constant_expression(node.right)
            op = node.operator if hasattr(node, 'operator') else getattr(node, 'op', '+')
            if op in ['+', 'plus']:
                return left + right
            elif op in ['-', 'minus']:
                return left - right
            elif op in ['*', 'times']:
                return left * right
            elif op in ['/', 'divided_by']:
                return left / right
        elif isinstance(node, UnaryOp):
            operand = self.eval_constant_expression(node.operand)
            if node.operator in ['-', 'minus']:
                return -operand if operand is not None else None
        return None

    def convert_percentage_to_pixels(self, value: Any, axis: str) -> float:
        """Convert percentage to pixel value"""
        if isinstance(value, dict) and value.get('type') == 'percentage':
            if axis in ['x', 'width']:
                return (value['value'] / 100) * self.GAME_WIDTH
            else:
                return (value['value'] / 100) * self.GAME_HEIGHT
        return float(value) if value is not None else 0

    def hex_to_rgb(self, hex_color: int) -> tuple:
        """Convert hex color to RGB tuple"""
        r = (hex_color >> 16) & 0xFF
        g = (hex_color >> 8) & 0xFF
        b = hex_color & 0xFF
        return (r, g, b)

    def color_name_to_rgb(self, name: str) -> tuple:
        """Convert color name to RGB tuple"""
        colors = {
            'white': (255, 255, 255),
            'black': (0, 0, 0),
            'red': (255, 0, 0),
            'green': (0, 255, 0),
            'blue': (0, 0, 255),
            'yellow': (255, 255, 0),
            'cyan': (0, 255, 255),
            'magenta': (255, 0, 255),
            'orange': (255, 136, 0),
            'purple': (136, 0, 255),
            'gray': (128, 128, 128),
            'grey': (128, 128, 128),
            'gold': (255, 215, 0),
        }
        return colors.get(name.lower(), (255, 255, 255))

    def emit_function_def(self, node: FunctionDef) -> None:
        """Emit user-defined function"""
        self.emit(f"def {node.name}():")
        self.indent_level += 1

        if not node.body:
            self.emit("pass")
        else:
            for stmt in node.body:
                self.emit_statement(stmt)

        self.indent_level -= 1
        self.emit_blank()

    def emit_statement(self, node: ASTNode) -> None:
        """Emit a single statement"""
        if isinstance(node, SetProperty):
            self.emit_set_property(node)
        elif isinstance(node, FunctionCall):
            self.emit_function_call(node)
        elif isinstance(node, IfStatement):
            self.emit_if_statement(node)
        elif isinstance(node, Print):
            self.emit_print(node)
        elif isinstance(node, PlaySound):
            self.emit(f'play_sound("{node.filename}")')
        elif isinstance(node, PlayMusic):
            self.emit(f'pygame.mixer.music.load(str(ASSETS_DIR / "{node.filename}"))')
            self.emit("pygame.mixer.music.play(-1)")  # -1 = loop forever
        elif isinstance(node, StopMusic):
            self.emit("pygame.mixer.music.stop()")

    def emit_set_property(self, node: SetProperty) -> None:
        """Emit property assignment"""
        target = self.emit_expression(node.target)
        value = self.emit_expression(node.value)

        # Special handling for text property
        if '.text' in target and 'set_text' not in target:
            # Use set_text method for TextObjects
            obj_name = target.split('.')[0]
            if obj_name in self.text_objects:
                self.emit(f"{obj_name}.set_text({value})")
                return

        # Special handling for font_size property
        if '.font_size' in target:
            obj_name = target.split('.')[0]
            if obj_name in self.text_objects:
                self.emit(f"{obj_name}.set_font_size({value})")
                return

        self.emit(f"{target} = {value}")

    def emit_function_call(self, node: FunctionCall) -> None:
        """Emit function call"""
        self.emit(f"{node.name}()")

    def emit_if_statement(self, node: IfStatement) -> None:
        """Emit if statement"""
        condition = self.emit_expression(node.condition)
        self.emit(f"if {condition}:")
        self.indent_level += 1

        if not node.then_body:
            self.emit("pass")
        else:
            for stmt in node.then_body:
                self.emit_statement(stmt)

        self.indent_level -= 1

        if node.else_body:
            self.emit("else:")
            self.indent_level += 1
            for stmt in node.else_body:
                self.emit_statement(stmt)
            self.indent_level -= 1

    def emit_print(self, node: Print) -> None:
        """Emit print statement"""
        value = self.emit_expression(node.value)
        self.emit(f"print({value})")

    def emit_expression(self, node: ASTNode) -> str:
        """Convert expression to Python code string"""
        if isinstance(node, Literal):
            if node.type_name == 'string':
                # Handle string interpolation
                if '{' in str(node.value) and '}' in str(node.value):
                    return f'f"{node.value}"'
                return f'"{node.value}"'
            elif node.type_name == 'boolean':
                return 'True' if node.value else 'False'
            else:
                return str(node.value)
        elif isinstance(node, Identifier):
            return node.name
        elif isinstance(node, PropertyAccess):
            obj = self.emit_expression(node.object)
            return f"{obj}.{node.property}"
        elif isinstance(node, BinaryOp):
            left = self.emit_expression(node.left)
            right = self.emit_expression(node.right)
            op = node.operator if hasattr(node, 'operator') else getattr(node, 'op', '+')
            # Map Rosh operators to Python
            op_map = {
                'plus': '+', 'minus': '-', 'times': '*', 'divided_by': '/',
                '+': '+', '-': '-', '*': '*', '/': '/'
            }
            py_op = op_map.get(op, op)
            return f"({left} {py_op} {right})"
        elif isinstance(node, Comparison):
            left = self.emit_expression(node.left)
            right = self.emit_expression(node.right)
            op_map = {
                'equal': '==',
                'not_equal': '!=',
                'above': '>',
                'below': '<',
                'at_least': '>=',
                'at_most': '<='
            }
            py_op = op_map.get(node.operator, '==')
            return f"({left} {py_op} {right})"
        elif isinstance(node, UnaryOp):
            operand = self.emit_expression(node.operand)
            if node.operator in ['-', 'minus']:
                return f"(-{operand})"
            return operand

        return "None"

    def emit_event_handler_functions(self, program: Program) -> None:
        """Emit event handler functions"""
        if not self.event_handlers:
            return

        self.emit_comment("Event handlers")

        for event_name, handlers in self.event_handlers.items():
            self.emit(f"def handle_{event_name}():")
            self.indent_level += 1

            for handler in handlers:
                for stmt in handler.body:
                    self.emit_statement(stmt)

            self.indent_level -= 1
            self.emit_blank()

    def emit_game_loop(self) -> None:
        """Emit the main game loop"""
        self.emit_comment("Main game loop")
        self.emit("running = True")
        self.emit("while running:")
        self.indent_level += 1

        # Event handling
        self.emit_comment("Event handling")
        self.emit("for event in pygame.event.get():")
        self.indent_level += 1
        self.emit("if event.type == pygame.QUIT:")
        self.indent_level += 1
        self.emit("running = False")
        self.indent_level -= 1

        # Key events
        if self.needs_keyboard_input:
            self.emit("elif event.type == pygame.KEYDOWN:")
            self.indent_level += 1

            key_events = [
                ('key_left', 'K_LEFT'),
                ('key_right', 'K_RIGHT'),
                ('key_up', 'K_UP'),
                ('key_down', 'K_DOWN'),
                ('space_pressed', 'K_SPACE'),
                ('key_r', 'K_r'),
            ]

            first = True
            for event_name, pygame_key in key_events:
                if event_name in self.event_handlers:
                    prefix = "if" if first else "elif"
                    self.emit(f"{prefix} event.key == pygame.{pygame_key}:")
                    self.indent_level += 1
                    self.emit(f"handle_{event_name}()")
                    self.indent_level -= 1
                    first = False

            self.indent_level -= 1

        self.indent_level -= 1
        self.emit_blank()

        # Check held keys for smooth movement
        if self.needs_keyboard_input:
            self.emit_comment("Check held keys for smooth movement")
            self.emit("keys = pygame.key.get_pressed()")
            # Check for while_key_* handlers (continuous movement)
            held_key_events = [
                ('while_key_left', 'K_LEFT'),
                ('while_key_right', 'K_RIGHT'),
                ('while_key_up', 'K_UP'),
                ('while_key_down', 'K_DOWN'),
            ]
            for event_name, pygame_key in held_key_events:
                if event_name in self.event_handlers:
                    self.emit(f"if keys[pygame.{pygame_key}]:")
                    self.indent_level += 1
                    self.emit(f"handle_{event_name}()")
                    self.indent_level -= 1
            self.emit_blank()

        # Per-frame update (if defined)
        if 'update' in self.event_handlers:
            self.emit_comment("Per-frame game update")
            self.emit("handle_update()")
            self.emit_blank()

        # Drawing
        self.emit_comment("Clear screen")
        self.emit("screen.fill((45, 45, 45))")
        self.emit_blank()

        self.emit_comment("Draw all objects")
        for obj_name in self.object_properties.keys():
            self.emit(f"{obj_name}.draw(screen)")
        self.emit_blank()

        # Update display
        self.emit("pygame.display.flip()")
        self.emit("clock.tick(60)")

        self.indent_level -= 1
        self.emit_blank()

        # Cleanup
        self.emit("pygame.quit()")
        self.emit("sys.exit()")
