"""
Tests for the IR Transformer

Tests that AST nodes are correctly transformed to IR representation.
"""

import pytest
from src.rosh.parser import Parser
from src.rosh.lexer import Lexer
from src.rosh.ir import (
    IR_Program, IR_Object, IR_Event, IR_Action, IR_Function,
    IR_Value, IR_Expression, IR_Conditional, IR_Loop
)
from src.rosh.ir_transformer import IRTransformer, transform_ast_to_ir


def parse(source: str):
    """Helper to parse Rosh source code."""
    lexer = Lexer(source)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    return parser.parse()


class TestIRTransformerBasics:
    """Basic IR transformation tests."""

    def test_empty_program(self):
        """Empty program should produce empty IR."""
        program = parse("")
        ir = transform_ast_to_ir(program)
        assert isinstance(ir, IR_Program)
        assert ir.objects == []
        assert ir.events == []
        assert ir.functions == []

    def test_metadata_defaults(self):
        """IR should have default canvas dimensions."""
        program = parse("")
        ir = transform_ast_to_ir(program)
        assert ir.metadata.canvas_width == 800
        assert ir.metadata.canvas_height == 600

    def test_custom_canvas_size(self):
        """Custom canvas dimensions should be preserved."""
        program = parse("")
        ir = transform_ast_to_ir(program, canvas_width=1024, canvas_height=768)
        assert ir.metadata.canvas_width == 1024
        assert ir.metadata.canvas_height == 768


class TestObjectTransformation:
    """Tests for object transformation."""

    def test_simple_object(self):
        """Create object should produce IR_Object with UUID."""
        program = parse("""
            create object ball
                set x to 100
                set y to 200
            end
        """)
        ir = transform_ast_to_ir(program)
        assert len(ir.objects) == 1
        obj = ir.objects[0]
        assert obj.name == "ball"
        assert obj.uuid  # UUID should be generated
        assert len(obj.uuid) == 36  # UUID format

    def test_coordinate_normalization(self):
        """Bare numbers are pixels, normalized to percentage of canvas."""
        # Per CLAUDE.md: bare numbers = pixels, 50% = percentage
        program = parse("""
            create object ball
                set x to 50
                set y to 50
            end
        """)
        ir = transform_ast_to_ir(program, canvas_width=800, canvas_height=600)
        obj = ir.objects[0]
        assert obj.properties['x'].type == 'percentage'
        assert obj.properties['x'].value == 50 / 800  # 50px on 800px canvas
        assert obj.properties['y'].type == 'percentage'
        assert obj.properties['y'].value == 50 / 600  # 50px on 600px canvas

    def test_percentage_explicit(self):
        """Explicit percentage (50%) normalizes to 0.5."""
        program = parse("""
            create object ball
                set x to 50%
            end
        """)
        ir = transform_ast_to_ir(program)
        obj = ir.objects[0]
        assert obj.properties['x'].type == 'percentage'
        assert obj.properties['x'].value == 0.5  # 50% = 0.5

    def test_pixel_explicit(self):
        """Explicit pixels (400px) should normalize to canvas dimensions."""
        program = parse("""
            create object ball
                set x to 400px
            end
        """)
        ir = transform_ast_to_ir(program, canvas_width=800)
        obj = ir.objects[0]
        assert obj.properties['x'].type == 'percentage'
        assert obj.properties['x'].value == 0.5  # 400px / 800 = 0.5

    def test_pixel_with_space(self):
        """Pixels with space (400 px) should also work."""
        program = parse("""
            create object ball
                set x to 400 px
            end
        """)
        ir = transform_ast_to_ir(program, canvas_width=800)
        obj = ir.objects[0]
        assert obj.properties['x'].type == 'percentage'
        assert obj.properties['x'].value == 0.5  # 400px / 800 = 0.5

    def test_color_string(self):
        """Color strings should be converted to hex."""
        program = parse("""
            create object ball
                set color to "red"
            end
        """)
        ir = transform_ast_to_ir(program)
        obj = ir.objects[0]
        assert obj.properties['color'].type == 'color'
        assert obj.properties['color'].value == 0xff0000

    def test_player_inheritance(self):
        """Objects from player should inherit player defaults."""
        program = parse("""
            create object hero from player
            end
        """)
        ir = transform_ast_to_ir(program)
        obj = ir.objects[0]
        assert obj.parent_type == 'player'
        assert obj.type == 'sprite'
        assert 'lives' in obj.properties
        assert obj.properties['lives'].value == 3


class TestEventTransformation:
    """Tests for event transformation."""

    def test_update_event(self):
        """When update should produce IR_Event with 'update' trigger."""
        program = parse("""
            when update then
                print "tick"
            end
        """)
        ir = transform_ast_to_ir(program)
        assert len(ir.events) == 1
        event = ir.events[0]
        assert event.trigger == 'update'
        assert len(event.handler) == 1

    def test_keydown_event(self):
        """Keyboard events should produce canonical trigger names."""
        program = parse("""
            when keydown space then
                print "jump"
            end
        """)
        ir = transform_ast_to_ir(program)
        event = ir.events[0]
        assert event.trigger == 'keydown:space'

    def test_collision_event(self):
        """Collision events should include object names."""
        program = parse("""
            when collision hero enemy then
                print "hit"
            end
        """)
        ir = transform_ast_to_ir(program)
        event = ir.events[0]
        assert event.trigger == 'collision:hero:enemy'


class TestActionTransformation:
    """Tests for action transformation."""

    def test_print_action(self):
        """Print statements should become print actions."""
        program = parse('print "hello"')
        ir = transform_ast_to_ir(program)
        assert len(ir.init_actions) == 1
        action = ir.init_actions[0]
        assert action.type == 'print'

    def test_set_property_action(self):
        """Set statements should become set_property actions."""
        program = parse("""
            create object ball
            end
            set ball.x to 100
        """)
        ir = transform_ast_to_ir(program)
        assert len(ir.init_actions) == 1
        action = ir.init_actions[0]
        assert action.type == 'set_property'
        assert action.params['target'] == 'ball'
        assert action.params['property'] == 'x'

    def test_play_sound_action(self):
        """Play sound should become play_sound action."""
        program = parse('play sound "laser.ogg"')
        ir = transform_ast_to_ir(program)
        action = ir.init_actions[0]
        assert action.type == 'play_sound'
        assert action.params['asset'] == 'laser.ogg'


class TestControlFlowTransformation:
    """Tests for control flow transformation."""

    def test_if_statement(self):
        """If statements should become IR_Conditional."""
        program = parse("""
            if 1 is equal to 1 then
                print "yes"
            end
        """)
        ir = transform_ast_to_ir(program)
        cond = ir.init_actions[0]
        assert isinstance(cond, IR_Conditional)
        assert len(cond.then_actions) == 1
        assert cond.else_actions == []

    def test_if_else(self):
        """If-else should populate both branches."""
        program = parse("""
            if 1 is above 2 then
                print "yes"
            else
                print "no"
            end
        """)
        ir = transform_ast_to_ir(program)
        cond = ir.init_actions[0]
        assert len(cond.then_actions) == 1
        assert len(cond.else_actions) == 1

    def test_while_loop(self):
        """While loops should become IR_Loop with type 'while'."""
        program = parse("""
            while x is below 10 then
                print x
            end
        """)
        ir = transform_ast_to_ir(program)
        loop = ir.init_actions[0]
        assert isinstance(loop, IR_Loop)
        assert loop.type == 'while'

    def test_for_loop(self):
        """For loops should become IR_Loop with type 'for'."""
        program = parse("""
            for i in 1 to 10 then
                print i
            end
        """)
        ir = transform_ast_to_ir(program)
        loop = ir.init_actions[0]
        assert isinstance(loop, IR_Loop)
        assert loop.type == 'for'
        assert loop.iterator == 'i'


class TestFunctionTransformation:
    """Tests for function transformation."""

    def test_function_def(self):
        """Function definitions should become IR_Function."""
        program = parse("""
            define function sum x y
                return x plus y
            end
        """)
        ir = transform_ast_to_ir(program)
        assert len(ir.functions) == 1
        func = ir.functions[0]
        assert func.name == 'sum'
        assert func.params == ['x', 'y']
        assert func.returns == True

    def test_function_without_return(self):
        """Functions without return should have returns=False."""
        program = parse("""
            define function greet name
                print name
            end
        """)
        ir = transform_ast_to_ir(program)
        func = ir.functions[0]
        assert func.returns == False


class TestExpressionTransformation:
    """Tests for expression transformation."""

    def test_comparison_operators(self):
        """Comparison operators should be mapped to IR symbols."""
        program = parse("""
            if x is equal to 5 then
                print "yes"
            end
        """)
        ir = transform_ast_to_ir(program)
        cond = ir.init_actions[0]
        assert cond.condition.operator == '=='

    def test_binary_operators(self):
        """Binary operators should be mapped correctly."""
        program = parse("""
            create object ball
            end
            set ball.x to 1 plus 2
        """)
        ir = transform_ast_to_ir(program)
        action = ir.init_actions[0]
        # The value should be an expression
        assert action.params['value'].type == 'expression'


class TestUUIDStability:
    """Tests for UUID generation and stability."""

    def test_unique_uuids(self):
        """Each object should get a unique UUID."""
        program = parse("""
            create object a end
            create object b end
            create object c end
        """)
        ir = transform_ast_to_ir(program)
        uuids = [obj.uuid for obj in ir.objects]
        assert len(set(uuids)) == 3  # All unique

    def test_uuid_format(self):
        """UUIDs should be valid format."""
        program = parse("create object test end")
        ir = transform_ast_to_ir(program)
        import re
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        assert re.match(uuid_pattern, ir.objects[0].uuid)


class TestCaseNormalization:
    """Tests for case normalization."""

    def test_object_names_lowercase(self):
        """Object names should be normalized to lowercase."""
        program = parse("create object HERO end")
        ir = transform_ast_to_ir(program)
        assert ir.objects[0].name == 'hero'

    def test_property_names_lowercase(self):
        """Property names should be normalized to lowercase."""
        program = parse("""
            create object ball
                set COLOR to "red"
            end
        """)
        ir = transform_ast_to_ir(program)
        assert 'color' in ir.objects[0].properties

    def test_event_names_lowercase(self):
        """Event names should be normalized to lowercase."""
        program = parse("""
            when UPDATE then
                print "tick"
            end
        """)
        ir = transform_ast_to_ir(program)
        assert ir.events[0].trigger == 'update'


class TestHiddenObjects:
    """Tests for hidden objects (underscore convention)."""

    def test_underscore_prefix_sets_hidden_flag(self):
        """Objects starting with '_' should have hidden=True."""
        program = parse("""
            create object _meta
                set title to "Test"
            end
        """)
        ir = transform_ast_to_ir(program)
        assert len(ir.objects) == 1
        obj = ir.objects[0]
        assert obj.name == "_meta"
        assert obj.hidden == True

    def test_regular_object_not_hidden(self):
        """Regular objects should have hidden=False."""
        program = parse("""
            create object ball
                set x to 100
            end
        """)
        ir = transform_ast_to_ir(program)
        obj = ir.objects[0]
        assert obj.name == "ball"
        assert obj.hidden == False

    def test_hidden_template(self):
        """Template objects with underscore should be hidden."""
        program = parse("""
            create object _template
                set speed to 5
            end
        """)
        ir = transform_ast_to_ir(program)
        obj = ir.objects[0]
        assert obj.hidden == True
        assert obj.properties['speed'].value == 5

    def test_hidden_config(self):
        """Config objects with underscore should be hidden."""
        program = parse("create _config")
        ir = transform_ast_to_ir(program)
        obj = ir.objects[0]
        assert obj.name == "_config"
        assert obj.hidden == True

    def test_mixed_hidden_and_visible(self):
        """Mix of hidden and visible objects."""
        program = parse("""
            create _meta end
            create player end
            create _template end
            create enemy end
        """)
        ir = transform_ast_to_ir(program)
        assert len(ir.objects) == 4

        hidden_objects = [o for o in ir.objects if o.hidden]
        visible_objects = [o for o in ir.objects if not o.hidden]

        assert len(hidden_objects) == 2
        assert len(visible_objects) == 2
        assert set(o.name for o in hidden_objects) == {'_meta', '_template'}
        assert set(o.name for o in visible_objects) == {'player', 'enemy'}


class TestSettingsLoading:
    """Tests for settings loading (Phase 2 - Project Arcade)."""

    def test_load_json_creates_objects(self, tmp_path):
        """Loading JSON file should create objects."""
        import json

        # Create test JSON file
        settings = {
            "player": {"x": 400, "y": 300, "color": "green"},
            "enemy": {"x": 200, "y": 100}
        }
        json_file = tmp_path / "settings.json"
        json_file.write_text(json.dumps(settings))

        # Parse with load statement
        program = parse(f'load "settings.json"')
        ir = transform_ast_to_ir(program, project_root=str(tmp_path))

        assert len(ir.objects) == 2
        player = next(o for o in ir.objects if o.name == 'player')
        enemy = next(o for o in ir.objects if o.name == 'enemy')

        assert player.properties['x'].value == 0.5  # 400/800 normalized
        assert player.properties['y'].value == 0.5  # 300/600 normalized
        assert enemy.hidden == False

    def test_hidden_objects_from_json(self, tmp_path):
        """Objects with underscore prefix in JSON should be hidden."""
        import json

        settings = {
            "_meta": {"title": "Test Game"},
            "_config": {"speed": 5},
            "player": {"x": 400}
        }
        json_file = tmp_path / "settings.json"
        json_file.write_text(json.dumps(settings))

        program = parse('load "settings.json"')
        ir = transform_ast_to_ir(program, project_root=str(tmp_path))

        assert len(ir.objects) == 3
        meta = next(o for o in ir.objects if o.name == '_meta')
        config = next(o for o in ir.objects if o.name == '_config')
        player = next(o for o in ir.objects if o.name == 'player')

        assert meta.hidden == True
        assert config.hidden == True
        assert player.hidden == False

    def test_color_conversion_from_json(self, tmp_path):
        """Color strings in JSON should be converted to hex."""
        import json

        settings = {
            "ball": {"color": "red"},
            "goal": {"color": "blue"}
        }
        json_file = tmp_path / "settings.json"
        json_file.write_text(json.dumps(settings))

        program = parse('load "settings.json"')
        ir = transform_ast_to_ir(program, project_root=str(tmp_path))

        ball = next(o for o in ir.objects if o.name == 'ball')
        goal = next(o for o in ir.objects if o.name == 'goal')

        assert ball.properties['color'].type == 'color'
        assert ball.properties['color'].value == 0xff0000  # red
        assert goal.properties['color'].value == 0x0000ff  # blue

    def test_property_types_from_json(self, tmp_path):
        """JSON property types should be correctly converted."""
        import json

        settings = {
            "config": {
                "name": "Test",
                "lives": 3,
                "speed": 5.5,
                "enabled": True,
                "items": ["sword", "shield"]
            }
        }
        json_file = tmp_path / "settings.json"
        json_file.write_text(json.dumps(settings))

        program = parse('load "settings.json"')
        ir = transform_ast_to_ir(program, project_root=str(tmp_path))

        config = ir.objects[0]
        assert config.properties['name'].type == 'string'
        assert config.properties['name'].value == 'Test'
        assert config.properties['lives'].type == 'number'
        assert config.properties['lives'].value == 3
        assert config.properties['speed'].type == 'number'
        assert config.properties['speed'].value == 5.5
        assert config.properties['enabled'].type == 'boolean'
        assert config.properties['enabled'].value == True
        assert config.properties['items'].type == 'list'

    def test_file_not_found_error(self, tmp_path):
        """Loading nonexistent file should raise FileNotFoundError."""
        program = parse('load "nonexistent.json"')

        with pytest.raises(FileNotFoundError):
            transform_ast_to_ir(program, project_root=str(tmp_path))

    def test_combined_load_and_create(self, tmp_path):
        """Load and create statements can be combined."""
        import json

        settings = {
            "_config": {"speed": 5}
        }
        json_file = tmp_path / "settings.json"
        json_file.write_text(json.dumps(settings))

        program = parse('''
            load "settings.json"
            create player
                set x to 400
            end
        ''')
        ir = transform_ast_to_ir(program, project_root=str(tmp_path))

        assert len(ir.objects) == 2
        config = next(o for o in ir.objects if o.name == '_config')
        player = next(o for o in ir.objects if o.name == 'player')

        assert config.hidden == True
        assert player.hidden == False

    def test_scene_extraction_from_json(self, tmp_path):
        """Scene and level properties should be extracted from JSON."""
        import json

        settings = {
            "npc": {"x": 100, "scene": "town", "level": 2}
        }
        json_file = tmp_path / "settings.json"
        json_file.write_text(json.dumps(settings))

        program = parse('load "settings.json"')
        ir = transform_ast_to_ir(program, project_root=str(tmp_path))

        npc = ir.objects[0]
        assert npc.scene == "town"
        assert npc.level == 2
        assert 'scene' not in npc.properties
        assert 'level' not in npc.properties


class TestQuerySyntax:
    """Tests for query syntax (Phase 3 - Project Arcade)."""

    def test_get_all_where_basic(self):
        """get all where condition should create IR action with filter."""
        program = parse('get all where x is above 100')
        ir = transform_ast_to_ir(program)

        assert len(ir.init_actions) == 1
        action = ir.init_actions[0]
        assert action.type == 'get'
        assert action.params['all'] == True
        assert action.params['filter'] is not None
        assert action.params['filter'].type == 'comparison'
        assert action.params['filter'].operator == '>'

    def test_get_all_where_compound(self):
        """get all where with AND/OR conditions."""
        program = parse('get all where x is above 100 and y is below 50')
        ir = transform_ast_to_ir(program)

        action = ir.init_actions[0]
        assert action.params['filter'].type == 'binary_op'
        assert action.params['filter'].operator == 'and'

    def test_get_all_type_where(self):
        """get all <type> where condition."""
        program = parse('get all enemies where speed is above 5')
        ir = transform_ast_to_ir(program)

        action = ir.init_actions[0]
        assert action.params['all'] == True
        assert action.params['target'] is not None
        assert action.params['filter'] is not None

    def test_get_all_including_hidden(self):
        """get all including hidden should set include_hidden flag."""
        program = parse('get all including hidden where x is above 0')
        ir = transform_ast_to_ir(program)

        action = ir.init_actions[0]
        assert action.params['include_hidden'] == True
        assert action.params['filter'] is not None

    def test_destroy_confirmed(self):
        """destroy confirmed should set confirmed flag."""
        program = parse('destroy confirmed')
        ir = transform_ast_to_ir(program)

        action = ir.init_actions[0]
        assert action.type == 'destroy'
        assert action.params['target'] == 'selection'
        assert action.params['confirmed'] == True

    def test_destroy_without_confirmed(self):
        """destroy without confirmed should have confirmed=False."""
        program = parse('destroy')
        ir = transform_ast_to_ir(program)

        action = ir.init_actions[0]
        assert action.type == 'destroy'
        assert action.params['target'] == 'selection'
        assert action.params['confirmed'] == False

    def test_delete_specific_object(self):
        """delete <name> should target specific object."""
        program = parse('delete enemy')
        ir = transform_ast_to_ir(program)

        action = ir.init_actions[0]
        assert action.type == 'destroy'
        assert action.params['target'] == 'enemy'
        assert action.params['confirmed'] == False


class TestSpriteAnimations:
    """Tests for sprite sheet animation support."""

    def test_spritesheet_properties(self):
        """Sprite columns and rows should be extracted to IR."""
        program = parse("""
            create object explosion
                set sprite to "explosion.png"
                set sprite_columns to 3
                set sprite_rows to 3
            end
        """)
        ir = transform_ast_to_ir(program)

        assert len(ir.objects) == 1
        obj = ir.objects[0]
        assert obj.grid_cols == 3
        assert obj.grid_rows == 3

    def test_set_animations_auto_divide(self):
        """set animations to list should auto-divide frames."""
        program = parse("""
            create object player
                set sprite to "player.png"
                set sprite_columns to 4
                set sprite_rows to 1
                set animations to idle walk run jump
            end
        """)
        ir = transform_ast_to_ir(program)

        obj = ir.objects[0]
        assert obj.animations == {
            'idle': (0, 0),
            'walk': (1, 1),
            'run': (2, 2),
            'jump': (3, 3)
        }

    def test_set_animations_with_remainder(self):
        """Extra frames should go to last animation."""
        program = parse("""
            create object explosion
                set sprite to "explosion.png"
                set sprite_columns to 3
                set sprite_rows to 3
                set animations to start middle finish
            end
        """)
        ir = transform_ast_to_ir(program)

        obj = ir.objects[0]
        # 9 frames / 3 animations = 3 each
        assert obj.animations == {
            'start': (0, 2),
            'middle': (3, 5),
            'finish': (6, 8)
        }

    def test_set_animation_frames_override(self):
        """set animation X to start end should override frames."""
        program = parse("""
            create object player
                set sprite to "player.png"
                set sprite_columns to 8
                set sprite_rows to 1
                set animations to idle walk
                set animation idle to 0 3
                set animation walk to 4 7
            end
        """)
        ir = transform_ast_to_ir(program)

        obj = ir.objects[0]
        assert obj.animations == {
            'idle': (0, 3),
            'walk': (4, 7)
        }

    def test_frame_rate_property(self):
        """frame_rate property should be extracted."""
        program = parse("""
            create object explosion
                set sprite to "explosion.png"
                set sprite_columns to 3
                set sprite_rows to 3
                set frame_rate to 15
            end
        """)
        ir = transform_ast_to_ir(program)

        obj = ir.objects[0]
        assert obj.frame_rate == 15.0

    def test_flip_properties(self):
        """flip_x and flip_y should be extracted."""
        program = parse("""
            create object player
                set sprite to "player.png"
                set flip_x to true
                set flip_y to false
            end
        """)
        ir = transform_ast_to_ir(program)

        obj = ir.objects[0]
        assert obj.flip_x == True
        assert obj.flip_y == False

    def test_play_animation_action(self):
        """play X on target should create play_animation action."""
        program = parse('play walk on player')
        ir = transform_ast_to_ir(program)

        action = ir.init_actions[0]
        assert action.type == 'play_animation'
        assert action.params['animation'] == 'walk'
        assert action.params['target'] == 'player'
        assert action.params['loop'] == True

    def test_stop_animation_action(self):
        """stop animation on target should create stop_animation action."""
        program = parse('stop animation on player')
        ir = transform_ast_to_ir(program)

        action = ir.init_actions[0]
        assert action.type == 'stop_animation'
        assert action.params['target'] == 'player'


class TestArrayPools:
    """Tests for array pool creation syntax."""

    def test_array_pool_creates_objects(self):
        """create N objects as name should create N objects."""
        program = parse('''
create 3 objects as balls
    set color to "red"
end
''')
        ir = transform_ast_to_ir(program)

        assert len(ir.objects) == 3
        assert ir.objects[0].name == 'balls_0'
        assert ir.objects[1].name == 'balls_1'
        assert ir.objects[2].name == 'balls_2'

    def test_array_pool_registers_pool(self):
        """create N objects as name should register array pool."""
        program = parse('''
create 4 objects as explosions
    set visible to false
end
''')
        ir = transform_ast_to_ir(program)

        assert 'explosions' in ir.array_pools
        assert ir.array_pools['explosions'] == ['explosions_0', 'explosions_1', 'explosions_2', 'explosions_3']

    def test_array_pool_inherits_properties(self):
        """Objects in array pool should all have the same properties."""
        program = parse('''
create 2 objects as items
    set x to 100
    set y to 200
    set color to "blue"
end
''')
        ir = transform_ast_to_ir(program)

        for obj in ir.objects:
            assert 'x' in obj.properties
            assert 'y' in obj.properties

    def test_array_pool_not_hidden(self):
        """Objects in array pool should not be hidden."""
        program = parse('''
create 3 objects as enemies
    set color to "red"
end
''')
        ir = transform_ast_to_ir(program)

        for obj in ir.objects:
            assert obj.hidden == False

    def test_array_access_in_set_property(self):
        """set arr[0].x should create set_property with list_index target."""
        program = parse('''
create 2 objects as balls
    set x to 0
end
set balls[0].x to 100
''')
        ir = transform_ast_to_ir(program)

        # Find the set_property action
        action = ir.init_actions[0]
        assert action.type == 'set_property'
        # Target should be an IR_Expression for list_index
        target = action.params['target']
        assert target.type == 'list_index'
