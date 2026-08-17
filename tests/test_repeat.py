# licence: MIT
"""Tests for the repeat keyword — counted loops."""

from __future__ import annotations

import io

import pytest

from rosh_lang.core.model import RepeatStatement, PrintStatement
from rosh_lang.core.parser import parse_string
from rosh_lang.core.runtime import Runtime


# ── Parser tests ──────────────────────────────────────────────


def test_parse_repeat_simple():
    prog = parse_string("repeat 3\n  print hello\nend")
    stmt = prog.statements[0]
    assert isinstance(stmt, RepeatStatement)
    assert stmt.count == "3"
    assert stmt.var == ""
    assert len(stmt.body) == 1
    assert isinstance(stmt.body[0], PrintStatement)


def test_parse_repeat_with_var():
    prog = parse_string("repeat 5 as i\n  print round\nend")
    stmt = prog.statements[0]
    assert isinstance(stmt, RepeatStatement)
    assert stmt.count == "5"
    assert stmt.var == "i"


def test_parse_repeat_variable_count():
    prog = parse_string("repeat rounds\n  print go\nend")
    stmt = prog.statements[0]
    assert isinstance(stmt, RepeatStatement)
    assert stmt.count == "rounds"


def test_parse_nested_repeat():
    prog = parse_string("repeat 2\n  repeat 3\n    print x\n  end\nend")
    outer = prog.statements[0]
    assert isinstance(outer, RepeatStatement)
    assert outer.count == "2"
    inner = outer.body[0]
    assert isinstance(inner, RepeatStatement)
    assert inner.count == "3"


# ── Runtime tests ─────────────────────────────────────────────


def test_runtime_repeat_simple():
    buf = io.StringIO()
    rt = Runtime(output=buf)
    rt.run(parse_string("repeat 3\n  print hello\nend"))
    assert buf.getvalue() == "hello\nhello\nhello\n"


def test_runtime_repeat_with_var():
    buf = io.StringIO()
    rt = Runtime(output=buf)
    rt.run(parse_string('repeat 3 as i\n  print "Round {i}"\nend'))
    assert buf.getvalue() == "Round 1\nRound 2\nRound 3\n"


def test_runtime_repeat_var_cleaned_up():
    buf = io.StringIO()
    rt = Runtime(output=buf)
    rt.run(parse_string("repeat 2 as i\n  print ok\nend"))
    assert "i" not in rt.state


def test_runtime_repeat_var_restored():
    """If the loop var existed before, it should be restored after."""
    buf = io.StringIO()
    rt = Runtime(output=buf)
    rt.run(parse_string(
        "create number i\nset i to 99\n"
        "repeat 2 as i\n  print ok\nend"
    ))
    assert rt.state["i"] == 99


def test_runtime_repeat_zero_count():
    buf = io.StringIO()
    rt = Runtime(output=buf)
    rt.run(parse_string("repeat 0\n  print nope\nend"))
    assert buf.getvalue() == ""


def test_runtime_repeat_negative_count():
    buf = io.StringIO()
    rt = Runtime(output=buf)
    rt.run(parse_string("repeat -1\n  print nope\nend"))
    assert buf.getvalue() == ""


def test_runtime_repeat_variable_count():
    buf = io.StringIO()
    rt = Runtime(output=buf)
    rt.run(parse_string(
        "create number rounds\nset rounds to 2\n"
        "repeat rounds\n  print go\nend"
    ))
    assert buf.getvalue() == "go\ngo\n"


def test_runtime_repeat_with_set():
    buf = io.StringIO()
    rt = Runtime(output=buf)
    rt.run(parse_string(
        "create number total\nset total to 0\n"
        "repeat 5\n  set total to total + 1\nend\n"
        'print "{total}"'
    ))
    assert "5" in buf.getvalue()


def test_runtime_repeat_nested():
    buf = io.StringIO()
    rt = Runtime(output=buf)
    rt.run(parse_string(
        "create number count\nset count to 0\n"
        "repeat 3\n  repeat 4\n    set count to count + 1\n  end\nend\n"
        'print "{count}"'
    ))
    assert "12" in buf.getvalue()


def test_runtime_repeat_max_guard():
    """Repeat count is capped at 10,000."""
    buf = io.StringIO()
    rt = Runtime(output=buf)
    rt.run(parse_string(
        "create number n\nset n to 0\n"
        "repeat 99999\n  set n to n + 1\nend"
    ))
    assert rt.state["n"] == 10_000


def test_nested_repeats_cannot_multiply_past_the_global_step_budget():
    """Each repeat's own 10,000-iteration cap is a per-loop limit, not a
    total one — nested loops multiply rather than add, so two levels of
    "repeat 10000" is 100,000,000 executed statements, not 20,000. Found
    exploitable as a same-process DoS against rosh-portal's shared,
    single-worker, synchronous WS world-command loop (any guest's tiny
    message could occupy the whole event loop for ~30s+, freezing every
    connected user — see rosh-dev/BUGS.md's round-eight entry,
    16-Aug-2026). Runtime._MAX_STEPS bounds the TOTAL statements executed
    across one outermost run()/execute() call, regardless of nesting
    depth, so this now aborts in well under a second instead of running
    to completion.
    """
    import time

    buf = io.StringIO()
    rt = Runtime(output=buf)
    programme = parse_string(
        'repeat 10000 as i\n'
        '  repeat 10000 as j\n'
        '    print "x"\n'
        '  end\n'
        'end'
    )
    start = time.time()
    with pytest.raises(RuntimeError, match="exceeded the maximum"):
        rt.run(programme)
    elapsed = time.time() - start
    assert elapsed < 2.0, f"budget check took {elapsed:.2f}s — too slow to be a real DoS guard"
