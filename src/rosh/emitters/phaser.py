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
from pathlib import Path
from typing import Dict, Any, Set
from .base import BaseEmitter
from .. import __version__
from ..ir import (
    IR_Program, IR_Object, IR_Event, IR_Action, IR_Function,
    IR_Value, IR_Expression, IR_Conditional, IR_Loop
)

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

        # Shared runtime option (new architecture)
        self.use_shared_runtime = self.meta.get('use_shared_runtime', False)

        # Mobile touch controls
        self.needs_touch_controls = False  # Set True if player objects exist

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
                self.needs_touch_controls = True

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
                self.needs_touch_controls = True  # Games with keyboard need touch on mobile
            elif event.trigger.startswith('continuous:'):
                # Continuous key polling (while_key_left, etc.)
                self.needs_keyboard = True
                self.needs_update = True  # Need update loop for polling
                self.needs_touch_controls = True  # Games with keyboard need touch on mobile
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
        self._emit_console()

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

        # Initialize implicit meta object (v0.2.7+)
        # meta holds game state and never renders
        self.write("this.meta = {};")
        self.write_blank()

        # Set up keyboard if needed
        if self.needs_keyboard:
            self.write("this.cursors = this.input.keyboard.createCursorKeys();")
            self.write("this.keys = this.input.keyboard.addKeys('A,B,C,D,E,F,G,H,I,J,K,L,M,N,O,P,Q,R,S,T,U,V,W,X,Y,Z,SPACE');")
            self.write_blank()

        # Set up mobile touch controls if needed
        if self.needs_touch_controls:
            self.write("// Mobile detection and touch state")
            self.write("this.isMobile = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent) || ('ontouchstart' in window);")
            self.write("this.touchDir = { left: false, right: false, up: false, down: false };")
            self.write("this.touchAction = { a: false, b: false };")
            self.write("if (this.isMobile) this.setupTouchControls();")
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

        # Update text for mobile (after objects created)
        if self.needs_touch_controls:
            self.write_blank()
            self.write("// Update instruction text for mobile")
            self.write("if (this.isMobile) this.updateTextForMobile();")

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
                # Add touchDir support for mobile
                touch_condition = self._get_touch_condition(key)
                if touch_condition and self.needs_touch_controls:
                    self.write(f"if ({condition} || {touch_condition}) {{ {handler_code} }}")
                else:
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

        # setupTouchControls (if needed)
        if self.needs_touch_controls:
            self._emit_touch_controls_method()

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
        # Include touch controls in conditions if needed
        if self.needs_touch_controls:
            self.write("if (this.cursors.left.isDown || this.keys.A.isDown || this.touchDir.left) {")
        else:
            self.write("if (this.cursors.left.isDown || this.keys.A.isDown) {")
        self.indent()
        self.write("player.x -= speed;")
        self.dedent()
        self.write("}")
        if self.needs_touch_controls:
            self.write("if (this.cursors.right.isDown || this.keys.D.isDown || this.touchDir.right) {")
        else:
            self.write("if (this.cursors.right.isDown || this.keys.D.isDown) {")
        self.indent()
        self.write("player.x += speed;")
        self.dedent()
        self.write("}")
        if self.needs_touch_controls:
            self.write("if (this.cursors.up.isDown || this.keys.W.isDown || this.touchDir.up) {")
        else:
            self.write("if (this.cursors.up.isDown || this.keys.W.isDown) {")
        self.indent()
        self.write("player.y -= speed;")
        self.dedent()
        self.write("}")
        if self.needs_touch_controls:
            self.write("if (this.cursors.down.isDown || this.keys.S.isDown || this.touchDir.down) {")
        else:
            self.write("if (this.cursors.down.isDown || this.keys.S.isDown) {")
        self.indent()
        self.write("player.y += speed;")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")
        self.write_blank()

    def _emit_touch_controls_method(self):
        """Emit mobile touch controls setup method with 8-way joystick and 2 buttons."""
        # Get control settings from meta
        controls = self.meta.get('controls', {})
        opacity = controls.get('opacity', 0.5)
        joystick_size = controls.get('joystick_size', 120)
        button_size = controls.get('button_size', 60)

        self.write("setupTouchControls() {")
        self.indent()
        self.write("const scene = this;")
        self.write_blank()

        # CSS for touch controls
        self.write("// Inject touch control styles")
        self.write("const style = document.createElement('style');")
        self.write(f"""style.textContent = `
      .touch-controls {{ position: fixed; bottom: 0; left: 0; right: 0; height: 180px; pointer-events: none; z-index: 1000; }}
      .touch-joystick-base {{
        position: absolute; bottom: 20px; left: 20px;
        width: {joystick_size}px; height: {joystick_size}px;
        background: rgba(255,255,255,0.15); border: 3px solid rgba(255,255,255,0.3);
        border-radius: 50%; pointer-events: auto; touch-action: none;
      }}
      .touch-joystick-thumb {{
        position: absolute; top: 50%; left: 50%;
        width: {joystick_size // 2}px; height: {joystick_size // 2}px;
        background: rgba(255,255,255,0.5); border-radius: 50%;
        transform: translate(-50%, -50%); pointer-events: none;
      }}
      .touch-button {{
        position: absolute; bottom: 30px;
        width: {button_size}px; height: {button_size}px;
        background: rgba(255,255,255,0.2); border: 3px solid rgba(255,255,255,0.4);
        border-radius: 50%; pointer-events: auto; touch-action: none;
        display: flex; align-items: center; justify-content: center;
        font-family: sans-serif; font-size: 20px; font-weight: bold; color: rgba(255,255,255,0.7);
        user-select: none; -webkit-user-select: none;
      }}
      .touch-button:active {{ background: rgba(255,255,255,0.4); }}
      .touch-button-a {{ right: {button_size + 30}px; }}
      .touch-button-b {{ right: 20px; }}
    `;""")
        self.write("document.head.appendChild(style);")
        self.write_blank()

        # Create touch controls container
        self.write("// Create touch controls container")
        self.write("const container = document.createElement('div');")
        self.write("container.className = 'touch-controls';")
        self.write_blank()

        # Create joystick
        self.write("// Create 8-way joystick")
        self.write("const joystickBase = document.createElement('div');")
        self.write("joystickBase.className = 'touch-joystick-base';")
        self.write("const joystickThumb = document.createElement('div');")
        self.write("joystickThumb.className = 'touch-joystick-thumb';")
        self.write("joystickBase.appendChild(joystickThumb);")
        self.write("container.appendChild(joystickBase);")
        self.write_blank()

        # Create buttons
        self.write("// Create action buttons")
        self.write("const buttonA = document.createElement('div');")
        self.write("buttonA.className = 'touch-button touch-button-a';")
        self.write("buttonA.textContent = 'A';")
        self.write("container.appendChild(buttonA);")
        self.write_blank()
        self.write("const buttonB = document.createElement('div');")
        self.write("buttonB.className = 'touch-button touch-button-b';")
        self.write("buttonB.textContent = 'B';")
        self.write("container.appendChild(buttonB);")
        self.write_blank()

        self.write("document.body.appendChild(container);")
        self.write_blank()

        # Joystick touch handling
        self.write("// Joystick touch handling")
        self.write(f"const baseRadius = {joystick_size // 2};")
        self.write("let joystickActive = false;")
        self.write_blank()

        self.write("const updateJoystick = (touchX, touchY) => {")
        self.indent()
        self.write("const rect = joystickBase.getBoundingClientRect();")
        self.write("const centerX = rect.left + rect.width / 2;")
        self.write("const centerY = rect.top + rect.height / 2;")
        self.write("let dx = touchX - centerX;")
        self.write("let dy = touchY - centerY;")
        self.write("const dist = Math.sqrt(dx*dx + dy*dy);")
        self.write_blank()
        self.write("// Clamp to base radius")
        self.write("if (dist > baseRadius) {")
        self.indent()
        self.write("dx = dx / dist * baseRadius;")
        self.write("dy = dy / dist * baseRadius;")
        self.dedent()
        self.write("}")
        self.write_blank()
        self.write("// Move thumb")
        self.write("joystickThumb.style.transform = `translate(calc(-50% + ${dx}px), calc(-50% + ${dy}px))`;")
        self.write_blank()
        self.write("// Calculate 8-way direction (22.5 degree zones)")
        self.write("const deadzone = baseRadius * 0.2;")
        self.write("if (dist < deadzone) {")
        self.indent()
        self.write("scene.touchDir = { left: false, right: false, up: false, down: false };")
        self.write("return;")
        self.dedent()
        self.write("}")
        self.write_blank()
        self.write("const angle = Math.atan2(dy, dx) * 180 / Math.PI;")
        self.write("// 8 directions: E=0, SE=45, S=90, SW=135, W=180/-180, NW=-135, N=-90, NE=-45")
        self.write("scene.touchDir.right = angle > -67.5 && angle < 67.5;")
        self.write("scene.touchDir.left = angle > 112.5 || angle < -112.5;")
        self.write("scene.touchDir.down = angle > 22.5 && angle < 157.5;")
        self.write("scene.touchDir.up = angle > -157.5 && angle < -22.5;")
        self.dedent()
        self.write("};")
        self.write_blank()

        self.write("const resetJoystick = () => {")
        self.indent()
        self.write("joystickThumb.style.transform = 'translate(-50%, -50%)';")
        self.write("scene.touchDir = { left: false, right: false, up: false, down: false };")
        self.write("joystickActive = false;")
        self.dedent()
        self.write("};")
        self.write_blank()

        # Touch events for joystick
        self.write("joystickBase.addEventListener('touchstart', (e) => {")
        self.indent()
        self.write("e.preventDefault();")
        self.write("joystickActive = true;")
        self.write("const touch = e.touches[0];")
        self.write("updateJoystick(touch.clientX, touch.clientY);")
        self.dedent()
        self.write("}, { passive: false });")
        self.write_blank()

        self.write("joystickBase.addEventListener('touchmove', (e) => {")
        self.indent()
        self.write("e.preventDefault();")
        self.write("if (!joystickActive) return;")
        self.write("const touch = e.touches[0];")
        self.write("updateJoystick(touch.clientX, touch.clientY);")
        self.dedent()
        self.write("}, { passive: false });")
        self.write_blank()

        self.write("joystickBase.addEventListener('touchend', resetJoystick);")
        self.write("joystickBase.addEventListener('touchcancel', resetJoystick);")
        self.write_blank()

        # Button touch events
        self.write("// Button A - triggers Space key action")
        self.write("buttonA.addEventListener('touchstart', (e) => {")
        self.indent()
        self.write("e.preventDefault();")
        self.write("scene.touchAction.a = true;")
        self.write("// Simulate Space keydown - both state and event")
        self.write("if (scene.keys && scene.keys.SPACE) {")
        self.indent()
        self.write("scene.keys.SPACE.isDown = true;")
        self.dedent()
        self.write("}")
        self.write("// Emit Phaser keyboard event for keydown handlers")
        self.write("scene.input.keyboard.emit('keydown-SPACE', { key: ' ' });")
        self.write("scene.triggerEvent('action_a');")
        self.dedent()
        self.write("}, { passive: false });")
        self.write_blank()

        self.write("buttonA.addEventListener('touchend', (e) => {")
        self.indent()
        self.write("scene.touchAction.a = false;")
        self.write("if (scene.keys && scene.keys.SPACE) {")
        self.indent()
        self.write("scene.keys.SPACE.isDown = false;")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("});")
        self.write_blank()

        self.write("// Button B - triggers Space (fire) and X key actions")
        self.write("buttonB.addEventListener('touchstart', (e) => {")
        self.indent()
        self.write("e.preventDefault();")
        self.write("scene.touchAction.b = true;")
        self.write("if (scene.keys && scene.keys.SPACE) {")
        self.indent()
        self.write("scene.keys.SPACE.isDown = true;")
        self.dedent()
        self.write("}")
        self.write("// Emit Phaser keyboard events - SPACE for fire, X for secondary")
        self.write("scene.input.keyboard.emit('keydown-SPACE', { key: ' ' });")
        self.write("scene.input.keyboard.emit('keydown-X', { key: 'x' });")
        self.write("scene.triggerEvent('action_b');")
        self.dedent()
        self.write("}, { passive: false });")
        self.write_blank()

        self.write("buttonB.addEventListener('touchend', (e) => {")
        self.indent()
        self.write("scene.touchAction.b = false;")
        self.write("if (scene.keys && scene.keys.SPACE) {")
        self.indent()
        self.write("scene.keys.SPACE.isDown = false;")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("});")

        self.dedent()
        self.write("}")
        self.write_blank()

        # Add getHelpText method for adaptive help display
        self._emit_help_text_method()

    def _emit_help_text_method(self):
        """Emit getHelpText() method that returns controls help based on platform."""
        self.write("getHelpText() {")
        self.indent()
        self.write("if (this.isMobile) {")
        self.indent()
        self.write("return 'Joystick to move, A to shoot';")
        self.dedent()
        self.write("} else {")
        self.indent()
        self.write("return 'Arrow keys to move, Space to shoot';")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")
        self.write_blank()

        # Add updateTextForMobile method
        self._emit_mobile_text_update_method()

    def _emit_mobile_text_update_method(self):
        """Emit updateTextForMobile() to replace keyboard instructions with touch-friendly text."""
        self.write("updateTextForMobile() {")
        self.indent()
        self.write("// Update any text objects containing keyboard instructions")
        self.write("const replacements = [")
        self.indent()
        self.write("{ from: /O\\/P to move.*SPACE to fire/i, to: 'Joystick to move, A to fire' },")
        self.write("{ from: /Arrow keys to move.*Space to fire/i, to: 'Joystick to move, A to fire' },")
        self.write("{ from: /Press SPACE to start/i, to: 'Press A to start' },")
        self.write("{ from: /Press R to restart/i, to: 'Press B to restart' },")
        self.write("{ from: /WASD|Arrow keys/i, to: 'Joystick' },")
        self.dedent()
        self.write("];")
        self.write_blank()
        self.write("// Find all text objects and update them")
        self.write("for (const key of Object.keys(this)) {")
        self.indent()
        self.write("const obj = this[key];")
        self.write("if (obj && obj.text !== undefined && typeof obj.setText === 'function') {")
        self.indent()
        self.write("let text = obj.text;")
        self.write("for (const r of replacements) {")
        self.indent()
        self.write("if (r.from.test(text)) {")
        self.indent()
        self.write("obj.setText(r.to);")
        self.write("break;")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")
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
        self.write_blank()
        self.write_comment("Embed player mute support")
        self.write("window.addEventListener('message', (e) => {")
        self.indent()
        self.write("if (e.data && e.data.type === 'rosh-mute') {")
        self.indent()
        self.write("game.sound.mute = e.data.muted;")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("});")

    def _get_shared_runtime_path(self) -> Path:
        """Get path to shared runtime files."""
        emitter_dir = Path(__file__).parent.parent.parent
        static_dir = emitter_dir / 'static'
        return static_dir

    def _emit_shared_runtime_console(self):
        """Emit REPL console using shared runtime files."""
        self.write_blank()
        self.write_comment("=" * 70)
        self.write_comment("Rosh Console (Shared Runtime v0.1.0)")
        self.write_comment("=" * 70)
        self.write_blank()

        static_dir = self._get_shared_runtime_path()

        # Read and emit the shared runtime
        runtime_file = static_dir / 'rosh-runtime.js'
        if runtime_file.exists():
            self.write_comment("Rosh Runtime - Shared REPL")
            runtime_code = runtime_file.read_text()
            for line in runtime_code.split('\n'):
                self.write(line)
            self.write_blank()
        else:
            self.write_comment(f"WARNING: rosh-runtime.js not found")
            self.write_blank()

        # Read and emit the Phaser adapter
        adapter_file = static_dir / 'rosh-adapter-phaser.js'
        if adapter_file.exists():
            self.write_comment("Phaser Adapter")
            adapter_code = adapter_file.read_text()
            for line in adapter_code.split('\n'):
                self.write(line)
            self.write_blank()
        else:
            self.write_comment(f"WARNING: rosh-adapter-phaser.js not found")
            self.write_blank()

        # Get the Phaser scene reference
        self.write_comment("Initialize Rosh Runtime with Phaser adapter")
        self.write("// Note: phaserScene is set in GameScene.create()")
        self.write("let phaserScene = null;")
        self.write("function initRoshRuntime(scene) {")
        self.indent()
        self.write("phaserScene = scene;")
        self.write("const roshAdapter = createPhaserAdapter(phaserScene, {});")

        # Register existing objects
        self.write("// Register pre-defined objects with the adapter")
        for obj in self.ir.objects:
            self.write(f"if (typeof rosh_{obj.name} !== 'undefined') roshAdapter.registerObject('{obj.name}', rosh_{obj.name});")

        self.write("RoshRuntime.init(roshAdapter);")
        self.dedent()
        self.write("}")
        self.write_blank()

    def _emit_console(self):
        """Emit in-game console with voice support.

        SPEC CHAIN: rosh-console.toml → phaser.py
        Must implement: list, look, set, hide, show, create, help
        """
        # Use shared runtime if enabled
        if self.use_shared_runtime:
            self._emit_shared_runtime_console()
            return

        # Legacy inline console code below
        self.write_blank()
        self.write_comment("=" * 70)
        self.write_comment("Rosh Console - Press ` (backtick) to toggle")
        self.write_comment("Voice: Hold Ctrl+Space to speak (Chrome/Edge)")
        self.write_comment("=" * 70)
        self.write_blank()

        # Console state
        self.write("let roshConsoleVisible = false;")
        self.write("let roshConsoleInput = '';")
        self.write("let roshConsoleOutput = [];")
        self.write("let roshObjectCounter = {};")
        self.write("let roshUndoStack = [];")
        self.write("let roshRedoStack = [];")
        self.write_blank()

        # Undo helpers
        self.write_comment("Undo support - save state before modifications")
        self.write("function roshSaveState(obj, name, props) {")
        self.indent()
        self.write("const state = { name, props: {} };")
        self.write("for (const p of props) { state.props[p] = obj[p]; }")
        self.write("roshUndoStack.push(state);")
        self.dedent()
        self.write("}")
        self.write("function roshUndo(count = 1) {")
        self.indent()
        self.write("for (let i = 0; i < count; i++) {")
        self.indent()
        self.write("if (roshUndoStack.length === 0) { roshLog('Nothing to undo', 'dim'); return; }")
        self.write("const state = roshUndoStack.pop();")
        self.write("const scene = getScene();")
        self.write("const obj = scene[state.name] || (scene.roshObjects && scene.roshObjects[state.name]);")
        self.write("if (!obj) { roshLog('Object no longer exists: ' + state.name, 'error'); continue; }")
        self.write_comment("Save current state to redo stack before restoring")
        self.write("const redoState = { name: state.name, props: {} };")
        self.write("for (const p of Object.keys(state.props)) { redoState.props[p] = obj[p]; }")
        self.write("roshRedoStack.push(redoState);")
        self.write_comment("Restore the saved state")
        self.write("for (const [p, v] of Object.entries(state.props)) { obj[p] = v; }")
        self.write("roshLog('Undid change to ' + state.name);")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")
        self.write_blank()
        self.write("function roshRedo(count = 1) {")
        self.indent()
        self.write("for (let i = 0; i < count; i++) {")
        self.indent()
        self.write("if (roshRedoStack.length === 0) { roshLog('Nothing to redo', 'dim'); return; }")
        self.write("const state = roshRedoStack.pop();")
        self.write("const scene = getScene();")
        self.write("const obj = scene[state.name] || (scene.roshObjects && scene.roshObjects[state.name]);")
        self.write("if (!obj) { roshLog('Object no longer exists: ' + state.name, 'error'); continue; }")
        self.write_comment("Save current state to undo stack before restoring")
        self.write("const undoState = { name: state.name, props: {} };")
        self.write("for (const p of Object.keys(state.props)) { undoState.props[p] = obj[p]; }")
        self.write("roshUndoStack.push(undoState);")
        self.write_comment("Restore the redo state")
        self.write("for (const [p, v] of Object.entries(state.props)) { obj[p] = v; }")
        self.write("roshLog('Redid change to ' + state.name);")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")
        self.write_blank()

        # Get scene reference helper
        self.write("function getScene() { return game.scene.scenes[0]; }")
        self.write_blank()

        # Initialize roshObjects namespace when scene is ready
        self.write_comment("Dedicated namespace for runtime-created objects (avoids engine collisions)")
        self.write("setTimeout(() => { const s = getScene(); if (s) s.roshObjects = s.roshObjects || {}; }, 100);")
        self.write_blank()

        # Console HTML/CSS
        self.write_comment("Create console DOM elements")
        self.write("const consoleDiv = document.createElement('div');")
        self.write("consoleDiv.id = 'rosh-console';")
        self.write("consoleDiv.innerHTML = `")
        self.write("  <div id='rosh-console-header'>Rosh Console (\\` to close) <span id='rosh-voice-btn'>🎤</span></div>")
        self.write("  <div id='rosh-console-output'></div>")
        self.write("  <div id='rosh-console-input-row'>")
        self.write("    <span>&gt; </span>")
        self.write("    <input type='text' id='rosh-console-input' autocomplete='off' placeholder='type command or hold Ctrl+Space'>")
        self.write("  </div>")
        self.write("`;")
        self.write("consoleDiv.style.cssText = `")
        self.write("  display: none; position: fixed; top: 0; left: 0; right: 0;")
        self.write("  height: 200px; background: rgba(20,20,40,0.95); color: #0ff;")
        self.write("  font-family: monospace; font-size: 14px; z-index: 9999;")
        self.write("  border-bottom: 2px solid #0ff;")
        self.write("`;")
        self.write("document.body.appendChild(consoleDiv);")
        self.write_blank()

        # Style the console elements
        self.write_comment("Style console elements")
        self.write("const style = document.createElement('style');")
        self.write("style.textContent = `")
        self.write("  #rosh-console-header { padding: 5px 10px; color: #6cf; border-bottom: 1px solid #333; }")
        self.write("  #rosh-console-output { height: 140px; overflow-y: auto; padding: 5px 10px; }")
        self.write("  #rosh-console-output div { display: block; margin: 2px 0; }")
        self.write("  #rosh-console-output .error { color: #f66; }")
        self.write("  #rosh-console-output .info { color: #6cf; }")
        self.write("  #rosh-console-output .dim { color: #666; }")
        self.write("  #rosh-console-input-row { display: flex; padding: 5px 10px; background: rgba(30,30,50,0.8); }")
        self.write("  #rosh-console-input { flex: 1; background: transparent; border: none; color: #0ff; outline: none; font-family: inherit; font-size: inherit; }")
        self.write("  #rosh-voice-btn { cursor: pointer; margin-left: 10px; opacity: 0.5; }")
        self.write("  #rosh-voice-btn:hover { opacity: 1; }")
        self.write("  #rosh-voice-btn.listening { opacity: 1; animation: pulse 1s infinite; }")
        self.write("  @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.5; } }")
        self.write("`;")
        self.write("document.head.appendChild(style);")
        self.write_blank()

        # Console log function
        self.write("function roshLog(msg, type = 'normal') {")
        self.indent()
        self.write("const output = document.getElementById('rosh-console-output');")
        self.write("const div = document.createElement('div');")
        self.write("div.className = type;")
        self.write("div.textContent = msg;")
        self.write("output.appendChild(div);")
        self.write("output.scrollTop = output.scrollHeight;")
        self.write("roshConsoleOutput.push(msg);")
        self.dedent()
        self.write("}")
        self.write_blank()

        # Toggle console
        self.write("function toggleRoshConsole() {")
        self.indent()
        self.write("roshConsoleVisible = !roshConsoleVisible;")
        self.write("consoleDiv.style.display = roshConsoleVisible ? 'block' : 'none';")
        self.write("// Disable Phaser keyboard when console is open so we can type")
        self.write("game.input.keyboard.enabled = !roshConsoleVisible;")
        self.write("if (roshConsoleVisible) document.getElementById('rosh-console-input').focus();")
        self.dedent()
        self.write("}")
        self.write_blank()

        # Voice corrections
        self.write_comment("Voice corrections for common mishearings")
        self.write("const VOICE_CORRECTIONS = {")
        self.indent()
        self.write("'raush': 'rosh', 'rush': 'rosh', 'rawsh': 'rosh', 'roush': 'rosh',")
        self.write("'colour': 'color', 'grey': 'gray', 'centre': 'center',")
        self.write("'visibility': 'visible', 'invisible': 'visible false',")
        self.dedent()
        self.write("};")
        self.write_blank()

        self.write("function applyVoiceCorrections(text) {")
        self.indent()
        self.write("let result = text.toLowerCase();")
        self.write("for (const [wrong, right] of Object.entries(VOICE_CORRECTIONS)) {")
        self.indent()
        self.write("result = result.replace(new RegExp('\\\\b' + wrong + '\\\\b', 'g'), right);")
        self.dedent()
        self.write("}")
        self.write("return result;")
        self.dedent()
        self.write("}")
        self.write_blank()

        # Process command - implements rosh-console.toml required commands
        self._emit_console_commands()

        # Keyboard handler
        self.write_comment("Keyboard handling")
        self.write("document.addEventListener('keydown', (e) => {")
        self.indent()
        self.write("if (e.key === '`' || e.key === '~') { e.preventDefault(); toggleRoshConsole(); return; }")
        self.write("if (!roshConsoleVisible) return;")
        self.write("const input = document.getElementById('rosh-console-input');")
        self.write("if (e.key === 'Enter' && document.activeElement === input) {")
        self.indent()
        self.write("const cmd = input.value.trim();")
        self.write("if (cmd) { roshLog('> ' + cmd, 'dim'); processRoshCommand(cmd); }")
        self.write("input.value = '';")
        self.dedent()
        self.write("}")
        self.write("if (e.key === 'Escape') { toggleRoshConsole(); }")
        self.dedent()
        self.write("});")
        self.write_blank()

        # Voice input
        self._emit_voice_support()

        self.write(f"roshLog('Rosh v{__version__} | Phaser', 'info');")
        self.write("roshLog('Type help for commands. Press ` to toggle console.', 'dim');")

    def _emit_console_commands(self):
        """Emit console command processing.

        SPEC: rosh-console.toml - required commands
        """
        self.write("function processRoshCommand(cmd) {")
        self.indent()
        self.write("const scene = getScene();")
        self.write("if (!scene) { roshLog('No active scene', 'error'); return; }")
        self.write_blank()
        self.write("cmd = applyVoiceCorrections(cmd);")
        self.write("const parts = cmd.trim().split(/\\s+/);")
        self.write("const command = parts[0].toLowerCase();")
        self.write_blank()

        self.write("try {")
        self.indent()

        # list command
        self.write("if (command === 'list' || command === 'ls' || command === 'objects') {")
        self.indent()
        self.write_comment("List original objects + runtime-created objects from roshObjects namespace")
        known_objects = [obj.name for obj in self.ir.objects if 'target' not in obj.properties]
        self.write(f"const originalObjects = {known_objects};")
        self.write("const runtimeObjects = scene.roshObjects ? Object.keys(scene.roshObjects) : [];")
        self.write("const allObjects = [...originalObjects, ...runtimeObjects];")
        self.write("roshLog('Objects: ' + allObjects.join(', '));")
        self.dedent()
        self.write("}")

        # look command
        self.write("else if (command === 'look' || command === 'l' || command === 'examine' || command === 'x') {")
        self.indent()
        self.write("if (parts.length < 2) { roshLog('Usage: look <object>', 'error'); return; }")
        self.write("const name = parts[1];")
        self.write_comment("Check both scene and roshObjects namespace")
        self.write("const obj = scene[name] || (scene.roshObjects && scene.roshObjects[name]);")
        self.write("if (!obj) { roshLog('Object not found: ' + name, 'error'); return; }")
        self.write("roshLog(name + ': x=' + Math.round(obj.x) + ', y=' + Math.round(obj.y));")
        self.write("if (obj.visible !== undefined) roshLog('  visible=' + obj.visible);")
        self.write("if (obj.text !== undefined) roshLog('  text=\"' + obj.text + '\"');")
        self.dedent()
        self.write("}")

        # set command
        self.write("else if (command === 'set') {")
        self.indent()
        self.write_comment("Parse: set <obj> <prop> to <value>  OR  set <obj> <color>")
        self.write("let name, prop, value;")
        self.write("if (parts.length >= 5 && parts[3] === 'to') {")
        self.indent()
        self.write("name = parts[1]; prop = parts[2]; value = parts.slice(4).join(' ');")
        self.dedent()
        self.write("} else if (parts.length === 4 && parts[2] === 'to') {")
        self.indent()
        self.write("name = parts[1]; prop = 'color'; value = parts[3];")
        self.dedent()
        self.write("} else if (parts.length === 3) {")
        self.indent()
        self.write("name = parts[1]; prop = 'color'; value = parts[2];")
        self.dedent()
        self.write("} else { roshLog('Usage: set <obj> <prop> to <value>', 'error'); return; }")
        self.write_blank()
        self.write_comment("Check both scene and roshObjects namespace")
        self.write("const obj = scene[name] || (scene.roshObjects && scene.roshObjects[name]);")
        self.write("if (!obj) { roshLog('Object not found: ' + name, 'error'); return; }")
        self.write_blank()
        self.write_comment("Save state for undo (clear redo stack on new action)")
        self.write("roshRedoStack = [];")
        self.write("roshSaveState(obj, name, [prop, 'x', 'y', 'visible', 'width', 'height', 'displayWidth', 'displayHeight']);")
        self.write_blank()
        self.write("const colors = {red: 0xff0000, green: 0x00ff00, blue: 0x0000ff, yellow: 0xffff00, cyan: 0x00ffff, magenta: 0xff00ff, white: 0xffffff, black: 0x000000, orange: 0xff8800, purple: 0x8800ff};")
        self.write("if (prop === 'x') obj.x = parseFloat(value);")
        self.write("else if (prop === 'y') obj.y = parseFloat(value);")
        self.write("else if (prop === 'width' || prop === 'w') {")
        self.indent()
        self.write("const w = parseFloat(value);")
        self.write("if (obj.setSize) obj.setSize(w, obj.height || 50);")
        self.write("else if (obj.setDisplaySize) obj.setDisplaySize(w, obj.displayHeight || 50);")
        self.write("else obj.width = w;")
        self.dedent()
        self.write("}")
        self.write("else if (prop === 'height' || prop === 'h') {")
        self.indent()
        self.write("const h = parseFloat(value);")
        self.write("if (obj.setSize) obj.setSize(obj.width || 50, h);")
        self.write("else if (obj.setDisplaySize) obj.setDisplaySize(obj.displayWidth || 50, h);")
        self.write("else obj.height = h;")
        self.dedent()
        self.write("}")
        self.write("else if (prop === 'text' && obj.setText) obj.setText(value);")
        self.write("else if (prop === 'color' || prop === 'colour') {")
        self.indent()
        self.write("const c = colors[value.toLowerCase()] || parseInt(value, 16);")
        self.write("if (obj.setTint) obj.setTint(c);")
        self.write("else if (obj.setColor) obj.setColor('#' + c.toString(16).padStart(6, '0'));")
        self.write("else if (obj.setFillStyle) obj.setFillStyle(c);")
        self.dedent()
        self.write("}")
        self.write("else if (prop === 'visible') obj.visible = (value === 'true' || value === '1');")
        self.write("else obj[prop] = value;")
        self.write("roshLog(name + '.' + prop + ' = ' + value);")
        self.dedent()
        self.write("}")

        # hide command
        self.write("else if (command === 'hide') {")
        self.indent()
        self.write("if (parts.length < 2) { roshLog('Usage: hide <object>', 'error'); return; }")
        self.write("const name = parts[1];")
        self.write("const obj = scene[name] || (scene.roshObjects && scene.roshObjects[name]);")
        self.write("if (!obj) { roshLog('Object not found: ' + name, 'error'); return; }")
        self.write_comment("Save state for undo")
        self.write("roshRedoStack = [];")
        self.write("roshSaveState(obj, name, ['visible']);")
        self.write("obj.visible = false;")
        self.write("roshLog(name + ' hidden');")
        self.dedent()
        self.write("}")

        # show command
        self.write("else if (command === 'show' || command === 'unhide') {")
        self.indent()
        self.write("if (parts.length < 2) { roshLog('Usage: show <object>', 'error'); return; }")
        self.write("const name = parts[1];")
        self.write("const obj = scene[name] || (scene.roshObjects && scene.roshObjects[name]);")
        self.write("if (!obj) { roshLog('Object not found: ' + name, 'error'); return; }")
        self.write_comment("Save state for undo")
        self.write("roshRedoStack = [];")
        self.write("roshSaveState(obj, name, ['visible']);")
        self.write("obj.visible = true;")
        self.write("roshLog(name + ' visible');")
        self.dedent()
        self.write("}")

        # create command - supports "create box" or "create 3 boxes"
        self.write("else if (command === 'create') {")
        self.indent()
        self.write("if (parts.length < 2) { roshLog('Usage: create <name> [at <x> <y>]', 'error'); return; }")
        self.write_blank()
        self.write_comment("Handle 'create 3 boxes' syntax")
        self.write("let count = 1;")
        self.write("let baseName = parts[1];")
        self.write("if (/^\\d+$/.test(parts[1]) && parts.length >= 3) {")
        self.indent()
        self.write("count = parseInt(parts[1]);")
        self.write("baseName = parts[2];")
        self.dedent()
        self.write("}")
        self.write_blank()
        self.write("for (let i = 0; i < count; i++) {")
        self.indent()
        self.write("let name = baseName;")
        self.write_comment("Auto-number if name exists in scene or roshObjects")
        self.write("if (!roshObjectCounter[baseName]) roshObjectCounter[baseName] = 0;")
        self.write("while (scene[name] || (scene.roshObjects && scene.roshObjects[name])) { roshObjectCounter[baseName]++; name = baseName + '-' + roshObjectCounter[baseName]; }")
        self.write_comment("Offset multiple objects so they don't stack")
        self.write("let x = 400 + (i * 60), y = 300;")
        self.write_comment("Create in roshObjects namespace (avoids engine collisions)")
        self.write("if (!scene.roshObjects) scene.roshObjects = {};")
        self.write("scene.roshObjects[name] = scene.add.rectangle(x, y, 50, 50, 0x00ff00);")
        self.write("roshLog('Created ' + name + ' at (' + x + ', ' + y + ')');")
        self.dedent()
        self.write("}")
        self.dedent()
        self.write("}")

        # undo command
        self.write("else if (command === 'undo') {")
        self.indent()
        self.write("const count = parts.length >= 2 ? parseInt(parts[1]) || 1 : 1;")
        self.write("roshUndo(count);")
        self.dedent()
        self.write("}")

        # redo command
        self.write("else if (command === 'redo') {")
        self.indent()
        self.write("const count = parts.length >= 2 ? parseInt(parts[1]) || 1 : 1;")
        self.write("roshRedo(count);")
        self.dedent()
        self.write("}")

        # oops command (alias for undo 1)
        self.write("else if (command === 'oops') {")
        self.indent()
        self.write("roshUndo(1);")
        self.dedent()
        self.write("}")

        # help command
        self.write("else if (command === 'help' || command === '?') {")
        self.indent()
        self.write("roshLog('Commands: list, look <obj>, set <obj> <prop> to <value>');")
        self.write("roshLog('          hide <obj>, show <obj>, create <name>');")
        self.write("roshLog('          undo [n], redo [n], oops');")
        self.write("roshLog('Voice: Hold Ctrl+Space to speak');")
        self.dedent()
        self.write("}")

        # unknown
        self.write("else { roshLog('Unknown command: ' + command + '. Type help for commands.', 'error'); }")

        self.dedent()
        self.write("} catch(e) { roshLog('Error: ' + e.message, 'error'); }")
        self.dedent()
        self.write("}")
        self.write_blank()

    def _emit_voice_support(self):
        """Emit Web Speech API voice input support."""
        self.write_comment("Voice Input - Hold Ctrl+Space to speak (Chrome/Edge)")
        self.write("const voiceBtn = document.getElementById('rosh-voice-btn');")
        self.write("let recognition = null;")
        self.write("let isListening = false;")
        self.write_blank()

        self.write("if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {")
        self.indent()
        self.write("const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;")
        self.write("recognition = new SpeechRecognition();")
        self.write("recognition.continuous = false;")
        self.write("recognition.interimResults = false;")
        self.write("recognition.lang = 'en-US';")
        self.write_blank()

        self.write("recognition.onresult = (event) => {")
        self.indent()
        self.write("const cmd = event.results[0][0].transcript;")
        self.write("roshLog('[voice] ' + cmd, 'info');")
        self.write("processRoshCommand(cmd);")
        self.dedent()
        self.write("};")
        self.write_blank()

        self.write("recognition.onend = () => { isListening = false; voiceBtn.classList.remove('listening'); };")
        self.write("recognition.onerror = (e) => { roshLog('[voice error] ' + e.error, 'error'); isListening = false; voiceBtn.classList.remove('listening'); };")
        self.write_blank()

        self.write("function startVoice() {")
        self.indent()
        self.write("if (isListening) return;")
        self.write("try { recognition.start(); isListening = true; voiceBtn.classList.add('listening'); roshLog('[voice] Listening...', 'dim'); }")
        self.write("catch(e) { roshLog('[voice] ' + e.message, 'error'); }")
        self.dedent()
        self.write("}")
        self.write_blank()

        self.write("function stopVoice() { if (isListening) { recognition.stop(); isListening = false; voiceBtn.classList.remove('listening'); } }")
        self.write_blank()

        # Ctrl+Space for push-to-talk
        self.write_comment("Ctrl+Space for push-to-talk")
        self.write("document.addEventListener('keydown', (e) => { if (e.ctrlKey && e.code === 'Space' && roshConsoleVisible) { e.preventDefault(); startVoice(); } });")
        self.write("document.addEventListener('keyup', (e) => { if (e.code === 'Space') stopVoice(); });")
        self.write("voiceBtn.addEventListener('click', () => { if (isListening) stopVoice(); else startVoice(); });")

        self.dedent()
        self.write("} else {")
        self.indent()
        self.write("voiceBtn.style.display = 'none';")
        self.write("roshLog('[voice] Not supported in this browser', 'dim');")
        self.dedent()
        self.write("}")
        self.write_blank()

    # =========================================================================
    # Object Emission
    # =========================================================================

    def _emit_create_object(self, obj: IR_Object):
        """Emit code to create an object.

        Hidden objects (name starts with '_') are skipped - they exist in IR
        for templates, config, meta, etc. but are not rendered in the game.
        """
        # Skip hidden objects - they exist in world state but are not rendered
        if obj.hidden:
            return

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

        # Apply initial visible property if set to false
        if 'visible' in obj.properties:
            vis_val = self.get_value(obj.properties['visible'])
            if vis_val is False or vis_val == 'false':
                self.write(f"this.{obj.name}.visible = false;")

        # Set additional properties
        skip_props = {'x', 'y', 'width', 'height', 'color', 'sprite', 'text', 'font_size', 'visible', 'target', 'saveable', 'type'}
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
                    if (this._selection && this._selection.length > 0) {
                        const count = this._selection.length;
                        this._selection.forEach(obj => { if (obj && obj.destroy) obj.destroy(); });
                        this._selection = [];
                        console.log('destroyed ' + count + ' objects');
                    }""".strip().replace('\n                    ', '\n')
                else:
                    return """
                    if (this._selection && this._selection.length > 0) {
                        console.warn('warning: destroy affects ' + this._selection.length + ' objects. Use "destroy confirmed" to proceed.');
                    } else {
                        console.log('no objects selected');
                    }""".strip().replace('\n                    ', '\n')
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

    def _emit_get_action(self, params: Dict) -> str:
        """Emit get action with query filtering.

        Populates this._selection with matching objects.
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
        lines = ["this._selection = Object.values(this._objects || {})"]

        # Filter by type if specified
        if target:
            target_name = self.emit_expression(target) if hasattr(target, 'type') else f"'{target}'"
            # Handle string literal
            if isinstance(target_name, str) and target_name.startswith("'"):
                type_name = target_name.strip("'")
            else:
                type_name = target_name
            lines[0] += f".filter(obj => obj._type === '{type_name}')"

        # Filter hidden objects
        if not include_hidden:
            lines[0] += ".filter(obj => !obj._hidden)"

        # Apply where condition
        if filter_expr:
            condition_code = self._emit_filter_condition(filter_expr)
            lines[0] += f".filter(obj => {condition_code})"

        lines.append("console.log('selected ' + this._selection.length + ' objects');")

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
        """Emit expression for filter context (obj.property instead of this.obj.property)"""
        if hasattr(expr, 'type'):
            if expr.type == 'property_access':
                # In filter context, left is the object type, right is property
                # We use obj.property since we're iterating
                prop = expr.right
                return f"obj.{prop}"
            elif expr.type == 'literal':
                if hasattr(expr, 'value') and hasattr(expr.value, 'value'):
                    val = expr.value.value
                    if isinstance(val, str):
                        return f"'{val}'"
                    return str(val)
                return self.emit_expression(expr)
        # Identifier in filter context - treat as obj property
        if hasattr(expr, 'value') and hasattr(expr.value, 'value'):
            val = expr.value.value
            if isinstance(val, str):
                # Could be a property name
                return f"obj.{val}"
            return str(val)
        return self.emit_expression(expr)

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

    def _get_touch_condition(self, key: str) -> str:
        """Get touchDir condition for a key, if applicable.

        Maps common movement keys to touch joystick directions:
        - LEFT, A, O → touchDir.left
        - RIGHT, D, P → touchDir.right
        - UP, W → touchDir.up
        - DOWN, S → touchDir.down
        - SPACE → touchAction.a
        """
        key = key.upper()
        touch_mapping = {
            'LEFT': 'this.touchDir.left',
            'A': 'this.touchDir.left',
            'O': 'this.touchDir.left',
            'RIGHT': 'this.touchDir.right',
            'D': 'this.touchDir.right',
            'P': 'this.touchDir.right',
            'UP': 'this.touchDir.up',
            'W': 'this.touchDir.up',
            'DOWN': 'this.touchDir.down',
            'S': 'this.touchDir.down',
            'SPACE': 'this.touchAction.a',
        }
        return touch_mapping.get(key, None)

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
