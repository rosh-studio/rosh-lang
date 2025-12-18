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

from typing import Dict, Any, Set, List
from .base import BaseEmitter
from ..ir import (
    IR_Program, IR_Object, IR_Event, IR_Action, IR_Function,
    IR_Value, IR_Expression, IR_Conditional, IR_Loop
)


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

        # Scan IR to detect features
        self._detect_features()

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
        self._emit_header()
        self._emit_scene_setup()
        self._emit_objects()
        if self.uses_scenes:
            self._emit_scene_visibility_function()
        if self.uses_save_load:
            self._emit_save_load_functions()
        self._emit_functions()
        self._emit_event_handlers()
        self._emit_animation_loop()
        self._emit_resize_handler()
        self._emit_repl_console()

        return self.get_code()

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

        if is_hud:
            # HUD objects are text sprites that display lives/score
            target = next((t for h, t in self.hud_objects if h == name), 'player')
            self._emit_hud_sprite(name, target, world_x, world_y, world_z)
        elif is_text:
            text = self._get_prop_string(obj, 'text', name)
            self._emit_text_sprite(name, text, color, world_x, world_y, world_z)
        elif 'sprite' in obj.properties:
            sprite = obj.properties['sprite'].value
            self._emit_textured_plane(name, sprite, world_x, world_y, world_z, width, height)
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

        # Custom properties in userData
        known = {'x', 'y', 'z', 'width', 'height', 'depth', 'color', 'shape', 'radius', 'text', 'sprite', 'visible'}
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
        self.write(f"scene.add({name});")

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
        self.write(f"scene.add({name});")

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

    # =========================================================================
    # Animation Loop
    # =========================================================================

    def _emit_animation_loop(self):
        """Emit the Three.js animation loop."""
        self.write_comment("Animation Loop")
        self.write("function animate() {")
        self.indent()
        self.write("requestAnimationFrame(animate);")
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
        self.write("#rosh-input-line { padding: 10px; border-top: 1px solid #0f0; display: flex; gap: 8px; }")
        self.write("#rosh-input-line input { flex: 1; background: #111; border: 1px solid #0f0;")
        self.write("  color: #0f0; padding: 8px; font-family: inherit; }")
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
        self.write("    <input type='text' id='rosh-input' placeholder='help for commands' autocomplete='off'>")
        self.write("  </div>`;")
        self.write("document.body.appendChild(consoleDiv);")
        self.write_blank()

        # Logic
        self.write("const output = document.getElementById('rosh-output');")
        self.write("const input = document.getElementById('rosh-input');")
        self.write("let currentObject = null, currentObjectName = null;")
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

        # execCommand function
        self._emit_exec_command()

        # Key handlers
        self.write("document.addEventListener('keydown', e => {")
        self.indent()
        self.write("if (e.key === '`') { e.preventDefault(); toggleConsole(); }")
        self.dedent()
        self.write("});")
        self.write_blank()

        # Input handler
        self.write("input.addEventListener('keydown', e => {")
        self.indent()
        self.write("if (e.key === 'Enter' && input.value.trim()) {")
        self.indent()
        self.write("execCommand(input.value); input.value = '';")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("});")
        self.write_blank()

        self.write("log('Rosh Console ready! Type help for commands.', 'cyan');")

    def _emit_exec_command(self):
        """Emit the execCommand function for REPL."""
        self.write("function execCommand(cmd) {")
        self.indent()
        self.write("log('> ' + cmd, 'cmd');")
        self.write("const parts = cmd.trim().toLowerCase().split(/\\s+/);")
        self.write("try {")
        self.indent()

        # Help
        self.write("if (parts[0] === 'help') {")
        self.indent()
        self.write("log('Commands: list, get, set, inspect, save, load, camera reset', 'cyan');")
        self.dedent()
        self.write("}")

        # List
        self.write("else if (parts[0] === 'list') {")
        self.indent()
        self.write("log('Objects:', 'cyan');")
        self.write("scene.traverse(o => { if (o.name && !o.name.startsWith('_')) log('  ' + o.name); });")
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

        # Set
        self.write("else if (parts[0] === 'set' && parts.length >= 3) {")
        self.indent()
        self.write("let obj, prop, val;")
        self.write("if (parts.length === 3 && currentObject) { obj = currentObject; prop = parts[1]; val = parts[2]; }")
        self.write("else { obj = scene.getObjectByName(parts[1]); prop = parts[2]; val = parts[3]; }")
        self.write("if (!obj) { log('No object', 'err'); return; }")
        self.write("if (!isNaN(val)) val = parseFloat(val);")
        self.write("if (prop === 'x') obj.position.x = val;")
        self.write("else if (prop === 'y') obj.position.y = val;")
        self.write("else if (prop === 'z') obj.position.z = val;")
        self.write("else if (prop === 'visible') obj.visible = val === 'true';")
        self.write("else if (prop === 'color' && obj.material) obj.material.color.set(val);")
        self.write("else obj.userData[prop] = val;")
        self.write("log('OK', 'ok');")
        self.dedent()
        self.write("}")

        # Inspect
        self.write("else if ((parts[0] === 'inspect' || parts[0] === 'look') && parts[1]) {")
        self.indent()
        self.write("const obj = scene.getObjectByName(parts[1]);")
        self.write("if (obj) {")
        self.indent()
        self.write("log(parts[1] + ':', 'cyan');")
        self.write("log('  pos: [' + obj.position.x.toFixed(1) + ',' + obj.position.y.toFixed(1) + ',' + obj.position.z.toFixed(1) + ']');")
        self.write("if (obj.material && obj.material.color) log('  color: #' + obj.material.color.getHexString());")
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
        self.write("if (o.material && o.material.color) data._color = o.material.color.getHex();")
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
        self.write("const obj = scene.getObjectByName(name);")
        self.write("if (obj) {")
        self.indent()
        self.write("if (data.x !== undefined) obj.position.x = data.x;")
        self.write("if (data.y !== undefined) obj.position.y = data.y;")
        self.write("if (data.z !== undefined) obj.position.z = data.z;")
        self.write("if (data._color !== undefined && obj.material) obj.material.color.setHex(data._color);")
        self.write("if (data._sx !== undefined && obj.scale) { obj.scale.x = data._sx; obj.scale.y = data._sy; obj.scale.z = data._sz; }")
        self.write("if (data._visible !== undefined) obj.visible = data._visible;")
        self.write("Object.assign(obj.userData, data);")
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
