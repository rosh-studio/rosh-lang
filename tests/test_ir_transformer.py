"""
Tests for the IR Transformer

Tests that AST nodes are correctly transformed to IR representation.
"""

import pytest
from rosh.parser import Parser
from rosh.lexer import Lexer
from rosh.ir import (
    IR_Program, IR_Object, IR_Event, IR_Action, IR_Function,
    IR_Value, IR_Expression, IR_Conditional, IR_Loop
)
from rosh.ir_transformer import IRTransformer, transform_ast_to_ir


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
        """Bare numbers are percentages (0-100 scale), normalized to 0-1."""
        # Design Decision (2025-12-18): set x to 50 means 50%, not 50 pixels
        program = parse("""
            create object ball
                set x to 50
                set y to 50
            end
        """)
        ir = transform_ast_to_ir(program)
        obj = ir.objects[0]
        assert obj.properties['x'].type == 'percentage'
        assert obj.properties['x'].value == 0.5  # 50% = 0.5
        assert obj.properties['y'].type == 'percentage'
        assert obj.properties['y'].value == 0.5  # 50% = 0.5

    def test_percentage_explicit(self):
        """Explicit percentage (50%) should work the same as bare 50."""
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
