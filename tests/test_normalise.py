"""Tests for rosh_lang.core.normalise."""

from __future__ import annotations

import pytest
from rosh_lang.core.normalise import fuzzy_color, normalise, normalise_programme
from rosh_lang.core.parser import parse_string
from rosh_lang.core.model import DestroyStatement, SetStatement


# ---------------------------------------------------------------------------
# fuzzy_color
# ---------------------------------------------------------------------------

class TestFuzzyColor:
    def test_direct_named_color(self):
        assert fuzzy_color("blue") == "blue"

    def test_color_with_qualifier(self):
        assert fuzzy_color("bright orange") == "orange"

    def test_simile_phrase(self):
        assert fuzzy_color("orange like autumn") == "orange"
        assert fuzzy_color("blue like the sky") == "blue"

    def test_semantic_noun(self):
        assert fuzzy_color("molten obsidian") == "black"
        assert fuzzy_color("cracked glacial permafrost") == "white"
        assert fuzzy_color("perfectly reflective mercury") == "silver"
        assert fuzzy_color("dark brown oak wood") == "brown"
        assert fuzzy_color("tangled ancient roots and moss") == "brown"

    def test_prose_sentence(self):
        assert fuzzy_color("pitch black thunderstorm darkness") == "black"
        assert fuzzy_color("blindingly bright white hot plasma") == "white"
        assert fuzzy_color("neon electric purple") == "purple"

    def test_rainbow_passthrough(self):
        assert fuzzy_color("rainbow") == "rainbow"

    def test_no_match_returns_none(self):
        assert fuzzy_color("xyzzy unknown stuff") is None
        assert fuzzy_color("") is None

    def test_ported_semantics(self):
        assert fuzzy_color("thunderstorm") == "gray"
        assert fuzzy_color("golden") == "gold"
        assert fuzzy_color("straw") == "yellow"


# ---------------------------------------------------------------------------
# normalise — destroy aliases
# ---------------------------------------------------------------------------

class TestDestroyAliases:
    def test_delete_becomes_destroy(self):
        assert normalise("delete campfire") == "destroy campfire"

    def test_remove_becomes_destroy(self):
        assert normalise("remove campfire") == "destroy campfire"

    def test_destroy_unchanged(self):
        assert normalise("destroy campfire") == "destroy campfire"


# ---------------------------------------------------------------------------
# normalise — colour verb
# ---------------------------------------------------------------------------

class TestColourVerb:
    def test_colour_simple(self):
        assert normalise("colour campfire red") == "set campfire.color to red"

    def test_color_us_spelling(self):
        assert normalise("color campfire blue") == "set campfire.color to blue"

    def test_paint_verb(self):
        assert normalise("paint rock gray") == "set rock.color to gray"

    def test_colour_prose_description(self):
        result = normalise("colour campfire orange like autumn")
        assert "set campfire.color to orange" in result
        assert "set campfire.color_desc to orange like autumn" in result

    def test_colour_semantic_noun(self):
        result = normalise("colour rock molten obsidian")
        assert "set rock.color to black" in result
        assert "set rock.color_desc to molten obsidian" in result

    def test_no_desc_preserved_when_exact_match(self):
        # "colour campfire red" -> just one line, no _desc needed
        result = normalise("colour campfire red")
        assert "color_desc" not in result


# ---------------------------------------------------------------------------
# normalise — change X colour to
# ---------------------------------------------------------------------------

class TestChangeColour:
    def test_change_colour_to(self):
        result = normalise("change campfire colour to red")
        assert "set campfire.color to red" in result

    def test_change_color_prose(self):
        result = normalise("change the rock color to dark obsidian darkness")
        assert "set rock.color to black" in result
        assert "color_desc" in result


# ---------------------------------------------------------------------------
# normalise — turn X
# ---------------------------------------------------------------------------

class TestTurnVerb:
    def test_turn_colour(self):
        result = normalise("turn campfire red")
        assert "set campfire.color to red" in result

    def test_turn_into_material(self):
        assert normalise("turn campfire into stone") == "set campfire.material to stone"

    def test_turn_into_multi_word_material(self):
        result = normalise("turn ball into dark wood")
        assert "set ball.material to wood" in result
        assert "set ball.material_desc to dark wood" in result

    def test_turn_invisible(self):
        assert normalise("turn campfire invisible") == "set campfire.opacity to 0"

    def test_turn_transparent(self):
        assert normalise("turn campfire transparent") == "set campfire.opacity to 0.3"

    def test_turn_visible(self):
        assert normalise("turn campfire visible") == "set campfire.opacity to 1"

    def test_turn_the_article_stripped(self):
        result = normalise("turn the campfire red")
        assert "set campfire.color to red" in result


# ---------------------------------------------------------------------------
# normalise — set X.color to <prose>
# ---------------------------------------------------------------------------

class TestSetColorProse:
    def test_simple_color_unchanged(self):
        # Exact named color: no expansion needed
        result = normalise("set campfire.color to red")
        assert result == "set campfire.color to red"

    def test_prose_color_expands(self):
        result = normalise("set campfire.color to molten obsidian")
        assert "set campfire.color to black" in result
        assert "set campfire.color_desc to molten obsidian" in result

    def test_material_prose_expands(self):
        result = normalise("set tree.material to cracked ancient bark wood")
        # Last word is the material noun; adjectives are stored in _desc
        assert "set tree.material to wood" in result
        assert "set tree.material_desc to cracked ancient bark wood" in result


# ---------------------------------------------------------------------------
# normalise — create aliases
# ---------------------------------------------------------------------------

class TestCreateAliases:
    def test_build_becomes_create(self):
        assert normalise("build campfire") == "create campfire"

    def test_put_becomes_create(self):
        assert normalise("put campfire") == "create campfire"

    def test_place_becomes_create(self):
        assert normalise("place campfire") == "create campfire"

    def test_strict_create_object_unchanged(self):
        # Already canonical — don't double-rewrite
        line = "create object campfire"
        assert normalise(line) == line


# ---------------------------------------------------------------------------
# normalise — passthrough cases
# ---------------------------------------------------------------------------

class TestPassthrough:
    def test_blank_line(self):
        assert normalise("") == ""

    def test_comment_unchanged(self):
        assert normalise("# this is a comment") == "# this is a comment"

    def test_strict_set_unchanged(self):
        assert normalise("set campfire.x to 5") == "set campfire.x to 5"

    def test_unknown_verb_unchanged(self):
        assert normalise("xyzzyfoo campfire") == "xyzzyfoo campfire"


# ---------------------------------------------------------------------------
# Integration: normalise flows through parse_string
# ---------------------------------------------------------------------------

class TestParserIntegration:
    def test_delete_parses_as_destroy(self):
        prog = parse_string("delete campfire", allow_extensions=True)
        stmts = [s for s in prog.statements if not hasattr(s, "text")]
        assert any(isinstance(s, DestroyStatement) for s in prog.statements)

    def test_colour_verb_parses_as_set(self):
        prog = parse_string("colour campfire red", allow_extensions=True)
        set_stmts = [s for s in prog.statements if isinstance(s, SetStatement)]
        assert any("color" in s.target for s in set_stmts)

    def test_prose_color_produces_two_set_statements(self):
        prog = parse_string("set campfire.color to molten obsidian", allow_extensions=True)
        set_stmts = [s for s in prog.statements if isinstance(s, SetStatement)]
        targets = [s.target for s in set_stmts]
        assert any("color" in t and "desc" not in t for t in targets)
        assert any("color_desc" in t for t in targets)
