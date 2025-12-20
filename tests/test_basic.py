"""
Basic functionality tests for Rosh core features
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


class TestBasicFeatures(unittest.TestCase):
    """Test core Rosh language features"""

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

    def test_create_number(self):
        """Test creating a number variable"""
        self.execute("set x to 42")
        self.assertEqual(self.interp.global_env.get('x'), 42)

    def test_create_string(self):
        """Test creating a string variable"""
        self.execute('set name to "Hero"')
        self.assertEqual(self.interp.global_env.get('name'), "Hero")

    def test_create_object(self):
        """Test creating an object"""
        self.execute("""
        create object player
            set name to "Hero"
            set health to 100
        end
        """)
        player = self.interp.global_env.get('player')
        self.assertIsInstance(player, RoshObject)
        self.assertEqual(player.get('name'), "Hero")
        self.assertEqual(player.get('health'), 100)

    def test_set_variable(self):
        """Test modifying a variable"""
        self.execute("set x to 10")
        self.execute("set x to 20")
        self.assertEqual(self.interp.global_env.get('x'), 20)

    def test_stack_operations(self):
        """Test basic stack operations"""
        self.execute("set a to 5")
        self.execute("set b to 3")
        self.execute("get a")
        self.execute("get b")
        self.execute("add")
        self.assertEqual(len(self.interp.data_stack), 1)
        self.assertEqual(self.interp.data_stack[0], 8)

    def test_if_statement(self):
        """Test conditional execution"""
        self.execute("""
        set x to 10
        set result to 0
        if x is above 5 then
            set result to 1
        end
        """)
        self.assertEqual(self.interp.global_env.get('result'), 1)

    def test_inheritance(self):
        """Test object inheritance"""
        self.execute("""
        create object warrior
            set class to "Warrior"
            set health to 100
        end
        clone warrior as player
        set player.name to "Hero"
        """)
        player = self.interp.global_env.get('player')
        self.assertEqual(player.get('class'), "Warrior")
        self.assertEqual(player.get('health'), 100)
        self.assertEqual(player.get('name'), "Hero")


class TestUUIDSystem(unittest.TestCase):
    """Test UUID-based instance tracking (v0.0.3+)"""

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

    def test_uuid_generation(self):
        """Test that objects get UUIDs"""
        self.execute("create object player\nend")
        player = self.interp.global_env.get('player')
        self.assertIsNotNone(player.uuid)
        self.assertTrue(len(player.uuid) > 0)

    def test_anonymous_instances(self):
        """Test anonymous instance creation with auto-numbering"""
        # First need to create a template
        self.execute("create object ball\nend")

        # Now create anonymous instances
        self.execute("create ball")
        self.execute("create ball")

        # Check instance tracking
        self.assertIn('ball', self.interp.instances)
        # Should have 3 instances: template + 2 anonymous
        self.assertEqual(len(self.interp.instances['ball']), 3)

    def test_get_instance_by_index(self):
        """Test getting specific instance by index"""
        self.execute("create object thing\nend")
        self.execute("create thing")
        self.execute("create thing")
        self.execute("get thing 2")

        # Should have one item on stack (thing-1)
        # 1-indexed for users: template is #1, thing-1 is #2, thing-2 is #3
        self.assertEqual(len(self.interp.data_stack), 1)
        obj = self.interp.data_stack[0]
        self.assertEqual(obj.id, "thing-1")  # get thing 2 = second instance (thing-1)

    def test_instance_tracking_persistence(self):
        """Test that instance tracking survives save/load"""
        self.execute("create object ball\nend")
        self.execute("create ball")
        self.execute("create ball")

        # Save state
        state = self.interp.get_state()

        # Create new interpreter and load
        new_interp = Interpreter()
        new_interp.global_env.bindings.update({
            name: new_interp._deserialize_value(val)
            for name, val in state['variables'].items()
        })

        # Restore instance counters
        if 'instance_counters' in state:
            new_interp.instance_counters = state['instance_counters'].copy()

        # Rebuild instance tracking
        for name, obj in new_interp.global_env.bindings.items():
            if isinstance(obj, RoshObject):
                if not hasattr(new_interp, 'uuid_map'):
                    new_interp.uuid_map = {}
                if not hasattr(new_interp, 'instances'):
                    new_interp.instances = {}

                new_interp.uuid_map[obj.uuid] = obj
                type_name = obj.id.rsplit('-', 1)[0] if obj.id and '-' in obj.id else obj.name
                if type_name not in new_interp.instances:
                    new_interp.instances[type_name] = []
                new_interp.instances[type_name].append(obj)

        # Verify instance tracking was restored
        self.assertIn('ball', new_interp.instances)
        self.assertEqual(len(new_interp.instances['ball']), 3)


class TestCaseInsensitivity(unittest.TestCase):
    """Test that Rosh is case-insensitive for keywords and identifiers"""

    def setUp(self):
        self.interp = Interpreter()

    def execute(self, code: str):
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        self.interp.execute(ast)

    def test_keywords_any_case(self):
        """Keywords work in any case"""
        # All these should be equivalent
        self.execute("SET x TO 42")
        self.assertEqual(self.interp.global_env.get('x'), 42)

        self.execute("Set y To 100")
        self.assertEqual(self.interp.global_env.get('y'), 100)

    def test_object_names_normalized(self):
        """Object names are normalized to lowercase"""
        self.execute("create object Hero\nend")
        # Should be accessible as lowercase
        hero = self.interp.global_env.get('hero')
        self.assertIsNotNone(hero)

    def test_object_access_any_case(self):
        """Can access objects regardless of case"""
        self.execute("create object Player\n    set health to 100\nend")
        self.execute("set PLAYER.health to 50")
        player = self.interp.global_env.get('player')
        self.assertEqual(player.get('health'), 50)

    def test_string_literals_preserve_case(self):
        """String literals should preserve their original case"""
        self.execute('set name to "Hello World"')
        self.assertEqual(self.interp.global_env.get('name'), "Hello World")

    def test_mixed_case_create_and_access(self):
        """Create with one case, access with another"""
        self.execute("CREATE OBJECT enemy\n    SET health TO 50\nEND")
        self.execute("set Enemy.health to 25")
        enemy = self.interp.global_env.get('enemy')
        self.assertEqual(enemy.get('health'), 25)


if __name__ == '__main__':
    unittest.main()
