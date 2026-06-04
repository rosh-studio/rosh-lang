"""Tests for Phase 2c: Collections — add, remove, for each, get count."""

from __future__ import annotations

import io
import warnings

import pytest

from rosh_lang.core.model import (
    AddStatement,
    CreateStatement,
    ForEachStatement,
    PrintStatement,
    RemoveStatement,
    SetStatement,
)
from rosh_lang.core.parser import ParseError, parse_string
from rosh_lang.core.runtime import Runtime


def _run(code: str) -> tuple[Runtime, str]:
    out = io.StringIO()
    rt = Runtime(output=out)
    rt.run(parse_string(code))
    return rt, out.getvalue()


# ── Parser tests ──────────────────────────────────────────────


class TestParserAdd:
    def test_add_basic(self):
        prog = parse_string("add visitor to visitors")
        stmt = prog.statements[0]
        assert isinstance(stmt, AddStatement)
        assert stmt.item == "visitor"
        assert stmt.target == "visitors"

    def test_add_literal_item(self):
        prog = parse_string('add "Alice" to names')
        stmt = prog.statements[0]
        assert stmt.item == '"Alice"'
        assert stmt.target == "names"

    def test_add_without_to_normalises_as_create(self):
        """'add X Y' (no 'to') is a natural-language create alias, not a collection add."""
        from rosh_lang.core.model import CreateStatement
        prog = parse_string("add a ball")
        assert isinstance(prog.statements[0], CreateStatement)

    def test_add_numeric_item(self):
        prog = parse_string("add 42 to scores")
        stmt = prog.statements[0]
        assert stmt.item == "42"
        assert stmt.target == "scores"


class TestParserRemove:
    def test_remove_basic(self):
        prog = parse_string("remove visitor from visitors")
        stmt = prog.statements[0]
        assert isinstance(stmt, RemoveStatement)
        assert stmt.item == "visitor"
        assert stmt.target == "visitors"

    def test_remove_without_from_normalises_as_destroy(self):
        """'remove X Y' (no 'from') is a destroy alias, not a collection remove."""
        from rosh_lang.core.model import DestroyStatement
        prog = parse_string("remove enemy")
        assert isinstance(prog.statements[0], DestroyStatement)


class TestParserForEach:
    def test_foreach_basic(self):
        prog = parse_string("for each item in items\n  print {item}\nend")
        stmt = prog.statements[0]
        assert isinstance(stmt, ForEachStatement)
        assert stmt.var == "item"
        assert stmt.target == "items"
        assert len(stmt.body) == 1
        assert isinstance(stmt.body[0], PrintStatement)

    def test_foreach_empty_body(self):
        prog = parse_string("for each x in xs\nend")
        stmt = prog.statements[0]
        assert isinstance(stmt, ForEachStatement)
        assert stmt.body == []

    def test_foreach_nested(self):
        code = "for each a in as\n  for each b in bs\n    print {b}\n  end\nend"
        prog = parse_string(code)
        stmt = prog.statements[0]
        assert isinstance(stmt, ForEachStatement)
        assert len(stmt.body) == 1
        assert isinstance(stmt.body[0], ForEachStatement)

    def test_foreach_no_end_raises(self):
        with pytest.raises(ParseError, match="no matching end"):
            parse_string("for each x in xs\n  print {x}")

    def test_foreach_bad_syntax_raises(self):
        with pytest.raises(ParseError, match="for requires"):
            parse_string("for visitor in visitors\nend")


# ── Runtime: add ─────────────────────────────────────────────


class TestRuntimeAdd:
    def test_add_scalar_to_list(self):
        rt, _ = _run("create list scores\nadd 10 to scores\nadd 20 to scores")
        assert rt.state["scores"] == [10, 20]

    def test_add_variable_to_list(self):
        rt, _ = _run(
            "create list names\n"
            "create string visitor\n"
            'set visitor to "Alice"\n'
            "add visitor to names"
        )
        assert rt.state["names"] == ["Alice"]

    def test_add_quoted_string(self):
        rt, _ = _run('create list tags\nadd "hello" to tags')
        assert rt.state["tags"] == ["hello"]

    def test_add_to_non_list_warns(self):
        with pytest.warns(UserWarning, match="not a list"):
            rt, _ = _run("create number x\nadd 1 to x")

    def test_add_multiple_items(self):
        rt, _ = _run(
            "create list nums\n"
            "add 1 to nums\nadd 2 to nums\nadd 3 to nums"
        )
        assert rt.state["nums"] == [1, 2, 3]


# ── Runtime: remove ────────────────────────────────────────────


class TestRuntimeRemove:
    def test_remove_existing_item(self):
        rt, _ = _run(
            "create list scores\n"
            "add 10 to scores\nadd 20 to scores\nadd 30 to scores\n"
            "remove 20 from scores"
        )
        assert rt.state["scores"] == [10, 30]

    def test_remove_not_found_noop(self):
        rt, _ = _run(
            "create list scores\nadd 10 to scores\nremove 99 from scores"
        )
        assert rt.state["scores"] == [10]

    def test_remove_first_occurrence_only(self):
        rt, _ = _run(
            "create list nums\n"
            "add 5 to nums\nadd 5 to nums\nadd 5 to nums\n"
            "remove 5 from nums"
        )
        assert rt.state["nums"] == [5, 5]

    def test_remove_variable_item(self):
        rt, _ = _run(
            "create list names\n"
            'add "Alice" to names\nadd "Bob" to names\n'
            'create string x\nset x to "Alice"\n'
            "remove x from names"
        )
        assert rt.state["names"] == ["Bob"]


# ── Runtime: for each ──────────────────────────────────────────


class TestRuntimeForEach:
    def test_foreach_prints_all_items(self):
        _, output = _run(
            "create list nums\n"
            "add 1 to nums\nadd 2 to nums\nadd 3 to nums\n"
            "for each n in nums\n  print {n}\nend"
        )
        assert output == "1\n2\n3\n"

    def test_foreach_empty_list_no_output(self):
        _, output = _run(
            "create list empty\n"
            "for each x in empty\n  print hello\nend"
        )
        assert output == ""

    def test_foreach_var_restored_after_loop(self):
        rt, _ = _run(
            "create list nums\nadd 1 to nums\n"
            "set n to 99\n"
            "for each n in nums\n  print {n}\nend"
        )
        assert rt.state["n"] == 99

    def test_foreach_var_removed_if_not_preset(self):
        rt, _ = _run(
            "create list nums\nadd 1 to nums\n"
            "for each n in nums\n  print {n}\nend"
        )
        assert "n" not in rt.state

    def test_foreach_modify_list_during_iteration_safe(self):
        _, output = _run(
            "create list nums\nadd 1 to nums\nadd 2 to nums\nadd 3 to nums\n"
            "for each n in nums\n  print {n}\nend"
        )
        assert output == "1\n2\n3\n"

    def test_foreach_on_non_list_warns(self):
        with pytest.warns(UserWarning, match="not a list"):
            _run("create number x\nfor each n in x\n  print {n}\nend")

    def test_foreach_can_mutate_state(self):
        rt, _ = _run(
            "create list nums\nadd 10 to nums\nadd 20 to nums\n"
            "create number total\nset total to 0\n"
            "for each n in nums\n  set total to total + n\nend"
        )
        assert rt.state["total"] == 30

    def test_foreach_nested(self):
        _, output = _run(
            "create list outer\nadd 1 to outer\nadd 2 to outer\n"
            "create list inner\nadd a to inner\nadd b to inner\n"
            "for each x in outer\n  for each y in inner\n    print {x}{y}\n  end\nend"
        )
        assert output == "1a\n1b\n2a\n2b\n"


# ── Runtime: count ─────────────────────────────────────────────


class TestRuntimeCount:
    def test_get_count_stores_in_count(self):
        rt, _ = _run(
            "create list nums\nadd 1 to nums\nadd 2 to nums\nadd 3 to nums\n"
            "get count of nums"
        )
        assert rt.state["_count"] == 3

    def test_get_count_empty_list(self):
        rt, _ = _run("create list empty\nget count of empty")
        assert rt.state["_count"] == 0

    def test_set_count_expression_form(self):
        rt, _ = _run(
            "create list nums\nadd 10 to nums\nadd 20 to nums\n"
            "set n to count of nums"
        )
        assert rt.state["n"] == 2

    def test_count_expression_in_print(self):
        _, output = _run(
            "create list items\nadd a to items\nadd b to items\n"
            "set n to count of items\n"
            "print Count: {n}"
        )
        assert output == "Count: 2\n"

    def test_count_non_list_returns_zero(self):
        rt, _ = _run("create number x\nset n to count of x")
        assert rt.state["n"] == 0


# ── Integration ────────────────────────────────────────────────


class TestCollectionsIntegration:
    def test_add_remove_count_cycle(self):
        rt, output = _run(
            "create list scores\n"
            "add 10 to scores\nadd 20 to scores\nadd 30 to scores\n"
            "set n to count of scores\n"
            "print Count: {n}\n"
            "remove 20 from scores\n"
            "set n to count of scores\n"
            "print After remove: {n}\n"
            "for each score in scores\n  print Score: {score}\nend"
        )
        assert output == (
            "Count: 3\n"
            "After remove: 2\n"
            "Score: 10\n"
            "Score: 30\n"
        )

    def test_collection_with_parameterised_function(self):
        """Collections + Phase 2b: call a function for each item."""
        _, output = _run(
            "create list nums\nadd 3 to nums\nadd 7 to nums\n"
            "define double with n\n  print doubled: {n}\nend\n"
            "for each n in nums\n  do double n=n\nend"
        )
        assert output == "doubled: 3\ndoubled: 7\n"


# ── Phase 2d: Missing/optional values ─────────────────────────


class TestPhase2dNothingValues:
    def test_set_to_nothing(self):
        rt, _ = _run("create number score\nset score to 100\nset score to nothing")
        assert rt.state["score"] is None

    def test_nothing_interpolates_empty(self):
        _, output = _run("set label to nothing\nprint {label}")
        assert output == "\n"

    def test_missing_key_interpolates_literal(self):
        _, output = _run("print {missing_key}")
        assert output == "{missing_key}\n"

    def test_condition_x_eq_nothing_when_unset(self):
        _, output = _run("if x == nothing\n  print absent\nend")
        assert output == "absent\n"

    def test_condition_x_eq_nothing_when_set_to_nothing(self):
        _, output = _run("set x to nothing\nif x == nothing\n  print cleared\nend")
        assert output == "cleared\n"

    def test_condition_x_eq_nothing_when_set(self):
        _, output = _run("set x to 5\nif x == nothing\n  print absent\nend")
        assert output == ""

    def test_condition_x_neq_nothing_when_set(self):
        _, output = _run("set x to 5\nif x != nothing\n  print present\nend")
        assert output == "present\n"

    def test_condition_x_neq_nothing_when_unset(self):
        _, output = _run("if x != nothing\n  print present\nend")
        assert output == ""

    def test_default_value_pattern(self):
        _, output = _run(
            "if label == nothing\n  set label to Default\nend\n"
            "print {label}"
        )
        assert output == "Default\n"

    def test_nothing_in_set_value(self):
        rt, _ = _run("set x to nothing")
        assert rt.state["x"] is None

    def test_nothing_false_comparison(self):
        """nothing == 5 is False"""
        _, output = _run("if nothing == 5\n  print yes\nend")
        assert output == ""
