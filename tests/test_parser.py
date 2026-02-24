"""Tests for the Rosh programme parser.

Tests are organized from simple to complex, following the scaffold path:
  1. print (hello world)
  2. create (objects)
  3. set (properties)
  4. when/end (events)
  5. comments and blanks
  6. backward compatibility with v0.1/v0.2 syntax
"""

from __future__ import annotations

from pathlib import Path

import pytest

from rosh_lang.model import (
    BlankStatement,
    CommentStatement,
    CreateStatement,
    EndStatement,
    PrintStatement,
    Programme,
    SetStatement,
    WhenStatement,
)
from rosh_lang.parser import ParseError, parse_file, parse_string


# ── print ──────────────────────────────────────────────────────


class TestPrint:
    def test_print_quoted(self) -> None:
        prog = parse_string('print "hello world"')
        assert len(prog.statements) == 1
        stmt = prog.statements[0]
        assert isinstance(stmt, PrintStatement)
        assert stmt.text == "hello world"

    def test_print_single_quoted(self) -> None:
        prog = parse_string("print 'hello world'")
        stmt = prog.statements[0]
        assert isinstance(stmt, PrintStatement)
        assert stmt.text == "hello world"

    def test_print_unquoted(self) -> None:
        """Speech-friendly: print hello world (no quotes needed)."""
        prog = parse_string("print hello world")
        stmt = prog.statements[0]
        assert isinstance(stmt, PrintStatement)
        assert stmt.text == "hello world"

    def test_print_with_interpolation(self) -> None:
        """String interpolation: print "Score: {score}" """
        prog = parse_string('print "Score: {score}"')
        stmt = prog.statements[0]
        assert isinstance(stmt, PrintStatement)
        assert stmt.text == "Score: {score}"

    def test_print_with_dot_interpolation(self) -> None:
        """v0.1/v0.2 style: print "Health: {player.health}" """
        prog = parse_string('print "Health: {player.health}"')
        stmt = prog.statements[0]
        assert isinstance(stmt, PrintStatement)
        assert stmt.text == "Health: {player.health}"

    def test_print_empty_raises(self) -> None:
        with pytest.raises(ParseError, match="print requires text"):
            parse_string("print")

    def test_print_case_insensitive(self) -> None:
        prog = parse_string('PRINT "hello"')
        assert isinstance(prog.statements[0], PrintStatement)

    def test_print_line_number(self) -> None:
        prog = parse_string('\nprint "hello"')
        stmt = prog.statements[1]
        assert isinstance(stmt, PrintStatement)
        assert stmt.line == 2


# ── create ─────────────────────────────────────────────────────


class TestCreate:
    def test_create_object(self) -> None:
        prog = parse_string("create object player")
        stmt = prog.statements[0]
        assert isinstance(stmt, CreateStatement)
        assert stmt.kind == "object"
        assert stmt.name == "player"
        assert stmt.count == 1
        assert stmt.parent == ""

    def test_create_number(self) -> None:
        prog = parse_string("create number score as 0")
        stmt = prog.statements[0]
        assert isinstance(stmt, CreateStatement)
        assert stmt.kind == "number"
        assert stmt.name == "score"

    def test_create_string(self) -> None:
        prog = parse_string("create string name")
        stmt = prog.statements[0]
        assert isinstance(stmt, CreateStatement)
        assert stmt.kind == "string"
        assert stmt.name == "name"

    def test_create_with_parent(self) -> None:
        """v0.1 inheritance: create object hero from player"""
        prog = parse_string("create object hero from player")
        stmt = prog.statements[0]
        assert isinstance(stmt, CreateStatement)
        assert stmt.name == "hero"
        assert stmt.parent == "player"

    def test_create_multiple(self) -> None:
        """v0.2 pool: create 5 objects as bullets"""
        prog = parse_string("create 5 objects as bullets")
        stmt = prog.statements[0]
        assert isinstance(stmt, CreateStatement)
        assert stmt.count == 5
        assert stmt.kind == "object"
        assert stmt.name == "bullets"

    def test_create_missing_name(self) -> None:
        with pytest.raises(ParseError, match="create requires"):
            parse_string("create object")

    def test_create_too_short(self) -> None:
        with pytest.raises(ParseError):
            parse_string("create")


# ── set ────────────────────────────────────────────────────────


class TestSet:
    def test_set_with_to(self) -> None:
        prog = parse_string("set x to 100")
        stmt = prog.statements[0]
        assert isinstance(stmt, SetStatement)
        assert stmt.target == "x"
        assert stmt.value == "100"

    def test_set_property_with_to(self) -> None:
        """set player health to 75"""
        prog = parse_string("set player health to 75")
        stmt = prog.statements[0]
        assert isinstance(stmt, SetStatement)
        assert stmt.target == "player.health"
        assert stmt.value == "75"

    def test_set_dot_notation(self) -> None:
        """set player.health to 75"""
        prog = parse_string("set player.health to 75")
        stmt = prog.statements[0]
        assert isinstance(stmt, SetStatement)
        assert stmt.target == "player.health"
        assert stmt.value == "75"

    def test_set_without_to(self) -> None:
        """v0.2 shorthand: set x 100"""
        prog = parse_string("set x 100")
        stmt = prog.statements[0]
        assert isinstance(stmt, SetStatement)
        assert stmt.target == "x"
        assert stmt.value == "100"

    def test_set_string_value(self) -> None:
        prog = parse_string('set name to "Hero"')
        stmt = prog.statements[0]
        assert isinstance(stmt, SetStatement)
        assert stmt.target == "name"
        assert stmt.value == '"Hero"'

    def test_set_expression_value(self) -> None:
        """v0.1 style: set score_text.text to "Score: {state.score}" """
        prog = parse_string('set score_text.text to "Score: {state.score}"')
        stmt = prog.statements[0]
        assert isinstance(stmt, SetStatement)
        assert stmt.target == "score_text.text"
        assert stmt.value == '"Score: {state.score}"'

    def test_set_deep_property(self) -> None:
        """set player position x to 100 → player.position.x"""
        prog = parse_string("set player position x to 100")
        stmt = prog.statements[0]
        assert isinstance(stmt, SetStatement)
        assert stmt.target == "player.position.x"
        assert stmt.value == "100"

    def test_set_empty_raises(self) -> None:
        with pytest.raises(ParseError, match="set requires"):
            parse_string("set")

    def test_set_no_value_raises(self) -> None:
        with pytest.raises(ParseError, match="set requires"):
            parse_string("set x")


# ── when / end ─────────────────────────────────────────────────


class TestWhen:
    def test_when_simple(self) -> None:
        prog = parse_string("when update then")
        stmt = prog.statements[0]
        assert isinstance(stmt, WhenStatement)
        assert stmt.event == "update"
        assert stmt.args == []

    def test_when_without_then(self) -> None:
        """'then' is optional for speech-friendliness."""
        prog = parse_string("when start")
        stmt = prog.statements[0]
        assert isinstance(stmt, WhenStatement)
        assert stmt.event == "start"

    def test_when_collision(self) -> None:
        """when collision hero enemy then"""
        prog = parse_string("when collision hero enemy then")
        stmt = prog.statements[0]
        assert isinstance(stmt, WhenStatement)
        assert stmt.event == "collision"
        assert stmt.args == ["hero", "enemy"]

    def test_when_key_event(self) -> None:
        prog = parse_string("when space_pressed then")
        stmt = prog.statements[0]
        assert isinstance(stmt, WhenStatement)
        assert stmt.event == "space_pressed"

    def test_when_empty_raises(self) -> None:
        with pytest.raises(ParseError, match="when requires"):
            parse_string("when then")

    def test_end(self) -> None:
        prog = parse_string("end")
        assert isinstance(prog.statements[0], EndStatement)


# ── Comments and blanks ────────────────────────────────────────


class TestCommentsAndBlanks:
    def test_comment(self) -> None:
        prog = parse_string("# this is a comment")
        stmt = prog.statements[0]
        assert isinstance(stmt, CommentStatement)
        assert stmt.text == "this is a comment"

    def test_blank_line(self) -> None:
        prog = parse_string("\n")
        # First line is blank
        assert isinstance(prog.statements[0], BlankStatement)

    def test_indented_blank(self) -> None:
        prog = parse_string("   ")
        assert isinstance(prog.statements[0], BlankStatement)

    def test_indented_code(self) -> None:
        """Indentation is cosmetic (v0.2 rule)."""
        prog = parse_string('    set x to 100')
        stmt = prog.statements[0]
        assert isinstance(stmt, SetStatement)
        assert stmt.target == "x"


# ── Multi-line programmes ─────────────────────────────────────


class TestMultiLine:
    def test_hello_world(self) -> None:
        prog = parse_string('print "Hello, World!"')
        assert len(prog.statements) == 1
        assert isinstance(prog.statements[0], PrintStatement)
        assert prog.statements[0].text == "Hello, World!"

    def test_simple_game(self) -> None:
        """Parse the equivalent of rosh-lang/examples/basics/hello.rosh"""
        prog = parse_string(
            '# Simple hello world program\n'
            '\n'
            'print "Hello, World!"\n'
        )
        assert len(prog.statements) == 3
        assert isinstance(prog.statements[0], CommentStatement)
        assert isinstance(prog.statements[1], BlankStatement)
        assert isinstance(prog.statements[2], PrintStatement)

    def test_create_with_properties(self) -> None:
        """Parse an object creation with set statements."""
        code = (
            "create object player\n"
            "    set x to 50\n"
            "    set y to 90\n"
            "    set health to 100\n"
            "end\n"
        )
        prog = parse_string(code)
        assert len(prog.statements) == 5
        assert isinstance(prog.statements[0], CreateStatement)
        assert isinstance(prog.statements[1], SetStatement)
        assert isinstance(prog.statements[2], SetStatement)
        assert isinstance(prog.statements[3], SetStatement)
        assert isinstance(prog.statements[4], EndStatement)

    def test_event_handler(self) -> None:
        """Parse a when block."""
        code = (
            "when start then\n"
            '    print "Game started!"\n'
            "end\n"
        )
        prog = parse_string(code)
        assert len(prog.statements) == 3
        assert isinstance(prog.statements[0], WhenStatement)
        assert isinstance(prog.statements[1], PrintStatement)
        assert isinstance(prog.statements[2], EndStatement)


# ── File loading ───────────────────────────────────────────────


class TestFileLoading:
    def test_parse_file(self, tmp_path: Path) -> None:
        p = tmp_path / "test.rosh"
        p.write_text('print "hello"\n')
        prog = parse_file(p)
        assert len(prog.statements) == 1
        assert prog.source == str(p)

    def test_parse_hello_example(self) -> None:
        """Parse the actual hello.rosh from rosh-lang."""
        hello_path = (
            Path(__file__).parent.parent.parent
            / "rosh-lang" / "examples" / "basics" / "hello.rosh"
        )
        if hello_path.exists():
            prog = parse_file(hello_path)
            prints = [s for s in prog.statements if isinstance(s, PrintStatement)]
            assert len(prints) == 1
            assert prints[0].text == "Hello, World!"


# ── Error reporting ────────────────────────────────────────────


class TestErrors:
    def test_unknown_keyword(self) -> None:
        with pytest.raises(ParseError, match="Unknown keyword"):
            parse_string("frobnicate everything")

    def test_error_includes_line_number(self) -> None:
        with pytest.raises(ParseError, match=":2:"):
            parse_string('print "hello"\nfrobnicate')

    def test_error_includes_source(self) -> None:
        with pytest.raises(ParseError, match="test.rosh"):
            parse_string("frobnicate", source="test.rosh")
