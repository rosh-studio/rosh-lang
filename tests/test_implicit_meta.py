"""
Tests for the implicit meta object behavior.

The meta object is a reserved implicit object that:
- Always exists (never needs to be created)
- Cannot be created by user code
- Cannot be deleted by user code
- Holds game state (meta.level, meta.phase, etc.)
- Supports nested properties (meta.game.title, meta.config.difficulty)
- Is included in save/load automatically
"""
import unittest
import sys
from pathlib import Path
from io import StringIO

# Add parent directory to path to import rosh
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from rosh.lexer import Lexer
from rosh.parser import Parser
from rosh.interpreter import Interpreter
from rosh.errors import RoshRuntimeError, RoshSyntaxError
from rosh.values import RoshObject


class TestImplicitMeta(unittest.TestCase):
    """Test the implicit meta object behavior"""

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

    def test_meta_exists_implicitly(self):
        """meta object exists without being created"""
        self.execute("set meta.level to 1")
        # Should not raise - meta exists implicitly
        meta = self.interp.global_env.get('meta')
        self.assertIsNotNone(meta)
        self.assertEqual(meta.get('level'), 1)

    def test_meta_set_property(self):
        """Can set properties on meta"""
        self.execute("set meta.phase to 1")
        self.execute("set meta.score to 100")
        meta = self.interp.global_env.get('meta')
        self.assertEqual(meta.get('phase'), 1)
        self.assertEqual(meta.get('score'), 100)

    def test_meta_nested_property(self):
        """Can set nested properties on meta (auto-creates intermediate objects)"""
        self.execute('set meta.game.title to "Space Shooter"')
        meta = self.interp.global_env.get('meta')
        game = meta.get('game')
        self.assertIsNotNone(game)
        self.assertIsInstance(game, RoshObject)
        self.assertEqual(game.get('title'), "Space Shooter")

    def test_cannot_create_meta(self):
        """Cannot create an object named 'meta' - it's reserved (caught at parse time)"""
        # meta is a reserved keyword, so the parser rejects it
        with self.assertRaises(RoshSyntaxError) as ctx:
            self.execute("create object meta\nend")
        self.assertIn("meta", str(ctx.exception).lower())

    def test_cannot_delete_meta(self):
        """Cannot delete the meta object - it's reserved (caught at parse time)"""
        self.execute("set meta.level to 1")  # Ensure it has properties
        # meta is a reserved keyword, so the parser rejects delete meta
        with self.assertRaises(RoshSyntaxError) as ctx:
            self.execute("delete meta")
        self.assertIn("meta", str(ctx.exception).lower())

    def test_meta_in_condition(self):
        """Can use meta properties in conditions"""
        self.execute("""
set meta.phase to 1
if meta.phase is equal to 1 then
    set meta.phase to 2
end
""")
        meta = self.interp.global_env.get('meta')
        self.assertEqual(meta.get('phase'), 2)

    def test_meta_never_has_visual_props(self):
        """meta object should not have visual properties set by default"""
        self.execute("set meta.level to 1")
        meta = self.interp.global_env.get('meta')
        # meta should not have visual properties like x, y, visible
        self.assertIsNone(meta.get('x'))
        self.assertIsNone(meta.get('y'))

    def test_multiple_nested_levels(self):
        """Can set deeply nested properties"""
        self.execute('set meta.config.game.difficulty to "hard"')
        meta = self.interp.global_env.get('meta')
        config = meta.get('config')
        self.assertIsNotNone(config)
        game = config.get('game')
        self.assertIsNotNone(game)
        self.assertEqual(game.get('difficulty'), "hard")


class TestMetaWithOtherObjects(unittest.TestCase):
    """Test meta interaction with regular objects"""

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

    def test_meta_separate_from_objects(self):
        """meta should exist alongside regular objects"""
        self.execute("""
create object player
    set x to 100
end
set meta.level to 1
""")
        # player should exist
        self.assertIsNotNone(self.interp.global_env.get('player'))
        # meta should exist
        self.assertIsNotNone(self.interp.global_env.get('meta'))

    def test_meta_and_object_with_same_property(self):
        """meta and objects can have same property names without conflict"""
        self.execute("""
create object state
    set level to 5
end
set meta.level to 1
""")
        state = self.interp.global_env.get('state')
        meta = self.interp.global_env.get('meta')
        self.assertEqual(state.get('level'), 5)
        self.assertEqual(meta.get('level'), 1)


if __name__ == '__main__':
    unittest.main()
