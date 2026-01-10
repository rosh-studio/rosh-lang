"""
Pygame Emitter - IR to Pygame Python

Converts IR representation to Pygame Python code.
This is a "mechanical translator" - all semantic decisions are in the IR.

Usage:
    from rosh.emitters.pygame import PygameEmitter

    ir = transform_ast_to_ir(ast)
    emitter = PygameEmitter(ir)
    py_code = emitter.emit()

See: rosh-dev/proposals/ROSH-IR-SPECIFICATION.md

⚠️  OUT OF SYNC - SPEC 0.3 (2026-01-10)
========================================
Status: NOT COMPLIANT - needs significant work

This emitter is behind Phaser/ThreeJS and missing Spec 0.3 features:
- No rosh_network.py equivalent (no multiplayer/Project Twin)
- No REQUEST/CONFIRMED protocol support
- Colors/sizes hardcoded, not from spec
- No REPL support in generated code
- Missing object types, properties from spec

TO BRING INTO SYNC:
1. Create rosh_network.py for multiplayer (match JS protocol)
2. Import colors/sizes from spec (or generate constants)
3. Implement REPL commands from spec
4. Add spec compliance tests for Pygame output
5. Test with rosh.cloud World Center (WebSocket from Python)

Priority: LOW - Pygame demos work for local testing
"""

from typing import Dict, Any, Set, List
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


class PygameEmitter(BaseEmitter):
    """Emit Pygame Python from Rosh IR.

    Generates a complete Pygame game including:
    - Game class with setup and game loop
    - Object creation as rectangles or sprites
    - Event handlers for keyboard input
    - Collision detection (AABB)
    - HUD text display
    """

    # Default object colors (RGB tuples for Pygame)
    DEFAULT_COLORS = [
        (0, 255, 0), (0, 0, 255), (255, 0, 0), (255, 255, 0),
        (255, 0, 255), (0, 255, 255), (255, 136, 0), (136, 0, 255),
    ]

    def __init__(self, ir: IR_Program, meta: Dict[str, Any] = None):
        super().__init__(ir, meta)
        self.color_index = 0
        self.sprite_assets: Set[str] = set()
        self.sound_assets: Set[str] = set()
        self.music_file: str = None
        self.needs_keyboard = False
        self.player_objects: Set[str] = set()
        self.collision_events: List = []
        self.hud_objects: List = []
        self.keydown_events: Dict[str, List[list]] = {}  # key -> [handler_lines, ...]
        self.update_handlers: List[list] = []  # List of update event handler code

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
            # Detect player objects by parent_type OR by name
            if obj.parent_type == 'player' or obj.name == 'player':
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

            if 'sprite' in obj.properties:
                sprite_val = obj.properties['sprite']
                if sprite_val.type == 'string':
                    self.sprite_assets.add(sprite_val.value)

            if 'target' in obj.properties:
                target_val = obj.properties['target']
                target_name = target_val.value if hasattr(target_val, 'value') else str(target_val)
                self.hud_objects.append((obj.name, target_name))

        for event in self.ir.events:
            if event.trigger == 'update':
                self.update_handlers.append(self._generate_handler_code(event))
            elif event.trigger.startswith('keydown:'):
                key = event.trigger.split(':')[1]
                if key not in self.keydown_events:
                    self.keydown_events[key] = []
                self.keydown_events[key].append(self._generate_handler_code(event))
                self.needs_keyboard = True
            elif event.trigger.startswith('collision:'):
                parts = event.trigger.split(':')
                if len(parts) >= 3:
                    obj_a, obj_b = parts[1], parts[2]
                    self.collision_events.append((obj_a, obj_b, self._generate_handler_code(event)))

            self._scan_actions_for_assets(event.handler)

        self._scan_actions_for_assets(self.ir.init_actions)

        # Also scan function bodies for assets
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

    def _generate_handler_code(self, event: IR_Event) -> list:
        """Generate handler code for an event as a list of lines."""
        lines = []
        for action in event.handler:
            if action:
                code = self.emit_action(action)
                if code:
                    lines.append(code)
        return lines if lines else ['pass']

    def emit(self) -> str:
        """Generate complete Pygame Python code."""
        self._emit_header()
        self._emit_imports()
        self._emit_class_start()
        self._emit_init()
        self._emit_run()
        self._emit_handle_events()
        self._emit_update()
        self._emit_draw()
        self._emit_helper_methods()
        self._emit_functions()
        self._emit_class_end()
        self._emit_main()

        return self.get_code()

    def write_comment(self, text: str):
        """Python-style comments."""
        self.write(f"# {text}")

    # =========================================================================
    # Structure Generation
    # =========================================================================

    def _emit_header(self):
        """Emit file header."""
        self.write_comment("Auto-generated from Rosh IR")
        self.write_comment("Emitter: Pygame v0.2.0")
        self.write_blank()

    def _emit_imports(self):
        """Emit Python imports."""
        self.write("import pygame")
        self.write("import sys")
        if self.sprite_assets or self.sound_assets or self.music_file:
            self.write("import os")
        self.write_blank()
        self.write_comment("Project Twin - shared world networking")
        self.write("try:")
        self.indent()
        self.write("from rosh_network import RoshNetwork")
        self.write("NETWORK_AVAILABLE = True")
        self.dedent()
        self.write("except ImportError:")
        self.indent()
        self.write("NETWORK_AVAILABLE = False")
        self.write("RoshNetwork = None")
        self.dedent()
        self.write_blank()

    def _emit_class_start(self):
        """Emit class declaration."""
        self.write("class Game:")
        self.indent()

    def _emit_class_end(self):
        """Close class."""
        self.dedent()
        self.write_blank()

    def _emit_init(self):
        """Emit __init__ method."""
        width = self.ir.metadata.canvas_width
        height = self.ir.metadata.canvas_height

        self.write("def __init__(self):")
        self.indent()
        self.write("pygame.init()")
        if self.sound_assets or self.music_file:
            self.write("pygame.mixer.init()")
        self.write(f"self.screen = pygame.display.set_mode(({width}, {height}))")
        self.write("pygame.display.set_caption('Rosh Game')")
        self.write("self.clock = pygame.time.Clock()")
        self.write("self.running = True")
        self.write("self.font = pygame.font.Font(None, 24)")
        self.write_blank()

        # Console state
        self.write_comment("Console state (press ` to toggle)")
        self.write("self.console_visible = False")
        self.write("self.console_input = ''")
        self.write("self.console_history = []")
        self.write("self.console_output = []")
        self.write(f"self.console_output.append('Rosh v{__version__} | Pygame')")
        self.write("self.console_output.append('Type help for commands. Press ` to toggle console.')")
        self.write("self.console_font = pygame.font.Font(None, 20)")
        self.write_blank()

        # Network state
        self.write_comment("Project Twin - shared world networking")
        self.write("self.network = None")
        self.write("if NETWORK_AVAILABLE:")
        self.indent()
        self.write("self.network = RoshNetwork(")
        self.indent()
        self.write("on_object_created=self._network_create_object,")
        self.write("on_object_deleted=self._network_delete_object,")
        self.write("on_object_moved=self._network_move_object,")
        self.write("on_log=lambda msg, style=None: self.console_output.append(msg)")
        self.dedent()
        self.write(")")
        self.dedent()

        # Scene/level state
        if self.uses_scenes:
            initial_scene = self.ir.metadata.initial_scene
            initial_level = self.ir.metadata.initial_level
            if initial_scene:
                self.write(f"self.current_scene = '{initial_scene}'")
            else:
                self.write("self.current_scene = None")
            self.write(f"self.current_level = {initial_level}")

        self.write_blank()

        # Load assets
        if self.sprite_assets:
            self.write_comment("Load sprites")
            self.write("self.sprites = {}")
            for sprite in self.sprite_assets:
                key = self._asset_key(sprite)
                self.write(f"self.sprites['{key}'] = pygame.image.load(os.path.join('assets', '{sprite}'))")
            self.write_blank()

        if self.sound_assets:
            self.write_comment("Load sounds")
            self.write("self.sounds = {}")
            for sound in self.sound_assets:
                key = self._asset_key(sound)
                self.write(f"self.sounds['{key}'] = pygame.mixer.Sound(os.path.join('assets', '{sound}'))")
            self.write_blank()

        if self.music_file:
            self.write_comment("Load music")
            self.write(f"pygame.mixer.music.load(os.path.join('assets', '{self.music_file}'))")
            self.write_blank()

        # Create objects
        self.write_comment("Create objects")
        for obj in self.ir.objects:
            self._emit_create_object(obj)

        # Initialize array pools
        if self.ir.array_pools:
            self.write_blank()
            self.write_comment("Array pools")
            for array_name, obj_names in self.ir.array_pools.items():
                obj_refs = ', '.join([f"self.{name}" for name in obj_names])
                self.write(f"self.{array_name} = [{obj_refs}]")

        # Init actions
        if self.ir.init_actions:
            self.write_blank()
            self.write_comment("Init actions")
            for action in self.ir.init_actions:
                if action:
                    code = self.emit_action(action)
                    if code:
                        self._write_with_markers(code)

        # Set initial scene/level visibility
        if self.uses_scenes:
            self.write_blank()
            self.write_comment("Set initial scene/level visibility")
            self.write("self.update_scene_visibility()")

        self.dedent()
        self.write_blank()

    def _emit_create_object(self, obj: IR_Object):
        """Emit code to create an object.

        Hidden objects (name starts with '_') still have their properties initialized
        for game state, but are not rendered visually.
        """
        # Hidden objects: create properties but no visual representation
        if obj.hidden:
            self.write_comment(f"Hidden data object: {obj.name}")
            self.write(f"self.{obj.name} = {{ }}")
            for prop_name, prop_value in obj.properties.items():
                val = self.get_value(prop_value)
                if isinstance(val, str):
                    self.write(f"self.{obj.name}_{prop_name} = '{val}'")
                elif isinstance(val, bool):
                    self.write(f"self.{obj.name}_{prop_name} = {val}")
                else:
                    self.write(f"self.{obj.name}_{prop_name} = {val}")
            return

        x = self._get_prop_value(obj, 'x', 0.5)
        y = self._get_prop_value(obj, 'y', 0.5)
        px = self.to_target_x(x)
        py = self.to_target_y(y)

        # HUD objects
        if 'target' in obj.properties:
            # HUD is handled in draw()
            return

        # Regular objects
        w = self._get_prop_value(obj, 'width', 0.05)
        h = self._get_prop_value(obj, 'height', 0.05)
        pw = self.to_target_width(w)
        ph = self.to_target_height(h)

        self.write(f"self.{obj.name} = pygame.Rect({int(px - pw/2)}, {int(py - ph/2)}, {int(pw)}, {int(ph)})")

        # Set properties as attributes
        for prop_name, prop_value in obj.properties.items():
            if prop_name not in ('x', 'y', 'width', 'height', 'sprite'):
                val = self.get_value(prop_value)
                if prop_name == 'color':
                    color = self._get_color_tuple(val)
                    self.write(f"self.{obj.name}_color = {color}")
                elif isinstance(val, str):
                    self.write(f"self.{obj.name}_{prop_name} = '{val}'")
                elif isinstance(val, bool):
                    self.write(f"self.{obj.name}_{prop_name} = {val}")
                else:
                    self.write(f"self.{obj.name}_{prop_name} = {val}")

        # Default color if not set
        if 'color' not in obj.properties:
            color = self.DEFAULT_COLORS[self.color_index % len(self.DEFAULT_COLORS)]
            self.write(f"self.{obj.name}_color = {color}")
            self.color_index += 1

        # Sprite reference
        if 'sprite' in obj.properties:
            sprite = obj.properties['sprite'].value
            key = self._asset_key(sprite)
            self.write(f"self.{obj.name}_sprite = '{key}'")

        # Scene/level membership
        if obj.scene is not None:
            self.write(f"self.{obj.name}_scene = '{obj.scene}'")
        if obj.level is not None:
            self.write(f"self.{obj.name}_level = {obj.level}")

    def _emit_run(self):
        """Emit run method (main game loop)."""
        self.write("def run(self):")
        self.indent()
        self.write("while self.running:")
        self.indent()
        self.write_comment("Process network messages from shared world")
        self.write("if self.network:")
        self.indent()
        self.write("self.network.process_messages()")
        self.dedent()
        self.write("self.handle_events()")
        self.write("self.update()")
        self.write("self.draw()")
        self.write("self.clock.tick(60)")
        self.dedent()
        self.write("pygame.quit()")
        self.write("sys.exit()")
        self.dedent()
        self.write_blank()

    def _emit_handle_events(self):
        """Emit event handling method."""
        self.write("def handle_events(self):")
        self.indent()
        self.write("for event in pygame.event.get():")
        self.indent()
        self.write("if event.type == pygame.QUIT:")
        self.indent()
        self.write("self.running = False")
        self.dedent()

        # Console handling
        self.write("elif event.type == pygame.KEYDOWN:")
        self.indent()
        self.write_comment("Console toggle with backtick")
        self.write("if event.key == pygame.K_BACKQUOTE:")
        self.indent()
        self.write("self.console_visible = not self.console_visible")
        self.dedent()
        self.write("elif self.console_visible:")
        self.indent()
        self.write_comment("Console input handling")
        self.write("if event.key == pygame.K_RETURN:")
        self.indent()
        self.write("self.process_console_command(self.console_input)")
        self.write("self.console_history.append(self.console_input)")
        self.write("self.console_input = ''")
        self.dedent()
        self.write("elif event.key == pygame.K_BACKSPACE:")
        self.indent()
        self.write("self.console_input = self.console_input[:-1]")
        self.dedent()
        self.write("elif event.key == pygame.K_ESCAPE:")
        self.indent()
        self.write("self.console_visible = False")
        self.dedent()
        self.write("elif event.unicode and event.unicode.isprintable():")
        self.indent()
        self.write("self.console_input += event.unicode")
        self.dedent()
        self.dedent()

        # Game keydown events (only when console not visible)
        if self.keydown_events:
            self.write("elif not self.console_visible:")
            self.indent()
            for key, handlers_list in self.keydown_events.items():
                pygame_key = self._pygame_key(key)
                self.write(f"if event.key == {pygame_key}:")
                self.indent()
                # Each handler_lines is a list of code lines for one event handler
                for handler_lines in handlers_list:
                    for line in handler_lines:
                        # Handle multi-line strings with indentation markers
                        self._write_with_markers(line)
                self.dedent()
            self.dedent()

        self.dedent()  # close elif KEYDOWN
        self.dedent()  # close for event loop
        self.dedent()  # close method body
        self.write_blank()

    def _emit_update(self):
        """Emit update method."""
        self.write("def update(self):")
        self.indent()

        # Player movement (held keys)
        if self.player_objects:
            self.write("keys = pygame.key.get_pressed()")
            for player in self.player_objects:
                self.write(f"speed = getattr(self, '{player}_speed', 5)")
                self.write(f"if keys[pygame.K_LEFT] or keys[pygame.K_a]:")
                self.indent()
                self.write(f"self.{player}.x -= speed")
                self.dedent()
                self.write(f"if keys[pygame.K_RIGHT] or keys[pygame.K_d]:")
                self.indent()
                self.write(f"self.{player}.x += speed")
                self.dedent()
                self.write(f"if keys[pygame.K_UP] or keys[pygame.K_w]:")
                self.indent()
                self.write(f"self.{player}.y -= speed")
                self.dedent()
                self.write(f"if keys[pygame.K_DOWN] or keys[pygame.K_s]:")
                self.indent()
                self.write(f"self.{player}.y += speed")
                self.dedent()

        # Collision detection
        if self.collision_events:
            self.write_blank()
            self.write_comment("Collision detection")
            for obj_a, obj_b, handler_lines in self.collision_events:
                self.write(f"if self.{obj_a}.colliderect(self.{obj_b}):")
                self.indent()
                for line in handler_lines:
                    self._write_with_markers(line)
                self.dedent()

        # Update event handlers (game logic that runs every frame)
        if self.update_handlers:
            self.write_blank()
            self.write_comment("Update event handlers")
            for handler_lines in self.update_handlers:
                for line in handler_lines:
                    self._write_with_markers(line)

        if not self.player_objects and not self.collision_events and not self.update_handlers:
            self.write("pass")

        self.dedent()
        self.write_blank()

    def _emit_draw(self):
        """Emit draw method."""
        self.write("def draw(self):")
        self.indent()
        bg_color = self.meta.get('canvas', {}).get('background', '#1a1a2e')
        rgb = self._hex_to_rgb(bg_color)
        self.write(f"self.screen.fill({rgb})")
        self.write_blank()

        # Draw objects
        self.write_comment("Draw objects")
        for obj in self.ir.objects:
            if obj.hidden:
                continue  # Skip hidden objects (game state, not rendered)
            if 'target' in obj.properties:
                continue  # Skip HUD objects here

            # Check if object has text property (render as text)
            if 'text' in obj.properties:
                self.write(f"if getattr(self, '{obj.name}_visible', True):")
                self.indent()
                self.write(f"_font = pygame.font.Font(None, self.{obj.name}_font_size)")
                self.write(f"_text_surf = _font.render(self.{obj.name}_text, True, self.{obj.name}_color)")
                self.write(f"_text_rect = _text_surf.get_rect(center=(self.{obj.name}.centerx, self.{obj.name}.centery))")
                self.write(f"self.screen.blit(_text_surf, _text_rect)")
                self.dedent()
            elif 'sprite' in obj.properties:
                key = self._asset_key(obj.properties['sprite'].value)
                self.write(f"if getattr(self, '{obj.name}_visible', True):")
                self.indent()
                # Scale sprite to object's rect size
                self.write(f"_sprite = pygame.transform.scale(self.sprites['{key}'], (self.{obj.name}.width, self.{obj.name}.height))")
                self.write(f"self.screen.blit(_sprite, self.{obj.name})")
                self.dedent()
            else:
                self.write(f"if getattr(self, '{obj.name}_visible', True):")
                self.indent()
                self.write(f"pygame.draw.rect(self.screen, self.{obj.name}_color, self.{obj.name})")
                self.dedent()

        # Draw HUD
        if self.hud_objects:
            self.write_blank()
            self.write_comment("Draw HUD")
            for hud_name, target in self.hud_objects:
                hud_obj = None
                for o in self.ir.objects:
                    if o.name == hud_name:
                        hud_obj = o
                        break
                if hud_obj:
                    x = self._get_prop_value(hud_obj, 'x', 0.02)
                    y = self._get_prop_value(hud_obj, 'y', 0.02)
                    px = int(self.to_target_x(x))
                    py = int(self.to_target_y(y))

                    target_obj = None
                    for o in self.ir.objects:
                        if o.name == target:
                            target_obj = o
                            break

                    y_offset = py
                    if target_obj and 'lives' in target_obj.properties:
                        self.write(f"lives_text = self.font.render(f'Lives: {{self.{target}_lives}}', True, (255, 255, 255))")
                        self.write(f"self.screen.blit(lives_text, ({px}, {y_offset}))")
                        y_offset += 20
                    if target_obj and 'score' in target_obj.properties:
                        self.write(f"score_text = self.font.render(f'Score: {{self.{target}_score}}', True, (255, 255, 255))")
                        self.write(f"self.screen.blit(score_text, ({px}, {y_offset}))")

        # Draw dynamically created objects (from console)
        self.write_blank()
        self.write_comment("Draw dynamically created objects")
        self.write("for attr in dir(self):")
        self.indent()
        self.write("if not attr.startswith('_') and isinstance(getattr(self, attr, None), pygame.Rect):")
        self.indent()
        known_objects = [obj.name for obj in self.ir.objects if 'target' not in obj.properties and not obj.hidden]
        self.write(f"if attr not in {known_objects}:")
        self.indent()
        self.write("rect = getattr(self, attr)")
        self.write("if getattr(self, f'{attr}_visible', True) and rect.width > 0:")
        self.indent()
        self.write("color = getattr(self, f'{attr}_color', (0, 255, 0))")
        self.write("pygame.draw.rect(self.screen, color, rect)")
        self.dedent()
        self.dedent()
        self.dedent()
        self.dedent()

        self.write_blank()
        self.write_comment("Draw console overlay")
        self.write("if self.console_visible:")
        self.indent()
        self.write("self.draw_console()")
        self.dedent()

        self.write_blank()
        self.write("pygame.display.flip()")
        self.dedent()
        self.write_blank()

    def _emit_helper_methods(self):
        """Emit any helper methods needed."""
        # Always emit console methods
        self._emit_console_methods()

        # Network callback methods (Project Twin)
        self._emit_network_callbacks()

        if self.uses_scenes:
            self._emit_scene_visibility_method()
        if self.uses_save_load:
            self._emit_save_load_methods()

    def _emit_console_methods(self):
        """Emit console drawing and command processing methods."""
        # Draw console method
        self.write("def draw_console(self):")
        self.indent()
        self.write_comment("Draw semi-transparent console overlay")
        self.write("console_height = 200")
        self.write("console_surf = pygame.Surface((self.screen.get_width(), console_height))")
        self.write("console_surf.set_alpha(220)")
        self.write("console_surf.fill((20, 20, 40))")
        self.write("self.screen.blit(console_surf, (0, 0))")
        self.write_blank()

        self.write_comment("Draw console header")
        self.write("header = self.console_font.render('Rosh Console (` to close, Enter to execute)', True, (100, 200, 255))")
        self.write("self.screen.blit(header, (10, 5))")
        self.write_blank()

        self.write_comment("Draw output lines")
        self.write("y = 25")
        self.write("for line in self.console_output[-7:]:")
        self.indent()
        self.write("color = (200, 200, 200) if not line.startswith('Error') else (255, 100, 100)")
        self.write("text = self.console_font.render(line, True, color)")
        self.write("self.screen.blit(text, (10, y))")
        self.write("y += 18")
        self.dedent()
        self.write_blank()

        self.write_comment("Draw input line")
        self.write("pygame.draw.rect(self.screen, (40, 40, 60), (5, console_height - 25, self.screen.get_width() - 10, 22))")
        self.write("prompt = self.console_font.render('> ' + self.console_input + '_', True, (0, 255, 255))")
        self.write("self.screen.blit(prompt, (10, console_height - 22))")
        self.dedent()
        self.write_blank()

        # Process console command method
        self.write("def process_console_command(self, cmd):")
        self.indent()
        self.write("if not cmd.strip():")
        self.indent()
        self.write("return")
        self.dedent()
        self.write_blank()

        self.write("parts = cmd.strip().split()")
        self.write("command = parts[0].lower()")
        self.write_blank()

        self.write("try:")
        self.indent()

        # list command
        self.write("if command in ('list', 'ls', 'objects'):")
        self.indent()
        self.write("objects = [name for name in dir(self) if isinstance(getattr(self, name, None), pygame.Rect)]")
        self.write("self.console_output.append('Objects: ' + ', '.join(objects) if objects else 'No objects')")
        self.dedent()

        # look command
        self.write("elif command in ('look', 'l', 'examine', 'x', 'dump'):")
        self.indent()
        self.write("if len(parts) > 1:")
        self.indent()
        self.write("name = parts[1]")
        self.write("rect = getattr(self, name, None)")
        self.write("if rect:")
        self.indent()
        self.write("color = getattr(self, f'{name}_color', 'N/A')")
        self.write("visible = getattr(self, f'{name}_visible', True)")
        self.write("self.console_output.append(f'{name}: x={rect.x}, y={rect.y}, w={rect.width}, h={rect.height}')")
        self.write("self.console_output.append(f'  color={color}, visible={visible}')")
        self.dedent()
        self.write("else:")
        self.indent()
        self.write("self.console_output.append(f'Object not found: {name}')")
        self.dedent()
        self.dedent()
        self.write("else:")
        self.indent()
        self.write("self.console_output.append('Usage: look <object>')")
        self.dedent()
        self.dedent()

        # set command: "set <obj> <prop> to <value>" or "set <obj> <color>"
        self.write("elif command == 'set':")
        self.indent()
        self.write_comment("Parse: set <obj> <prop> to <value>  OR  set <obj> <color>")
        self.write("if len(parts) >= 5 and parts[3] == 'to':")
        self.indent()
        self.write("name, prop, value = parts[1], parts[2], ' '.join(parts[4:])")
        self.dedent()
        self.write("elif len(parts) == 4 and parts[2] == 'to':")
        self.indent()
        self.write_comment("set <obj> to <color> - shorthand for color")
        self.write("name, prop, value = parts[1], 'color', parts[3]")
        self.dedent()
        self.write("elif len(parts) == 3:")
        self.indent()
        self.write_comment("set <obj> <color> - even shorter")
        self.write("name, prop, value = parts[1], 'color', parts[2]")
        self.dedent()
        self.write("else:")
        self.indent()
        self.write("self.console_output.append('Usage: set <obj> <prop> to <value>')")
        self.write("return")
        self.dedent()
        self.write_blank()

        self.write("rect = getattr(self, name, None)")
        self.write("if not rect:")
        self.indent()
        self.write("self.console_output.append(f'Object not found: {name}')")
        self.write("return")
        self.dedent()
        self.write_blank()

        self.write("if prop == 'x':")
        self.indent()
        self.write("rect.x = int(value)")
        self.dedent()
        self.write("elif prop == 'y':")
        self.indent()
        self.write("rect.y = int(value)")
        self.dedent()
        self.write("elif prop in ('width', 'w'):")
        self.indent()
        self.write("rect.width = int(value)")
        self.dedent()
        self.write("elif prop in ('height', 'h'):")
        self.indent()
        self.write("rect.height = int(value)")
        self.dedent()
        self.write("elif prop == 'text':")
        self.indent()
        self.write("setattr(self, f'{name}_text', value)")
        self.dedent()
        self.write("elif prop in ('color', 'colour'):")
        self.indent()
        self.write("colors = {'red': (255,0,0), 'green': (0,255,0), 'blue': (0,0,255), 'yellow': (255,255,0), 'cyan': (0,255,255), 'magenta': (255,0,255), 'white': (255,255,255), 'black': (0,0,0), 'orange': (255,136,0), 'purple': (136,0,255)}")
        self.write("setattr(self, f'{name}_color', colors.get(value.lower(), (0,255,0)))")
        self.dedent()
        self.write("elif prop == 'visible':")
        self.indent()
        self.write("setattr(self, f'{name}_visible', value.lower() in ('true', '1', 'yes', 'on'))")
        self.dedent()
        self.write("else:")
        self.indent()
        self.write_comment("Generic property set")
        self.write("setattr(self, f'{name}_{prop}', value)")
        self.dedent()
        self.write("self.console_output.append(f'{name}.{prop} = {value}')")
        self.dedent()

        # hide/show commands
        self.write("elif command == 'hide':")
        self.indent()
        self.write("if len(parts) > 1:")
        self.indent()
        self.write("setattr(self, f'{parts[1]}_visible', False)")
        self.write("self.console_output.append(f'{parts[1]} hidden')")
        self.dedent()
        self.dedent()

        self.write("elif command in ('show', 'unhide'):")
        self.indent()
        self.write("if len(parts) > 1:")
        self.indent()
        self.write("setattr(self, f'{parts[1]}_visible', True)")
        self.write("self.console_output.append(f'{parts[1]} visible')")
        self.dedent()
        self.dedent()

        # create command: "create <name>" or "create 3 boxes" or "create <name> at <x> <y>"
        self.write("elif command == 'create':")
        self.indent()
        self.write("if len(parts) < 2:")
        self.indent()
        self.write("self.console_output.append('Usage: create <name> [at <x> <y>]')")
        self.write("return")
        self.dedent()
        self.write_blank()
        self.write_comment("Handle 'create 3 boxes' syntax")
        self.write("count = 1")
        self.write("base_name = parts[1]")
        self.write("if parts[1].isdigit() and len(parts) >= 3:")
        self.indent()
        self.write("count = int(parts[1])")
        self.write("base_name = parts[2]")
        self.dedent()
        self.write_blank()
        self.write("for i in range(count):")
        self.indent()
        self.write("name = base_name")
        self.write_comment("Auto-number if name exists")
        self.write("counter = 1")
        self.write("while hasattr(self, name):")
        self.indent()
        self.write("counter += 1")
        self.write("name = f'{base_name}-{counter}'")
        self.dedent()
        self.write_comment("Offset multiple objects so they don't stack")
        self.write("x, y = 400 + (i * 60), 300")
        self.write("setattr(self, name, pygame.Rect(x - 25, y - 25, 50, 50))")
        self.write("setattr(self, f'{name}_color', (0, 255, 0))")
        self.write("setattr(self, f'{name}_visible', True)")
        self.write("self.console_output.append(f'Created {name} at ({x}, {y})')")
        self.write_comment("Broadcast to network if connected")
        self.write("if self.network and self.network.is_connected():")
        self.indent()
        self.write("self.network.broadcast_create(name, {'type': base_name, 'x': (x - 400) / 50, 'z': (y - 300) / 50, 'color': 'green'})")
        self.dedent()
        self.dedent()
        self.dedent()

        # connect command (Project Twin)
        self.write("elif command in ('connect', 'twin'):")
        self.indent()
        self.write("if self.network:")
        self.indent()
        self.write("world_id = parts[1] if len(parts) > 1 else 'default'")
        self.write("self.network.connect(world_id)")
        self.dedent()
        self.write("else:")
        self.indent()
        self.write("self.console_output.append('Network not available. Install: pip install websocket-client')")
        self.dedent()
        self.dedent()

        # disconnect command
        self.write("elif command == 'disconnect':")
        self.indent()
        self.write("if self.network:")
        self.indent()
        self.write("self.network.disconnect()")
        self.dedent()
        self.dedent()

        # say command
        self.write("elif command == 'say':")
        self.indent()
        self.write("if self.network:")
        self.indent()
        self.write("message = ' '.join(parts[1:]) if len(parts) > 1 else ''")
        self.write("self.network.say(message)")
        self.dedent()
        self.dedent()

        # users/who command
        self.write("elif command in ('users', 'who'):")
        self.indent()
        self.write("if self.network:")
        self.indent()
        self.write("self.network.list_users()")
        self.dedent()
        self.dedent()

        # help command
        self.write("elif command == 'help':")
        self.indent()
        self.write("self.console_output.append('Commands: list, look <obj>, set <obj> <prop> to <value>')")
        self.write("self.console_output.append('          hide <obj>, show <obj>, create <name>, help')")
        self.write("self.console_output.append('Network: connect [world], disconnect, say <msg>, users')")
        self.dedent()

        # unknown command
        self.write("else:")
        self.indent()
        self.write("self.console_output.append(f'Unknown command: {command}')")
        self.dedent()

        self.dedent()  # try
        self.write("except Exception as e:")
        self.indent()
        self.write("self.console_output.append(f'Error: {e}')")
        self.dedent()

        self.dedent()  # function
        self.write_blank()

    def _emit_network_callbacks(self):
        """Emit network callback methods for Project Twin shared worlds."""
        # _network_create_object callback
        self.write("def _network_create_object(self, obj_id, data):")
        self.indent()
        self.write_comment("Called when another user creates an object")
        self.write("if hasattr(self, obj_id):")
        self.indent()
        self.write("return  # Object already exists")
        self.dedent()
        self.write_blank()
        self.write_comment("Transform 3D coords to 2D: Three.js x,z -> Pygame x,y")
        self.write("x = data.get('x', 0)")
        self.write("z = data.get('z', 0)  # In 3D, z is horizontal depth")
        self.write("px = 400 + (x * 50)  # Center + scale")
        self.write("py = 300 + (z * 50)")
        self.write_blank()
        self.write("rect = pygame.Rect(int(px) - 25, int(py) - 25, 50, 50)")
        self.write("setattr(self, obj_id, rect)")
        self.write_blank()
        self.write_comment("Parse color")
        self.write("color = data.get('color', 'green')")
        self.write("colors = {'red': (255,0,0), 'green': (0,255,0), 'blue': (0,0,255), 'yellow': (255,255,0), 'cyan': (0,255,255), 'magenta': (255,0,255), 'white': (255,255,255), 'black': (0,0,0), 'orange': (255,136,0), 'purple': (136,0,255)}")
        self.write("if isinstance(color, str):")
        self.indent()
        self.write("color_tuple = colors.get(color.lower(), (0, 255, 0))")
        self.dedent()
        self.write("elif isinstance(color, int):")
        self.indent()
        self.write("color_tuple = ((color >> 16) & 0xFF, (color >> 8) & 0xFF, color & 0xFF)")
        self.dedent()
        self.write("else:")
        self.indent()
        self.write("color_tuple = (0, 255, 0)")
        self.dedent()
        self.write("setattr(self, f'{obj_id}_color', color_tuple)")
        self.write("setattr(self, f'{obj_id}_visible', True)")
        self.dedent()
        self.write_blank()

        # _network_delete_object callback
        self.write("def _network_delete_object(self, obj_id):")
        self.indent()
        self.write_comment("Called when another user deletes an object")
        self.write("if hasattr(self, obj_id):")
        self.indent()
        self.write("rect = getattr(self, obj_id)")
        self.write("rect.width = 0")
        self.write("rect.height = 0")
        self.write("setattr(self, f'{obj_id}_visible', False)")
        self.dedent()
        self.dedent()
        self.write_blank()

        # _network_move_object callback
        self.write("def _network_move_object(self, obj_id, x, y, z):")
        self.indent()
        self.write_comment("Called when another user moves an object")
        self.write("if hasattr(self, obj_id):")
        self.indent()
        self.write("rect = getattr(self, obj_id)")
        self.write_comment("Transform 3D coords to 2D")
        self.write("px = 400 + (x * 50)")
        self.write("py = 300 + (z * 50)  # Use z for depth in 3D")
        self.write("rect.centerx = int(px)")
        self.write("rect.centery = int(py)")
        self.dedent()
        self.dedent()
        self.write_blank()

    def _emit_scene_visibility_method(self):
        """Emit update_scene_visibility helper method."""
        self.write("def update_scene_visibility(self):")
        self.indent()
        self.write_comment("Roshonic \"Dimensions, Not Modes\" - scene/level as coordinates")

        for obj in self.ir.objects:
            if obj.scene is None and obj.level is None:
                continue  # Always visible, skip

            conditions = []
            if obj.scene is not None:
                conditions.append(f"self.current_scene == '{obj.scene}'")
            if obj.level is not None:
                conditions.append(f"self.current_level == {obj.level}")

            condition = " and ".join(conditions)
            self.write(f"self.{obj.name}_visible = ({condition})")

        self.dedent()
        self.write_blank()

    def _emit_save_load_methods(self):
        """Emit save/load game methods using JSON files."""
        saveable_objects = [obj for obj in self.ir.objects if obj.saveable]

        # save_game method
        self.write("def save_game(self, slot):")
        self.indent()
        self.write("import json")
        self.write("import os")
        self.write("save_data = {")
        self.indent()
        self.write("'version': '1.0',")
        if self.uses_scenes:
            self.write("'scene': self.current_scene,")
            self.write("'level': self.current_level,")
        self.write("'objects': {}")
        self.dedent()
        self.write("}")
        self.write_blank()

        for obj in saveable_objects:
            self.write(f"save_data['objects']['{obj.name}'] = {{")
            self.indent()
            self.write(f"'x': self.{obj.name}_x,")
            self.write(f"'y': self.{obj.name}_y,")
            for prop_name in obj.properties:
                if prop_name not in ('x', 'y', 'width', 'height', 'sprite', 'color', 'text', 'saveable'):
                    self.write(f"'{prop_name}': self.{obj.name}_{prop_name},")
            self.dedent()
            self.write("}")

        self.write_blank()
        self.write("os.makedirs('saves', exist_ok=True)")
        self.write("with open(f'saves/{slot}.json', 'w') as f:")
        self.indent()
        self.write("json.dump(save_data, f)")
        self.dedent()
        self.write("print(f'Game saved to slot: {slot}')")
        self.dedent()
        self.write_blank()

        # load_game method
        self.write("def load_game(self, slot):")
        self.indent()
        self.write("import json")
        self.write("import os")
        self.write("filepath = f'saves/{slot}.json'")
        self.write("if not os.path.exists(filepath):")
        self.indent()
        self.write("print(f'No save found in slot: {slot}')")
        self.write("return")
        self.dedent()
        self.write("with open(filepath, 'r') as f:")
        self.indent()
        self.write("save_data = json.load(f)")
        self.dedent()
        self.write_blank()

        if self.uses_scenes:
            self.write("if 'scene' in save_data:")
            self.indent()
            self.write("self.current_scene = save_data['scene']")
            self.dedent()
            self.write("if 'level' in save_data:")
            self.indent()
            self.write("self.current_level = save_data['level']")
            self.dedent()
            self.write("self.update_scene_visibility()")
            self.write_blank()

        self.write("objects = save_data.get('objects', {})")
        for obj in saveable_objects:
            self.write(f"if '{obj.name}' in objects:")
            self.indent()
            self.write(f"data = objects['{obj.name}']")
            self.write(f"if 'x' in data: self.{obj.name}_x = data['x']")
            self.write(f"if 'y' in data: self.{obj.name}_y = data['y']")
            for prop_name in obj.properties:
                if prop_name not in ('x', 'y', 'width', 'height', 'sprite', 'color', 'text', 'saveable'):
                    self.write(f"if '{prop_name}' in data: self.{obj.name}_{prop_name} = data['{prop_name}']")
            self.dedent()

        self.write("print(f'Game loaded from slot: {slot}')")
        self.dedent()
        self.write_blank()

    def _write_with_markers(self, code: str):
        """Write code that may contain relative indentation markers.

        Lines starting with '>' are indented one additional level.
        Multiple '>' prefixes add multiple levels.
        """
        for line in code.split('\n'):
            # Count leading '>' markers
            extra_indent = 0
            while line.startswith('>'):
                extra_indent += 1
                line = line[1:]

            # Apply extra indentation
            for _ in range(extra_indent):
                self.indent()

            self.write(line)

            # Restore indentation
            for _ in range(extra_indent):
                self.dedent()

    def _emit_functions(self):
        """Emit user-defined functions."""
        for func in self.ir.functions:
            params = ", ".join(["self"] + func.params)
            self.write(f"def {func.name}({params}):")
            self.indent()
            if func.body:
                for action in func.body:
                    if action:
                        code = self.emit_action(action)
                        if code:
                            self._write_with_markers(code)
            else:
                self.write("pass")
            self.dedent()
            self.write_blank()

    def _emit_main(self):
        """Emit main entry point."""
        self.write("if __name__ == '__main__':")
        self.indent()
        self.write("game = Game()")
        self.write("game.run()")
        self.dedent()

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
                return f"print({expr})"
            return "print()"
        elif action_type == 'play_sound':
            key = self._asset_key(params.get('asset', ''))
            return f"self.sounds['{key}'].play()"
        elif action_type == 'play_music':
            return "pygame.mixer.music.play(-1)"
        elif action_type == 'stop_music':
            return "pygame.mixer.music.stop()"
        elif action_type == 'destroy':
            target = params.get('target', '')
            return f"self.{target} = pygame.Rect(0, 0, 0, 0)"
        elif action_type == 'return':
            value = params.get('value')
            if value:
                return f"return {self.emit_expression(value)}"
            return "return"
        elif action_type == 'call':
            func_name = params.get('function', '')
            args = params.get('args', [])
            arg_strs = [self.emit_expression(a) for a in args]
            return f"self.{func_name}({', '.join(arg_strs)})"
        elif action_type == 'goto':
            scene = params.get('scene')
            level = params.get('level')
            code_parts = []
            if scene is not None:
                code_parts.append(f"self.current_scene = '{scene}'")
            if level is not None:
                code_parts.append(f"self.current_level = {level}")
            code_parts.append("self.update_scene_visibility()")
            return "\n".join(code_parts)

        elif action_type == 'save_game':
            slot = params.get('slot') or 'default'
            self.uses_save_load = True
            return f"self.save_game('{slot}')"

        elif action_type == 'load_game':
            slot = params.get('slot') or 'default'
            self.uses_save_load = True
            return f"self.load_game('{slot}')"

        return f"pass  # TODO: {action_type}"

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

        # Position properties update rect directly
        if prop == 'x':
            return f"self.{target}.centerx = {val_str}"
        elif prop == 'y':
            return f"self.{target}.centery = {val_str}"
        else:
            return f"self.{target}_{prop} = {val_str}"

    def _emit_conditional(self, cond: IR_Conditional) -> str:
        """Emit conditional as Python code.

        Returns lines with relative indentation markers:
        - Lines starting with no indent are at current level
        - Lines starting with '>' are indented one level deeper
        """
        condition = self.emit_expression(cond.condition)
        lines = [f"if {condition}:"]

        has_then = False
        for action in cond.then_actions:
            if action:
                code = self.emit_action(action)
                if code:
                    for subline in code.split('\n'):
                        lines.append(f">{subline}")
                    has_then = True

        if not has_then:
            lines.append(">pass")

        if cond.else_actions:
            lines.append("else:")
            has_else = False
            for action in cond.else_actions:
                if action:
                    code = self.emit_action(action)
                    if code:
                        for subline in code.split('\n'):
                            lines.append(f">{subline}")
                        has_else = True
            if not has_else:
                lines.append(">pass")

        return '\n'.join(lines)

    def emit_loop(self, loop: IR_Loop) -> str:
        """Emit loop as Python code.

        Returns lines with relative indentation markers:
        - Lines starting with no indent are at current level
        - Lines starting with '>' are indented one level deeper
        """
        lines = []

        if loop.type == 'while':
            condition = self.emit_expression(loop.condition)
            lines.append(f"while {condition}:")
        elif loop.type == 'for':
            start = self.emit_expression(loop.start)
            end = self.emit_expression(loop.end)
            step = self.emit_expression(loop.step) if loop.step else "1"
            if step == "1":
                lines.append(f"for {loop.iterator} in range({start}, {end} + 1):")
            else:
                lines.append(f"for {loop.iterator} in range({start}, {end} + 1, {step}):")
        elif loop.type == 'for_each':
            iterable = self.emit_expression(loop.iterable)
            # Add self. prefix if iterable is a simple identifier (array pool name)
            if iterable.isidentifier():
                iterable = f"self.{iterable}"
            lines.append(f"for {loop.iterator} in {iterable}:")

        has_body = False
        for action in loop.body:
            if action:
                code = self.emit_action(action)
                if code:
                    for subline in code.split('\n'):
                        lines.append(f">{subline}")
                    has_body = True

        if not has_body:
            lines.append(">pass")

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
            # Check if it's a position property
            if expr.right in ('x', 'y'):
                attr = 'centerx' if expr.right == 'x' else 'centery'
                return f"self.{expr.left}.{attr}"
            return f"self.{expr.left}_{expr.right}"
        elif expr.type == 'comparison':
            left = self.emit_expression(expr.left)
            right = self.emit_expression(expr.right)
            return f"{left} {expr.operator} {right}"
        elif expr.type == 'binary_op':
            left = self.emit_expression(expr.left)
            right = self.emit_expression(expr.right)
            op = expr.operator
            if op == 'and':
                op = 'and'
            elif op == 'or':
                op = 'or'
            return f"({left} {op} {right})"
        elif expr.type == 'unary_op':
            right = self.emit_expression(expr.right)
            op = expr.operator
            if op == 'not':
                op = 'not '
            return f"{op}{right}"
        elif expr.type == 'list_index':
            # Array index: arr[0] -> self.arr[0]
            # Handle the case where left is a literal string (variable name)
            # Note: IR_Value is imported at module level
            if (expr.left and expr.left.type == 'literal' and
                isinstance(expr.left.value, IR_Value) and expr.left.value.type == 'string'):
                # It's a variable name stored as string literal
                list_expr = f"self.{expr.left.value.value}"
            else:
                list_expr = self.emit_expression(expr.left)
                # If list_expr is a simple identifier, add self. prefix
                if list_expr.isidentifier():
                    list_expr = f"self.{list_expr}"
            index_expr = self.emit_expression(expr.right) if expr.right else '0'
            return f"{list_expr}[{index_expr}]"

        return str(expr)

    def emit_object(self, obj: IR_Object) -> str:
        """Generate code for object (for testing)."""
        return ""

    def emit_event(self, event: IR_Event) -> str:
        """Generate code for event (for testing)."""
        return ""

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _format_value(self, value: IR_Value, context: str = None) -> str:
        """Format IR_Value for Python.

        Args:
            value: The IR_Value to format
            context: Optional context (property name) to determine coordinate conversion
        """
        if value.type == 'string':
            # Handle string interpolation
            text = str(value.value)
            # Convert {obj.prop} to {self.obj_prop}
            import re
            text = re.sub(r'\{(\w+)\.(\w+)\}', r'{self.\1_\2}', text)
            text = re.sub(r'\{(\w+)\}', r'{self.\1}', text)
            return f"f'{text}'"
        elif value.type == 'number':
            return str(value.value)
        elif value.type == 'boolean':
            return 'True' if value.value else 'False'
        elif value.type == 'percentage':
            # Convert percentage to pixels based on context
            if context in ('x', 'width'):
                return str(self.to_target_x(value.value))
            elif context in ('y', 'height'):
                return str(self.to_target_y(value.value))
            return str(value.value)
        elif value.type == 'color':
            return str(self._get_color_tuple(value.value))
        elif value.type == 'expression':
            return self.emit_expression(value.value)
        else:
            return str(value.value)

    def _get_prop_value(self, obj: IR_Object, prop: str, default: float) -> float:
        """Get property value from object."""
        if prop in obj.properties:
            val = obj.properties[prop]
            if val.type == 'percentage':
                return val.value
            elif val.type == 'number':
                return val.value
        return default

    def _get_color_tuple(self, color_value) -> tuple:
        """Convert hex color to RGB tuple."""
        if isinstance(color_value, int):
            r = (color_value >> 16) & 0xFF
            g = (color_value >> 8) & 0xFF
            b = color_value & 0xFF
            return (r, g, b)
        return (0, 255, 0)  # Default green

    def _hex_to_rgb(self, hex_color: str) -> tuple:
        """Convert hex color string to RGB tuple."""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 6:
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        return (26, 26, 46)  # Default dark blue

    def _asset_key(self, filename: str) -> str:
        """Convert filename to asset key."""
        return filename.replace('.', '_').replace('/', '_')

    def _pygame_key(self, key: str) -> str:
        """Convert Rosh key name to Pygame constant."""
        key_map = {
            'space': 'pygame.K_SPACE',
            'enter': 'pygame.K_RETURN',
            'escape': 'pygame.K_ESCAPE',
            'left': 'pygame.K_LEFT',
            'right': 'pygame.K_RIGHT',
            'up': 'pygame.K_UP',
            'down': 'pygame.K_DOWN',
        }
        return key_map.get(key.lower(), f"pygame.K_{key.lower()}")
