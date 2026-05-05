"""Tests for Step 24: Functions — define/do keywords."""

from __future__ import annotations

import io

import pytest

from rosh_lang.core.model import DefineStatement, DoStatement, PrintStatement, SetStatement
from rosh_lang.core.parser import ParseError, parse_string
from rosh_lang.core.runtime import Runtime
from rosh_lang.targets._js_codegen import compile_programme


# ── Parser tests ──────────────────────────────────────────────


class TestParserDefine:
    def test_define_basic(self):
        prog = parse_string("define greet\n  print hello\nend")
        assert len(prog.statements) == 1
        stmt = prog.statements[0]
        assert isinstance(stmt, DefineStatement)
        assert stmt.name == "greet"
        assert len(stmt.body) == 1
        assert isinstance(stmt.body[0], PrintStatement)
        assert stmt.body[0].text == "hello"

    def test_define_empty_body(self):
        prog = parse_string("define noop\nend")
        stmt = prog.statements[0]
        assert isinstance(stmt, DefineStatement)
        assert stmt.name == "noop"
        assert stmt.body == []

    def test_define_multiple_statements(self):
        code = "define setup\n  create number score\n  set score to 0\n  print ready\nend"
        prog = parse_string(code)
        stmt = prog.statements[0]
        assert isinstance(stmt, DefineStatement)
        assert len(stmt.body) == 3

    def test_define_with_if_block(self):
        code = "define check\n  if score > 10\n    print win\n  end\nend"
        prog = parse_string(code)
        stmt = prog.statements[0]
        assert isinstance(stmt, DefineStatement)
        assert len(stmt.body) == 1  # if block collapsed

    def test_define_no_name_raises(self):
        with pytest.raises(ParseError, match="function name"):
            parse_string("define\nend")

    def test_define_no_end_raises(self):
        with pytest.raises(ParseError, match="no matching end"):
            parse_string("define greet\n  print hello")

    def test_define_preserves_line_number(self):
        prog = parse_string("print x\ndefine greet\n  print hello\nend")
        stmt = prog.statements[1]
        assert isinstance(stmt, DefineStatement)
        assert stmt.line == 2


class TestParserDo:
    def test_do_basic(self):
        prog = parse_string("do greet")
        assert len(prog.statements) == 1
        stmt = prog.statements[0]
        assert isinstance(stmt, DoStatement)
        assert stmt.name == "greet"

    def test_do_no_name_raises(self):
        with pytest.raises(ParseError, match="function name"):
            parse_string("do")

    def test_do_preserves_line(self):
        prog = parse_string("print x\ndo greet")
        assert prog.statements[1].line == 2


# ── Runtime tests ─────────────────────────────────────────────


class TestRuntimeFunctions:
    def _run(self, code: str) -> tuple[Runtime, str]:
        out = io.StringIO()
        rt = Runtime(output=out)
        rt.run(parse_string(code))
        return rt, out.getvalue()

    def test_define_and_do(self):
        code = "define greet\n  print hello\nend\ndo greet"
        _, output = self._run(code)
        assert output == "hello\n"

    def test_do_modifies_state(self):
        code = (
            "create number score\n"
            "define add_ten\n  set score to score + 10\nend\n"
            "do add_ten\n"
            "do add_ten"
        )
        rt, _ = self._run(code)
        assert rt.state["score"] == 20

    def test_do_undefined_warns(self):
        code = "do nonexistent"
        with pytest.warns(UserWarning, match="not defined"):
            self._run(code)

    def test_define_not_executed_immediately(self):
        code = "define greet\n  print hello\nend"
        _, output = self._run(code)
        assert output == ""

    def test_last_definition_wins(self):
        code = (
            "define greet\n  print first\nend\n"
            "define greet\n  print second\nend\n"
            "do greet"
        )
        _, output = self._run(code)
        assert output == "second\n"

    def test_recursion_rejected(self):
        code = "define loop\n  do loop\nend\ndo loop"
        with pytest.raises(RuntimeError, match="Recursive"):
            self._run(code)

    def test_functions_call_other_functions(self):
        code = (
            "define inner\n  print inner\nend\n"
            "define outer\n  print outer\n  do inner\nend\n"
            "do outer"
        )
        _, output = self._run(code)
        assert output == "outer\ninner\n"

    def test_mutual_recursion_rejected(self):
        code = (
            "define a\n  do b\nend\n"
            "define b\n  do a\nend\n"
            "do a"
        )
        with pytest.raises(RuntimeError, match="Recursive"):
            self._run(code)

    def test_function_with_if(self):
        code = (
            "create number x\nset x to 5\n"
            "define check\n  if x > 3\n    print big\n  else\n    print small\n  end\nend\n"
            "do check"
        )
        _, output = self._run(code)
        assert output == "big\n"

    def test_function_with_interpolation(self):
        code = (
            "create number score\nset score to 42\n"
            "define show\n  print Score: {score}\nend\n"
            "do show"
        )
        _, output = self._run(code)
        assert output == "Score: 42\n"

    def test_function_in_when_handler(self):
        code = (
            "define greet\n  print hello\nend\n"
            "when start\n  do greet\nend"
        )
        rt, _ = self._run(code)
        out = io.StringIO()
        rt.output = out
        rt.send("start")
        assert out.getvalue() == "hello\n"

    def test_on_do_action(self):
        code = (
            "create number x\n"
            "define bump\n  set x to x + 1\nend\n"
            "on click do bump"
        )
        rt, _ = self._run(code)
        rt.send("click")
        assert rt.state["x"] == 1
        rt.send("click")
        assert rt.state["x"] == 2


# ── JS codegen tests ─────────────────────────────────────────


class TestJSCodegenFunctions:
    def test_define_emits_function(self):
        code = "define greet\n  print hello\nend"
        result = compile_programme(parse_string(code))
        assert "function rosh_fn_greet()" in result.init_code
        assert 'rosh.appendOutput(rosh.interpolate("hello"))' in result.init_code

    def test_do_emits_call(self):
        code = "define greet\n  print hello\nend\ndo greet"
        result = compile_programme(parse_string(code))
        assert "rosh_fn_greet();" in result.init_code

    def test_do_in_handler(self):
        code = "define fire\n  print bang\nend\nwhen click\n  do fire\nend"
        result = compile_programme(parse_string(code))
        assert "rosh_fn_fire();" in result.handler_code

    def test_on_do_emits_call(self):
        code = "define fire\n  print bang\nend\non click do fire"
        result = compile_programme(parse_string(code))
        assert "rosh_fn_fire();" in result.handler_code

    def test_hyphenated_name(self):
        code = "define fire-bullet\n  print fire\nend\ndo fire-bullet"
        result = compile_programme(parse_string(code))
        assert "rosh_fn_fire_bullet()" in result.init_code
