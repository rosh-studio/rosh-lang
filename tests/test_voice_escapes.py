"""
Tests for voice escapes in Rosh voice normalization.

Voice escapes allow users to speak syntax characters:
- "dot" → . (joins adjacent words)
- "underscore" → _ (joins adjacent words)
- "equals" → = (with spaces)
- "plus" → + (with spaces)

Voice escapes are ALWAYS applied (useful for demos).
Autocorrections (typos, spellings) are only applied when is_voice=True.
"""
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from rosh.voice import apply_voice_escapes, normalize_input


class TestVoiceEscapes(unittest.TestCase):
    """Test voice escape processing."""

    def test_dot_escape_joins_words(self):
        """'player dot speed' becomes 'player.speed'."""
        result, msgs = apply_voice_escapes("player dot speed")
        self.assertEqual(result, "player.speed")
        self.assertTrue(any("dot" in m for m in msgs))

    def test_underscore_escape_joins_words(self):
        """'player underscore id' becomes 'player_id'."""
        result, msgs = apply_voice_escapes("player underscore id")
        self.assertEqual(result, "player_id")
        self.assertTrue(any("underscore" in m for m in msgs))

    def test_equals_escape_preserves_spacing(self):
        """'x equals 10' becomes 'x = 10'."""
        result, msgs = apply_voice_escapes("x equals 10")
        self.assertEqual(result, "x = 10")
        self.assertTrue(any("equals" in m for m in msgs))

    def test_plus_escape_preserves_spacing(self):
        """'x plus 5' becomes 'x + 5'."""
        result, msgs = apply_voice_escapes("x plus 5")
        self.assertEqual(result, "x + 5")
        self.assertTrue(any("plus" in m for m in msgs))

    def test_plus_in_expression(self):
        """'score plus 10' works in expressions."""
        result, msgs = apply_voice_escapes("set score to score plus 10")
        self.assertEqual(result, "set score to score + 10")

    def test_full_set_command_with_dot(self):
        """'set player dot speed to 10' works correctly."""
        result, msgs = apply_voice_escapes("set player dot speed to 10")
        self.assertEqual(result, "set player.speed to 10")

    def test_full_set_command_with_underscore(self):
        """'set player underscore id to 42' works correctly."""
        result, msgs = apply_voice_escapes("set player underscore id to 42")
        self.assertEqual(result, "set player_id to 42")

    def test_combined_escapes(self):
        """'player dot stats underscore health' becomes 'player.stats_health'."""
        result, msgs = apply_voice_escapes("player dot stats underscore health")
        self.assertEqual(result, "player.stats_health")
        self.assertEqual(len(msgs), 2)  # Two escapes

    def test_escapes_case_insensitive(self):
        """Escapes work regardless of case."""
        result, _ = apply_voice_escapes("player DOT speed")
        self.assertEqual(result, "player.speed")

        result, _ = apply_voice_escapes("player UNDERSCORE id")
        self.assertEqual(result, "player_id")

    def test_no_escapes_passthrough(self):
        """Commands without escapes pass through unchanged."""
        result, msgs = apply_voice_escapes("set x to 10")
        self.assertEqual(result, "set x to 10")
        self.assertEqual(len(msgs), 0)

    def test_dot_at_start(self):
        """Dot at start of command."""
        result, msgs = apply_voice_escapes("dot speed to 10")
        # Should produce ".speed to 10" (no previous word to join)
        self.assertEqual(result, ".speed to 10")

    def test_dot_at_end(self):
        """Dot at end of command."""
        result, msgs = apply_voice_escapes("player dot")
        # Should produce "player." (no next word to join)
        self.assertEqual(result, "player.")

    def test_multiple_dots(self):
        """Multiple dots in chain."""
        result, msgs = apply_voice_escapes("player dot stats dot health")
        self.assertEqual(result, "player.stats.health")


class TestVoiceNormalizationPipeline(unittest.TestCase):
    """Test full voice normalization pipeline with escapes."""

    def test_escapes_applied_before_corrections(self):
        """Voice escapes run before typo corrections (voice mode)."""
        result, msgs = normalize_input("creat player dot speed to 10", is_voice=True)
        # Should correct 'creat' to 'create' AND process 'dot'
        self.assertIn("create", result)
        self.assertIn("player.speed", result)

    def test_escapes_without_voice_mode(self):
        """Voice escapes apply even without is_voice=True."""
        result, msgs = normalize_input("player dot speed to 10")
        # Escapes always apply
        self.assertIn("player.speed", result)

    def test_typos_not_corrected_without_voice_mode(self):
        """Typo corrections only apply with is_voice=True."""
        result, msgs = normalize_input("creat box")
        # Without is_voice=True, typos are NOT corrected
        self.assertIn("creat", result)  # Typo preserved

    def test_escapes_with_politeness_stripping(self):
        """Escapes work with politeness stripping (voice mode)."""
        result, msgs = normalize_input("please set player dot health to 100", is_voice=True)
        # Should strip 'please' AND process escape
        self.assertEqual(result, "set player.health to 100")

    def test_escapes_with_article_stripping(self):
        """Escapes work with article stripping (voice mode)."""
        result, msgs = normalize_input("create a player dot stats", is_voice=True)
        # Should strip 'a' AND process escape
        self.assertEqual(result, "create player.stats")

    def test_escapes_with_implied_to(self):
        """Escapes work with implied 'to' (always on)."""
        # Without 'to', it should be added (implied 'to' is always on)
        result, msgs = normalize_input("set player dot speed 10")
        self.assertEqual(result, "set player.speed to 10")

    def test_plus_escape_in_pipeline(self):
        """Plus escape works in full pipeline."""
        result, msgs = normalize_input("set score to score plus 10")
        self.assertEqual(result, "set score to score + 10")


if __name__ == '__main__':
    unittest.main()
