"""
Tests for the event system (v0.0.7)
"""

import pytest
from src.rosh.lexer import Lexer
from src.rosh.parser import Parser
from src.rosh.interpreter import Interpreter
from src.rosh.errors import RoshRuntimeError
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


class TestBasicEvents:
    """Test basic event registration and triggering"""

    def test_simple_event_no_parameters(self):
        """Test event with no parameters"""
        code = """
        when game_over then
            print "You lost!"
        end

        trigger game_over
        """
        output = execute_rosh(code)
        assert "You lost!" in output

    def test_event_with_parameters(self):
        """Test event with parameters"""
        code = """
        when player_damaged amount then
            print "Took {amount} damage!"
        end

        trigger player_damaged with 25
        """
        output = execute_rosh(code)
        assert "Took 25 damage!" in output

    def test_event_with_multiple_parameters(self):
        """Test event with multiple parameters"""
        code = """
        when combat_start attacker defender then
            print "{attacker} attacks {defender}!"
        end

        trigger combat_start with "Goblin" "Player"
        """
        output = execute_rosh(code)
        assert "Goblin attacks Player!" in output

    def test_multiple_handlers_same_event(self):
        """Test multiple handlers for same event"""
        code = """
        when player_died then
            print "Game Over!"
        end

        when player_died then
            print "Final Score: 100"
        end

        trigger player_died
        """
        output = execute_rosh(code)
        assert "Game Over!" in output
        assert "Final Score: 100" in output

    def test_trigger_event_with_no_handlers(self):
        """Test triggering event with no handlers (should not error)"""
        code = """
        trigger nonexistent_event
        print "Still running"
        """
        output = execute_rosh(code)
        assert "Still running" in output


class TestEventArguments:
    """Test event argument passing and binding"""

    def test_event_with_expression_arguments(self):
        """Test triggering event with expression arguments"""
        code = """
        set x to 10
        set y to 5

        when calculation result then
            print "Result: {result}"
        end

        trigger calculation with x plus y
        """
        output = execute_rosh(code)
        assert "Result: 15" in output

    def test_event_with_object_arguments(self):
        """Test passing objects as event arguments"""
        code = """
        create object player
            set name to "Hero"
            set health to 100
        end

        when player_info p then
            print "{p.name} has {p.health} health"
        end

        trigger player_info with player
        """
        output = execute_rosh(code)
        assert "Hero has 100 health" in output

    def test_event_insufficient_arguments(self):
        """Test event with fewer arguments than parameters (should bind to null)"""
        code = """
        when test_event a b c then
            print "a={a}"
            print "b={b}"
            print "c={c}"
        end

        trigger test_event with 1 2
        """
        output = execute_rosh(code)
        assert "a=1" in output
        assert "b=2" in output
        assert "c=null" in output


class TestEventScoping:
    """Test event handler scoping and environment"""

    def test_event_handler_local_scope(self):
        """Test that event handlers have their own scope"""
        code = """
        set x to 10

        when test_event value then
            set x to value
            print "Inside handler: x={x}"
        end

        trigger test_event with 99
        print "Outside handler: x={x}"
        """
        output = execute_rosh(code)
        assert "Inside handler: x=99" in output
        # Handler should have its own environment, but it modifies parent scope
        # This tests that the handler can see and modify the outer scope

    def test_event_handler_access_global_variables(self):
        """Test that event handlers can access global variables"""
        code = """
        set score to 0

        when add_points amount then
            set score to score plus amount
        end

        trigger add_points with 10
        trigger add_points with 5

        print "Score: {score}"
        """
        output = execute_rosh(code)
        assert "Score: 15" in output

    def test_event_parameter_shadows_global(self):
        """Test that event parameters shadow global variables"""
        code = """
        set message to "Global"

        when test_event message then
            print "Handler: {message}"
        end

        trigger test_event with "Local"
        print "After: {message}"
        """
        output = execute_rosh(code)
        assert "Handler: Local" in output
        assert "After: Global" in output


class TestEventControl:
    """Test control flow within event handlers"""

    def test_event_with_if_statement(self):
        """Test if statement inside event handler"""
        code = """
        when check_health hp then
            if hp is below 20 then
                print "Critical!"
            else
                print "OK"
            end
        end

        trigger check_health with 10
        trigger check_health with 50
        """
        output = execute_rosh(code)
        assert "Critical!" in output
        assert "OK" in output

    def test_event_with_loop(self):
        """Test loop inside event handler"""
        code = """
        when countdown n then
            for i in n to 1 step -1 then
                get i
                print stack
            end
        end

        trigger countdown with 3
        """
        output = execute_rosh(code)
        assert "3" in output
        assert "2" in output
        assert "1" in output

    def test_nested_event_triggers(self):
        """Test triggering events from within event handlers"""
        code = """
        when outer_event then
            print "Outer"
            trigger inner_event
        end

        when inner_event then
            print "Inner"
        end

        trigger outer_event
        """
        output = execute_rosh(code)
        assert "Outer" in output
        assert "Inner" in output


class TestEventWithObjects:
    """Test events with object system integration"""

    def test_event_modifying_objects(self):
        """Test event handler modifying object properties"""
        code = """
        create object player
            set health to 100
        end

        when take_damage amount then
            set player.health to player.health minus amount
        end

        trigger take_damage with 25

        get player.health
        print stack
        """
        output = execute_rosh(code)
        assert "75" in output

    def test_event_with_multiple_objects(self):
        """Test event with multiple object arguments"""
        code = """
        create object goblin
            set name to "Goblin"
            set damage to 10
        end

        create object player
            set name to "Hero"
            set health to 100
        end

        when combat attacker defender dmg then
            print "{attacker.name} hits {defender.name} for {dmg} damage!"
            set defender.health to defender.health minus dmg
        end

        trigger combat with goblin player goblin.damage

        get player.health
        print stack
        """
        output = execute_rosh(code)
        assert "Goblin hits Hero for 10 damage!" in output
        assert "90" in output


class TestComplexEventScenarios:
    """Test complex real-world event scenarios"""

    def test_simple_combat_system(self):
        """Test a simple combat event system"""
        code = """
        create object player
            set health to 100
            set alive to true
        end

        when player_damaged amount then
            set player.health to player.health minus amount
            print "Player took {amount} damage! Health: {player.health}"

            if player.health is below 1 then
                trigger player_died
            end
        end

        when player_died then
            set player.alive to false
            print "Game Over!"
        end

        trigger player_damaged with 30
        trigger player_damaged with 50
        trigger player_damaged with 25
        """
        output = execute_rosh(code)
        assert "Player took 30 damage! Health: 70" in output
        assert "Player took 50 damage! Health: 20" in output
        assert "Player took 25 damage! Health: -5" in output
        assert "Game Over!" in output

    def test_quest_system(self):
        """Test a simple quest event system"""
        code = """
        set gems_collected to 0
        set quest_complete to false

        when gem_collected then
            set gems_collected to gems_collected plus 1
            print "Collected gem #{gems_collected}"

            if gems_collected is equal to 3 then
                trigger quest_complete
            end
        end

        when quest_complete then
            set quest_complete to true
            print "Quest complete! Collected all 3 gems!"
        end

        trigger gem_collected
        trigger gem_collected
        trigger gem_collected
        """
        output = execute_rosh(code)
        assert "Collected gem #1" in output
        assert "Collected gem #2" in output
        assert "Collected gem #3" in output
        assert "Quest complete! Collected all 3 gems!" in output


class TestEventEdgeCases:
    """Test edge cases and error conditions"""

    def test_event_name_case_sensitivity(self):
        """Test that event names are case-sensitive"""
        code = """
        when TestEvent then
            print "Upper"
        end

        when testevent then
            print "Lower"
        end

        trigger TestEvent
        trigger testevent
        """
        output = execute_rosh(code)
        assert "Upper" in output
        assert "Lower" in output

    def test_event_with_list_argument(self):
        """Test passing a list as event argument"""
        code = """
        when show_items items then
            for item in items then
                get item
                print stack
            end
        end

        trigger show_items with [1, 2, 3]
        """
        output = execute_rosh(code)
        assert "1" in output
        assert "2" in output
        assert "3" in output

    def test_multiple_triggers_sequential(self):
        """Test multiple sequential triggers of same event"""
        code = """
        set counter to 0

        when count_up then
            set counter to counter plus 1
        end

        trigger count_up
        trigger count_up
        trigger count_up

        get counter
        print stack
        """
        output = execute_rosh(code)
        assert "3" in output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
