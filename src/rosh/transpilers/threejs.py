"""
Three.js Transpiler

Transpile Rosh code to Three.js JavaScript for 3D browser-based games/scenes.
Supports both native 3D and 2D→3D conversion (sprites become textured planes).

v0.1.0 - Initial implementation (Phase 1)
"""

from typing import Dict, Any, List
from .base import BaseTranspiler
from ..ast_nodes import *
from ..errors import RoshRuntimeError


class ThreeJSTranspiler(BaseTranspiler):
    """Transpile Rosh code to Three.js JavaScript

    Phase 1 Features:
    - Objects (create object ... end) → Three.js meshes
    - Basic shapes: cube, sphere, plane
    - 2D→3D: images become textured planes at z=0
    - Properties: x, y, z, width, height, depth, color
    - Default camera with OrbitControls
    - Default lighting (ambient + directional)
    - Events: update loop, keyboard input

    Future Phases:
    - Phase 2: Console/REPL integration
    - Phase 3: Dynamic object discovery, GLTF loading
    - Phase 4: Demo polish
    """

    # CSS color names to hex (same as Phaser for consistency)
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

    # Auto-assigned colors for objects (rotates through these)
    DEFAULT_COLORS = [
        0x00ff00,  # Green
        0x0000ff,  # Blue
        0xff0000,  # Red
        0xffff00,  # Yellow
        0xff00ff,  # Magenta
        0x00ffff,  # Cyan
        0xff8800,  # Orange
        0x8800ff,  # Purple
    ]

    # Default canvas size (matches Phaser for consistency)
    CANVAS_WIDTH = 800
    CANVAS_HEIGHT = 600

    def __init__(self):
        super().__init__()
        self.object_counter = 0
        self.object_properties: Dict[str, Dict[str, Any]] = {}
        self.event_handlers: Dict[str, list] = {}
        self.needs_update_loop = False
        self.needs_keyboard_input = False
        self.sprite_assets: Dict[str, str] = {}  # object_name -> texture filename
        self.text_objects: List[str] = []  # Objects with text (need special handling)

    def transpile(self, program: Program) -> str:
        """Convert Rosh Program AST to Three.js JavaScript

        Args:
            program: Rosh Program AST node

        Returns:
            Generated Three.js JavaScript code
        """
        # 1. Validate AST
        self.validate_ast(program)

        # 2. Detect features needed
        self.detect_features(program)

        # 3. Generate code
        self.emit_comment("Auto-generated from Rosh code")
        self.emit_comment("Transpiled with Rosh Three.js Transpiler v0.1.0")
        self.emit_comment("Three.js and OrbitControls loaded via HTML template")
        self.emit_blank()

        # 5. Generate scene setup
        self.emit_scene_setup()

        # 6. Generate object creation
        self.emit_comment("Game Objects")
        for statement in program.statements:
            if isinstance(statement, CreateObject):
                self.emit_create_object(statement)
        self.emit_blank()

        # 7. Generate event handlers
        if self.event_handlers:
            self.emit_event_handlers(program)

        # 8. Generate animation loop
        self.emit_animation_loop()

        # 9. Generate resize handler
        self.emit_resize_handler()

        # 10. Generate REPL console (always enabled for now)
        self.emit_repl_code()

        return self.get_code()

    def validate_ast(self, program: Program) -> None:
        """Validate AST contains only supported features

        Args:
            program: Rosh Program AST to validate

        Raises:
            RoshRuntimeError: If unsupported features found
        """
        unsupported_types = [
            (WhileLoop, "while loops"),
            (ForLoop, "for loops"),
            (Input, "user input"),
            (Import, "imports"),
            (Eval, "eval"),
            (Load, "load"),
            (Save, "save"),
        ]

        def check_node(node: ASTNode, path: str = "top level") -> None:
            for unsupported_type, feature_name in unsupported_types:
                if isinstance(node, unsupported_type):
                    raise RoshRuntimeError(
                        f"Three.js transpiler does not support '{feature_name}' yet\n"
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
        """Scan program to determine what features are needed

        Args:
            program: Rosh Program AST to scan
        """
        for statement in program.statements:
            if isinstance(statement, WhenStatement):
                event_name = statement.event_name
                if event_name not in self.event_handlers:
                    self.event_handlers[event_name] = []
                self.event_handlers[event_name].append(statement)

                if event_name == 'update':
                    self.needs_update_loop = True
                elif event_name.startswith('key_'):
                    self.needs_keyboard_input = True

            elif isinstance(statement, CreateObject):
                # Scan object body for sprites/text
                for prop_stmt in statement.body:
                    if isinstance(prop_stmt, SetProperty) and isinstance(prop_stmt.target, Identifier):
                        prop_name = prop_stmt.target.name
                        if prop_name == 'image' and isinstance(prop_stmt.value, String):
                            self.sprite_assets[statement.name] = prop_stmt.value.value
                        elif prop_name == 'text':
                            self.text_objects.append(statement.name)

    def emit_scene_setup(self) -> None:
        """Generate Three.js scene, camera, renderer, lights setup"""
        self.emit_comment("Scene Setup")
        self.emit("const scene = new THREE.Scene();")
        self.emit("scene.background = new THREE.Color(0x1a1a2e);")
        self.emit_blank()

        # Camera - starts far away for zoom-in effect
        self.emit_comment("Camera (auto-generated, use OrbitControls to navigate)")
        self.emit(f"const camera = new THREE.PerspectiveCamera(50, {self.CANVAS_WIDTH} / {self.CANVAS_HEIGHT}, 0.1, 1000);")
        self.emit("camera.position.set(0, 5, 150);  // Start far for zoom-in effect")
        self.emit("camera.lookAt(0, 0, 0);")
        self.emit("let cameraZoomTarget = 50;  // Target z position")
        self.emit("let cameraZooming = true;")
        self.emit_blank()

        # Renderer (fills window)
        self.emit_comment("Renderer")
        self.emit("const renderer = new THREE.WebGLRenderer({ antialias: true });")
        self.emit("renderer.setSize(window.innerWidth, window.innerHeight);")
        self.emit("renderer.setPixelRatio(window.devicePixelRatio);")
        self.emit("document.body.appendChild(renderer.domElement);")
        self.emit_blank()

        # OrbitControls - the "wow" factor
        self.emit_comment("OrbitControls - drag to rotate, scroll to zoom")
        self.emit("const controls = new THREE.OrbitControls(camera, renderer.domElement);")
        self.emit("controls.enableDamping = true;")
        self.emit("controls.dampingFactor = 0.05;")
        self.emit_blank()

        # WASD movement controls + arrow key rotation
        self.emit_comment("WASD movement controls + arrow key rotation")
        self.emit("const moveState = { forward: false, backward: false, left: false, right: false, up: false, down: false, rotateLeft: false, rotateRight: false };")
        self.emit("document.addEventListener('keydown', (e) => {")
        self.indent_level += 1
        self.emit("if (e.key === 'w' || e.key === 'W') moveState.forward = true;")
        self.emit("if (e.key === 's' || e.key === 'S') moveState.backward = true;")
        self.emit("if (e.key === 'a' || e.key === 'A') moveState.left = true;")
        self.emit("if (e.key === 'd' || e.key === 'D') moveState.right = true;")
        self.emit("if (e.key === 'q' || e.key === 'Q') moveState.down = true;")
        self.emit("if (e.key === 'e' || e.key === 'E') moveState.up = true;")
        self.emit("if (e.key === 'ArrowLeft') moveState.rotateLeft = true;")
        self.emit("if (e.key === 'ArrowRight') moveState.rotateRight = true;")
        self.indent_level -= 1
        self.emit("});")
        self.emit("document.addEventListener('keyup', (e) => {")
        self.indent_level += 1
        self.emit("if (e.key === 'w' || e.key === 'W') moveState.forward = false;")
        self.emit("if (e.key === 's' || e.key === 'S') moveState.backward = false;")
        self.emit("if (e.key === 'a' || e.key === 'A') moveState.left = false;")
        self.emit("if (e.key === 'd' || e.key === 'D') moveState.right = false;")
        self.emit("if (e.key === 'q' || e.key === 'Q') moveState.down = false;")
        self.emit("if (e.key === 'e' || e.key === 'E') moveState.up = false;")
        self.emit("if (e.key === 'ArrowLeft') moveState.rotateLeft = false;")
        self.emit("if (e.key === 'ArrowRight') moveState.rotateRight = false;")
        self.indent_level -= 1
        self.emit("});")
        self.emit_blank()

        # Lighting
        self.emit_comment("Lighting (auto-generated)")
        self.emit("const ambientLight = new THREE.AmbientLight(0x404040, 0.5);")
        self.emit("scene.add(ambientLight);")
        self.emit_blank()
        self.emit("const directionalLight = new THREE.DirectionalLight(0xffffff, 1);")
        self.emit("directionalLight.position.set(5, 10, 7);")
        self.emit("scene.add(directionalLight);")
        self.emit_blank()

        # Ground grid (for depth perception)
        self.emit_comment("Ground grid for depth perception")
        self.emit("const gridHelper = new THREE.GridHelper(100, 50, 0x444466, 0x333355);")
        self.emit("gridHelper.position.y = -1;")
        self.emit("scene.add(gridHelper);")
        self.emit_blank()

        # Console visibility flag (used by animation loop)
        self.emit("let consoleVisible = false;")
        self.emit_blank()

        # Keyboard state if needed
        if self.needs_keyboard_input:
            self.emit_comment("Keyboard state")
            self.emit("const keys = {};")
            self.emit("document.addEventListener('keydown', (e) => keys[e.code] = true);")
            self.emit("document.addEventListener('keyup', (e) => keys[e.code] = false);")
            self.emit_blank()

        # Texture loader if sprites used
        if self.sprite_assets:
            self.emit_comment("Texture loader")
            self.emit("const textureLoader = new THREE.TextureLoader();")
            self.emit_blank()

    def emit_create_object(self, node: CreateObject) -> None:
        """Generate Three.js mesh for a Rosh object

        Args:
            node: CreateObject AST node
        """
        obj_name = node.name

        # Collect properties from object body
        props = self._collect_properties(node)
        self.object_properties[obj_name] = props

        # Determine object type and generate appropriate mesh
        shape = props.get('shape', None)
        has_image = obj_name in self.sprite_assets
        has_text = obj_name in self.text_objects

        # Get position (default to origin, convert 2D y to 3D y)
        x = props.get('x', 0)
        y = props.get('y', 0)
        z = props.get('z', 0)

        # Convert 2D screen coordinates to 3D world coordinates
        # In 2D: y increases downward, origin at top-left
        # In 3D: y increases upward, origin at center
        # Map screen center (400, 300) to 3D (0, 2, 0) - above ground
        if 'z' not in props:
            # 2D mode: convert screen coords to world coords
            x = (x - self.CANVAS_WIDTH / 2) / 50  # Scale down and center
            # Map Y so screen center is at y=2 (above ground), higher on screen = higher in 3D
            y = (self.CANVAS_HEIGHT / 2 - y) / 50 + 2  # Flip Y, scale, offset above ground
            z = 0

        # Get size (scale down 2D pixel sizes to 3D units)
        width = props.get('width', 1)
        height = props.get('height', 1)
        depth = props.get('depth', 1)
        radius = props.get('radius', 0.5)

        # Scale down large 2D pixel values to reasonable 3D sizes
        if 'z' not in props:
            # 2D mode: scale sizes down (e.g., 8px -> 0.5 units)
            if width > 2:
                width = width / 16
            if height > 2:
                height = height / 16

        # Get color
        color = self._resolve_color(props.get('color', None))
        if color is None:
            color = self.DEFAULT_COLORS[self.object_counter % len(self.DEFAULT_COLORS)]

        # Get visibility
        visible = props.get('visible', True)

        self.emit_comment(f"Object: {obj_name}")

        if has_text:
            # Text object - create a sprite with canvas texture
            text = props.get('text', obj_name)
            font_size = props.get('font_size', 24)
            self._emit_text_sprite(obj_name, text, font_size, color, x, y, z, visible)
        elif has_image:
            # Sprite - create a textured plane
            image_file = self.sprite_assets[obj_name]
            self._emit_textured_plane(obj_name, image_file, x, y, z, width, height, visible)
        elif shape == 'sphere':
            # Sphere
            self.emit(f"const {obj_name}Geometry = new THREE.SphereGeometry({radius}, 32, 32);")
            self.emit(f"const {obj_name}Material = new THREE.MeshStandardMaterial({{ color: 0x{color:06x} }});")
            self.emit(f"const {obj_name} = new THREE.Mesh({obj_name}Geometry, {obj_name}Material);")
            self.emit(f"{obj_name}.position.set({x}, {y}, {z});")
            self.emit(f"{obj_name}.name = '{obj_name}';")
            if not visible:
                self.emit(f"{obj_name}.visible = false;")
            self.emit(f"scene.add({obj_name});")
        elif shape == 'plane':
            # Plane (for 2D elements in 3D space)
            self.emit(f"const {obj_name}Geometry = new THREE.PlaneGeometry({width}, {height});")
            self.emit(f"const {obj_name}Material = new THREE.MeshStandardMaterial({{ color: 0x{color:06x}, side: THREE.DoubleSide }});")
            self.emit(f"const {obj_name} = new THREE.Mesh({obj_name}Geometry, {obj_name}Material);")
            self.emit(f"{obj_name}.position.set({x}, {y}, {z});")
            self.emit(f"{obj_name}.name = '{obj_name}';")
            if not visible:
                self.emit(f"{obj_name}.visible = false;")
            self.emit(f"scene.add({obj_name});")
        else:
            # Default: cube (box)
            self.emit(f"const {obj_name}Geometry = new THREE.BoxGeometry({width}, {height}, {depth});")
            self.emit(f"const {obj_name}Material = new THREE.MeshStandardMaterial({{ color: 0x{color:06x} }});")
            self.emit(f"const {obj_name} = new THREE.Mesh({obj_name}Geometry, {obj_name}Material);")
            self.emit(f"{obj_name}.position.set({x}, {y}, {z});")
            self.emit(f"{obj_name}.name = '{obj_name}';")
            if not visible:
                self.emit(f"{obj_name}.visible = false;")
            self.emit(f"scene.add({obj_name});")

        # Set custom properties in userData
        known_props = {'x', 'y', 'z', 'width', 'height', 'depth', 'color', 'visible',
                       'shape', 'radius', 'text', 'font_size', 'image'}
        for prop_name, prop_value in props.items():
            if prop_name not in known_props:
                # Custom property - store in userData
                if isinstance(prop_value, str):
                    self.emit(f"{obj_name}.userData.{prop_name} = '{prop_value}';")
                elif isinstance(prop_value, bool):
                    self.emit(f"{obj_name}.userData.{prop_name} = {'true' if prop_value else 'false'};")
                else:
                    self.emit(f"{obj_name}.userData.{prop_name} = {prop_value};")

        # Assign UUID to object for REPL get command (#017)
        self.emit(f"{obj_name}.userData._rosh_uuid = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {{")
        self.indent_level += 1
        self.emit("const r = Math.random() * 16 | 0;")
        self.emit("return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);")
        self.indent_level -= 1
        self.emit("});")

        self.emit_blank()
        self.object_counter += 1

    def _emit_text_sprite(self, name: str, text: str, font_size: int, color: int, x: float, y: float, z: float, visible: bool) -> None:
        """Generate a text sprite using canvas texture

        Args:
            name: Object name
            text: Text to display
            font_size: Font size
            color: Color as hex int
            x, y, z: Position
            visible: Visibility flag
        """
        # Convert color to CSS
        css_color = f"#{color:06x}"

        self.emit(f"// Text sprite: {name}")
        self.emit(f"const {name}Canvas = document.createElement('canvas');")
        self.emit(f"const {name}Ctx = {name}Canvas.getContext('2d');")
        self.emit(f"{name}Canvas.width = 1024;")  # Wide enough for longer text
        self.emit(f"{name}Canvas.height = 256;")
        self.emit(f"{name}Ctx.fillStyle = '{css_color}';")
        # Scale font size for canvas (minimum 48px for visibility)
        canvas_font_size = max(font_size, 48)
        self.emit(f"{name}Ctx.font = 'bold {canvas_font_size}px Arial';")
        self.emit(f"{name}Ctx.textAlign = 'center';")
        self.emit(f"{name}Ctx.textBaseline = 'middle';")
        self.emit(f"{name}Ctx.fillText('{text}', 512, 128);")
        self.emit_blank()
        self.emit(f"const {name}Texture = new THREE.CanvasTexture({name}Canvas);")
        self.emit(f"const {name}Material = new THREE.SpriteMaterial({{ map: {name}Texture, transparent: true }});")
        self.emit(f"const {name} = new THREE.Sprite({name}Material);")
        self.emit(f"{name}.position.set({x}, {y}, {z});")
        self.emit(f"{name}.scale.set(20, 5, 1);")  # Large scale for visibility
        self.emit(f"{name}.name = '{name}';")
        # Store canvas/ctx for dynamic updates
        self.emit(f"{name}._canvas = {name}Canvas;")
        self.emit(f"{name}._ctx = {name}Ctx;")
        self.emit(f"{name}._text = '{text}';")
        self.emit(f"{name}._fontSize = {font_size};")
        self.emit(f"{name}._color = '{css_color}';")
        if not visible:
            self.emit(f"{name}.visible = false;")
        self.emit(f"scene.add({name});")
        # Assign UUID to object for REPL get command (#017)
        self.emit(f"{name}.userData._rosh_uuid = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {{")
        self.indent_level += 1
        self.emit("const r = Math.random() * 16 | 0;")
        self.emit("return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);")
        self.indent_level -= 1
        self.emit("});")

    def _emit_textured_plane(self, name: str, image_file: str, x: float, y: float, z: float, width: float, height: float, visible: bool) -> None:
        """Generate a textured plane for 2D sprites in 3D space

        Args:
            name: Object name
            image_file: Image filename
            x, y, z: Position
            width, height: Dimensions
            visible: Visibility flag
        """
        self.emit(f"// Textured plane (2D sprite): {name}")
        self.emit(f"const {name}Texture = textureLoader.load('assets/{image_file}');")
        self.emit(f"const {name}Geometry = new THREE.PlaneGeometry({width}, {height});")
        self.emit(f"const {name}Material = new THREE.MeshBasicMaterial({{ map: {name}Texture, transparent: true, side: THREE.DoubleSide }});")
        self.emit(f"const {name} = new THREE.Mesh({name}Geometry, {name}Material);")
        self.emit(f"{name}.position.set({x}, {y}, {z});")
        self.emit(f"{name}.name = '{name}';")
        if not visible:
            self.emit(f"{name}.visible = false;")
        self.emit(f"scene.add({name});")
        # Assign UUID to object for REPL get command (#017)
        self.emit(f"{name}.userData._rosh_uuid = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {{")
        self.indent_level += 1
        self.emit("const r = Math.random() * 16 | 0;")
        self.emit("return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);")
        self.indent_level -= 1
        self.emit("});")

    def _collect_properties(self, node: CreateObject) -> Dict[str, Any]:
        """Extract properties from CreateObject body

        Args:
            node: CreateObject AST node

        Returns:
            Dict of property_name -> value
        """
        props = {}
        for stmt in node.body:
            if isinstance(stmt, SetProperty):
                # SetProperty has target (Identifier or PropertyAccess) and value
                if isinstance(stmt.target, Identifier):
                    prop_name = stmt.target.name
                    value = self._evaluate_value(stmt.value)
                    props[prop_name] = value
        return props

    def _evaluate_value(self, value_node) -> Any:
        """Evaluate an AST value node to a Python value

        Args:
            value_node: AST node representing a value

        Returns:
            Python value (int, float, str, bool)
        """
        if isinstance(value_node, Literal):
            return value_node.value
        elif isinstance(value_node, Identifier):
            # Could be a boolean or reference
            if value_node.name == 'true':
                return True
            elif value_node.name == 'false':
                return False
            return value_node.name
        elif isinstance(value_node, BinaryOp):
            # For now, return as string (will be evaluated at runtime)
            return str(value_node)
        return None

    def _resolve_color(self, color_value) -> int:
        """Resolve a color value to hex int

        Args:
            color_value: String color name or hex value

        Returns:
            Hex int color value, or None if not resolvable
        """
        if color_value is None:
            return None
        if isinstance(color_value, int):
            return color_value
        if isinstance(color_value, str):
            color_lower = color_value.lower()
            if color_lower in self.CSS_COLORS:
                return self.CSS_COLORS[color_lower]
            # Try to parse as hex
            if color_lower.startswith('0x'):
                return int(color_lower, 16)
            if color_lower.startswith('#'):
                return int(color_lower[1:], 16)
        return None

    def emit_event_handlers(self, program: Program) -> None:
        """Generate event handler code

        Args:
            program: Full program AST for context
        """
        self.emit_comment("Event Handlers")

        # Generate handler functions
        for event_name, handlers in self.event_handlers.items():
            for i, handler in enumerate(handlers):
                func_name = f"handle_{event_name}" if i == 0 else f"handle_{event_name}_{i}"
                self.emit(f"function {func_name}() {{")
                self.indent_level += 1

                for stmt in handler.body:
                    self._emit_event_statement(stmt)

                self.indent_level -= 1
                self.emit("}")
                self.emit_blank()

    def _emit_event_statement(self, stmt) -> None:
        """Emit a statement inside an event handler

        Args:
            stmt: AST statement node
        """
        if isinstance(stmt, SetProperty):
            self._emit_set_property(stmt)
        elif isinstance(stmt, IfStatement):
            self._emit_if_statement(stmt)
        elif isinstance(stmt, Print):
            self._emit_print_statement(stmt)

    def _emit_set_property(self, stmt: SetProperty) -> None:
        """Emit a set property statement

        Args:
            stmt: SetProperty AST node
        """
        # Handle target: Identifier (simple name) or PropertyAccess (object.property)
        if isinstance(stmt.target, PropertyAccess):
            # PropertyAccess has .object (ASTNode) and .property (str)
            if isinstance(stmt.target.object, Identifier):
                obj_name = stmt.target.object.name
            else:
                obj_name = str(stmt.target.object)  # Nested access - stringify for now
            prop_name = stmt.target.property
        elif isinstance(stmt.target, Identifier):
            # Simple identifier - could be global or implied object
            obj_name = None
            prop_name = stmt.target.name
        else:
            return  # Unsupported target type

        value_code = self._emit_value(stmt.value)

        if obj_name:
            # Map Rosh properties to Three.js
            if prop_name in ['x', 'y', 'z']:
                self.emit(f"{obj_name}.position.{prop_name} = {value_code};")
            elif prop_name == 'rotation_x':
                self.emit(f"{obj_name}.rotation.x = {value_code};")
            elif prop_name == 'rotation_y':
                self.emit(f"{obj_name}.rotation.y = {value_code};")
            elif prop_name == 'rotation_z':
                self.emit(f"{obj_name}.rotation.z = {value_code};")
            elif prop_name == 'visible':
                self.emit(f"{obj_name}.visible = {value_code};")
            elif prop_name == 'color':
                color_val = self._resolve_color(self._evaluate_value(stmt.value))
                if color_val is not None:
                    self.emit(f"{obj_name}.material.color.setHex(0x{color_val:06x});")
                else:
                    self.emit(f"{obj_name}.material.color.set({value_code});")
            elif prop_name == 'width':
                # Scale geometry - more complex in Three.js
                self.emit(f"{obj_name}.scale.x = {value_code};")
            elif prop_name == 'height':
                self.emit(f"{obj_name}.scale.y = {value_code};")
            elif prop_name == 'depth':
                self.emit(f"{obj_name}.scale.z = {value_code};")
            elif prop_name == 'font_size':
                # For text sprites, need to redraw
                self.emit(f"if ({obj_name}._ctx) {{")
                self.indent_level += 1
                self.emit(f"{obj_name}._fontSize = {value_code};")
                self.emit(f"{obj_name}._ctx.clearRect(0, 0, 512, 128);")
                self.emit(f"{obj_name}._ctx.font = 'bold ' + {obj_name}._fontSize + 'px Arial';")
                self.emit(f"{obj_name}._ctx.fillStyle = {obj_name}._color;")
                self.emit(f"{obj_name}._ctx.fillText({obj_name}._text, 256, 64);")
                self.emit(f"{obj_name}.material.map.needsUpdate = true;")
                self.indent_level -= 1
                self.emit("}")
            else:
                # Generic property
                self.emit(f"{obj_name}.userData.{prop_name} = {value_code};")
        else:
            # Global variable
            self.emit(f"let {prop_name} = {value_code};")

    def _emit_if_statement(self, stmt: IfStatement) -> None:
        """Emit an if statement

        Args:
            stmt: IfStatement AST node
        """
        condition_code = self._emit_condition(stmt.condition)
        self.emit(f"if ({condition_code}) {{")
        self.indent_level += 1

        for body_stmt in stmt.then_body:
            self._emit_event_statement(body_stmt)

        self.indent_level -= 1

        if stmt.else_body:
            self.emit("} else {")
            self.indent_level += 1
            for body_stmt in stmt.else_body:
                self._emit_event_statement(body_stmt)
            self.indent_level -= 1

        self.emit("}")

    def _emit_condition(self, condition) -> str:
        """Emit a condition expression

        Args:
            condition: AST condition node

        Returns:
            JavaScript condition code
        """
        if isinstance(condition, Comparison):
            left = self._emit_value(condition.left)
            right = self._emit_value(condition.right)

            op_map = {
                'equal': '===',
                'equals': '===',
                'is': '===',
                'not equal': '!==',
                'below': '<',
                'less': '<',
                'above': '>',
                'greater': '>',
                'at most': '<=',
                'at least': '>=',
            }

            op = op_map.get(condition.operator, '===')
            return f"{left} {op} {right}"
        elif isinstance(condition, BinaryOp):
            left = self._emit_value(condition.left)
            right = self._emit_value(condition.right)

            op_map = {
                'is equal to': '===',
                'equals': '===',
                'is': '===',
                'is not equal to': '!==',
                'is below': '<',
                'is less than': '<',
                'is above': '>',
                'is greater than': '>',
                'is at most': '<=',
                'is at least': '>=',
            }

            op = op_map.get(condition.operator, condition.operator)
            return f"{left} {op} {right}"
        else:
            return self._emit_value(condition)

    def _emit_value(self, value_node) -> str:
        """Emit a value expression as JavaScript

        Args:
            value_node: AST value node

        Returns:
            JavaScript code string
        """
        if isinstance(value_node, Literal):
            value = value_node.value
            if isinstance(value, str):
                return f"'{value}'"
            elif isinstance(value, bool):
                return 'true' if value else 'false'
            else:
                return str(value)
        elif isinstance(value_node, Identifier):
            name = value_node.name
            if name == 'true':
                return 'true'
            elif name == 'false':
                return 'false'
            return name
        elif isinstance(value_node, PropertyAccess):
            # PropertyAccess has .object (ASTNode) and .property (str)
            if isinstance(value_node.object, Identifier):
                obj_name = value_node.object.name
            else:
                obj_name = str(value_node.object)
            prop_name = value_node.property

            # Map Rosh properties to Three.js
            if prop_name in ['x', 'y', 'z']:
                return f"{obj_name}.position.{prop_name}"
            elif prop_name == 'rotation_y':
                return f"{obj_name}.rotation.y"
            elif prop_name == 'visible':
                return f"{obj_name}.visible"
            elif prop_name == 'font_size':
                return f"({obj_name}._fontSize || 24)"
            elif prop_name == 'width':
                return f"{obj_name}.scale.x"
            elif prop_name == 'height':
                return f"{obj_name}.scale.y"
            else:
                return f"{obj_name}.userData.{prop_name}"
        elif isinstance(value_node, BinaryOp):
            left = self._emit_value(value_node.left)
            right = self._emit_value(value_node.right)

            op_map = {
                'plus': '+',
                'minus': '-',
                'times': '*',
                'divided by': '/',
            }
            op = op_map.get(value_node.operator, value_node.operator)
            return f"({left} {op} {right})"
        else:
            return str(value_node)

    def _emit_print_statement(self, stmt: Print) -> None:
        """Emit a print statement as console.log

        Args:
            stmt: Print AST node
        """
        value_code = self._emit_value(stmt.value)
        self.emit(f"console.log({value_code});")

    def emit_animation_loop(self) -> None:
        """Generate the Three.js animation loop"""
        self.emit_comment("Animation Loop")
        self.emit("function animate() {")
        self.indent_level += 1
        self.emit("requestAnimationFrame(animate);")
        self.emit_blank()

        # Call update handlers
        if 'update' in self.event_handlers:
            self.emit("// Update event handlers")
            for i in range(len(self.event_handlers['update'])):
                func_name = "handle_update" if i == 0 else f"handle_update_{i}"
                self.emit(f"{func_name}();")
            self.emit_blank()

        # Intro zoom animation
        self.emit("if (cameraZooming) {")
        self.indent_level += 1
        self.emit("const zoomSpeed = 0.02;")
        self.emit("camera.position.z += (cameraZoomTarget - camera.position.z) * zoomSpeed;")
        self.emit("if (Math.abs(camera.position.z - cameraZoomTarget) < 0.1) cameraZooming = false;")
        self.indent_level -= 1
        self.emit("}")
        self.emit_blank()

        # WASD movement (only when console is closed)
        self.emit("// WASD movement + arrow key rotation (disabled when console open)")
        self.emit("if (!consoleVisible) {")
        self.indent_level += 1
        self.emit("const moveSpeed = 0.5;")
        self.emit("const rotateSpeed = 0.02;")
        self.emit("if (moveState.forward) { camera.position.z -= moveSpeed; controls.target.z -= moveSpeed; }")
        self.emit("if (moveState.backward) { camera.position.z += moveSpeed; controls.target.z += moveSpeed; }")
        self.emit("if (moveState.left) { camera.position.x -= moveSpeed; controls.target.x -= moveSpeed; }")
        self.emit("if (moveState.right) { camera.position.x += moveSpeed; controls.target.x += moveSpeed; }")
        self.emit("if (moveState.up) { camera.position.y += moveSpeed; controls.target.y += moveSpeed; }")
        self.emit("if (moveState.down) { camera.position.y -= moveSpeed; controls.target.y -= moveSpeed; }")
        self.emit_blank()
        self.emit("// Arrow key rotation around target (orbit)")
        self.emit("if (moveState.rotateLeft || moveState.rotateRight) {")
        self.indent_level += 1
        self.emit("const angle = moveState.rotateLeft ? 0.03 : -0.03;")
        self.emit("const offset = camera.position.clone().sub(controls.target);")
        self.emit("offset.applyAxisAngle(new THREE.Vector3(0, 1, 0), angle);")
        self.emit("camera.position.copy(controls.target).add(offset);")
        self.emit("camera.lookAt(controls.target);")
        self.indent_level -= 1
        self.emit("}")
        self.emit_blank()
        self.emit("// Prevent going through floor")
        self.emit("if (camera.position.y < 1) { camera.position.y = 1; controls.target.y = Math.max(controls.target.y, 0); }")
        self.indent_level -= 1
        self.emit("}")
        self.emit_blank()

        # Update controls
        self.emit("controls.update();")
        self.emit("renderer.render(scene, camera);")

        self.indent_level -= 1
        self.emit("}")
        self.emit_blank()
        self.emit("animate();")
        self.emit_blank()

    def emit_resize_handler(self) -> None:
        """Generate window resize handler"""
        self.emit_comment("Resize Handler")
        self.emit("window.addEventListener('resize', () => {")
        self.indent_level += 1
        self.emit("camera.aspect = window.innerWidth / window.innerHeight;")
        self.emit("camera.updateProjectionMatrix();")
        self.emit("renderer.setSize(window.innerWidth, window.innerHeight);")
        self.indent_level -= 1
        self.emit("});")

    def emit_repl_code(self) -> None:
        """Generate in-game REPL console for Three.js"""
        self.emit_blank()
        self.emit_comment("=" * 60)
        self.emit_comment("ROSH CONSOLE - Press ` (backtick) to toggle")
        self.emit_comment("=" * 60)
        self.emit_blank()

        # CSS for console
        self.emit("// Console CSS")
        self.emit("const consoleStyle = document.createElement('style');")
        self.emit("consoleStyle.textContent = `")
        self.emit("#rosh-console {")
        self.emit("    position: fixed;")
        self.emit("    bottom: 0;")
        self.emit("    left: 0;")
        self.emit("    width: 100%;")
        self.emit("    height: 250px;")
        self.emit("    background: rgba(0, 0, 0, 0.95);")
        self.emit("    color: #00ff00;")
        self.emit("    font-family: 'Courier New', monospace;")
        self.emit("    font-size: 14px;")
        self.emit("    border-top: 2px solid #00ff00;")
        self.emit("    display: none;")
        self.emit("    flex-direction: column;")
        self.emit("    z-index: 10000;")
        self.emit("}")
        self.emit("#rosh-console.visible { display: flex; }")
        self.emit("#rosh-output {")
        self.emit("    flex: 1;")
        self.emit("    overflow-y: auto;")
        self.emit("    padding: 10px;")
        self.emit("}")
        self.emit("#rosh-output .cmd { color: #ffff00; }")
        self.emit("#rosh-output .ok { color: #33ff33; }")
        self.emit("#rosh-output .err { color: #ff3333; }")
        self.emit("#rosh-output .info { color: #00ffff; }")
        self.emit("#rosh-input-line {")
        self.emit("    padding: 10px;")
        self.emit("    border-top: 1px solid #00ff00;")
        self.emit("    display: flex;")
        self.emit("    gap: 8px;")
        self.emit("}")
        self.emit("#rosh-input-line input {")
        self.emit("    flex: 1;")
        self.emit("    background: #111;")
        self.emit("    border: 1px solid #00ff00;")
        self.emit("    color: #00ff00;")
        self.emit("    padding: 8px;")
        self.emit("    font-family: inherit;")
        self.emit("    font-size: 14px;")
        self.emit("}")
        self.emit("`;")
        self.emit("document.head.appendChild(consoleStyle);")
        self.emit_blank()

        # HTML structure
        self.emit("// Console HTML")
        self.emit("const consoleDiv = document.createElement('div');")
        self.emit("consoleDiv.id = 'rosh-console';")
        self.emit("consoleDiv.innerHTML = `")
        self.emit("    <div style='padding:8px;background:#111;border-bottom:1px solid #00ff00'>")
        self.emit("        <strong>🎮 ROSH CONSOLE</strong> <small style='color:#888'>Press \` to toggle | Commands: list, set, inspect, help</small>")
        self.emit("    </div>")
        self.emit("    <div id='rosh-output'></div>")
        self.emit("    <div id='rosh-input-line'>")
        self.emit("        <span style='color:#00ff00'>rosh></span>")
        self.emit("        <input type='text' id='rosh-input' placeholder='Enter command...' autocomplete='off'>")
        self.emit("    </div>")
        self.emit("`;")
        self.emit("document.body.appendChild(consoleDiv);")
        self.emit_blank()

        # Console logic
        self.emit("// Console logic")
        self.emit("const output = document.getElementById('rosh-output');")
        self.emit("const input = document.getElementById('rosh-input');")
        self.emit("const commandHistory = [];")
        self.emit("let historyIndex = -1;")
        self.emit_blank()

        self.emit("function log(msg, cls = '') {")
        self.indent_level += 1
        self.emit("const div = document.createElement('div');")
        self.emit("div.className = cls;")
        self.emit("div.textContent = msg;")
        self.emit("output.appendChild(div);")
        self.emit("output.scrollTop = output.scrollHeight;")
        self.indent_level -= 1
        self.emit("}")
        self.emit_blank()

        self.emit("function toggleConsole() {")
        self.indent_level += 1
        self.emit("consoleVisible = !consoleVisible;")
        self.emit("consoleDiv.classList.toggle('visible', consoleVisible);")
        self.emit("if (consoleVisible) input.focus();")
        self.indent_level -= 1
        self.emit("}")
        self.emit_blank()

        # Execute command function
        self.emit("function execCommand(cmd) {")
        self.indent_level += 1
        self.emit("log('> ' + cmd, 'cmd');")
        self.emit("try {")
        self.indent_level += 1
        self.emit("const parts = cmd.trim().toLowerCase().split(/\\s+/);")
        self.emit_blank()

        # Help command
        self.emit("if (parts[0] === 'help') {")
        self.indent_level += 1
        self.emit("log('Commands:', 'info');")
        self.emit("log('  list objects      - Show all objects in scene');")
        self.emit("log('  examine/look/inspect <name> - Show object properties');")
        self.emit("log('  get <obj>         - Get object (display)');")
        self.emit("log('  get <obj> <prop>  - Get property value');")
        self.emit("log('  get <uuid>        - Get by UUID (8+ chars)');")
        self.emit("log('  set <obj> <prop> to <value> - Change property');")
        self.emit("log('  camera reset      - Reset camera to default view');")
        self.emit("log('  camera <x> <y> <z> - Move camera to position');")
        self.emit("log('  clear             - Clear console');")
        self.indent_level -= 1
        self.emit("}")
        self.emit_blank()

        # List objects command
        self.emit("else if (parts[0] === 'list') {")
        self.indent_level += 1
        self.emit("log('Objects in scene:', 'info');")
        self.emit("scene.traverse(obj => {")
        self.indent_level += 1
        self.emit("if (obj.name && !obj.name.startsWith('_')) {")
        self.indent_level += 1
        self.emit("const type = obj.isMesh ? 'mesh' : obj.isSprite ? 'sprite' : obj.isLight ? 'light' : 'object';")
        self.emit("const pos = obj.position;")
        self.emit("log(`  ${obj.name} (${type}) at [${pos.x.toFixed(1)}, ${pos.y.toFixed(1)}, ${pos.z.toFixed(1)}]`);")
        self.indent_level -= 1
        self.emit("}")
        self.indent_level -= 1
        self.emit("});")
        self.indent_level -= 1
        self.emit("}")
        self.emit_blank()

        # Camera command
        self.emit("else if (parts[0] === 'camera') {")
        self.indent_level += 1
        self.emit("if (parts[1] === 'reset') {")
        self.indent_level += 1
        self.emit("camera.position.set(0, 5, 50);")
        self.emit("camera.lookAt(0, 0, 0);")
        self.emit("controls.target.set(0, 0, 0);")
        self.emit("log('✓ Camera reset to default view', 'ok');")
        self.indent_level -= 1
        self.emit("} else if (parts.length >= 4) {")
        self.indent_level += 1
        self.emit("const x = parseFloat(parts[1]), y = parseFloat(parts[2]), z = parseFloat(parts[3]);")
        self.emit("camera.position.set(x, y, z);")
        self.emit("log(`✓ Camera moved to [${x}, ${y}, ${z}]`, 'ok');")
        self.indent_level -= 1
        self.emit("} else {")
        self.indent_level += 1
        self.emit("log(`Camera at [${camera.position.x.toFixed(1)}, ${camera.position.y.toFixed(1)}, ${camera.position.z.toFixed(1)}]`, 'info');")
        self.indent_level -= 1
        self.emit("}")
        self.indent_level -= 1
        self.emit("}")
        self.emit_blank()

        # Inspect command (aliases: examine, look, x)
        self.emit("else if ((parts[0] === 'inspect' || parts[0] === 'examine' || parts[0] === 'look' || parts[0] === 'x') && parts[1]) {")
        self.indent_level += 1
        self.emit("const obj = scene.getObjectByName(parts[1]);")
        self.emit("if (obj) {")
        self.indent_level += 1
        self.emit("log(`${parts[1]}:`, 'info');")
        self.emit("log(`  position: [${obj.position.x.toFixed(2)}, ${obj.position.y.toFixed(2)}, ${obj.position.z.toFixed(2)}]`);")
        self.emit("log(`  visible: ${obj.visible}`);")
        self.emit("if (obj.material && obj.material.color) {")
        self.indent_level += 1
        self.emit("log(`  color: #${obj.material.color.getHexString()}`);")
        self.indent_level -= 1
        self.emit("}")
        self.emit("// Show text sprite properties")
        self.emit("if (obj._fontSize) log(`  font_size: ${obj._fontSize}`);")
        self.emit("if (obj._text) log(`  text: \"${obj._text}\"`);")
        self.emit("if (obj._color) log(`  text_color: ${obj._color}`);")
        self.emit("if (obj.scale) log(`  scale: [${obj.scale.x.toFixed(1)}, ${obj.scale.y.toFixed(1)}, ${obj.scale.z.toFixed(1)}]`);")
        self.emit("if (obj.userData) {")
        self.indent_level += 1
        self.emit("for (const [k, v] of Object.entries(obj.userData)) {")
        self.indent_level += 1
        self.emit("log(`  ${k}: ${v}`);")
        self.indent_level -= 1
        self.emit("}")
        self.indent_level -= 1
        self.emit("}")
        self.indent_level -= 1
        self.emit("} else {")
        self.indent_level += 1
        self.emit("log(`Object '${parts[1]}' not found`, 'err');")
        self.indent_level -= 1
        self.emit("}")
        self.indent_level -= 1
        self.emit("}")
        self.emit_blank()

        # Get command - unified get with space syntax and UUID support
        self.emit("// Get command - unified get (space syntax, dot syntax, UUID)")
        self.emit("else if (parts[0] === 'get' && parts.length >= 2) {")
        self.indent_level += 1
        self.emit("// Parse: 'get book', 'get book color', 'get book.color', or 'get <uuid>'")
        self.emit("const targetStr = cmd.slice(4).trim();")
        self.emit("const targetParts = targetStr.split(/[\\s.]+/);")
        self.emit("const objName = targetParts[0];")
        self.emit("const propName = targetParts[1] || null;")
        self.emit_blank()
        self.emit("// Find object by name or UUID")
        self.emit("let obj = scene.getObjectByName(objName);")
        self.emit("let foundName = objName;")
        self.emit_blank()
        self.emit("// If not found by name, try UUID lookup (8+ chars)")
        self.emit("if (!obj && objName.length >= 8) {")
        self.indent_level += 1
        self.emit("scene.traverse(child => {")
        self.indent_level += 1
        self.emit("if (!obj && child.userData && child.userData._rosh_uuid && child.userData._rosh_uuid.startsWith(objName)) {")
        self.indent_level += 1
        self.emit("obj = child;")
        self.emit("foundName = child.name || objName;")
        self.indent_level -= 1
        self.emit("}")
        self.indent_level -= 1
        self.emit("});")
        self.indent_level -= 1
        self.emit("}")
        self.emit_blank()
        self.emit("if (!obj) {")
        self.indent_level += 1
        self.emit("// List available objects")
        self.emit("const available = [];")
        self.emit("scene.traverse(child => { if (child.name && !child.name.startsWith('_')) available.push(child.name); });")
        self.emit("if (available.length > 0) {")
        self.indent_level += 1
        self.emit("log(`Object '${objName}' not found. Available: ${available.slice(0, 5).join(', ')}`, 'err');")
        self.indent_level -= 1
        self.emit("} else {")
        self.indent_level += 1
        self.emit("log(`Object '${objName}' not found`, 'err');")
        self.indent_level -= 1
        self.emit("}")
        self.emit("return;")
        self.indent_level -= 1
        self.emit("}")
        self.emit_blank()
        self.emit("// If no property requested, display the object")
        self.emit("if (!propName) {")
        self.indent_level += 1
        self.emit("const objType = obj.isMesh ? 'mesh' : obj.isSprite ? 'sprite' : obj.isLight ? 'light' : 'object';")
        self.emit("log(`<${objType}: ${foundName}>`, 'ok');")
        self.emit("return;")
        self.indent_level -= 1
        self.emit("}")
        self.emit_blank()
        self.emit("// Special case: uuid property")
        self.emit("if (propName.toLowerCase() === 'uuid') {")
        self.indent_level += 1
        self.emit("if (obj.userData && obj.userData._rosh_uuid) {")
        self.indent_level += 1
        self.emit("log(obj.userData._rosh_uuid, 'ok');")
        self.indent_level -= 1
        self.emit("} else {")
        self.indent_level += 1
        self.emit("log(`Object '${foundName}' has no UUID`, 'err');")
        self.indent_level -= 1
        self.emit("}")
        self.emit("return;")
        self.indent_level -= 1
        self.emit("}")
        self.emit_blank()
        self.emit("// Get the property value")
        self.emit("let value;")
        self.emit("if (propName === 'x') value = obj.position.x;")
        self.emit("else if (propName === 'y') value = obj.position.y;")
        self.emit("else if (propName === 'z') value = obj.position.z;")
        self.emit("else if (propName === 'visible') value = obj.visible;")
        self.emit("else if (propName === 'color' && obj.material && obj.material.color) value = '#' + obj.material.color.getHexString();")
        self.emit("else if (propName === 'scale') value = obj.scale.x;")
        self.emit("else if (obj.userData && obj.userData[propName] !== undefined) value = obj.userData[propName];")
        self.emit("else if (obj['_' + propName] !== undefined) value = obj['_' + propName];")
        self.emit("else {")
        self.indent_level += 1
        self.emit("log(`Property '${propName}' not found on '${foundName}'`, 'err');")
        self.emit("return;")
        self.indent_level -= 1
        self.emit("}")
        self.emit_blank()
        self.emit("// Display the value")
        self.emit("const displayValue = typeof value === 'number' ? value.toFixed(2) : JSON.stringify(value);")
        self.emit("log(displayValue, 'ok');")
        self.indent_level -= 1
        self.emit("}")
        self.emit_blank()

        # Set command - supports both "set logo.color to red" and "set logo color to red"
        self.emit("else if (parts[0] === 'set' && cmd.includes(' to ')) {")
        self.indent_level += 1
        self.emit("// Match both dot syntax (logo.color) and natural language (logo color)")
        self.emit("const match = cmd.match(/set\\s+(\\w+)(?:\\.|\\s+)(\\w+)\\s+to\\s+(.+)/i);")
        self.emit("if (match) {")
        self.indent_level += 1
        self.emit("const [_, objName, prop, valueStr] = match;")
        self.emit("const obj = scene.getObjectByName(objName);")
        self.emit("if (!obj) { log(`Object '${objName}' not found`, 'err'); return; }")
        self.emit("// Security: check if object is locked")
        self.emit("if (obj.userData && obj.userData.locked) {")
        self.indent_level += 1
        self.emit("log(`🔒 Security: '${objName}' is locked and cannot be modified`, 'err');")
        self.emit("return;")
        self.indent_level -= 1
        self.emit("}")
        self.emit_blank()
        self.emit("let value = valueStr.trim();")
        self.emit("// Parse value")
        self.emit("if (value === 'true') value = true;")
        self.emit("else if (value === 'false') value = false;")
        self.emit("else if (!isNaN(value)) value = parseFloat(value);")
        self.emit_blank()
        self.emit("// Apply property")
        self.emit("if (prop === 'x') { obj.position.x = value; log(`✓ ${objName}.x = ${value}`, 'ok'); }")
        self.emit("else if (prop === 'y') { obj.position.y = value; log(`✓ ${objName}.y = ${value}`, 'ok'); }")
        self.emit("else if (prop === 'z') { obj.position.z = value; log(`✓ ${objName}.z = ${value}`, 'ok'); }")
        self.emit("else if (prop === 'visible') { obj.visible = value; log(`✓ ${objName}.visible = ${value}`, 'ok'); }")
        self.emit("else if (prop === 'scale') { obj.scale.set(value, value, value); log(`✓ ${objName}.scale = ${value}`, 'ok'); }")
        self.emit("else if (prop === 'font_size') {")
        self.indent_level += 1
        self.emit("if (obj._ctx) {")
        self.indent_level += 1
        self.emit("obj._fontSize = value;")
        self.emit("obj._ctx.clearRect(0, 0, obj._canvas.width, obj._canvas.height);")
        self.emit("obj._ctx.fillStyle = obj._color || '#ffffff';")
        self.emit("obj._ctx.font = 'bold ' + value + 'px Arial';")
        self.emit("obj._ctx.textAlign = 'center';")
        self.emit("obj._ctx.textBaseline = 'middle';")
        self.emit("obj._ctx.fillText(obj._text || '', obj._canvas.width/2, obj._canvas.height/2);")
        self.emit("obj.material.map.needsUpdate = true;")
        self.emit("log(`✓ ${objName}.font_size = ${value}`, 'ok');")
        self.indent_level -= 1
        self.emit("} else {")
        self.indent_level += 1
        self.emit("log(`Cannot set font_size on ${objName} (not a text object)`, 'err');")
        self.indent_level -= 1
        self.emit("}")
        self.indent_level -= 1
        self.emit("}")
        self.emit("else if (prop === 'color') {")
        self.indent_level += 1
        self.emit("// Handle text sprites (canvas-based)")
        self.emit("if (obj._ctx && obj._canvas) {")
        self.indent_level += 1
        self.emit("obj._color = value;")
        self.emit("obj._ctx.clearRect(0, 0, obj._canvas.width, obj._canvas.height);")
        self.emit("obj._ctx.fillStyle = value;")
        self.emit("obj._ctx.font = 'bold ' + (obj._fontSize || 48) + 'px Arial';")
        self.emit("obj._ctx.textAlign = 'center';")
        self.emit("obj._ctx.textBaseline = 'middle';")
        self.emit("obj._ctx.fillText(obj._text || objName, obj._canvas.width/2, obj._canvas.height/2);")
        self.emit("obj.material.map.needsUpdate = true;")
        self.emit("log(`✓ ${objName}.color = ${value}`, 'ok');")
        self.indent_level -= 1
        self.emit("}")
        self.emit("// Handle meshes with material")
        self.emit("else if (obj.material && obj.material.color) {")
        self.indent_level += 1
        self.emit("obj.material.color.set(value);")
        self.emit("log(`✓ ${objName}.color = ${value}`, 'ok');")
        self.indent_level -= 1
        self.emit("}")
        self.emit("else { log(`Cannot set color on ${objName}`, 'err'); }")
        self.indent_level -= 1
        self.emit("}")
        self.emit("else {")
        self.indent_level += 1
        self.emit("const knownProps = ['x', 'y', 'z', 'visible', 'scale', 'color', 'font_size', 'text'];")
        self.emit("if (knownProps.some(p => prop.toLowerCase().includes(p.replace('_','')))) {")
        self.indent_level += 1
        self.emit("log(`Unknown property '${prop}'. Did you mean: ${knownProps.join(', ')}?`, 'err');")
        self.indent_level -= 1
        self.emit("} else {")
        self.indent_level += 1
        self.emit("log(`Unknown property '${prop}' on ${objName}`, 'err');")
        self.indent_level -= 1
        self.emit("}")
        self.indent_level -= 1
        self.emit("}")
        self.indent_level -= 1
        self.emit("} else {")
        self.indent_level += 1
        self.emit("log('Usage: set <object>.<property> to <value>', 'err');")
        self.indent_level -= 1
        self.emit("}")
        self.indent_level -= 1
        self.emit("}")
        self.emit_blank()

        # Clear command
        self.emit("else if (parts[0] === 'clear') {")
        self.indent_level += 1
        self.emit("output.innerHTML = '';")
        self.indent_level -= 1
        self.emit("}")
        self.emit_blank()

        self.emit("else if (cmd.trim()) {")
        self.indent_level += 1
        self.emit("log(`Unknown command: ${parts[0]}. Type 'help' for commands.`, 'err');")
        self.indent_level -= 1
        self.emit("}")

        # Close try block and add catch
        self.indent_level -= 1
        self.emit("} catch (e) {")
        self.indent_level += 1
        self.emit("log(`Error: ${e.message}`, 'err');")
        self.indent_level -= 1
        self.emit("}")

        self.indent_level -= 1
        self.emit("}")
        self.emit_blank()

        # Key handler
        self.emit("// Toggle with backtick")
        self.emit("document.addEventListener('keydown', e => {")
        self.indent_level += 1
        self.emit("if (e.key === '`') { e.preventDefault(); toggleConsole(); }")
        self.indent_level -= 1
        self.emit("});")
        self.emit_blank()

        # Input handler with history
        self.emit("// Execute on Enter, history with up/down arrows")
        self.emit("input.addEventListener('keydown', e => {")
        self.indent_level += 1
        self.emit("if (e.key === 'Enter' && input.value.trim()) {")
        self.indent_level += 1
        self.emit("commandHistory.push(input.value);")
        self.emit("historyIndex = commandHistory.length;")
        self.emit("execCommand(input.value);")
        self.emit("input.value = '';")
        self.indent_level -= 1
        self.emit("} else if (e.key === 'ArrowUp') {")
        self.indent_level += 1
        self.emit("e.preventDefault();")
        self.emit("if (historyIndex > 0) {")
        self.indent_level += 1
        self.emit("historyIndex--;")
        self.emit("input.value = commandHistory[historyIndex];")
        self.indent_level -= 1
        self.emit("}")
        self.indent_level -= 1
        self.emit("} else if (e.key === 'ArrowDown') {")
        self.indent_level += 1
        self.emit("e.preventDefault();")
        self.emit("if (historyIndex < commandHistory.length - 1) {")
        self.indent_level += 1
        self.emit("historyIndex++;")
        self.emit("input.value = commandHistory[historyIndex];")
        self.indent_level -= 1
        self.emit("} else {")
        self.indent_level += 1
        self.emit("historyIndex = commandHistory.length;")
        self.emit("input.value = '';")
        self.indent_level -= 1
        self.emit("}")
        self.indent_level -= 1
        self.emit("}")
        self.indent_level -= 1
        self.emit("});")
        self.emit_blank()

        self.emit("log('🎮 Rosh Console ready! Press ` to toggle.', 'info');")
