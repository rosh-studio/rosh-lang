"""
Tests for event handler lexical scoping (v0.0.7)
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


class TestEventLexicalScoping:
    """Test that event handlers capture their defining environment"""

    def test_handler_captures_local_variables(self):
        """Test that handler can access locals from defining scope"""
        code = """
        define function setup_handler message
            # Handler defined inside function - should capture 'message'
            when show_message then
                print message
            end
        end

        # Call function to register handler with local variable
        call setup_handler "Hello from closure!"

        # Trigger event AFTER function has returned
        trigger show_message
        """
        output = execute_rosh(code)
        assert "Hello from closure!" in output

    def test_handler_captures_multiple_locals(self):
        """Test that handler captures multiple local variables"""
        code = """
        define function register_combat_handler name damage
            when attack then
                print "{name} attacks for {damage} damage!"
            end
        end

        call register_combat_handler "Goblin" 15
        trigger attack
        """
        output = execute_rosh(code)
        assert "Goblin attacks for 15 damage!" in output

    def test_multiple_handlers_different_closures(self):
        """Test multiple handlers with different captured variables"""
        code = """
        define function create_greeter name
            when greet then
                print "Hello from {name}!"
            end
        end

        call create_greeter "Alice"
        call create_greeter "Bob"
        call create_greeter "Charlie"

        trigger greet
        """
        output = execute_rosh(code)
        assert "Hello from Alice!" in output
        assert "Hello from Bob!" in output
        assert "Hello from Charlie!" in output

    def test_handler_with_nested_scope(self):
        """Test handler defined in deeply nested scope"""
        code = """
        set outer_var to "outer"

        define function outer
            set middle_var to "middle"

            define function inner
                set inner_var to "inner"

                when nested_event then
                    print outer_var
                    print middle_var
                    print inner_var
                end
            end

            call inner
        end

        call outer
        trigger nested_event
        """
        output = execute_rosh(code)
        assert "outer" in output
        assert "middle" in output
        assert "inner" in output

    def test_handler_modifies_captured_variables(self):
        """Test that handler can modify variables in captured scope"""
        code = """
        set counter to 0

        define function setup_counter
            when count_up then
                set counter to counter plus 1
            end
        end

        call setup_counter

        trigger count_up
        trigger count_up
        trigger count_up

        get counter
        print stack
        """
        output = execute_rosh(code)
        assert "3" in output

    def test_handler_with_object_from_closure(self):
        """Test handler accessing objects from defining scope"""
        code = """
        define function create_npc npc_name health
            create object npc
                set name to npc_name
                set hp to health
            end

            when npc_speaks then
                print "{npc.name} says: I have {npc.hp} HP!"
            end
        end

        call create_npc "Merchant" 100
        trigger npc_speaks
        """
        output = execute_rosh(code)
        assert "Merchant says: I have 100 HP!" in output

    def test_handler_parameters_shadow_captured_vars(self):
        """Test that handler parameters shadow captured variables"""
        code = """
        set value to "outer"

        define function setup
            when test_event value then
                print "Parameter: {value}"
            end
        end

        call setup
        trigger test_event with "inner"
        """
        output = execute_rosh(code)
        assert "Parameter: inner" in output
        assert "Parameter: outer" not in output

    def test_handler_accesses_global_after_local_function(self):
        """Test handler can access globals even when defined in function"""
        code = """
        set global_message to "Global"

        define function register_handler
            when show_global then
                print global_message
            end
        end

        call register_handler
        trigger show_global
        """
        output = execute_rosh(code)
        assert "Global" in output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
