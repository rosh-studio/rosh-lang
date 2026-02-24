"""Tests for the rosh-compose runtime."""

from __future__ import annotations

import io
from pathlib import Path

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
from rosh_lang.runtime import Runtime, run


def _run(stmts: list, *, output: io.StringIO | None = None) -> Runtime:
    """Helper: run a list of statements, return the runtime."""
    buf = output or io.StringIO()
    rt = Runtime(output=buf)
    rt.run(Programme(statements=stmts))
    rt.output = buf  # keep reference for assertions
    return rt


def _output(rt: Runtime) -> str:
    """Get output text from a runtime whose output is a StringIO."""
    return rt.output.getvalue()


# ── Print ─────────────────────────────────────────────────────


class TestPrintExecution:
    def test_hello_world(self) -> None:
        rt = _run([PrintStatement(text="hello world")])
        assert _output(rt) == "hello world\n"

    def test_print_multiple(self) -> None:
        rt = _run([
            PrintStatement(text="line one"),
            PrintStatement(text="line two"),
        ])
        assert _output(rt) == "line one\nline two\n"

    def test_print_interpolation(self) -> None:
        rt = _run([
            CreateStatement(kind="number", name="score"),
            SetStatement(target="score", value="42"),
            PrintStatement(text="Score: {score}"),
        ])
        assert _output(rt) == "Score: 42\n"

    def test_print_dot_interpolation(self) -> None:
        rt = _run([
            CreateStatement(kind="object", name="player"),
            SetStatement(target="player.health", value="100"),
            PrintStatement(text="HP: {player.health}"),
        ])
        assert _output(rt) == "HP: 100\n"

    def test_print_unquoted(self) -> None:
        """Unquoted print text works the same way."""
        rt = _run([PrintStatement(text="hello world")])
        assert _output(rt) == "hello world\n"

    def test_print_missing_var(self) -> None:
        """Missing vars are left as {name} — no crash."""
        rt = _run([PrintStatement(text="Hello {nobody}")])
        assert _output(rt) == "Hello {nobody}\n"


# ── Create ────────────────────────────────────────────────────


class TestCreateExecution:
    def test_create_object(self) -> None:
        rt = _run([CreateStatement(kind="object", name="player")])
        assert rt.state["player"] == {}

    def test_create_number(self) -> None:
        rt = _run([CreateStatement(kind="number", name="score")])
        assert rt.state["score"] == 0

    def test_create_string(self) -> None:
        rt = _run([CreateStatement(kind="string", name="name")])
        assert rt.state["name"] == ""

    def test_create_with_parent(self) -> None:
        rt = _run([
            CreateStatement(kind="object", name="base"),
            SetStatement(target="base.health", value="100"),
            CreateStatement(kind="object", name="hero", parent="base"),
        ])
        assert rt.state["hero"] == {"health": 100}
        # verify it's a copy, not the same dict
        assert rt.state["hero"] is not rt.state["base"]


# ── Set ───────────────────────────────────────────────────────


class TestSetExecution:
    def test_set_simple(self) -> None:
        rt = _run([SetStatement(target="x", value="100")])
        assert rt.state["x"] == 100

    def test_set_property(self) -> None:
        rt = _run([
            CreateStatement(kind="object", name="player"),
            SetStatement(target="player.health", value="75"),
        ])
        assert rt.state["player"]["health"] == 75

    def test_set_string_value(self) -> None:
        rt = _run([SetStatement(target="name", value='"Alice"')])
        assert rt.state["name"] == "Alice"

    def test_set_number_coercion(self) -> None:
        rt = _run([SetStatement(target="x", value="100")])
        assert rt.state["x"] == 100
        assert isinstance(rt.state["x"], int)

    def test_set_float_coercion(self) -> None:
        rt = _run([SetStatement(target="speed", value="3.14")])
        assert rt.state["speed"] == 3.14

    def test_set_deep_property(self) -> None:
        rt = _run([
            CreateStatement(kind="object", name="player"),
            SetStatement(target="player.pos.x", value="10"),
        ])
        assert rt.state["player"]["pos"]["x"] == 10


# ── When / Event Handlers ────────────────────────────────────


class TestWhenExecution:
    def test_when_registers_handler(self) -> None:
        rt = _run([
            WhenStatement(event="start"),
            PrintStatement(text="started"),
            EndStatement(),
        ])
        # handler registered, but not executed during run
        assert _output(rt) == ""
        assert "start" in rt.handlers

    def test_send_event(self) -> None:
        buf = io.StringIO()
        rt = _run(
            [
                WhenStatement(event="start"),
                PrintStatement(text="go!"),
                EndStatement(),
            ],
            output=buf,
        )
        assert buf.getvalue() == ""
        rt.send("start")
        assert buf.getvalue() == "go!\n"

    def test_handler_body(self) -> None:
        buf = io.StringIO()
        rt = _run(
            [
                CreateStatement(kind="number", name="x"),
                WhenStatement(event="tick"),
                SetStatement(target="x", value="42"),
                PrintStatement(text="x is {x}"),
                EndStatement(),
            ],
            output=buf,
        )
        assert rt.state["x"] == 0
        rt.send("tick")
        assert rt.state["x"] == 42
        assert buf.getvalue() == "x is 42\n"


# ── Skipped Statements ───────────────────────────────────────


class TestSkippedStatements:
    def test_comments_and_blanks_ignored(self) -> None:
        rt = _run([
            CommentStatement(text="this is a comment"),
            BlankStatement(),
            PrintStatement(text="hello"),
        ])
        assert _output(rt) == "hello\n"


# ── End-to-End File Execution ────────────────────────────────


EXAMPLES = Path(__file__).parent.parent / "examples"


class TestRunFile:
    def test_run_hello_rosh(self) -> None:
        from rosh_lang.parser import parse_file

        buf = io.StringIO()
        prog = parse_file(EXAMPLES / "hello.rosh")
        rt = run(prog, output=buf)
        assert buf.getvalue() == "hello world\n"

    def test_run_counter_rosh(self) -> None:
        from rosh_lang.parser import parse_file

        buf = io.StringIO()
        prog = parse_file(EXAMPLES / "counter.rosh")
        rt = run(prog, output=buf)
        assert buf.getvalue() == "Count is: 1\n"

    def test_run_player_rosh(self) -> None:
        from rosh_lang.parser import parse_file

        buf = io.StringIO()
        prog = parse_file(EXAMPLES / "player.rosh")
        rt = run(prog, output=buf)
        assert buf.getvalue() == "Player created at (50, 90) with 100 HP\n"


# ── Convenience function ─────────────────────────────────────


class TestConvenienceRun:
    def test_run_returns_runtime(self) -> None:
        buf = io.StringIO()
        rt = run(Programme(statements=[PrintStatement(text="hi")]), output=buf)
        assert isinstance(rt, Runtime)
        assert buf.getvalue() == "hi\n"
