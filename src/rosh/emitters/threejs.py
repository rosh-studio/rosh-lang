"""
Three.js Emitter - IR to Three.js JavaScript

Converts IR representation to Three.js JavaScript code for 3D scenes.
This is a "mechanical translator" - all semantic decisions are in the IR.

Usage:
    from rosh.emitters.threejs import ThreeJSEmitter

    ir = transform_ast_to_ir(ast)
    emitter = ThreeJSEmitter(ir)
    js_code = emitter.emit()

See: rosh-dev/proposals/ROSH-IR-SPECIFICATION.md
"""

import json
from typing import Dict, Any, Set, List
from .base import BaseEmitter
from ..ir import (
    IR_Program, IR_Object, IR_Event, IR_Action, IR_Function,
    IR_Value, IR_Expression, IR_Conditional, IR_Loop
)
from .. import __version__


class ThreeJSEmitter(BaseEmitter):
    """Emit Three.js JavaScript from Rosh IR.

    Generates a complete Three.js scene including:
    - Scene, camera, renderer, lights setup
    - Objects as 3D meshes (cubes, spheres, planes)
    - OrbitControls for camera manipulation
    - WASD movement controls
    - Animation loop with update handlers
    - In-game REPL console
    """

    # CSS color names to hex
    CSS_COLORS = {
        'white': 0xffffff, 'black': 0x000000, 'red': 0xff0000,
        'green': 0x00ff00, 'blue': 0x0000ff, 'yellow': 0xffff00,
        'cyan': 0x00ffff, 'magenta': 0xff00ff, 'orange': 0xff8800,
        'purple': 0x8800ff, 'pink': 0xff69b4, 'gray': 0x888888,
        'grey': 0x888888, 'gold': 0xffd700, 'silver': 0xc0c0c0,
    }

    # Default object colors (rotates through these)
    DEFAULT_COLORS = [
        0x00ff00, 0x0000ff, 0xff0000, 0xffff00,
        0xff00ff, 0x00ffff, 0xff8800, 0x8800ff,
    ]

    def __init__(self, ir: IR_Program, meta: Dict[str, Any] = None):
        super().__init__(ir, meta)
        self.color_index = 0
        self.sprite_assets: Set[str] = set()
        self.sound_assets: Set[str] = set()
        self.text_objects: List[str] = []
        self.player_objects: Set[str] = set()
        self.hud_objects: List[tuple] = []  # (hud_name, target_name)
        self.collision_events: List[tuple] = []  # (obj_a, obj_b, handler_lines)
        self.keydown_events: Dict[str, List[str]] = {}  # key -> handler lines
        self.needs_keyboard = False
        self.update_handlers: List[IR_Event] = []
        self.key_handlers: Dict[str, List] = {}  # key -> list of handlers

        # Scene/level system
        self.uses_scenes = False
        self.scene_objects: Dict[str, list] = {}  # scene_name -> [object_names]
        self.level_objects: Dict[int, list] = {}  # level_num -> [object_names]

        # Save/Load support
        self.uses_save_load = False

        # Arcade mode (2D game on 3D plane)
        self.arcade_mode = self.ir.metadata.extra.get('mode') == 'arcade'

        # Scan IR to detect features
        self._detect_features()
        # Capability bridge metadata
        self.capability_manifest = {
            "schema_version": 1,
            "capabilities": []
        }
        self.capability_handler_defs: Dict[str, str] = {}
        self.capability_policy = self._build_capability_policy()
        self._register_default_capabilities()

    def _detect_features(self):
        """Scan IR to detect what features are needed."""
        for obj in self.ir.objects:
            # Player objects
            if obj.parent_type == 'player':
                self.player_objects.add(obj.name)
                self.needs_keyboard = True

            # Scene/level detection
            if obj.scene is not None:
                self.uses_scenes = True
                if obj.scene not in self.scene_objects:
                    self.scene_objects[obj.scene] = []
                self.scene_objects[obj.scene].append(obj.name)
            if obj.level is not None:
                self.uses_scenes = True
                if obj.level not in self.level_objects:
                    self.level_objects[obj.level] = []
                self.level_objects[obj.level].append(obj.name)

            # Sprites
            if 'sprite' in obj.properties:
                sprite_val = obj.properties['sprite']
                if sprite_val.type == 'string':
                    self.sprite_assets.add(sprite_val.value)

            # Text objects
            if 'text' in obj.properties:
                self.text_objects.append(obj.name)

            # HUD objects (have 'target' property)
            if 'target' in obj.properties:
                target_val = obj.properties['target']
                target_name = target_val.value if hasattr(target_val, 'value') else str(target_val)
                self.hud_objects.append((obj.name, target_name))

        for event in self.ir.events:
            if event.trigger == 'update':
                self.update_handlers.append(event)
            elif event.trigger.startswith('keydown:'):
                key = event.trigger.split(':')[1]
                handler_lines = self._generate_handler_lines(event)
                if key not in self.keydown_events:
                    self.keydown_events[key] = []
                self.keydown_events[key].extend(handler_lines)
                self.needs_keyboard = True
            elif event.trigger.startswith('collision:'):
                parts = event.trigger.split(':')
                if len(parts) >= 3:
                    obj_a, obj_b = parts[1], parts[2]
                    handler_lines = self._generate_handler_lines(event)
                    self.collision_events.append((obj_a, obj_b, handler_lines))

            # Scan for sound assets
            self._scan_actions_for_sounds(event.handler)

        # Also scan init actions for sounds
        self._scan_actions_for_sounds(self.ir.init_actions)

    def _build_capability_policy(self) -> Dict[str, Any]:
        """Build capability policy from project meta."""
        policy = self.meta.get('engine_capabilities', {}) or {}
        allow_tags = policy.get('allow', ['safe'])
        deny_tags = policy.get('deny', [])
        allow_capabilities = policy.get('allow_capabilities', [])
        deny_capabilities = policy.get('deny_capabilities', [])
        allow_passthrough = policy.get('allow_passthrough', False)
        return {
            "allow_tags": allow_tags,
            "deny_tags": deny_tags,
            "allow_capabilities": allow_capabilities,
            "deny_capabilities": deny_capabilities,
            "allow_passthrough": allow_passthrough
        }

    def _register_capability(self, name: str, handler: str = None, applies_to=None,
                              tags=None, args=None, description: str = ""):
        """Register a capability entry and associate it with a runtime handler."""
        handler = handler or name
        entry = {
            "name": name,
            "handler": handler,
            "applies_to": applies_to or [],
            "tags": tags or [],
            "args": args or [],
            "doc": description
        }
        self.capability_manifest["capabilities"].append(entry)

    def _register_default_capabilities(self):
        """Register built-in capability metadata."""
        self._register_capability(
            "color",
            handler="color",
            applies_to=["mesh", "text", "sprite", "hud"],
            tags=["safe"],
            args=["css_or_hex"],
            description="Change mesh or text color."
        )
        self._register_capability(
            "font_size",
            handler="font_size",
            applies_to=["text", "hud"],
            tags=["safe"],
            args=["pixels"],
            description="Adjust text sprite font size."
        )
        self._register_capability(
            "font",
            handler="font",
            applies_to=["text", "hud"],
            tags=["safe"],
            args=["font_family"],
            description="Set font family (default: Inter). Examples: 'Arial', 'Georgia', 'Courier New'."
        )
        self._register_capability(
            "text",
            handler="text",
            applies_to=["text", "hud"],
            tags=["safe"],
            args=["value"],
            description="Update HUD/text sprite contents."
        )
        self._register_capability(
            "scale",
            handler="scale",
            applies_to=["mesh", "sprite"],
            tags=["safe"],
            args=["uniform|x y z"],
            description="Scale objects uniformly or per-axis."
        )
        self._register_capability(
            "spin",
            handler="spin",
            applies_to=["mesh", "sprite"],
            tags=["safe"],
            args=["xSpeed ySpeed zSpeed"],
            description="Rotate objects continuously (degrees per second)."
        )
        self._register_capability(
            "bounce",
            handler="bounce",
            applies_to=["mesh", "sprite"],
            tags=["safe"],
            args=["amplitude frequency"],
            description="Apply vertical bounce animation (frequency per second)."
        )
        self._register_capability(
            "pulse",
            handler="pulse",
            applies_to=["mesh", "sprite", "text", "hud"],
            tags=["safe"],
            args=["amplitude frequency"],
            description="Scale object in/out with a sine wave (amplitude multiplier, frequency in Hz)."
        )
        self._register_capability(
            "orbit",
            handler="orbit",
            applies_to=["mesh", "sprite"],
            tags=["safe"],
            args=["radius speed [height]"],
            description="Orbit around the object's starting point (radius in world units, speed in degrees/sec, optional height override)."
        )

    def _scan_actions_for_sounds(self, actions):
        """Scan actions for sound assets."""
        for action in actions:
            if isinstance(action, IR_Action):
                if action.type == 'play_sound':
                    self.sound_assets.add(action.params.get('asset', ''))
            elif isinstance(action, IR_Conditional):
                self._scan_actions_for_sounds(action.then_actions)
                self._scan_actions_for_sounds(action.else_actions)

    def _generate_handler_lines(self, event: IR_Event) -> List[str]:
        """Generate handler code lines for an event."""
        lines = []
        for action in event.handler:
            if action:
                code = self.emit_action(action)
                if code:
                    lines.append(code)
        return lines if lines else ['// no-op']

    def emit(self) -> str:
        """Generate complete Three.js JavaScript code."""
        if self.arcade_mode:
            return self._emit_arcade_mode()

        self._emit_header()
        self._emit_scene_setup()
        self._emit_objects()
        self._emit_init_actions()  # Emit top-level set statements
        if self.uses_scenes:
            self._emit_scene_visibility_function()
        if self.uses_save_load:
            self._emit_save_load_functions()
        self._emit_functions()
        self._emit_event_handlers()
        self._emit_capability_runtime()
        self._emit_animation_loop()
        self._emit_resize_handler()
        self._emit_repl_console()

        return self.get_code()

    def _emit_arcade_mode(self) -> str:
        """Emit arcade mode - 2D game rendered on a 3D plane."""
        width = self.ir.metadata.canvas_width
        height = self.ir.metadata.canvas_height

        self._emit_header()
        self.write_comment("=== ARCADE MODE: 2D game on 3D plane ===")
        self.write_blank()

        # Collect sprite assets for loading
        for obj in self.ir.objects:
            sprite = obj.get_property('sprite')
            if sprite:
                self.sprite_assets.add(sprite)
        # Check for sounds in events
        for event in self.ir.events:
            for action in event.handler:
                if hasattr(action, 'action_type') and action.action_type == 'play_sound':
                    sound = action.params.get('sound', '')
                    if sound:
                        self.sound_assets.add(sound)

        # Scene setup
        self.write_comment("3D Scene Setup")
        self.write("const scene = new THREE.Scene();")
        self.write("scene.background = new THREE.Color(0x1a1a2e);")
        self.write_blank()

        self.write_comment("Camera - looking at arcade screen")
        self.write(f"const camera = new THREE.PerspectiveCamera(50, window.innerWidth / window.innerHeight, 0.1, 1000);")
        self.write("camera.position.set(0, 0, 600);")
        self.write("camera.lookAt(0, 0, 0);")
        self.write_blank()

        self.write_comment("Renderer")
        self.write("const renderer = new THREE.WebGLRenderer({ antialias: true });")
        self.write("renderer.setSize(window.innerWidth, window.innerHeight);")
        self.write("renderer.setPixelRatio(window.devicePixelRatio);")
        self.write("document.body.appendChild(renderer.domElement);")
        self.write_blank()

        self.write_comment("OrbitControls for zoom/pan")
        self.write("const controls = new THREE.OrbitControls(camera, renderer.domElement);")
        self.write("controls.enableDamping = true;")
        self.write("controls.dampingFactor = 0.05;")
        self.write("controls.minDistance = 300;")
        self.write("controls.maxDistance = 1200;")
        self.write_blank()

        # 2D Canvas for the game
        self.write_comment("2D Game Canvas (off-screen)")
        self.write(f"const gameCanvas = document.createElement('canvas');")
        self.write(f"gameCanvas.width = {width};")
        self.write(f"gameCanvas.height = {height};")
        self.write("const ctx = gameCanvas.getContext('2d');")
        self.write_blank()

        # Arcade screen plane
        self.write_comment("Arcade Screen Plane")
        self.write(f"const screenGeometry = new THREE.PlaneGeometry({width}, {height});")
        self.write("const screenTexture = new THREE.CanvasTexture(gameCanvas);")
        self.write("screenTexture.minFilter = THREE.LinearFilter;")
        self.write("const screenMaterial = new THREE.MeshBasicMaterial({ map: screenTexture });")
        self.write("const arcadeScreen = new THREE.Mesh(screenGeometry, screenMaterial);")
        self.write("scene.add(arcadeScreen);")
        self.write_blank()

        # Add subtle glow/frame effect
        self.write_comment("Arcade Cabinet Frame")
        self.write(f"const frameGeometry = new THREE.PlaneGeometry({width + 40}, {height + 40});")
        self.write("const frameMaterial = new THREE.MeshBasicMaterial({ color: 0x333333 });")
        self.write("const frame = new THREE.Mesh(frameGeometry, frameMaterial);")
        self.write("frame.position.z = -1;")
        self.write("scene.add(frame);")
        self.write_blank()

        # Asset loading
        self._emit_arcade_asset_loading()

        # Game state object registry
        self.write_comment("Game Objects Registry")
        self.write("const ROSH_OBJECTS = {};")
        self.write("const meta = { userData: {} };")
        self.write_blank()

        # Emit 2D game objects as data
        self._emit_arcade_objects()

        # Emit functions
        self._emit_arcade_functions()

        # Emit event handlers
        self._emit_arcade_event_handlers()

        # 2D Render function
        self._emit_arcade_render()

        # Animation loop
        self._emit_arcade_animation_loop()

        # Resize handler
        self._emit_resize_handler()

        # REPL Console
        self._emit_repl_console()

        # Arcade mode REPL overrides
        self._emit_arcade_repl_overrides()

        return self.get_code()

    def _emit_arcade_repl_overrides(self):
        """Override REPL commands for arcade mode (2D objects)."""
        width = self.ir.metadata.canvas_width
        height = self.ir.metadata.canvas_height

        self.write_blank()
        self.write_comment("Arcade Mode REPL Overrides")
        # Override scene.getObjectByName to use ROSH_OBJECTS
        self.write("scene.getObjectByName = (name) => ROSH_OBJECTS[name];")
        # Override scene.traverse to iterate ROSH_OBJECTS
        self.write("scene.traverse = (fn) => { for (const name in ROSH_OBJECTS) { const o = ROSH_OBJECTS[name]; o.name = name; fn(o); } };")
        # Map position property access to x/y with normalized-to-pixel conversion
        self.write("for (const name in ROSH_OBJECTS) {")
        self.indent()
        self.write("const obj = ROSH_OBJECTS[name];")
        # Position proxy: converts normalized (0-1) to pixels, passes through pixel values
        self.write(f"obj.position = {{")
        self.indent()
        self.write(f"get x() {{ return obj.x; }},")
        self.write(f"set x(v) {{ obj.x = (v >= 0 && v <= 1) ? v * {width} : v; }},")
        self.write(f"get y() {{ return obj.y; }},")
        self.write(f"set y(v) {{ obj.y = (v >= 0 && v <= 1) ? v * {height} : v; }},")
        self.write(f"z: 0")
        self.dedent()
        self.write("};")
        self.dedent()
        self.write("}")
        self.write_blank()

    def _emit_arcade_asset_loading(self):
        """Emit asset loading for arcade mode."""
        self.write_comment("Asset Loading")
        self.write("const assets = {};")
        self.write("let assetsLoaded = 0;")
        self.write(f"const totalAssets = {len(self.sprite_assets)};")
        self.write_blank()

        if self.sprite_assets:
            self.write("function loadAssets(callback) {")
            self.indent()
            self.write("if (totalAssets === 0) { callback(); return; }")
            for sprite in self.sprite_assets:
                self.write(f"const img_{sprite.replace('.', '_').replace('-', '_')} = new Image();")
                self.write(f"img_{sprite.replace('.', '_').replace('-', '_')}.onload = () => {{ assetsLoaded++; if (assetsLoaded >= totalAssets) callback(); }};")
                self.write(f"img_{sprite.replace('.', '_').replace('-', '_')}.src = 'assets/{sprite}';")
                self.write(f"assets['{sprite}'] = img_{sprite.replace('.', '_').replace('-', '_')};")
            self.dedent()
            self.write("}")
        else:
            self.write("function loadAssets(callback) { callback(); }")
        self.write_blank()

    def _arcade_get_value(self, val, canvas_dim=None):
        """Convert IR value/expression to a simple Python value for arcade mode."""
        if val is None:
            return 0
        if isinstance(val, (int, float, bool)):
            # Convert normalized (0-1) to pixels if needed
            if canvas_dim and isinstance(val, float) and 0 <= val <= 1:
                return int(canvas_dim * val)
            return val
        if isinstance(val, str):
            return val
        if isinstance(val, IR_Expression):
            # Try to evaluate simple expressions
            if val.type == 'literal' and hasattr(val, 'value'):
                return self._arcade_get_value(val.value.value if hasattr(val.value, 'value') else val.value, canvas_dim)
            if val.type == 'unary_op' and val.operator == '-':
                inner = self._arcade_get_value(val.left, canvas_dim) if val.left else self._arcade_get_value(val.right, canvas_dim)
                if isinstance(inner, (int, float)):
                    return -inner
            # Fall back to emitting as JS expression
            return self.emit_expression(val)
        if isinstance(val, IR_Value):
            return self._arcade_get_value(val.value, canvas_dim)
        return val

    def _emit_arcade_objects(self):
        """Emit 2D game objects as JavaScript data."""
        self.write_comment("Game Objects")
        width = self.ir.metadata.canvas_width
        height = self.ir.metadata.canvas_height

        for obj in self.ir.objects:
            name = obj.name

            # Get properties using get_property and convert to simple values
            x = self._arcade_get_value(obj.get_property('x', 0), width)
            y = self._arcade_get_value(obj.get_property('y', 0), height)
            w = self._arcade_get_value(obj.get_property('width', 50), width)
            h = self._arcade_get_value(obj.get_property('height', 50), height)
            visible = obj.get_property('visible', True)
            color_raw = obj.get_property('color', 0x00ff00)
            sprite = obj.get_property('sprite')
            text = obj.get_property('text')
            font_size = self._arcade_get_value(obj.get_property('font_size', 16))

            # Convert color to CSS hex string
            if isinstance(color_raw, int):
                color = f"#{color_raw:06x}"
            elif isinstance(color_raw, str) and color_raw.startswith('#'):
                color = color_raw
            else:
                color = f"#{self.CSS_COLORS.get(str(color_raw).lower(), 0x00ff00):06x}"

            # Collect custom properties
            custom_props = {}
            for key, ir_val in obj.properties.items():
                if key not in ('x', 'y', 'width', 'height', 'visible', 'color', 'sprite', 'text', 'font_size'):
                    val = ir_val.value
                    if isinstance(val, str):
                        custom_props[key] = f"'{val}'"
                    elif isinstance(val, bool):
                        custom_props[key] = str(val).lower()
                    else:
                        custom_props[key] = val

            self.write(f"const {name} = {{")
            self.indent()
            self.write(f"x: {x},")
            self.write(f"y: {y},")
            self.write(f"width: {w},")
            self.write(f"height: {h},")
            self.write(f"visible: {str(visible).lower()},")
            self.write(f"color: '{color}',")
            if sprite:
                self.write(f"sprite: '{sprite}',")
            if text:
                self.write(f"text: '{text}',")
                self.write(f"font_size: {font_size},")
            # userData with custom properties (matching 3D mode structure)
            if custom_props:
                props_str = ", ".join(f"{k}: {v}" for k, v in custom_props.items())
                self.write(f"userData: {{ {props_str} }}")
            else:
                self.write(f"userData: {{}}")
            self.dedent()
            self.write("};")
            self.write(f"ROSH_OBJECTS['{name}'] = {name};")
        self.write_blank()

    def _emit_arcade_functions(self):
        """Emit user-defined functions for arcade mode."""
        self.write_comment("User Functions")
        for func in self.ir.functions:
            self.write(f"function {func.name}() {{")
            self.indent()
            for action in func.body:
                code = self.emit_action(action)
                if code:
                    self.write(code)
            self.dedent()
            self.write("}")
        self.write_blank()

    def _emit_arcade_event_handlers(self):
        """Emit event handlers for arcade mode."""
        self.write_comment("Keyboard State")
        self.write("const keyState = {};")
        self.write("let consoleVisible = false;")
        self.write_blank()

        # Collect handlers by type
        update_actions = []
        keydown_handlers = {}
        while_key_handlers = {}

        for event in self.ir.events:
            trigger = event.trigger
            if trigger == 'update':
                update_actions.extend(event.handler)
            elif trigger.startswith('keydown:'):
                key = trigger.split(':')[1]
                if key not in keydown_handlers:
                    keydown_handlers[key] = []
                keydown_handlers[key].extend(event.handler)
            elif trigger.startswith('while_key:') or trigger.startswith('continuous:'):
                key = trigger.split(':')[1]
                if key not in while_key_handlers:
                    while_key_handlers[key] = []
                while_key_handlers[key].extend(event.handler)

        # Store update actions for animation loop
        self._arcade_update_actions = update_actions
        self._arcade_while_key_handlers = while_key_handlers

        # Keyboard event listeners
        self.write("document.addEventListener('keydown', (e) => {")
        self.indent()
        self.write("if (consoleVisible) return;")
        self.write("keyState[e.code] = true;")

        for key, actions in keydown_handlers.items():
            key_code = self._get_key_code(key)
            self.write(f"if (e.code === '{key_code}') {{")
            self.indent()
            for action in actions:
                code = self.emit_action(action)
                if code:
                    self.write(code)
            self.dedent()
            self.write("}")

        self.dedent()
        self.write("});")
        self.write_blank()

        self.write("document.addEventListener('keyup', (e) => {")
        self.indent()
        self.write("keyState[e.code] = false;")
        self.dedent()
        self.write("});")
        self.write_blank()

    def _get_key_code(self, key: str) -> str:
        """Convert Rosh key name to JavaScript key code."""
        key_map = {
            'space': 'Space',
            'left': 'ArrowLeft',
            'right': 'ArrowRight',
            'up': 'ArrowUp',
            'down': 'ArrowDown',
            'r': 'KeyR',
            'p': 'KeyP',
        }
        return key_map.get(key.lower(), f'Key{key.upper()}')

    def _emit_arcade_render(self):
        """Emit 2D rendering function."""
        self.write_comment("2D Render Function")
        self.write("function render2D() {")
        self.indent()
        self.write("ctx.fillStyle = '#1a1a2e';")
        self.write(f"ctx.fillRect(0, 0, {self.ir.metadata.canvas_width}, {self.ir.metadata.canvas_height});")
        self.write_blank()

        self.write("// Render all visible objects")
        self.write("for (const name in ROSH_OBJECTS) {")
        self.indent()
        self.write("const obj = ROSH_OBJECTS[name];")
        self.write("if (!obj.visible) continue;")
        self.write_blank()

        self.write("// Draw sprite or shape")
        self.write("if (obj.sprite && assets[obj.sprite]) {")
        self.indent()
        self.write("ctx.drawImage(assets[obj.sprite], obj.x - obj.width/2, obj.y - obj.height/2, obj.width, obj.height);")
        self.dedent()
        self.write("} else if (obj.text) {")
        self.indent()
        self.write("ctx.fillStyle = obj.color || '#ffffff';")
        self.write("ctx.font = (obj.font_size || 16) + 'px Arial';")
        self.write("ctx.textAlign = 'center';")
        self.write("ctx.fillText(obj.text, obj.x, obj.y);")
        self.dedent()
        self.write("} else {")
        self.indent()
        self.write("ctx.fillStyle = obj.color || '#00ff00';")
        self.write("ctx.fillRect(obj.x - obj.width/2, obj.y - obj.height/2, obj.width, obj.height);")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")
        self.write_blank()

        self.write("// Update texture")
        self.write("screenTexture.needsUpdate = true;")
        self.dedent()
        self.write("}")
        self.write_blank()

    def _emit_arcade_animation_loop(self):
        """Emit animation loop for arcade mode."""
        self.write_comment("Animation Loop")
        self.write("function animate() {")
        self.indent()
        self.write("requestAnimationFrame(animate);")
        self.write_blank()

        # While-key handlers
        if hasattr(self, '_arcade_while_key_handlers'):
            for key, actions in self._arcade_while_key_handlers.items():
                key_code = self._get_key_code(key)
                self.write(f"if (keyState['{key_code}']) {{")
                self.indent()
                for action in actions:
                    code = self.emit_action(action)
                    if code:
                        self.write(code)
                self.dedent()
                self.write("}")

        # Update handlers
        if hasattr(self, '_arcade_update_actions'):
            for action in self._arcade_update_actions:
                code = self.emit_action(action)
                if code:
                    self.write(code)

        self.write_blank()
        self.write("render2D();")
        self.write("controls.update();")
        self.write("renderer.render(scene, camera);")
        self.dedent()
        self.write("}")
        self.write_blank()

        self.write("// Start after assets loaded")
        self.write("loadAssets(() => {")
        self.indent()
        self.write("console.log('Assets loaded, starting game');")
        self.write("animate();")
        self.dedent()
        self.write("});")
        self.write_blank()

    def write_comment(self, text: str):
        """JavaScript-style comments."""
        self.write(f"// {text}")

    # =========================================================================
    # Scene Setup
    # =========================================================================

    def _emit_header(self):
        """Emit file header."""
        self.write_comment("Auto-generated from Rosh IR")
        self.write_comment("Emitter: Three.js v0.2.0")
        self.write_comment("Three.js and OrbitControls loaded via HTML template")
        self.write_blank()

    def _emit_scene_setup(self):
        """Emit Three.js scene, camera, renderer, lights."""
        width = self.ir.metadata.canvas_width
        height = self.ir.metadata.canvas_height

        self.write_comment("Scene Setup")
        self.write("const scene = new THREE.Scene();")
        self.write("scene.background = new THREE.Color(0x1a1a2e);")
        self.write_blank()

        # Implicit meta object for game state (v0.2.7+)
        self.write_comment("Meta object for game state")
        self.write("const meta = { userData: {} };")
        self.write_blank()

        # Camera
        self.write_comment("Camera")
        self.write(f"const camera = new THREE.PerspectiveCamera(50, {width} / {height}, 0.1, 1000);")
        self.write("camera.position.set(0, 5, 50);")
        self.write("camera.lookAt(0, 0, 0);")
        self.write_blank()

        # Renderer
        self.write_comment("Renderer")
        self.write("const renderer = new THREE.WebGLRenderer({ antialias: true });")
        self.write("renderer.setSize(window.innerWidth, window.innerHeight);")
        self.write("renderer.setPixelRatio(window.devicePixelRatio);")
        self.write("document.body.appendChild(renderer.domElement);")
        self.write_blank()

        # OrbitControls
        self.write_comment("OrbitControls")
        self.write("const controls = new THREE.OrbitControls(camera, renderer.domElement);")
        self.write("controls.enableDamping = true;")
        self.write("controls.dampingFactor = 0.05;")
        self.write_blank()

        # WASD camera movement + Arrow keys for player objects
        self.write_comment("Keyboard controls")
        self.write("const moveState = { forward: false, backward: false, left: false, right: false, up: false, down: false };")
        self.write("const arrowState = { left: false, right: false, up: false, down: false, rise: false, fall: false };")
        self.write("document.addEventListener('keydown', (e) => {")
        self.indent()
        self.write("if (consoleVisible) return;")

        # Game keydown events
        if self.keydown_events:
            self.write_comment("Game key events")
            for key, handler_lines in self.keydown_events.items():
                js_key = self._js_key(key)
                self.write(f"if ({js_key}) {{")
                self.indent()
                for line in handler_lines:
                    self.write(line)
                self.dedent()
                self.write("}")

        self.write_comment("WASD + QE for camera")
        self.write("if (e.key === 'w' || e.key === 'W') moveState.forward = true;")
        self.write("if (e.key === 's' || e.key === 'S') moveState.backward = true;")
        self.write("if (e.key === 'a' || e.key === 'A') moveState.left = true;")
        self.write("if (e.key === 'd' || e.key === 'D') moveState.right = true;")
        self.write("if (e.key === 'q' || e.key === 'Q') moveState.down = true;")
        self.write("if (e.key === 'e' || e.key === 'E') moveState.up = true;")
        self.write_comment("Arrow keys + ./  for player objects")
        self.write("if (e.key === 'ArrowLeft') arrowState.left = true;")
        self.write("if (e.key === 'ArrowRight') arrowState.right = true;")
        self.write("if (e.key === 'ArrowUp') arrowState.up = true;")
        self.write("if (e.key === 'ArrowDown') arrowState.down = true;")
        self.write("if (e.key === '.') arrowState.rise = true;")
        self.write("if (e.key === '/') arrowState.fall = true;")
        self.dedent()
        self.write("});")
        self.write("document.addEventListener('keyup', (e) => {")
        self.indent()
        self.write("if (e.key === 'w' || e.key === 'W') moveState.forward = false;")
        self.write("if (e.key === 's' || e.key === 'S') moveState.backward = false;")
        self.write("if (e.key === 'a' || e.key === 'A') moveState.left = false;")
        self.write("if (e.key === 'd' || e.key === 'D') moveState.right = false;")
        self.write("if (e.key === 'q' || e.key === 'Q') moveState.down = false;")
        self.write("if (e.key === 'e' || e.key === 'E') moveState.up = false;")
        self.write("if (e.key === 'ArrowLeft') arrowState.left = false;")
        self.write("if (e.key === 'ArrowRight') arrowState.right = false;")
        self.write("if (e.key === 'ArrowUp') arrowState.up = false;")
        self.write("if (e.key === 'ArrowDown') arrowState.down = false;")
        self.write("if (e.key === '.') arrowState.rise = false;")
        self.write("if (e.key === '/') arrowState.fall = false;")
        self.dedent()
        self.write("});")
        self.write_blank()

        # Lighting
        self.write_comment("Lighting")
        self.write("const ambientLight = new THREE.AmbientLight(0x404040, 0.5);")
        self.write("scene.add(ambientLight);")
        self.write("const directionalLight = new THREE.DirectionalLight(0xffffff, 1);")
        self.write("directionalLight.position.set(5, 10, 7);")
        self.write("scene.add(directionalLight);")
        self.write_blank()

        # Ground grid
        self.write_comment("Ground grid")
        self.write("const gridHelper = new THREE.GridHelper(100, 50, 0x444466, 0x333355);")
        self.write("gridHelper.position.y = -1;")
        self.write("scene.add(gridHelper);")
        self.write_blank()

        # Console state
        self.write("let consoleVisible = false;")

        # Scene/level state
        if self.uses_scenes:
            initial_scene = self.ir.metadata.initial_scene
            initial_level = self.ir.metadata.initial_level
            if initial_scene:
                self.write(f"let currentScene = '{initial_scene}';")
            else:
                self.write("let currentScene = null;")
            self.write(f"let currentLevel = {initial_level};")

        self.write_blank()

        # Texture loader if needed
        if self.sprite_assets:
            self.write_comment("Texture loader")
            self.write("const textureLoader = new THREE.TextureLoader();")
            self.write_blank()

        # Sound loading
        if self.sound_assets:
            self.write_comment("Audio")
            self.write("const audioListener = new THREE.AudioListener();")
            self.write("camera.add(audioListener);")
            self.write("const audioLoader = new THREE.AudioLoader();")
            self.write("const sounds = {};")
            for sound in self.sound_assets:
                if sound:
                    safe_name = sound.replace('.', '_').replace('-', '_').replace('/', '_')
                    self.write(f"audioLoader.load('assets/{sound}', (buffer) => {{")
                    self.indent()
                    self.write(f"sounds['{safe_name}'] = new THREE.Audio(audioListener);")
                    self.write(f"sounds['{safe_name}'].setBuffer(buffer);")
                    self.dedent()
                    self.write("});")
            self.write_blank()

    # =========================================================================
    # Object Creation
    # =========================================================================

    def _emit_objects(self):
        """Emit all game objects."""
        self.write_comment("Game Objects")

        for obj in self.ir.objects:
            self._emit_object(obj)

        self.write_blank()

    def _emit_object(self, obj: IR_Object):
        """Emit a single Three.js object."""
        name = obj.name

        # Get position (normalized 0-1 in IR, convert to 3D world coords)
        x = self._get_prop_value(obj, 'x', 0.5)
        y = self._get_prop_value(obj, 'y', 0.5)
        z = self._get_prop_value(obj, 'z', 0)

        # Convert normalized coords to 3D world
        # x: 0-1 maps to roughly -8 to 8
        # y: 0-1 maps to roughly 8 to 0 (inverted, above ground)
        world_x = (x - 0.5) * 16
        world_y = (0.5 - y) * 8 + 2  # Center at y=2 (above ground)
        world_z = z * 16 if z != 0 else 0

        # Get shape type
        shape = 'box'
        if 'shape' in obj.properties:
            shape_val = obj.properties['shape']
            shape = shape_val.value if hasattr(shape_val, 'value') else str(shape_val)

        # Get size
        width = self._get_prop_value(obj, 'width', 0.05) * 16
        height = self._get_prop_value(obj, 'height', 0.05) * 16
        depth = self._get_prop_value(obj, 'depth', 0.05) * 16
        radius = self._get_prop_value(obj, 'radius', 0.5)

        # Get color
        color = self._get_color(obj)

        # Check if text or HUD object
        is_text = name in self.text_objects
        is_hud = any(hud_name == name for hud_name, _ in self.hud_objects)

        self.write_comment(f"Object: {name}")

        object_kind = 'mesh'
        if is_hud:
            # HUD objects are text sprites that display lives/score
            target = next((t for h, t in self.hud_objects if h == name), 'player')
            self._emit_hud_sprite(name, target, world_x, world_y, world_z)
            object_kind = 'hud'
        elif is_text:
            text = self._get_prop_string(obj, 'text', name)
            self._emit_text_sprite(name, text, color, world_x, world_y, world_z)
            object_kind = 'text'
        elif 'sprite' in obj.properties:
            sprite = obj.properties['sprite'].value
            self._emit_textured_plane(name, sprite, world_x, world_y, world_z, width, height)
            object_kind = 'sprite'
        elif shape == 'sphere':
            self.write(f"const {name}Geometry = new THREE.SphereGeometry({radius}, 32, 32);")
            self.write(f"const {name}Material = new THREE.MeshStandardMaterial({{ color: 0x{color:06x} }});")
            self.write(f"const {name} = new THREE.Mesh({name}Geometry, {name}Material);")
            self.write(f"{name}.position.set({world_x:.2f}, {world_y:.2f}, {world_z:.2f});")
            self.write(f"{name}.name = '{name}';")
            self.write(f"scene.add({name});")
        elif shape == 'plane':
            self.write(f"const {name}Geometry = new THREE.PlaneGeometry({width:.2f}, {height:.2f});")
            self.write(f"const {name}Material = new THREE.MeshStandardMaterial({{ color: 0x{color:06x}, side: THREE.DoubleSide }});")
            self.write(f"const {name} = new THREE.Mesh({name}Geometry, {name}Material);")
            self.write(f"{name}.position.set({world_x:.2f}, {world_y:.2f}, {world_z:.2f});")
            self.write(f"{name}.name = '{name}';")
            self.write(f"scene.add({name});")
        else:
            # Default: box
            self.write(f"const {name}Geometry = new THREE.BoxGeometry({width:.2f}, {height:.2f}, {depth:.2f});")
            self.write(f"const {name}Material = new THREE.MeshStandardMaterial({{ color: 0x{color:06x} }});")
            self.write(f"const {name} = new THREE.Mesh({name}Geometry, {name}Material);")
            self.write(f"{name}.position.set({world_x:.2f}, {world_y:.2f}, {world_z:.2f});")
            self.write(f"{name}.name = '{name}';")
            self.write(f"scene.add({name});")

        self.write(f"{name}.userData._rosh_kind = '{object_kind}';")

        # Apply initial visible property if set to false
        if 'visible' in obj.properties:
            vis_val = self.get_value(obj.properties['visible'])
            if vis_val is False or vis_val == 'false':
                self.write(f"{name}.visible = false;")

        # Custom properties in userData
        known = {'x', 'y', 'z', 'width', 'height', 'depth', 'color', 'shape', 'radius', 'text', 'sprite', 'visible', 'saveable', 'type'}
        for prop_name, prop_value in obj.properties.items():
            if prop_name not in known:
                val = self.get_value(prop_value)
                if isinstance(val, str):
                    self.write(f"{name}.userData.{prop_name} = '{val}';")
                elif isinstance(val, bool):
                    self.write(f"{name}.userData.{prop_name} = {'true' if val else 'false'};")
                else:
                    self.write(f"{name}.userData.{prop_name} = {val};")

        # Scene/level membership
        if obj.scene is not None:
            self.write(f"{name}.userData._scene = '{obj.scene}';")
        if obj.level is not None:
            self.write(f"{name}.userData._level = {obj.level};")

        # UUID for REPL
        self.write(f"{name}.userData._rosh_uuid = crypto.randomUUID();")
        self.write_blank()
        self.color_index += 1

    def _emit_init_actions(self):
        """Emit initialization actions (top-level set statements like set meta.phase to 1)."""
        if not self.ir.init_actions:
            return

        self.write_comment("Initialization")
        for action in self.ir.init_actions:
            code = self.emit_action(action)
            if code:
                self.write(code)
        self.write_blank()

    def _emit_scene_visibility_function(self):
        """Emit updateSceneVisibility helper function."""
        self.write_comment("Scene/Level Visibility - Roshonic \"Dimensions, Not Modes\"")
        self.write("function updateSceneVisibility() {")
        self.indent()

        for obj in self.ir.objects:
            if obj.scene is None and obj.level is None:
                continue  # Always visible, skip

            conditions = []
            if obj.scene is not None:
                conditions.append(f"currentScene === '{obj.scene}'")
            if obj.level is not None:
                conditions.append(f"currentLevel === {obj.level}")

            condition = " && ".join(conditions)
            self.write(f"if ({obj.name}) {obj.name}.visible = ({condition});")

        self.dedent()
        self.write("}")
        self.write("else if (parts[0] === 'capabilities') {")
        self.indent()
        self.write("const allowedTags = Array.from(CAPABILITY_POLICY.allowTags);")
        self.write("const deniedTags = Array.from(CAPABILITY_POLICY.denyTags);")
        self.write("const allowedCaps = Array.from(CAPABILITY_POLICY.allowCapabilities || []);")
        self.write("log('Enabled capability tags: ' + (allowedTags.length ? allowedTags.join(', ') : 'safe (default)'), 'cyan');")
        self.write("if (deniedTags.length) log('Denied tags: ' + deniedTags.join(', '), 'cyan');")
        self.write("if (allowedCaps.length) log('Explicit allowlist: ' + allowedCaps.join(', '), 'cyan');")
        self.write("log('Use help <object> or help <capability> for details.', 'dim');")
        self.write("log('Configure via _meta/threejs.toml [engine_capabilities] allow = [\"safe\",\"experimental\"], deny = [\"destructive\"], etc.', 'dim');")
        self.dedent()
        self.write("}")
        self.write_blank()

        # Call initially
        self.write_comment("Set initial scene/level visibility")
        self.write("updateSceneVisibility();")
        self.write_blank()

    def _emit_save_load_functions(self):
        """Emit save/load game functions using localStorage."""
        saveable_objects = [obj for obj in self.ir.objects if obj.saveable]

        # saveGame function
        self.write_comment("Save/Load - Roshonic \"Save Everything by Default\"")
        self.write("function saveGame(slot) {")
        self.indent()
        self.write("const saveData = {")
        self.indent()
        self.write("version: '1.0',")
        self.write("timestamp: new Date().toISOString(),")
        if self.uses_scenes:
            self.write("scene: currentScene,")
            self.write("level: currentLevel,")
        self.write("objects: {}")
        self.dedent()
        self.write("};")
        self.write_blank()

        for obj in saveable_objects:
            self.write(f"if ({obj.name}) {{")
            self.indent()
            self.write(f"saveData.objects['{obj.name}'] = {{")
            self.indent()
            self.write(f"x: {obj.name}.position.x,")
            self.write(f"y: {obj.name}.position.y,")
            self.write(f"z: {obj.name}.position.z,")
            for prop_name in obj.properties:
                if prop_name not in ('x', 'y', 'z', 'width', 'height', 'depth', 'sprite', 'color', 'text', 'saveable', 'type', 'radius'):
                    self.write(f"{prop_name}: {obj.name}.userData.{prop_name},")
            self.dedent()
            self.write("};")
            self.dedent()
            self.write("}")

        self.write_blank()
        self.write("localStorage.setItem('rosh_save_' + slot, JSON.stringify(saveData));")
        self.write("console.log('Game saved to slot:', slot);")
        self.dedent()
        self.write("}")
        self.write_blank()

        # loadGame function
        self.write("function loadGame(slot) {")
        self.indent()
        self.write("const json = localStorage.getItem('rosh_save_' + slot);")
        self.write("if (!json) { console.log('No save found in slot:', slot); return; }")
        self.write("const saveData = JSON.parse(json);")
        self.write_blank()

        if self.uses_scenes:
            self.write("if (saveData.scene !== undefined) currentScene = saveData.scene;")
            self.write("if (saveData.level !== undefined) currentLevel = saveData.level;")
            self.write("updateSceneVisibility();")
            self.write_blank()

        self.write("const objects = saveData.objects || {};")
        for obj in saveable_objects:
            self.write(f"if (objects['{obj.name}'] && {obj.name}) {{")
            self.indent()
            self.write(f"const data = objects['{obj.name}'];")
            self.write(f"if (data.x !== undefined) {obj.name}.position.x = data.x;")
            self.write(f"if (data.y !== undefined) {obj.name}.position.y = data.y;")
            self.write(f"if (data.z !== undefined) {obj.name}.position.z = data.z;")
            for prop_name in obj.properties:
                if prop_name not in ('x', 'y', 'z', 'width', 'height', 'depth', 'sprite', 'color', 'text', 'saveable', 'type', 'radius'):
                    self.write(f"if (data.{prop_name} !== undefined) {obj.name}.userData.{prop_name} = data.{prop_name};")
            self.dedent()
            self.write("}")

        self.write_blank()
        self.write("console.log('Game loaded from slot:', slot);")
        self.dedent()
        self.write("}")
        self.write_blank()

    def _emit_text_sprite(self, name: str, text: str, color: int, x: float, y: float, z: float):
        """Emit a text sprite using canvas texture."""
        css_color = f"#{color:06x}"

        self.write(f"const {name}Canvas = document.createElement('canvas');")
        self.write(f"const {name}Ctx = {name}Canvas.getContext('2d');")
        self.write(f"{name}Canvas.width = 1024;")
        self.write(f"{name}Canvas.height = 256;")
        self.write(f"{name}Ctx.fillStyle = '{css_color}';")
        self.write(f"{name}Ctx.font = 'bold 48px Arial';")
        self.write(f"{name}Ctx.textAlign = 'center';")
        self.write(f"{name}Ctx.textBaseline = 'middle';")
        self.write(f"{name}Ctx.fillText('{text}', 512, 128);")
        self.write(f"const {name}Texture = new THREE.CanvasTexture({name}Canvas);")
        self.write(f"const {name}Material = new THREE.SpriteMaterial({{ map: {name}Texture, transparent: true }});")
        self.write(f"const {name} = new THREE.Sprite({name}Material);")
        self.write(f"{name}.position.set({x:.2f}, {y:.2f}, {z:.2f});")
        self.write(f"{name}.scale.set(20, 5, 1);")
        self.write(f"{name}.name = '{name}';")
        self.write(f"{name}._canvas = {name}Canvas;")
        self.write(f"{name}._ctx = {name}Ctx;")
        self.write(f"{name}._text = '{text}';")
        self.write(f"{name}._color = '{css_color}';")
        self.write(f"{name}._font = 'Inter';")
        self.write(f"scene.add({name});")
        self.write(f"{name}.userData.font_size = 48;")

    def _emit_textured_plane(self, name: str, image: str, x: float, y: float, z: float, w: float, h: float):
        """Emit a textured plane for 2D sprites."""
        self.write(f"const {name}Texture = textureLoader.load('assets/{image}');")
        self.write(f"const {name}Geometry = new THREE.PlaneGeometry({w:.2f}, {h:.2f});")
        self.write(f"const {name}Material = new THREE.MeshBasicMaterial({{ map: {name}Texture, transparent: true, side: THREE.DoubleSide }});")
        self.write(f"const {name} = new THREE.Mesh({name}Geometry, {name}Material);")
        self.write(f"{name}.position.set({x:.2f}, {y:.2f}, {z:.2f});")
        self.write(f"{name}.name = '{name}';")
        self.write(f"scene.add({name});")

    def _emit_hud_sprite(self, name: str, target: str, x: float, y: float, z: float):
        """Emit a HUD sprite that displays lives/score."""
        self.write(f"const {name}Canvas = document.createElement('canvas');")
        self.write(f"const {name}Ctx = {name}Canvas.getContext('2d');")
        self.write(f"{name}Canvas.width = 512;")
        self.write(f"{name}Canvas.height = 128;")
        self.write(f"{name}Ctx.fillStyle = '#ffffff';")
        self.write(f"{name}Ctx.font = 'bold 32px Arial';")
        self.write(f"{name}Ctx.textAlign = 'left';")
        self.write(f"{name}Ctx.fillText('Lives: 3  Score: 0', 20, 50);")
        self.write(f"const {name}Texture = new THREE.CanvasTexture({name}Canvas);")
        self.write(f"const {name}Material = new THREE.SpriteMaterial({{ map: {name}Texture, transparent: true }});")
        self.write(f"const {name} = new THREE.Sprite({name}Material);")
        self.write(f"{name}.position.set({x:.2f}, {y:.2f}, {z:.2f});")
        self.write(f"{name}.scale.set(15, 4, 1);")
        self.write(f"{name}.name = '{name}';")
        self.write(f"{name}._canvas = {name}Canvas;")
        self.write(f"{name}._ctx = {name}Ctx;")
        self.write(f"{name}._color = '#ffffff';")
        self.write(f"{name}._font = 'Inter';")
        self.write(f"scene.add({name});")
        self.write(f"{name}.userData.font_size = 32;")

    # =========================================================================
    # Functions and Events
    # =========================================================================

    def _emit_functions(self):
        """Emit user-defined functions."""
        if not self.ir.functions:
            return

        self.write_comment("User Functions")
        for func in self.ir.functions:
            params = ", ".join(func.params)
            self.write(f"function {func.name}({params}) {{")
            self.indent()
            for action in func.body:
                if action:
                    code = self.emit_action(action)
                    if code:
                        self.write(code)
            self.dedent()
            self.write("}")
            self.write_blank()

    def _emit_event_handlers(self):
        """Emit event handler functions."""
        if not self.update_handlers and not self.key_handlers:
            return

        self.write_comment("Event Handlers")

        # Update handlers
        for i, event in enumerate(self.update_handlers):
            func_name = "handle_update" if i == 0 else f"handle_update_{i}"
            self.write(f"function {func_name}() {{")
            self.indent()
            for action in event.handler:
                if action:
                    code = self.emit_action(action)
                    if code:
                        self.write(code)
            self.dedent()
            self.write("}")
            self.write_blank()

    def _emit_capability_runtime(self):
        """Emit manifest + runtime helpers for engine capabilities."""
        manifest_js = json.dumps(self.capability_manifest)
        policy_js = json.dumps(self.capability_policy)

        self.write_comment("Engine capability manifest + runtime bridge")
        self.write(f"let CAPABILITY_MANIFEST = {manifest_js};")
        self.write("const CAPABILITY_INDEX = {};")
        self.write("const CAPABILITY_RUNTIME = {};")
        self.write(f"const CAPABILITY_POLICY = {policy_js};")
        self.write("CAPABILITY_POLICY.allowTags = new Set(CAPABILITY_POLICY.allow_tags || []);")
        self.write("CAPABILITY_POLICY.denyTags = new Set(CAPABILITY_POLICY.deny_tags || []);")
        self.write("CAPABILITY_POLICY.allowCapabilities = new Set(CAPABILITY_POLICY.allow_capabilities || []);")
        self.write("CAPABILITY_POLICY.denyCapabilities = new Set(CAPABILITY_POLICY.deny_capabilities || []);")
        self.write("const capabilityState = { spin: new Map(), bounce: new Map(), pulse: new Map(), orbit: new Map() };")
        self.write_blank()

        # Index rebuild + optional fetch
        self.write("function rebuildCapabilityIndex() {")
        self.indent()
        self.write("for (const key of Object.keys(CAPABILITY_INDEX)) delete CAPABILITY_INDEX[key];")
        self.write("for (const cap of CAPABILITY_MANIFEST.capabilities || []) { CAPABILITY_INDEX[cap.name] = cap; }")
        self.dedent()
        self.write("}")
        self.write("rebuildCapabilityIndex();")
        self.write("if (typeof window !== 'undefined' && window.fetch) {")
        self.indent()
        self.write("fetch('capabilities.json').then(r => r.json()).then(data => {")
        self.indent()
        self.write("if (data && data.capabilities) { CAPABILITY_MANIFEST = data; rebuildCapabilityIndex(); }")
        self.dedent()
        self.write("}).catch(() => { console.warn('Capability manifest not found (capabilities.json)'); });")
        self.dedent()
        self.write("}")
        self.write_blank()

        # Helper functions
        self.write("function getObjectKind(obj) {")
        self.indent()
        self.write("if (!obj || !obj.userData) return 'mesh';")
        self.write("return obj.userData._rosh_kind || 'mesh';")
        self.dedent()
        self.write("}")

        self.write("function capabilityAllowed(cap) {")
        self.indent()
        self.write("if (CAPABILITY_POLICY.denyCapabilities.has(cap.name)) return false;")
        self.write("if (CAPABILITY_POLICY.allowCapabilities.size && !CAPABILITY_POLICY.allowCapabilities.has(cap.name)) return false;")
        self.write("for (const tag of cap.tags || []) { if (CAPABILITY_POLICY.denyTags.has(tag)) return false; }")
        self.write("if (!cap.tags || !cap.tags.length) return true;")
        self.write("return cap.tags.some(tag => CAPABILITY_POLICY.allowTags.has(tag));")
        self.dedent()
        self.write("}")

        self.write("function capabilityAppliesTo(cap, obj) {")
        self.indent()
        self.write("if (!cap.applies_to || !cap.applies_to.length) return true;")
        self.write("const kind = getObjectKind(obj);")
        self.write("return cap.applies_to.includes(kind);")
        self.dedent()
        self.write("}")

        self.write("function describeCapability(cap) {")
        self.indent()
        self.write("if (!cap) return '';")
        self.write("const args = cap.args && cap.args.length ? ' (' + cap.args.join(', ') + ')' : '';")
        self.write("const doc = cap.doc ? ' - ' + cap.doc : '';")
        self.write("return cap.name + args + doc;")
        self.dedent()
        self.write("}")

        self.write("function logCapabilityHelp(cap) {")
        self.indent()
        self.write("if (!cap) { log('Unknown capability.', 'err'); return; }")
        self.write("const status = capabilityAllowed(cap) ? 'enabled' : 'disabled by policy';")
        self.write("log(describeCapability(cap), capabilityAllowed(cap) ? 'cyan' : 'err');")
        self.write("if (cap.tags && cap.tags.length) log('  Tags: ' + cap.tags.join(', '), 'dim');")
        self.write("log('  Status: ' + status, capabilityAllowed(cap) ? 'dim' : 'err');")
        self.write("if (cap.args && cap.args.length) log('  Usage: ' + cap.name + ' ' + cap.args.join(' '), 'dim');")
        self.write("if (!capabilityAllowed(cap) && cap.tags && cap.tags.length) {")
        self.indent()
        self.write("const tagHint = cap.tags.map(t => '\"' + t + '\"').join(', ');")
        self.write("log('  Enable via _meta/threejs.toml [engine_capabilities] allow = [' + tagHint + ']', 'dim');")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")

        self.write("function availableCapabilitiesFor(obj) {")
        self.indent()
        self.write("const kind = getObjectKind(obj);")
        self.write("return (CAPABILITY_MANIFEST.capabilities || []).filter(cap => capabilityAllowed(cap) && (!cap.applies_to || cap.applies_to.includes(kind)));")
        self.dedent()
        self.write("}")

        self.write("function coerceSingleValue(tokens) {")
        self.indent()
        self.write("if (!tokens || !tokens.length) return null;")
        self.write("if (tokens.length === 1) {")
        self.indent()
        self.write("const raw = tokens[0];")
        self.write("if (raw === 'true') return true;")
        self.write("if (raw === 'false') return false;")
        self.write("const n = parseFloat(raw);")
        self.write("if (!Number.isNaN(n)) return n;")
        self.write("return raw;")
        self.dedent()
        self.write("}")
        self.write("return tokens.join(' ');")
        self.dedent()
        self.write("}")

        self.write("function coerceNumbers(tokens) {")
        self.indent()
        self.write("if (!tokens || !tokens.length) return [];")
        self.write("return tokens.map(t => parseFloat(t)).filter(v => !Number.isNaN(v));")
        self.dedent()
        self.write("}")

        self.write("function handleCoreSet(obj, prop, tokens) {")
        self.indent()
        self.write("const value = coerceSingleValue(tokens);")
        self.write("if (value === null || value === undefined) return { ok: false };")
        self.write("const numVal = typeof value === 'number' ? value : parseFloat(value);")
        self.write("if (prop === 'x' && !Number.isNaN(numVal)) { obj.position.x = numVal; return { ok: true }; }")
        self.write("if (prop === 'y' && !Number.isNaN(numVal)) { obj.position.y = numVal; return { ok: true }; }")
        self.write("if (prop === 'z' && !Number.isNaN(numVal)) { obj.position.z = numVal; return { ok: true }; }")
        self.write("if (prop === 'visible') { obj.visible = value === true || value === 'true'; return { ok: true }; }")
        self.write("return { ok: false };")
        self.dedent()
        self.write("}")

        self.write("function redrawTextSprite(obj, textOverride) {")
        self.indent()
        self.write("if (!obj || !obj._ctx) return;")
        self.write("const fontSize = obj.userData.font_size || 48;")
        self.write("const fontFamily = obj._font || 'Inter';")
        self.write("obj._ctx.clearRect(0, 0, obj._canvas.width, obj._canvas.height);")
        self.write("obj._ctx.font = 'bold ' + fontSize + 'px ' + fontFamily;")
        self.write("obj._ctx.textAlign = 'center';")
        self.write("obj._ctx.textBaseline = 'middle';")
        self.write("obj._ctx.fillStyle = obj._color || '#ffffff';")
        self.write("obj._ctx.fillText(textOverride || obj._text || '', obj._canvas.width / 2, obj._canvas.height / 2);")
        self.write("if (obj.material && obj.material.map) obj.material.map.needsUpdate = true;")
        self.dedent()
        self.write("}")

        self.write("function applyCapabilityBridge(obj, prop, tokens) {")
        self.indent()
        self.write("const cap = CAPABILITY_INDEX[prop];")
        self.write("if (!cap) {")
        self.indent()
        self.write("const options = availableCapabilitiesFor(obj).map(entry => entry.name).join(', ') || null;")
        self.write("return { ok: false, reason: 'unknown', message: \"Unknown property '\" + prop + \"'.\", suggestion: options };")
        self.dedent()
        self.write("}")
        self.write("if (!capabilityAllowed(cap)) { return { ok: false, reason: 'denied', message: \"Capability '\" + prop + \"' is disabled.\" }; }")
        self.write("if (!capabilityAppliesTo(cap, obj)) { return { ok: false, reason: 'not_applicable', message: \"'\" + prop + \"' not supported for this object.\" }; }")
        self.write("const handler = CAPABILITY_RUNTIME[prop];")
        self.write("if (!handler) { return { ok: false, reason: 'missing_handler', message: \"No handler for '\" + prop + \"'.\" }; }")
        self.write("try {")
        self.indent()
        self.write("handler({ object: obj, tokens, raw: tokens.join(' '), numbers: coerceNumbers(tokens) });")
        self.write("return { ok: true };")
        self.dedent()
        self.write("} catch (err) {")
        self.indent()
        self.write("const msg = err && err.message ? err.message : String(err);")
        self.write("return { ok: false, reason: 'error', message: msg };")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")

        # Handler implementations
        self.write("CAPABILITY_RUNTIME['color'] = function(ctx) {")
        self.indent()
        self.write("const val = ctx.raw || '#ffffff';")
        self.write("if (ctx.object._ctx) {")
        self.indent()
        self.write("ctx.object._color = val;")
        self.write("redrawTextSprite(ctx.object);")
        self.dedent()
        self.write("} else if (ctx.object.material && ctx.object.material.color) {")
        self.indent()
        self.write("ctx.object.material.color.set(val);")
        self.dedent()
        self.write("} else { throw new Error('Color not supported for this object'); }")
        self.dedent()
        self.write("};")

        self.write("CAPABILITY_RUNTIME['font_size'] = function(ctx) {")
        self.indent()
        self.write("if (!ctx.object._ctx) throw new Error('Only text sprites support font_size');")
        self.write("const n = parseFloat(ctx.tokens[0]);")
        self.write("if (Number.isNaN(n)) throw new Error('Provide a numeric font size');")
        self.write("ctx.object.userData.font_size = n;")
        self.write("redrawTextSprite(ctx.object);")
        self.dedent()
        self.write("};")

        self.write("CAPABILITY_RUNTIME['font'] = function(ctx) {")
        self.indent()
        self.write("if (!ctx.object._ctx) throw new Error('Only text sprites support font');")
        self.write("if (!ctx.raw || !ctx.raw.trim()) throw new Error('Provide a font family name');")
        self.write("ctx.object._font = ctx.raw.trim();")
        self.write("redrawTextSprite(ctx.object);")
        self.dedent()
        self.write("};")

        self.write("CAPABILITY_RUNTIME['text'] = function(ctx) {")
        self.indent()
        self.write("if (!ctx.object._ctx) throw new Error('Only text sprites support text updates');")
        self.write("ctx.object._text = ctx.raw;")
        self.write("redrawTextSprite(ctx.object, ctx.raw);")
        self.dedent()
        self.write("};")

        self.write("CAPABILITY_RUNTIME['scale'] = function(ctx) {")
        self.indent()
        self.write("if (!ctx.object.scale) throw new Error('Scale not supported');")
        self.write("const nums = ctx.numbers;")
        self.write("if (!nums.length) throw new Error('Provide numeric scale values');")
        self.write("if (nums.length === 1) { ctx.object.scale.set(nums[0], nums[0], nums[0]); }")
        self.write("else { ctx.object.scale.set(nums[0], nums[1] ?? nums[0], nums[2] ?? nums[0]); }")
        self.dedent()
        self.write("};")

        self.write("CAPABILITY_RUNTIME['spin'] = function(ctx) {")
        self.indent()
        self.write("if (!ctx.object) throw new Error('No object to spin');")
        self.write("const raw = ctx.raw.trim();")
        self.write("if (!raw || raw === 'off') { capabilityState.spin.delete(ctx.object); delete ctx.object.userData._spin; return; }")
        self.write("const nums = ctx.numbers;")
        self.write("if (!nums.length) throw new Error('Provide rotation speed(s)');")
        self.write("const speeds = [nums[0] || 0, nums[1] ?? nums[0] ?? 0, nums[2] ?? 0].map(v => v * Math.PI / 180);")
        self.write("if (speeds.every(v => v === 0)) { capabilityState.spin.delete(ctx.object); delete ctx.object.userData._spin; return; }")
        self.write("capabilityState.spin.set(ctx.object, { x: speeds[0], y: speeds[1], z: speeds[2] });")
        self.write("ctx.object.userData._spin = speeds;")
        self.dedent()
        self.write("};")

        self.write("CAPABILITY_RUNTIME['bounce'] = function(ctx) {")
        self.indent()
        self.write("if (!ctx.object) throw new Error('No object to bounce');")
        self.write("const raw = ctx.raw.trim();")
        self.write("if (!raw || raw === 'off') { capabilityState.bounce.delete(ctx.object); delete ctx.object.userData._bounce; return; }")
        self.write("const nums = ctx.numbers;")
        self.write("if (!nums.length) throw new Error('Provide amplitude and optional frequency');")
        self.write("const amplitude = nums[0];")
        self.write("const freq = nums[1] || 1;")
        self.write("if (amplitude === 0) { capabilityState.bounce.delete(ctx.object); delete ctx.object.userData._bounce; return; }")
        self.write("capabilityState.bounce.set(ctx.object, { amplitude, frequency: freq * Math.PI * 2, base: ctx.object.position.y, elapsed: 0 });")
        self.write("ctx.object.userData._bounce = { amplitude, freq };")
        self.dedent()
        self.write("};")

        self.write("CAPABILITY_RUNTIME['pulse'] = function(ctx) {")
        self.indent()
        self.write("if (!ctx.object || !ctx.object.scale) throw new Error('Pulse requires scale support');")
        self.write("const raw = ctx.raw.trim();")
        self.write("if (!raw || raw === 'off') {")
        self.indent()
        self.write("const prev = capabilityState.pulse.get(ctx.object);")
        self.write("if (prev && prev.base) ctx.object.scale.set(prev.base.x, prev.base.y, prev.base.z);")
        self.write("capabilityState.pulse.delete(ctx.object);")
        self.write("delete ctx.object.userData._pulse;")
        self.write("return;")
        self.dedent()
        self.write("}")
        self.write("const nums = ctx.numbers;")
        self.write("if (!nums.length) throw new Error('Provide amplitude (scale delta) and optional frequency');")
        self.write("const amplitude = nums[0];")
        self.write("const freq = nums[1] || 1;")
        self.write("if (amplitude === 0) {")
        self.indent()
        self.write("const prev = capabilityState.pulse.get(ctx.object);")
        self.write("if (prev && prev.base) ctx.object.scale.set(prev.base.x, prev.base.y, prev.base.z);")
        self.write("capabilityState.pulse.delete(ctx.object);")
        self.write("delete ctx.object.userData._pulse;")
        self.write("return;")
        self.dedent()
        self.write("}")
        self.write("capabilityState.pulse.set(ctx.object, { amplitude, frequency: freq * Math.PI * 2, elapsed: 0, base: { x: ctx.object.scale.x, y: ctx.object.scale.y, z: ctx.object.scale.z } });")
        self.write("ctx.object.userData._pulse = { amplitude, freq };")
        self.dedent()
        self.write("};")

        self.write("CAPABILITY_RUNTIME['orbit'] = function(ctx) {")
        self.indent()
        self.write("if (!ctx.object) throw new Error('No object to orbit');")
        self.write("const raw = ctx.raw.trim();")
        self.write("if (!raw || raw === 'off') {")
        self.indent()
        self.write("capabilityState.orbit.delete(ctx.object);")
        self.write("delete ctx.object.userData._orbit;")
        self.write("return;")
        self.dedent()
        self.write("}")
        self.write("const nums = ctx.numbers;")
        self.write("if (!nums.length) throw new Error('Provide radius and optional speed/height');")
        self.write("const radius = nums[0];")
        self.write("if (radius <= 0) throw new Error('Radius must be positive');")
        self.write("const speedDeg = nums[1] || 30;")
        self.write("const height = nums[2];")
        self.write("const center = { x: ctx.object.position.x, z: ctx.object.position.z };")
        self.write("capabilityState.orbit.set(ctx.object, {")
        self.indent()
        self.write("center,")
        self.write("radius,")
        self.write("speed: speedDeg * Math.PI / 180,")
        self.write("angle: 0,")
        self.write("height: Number.isFinite(height) ? height : ctx.object.position.y")
        self.dedent()
        self.write("});")
        self.write("ctx.object.userData._orbit = { radius, speed: speedDeg, height: Number.isFinite(height) ? height : ctx.object.position.y, centerX: center.x, centerZ: center.z };")
        self.dedent()
        self.write("};")
        self.write_blank()

        self.write("function restoreCapabilityState(obj) {")
        self.indent()
        self.write("if (!obj || !obj.userData) return;")
        self.write("const spin = obj.userData._spin;")
        self.write("if (Array.isArray(spin) && spin.length >= 3) {")
        self.indent()
        self.write("capabilityState.spin.set(obj, { x: spin[0], y: spin[1], z: spin[2] });")
        self.write("obj.userData._spin = spin;")
        self.dedent()
        self.write("} else { capabilityState.spin.delete(obj); delete obj.userData._spin; }")
        self.write("const bounce = obj.userData._bounce;")
        self.write("if (bounce && typeof bounce.amplitude === 'number') {")
        self.indent()
        self.write("const freq = (bounce.freq || bounce.frequency || 1) * Math.PI * 2;")
        self.write("capabilityState.bounce.set(obj, { amplitude: bounce.amplitude, frequency: freq, base: obj.position.y, elapsed: 0 });")
        self.write("obj.userData._bounce = { amplitude: bounce.amplitude, freq: bounce.freq || bounce.frequency || 1 };")
        self.dedent()
        self.write("} else { capabilityState.bounce.delete(obj); delete obj.userData._bounce; }")
        self.write("const pulse = obj.userData._pulse;")
        self.write("if (pulse && typeof pulse.amplitude === 'number' && obj.scale) {")
        self.indent()
        self.write("capabilityState.pulse.set(obj, { amplitude: pulse.amplitude, frequency: (pulse.freq || 1) * Math.PI * 2, elapsed: 0, base: { x: obj.scale.x, y: obj.scale.y, z: obj.scale.z } });")
        self.write("obj.userData._pulse = { amplitude: pulse.amplitude, freq: pulse.freq || 1 };")
        self.dedent()
        self.write("} else { capabilityState.pulse.delete(obj); delete obj.userData._pulse; }")
        self.write("const orbit = obj.userData._orbit;")
        self.write("if (orbit && typeof orbit.radius === 'number' && orbit.radius > 0) {")
        self.indent()
        self.write("const center = { x: orbit.centerX ?? obj.position.x, z: orbit.centerZ ?? obj.position.z };")
        self.write("capabilityState.orbit.set(obj, { center, radius: orbit.radius, speed: (orbit.speed || 30) * Math.PI / 180, angle: 0, height: orbit.height ?? obj.position.y });")
        self.write("obj.userData._orbit = { radius: orbit.radius, speed: orbit.speed || 30, height: orbit.height ?? obj.position.y, centerX: center.x, centerZ: center.z };")
        self.dedent()
        self.write("} else { capabilityState.orbit.delete(obj); delete obj.userData._orbit; }")
        self.dedent()
        self.write("}")
    # =========================================================================
    # Animation Loop
    # =========================================================================

    def _emit_animation_loop(self):
        """Emit the Three.js animation loop."""
        self.write("let _roshLastFrame = performance.now();")
        self.write_comment("Animation Loop")
        self.write("function animate() {")
        self.indent()
        self.write("requestAnimationFrame(animate);")
        self.write("const now = performance.now();")
        self.write("const delta = (now - _roshLastFrame) / 1000;")
        self.write("_roshLastFrame = now;")
        self.write_blank()

        # Call update handlers
        if self.update_handlers:
            for i in range(len(self.update_handlers)):
                func_name = "handle_update" if i == 0 else f"handle_update_{i}"
                self.write(f"{func_name}();")
            self.write_blank()

        # Player object movement with arrow keys
        if self.player_objects:
            self.write_comment("Player movement (arrows=XZ, Space/Shift=Y)")
            self.write("if (!consoleVisible) {")
            self.indent()
            for player in self.player_objects:
                self.write(f"const {player}Speed = {player}.userData.speed || 0.2;")
                self.write(f"if (arrowState.left) {player}.position.x -= {player}Speed;")
                self.write(f"if (arrowState.right) {player}.position.x += {player}Speed;")
                self.write(f"if (arrowState.up) {player}.position.z -= {player}Speed;")
                self.write(f"if (arrowState.down) {player}.position.z += {player}Speed;")
                self.write(f"if (arrowState.rise) {player}.position.y += {player}Speed;")
                self.write(f"if (arrowState.fall) {player}.position.y -= {player}Speed;")
            self.dedent()
            self.write("}")
            self.write_blank()

        # Collision detection
        if self.collision_events:
            self.write_comment("Collision detection")
            for obj_a, obj_b, handler_lines in self.collision_events:
                self.write(f"if ({obj_a}.position.distanceTo({obj_b}.position) < 1.5) {{")
                self.indent()
                for line in handler_lines:
                    self.write(line)
                self.dedent()
                self.write("}")
            self.write_blank()

        # Capability-driven animations
        self.write_comment("Engine capability-driven transforms")
        self.write("capabilityState.spin.forEach((state, target) => {")
        self.indent()
        self.write("if (!target) return;")
        self.write("target.rotation.x += state.x * delta;")
        self.write("target.rotation.y += state.y * delta;")
        self.write("target.rotation.z += state.z * delta;")
        self.dedent()
        self.write("});")
        self.write("capabilityState.bounce.forEach((state, target) => {")
        self.indent()
        self.write("if (!target) return;")
        self.write("state.elapsed = (state.elapsed || 0) + delta;")
        self.write("const offset = Math.sin(state.elapsed * state.frequency) * state.amplitude;")
        self.write("target.position.y = state.base + offset;")
        self.dedent()
        self.write("});")
        self.write("capabilityState.pulse.forEach((state, target) => {")
        self.indent()
        self.write("if (!target || !target.scale || !state.base) return;")
        self.write("state.elapsed = (state.elapsed || 0) + delta;")
        self.write("const factor = 1 + Math.sin(state.elapsed * state.frequency) * state.amplitude;")
        self.write("target.scale.set(state.base.x * factor, state.base.y * factor, state.base.z * factor);")
        self.dedent()
        self.write("});")
        self.write("capabilityState.orbit.forEach((state, target) => {")
        self.indent()
        self.write("if (!target) return;")
        self.write("state.angle = (state.angle || 0) + state.speed * delta;")
        self.write("target.position.x = state.center.x + Math.cos(state.angle) * state.radius;")
        self.write("target.position.z = state.center.z + Math.sin(state.angle) * state.radius;")
        self.write("target.position.y = state.height;")
        self.dedent()
        self.write("});")
        self.write_blank()

        # HUD updates
        if self.hud_objects:
            self.write_comment("HUD updates")
            for hud_name, target in self.hud_objects:
                self.write(f"if ({hud_name}._ctx && {target}) {{")
                self.indent()
                self.write(f"{hud_name}._ctx.clearRect(0, 0, {hud_name}._canvas.width, {hud_name}._canvas.height);")
                self.write(f"{hud_name}._ctx.fillStyle = {hud_name}._color || '#ffffff';")
                self.write(f"{hud_name}._ctx.font = 'bold 32px Arial';")
                self.write(f"{hud_name}._ctx.textAlign = 'left';")
                self.write(f"const lives = {target}.userData.lives !== undefined ? {target}.userData.lives : 3;")
                self.write(f"const score = {target}.userData.score !== undefined ? {target}.userData.score : 0;")
                self.write(f"{hud_name}._ctx.fillText('Lives: ' + lives + '  Score: ' + score, 20, 50);")
                self.write(f"{hud_name}.material.map.needsUpdate = true;")
                self.dedent()
                self.write("}")
            self.write_blank()

        # WASD camera movement
        self.write_comment("WASD camera movement (disabled when console open)")
        self.write("if (!consoleVisible) {")
        self.indent()
        self.write("const moveSpeed = 0.5;")
        self.write("if (moveState.forward) { camera.position.z -= moveSpeed; controls.target.z -= moveSpeed; }")
        self.write("if (moveState.backward) { camera.position.z += moveSpeed; controls.target.z += moveSpeed; }")
        self.write("if (moveState.left) { camera.position.x -= moveSpeed; controls.target.x -= moveSpeed; }")
        self.write("if (moveState.right) { camera.position.x += moveSpeed; controls.target.x += moveSpeed; }")
        self.write("if (moveState.up) { camera.position.y += moveSpeed; controls.target.y += moveSpeed; }")
        self.write("if (moveState.down) { camera.position.y -= moveSpeed; controls.target.y -= moveSpeed; }")
        self.write("if (camera.position.y < 1) { camera.position.y = 1; }")
        self.dedent()
        self.write("}")
        self.write_blank()

        self.write("controls.update();")
        self.write("renderer.render(scene, camera);")
        self.dedent()
        self.write("}")
        self.write("animate();")
        self.write_blank()

    def _emit_resize_handler(self):
        """Emit window resize handler."""
        self.write_comment("Resize Handler")
        self.write("window.addEventListener('resize', () => {")
        self.indent()
        self.write("camera.aspect = window.innerWidth / window.innerHeight;")
        self.write("camera.updateProjectionMatrix();")
        self.write("renderer.setSize(window.innerWidth, window.innerHeight);")
        self.dedent()
        self.write("});")
        self.write_blank()

    # =========================================================================
    # REPL Console
    # =========================================================================

    def _emit_repl_console(self):
        """Emit in-game REPL console."""
        self.write_comment("=" * 50)
        self.write_comment("ROSH CONSOLE - Press ` to toggle")
        self.write_comment("=" * 50)
        self.write_blank()

        # CSS
        self.write("const consoleStyle = document.createElement('style');")
        self.write("consoleStyle.textContent = `")
        self.write("#rosh-console { position: fixed; bottom: 0; left: 0; width: 100%; height: 250px;")
        self.write("  background: rgba(0,0,0,0.95); color: #0f0; font-family: monospace; font-size: 14px;")
        self.write("  border-top: 2px solid #0f0; display: none; flex-direction: column; z-index: 10000; }")
        self.write("#rosh-console.visible { display: flex; }")
        self.write("#rosh-output { flex: 1; overflow-y: auto; padding: 10px; }")
        self.write("#rosh-output .cmd { color: #ff0; } #rosh-output .ok { color: #3f3; }")
        self.write("#rosh-output .err { color: #f33; } #rosh-output .cyan { color: #0ff; }")
        self.write("#rosh-input-line { padding: 10px; border-top: 1px solid #0f0; display: flex; gap: 8px; align-items: center; }")
        self.write("#rosh-input-line input { flex: 1; background: #111; border: 1px solid #0f0;")
        self.write("  color: #0f0; padding: 8px; font-family: inherit; }")
        self.write("#rosh-voice { width: 24px; height: 24px; cursor: pointer; opacity: 0.5; transition: all 0.2s; }")
        self.write("#rosh-voice:hover { opacity: 0.8; }")
        self.write("#rosh-voice.listening { opacity: 1; animation: pulse 1s infinite; }")
        self.write("@keyframes pulse { 0%,100% { transform: scale(1); } 50% { transform: scale(1.2); } }")
        self.write("`;")
        self.write("document.head.appendChild(consoleStyle);")
        self.write_blank()

        # HTML
        self.write("const consoleDiv = document.createElement('div');")
        self.write("consoleDiv.id = 'rosh-console';")
        self.write("consoleDiv.innerHTML = `")
        self.write("  <div style='padding:8px;background:#111;border-bottom:1px solid #0f0'>")
        self.write("    <strong>ROSH CONSOLE</strong> <small style='color:#888'>Press \\` to toggle</small>")
        self.write("  </div>")
        self.write("  <div id='rosh-output'></div>")
        self.write("  <div id='rosh-input-line'>")
        self.write("    <span style='color:#0f0'>rosh></span>")
        self.write("    <input type='text' id='rosh-input' placeholder='type or Ctrl+Space for voice' autocomplete='off'>")
        self.write("    <svg id='rosh-voice' viewBox='0 0 24 24' fill='#0f0' title='Click or Ctrl+Space to speak'>")
        self.write("      <path d='M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm-1-9c0-.55.45-1 1-1s1 .45 1 1v6c0 .55-.45 1-1 1s-1-.45-1-1V5zm6 6c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z'/>")
        self.write("    </svg>")
        self.write("  </div>`;")
        self.write("document.body.appendChild(consoleDiv);")
        self.write_blank()

        # Logic
        self.write("const output = document.getElementById('rosh-output');")
        self.write("const input = document.getElementById('rosh-input');")
        self.write("let currentObject = null, currentObjectName = null;")
        self.write("const cmdHistory = []; let historyIdx = -1;")
        self.write_blank()

        self.write("function log(msg, cls='') {")
        self.indent()
        self.write("const div = document.createElement('div'); div.className = cls;")
        self.write("div.textContent = msg; output.appendChild(div); output.scrollTop = output.scrollHeight;")
        self.dedent()
        self.write("}")
        self.write_blank()

        self.write("function toggleConsole() {")
        self.indent()
        self.write("consoleVisible = !consoleVisible;")
        self.write("consoleDiv.classList.toggle('visible', consoleVisible);")
        self.write("if (consoleVisible) input.focus();")
        self.dedent()
        self.write("}")
        self.write_blank()

        # Fuzzy matching helpers
        self._emit_fuzzy_matching()

        # execCommand function
        self._emit_exec_command()

        # Key handlers
        self.write("document.addEventListener('keydown', e => {")
        self.indent()
        self.write("if (e.key === '`') { e.preventDefault(); toggleConsole(); }")
        self.dedent()
        self.write("});")
        self.write_blank()

        # Input handler with history
        self.write("input.addEventListener('keydown', e => {")
        self.indent()
        self.write("if (e.key === 'Enter' && input.value.trim()) {")
        self.indent()
        self.write("cmdHistory.unshift(input.value); historyIdx = -1;")
        self.write("execCommand(input.value); input.value = '';")
        self.dedent()
        self.write("} else if (e.key === 'ArrowUp') {")
        self.indent()
        self.write("e.preventDefault();")
        self.write("if (historyIdx < cmdHistory.length - 1) { historyIdx++; input.value = cmdHistory[historyIdx]; }")
        self.dedent()
        self.write("} else if (e.key === 'ArrowDown') {")
        self.indent()
        self.write("e.preventDefault();")
        self.write("if (historyIdx > 0) { historyIdx--; input.value = cmdHistory[historyIdx]; }")
        self.write("else if (historyIdx === 0) { historyIdx = -1; input.value = ''; }")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("});")
        self.write_blank()

        # Voice input
        self._emit_voice_input()
        self.write_blank()

        self.write(f"log('Rosh Console ready! Rosh v{__version__}. Type help for commands.', 'cyan');")

    def _emit_fuzzy_matching(self):
        """Emit fuzzy matching helpers for typo/voice tolerance."""
        self.write_comment("Fuzzy Matching - typo and voice tolerance")

        # Levenshtein distance
        self.write("function levenshtein(a, b) {")
        self.indent()
        self.write("if (!a.length) return b.length;")
        self.write("if (!b.length) return a.length;")
        self.write("const matrix = [];")
        self.write("for (let i = 0; i <= b.length; i++) matrix[i] = [i];")
        self.write("for (let j = 0; j <= a.length; j++) matrix[0][j] = j;")
        self.write("for (let i = 1; i <= b.length; i++) {")
        self.indent()
        self.write("for (let j = 1; j <= a.length; j++) {")
        self.indent()
        self.write("const cost = b[i-1] === a[j-1] ? 0 : 1;")
        self.write("matrix[i][j] = Math.min(matrix[i-1][j] + 1, matrix[i][j-1] + 1, matrix[i-1][j-1] + cost);")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")
        self.write("return matrix[b.length][a.length];")
        self.dedent()
        self.write("}")
        self.write_blank()

        # Fuzzy match function
        self.write("function fuzzyMatch(input, candidates, threshold = 0.6) {")
        self.indent()
        self.write("if (!input || !candidates.length) return null;")
        self.write("const inputLower = input.toLowerCase();")
        self.write("// Exact match first")
        self.write("const exact = candidates.find(c => c.toLowerCase() === inputLower);")
        self.write("if (exact) return { match: exact, confidence: 1.0, corrected: false };")
        self.write("// Prefix match (e.g. 'col' matches 'color')")
        self.write("const prefix = candidates.find(c => c.toLowerCase().startsWith(inputLower));")
        self.write("if (prefix && inputLower.length >= 2) return { match: prefix, confidence: 0.95, corrected: true };")
        self.write("// Levenshtein distance match")
        self.write("let best = null;")
        self.write("for (const c of candidates) {")
        self.indent()
        self.write("const dist = levenshtein(inputLower, c.toLowerCase());")
        self.write("const maxLen = Math.max(input.length, c.length);")
        self.write("const confidence = 1 - (dist / maxLen);")
        self.write("if (confidence >= threshold && (!best || confidence > best.confidence)) {")
        self.indent()
        self.write("best = { match: c, confidence, corrected: true };")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")
        self.write("return best;")
        self.dedent()
        self.write("}")
        self.write_blank()

        # Voice corrections table - common mishearings
        self.write("const VOICE_CORRECTIONS = {")
        self.indent()
        self.write("'enter': 'Inter', 'inter': 'Inter', 'inner': 'Inter',")
        self.write("'aerial': 'Arial', 'arial': 'Arial', 'area': 'Arial',")
        self.write("'read': 'red', 'reed': 'red',")
        self.write("'great': 'gray', 'grey': 'gray',")
        self.write("'blew': 'blue', 'blow': 'blue',")
        self.write("'wait': 'white', 'weight': 'white', 'wet': 'white',")
        self.write("'lack': 'black', 'block': 'black',")
        self.write("'screen': 'green', 'grain': 'green',")
        self.write("'fellow': 'yellow', 'yell': 'yellow',")
        self.write("'science': 'cyan', 'sign': 'cyan',")
        self.write("'orange': 'orange', 'arrange': 'orange',")
        self.write("'pink': 'pink', 'ping': 'pink',")
        self.write("'perple': 'purple', 'people': 'purple',")
        self.write("'collar': 'color', 'colour': 'color', 'cooler': 'color',")
        self.write("'fund': 'font', 'front': 'font', 'funt': 'font',")
        self.write("'ex': 'x', 'eggs': 'x',")
        self.write("'why': 'y', 'wie': 'y',")
        self.write("'see': 'z', 'zee': 'z', 'zed': 'z',")
        self.write("'with': 'width', 'whith': 'width',")
        self.write("'height': 'height', 'hide': 'height', 'hight': 'height',")
        self.write("'visible': 'visible', 'fizzy ball': 'visible',")
        self.write("'scale': 'scale', 'skill': 'scale',")
        self.write("'polls': 'pulse', 'pulls': 'pulse', 'pals': 'pulse',")
        self.write("'logo': 'logo', 'lego': 'logo', 'local': 'logo',")
        self.write("'rush': 'rosh', 'rash': 'rosh', 'ross': 'rosh', 'roush': 'rosh',")
        self.dedent()
        self.write("};")
        self.write_blank()

        # Apply voice corrections
        self.write("function applyVoiceCorrections(text) {")
        self.indent()
        self.write("let corrected = text;")
        self.write("let changes = [];")
        self.write("for (const [wrong, right] of Object.entries(VOICE_CORRECTIONS)) {")
        self.indent()
        self.write("const regex = new RegExp('\\\\b' + wrong + '\\\\b', 'gi');")
        self.write("if (regex.test(corrected)) {")
        self.indent()
        self.write("changes.push(wrong + ' → ' + right);")
        self.write("corrected = corrected.replace(regex, right);")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")
        self.write("return { text: corrected, changes };")
        self.dedent()
        self.write("}")
        self.write_blank()

        # Get all known object names from scene
        self.write("function getObjectNames() {")
        self.indent()
        self.write("const names = [];")
        self.write("scene.traverse(o => { if (o.name && !o.name.startsWith('_')) names.push(o.name); });")
        self.write("return names;")
        self.dedent()
        self.write("}")
        self.write_blank()

        # Get known property names
        self.write("const KNOWN_PROPERTIES = ['x', 'y', 'z', 'color', 'text', 'font', 'font_size', 'scale', 'visible', 'pulse', 'width', 'height', 'rotation', 'opacity', 'active'];")
        self.write("const KNOWN_COLORS = ['red', 'green', 'blue', 'yellow', 'cyan', 'magenta', 'white', 'black', 'orange', 'purple', 'pink', 'gray'];")
        self.write("const KNOWN_FONTS = ['Inter', 'Arial', 'Helvetica', 'Times', 'Georgia', 'Courier', 'Verdana', 'Roboto'];")
        self.write("const KNOWN_COMMANDS = ['set', 'get', 'list', 'create', 'delete', 'clone', 'look', 'examine', 'inspect', 'help', 'prompt', 'save', 'load', 'capabilities', 'camera'];")
        self.write_blank()

        # Fuzzy correct a command
        self.write("function fuzzyCorrectCommand(cmd) {")
        self.indent()
        self.write("// Apply voice corrections first")
        self.write("const voiceResult = applyVoiceCorrections(cmd);")
        self.write("let corrected = voiceResult.text;")
        self.write("let corrections = voiceResult.changes.slice();")
        self.write_blank()
        self.write("// Split and correct each part")
        self.write("const parts = corrected.split(/\\s+/);")
        self.write("if (!parts.length) return { cmd: corrected, corrections };")
        self.write_blank()
        self.write("// Correct command verb")
        self.write("const cmdMatch = fuzzyMatch(parts[0], KNOWN_COMMANDS, 0.7);")
        self.write("if (cmdMatch && cmdMatch.corrected) {")
        self.indent()
        self.write("corrections.push(parts[0] + ' → ' + cmdMatch.match);")
        self.write("parts[0] = cmdMatch.match;")
        self.dedent()
        self.write("}")
        self.write_blank()
        self.write("// For set/get commands, try to correct object and property names")
        self.write("if ((parts[0] === 'set' || parts[0] === 'get' || parts[0] === 'look' || parts[0] === 'examine' || parts[0] === 'delete' || parts[0] === 'clone') && parts.length > 1) {")
        self.indent()
        self.write("const objNames = getObjectNames();")
        self.write("const objMatch = fuzzyMatch(parts[1], objNames, 0.6);")
        self.write("if (objMatch && objMatch.corrected) {")
        self.indent()
        self.write("corrections.push(parts[1] + ' → ' + objMatch.match);")
        self.write("parts[1] = objMatch.match;")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")
        self.write_blank()
        self.write("// For set commands, try to correct property name")
        self.write("if (parts[0] === 'set' && parts.length > 2) {")
        self.indent()
        self.write("const propIdx = parts[2] === 'to' ? 1 : 2;")
        self.write("if (propIdx < parts.length) {")
        self.indent()
        self.write("const propMatch = fuzzyMatch(parts[propIdx], KNOWN_PROPERTIES, 0.7);")
        self.write("if (propMatch && propMatch.corrected) {")
        self.indent()
        self.write("corrections.push(parts[propIdx] + ' → ' + propMatch.match);")
        self.write("parts[propIdx] = propMatch.match;")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")
        self.write_blank()
        self.write("// For color values, try to correct")
        self.write("const toIdx = parts.indexOf('to');")
        self.write("if (toIdx > 0 && toIdx < parts.length - 1) {")
        self.indent()
        self.write("const valueIdx = toIdx + 1;")
        self.write("// Check if property is color-related")
        self.write("const propName = parts.slice(1, toIdx).find(p => KNOWN_PROPERTIES.includes(p.toLowerCase()));")
        self.write("if (propName === 'color') {")
        self.indent()
        self.write("const colorMatch = fuzzyMatch(parts[valueIdx], KNOWN_COLORS, 0.7);")
        self.write("if (colorMatch && colorMatch.corrected) {")
        self.indent()
        self.write("corrections.push(parts[valueIdx] + ' → ' + colorMatch.match);")
        self.write("parts[valueIdx] = colorMatch.match;")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("} else if (propName === 'font') {")
        self.indent()
        self.write("const fontMatch = fuzzyMatch(parts[valueIdx], KNOWN_FONTS, 0.6);")
        self.write("if (fontMatch && fontMatch.corrected) {")
        self.indent()
        self.write("corrections.push(parts[valueIdx] + ' → ' + fontMatch.match);")
        self.write("parts[valueIdx] = fontMatch.match;")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")
        self.write_blank()
        self.write("return { cmd: parts.join(' '), corrections };")
        self.dedent()
        self.write("}")
        self.write_blank()

    def _emit_voice_input(self):
        """Emit Web Speech API voice input with push-to-talk."""
        self.write_comment("Voice Input - Hold Ctrl+Space to speak (Chrome/Edge)")
        self.write("const voiceBtn = document.getElementById('rosh-voice');")
        self.write("let recognition = null;")
        self.write("let isListening = false;")
        self.write_blank()

        # Check for browser support
        self.write("const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;")
        self.write("if (SpeechRecognition) {")
        self.indent()
        self.write("recognition = new SpeechRecognition();")
        self.write("recognition.continuous = false;")
        self.write("recognition.interimResults = false;")
        self.write("recognition.lang = 'en-US';")
        self.write_blank()

        # On result - execute command and add to history
        self.write("recognition.onresult = (event) => {")
        self.indent()
        self.write("let cmd = event.results[0][0].transcript.toLowerCase();")
        # Spelling normalization (British + voice quirks)
        self.write("cmd = cmd.replace(/colour/gi, 'color').replace(/centre/gi, 'center').replace(/rodger/gi, 'roger');")
        # Word to number conversion
        self.write("const numWords = {zero:0,one:1,two:2,three:3,four:4,five:5,six:6,seven:7,eight:8,nine:9,ten:10};")
        self.write("cmd = cmd.replace(/\\b(zero|one|two|three|four|five|six|seven|eight|nine|ten)\\b/gi, m => numWords[m.toLowerCase()]);")
        self.write("log('[voice] ' + cmd, 'cyan');")
        # Apply fuzzy correction and add corrected command to history
        self.write("const corrected = fuzzyCorrectCommand(cmd);")
        self.write("cmdHistory.unshift(corrected.cmd); historyIdx = -1;")
        self.write("execCommand(cmd);")
        self.dedent()
        self.write("};")
        self.write_blank()

        # On end - reset state
        self.write("recognition.onend = () => {")
        self.indent()
        self.write("isListening = false;")
        self.write("voiceBtn.classList.remove('listening');")
        self.dedent()
        self.write("};")
        self.write_blank()

        # On error
        self.write("recognition.onerror = (event) => {")
        self.indent()
        self.write("log('[voice error] ' + event.error, 'err');")
        self.write("isListening = false;")
        self.write("voiceBtn.classList.remove('listening');")
        self.dedent()
        self.write("};")
        self.dedent()
        self.write("} else {")
        self.indent()
        self.write("voiceBtn.style.display = 'none';")
        self.write("log('[voice] Not supported in this browser', 'dim');")
        self.dedent()
        self.write("}")
        self.write_blank()

        # Start voice function
        self.write("function startVoice() {")
        self.indent()
        self.write("if (!recognition || isListening) return;")
        self.write("try {")
        self.indent()
        self.write("recognition.start();")
        self.write("isListening = true;")
        self.write("voiceBtn.classList.add('listening');")
        self.write("log('[voice] Listening...', 'dim');")
        self.dedent()
        self.write("} catch(e) { log('[voice] ' + e.message, 'err'); }")
        self.dedent()
        self.write("}")
        self.write_blank()

        # Stop voice function
        self.write("function stopVoice() {")
        self.indent()
        self.write("if (!recognition || !isListening) return;")
        self.write("recognition.stop();")
        self.dedent()
        self.write("}")
        self.write_blank()

        # Ctrl+Space push-to-talk (works anywhere when console visible)
        self.write("document.addEventListener('keydown', e => {")
        self.indent()
        self.write("if (e.ctrlKey && e.code === 'Space' && consoleVisible && !e.repeat) {")
        self.indent()
        self.write("e.preventDefault();")
        self.write("startVoice();")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("});")
        self.write_blank()

        self.write("document.addEventListener('keyup', e => {")
        self.indent()
        self.write("if (e.code === 'Space' && isListening) {")
        self.indent()
        self.write("stopVoice();")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("});")
        self.write_blank()

        # Click to toggle voice
        self.write("voiceBtn.addEventListener('click', () => {")
        self.indent()
        self.write("if (isListening) stopVoice(); else startVoice();")
        self.dedent()
        self.write("});")

    def _emit_exec_command(self):
        """Emit the execCommand function for REPL."""
        self.write("function execCommand(cmd) {")
        self.indent()
        self.write("// Apply fuzzy matching to correct typos and voice errors")
        self.write("const fuzzyResult = fuzzyCorrectCommand(cmd);")
        self.write("const originalCmd = cmd;")
        self.write("cmd = fuzzyResult.cmd;")
        self.write("if (fuzzyResult.corrections.length > 0) {")
        self.indent()
        self.write("log('[corrected: ' + fuzzyResult.corrections.join(', ') + ']', 'dim');")
        self.dedent()
        self.write("}")
        self.write("log('> ' + cmd, 'cmd');")
        # Normalize British spellings (fuzzy matching handles most, but keep as fallback)
        self.write("cmd = cmd.replace(/colour/gi, 'color').replace(/centre/gi, 'center');")
        self.write("const parts = cmd.trim().toLowerCase().split(/\\s+/);")
        self.write("try {")
        self.indent()

        # Help
        self.write("if (parts[0] === 'help' && parts[1]) {")
        self.indent()
        self.write("const obj = scene.getObjectByName(parts[1]);")
        self.write("if (obj) {")
        self.indent()
        self.write("const caps = availableCapabilitiesFor(obj);")
        self.write("if (caps.length) {")
        self.indent()
        self.write("log('Capabilities for ' + parts[1] + ':', 'cyan');")
        self.write("caps.forEach(cap => log('  ' + describeCapability(cap), 'cyan'));")
        self.dedent()
        self.write("} else log('No engine capabilities for ' + parts[1], 'dim');")
        self.dedent()
        self.write("} else {")
        self.indent()
        self.write("const cap = CAPABILITY_INDEX[parts[1]];")
        self.write("if (cap) logCapabilityHelp(cap); else log('Not found: ' + parts[1], 'err');")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")
        self.write("else if (parts[0] === 'help') {")
        self.indent()
        self.write("log('Commands: list, get, set, look/examine, create, delete, clone, prompt, save, load, camera reset, capabilities', 'cyan');")
        self.dedent()
        self.write("}")

        # Create - parse natural language like "create big yellow ball"
        self.write("else if (parts[0] === 'create') {")
        self.indent()
        self.write("const desc = parts.slice(1).join(' ').toLowerCase();")
        self.write("const colors = {red:0xff0000, green:0x00ff00, blue:0x0000ff, yellow:0xffff00, cyan:0x00ffff, magenta:0xff00ff, white:0xffffff, orange:0xff8800, purple:0x8800ff, pink:0xff88ff, gray:0x888888, black:0x111111};")
        self.write("let color = 0x00ff00, size = 1, shape = 'box', name = 'object';")
        self.write("for (const [c, hex] of Object.entries(colors)) if (desc.includes(c)) color = hex;")
        self.write("if (desc.includes('big') || desc.includes('large')) size = 2;")
        self.write("if (desc.includes('small') || desc.includes('tiny')) size = 0.5;")
        self.write("if (desc.includes('ball')) { shape = 'sphere'; name = 'ball'; }")
        self.write("else if (desc.includes('sphere')) { shape = 'sphere'; name = 'sphere'; }")
        self.write("else if (desc.includes('cube')) { shape = 'box'; name = 'cube'; }")
        self.write("else if (desc.includes('box')) { shape = 'box'; name = 'box'; }")
        self.write("else if (desc.includes('cylinder')) { shape = 'cylinder'; name = 'cylinder'; }")
        self.write("else if (desc.includes('tube')) { shape = 'cylinder'; name = 'tube'; }")
        # Check if name exists and append number if needed
        self.write("let finalName = name; let n = 1;")
        self.write("while (scene.getObjectByName(finalName)) { finalName = name + n; n++; }")
        self.write("let geom = shape === 'sphere' ? new THREE.SphereGeometry(size) : shape === 'cylinder' ? new THREE.CylinderGeometry(size, size, size*2) : new THREE.BoxGeometry(size, size, size);")
        self.write("const mat = new THREE.MeshStandardMaterial({color: color});")
        self.write("const mesh = new THREE.Mesh(geom, mat);")
        self.write("mesh.name = finalName;")
        self.write("mesh.position.set((Math.random()-0.5)*10, size, (Math.random()-0.5)*10);")
        self.write("mesh.userData._consoleTemplate = { type: 'mesh', shape, size, color };")
        self.write("scene.add(mesh);")
        self.write("log('Created ' + shape + ': ' + mesh.name, 'ok');")
        self.dedent()
        self.write("}")

        # Prompt - interpret natural language and execute as Rosh
        self.write("else if (parts[0] === 'prompt') {")
        self.indent()
        self.write("const desc = parts.slice(1).join(' ').toLowerCase();")
        self.write("// Simple pattern matching for common requests")
        self.write("if (desc.includes('create')) { execCommand('create ' + desc.replace('create', '')); }")
        self.write("else if (desc.match(/set\\s+(\\w+)\\s+(\\w+)\\s+to\\s+(\\w+)/)) {")
        self.indent()
        self.write("const m = desc.match(/set\\s+(\\w+)\\s+(\\w+)\\s+to\\s+(\\w+)/);")
        self.write("execCommand('set ' + m[1] + ' ' + m[2] + ' to ' + m[3]);")
        self.dedent()
        self.write("}")
        self.write("else if (desc.match(/move\\s+(\\w+)/)) {")
        self.indent()
        self.write("const obj = desc.match(/move\\s+(\\w+)/)[1];")
        self.write("const x = desc.includes('left') ? -2 : desc.includes('right') ? 2 : 0;")
        self.write("const y = desc.includes('up') ? 2 : desc.includes('down') ? -2 : 0;")
        self.write("execCommand('set ' + obj + ' x to ' + x);")
        self.write("if (y !== 0) execCommand('set ' + obj + ' y to ' + y);")
        self.dedent()
        self.write("}")
        self.write("else { log('Could not interpret: ' + desc, 'err'); log('Try: create big yellow ball, set logo color to red', 'cyan'); }")
        self.dedent()
        self.write("}")

        # List
        self.write("else if (parts[0] === 'list') {")
        self.indent()
        self.write("log('Objects:', 'cyan');")
        self.write("scene.traverse(o => { if (o.name && !o.name.startsWith('_')) log('  ' + o.name); });")
        self.dedent()
        self.write("}")

        # Delete
        self.write("else if (parts[0] === 'delete' && parts[1]) {")
        self.indent()
        self.write("const obj = scene.getObjectByName(parts[1]);")
        self.write("if (obj) { scene.remove(obj); log(\"Deleted '\" + parts[1] + \"'\", 'ok'); }")
        self.write("else log('Not found: ' + parts[1], 'err');")
        self.dedent()
        self.write("}")

        # Clone
        self.write("else if (parts[0] === 'clone' && parts[1]) {")
        self.indent()
        self.write("const src = scene.getObjectByName(parts[1]);")
        self.write("if (!src) { log('Not found: ' + parts[1], 'err'); return; }")
        # Determine target name - use 'as' keyword or auto-generate
        self.write("let targetName = parts[3] && (parts[2] === 'as' || parts[2] === 'to') ? parts[3] : null;")
        self.write("if (!targetName) { let n = 1; while (scene.getObjectByName(parts[1] + n)) n++; targetName = parts[1] + n; }")
        self.write("const clone = src.clone();")
        self.write("clone.name = targetName;")
        self.write("clone.position.x += 2;")  # Offset so it's visible
        self.write("scene.add(clone);")
        self.write("log(\"Cloned '\" + parts[1] + \"' as '\" + targetName + \"'\", 'ok');")
        self.dedent()
        self.write("}")

        # Get
        self.write("else if (parts[0] === 'get' && parts[1]) {")
        self.indent()
        self.write("const obj = scene.getObjectByName(parts[1]);")
        self.write("if (obj) { currentObject = obj; currentObjectName = parts[1]; log('<object: ' + parts[1] + '>', 'ok'); }")
        self.write("else log('Not found: ' + parts[1], 'err');")
        self.dedent()
        self.write("}")

        # Set - handles: set obj prop val, set obj prop to val, set prop val (with current obj)
        self.write("else if (parts[0] === 'set' && parts.length >= 3) {")
        self.indent()
        self.write("const filtered = parts.filter(x => x !== 'to');")
        self.write("let obj = null;")
        self.write("let prop = null;")
        self.write("let valueTokens = [];")
        self.write("if (filtered.length >= 4) {")
        self.indent()
        self.write("const candidate = scene.getObjectByName(filtered[1]);")
        self.write("if (candidate) {")
        self.indent()
        self.write("obj = candidate;")
        self.write("prop = filtered[2];")
        self.write("valueTokens = filtered.slice(3);")
        self.dedent()
        self.write("} else if (currentObject) {")
        self.indent()
        self.write("obj = currentObject;")
        self.write("prop = filtered[1];")
        self.write("valueTokens = filtered.slice(2);")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("} else if (currentObject && filtered.length >= 3) {")
        self.indent()
        self.write("obj = currentObject;")
        self.write("prop = filtered[1];")
        self.write("valueTokens = filtered.slice(2);")
        self.dedent()
        self.write("}")
        self.write("if (!obj || !prop || !valueTokens.length) { log('Usage: set <object> <property> to <value>', 'err'); return; }")
        self.write("const coreResult = handleCoreSet(obj, prop, valueTokens);")
        self.write("if (coreResult.ok) { log('OK', 'ok'); return; }")
        self.write("const capResult = applyCapabilityBridge(obj, prop, valueTokens);")
        self.write("if (capResult.ok) { log('OK', 'ok'); return; }")
        self.write("if (capResult.reason === 'unknown' && CAPABILITY_POLICY.allow_passthrough) {")
        self.indent()
        self.write("const passthroughValue = coerceSingleValue(valueTokens);")
        self.write("obj.userData[prop] = passthroughValue;")
        self.write("log('Stored on userData.' + prop, 'ok');")
        self.dedent()
        self.write("} else {")
        self.indent()
        self.write("log(capResult.message || ('Could not set ' + prop), 'err');")
        self.write("if (capResult.suggestion) log('Try: ' + capResult.suggestion, 'cyan');")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")

        # Inspect/Look/Examine
        self.write("else if ((parts[0] === 'inspect' || parts[0] === 'look' || parts[0] === 'examine') && parts[1]) {")
        self.indent()
        self.write("const obj = scene.getObjectByName(parts[1]);")
        self.write("if (obj) {")
        self.indent()
        self.write("log(parts[1] + ':', 'cyan');")
        self.write("log('  pos: [' + obj.position.x.toFixed(1) + ',' + obj.position.y.toFixed(1) + ',' + obj.position.z.toFixed(1) + ']');")
        self.write("if (obj._color) log('  color: ' + obj._color);")  # Text sprite color
        self.write("else if (obj.material && obj.material.color) log('  color: #' + obj.material.color.getHexString());")
        self.write("if (obj._text) log('  text: ' + obj._text);")
        self.write("log('  visible: ' + obj.visible);")
        self.write("for (const [k, v] of Object.entries(obj.userData)) { if (!k.startsWith('_')) log('  ' + k + ': ' + v); }")
        self.write("const caps = availableCapabilitiesFor(obj);")
        self.write("if (caps.length) {")
        self.indent()
        self.write("log('  capabilities:', 'cyan');")
        self.write("caps.forEach(cap => log('    ' + describeCapability(cap), 'cyan'));")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("} else log('Not found', 'err');")
        self.dedent()
        self.write("}")

        # Camera
        self.write("else if (parts[0] === 'camera' && parts[1] === 'reset') {")
        self.indent()
        self.write("camera.position.set(0, 5, 50); controls.target.set(0, 0, 0); log('Camera reset', 'ok');")
        self.dedent()
        self.write("}")

        # Save
        self.write("else if (parts[0] === 'save') {")
        self.indent()
        self.write("const slot = parts[1] || 'default';")
        self.write("const saveData = {};")
        self.write("scene.traverse(o => {")
        self.indent()
        self.write("if (o.name && !o.name.startsWith('_')) {")
        self.indent()
        self.write("const data = { x: o.position.x, y: o.position.y, z: o.position.z, ...o.userData };")
        self.write("if (o._color) data._textColor = o._color;")  # Text sprite color (CSS string)
        self.write("else if (o.material && o.material.color) data._color = o.material.color.getHex();")  # Mesh color (hex)
        self.write("if (o.scale) { data._sx = o.scale.x; data._sy = o.scale.y; data._sz = o.scale.z; }")
        self.write("if (o.visible !== undefined) data._visible = o.visible;")
        self.write("saveData[o.name] = data;")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("});")
        self.write("localStorage.setItem('rosh_save_' + slot, JSON.stringify(saveData));")
        self.write("log('Game saved to slot: ' + slot, 'ok');")
        self.dedent()
        self.write("}")

        # Load
        self.write("else if (parts[0] === 'load') {")
        self.indent()
        self.write("const slot = parts[1] || 'default';")
        self.write("const json = localStorage.getItem('rosh_save_' + slot);")
        self.write("if (!json) { log('No save found in slot: ' + slot, 'err'); return; }")
        self.write("const saveData = JSON.parse(json);")
        self.write("for (const [name, data] of Object.entries(saveData)) {")
        self.indent()
        self.write("let obj = scene.getObjectByName(name);")
        self.write("if (!obj && data._consoleTemplate && data._consoleTemplate.type === 'mesh') {")
        self.indent()
        self.write("const tpl = data._consoleTemplate;")
        self.write("let geom = null;")
        self.write("const size = tpl.size || 1;")
        self.write("if (tpl.shape === 'sphere') geom = new THREE.SphereGeometry(size, 32, 32);")
        self.write("else if (tpl.shape === 'cylinder') geom = new THREE.CylinderGeometry(size, size, size * 2);")
        self.write("else geom = new THREE.BoxGeometry(size, size, size);")
        self.write("const mat = new THREE.MeshStandardMaterial({ color: tpl.color ?? 0x00ff00 });")
        self.write("const mesh = new THREE.Mesh(geom, mat);")
        self.write("mesh.name = name;")
        self.write("mesh.userData = Object.assign({}, tpl);")
        self.write("scene.add(mesh);")
        self.write("obj = mesh;")
        self.dedent()
        self.write("}")
        self.write("if (obj) {")
        self.indent()
        self.write("if (data.x !== undefined) obj.position.x = data.x;")
        self.write("if (data.y !== undefined) obj.position.y = data.y;")
        self.write("if (data.z !== undefined) obj.position.z = data.z;")
        self.write("const fontSize = data.font_size || (obj.userData && obj.userData.font_size) || 48;")
        self.write("if (data._textColor !== undefined && obj._ctx) {")  # Text sprite
        self.indent()
        self.write("obj._color = data._textColor; obj._ctx.clearRect(0, 0, obj._canvas.width, obj._canvas.height);")
        self.write("obj._ctx.font = 'bold ' + fontSize + 'px Arial'; obj._ctx.textAlign = 'center'; obj._ctx.textBaseline = 'middle';")
        self.write("obj._ctx.fillStyle = data._textColor; obj._ctx.fillText(obj._text, obj._canvas.width/2, obj._canvas.height/2);")
        self.write("obj.material.map.needsUpdate = true;")
        self.dedent()
        self.write("} else if (data._color !== undefined && obj.material && obj.material.color) obj.material.color.setHex(data._color);")
        self.write("if (data._sx !== undefined && obj.scale) { obj.scale.x = data._sx; obj.scale.y = data._sy; obj.scale.z = data._sz; }")
        self.write("if (data._visible !== undefined) obj.visible = data._visible;")
        self.write("Object.assign(obj.userData, data);")
        self.write("restoreCapabilityState(obj);")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")
        self.write("log('Game loaded from slot: ' + slot, 'ok');")
        self.dedent()
        self.write("}")

        # Clear
        self.write("else if (parts[0] === 'clear') { output.innerHTML = ''; }")

        self.write("else if (cmd.trim()) log('Unknown: ' + parts[0], 'err');")

        self.dedent()
        self.write("} catch(e) { log('Error: ' + e.message, 'err'); }")
        self.dedent()
        self.write("}")
        self.write_blank()

    # =========================================================================
    # Action Emission
    # =========================================================================

    def emit_action(self, action) -> str:
        """Generate code for an action."""
        if isinstance(action, IR_Conditional):
            return self._emit_conditional(action)
        elif isinstance(action, IR_Loop):
            return self.emit_loop(action)
        elif not isinstance(action, IR_Action):
            return ""

        action_type = action.type
        params = action.params

        if action_type == 'set_property':
            return self._emit_set_property(params)
        elif action_type == 'print':
            msg = params.get('message')
            if msg:
                expr = self.emit_expression(msg)
                return f"console.log({expr});"
            return "console.log();"
        elif action_type == 'play_sound':
            asset = params.get('asset', '')
            safe_name = asset.replace('.', '_').replace('-', '_').replace('/', '_')
            return f"if (sounds['{safe_name}']) {{ sounds['{safe_name}'].stop(); sounds['{safe_name}'].play(); }}"
        elif action_type == 'goto':
            scene = params.get('scene')
            level = params.get('level')
            code_parts = []
            if scene is not None:
                code_parts.append(f"currentScene = '{scene}';")
            if level is not None:
                code_parts.append(f"currentLevel = {level};")
            code_parts.append("updateSceneVisibility();")
            return " ".join(code_parts)

        elif action_type == 'save_game':
            slot = params.get('slot') or 'default'
            self.uses_save_load = True
            return f"saveGame('{slot}');"

        elif action_type == 'load_game':
            slot = params.get('slot') or 'default'
            self.uses_save_load = True
            return f"loadGame('{slot}');"

        elif action_type == 'call':
            func_name = params.get('function', params.get('name', ''))
            return f"{func_name}();"

        return f"// TODO: {action_type}"

    def _emit_set_property(self, params: Dict) -> str:
        """Emit set_property action."""
        target = params.get('target')
        prop = params.get('property')
        value = params.get('value')

        if isinstance(value, IR_Value):
            val_str = self._format_value(value)
        elif isinstance(value, IR_Expression):
            val_str = self.emit_expression(value)
        else:
            val_str = str(value)

        # Map to Three.js
        if prop in ('x', 'y', 'z'):
            return f"{target}.position.{prop} = {val_str};"
        elif prop == 'visible':
            return f"{target}.visible = {val_str};"
        elif prop == 'color':
            return f"{target}.material.color.set({val_str});"
        elif prop == 'font_size':
            # Update font_size and redraw text sprite
            return f"{target}.userData.font_size = {val_str}; if ({target}._ctx) {{ {target}._ctx.clearRect(0, 0, {target}._canvas.width, {target}._canvas.height); {target}._ctx.font = 'bold ' + {target}.userData.font_size + 'px Arial'; {target}._ctx.fillStyle = {target}._color || '#ffffff'; {target}._ctx.textAlign = 'center'; {target}._ctx.textBaseline = 'middle'; {target}._ctx.fillText({target}._text, {target}._canvas.width/2, {target}._canvas.height/2); {target}.material.map.needsUpdate = true; }}"
        elif prop == 'text':
            # Update text content and redraw text sprite
            return f"{target}._text = {val_str}; if ({target}._ctx) {{ {target}._ctx.clearRect(0, 0, {target}._canvas.width, {target}._canvas.height); {target}._ctx.font = 'bold ' + ({target}.userData.font_size || 48) + 'px Arial'; {target}._ctx.fillStyle = {target}._color || '#ffffff'; {target}._ctx.textAlign = 'center'; {target}._ctx.textBaseline = 'middle'; {target}._ctx.fillText({target}._text, {target}._canvas.width/2, {target}._canvas.height/2); {target}.material.map.needsUpdate = true; }}"
        else:
            return f"{target}.userData.{prop} = {val_str};"

    def _emit_conditional(self, cond: IR_Conditional) -> str:
        """Emit conditional as JavaScript."""
        condition = self.emit_expression(cond.condition)
        lines = [f"if ({condition}) {{"]

        for action in cond.then_actions:
            if action:
                code = self.emit_action(action)
                if code:
                    lines.append(f"    {code}")

        if cond.else_actions:
            lines.append("} else {")
            for action in cond.else_actions:
                if action:
                    code = self.emit_action(action)
                    if code:
                        lines.append(f"    {code}")

        lines.append("}")
        return '\n'.join(lines)

    # =========================================================================
    # Expression Emission
    # =========================================================================

    def emit_expression(self, expr) -> str:
        """Generate code for an expression."""
        if isinstance(expr, IR_Value):
            return self._format_value(expr)

        if not isinstance(expr, IR_Expression):
            return str(expr)

        if expr.type == 'literal':
            return self._format_value(expr.value)
        elif expr.type == 'property_access':
            if expr.right in ('x', 'y', 'z'):
                return f"{expr.left}.position.{expr.right}"
            return f"{expr.left}.userData.{expr.right}"
        elif expr.type == 'comparison':
            left = self.emit_expression(expr.left)
            right = self.emit_expression(expr.right)
            return f"{left} {expr.operator} {right}"
        elif expr.type == 'binary_op':
            left = self.emit_expression(expr.left)
            right = self.emit_expression(expr.right)
            op = '&&' if expr.operator == 'and' else '||' if expr.operator == 'or' else expr.operator
            return f"({left} {op} {right})"
        elif expr.type == 'unary_op':
            operand = self.emit_expression(expr.left) if expr.left else self.emit_expression(expr.right)
            return f"({expr.operator}{operand})"

        return str(expr)

    def emit_object(self, obj: IR_Object) -> str:
        """Stub for testing."""
        return ""

    def emit_event(self, event: IR_Event) -> str:
        """Stub for testing."""
        return ""

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _format_value(self, value: IR_Value) -> str:
        """Format IR_Value for JavaScript."""
        if value.type == 'string':
            s = value.value
            # Convert string interpolation {var.prop} to template literal ${var.userData.prop}
            import re
            def replace_interp(m):
                expr = m.group(1)
                if '.' in expr:
                    parts = expr.split('.')
                    obj = parts[0]
                    prop = parts[1]
                    if prop in ('x', 'y', 'z'):
                        return f"${{{obj}.position.{prop}}}"
                    return f"${{{obj}.userData.{prop}}}"
                return f"${{{expr}}}"
            if '{' in s:
                s = re.sub(r'\{([^}]+)\}', replace_interp, s)
                return f"`{s}`"
            return f"'{s}'"
        elif value.type == 'number':
            return str(value.value)
        elif value.type == 'boolean':
            return 'true' if value.value else 'false'
        elif value.type == 'percentage':
            return str(value.value)
        elif value.type == 'expression':
            return self.emit_expression(value.value)
        else:
            return str(value.value)

    def _get_prop_value(self, obj: IR_Object, prop: str, default: float) -> float:
        """Get property value from object."""
        if prop in obj.properties:
            val = obj.properties[prop]
            if val.type in ('percentage', 'number'):
                return val.value
        return default

    def _get_prop_string(self, obj: IR_Object, prop: str, default: str) -> str:
        """Get string property value."""
        if prop in obj.properties:
            val = obj.properties[prop]
            if val.type == 'string':
                return val.value
        return default

    def _get_color(self, obj: IR_Object) -> int:
        """Get color for object."""
        if 'color' in obj.properties:
            color_val = obj.properties['color']
            if color_val.type == 'color':
                return color_val.value
            elif color_val.type == 'string':
                color_name = color_val.value.lower()
                if color_name in self.CSS_COLORS:
                    return self.CSS_COLORS[color_name]
        # Default color
        return self.DEFAULT_COLORS[self.color_index % len(self.DEFAULT_COLORS)]

    def _js_key(self, key: str) -> str:
        """Convert Rosh key name to JavaScript key comparison."""
        key_map = {
            'space': "e.key === ' ' || e.code === 'Space'",
            'enter': "e.key === 'Enter'",
            'escape': "e.key === 'Escape'",
            'left': "e.key === 'ArrowLeft'",
            'right': "e.key === 'ArrowRight'",
            'up': "e.key === 'ArrowUp'",
            'down': "e.key === 'ArrowDown'",
        }
        # Check special keys
        if key.lower() in key_map:
            return key_map[key.lower()]
        # Number keys
        if key.isdigit():
            return f"e.key === '{key}'"
        # Letter keys
        if len(key) == 1:
            return f"e.key === '{key.lower()}' || e.key === '{key.upper()}'"
        return f"e.key === '{key}'"
