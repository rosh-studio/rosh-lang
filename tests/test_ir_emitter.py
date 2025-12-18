"""
Tests for the IR Emitter (Phaser)

Tests that IR is correctly emitted as Phaser JavaScript code.
"""

import pytest
from rosh.parser import Parser
from rosh.lexer import Lexer
from rosh.ir_transformer import transform_ast_to_ir
from rosh.emitters.phaser import PhaserEmitter


def parse(source: str):
    """Helper to parse Rosh source code."""
    lexer = Lexer(source)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    return parser.parse()


def emit_phaser(source: str, **kwargs) -> str:
    """Helper to transform and emit Phaser code."""
    ast = parse(source)
    ir = transform_ast_to_ir(ast, **kwargs)
    emitter = PhaserEmitter(ir)
    return emitter.emit()


class TestPhaserEmitterBasics:
    """Basic emitter tests."""

    def test_empty_program(self):
        """Empty program should produce valid Phaser boilerplate."""
        code = emit_phaser("")
        assert "class GameScene extends Phaser.Scene" in code
        assert "create()" in code
        assert "new Phaser.Game(config)" in code

    def test_game_config_dimensions(self):
        """Game config should use canvas dimensions."""
        code = emit_phaser("", canvas_width=1024, canvas_height=768)
        assert "width: 1024" in code
        assert "height: 768" in code


class TestObjectEmission:
    """Tests for object emission."""

    def test_simple_object(self):
        """Object should be created as rectangle."""
        code = emit_phaser("""
            create object ball
                set x to 400
                set y to 300
            end
        """)
        assert "this.ball = this.add.rectangle" in code

    def test_object_position(self):
        """Object position should be denormalized from percentage to pixels."""
        code = emit_phaser("""
            create object ball
                set x to 50
                set y to 50
            end
        """, canvas_width=800, canvas_height=600)
        # 50% of 800 = 400, 50% of 600 = 300
        assert "400" in code
        assert "300" in code

    def test_object_position_explicit_pixels(self):
        """Explicit pixel values (400px) should work."""
        code = emit_phaser("""
            create object ball
                set x to 400px
                set y to 300px
            end
        """, canvas_width=800, canvas_height=600)
        # 400px normalized to 0.5, then back to 400
        assert "400" in code
        assert "300" in code

    def test_object_color(self):
        """Object color should be hex formatted."""
        code = emit_phaser("""
            create object ball
                set color to "red"
            end
        """)
        assert "0xff0000" in code

    def test_sprite_object(self):
        """Object with sprite should use add.sprite."""
        code = emit_phaser("""
            create object hero
                set sprite to "hero.png"
            end
        """)
        assert "this.add.sprite" in code
        assert "hero_png" in code  # Asset key

    def test_player_inheritance(self):
        """Player objects should get auto-controls."""
        code = emit_phaser("""
            create object hero from player
            end
        """)
        assert "handlePlayerInput" in code
        assert "cursors" in code


class TestEventEmission:
    """Tests for event emission."""

    def test_update_event(self):
        """Update event should register handler."""
        code = emit_phaser("""
            when update then
                print "tick"
            end
        """)
        assert "registerEvent('update'" in code
        assert "console.log" in code

    def test_keydown_event(self):
        """Keydown events should use Phaser keyboard input."""
        code = emit_phaser("""
            when keydown space then
                print "jump"
            end
        """)
        assert "keydown-SPACE" in code


class TestActionEmission:
    """Tests for action emission."""

    def test_print_action(self):
        """Print should become console.log."""
        code = emit_phaser('print "hello"')
        assert "console.log" in code

    def test_set_property_action(self):
        """Set property should update object."""
        code = emit_phaser("""
            create object ball
            end
            set ball.x to 100
        """)
        assert "this.ball.x =" in code

    def test_play_sound(self):
        """Play sound should use Phaser sound system."""
        code = emit_phaser('play sound "laser.ogg"')
        assert "preload()" in code
        assert "this.load.audio" in code
        assert "this.sound.play" in code


class TestExpressionEmission:
    """Tests for expression emission."""

    def test_comparison_expression(self):
        """Comparisons should use JavaScript operators."""
        code = emit_phaser("""
            if 1 is equal to 1 then
                print "yes"
            end
        """)
        assert "==" in code

    def test_binary_expression(self):
        """Binary operations should be parenthesized."""
        code = emit_phaser("""
            create object ball
            end
            set ball.x to 1 plus 2
        """)
        assert "(1 + 2)" in code or "1 + 2" in code

    def test_logical_operators(self):
        """Logical operators should become && and ||."""
        code = emit_phaser("""
            if 1 is above 0 and 2 is above 1 then
                print "yes"
            end
        """)
        assert "&&" in code


class TestFunctionEmission:
    """Tests for function emission."""

    def test_function_def(self):
        """Functions should become class methods."""
        code = emit_phaser("""
            define function greet name
                print name
            end
        """)
        assert "greet(name)" in code

    def test_function_with_return(self):
        """Return statements should work."""
        code = emit_phaser("""
            define function double x
                return x times 2
            end
        """)
        assert "return" in code


class TestPreloadGeneration:
    """Tests for asset preloading."""

    def test_no_preload_without_assets(self):
        """No preload method if no assets used."""
        code = emit_phaser("""
            create object ball
            end
        """)
        # Rectangle objects don't need preload
        assert "preload()" not in code or "this.load" not in code

    def test_preload_with_sprite(self):
        """Preload method generated for sprites."""
        code = emit_phaser("""
            create object hero
                set sprite to "hero.png"
            end
        """)
        assert "preload()" in code
        assert "this.load.image" in code

    def test_preload_with_sound(self):
        """Preload method generated for sounds."""
        code = emit_phaser('play sound "laser.ogg"')
        assert "preload()" in code
        assert "this.load.audio" in code


class TestHelperMethods:
    """Tests for helper method generation."""

    def test_event_helpers_generated(self):
        """Event helpers generated when events used."""
        code = emit_phaser("""
            when update then
                print "tick"
            end
        """)
        assert "registerEvent(name, handler)" in code
        assert "triggerEvent(name" in code

    def test_player_input_helper(self):
        """Player input helper generated for player objects."""
        code = emit_phaser("""
            create object hero from player
            end
        """)
        assert "handlePlayerInput(player)" in code
        assert "cursors.left.isDown" in code
