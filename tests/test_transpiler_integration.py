"""
Integration tests for transpiler CLI and end-to-end workflow
"""
import unittest
import tempfile
import subprocess
from pathlib import Path


class TestTranspilerCLI(unittest.TestCase):
    """Test transpiler CLI integration"""

    def test_build_command_basic(self):
        """Test 'rosh build' command creates output files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test Rosh file (coordinates are percentages now)
            rosh_file = Path(tmpdir) / "test.rosh"
            rosh_file.write_text("""
            create object goblin
                set x to 50
                set y to 50
            end

            print "Game created"
            """)

            output_dir = Path(tmpdir) / "dist"

            # Run build command
            result = subprocess.run(
                ["rosh", "build", str(rosh_file), "--target", "phaser",
                 "--output", str(output_dir)],
                capture_output=True,
                text=True
            )

            # Verify success
            self.assertEqual(result.returncode, 0)
            self.assertIn("✅ Build successful!", result.stderr)

            # Verify output files exist
            self.assertTrue((output_dir / "game.js").exists(), "game.js should exist")
            self.assertTrue((output_dir / "index.html").exists(), "index.html should exist")
            self.assertTrue((output_dir / "assets").exists(), "assets/ should exist")
            self.assertTrue((output_dir / "assets").is_dir(), "assets should be a directory")

    def test_build_command_with_content_verification(self):
        """Test build command generates correct JavaScript content"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test Rosh file (coordinates are percentages now)
            # 50% = 400px on 800 width, 50% = 300px on 600 height
            rosh_file = Path(tmpdir) / "test.rosh"
            rosh_file.write_text("""
            create object goblin
                set x to 50
                set y to 50
            end
            """)

            output_dir = Path(tmpdir) / "dist"

            # Build
            result = subprocess.run(
                ["rosh", "build", str(rosh_file), "--target", "phaser",
                 "--output", str(output_dir)],
                capture_output=True,
                text=True
            )

            self.assertEqual(result.returncode, 0)

            # Verify game.js content (50% = 400.0 x, 300.0 y on 800x600 canvas)
            js_content = (output_dir / "game.js").read_text()
            self.assertIn("this.goblin = this.add.rectangle(400.0, 300.0", js_content)
            self.assertIn("class GameScene extends Phaser.Scene", js_content)
            self.assertIn("const game = new Phaser.Game(config)", js_content)

    def test_javascript_syntax_validation(self):
        """Test that generated JavaScript has valid syntax (using Node.js)"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test Rosh file (coordinates are percentages now)
            rosh_file = Path(tmpdir) / "test.rosh"
            rosh_file.write_text("""
            create object goblin
                set x to 50
                set y to 50
            end
            """)

            output_dir = Path(tmpdir) / "dist"

            # Build
            subprocess.run(
                ["rosh", "build", str(rosh_file), "--target", "phaser",
                 "--output", str(output_dir)],
                check=True,
                capture_output=True
            )

            # Validate JS syntax with Node.js
            result = subprocess.run(
                ["node", "--check", str(output_dir / "game.js")],
                capture_output=True,
                text=True
            )

            # Should exit with 0 (valid syntax)
            self.assertEqual(result.returncode, 0,
                           f"Invalid JavaScript syntax: {result.stderr}")

    def test_build_nonexistent_file(self):
        """Test build command with nonexistent file"""
        result = subprocess.run(
            ["rosh", "build", "nonexistent.rosh", "--target", "phaser"],
            capture_output=True,
            text=True
        )

        # Should fail with error
        self.assertEqual(result.returncode, 1)
        self.assertIn("File not found", result.stderr)

    def test_build_with_while_loop(self):
        """Test build command handles while loops (now supported via IR emitter)"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create Rosh file with while loop (now supported by IR emitter)
            rosh_file = Path(tmpdir) / "test.rosh"
            rosh_file.write_text("""
            while true then
                print "test"
            end
            """)

            output_dir = Path(tmpdir) / "dist"

            # Build should succeed (IR emitter supports while loops)
            result = subprocess.run(
                ["rosh", "build", str(rosh_file), "--target", "phaser",
                 "--output", str(output_dir)],
                capture_output=True,
                text=True
            )

            self.assertEqual(result.returncode, 0)
            self.assertIn("✅ Build successful!", result.stderr)

    def test_html_template_content(self):
        """Test that HTML template includes Phaser CDN"""
        with tempfile.TemporaryDirectory() as tmpdir:
            rosh_file = Path(tmpdir) / "test.rosh"
            rosh_file.write_text("print \"test\"")

            output_dir = Path(tmpdir) / "dist"

            subprocess.run(
                ["rosh", "build", str(rosh_file), "--target", "phaser",
                 "--output", str(output_dir)],
                check=True,
                capture_output=True
            )

            # Check HTML content
            html_content = (output_dir / "index.html").read_text()
            self.assertIn("phaser", html_content.lower())
            self.assertIn("game.js", html_content)
            self.assertIn("<!DOCTYPE html>", html_content)


class TestTranspilerGrep(unittest.TestCase):
    """Test transpiler output with grep-based validation (as recommended in plan)"""

    def test_grep_validation_phaser_calls(self):
        """Test using grep to validate Phaser API calls in generated code"""
        with tempfile.TemporaryDirectory() as tmpdir:
            rosh_file = Path(tmpdir) / "test.rosh"
            rosh_file.write_text("""
            create object goblin
                set x to 100
                set y to 200
            end
            """)

            output_dir = Path(tmpdir) / "dist"

            # Build
            subprocess.run(
                ["rosh", "build", str(rosh_file), "--target", "phaser",
                 "--output", str(output_dir)],
                check=True,
                capture_output=True
            )

            game_js = output_dir / "game.js"

            # Test 1: Check for rectangle creation
            result = subprocess.run(
                ["grep", "-q", "this.goblin = this.add.rectangle", str(game_js)],
                capture_output=True
            )
            self.assertEqual(result.returncode, 0, "Should find Phaser rectangle call")

            # Test 2: Check for game config
            result = subprocess.run(
                ["grep", "-q", "const config = {", str(game_js)],
                capture_output=True
            )
            self.assertEqual(result.returncode, 0, "Should find Phaser config")


if __name__ == '__main__':
    unittest.main()
