"""
Tests for CLI functionality
"""
import unittest
import sys
import tempfile
from pathlib import Path

# Add parent directory to path to import rosh
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from rosh.cli import resolve_rosh_path


class TestMainRoshConvention(unittest.TestCase):
    """Test the main.rosh convention for directory resolution"""

    def test_directory_with_main_rosh(self):
        """If directory contains main.rosh, resolve to it"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create main.rosh in the directory
            main_path = Path(tmp_dir) / "main.rosh"
            main_path.write_text('print "hello"')

            # Should resolve to main.rosh
            result = resolve_rosh_path(tmp_dir)
            self.assertEqual(result, str(main_path))

    def test_directory_without_main_rosh(self):
        """If directory has no main.rosh, raise FileNotFoundError"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Empty directory
            with self.assertRaises(FileNotFoundError) as cm:
                resolve_rosh_path(tmp_dir)

            # Check error message is helpful
            self.assertIn("No main.rosh found", str(cm.exception))
            self.assertIn(tmp_dir, str(cm.exception))

    def test_file_path_unchanged(self):
        """Direct file paths should be returned unchanged"""
        # Even if file doesn't exist, resolve_rosh_path just returns it
        result = resolve_rosh_path("game.rosh")
        self.assertEqual(result, "game.rosh")

        result = resolve_rosh_path("/some/path/to/file.rosh")
        self.assertEqual(result, "/some/path/to/file.rosh")

    def test_nested_directory_with_main_rosh(self):
        """Nested directories should work"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create nested structure: tmp/my-game/main.rosh
            game_dir = Path(tmp_dir) / "my-game"
            game_dir.mkdir()
            main_path = game_dir / "main.rosh"
            main_path.write_text('print "nested game"')

            # Should resolve to nested main.rosh
            result = resolve_rosh_path(str(game_dir))
            self.assertEqual(result, str(main_path))

    def test_directory_with_other_rosh_files(self):
        """Only main.rosh is special - other .rosh files are ignored"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create a different rosh file but no main.rosh
            other_path = Path(tmp_dir) / "game.rosh"
            other_path.write_text('print "not main"')

            # Should still fail - only main.rosh counts
            with self.assertRaises(FileNotFoundError):
                resolve_rosh_path(tmp_dir)


if __name__ == '__main__':
    unittest.main()
