"""
Tests for stdlib function validation
"""

import pytest
from src.rosh.lexer import Lexer
from src.rosh.parser import Parser
from src.rosh.interpreter import Interpreter
from io import StringIO


def execute_rosh(code: str) -> str:
    """Helper to execute Rosh code and capture output"""
    output = StringIO()
    lexer = Lexer(code)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    program = parser.parse()
    interpreter = Interpreter(output_stream=output)
    interpreter.execute(program)
    return output.getvalue()


class TestEveryFunctionValidation:
    """Test validation in the every() function from game-loop-simple"""

    def test_every_valid_inputs(self):
        """Test every() with valid numeric inputs"""
        code = """
        import "stdlib/game-loop-simple.rosh"

        if call every 5 10 then
            print "Divisible!"
        end
        """
        output = execute_rosh(code)
        assert "Divisible!" in output

    def test_every_zero_interval(self):
        """Test every() rejects zero interval"""
        code = """
        import "stdlib/game-loop-simple.rosh"

        if call every 0 10 then
            print "Should not print"
        else
            print "Correctly rejected"
        end
        """
        output = execute_rosh(code)
        assert "ERROR: every() interval cannot be zero" in output
        assert "Should not print" not in output

    def test_every_negative_interval(self):
        """Test every() rejects negative interval"""
        code = """
        import "stdlib/game-loop-simple.rosh"

        if call every -5 10 then
            print "Should not print"
        else
            print "Correctly rejected"
        end
        """
        output = execute_rosh(code)
        assert "ERROR: every() interval must be positive" in output

    def test_every_non_numeric_interval(self):
        """Test every() rejects non-numeric interval"""
        code = """
        import "stdlib/game-loop-simple.rosh"

        if call every "hello" 10 then
            print "Should not print"
        else
            print "Correctly rejected"
        end
        """
        output = execute_rosh(code)
        assert "ERROR: every() interval must be a number" in output

    def test_every_non_numeric_current(self):
        """Test every() rejects non-numeric current"""
        code = """
        import "stdlib/game-loop-simple.rosh"

        if call every 5 "world" then
            print "Should not print"
        else
            print "Correctly rejected"
        end
        """
        output = execute_rosh(code)
        assert "ERROR: every() current must be a number" in output

    def test_every_in_game_loop(self):
        """Test every() works correctly in a game loop"""
        code = """
        import "stdlib/game-loop-simple.rosh"

        set count to 0

        while tick_count is below 10 then
            if call every 3 tick_count then
                set count to count plus 1
            end
            set tick_count to tick_count plus 1
        end

        get count
        print stack
        """
        output = execute_rosh(code)
        # Should trigger at 0, 3, 6, 9 = 4 times
        assert "4" in output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
