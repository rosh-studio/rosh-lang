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
See: rosh-dev/proposals/IR-VERSIONING-POLICY.md

SPEC COMPLIANCE AUDIT (2026-01-10):
====================================
Status: MOSTLY COMPLIANT - needs cleanup

Rogue code found (should use spec values):
- Lines 60-64: CSS_COLORS dict duplicates spec colors
- Lines 69-70: Hardcoded color palette for random colors
- Line 2603: TWIN_COLORS inline definition
- Various: Hardcoded scene colors (0x1a1a2e, 0x333333, etc.)

TODO:
1. Generate code that imports from rosh-colors.js
2. Create rosh-sizes.js module and use it
3. Remove CSS_COLORS dict, use spec instead
4. Use spec/v0.3.0/rosh-spec.toml as source of truth

Runtime JS files (static/) are mostly compliant:
- rosh-colors.js: Centralized colors (needs sync with spec)
- rosh-adapter-threejs.js: Uses RoshColors, has fallback SIZE_MAP
"""

# =============================================================================
# STOP - DO NOT MODIFY THIS EMITTER
# =============================================================================
# This emitter is FROZEN for demo purposes. All new features must go through:
#   1. Parser/IR first (src/rosh/parser.py, ir.py, ir_transformer.py)
#   2. Bump IR_VERSION
#   3. Update ALL emitters together
#
# Adding features here without IR changes violates the versioning policy.
# See: rosh-dev/proposals/IR-VERSIONING-POLICY.md
# =============================================================================
IMPLEMENTS_IR_VERSION = "0.2.1"
# NOTE: Python interpreter is at 0.2.3 (spec test infrastructure).
# Emitters are deliberately behind - they work, but don't have spec testing.
# Priority: Sync emitters to 0.2.3 when parity tests are implemented.

import json
from pathlib import Path
from typing import Dict, Any, Set, List
from .base import BaseEmitter
from ..ir import (
    IR_Program, IR_Object, IR_Event, IR_Action, IR_Function,
    IR_Value, IR_Expression, IR_Conditional, IR_Loop
)
from ..data import get_known_objects_3d, get_known_objects_by_category
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
        self.model_assets: Set[str] = set()  # GLB model files needed
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

        # Shared runtime option (new architecture)
        # Check both external meta (TOML) and IR metadata (inline meta block)
        # Use shared runtime by default (new architecture as of v0.2.7)
        # Can be disabled with use_shared_runtime: false in meta
        self.use_shared_runtime = (
            self.meta.get('use_shared_runtime', True) and
            self.ir.metadata.extra.get('use_shared_runtime', True)
        )

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
        """Build capability policy from project config."""
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
            applies_to=["mesh", "sprite", "model"],
            tags=["safe"],
            args=["uniform|x y z"],
            description="Scale objects uniformly or per-axis."
        )
        self._register_capability(
            "spin",
            handler="spin",
            applies_to=["mesh", "sprite", "model"],
            tags=["safe"],
            args=["xSpeed ySpeed zSpeed"],
            description="Rotate objects continuously (degrees per second)."
        )
        self._register_capability(
            "bounce",
            handler="bounce",
            applies_to=["mesh", "sprite", "model"],
            tags=["safe"],
            args=["amplitude frequency"],
            description="Apply vertical bounce animation (frequency per second)."
        )
        self._register_capability(
            "pulse",
            handler="pulse",
            applies_to=["mesh", "sprite", "text", "hud", "model"],
            tags=["safe"],
            args=["amplitude frequency"],
            description="Scale object in/out with a sine wave (amplitude multiplier, frequency in Hz)."
        )
        self._register_capability(
            "orbit",
            handler="orbit",
            applies_to=["mesh", "sprite", "model"],
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
        self.write("const gameObjects = {};  // Registry for console-created objects")
        self.write("window._objects = {};  // Global object registry for query syntax")
        self.write("window._selection = [];  // Current selection for bulk operations")
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

        # GLTFLoader for 3D models
        self.write_comment("GLTFLoader for 3D models")
        self.write("const gltfLoader = new THREE.GLTFLoader();")
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
        """Emit 2D game objects as JavaScript data.

        Hidden objects (name starts with '_') are skipped - they exist in IR
        for templates, config, meta, etc. but are not rendered in the game.
        """
        self.write_comment("Game Objects")
        width = self.ir.metadata.canvas_width
        height = self.ir.metadata.canvas_height

        for obj in self.ir.objects:
            name = obj.name

            # Hidden objects: create data-only object (not rendered in scene)
            if obj.hidden:
                self.write_comment(f"Hidden data object: {name}")
                self.write(f"const {name} = {{ userData: {{}} }};")
                # Set properties on userData
                for prop_name, prop_value in obj.properties.items():
                    val = prop_value.value
                    if isinstance(val, str):
                        escaped_val = val.replace("\\", "\\\\").replace("'", "\\'")
                        self.write(f"{name}.userData.{prop_name} = '{escaped_val}';")
                    elif isinstance(val, bool):
                        self.write(f"{name}.userData.{prop_name} = {str(val).lower()};")
                    else:
                        self.write(f"{name}.userData.{prop_name} = {val};")
                # Set default x/y on userData for consistency
                self.write(f"{name}.userData.x = 0.5;")
                self.write(f"{name}.userData.y = 0.5;")
                self.write(f"window._objects['{name}'] = {name};")
                continue

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
                        escaped_val = val.replace("\\", "\\\\").replace("'", "\\'")
                        custom_props[key] = f"'{escaped_val}'"
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
        self.write("if (window.consoleVisible) return;  // Skip when console open")
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
        self.write("let _roshLastFrame = performance.now();")
        self.write_comment("Animation Loop")
        self.write("function animate() {")
        self.indent()
        self.write("requestAnimationFrame(animate);")
        self.write("const now = performance.now();")
        self.write("const delta = (now - _roshLastFrame) / 1000;")
        self.write("_roshLastFrame = now;")
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
        # Physics update (gravity, click-to-move) - only if adapter exists
        self.write_comment("Physics update (gravity, click-to-move)")
        self.write("if (typeof adapter !== 'undefined' && adapter && adapter.update) adapter.update(delta);")
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
        self.write("const gameObjects = {};  // Registry for console-created objects")
        self.write("window._objects = {};  // Global object registry for query syntax")
        self.write("window._selection = [];  // Current selection for bulk operations")
        self.write("scene.background = new THREE.Color(0x1a1a2e);")
        self.write_blank()

        # Runtime configuration for REPL settings
        self.write_comment("Runtime config for REPL settings")
        self.write("const _config = { modelScale: 2, useModels: true, floor: true, floorColor: null, confirm: true };")
        self.write("// _config.modelScale: global multiplier for all 3D model sizes (default 2)")
        self.write("// _config.useModels: if false, use primitive shapes instead of GLB models")
        self.write("// _config.floor: show/hide the ground grid (default true)")
        self.write("// _config.floorColor: solid floor color (null = grid only, hex = solid floor)")
        self.write("// _config.confirm: require confirmation for bulk ops >= 10 (default true)")
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

        # Scene transition overlay (cheap fade effect)
        if self.uses_scenes:
            self.write_comment("Scene transition overlay")
            self.write("const transitionOverlay = document.createElement('div');")
            self.write("transitionOverlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:#000;opacity:0;pointer-events:none;transition:opacity 0.3s ease;z-index:999';")
            self.write("document.body.appendChild(transitionOverlay);")
            self.write("function transitionToScene(newScene) {")
            self.indent()
            self.write("transitionOverlay.style.opacity = '1';")
            self.write("setTimeout(() => {")
            self.indent()
            self.write("currentScene = newScene;")
            self.write("updateSceneVisibility();")
            self.write("setTimeout(() => { transitionOverlay.style.opacity = '0'; }, 50);")
            self.dedent()
            self.write("}, 300);")
            self.dedent()
            self.write("}")
            self.write_blank()

        # OrbitControls
        self.write_comment("OrbitControls")
        self.write("const controls = new THREE.OrbitControls(camera, renderer.domElement);")
        self.write("controls.enableDamping = true;")
        self.write("controls.dampingFactor = 0.05;")
        self.write_blank()

        # GLTFLoader for 3D models
        self.write_comment("GLTFLoader for 3D models")
        self.write("const gltfLoader = new THREE.GLTFLoader();")
        self.write_blank()

        # Edit mode raycaster for object selection
        self.write_comment("Edit mode raycaster")
        self.write("const raycaster = new THREE.Raycaster();")
        self.write("const mouse = new THREE.Vector2();")
        self.write_blank()

        # Click handler for edit mode selection
        self.write_comment("Edit mode click selection")
        self.write("renderer.domElement.addEventListener('click', (e) => {")
        self.indent()
        self.write("if (!editMode && !window.editMode) return;")
        self.write("if (window.consoleVisible) return;")
        self.write("mouse.x = (e.clientX / window.innerWidth) * 2 - 1;")
        self.write("mouse.y = -(e.clientY / window.innerHeight) * 2 + 1;")
        self.write("raycaster.setFromCamera(mouse, camera);")
        self.write("const selectables = Object.values(gameObjects).filter(o => o && o.visible !== false);")
        self.write("const intersects = raycaster.intersectObjects(selectables, true);")
        self.write("if (intersects.length > 0) {")
        self.indent()
        self.write("let hitObj = intersects[0].object;")
        self.write("// Find which gameObject contains this hit (works for both primitives and loaded models)")
        self.write("let foundName = null;")
        self.write("for (const [name, go] of Object.entries(gameObjects)) {")
        self.indent()
        self.write("if (!go) continue;")
        self.write("// Check if hitObj is the object or a descendant of it")
        self.write("let check = hitObj;")
        self.write("while (check) {")
        self.indent()
        self.write("if (check === go) { foundName = name; break; }")
        self.write("check = check.parent;")
        self.dedent()
        self.write("}")
        self.write("if (foundName) break;")
        self.dedent()
        self.write("}")
        self.write("if (foundName && gameObjects[foundName]) {")
        self.indent()
        self.write("window.selectedObject = gameObjects[foundName];")
        self.write("console.log('Selected:', foundName);")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("} else {")
        self.indent()
        self.write("window.selectedObject = null;")
        self.write("console.log('Selection cleared');")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("});")
        self.write_blank()

        # WASD camera movement + Arrow keys for player objects
        self.write_comment("Keyboard controls")
        self.write("const moveState = { forward: false, backward: false, left: false, right: false, up: false, down: false };")
        self.write("const arrowState = { left: false, right: false, up: false, down: false, rise: false, fall: false };")
        self.write("document.addEventListener('keydown', (e) => {")
        self.indent()
        self.write("// Allow arrow keys in edit mode even when console not focused")
        self.write("const isArrowKey = ['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', '.', '/'].includes(e.key);")
        self.write("if ((window.consoleVisible || consoleVisible) && !(window.editMode && isArrowKey)) return;")

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
        self.write("const ambientLight = new THREE.AmbientLight(0x606060, 1.0);")
        self.write("scene.add(ambientLight);")
        self.write("const directionalLight = new THREE.DirectionalLight(0xffffff, 1.5);")
        self.write("directionalLight.position.set(5, 10, 7);")
        self.write("scene.add(directionalLight);")
        self.write("// Add fill light from opposite side for better visibility")
        self.write("const fillLight = new THREE.DirectionalLight(0xffffff, 0.5);")
        self.write("fillLight.position.set(-5, 5, -5);")
        self.write("scene.add(fillLight);")
        self.write_blank()

        # Ground grid and floor
        self.write_comment("Ground grid and floor")
        self.write("const gridHelper = new THREE.GridHelper(100, 50, 0x444466, 0x333355);")
        self.write("gridHelper.name = '_grid';")
        self.write("gridHelper.position.y = -1;")
        self.write("scene.add(gridHelper);")
        self.write("// Solid floor plane (initially hidden, shown when _config.floorColor is set)")
        self.write("const floorGeom = new THREE.PlaneGeometry(100, 100);")
        self.write("const floorMat = new THREE.MeshStandardMaterial({ color: 0x333333, side: THREE.DoubleSide });")
        self.write("const floorMesh = new THREE.Mesh(floorGeom, floorMat);")
        self.write("floorMesh.name = '_floor';")
        self.write("floorMesh.rotation.x = -Math.PI / 2;")
        self.write("floorMesh.position.y = -1.01;")  # Slightly below grid
        self.write("floorMesh.visible = false;")
        self.write("scene.add(floorMesh);")
        self.write_blank()

        # Console state
        self.write("let consoleVisible = false;")
        self.write("let pendingOp = null;")  # For confirmation on bulk operations
        self.write("// pendingOp = { type: 'delete'|'create', count: N, execute: () => {...} }")
        self.write("let pendingScene = null;")  # For fuzzy scene match confirmation
        self.write("let pendingAction = null;")  # For other confirmations

        # Scene/level state (always declare for REPL compatibility)
        initial_scene = self.ir.metadata.initial_scene if self.uses_scenes else None
        initial_level = self.ir.metadata.initial_level if self.uses_scenes else 1
        if initial_scene:
            self.write(f"let currentScene = '{initial_scene}';")
        else:
            self.write("let currentScene = null;")
        self.write(f"let currentLevel = {initial_level};")

        # Edit mode state
        self.write("let editMode = false;")
        self.write("let selectedObject = null;")

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
        """Emit a single Three.js object.

        Hidden objects (name starts with '_') are created as data-only objects
        (not added to scene) for templates, config, state, etc.
        """
        name = obj.name

        # Hidden objects: create data-only object (not rendered)
        if obj.hidden:
            self.write_comment(f"Hidden data object: {name}")
            self.write(f"const {name} = {{ userData: {{}} }};")
            # Set properties
            for prop_name, prop_value in obj.properties.items():
                val = self.get_value(prop_value)
                if isinstance(val, bool):
                    self.write(f"{name}.userData.{prop_name} = {'true' if val else 'false'};")
                elif isinstance(val, str):
                    escaped_val = val.replace("\\", "\\\\").replace("'", "\\'")
                    self.write(f"{name}.userData.{prop_name} = '{escaped_val}';")
                else:
                    self.write(f"{name}.userData.{prop_name} = {val};")
            # Register in _objects for queries
            self.write(f"window._objects['{name}'] = {name};")
            self.write_blank()
            return

        # Get position (normalized 0-1 in IR, convert to 3D world coords)
        x = self._get_prop_value(obj, 'x', 0.5)
        y = self._get_prop_value(obj, 'y', 0.5)
        z = self._get_prop_value(obj, 'z', 0)

        # Convert normalized coords to 3D world
        # Values in 0-1 range are normalized, outside that range are world coords
        # x: 0-1 maps to roughly -8 to 8, else used directly
        # y: 0-1 maps to roughly 8 to 0 (inverted, above ground), else used directly
        # z: used directly as world coordinate (not normalized)
        if 0 <= x <= 1:
            world_x = (x - 0.5) * 16
        else:
            world_x = x  # World coordinate
        if 0 <= y <= 1:
            world_y = (0.5 - y) * 8 + 2  # Center at y=2 (above ground)
        else:
            world_y = y  # World coordinate
        world_z = z  # Z is passed through directly as world coordinate

        # Get shape type - check both 'shape' and 'type' properties
        shape = 'box'
        type_val = None
        for shape_prop in ('type', 'shape'):
            if shape_prop in obj.properties:
                prop_val = obj.properties[shape_prop]
                shape = prop_val.value if hasattr(prop_val, 'value') else str(prop_val)
                if shape_prop == 'type':
                    type_val = shape
                break

        # If type is a known object, look up its shape from known_objects
        if type_val:
            known_objects = get_known_objects_3d()
            if type_val in known_objects and 'shape' in known_objects[type_val]:
                shape = known_objects[type_val]['shape']

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
            font_size = self._get_prop_number(obj, 'font_size', 48)
            self._emit_text_sprite(name, text, color, world_x, world_y, world_z, font_size)
            object_kind = 'text'
        elif 'sprite' in obj.properties:
            sprite = obj.properties['sprite'].value
            self._emit_textured_plane(name, sprite, world_x, world_y, world_z, width, height)
            object_kind = 'sprite'
        elif shape in ('sphere', 'ball'):
            self.write(f"const {name}Geometry = new THREE.SphereGeometry({radius}, 32, 32);")
            self.write(f"const {name}Material = new THREE.MeshStandardMaterial({{ color: 0x{color:06x} }});")
            self.write(f"const {name} = new THREE.Mesh({name}Geometry, {name}Material);")
            self.write(f"{name}.position.set({world_x:.2f}, {world_y:.2f}, {world_z:.2f});")
            self.write(f"{name}.name = '{name}';")
            self.write(f"scene.add({name});")
        elif shape in ('cylinder', 'tube'):
            self.write(f"const {name}Geometry = new THREE.CylinderGeometry({radius}, {radius}, {height:.2f}, 32);")
            self.write(f"const {name}Material = new THREE.MeshStandardMaterial({{ color: 0x{color:06x} }});")
            self.write(f"const {name} = new THREE.Mesh({name}Geometry, {name}Material);")
            self.write(f"{name}.position.set({world_x:.2f}, {world_y:.2f}, {world_z:.2f});")
            self.write(f"{name}.name = '{name}';")
            self.write(f"scene.add({name});")
        elif shape == 'cone':
            self.write(f"const {name}Geometry = new THREE.ConeGeometry({radius}, {height:.2f}, 32);")
            self.write(f"const {name}Material = new THREE.MeshStandardMaterial({{ color: 0x{color:06x} }});")
            self.write(f"const {name} = new THREE.Mesh({name}Geometry, {name}Material);")
            self.write(f"{name}.position.set({world_x:.2f}, {world_y:.2f}, {world_z:.2f});")
            self.write(f"{name}.name = '{name}';")
            self.write(f"scene.add({name});")
        elif shape == 'torus':
            self.write(f"const {name}Geometry = new THREE.TorusGeometry({radius}, {radius * 0.3:.2f}, 16, 48);")
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
            # Default: box/cube
            self.write(f"const {name}Geometry = new THREE.BoxGeometry({width:.2f}, {height:.2f}, {depth:.2f});")
            self.write(f"const {name}Material = new THREE.MeshStandardMaterial({{ color: 0x{color:06x} }});")
            self.write(f"const {name} = new THREE.Mesh({name}Geometry, {name}Material);")
            self.write(f"{name}.position.set({world_x:.2f}, {world_y:.2f}, {world_z:.2f});")
            self.write(f"{name}.name = '{name}';")
            self.write(f"scene.add({name});")

        self.write(f"{name}.userData._rosh_kind = '{object_kind}';")

        # Store type for known object model loading at runtime
        if 'type' in obj.properties:
            type_val = self.get_value(obj.properties['type'])
            if isinstance(type_val, str):
                self.write(f"{name}.userData._type = '{type_val}';")
                # Mark as needing model load at startup
                self.write(f"{name}.userData._needsModelLoad = true;")
                # Track model assets needed for build
                known_objects = get_known_objects_3d()
                if type_val in known_objects and 'model' in known_objects[type_val]:
                    self.model_assets.add(known_objects[type_val]['model'])

        # Apply initial visible property if set to false
        if 'visible' in obj.properties:
            vis_val = self.get_value(obj.properties['visible'])
            if vis_val is False or vis_val == 'false':
                self.write(f"{name}.visible = false;")

        # Custom properties in userData
        known = {'x', 'y', 'z', 'width', 'height', 'depth', 'color', 'shape', 'radius', 'text', 'sprite', 'visible', 'saveable', 'type', 'fixed'}
        # Capability properties need special handling - stored as _name with array values
        capability_props = {'spin', 'orbit', 'bounce', 'pulse'}
        for prop_name, prop_value in obj.properties.items():
            if prop_name not in known:
                val = self.get_value(prop_value)
                if prop_name in capability_props:
                    # Parse "x y z" string into array and store as _name
                    if isinstance(val, str):
                        parts = val.split()
                        try:
                            nums = [float(p) for p in parts]
                            self.write(f"{name}.userData._{prop_name} = [{', '.join(str(n) for n in nums)}];")
                        except ValueError:
                            self.write(f"{name}.userData._{prop_name} = '{val}';")
                    else:
                        self.write(f"{name}.userData._{prop_name} = {val};")
                elif isinstance(val, str):
                    escaped_val = val.replace("\\", "\\\\").replace("'", "\\'")
                    self.write(f"{name}.userData.{prop_name} = '{escaped_val}';")
                elif isinstance(val, bool):
                    self.write(f"{name}.userData.{prop_name} = {'true' if val else 'false'};")
                else:
                    self.write(f"{name}.userData.{prop_name} = {val};")

        # Scene/level membership
        if obj.scene is not None:
            self.write(f"{name}.userData._scene = '{obj.scene}';")
        if obj.level is not None:
            self.write(f"{name}.userData._level = {obj.level};")

        # Store object type for query filtering (use object name as type if not specified)
        if 'type' not in obj.properties:
            self.write(f"{name}.userData._type = '{name}';")

        # Register in global _objects for query support (Phase 3)
        self.write(f"window._objects['{name}'] = {name};")
        # Also register in gameObjects for REPL list command
        self.write(f"gameObjects['{name}'] = {name};")

        # UUID for REPL
        self.write(f"{name}.userData._rosh_uuid = crypto.randomUUID();")

        # Scene objects are fixed by default (immune to gravity) unless explicitly set to false
        # Text objects are always fixed (never affected by gravity)
        if object_kind in ('text', 'hud', 'sprite'):
            self.write(f"{name}.userData.fixed = true;  // Text/sprites never fall")
        elif 'fixed' in obj.properties:
            fixed_val = self.get_value(obj.properties['fixed'])
            if fixed_val is False or fixed_val == 'false':
                self.write(f"{name}.userData.fixed = false;")
            else:
                self.write(f"{name}.userData.fixed = true;")
        else:
            # Scene objects default to fixed=true
            self.write(f"{name}.userData.fixed = true;  // Scene objects fixed by default")
        self.write_blank()
        self.color_index += 1

    def _emit_init_actions(self):
        """Emit initialization actions (top-level set statements like set _config.phase to 1)."""
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

        # Static objects from source
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

        # Dynamic objects created at runtime
        self.write("// Handle dynamically created objects")
        self.write("scene.traverse((obj) => {")
        self.indent()
        self.write("if (obj.userData && obj.userData._scene) {")
        self.indent()
        self.write("obj.visible = (obj.userData._scene === currentScene);")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("});")

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

    def _emit_text_sprite(self, name: str, text: str, color: int, x: float, y: float, z: float, font_size: int = 48):
        """Emit a text sprite using canvas texture."""
        css_color = f"#{color:06x}"
        # Use fixed sprite scale - font_size only affects canvas text rendering
        # This allows font_size animation to work (text grows within fixed sprite)
        scale_x = 20
        scale_y = 5

        self.write(f"const {name}Canvas = document.createElement('canvas');")
        self.write(f"const {name}Ctx = {name}Canvas.getContext('2d');")
        self.write(f"{name}Canvas.width = 1024;")
        self.write(f"{name}Canvas.height = 256;")
        self.write(f"{name}Ctx.fillStyle = '{css_color}';")
        self.write(f"{name}Ctx.font = 'bold {font_size}px Arial';")
        self.write(f"{name}Ctx.textAlign = 'center';")
        self.write(f"{name}Ctx.textBaseline = 'middle';")
        self.write(f"{name}Ctx.fillText('{text}', 512, 128);")
        self.write(f"const {name}Texture = new THREE.CanvasTexture({name}Canvas);")
        self.write(f"const {name}Material = new THREE.SpriteMaterial({{ map: {name}Texture, transparent: true }});")
        self.write(f"const {name} = new THREE.Sprite({name}Material);")
        self.write(f"{name}.position.set({x:.2f}, {y:.2f}, {z:.2f});")
        self.write(f"{name}.scale.set({scale_x:.2f}, {scale_y:.2f}, 1);")
        self.write(f"{name}.name = '{name}';")
        self.write(f"{name}._canvas = {name}Canvas;")
        self.write(f"{name}._ctx = {name}Ctx;")
        self.write(f"{name}._text = '{text}';")
        self.write(f"{name}._color = '{css_color}';")
        self.write(f"{name}._font = 'Inter';")
        self.write(f"scene.add({name});")
        self.write(f"{name}.userData.font_size = {font_size};")

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
        self.write("const name = obj && obj.name ? obj.name : '(object)';")
        self.write("const numVal = typeof value === 'number' ? value : parseFloat(value);")
        self.write("if (prop === 'x' && !Number.isNaN(numVal)) {")
        self.indent()
        self.write("const prev = obj.position.x;")
        self.write("obj.position.x = numVal;")
        self.write("return { ok: true, description: `${name}.x`, undo: () => { obj.position.x = prev; }, redo: () => { obj.position.x = numVal; } };")
        self.dedent()
        self.write("}")
        self.write("if (prop === 'y' && !Number.isNaN(numVal)) {")
        self.indent()
        self.write("const prev = obj.position.y;")
        self.write("obj.position.y = numVal;")
        self.write("return { ok: true, description: `${name}.y`, undo: () => { obj.position.y = prev; }, redo: () => { obj.position.y = numVal; } };")
        self.dedent()
        self.write("}")
        self.write("if (prop === 'z' && !Number.isNaN(numVal)) {")
        self.indent()
        self.write("const prev = obj.position.z;")
        self.write("obj.position.z = numVal;")
        self.write("return { ok: true, description: `${name}.z`, undo: () => { obj.position.z = prev; }, redo: () => { obj.position.z = numVal; } };")
        self.dedent()
        self.write("}")
        self.write("if (prop === 'visible') {")
        self.indent()
        self.write("const prev = obj.visible;")
        self.write("const next = value === true || value === 'true';")
        self.write("obj.visible = next;")
        self.write("return { ok: true, description: `${name}.visible`, undo: () => { obj.visible = prev; }, redo: () => { obj.visible = next; } };")
        self.dedent()
        self.write("}")
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
        self.write("const result = handler({ object: obj, tokens, raw: tokens.join(' '), numbers: coerceNumbers(tokens) });")
        self.write("if (result && typeof result === 'object' && typeof result.undo === 'function') {")
        self.indent()
        self.write("return { ok: true, undo: result.undo, redo: typeof result.redo === 'function' ? result.redo : null, description: result.description || `${obj.name || '(object)'}.${prop}` };")
        self.dedent()
        self.write("}")
        self.write("return { ok: true, description: `${obj.name || '(object)'}.${prop}` };")
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
        self.write("const target = ctx.object;")
        self.write("if (!target) throw new Error('No object to color');")
        self.write("const val = ctx.raw && ctx.raw.trim() ? ctx.raw.trim() : '#ffffff';")
        self.write("const description = `${target.name || '(object)'}.color`;")
        self.write("if (target._ctx) {")
        self.indent()
        self.write("const prev = target._color;")
        self.write("const apply = (color) => {")
        self.indent()
        self.write("if (color === undefined) delete target._color; else target._color = color;")
        self.write("redrawTextSprite(target);")
        self.dedent()
        self.write("};")
        self.write("apply(val);")
        self.write("return { description, undo: () => apply(prev), redo: () => apply(val) };")
        self.dedent()
        self.write("} else if (target.material && target.material.color) {")
        self.indent()
        self.write("const prev = target.material.color.getHex();")
        self.write("target.material.color.set(val);")
        self.write("return { description, undo: () => { if (target.material && target.material.color) target.material.color.setHex(prev); }, redo: () => { if (target.material && target.material.color) target.material.color.set(val); } };")
        self.dedent()
        self.write("} else { throw new Error('Color not supported for this object'); }")
        self.dedent()
        self.write("};")

        self.write("CAPABILITY_RUNTIME['font_size'] = function(ctx) {")
        self.indent()
        self.write("const target = ctx.object;")
        self.write("if (!target || !target._ctx) throw new Error('Only text sprites support font_size');")
        self.write("const n = parseFloat(ctx.tokens[0]);")
        self.write("if (Number.isNaN(n)) throw new Error('Provide a numeric font size');")
        self.write("const prev = target.userData.font_size;")
        self.write("const description = `${target.name || '(object)'}.font_size`;")
        self.write("const apply = (size) => {")
        self.indent()
        self.write("if (size === undefined) delete target.userData.font_size; else target.userData.font_size = size;")
        self.write("redrawTextSprite(target);")
        self.dedent()
        self.write("};")
        self.write("apply(n);")
        self.write("return { description, undo: () => apply(prev), redo: () => apply(n) };")
        self.dedent()
        self.write("};")

        self.write("CAPABILITY_RUNTIME['font'] = function(ctx) {")
        self.indent()
        self.write("const target = ctx.object;")
        self.write("if (!target || !target._ctx) throw new Error('Only text sprites support font');")
        self.write("if (!ctx.raw || !ctx.raw.trim()) throw new Error('Provide a font family name');")
        self.write("const prev = target._font;")
        self.write("const description = `${target.name || '(object)'}.font`;")
        self.write("const apply = (fontName) => {")
        self.indent()
        self.write("if (fontName === undefined) delete target._font; else target._font = fontName;")
        self.write("redrawTextSprite(target);")
        self.dedent()
        self.write("};")
        self.write("const nextFont = ctx.raw.trim();")
        self.write("apply(nextFont);")
        self.write("return { description, undo: () => apply(prev), redo: () => apply(nextFont) };")
        self.dedent()
        self.write("};")

        self.write("CAPABILITY_RUNTIME['text'] = function(ctx) {")
        self.indent()
        self.write("const target = ctx.object;")
        self.write("if (!target || !target._ctx) throw new Error('Only text sprites support text updates');")
        self.write("const prev = target._text;")
        self.write("const description = `${target.name || '(object)'}.text`;")
        self.write("const apply = (textValue) => { target._text = textValue; redrawTextSprite(target, textValue); };")
        self.write("apply(ctx.raw);")
        self.write("return { description, undo: () => apply(prev), redo: () => apply(ctx.raw) };")
        self.dedent()
        self.write("};")

        self.write("CAPABILITY_RUNTIME['scale'] = function(ctx) {")
        self.indent()
        self.write("const target = ctx.object;")
        self.write("if (!target || !target.scale) throw new Error('Scale not supported');")
        self.write("const nums = ctx.numbers;")
        self.write("if (!nums.length) throw new Error('Provide numeric scale values');")
        self.write("const prev = { x: target.scale.x, y: target.scale.y, z: target.scale.z };")
        self.write("const description = `${target.name || '(object)'}.scale`;")
        self.write("const apply = (vals) => { if (target.scale) target.scale.set(vals.x, vals.y, vals.z); };")
        self.write("const next = nums.length === 1 ? { x: nums[0], y: nums[0], z: nums[0] } : { x: nums[0], y: nums[1] ?? nums[0], z: nums[2] ?? nums[0] };")
        self.write("apply(next);")
        self.write("return { description, undo: () => apply(prev), redo: () => apply(next) };")
        self.dedent()
        self.write("};")

        self.write("CAPABILITY_RUNTIME['spin'] = function(ctx) {")
        self.indent()
        self.write("const target = ctx.object;")
        self.write("if (!target) throw new Error('No object to spin');")
        self.write("const prevState = capabilityState.spin.get(target);")
        self.write("const prevSnapshot = prevState ? { x: prevState.x, y: prevState.y, z: prevState.z } : null;")
        self.write("const prevUserData = Array.isArray(target.userData._spin) ? target.userData._spin.slice() : null;")
        self.write("const description = `${target.name || '(object)'}.spin`;")
        self.write("const restorePrev = () => {")
        self.indent()
        self.write("if (prevSnapshot) {")
        self.indent()
        self.write("capabilityState.spin.set(target, { x: prevSnapshot.x, y: prevSnapshot.y, z: prevSnapshot.z });")
        self.write("if (prevUserData) target.userData._spin = prevUserData.slice(); else delete target.userData._spin;")
        self.dedent()
        self.write("} else {")
        self.indent()
        self.write("capabilityState.spin.delete(target);")
        self.write("delete target.userData._spin;")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("};")
        self.write("const raw = (ctx.raw || '').trim();")
        self.write("const applyOff = () => { capabilityState.spin.delete(target); delete target.userData._spin; };")
        self.write("if (!raw || raw === 'off') {")
        self.indent()
        self.write("const hadPrev = !!prevSnapshot || !!prevUserData;")
        self.write("applyOff();")
        self.write("if (!hadPrev) return { description };")
        self.write("return { description, undo: restorePrev, redo: applyOff };")
        self.dedent()
        self.write("}")
        self.write("const nums = ctx.numbers;")
        self.write("if (!nums.length) throw new Error('Provide rotation speed(s)');")
        self.write("const speeds = [nums[0] || 0, nums[1] ?? nums[0] ?? 0, nums[2] ?? 0].map(v => v * Math.PI / 180);")
        self.write("const applySpin = () => { capabilityState.spin.set(target, { x: speeds[0], y: speeds[1], z: speeds[2] }); target.userData._spin = speeds.slice(); };")
        self.write("if (speeds.every(v => v === 0)) {")
        self.indent()
        self.write("const hadPrev = !!prevSnapshot || !!prevUserData;")
        self.write("applyOff();")
        self.write("if (!hadPrev) return { description };")
        self.write("return { description, undo: restorePrev, redo: applyOff };")
        self.dedent()
        self.write("}")
        self.write("applySpin();")
        self.write("return { description, undo: restorePrev, redo: applySpin };")
        self.dedent()
        self.write("};")

        self.write("CAPABILITY_RUNTIME['bounce'] = function(ctx) {")
        self.indent()
        self.write("const target = ctx.object;")
        self.write("if (!target) throw new Error('No object to bounce');")
        self.write("const prevState = capabilityState.bounce.get(target);")
        self.write("const prevSnapshot = prevState ? { amplitude: prevState.amplitude, frequency: prevState.frequency, base: prevState.base, elapsed: prevState.elapsed } : null;")
        self.write("const prevUserData = target.userData._bounce ? { amplitude: target.userData._bounce.amplitude, freq: target.userData._bounce.freq } : null;")
        self.write("const description = `${target.name || '(object)'}.bounce`;")
        self.write("const restorePrev = () => {")
        self.indent()
        self.write("if (prevSnapshot) {")
        self.indent()
        self.write("capabilityState.bounce.set(target, { amplitude: prevSnapshot.amplitude, frequency: prevSnapshot.frequency, base: prevSnapshot.base, elapsed: prevSnapshot.elapsed || 0 });")
        self.write("if (prevUserData) target.userData._bounce = { amplitude: prevUserData.amplitude, freq: prevUserData.freq }; else delete target.userData._bounce;")
        self.dedent()
        self.write("} else {")
        self.indent()
        self.write("capabilityState.bounce.delete(target);")
        self.write("delete target.userData._bounce;")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("};")
        self.write("const raw = (ctx.raw || '').trim();")
        self.write("const applyOff = () => { capabilityState.bounce.delete(target); delete target.userData._bounce; };")
        self.write("if (!raw || raw === 'off') {")
        self.indent()
        self.write("const hadPrev = !!prevSnapshot || !!prevUserData;")
        self.write("applyOff();")
        self.write("if (!hadPrev) return { description };")
        self.write("return { description, undo: restorePrev, redo: applyOff };")
        self.dedent()
        self.write("}")
        self.write("const nums = ctx.numbers;")
        self.write("if (!nums.length) throw new Error('Provide amplitude and optional frequency');")
        self.write("const amplitude = nums[0];")
        self.write("const freq = nums[1] || 1;")
        self.write("if (amplitude === 0) {")
        self.indent()
        self.write("const hadPrev = !!prevSnapshot || !!prevUserData;")
        self.write("applyOff();")
        self.write("if (!hadPrev) return { description };")
        self.write("return { description, undo: restorePrev, redo: applyOff };")
        self.dedent()
        self.write("}")
        self.write("const applyBounce = () => { capabilityState.bounce.set(target, { amplitude, frequency: freq * Math.PI * 2, base: target.position.y, elapsed: 0 }); target.userData._bounce = { amplitude, freq }; };")
        self.write("applyBounce();")
        self.write("return { description, undo: restorePrev, redo: applyBounce };")
        self.dedent()
        self.write("};")

        self.write("CAPABILITY_RUNTIME['pulse'] = function(ctx) {")
        self.indent()
        self.write("const target = ctx.object;")
        self.write("if (!target || !target.scale) throw new Error('Pulse requires scale support');")
        self.write("const prevState = capabilityState.pulse.get(target);")
        self.write("const prevSnapshot = prevState ? {")
        self.indent()
        self.write("amplitude: prevState.amplitude,")
        self.write("frequency: prevState.frequency,")
        self.write("elapsed: prevState.elapsed || 0,")
        self.write("base: prevState.base ? { x: prevState.base.x, y: prevState.base.y, z: prevState.base.z } : null")
        self.dedent()
        self.write("} : null;")
        self.write("const prevUserData = target.userData._pulse ? { amplitude: target.userData._pulse.amplitude, freq: target.userData._pulse.freq } : null;")
        self.write("const description = `${target.name || '(object)'}.pulse`;")
        self.write("const restorePrev = () => {")
        self.indent()
        self.write("if (prevSnapshot) {")
        self.indent()
        self.write("capabilityState.pulse.set(target, {")
        self.indent()
        self.write("amplitude: prevSnapshot.amplitude,")
        self.write("frequency: prevSnapshot.frequency,")
        self.write("elapsed: prevSnapshot.elapsed || 0,")
        self.write("base: prevSnapshot.base ? { x: prevSnapshot.base.x, y: prevSnapshot.base.y, z: prevSnapshot.base.z } : null")
        self.dedent()
        self.write("});")
        self.write("if (prevSnapshot.base && target.scale) target.scale.set(prevSnapshot.base.x, prevSnapshot.base.y, prevSnapshot.base.z);")
        self.write("if (prevUserData) target.userData._pulse = { amplitude: prevUserData.amplitude, freq: prevUserData.freq }; else delete target.userData._pulse;")
        self.dedent()
        self.write("} else {")
        self.indent()
        self.write("capabilityState.pulse.delete(target);")
        self.write("delete target.userData._pulse;")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("};")
        self.write("const raw = (ctx.raw || '').trim();")
        self.write("const clearPulse = () => {")
        self.indent()
        self.write("const active = capabilityState.pulse.get(target);")
        self.write("if (active && active.base && target.scale) target.scale.set(active.base.x, active.base.y, active.base.z);")
        self.write("capabilityState.pulse.delete(target);")
        self.write("delete target.userData._pulse;")
        self.dedent()
        self.write("};")
        self.write("if (!raw || raw === 'off') {")
        self.indent()
        self.write("const hadPrev = !!prevSnapshot || !!prevUserData;")
        self.write("clearPulse();")
        self.write("if (!hadPrev) return { description };")
        self.write("return { description, undo: restorePrev, redo: clearPulse };")
        self.dedent()
        self.write("}")
        self.write("const nums = ctx.numbers;")
        self.write("if (!nums.length) throw new Error('Provide amplitude (scale delta) and optional frequency');")
        self.write("const amplitude = nums[0];")
        self.write("const freq = nums[1] || 1;")
        self.write("if (amplitude === 0) {")
        self.indent()
        self.write("const hadPrev = !!prevSnapshot || !!prevUserData;")
        self.write("clearPulse();")
        self.write("if (!hadPrev) return { description };")
        self.write("return { description, undo: restorePrev, redo: clearPulse };")
        self.dedent()
        self.write("}")
        self.write("const applyPulse = () => {")
        self.indent()
        self.write("console.log('Applying pulse to', target.name, 'type:', target.type, 'scale:', target.scale.x, target.scale.y, target.scale.z);")
        self.write("capabilityState.pulse.set(target, { amplitude, frequency: freq * Math.PI * 2, elapsed: 0, base: { x: target.scale.x, y: target.scale.y, z: target.scale.z } });")
        self.write("target.userData._pulse = { amplitude, freq };")
        self.dedent()
        self.write("};")
        self.write("applyPulse();")
        self.write("return { description, undo: restorePrev, redo: applyPulse };")
        self.dedent()
        self.write("};")

        self.write("CAPABILITY_RUNTIME['orbit'] = function(ctx) {")
        self.indent()
        self.write("const target = ctx.object;")
        self.write("if (!target) throw new Error('No object to orbit');")
        self.write("const prevState = capabilityState.orbit.get(target);")
        self.write("const prevSnapshot = prevState ? {")
        self.indent()
        self.write("center: prevState.center ? { x: prevState.center.x, z: prevState.center.z } : null,")
        self.write("radius: prevState.radius,")
        self.write("speed: prevState.speed,")
        self.write("angle: prevState.angle || 0,")
        self.write("height: prevState.height")
        self.dedent()
        self.write("} : null;")
        self.write("const prevUserData = target.userData._orbit ? {")
        self.indent()
        self.write("radius: target.userData._orbit.radius,")
        self.write("speed: target.userData._orbit.speed,")
        self.write("height: target.userData._orbit.height,")
        self.write("centerX: target.userData._orbit.centerX,")
        self.write("centerZ: target.userData._orbit.centerZ")
        self.dedent()
        self.write("} : null;")
        self.write("const description = `${target.name || '(object)'}.orbit`;")
        self.write("const restorePrev = () => {")
        self.indent()
        self.write("if (prevSnapshot) {")
        self.indent()
        self.write("const center = prevSnapshot.center ? { x: prevSnapshot.center.x, z: prevSnapshot.center.z } : { x: target.position.x, z: target.position.z };")
        self.write("capabilityState.orbit.set(target, { center, radius: prevSnapshot.radius, speed: prevSnapshot.speed, angle: prevSnapshot.angle || 0, height: prevSnapshot.height });")
        self.write("if (prevUserData) {")
        self.indent()
        self.write("target.userData._orbit = { radius: prevUserData.radius, speed: prevUserData.speed, height: prevUserData.height, centerX: prevUserData.centerX, centerZ: prevUserData.centerZ };")
        self.dedent()
        self.write("} else delete target.userData._orbit;")
        self.dedent()
        self.write("} else {")
        self.indent()
        self.write("capabilityState.orbit.delete(target);")
        self.write("delete target.userData._orbit;")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("};")
        self.write("const raw = (ctx.raw || '').trim();")
        self.write("const clearOrbit = () => { capabilityState.orbit.delete(target); delete target.userData._orbit; };")
        self.write("if (!raw || raw === 'off') {")
        self.indent()
        self.write("const hadPrev = !!prevSnapshot || !!prevUserData;")
        self.write("clearOrbit();")
        self.write("if (!hadPrev) return { description };")
        self.write("return { description, undo: restorePrev, redo: clearOrbit };")
        self.dedent()
        self.write("}")
        self.write("const nums = ctx.numbers;")
        self.write("if (!nums.length) throw new Error('Provide radius and optional speed/height');")
        self.write("const radius = nums[0];")
        self.write("if (radius <= 0) throw new Error('Radius must be positive');")
        self.write("const speedDeg = nums[1] || 30;")
        self.write("const height = nums[2];")
        self.write("const center = { x: target.position.x, z: target.position.z };")
        self.write("const applyOrbit = () => {")
        self.indent()
        self.write("capabilityState.orbit.set(target, {")
        self.indent()
        self.write("center,")
        self.write("radius,")
        self.write("speed: speedDeg * Math.PI / 180,")
        self.write("angle: 0,")
        self.write("height: Number.isFinite(height) ? height : target.position.y")
        self.dedent()
        self.write("});")
        self.write("target.userData._orbit = { radius, speed: speedDeg, height: Number.isFinite(height) ? height : target.position.y, centerX: center.x, centerZ: center.z };")
        self.dedent()
        self.write("};")
        self.write("applyOrbit();")
        self.write("return { description, undo: restorePrev, redo: applyOrbit };")
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

        # Edit mode: move selected object with arrow keys
        self.write_comment("Edit mode: move selected object")
        self.write("if (window.editMode && window.selectedObject) {")
        self.indent()
        self.write("const editSpeed = 0.2;")
        self.write("const anyMove = arrowState.left || arrowState.right || arrowState.up || arrowState.down || arrowState.rise || arrowState.fall;")
        self.write("if (arrowState.left) window.selectedObject.position.x -= editSpeed;")
        self.write("if (arrowState.right) window.selectedObject.position.x += editSpeed;")
        self.write("if (arrowState.up) window.selectedObject.position.z -= editSpeed;")
        self.write("if (arrowState.down) window.selectedObject.position.z += editSpeed;")
        self.write("if (arrowState.rise) window.selectedObject.position.y += editSpeed;")
        self.write("if (arrowState.fall) window.selectedObject.position.y -= editSpeed;")
        self.write_comment("Broadcast move to Twin (throttled)")
        self.write("if (anyMove && typeof twinBroadcastMove === 'function') {")
        self.indent()
        self.write("twinBroadcastMove(window.selectedObject.name, window.selectedObject.position.x, window.selectedObject.position.y, window.selectedObject.position.z);")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")
        self.write_blank()

        # Player object movement with arrow keys
        if self.player_objects:
            self.write_comment("Player movement (arrows=XZ, ./=Y) - only when not in edit mode")
            self.write("if (!editMode && !window.consoleVisible && !consoleVisible) {")
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
        self.write("if (!window.consoleVisible && !consoleVisible) {")
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

        # Physics update (gravity, click-to-move) - only if adapter exists
        self.write_comment("Physics update (gravity, click-to-move)")
        self.write("if (typeof adapter !== 'undefined' && adapter && adapter.update) adapter.update(delta);")
        self.write_blank()

        self.write("controls.update();")
        self.write("renderer.render(scene, camera);")
        self.dedent()
        self.write("}")
        self.write_blank()

        # Initialize capability states for objects defined in .rosh file
        self.write_comment("Initialize capability states from userData")
        self.write("scene.traverse(obj => {")
        self.indent()
        self.write("if (!obj.userData) return;")
        self.write("if (Array.isArray(obj.userData._spin) && obj.userData._spin.length >= 3) {")
        self.indent()
        self.write("const s = obj.userData._spin;")
        self.write("capabilityState.spin.set(obj, { x: s[0], y: s[1], z: s[2] });")
        self.dedent()
        self.write("}")
        self.write("if (Array.isArray(obj.userData._bounce) && obj.userData._bounce.length >= 2) {")
        self.indent()
        self.write("const b = obj.userData._bounce;")
        self.write("capabilityState.bounce.set(obj, { amplitude: b[0], frequency: b[1] * Math.PI * 2, baseY: obj.position.y, phase: 0 });")
        self.dedent()
        self.write("}")
        self.write("if (Array.isArray(obj.userData._pulse) && obj.userData._pulse.length >= 2) {")
        self.indent()
        self.write("const p = obj.userData._pulse;")
        self.write("capabilityState.pulse.set(obj, { amount: p[0], frequency: p[1] * Math.PI * 2, baseScale: obj.scale.x, phase: 0 });")
        self.dedent()
        self.write("}")
        self.write("if (Array.isArray(obj.userData._orbit) && obj.userData._orbit.length >= 3) {")
        self.indent()
        self.write("const o = obj.userData._orbit;")
        self.write("capabilityState.orbit.set(obj, { center: new THREE.Vector3(0, obj.position.y, 0), radius: o[0], speed: o[1] * Math.PI / 180, angle: 0, height: o[2] || obj.position.y });")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("});")
        self.write_blank()

        # Emit KNOWN_OBJECTS early so model loading can use it
        self._emit_known_objects()
        self.write_blank()

        # Load models for objects with known types
        self.write("// Load 3D models for pre-placed objects with known types")
        self.write("scene.traverse(obj => {")
        self.indent()
        self.write("if (obj.userData && obj.userData._needsModelLoad && obj.userData._type) {")
        self.indent()
        self.write("const typeName = obj.userData._type;")
        self.write("const preset = KNOWN_OBJECTS[typeName];")
        self.write("if (preset && preset.model && _config.useModels) {")
        self.indent()
        self.write("const pos = obj.position.clone();")
        self.write("const size = obj.userData.size || 1;")
        self.write("const spin = obj.userData._spin;")
        self.write("const bounce = obj.userData._bounce;")
        self.write("const pulse = obj.userData._pulse;")
        self.write("const orbit = obj.userData._orbit;")
        self.write("const objScene = obj.userData._scene;")
        self.write("const objName = obj.name;")
        self.write("const objUuid = obj.userData._rosh_uuid;")
        self.write("gltfLoader.load(preset.model, (gltf) => {")
        self.indent()
        self.write("const model = gltf.scene;")
        self.write("model.name = objName;")
        self.write("model.userData._type = typeName;")
        self.write("model.userData._rosh_kind = 'model';")
        self.write("model.userData._rosh_uuid = objUuid;  // Copy UUID for edit mode selection")
        self.write("if (objScene) model.userData._scene = objScene;")
        self.write("if (spin) model.userData._spin = spin;")
        self.write("if (bounce) model.userData._bounce = bounce;")
        self.write("if (pulse) model.userData._pulse = pulse;")
        self.write("if (orbit) model.userData._orbit = orbit;")
        self.write("if (preset.credit) model.userData._credit = preset.credit;")
        self.write("const box = new THREE.Box3().setFromObject(model);")
        self.write("const modelSize = box.getSize(new THREE.Vector3());")
        self.write("const maxDim = Math.max(modelSize.x, modelSize.y, modelSize.z);")
        self.write("const normalizeScale = 1 / maxDim;")
        self.write("const gs = _config.modelScale || 2;")
        self.write("model.scale.set(normalizeScale * size * gs, normalizeScale * size * gs, normalizeScale * size * gs);")
        self.write("// Center the model based on its bounding box (fixes models with offset origins)")
        self.write("const scaledBox = new THREE.Box3().setFromObject(model);")
        self.write("const center = scaledBox.getCenter(new THREE.Vector3());")
        self.write("model.position.set(pos.x - center.x, pos.y - center.y, pos.z - center.z);")
        self.write("scene.remove(obj);")
        self.write("scene.add(model);")
        self.write("// Transfer capability states from old placeholder to loaded model")
        self.write("if (capabilityState.spin.has(obj)) { capabilityState.spin.set(model, capabilityState.spin.get(obj)); capabilityState.spin.delete(obj); }")
        self.write("if (capabilityState.bounce.has(obj)) { capabilityState.bounce.set(model, capabilityState.bounce.get(obj)); capabilityState.bounce.delete(obj); }")
        self.write("if (capabilityState.pulse.has(obj)) { capabilityState.pulse.set(model, capabilityState.pulse.get(obj)); capabilityState.pulse.delete(obj); }")
        self.write("if (capabilityState.orbit.has(obj)) { const s = capabilityState.orbit.get(obj); s.center = model.position.clone(); capabilityState.orbit.set(model, s); capabilityState.orbit.delete(obj); }")
        self.write("// Update ALL registries so edit mode and console commands work with loaded models")
        self.write("const oldObj = gameObjects[objName];")
        self.write("gameObjects[objName] = model;")
        self.write("window._objects[objName] = model;")
        self.write("if (typeof adapter !== 'undefined' && adapter.registerObject) adapter.registerObject(objName, model);")
        self.write("// If the old placeholder was selected, update selection to the new model")
        self.write("if (window.selectedObject === oldObj) {")
        self.indent()
        self.write("window.selectedObject = model;")
        self.dedent()
        self.write("}")
        self.write("if (objScene && objScene !== currentScene) model.visible = false;")
        self.dedent()
        self.write("}, undefined, (err) => console.error('Model load error:', objName, err));")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("});")
        self.write_blank()

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

    def _get_shared_runtime_path(self) -> Path:
        """Get path to shared runtime files."""
        # Path: threejs.py -> emitters -> rosh -> src -> rosh-lang
        rosh_lang_dir = Path(__file__).parent.parent.parent.parent
        static_dir = rosh_lang_dir / 'static'
        return static_dir

    def _emit_shared_runtime_console(self):
        """Emit REPL console using shared runtime files.

        This is the new architecture that uses external JS files for the REPL,
        making it easier to maintain parity across emitters.
        """
        self.write_comment("=" * 50)
        self.write_comment("ROSH CONSOLE (Shared Runtime v0.1.0)")
        self.write_comment("=" * 50)
        self.write_blank()

        static_dir = self._get_shared_runtime_path()

        # Read and emit the shared runtime
        runtime_file = static_dir / 'rosh-runtime.js'
        if runtime_file.exists():
            self.write_comment("Rosh Runtime - Shared REPL")
            runtime_code = runtime_file.read_text()
            # Write as-is (it's already valid JS)
            for line in runtime_code.split('\n'):
                self.write(line)
            self.write_blank()
        else:
            self.write_comment(f"WARNING: rosh-runtime.js not found at {runtime_file}")
            self.write_blank()

        # Read and emit the Three.js adapter
        adapter_file = static_dir / 'rosh-adapter-threejs.js'
        if adapter_file.exists():
            self.write_comment("Three.js Adapter")
            adapter_code = adapter_file.read_text()
            for line in adapter_code.split('\n'):
                self.write(line)
            self.write_blank()
        else:
            self.write_comment(f"WARNING: rosh-adapter-threejs.js not found at {adapter_file}")
            self.write_blank()

        # Emit KNOWN_OBJECTS for the adapter
        self._emit_known_objects()

        # Initialize the adapter with the scene
        self.write_comment("Initialize Rosh Runtime with Three.js adapter")
        self.write("const roshAdapter = createThreeJSAdapter(scene, camera, renderer, {")
        self.indent()
        self.write("knownObjects: KNOWN_OBJECTS,")
        # Use initial_scene from meta block, fallback to 'default'
        initial_scene = self.ir.metadata.initial_scene or 'default'
        self.write(f"defaultScene: '{initial_scene}'")
        self.dedent()
        self.write("});")
        self.write_blank()

        # Wrap adapter.setProperty to route capability properties through the capability system
        self.write("// Wrap setProperty to handle capabilities (pulse, orbit, spin, bounce)")
        self.write("const originalSetProperty = roshAdapter.setProperty.bind(roshAdapter);")
        self.write("roshAdapter.setProperty = function(objName, prop, value) {")
        self.indent()
        self.write("const capabilityProps = ['pulse', 'orbit', 'spin', 'bounce'];")
        self.write("if (capabilityProps.includes(prop)) {")
        self.indent()
        self.write("// Route through capability system")
        self.write("const obj = gameObjects[objName] || scene.getObjectByName(objName);")
        self.write("if (obj && typeof applyCapabilityBridge === 'function') {")
        self.indent()
        self.write("// Split value into tokens array as expected by capability handlers")
        self.write("const tokens = String(value).trim().split(/\\s+/);")
        self.write("const capResult = applyCapabilityBridge(obj, prop, tokens);")
        self.write("return { success: capResult && capResult.ok !== false };")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")
        self.write("// Fall through to original for non-capability properties")
        self.write("originalSetProperty(objName, prop, value);")
        self.dedent()
        self.write("};")
        self.write_blank()

        # Register existing objects with the adapter
        self.write("// Register pre-defined objects with the adapter")
        for obj in self.ir.objects:
            self.write(f"if (typeof {obj.name} !== 'undefined') roshAdapter.registerObject('{obj.name}', {obj.name});")
        self.write_blank()

        # Initialize the runtime
        self.write("RoshRuntime.init(roshAdapter);")
        self.write_blank()

        # Initialize RoshNetwork for multiplayer (uses shared rosh-network.js)
        self.write("// Initialize RoshNetwork for multiplayer")
        self.write("if (typeof RoshNetwork !== 'undefined') {")
        self.indent()
        self.write("RoshNetwork.init({")
        self.indent()
        self.write("log: function(msg, cls) { RoshRuntime.log && RoshRuntime.log(msg, cls); },")
        self.write("adapter: roshAdapter")
        self.dedent()
        self.write("});")
        self.dedent()
        self.write("}")
        self.write_blank()

        # Alias for animation loop physics update (var hoists to global scope)
        self.write("// Alias for physics update in animation loop")
        self.write("var adapter = roshAdapter;")
        self.write_blank()

    def _emit_repl_console(self):
        """Emit in-game REPL console."""
        # Use shared runtime if enabled
        if self.use_shared_runtime:
            self._emit_shared_runtime_console()
            return

        # Legacy inline REPL code below
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
        self.write("let currentSelection = [], currentSelectionType = null;")  # For get all
        self.write("const cmdHistory = []; let historyIdx = -1;")
        self.write("const undoStack = [];")
        self.write("const redoStack = [];")
        self.write("let undoGroup = 0;")  # Group ID for bulk undo
        self.write("let lastUserCommand = null;")  # For :repeat
        self.write("let bulkCreateMode = false;")  # Suppress individual logs in bulk mode
        self.write("let bulkCreateCount = 0;")  # Count items created in bulk mode
        self.write("const BULK_LOG_LIMIT = 10;")  # Show first N items in bulk mode
        # Project Twin - Using shared RoshNetwork module
        self.write("// Project Twin networking via shared RoshNetwork module")
        self.write_blank()

        self.write("function log(msg, cls='') {")
        self.indent()
        self.write("const div = document.createElement('div'); div.className = cls;")
        self.write("div.textContent = msg; output.appendChild(div); output.scrollTop = output.scrollHeight;")
        self.dedent()
        self.write("}")
        self.write_blank()

        # Project Twin - Shared lookup tables for semantic values
        self.write_comment("Shared lookup tables for Project Twin (semantic -> numeric)")
        self.write("const TWIN_COLORS = {red:0xff0000, green:0x00ff00, blue:0x0000ff, yellow:0xffff00, cyan:0x00ffff, magenta:0xff00ff, white:0xffffff, black:0x111111, orange:0xff8800, purple:0x8800ff, pink:0xff88ff, gray:0x888888, grey:0x888888, gold:0xffd700, silver:0xc0c0c0, brown:0x8b4513};")
        self.write("const TWIN_SIZES = {tiny:0.25, small:0.5, medium:1, big:2, large:2, huge:4};")
        self.write_blank()

        # Project Twin - Helper to create objects from shared world
        self.write("function twinCreateObject(id, data, announce = true) {")
        self.indent()
        self.write_comment("Simple semantic lookup - no format conversion")
        self.write("const color = TWIN_COLORS[data.color] || 0x888888;  // Default gray")
        self.write("const size = TWIN_SIZES[data.size] || (typeof data.size === 'number' ? data.size : 1);  // Default medium")
        self.write_blank()
        self.write_comment("Build human-readable command description")
        self.write("const sizeWord = data.size ? data.size + ' ' : '';")
        self.write("const colorWord = data.color ? data.color + ' ' : '';")
        self.write("const typeWord = data.type || 'object';")
        self.write("const cmdDesc = 'create a ' + sizeWord + colorWord + typeWord;")
        self.write_blank()
        self.write_comment("Log clearly what was received (show in Rosh console)")
        self.write("if (announce && data.created_by) {")
        self.indent()
        self.write("log('[' + data.created_by.slice(0,6) + '] sent: ' + cmdDesc, 'cyan');")
        self.dedent()
        self.write("}")
        self.write_blank()
        self.write_comment("Log warnings for unknown values")
        self.write("if (!TWIN_COLORS[data.color] && data.color) log('  (unknown color \"' + data.color + '\", using gray)', 'dim');")
        self.write("if (!TWIN_SIZES[data.size] && data.size && typeof data.size !== 'number') log('  (unknown size \"' + data.size + '\", using medium)', 'dim');")
        self.write_blank()
        self.write("let geom, mesh;")
        self.write("const shapeType = data.type || 'cube';")
        self.write("if (shapeType === 'sphere' || shapeType === 'ball' || shapeType === 'circle') geom = new THREE.SphereGeometry(size);")
        self.write("else if (shapeType === 'cylinder') geom = new THREE.CylinderGeometry(size*0.5, size*0.5, size);")
        self.write("else geom = new THREE.BoxGeometry(size, size, size);")
        self.write("mesh = new THREE.Mesh(geom, new THREE.MeshStandardMaterial({ color: color }));")
        self.write("mesh.name = id;")
        self.write("mesh.userData._type = shapeType;")
        self.write("mesh.userData._twin = true;")
        self.write("mesh.position.set(data.x || 0, data.y || 1, data.z || 0);")
        self.write("scene.add(mesh);")
        self.write("gameObjects[id] = mesh;")
        self.dedent()
        self.write("}")
        self.write_blank()

        # Project Twin - Broadcast object creation via shared RoshNetwork
        self.write("function twinBroadcastCreate(name, type, x, y, z, color, size) {")
        self.indent()
        self.write("if (typeof RoshNetwork !== 'undefined' && RoshNetwork.isConnected()) {")
        self.indent()
        self.write("const colorStr = typeof color === 'number' ? '#' + color.toString(16).padStart(6, '0') : color;")
        self.write("RoshNetwork.broadcastCreate(name, { type, x, y, z, color: colorStr, size });")
        self.write("log('🌐 Shared: ' + name, 'ok');")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")
        self.write_blank()

        # Project Twin - Broadcast object deletion via shared RoshNetwork
        self.write("function twinBroadcastDelete(name) {")
        self.indent()
        self.write("if (typeof RoshNetwork !== 'undefined' && RoshNetwork.isConnected()) {")
        self.indent()
        self.write("RoshNetwork.broadcastDelete(name);")
        self.write("log('🌐 Shared: deleted ' + name, 'dim');")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")
        self.write_blank()

        self.write("function pushUndo(description, undoFn, redoFn) {")
        self.indent()
        self.write("if (typeof undoFn !== 'function') return;")
        self.write("undoStack.push({ description: description || 'change', undo: undoFn, redo: typeof redoFn === 'function' ? redoFn : null, group: undoGroup });")
        self.write("if (undoStack.length > 100) undoStack.shift();")
        self.write("redoStack.length = 0;")
        self.dedent()
        self.write("}")
        self.write_blank()

        self.write("function performUndo(count = 1) {")
        self.indent()
        self.write("if (!undoStack.length) { log('Nothing to undo', 'err'); return; }")
        self.write("// Undo by group: pop all entries with the same group as the most recent")
        self.write("for (let step = 0; step < count; step++) {")
        self.indent()
        self.write("if (!undoStack.length) break;")
        self.write("const targetGroup = undoStack[undoStack.length - 1].group;")
        self.write("const groupEntries = [];")
        self.write("// Collect all entries in this group (they should be contiguous at the end)")
        self.write("while (undoStack.length && undoStack[undoStack.length - 1].group === targetGroup) {")
        self.indent()
        self.write("groupEntries.push(undoStack.pop());")
        self.dedent()
        self.write("}")
        self.write("// Execute undos in reverse order (most recent first)")
        self.write("let undoCount = 0;")
        self.write("for (const entry of groupEntries) {")
        self.indent()
        self.write("try {")
        self.indent()
        self.write("entry.undo();")
        self.write("undoCount++;")
        self.write("if (entry.redo) redoStack.push(entry);")
        self.dedent()
        self.write("} catch (err) {")
        self.indent()
        self.write("log('Undo failed: ' + (err && err.message ? err.message : err), 'err');")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")
        self.write("if (undoCount > 1) log('Undo: ' + groupEntries[0].description + ' (' + undoCount + ' operations)', 'ok');")
        self.write("else if (undoCount === 1) log('Undo: ' + groupEntries[0].description, 'ok');")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")
        self.write_blank()

        self.write("function performRedo(count = 1) {")
        self.indent()
        self.write("if (!redoStack.length) { log('Nothing to redo', 'err'); return; }")
        self.write("const steps = Math.min(Math.max(1, count), redoStack.length);")
        self.write("for (let i = 0; i < steps; i++) {")
        self.indent()
        self.write("const entry = redoStack.pop();")
        self.write("if (!entry || typeof entry.redo !== 'function') continue;")
        self.write("try {")
        self.indent()
        self.write("entry.redo();")
        self.write("log('Redo: ' + entry.description, 'ok');")
        self.write("undoStack.push(entry);")
        self.dedent()
        self.write("} catch (err) {")
        self.indent()
        self.write("log('Redo failed: ' + (err && err.message ? err.message : err), 'err');")
        self.write("break;")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")
        self.write_blank()

        self.write("function describeUndoStack(limit = 5) {")
        self.indent()
        self.write("if (!undoStack.length) { log('Undo stack is empty', 'dim'); return; }")
        self.write("log('Recent undo entries:', 'cyan');")
        self.write("const entries = undoStack.slice(-limit).reverse();")
        self.write("entries.forEach((entry, idx) => log('  #' + (idx + 1) + ' ' + entry.description, 'dim'));")
        self.dedent()
        self.write("}")
        self.write_blank()

        self.write("function describeRedoStack(limit = 5) {")
        self.indent()
        self.write("if (!redoStack.length) { log('Redo stack is empty', 'dim'); return; }")
        self.write("log('Pending redo entries:', 'cyan');")
        self.write("const entries = redoStack.slice(-limit).reverse();")
        self.write("entries.forEach((entry, idx) => log('  #' + (idx + 1) + ' ' + entry.description, 'dim'));")
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

        self.write(f"log('Rosh v{__version__} | Three.js', 'cyan');")
        self.write("log('Type help for commands. Press ` to toggle console.', 'dim');")

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

        # Singularize function - convert plurals to singular form
        self.write("function singularize(word) {")
        self.indent()
        self.write("if (!word || word.length < 2) return word;")
        self.write("const w = word.toLowerCase();")
        self.write("// Handle special plural endings")
        self.write("if (w.endsWith('ies') && w.length > 3) return w.slice(0, -3) + 'y';  // berries → berry")
        self.write("if (w.endsWith('xes') || w.endsWith('shes') || w.endsWith('ches')) return w.slice(0, -2);  // boxes → box")
        self.write("if (w.endsWith('ses') || w.endsWith('zes')) return w.slice(0, -2);  // buses → bus")
        self.write("if (w.endsWith('s') && !w.endsWith('ss')) return w.slice(0, -1);  // balls → ball")
        self.write("return w;")
        self.dedent()
        self.write("}")
        self.write_blank()

        # Voice corrections table - common mishearings
        self.write("const VOICE_CORRECTIONS = {")
        self.indent()
        self.write("'enter': 'Inter', 'inter': 'Inter', 'inner': 'Inter',")
        self.write("'aerial': 'Arial', 'arial': 'Arial', 'area': 'Arial',")
        self.write("'read': 'red', 'reed': 'red',")
        self.write("'grey': 'gray',")  # Removed 'great': 'gray' - too aggressive (BUG-006)
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
        self.write("'height': 'height', 'hight': 'height',")
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
        self.write("const KNOWN_COMMANDS = ['set', 'get', 'list', 'create', 'delete', 'remove', 'reset', 'hide', 'show', 'clone', 'look', 'examine', 'inspect', 'x', 'ex', 'help', 'prompt', 'save', 'load', 'capabilities', 'camera', 'undo', 'redo', 'count', 'move', 'make', 'credits', 'clear', 'redraw', 'repeat', ':repeat', ':r', 'go', 'goto', 'scene', 'scenes', 'rooms', 'galleries', 'connect', 'disconnect', 'twin', 'sync', 'edit'];")
        # Emit SCENE_LIST for scene navigation
        if self.uses_scenes and self.scene_objects:
            scenes = list(self.scene_objects.keys())
            self.write(f"const SCENE_LIST = {scenes};")
        else:
            self.write("const SCENE_LIST = [];")
        # Known objects with preset shapes/colors - loaded from known_objects.toml
        self._emit_known_objects()
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
        self.write("// Skip fuzzy matching for keywords: all, config (they have special handlers)")
        self.write("const skipFuzzy = ['all', 'config'];")
        self.write("if ((parts[0] === 'set' || parts[0] === 'get' || parts[0] === 'look' || parts[0] === 'examine' || parts[0] === 'x' || parts[0] === 'ex' || parts[0] === 'delete' || parts[0] === 'remove' || parts[0] === 'reset' || parts[0] === 'hide' || parts[0] === 'show' || parts[0] === 'clone') && parts.length > 1 && !skipFuzzy.includes(parts[1])) {")
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

    def _emit_known_objects(self):
        """Emit KNOWN_OBJECTS constant from known_objects.toml."""
        # Only emit once (may be called from multiple places)
        if hasattr(self, '_known_objects_emitted') and self._known_objects_emitted:
            return
        self._known_objects_emitted = True

        objects = get_known_objects_3d()

        # Build JavaScript object literal
        entries = []
        for name, props in objects.items():
            shape = props.get('shape', 'box')
            color = props.get('color', 0x00ff00)
            scale_x = props.get('scaleX', 1.0)
            scale_y = props.get('scaleY', 1.0)
            scale_z = props.get('scaleZ', 1.0)
            opacity = props.get('opacity', None)
            model = props.get('model', None)
            credit = props.get('credit', None)

            # Build property list
            parts = [
                f"shape: '{shape}'",
                f"color: {color:#x}",
                f"scaleX: {scale_x}",
                f"scaleY: {scale_y}",
                f"scaleZ: {scale_z}",
            ]
            if opacity is not None:
                parts.append(f"opacity: {opacity}")
            if model is not None:
                # Add assets/ prefix for runtime loading
                parts.append(f"model: 'assets/{model}'")
            if credit is not None:
                # Escape quotes in credit string
                credit_escaped = credit.replace("'", "\\'")
                parts.append(f"credit: '{credit_escaped}'")

            entry = f"{name}: {{ {', '.join(parts)} }}"
            entries.append(entry)

        # Write as multi-line for readability
        self.write("const KNOWN_OBJECTS = {")
        self.indent()
        for entry in entries:
            self.write(f"{entry},")
        self.dedent()
        self.write("};")

    def _emit_voice_input(self):
        """Emit Web Speech API voice input with push-to-talk."""
        self.write_comment("Voice Input - Hold Ctrl+Space to speak (Chrome/Edge)")
        self.write("const voiceBtn = document.getElementById('rosh-voice');")
        self.write("let recognition = null;")
        self.write("let isListening = false;")
        self.write_blank()

        # Check for browser support and warn Safari users
        self.write("const isSafari = /^((?!chrome|android).)*safari/i.test(navigator.userAgent);")
        self.write("if (isSafari) log('[note] Voice works best in Chrome. Safari support is limited.', 'warn');")
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
        self.write("function execCommand(cmd, isUserCommand = true) {")
        self.indent()
        self.write("// Increment undo group for each user command (not internal calls)")
        self.write("if (isUserCommand) undoGroup++;")
        self.write_blank()
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
        self.write_blank()
        # Resolve "it" and "this" to current object
        self.write("// Resolve 'it' and 'this' to current object (stack top)")
        self.write("if (currentObjectName && /\\b(it|this)\\b/i.test(cmd)) {")
        self.indent()
        self.write("cmd = cmd.replace(/\\b(it|this)\\b/gi, currentObjectName);")
        self.write("log('[resolved: it/this → ' + currentObjectName + ']', 'dim');")
        self.dedent()
        self.write("}")
        self.write_blank()
        # Track last substantive user command for :repeat
        self.write("// Track last substantive command for :repeat (skip undo/redo/help/config)")
        self.write("const nonSubstantive = /^(undo|redo|help|:repeat|\\?|history)/i;")
        self.write("if (isUserCommand && !nonSubstantive.test(cmd.trim())) lastUserCommand = originalCmd;")
        self.write_blank()

        # Helper functions for deep search (used by get and set commands)
        self.write("// Deep search helpers")
        self.write("const colorHexMap = {0xff0000:'red', 0x00ff00:'green', 0x0000ff:'blue', 0xffff00:'yellow', 0x00ffff:'cyan', 0xff00ff:'magenta', 0xffffff:'white', 0x000000:'black', 0x111111:'black', 0xff8800:'orange', 0x8800ff:'purple', 0xff88ff:'pink', 0xff88cc:'pink', 0x888888:'gray', 0xffd700:'gold', 0xc0c0c0:'silver'};")
        self.write("const getColorName = (mesh) => {")
        self.indent()
        self.write("if (mesh.userData && mesh.userData._color) return mesh.userData._color.toLowerCase();")
        self.write("if (mesh.material && mesh.material.color) {")
        self.indent()
        self.write("const hex = mesh.material.color.getHex();")
        self.write("if (colorHexMap[hex]) return colorHexMap[hex];")
        self.write("const r = (hex >> 16) & 0xff, g = (hex >> 8) & 0xff, b = hex & 0xff;")
        self.write("if (r > 200 && g < 100 && b < 100) return 'red';")
        self.write("if (r < 100 && g > 200 && b < 100) return 'green';")
        self.write("if (r < 100 && g < 100 && b > 200) return 'blue';")
        self.write("if (r > 200 && g > 200 && b < 100) return 'yellow';")
        self.write("if (r < 100 && g > 200 && b > 200) return 'cyan';")
        self.write("if (r > 200 && g < 100 && b > 200) return 'magenta';")
        self.write("if (r > 200 && g > 100 && b < 100) return 'orange';")
        self.write("if (r > 100 && g < 100 && b > 200) return 'purple';")
        self.write("if (r > 200 && g > 100 && b > 150) return 'pink';")
        self.write("if (r > 220 && g > 220 && b > 220) return 'white';")
        self.write("if (r < 50 && g < 50 && b < 50) return 'black';")
        self.write("if (Math.abs(r-g) < 30 && Math.abs(g-b) < 30) return 'gray';")
        self.dedent()
        self.write("}")
        self.write("return '';")
        self.dedent()
        self.write("};")
        self.write("const getTypeName = (mesh) => {")
        self.indent()
        self.write("if (mesh.userData && mesh.userData._type) return mesh.userData._type.toLowerCase();")
        self.write("if (mesh.geometry) {")
        self.indent()
        self.write("const gt = mesh.geometry.type.toLowerCase();")
        self.write("if (gt.includes('box')) return 'cube';")
        self.write("if (gt.includes('sphere')) return 'sphere';")
        self.write("if (gt.includes('cylinder')) return 'cylinder';")
        self.write("if (gt.includes('cone')) return 'cone';")
        self.write("if (gt.includes('torus')) return 'torus';")
        self.write("if (gt.includes('plane')) return 'plane';")
        self.dedent()
        self.write("}")
        self.write("return '';")
        self.dedent()
        self.write("};")
        self.write_blank()

        # Bulk create: "create N [modifiers] type" -> loop with confirmation for >= 10
        # Last word is type name, all preceding words are modifiers (known or custom)
        # Trailing 'go'/'confirm' skips confirmation
        self.write("// Bulk create expansion: create 100 balls, create 50 angry orcs")
        self.write("const bulkCreateMatch = cmd.match(/^create\\s+(\\d+)\\s+(.+)$/i);")
        self.write("if (bulkCreateMatch) {")
        self.indent()
        self.write("const count = parseInt(bulkCreateMatch[1], 10);")
        self.write("let words = bulkCreateMatch[2].trim().split(/\\s+/);")
        # Check for trailing 'go'/'confirm'/'yes' for auto-confirmation
        self.write("// Check for trailing go/confirm for auto-execution")
        self.write("let autoConfirm = false;")
        self.write("if (words.length > 1 && ['go', 'confirm', 'yes'].includes(words[words.length - 1].toLowerCase())) {")
        self.indent()
        self.write("autoConfirm = true;")
        self.write("words = words.slice(0, -1);")
        self.dedent()
        self.write("}")
        self.write("if (words.length > 0 && count > 0) {")
        self.indent()
        # Last word is type, rest are modifiers
        self.write("let typeName = singularize(words[words.length - 1]);")
        self.write("const modifiers = words.slice(0, -1).map(w => w.toLowerCase());")
        self.write("const createCmd = 'create ' + (modifiers.length ? modifiers.join(' ') + ' ' : '') + typeName;")
        # Confirmation for >= 10 (if _config.confirm is true and no auto-confirm)
        self.write("if (count >= 10 && _config.confirm && !autoConfirm) {")
        self.indent()
        self.write("pendingOp = {")
        self.indent()
        self.write("type: 'create',")
        self.write("execute: () => {")
        self.indent()
        self.write("bulkCreateMode = true; bulkCreateCount = 0;")
        self.write("for (let i = 0; i < count; i++) execCommand(createCmd, false);")
        self.write("if (count > BULK_LOG_LIMIT) log('  ... and ' + (count - BULK_LOG_LIMIT) + ' more', 'dim');")
        self.write("bulkCreateMode = false;")
        self.write("log('Created ' + count + ' ' + typeName + '(s)', 'ok');")
        self.write("const preset = KNOWN_OBJECTS[typeName];")
        self.write("if (preset && preset.credit) log('Credit: ' + preset.credit, 'dim');")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("};")
        self.write("log('⚠ Create ' + count + ' ' + (modifiers.length ? modifiers.join(' ') + ' ' : '') + typeName + '(s)?', 'warn');")
        self.write("log(\"Type 'go' or 'confirm' to execute\", 'dim');")
        self.dedent()
        self.write("} else {")
        self.indent()
        self.write("bulkCreateMode = true; bulkCreateCount = 0;")
        self.write("for (let i = 0; i < count; i++) execCommand(createCmd, false);")
        self.write("if (count > BULK_LOG_LIMIT) log('  ... and ' + (count - BULK_LOG_LIMIT) + ' more', 'dim');")
        self.write("bulkCreateMode = false;")
        self.write("log('Created ' + count + ' ' + typeName + '(s)', 'ok');")
        self.write("const preset = KNOWN_OBJECTS[typeName];")
        self.write("if (preset && preset.credit) log('Credit: ' + preset.credit, 'dim');")
        self.dedent()
        self.write("}")
        self.write("return;")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")

        # Bulk set: "set N type property to value" -> loop over first N
        self.write("// Bulk set expansion: set 20 balls color to blue")
        self.write("const bulkSetMatch = cmd.match(/^set\\s+(\\d+)\\s+(\\w+)\\s+(\\w+)\\s+to\\s+(.+)$/i);")
        self.write("if (bulkSetMatch) {")
        self.indent()
        self.write("const count = parseInt(bulkSetMatch[1], 10);")
        self.write("let typeName = singularize(bulkSetMatch[2]);")
        self.write("const prop = bulkSetMatch[3].toLowerCase();")
        self.write("const value = bulkSetMatch[4].trim();")
        self.write("const typeObjs = [];")
        self.write("scene.traverse(o => { if (o.name === typeName || o.name.startsWith(typeName + '-') || o.userData._type === typeName) typeObjs.push(o); });")
        self.write("const targets = typeObjs.slice(0, count);")
        self.write("if (targets.length === 0) { log('No ' + typeName + ' objects found', 'err'); }")
        self.write("else {")
        self.indent()
        self.write("for (const obj of targets) execCommand('set ' + obj.name + ' ' + prop + ' to ' + value, false);")
        self.write("log('Set ' + prop + ' on ' + targets.length + ' ' + typeName + '(s)', 'ok');")
        self.dedent()
        self.write("}")
        self.write("return;")
        self.dedent()
        self.write("}")

        # Bulk get: "get N type" -> select first N of type
        self.write("// Bulk get expansion: get 5 balls")
        self.write("const bulkGetMatch = cmd.match(/^get\\s+(\\d+)\\s+(\\w+)$/i);")
        self.write("if (bulkGetMatch) {")
        self.indent()
        self.write("const count = parseInt(bulkGetMatch[1], 10);")
        self.write("let typeName = singularize(bulkGetMatch[2]);")
        self.write("const typeObjs = [];")
        self.write("scene.traverse(o => { if (o.name === typeName || o.name.startsWith(typeName + '-') || o.userData._type === typeName) typeObjs.push(o); });")
        self.write("const targets = typeObjs.slice(0, count);")
        self.write("if (targets.length === 0) { log('No ' + typeName + ' objects found', 'err'); }")
        self.write("else {")
        self.indent()
        self.write("currentSelection = targets;")  # Replace selection
        self.write("currentSelectionType = typeName;")
        self.write("log('Selected ' + targets.length + ' ' + typeName + '(s)', 'ok');")
        self.dedent()
        self.write("}")
        self.write("return;")
        self.dedent()
        self.write("}")

        self.write("const parts = cmd.trim().toLowerCase().split(/\\s+/);")
        self.write("try {")
        self.indent()

        # Handle confirmation for pending operations
        self.write("// Handle confirmation for pending operations")
        self.write("if ((parts[0] === 'go' || parts[0] === 'confirm' || parts[0] === 'yes') && pendingOp) {")
        self.indent()
        self.write("pendingOp.execute();")
        self.write("pendingOp = null;")
        self.write("return;")
        self.dedent()
        self.write("}")
        self.write("// Cancel pending op on any other command")
        self.write("if (pendingOp && parts[0] !== 'go' && parts[0] !== 'confirm' && parts[0] !== 'yes') {")
        self.indent()
        self.write("log('Cancelled pending operation', 'dim');")
        self.write("pendingOp = null;")
        self.dedent()
        self.write("}")
        self.write_blank()

        # Help - specific handlers first, then generic
        self.write("if (parts[0] === 'help' && (parts[1] === 'create' || parts[1] === 'clone')) {")
        self.indent()
        self.write("log('create - Create objects', 'cyan');")
        self.write("log('');")
        self.write("log('You can create any object:');")
        self.write("log('  create thing           - Create empty object');")
        self.write("log('  create car porsche     - Create \"porsche\" of type \"car\"');")
        self.write("log('  create big red ball    - Create with modifiers');")
        self.write("log('  clone ball             - Clone existing object');")
        self.write("log('');")
        self.write("log('Known object types (with pre-defined properties):', 'cyan');")
        self.write("const names = Object.keys(KNOWN_OBJECTS).sort();")
        self.write("const perLine = 6;")
        self.write("for (let i = 0; i < names.length; i += perLine) {")
        self.indent()
        self.write("log('  ' + names.slice(i, i + perLine).join(', '));")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")
        self.write("else if (parts[0] === 'help' && parts[1] === 'make') {")
        self.indent()
        self.write("log('make - Adjust object properties (REPL only)', 'cyan');")
        self.write("log('');")
        self.write("log('Usage:');")
        self.write("log('  make <obj> bigger    - Scale up by 1.5x');")
        self.write("log('  make <obj> smaller   - Scale down by 1.5x');")
        self.write("log('  make <obj> visible   - Show the object');")
        self.write("log('  make <obj> hidden    - Hide the object');")
        self.write("log('  make <obj> <color>   - Change color (red, blue, etc.)');")
        self.write("log('  make all <type> <modifier> - Apply to all of type');")
        self.write("log('    Example: make all orcs bigger');")
        self.write("log('');")
        self.write("log('Note: \"make\" is a REPL convenience command.', 'dim');")
        self.dedent()
        self.write("}")

        # Help for additional commands
        self.write("else if (parts[0] === 'help' && parts[1] === 'undo') {")
        self.indent()
        self.write("log('undo - Undo recent changes', 'cyan');")
        self.write("log('Usage:', 'dim');")
        self.write("log('  undo           - Undo last change');")
        self.write("log('  undo 3         - Undo last 3 changes');")
        self.write("log('  undo stack     - Show undo history');")
        self.write("log('  oops           - Same as undo');")
        self.dedent()
        self.write("}")
        self.write("else if (parts[0] === 'help' && parts[1] === 'redo') {")
        self.indent()
        self.write("log('redo - Redo undone changes', 'cyan');")
        self.write("log('Usage:', 'dim');")
        self.write("log('  redo           - Redo last undo');")
        self.write("log('  redo 3         - Redo last 3 undos');")
        self.write("log('  redo stack     - Show redo history');")
        self.dedent()
        self.write("}")
        self.write("else if (parts[0] === 'help' && parts[1] === 'list') {")
        self.indent()
        self.write("log('list - List all objects in scene', 'cyan');")
        self.write("log('Usage:', 'dim');")
        self.write("log('  list           - Show all objects');")
        self.dedent()
        self.write("}")
        self.write("else if (parts[0] === 'help' && parts[1] === 'count') {")
        self.indent()
        self.write("log('count - Count objects', 'cyan');")
        self.write("log('Usage:', 'dim');")
        self.write("log('  count          - Count all objects');")
        self.write("log('  count ball     - Count objects of type \"ball\"');")
        self.dedent()
        self.write("}")
        self.write("else if (parts[0] === 'help' && (parts[1] === 'hide' || parts[1] === 'show')) {")
        self.indent()
        self.write("log('hide/show - Toggle object visibility', 'cyan');")
        self.write("log('Usage:', 'dim');")
        self.write("log('  hide <object>  - Make object invisible');")
        self.write("log('  show <object>  - Make object visible');")
        self.dedent()
        self.write("}")
        self.write("else if (parts[0] === 'help' && parts[1] === 'prompt') {")
        self.indent()
        self.write("log('prompt - AI-assisted commands', 'cyan');")
        self.write("log('Usage:', 'dim');")
        self.write("log('  prompt create a big blue ball');")
        self.write("log('  prompt move the logo to the right');")
        self.dedent()
        self.write("}")
        self.write("else if (parts[0] === 'help' && (parts[1] === 'save' || parts[1] === 'load')) {")
        self.indent()
        self.write("log('save/load - Persist game state', 'cyan');")
        self.write("log('Usage:', 'dim');")
        self.write("log('  save <slot>    - Save to slot (1-9)');")
        self.write("log('  load <slot>    - Load from slot');")
        self.dedent()
        self.write("}")
        self.write("else if (parts[0] === 'help' && parts[1] === 'camera') {")
        self.indent()
        self.write("log('camera - Camera controls', 'cyan');")
        self.write("log('Usage:', 'dim');")
        self.write("log('  camera reset   - Reset camera to default position');")
        self.dedent()
        self.write("}")
        self.write("else if (parts[0] === 'help' && parts[1] === 'redraw') {")
        self.indent()
        self.write("log('redraw - Recreate all typed objects', 'cyan');")
        self.write("log('Usage:', 'dim');")
        self.write("log('  redraw         - Recreate objects with current config settings');")
        self.write("log('  (useful after changing config scale or config models)');")
        self.dedent()
        self.write("}")
        self.write("else if (parts[0] === 'help' && parts[1] === 'reset') {")
        self.indent()
        self.write("log('reset - Reset object to default state', 'cyan');")
        self.write("log('Usage:', 'dim');")
        self.write("log('  reset <object> - Reset position, scale, rotation');")
        self.dedent()
        self.write("}")
        self.write("else if (parts[0] === 'help' && (parts[1] === 'delete' || parts[1] === 'remove')) {")
        self.indent()
        self.write("log('delete/remove - Remove objects from scene', 'cyan');")
        self.write("log('Usage:', 'dim');")
        self.write("log('  delete <object>');")
        self.write("log('  remove <object>');")
        self.dedent()
        self.write("}")
        self.write("else if (parts[0] === 'help' && parts[1] === 'credits') {")
        self.indent()
        self.write("log('credits - Show Rosh credits', 'cyan');")
        self.dedent()
        self.write("}")
        self.write("else if (parts[0] === 'help' && parts[1] === 'move') {")
        self.indent()
        self.write("log('move - Move object to coordinates', 'cyan');")
        self.write("log('Usage:', 'dim');")
        self.write("log('  move <object> to x, y, z');")
        self.write("log('  move ball to 0, 5, 0');")
        self.dedent()
        self.write("}")
        self.write("else if (parts[0] === 'help' && (parts[1] === 'look' || parts[1] === 'examine' || parts[1] === 'inspect' || parts[1] === 'x' || parts[1] === 'ex')) {")
        self.indent()
        self.write("log('look/examine/inspect/x/ex - Inspect an object', 'cyan');")
        self.write("log('Usage:', 'dim');")
        self.write("log('  look <object>  - Show object properties');")
        self.write("log('  examine ball   - Same as look');")
        self.write("log('  x ball         - Shorthand');")
        self.write("log('  ex ball        - Shorthand');")
        self.dedent()
        self.write("}")
        self.write("else if (parts[0] === 'help' && parts[1] === 'get') {")
        self.indent()
        self.write("log('get - Get object or property value', 'cyan');")
        self.write("log('Usage:', 'dim');")
        self.write("log('  get <object>           - Select object');")
        self.write("log('  get <object> <prop>    - Get property value');")
        self.write("log('  get all <type>         - Select all of type');")
        self.write("log('  get config scale       - Get model scale setting');")
        self.dedent()
        self.write("}")
        self.write("else if (parts[0] === 'help' && parts[1] === 'set') {")
        self.indent()
        self.write("log('set - Set object properties', 'cyan');")
        self.write("log('Usage:', 'dim');")
        self.write("log('  set <object> <prop> to <value>');")
        self.write("log('  set ball color to red');")
        self.write("log('  set all ball color to blue');")
        self.write("log('  set config scale to 3   - Set model scale');")
        self.write("log('  set config models off   - Disable 3D models');")
        self.write("log('  set config floor off    - Hide floor/grid');")
        self.write("log('  set config floor green  - Solid color floor');")
        self.write("log('  set config confirm off  - Disable bulk op confirmation');")
        self.dedent()
        self.write("}")
        self.write("else if (parts[0] === 'help' && parts[1]) {")
        self.indent()
        self.write("// Generic help <object> or help <capability>")
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
        self.write("log('Commands: list, get, set, make, look/examine, create, delete/remove', 'cyan');")
        self.write("log('          reset, hide, show, clone, count, move', 'cyan');")
        self.write("log('          prompt, save, load, undo, redo, camera reset', 'cyan');")
        self.write("if (SCENE_LIST.length > 0) log('Scenes:   go <scene>, scenes - navigate between scenes', 'cyan');")
        self.write("log('Natural: make <obj> red, make <obj> big, make <obj> visible', 'dim');")
        self.write("log('Type \"help create\" to see available object types', 'dim');")
        self.dedent()
        self.write("}")
        self.write("else if (parts[0] === 'undo' && parts[1] === 'stack') {")
        self.indent()
        self.write("const count = parts[2] ? parseInt(parts[2], 10) : 5;")
        self.write("describeUndoStack(Number.isFinite(count) && count > 0 ? count : 5);")
        self.dedent()
        self.write("}")
        self.write("else if (parts[0] === 'undo') {")
        self.indent()
        self.write("const steps = parts[1] ? parseInt(parts[1], 10) : 1;")
        self.write("performUndo(Number.isFinite(steps) && steps > 0 ? steps : 1);")
        self.dedent()
        self.write("}")
        self.write("else if (parts[0] === 'redo' && parts[1] === 'stack') {")
        self.indent()
        self.write("const count = parts[2] ? parseInt(parts[2], 10) : 5;")
        self.write("describeRedoStack(Number.isFinite(count) && count > 0 ? count : 5);")
        self.dedent()
        self.write("}")
        self.write("else if (parts[0] === 'redo') {")
        self.indent()
        self.write("const steps = parts[1] ? parseInt(parts[1], 10) : 1;")
        self.write("performRedo(Number.isFinite(steps) && steps > 0 ? steps : 1);")
        self.dedent()
        self.write("}")

        # :repeat - repeat the last substantive command
        self.write("else if (parts[0] === ':repeat' || parts[0] === 'repeat' || parts[0] === ':r') {")
        self.indent()
        self.write("if (lastUserCommand) {")
        self.indent()
        self.write("log('Repeating: ' + lastUserCommand, 'dim');")
        self.write("execCommand(lastUserCommand);")
        self.dedent()
        self.write("} else {")
        self.indent()
        self.write("log('No command to repeat', 'err');")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")

        # Scene navigation - "go <scene>" or "goto <scene>" or "scene <scene>"
        self.write("else if ((parts[0] === 'go' || parts[0] === 'goto' || parts[0] === 'scene') && parts[1]) {")
        self.indent()
        self.write("const targetScene = parts.slice(1).join(' ').toLowerCase().replace(/^(to\\s+)?the\\s+/, '').replace(/\\s+room$/, '').replace(/\\s+gallery$/, '').replace(/\\s+scene$/, '');")
        self.write("if (typeof SCENE_LIST !== 'undefined' && SCENE_LIST.length > 0) {")
        self.indent()
        self.write("// Try exact match first")
        self.write("const exactMatch = SCENE_LIST.find(s => s.toLowerCase() === targetScene);")
        self.write("if (exactMatch) {")
        self.indent()
        self.write("pendingScene = null;")
        self.write("if (typeof transitionToScene === 'function') { transitionToScene(exactMatch); } else { currentScene = exactMatch; updateSceneVisibility(); }")
        self.write("log('Entered: ' + exactMatch, 'ok');")
        self.dedent()
        self.write("} else {")
        self.indent()
        self.write("// Try fuzzy match")
        self.write("const fuzzyMatch = SCENE_LIST.find(s => s.toLowerCase().includes(targetScene) || targetScene.includes(s.toLowerCase()));")
        self.write("if (fuzzyMatch) {")
        self.indent()
        self.write("pendingScene = fuzzyMatch;")
        self.write("log('Did you mean: ' + fuzzyMatch + '?', 'warn');")
        self.write("log('Type go to confirm', 'dim');")
        self.dedent()
        self.write("} else {")
        self.indent()
        self.write("log('Scene not found: ' + targetScene, 'err');")
        self.write("log('Available: ' + SCENE_LIST.join(', '), 'dim');")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("} else {")
        self.indent()
        self.write("log('No scenes defined in this demo', 'err');")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")

        # "go" without arguments - confirm pending or show help
        self.write("else if (parts[0] === 'go' || parts[0] === 'goto' || parts[0] === 'scene') {")
        self.indent()
        self.write("if (pendingScene) {")
        self.indent()
        self.write("const target = pendingScene;")
        self.write("pendingScene = null;")
        self.write("if (typeof transitionToScene === 'function') { transitionToScene(target); } else { currentScene = target; updateSceneVisibility(); }")
        self.write("log('Entered: ' + target, 'ok');")
        self.dedent()
        self.write("} else if (pendingAction) {")
        self.indent()
        self.write("pendingAction(); pendingAction = null;")
        self.dedent()
        self.write("} else {")
        self.indent()
        self.write("log('go - Move to a scene or confirm a pending command', 'cyan');")
        self.write("if (typeof SCENE_LIST !== 'undefined' && SCENE_LIST.length > 0) {")
        self.indent()
        self.write("log('Scenes: ' + SCENE_LIST.join(', '), 'dim');")
        self.write("log('Usage: go <scene>', 'dim');")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")

        # List scenes - "scenes" or "rooms"
        self.write("else if (parts[0] === 'scenes' || parts[0] === 'rooms' || parts[0] === 'galleries') {")
        self.indent()
        self.write("if (typeof SCENE_LIST !== 'undefined' && SCENE_LIST.length > 0) {")
        self.indent()
        self.write("log('Scenes: ' + SCENE_LIST.join(', '), 'cyan');")
        self.write("log('Current: ' + currentScene, 'dim');")
        self.write("log('Type \"go <scene>\" to change', 'dim');")
        self.dedent()
        self.write("} else {")
        self.indent()
        self.write("log('No scenes defined in this demo', 'dim');")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")

        # Project Twin - Connect to shared world (via shared RoshNetwork)
        self.write("else if (parts[0] === 'connect' || parts[0] === 'twin') {")
        self.indent()
        self.write("if (typeof RoshNetwork !== 'undefined') {")
        self.indent()
        self.write("RoshNetwork.connect(parts[1] || 'default');")
        self.dedent()
        self.write("} else {")
        self.indent()
        self.write("log('RoshNetwork not loaded', 'err');")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")

        # Project Twin - Disconnect from shared world (via shared RoshNetwork)
        self.write("else if (parts[0] === 'disconnect') {")
        self.indent()
        self.write("if (typeof RoshNetwork !== 'undefined') RoshNetwork.disconnect();")
        self.write("else log('Not connected', 'dim');")
        self.dedent()
        self.write("}")

        # Project Twin - Sync command (broadcast object creation) - via RoshNetwork
        self.write("else if (parts[0] === 'sync' && parts[1]) {")
        self.indent()
        self.write("if (typeof RoshNetwork === 'undefined' || !RoshNetwork.isConnected()) {")
        self.indent()
        self.write("log('Not connected. Use \"connect\" first.', 'err');")
        self.dedent()
        self.write("} else {")
        self.indent()
        self.write("const objName = parts.slice(1).join(' ');")
        self.write("const obj = scene.getObjectByName(objName);")
        self.write("if (!obj) { log('Object not found: ' + objName, 'err'); }")
        self.write("else {")
        self.indent()
        self.write("const data = { type: obj.userData._type || 'cube', x: obj.position.x, y: obj.position.y, z: obj.position.z, color: obj.material?.color?.getHexString() || 'ffffff', size: obj.scale?.x || 1 };")
        self.write("RoshNetwork.broadcastCreate(objName, data);")
        self.write("log('Synced ' + objName + ' to shared world', 'ok');")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")

        # Create - "create banana" creates banana, or clones if exists
        self.write("else if (parts[0] === 'create' && parts[1]) {")
        self.indent()
        self.write("const desc = parts.slice(1).join(' ').toLowerCase();")
        self.write("const words = desc.split(/\\s+/);")
        self.write("const colors = {red:0xff0000, green:0x00ff00, blue:0x0000ff, yellow:0xffff00, cyan:0x00ffff, magenta:0xff00ff, white:0xffffff, orange:0xff8800, purple:0x8800ff, pink:0xff88ff, gray:0x888888, black:0x111111};")
        self.write("const shapeWords = ['ball', 'sphere', 'cube', 'box', 'cylinder', 'tube'];")
        self.write("const articles = ['a', 'an', 'the'];")
        self.write("const knownMods = ['big', 'large', 'small', 'tiny', ...Object.keys(colors), ...articles];")
        # Last word is the name (singularize), preceding unknown words become description
        self.write("let name = singularize(words[words.length - 1] || 'object');")
        self.write("const descWords = words.slice(0, -1).filter(w => !knownMods.includes(w) && !shapeWords.includes(w));")
        self.write("const objDescription = descWords.length > 0 ? descWords.join(' ') + ' ' + name : null;")
        self.write("let color = null, size = 1, shape = 'box';")
        self.write("let userSize = null;")  # Track if user specified a size
        self.write("for (const [c, hex] of Object.entries(colors)) if (desc.includes(c)) color = hex;")
        self.write("const userColor = color;")  # Remember if user specified a color
        self.write("if (desc.includes('big') || desc.includes('large')) { size = 2; userSize = 2; }")
        self.write("if (desc.includes('small') || desc.includes('tiny')) { size = 0.5; userSize = 0.5; }")
        self.write("if (desc.includes('ball') || desc.includes('sphere')) shape = 'sphere';")
        self.write("else if (desc.includes('cylinder') || desc.includes('tube')) shape = 'cylinder';")
        # Check if object with this name exists
        self.write("const existing = scene.getObjectByName(name);")
        # Only clone if NO modifiers specified (user wants exact duplicate)
        self.write("const hasModifiers = userColor !== null || userSize !== null;")
        self.write("if (existing && !hasModifiers) {")
        self.indent()
        self.write("// Clone existing object (no modifiers specified)")
        self.write("let n = 1; while (scene.getObjectByName(name + '-' + n)) n++;")
        self.write("const clone = existing.clone();")
        self.write("clone.name = name + '-' + n;")
        self.write("clone.position.x += 2;")
        self.write("clone.userData._twin = true;")
        self.write("clone.userData._scene = currentScene;")  # Clone goes to current scene, not source scene
        self.write("clone.visible = true;")  # Make visible immediately (source might be hidden)
        self.write("scene.add(clone);")
        self.write("gameObjects[clone.name] = clone;")
        self.write("pushUndo('create ' + clone.name, () => { scene.remove(clone); delete gameObjects[clone.name]; }, () => { scene.add(clone); gameObjects[clone.name] = clone; });")
        self.write("const cloneType = existing.userData._type || 'cube';")
        self.write("const cloneColor = existing.material && existing.material.color ? existing.material.color.getHex() : 0x00ff00;")
        self.write("twinBroadcastCreate(clone.name, cloneType, clone.position.x, clone.position.y, clone.position.z, cloneColor, 1);")
        self.write("if (!bulkCreateMode || bulkCreateCount < BULK_LOG_LIMIT) log('Created ' + clone.name + ' (cloned from ' + name + ')', 'ok');")
        self.write("if (!bulkCreateMode) { currentObject = clone; currentObjectName = clone.name; }")
        self.write("bulkCreateCount++;")
        self.dedent()
        self.write("} else {")
        self.indent()
        self.write("// Create new object - check KNOWN_OBJECTS for presets")
        self.write("const preset = KNOWN_OBJECTS[name];")
        self.write("if (preset) { shape = preset.shape; color = userColor !== null ? userColor : preset.color; } else { color = userColor !== null ? userColor : 0x00ff00; }")
        self.write("// Check if preset has a 3D model to load (and _config.useModels is true)")
        self.write("if (preset && preset.model && _config.useModels) {")
        self.indent()
        self.write("log('Loading 3D model for ' + name + '...', 'dim');")
        self.write("gltfLoader.load(preset.model, (gltf) => {")
        self.indent()
        self.write("const model = gltf.scene;")
        self.write("model.name = name;")
        self.write("model.userData._type = name;")
        self.write("if (objDescription) model.userData.description = objDescription;")
        self.write("if (preset.credit) model.userData.credit = preset.credit;")
        self.write("// Auto-normalize: compute bounding box and scale to fit 1 unit")
        self.write("const box = new THREE.Box3().setFromObject(model);")
        self.write("const modelSize = box.getSize(new THREE.Vector3());")
        self.write("const maxDim = Math.max(modelSize.x, modelSize.y, modelSize.z);")
        self.write("const normalizeScale = maxDim > 0 ? 1 / maxDim : 1;")
        self.write("// Apply normalize + preset scale + global _config.modelScale")
        self.write("const sx = preset.scaleX || 1, sy = preset.scaleY || 1, sz = preset.scaleZ || 1;")
        self.write("const gs = _config.modelScale || 2;")
        self.write("model.scale.set(normalizeScale * sx * size * gs, normalizeScale * sy * size * gs, normalizeScale * sz * size * gs);")
        self.write("model.position.set((Math.random()-0.5)*10, size, (Math.random()-0.5)*10);")
        self.write("model.userData._twin = true;")
        self.write("scene.add(model);")
        self.write("gameObjects[model.name] = model;")
        self.write("pushUndo('create ' + model.name, () => { scene.remove(model); delete gameObjects[model.name]; }, () => { scene.add(model); gameObjects[model.name] = model; });")
        self.write("twinBroadcastCreate(model.name, name, model.position.x, model.position.y, model.position.z, null, size);")
        self.write("if (!bulkCreateMode || bulkCreateCount < BULK_LOG_LIMIT) {")
        self.write("log('Created ' + name + ' (3D model)', 'ok');")
        self.write("if (preset.credit && !bulkCreateMode) log('Credit: ' + preset.credit, 'dim');")
        self.write("}")
        self.write("if (!bulkCreateMode) { currentObject = model; currentObjectName = name; }")
        self.write("bulkCreateCount++;")
        self.dedent()
        self.write("}, undefined, (err) => {")
        self.indent()
        self.write("console.error('GLTF load error:', err);")
        self.write("log('Failed to load ' + preset.model + ': ' + (err.message || err), 'warn');")
        self.write("// Fallback to primitive shape")
        self.write("let geom = shape === 'sphere' ? new THREE.SphereGeometry(size) : shape === 'cylinder' ? new THREE.CylinderGeometry(size*0.5, size*0.5, size) : new THREE.BoxGeometry(size, size, size);")
        self.write("const mat = new THREE.MeshStandardMaterial({color: color});")
        self.write("const mesh = new THREE.Mesh(geom, mat);")
        self.write("mesh.name = name;")
        self.write("mesh.userData._type = name;")
        self.write("mesh.userData._consoleTemplate = { type: 'mesh', shape: shape, size: size, color: color };")
        self.write("if (objDescription) mesh.userData.description = objDescription;")
        self.write("if (currentScene) mesh.userData._scene = currentScene;")
        self.write("if (preset.scaleX || preset.scaleY || preset.scaleZ) mesh.scale.set(preset.scaleX || 1, preset.scaleY || 1, preset.scaleZ || 1);")
        self.write("mesh.position.set((Math.random()-0.5)*10, size, (Math.random()-0.5)*10);")
        self.write("mesh.userData._twin = true;")
        self.write("scene.add(mesh);")
        self.write("gameObjects[mesh.name] = mesh;")
        self.write("pushUndo('create ' + mesh.name, () => { scene.remove(mesh); delete gameObjects[mesh.name]; }, () => { scene.add(mesh); gameObjects[mesh.name] = mesh; });")
        self.write("twinBroadcastCreate(mesh.name, shape, mesh.position.x, mesh.position.y, mesh.position.z, color, size);")
        self.write("if (!bulkCreateMode || bulkCreateCount < BULK_LOG_LIMIT) log('Created ' + name + ' (fallback)', 'ok');")
        self.write("bulkCreateCount++;")
        self.dedent()
        self.write("});")
        self.dedent()
        self.write("} else {")
        self.indent()
        self.write("// No model - create primitive shape")
        self.write("let geom = shape === 'sphere' ? new THREE.SphereGeometry(size) : shape === 'cylinder' ? new THREE.CylinderGeometry(size*0.5, size*0.5, size) : new THREE.BoxGeometry(size, size, size);")
        self.write("const mat = new THREE.MeshStandardMaterial({color: color});")
        self.write("const mesh = new THREE.Mesh(geom, mat);")
        self.write("mesh.name = name;")
        self.write("if (preset && (preset.scaleX || preset.scaleY || preset.scaleZ)) mesh.scale.set(preset.scaleX || 1, preset.scaleY || 1, preset.scaleZ || 1);")
        self.write("mesh.position.set((Math.random()-0.5)*10, size, (Math.random()-0.5)*10);")
        self.write("mesh.userData._type = name;")
        self.write("mesh.userData._consoleTemplate = { type: 'mesh', shape: shape, size: size, color: color };")
        self.write("if (objDescription) mesh.userData.description = objDescription;")
        self.write("if (currentScene) mesh.userData._scene = currentScene;")
        self.write("mesh.userData._twin = true;")
        self.write("scene.add(mesh);")
        self.write("gameObjects[mesh.name] = mesh;")
        self.write("pushUndo('create ' + mesh.name, () => { scene.remove(mesh); delete gameObjects[mesh.name]; }, () => { scene.add(mesh); gameObjects[mesh.name] = mesh; });")
        self.write("twinBroadcastCreate(mesh.name, shape, mesh.position.x, mesh.position.y, mesh.position.z, color, size);")
        self.write("if (!bulkCreateMode || bulkCreateCount < BULK_LOG_LIMIT) {")
        self.indent()
        self.write("log('Created ' + name, 'ok');")
        self.write("// Show properties")
        self.write("const sizeName = size >= 2 ? 'big' : size <= 0.5 ? 'small' : null;")
        self.write("const colorName = Object.entries(colors).find(([k,v]) => v === color)?.[0];")
        self.write("const desc = [sizeName, colorName, shape].filter(Boolean).join(' ');")
        self.write("if (desc !== shape) log('  ' + desc, 'dim');")
        self.write("if (colorName) log('  color: ' + colorName, 'dim');")
        self.write("if (sizeName) log('  scale: ' + size, 'dim');")
        self.dedent()
        self.write("}")
        self.write("if (!bulkCreateMode) { currentObject = mesh; currentObjectName = name; }")
        self.write("bulkCreateCount++;")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")

        # Prompt - interpret natural language and execute as Rosh
        self.write("else if (parts[0] === 'prompt') {")
        self.indent()
        self.write("const desc = parts.slice(1).join(' ').toLowerCase();")
        self.write("// Simple pattern matching for common requests")
        self.write("if (desc.includes('create')) { execCommand('create ' + desc.replace('create', ''), false); }")
        self.write("else if (desc.match(/set\\s+(\\w+)\\s+(\\w+)\\s+to\\s+(\\w+)/)) {")
        self.indent()
        self.write("const m = desc.match(/set\\s+(\\w+)\\s+(\\w+)\\s+to\\s+(\\w+)/);")
        self.write("execCommand('set ' + m[1] + ' ' + m[2] + ' to ' + m[3], false);")
        self.dedent()
        self.write("}")
        self.write("else if (desc.match(/move\\s+(\\w+)/)) {")
        self.indent()
        self.write("const obj = desc.match(/move\\s+(\\w+)/)[1];")
        self.write("const x = desc.includes('left') ? -2 : desc.includes('right') ? 2 : 0;")
        self.write("const y = desc.includes('up') ? 2 : desc.includes('down') ? -2 : 0;")
        self.write("execCommand('set ' + obj + ' x to ' + x, false);")
        self.write("if (y !== 0) execCommand('set ' + obj + ' y to ' + y, false);")
        self.dedent()
        self.write("}")
        self.write("else { log('Could not interpret: ' + desc, 'err'); log('Try: create big yellow ball, set logo color to red', 'cyan'); }")
        self.dedent()
        self.write("}")

        # List - supports: list, list all, list <scene>
        # Only shows registered Rosh objects (gameObjects), not raw Three.js scene children
        self.write("else if (parts[0] === 'list') {")
        self.indent()
        self.write("const arg = parts.slice(1).join(' ').toLowerCase();")
        self.write("if (arg === 'all') {")
        self.indent()
        self.write("// List all Rosh objects grouped by scene")
        self.write("const byScene = {};")
        self.write("Object.keys(gameObjects).forEach(name => {")
        self.indent()
        self.write("const o = gameObjects[name];")
        self.write("const s = (o.userData && o.userData._scene) || 'Global';")
        self.write("if (!byScene[s]) byScene[s] = [];")
        self.write("byScene[s].push(name);")
        self.dedent()
        self.write("});")
        self.write("Object.keys(byScene).forEach(s => {")
        self.indent()
        self.write("log(s + ' (' + byScene[s].length + '):', 'cyan');")
        self.write("byScene[s].slice(0, 10).forEach(n => log('  ' + n));")
        self.write("if (byScene[s].length > 10) log('  ...' + (byScene[s].length - 10) + ' more', 'dim');")
        self.dedent()
        self.write("});")
        self.dedent()
        self.write("} else if (arg && typeof SCENE_LIST !== 'undefined') {")
        self.indent()
        self.write("// List Rosh objects for specific scene")
        self.write("const match = SCENE_LIST.find(s => s.toLowerCase() === arg || s.toLowerCase().includes(arg));")
        self.write("if (match) {")
        self.indent()
        self.write("const objs = [];")
        self.write("Object.keys(gameObjects).forEach(name => {")
        self.indent()
        self.write("const o = gameObjects[name];")
        self.write("const objScene = o.userData && o.userData._scene;")
        self.write("if (objScene === match || (!objScene && match === 'Global')) objs.push(name);")
        self.dedent()
        self.write("});")
        self.write("log('Scene: ' + match + ' (' + objs.length + ' objects)', 'cyan');")
        self.write("objs.slice(0, 15).forEach(n => log('  ' + n));")
        self.write("if (objs.length > 15) log('  ...' + (objs.length - 15) + ' more', 'dim');")
        self.dedent()
        self.write("} else {")
        self.indent()
        self.write("log('Scene not found: ' + arg, 'err');")
        self.write("log('Available: ' + SCENE_LIST.join(', '), 'dim');")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("} else {")
        self.indent()
        self.write("// List Rosh objects in current scene")
        self.write("const objs = [];")
        self.write("Object.keys(gameObjects).forEach(name => {")
        self.indent()
        self.write("const o = gameObjects[name];")
        self.write("const objScene = o.userData && o.userData._scene;")
        self.write("if (currentScene && objScene && objScene !== currentScene) return;")
        self.write("objs.push(name);")
        self.dedent()
        self.write("});")
        self.write("if (currentScene) log('Scene: ' + currentScene, 'cyan');")
        self.write("log(objs.length + ' objects:', 'cyan');")
        self.write("objs.slice(0, 15).forEach(n => log('  ' + n));")
        self.write("if (objs.length > 15) log('  ...' + (objs.length - 15) + ' more', 'dim');")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")

        # Delete - handles: delete obj, delete N type, delete all type
        self.write("else if (parts[0] === 'delete' && parts[1]) {")
        self.indent()
        # Helper to find objects by type
        self.write("function findByType(typeName) {")
        self.indent()
        self.write("const matches = [];")
        self.write("scene.traverse(o => {")
        self.indent()
        self.write("if (o.name === typeName || o.name.startsWith(typeName + '-') || o.userData._type === typeName) matches.push(o);")
        self.dedent()
        self.write("});")
        self.write("return matches;")
        self.dedent()
        self.write("}")
        self.write_blank()
        # Check for trailing 'go'/'confirm' for auto-confirmation
        self.write("// Check for trailing go/confirm for auto-execution")
        self.write("let autoConfirm = false;")
        self.write("let delParts = [...parts];")  # Copy to avoid const reassignment
        self.write("const lastPart = delParts[delParts.length - 1]?.toLowerCase();")
        self.write("if (['go', 'confirm', 'yes'].includes(lastPart)) {")
        self.indent()
        self.write("autoConfirm = true;")
        self.write("delParts = delParts.slice(0, -1);")
        self.dedent()
        self.write("}")
        self.write_blank()
        # Check for "delete N type" pattern
        self.write("const count = parseInt(delParts[1]);")
        self.write("if (!isNaN(count) && delParts[2]) {")
        self.indent()
        self.write("const typeName = singularize(delParts[2]);")
        self.write("const matches = findByType(typeName);")
        self.write("if (matches.length === 0) { log('No ' + typeName + ' objects found', 'err'); }")
        self.write("else {")
        self.indent()
        self.write("const toDelete = matches.slice(0, count);")
        self.write("const actualCount = toDelete.length;")
        # Helper to execute bulk delete with undo support
        self.write("const doBulkDelete = () => {")
        self.indent()
        self.write("toDelete.forEach(o => {")
        self.indent()
        self.write("const parent = o.parent || scene;")
        self.write("const removeObj = () => { if (o.parent) o.parent.remove(o); else scene.remove(o); };")
        self.write("removeObj();")
        self.write("pushUndo('delete ' + typeName + ' ' + o.name, () => { parent.add(o); }, removeObj);")
        self.dedent()
        self.write("});")
        self.write("log('Deleted ' + actualCount + ' ' + typeName + '(s)', 'ok');")
        self.dedent()
        self.write("};")
        # Confirmation for >= 10 (if _config.confirm is true and no auto-confirm)
        self.write("if (actualCount >= 10 && _config.confirm && !autoConfirm) {")
        self.indent()
        self.write("pendingOp = {")
        self.indent()
        self.write("type: 'delete',")
        self.write("execute: doBulkDelete")
        self.dedent()
        self.write("};")
        self.write("log('⚠ Delete ' + actualCount + ' ' + typeName + '(s)?', 'warn');")
        self.write("log(\"Type 'go' or 'confirm' to execute\", 'dim');")
        self.dedent()
        self.write("} else {")
        self.indent()
        self.write("doBulkDelete();")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")
        # Check for "delete all type" pattern
        self.write("else if (delParts[1] === 'all' && delParts[2]) {")
        self.indent()
        self.write("const typeName = singularize(delParts[2]);")
        self.write("const matches = findByType(typeName);")
        self.write("if (matches.length === 0) { log('No ' + typeName + ' objects found', 'err'); }")
        self.write("else {")
        self.indent()
        self.write("const actualCount = matches.length;")
        # Helper to execute bulk delete with undo support
        self.write("const doDeleteAll = () => {")
        self.indent()
        self.write("matches.forEach(o => {")
        self.indent()
        self.write("const parent = o.parent || scene;")
        self.write("const removeObj = () => { if (o.parent) o.parent.remove(o); else scene.remove(o); };")
        self.write("removeObj();")
        self.write("pushUndo('delete ' + typeName + ' ' + o.name, () => { parent.add(o); }, removeObj);")
        self.dedent()
        self.write("});")
        self.write("log('Deleted all ' + actualCount + ' ' + typeName + '(s)', 'ok');")
        self.dedent()
        self.write("};")
        # Confirmation for >= 10 (if _config.confirm is true and no auto-confirm)
        self.write("if (actualCount >= 10 && _config.confirm && !autoConfirm) {")
        self.indent()
        self.write("pendingOp = {")
        self.indent()
        self.write("type: 'delete',")
        self.write("execute: doDeleteAll")
        self.dedent()
        self.write("};")
        self.write("log('⚠ Delete all ' + actualCount + ' ' + typeName + '(s)?', 'warn');")
        self.write("log(\"Type 'go' or 'confirm' to execute\", 'dim');")
        self.dedent()
        self.write("} else {")
        self.indent()
        self.write("doDeleteAll();")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")
        # Single object delete (try singularizing if not found)
        self.write("else {")
        self.indent()
        self.write("let objName = delParts[1];")
        self.write("let obj = scene.getObjectByName(objName);")
        self.write("// Try singularizing if not found")
        self.write("if (!obj) {")
        self.indent()
        self.write("const singular = singularize(objName);")
        self.write("if (singular !== objName) { obj = scene.getObjectByName(singular); if (obj) objName = singular; }")
        self.dedent()
        self.write("}")
        self.write("if (obj) {")
        self.indent()
        self.write("const parent = obj.parent;")
        self.write("const removeObj = () => { if (obj.parent) obj.parent.remove(obj); else scene.remove(obj); };")
        self.write("removeObj();")
        self.write("delete gameObjects[objName];")
        self.write("pushUndo(\"delete '\" + objName + \"'\", () => { (parent || scene).add(obj); gameObjects[objName] = obj; }, removeObj);")
        self.write("twinBroadcastDelete(objName);")
        self.write("log(\"Deleted '\" + objName + \"'\", 'ok');")
        self.dedent()
        self.write("}")
        self.write("else log('Not found: ' + parts[1], 'err');")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")

        # Remove (alias for delete)
        self.write("else if (parts[0] === 'remove' && parts[1]) {")
        self.indent()
        self.write("const obj = scene.getObjectByName(parts[1]);")
        self.write("if (obj) {")
        self.indent()
        self.write("const parent = obj.parent;")
        self.write("const removeObj = () => { if (obj.parent) obj.parent.remove(obj); else scene.remove(obj); };")
        self.write("removeObj();")
        self.write("delete gameObjects[parts[1]];")
        self.write("pushUndo(\"remove '\" + parts[1] + \"'\", () => { (parent || scene).add(obj); gameObjects[parts[1]] = obj; }, removeObj);")
        self.write("twinBroadcastDelete(parts[1]);")
        self.write("log(\"Removed '\" + parts[1] + \"'\", 'ok');")
        self.dedent()
        self.write("}")
        self.write("else log('Not found: ' + parts[1], 'err');")
        self.dedent()
        self.write("}")

        # Reset scene (clear localStorage and reload)
        self.write("else if (parts[0] === 'reset' && (parts[1] === 'scene' || parts[1] === 'all')) {")
        self.indent()
        self.write("log('Clearing saved data and reloading...', 'warn');")
        self.write("// Clear all rosh saves from localStorage")
        self.write("Object.keys(localStorage).filter(k => k.startsWith('rosh_save_')).forEach(k => localStorage.removeItem(k));")
        self.write("setTimeout(() => location.reload(), 500);")
        self.dedent()
        self.write("}")

        # Reset (clear userData overrides)
        self.write("else if (parts[0] === 'reset' && parts[1]) {")
        self.indent()
        self.write("const obj = scene.getObjectByName(parts[1]);")
        self.write("if (obj) {")
        self.indent()
        self.write("const prevUserData = JSON.parse(JSON.stringify(obj.userData || {}));")
        self.write("obj.userData = {};")
        self.write("pushUndo(\"reset '\" + parts[1] + \"'\", () => { obj.userData = prevUserData; }, () => { obj.userData = {}; });")
        self.write("log(\"Reset '\" + parts[1] + \"' to defaults\", 'ok');")
        self.dedent()
        self.write("}")
        self.write("else log('Not found: ' + parts[1], 'err');")
        self.dedent()
        self.write("}")

        # Hide (set visible to false) - supports: hide <name>, hide all, hide all <type>
        self.write("else if (parts[0] === 'hide' && parts[1]) {")
        self.indent()
        self.write("if (parts[1] === 'all') {")
        self.indent()
        self.write("const typeName = parts[2] ? singularize(parts[2]) : null;")
        self.write("let count = 0;")
        self.write("const undoStates = [];")
        self.write("scene.traverse(o => {")
        self.indent()
        self.write("if (!o.name || o.name.startsWith('_') || o.type === 'AmbientLight' || o.type === 'DirectionalLight') return;")
        self.write("if (typeName) {")
        self.indent()
        self.write("const oType = getTypeName(o);")
        self.write("const oColor = getColorName(o);")
        self.write("if (oType !== typeName && oColor !== typeName && !o.name.startsWith(typeName)) return;")
        self.dedent()
        self.write("}")
        self.write("if (o.visible !== false) { undoStates.push({obj: o, was: o.visible}); o.visible = false; count++; }")
        self.dedent()
        self.write("});")
        self.write("if (count > 0) {")
        self.indent()
        self.write("pushUndo('hide all' + (typeName ? ' ' + typeName : ''), () => { undoStates.forEach(s => s.obj.visible = s.was); }, () => { undoStates.forEach(s => s.obj.visible = false); });")
        self.write("log('Hid ' + count + ' object' + (count > 1 ? 's' : '') + (typeName ? ' (' + typeName + ')' : ''), 'ok');")
        self.dedent()
        self.write("} else log('No ' + (typeName || 'visible') + ' objects to hide', 'dim');")
        self.dedent()
        self.write("} else {")
        self.indent()
        self.write("const obj = scene.getObjectByName(parts[1]);")
        self.write("if (obj) {")
        self.indent()
        self.write("const wasVisible = obj.visible;")
        self.write("obj.visible = false;")
        self.write("pushUndo(\"hide '\" + parts[1] + \"'\", () => { obj.visible = wasVisible; }, () => { obj.visible = false; });")
        self.write("log(\"Hid '\" + parts[1] + \"'\", 'ok');")
        self.dedent()
        self.write("}")
        self.write("else log('Not found: ' + parts[1], 'err');")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")

        # Show (set visible to true) - supports: show <name>, show all, show all <type>
        self.write("else if (parts[0] === 'show' && parts[1]) {")
        self.indent()
        self.write("if (parts[1] === 'all') {")
        self.indent()
        self.write("const typeName = parts[2] ? singularize(parts[2]) : null;")
        self.write("let count = 0;")
        self.write("const undoStates = [];")
        self.write("scene.traverse(o => {")
        self.indent()
        self.write("if (!o.name || o.name.startsWith('_') || o.type === 'AmbientLight' || o.type === 'DirectionalLight') return;")
        self.write("if (typeName) {")
        self.indent()
        self.write("const oType = getTypeName(o);")
        self.write("const oColor = getColorName(o);")
        self.write("if (oType !== typeName && oColor !== typeName && !o.name.startsWith(typeName)) return;")
        self.dedent()
        self.write("}")
        self.write("if (o.visible !== true) { undoStates.push({obj: o, was: o.visible}); o.visible = true; count++; }")
        self.dedent()
        self.write("});")
        self.write("if (count > 0) {")
        self.indent()
        self.write("pushUndo('show all' + (typeName ? ' ' + typeName : ''), () => { undoStates.forEach(s => s.obj.visible = s.was); }, () => { undoStates.forEach(s => s.obj.visible = true); });")
        self.write("log('Showed ' + count + ' object' + (count > 1 ? 's' : '') + (typeName ? ' (' + typeName + ')' : ''), 'ok');")
        self.dedent()
        self.write("} else log('No ' + (typeName || 'hidden') + ' objects to show', 'dim');")
        self.dedent()
        self.write("} else {")
        self.indent()
        self.write("const obj = scene.getObjectByName(parts[1]);")
        self.write("if (obj) {")
        self.indent()
        self.write("const wasVisible = obj.visible;")
        self.write("obj.visible = true;")
        self.write("pushUndo(\"show '\" + parts[1] + \"'\", () => { obj.visible = wasVisible; }, () => { obj.visible = true; });")
        self.write("log(\"Showed '\" + parts[1] + \"'\", 'ok');")
        self.dedent()
        self.write("}")
        self.write("else log('Not found: ' + parts[1], 'err');")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")

        # Count - count objects of a type
        self.write("else if (parts[0] === 'count' && parts[1]) {")
        self.indent()
        self.write("let typeName = singularize(parts[1]);")
        self.write("let count = 0;")
        self.write("const matches = [];")
        self.write("scene.traverse(o => {")
        self.indent()
        self.write("if (!o.name || o.name.startsWith('_')) return;")
        self.write("const oType = (o.userData && o.userData._type) || o.name.replace(/-\\d+$/, '');")
        self.write("if (oType === typeName || o.name === typeName) { count++; matches.push(o.name); }")
        self.dedent()
        self.write("});")
        self.write("if (count === 0) log('No ' + typeName + ' objects found', 'dim');")
        self.write("else {")
        self.indent()
        self.write("log(count + ' ' + typeName + (count > 1 ? ' objects:' : ' object:'), 'cyan');")
        self.write("// Show first 10, then '...N more'")
        self.write("matches.slice(0, 10).forEach(n => log('  ' + n));")
        self.write("if (count > 10) log('  ...' + (count - 10) + ' more', 'dim');")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")

        # Count all (no type specified)
        self.write("else if (parts[0] === 'count') {")
        self.indent()
        self.write("let count = 0;")
        self.write("scene.traverse(o => { if (o.name && !o.name.startsWith('_')) count++; });")
        self.write("log(count + ' objects in scene', 'cyan');")
        self.dedent()
        self.write("}")

        # Move - move object to x,y,z
        self.write("else if (parts[0] === 'move' && parts[1]) {")
        self.indent()
        self.write("const obj = scene.getObjectByName(parts[1]);")
        self.write("if (!obj) { log('Not found: ' + parts[1], 'err'); }")
        self.write("else {")
        self.indent()
        # Parse "move obj to x,y" or "move obj to x y z" or "move obj x y z"
        # Also handle named positions: center, origin
        self.write("let rest = parts.slice(2).join(' ').replace(/^to\\s+/, '').replace(/^the\\s+/, '');")
        self.write("const namedPositions = { 'center': [0, obj.position.y, 0], 'origin': [0, 0, 0], 'ground': [obj.position.x, 0, obj.position.z] };")
        self.write("let coords;")
        self.write("if (namedPositions[rest.toLowerCase()]) {")
        self.indent()
        self.write("coords = namedPositions[rest.toLowerCase()];")
        self.write("log('[resolved: ' + rest + ' → ' + coords.join(', ') + ']', 'dim');")
        self.dedent()
        self.write("} else {")
        self.indent()
        self.write("coords = rest.split(/[,\\s]+/).map(Number).filter(n => !isNaN(n));")
        self.dedent()
        self.write("}")
        self.write("if (coords.length === 0) { log('Usage: move <obj> to x,y,z or center/origin/ground', 'err'); }")
        self.write("else {")
        self.indent()
        self.write("const oldPos = obj.position.clone();")
        self.write("const newX = coords[0] !== undefined ? coords[0] : obj.position.x;")
        self.write("const newY = coords[1] !== undefined ? coords[1] : obj.position.y;")
        self.write("const newZ = coords[2] !== undefined ? coords[2] : obj.position.z;")
        self.write("obj.position.set(newX, newY, newZ);")
        self.write("pushUndo('move ' + parts[1], () => { obj.position.copy(oldPos); }, () => { obj.position.set(newX, newY, newZ); });")
        self.write("log('Moved ' + parts[1] + ' to (' + newX.toFixed(1) + ', ' + newY.toFixed(1) + ', ' + newZ.toFixed(1) + ')', 'ok');")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")

        # Make - natural language for modifications
        # Handle "make N [adjectives] <type> [modifier]" pattern
        # e.g., "make 30 orcs", "make 30 green orcs", "make 30 orcs bigger", "make 30 angry green orcs bigger"
        self.write("else if (parts[0] === 'make' && !isNaN(parseInt(parts[1])) && parts[2]) {")
        self.indent()
        self.write("const count = parseInt(parts[1]);")
        # Check for trailing 'go'/'confirm' for auto-confirmation
        self.write("let autoConfirm = false;")
        self.write("let words = parts.slice(2);")  # Everything after count
        self.write("if (['go', 'confirm', 'yes'].includes(words[words.length - 1]?.toLowerCase())) {")
        self.indent()
        self.write("autoConfirm = true;")
        self.write("words = words.slice(0, -1);")
        self.dedent()
        self.write("}")
        self.write("if (words.length === 0) { log('Usage: make <count> [adjectives] <type> [modifier]', 'err'); }")
        self.write("else {")
        self.indent()
        # Known action modifiers (things you do to existing objects)
        self.write("const actionModifiers = ['big', 'bigger', 'large', 'larger', 'small', 'smaller', 'tiny', 'visible', 'shown', 'invisible', 'hidden'];")
        self.write("const knownColors = {red:1, green:1, blue:1, yellow:1, cyan:1, magenta:1, white:1, black:1, orange:1, purple:1, pink:1, gray:1};")
        # Check if last word is an action modifier
        self.write("const lastWord = words[words.length - 1].toLowerCase();")
        self.write("const isActionModifier = actionModifiers.includes(lastWord);")
        self.write("const isColorModifier = knownColors[lastWord] && words.length > 1;")  # Color only if there's a type before it
        self.write_blank()
        self.write("if (isActionModifier || isColorModifier) {")
        self.indent()
        # Last word is modifier, second-to-last is type, rest are ignored for now
        self.write("// Action modifier: make N [adj] type bigger")
        self.write("const modifier = lastWord;")
        self.write("const typeName = singularize(words.length > 1 ? words[words.length - 2] : words[0]);")
        self.write("if (!modifier) { log('Usage: make <count> <type> <modifier>', 'err'); }")
        self.write("else {")
        self.indent()
        self.write("const knownColors = {red:0xff0000, green:0x00ff00, blue:0x0000ff, yellow:0xffff00, cyan:0x00ffff, magenta:0xff00ff, white:0xffffff, black:0x111111, orange:0xff8800, purple:0x8800ff, pink:0xff88ff, gray:0x888888};")
        self.write("const allTargets = [];")
        self.write("scene.traverse(o => { if (o.name === typeName || o.name.startsWith(typeName + '-') || o.userData._type === typeName) allTargets.push(o); });")
        self.write("if (allTargets.length === 0) { log('No ' + typeName + 's found', 'err'); }")
        self.write("else {")
        self.indent()
        self.write("const targets = allTargets.slice(0, count);")
        self.write("function applyModifier() {")
        self.indent()
        self.write("let modified = 0;")
        self.write("const colorMatch = modifier.match(/^colou?r\\s+(\\w+)$/i);")
        self.write("const effectiveModifier = colorMatch ? colorMatch[1].toLowerCase() : modifier;")
        self.write("let failures = 0;")
        self.write("for (const obj of targets) {")
        self.indent()
        self.write("if (['big', 'bigger', 'large', 'larger'].includes(effectiveModifier)) { obj.scale.multiplyScalar(1.5); modified++; }")
        self.write("else if (['small', 'smaller', 'tiny'].includes(effectiveModifier)) { obj.scale.multiplyScalar(1/1.5); modified++; }")
        self.write("else if (effectiveModifier === 'visible' || effectiveModifier === 'shown') { obj.visible = true; modified++; }")
        self.write("else if (effectiveModifier === 'invisible' || effectiveModifier === 'hidden') { obj.visible = false; modified++; }")
        self.write("else if (knownColors[effectiveModifier]) {")
        self.indent()
        self.write("const result = applyCapabilityBridge(obj, 'color', [effectiveModifier]);")
        self.write("if (result.ok) modified++; else failures++;")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")
        self.write("if (modified > 0) log('Modified ' + modified + ' ' + typeName + '(s): ' + modifier, 'ok');")
        self.write("else if (failures > 0) log('Color not supported for ' + typeName + ' (3D models need direct material access)', 'err');")
        self.write("else log('Unknown modifier: ' + modifier, 'err');")
        self.dedent()
        self.write("}")
        # Confirmation for >= 10 (if _config.confirm is true and no auto-confirm)
        self.write("if (targets.length >= 10 && _config.confirm && !autoConfirm) {")
        self.indent()
        self.write("pendingOp = { type: 'make', execute: applyModifier };")
        self.write("log('⚠ Modify ' + targets.length + ' ' + typeName + '(s)?', 'warn');")
        self.write("log(\"Type 'go' or 'confirm' to execute\", 'dim');")
        self.dedent()
        self.write("} else applyModifier();")
        self.dedent()
        self.write("}")  # close targets exist
        self.dedent()
        self.write("}")  # close else (modifier exists)
        self.dedent()
        self.write("} else {")
        self.indent()
        # No action modifier - treat as create with adjectives
        self.write("// No action modifier - treat as 'create N [adjectives] type'")
        self.write("const createCmd = 'create ' + count + ' ' + words.join(' ');")
        self.write("log('→ ' + createCmd, 'dim');")
        self.write("execCommand(createCmd, false);")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")  # close else (words.length > 0)
        self.dedent()
        self.write("}")  # close else if (make N ...)

        # Handle "make all <type> <modifier>" pattern
        self.write("else if (parts[0] === 'make' && parts[1] === 'all' && parts[2] && parts[3]) {")
        self.indent()
        # Check for trailing 'go'/'confirm' for auto-confirmation
        self.write("// Check for trailing go/confirm for auto-execution")
        self.write("let autoConfirm = false;")
        self.write("let modParts = parts.slice(3);")
        self.write("if (['go', 'confirm', 'yes'].includes(modParts[modParts.length - 1]?.toLowerCase())) {")
        self.indent()
        self.write("autoConfirm = true;")
        self.write("modParts = modParts.slice(0, -1);")
        self.dedent()
        self.write("}")
        self.write("const typeName = singularize(parts[2]);")
        self.write("const modifier = modParts.join(' ');")
        self.write("if (!modifier) { log('Usage: make all <type> <modifier>', 'err'); }")
        self.write("else {")
        self.indent()
        self.write("const knownColors = {red:0xff0000, green:0x00ff00, blue:0x0000ff, yellow:0xffff00, cyan:0x00ffff, magenta:0xff00ff, white:0xffffff, black:0x111111, orange:0xff8800, purple:0x8800ff, pink:0xff88ff, gray:0x888888};")
        self.write("const targets = [];")
        self.write("scene.traverse(o => { if (o.name === typeName || o.name.startsWith(typeName + '-') || o.userData._type === typeName) targets.push(o); });")
        self.write("if (targets.length === 0) { log('No ' + typeName + 's found', 'err'); }")
        self.write("else {")
        self.indent()
        self.write("function applyModifier() {")
        self.indent()
        self.write("let count = 0;")
        self.write("let failures = 0;")
        self.write("// Handle 'color <name>' or 'colour <name>' patterns")
        self.write("const colorMatch = modifier.match(/^colou?r\\s+(\\w+)$/i);")
        self.write("const effectiveModifier = colorMatch ? colorMatch[1].toLowerCase() : modifier;")
        self.write("for (const obj of targets) {")
        self.indent()
        self.write("if (['big', 'bigger', 'large', 'larger'].includes(effectiveModifier)) { obj.scale.multiplyScalar(1.5); count++; }")
        self.write("else if (['small', 'smaller', 'tiny'].includes(effectiveModifier)) { obj.scale.multiplyScalar(1/1.5); count++; }")
        self.write("else if (effectiveModifier === 'visible' || effectiveModifier === 'shown') { obj.visible = true; count++; }")
        self.write("else if (effectiveModifier === 'invisible' || effectiveModifier === 'hidden') { obj.visible = false; count++; }")
        self.write("else if (knownColors[effectiveModifier]) {")
        self.indent()
        self.write("const result = applyCapabilityBridge(obj, 'color', [effectiveModifier]);")
        self.write("if (result.ok) count++; else failures++;")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")
        self.write("if (count > 0) log('Modified ' + count + ' ' + typeName + '(s): ' + modifier, 'ok');")
        self.write("else if (failures > 0) log('Color not supported for ' + typeName + ' (3D models need direct material access)', 'err');")
        self.write("else log('Unknown modifier: ' + modifier, 'err');")
        self.dedent()
        self.write("}")
        # Confirmation for >= 10 (if _config.confirm is true and no auto-confirm)
        self.write("if (targets.length >= 10 && _config.confirm && !autoConfirm) {")
        self.indent()
        self.write("pendingOp = { type: 'make', execute: applyModifier };")
        self.write("log('⚠ Modify ' + targets.length + ' ' + typeName + '(s)?', 'warn');")
        self.write("log(\"Type 'go' or 'confirm' to execute\", 'dim');")
        self.dedent()
        self.write("} else applyModifier();")
        self.dedent()
        self.write("}")  # close targets exist
        self.dedent()
        self.write("}")  # close else (modifier exists)
        self.dedent()
        self.write("}")  # close else if (make all)

        # Single object make
        self.write("else if (parts[0] === 'make' && parts[1] && parts[2]) {")
        self.indent()
        self.write("let objName = parts[1];")
        self.write("const rest = parts.slice(2);")
        self.write("const knownColors = {red:0xff0000, green:0x00ff00, blue:0x0000ff, yellow:0xffff00, cyan:0x00ffff, magenta:0xff00ff, white:0xffffff, black:0x111111, orange:0xff8800, purple:0x8800ff, pink:0xff88ff, gray:0x888888};")
        self.write("let obj = scene.getObjectByName(objName);")
        self.write("// Try singularizing if not found")
        self.write("if (!obj) {")
        self.indent()
        self.write("const singular = singularize(objName);")
        self.write("if (singular !== objName) { obj = scene.getObjectByName(singular); if (obj) objName = singular; }")
        self.dedent()
        self.write("}")
        # If object not found, check if this looks like a creation command
        self.write("if (!obj) {")
        self.indent()
        self.write("// Check if user means 'create' - articles, colors, sizes suggest creation")
        self.write("const articles = ['a', 'an', 'the'];")
        self.write("const colors = ['red', 'green', 'blue', 'yellow', 'cyan', 'magenta', 'white', 'black', 'orange', 'purple', 'pink', 'gray'];")
        self.write("const sizes = ['big', 'small', 'large', 'tiny', 'huge'];")
        self.write("const firstWord = parts[1].toLowerCase();")
        self.write("if (articles.includes(firstWord) || colors.includes(firstWord) || sizes.includes(firstWord)) {")
        self.indent()
        # Filter out articles and build create command
        self.write("const createParts = parts.slice(1).filter(w => !articles.includes(w.toLowerCase()));")
        self.write("const createCmd = 'create ' + createParts.join(' ');")
        self.write("log('→ ' + createCmd, 'dim');")
        self.write("execCommand(createCmd, false);")
        self.dedent()
        self.write("}")
        self.write("else { log('Not found: ' + parts[1] + '. Did you mean: create ' + parts.slice(1).join(' ') + '?', 'err'); }")
        self.dedent()
        self.write("}")
        self.write("else {")
        self.indent()
        # make <obj> visible/hidden
        self.write("if (rest[0] === 'visible' || rest[0] === 'shown') {")
        self.indent()
        self.write("const was = obj.visible;")
        self.write("obj.visible = true;")
        self.write("pushUndo('make ' + objName + ' visible', () => { obj.visible = was; }, () => { obj.visible = true; });")
        self.write("log('Showed ' + objName, 'ok');")
        self.dedent()
        self.write("}")
        self.write("else if (rest[0] === 'invisible' || rest[0] === 'hidden') {")
        self.indent()
        self.write("const was = obj.visible;")
        self.write("obj.visible = false;")
        self.write("pushUndo('make ' + objName + ' hidden', () => { obj.visible = was; }, () => { obj.visible = false; });")
        self.write("log('Hid ' + objName, 'ok');")
        self.dedent()
        self.write("}")
        # make <obj> <color>
        self.write("else if (knownColors[rest[0]]) {")
        self.indent()
        self.write("log('→ set ' + objName + ' color to ' + rest[0], 'dim');")
        self.write("const result = applyCapabilityBridge(obj, 'color', [rest[0]]);")
        self.write("if (result.ok) log(result.message, 'ok'); else log(result.message, 'err');")
        self.dedent()
        self.write("}")
        # make <obj> big/small - relative scaling (multiply/divide by 1.5)
        self.write("else if (['big', 'bigger', 'large', 'larger'].includes(rest[0])) {")
        self.indent()
        self.write("const oldScale = obj.scale.clone();")
        self.write("const factor = 1.5;")
        self.write("obj.scale.multiplyScalar(factor);")
        self.write("const newScale = obj.scale.x.toFixed(2);")
        self.write("pushUndo('make ' + objName + ' bigger', () => { obj.scale.copy(oldScale); }, () => { obj.scale.copy(oldScale).multiplyScalar(factor); });")
        self.write("log(objName + '.scale = ' + newScale, 'ok');")
        self.dedent()
        self.write("}")
        self.write("else if (['small', 'smaller', 'tiny'].includes(rest[0])) {")
        self.indent()
        self.write("const oldScale = obj.scale.clone();")
        self.write("const factor = 1/1.5;")
        self.write("obj.scale.multiplyScalar(factor);")
        self.write("const newScale = obj.scale.x.toFixed(2);")
        self.write("pushUndo('make ' + objName + ' smaller', () => { obj.scale.copy(oldScale); }, () => { obj.scale.copy(oldScale).multiplyScalar(factor); });")
        self.write("log(objName + '.scale = ' + newScale, 'ok');")
        self.dedent()
        self.write("}")
        # make <obj> <prop> <value>
        self.write("else if (rest.length >= 2) {")
        self.indent()
        self.write("const prop = rest[0];")
        self.write("const valueTokens = rest.slice(1);")
        self.write("log('→ set ' + objName + ' ' + prop + ' to ' + valueTokens.join(' '), 'dim');")
        self.write("let result = handleCoreSet(obj, prop, valueTokens);")
        self.write("if (!result.ok) result = applyCapabilityBridge(obj, prop, valueTokens);")
        self.write("if (result.ok) log(result.message, 'ok'); else log(result.message, 'err');")
        self.dedent()
        self.write("}")
        self.write("else { log('Usage: make <obj> <color|visible|big|prop value>', 'err'); }")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")

        # Handle "make <word>" (2 words) - treat as create
        self.write("else if (parts[0] === 'make' && parts[1] && !parts[2]) {")
        self.indent()
        self.write("// 'make ball' or 'make yellow' -> create it")
        self.write("const createCmd = 'create ' + parts[1];")
        self.write("log('→ ' + createCmd, 'dim');")
        self.write("execCommand(createCmd, false);")
        self.dedent()
        self.write("}")

        # Clone
        self.write("else if (parts[0] === 'clone' && parts[1]) {")
        self.indent()
        self.write("let src = scene.getObjectByName(parts[1]);")
        # If object doesn't exist, create it (don't also clone)
        self.write("if (!src) {")
        self.indent()
        self.write("// Smart default: create if doesn't exist (just create, don't clone)")
        self.write("const preset = KNOWN_OBJECTS[parts[1]] || { shape: 'box', color: 0x00ff00 };")
        self.write("// Check if preset has a 3D model to load (and _config.useModels is true)")
        self.write("if (preset.model && _config.useModels) {")
        self.indent()
        self.write("log('Loading 3D model for ' + parts[1] + '...', 'dim');")
        self.write("gltfLoader.load(preset.model, (gltf) => {")
        self.indent()
        self.write("const model = gltf.scene;")
        self.write("model.name = parts[1];")
        self.write("model.userData._type = parts[1];")
        self.write("if (preset.credit) model.userData._credit = preset.credit;")
        self.write("// Auto-normalize: compute bounding box and scale to fit 1 unit")
        self.write("const box = new THREE.Box3().setFromObject(model);")
        self.write("const modelSize = box.getSize(new THREE.Vector3());")
        self.write("const maxDim = Math.max(modelSize.x, modelSize.y, modelSize.z);")
        self.write("const normalizeScale = maxDim > 0 ? 1 / maxDim : 1;")
        self.write("// Apply normalize + preset scale + global _config.modelScale")
        self.write("const sx = preset.scaleX || 1, sy = preset.scaleY || 1, sz = preset.scaleZ || 1;")
        self.write("const gs = _config.modelScale || 2;")
        self.write("model.scale.set(normalizeScale * sx * gs, normalizeScale * sy * gs, normalizeScale * sz * gs);")
        self.write("model.position.set((Math.random()-0.5)*10, 1, (Math.random()-0.5)*10);")
        self.write("scene.add(model);")
        self.write("pushUndo('create ' + model.name, () => { scene.remove(model); }, () => { scene.add(model); });")
        self.write("log('Created ' + parts[1] + ' (3D model)', 'ok');")
        self.write("if (preset.credit) log('Credit: ' + preset.credit, 'dim');")
        self.dedent()
        self.write("}, undefined, (err) => {")
        self.indent()
        self.write("console.error('GLTF load error:', err);")
        self.write("log('Failed to load ' + preset.model + ': ' + (err.message || err), 'warn');")
        self.write("let geom = preset.shape === 'sphere' ? new THREE.SphereGeometry(1) : preset.shape === 'cylinder' ? new THREE.CylinderGeometry(0.5, 0.5, 1) : new THREE.BoxGeometry(1, 1, 1);")
        self.write("const mat = new THREE.MeshStandardMaterial({color: preset.color});")
        self.write("const mesh = new THREE.Mesh(geom, mat);")
        self.write("mesh.name = parts[1];")
        self.write("mesh.userData._type = parts[1];")
        self.write("if (preset.scaleX || preset.scaleY || preset.scaleZ) mesh.scale.set(preset.scaleX || 1, preset.scaleY || 1, preset.scaleZ || 1);")
        self.write("mesh.position.set((Math.random()-0.5)*10, 1, (Math.random()-0.5)*10);")
        self.write("scene.add(mesh);")
        self.write("pushUndo('create ' + mesh.name, () => { scene.remove(mesh); }, () => { scene.add(mesh); });")
        self.write("log('Created ' + parts[1] + ' (fallback)', 'ok');")
        self.dedent()
        self.write("});")
        self.write("return;")
        self.dedent()
        self.write("}")
        self.write("// No model - create primitive shape")
        self.write("let geom;")
        self.write("if (preset.shape === 'sphere') geom = new THREE.SphereGeometry(1);")
        self.write("else if (preset.shape === 'cylinder') geom = new THREE.CylinderGeometry(0.5, 0.5, 1);")
        self.write("else geom = new THREE.BoxGeometry(1, 1, 1);")
        self.write("const mat = new THREE.MeshStandardMaterial({color: preset.color});")
        self.write("src = new THREE.Mesh(geom, mat);")
        self.write("src.name = parts[1];")
        self.write("if (preset.scaleX || preset.scaleY || preset.scaleZ) src.scale.set(preset.scaleX || 1, preset.scaleY || 1, preset.scaleZ || 1);")
        self.write("src.position.set((Math.random()-0.5)*10, 1, (Math.random()-0.5)*10);")
        self.write("src.userData._type = parts[1];")
        self.write("scene.add(src);")
        self.write("pushUndo('create ' + parts[1], () => { scene.remove(src); }, () => { scene.add(src); });")
        self.write("log('Created ' + parts[1], 'ok');")
        self.write("return;")
        self.dedent()
        self.write("}")
        # Determine target name - use 'as' keyword or auto-generate
        self.write("let targetName = parts[3] && (parts[2] === 'as' || parts[2] === 'to') ? parts[3] : null;")
        self.write("if (!targetName) { let n = 1; while (scene.getObjectByName(parts[1] + '-' + n)) n++; targetName = parts[1] + '-' + n; }")
        self.write("const clone = src.clone();")
        self.write("clone.name = targetName;")
        self.write("clone.userData._type = parts[1];")  # Inherit type from source
        self.write("clone.position.x += 2;")  # Offset so it's visible
        self.write("scene.add(clone);")
        self.write("const cloneParent = scene;")
        self.write("pushUndo(\"clone '\" + parts[1] + \"'\", () => { cloneParent.remove(clone); }, () => { cloneParent.add(clone); });")
        self.write("log(\"Cloned '\" + parts[1] + \"' as '\" + targetName + \"'\", 'ok');")
        self.dedent()
        self.write("}")

        # Get config - show all config settings
        self.write("else if (parts[0] === 'get' && parts[1] === 'config' && !parts[2]) {")
        self.indent()
        self.write("log('config settings:', 'cyan');")
        self.write("log('  modelScale = ' + _config.modelScale);")
        self.write("log('  useModels = ' + _config.useModels);")
        self.write("log('  floor = ' + _config.floor);")
        self.write("log('  floorColor = ' + (_config.floorColor !== null ? '#' + _config.floorColor.toString(16).padStart(6, '0') : 'none'));")
        self.write("log('  confirm = ' + _config.confirm);")
        self.dedent()
        self.write("}")

        # Get config scale - show current model scale
        self.write("else if (parts[0] === 'get' && parts[1] === 'config' && parts[2] === 'scale') {")
        self.indent()
        self.write("log('_config.modelScale = ' + _config.modelScale, 'cyan');")
        self.dedent()
        self.write("}")

        # Get config floor - show floor settings
        self.write("else if (parts[0] === 'get' && parts[1] === 'config' && parts[2] === 'floor') {")
        self.indent()
        self.write("log('_config.floor = ' + _config.floor, 'cyan');")
        self.write("log('_config.floorColor = ' + (_config.floorColor !== null ? '#' + _config.floorColor.toString(16).padStart(6, '0') : 'none'), 'cyan');")
        self.dedent()
        self.write("}")

        # Get all <type> - list and select all instances of a type
        self.write("else if (parts[0] === 'get' && parts[1] === 'all' && parts[2]) {")
        self.indent()
        self.write("let typeName = parts[2];")
        self.write("let corrected = false;")
        # Helper to find matches for a type name
        self.write("function findMatches(name) {")
        self.indent()
        self.write("const m = [];")
        self.write("scene.traverse(o => {")
        self.indent()
        self.write("if (!o.name || o.name.startsWith('_')) return;")
        self.write("if (o.userData._type === name || o.name === name || o.name.startsWith(name + '-')) m.push(o);")
        self.dedent()
        self.write("});")
        self.write("return m;")
        self.dedent()
        self.write("}")
        self.write("let matches = findMatches(typeName);")
        # Try singular forms if no matches (plurals: bananas→banana, boxes→box, berries→berry)
        self.write("if (matches.length === 0) {")
        self.indent()
        self.write("const singular = typeName.endsWith('ies') ? typeName.slice(0,-3)+'y' : typeName.endsWith('es') ? typeName.slice(0,-2) : typeName.endsWith('s') ? typeName.slice(0,-1) : null;")
        self.write("if (singular) { matches = findMatches(singular); if (matches.length > 0) { corrected = true; typeName = singular; } }")
        self.dedent()
        self.write("}")
        self.write("if (matches.length === 0) { log('No ' + parts[2] + ' objects found', 'warn'); }")
        self.write("else {")
        self.indent()
        self.write("if (corrected) log('[corrected: ' + parts[2] + ' → ' + typeName + ']', 'dim');")
        self.write("currentSelection = matches;")
        self.write("currentSelectionType = typeName;")
        self.write("log('Selected ' + matches.length + ' ' + typeName + '(s):', 'ok');")
        self.write("// Show first 10, then '...N more'")
        self.write("matches.slice(0, 10).forEach(o => log('  ' + o.name));")
        self.write("if (matches.length > 10) log('  ...' + (matches.length - 10) + ' more', 'dim');")
        self.write("log('Use \"set all <prop> to <value>\" to modify all', 'dim');")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")

        # Get - with deep attribute search fallback
        self.write("else if (parts[0] === 'get' && parts[1]) {")
        self.indent()
        self.write("const queryParts = parts.slice(1);")
        self.write("const queryJoined = queryParts.join('-');")  # Try hyphenated version
        self.write("let obj = scene.getObjectByName(queryParts[0]) || scene.getObjectByName(queryJoined);")
        self.write("if (obj) { currentObject = obj; currentObjectName = obj.name; log('<object: ' + obj.name + '>', 'ok'); }")
        self.write("else {")
        self.indent()
        # Deep search by color and type attributes (helper functions defined at top of execCommand)
        self.write("// Deep search by attributes (color, shape type)")
        self.write("const knownColors = {red:1, green:1, blue:1, yellow:1, cyan:1, magenta:1, white:1, black:1, orange:1, purple:1, pink:1, gray:1, grey:1, gold:1, silver:1};")
        self.write("const shapeSynonyms = {box:'cube', cube:'cube', ball:'sphere', sphere:'sphere', cylinder:'cylinder', tube:'cylinder', cone:'cone', torus:'torus', ring:'torus'};")
        self.write("let targetColor = null, targetShape = null;")
        self.write("for (const w of queryParts) {")
        self.indent()
        self.write("const wl = w.toLowerCase();")
        self.write("if (knownColors[wl]) targetColor = wl;")
        self.write("if (shapeSynonyms[wl]) targetShape = shapeSynonyms[wl];")
        self.dedent()
        self.write("}")
        self.write("if (!targetColor && !targetShape) {")
        self.indent()
        self.write("log('Not found: ' + queryParts[0], 'err');")
        self.dedent()
        self.write("} else {")
        self.indent()
        self.write("const matches = [];")
        self.write("scene.traverse(child => {")
        self.indent()
        self.write("if (child.isMesh && child.name && !child.name.startsWith('_')) {")
        self.indent()
        self.write("const cType = getTypeName(child);")
        self.write("const cColor = getColorName(child);")
        self.write("const typeMatch = !targetShape || cType.includes(targetShape);")
        self.write("const colorMatch = !targetColor || cColor === targetColor || (targetColor === 'grey' && cColor === 'gray');")
        self.write("if (typeMatch && colorMatch) matches.push(child.name);")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("});")
        self.write("if (matches.length === 0) {")
        self.indent()
        self.write("log('Not found: no ' + (targetColor || '') + ' ' + (targetShape || 'objects'), 'err');")
        self.dedent()
        self.write("} else if (matches.length === 1) {")
        self.indent()
        self.write("const found = scene.getObjectByName(matches[0]);")
        self.write("currentObject = found; currentObjectName = matches[0];")
        self.write("log('[deep search] <object: ' + matches[0] + '>', 'ok');")
        self.dedent()
        self.write("} else {")
        self.indent()
        self.write("log('[deep search] Found ' + matches.length + ': ' + matches.join(', '), 'ok');")
        self.write("const found = scene.getObjectByName(matches[0]);")
        self.write("currentObject = found; currentObjectName = matches[0];")
        self.write("log('Selected: ' + matches[0], 'ok');")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")

        # Set config scale - global model scale multiplier
        self.write("else if (parts[0] === 'set' && parts[1] === 'config' && parts[2] === 'scale') {")
        self.indent()
        self.write("const filtered = parts.filter(x => x !== 'to');")
        self.write("const val = parseFloat(filtered[3]);")
        self.write("if (!isNaN(val) && val > 0) {")
        self.indent()
        self.write("const prev = _config.modelScale;")
        self.write("_config.modelScale = val;")
        self.write("pushUndo('set config scale', () => { _config.modelScale = prev; }, () => { _config.modelScale = val; });")
        self.write("log('Model scale set to ' + val + ' (affects new models)', 'ok');")
        self.dedent()
        self.write("} else log('Usage: set config scale to <number>', 'err');")
        self.dedent()
        self.write("}")

        # Set config models on/off - toggle 3D models vs primitives
        self.write("else if (parts[0] === 'set' && parts[1] === 'config' && parts[2] === 'models') {")
        self.indent()
        self.write("const filtered = parts.filter(x => x !== 'to');")
        self.write("const val = filtered[3];")
        self.write("if (val === 'on' || val === 'true' || val === '1') {")
        self.indent()
        self.write("_config.useModels = true;")
        self.write("log('3D models enabled (affects new objects)', 'ok');")
        self.dedent()
        self.write("} else if (val === 'off' || val === 'false' || val === '0') {")
        self.indent()
        self.write("_config.useModels = false;")
        self.write("log('3D models disabled - using primitive shapes (affects new objects)', 'ok');")
        self.dedent()
        self.write("} else log('Usage: set config models to on/off', 'err');")
        self.dedent()
        self.write("}")

        # Set config floor on/off - toggle grid visibility
        self.write("else if (parts[0] === 'set' && parts[1] === 'config' && parts[2] === 'floor') {")
        self.indent()
        self.write("const filtered = parts.filter(x => x !== 'to');")
        self.write("const val = filtered[3];")
        self.write("const grid = scene.getObjectByName('_grid');")
        self.write("const floor = scene.getObjectByName('_floor');")
        # Save previous state for undo
        self.write("const prevFloor = _config.floor;")
        self.write("const prevFloorColor = _config.floorColor;")
        self.write("const prevGridVis = grid ? grid.visible : false;")
        self.write("const prevFloorVis = floor ? floor.visible : false;")
        self.write("const prevFloorHex = floor && floor.material ? floor.material.color.getHex() : 0x333333;")
        self.write("if (val === 'on' || val === 'true' || val === '1') {")
        self.indent()
        self.write("_config.floor = true;")
        self.write("if (grid) grid.visible = true;")
        self.write("pushUndo('set config floor on', () => { _config.floor = prevFloor; if (grid) grid.visible = prevGridVis; if (floor) floor.visible = prevFloorVis; }, () => { _config.floor = true; if (grid) grid.visible = true; });")
        self.write("log('Floor grid visible', 'ok');")
        self.dedent()
        self.write("} else if (val === 'off' || val === 'false' || val === '0') {")
        self.indent()
        self.write("_config.floor = false;")
        self.write("if (grid) grid.visible = false;")
        self.write("if (floor) floor.visible = false;")
        self.write("pushUndo('set config floor off', () => { _config.floor = prevFloor; if (grid) grid.visible = prevGridVis; if (floor) floor.visible = prevFloorVis; }, () => { _config.floor = false; if (grid) grid.visible = false; if (floor) floor.visible = false; });")
        self.write("log('Floor hidden', 'ok');")
        self.dedent()
        self.write("} else {")
        self.indent()
        self.write("// Treat as color: set config floor to red/blue/#ff0000")
        self.write("const knownColors = {red:0xff0000, green:0x00ff00, blue:0x0000ff, yellow:0xffff00, cyan:0x00ffff, magenta:0xff00ff, white:0xffffff, black:0x111111, orange:0xff8800, purple:0x8800ff, pink:0xff88ff, gray:0x888888, brown:0x8b4513};")
        self.write("let color = knownColors[val];")
        self.write("if (!color && val && val.startsWith('#')) color = parseInt(val.slice(1), 16);")
        self.write("if (color !== undefined) {")
        self.indent()
        self.write("_config.floorColor = color;")
        self.write("_config.floor = true;")
        self.write("if (grid) grid.visible = false;")  # Hide grid when using solid floor
        self.write("if (floor) { floor.material.color.setHex(color); floor.visible = true; }")
        self.write("pushUndo('set config floor ' + val, () => { _config.floor = prevFloor; _config.floorColor = prevFloorColor; if (grid) grid.visible = prevGridVis; if (floor) { floor.material.color.setHex(prevFloorHex); floor.visible = prevFloorVis; } }, () => { _config.floor = true; _config.floorColor = color; if (grid) grid.visible = false; if (floor) { floor.material.color.setHex(color); floor.visible = true; } });")
        self.write("log('Floor color: #' + color.toString(16).padStart(6, '0'), 'ok');")
        self.dedent()
        self.write("} else log('Usage: set config floor to on/off/<color>', 'err');")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")

        # Set config confirm on/off - toggle confirmation for bulk ops
        self.write("else if (parts[0] === 'set' && parts[1] === 'config' && parts[2] === 'confirm') {")
        self.indent()
        self.write("const filtered = parts.filter(x => x !== 'to');")
        self.write("const val = filtered[3];")
        self.write("if (val === 'on' || val === 'true' || val === '1') {")
        self.indent()
        self.write("_config.confirm = true;")
        self.write("log('Confirmation enabled for bulk operations (>= 10)', 'ok');")
        self.dedent()
        self.write("} else if (val === 'off' || val === 'false' || val === '0') {")
        self.indent()
        self.write("_config.confirm = false;")
        self.write("log('Confirmation disabled - bulk ops execute immediately', 'ok');")
        self.dedent()
        self.write("} else log('Usage: set config confirm to on/off', 'err');")
        self.dedent()
        self.write("}")

        # Set all - bulk operation on selected objects
        self.write("else if (parts[0] === 'set' && parts[1] === 'all' && parts.length >= 4) {")
        self.indent()
        self.write("if (currentSelection.length === 0) { log('No objects selected. Use \"get all <type>\" first', 'warn'); return; }")
        self.write("const filtered = parts.slice(2).filter(x => x !== 'to');")
        self.write("const prop = filtered[0];")
        self.write("const valueTokens = filtered.slice(1);")
        self.write("if (!prop || !valueTokens.length) { log('Usage: set all <property> to <value>', 'err'); return; }")
        self.write("let count = 0;")
        self.write("const undoOps = [];")
        self.write("for (const obj of currentSelection) {")
        self.indent()
        # Try core set first, then capability bridge
        self.write("let result = handleCoreSet(obj, prop, valueTokens);")
        self.write("if (!result.ok) result = applyCapabilityBridge(obj, prop, valueTokens);")
        self.write("if (result.ok) { undoOps.push({ undo: result.undo, redo: result.redo }); count++; }")
        self.dedent()
        self.write("}")
        self.write("if (count > 0) {")
        self.indent()
        self.write("pushUndo('set all ' + currentSelectionType + ' ' + prop, () => undoOps.forEach(op => op.undo()), () => undoOps.forEach(op => op.redo()));")
        self.write("log('Set ' + prop + ' on ' + count + ' ' + currentSelectionType + '(s)', 'ok');")
        self.dedent()
        self.write("} else log('No objects modified', 'warn');")
        self.dedent()
        self.write("}")

        # Set - handles: set obj prop val, set obj prop to val, set prop val (with current obj)
        # Also supports deep search: "set pink box y to 10" → finds pink box via deep search
        self.write("else if (parts[0] === 'set' && parts.length >= 3) {")
        self.indent()
        self.write("const filtered = parts.filter(x => x !== 'to');")
        self.write("let obj = null;")
        self.write("let prop = null;")
        self.write("let valueTokens = [];")
        self.write("if (filtered.length >= 4) {")
        self.indent()
        self.write("// Prefer gameObjects lookup (updated when models load) over scene.getObjectByName")
        self.write("const candidate = gameObjects[filtered[1]] || scene.getObjectByName(filtered[1]);")
        self.write("if (candidate) {")
        self.indent()
        self.write("obj = candidate;")
        self.write("prop = filtered[2];")
        self.write("valueTokens = filtered.slice(3);")
        self.dedent()
        self.write("} else if (filtered.length >= 5) {")
        self.indent()
        # Deep search: "set pink box y to 10" → filtered = ['set', 'pink', 'box', 'y', '10']
        self.write("// Deep search for 'color shape' pattern")
        self.write("const knownColors = {red:1, green:1, blue:1, yellow:1, cyan:1, magenta:1, white:1, black:1, orange:1, purple:1, pink:1, gray:1, grey:1};")
        self.write("const shapeSynonyms = {box:'cube', cube:'cube', ball:'sphere', sphere:'sphere', cylinder:'cylinder', tube:'cylinder', cone:'cone', torus:'torus'};")
        self.write("const w1 = filtered[1].toLowerCase(), w2 = filtered[2].toLowerCase();")
        self.write("if ((knownColors[w1] && shapeSynonyms[w2]) || (shapeSynonyms[w1] && knownColors[w2])) {")
        self.indent()
        self.write("const targetColor = knownColors[w1] ? w1 : w2;")
        self.write("const targetShape = shapeSynonyms[w1] ? shapeSynonyms[w1] : shapeSynonyms[w2];")
        self.write("let found = null;")
        self.write("scene.traverse(child => {")
        self.indent()
        self.write("if (found || !child.isMesh || !child.name || child.name.startsWith('_')) return;")
        self.write("const cType = getTypeName(child), cColor = getColorName(child);")
        self.write("if (cType.includes(targetShape) && cColor === targetColor) found = child;")
        self.dedent()
        self.write("});")
        self.write("if (found) {")
        self.indent()
        self.write("obj = found;")
        self.write("prop = filtered[3];")
        self.write("valueTokens = filtered.slice(4);")
        self.write("log('[deep search] Using ' + found.name, 'ok');")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")
        self.write("if (!obj && currentObject) {")
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
        self.write("if (coreResult.ok) {")
        self.indent()
        self.write("pushUndo(coreResult.description, coreResult.undo, coreResult.redo);")
        self.write("log('OK', 'ok');")
        self.write("return;")
        self.dedent()
        self.write("}")
        self.write("const capResult = applyCapabilityBridge(obj, prop, valueTokens);")
        self.write("if (capResult.ok) {")
        self.indent()
        self.write("pushUndo(capResult.description, capResult.undo, capResult.redo);")
        self.write("log('OK', 'ok');")
        self.write("return;")
        self.dedent()
        self.write("}")
        self.write("if (capResult.reason === 'unknown' && CAPABILITY_POLICY.allow_passthrough) {")
        self.indent()
        self.write("const passthroughValue = coerceSingleValue(valueTokens);")
        self.write("if (!obj.userData) obj.userData = {};")
        self.write("const hadPrev = Object.prototype.hasOwnProperty.call(obj.userData, prop);")
        self.write("const prev = hadPrev ? obj.userData[prop] : undefined;")
        self.write("const next = passthroughValue;")
        self.write("obj.userData[prop] = next;")
        self.write("const desc = `${obj.name || '(object)'}.userData.${prop}`;")
        self.write("pushUndo(desc, () => {")
        self.indent()
        self.write("if (!obj || !obj.userData) return;")
        self.write("if (hadPrev) obj.userData[prop] = prev; else delete obj.userData[prop];")
        self.dedent()
        self.write("}, () => { obj.userData[prop] = next; });")
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

        # Inspect/Look/Examine (x, ex are shorthands)
        self.write("else if ((parts[0] === 'inspect' || parts[0] === 'look' || parts[0] === 'examine' || parts[0] === 'x' || parts[0] === 'ex') && parts[1]) {")
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
        self.write("if (obj.userData.description) log('  description: ' + obj.userData.description);")
        self.write("for (const [k, v] of Object.entries(obj.userData)) { if (!k.startsWith('_')) log('  ' + k + ': ' + v); }")
        self.write("const caps = availableCapabilitiesFor(obj);")
        self.write("if (caps.length) {")
        self.indent()
        self.write("log('  capabilities:', 'cyan');")
        self.write("caps.forEach(cap => log('    ' + describeCapability(cap), 'cyan'));")
        self.dedent()
        self.write("}")
        self.write("// Show 3D model credit if available")
        self.write("if (obj.userData._credit) log('  credit: ' + obj.userData._credit, 'dim');")
        self.dedent()
        self.write("} else {")
        self.indent()
        self.write("// Suggest similar object names")
        self.write("const allNames = getObjectNames();")
        self.write("const suggestions = allNames.filter(n => n.includes(parts[1]) || parts[1].includes(n.substring(0, Math.min(n.length, parts[1].length))));")
        self.write("if (suggestions.length > 0 && suggestions.length <= 5) {")
        self.indent()
        self.write("log('Object not found: ' + parts[1], 'err');")
        self.write("log('Did you mean: ' + suggestions.join(', ') + '?', 'cyan');")
        self.dedent()
        self.write("} else {")
        self.indent()
        self.write("// Try Levenshtein-based fuzzy match with lower threshold")
        self.write("const fuzzyResult = fuzzyMatch(parts[1], allNames, 0.3);")
        self.write("if (fuzzyResult && fuzzyResult.match) {")
        self.indent()
        self.write("log('Object not found: ' + parts[1], 'err');")
        self.write("log('Did you mean: ' + fuzzyResult.match + '?', 'cyan');")
        self.dedent()
        self.write("} else {")
        self.indent()
        self.write("log('Object not found: ' + parts[1], 'err');")
        self.write("if (allNames.length > 0) log('Available: ' + allNames.slice(0, 10).join(', ') + (allNames.length > 10 ? '...' : ''), 'dim');")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")

        # Camera
        self.write("else if (parts[0] === 'camera' && parts[1] === 'reset') {")
        self.indent()
        self.write("camera.position.set(0, 5, 50); controls.target.set(0, 0, 0); log('Camera reset', 'ok');")
        self.dedent()
        self.write("}")

        # Redraw - recreate all typed objects with current config settings
        self.write("else if (parts[0] === 'redraw') {")
        self.indent()
        self.write("// Collect all objects with _type (user-created known objects)")
        self.write("const toRedraw = [];")
        self.write("scene.traverse(o => {")
        self.indent()
        self.write("if (o.userData && o.userData._type) {")
        self.indent()
        self.write("toRedraw.push({ name: o.name, type: o.userData._type, pos: o.position.clone() });")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("});")
        self.write("if (toRedraw.length === 0) { log('No typed objects to redraw', 'warn'); return; }")
        self.write("log('Redrawing ' + toRedraw.length + ' object(s) with current settings...', 'dim');")
        self.write("// Delete old objects")
        self.write("toRedraw.forEach(item => {")
        self.indent()
        self.write("const old = scene.getObjectByName(item.name);")
        self.write("if (old) scene.remove(old);")
        self.dedent()
        self.write("});")
        self.write("// Recreate with current config settings")
        self.write("toRedraw.forEach(item => {")
        self.indent()
        self.write("const preset = KNOWN_OBJECTS[item.type] || { shape: 'box', color: 0x00ff00 };")
        self.write("if (preset.model && _config.useModels) {")
        self.indent()
        self.write("gltfLoader.load(preset.model, (gltf) => {")
        self.indent()
        self.write("const model = gltf.scene;")
        self.write("model.name = item.name;")
        self.write("model.userData._type = item.type;")
        self.write("if (preset.credit) model.userData._credit = preset.credit;")
        self.write("const box = new THREE.Box3().setFromObject(model);")
        self.write("const modelSize = box.getSize(new THREE.Vector3());")
        self.write("const maxDim = Math.max(modelSize.x, modelSize.y, modelSize.z);")
        self.write("const normalizeScale = maxDim > 0 ? 1 / maxDim : 1;")
        self.write("const sx = preset.scaleX || 1, sy = preset.scaleY || 1, sz = preset.scaleZ || 1;")
        self.write("const gs = _config.modelScale || 2;")
        self.write("model.scale.set(normalizeScale * sx * gs, normalizeScale * sy * gs, normalizeScale * sz * gs);")
        self.write("model.position.copy(item.pos);")
        self.write("scene.add(model);")
        self.dedent()
        self.write("});")
        self.dedent()
        self.write("} else {")
        self.indent()
        self.write("let geom = preset.shape === 'sphere' ? new THREE.SphereGeometry(1) : preset.shape === 'cylinder' ? new THREE.CylinderGeometry(0.5, 0.5, 1) : new THREE.BoxGeometry(1, 1, 1);")
        self.write("const mat = new THREE.MeshStandardMaterial({color: preset.color});")
        self.write("const mesh = new THREE.Mesh(geom, mat);")
        self.write("mesh.name = item.name;")
        self.write("mesh.userData._type = item.type;")
        self.write("if (preset.scaleX || preset.scaleY || preset.scaleZ) mesh.scale.set(preset.scaleX || 1, preset.scaleY || 1, preset.scaleZ || 1);")
        self.write("mesh.position.copy(item.pos);")
        self.write("scene.add(mesh);")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("});")
        self.write("log('Redrawn ' + toRedraw.length + ' object(s)', 'ok');")
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

        # Credits
        self.write("else if (parts[0] === 'credits') {")
        self.indent()
        self.write(f"log('Rosh v{__version__}', 'cyan');")
        self.write("log('Copyright (c) 2026 Roger Dubar');")
        self.write("log('https://rosh.cloud', 'dim');")
        self.dedent()
        self.write("}")

        # Edit mode - enables selection and object control
        self.write("else if (parts[0] === 'edit') {")
        self.indent()
        self.write("const arg = parts[1] ? parts[1].toLowerCase() : '';")
        self.write("if (arg === 'on') {")
        self.indent()
        self.write("editMode = true;")
        self.write("log('Edit mode ON - click to select objects, arrow keys to move', 'ok');")
        self.dedent()
        self.write("} else if (arg === 'off') {")
        self.indent()
        self.write("editMode = false;")
        self.write("selectedObject = null;")
        self.write("log('Edit mode OFF - view only', 'ok');")
        self.dedent()
        self.write("} else {")
        self.indent()
        self.write("log('Edit mode: ' + (editMode ? 'ON' : 'OFF'), 'dim');")
        self.write("log('Usage: edit on | edit off', 'dim');")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")

        # Usage hints for commands without arguments
        self.write("else if (parts[0] === 'set' && parts.length < 3) {")
        self.indent()
        self.write("log('set - Set object properties', 'cyan');")
        self.write("log('Usage:', 'dim');")
        self.write("log('  set <object> <property> to <value>');")
        self.write("log('  set ball color to red');")
        self.write("log('  set logo x to 100');")
        self.dedent()
        self.write("}")
        self.write("else if (parts[0] === 'get' && parts.length < 2) {")
        self.indent()
        self.write("log('get - Get object properties or select objects', 'cyan');")
        self.write("log('Usage:', 'dim');")
        self.write("log('  get <object> <property>');")
        self.write("log('  get all <type>  # select all of type');")
        self.dedent()
        self.write("}")
        self.write("else if (parts[0] === 'create' && parts.length < 2) {")
        self.indent()
        self.write("log('create - Create objects', 'cyan');")
        self.write("log('Usage:', 'dim');")
        self.write("log('  create <name>           # create object');")
        self.write("log('  create <type> <name>    # create named object of type');")
        self.write("log('  create big red ball     # create with modifiers');")
        self.write("log('Type \"help create\" for known object types', 'dim');")
        self.dedent()
        self.write("}")
        self.write("else if (parts[0] === 'clone' && parts.length < 2) {")
        self.indent()
        self.write("log('clone - Clone existing objects', 'cyan');")
        self.write("log('Usage:', 'dim');")
        self.write("log('  clone <object>          # auto-named copy');")
        self.write("log('  clone <object> as <name>');")
        self.dedent()
        self.write("}")
        self.write("else if (parts[0] === 'delete' && parts.length < 2) {")
        self.indent()
        self.write("log('delete - Remove objects', 'cyan');")
        self.write("log('Usage:', 'dim');")
        self.write("log('  delete <object>');")
        self.dedent()
        self.write("}")
        self.write("else if (parts[0] === 'move' && parts.length < 2) {")
        self.indent()
        self.write("log('move - Move objects to coordinates', 'cyan');")
        self.write("log('Usage:', 'dim');")
        self.write("log('  move <object> to x, y, z');")
        self.write("log('  move ball to 0, 5, 0');")
        self.dedent()
        self.write("}")
        self.write("else if (parts[0] === 'make' && parts.length < 2) {")
        self.indent()
        self.write("log('make - Adjust object properties naturally', 'cyan');")
        self.write("log('Usage:', 'dim');")
        self.write("log('  make <object> bigger/smaller');")
        self.write("log('  make <object> <color>');")
        self.write("log('  make <object> visible/hidden');")
        self.dedent()
        self.write("}")
        self.write("else if ((parts[0] === 'look' || parts[0] === 'examine' || parts[0] === 'x' || parts[0] === 'ex') && parts.length < 2) {")
        self.indent()
        self.write("log('look/examine/x/ex - Inspect objects', 'cyan');")
        self.write("log('Usage:', 'dim');")
        self.write("log('  look <object>');")
        self.write("log('  examine ball');")
        self.write("log('  x ball   (shorthand)');")
        self.write("log('  ex ball  (shorthand)');")
        self.dedent()
        self.write("}")
        self.write("else if (parts[0] === 'save' && parts.length < 2) {")
        self.indent()
        self.write("log('save - Save game state', 'cyan');")
        self.write("log('Usage:', 'dim');")
        self.write("log('  save <slot>');")
        self.write("log('  save 1');")
        self.dedent()
        self.write("}")
        self.write("else if (parts[0] === 'load' && parts.length < 2) {")
        self.indent()
        self.write("log('load - Load game state', 'cyan');")
        self.write("log('Usage:', 'dim');")
        self.write("log('  load <slot>');")
        self.write("log('  load 1');")
        self.dedent()
        self.write("}")

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
                # Use roshLog if available, otherwise queue for later
                return f"if (typeof window.roshLog === 'function') {{ window.roshLog({expr}); }} else {{ (window._roshPendingLogs = window._roshPendingLogs || []).push({expr}); }}"
            return ""
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

        elif action_type == 'get':
            # Query syntax: get all [type] [where condition]
            return self._emit_get_action(params)

        elif action_type == 'destroy':
            target = params.get('target', '')
            confirmed = params.get('confirmed', False)
            # Bulk destroy on selection
            if target == 'selection':
                if confirmed:
                    return """
                    if (window._selection && window._selection.length > 0) {
                        const count = window._selection.length;
                        window._selection.forEach(obj => { if (obj && obj.parent) obj.parent.remove(obj); });
                        window._selection = [];
                        console.log('destroyed ' + count + ' objects');
                    }""".strip().replace('\n                    ', '\n')
                else:
                    return """
                    if (window._selection && window._selection.length > 0) {
                        console.warn('warning: destroy affects ' + window._selection.length + ' objects. Use "destroy confirmed" to proceed.');
                    } else {
                        console.log('no objects selected');
                    }""".strip().replace('\n                    ', '\n')
            return f"if ({target} && {target}.parent) {{ {target}.parent.remove({target}); {target} = null; }}"

        return f"// TODO: {action_type}"

    def _emit_get_action(self, params: Dict) -> str:
        """Emit get action with query filtering.

        Populates window._selection with matching objects.
        Supports:
        - get all where <condition>
        - get all <type> where <condition>
        - get all including hidden where <condition>
        """
        target = params.get('target')  # Type filter (e.g., 'enemy')
        get_all = params.get('all', False)
        filter_expr = params.get('filter')  # IR_Expression for where condition
        include_hidden = params.get('include_hidden', False)

        # Build the filter function
        lines = ["window._selection = Object.values(window._objects || {})"]

        # Filter by type if specified
        if target:
            target_name = self.emit_expression(target) if hasattr(target, 'type') else f"'{target}'"
            # Handle string literal
            if isinstance(target_name, str) and target_name.startswith("'"):
                type_name = target_name.strip("'")
            else:
                type_name = target_name
            lines[0] += f".filter(obj => obj.userData && obj.userData._type === '{type_name}')"

        # Filter hidden objects
        if not include_hidden:
            lines[0] += ".filter(obj => !(obj.userData && obj.userData._hidden))"

        # Apply where condition
        if filter_expr:
            condition_code = self._emit_filter_condition(filter_expr)
            lines[0] += f".filter(obj => {condition_code})"

        lines.append("console.log('selected ' + window._selection.length + ' objects');")

        return "; ".join(lines)

    def _emit_filter_condition(self, expr) -> str:
        """Emit a filter condition for use in .filter(obj => ...)"""
        if expr.type == 'comparison':
            left = self._emit_filter_expression(expr.left)
            right = self._emit_filter_expression(expr.right)
            op = expr.operator
            return f"({left} {op} {right})"
        elif expr.type == 'binary_op':
            left = self._emit_filter_condition(expr.left)
            right = self._emit_filter_condition(expr.right)
            op = expr.operator
            if op == 'and':
                op = '&&'
            elif op == 'or':
                op = '||'
            return f"({left} {op} {right})"
        elif expr.type == 'unary_op':
            right = self._emit_filter_condition(expr.right)
            if expr.operator == 'not':
                return f"(!{right})"
            return f"({expr.operator}{right})"
        else:
            return self._emit_filter_expression(expr)

    def _emit_filter_expression(self, expr) -> str:
        """Emit expression for filter context (obj.userData.prop instead of global)"""
        if hasattr(expr, 'type'):
            if expr.type == 'property_access':
                # In filter context, use obj.userData.property
                prop = expr.right
                return f"(obj.userData && obj.userData.{prop})"
            elif expr.type == 'literal':
                if hasattr(expr, 'value') and hasattr(expr.value, 'value'):
                    val = expr.value.value
                    if isinstance(val, str):
                        return f"'{val}'"
                    return str(val)
                return self.emit_expression(expr)
        # Identifier in filter context - treat as userData property
        if hasattr(expr, 'value') and hasattr(expr.value, 'value'):
            val = expr.value.value
            if isinstance(val, str):
                return f"(obj.userData && obj.userData.{val})"
            return str(val)
        return self.emit_expression(expr)

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
            elif val.type == 'expression':
                # Try to evaluate simple expressions like unary minus
                return self._eval_simple_expr(val.value, default)
        return default

    def _eval_simple_expr(self, expr, default: float) -> float:
        """Evaluate simple IR expressions (unary minus, literals)."""
        if not hasattr(expr, 'type'):
            if isinstance(expr, (int, float)):
                return float(expr)
            return default

        if expr.type == 'unary_op' and expr.operator == '-':
            # Unary minus: -value
            inner = self._eval_simple_expr(expr.right, default)
            return -inner
        elif expr.type == 'literal':
            # Literal value wrapped in IR_Value
            if hasattr(expr.value, 'value'):
                return float(expr.value.value)
            elif isinstance(expr.value, (int, float)):
                return float(expr.value)
        elif hasattr(expr, 'value') and isinstance(expr.value, (int, float)):
            return float(expr.value)
        return default

    def _get_prop_string(self, obj: IR_Object, prop: str, default: str) -> str:
        """Get string property value."""
        if prop in obj.properties:
            val = obj.properties[prop]
            if val.type == 'string':
                return val.value
        return default

    def _get_prop_number(self, obj: IR_Object, prop: str, default: float) -> float:
        """Get numeric property value."""
        if prop in obj.properties:
            val = obj.properties[prop]
            if val.type == 'number':
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
