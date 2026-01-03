"""
AST to IR Transformer

Converts Rosh AST (parser output) to Rosh IR (target-agnostic representation).

Key responsibilities:
1. Normalize coordinates (absolute → 0.0-1.0)
2. Assign UUIDs to objects
3. Convert colors to hex integers
4. Map events to canonical trigger names
5. Resolve type inheritance

See: rosh-dev/proposals/ROSH-IR-SPECIFICATION.md
"""

from typing import List, Dict, Any, Optional
import uuid
import json
import os

from .ast_nodes import (
    Program, ASTNode, CreateObject, CreateValue, SetProperty, PropertyAccess,
    Identifier, Literal, BinaryOp, UnaryOp, Comparison, LogicalOp, Contains,
    IfStatement, WhileLoop, ForLoop, WhenStatement, TriggerEvent,
    FunctionDef, FunctionCall, Return, Break, Continue,
    Print, PlaySound, PlayMusic, StopMusic, Save, Load, LoadSettings,
    CloneObject, DeleteObject, ActivateObject, DeactivateObject, SpawnAt, MoveDirection,
    Increment, Decrement, Random, Length,
    ListLiteral, ListIndex, Append, Remove, Get, GotoScene, SaveGame, LoadGame,
    Metadata, PlayAnimation, StopAnimation, SetGrid, SetAnimations, SetAnimationFrames
)
from .ir import (
    IR_Program, IR_Object, IR_Event, IR_Action, IR_Function,
    IR_Value, IR_Expression, IR_Conditional, IR_Loop, IR_Metadata,
    normalize_coordinate, color_to_hex
)


class IRTransformer:
    """Transform Rosh AST to IR representation.

    Usage:
        transformer = IRTransformer(canvas_width=800, canvas_height=600)
        ir_program = transformer.transform(ast_program)
    """

    def __init__(self, canvas_width: int = 800, canvas_height: int = 600,
                 meta: Dict[str, Any] = None, project_root: str = None):
        """Initialize transformer with canvas dimensions.

        Args:
            canvas_width: Logical canvas width (for coordinate normalization)
            canvas_height: Logical canvas height
            meta: Optional metadata dict from _meta/*.toml
            project_root: Project root directory for resolving load paths
        """
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height
        self.meta = meta or {}
        self.project_root = project_root or os.getcwd()

        # Track objects by name for lookups
        self.objects: Dict[str, IR_Object] = {}

        # Base type defaults (for inheritance)
        self.base_types = {
            'player': {
                'lives': IR_Value('number', 3),
                'score': IR_Value('number', 0),
                'speed': IR_Value('number', 5),
                'width': IR_Value('percentage', 0.0375),  # 30/800
                'height': IR_Value('percentage', 0.05),   # 30/600
                'color': IR_Value('color', 0x00ff00),
            },
            'enemy': {
                'health': IR_Value('number', 100),
                'speed': IR_Value('number', 3),
                'width': IR_Value('percentage', 0.0375),
                'height': IR_Value('percentage', 0.05),
                'color': IR_Value('color', 0xff0000),
            },
            'item': {
                'width': IR_Value('percentage', 0.025),
                'height': IR_Value('percentage', 0.033),
                'color': IR_Value('color', 0xffff00),
            },
        }

        # Coordinate properties that need normalization
        self.coordinate_props = {'x', 'y', 'width', 'height'}

    def transform(self, program: Program) -> IR_Program:
        """Transform AST Program to IR_Program.

        Args:
            program: Rosh AST Program node

        Returns:
            IR_Program with normalized, target-agnostic representation
        """
        # Pre-pass: extract metadata from AST Metadata nodes
        ast_meta = {}
        for stmt in program.statements:
            if isinstance(stmt, Metadata) and stmt.scope is None:
                # Core metadata (no scope) - extract field values
                for key, value_expr in stmt.fields.items():
                    if isinstance(value_expr, Literal):
                        ast_meta[key] = value_expr.value
                    elif isinstance(value_expr, Identifier):
                        ast_meta[key] = value_expr.name

        # Merge AST metadata with config meta (AST takes precedence)
        merged_meta = {**self.meta, **ast_meta}

        # Pass through extra metadata fields (like use_shared_runtime)
        known_meta_keys = {'title', 'version', 'initial_scene', 'canvas_width', 'canvas_height'}
        extra_meta = {k: v for k, v in merged_meta.items() if k not in known_meta_keys}

        ir_program = IR_Program(
            metadata=IR_Metadata(
                canvas_width=self.canvas_width,
                canvas_height=self.canvas_height,
                title=merged_meta.get('title'),
                version=merged_meta.get('version'),
                initial_scene=merged_meta.get('initial_scene'),
                extra=extra_meta,
            )
        )

        # First pass: collect all objects (including from loaded settings)
        for stmt in program.statements:
            if isinstance(stmt, CreateObject):
                # Check for array pool syntax
                if stmt.count and stmt.array_name:
                    # Create N objects and register as array pool
                    pool_objects = []
                    for i in range(stmt.count):
                        ir_obj = self.transform_create_object(stmt, index=i)
                        ir_program.objects.append(ir_obj)
                        self.objects[ir_obj.name] = ir_obj
                        pool_objects.append(ir_obj.name)
                    # Register the array pool
                    ir_program.array_pools[stmt.array_name.lower()] = pool_objects
                else:
                    ir_obj = self.transform_create_object(stmt)
                    ir_program.objects.append(ir_obj)
                    self.objects[ir_obj.name] = ir_obj
            elif isinstance(stmt, LoadSettings):
                # Load JSON settings file and create objects from it
                loaded_objects = self.load_settings_file(stmt.filepath)
                for ir_obj in loaded_objects:
                    ir_program.objects.append(ir_obj)
                    self.objects[ir_obj.name] = ir_obj

        # Second pass: collect events and functions
        for stmt in program.statements:
            if isinstance(stmt, WhenStatement):
                ir_event = self.transform_when_statement(stmt)
                ir_program.events.append(ir_event)
            elif isinstance(stmt, FunctionDef):
                ir_func = self.transform_function_def(stmt)
                ir_program.functions.append(ir_func)

        # Third pass: collect init actions (top-level statements)
        for stmt in program.statements:
            if not isinstance(stmt, (CreateObject, WhenStatement, FunctionDef)):
                # Check for set _meta X to Y - store in metadata.extra
                if isinstance(stmt, SetProperty):
                    if isinstance(stmt.target, PropertyAccess):
                        target_name = self.get_object_name(stmt.target.object)
                        if target_name == '_meta':
                            prop_name = stmt.target.property.lower()
                            value = self.transform_value(stmt.value, prop_name)
                            ir_program.metadata.extra[prop_name] = value.value if hasattr(value, 'value') else str(value)
                            continue  # Don't add to init_actions
                action = self.transform_statement(stmt)
                if action:
                    ir_program.init_actions.append(action)

        return ir_program

    # =========================================================================
    # Settings Loading (Phase 2 - Project Arcade)
    # =========================================================================

    def load_settings_file(self, filepath: str) -> List[IR_Object]:
        """Load a JSON settings file and create IR_Objects from it.

        Args:
            filepath: Relative path to JSON file (from project root)

        Returns:
            List of IR_Object created from JSON structure

        JSON structure maps to objects:
            {
                "_meta": {"title": "Game Name"},  # Hidden (underscore prefix)
                "player": {"x": 400, "color": "green"},  # Visible object
                "_config": {"speed": 5}  # Hidden config object
            }
        """
        full_path = os.path.join(self.project_root, filepath)

        if not os.path.exists(full_path):
            raise FileNotFoundError(f"Settings file not found: {filepath}")

        with open(full_path, 'r') as f:
            data = json.load(f)

        return self.json_to_objects(data)

    def json_to_objects(self, data: dict) -> List[IR_Object]:
        """Convert JSON dictionary to list of IR_Objects.

        Each top-level key becomes an object name.
        Objects with names starting with '_' are hidden.

        Args:
            data: Parsed JSON dictionary

        Returns:
            List of IR_Object
        """
        objects = []

        for obj_name, obj_data in data.items():
            if not isinstance(obj_data, dict):
                # Skip non-dict values (could be simple metadata)
                continue

            # Underscore prefix = hidden object
            is_hidden = obj_name.startswith('_')

            # Convert properties from JSON values to IR_Values
            properties: Dict[str, IR_Value] = {}
            for prop_name, prop_value in obj_data.items():
                properties[prop_name.lower()] = self.json_value_to_ir(prop_value, prop_name.lower())

            # Default position if not specified
            if 'x' not in properties:
                properties['x'] = IR_Value('percentage', 0.5)
            if 'y' not in properties:
                properties['y'] = IR_Value('percentage', 0.5)

            # Extract scene/level if present
            scene = None
            level = None
            if 'scene' in properties:
                scene = properties.pop('scene').value
                if 'level' in properties:
                    level_val = properties.pop('level').value
                    level = int(level_val) if level_val is not None else None

            # Create IR_Object
            ir_obj = IR_Object(
                uuid=str(uuid.uuid4()),
                name=obj_name.lower(),
                type="shape",  # Default type for settings-loaded objects
                parent_type=None,
                properties=properties,
                saveable=True,
                hidden=is_hidden,
                scene=scene,
                level=level
            )
            objects.append(ir_obj)

        return objects

    def json_value_to_ir(self, value: Any, prop_name: str = None) -> IR_Value:
        """Convert a JSON value to IR_Value.

        Args:
            value: JSON value (str, int, float, bool, list, etc.)
            prop_name: Property name for context (affects normalization)

        Returns:
            IR_Value
        """
        if isinstance(value, bool):
            return IR_Value('boolean', value)
        elif isinstance(value, int) or isinstance(value, float):
            # Check if it's a coordinate property
            if prop_name in self.coordinate_props:
                # Normalize pixel values
                if prop_name in ('x', 'width'):
                    normalized = value / self.canvas_width
                else:  # y, height
                    normalized = value / self.canvas_height
                return IR_Value('percentage', normalized)
            return IR_Value('number', value)
        elif isinstance(value, str):
            # Check for color property
            if prop_name == 'color':
                return IR_Value('color', color_to_hex(value))
            return IR_Value('string', value)
        elif isinstance(value, list):
            elements = [self.json_value_to_ir(e).value for e in value]
            return IR_Value('list', elements)
        elif value is None:
            return IR_Value('null', None)
        else:
            return IR_Value('string', str(value))

    # =========================================================================
    # Object Transformation
    # =========================================================================

    def transform_create_object(self, node: CreateObject, index: int = None) -> IR_Object:
        """Transform CreateObject AST node to IR_Object.

        Args:
            node: The CreateObject AST node
            index: Optional index for array pools (e.g., 0, 1, 2, 3 for a pool of 4)
        """
        # Determine object name
        if index is not None and node.array_name:
            # Array pool: use array_name + index (e.g., explosions_0)
            obj_name = f"{node.array_name.lower()}_{index}"
        else:
            obj_name = node.name.lower()

        # Determine object type and parent
        parent_type = None
        obj_type = "shape"

        if node.parents:
            parent_type = node.parents[0].lower()
            if parent_type in ('player', 'enemy', 'item'):
                obj_type = "sprite"  # Assumed for game entities

        # Start with inherited properties
        properties: Dict[str, IR_Value] = {}
        if parent_type and parent_type in self.base_types:
            properties = dict(self.base_types[parent_type])

        # Process body statements to extract properties
        for stmt in node.body:
            if isinstance(stmt, SetProperty):
                prop_name, prop_value = self.extract_property(stmt)
                if prop_name:
                    properties[prop_name] = prop_value

        # Default position if not specified
        if 'x' not in properties:
            properties['x'] = IR_Value('percentage', 0.5)
        if 'y' not in properties:
            properties['y'] = IR_Value('percentage', 0.5)

        # Extract scene/level from properties (Roshonic "Dimensions, Not Modes")
        # Note: 'level' alone is just a regular property (e.g., game state)
        # Only treat 'level' as a coordinate if 'scene' is also present
        scene = None
        level = None
        if 'scene' in properties:
            scene = properties.pop('scene').value  # Extract and remove from properties
            # Only extract level as coordinate if scene is set
            if 'level' in properties:
                level_val = properties.pop('level').value
                level = int(level_val) if level_val is not None else None

        # Extract saveable (default True, can be set to False)
        saveable = True
        if 'saveable' in properties:
            saveable_val = properties.pop('saveable').value
            saveable = bool(saveable_val) if saveable_val is not None else True

        # Extract sprite animation properties
        grid_cols = None
        grid_rows = None
        frame_rate = 10.0
        flip_x = False
        flip_y = False
        if 'sprite_columns' in properties:
            grid_cols = int(properties.pop('sprite_columns').value)
        if 'sprite_rows' in properties:
            grid_rows = int(properties.pop('sprite_rows').value)
        if 'frame_rate' in properties:
            frame_rate = float(properties.pop('frame_rate').value)
        if 'flip_x' in properties:
            flip_x = bool(properties.pop('flip_x').value)
        if 'flip_y' in properties:
            flip_y = bool(properties.pop('flip_y').value)

        # For array pools, objects are not hidden even though the template is
        is_hidden = node.hidden if index is None else False

        ir_obj = IR_Object(
            uuid=str(uuid.uuid4()),
            name=obj_name,
            type=obj_type,
            parent_type=parent_type,
            properties=properties,
            saveable=saveable,
            hidden=is_hidden,
            scene=scene,
            level=level,
            grid_cols=grid_cols,
            grid_rows=grid_rows,
            frame_rate=frame_rate,
            flip_x=flip_x,
            flip_y=flip_y
        )

        # Process animation definitions inside create block
        for stmt in node.body:
            if isinstance(stmt, SetAnimations):
                # Define animations with auto-division of frames
                if ir_obj.grid_cols and ir_obj.grid_rows:
                    total_frames = ir_obj.grid_cols * ir_obj.grid_rows
                    num_anims = len(stmt.names)
                    if num_anims > 0:
                        frames_per_anim = total_frames // num_anims
                        remainder = total_frames % num_anims
                        frame = 0
                        for i, name in enumerate(stmt.names):
                            # Last animation gets remainder
                            count = frames_per_anim + (remainder if i == num_anims - 1 else 0)
                            ir_obj.animations[name.lower()] = (frame, frame + count - 1)
                            frame += count
            elif isinstance(stmt, SetAnimationFrames):
                # Override specific animation frame range
                ir_obj.animations[stmt.animation.lower()] = (stmt.start, stmt.end)

        return ir_obj

    def extract_property(self, stmt: SetProperty) -> tuple:
        """Extract property name and IR_Value from SetProperty."""
        # Get property name
        if isinstance(stmt.target, Identifier):
            prop_name = stmt.target.name.lower()
        elif isinstance(stmt.target, PropertyAccess):
            prop_name = stmt.target.property.lower()
        else:
            return None, None

        # Transform value
        prop_value = self.transform_value(stmt.value, prop_name)
        return prop_name, prop_value

    def transform_value(self, node: ASTNode, context_prop: str = None) -> IR_Value:
        """Transform AST value expression to IR_Value.

        Args:
            node: AST expression node
            context_prop: Property name for context (affects normalization)
        """
        if isinstance(node, Literal):
            return self.transform_literal(node, context_prop)
        elif isinstance(node, Identifier):
            # Reference to another value - keep as string for now
            return IR_Value('string', node.name.lower())
        elif isinstance(node, ListLiteral):
            elements = [self.transform_value(e).value for e in node.elements]
            return IR_Value('list', elements)
        elif isinstance(node, BinaryOp):
            # For binary ops, return as expression (emitter will handle)
            return IR_Value('expression', self.transform_expression(node))
        elif isinstance(node, Random):
            # Random needs special handling by emitter
            return IR_Value('random', {
                'min': self.transform_value(node.min_val).value if node.min_val else 0,
                'max': self.transform_value(node.max_val).value if node.max_val else 1,
            })
        elif isinstance(node, PropertyAccess):
            # Property access like player.x - return as expression
            return IR_Value('expression', self.transform_expression(node))
        elif isinstance(node, UnaryOp):
            # Unary operations like -50 - return as expression
            return IR_Value('expression', self.transform_expression(node))
        else:
            # Fallback
            return IR_Value('null', None)

    def transform_literal(self, node: Literal, context_prop: str = None) -> IR_Value:
        """Transform Literal AST node to IR_Value with normalization.

        Design Decision (2025-12-18):
        For ALL coordinate properties (x, y, width, height):
        - Bare numbers are PIXELS: `set x to 400` = 400 pixels
        - Explicit percentages: `set x to 50%` = 50% of canvas

        Recommended usage:
        - Use `%` for UI elements (centered text, responsive positioning)
        - Use bare numbers for game logic (grid positions, fixed layouts)
        """
        value = node.value
        type_name = node.type_name

        # Handle coordinate properties
        if context_prop in self.coordinate_props:
            if type_name == 'number':
                # Bare numbers are pixels - normalize to 0-1 range for emitters
                if context_prop in ('x', 'width'):
                    normalized = value / self.canvas_width
                else:  # y, height
                    normalized = value / self.canvas_height
                return IR_Value('percentage', normalized)

            elif type_name == 'pixel':
                # Explicit pixels: 400px → normalize to canvas dimensions
                if context_prop in ('x', 'width'):
                    normalized = value / self.canvas_width
                else:  # y, height
                    normalized = value / self.canvas_height
                return IR_Value('percentage', normalized)

            elif type_name == 'percentage':
                # Explicit percentage: 50% → 0.5
                return IR_Value('percentage', value / 100.0)

        # Handle percentage values outside of coordinate context
        if type_name == 'percentage':
            return IR_Value('percentage', value / 100.0)

        # Handle colors
        if context_prop == 'color':
            if type_name == 'string':
                return IR_Value('color', color_to_hex(value))
            elif type_name == 'number':
                return IR_Value('color', int(value))

        # Standard type mapping
        type_map = {
            'number': 'number',
            'string': 'string',
            'boolean': 'boolean',
            'null': 'null',
        }

        return IR_Value(type_map.get(type_name, 'string'), value)

    # =========================================================================
    # Expression Transformation
    # =========================================================================

    def transform_expression(self, node: ASTNode) -> IR_Expression:
        """Transform AST expression to IR_Expression."""
        if isinstance(node, Literal):
            return IR_Expression(
                type='literal',
                value=self.transform_value(node)
            )

        elif isinstance(node, Identifier):
            # Use 'identifier' type for variable references (loop vars, etc.)
            return IR_Expression(
                type='literal',
                value=IR_Value('identifier', node.name.lower())
            )

        elif isinstance(node, PropertyAccess):
            return IR_Expression(
                type='property_access',
                left=self.get_object_name(node.object),
                right=node.property.lower()
            )

        elif isinstance(node, Comparison):
            op_map = {
                'equal': '==',
                'not_equal': '!=',
                'below': '<',
                'above': '>',
                'at_most': '<=',
                'at_least': '>=',
                'collides': 'collides',  # Arcade collision check (bbox overlap)
                'offscreen': 'offscreen',  # Arcade bounds check
            }
            return IR_Expression(
                type='comparison',
                operator=op_map.get(node.operator, node.operator),
                left=self.transform_expression(node.left),
                right=self.transform_expression(node.right)
            )

        elif isinstance(node, BinaryOp):
            op_map = {
                'plus': '+',
                'minus': '-',
                'times': '*',
                'divided': '/',
                'modulo': '%',
            }
            return IR_Expression(
                type='binary_op',
                operator=op_map.get(node.operator, node.operator),
                left=self.transform_expression(node.left),
                right=self.transform_expression(node.right)
            )

        elif isinstance(node, UnaryOp):
            return IR_Expression(
                type='unary_op',
                operator='-' if node.operator == 'minus' else node.operator,
                right=self.transform_expression(node.operand)
            )

        elif isinstance(node, LogicalOp):
            if node.operator == 'not':
                return IR_Expression(
                    type='unary_op',
                    operator='not',
                    right=self.transform_expression(node.right)
                )
            else:
                return IR_Expression(
                    type='binary_op',
                    operator=node.operator,  # 'and', 'or'
                    left=self.transform_expression(node.left),
                    right=self.transform_expression(node.right)
                )

        elif isinstance(node, Contains):
            return IR_Expression(
                type='function_call',
                left='contains',
                right=[
                    self.transform_expression(node.container),
                    self.transform_expression(node.item)
                ]
            )

        elif isinstance(node, Random):
            return IR_Expression(
                type='function_call',
                left='random',
                right=[
                    self.transform_expression(node.min_val) if node.min_val else IR_Expression(type='literal', value=IR_Value('number', 0)),
                    self.transform_expression(node.max_val) if node.max_val else IR_Expression(type='literal', value=IR_Value('number', 1)),
                ]
            )

        elif isinstance(node, Length):
            return IR_Expression(
                type='function_call',
                left='length',
                right=[self.transform_expression(node.target)]
            )

        elif isinstance(node, FunctionCall):
            return IR_Expression(
                type='function_call',
                left=node.name.lower(),
                right=[self.transform_expression(arg) for arg in node.arguments]
            )

        elif isinstance(node, ListIndex):
            # Array index access: arr[0] or arr[i]
            return IR_Expression(
                type='list_index',
                left=self.transform_expression(node.list_expr),
                right=self.transform_expression(node.index_expr) if node.index_expr else None
            )

        else:
            # Fallback for unsupported expressions
            return IR_Expression(type='literal', value=IR_Value('null', None))

    def get_object_name(self, node: ASTNode) -> str:
        """Extract object name from Identifier, PropertyAccess, or ListIndex."""
        if isinstance(node, Identifier):
            return node.name.lower()
        elif isinstance(node, PropertyAccess):
            return self.get_object_name(node.object)
        elif isinstance(node, ListIndex):
            # For list index, return as expression so emitter can handle
            return self.transform_expression(node)
        return ''

    # =========================================================================
    # Statement Transformation
    # =========================================================================

    def transform_statement(self, stmt: ASTNode) -> Any:
        """Transform a statement to IR_Action or control flow node."""
        if isinstance(stmt, SetProperty):
            return self.transform_set_property(stmt)

        elif isinstance(stmt, Print):
            return IR_Action('print', {
                'message': self.transform_expression(stmt.expression) if stmt.expression else None
            })

        elif isinstance(stmt, PlaySound):
            return IR_Action('play_sound', {'asset': stmt.filename})

        elif isinstance(stmt, PlayMusic):
            return IR_Action('play_music', {'asset': stmt.filename})

        elif isinstance(stmt, StopMusic):
            return IR_Action('stop_music', {})

        elif isinstance(stmt, PlayAnimation):
            # Target can be an expression (e.g., arr[0]) or None
            target = None
            if stmt.target:
                target = self.transform_expression(stmt.target)
            return IR_Action('play_animation', {
                'animation': stmt.animation.lower(),
                'target': target,
                'loop': stmt.loop
            })

        elif isinstance(stmt, StopAnimation):
            # Target can be an expression (e.g., arr[0]) or None
            target = None
            if stmt.target:
                target = self.transform_expression(stmt.target)
            return IR_Action('stop_animation', {
                'target': target
            })

        elif isinstance(stmt, SetGrid):
            # Set grid on target object
            target_obj = self.program.get_object_by_name(stmt.target)
            if target_obj:
                target_obj.grid_cols = stmt.cols
                target_obj.grid_rows = stmt.rows
            return None  # No runtime action, just modifies IR

        elif isinstance(stmt, SetAnimations):
            # Define animations with auto-division
            target_obj = self.program.get_object_by_name(stmt.target)
            if target_obj and target_obj.grid_cols and target_obj.grid_rows:
                total_frames = target_obj.grid_cols * target_obj.grid_rows
                num_anims = len(stmt.names)
                if num_anims > 0:
                    frames_per_anim = total_frames // num_anims
                    remainder = total_frames % num_anims
                    frame = 0
                    for i, name in enumerate(stmt.names):
                        # Last animation gets remainder
                        count = frames_per_anim + (remainder if i == num_anims - 1 else 0)
                        target_obj.animations[name.lower()] = (frame, frame + count - 1)
                        frame += count
            return None  # No runtime action

        elif isinstance(stmt, SetAnimationFrames):
            # Override specific animation frame range
            target_obj = self.program.get_object_by_name(stmt.target)
            if target_obj:
                target_obj.animations[stmt.animation.lower()] = (stmt.start, stmt.end)
            return None  # No runtime action

        elif isinstance(stmt, Save):
            return IR_Action('save', {
                'slot': self.transform_expression(stmt.filepath) if stmt.filepath else None
            })

        elif isinstance(stmt, Load):
            return IR_Action('load', {
                'slot': self.transform_expression(stmt.filepath)
            })

        elif isinstance(stmt, DeleteObject):
            return IR_Action('destroy', {
                'target': stmt.name.lower(),
                'confirmed': stmt.confirmed
            })

        elif isinstance(stmt, ActivateObject):
            return IR_Action('activate', {
                'target': self.transform_expression(stmt.target)
            })

        elif isinstance(stmt, DeactivateObject):
            return IR_Action('deactivate', {
                'target': self.transform_expression(stmt.target)
            })

        elif isinstance(stmt, SpawnAt):
            return IR_Action('spawn_at', {
                'target': self.transform_expression(stmt.target) if stmt.target else None,
                'x': self.transform_expression(stmt.x),
                'y': self.transform_expression(stmt.y)
            })

        elif isinstance(stmt, MoveDirection):
            return IR_Action('move_direction', {
                'target': self.transform_expression(stmt.target),
                'direction': stmt.direction,
                'amount': self.transform_expression(stmt.amount)
            })

        elif isinstance(stmt, CloneObject):
            return IR_Action('spawn', {
                'template': stmt.source.lower(),
                'name': stmt.target.lower() if stmt.target else None,
            })

        elif isinstance(stmt, TriggerEvent):
            return IR_Action('trigger', {
                'event': stmt.event_name.lower(),
                'params': [self.transform_expression(arg) for arg in stmt.arguments]
            })

        elif isinstance(stmt, Increment):
            return self.transform_increment(stmt)

        elif isinstance(stmt, Decrement):
            return self.transform_decrement(stmt)

        elif isinstance(stmt, Return):
            return IR_Action('return', {
                'value': self.transform_expression(stmt.value) if stmt.value else None
            })

        elif isinstance(stmt, Break):
            return IR_Action('break', {})

        elif isinstance(stmt, Continue):
            return IR_Action('continue', {})

        elif isinstance(stmt, IfStatement):
            return self.transform_if_statement(stmt)

        elif isinstance(stmt, WhileLoop):
            return self.transform_while_loop(stmt)

        elif isinstance(stmt, ForLoop):
            return self.transform_for_loop(stmt)

        elif isinstance(stmt, FunctionCall):
            return IR_Action('call', {
                'function': stmt.name.lower(),
                'args': [self.transform_expression(arg) for arg in stmt.arguments]
            })

        elif isinstance(stmt, Append):
            return IR_Action('append', {
                'target': self.transform_expression(stmt.target),
                'item': self.transform_expression(stmt.item)
            })

        elif isinstance(stmt, Remove):
            return IR_Action('remove', {
                'target': self.transform_expression(stmt.target),
                'item': self.transform_expression(stmt.item)
            })

        elif isinstance(stmt, Get):
            return IR_Action('get', {
                'target': self.transform_expression(stmt.target) if stmt.target else None,
                'index': stmt.instance_index,
                'all': stmt.get_all,
                'next': stmt.get_next,
                'filter': self.transform_expression(stmt.where_condition) if stmt.where_condition else None,
                'include_hidden': stmt.include_hidden
            })

        elif isinstance(stmt, GotoScene):
            return IR_Action('goto', {
                'scene': stmt.scene,
                'level': stmt.level
            })

        elif isinstance(stmt, SaveGame):
            return IR_Action('save_game', {
                'slot': stmt.slot
            })

        elif isinstance(stmt, LoadGame):
            return IR_Action('load_game', {
                'slot': stmt.slot
            })

        else:
            # Unknown statement type - skip
            return None

    def transform_set_property(self, stmt: SetProperty) -> IR_Action:
        """Transform SetProperty to IR_Action."""
        # Determine target object and property
        if isinstance(stmt.target, PropertyAccess):
            target_obj = self.get_object_name(stmt.target.object)
            prop_name = stmt.target.property.lower()
        elif isinstance(stmt.target, Identifier):
            target_obj = None  # Top-level variable or current context
            prop_name = stmt.target.name.lower()
        else:
            target_obj = None
            prop_name = 'unknown'

        # Transform value with property context
        value = self.transform_value(stmt.value, prop_name)

        return IR_Action('set_property', {
            'target': target_obj,
            'property': prop_name,
            'value': value
        })

    def transform_increment(self, stmt: Increment) -> IR_Action:
        """Transform Increment to set_property with +1."""
        if isinstance(stmt.target, PropertyAccess):
            target_obj = self.get_object_name(stmt.target.object)
            prop_name = stmt.target.property.lower()
        else:
            target_obj = None
            prop_name = stmt.target.name.lower() if isinstance(stmt.target, Identifier) else 'unknown'

        return IR_Action('set_property', {
            'target': target_obj,
            'property': prop_name,
            'value': IR_Expression(
                type='binary_op',
                operator='+',
                left=IR_Expression(type='property_access', left=target_obj, right=prop_name),
                right=IR_Expression(type='literal', value=IR_Value('number', 1))
            )
        })

    def transform_decrement(self, stmt: Decrement) -> IR_Action:
        """Transform Decrement to set_property with -1."""
        if isinstance(stmt.target, PropertyAccess):
            target_obj = self.get_object_name(stmt.target.object)
            prop_name = stmt.target.property.lower()
        else:
            target_obj = None
            prop_name = stmt.target.name.lower() if isinstance(stmt.target, Identifier) else 'unknown'

        return IR_Action('set_property', {
            'target': target_obj,
            'property': prop_name,
            'value': IR_Expression(
                type='binary_op',
                operator='-',
                left=IR_Expression(type='property_access', left=target_obj, right=prop_name),
                right=IR_Expression(type='literal', value=IR_Value('number', 1))
            )
        })

    # =========================================================================
    # Control Flow Transformation
    # =========================================================================

    def transform_if_statement(self, stmt: IfStatement) -> IR_Conditional:
        """Transform IfStatement to IR_Conditional."""
        return IR_Conditional(
            condition=self.transform_expression(stmt.condition),
            then_actions=[self.transform_statement(s) for s in stmt.then_body if s],
            else_actions=[self.transform_statement(s) for s in (stmt.else_body or []) if s]
        )

    def transform_while_loop(self, stmt: WhileLoop) -> IR_Loop:
        """Transform WhileLoop to IR_Loop."""
        return IR_Loop(
            type='while',
            condition=self.transform_expression(stmt.condition),
            body=[self.transform_statement(s) for s in stmt.body if s]
        )

    def transform_for_loop(self, stmt: ForLoop) -> IR_Loop:
        """Transform ForLoop to IR_Loop."""
        if stmt.is_collection:
            # for item in all items
            return IR_Loop(
                type='for_each',
                iterator=stmt.variable.lower(),
                iterable=self.transform_expression(stmt.start),
                body=[self.transform_statement(s) for s in stmt.body if s]
            )
        else:
            # for i in 1 to 10 step 2
            return IR_Loop(
                type='for',
                iterator=stmt.variable.lower(),
                start=self.transform_expression(stmt.start),
                end=self.transform_expression(stmt.end),
                step=self.transform_expression(stmt.step) if stmt.step else IR_Expression(type='literal', value=IR_Value('number', 1)),
                body=[self.transform_statement(s) for s in stmt.body if s]
            )

    # =========================================================================
    # Event Transformation
    # =========================================================================

    def transform_when_statement(self, stmt: WhenStatement) -> IR_Event:
        """Transform WhenStatement to IR_Event with canonical trigger name."""
        event_name = stmt.event_name.lower()

        # Map Rosh event names to canonical IR trigger names
        if event_name == 'update':
            trigger = 'update'
        elif event_name == 'space_pressed':
            # Space bar pressed
            trigger = 'keydown:space'
        elif event_name.startswith('while_key_'):
            # Continuous key polling (while_key_left, while_key_right, etc.)
            key = event_name.replace('while_key_', '')
            trigger = f"continuous:{key}"
        elif event_name.startswith('key_'):
            # Single key press (key_r, key_space, etc.)
            key = event_name.replace('key_', '')
            trigger = f"keydown:{key}"
        elif event_name.startswith('keydown') or event_name.startswith('keyup'):
            # keydown, keyup with parameter
            key = stmt.parameters[0].lower() if stmt.parameters else 'any'
            trigger = f"{event_name}:{key}"
        elif event_name == 'collision':
            # Collision between two objects
            if len(stmt.parameters) >= 2:
                trigger = f"collision:{stmt.parameters[0]}:{stmt.parameters[1]}"
            else:
                trigger = f"collision:{':'.join(stmt.parameters)}"
        elif event_name == 'init' or event_name == 'start':
            trigger = 'init'
        else:
            # Custom event
            trigger = f"custom:{event_name}"

        return IR_Event(
            trigger=trigger,
            target=None,  # Object-specific events not yet implemented
            handler=[self.transform_statement(s) for s in stmt.body if s]
        )

    # =========================================================================
    # Function Transformation
    # =========================================================================

    def transform_function_def(self, stmt: FunctionDef) -> IR_Function:
        """Transform FunctionDef to IR_Function."""
        has_return = any(isinstance(s, Return) for s in stmt.body)

        return IR_Function(
            name=stmt.name.lower(),
            params=[p.lower() for p in stmt.parameters],
            body=[self.transform_statement(s) for s in stmt.body if s],
            returns=has_return
        )


def transform_ast_to_ir(program: Program,
                        canvas_width: int = 800,
                        canvas_height: int = 600,
                        meta: Dict[str, Any] = None,
                        project_root: str = None) -> IR_Program:
    """Convenience function to transform AST to IR.

    Args:
        program: Rosh AST Program node
        canvas_width: Canvas width for normalization
        canvas_height: Canvas height for normalization
        meta: Optional metadata from _meta/*.toml
        project_root: Project root directory for resolving load paths

    Returns:
        IR_Program
    """
    transformer = IRTransformer(canvas_width, canvas_height, meta, project_root)
    return transformer.transform(program)
