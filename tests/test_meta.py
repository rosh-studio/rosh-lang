"""
Tests for _meta/ folder configuration loading
"""
import unittest
import sys
import tempfile
from pathlib import Path

# Add parent directory to path to import rosh
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from rosh.meta import load_meta, _deep_merge


class TestMetaLoader(unittest.TestCase):
    """Test the _meta/ folder configuration loading"""

    def test_no_meta_folder(self):
        """If no _meta/ folder, return empty dict"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = load_meta(tmp_dir)
            self.assertEqual(result, {})

    def test_project_toml_loading(self):
        """Load settings from _meta/project.toml"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create _meta/ folder with project.toml
            meta_dir = Path(tmp_dir) / "_meta"
            meta_dir.mkdir()
            (meta_dir / "project.toml").write_text('''
title = "My Game"
version = "1.0.0"

[canvas]
width = 1024
height = 768
''')
            result = load_meta(tmp_dir)
            self.assertEqual(result['title'], "My Game")
            self.assertEqual(result['version'], "1.0.0")
            self.assertEqual(result['canvas']['width'], 1024)
            self.assertEqual(result['canvas']['height'], 768)

    def test_target_specific_loading(self):
        """Load target-specific settings from _meta/{target}.toml"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create _meta/ folder with phaser.toml
            meta_dir = Path(tmp_dir) / "_meta"
            meta_dir.mkdir()
            (meta_dir / "phaser.toml").write_text('''
[physics]
engine = "arcade"
debug = true
''')
            result = load_meta(tmp_dir, target="phaser")
            self.assertEqual(result['physics']['engine'], "arcade")
            self.assertEqual(result['physics']['debug'], True)

    def test_target_overrides_project(self):
        """Target settings override project settings"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            meta_dir = Path(tmp_dir) / "_meta"
            meta_dir.mkdir()

            # Project says 800x600
            (meta_dir / "project.toml").write_text('''
[canvas]
width = 800
height = 600
background = "#000000"
''')

            # Phaser overrides to 1024x768
            (meta_dir / "phaser.toml").write_text('''
[canvas]
width = 1024
height = 768
''')

            result = load_meta(tmp_dir, target="phaser")
            # Width/height overridden, background preserved
            self.assertEqual(result['canvas']['width'], 1024)
            self.assertEqual(result['canvas']['height'], 768)
            self.assertEqual(result['canvas']['background'], "#000000")

    def test_missing_target_file(self):
        """Missing target file is fine - just use project settings"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            meta_dir = Path(tmp_dir) / "_meta"
            meta_dir.mkdir()
            (meta_dir / "project.toml").write_text('''
title = "Test"
''')
            # Request pygame but only project.toml exists
            result = load_meta(tmp_dir, target="pygame")
            self.assertEqual(result['title'], "Test")


class TestDeepMerge(unittest.TestCase):
    """Test deep merge helper function"""

    def test_simple_override(self):
        """Simple values are overridden"""
        base = {'a': 1, 'b': 2}
        override = {'b': 3, 'c': 4}
        _deep_merge(base, override)
        self.assertEqual(base, {'a': 1, 'b': 3, 'c': 4})

    def test_nested_merge(self):
        """Nested dicts are merged recursively"""
        base = {'canvas': {'width': 800, 'height': 600}}
        override = {'canvas': {'width': 1024}}
        _deep_merge(base, override)
        self.assertEqual(base['canvas']['width'], 1024)
        self.assertEqual(base['canvas']['height'], 600)

    def test_nested_add(self):
        """Can add new keys in nested dicts"""
        base = {'canvas': {'width': 800}}
        override = {'canvas': {'background': '#000'}}
        _deep_merge(base, override)
        self.assertEqual(base['canvas']['width'], 800)
        self.assertEqual(base['canvas']['background'], '#000')


if __name__ == '__main__':
    unittest.main()
