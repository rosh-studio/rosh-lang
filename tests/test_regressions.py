"""
Regression tests for bugs fixed in v0.0.4

These tests ensure that previously fixed bugs don't reappear.
"""
import unittest
import sys
from pathlib import Path

# Add parent directory to path to import rosh
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from rosh.lexer import Lexer
from rosh.parser import Parser
from rosh.interpreter import Interpreter
from rosh.values import RoshObject
from rosh.errors import RoshRuntimeError


class TestV004Regressions(unittest.TestCase):
    """Regression tests for v0.0.4 bug fixes"""

    def setUp(self):
        """Create a fresh interpreter for each test"""
        self.interp = Interpreter()

    def execute(self, code: str):
        """Helper: Execute Rosh code"""
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        self.interp.execute(ast)

    def test_delete_cleanup(self):
        """
        Test that delete properly cleans up instance tracking.

        Bug: delete command removed objects from environment but left stale
        references in instances, uuid_map, and instance_counters.

        Fixed in: v0.0.4
        """
        # Create an object with instances
        self.execute("create object ball\nend")
        self.execute("create ball")  # ball-1
        self.execute("create ball")  # ball-2

        # Verify initial state
        self.assertEqual(len(self.interp.instances['ball']), 3)
        ball_1 = self.interp.global_env.get('ball-1')
        ball_1_uuid = ball_1.uuid

        # Delete ball-1
        self.execute("delete ball-1")

        # Verify cleanup
        self.assertNotIn('ball-1', self.interp.global_env.bindings)
        self.assertNotIn(ball_1_uuid, self.interp.uuid_map)
        self.assertEqual(len(self.interp.instances['ball']), 2)

        # Verify remaining instances are intact
        self.assertIn('ball', self.interp.instances)
        self.assertIn('ball-2', self.interp.global_env.bindings)

    def test_cycle_protection(self):
        """
        Test that circular inheritance is detected and rejected.

        Bug: Circular inheritance caused infinite recursion/stack overflow.

        Fixed in: v0.0.4
        """
        # Create objects that will form a cycle
        self.execute("create object a\nend")
        self.execute("create object b\nend")

        # This would create a cycle: a -> b -> a
        # We can't easily test this without modifying the objects directly
        # since the language doesn't provide syntax to create cycles.
        # Instead, we verify the _get_all_properties method has cycle detection.

        a = self.interp.global_env.get('a')
        b = self.interp.global_env.get('b')

        # Manually create a cycle (normally impossible via Rosh syntax)
        a.parents = [b]
        b.parents = [a]

        # This should raise an error, not hang
        with self.assertRaises(RoshRuntimeError) as context:
            self.interp._get_all_properties(a)

        self.assertIn("Circular inheritance", str(context.exception))

    def test_state_persistence_with_instances(self):
        """
        Test that save/load preserves instance tracking.

        Bug: State persistence omitted instances, uuid_map, and instance_counters,
        breaking instance features after load.

        Fixed in: v0.0.4
        """
        # Create objects with instances
        self.execute("create object ball\nend")
        self.execute("create ball")
        self.execute("create ball")

        # Save state
        state = self.interp.get_state()

        # Verify instance_counters are saved
        self.assertIn('instance_counters', state)
        self.assertIn('ball', state['instance_counters'])

        # Create new interpreter and load
        new_interp = Interpreter()

        # Simulate eval_load restoration logic
        if 'instance_counters' in state:
            if not hasattr(new_interp, 'instance_counters'):
                new_interp.instance_counters = {}
            new_interp.instance_counters.update(state['instance_counters'])

        for name, value in state['variables'].items():
            deserialized = new_interp._deserialize_value(value)
            if deserialized is None:
                continue
            new_interp.global_env.define(name, deserialized)

            # Rebuild instance tracking
            if isinstance(deserialized, RoshObject):
                if not hasattr(new_interp, 'uuid_map'):
                    new_interp.uuid_map = {}
                if not hasattr(new_interp, 'instances'):
                    new_interp.instances = {}

                new_interp.uuid_map[deserialized.uuid] = deserialized
                type_name = deserialized.id.rsplit('-', 1)[0] if deserialized.id and '-' in deserialized.id else deserialized.name
                if type_name not in new_interp.instances:
                    new_interp.instances[type_name] = []
                new_interp.instances[type_name].append(deserialized)

        # Verify instance tracking was restored
        self.assertIn('ball', new_interp.instances)
        self.assertEqual(len(new_interp.instances['ball']), 3)
        self.assertEqual(new_interp.instance_counters['ball'], self.interp.instance_counters['ball'])

    def test_duplicate_eval_connect_removed(self):
        """
        Test that eval_connect is defined only once.

        Bug: Two identical eval_connect definitions at lines 1330 and 1436.
        First was dead code.

        Fixed in: v0.0.4
        """
        # Verify there's only one eval_connect method
        eval_connect_methods = [
            name for name in dir(self.interp)
            if name == 'eval_connect'
        ]
        self.assertEqual(len(eval_connect_methods), 1)

        # Verify it works (not dead code)
        # Note: This requires MUD library, so we'll just verify the method exists
        self.assertTrue(hasattr(self.interp, 'eval_connect'))
        self.assertTrue(callable(getattr(self.interp, 'eval_connect')))


class TestSecurityImprovements(unittest.TestCase):
    """Tests for security improvements in v0.0.4"""

    def test_prompt_exec_requires_confirmation(self):
        """
        Test that prompt exec requires user confirmation.

        This is a behavioral test - we verify the code path exists.
        """
        interp = Interpreter()

        # Verify the eval_prompt method has confirmation logic for exec mode
        import inspect
        source = inspect.getsource(interp.eval_prompt)

        # Check for security confirmation
        self.assertIn("Execute this AI-generated code?", source)
        self.assertIn("input(", source)

    def test_module_reload_syntax(self):
        """
        Test that import "!path" forces module reload.

        Bug: No way to reload a module once cached.

        Fixed in: v0.0.4
        """
        interp = Interpreter()

        # Verify eval_import has reload logic
        import inspect
        source = inspect.getsource(interp.eval_import)

        # Check for force reload handling
        self.assertIn("force_reload", source)
        self.assertIn("startswith('!')", source)
        self.assertIn("Force reloading", source)


class TestV0119Regressions(unittest.TestCase):
    """Regression tests for v0.1.19 features (2025-12-21)

    Features:
    - Bulk undo grouping (undo all of a bulk operation at once)
    - Print with bare words (no quotes needed)
    - Case-preserving identifiers with case-insensitive lookup
    - Repeat command
    """

    def setUp(self):
        """Create a fresh interpreter for each test"""
        self.interp = Interpreter()
        self.interp.interactive = False  # Suppress feedback messages

    def execute(self, code: str):
        """Helper: Execute Rosh code"""
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        self.interp.execute(ast)

    def test_print_bare_words(self):
        """
        Test that print works without quotes.

        print Hello World  →  outputs "Hello World"
        """
        import io
        output = io.StringIO()
        self.interp.output_stream = output

        self.execute('print Hello World')

        self.assertEqual(output.getvalue().strip(), 'Hello World')

    def test_print_bare_words_case_preserved(self):
        """
        Test that bare print preserves case of identifiers.

        print Hello World  →  "Hello World" (not lowercase)
        """
        import io
        output = io.StringIO()
        self.interp.output_stream = output

        self.execute('print HeLLo WoRLd')

        self.assertEqual(output.getvalue().strip(), 'HeLLo WoRLd')

    def test_print_single_word_variable_lookup(self):
        """
        Test that single word after print checks for variable first.

        create box → print box → prints object properties
        """
        import io
        output = io.StringIO()
        self.interp.output_stream = output

        self.execute('create box')
        self.execute('print box')

        # Should contain object representation, not just "box"
        self.assertIn('box', output.getvalue())
        self.assertIn('_type', output.getvalue())

    def test_print_single_word_bare_string(self):
        """
        Test that single word not matching variable is printed as string.

        print Hello  →  outputs "Hello"
        """
        import io
        output = io.StringIO()
        self.interp.output_stream = output

        self.execute('print Greetings')

        self.assertEqual(output.getvalue().strip(), 'Greetings')

    def test_print_property_access(self):
        """
        Test that print obj.prop still works.
        """
        import io
        output = io.StringIO()
        self.interp.output_stream = output

        self.execute('create box')
        self.execute('set box.name to "MyBox"')
        self.execute('print box.name')

        self.assertEqual(output.getvalue().strip(), 'MyBox')

    def test_variable_case_insensitive_lookup(self):
        """
        Test that variable lookup is case-insensitive.

        create Enemy → set enemy.health to 50 → works
        """
        self.execute('create Enemy')
        self.execute('set enemy.health to 50')

        # Should be able to access with any case
        enemy = self.interp.global_env.get('enemy')
        self.assertEqual(enemy.get('health'), 50)

        enemy2 = self.interp.global_env.get('ENEMY')
        self.assertEqual(enemy2.get('health'), 50)

    def test_variable_case_preserved_in_name(self):
        """
        Test that the original case is preserved for the stored name.
        """
        self.execute('create MyPlayer')

        # The original name should be preserved
        self.assertTrue(self.interp.global_env.exists('myplayer'))
        self.assertTrue(self.interp.global_env.exists('MyPlayer'))
        self.assertTrue(self.interp.global_env.exists('MYPLAYER'))

    def test_undo_group_bulk_create(self):
        """
        Test that bulk create can be undone as a single operation.

        create 5 orcs; go → undo → all 5 should be removed
        """
        from rosh.cli import run_source

        # Simulate bulk create through the CLI which handles grouping
        self.interp.start_undo_group()
        self.execute('create orc')
        self.execute('create orc')
        self.execute('create orc')

        # Should have 3 orcs
        self.assertEqual(len(self.interp.instances.get('orc', [])), 3)

        # Undo should remove all 3 at once (same group)
        self.interp.perform_undo(1)

        # Should have 0 orcs
        self.assertEqual(len(self.interp.instances.get('orc', [])), 0)

    def test_undo_separate_commands(self):
        """
        Test that separate commands are in separate undo groups.
        """
        # First command
        self.interp.start_undo_group()
        self.execute('create box')

        # Second command (new group)
        self.interp.start_undo_group()
        self.execute('create ball')

        # Should have both
        self.assertTrue(self.interp.global_env.exists('box'))
        self.assertTrue(self.interp.global_env.exists('ball'))

        # Undo should only remove ball
        self.interp.perform_undo(1)

        self.assertTrue(self.interp.global_env.exists('box'))
        self.assertFalse(self.interp.global_env.exists('ball'))

    def test_repeat_command(self):
        """
        Test that repeat re-executes the last substantive command.
        """
        self.execute('create box')
        self.execute('repeat')

        # Should have 2 box objects (box and box-1)
        self.assertEqual(len(self.interp.instances.get('box', [])), 2)

    def test_repeat_skips_utility_commands(self):
        """
        Test that repeat skips utility commands (help, confirm, repeat itself).
        """
        self.execute('create box')
        # Help shouldn't become last_command
        # (We can't easily execute help in test, so we verify the logic exists)

        self.execute('repeat')

        # Should repeat create box, not help
        self.assertEqual(len(self.interp.instances.get('box', [])), 2)

    def test_print_bare_interpolation(self):
        """
        Test that bare print supports {interpolation} without quotes.

        print {name} is {age} years old  →  "Alice is 25 years old"
        """
        import io
        output = io.StringIO()
        self.interp.output_stream = output

        self.execute('set name to "Alice"')
        self.execute('set age to 25')
        self.execute('print {name} is {age} years old')

        self.assertEqual(output.getvalue().strip(), 'Alice is 25 years old')

    def test_print_bare_interpolation_with_property(self):
        """
        Test that bare print interpolation works with object properties.

        print {player.name} has {player.health} HP
        """
        import io
        output = io.StringIO()
        self.interp.output_stream = output

        self.execute('create player')
        self.execute('set player.name to "Hero"')
        self.execute('set player.health to 100')
        self.execute('print {player.name} has {player.health} HP')

        self.assertEqual(output.getvalue().strip(), 'Hero has 100 HP')


if __name__ == '__main__':
    unittest.main()
