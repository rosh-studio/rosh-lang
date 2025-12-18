"""
Phaser 3 Emitter - IR to Phaser JavaScript

Converts IR representation to Phaser 3 JavaScript code.
This is a "mechanical translator" - all semantic decisions are in the IR.

Usage:
    from rosh.emitters.phaser import PhaserEmitter

    ir = transform_ast_to_ir(ast)
    emitter = PhaserEmitter(ir)
    js_code = emitter.emit()

See: rosh-dev/proposals/ROSH-IR-SPECIFICATION.md
"""

import re
from typing import Dict, Any, Set
from .base import BaseEmitter
from ..ir import (
    IR_Program, IR_Object, IR_Event, IR_Action, IR_Function,
    IR_Value, IR_Expression, IR_Conditional, IR_Loop
)


class PhaserEmitter(BaseEmitter):
    """Emit Phaser 3 JavaScript from Rosh IR.

    Generates a complete Phaser game including:
    - GameScene class with create() and update() methods
    - Object creation as rectangles or sprites
    - Event handlers mapped to Phaser events
    - Keyboard input handling
    """

    # Default object colors (for objects without explicit color)
    DEFAULT_COLORS = [
        0x00ff00, 0x0000ff, 0xff0000, 0xffff00,
        0xff00ff, 0x00ffff, 0xff8800, 0x8800ff,
    ]

    def __init__(self, ir: IR_Program, meta: Dict[str, Any] = None):
        super().__init__(ir, meta)
        self.color_index = 0
        self.sprite_assets: Set[str] = set()
        self.sound_assets: Set[str] = set()
        self.music_file: str = None
        self.needs_keyboard = False
        self.needs_update = False
        self.player_objects: Set[str] = set()
        self.collision_events: list = []  # [(obj_a, obj_b, handler_code), ...]
        self.hud_objects: list = []  # [(hud_name, target_name), ...]
        self.continuous_key_events: list = []  # [(key, handler_code), ...]

        # Scene/Level support (Roshonic "Dimensions, Not Modes")
        self.uses_scenes = False  # True if any object has scene/level
        self.scene_objects: Dict[str, list] = {}  # scene_name -> [obj_names]
        self.level_objects: Dict[int, list] = {}  # level_num -> [obj_names]

        # Save/Load support
        self.uses_save_load = False  # True if save/load commands used

        # Scan IR to detect features
        self._detect_features()

    def _detect_features(self):
        """Scan IR to detect what features are needed."""
        # Check objects for player type, sprites, HUD, and scene/level
        for obj in self.ir.objects:
            if obj.parent_type == 'player':
                self.player_objects.add(obj.name)
                self.needs_keyboard = True
                self.needs_update = True

            if 'sprite' in obj.properties:
                sprite_val = obj.properties['sprite']
                if sprite_val.type == 'string':
                    self.sprite_assets.add(sprite_val.value)

            # HUD objects have 'target' property
            if 'target' in obj.properties:
                target_val = obj.properties['target']
                target_name = target_val.value if hasattr(target_val, 'value') else str(target_val)
                self.hud_objects.append((obj.name, target_name))
                self.needs_update = True  # HUD needs update loop

            # Scene/Level tracking (Roshonic "Dimensions, Not Modes")
            if obj.scene is not None or obj.level is not None:
                self.uses_scenes = True
                if obj.scene is not None:
                    if obj.scene not in self.scene_objects:
                        self.scene_objects[obj.scene] = []
                    self.scene_objects[obj.scene].append(obj.name)
                if obj.level is not None:
                    if obj.level not in self.level_objects:
                        self.level_objects[obj.level] = []
                    self.level_objects[obj.level].append(obj.name)

        # Check events
        for event in self.ir.events:
            if event.trigger == 'update':
                self.needs_update = True
            elif event.trigger.startswith('keydown:') or event.trigger.startswith('keyup:'):
                self.needs_keyboard = True
            elif event.trigger.startswith('continuous:'):
                # Continuous key polling (while_key_left, etc.)
                self.needs_keyboard = True
                self.needs_update = True  # Need update loop for polling
            elif event.trigger.startswith('collision:'):
                # Collision events need update loop for AABB checks
                self.needs_update = True

            # Check for sound/music in event handlers
            self._scan_actions_for_assets(event.handler)

        # Check init actions
        self._scan_actions_for_assets(self.ir.init_actions)

        # Check functions for assets (e.g., fire_bullet playing sounds)
        for func in self.ir.functions:
            self._scan_actions_for_assets(func.body)

    def _scan_actions_for_assets(self, actions):
        """Scan actions for sound/music assets."""
        for action in actions:
            if isinstance(action, IR_Action):
                if action.type == 'play_sound':
                    self.sound_assets.add(action.params.get('asset', ''))
                elif action.type == 'play_music':
                    self.music_file = action.params.get('asset', '')

            elif isinstance(action, IR_Conditional):
                self._scan_actions_for_assets(action.then_actions)
                self._scan_actions_for_assets(action.else_actions)

            elif isinstance(action, IR_Loop):
                self._scan_actions_for_assets(action.body)

    def emit(self) -> str:
        """Generate complete Phaser 3 JavaScript code."""
        self._emit_header()
        self._emit_class_start()
        self._emit_constructor()

        if self.sprite_assets or self.sound_assets or self.music_file:
            self._emit_preload()

        self._emit_create()

        if self.needs_update or self.ir.events:
            self._emit_update()

        self._emit_helper_methods()
        self._emit_functions()
        self._emit_class_end()
        self._emit_game_config()

        return self.get_code()

    # =========================================================================
    # Structure Generation
    # =========================================================================

    def _emit_header(self):
        """Emit file header comment."""
        self.write_comment("Auto-generated from Rosh IR")
        self.write_comment("Emitter: Phaser 3 v0.2.0")
        self.write_blank()

    def _emit_class_start(self):
        """Emit class declaration."""
        self.write("class GameScene extends Phaser.Scene {")
        self.indent()

    def _emit_class_end(self):
        """Close class declaration."""
        self.dedent()
        self.write("}")
        self.write_blank()

    def _emit_constructor(self):
        """Emit constructor method."""
        self.write("constructor() {")
        self.indent()
        self.write("super({ key: 'GameScene' });")
        if self.ir.events or self.player_objects:
            self.write("this.eventHandlers = {};")
        # Scene/Level state (Roshonic "Dimensions, Not Modes")
        if self.uses_scenes:
            initial_scene = self.ir.metadata.initial_scene
            initial_level = self.ir.metadata.initial_level
            scene_str = f"'{initial_scene}'" if initial_scene else "null"
            self.write(f"this.currentScene = {scene_str};")
            self.write(f"this.currentLevel = {initial_level};")
        self.dedent()
        self.write("}")
        self.write_blank()

    def _emit_preload(self):
        """Emit preload method for assets."""
        self.write("preload() {")
        self.indent()

        for sprite in self.sprite_assets:
            key = self._asset_key(sprite)
            self.write(f"this.load.image('{key}', 'assets/{sprite}');")

        for sound in self.sound_assets:
            key = self._asset_key(sound)
            self.write(f"this.load.audio('{key}', 'assets/{sound}');")

        if self.music_file:
            key = self._asset_key(self.music_file)
            self.write(f"this.load.audio('{key}', 'assets/{self.music_file}');")

        self.dedent()
        self.write("}")
        self.write_blank()

    def _emit_create(self):
        """Emit create method with objects and init actions."""
        self.write("create() {")
        self.indent()

        # Set up keyboard if needed
        if self.needs_keyboard:
            self.write("this.cursors = this.input.keyboard.createCursorKeys();")
            self.write("this.keys = this.input.keyboard.addKeys('W,A,S,D,SPACE,R');")
            self.write_blank()

        # Create objects
        for obj in self.ir.objects:
            self._emit_create_object(obj)

        # Register event handlers
        self._emit_event_registrations()

        # Player auto-controls
        if self.player_objects:
            self._emit_player_controls()

        # Init actions
        for action in self.ir.init_actions:
            if action:
                code = self.emit_action(action)
                if code:
                    self.write(code)

        # Set initial scene/level visibility
        if self.uses_scenes:
            self.write_blank()
            self.write("// Set initial scene/level visibility")
            self.write("this.updateSceneVisibility();")

        self.dedent()
        self.write("}")
        self.write_blank()

    def _emit_update(self):
        """Emit update method."""
        self.write("update() {")
        self.indent()

        # Trigger update handlers
        self.write("this.triggerEvent('update');")

        # Player keyboard handling
        if self.player_objects:
            for player in self.player_objects:
                self.write(f"this.handlePlayerInput(this.{player});")

        # Continuous key polling (while_key_* handlers)
        if self.continuous_key_events:
            self.write_blank()
            self.write("// Continuous key handlers")
            for key, handler_code in self.continuous_key_events:
                condition = self._get_key_condition(key)
                self.write(f"if ({condition}) {{ {handler_code} }}")

        # Collision detection (simple AABB)
        if self.collision_events:
            self.write_blank()
            self.write("// Collision detection")
            for obj_a, obj_b, handler_code in self.collision_events:
                self.write(f"if (this.{obj_a} && this.{obj_b} && this.checkCollision(this.{obj_a}, this.{obj_b})) {{")
                self.indent()
                self.write(handler_code)
                self.dedent()
                self.write("}")

        # HUD updates
        if self.hud_objects:
            self.write_blank()
            self.write("// Update HUD")
            for hud_name, target in self.hud_objects:
                # Find target object to check what properties it has
                target_obj = None
                for o in self.ir.objects:
                    if o.name == target:
                        target_obj = o
                        break
                if target_obj and 'lives' in target_obj.properties:
                    self.write(f"if (this.{hud_name}_lives) this.{hud_name}_lives.setText('Lives: ' + this.{target}.lives);")
                if target_obj and 'score' in target_obj.properties:
                    self.write(f"if (this.{hud_name}_score) this.{hud_name}_score.setText('Score: ' + this.{target}.score);")

        self.dedent()
        self.write("}")
        self.write_blank()

    def _emit_helper_methods(self):
        """Emit helper methods for event system."""
        if not (self.ir.events or self.player_objects):
            return

        # registerEvent
        self.write("registerEvent(name, handler) {")
        self.indent()
        self.write("if (!this.eventHandlers[name]) {")
        self.indent()
        self.write("this.eventHandlers[name] = [];")
        self.dedent()
        self.write("}")
        self.write("this.eventHandlers[name].push(handler);")
        self.dedent()
        self.write("}")
        self.write_blank()

        # triggerEvent
        self.write("triggerEvent(name, ...args) {")
        self.indent()
        self.write("if (this.eventHandlers[name]) {")
        self.indent()
        self.write("for (const handler of this.eventHandlers[name]) {")
        self.indent()
        self.write("handler.call(this, ...args);")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")
        self.write_blank()

        # handlePlayerInput (if needed)
        if self.player_objects:
            self._emit_player_input_method()

        # checkCollision (if needed)
        if self.collision_events:
            self._emit_collision_helper()

        # updateSceneVisibility (if using scenes/levels)
        if self.uses_scenes:
            self._emit_scene_visibility_helper()

        # Save/Load helpers
        if self.uses_save_load:
            self._emit_save_load_helpers()

    def _emit_player_input_method(self):
        """Emit player input handling method."""
        self.write("handlePlayerInput(player) {")
        self.indent()
        self.write("if (!player || !player.speed) return;")
        self.write("const speed = player.speed;")
        self.write_blank()
        self.write("if (this.cursors.left.isDown || this.keys.A.isDown) {")
        self.indent()
        self.write("player.x -= speed;")
        self.dedent()
        self.write("}")
        self.write("if (this.cursors.right.isDown || this.keys.D.isDown) {")
        self.indent()
        self.write("player.x += speed;")
        self.dedent()
        self.write("}")
        self.write("if (this.cursors.up.isDown || this.keys.W.isDown) {")
        self.indent()
        self.write("player.y -= speed;")
        self.dedent()
        self.write("}")
        self.write("if (this.cursors.down.isDown || this.keys.S.isDown) {")
        self.indent()
        self.write("player.y += speed;")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")
        self.write_blank()

    def _emit_collision_helper(self):
        """Emit simple AABB collision check method."""
        self.write("checkCollision(a, b) {")
        self.indent()
        self.write("// Simple AABB rectangle overlap")
        self.write("const aw = a.width || 40;")
        self.write("const ah = a.height || 30;")
        self.write("const bw = b.width || 40;")
        self.write("const bh = b.height || 30;")
        self.write("return a.x - aw/2 < b.x + bw/2 &&")
        self.write("       a.x + aw/2 > b.x - bw/2 &&")
        self.write("       a.y - ah/2 < b.y + bh/2 &&")
        self.write("       a.y + ah/2 > b.y - bh/2;")
        self.dedent()
        self.write("}")
        self.write_blank()

    def _emit_scene_visibility_helper(self):
        """Emit helper to update object visibility based on current scene/level."""
        self.write("updateSceneVisibility() {")
        self.indent()
        self.write("// Roshonic \"Dimensions, Not Modes\" - scene/level as coordinates")

        # For each object with scene/level, generate visibility check
        for obj in self.ir.objects:
            if obj.scene is not None or obj.level is not None:
                checks = []
                if obj.scene is not None:
                    checks.append(f"this.currentScene === '{obj.scene}'")
                if obj.level is not None:
                    checks.append(f"this.currentLevel === {obj.level}")

                condition = " && ".join(checks)
                self.write(f"if (this.{obj.name}) this.{obj.name}.visible = ({condition});")

        self.dedent()
        self.write("}")
        self.write_blank()

    def _emit_save_load_helpers(self):
        """Emit save/load game methods using localStorage."""
        # Get list of saveable objects
        saveable_objects = [obj for obj in self.ir.objects if obj.saveable]

        # saveGame method
        self.write("saveGame(slot) {")
        self.indent()
        self.write("const saveData = {")
        self.indent()
        self.write("version: '1.0',")
        self.write("timestamp: new Date().toISOString(),")
        if self.uses_scenes:
            self.write("scene: this.currentScene,")
            self.write("level: this.currentLevel,")
        self.write("objects: {}")
        self.dedent()
        self.write("};")
        self.write_blank()

        # Save each saveable object's properties
        for obj in saveable_objects:
            self.write(f"if (this.{obj.name}) {{")
            self.indent()
            self.write(f"saveData.objects['{obj.name}'] = {{")
            self.indent()
            self.write(f"x: this.{obj.name}.x,")
            self.write(f"y: this.{obj.name}.y,")
            # Save custom properties
            for prop_name in obj.properties:
                if prop_name not in ('x', 'y', 'width', 'height', 'sprite', 'color', 'text', 'saveable'):
                    self.write(f"{prop_name}: this.{obj.name}.{prop_name},")
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

        # loadGame method
        self.write("loadGame(slot) {")
        self.indent()
        self.write("const json = localStorage.getItem('rosh_save_' + slot);")
        self.write("if (!json) { console.log('No save found in slot:', slot); return; }")
        self.write("const saveData = JSON.parse(json);")
        self.write_blank()

        # Restore scene/level
        if self.uses_scenes:
            self.write("if (saveData.scene !== undefined) this.currentScene = saveData.scene;")
            self.write("if (saveData.level !== undefined) this.currentLevel = saveData.level;")
            self.write("this.updateSceneVisibility();")
            self.write_blank()

        # Restore each object's properties
        self.write("const objects = saveData.objects || {};")
        for obj in saveable_objects:
            self.write(f"if (objects['{obj.name}'] && this.{obj.name}) {{")
            self.indent()
            self.write(f"const data = objects['{obj.name}'];")
            self.write(f"if (data.x !== undefined) this.{obj.name}.x = data.x;")
            self.write(f"if (data.y !== undefined) this.{obj.name}.y = data.y;")
            # Restore custom properties
            for prop_name in obj.properties:
                if prop_name not in ('x', 'y', 'width', 'height', 'sprite', 'color', 'text', 'saveable'):
                    self.write(f"if (data.{prop_name} !== undefined) this.{obj.name}.{prop_name} = data.{prop_name};")
            self.dedent()
            self.write("}")

        self.write_blank()
        self.write("console.log('Game loaded from slot:', slot);")
        self.dedent()
        self.write("}")
        self.write_blank()

    def _emit_functions(self):
        """Emit user-defined functions as class methods."""
        for func in self.ir.functions:
            self._emit_function(func)

    def _emit_function(self, func: IR_Function):
        """Emit a single function."""
        params = ", ".join(func.params)
        self.write(f"{func.name}({params}) {{")
        self.indent()

        for action in func.body:
            if action:
                code = self.emit_action(action)
                if code:
                    self.write(code)

        self.dedent()
        self.write("}")
        self.write_blank()

    def _emit_game_config(self):
        """Emit Phaser game configuration and initialization."""
        width = self.ir.metadata.canvas_width
        height = self.ir.metadata.canvas_height
        bg_color = self.meta.get('canvas', {}).get('background', '#1a1a2e')

        self.write("const config = {")
        self.indent()
        self.write("type: Phaser.AUTO,")
        self.write("parent: 'game-container',")
        self.write(f"width: {width},")
        self.write(f"height: {height},")
        self.write(f"backgroundColor: '{bg_color}',")
        self.write("scene: GameScene")
        self.dedent()
        self.write("};")
        self.write_blank()
        self.write("const game = new Phaser.Game(config);")

    # =========================================================================
    # Object Emission
    # =========================================================================

    def _emit_create_object(self, obj: IR_Object):
        """Emit code to create an object."""
        x = self._get_prop_value(obj, 'x', 0.5)
        y = self._get_prop_value(obj, 'y', 0.5)

        # Convert normalized to pixels
        px = self.to_target_x(x)
        py = self.to_target_y(y)

        # Check if this is a HUD object (has 'target' property)
        if 'target' in obj.properties:
            self._emit_hud_object(obj, px, py)
            return

        if 'text' in obj.properties:
            # Text object
            text = obj.properties['text'].value
            font_size = self._get_prop_value(obj, 'font_size', 16)
            color = self._get_color_css(obj)
            self.write(f"this.{obj.name} = this.add.text({px}, {py}, '{text}', {{ fontSize: '{int(font_size)}px', fill: '{color}' }});")
            self.write(f"this.{obj.name}.setOrigin(0.5, 0.5);")
            # Store font_size as custom property for animation access
            self.write(f"this.{obj.name}.font_size = {int(font_size)};")
        elif 'sprite' in obj.properties:
            # Sprite object
            sprite = obj.properties['sprite'].value
            key = self._asset_key(sprite)
            self.write(f"this.{obj.name} = this.add.sprite({px}, {py}, '{key}');")
            # Apply scaling if width/height specified
            if 'width' in obj.properties or 'height' in obj.properties:
                w = self._get_prop_value(obj, 'width', 0.05)
                h = self._get_prop_value(obj, 'height', 0.05)
                pw = self.to_target_width(w)
                ph = self.to_target_height(h)
                self.write(f"this.{obj.name}.setDisplaySize({pw}, {ph});")
        else:
            # Rectangle object
            w = self._get_prop_value(obj, 'width', 0.05)
            h = self._get_prop_value(obj, 'height', 0.05)
            pw = self.to_target_width(w)
            ph = self.to_target_height(h)
            color = self._get_color(obj)
            self.write(f"this.{obj.name} = this.add.rectangle({px}, {py}, {pw}, {ph}, {self.format_color(color)});")

        # Set additional properties
        skip_props = {'x', 'y', 'width', 'height', 'color', 'sprite', 'text', 'font_size'}
        for prop_name, prop_value in obj.properties.items():
            if prop_name not in skip_props:
                val = self.get_value(prop_value)
                if isinstance(val, bool):
                    # JavaScript uses lowercase booleans
                    self.write(f"this.{obj.name}.{prop_name} = {'true' if val else 'false'};")
                elif isinstance(val, str):
                    self.write(f"this.{obj.name}.{prop_name} = '{val}';")
                else:
                    self.write(f"this.{obj.name}.{prop_name} = {val};")

        self.write_blank()

    def _emit_hud_object(self, obj: IR_Object, px: float, py: float):
        """Emit HUD text objects showing lives/score of target."""
        target_val = obj.properties['target']
        target = target_val.value if hasattr(target_val, 'value') else str(target_val)

        self.write(f"// HUD for {target}")
        y_offset = py

        # Find target object to check what properties it has
        target_obj = None
        for o in self.ir.objects:
            if o.name == target:
                target_obj = o
                break

        # Create lives text if target has lives
        if target_obj and 'lives' in target_obj.properties:
            lives_default = target_obj.properties['lives'].value
            self.write(f"this.{obj.name}_lives = this.add.text({px}, {y_offset}, "
                      f"'Lives: ' + (this.{target}.lives || {lives_default}), "
                      f"{{ fontSize: '16px', fill: '#fff' }});")
            y_offset += 20

        # Create score text if target has score
        if target_obj and 'score' in target_obj.properties:
            score_default = target_obj.properties['score'].value
            self.write(f"this.{obj.name}_score = this.add.text({px}, {y_offset}, "
                      f"'Score: ' + (this.{target}.score || {score_default}), "
                      f"{{ fontSize: '16px', fill: '#fff' }});")

        self.write_blank()

    def emit_object(self, obj: IR_Object) -> str:
        """Generate code for object (called directly for testing)."""
        # Save current output
        old_output = self.output
        self.output = []

        self._emit_create_object(obj)

        result = self.get_code()
        self.output = old_output
        return result

    # =========================================================================
    # Event Emission
    # =========================================================================

    def _emit_event_registrations(self):
        """Emit event handler registrations."""
        for event in self.ir.events:
            handler_code = self._generate_handler_code(event)

            if event.trigger == 'update':
                self.write(f"this.registerEvent('update', function() {{ {handler_code} }});")
            elif event.trigger.startswith('keydown:'):
                key = event.trigger.split(':')[1].upper()
                key = self._map_phaser_key(key)
                self.write(f"this.input.keyboard.on('keydown-{key}', () => {{ {handler_code} }});")
            elif event.trigger.startswith('continuous:'):
                # Store for polling in update loop
                key = event.trigger.split(':')[1].upper()
                self.continuous_key_events.append((key, handler_code))
            elif event.trigger.startswith('collision:'):
                # Store collision events for AABB checking in update()
                parts = event.trigger.split(':')
                if len(parts) >= 3:
                    obj_a, obj_b = parts[1], parts[2]
                    self.collision_events.append((obj_a, obj_b, handler_code))
            elif event.trigger.startswith('custom:'):
                event_name = event.trigger.split(':')[1]
                self.write(f"this.registerEvent('{event_name}', function() {{ {handler_code} }});")
            elif event.trigger == 'init':
                # Init events run immediately
                self.write(handler_code)

        if self.ir.events:
            self.write_blank()

    def _generate_handler_code(self, event: IR_Event) -> str:
        """Generate inline handler code for an event."""
        actions = []
        for action in event.handler:
            if action:
                code = self.emit_action(action)
                if code:
                    actions.append(code)
        return " ".join(actions)

    def emit_event(self, event: IR_Event) -> str:
        """Generate code for event handler."""
        return self._generate_handler_code(event)

    # =========================================================================
    # Action Emission
    # =========================================================================

    def emit_action(self, action) -> str:
        """Generate code for an action."""
        if isinstance(action, IR_Conditional):
            return self._emit_conditional_inline(action)
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
            key = self._asset_key(params.get('asset', ''))
            return f"this.sound.play('{key}');"
        elif action_type == 'play_music':
            key = self._asset_key(params.get('asset', ''))
            return f"if (!this.bgMusic || !this.bgMusic.isPlaying) {{ this.bgMusic = this.sound.add('{key}', {{ loop: true }}); this.bgMusic.play(); }}"
        elif action_type == 'stop_music':
            return "if (this.bgMusic) { this.bgMusic.stop(); }"
        elif action_type == 'trigger':
            event_name = params.get('event', '')
            return f"this.triggerEvent('{event_name}');"
        elif action_type == 'destroy':
            target = params.get('target', '')
            return f"if (this.{target}) {{ this.{target}.destroy(); this.{target} = null; }}"
        elif action_type == 'return':
            value = params.get('value')
            if value:
                return f"return {self.emit_expression(value)};"
            return "return;"
        elif action_type == 'break':
            return "break;"
        elif action_type == 'continue':
            return "continue;"
        elif action_type == 'call':
            func_name = params.get('function', '')
            args = params.get('args', [])
            arg_strs = [self.emit_expression(a) for a in args]
            return f"this.{func_name}({', '.join(arg_strs)});"
        elif action_type == 'goto':
            # Scene/Level navigation (Roshonic "Dimensions, Not Modes")
            scene = params.get('scene')
            level = params.get('level')
            code_parts = []
            if scene is not None:
                code_parts.append(f"this.currentScene = '{scene}';")
            if level is not None:
                code_parts.append(f"this.currentLevel = {level};")
            code_parts.append("this.updateSceneVisibility();")
            return " ".join(code_parts)

        elif action_type == 'save_game':
            slot = params.get('slot') or 'default'
            self.uses_save_load = True
            return f"this.saveGame('{slot}');"

        elif action_type == 'load_game':
            slot = params.get('slot') or 'default'
            self.uses_save_load = True
            return f"this.loadGame('{slot}');"

        return f"// TODO: {action_type}"

    def _emit_set_property(self, params: Dict) -> str:
        """Emit set_property action."""
        target = params.get('target')
        prop = params.get('property')
        value = params.get('value')

        if isinstance(value, IR_Value):
            val_str = self._format_value(value, prop)
        elif isinstance(value, IR_Expression):
            val_str = self.emit_expression(value)
        else:
            val_str = str(value)

        # Special handling for Phaser text properties
        if prop == 'font_size':
            if target:
                # Store value first, then call Phaser method with stored value
                return f"this.{target}.font_size = {val_str}; if (this.{target}.setFontSize) this.{target}.setFontSize(this.{target}.font_size);"
            else:
                return f"this.font_size = {val_str}; if (this.setFontSize) this.setFontSize(this.font_size);"

        if target:
            return f"this.{target}.{prop} = {val_str};"
        else:
            return f"this.{prop} = {val_str};"

    def _emit_conditional_inline(self, cond: IR_Conditional) -> str:
        """Emit conditional as inline code."""
        condition = self.emit_expression(cond.condition)
        then_code = " ".join(self.emit_action(a) for a in cond.then_actions if a)

        if cond.else_actions:
            else_code = " ".join(self.emit_action(a) for a in cond.else_actions if a)
            return f"if ({condition}) {{ {then_code} }} else {{ {else_code} }}"
        else:
            return f"if ({condition}) {{ {then_code} }}"

    def _emit_player_controls(self):
        """Emit player auto-control setup."""
        # Already handled in update via handlePlayerInput
        pass

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
            return f"this.{expr.left}.{expr.right}"

        elif expr.type == 'comparison':
            left = self.emit_expression(expr.left)
            right = self.emit_expression(expr.right)
            return f"{left} {expr.operator} {right}"

        elif expr.type == 'binary_op':
            left = self.emit_expression(expr.left)
            right = self.emit_expression(expr.right)
            op = expr.operator
            if op == 'and':
                op = '&&'
            elif op == 'or':
                op = '||'
            return f"({left} {op} {right})"

        elif expr.type == 'unary_op':
            right = self.emit_expression(expr.right)
            op = expr.operator
            if op == 'not':
                op = '!'
            return f"{op}{right}"

        elif expr.type == 'function_call':
            func = expr.left
            args = [self.emit_expression(a) for a in (expr.right or [])]

            if func == 'random':
                if len(args) >= 2:
                    return f"Phaser.Math.Between({args[0]}, {args[1]})"
                return "Math.random()"
            elif func == 'length':
                return f"{args[0]}.length"
            elif func == 'contains':
                return f"{args[0]}.includes({args[1]})"
            else:
                return f"this.{func}({', '.join(args)})"

        return str(expr)

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _format_value(self, value: IR_Value, context: str = None) -> str:
        """Format IR_Value for JavaScript."""
        if value.type == 'string':
            # Convert Rosh string interpolation {var} to JS template literal ${this.var}
            text = str(value.value)
            text = text.replace('`', '\\`')
            # Convert {obj.prop} to ${this.obj.prop}
            text = re.sub(r'\{(\w+)\.(\w+)\}', r'${this.\1.\2}', text)
            # Convert {var} to ${this.var}
            text = re.sub(r'\{(\w+)\}', r'${this.\1}', text)
            return f"`{text}`"
        elif value.type == 'number':
            return str(value.value)
        elif value.type == 'boolean':
            return 'true' if value.value else 'false'
        elif value.type == 'null':
            return 'null'
        elif value.type == 'percentage':
            if context in ('x', 'width'):
                return str(self.to_target_x(value.value))
            elif context in ('y', 'height'):
                return str(self.to_target_y(value.value))
            return str(value.value)
        elif value.type == 'color':
            return self.format_color(value.value)
        elif value.type == 'expression':
            return self.emit_expression(value.value)
        elif value.type == 'list':
            items = [self._format_value(IR_Value('number', v)) if isinstance(v, (int, float)) else f"'{v}'" for v in value.value]
            return f"[{', '.join(items)}]"
        else:
            return str(value.value)

    def _get_prop_value(self, obj: IR_Object, prop: str, default: float) -> float:
        """Get property value from object, or default."""
        if prop in obj.properties:
            val = obj.properties[prop]
            if val.type == 'percentage':
                return val.value
            elif val.type == 'number':
                # Already normalized by transformer
                return val.value
        return default

    def _get_color(self, obj: IR_Object) -> int:
        """Get color for object, or assign default."""
        if 'color' in obj.properties:
            return obj.properties['color'].value
        color = self.DEFAULT_COLORS[self.color_index % len(self.DEFAULT_COLORS)]
        self.color_index += 1
        return color

    def _get_color_css(self, obj: IR_Object) -> str:
        """Get color as CSS hex string (#rrggbb)."""
        color = self._get_color(obj)
        return f"#{color:06x}"

    def _get_key_condition(self, key: str) -> str:
        """Get Phaser condition for checking if a key is held down.

        Args:
            key: Key name (LEFT, RIGHT, UP, DOWN, SPACE, or letter)

        Returns:
            JavaScript condition string
        """
        key = key.upper()
        key_mapping = {
            'LEFT': 'this.cursors.left.isDown',
            'RIGHT': 'this.cursors.right.isDown',
            'UP': 'this.cursors.up.isDown',
            'DOWN': 'this.cursors.down.isDown',
            'SPACE': 'this.cursors.space.isDown',
        }

        if key in key_mapping:
            return key_mapping[key]

        # For letter keys, check this.keys.X.isDown
        if len(key) == 1 and key.isalpha():
            return f"this.keys.{key}.isDown"

        # Fallback to input keyboard check
        return f"this.input.keyboard.addKey(Phaser.Input.Keyboard.KeyCodes.{key}).isDown"

    def _map_phaser_key(self, key: str) -> str:
        """Map key name to Phaser keydown event name."""
        # Number keys need word names in Phaser
        number_map = {
            '0': 'ZERO', '1': 'ONE', '2': 'TWO', '3': 'THREE', '4': 'FOUR',
            '5': 'FIVE', '6': 'SIX', '7': 'SEVEN', '8': 'EIGHT', '9': 'NINE',
        }
        if key in number_map:
            return number_map[key]
        return key

    def _asset_key(self, filename: str) -> str:
        """Convert filename to Phaser asset key."""
        return filename.replace('.', '_').replace('/', '_')
