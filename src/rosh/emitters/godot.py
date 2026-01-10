"""
Godot Emitter - IR to GDScript

Converts IR representation to Godot GDScript code.
This is a "mechanical translator" - all semantic decisions are in the IR.

Usage:
    from rosh.emitters.godot import GodotEmitter

    ir = transform_ast_to_ir(ast)
    emitter = GodotEmitter(ir)
    gd_code = emitter.emit()

See: rosh-dev/proposals/ROSH-IR-SPECIFICATION.md
See: rosh-dev/proposals/GODOT-EMITTER-PROPOSAL.md

⚠️  OUT OF SYNC - SPEC 0.3 (2026-01-10)
========================================
Status: NOT COMPLIANT - needs significant work

This emitter is behind Phaser/ThreeJS and missing Spec 0.3 features:
- No rosh-network.js equivalent (no multiplayer/Project Twin)
- No REQUEST/CONFIRMED protocol support
- Colors/sizes hardcoded, not from spec
- No REPL support
- Missing object types, properties from spec

TO BRING INTO SYNC:
1. Create rosh_network.gd for multiplayer (match JS protocol)
2. Create rosh_colors.gd / rosh_sizes.gd from spec
3. Implement REPL commands from spec
4. Add spec compliance tests for Godot output
5. Test with rosh.cloud World Center

Priority: LOW - Godot demos work for local testing
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


class GodotEmitter(BaseEmitter):
    """Emit Godot GDScript from Rosh IR.

    Generates a complete Godot project including:
    - project.godot (project file)
    - main.tscn (main scene)
    - main.gd (game logic)
    - Object creation as ColorRect or Sprite2D
    - Event handlers for keyboard input
    """

    # Default object colors (RGB for Godot Color)
    DEFAULT_COLORS = [
        (0.0, 1.0, 0.0),    # green
        (0.0, 0.0, 1.0),    # blue
        (1.0, 0.0, 0.0),    # red
        (1.0, 1.0, 0.0),    # yellow
        (1.0, 0.0, 1.0),    # magenta
        (0.0, 1.0, 1.0),    # cyan
        (1.0, 0.53, 0.0),   # orange
        (0.53, 0.0, 1.0),   # purple
    ]

    def __init__(self, ir: IR_Program, meta: Dict[str, Any] = None):
        super().__init__(ir, meta)
        self.color_index = 0
        self.sprite_assets: Set[str] = set()
        self.sound_assets: Set[str] = set()
        self.needs_keyboard = False
        self.player_objects: Set[str] = set()
        self.keydown_events: Dict[str, List[list]] = {}
        self.continuous_keys: Dict[str, List[list]] = {}
        self.update_handlers: List[list] = []
        self.text_objects: Set[str] = set()  # Objects with text property
        self.sprite_objects: Dict[str, str] = {}  # object_name -> sprite_file
        self.has_meta = False  # Whether meta object is used

        # 3D vs 2D mode - default is 3D, arcade mode is 2D
        self.arcade_mode = self.ir.metadata.extra.get('mode') == 'arcade'

        # Output files
        self.gd_output: List[str] = []
        self.project_godot: str = ""
        self.main_tscn: str = ""

        # Scan IR to detect features
        self._detect_features()

    def _detect_features(self):
        """Scan IR to detect what features are needed."""
        for obj in self.ir.objects:
            # Detect player objects by parent_type OR by name
            if obj.parent_type == 'player' or obj.name == 'player':
                self.player_objects.add(obj.name)
                self.needs_keyboard = True

            # Detect text objects
            if 'text' in obj.properties:
                self.text_objects.add(obj.name)

            if 'sprite' in obj.properties:
                sprite_val = obj.properties['sprite']
                if sprite_val.type == 'string':
                    self.sprite_assets.add(sprite_val.value)
                    self.sprite_objects[obj.name] = sprite_val.value

        # Detect meta object usage
        if self.ir.init_actions:
            for action in self.ir.init_actions:
                if self._action_uses_meta(action):
                    self.has_meta = True
                    break
        if not self.has_meta:
            for event in self.ir.events:
                for action in event.handler:
                    if self._action_uses_meta(action):
                        self.has_meta = True
                        break

        # Scan event handlers
        self._scan_event_handlers()

    def _action_uses_meta(self, action) -> bool:
        """Check if an action uses the meta object."""
        if isinstance(action, IR_Action):
            target = action.params.get('target', '')
            if target == 'meta' or (isinstance(target, str) and target.startswith('meta.')):
                return True
        elif isinstance(action, IR_Conditional):
            # Check condition for meta references
            if self._expr_uses_meta(action.condition):
                return True
            for a in action.then_actions + action.else_actions:
                if self._action_uses_meta(a):
                    return True
        return False

    def _expr_uses_meta(self, expr) -> bool:
        """Check if an expression uses the meta object."""
        if isinstance(expr, IR_Expression):
            if expr.type == 'property_access':
                if expr.left == 'meta':
                    return True
            if hasattr(expr, 'left') and self._expr_uses_meta(expr.left):
                return True
            if hasattr(expr, 'right') and self._expr_uses_meta(expr.right):
                return True
        return False

    def _scan_event_handlers(self):
        """Scan event handlers and categorize them."""
        for event in self.ir.events:
            if event.trigger == 'update':
                self.update_handlers.append(self._generate_handler_code(event))
            elif event.trigger.startswith('keydown:'):
                key = event.trigger.split(':')[1]
                if key not in self.keydown_events:
                    self.keydown_events[key] = []
                self.keydown_events[key].append(self._generate_handler_code(event))
                self.needs_keyboard = True
            elif event.trigger.startswith('continuous:'):
                key = event.trigger.split(':')[1]
                if key not in self.continuous_keys:
                    self.continuous_keys[key] = []
                self.continuous_keys[key].append(self._generate_handler_code(event))
                self.needs_keyboard = True

            self._scan_actions_for_assets(event.handler)

        self._scan_actions_for_assets(self.ir.init_actions)

    def _scan_actions_for_assets(self, actions):
        """Scan actions for sound assets."""
        for action in actions:
            if isinstance(action, IR_Action):
                if action.type == 'play_sound':
                    self.sound_assets.add(action.params.get('asset', ''))
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
        """Generate complete GDScript code."""
        if self.arcade_mode:
            return self._emit_arcade_mode()
        else:
            return self._emit_3d_mode()

    def _emit_arcade_mode(self) -> str:
        """Emit 2D arcade mode (Node2D with draw_*)."""
        self._emit_header()
        self._emit_extends_2d()
        self._emit_variables()
        self._emit_ready()
        self._emit_draw()
        self._emit_process()
        self._emit_input()
        self._emit_helper_methods()
        self._emit_functions()
        return self.get_code()

    def _emit_3d_mode(self) -> str:
        """Emit 3D world mode (Node3D with Camera3D and meshes)."""
        self._emit_header()
        self._emit_extends_3d()
        self._emit_variables_3d()
        self._emit_ready_3d()
        self._emit_process_3d()
        self._emit_input()
        self._emit_helper_methods_3d()
        self._emit_functions()
        return self.get_code()

    def emit_project_godot(self) -> str:
        """Generate project.godot file."""
        width = self.ir.metadata.canvas_width
        height = self.ir.metadata.canvas_height

        # Godot 4 has built-in ui_left/right/up/down actions, no need to redefine
        return f'''; Rosh Generated Project
config_version=5

[application]
config/name="Rosh Game"
run/main_scene="res://main.tscn"
config/features=PackedStringArray("4.2")

[display]
window/size/viewport_width={width}
window/size/viewport_height={height}
'''

    def emit_main_tscn(self) -> str:
        """Generate main.tscn scene file."""
        if self.arcade_mode:
            return '''[gd_scene load_steps=2 format=3]

[ext_resource type="Script" path="res://main.gd" id="1"]

[node name="Main" type="Node2D"]
script = ExtResource("1")
'''
        else:
            return '''[gd_scene load_steps=2 format=3]

[ext_resource type="Script" path="res://main.gd" id="1"]

[node name="Main" type="Node3D"]
script = ExtResource("1")
'''

    def write_comment(self, text: str):
        """GDScript-style comments."""
        self.write(f"# {text}")

    # =========================================================================
    # Structure Generation
    # =========================================================================

    def _emit_header(self):
        """Emit file header."""
        self.write_comment("Auto-generated from Rosh IR")
        self.write_comment(f"Emitter: Godot GDScript v{IMPLEMENTS_IR_VERSION}")
        self.write_comment("DO NOT EDIT - Regenerate from .rosh source")
        self.write_blank()

    def _emit_extends_2d(self):
        """Emit extends declaration for 2D arcade mode."""
        self.write("extends Node2D")
        self.write_blank()

    def _emit_extends_3d(self):
        """Emit extends declaration for 3D world mode."""
        self.write("extends Node3D")
        self.write_blank()

    def _emit_variables(self):
        """Emit variable declarations."""
        # Meta object for game state
        if self.has_meta:
            self.write_comment("Meta object for game state")
            self.write("var meta: Dictionary = {}")
            self.write_blank()

        self.write_comment("Object data (position, size, color, visibility)")
        # Skip hidden objects - they exist in world state but are not rendered
        for obj in self.ir.objects:
            if obj.hidden:
                continue
            x = self._get_prop_value(obj, 'x', 0.5)
            y = self._get_prop_value(obj, 'y', 0.5)
            px = int(self.to_target_x(x))
            py = int(self.to_target_y(y))
            color = self._get_color(obj)
            visible = self._get_bool_prop(obj, 'visible', True)

            self.write(f"var {obj.name}_x: float = {px}")
            self.write(f"var {obj.name}_y: float = {py}")
            self.write(f"var {obj.name}_visible: bool = {str(visible).lower()}")
            self.write(f"var {obj.name}_color: Color = Color({color[0]}, {color[1]}, {color[2]})")

            # Text objects get text and font_size
            if obj.name in self.text_objects:
                text = self._get_string_prop(obj, 'text', '')
                font_size = self._get_prop_value(obj, 'font_size', 16)
                self.write(f'var {obj.name}_text: String = "{text}"')
                self.write(f"var {obj.name}_font_size: int = {int(font_size)}")
            else:
                # Shape objects get width/height
                w = self._get_prop_value(obj, 'width', 0.05)
                h = self._get_prop_value(obj, 'height', 0.05)
                pw = int(self.to_target_width(w))
                ph = int(self.to_target_height(h))
                self.write(f"var {obj.name}_w: int = {pw}")
                self.write(f"var {obj.name}_h: int = {ph}")
        self.write_blank()

        self.write_comment("Object properties")
        for obj in self.ir.objects:
            if obj.hidden:
                continue
            skip_props = {'x', 'y', 'width', 'height', 'color', 'sprite', 'text', 'font_size', 'visible'}
            for prop_name, prop_value in obj.properties.items():
                if prop_name not in skip_props:
                    val = self.get_value(prop_value)
                    var_name = f"{obj.name}_{prop_name}"
                    if isinstance(val, str):
                        self.write(f'var {var_name}: String = "{val}"')
                    elif isinstance(val, bool):
                        self.write(f"var {var_name}: bool = {str(val).lower()}")
                    elif isinstance(val, float):
                        self.write(f"var {var_name}: float = {val}")
                    elif isinstance(val, int):
                        self.write(f"var {var_name}: int = {val}")
                    else:
                        self.write(f"var {var_name} = {val}")
        self.write_blank()

        # Font resource for text
        if self.text_objects:
            self.write_comment("Font for text rendering")
            self.write("var _font: Font")
            self.write_blank()

        # Sprite textures
        if self.sprite_assets:
            self.write_comment("Sprite textures")
            for sprite_file in sorted(self.sprite_assets):
                # Create a safe variable name from the sprite file
                var_name = "_tex_" + sprite_file.replace('.', '_').replace('-', '_')
                self.write(f"var {var_name}: Texture2D")
            self.write_blank()

        # REPL Console
        self.write_comment("REPL Console")
        self.write("var _console_visible: bool = false")
        self.write("var _console_layer: CanvasLayer")
        self.write("var _console_input: LineEdit")
        self.write("var _console_output: RichTextLabel")
        self.write("var _console_history: Array = []")
        self.write("var _history_index: int = -1")
        self.write("var _runtime_objects: Dictionary = {}")
        self.write_blank()

    def _emit_ready(self):
        """Emit _ready function."""
        self.write("func _ready():")
        self.indent()

        # Load font for text rendering
        if self.text_objects:
            self.write_comment("Load default font")
            self.write("_font = ThemeDB.fallback_font")
            self.write_blank()

        # Load sprite textures
        if self.sprite_assets:
            self.write_comment("Load sprite textures")
            for sprite_file in sorted(self.sprite_assets):
                var_name = "_tex_" + sprite_file.replace('.', '_').replace('-', '_')
                self.write(f'{var_name} = load("res://{sprite_file}")')
            self.write_blank()

        # Set up REPL console
        self.write_comment("Set up REPL console")
        self.write("_setup_console()")
        self.write_blank()

        # Init actions
        if self.ir.init_actions:
            self.write_comment("Init actions")
            for action in self.ir.init_actions:
                if action:
                    code = self.emit_action(action)
                    if code:
                        self.write(code)

        self.dedent()
        self.write_blank()

    def _emit_draw(self):
        """Emit _draw function to render objects.

        Hidden objects (name starts with '_') are skipped - they exist in IR
        for templates, config, meta, etc. but are not rendered in the game.
        """
        self.write("func _draw():")
        self.indent()
        self.write_comment("Draw all objects")
        for obj in self.ir.objects:
            # Skip hidden objects
            if obj.hidden:
                continue
            self.write(f"if {obj.name}_visible:")
            self.indent()
            if obj.name in self.text_objects:
                # Text object - use draw_string with full width for centering
                canvas_width = self.ir.metadata.canvas_width
                self.write(f"draw_string(_font, Vector2(0, {obj.name}_y), {obj.name}_text, HORIZONTAL_ALIGNMENT_CENTER, {canvas_width}, {obj.name}_font_size, {obj.name}_color)")
            elif obj.name in self.sprite_objects:
                # Sprite object - use draw_texture
                sprite_file = self.sprite_objects[obj.name]
                tex_var = "_tex_" + sprite_file.replace('.', '_').replace('-', '_')
                self.write(f"draw_texture({tex_var}, Vector2({obj.name}_x - {obj.name}_w/2, {obj.name}_y - {obj.name}_h/2))")
            else:
                # Shape object - use draw_rect
                self.write(f"draw_rect(Rect2({obj.name}_x - {obj.name}_w/2, {obj.name}_y - {obj.name}_h/2, {obj.name}_w, {obj.name}_h), {obj.name}_color)")
            self.dedent()
        if not self.ir.objects:
            self.write("pass")
        self.dedent()
        self.write_blank()

    def _emit_process(self):
        """Emit _process function."""
        self.write("func _process(delta):")
        self.indent()

        has_content = False

        # Player auto-movement
        for player_name in self.player_objects:
            has_content = True
            self._emit_player_controls(player_name)

        # Continuous key handlers
        for key, handlers in self.continuous_keys.items():
            has_content = True
            action_name = self._key_to_action(key)
            self.write(f'if Input.is_action_pressed("{action_name}"):')
            self.indent()
            for handler_lines in handlers:
                for line in handler_lines:
                    # Handle multi-line output (e.g., conditionals)
                    for subline in line.split('\n'):
                        self.write(subline)
            self.dedent()

        # Update handlers
        for handler_lines in self.update_handlers:
            has_content = True
            for line in handler_lines:
                # Handle multi-line output (e.g., conditionals)
                for subline in line.split('\n'):
                    self.write(subline)

        if not has_content:
            self.write("pass")

        # Redraw to update visuals
        self.write("queue_redraw()")

        self.dedent()
        self.write_blank()

    def _emit_player_controls(self, player_name: str):
        """Emit automatic player controls."""
        self.write_comment(f"Auto-controls for {player_name}")
        speed = f"{player_name}_speed" if any(
            f"{player_name}_speed" in line for line in self.output
        ) else "5.0"

        self.write(f'if Input.is_action_pressed("ui_left"):')
        self.indent()
        self.write(f"{player_name}_x -= {speed}")
        self.dedent()

        self.write(f'if Input.is_action_pressed("ui_right"):')
        self.indent()
        self.write(f"{player_name}_x += {speed}")
        self.dedent()

        self.write(f'if Input.is_action_pressed("ui_up"):')
        self.indent()
        self.write(f"{player_name}_y -= {speed}")
        self.dedent()

        self.write(f'if Input.is_action_pressed("ui_down"):')
        self.indent()
        self.write(f"{player_name}_y += {speed}")
        self.dedent()

        self.write_blank()

    def _emit_input(self):
        """Emit _input function for keydown events."""
        self.write("func _input(event):")
        self.indent()

        # Mouse look for 3D camera (only when not in arcade mode)
        if not self.arcade_mode:
            self.write_comment("Mouse look for camera (right-click drag)")
            self.write("if event is InputEventMouseMotion and Input.is_mouse_button_pressed(MOUSE_BUTTON_RIGHT):")
            self.indent()
            self.write("_camera_rotation.x -= event.relative.y * _mouse_sensitivity")
            self.write("_camera_rotation.y -= event.relative.x * _mouse_sensitivity")
            self.write("_camera_rotation.x = clamp(_camera_rotation.x, -PI/2, PI/2)")
            self.write("_camera.rotation = Vector3(_camera_rotation.x, _camera_rotation.y, 0)")
            self.write("return")
            self.dedent()
            self.write_blank()

        self.write("if event is InputEventKey and event.pressed:")
        self.indent()

        # Console toggle with backtick
        self.write_comment("Toggle console with backtick")
        self.write("if event.keycode == KEY_QUOTELEFT:")
        self.indent()
        self.write("_toggle_console()")
        self.write("get_viewport().set_input_as_handled()")
        self.write("return")
        self.dedent()

        # Console history navigation
        self.write_comment("Console history with up/down arrows")
        self.write("if _console_visible and _console_history.size() > 0:")
        self.indent()
        self.write("if event.keycode == KEY_UP:")
        self.indent()
        self.write("if _history_index < _console_history.size() - 1:")
        self.indent()
        self.write("_history_index += 1")
        self.dedent()
        self.write("_console_input.text = _console_history[_console_history.size() - 1 - _history_index]")
        self.write("_console_input.caret_column = _console_input.text.length()")
        self.write("get_viewport().set_input_as_handled()")
        self.write("return")
        self.dedent()
        self.write("if event.keycode == KEY_DOWN:")
        self.indent()
        self.write("if _history_index > 0:")
        self.indent()
        self.write("_history_index -= 1")
        self.write("_console_input.text = _console_history[_console_history.size() - 1 - _history_index]")
        self.dedent()
        self.write("else:")
        self.indent()
        self.write("_history_index = -1")
        self.write('_console_input.text = ""')
        self.dedent()
        self.write("_console_input.caret_column = _console_input.text.length()")
        self.write("get_viewport().set_input_as_handled()")
        self.write("return")
        self.dedent()
        self.dedent()

        # User-defined keydown events
        for key, handlers in self.keydown_events.items():
            keycode = self._key_to_keycode(key)
            self.write(f"if event.keycode == {keycode}:")
            self.indent()
            for handler_lines in handlers:
                for line in handler_lines:
                    # Handle multi-line output (e.g., conditionals)
                    for subline in line.split('\n'):
                        self.write(subline)
            self.dedent()

        self.dedent()
        self.dedent()
        self.write_blank()

    def _emit_helper_methods(self):
        """Emit helper methods."""
        self._emit_console_methods()

    def _emit_console_methods(self):
        """Emit REPL console helper methods."""
        # Generate list of object names for the console (use single quotes to avoid escaping)
        obj_names = [obj.name for obj in self.ir.objects]
        obj_list_str = ", ".join(obj_names)

        self.write("func _setup_console():")
        self.indent()
        self.write_comment("Create console UI layer")
        self.write("_console_layer = CanvasLayer.new()")
        self.write("_console_layer.layer = 100")
        self.write("add_child(_console_layer)")
        self.write_blank()

        self.write_comment("Console background")
        self.write("var bg = ColorRect.new()")
        self.write("bg.color = Color(0, 0, 0, 0.8)")
        self.write("bg.set_anchors_preset(Control.PRESET_TOP_WIDE)")
        self.write("bg.size.y = 200")
        self.write("bg.visible = false")
        self.write("bg.name = 'ConsoleBG'")
        self.write("_console_layer.add_child(bg)")
        self.write_blank()

        self.write_comment("Console output")
        self.write("_console_output = RichTextLabel.new()")
        self.write("_console_output.set_anchors_preset(Control.PRESET_TOP_WIDE)")
        self.write("_console_output.position.y = 10")
        self.write("_console_output.size = Vector2(get_viewport().size.x - 20, 140)")
        self.write("_console_output.position.x = 10")
        self.write("_console_output.bbcode_enabled = true")
        self.write(f'_console_output.text = "[color=cyan]Rosh v{__version__} | Godot[/color]\\n"')
        self.write('_console_output.append_text("[color=gray]Type help for commands. Press ` to toggle console.[/color]\\n")')
        self.write("bg.add_child(_console_output)")
        self.write_blank()

        self.write_comment("Console input")
        self.write("_console_input = LineEdit.new()")
        self.write("_console_input.set_anchors_preset(Control.PRESET_TOP_WIDE)")
        self.write("_console_input.position = Vector2(10, 160)")
        self.write("_console_input.size.x = get_viewport().size.x - 20")
        self.write('_console_input.placeholder_text = "Enter Rosh command..."')
        self.write("_console_input.text_submitted.connect(_on_console_submit)")
        self.write("bg.add_child(_console_input)")
        self.dedent()
        self.write_blank()

        self.write("func _toggle_console():")
        self.indent()
        self.write("_console_visible = not _console_visible")
        self.write("var bg = _console_layer.get_node('ConsoleBG')")
        self.write("bg.visible = _console_visible")
        self.write("if _console_visible:")
        self.indent()
        self.write("_console_input.grab_focus()")
        self.dedent()
        self.dedent()
        self.write_blank()

        self.write("func _on_console_submit(text: String):")
        self.indent()
        self.write("if text.strip_edges() == '':")
        self.indent()
        self.write("return")
        self.dedent()
        self.write("_console_history.append(text)")
        self.write("_history_index = -1")
        self.write('_console_output.append_text("[color=yellow]> " + text + "[/color]\\n")')
        self.write("var result = _execute_command(text)")
        self.write('_console_output.append_text(result + "\\n")')
        self.write('_console_input.text = ""')
        self.dedent()
        self.write_blank()

        self.write("func _execute_command(cmd: String) -> String:")
        self.indent()
        self.write("var parts = cmd.strip_edges().split(' ')")
        self.write("if parts.size() == 0:")
        self.indent()
        self.write('return "[color=red]Empty command[/color]"')
        self.dedent()
        self.write_blank()

        self.write_comment("Handle 'set obj prop to value' (space syntax like Phaser)")
        self.write('if parts[0] == "set" and parts.size() >= 5 and parts[3] == "to":')
        self.indent()
        self.write("var obj_name = parts[1]")
        self.write("var prop_name = parts[2]")
        self.write('var value_str = " ".join(parts.slice(4))')
        self.write("return _set_property(obj_name, prop_name, value_str)")
        self.dedent()
        self.write_blank()

        self.write_comment("Handle 'set obj.prop to value' (dot syntax)")
        self.write('if parts[0] == "set" and parts.size() >= 4 and parts[2] == "to":')
        self.indent()
        self.write("var target_prop = parts[1].split('.')")
        self.write("if target_prop.size() == 2:")
        self.indent()
        self.write("return _set_property(target_prop[0], target_prop[1], \" \".join(parts.slice(3)))")
        self.dedent()
        self.dedent()
        self.write_blank()

        self.write_comment("Handle 'list' command (aliases: ls, objects)")
        self.write('if parts[0] == "list" or parts[0] == "ls" or parts[0] == "objects":')
        self.indent()
        self.write(f'var all_objs = "{obj_list_str}"')
        self.write("if _runtime_objects.size() > 0:")
        self.indent()
        self.write('all_objs += ", " + ", ".join(_runtime_objects.keys())')
        self.dedent()
        self.write('return "[color=green]Objects: " + all_objs + "[/color]"')
        self.dedent()
        self.write_blank()

        self.write_comment("Handle 'look' command (aliases: l, examine, x)")
        self.write('if parts[0] == "look" or parts[0] == "l" or parts[0] == "examine" or parts[0] == "x":')
        self.indent()
        self.write('if parts.size() < 2:')
        self.indent()
        self.write('return "[color=red]Usage: look <object>[/color]"')
        self.dedent()
        self.write("return _look_object(parts[1])")
        self.dedent()
        self.write_blank()

        self.write_comment("Handle 'hide' command")
        self.write('if parts[0] == "hide":')
        self.indent()
        self.write('if parts.size() < 2:')
        self.indent()
        self.write('return "[color=red]Usage: hide <object>[/color]"')
        self.dedent()
        self.write("return _set_property(parts[1], \"visible\", \"false\")")
        self.dedent()
        self.write_blank()

        self.write_comment("Handle 'show' command (alias: unhide)")
        self.write('if parts[0] == "show" or parts[0] == "unhide":')
        self.indent()
        self.write('if parts.size() < 2:')
        self.indent()
        self.write('return "[color=red]Usage: show <object>[/color]"')
        self.dedent()
        self.write("return _set_property(parts[1], \"visible\", \"true\")")
        self.dedent()
        self.write_blank()

        self.write_comment("Handle 'create' command")
        self.write('if parts[0] == "create":')
        self.indent()
        self.write('if parts.size() < 2:')
        self.indent()
        self.write('return "[color=red]Usage: create <name> [at <x> <y>][/color]"')
        self.dedent()
        self.write("return _create_object(parts)")
        self.dedent()
        self.write_blank()

        self.write_comment("Handle 'delete' command (aliases: destroy, remove, rm)")
        self.write('if parts[0] == "delete" or parts[0] == "destroy" or parts[0] == "remove" or parts[0] == "rm":')
        self.indent()
        self.write('if parts.size() < 2: return "[color=red]Usage: delete <object>[/color]"')
        self.write("return _delete_object(parts[1])")
        self.dedent()
        self.write_blank()

        self.write_comment("Handle 'move' command")
        self.write('if parts[0] == "move":')
        self.indent()
        self.write('if parts.size() < 5 or parts[2] != "to": return "[color=red]Usage: move <obj> to <x> <y>[/color]"')
        self.write("var result = _set_property(parts[1], \"x\", parts[3])")
        self.write("_set_property(parts[1], \"y\", parts[4])")
        self.write('return "[color=green]Moved " + parts[1] + "[/color]"')
        self.dedent()
        self.write_blank()

        self.write_comment("Handle 'clear' command (alias: cls)")
        self.write('if parts[0] == "clear" or parts[0] == "cls":')
        self.indent()
        self.write(f'_console_output.text = "[color=cyan]Rosh v{__version__} | Godot[/color]\\n"')
        self.write('return ""')
        self.dedent()
        self.write_blank()

        self.write_comment("Handle 'help' command (alias: ?)")
        self.write('if parts[0] == "help" or parts[0] == "?":')
        self.indent()
        self.write('return "[color=cyan]Commands:\\n  set obj prop to value\\n  look/examine obj\\n  hide/show obj\\n  create [color] [size] name [at x y]\\n  delete/rm obj\\n  move obj to x y\\n  list - show objects\\n  clear - clear console\\n  help - this help[/color]"')
        self.dedent()
        self.write_blank()

        self.write('return "[color=red]Unknown command: " + parts[0] + "[/color]"')
        self.dedent()
        self.write_blank()

        # Generate _set_property function with all object properties
        self.write("func _set_property(obj_name: String, prop_name: String, value_str: String) -> String:")
        self.indent()
        self.write("var val = value_str")
        self.write_comment("Try to convert to number")
        self.write("if val.is_valid_float():")
        self.indent()
        self.write("val = float(val)")
        self.dedent()
        self.write('elif val == "true":\n        val = true')
        self.write('elif val == "false":\n        val = false')
        self.write_blank()

        # Generate property setters for each object
        for obj in self.ir.objects:
            self.write(f'if obj_name == "{obj.name}":')
            self.indent()
            self.write(f'if prop_name == "x": {obj.name}_x = val')
            self.write(f'elif prop_name == "y": {obj.name}_y = val')
            self.write(f'elif prop_name == "visible": {obj.name}_visible = val')
            self.write(f'elif prop_name == "color": {obj.name}_color = _parse_color(value_str)')
            if obj.name in self.text_objects:
                self.write(f'elif prop_name == "font_size": {obj.name}_font_size = int(val)')
                self.write(f'elif prop_name == "text": {obj.name}_text = value_str')
            self.write(f'else: return "[color=red]Unknown property: " + prop_name + "[/color]"')
            self.write(f'return "[color=green]Set {obj.name}." + prop_name + " = " + str(val) + "[/color]"')
            self.dedent()

        # Handle runtime objects (created via console)
        self.write_comment("Handle runtime objects")
        self.write("if _runtime_objects.has(obj_name):")
        self.indent()
        self.write("var obj = _runtime_objects[obj_name]")
        self.write('if prop_name == "x": obj.position.x = float(val)')
        self.write('elif prop_name == "y": obj.position.y = float(val)')
        self.write('elif prop_name == "visible": obj.visible = val')
        self.write('elif prop_name == "color": obj.color = _parse_color(value_str)')
        self.write('else: return "[color=red]Unknown property: " + prop_name + "[/color]"')
        self.write('return "[color=green]Set " + obj_name + "." + prop_name + " = " + str(val) + "[/color]"')
        self.dedent()

        self.write('return "[color=red]Unknown object: " + obj_name + "[/color]"')
        self.dedent()
        self.write_blank()

        # Color parsing helper
        self.write("func _parse_color(color_str: String) -> Color:")
        self.indent()
        self.write("var colors = {")
        self.indent()
        self.write('"red": Color.RED, "green": Color.GREEN, "blue": Color.BLUE,')
        self.write('"yellow": Color.YELLOW, "cyan": Color.CYAN, "magenta": Color.MAGENTA,')
        self.write('"white": Color.WHITE, "black": Color.BLACK, "orange": Color.ORANGE,')
        self.write('"purple": Color(0.5, 0, 1), "gray": Color.GRAY, "grey": Color.GRAY')
        self.dedent()
        self.write("}")
        self.write("if color_str.to_lower() in colors:")
        self.indent()
        self.write("return colors[color_str.to_lower()]")
        self.dedent()
        self.write("if color_str.begins_with('#'):")
        self.indent()
        self.write("return Color.html(color_str)")
        self.dedent()
        self.write("return Color.WHITE")
        self.dedent()
        self.write_blank()

        # Look object helper
        self.write("func _look_object(obj_name: String) -> String:")
        self.indent()
        for obj in self.ir.objects:
            self.write(f'if obj_name == "{obj.name}":')
            self.indent()
            if obj.name in self.text_objects:
                self.write(f'return "[color=green]{obj.name}: x=" + str(int({obj.name}_x)) + ", y=" + str(int({obj.name}_y)) + ", visible=" + str({obj.name}_visible) + ", text=\\"" + {obj.name}_text + "\\"[/color]"')
            else:
                self.write(f'return "[color=green]{obj.name}: x=" + str(int({obj.name}_x)) + ", y=" + str(int({obj.name}_y)) + ", visible=" + str({obj.name}_visible) + "[/color]"')
            self.dedent()
        self.write_comment("Check runtime objects")
        self.write("if _runtime_objects.has(obj_name):")
        self.indent()
        self.write("var obj = _runtime_objects[obj_name]")
        self.write('return "[color=green]" + obj_name + ": x=" + str(int(obj.x)) + ", y=" + str(int(obj.y)) + "[/color]"')
        self.dedent()
        self.write('return "[color=red]Object not found: " + obj_name + "[/color]"')
        self.dedent()
        self.write_blank()

        # Create object helper - parses modifiers per rosh-console.toml spec
        self.write("func _create_object(parts: Array) -> String:")
        self.indent()
        self.write_comment("Parse modifiers: 'create blue box' → name='box', color=blue")
        self.write("var colors = {")
        self.indent()
        self.write('"red": Color.RED, "green": Color.GREEN, "blue": Color.BLUE,')
        self.write('"yellow": Color.YELLOW, "cyan": Color.CYAN, "magenta": Color.MAGENTA,')
        self.write('"white": Color.WHITE, "black": Color.BLACK, "orange": Color.ORANGE,')
        self.write('"purple": Color(0.5, 0, 1), "pink": Color(1, 0.5, 1),')
        self.write('"gray": Color.GRAY, "grey": Color.GRAY')
        self.dedent()
        self.write("}")
        self.write('var size_mods = ["big", "large", "small", "tiny"]')
        self.write('var articles = ["a", "an", "the"]')
        self.write_blank()
        self.write("var x = get_viewport().size.x / 2")
        self.write("var y = get_viewport().size.y / 2")
        self.write("var obj_color = Color.GREEN")
        self.write("var obj_size = 50")
        self.write_blank()
        self.write_comment("Find 'at x y' position")
        self.write("var at_idx = -1")
        self.write("for i in range(parts.size()):")
        self.indent()
        self.write('if parts[i] == "at": at_idx = i; break')
        self.dedent()
        self.write("if at_idx > 0 and parts.size() >= at_idx + 3:")
        self.indent()
        self.write("x = float(parts[at_idx + 1])")
        self.write("y = float(parts[at_idx + 2])")
        self.dedent()
        self.write_blank()
        self.write_comment("Parse words before 'at' (or all if no 'at')")
        self.write("var desc_parts = parts.slice(1, at_idx if at_idx > 0 else parts.size())")
        self.write("var obj_name = 'object'")
        self.write_blank()
        self.write_comment("Find the name - last word that isn't a color, size, or article")
        self.write("for i in range(desc_parts.size() - 1, -1, -1):")
        self.indent()
        self.write("var word = desc_parts[i].to_lower()")
        self.write("if not colors.has(word) and not (word in size_mods) and not (word in articles):")
        self.indent()
        self.write("obj_name = word")
        self.write("break")
        self.dedent()
        self.dedent()
        self.write_blank()
        self.write_comment("Apply modifiers")
        self.write("for word in desc_parts:")
        self.indent()
        self.write("var w = word.to_lower()")
        self.write("if colors.has(w): obj_color = colors[w]")
        self.write('if w == "big" or w == "large": obj_size = 80')
        self.write('if w == "small" or w == "tiny": obj_size = 25')
        self.dedent()
        self.write_blank()
        self.write_comment("Auto-number if name exists")
        self.write("var final_name = obj_name")
        self.write("var counter = 2")
        self.write("while _runtime_objects.has(final_name):")
        self.indent()
        self.write("final_name = obj_name + str(counter)")
        self.write("counter += 1")
        self.dedent()
        self.write_blank()
        self.write_comment("Create colored rectangle")
        self.write("var rect = ColorRect.new()")
        self.write("rect.color = obj_color")
        self.write("rect.size = Vector2(obj_size, obj_size)")
        self.write("rect.position = Vector2(x - obj_size/2, y - obj_size/2)")
        self.write("add_child(rect)")
        self.write("_runtime_objects[final_name] = rect")
        self.write('return "[color=green]Created " + final_name + " at (" + str(int(x)) + ", " + str(int(y)) + ")[/color]"')
        self.dedent()
        self.write_blank()

        # Delete object helper for 2D
        self.write("func _delete_object(obj_name: String) -> String:")
        self.indent()
        self.write("if _runtime_objects.has(obj_name):")
        self.indent()
        self.write("var obj = _runtime_objects[obj_name]")
        self.write("obj.queue_free()")
        self.write("_runtime_objects.erase(obj_name)")
        self.write('return "[color=green]Deleted " + obj_name + "[/color]"')
        self.dedent()
        self.write('return "[color=red]Object not found: " + obj_name + "[/color]"')
        self.dedent()
        self.write_blank()

    def _emit_functions(self):
        """Emit user-defined functions."""
        for func in self.ir.functions:
            self._emit_function(func)

    def _emit_function(self, func: IR_Function):
        """Emit a user-defined function."""
        params = ", ".join(func.params) if func.params else ""
        self.write(f"func {func.name}({params}):")
        self.indent()

        if func.body:
            for action in func.body:
                if action:
                    code = self.emit_action(action)
                    if code:
                        # Handle multi-line output (e.g., conditionals)
                        for subline in code.split('\n'):
                            self.write(subline)
        else:
            self.write("pass")

        self.dedent()
        self.write_blank()

    # =========================================================================
    # Abstract Method Implementations
    # =========================================================================

    def emit_object(self, obj: IR_Object) -> str:
        """Generate code for an object definition."""
        # Object creation is handled in _emit_create_object
        return ""

    def emit_event(self, event: IR_Event) -> str:
        """Generate code for an event handler."""
        # Events are handled in _emit_process and _emit_input
        return ""

    def emit_action(self, action) -> str:
        """Generate code for an action."""
        if isinstance(action, IR_Action):
            return self._emit_ir_action(action)
        elif isinstance(action, IR_Conditional):
            return self._emit_conditional(action)
        elif isinstance(action, IR_Loop):
            return self._emit_loop(action)
        return ""

    def _emit_ir_action(self, action: IR_Action) -> str:
        """Emit code for an IR_Action."""
        if action.type == 'set_property':
            return self._emit_set_property(action)
        elif action.type == 'print':
            msg = action.params.get('message')
            if msg:
                expr = self.emit_expression(msg)
                return f"print({expr})"
            return "print()"
        elif action.type == 'spawn':
            return self._emit_spawn(action)
        elif action.type == 'destroy':
            target = action.params.get('target', '')
            return f"{target}.queue_free()"
        elif action.type == 'play_sound':
            # TODO: Implement sound
            return f"# play_sound: {action.params.get('asset', '')}"
        elif action.type == 'call_function':
            func_name = action.params.get('name', '')
            args = action.params.get('arguments', [])
            args_str = ", ".join(str(self._emit_value(a)) for a in args)
            return f"{func_name}({args_str})"
        elif action.type == 'call':
            # IR uses 'call' with 'function' and 'args' params
            func_name = action.params.get('function', '')
            args = action.params.get('args', [])
            args_str = ", ".join(str(self._emit_value(a)) for a in args)
            return f"{func_name}({args_str})"
        return ""

    def _emit_set_property(self, action: IR_Action) -> str:
        """Emit set_property action."""
        target = action.params.get('target', '')
        prop = action.params.get('property', '')
        value = action.params.get('value')

        val_str = self._emit_value(value)

        # Meta object uses dictionary access
        if target == 'meta':
            return f'meta["{prop}"] = {val_str}'

        # Color needs special handling
        if prop == 'color':
            if isinstance(value, IR_Value) and value.type == 'color':
                color = self._hex_to_color(value.value)
                return f"{target}_color = Color({color[0]}, {color[1]}, {color[2]})"
            return f"{target}_color = {val_str}"

        # All properties use flat variable names
        return f"{target}_{prop} = {val_str}"

    def _emit_spawn(self, action: IR_Action) -> str:
        """Emit spawn action."""
        template = action.params.get('template', '')
        name = action.params.get('name', f'{template}_copy')
        return f"var {name} = {template}.duplicate(); add_child({name})"

    def _emit_value(self, value) -> str:
        """Convert an IR value to GDScript."""
        if isinstance(value, IR_Value):
            if value.type == 'string':
                return f'"{value.value}"'
            elif value.type == 'boolean':
                return str(value.value).lower()
            elif value.type == 'percentage':
                # Denormalize based on context (assume x for now)
                return str(self.to_target_x(value.value))
            elif value.type == 'color':
                color = self._hex_to_color(value.value)
                return f"Color({color[0]}, {color[1]}, {color[2]})"
            elif value.type == 'expression':
                # IR_Value wrapping an expression - emit the expression
                return self.emit_expression(value.value)
            else:
                return str(value.value)
        elif isinstance(value, IR_Expression):
            return self.emit_expression(value)
        else:
            return str(value)

    def _emit_conditional(self, cond: IR_Conditional) -> str:
        """Emit conditional statement."""
        lines = []
        lines.append(f"if {self.emit_expression(cond.condition)}:")

        has_then = False
        for action in cond.then_actions:
            if action:
                code = self.emit_action(action)
                if code:
                    # Handle nested conditionals - split by newlines and indent each
                    for subline in code.split('\n'):
                        lines.append(f"    {subline}")
                    has_then = True
        if not has_then:
            lines.append("    pass")

        if cond.else_actions:
            lines.append("else:")
            has_else = False
            for action in cond.else_actions:
                if action:
                    code = self.emit_action(action)
                    if code:
                        for subline in code.split('\n'):
                            lines.append(f"    {subline}")
                        has_else = True
            if not has_else:
                lines.append("    pass")

        return "\n".join(lines)

    def _emit_loop(self, loop: IR_Loop) -> str:
        """Emit loop statement."""
        lines = []

        if loop.type == 'while':
            lines.append(f"while {self.emit_expression(loop.condition)}:")
        elif loop.type == 'for':
            start = self.emit_expression(loop.start)
            end = self.emit_expression(loop.end)
            lines.append(f"for {loop.iterator} in range({start}, {end} + 1):")
        elif loop.type == 'for_each':
            iterable = self.emit_expression(loop.iterable)
            lines.append(f"for {loop.iterator} in {iterable}:")

        for action in loop.body:
            if action:
                code = self.emit_action(action)
                if code:
                    lines.append(f"\t{code}")
        if not loop.body:
            lines.append("\tpass")

        return "\n".join(lines)

    def emit_expression(self, expr) -> str:
        """Generate code for an expression."""
        if isinstance(expr, IR_Expression):
            if expr.type == 'literal':
                return self._emit_value(expr.value)
            elif expr.type == 'property_access':
                obj = expr.left
                prop = expr.right
                # Meta object uses dictionary access
                if obj == 'meta':
                    return f'meta["{prop}"]'
                # All other objects use flat variables
                return f"{obj}_{prop}"
            elif expr.type == 'comparison':
                left = self.emit_expression(expr.left)
                right = self.emit_expression(expr.right)
                op = self._map_operator(expr.operator)
                return f"{left} {op} {right}"
            elif expr.type == 'binary_op':
                left = self.emit_expression(expr.left)
                right = self.emit_expression(expr.right)
                op = self._map_operator(expr.operator)
                return f"{left} {op} {right}"
            elif expr.type == 'unary_op':
                # Unary operand is stored in expr.right (not expr.left)
                operand = self.emit_expression(expr.right)
                op = self._map_operator(expr.operator)
                return f"{op}{operand}"
        elif isinstance(expr, IR_Value):
            return self._emit_value(expr)
        elif isinstance(expr, str):
            return expr
        elif isinstance(expr, (int, float)):
            return str(expr)

        return str(expr)

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _get_prop_value(self, obj: IR_Object, prop: str, default: float) -> float:
        """Get a property value from an object."""
        if prop in obj.properties:
            val = obj.properties[prop]
            if val.type == 'percentage':
                return val.value
            # Handle case where value is an expression (can't evaluate statically)
            if hasattr(val.value, 'type'):  # It's an IR_Expression
                return default
            try:
                return float(val.value)
            except (TypeError, ValueError):
                return default
        return default

    def _get_bool_prop(self, obj: IR_Object, prop: str, default: bool) -> bool:
        """Get a boolean property value from an object."""
        if prop in obj.properties:
            val = obj.properties[prop]
            if val.type == 'boolean':
                return val.value
            return bool(val.value)
        return default

    def _get_string_prop(self, obj: IR_Object, prop: str, default: str) -> str:
        """Get a string property value from an object."""
        if prop in obj.properties:
            val = obj.properties[prop]
            return str(val.value)
        return default

    def _get_color(self, obj: IR_Object) -> tuple:
        """Get color for an object as RGB tuple (0-1 range)."""
        if 'color' in obj.properties:
            color_val = obj.properties['color'].value
            # Handle both int and string color values
            if isinstance(color_val, int):
                return self._hex_to_color(color_val)
            elif isinstance(color_val, str):
                # Try to parse as hex string
                if color_val.startswith('0x') or color_val.startswith('#'):
                    hex_str = color_val.lstrip('#').lstrip('0x')
                    return self._hex_to_color(int(hex_str, 16))
                # Named colors
                named_colors = {
                    'red': (1.0, 0.0, 0.0),
                    'green': (0.0, 1.0, 0.0),
                    'blue': (0.0, 0.0, 1.0),
                    'yellow': (1.0, 1.0, 0.0),
                    'magenta': (1.0, 0.0, 1.0),
                    'cyan': (0.0, 1.0, 1.0),
                    'white': (1.0, 1.0, 1.0),
                    'black': (0.0, 0.0, 0.0),
                    'orange': (1.0, 0.5, 0.0),
                    'purple': (0.5, 0.0, 1.0),
                }
                return named_colors.get(color_val.lower(), (1.0, 1.0, 1.0))
            return (1.0, 1.0, 1.0)  # Default white
        else:
            color = self.DEFAULT_COLORS[self.color_index % len(self.DEFAULT_COLORS)]
            self.color_index += 1
            return color

    def _hex_to_color(self, hex_val: int) -> tuple:
        """Convert hex color to RGB tuple (0-1 range)."""
        r = ((hex_val >> 16) & 0xFF) / 255.0
        g = ((hex_val >> 8) & 0xFF) / 255.0
        b = (hex_val & 0xFF) / 255.0
        return (round(r, 3), round(g, 3), round(b, 3))

    def _key_to_action(self, key: str) -> str:
        """Map Rosh key name to Godot input action."""
        key_map = {
            'left': 'ui_left',
            'right': 'ui_right',
            'up': 'ui_up',
            'down': 'ui_down',
            'space': 'ui_accept',
            'enter': 'ui_accept',
            'escape': 'ui_cancel',
        }
        return key_map.get(key.lower(), f"ui_{key.lower()}")

    def _key_to_keycode(self, key: str) -> str:
        """Map Rosh key name to Godot keycode."""
        key_map = {
            'space': 'KEY_SPACE',
            'enter': 'KEY_ENTER',
            'escape': 'KEY_ESCAPE',
            'left': 'KEY_LEFT',
            'right': 'KEY_RIGHT',
            'up': 'KEY_UP',
            'down': 'KEY_DOWN',
            'a': 'KEY_A', 'b': 'KEY_B', 'c': 'KEY_C', 'd': 'KEY_D',
            'e': 'KEY_E', 'f': 'KEY_F', 'g': 'KEY_G', 'h': 'KEY_H',
            'i': 'KEY_I', 'j': 'KEY_J', 'k': 'KEY_K', 'l': 'KEY_L',
            'm': 'KEY_M', 'n': 'KEY_N', 'o': 'KEY_O', 'p': 'KEY_P',
            'q': 'KEY_Q', 'r': 'KEY_R', 's': 'KEY_S', 't': 'KEY_T',
            'u': 'KEY_U', 'v': 'KEY_V', 'w': 'KEY_W', 'x': 'KEY_X',
            'y': 'KEY_Y', 'z': 'KEY_Z',
        }
        return key_map.get(key.lower(), f'KEY_{key.upper()}')

    def _map_operator(self, op: str) -> str:
        """Map IR operator to GDScript operator."""
        op_map = {
            'is': '==',
            'is_not': '!=',
            'equals': '==',
            'above': '>',
            'below': '<',
            'at_least': '>=',
            'at_most': '<=',
            'plus': '+',
            'minus': '-',
            'times': '*',
            'divided_by': '/',
            'and': 'and',
            'or': 'or',
            'not': 'not ',
        }
        return op_map.get(op, op)

    # =========================================================================
    # 3D World Mode Methods
    # =========================================================================

    def _emit_variables_3d(self):
        """Emit variable declarations for 3D mode."""
        # Meta object for game state
        if self.has_meta:
            self.write_comment("Meta object for game state")
            self.write("var meta: Dictionary = {}")
            self.write_blank()

        self.write_comment("3D Objects (Node3D references)")
        for obj in self.ir.objects:
            self.write(f"var {obj.name}: Node3D")
        self.write_blank()

        self.write_comment("Object properties")
        for obj in self.ir.objects:
            visible = self._get_bool_prop(obj, 'visible', True)
            self.write(f"var {obj.name}_visible: bool = {str(visible).lower()}")
            if obj.name in self.text_objects:
                text = self._get_string_prop(obj, 'text', '')
                font_size = self._get_prop_value(obj, 'font_size', 16)
                self.write(f'var {obj.name}_text: String = "{text}"')
                self.write(f"var {obj.name}_font_size: float = {font_size}")
            # Additional properties
            skip_props = {'x', 'y', 'z', 'width', 'height', 'color', 'sprite', 'text', 'font_size', 'visible'}
            for prop_name, prop_value in obj.properties.items():
                if prop_name not in skip_props:
                    val = self.get_value(prop_value)
                    var_name = f"{obj.name}_{prop_name}"
                    if isinstance(val, str):
                        self.write(f'var {var_name}: String = "{val}"')
                    elif isinstance(val, bool):
                        self.write(f"var {var_name}: bool = {str(val).lower()}")
                    elif isinstance(val, float):
                        self.write(f"var {var_name}: float = {val}")
                    elif isinstance(val, int):
                        self.write(f"var {var_name}: int = {val}")
        self.write_blank()

        # Camera and lighting
        self.write_comment("3D Scene components")
        self.write("var _camera: Camera3D")
        self.write("var _light: DirectionalLight3D")
        self.write("var _camera_speed: float = 5.0")
        self.write("var _mouse_sensitivity: float = 0.003")
        self.write("var _camera_rotation: Vector2 = Vector2.ZERO")
        self.write_blank()

        # REPL Console (same as 2D)
        self.write_comment("REPL Console")
        self.write("var _console_visible: bool = false")
        self.write("var _console_layer: CanvasLayer")
        self.write("var _console_input: LineEdit")
        self.write("var _console_output: RichTextLabel")
        self.write("var _console_history: Array = []")
        self.write("var _history_index: int = -1")
        self.write("var _runtime_objects: Dictionary = {}")
        self.write("var _undo_stack: Array = []")
        self.write("var _redo_stack: Array = []")
        self.write_blank()

    def _emit_ready_3d(self):
        """Emit _ready function for 3D mode."""
        self.write("func _ready():")
        self.indent()

        # Create camera
        self.write_comment("Create camera")
        self.write("_camera = Camera3D.new()")
        self.write("_camera.position = Vector3(0, 5, 10)")
        self.write("add_child(_camera)")
        self.write("_camera.look_at(Vector3.ZERO)")
        self.write_blank()

        # Create directional light
        self.write_comment("Create lighting")
        self.write("_light = DirectionalLight3D.new()")
        self.write("_light.position = Vector3(5, 10, 5)")
        self.write("add_child(_light)")
        self.write("_light.look_at(Vector3.ZERO)")
        self.write_blank()

        # Create floor/ground
        self.write_comment("Create ground plane")
        self.write("var floor_mesh = MeshInstance3D.new()")
        self.write("var plane = PlaneMesh.new()")
        self.write("plane.size = Vector2(20, 20)")
        self.write("floor_mesh.mesh = plane")
        self.write("var floor_mat = StandardMaterial3D.new()")
        self.write("floor_mat.albedo_color = Color(0.2, 0.2, 0.25)")
        self.write("floor_mesh.material_override = floor_mat")
        self.write("add_child(floor_mesh)")
        self.write_blank()

        # Create objects
        for obj in self.ir.objects:
            self._emit_create_object_3d(obj)

        # Set up REPL console
        self.write_comment("Set up REPL console")
        self.write("_setup_console()")
        self.write_blank()

        # Init actions
        if self.ir.init_actions:
            self.write_comment("Init actions")
            for action in self.ir.init_actions:
                if action:
                    code = self.emit_action(action)
                    if code:
                        for line in code.split('\n'):
                            self.write(line)
        self.write_blank()

        self.dedent()
        self.write_blank()

    def _emit_create_object_3d(self, obj: IR_Object):
        """Create a 3D object (box mesh or text label).

        Hidden objects (name starts with '_') are skipped - they exist in IR
        for templates, config, meta, etc. but are not rendered in the game.
        """
        # Skip hidden objects - they exist in world state but are not rendered
        if obj.hidden:
            return

        x = self._get_prop_value(obj, 'x', 0.5)
        y = self._get_prop_value(obj, 'y', 0.5)
        z = self._get_prop_value(obj, 'z', 0.0)
        color = self._get_color(obj)

        # Convert normalized coords to 3D space
        # X: horizontal (-10 to 10)
        # Y: vertical height (0.5 - y) * 5 so top of screen is higher
        # Z: depth (near camera = positive)
        px = (x - 0.5) * 10
        py = (0.5 - y) * 5 + 1  # Invert Y, scale, raise above ground
        pz = z if z != 0 else 0  # Depth defaults to center

        if obj.name in self.text_objects:
            # Create 3D text using Label3D
            text = self._get_string_prop(obj, 'text', obj.name)
            font_size = self._get_prop_value(obj, 'font_size', 16)
            self.write_comment(f"Create 3D text: {obj.name}")
            self.write(f"{obj.name} = MeshInstance3D.new()")
            self.write(f"var {obj.name}_label = Label3D.new()")
            self.write(f'{obj.name}_label.text = "{text}"')
            self.write(f"{obj.name}_label.font_size = {int(font_size)}")
            self.write(f"{obj.name}_label.modulate = Color({color[0]}, {color[1]}, {color[2]})")
            self.write(f"{obj.name}_label.position = Vector3({px}, {py}, {pz})")
            self.write(f"{obj.name}_label.billboard = BaseMaterial3D.BILLBOARD_ENABLED")
            self.write(f"add_child({obj.name}_label)")
            self.write(f"{obj.name} = {obj.name}_label")  # Reference for property access
        else:
            # Create 3D box
            w = self._get_prop_value(obj, 'width', 0.05)
            h = self._get_prop_value(obj, 'height', 0.05)
            bw = w * 20  # Scale to 3D space
            bh = h * 20
            self.write_comment(f"Create 3D box: {obj.name}")
            self.write(f"{obj.name} = MeshInstance3D.new()")
            self.write(f"var {obj.name}_mesh = BoxMesh.new()")
            self.write(f"{obj.name}_mesh.size = Vector3({bw}, {bh}, {bh})")
            self.write(f"{obj.name}.mesh = {obj.name}_mesh")
            self.write(f"var {obj.name}_mat = StandardMaterial3D.new()")
            self.write(f"{obj.name}_mat.albedo_color = Color({color[0]}, {color[1]}, {color[2]})")
            self.write(f"{obj.name}.material_override = {obj.name}_mat")
            self.write(f"{obj.name}.position = Vector3({px}, {py}, {pz})")
            self.write(f"add_child({obj.name})")

        visible = self._get_bool_prop(obj, 'visible', True)
        if not visible:
            self.write(f"{obj.name}.visible = false")
        self.write_blank()

    def _emit_process_3d(self):
        """Emit _process function for 3D mode."""
        self.write("func _process(delta):")
        self.indent()

        has_content = True  # Always has camera controls

        # WASD camera controls
        self.write_comment("WASD Camera movement (when console not open)")
        self.write("if not _console_visible:")
        self.indent()
        self.write("var move_dir = Vector3.ZERO")
        self.write('if Input.is_action_pressed("ui_up") or Input.is_key_pressed(KEY_W):')
        self.indent()
        self.write("move_dir -= _camera.global_transform.basis.z")
        self.dedent()
        self.write('if Input.is_action_pressed("ui_down") or Input.is_key_pressed(KEY_S):')
        self.indent()
        self.write("move_dir += _camera.global_transform.basis.z")
        self.dedent()
        self.write('if Input.is_action_pressed("ui_left") or Input.is_key_pressed(KEY_A):')
        self.indent()
        self.write("move_dir -= _camera.global_transform.basis.x")
        self.dedent()
        self.write('if Input.is_action_pressed("ui_right") or Input.is_key_pressed(KEY_D):')
        self.indent()
        self.write("move_dir += _camera.global_transform.basis.x")
        self.dedent()
        self.write("if Input.is_key_pressed(KEY_Q):")
        self.indent()
        self.write("move_dir.y -= 1")
        self.dedent()
        self.write("if Input.is_key_pressed(KEY_E):")
        self.indent()
        self.write("move_dir.y += 1")
        self.dedent()
        self.write("if move_dir.length() > 0:")
        self.indent()
        self.write("_camera.position += move_dir.normalized() * _camera_speed * delta")
        self.dedent()
        self.dedent()
        self.write_blank()

        # Process update events
        for event in self.ir.events:
            if event.trigger == 'update':
                for action in event.handler:
                    if action:
                        code = self.emit_action(action)
                        if code:
                            # Handle multi-line code (conditionals)
                            for subline in code.split('\n'):
                                self.write(subline)

        # Sync visibility for text objects (font_size update)
        for obj in self.ir.objects:
            if obj.name in self.text_objects:
                has_content = True
                self.write_comment(f"Sync {obj.name} properties")
                self.write(f"if {obj.name}:")
                self.indent()
                self.write(f"{obj.name}.visible = {obj.name}_visible")
                self.write(f"if {obj.name} is Label3D:")
                self.indent()
                self.write(f"{obj.name}.font_size = int({obj.name}_font_size)")
                self.write(f"{obj.name}.text = {obj.name}_text")
                self.dedent()
                self.dedent()

        if not has_content:
            self.write("pass")

        self.dedent()
        self.write_blank()

    def _emit_helper_methods_3d(self):
        """Emit helper methods for 3D mode."""
        self._emit_console_methods_3d()

    def _emit_console_methods_3d(self):
        """Emit REPL console helper methods for 3D mode."""
        obj_names = [obj.name for obj in self.ir.objects]
        obj_list_str = ", ".join(obj_names)

        # Reuse most of the 2D console setup
        self.write("func _setup_console():")
        self.indent()
        self.write_comment("Create console UI layer")
        self.write("_console_layer = CanvasLayer.new()")
        self.write("_console_layer.layer = 100")
        self.write("add_child(_console_layer)")
        self.write_blank()

        self.write_comment("Console background")
        self.write("var bg = ColorRect.new()")
        self.write("bg.color = Color(0, 0, 0, 0.8)")
        self.write("bg.set_anchors_preset(Control.PRESET_TOP_WIDE)")
        self.write("bg.size.y = 200")
        self.write("bg.visible = false")
        self.write("bg.name = 'ConsoleBG'")
        self.write("_console_layer.add_child(bg)")
        self.write_blank()

        self.write_comment("Console output")
        self.write("_console_output = RichTextLabel.new()")
        self.write("_console_output.set_anchors_preset(Control.PRESET_TOP_WIDE)")
        self.write("_console_output.position.y = 10")
        self.write("_console_output.size = Vector2(get_viewport().size.x - 20, 140)")
        self.write("_console_output.position.x = 10")
        self.write("_console_output.bbcode_enabled = true")
        self.write(f'_console_output.text = "[color=cyan]Rosh v{__version__} | Godot 3D[/color]\\n"')
        self.write('_console_output.append_text("[color=gray]Type help for commands. Press ` to toggle console.[/color]\\n")')
        self.write("bg.add_child(_console_output)")
        self.write_blank()

        self.write_comment("Console input")
        self.write("_console_input = LineEdit.new()")
        self.write("_console_input.set_anchors_preset(Control.PRESET_TOP_WIDE)")
        self.write("_console_input.position = Vector2(10, 160)")
        self.write("_console_input.size.x = get_viewport().size.x - 20")
        self.write('_console_input.placeholder_text = "Enter Rosh command..."')
        self.write("_console_input.text_submitted.connect(_on_console_submit)")
        self.write("bg.add_child(_console_input)")
        self.dedent()
        self.write_blank()

        self.write("func _toggle_console():")
        self.indent()
        self.write("_console_visible = not _console_visible")
        self.write("var bg = _console_layer.get_node('ConsoleBG')")
        self.write("bg.visible = _console_visible")
        self.write("if _console_visible:")
        self.indent()
        self.write("_console_input.grab_focus()")
        self.dedent()
        self.dedent()
        self.write_blank()

        self.write("func _on_console_submit(text: String):")
        self.indent()
        self.write("if text.strip_edges() == '':")
        self.indent()
        self.write("return")
        self.dedent()
        self.write("_console_history.append(text)")
        self.write("_history_index = -1")
        self.write('_console_output.append_text("[color=yellow]> " + text + "[/color]\\n")')
        self.write("var result = _execute_command(text)")
        self.write('_console_output.append_text(result + "\\n")')
        self.write('_console_input.text = ""')
        self.dedent()
        self.write_blank()

        self.write("func _execute_command(cmd: String) -> String:")
        self.indent()
        self.write("var parts = cmd.strip_edges().split(' ')")
        self.write("if parts.size() == 0:")
        self.indent()
        self.write('return "[color=red]Empty command[/color]"')
        self.dedent()
        self.write_blank()

        # Handle set command for 3D
        self.write_comment("Handle 'set obj prop to value' (space syntax)")
        self.write('if parts[0] == "set" and parts.size() >= 5 and parts[3] == "to":')
        self.indent()
        self.write("var obj_name = parts[1]")
        self.write("var prop_name = parts[2]")
        self.write('var value_str = " ".join(parts.slice(4))')
        self.write("return _set_property(obj_name, prop_name, value_str)")
        self.dedent()
        self.write_blank()

        # List command (include runtime objects)
        self.write_comment("Handle 'list' command")
        self.write('if parts[0] == "list" or parts[0] == "ls" or parts[0] == "objects":')
        self.indent()
        self.write(f'var all_objs = "{obj_list_str}"')
        self.write("if _runtime_objects.size() > 0:")
        self.indent()
        self.write('all_objs += ", " + ", ".join(_runtime_objects.keys())')
        self.dedent()
        self.write('return "[color=green]Objects: " + all_objs + "[/color]"')
        self.dedent()
        self.write_blank()

        # Look command for 3D
        self.write_comment("Handle 'look' command (aliases: l, examine, x)")
        self.write('if parts[0] == "look" or parts[0] == "l" or parts[0] == "examine" or parts[0] == "x":')
        self.indent()
        self.write('if parts.size() < 2:')
        self.indent()
        self.write('return "[color=red]Usage: look <object>[/color]"')
        self.dedent()
        self.write("return _look_object(parts[1])")
        self.dedent()
        self.write_blank()

        # Hide/show commands
        self.write_comment("Handle 'hide' command")
        self.write('if parts[0] == "hide":')
        self.indent()
        self.write('if parts.size() < 2: return "[color=red]Usage: hide <object>[/color]"')
        self.write("return _set_property(parts[1], \"visible\", \"false\")")
        self.dedent()
        self.write_blank()

        self.write_comment("Handle 'show' command (alias: unhide)")
        self.write('if parts[0] == "show" or parts[0] == "unhide":')
        self.indent()
        self.write('if parts.size() < 2: return "[color=red]Usage: show <object>[/color]"')
        self.write("return _set_property(parts[1], \"visible\", \"true\")")
        self.dedent()
        self.write_blank()

        # Create command
        self.write_comment("Handle 'create' command")
        self.write('if parts[0] == "create":')
        self.indent()
        self.write('if parts.size() < 2: return "[color=red]Usage: create <name> [at x y z][/color]"')
        self.write("return _create_object(parts)")
        self.dedent()
        self.write_blank()

        # Delete command
        self.write_comment("Handle 'delete' command (aliases: destroy, remove, rm)")
        self.write('if parts[0] == "delete" or parts[0] == "destroy" or parts[0] == "remove" or parts[0] == "rm":')
        self.indent()
        self.write('if parts.size() < 2: return "[color=red]Usage: delete <object>[/color]"')
        self.write("return _delete_object(parts[1])")
        self.dedent()
        self.write_blank()

        # Move command
        self.write_comment("Handle 'move' command")
        self.write('if parts[0] == "move":')
        self.indent()
        self.write('if parts.size() < 5 or parts[2] != "to": return "[color=red]Usage: move <obj> to <x> <y> [z][/color]"')
        self.write("var result = _set_property(parts[1], \"x\", parts[3])")
        self.write("_set_property(parts[1], \"y\", parts[4])")
        self.write('if parts.size() >= 6: _set_property(parts[1], "z", parts[5])')
        self.write('return "[color=green]Moved " + parts[1] + "[/color]"')
        self.dedent()
        self.write_blank()

        # Clear command
        self.write_comment("Handle 'clear' command (alias: cls)")
        self.write('if parts[0] == "clear" or parts[0] == "cls":')
        self.indent()
        self.write(f'_console_output.text = "[color=cyan]Rosh v{__version__} | Godot 3D[/color]\\n"')
        self.write('return ""')
        self.dedent()
        self.write_blank()

        # Undo command
        self.write_comment("Handle 'undo' command (alias: oops)")
        self.write('if parts[0] == "undo" or parts[0] == "oops":')
        self.indent()
        self.write("return _perform_undo()")
        self.dedent()
        self.write_blank()

        # Redo command
        self.write_comment("Handle 'redo' command")
        self.write('if parts[0] == "redo":')
        self.indent()
        self.write("return _perform_redo()")
        self.dedent()
        self.write_blank()

        # Help command
        self.write_comment("Handle 'help' command (alias: ?)")
        self.write('if parts[0] == "help" or parts[0] == "?":')
        self.indent()
        self.write('return "[color=cyan]Commands:\\n  set obj prop to value\\n  look/examine obj\\n  hide/show obj\\n  create [color] [size] [shape] name [at x y z]\\n  delete/rm obj\\n  move obj to x y [z]\\n  undo/redo\\n  list\\n  clear\\n  help[/color]"')
        self.dedent()
        self.write_blank()

        self.write('return "[color=red]Unknown command: " + parts[0] + "[/color]"')
        self.dedent()
        self.write_blank()

        # 3D-specific set_property
        self.write("func _set_property(obj_name: String, prop_name: String, value_str: String) -> String:")
        self.indent()
        self.write("var val = value_str")
        self.write("if val.is_valid_float(): val = float(val)")
        self.write('elif val == "true": val = true')
        self.write('elif val == "false": val = false')
        self.write_blank()

        for obj in self.ir.objects:
            self.write(f'if obj_name == "{obj.name}":')
            self.indent()
            self.write(f'if prop_name == "visible": {obj.name}_visible = val; {obj.name}.visible = val')
            if obj.name in self.text_objects:
                self.write(f'elif prop_name == "font_size": {obj.name}_font_size = float(val)')
                self.write(f'elif prop_name == "text": {obj.name}_text = value_str')
            self.write(f'elif prop_name == "x" and {obj.name}: {obj.name}.position.x = float(val)')
            self.write(f'elif prop_name == "y" and {obj.name}: {obj.name}.position.y = float(val)')
            self.write(f'elif prop_name == "z" and {obj.name}: {obj.name}.position.z = float(val)')
            self.write(f'else: return "[color=red]Unknown property: " + prop_name + "[/color]"')
            self.write(f'return "[color=green]Set {obj.name}." + prop_name + " = " + str(val) + "[/color]"')
            self.dedent()

        # Handle runtime objects
        self.write_comment("Handle runtime objects")
        self.write("if _runtime_objects.has(obj_name):")
        self.indent()
        self.write("var obj = _runtime_objects[obj_name]")
        self.write('if prop_name == "x": obj.position.x = float(val)')
        self.write('elif prop_name == "y": obj.position.y = float(val)')
        self.write('elif prop_name == "z": obj.position.z = float(val)')
        self.write('elif prop_name == "visible": obj.visible = val')
        self.write('else: return "[color=red]Unknown property: " + prop_name + "[/color]"')
        self.write('return "[color=green]Set " + obj_name + "." + prop_name + " = " + str(val) + "[/color]"')
        self.dedent()

        self.write('return "[color=red]Unknown object: " + obj_name + "[/color]"')
        self.dedent()
        self.write_blank()

        # 3D-specific look_object
        self.write("func _look_object(obj_name: String) -> String:")
        self.indent()
        for obj in self.ir.objects:
            self.write(f'if obj_name == "{obj.name}" and {obj.name}:')
            self.indent()
            self.write(f'var pos = {obj.name}.position')
            if obj.name in self.text_objects:
                self.write(f'return "[color=green]{obj.name}: pos=(" + str(pos.x) + "," + str(pos.y) + "," + str(pos.z) + "), text=\\"" + {obj.name}_text + "\\"[/color]"')
            else:
                self.write(f'return "[color=green]{obj.name}: pos=(" + str(pos.x) + "," + str(pos.y) + "," + str(pos.z) + ")[/color]"')
            self.dedent()
        self.write("if _runtime_objects.has(obj_name):")
        self.indent()
        self.write("var obj = _runtime_objects[obj_name]")
        self.write('return "[color=green]" + obj_name + ": pos=(" + str(obj.position.x) + "," + str(obj.position.y) + "," + str(obj.position.z) + ")[/color]"')
        self.dedent()
        self.write('return "[color=red]Object not found: " + obj_name + "[/color]"')
        self.dedent()
        self.write_blank()

        # Create object for 3D - parses modifiers per rosh-console.toml spec
        self.write("func _create_object(parts: Array) -> String:")
        self.indent()
        self.write_comment("Parse modifiers: 'create blue box' → name='box', color=blue")
        self.write("var colors = {")
        self.indent()
        self.write('"red": Color.RED, "green": Color.GREEN, "blue": Color.BLUE,')
        self.write('"yellow": Color.YELLOW, "cyan": Color.CYAN, "magenta": Color.MAGENTA,')
        self.write('"white": Color.WHITE, "black": Color.BLACK, "orange": Color.ORANGE,')
        self.write('"purple": Color(0.5, 0, 1), "pink": Color(1, 0.5, 1),')
        self.write('"gray": Color.GRAY, "grey": Color.GRAY')
        self.dedent()
        self.write("}")
        self.write('var size_mods = ["big", "large", "small", "tiny"]')
        self.write('var shape_words = ["ball", "sphere", "cube", "box", "cylinder"]')
        self.write('var articles = ["a", "an", "the"]')
        self.write_blank()
        self.write("var x = 0.0; var y = 1.0; var z = 0.0")
        self.write("var obj_color = Color.GREEN")
        self.write("var obj_size = 1.0")
        self.write('var obj_shape = "box"')
        self.write_blank()
        self.write_comment("Find 'at x y z' position")
        self.write("var at_idx = -1")
        self.write("for i in range(parts.size()):")
        self.indent()
        self.write('if parts[i] == "at": at_idx = i; break')
        self.dedent()
        self.write("if at_idx > 0 and parts.size() >= at_idx + 3:")
        self.indent()
        self.write("x = float(parts[at_idx + 1])")
        self.write("y = float(parts[at_idx + 2])")
        self.write("if parts.size() >= at_idx + 4: z = float(parts[at_idx + 3])")
        self.dedent()
        self.write_blank()
        self.write_comment("Parse words before 'at' (or all if no 'at')")
        self.write("var desc_parts = parts.slice(1, at_idx if at_idx > 0 else parts.size())")
        self.write("var obj_name = 'object'")
        self.write_blank()
        self.write_comment("Find the name - last word that isn't a color, size, or article")
        self.write_comment("Shape words (ball, box) can be names if nothing else found")
        self.write("for i in range(desc_parts.size() - 1, -1, -1):")
        self.indent()
        self.write("var word = desc_parts[i].to_lower()")
        self.write("if not colors.has(word) and not (word in size_mods) and not (word in articles):")
        self.indent()
        self.write("obj_name = word")
        self.write("break")
        self.dedent()
        self.dedent()
        self.write_blank()
        self.write_comment("Apply modifiers")
        self.write("for word in desc_parts:")
        self.indent()
        self.write("var w = word.to_lower()")
        self.write("if colors.has(w): obj_color = colors[w]")
        self.write('if w == "big" or w == "large": obj_size = 2.0')
        self.write('if w == "small" or w == "tiny": obj_size = 0.5')
        self.write('if w == "ball" or w == "sphere": obj_shape = "sphere"')
        self.write('if w == "cylinder" or w == "tube": obj_shape = "cylinder"')
        self.dedent()
        self.write_blank()
        self.write_comment("Auto-number if name exists")
        self.write("var final_name = obj_name")
        self.write("var counter = 2")
        self.write("while _runtime_objects.has(final_name):")
        self.indent()
        self.write("final_name = obj_name + str(counter); counter += 1")
        self.dedent()
        self.write_blank()
        self.write_comment("Create 3D mesh based on shape")
        self.write("var mesh = MeshInstance3D.new()")
        self.write('if obj_shape == "sphere":')
        self.indent()
        self.write("var sphere = SphereMesh.new()")
        self.write("sphere.radius = obj_size * 0.5")
        self.write("sphere.height = obj_size")
        self.write("mesh.mesh = sphere")
        self.dedent()
        self.write('elif obj_shape == "cylinder":')
        self.indent()
        self.write("var cyl = CylinderMesh.new()")
        self.write("cyl.top_radius = obj_size * 0.5")
        self.write("cyl.bottom_radius = obj_size * 0.5")
        self.write("cyl.height = obj_size")
        self.write("mesh.mesh = cyl")
        self.dedent()
        self.write("else:")
        self.indent()
        self.write("var box = BoxMesh.new()")
        self.write("box.size = Vector3(obj_size, obj_size, obj_size)")
        self.write("mesh.mesh = box")
        self.dedent()
        self.write("var mat = StandardMaterial3D.new()")
        self.write("mat.albedo_color = obj_color")
        self.write("mesh.material_override = mat")
        self.write("mesh.position = Vector3(x, y, z)")
        self.write("add_child(mesh)")
        self.write("_runtime_objects[final_name] = mesh")
        self.write_comment("Add to undo stack")
        self.write('_undo_stack.append({"type": "create", "name": final_name, "obj": mesh})')
        self.write("_redo_stack.clear()")
        self.write('return "[color=green]Created " + final_name + " at (" + str(x) + "," + str(y) + "," + str(z) + ")[/color]"')
        self.dedent()
        self.write_blank()

        # Delete object for 3D
        self.write("func _delete_object(obj_name: String) -> String:")
        self.indent()
        self.write("if _runtime_objects.has(obj_name):")
        self.indent()
        self.write("var obj = _runtime_objects[obj_name]")
        self.write("var pos = obj.position")
        self.write("obj.queue_free()")
        self.write("_runtime_objects.erase(obj_name)")
        self.write('_undo_stack.append({"type": "delete", "name": obj_name, "pos": pos})')
        self.write("_redo_stack.clear()")
        self.write('return "[color=green]Deleted " + obj_name + "[/color]"')
        self.dedent()
        self.write('return "[color=red]Object not found: " + obj_name + "[/color]"')
        self.dedent()
        self.write_blank()

        # Undo for 3D
        self.write("func _perform_undo() -> String:")
        self.indent()
        self.write("if _undo_stack.size() == 0:")
        self.indent()
        self.write('return "[color=yellow]Nothing to undo[/color]"')
        self.dedent()
        self.write("var action = _undo_stack.pop_back()")
        self.write('if action["type"] == "create":')
        self.indent()
        self.write('var obj = _runtime_objects.get(action["name"])')
        self.write("if obj: obj.queue_free()")
        self.write('_runtime_objects.erase(action["name"])')
        self.write("_redo_stack.append(action)")
        self.write('return "[color=green]Undo: create " + action["name"] + "[/color]"')
        self.dedent()
        self.write('elif action["type"] == "delete":')
        self.indent()
        self.write_comment("Recreate deleted object")
        self.write("var mesh = MeshInstance3D.new()")
        self.write("var box = BoxMesh.new()")
        self.write("box.size = Vector3(1, 1, 1)")
        self.write("mesh.mesh = box")
        self.write("var mat = StandardMaterial3D.new()")
        self.write("mat.albedo_color = Color.GREEN")
        self.write("mesh.material_override = mat")
        self.write('mesh.position = action["pos"]')
        self.write("add_child(mesh)")
        self.write('_runtime_objects[action["name"]] = mesh')
        self.write("_redo_stack.append(action)")
        self.write('return "[color=green]Undo: delete " + action["name"] + "[/color]"')
        self.dedent()
        self.write('return "[color=yellow]Unknown undo action[/color]"')
        self.dedent()
        self.write_blank()

        # Redo for 3D
        self.write("func _perform_redo() -> String:")
        self.indent()
        self.write("if _redo_stack.size() == 0:")
        self.indent()
        self.write('return "[color=yellow]Nothing to redo[/color]"')
        self.dedent()
        self.write("var action = _redo_stack.pop_back()")
        self.write('if action["type"] == "create":')
        self.indent()
        self.write_comment("Recreate object")
        self.write("var mesh = MeshInstance3D.new()")
        self.write("var box = BoxMesh.new()")
        self.write("box.size = Vector3(1, 1, 1)")
        self.write("mesh.mesh = box")
        self.write("var mat = StandardMaterial3D.new()")
        self.write("mat.albedo_color = Color.GREEN")
        self.write("mesh.material_override = mat")
        self.write("add_child(mesh)")
        self.write('_runtime_objects[action["name"]] = mesh')
        self.write("_undo_stack.append(action)")
        self.write('return "[color=green]Redo: create " + action["name"] + "[/color]"')
        self.dedent()
        self.write('elif action["type"] == "delete":')
        self.indent()
        self.write('var obj = _runtime_objects.get(action["name"])')
        self.write("if obj: obj.queue_free()")
        self.write('_runtime_objects.erase(action["name"])')
        self.write("_undo_stack.append(action)")
        self.write('return "[color=green]Redo: delete " + action["name"] + "[/color]"')
        self.dedent()
        self.write('return "[color=yellow]Unknown redo action[/color]"')
        self.dedent()
        self.write_blank()
