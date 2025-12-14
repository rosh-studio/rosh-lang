"""
Unit tests for Phaser transpiler
"""
import unittest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from rosh.lexer import Lexer
from rosh.parser import Parser
from rosh.transpilers.phaser import PhaserTranspiler
from rosh.errors import RoshRuntimeError


class TestPhaserTranspiler(unittest.TestCase):
    """Test Phaser transpiler functionality"""

    def transpile(self, code: str) -> str:
        """Helper: Transpile Rosh code to Phaser JavaScript"""
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        program = parser.parse()

        transpiler = PhaserTranspiler()
        return transpiler.transpile(program)

    def test_empty_program(self):
        """Test transpiling empty program generates valid boilerplate"""
        js = self.transpile("")

        # Should still generate valid Phaser boilerplate
        self.assertIn("class GameScene extends Phaser.Scene", js)
        self.assertIn("constructor()", js)
        self.assertIn("create()", js)
        self.assertIn("const config = {", js)
        self.assertIn("const game = new Phaser.Game(config)", js)

    def test_simple_object(self):
        """Test transpiling a simple object"""
        code = """
        create object goblin
            set x to 100
            set y to 200
        end
        """

        js = self.transpile(code)

        # Verify Phaser rectangle call
        self.assertIn("this.goblin = this.add.rectangle(100, 200", js)
        self.assertIn("class GameScene extends Phaser.Scene", js)
        self.assertIn("// Goblin object", js)

    def test_multiple_objects(self):
        """Test transpiling multiple objects"""
        code = """
        create object goblin
            set x to 100
            set y to 200
        end

        create object chest
            set x to 400
            set y to 200
        end
        """

        js = self.transpile(code)

        self.assertIn("this.goblin = this.add.rectangle(100, 200", js)
        self.assertIn("this.chest = this.add.rectangle(400, 200", js)
        self.assertEqual(js.count("this.add.rectangle"), 2)

    def test_object_with_custom_dimensions(self):
        """Test object with custom width and height"""
        code = """
        create object chest
            set x to 400
            set y to 200
            set width to 80
            set height to 60
        end
        """

        js = self.transpile(code)

        self.assertIn("this.chest = this.add.rectangle(400, 200, 80, 60", js)

    def test_print_simple(self):
        """Test transpiling simple print statement"""
        code = """
        print "Hello, world!"
        """

        js = self.transpile(code)

        self.assertIn('console.log("Hello, world!")', js)
        self.assertIn("// Print statement", js)

    def test_print_with_interpolation(self):
        """Test transpiling print with string interpolation"""
        code = """
        create object goblin
            set x to 100
            set y to 200
        end

        print "Goblin at ({goblin.x}, {goblin.y})"
        """

        js = self.transpile(code)

        # Should use template literal
        self.assertIn("console.log(`Goblin at (${this.goblin.x}, ${this.goblin.y})`)", js)

    def test_color_rotation(self):
        """Test that multiple objects get different auto-assigned colors"""
        code = """
        create object obj1
        end
        create object obj2
        end
        create object obj3
        end
        """

        js = self.transpile(code)

        # Should have 3 different colors (green, blue, red by default)
        self.assertIn("0xff00", js)    # Green
        self.assertIn("0xff", js)       # Blue
        self.assertIn("0xff0000", js)   # Red

    def test_unsupported_feature_if(self):
        """Test that if statements raise clear error"""
        code = """
        if true then
            print "test"
        end
        """

        with self.assertRaises(RoshRuntimeError) as ctx:
            self.transpile(code)

        error_msg = str(ctx.exception)
        self.assertIn("does not support 'if/else statements'", error_msg)
        self.assertIn("Planned for v0.1.6", error_msg)
        self.assertIn("✅ create object", error_msg)

    def test_unsupported_feature_while(self):
        """Test that while loops raise error"""
        code = """
        while true then
            print "test"
        end
        """

        with self.assertRaises(RoshRuntimeError) as ctx:
            self.transpile(code)

        self.assertIn("does not support 'while loops'", str(ctx.exception))

    def test_event_handlers_supported(self):
        """Test that event handlers are now supported in v0.1.6"""
        code = """
        when start then
            print "game started"
        end
        """

        js = self.transpile(code)

        # Should generate event handler registration
        self.assertIn("registerEventHandler('start'", js)
        self.assertIn('console.log("game started")', js)
        self.assertIn("eventHandlers", js)

    def test_generated_code_structure(self):
        """Test overall structure of generated code"""
        code = """
        create object goblin
            set x to 100
            set y to 200
        end
        """

        js = self.transpile(code)

        # Check for proper structure
        lines = js.split('\n')

        # Should start with comments
        self.assertTrue(any("Auto-generated" in line for line in lines[:5]))

        # Should have proper indentation
        self.assertTrue(any("    constructor()" in line for line in lines))
        self.assertTrue(any("    create()" in line for line in lines))

    def test_phaser_config_values(self):
        """Test that Phaser config has correct values"""
        js = self.transpile("")

        self.assertIn("type: Phaser.AUTO", js)
        self.assertIn("width: 800", js)
        self.assertIn("height: 600", js)
        self.assertIn("backgroundColor: '#2d2d2d'", js)
        self.assertIn("scene: GameScene", js)


class TestPhaserTranspilerEdgeCases(unittest.TestCase):
    """Test edge cases and error handling"""

    def transpile(self, code: str) -> str:
        """Helper: Transpile Rosh code"""
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        program = parser.parse()

        transpiler = PhaserTranspiler()
        return transpiler.transpile(program)

    def test_object_no_properties(self):
        """Test object with no properties uses defaults"""
        code = """
        create object empty
        end
        """

        js = self.transpile(code)

        # Should use defaults (100, 100, 50, 50)
        self.assertIn("this.empty = this.add.rectangle(100, 100, 50, 50", js)

    def test_multiple_print_statements(self):
        """Test multiple print statements"""
        code = """
        print "Line 1"
        print "Line 2"
        print "Line 3"
        """

        js = self.transpile(code)

        self.assertEqual(js.count("console.log"), 3)
        self.assertIn('console.log("Line 1")', js)
        self.assertIn('console.log("Line 2")', js)
        self.assertIn('console.log("Line 3")', js)

    def test_mixed_objects_and_prints(self):
        """Test mix of objects and print statements"""
        code = """
        create object goblin
            set x to 100
        end

        print "Created goblin"

        create object chest
            set x to 200
        end

        print "Created chest"
        """

        js = self.transpile(code)

        self.assertIn("this.goblin", js)
        self.assertIn("this.chest", js)
        self.assertEqual(js.count("console.log"), 2)


class TestPhaserTranspilerV016(unittest.TestCase):
    """Test v0.1.6 features: inheritance, auto-controls, HUD, property mutations, triggers"""

    def transpile(self, code: str) -> str:
        """Helper: Transpile Rosh code"""
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        program = parser.parse()

        transpiler = PhaserTranspiler()
        return transpiler.transpile(program)

    def test_inheritance_basic(self):
        """Test object inheritance from player"""
        code = """
        create object hero from player
            set x to 200
        end
        """

        js = self.transpile(code)

        # Should have player defaults
        self.assertIn("this.hero.lives = 3", js)
        self.assertIn("this.hero.score = 0", js)
        self.assertIn("this.hero.speed = 5", js)

    def test_inheritance_override(self):
        """Test property override in inheritance"""
        code = """
        create object hero from player
            set lives to 5
        end
        """

        js = self.transpile(code)

        # Should override default lives
        self.assertIn("this.hero.lives = 5", js)
        # But keep other defaults
        self.assertIn("this.hero.score = 0", js)

    def test_player_auto_controls(self):
        """Test automatic keyboard controls for player objects"""
        code = """
        create object hero from player
            set x to 100
        end
        """

        js = self.transpile(code)

        # Should have keyboard setup
        self.assertIn("this.cursors = this.input.keyboard.createCursorKeys()", js)
        self.assertIn("this.keys = {", js)

        # Should auto-generate movement code
        self.assertIn("this.hero.x -= 5", js)
        self.assertIn("this.hero.x += 5", js)
        self.assertIn("this.hero.y -= 5", js)
        self.assertIn("this.hero.y += 5", js)

        # Should auto-generate fire handler
        self.assertIn("triggerEvent('fire'", js)

    def test_hud_display(self):
        """Test explicit HUD creation for lives/score"""
        code = """
        create object hero from player
            set lives to 5
            set score to 100
        end

        create object hud
            set target to hero
        end
        """

        js = self.transpile(code)

        # Should create HUD text objects
        self.assertIn("this.hud_lives", js)
        self.assertIn("this.hud_score", js)
        self.assertIn("'Lives: '", js)
        self.assertIn("'Score: '", js)

        # Should update HUD in update loop
        self.assertIn("setText('Lives: '", js)
        self.assertIn("setText('Score: '", js)

    def test_property_mutation(self):
        """Test property mutation in event handlers"""
        code = """
        create object player
            set x to 100
            set lives to 3
        end

        when fire then
            set player.x to player.x minus 5
            set player.lives to player.lives minus 1
        end
        """

        js = self.transpile(code)

        self.assertIn("this.player.x = (this.player.x - 5)", js)
        self.assertIn("this.player.lives = (this.player.lives - 1)", js)

    def test_trigger_without_params(self):
        """Test trigger statement without parameters"""
        code = """
        when start then
            trigger game_over
        end
        """

        js = self.transpile(code)

        self.assertIn("this.triggerEvent('game_over', null)", js)

    def test_trigger_with_params(self):
        """Test trigger statement with parameters"""
        code = """
        create object player
        end

        when start then
            trigger damage with 15
        end
        """

        js = self.transpile(code)

        self.assertIn("this.triggerEvent('damage', 15)", js)

    def test_special_property_fixed(self):
        """Test fixed property storage"""
        code = """
        create object chest
            set fixed to true
        end
        """

        js = self.transpile(code)

        self.assertIn("this.chest.fixed = true", js)

    def test_comprehensive_v016(self):
        """Test all v0.1.6 features together"""
        code = """
        create object hero from player
            set x to 400
            set lives to 3
        end

        create object hud
            set target to hero
        end

        when fire then
            set hero.score to hero.score plus 10
            trigger victory
        end
        """

        js = self.transpile(code)

        # Inheritance
        self.assertIn("this.hero.lives = 3", js)
        self.assertIn("this.hero.score = 0", js)

        # Auto-controls
        self.assertIn("this.cursors", js)
        self.assertIn("this.hero.x -= 5", js)

        # HUD
        self.assertIn("this.hud_lives", js)
        self.assertIn("this.hud_score", js)

        # Property mutation
        self.assertIn("this.hero.score = (this.hero.score + 10)", js)

        # Trigger
        self.assertIn("this.triggerEvent('victory', null)", js)

        # Event system
        self.assertIn("registerEventHandler", js)
        self.assertIn("triggerEvent", js)


class TestPhaserTranspilerV017(unittest.TestCase):
    """Test v0.1.7 features: sprite support with fallback"""

    def transpile(self, code: str):
        """Helper: Transpile Rosh code and return both JS and transpiler"""
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        program = parser.parse()

        transpiler = PhaserTranspiler()
        js = transpiler.transpile(program)
        return js, transpiler

    def test_sprite_preload_generation(self):
        """Test that sprite property generates preload() method"""
        code = """
        create object hero from player
            set x to 100
            set y to 100
            set sprite to "hero.png"
        end
        """

        js, transpiler = self.transpile(code)

        # Should generate preload() method
        self.assertIn("preload() {", js)
        self.assertIn("// Load sprite for hero", js)
        self.assertIn("this.load.image('hero_sprite', 'assets/hero.png')", js)

    def test_sprite_fallback_rendering(self):
        """Test that sprite rendering includes fallback to rectangle"""
        code = """
        create object hero
            set x to 100
            set y to 100
            set sprite to "hero.png"
        end
        """

        js, transpiler = self.transpile(code)

        # Should check if texture exists
        self.assertIn("if (this.textures.exists('hero_sprite'))", js)

        # Should render sprite if exists
        self.assertIn("this.hero = this.add.image(100, 100, 'hero_sprite')", js)

        # Should have fallback to rectangle
        self.assertIn("} else {", js)
        self.assertIn("console.warn('Sprite not found: hero.png, using colored rectangle')", js)
        self.assertIn("this.hero = this.add.rectangle(100, 100,", js)

    def test_sprite_assets_tracking(self):
        """Test that transpiler tracks sprite assets correctly"""
        code = """
        create object hero
            set sprite to "hero.png"
        end

        create object enemy
            set sprite to "enemy.png"
        end

        create object coin
            set sprite to "coin.png"
        end
        """

        js, transpiler = self.transpile(code)

        # Transpiler should track all sprite assets
        self.assertEqual(len(transpiler.sprite_assets), 3)
        self.assertEqual(transpiler.sprite_assets['hero'], 'hero.png')
        self.assertEqual(transpiler.sprite_assets['enemy'], 'enemy.png')
        self.assertEqual(transpiler.sprite_assets['coin'], 'coin.png')

    def test_mixed_sprites_and_rectangles(self):
        """Test mixing objects with sprites and without sprites"""
        code = """
        create object hero
            set sprite to "hero.png"
        end

        create object chest
            set x to 200
            set y to 200
        end
        """

        js, transpiler = self.transpile(code)

        # Hero should have sprite with fallback
        self.assertIn("this.textures.exists('hero_sprite')", js)
        self.assertIn("this.hero = this.add.image", js)

        # Chest should be plain rectangle (no sprite check)
        self.assertIn("this.chest = this.add.rectangle(200, 200", js)

        # Only hero sprite should be tracked
        self.assertEqual(len(transpiler.sprite_assets), 1)
        self.assertIn('hero', transpiler.sprite_assets)

    def test_no_sprites_no_preload(self):
        """Test that preload() is not generated when no sprites"""
        code = """
        create object chest
            set x to 100
            set y to 100
        end
        """

        js, transpiler = self.transpile(code)

        # Should NOT have preload method
        self.assertNotIn("preload() {", js)

        # Should have empty sprite_assets
        self.assertEqual(len(transpiler.sprite_assets), 0)

    def test_sprite_with_player_auto_controls(self):
        """Test that sprites work with player auto-controls"""
        code = """
        create object hero from player
            set x to 50%
            set y to 50%
            set sprite to "hero.png"
        end
        """

        js, transpiler = self.transpile(code)

        # Should have sprite preloading
        self.assertIn("preload() {", js)
        self.assertIn("this.load.image('hero_sprite'", js)

        # Should have sprite rendering with fallback
        self.assertIn("this.textures.exists('hero_sprite')", js)

        # Should have auto-controls
        self.assertIn("this.cursors = this.input.keyboard.createCursorKeys()", js)
        self.assertIn("this.hero.x -= 5", js)

    def test_multiple_sprites_preload(self):
        """Test that multiple sprites all get preloaded"""
        code = """
        create object hero
            set sprite to "hero.png"
        end

        create object enemy
            set sprite to "enemy.png"
        end

        create object coin
            set sprite to "coin.png"
        end
        """

        js, transpiler = self.transpile(code)

        # Should preload all three sprites
        self.assertIn("this.load.image('hero_sprite', 'assets/hero.png')", js)
        self.assertIn("this.load.image('enemy_sprite', 'assets/enemy.png')", js)
        self.assertIn("this.load.image('coin_sprite', 'assets/coin.png')", js)

        # All three should have fallback code
        self.assertEqual(js.count("this.textures.exists"), 3)
        self.assertEqual(js.count("console.warn('Sprite not found:"), 3)

    def test_sprite_literal_string_only(self):
        """Test that sprite property must be a literal string"""
        code = """
        create object hero
            set sprite to "hero.png"
        end
        """

        js, transpiler = self.transpile(code)

        # Should work with literal string
        self.assertIn("hero.png", js)
        self.assertEqual(transpiler.sprite_assets['hero'], 'hero.png')

        # Note: We can't test variable/expression rejection at transpiler level
        # because the parser would reject it first. This is documented limitation.


if __name__ == '__main__':
    unittest.main()
