"""An `if` that can never be true is an error with its line (BUGS.md 27 Oct)."""

import pytest

from rosh_lang.core.parser import ParseError, parse_string
from rosh_lang.core.runtime import Runtime


def _run(src):
    runtime = Runtime()
    for statement in parse_string(src, normalise=False).statements:
        runtime.execute(statement)
    return runtime


@pytest.mark.parametrize("op, hint", [("=", "=="), ("equals", "=="), ("=>", ">="), ("~", None)])
def test_an_unknown_operator_is_refused_with_its_line(op, hint):
    with pytest.raises(ParseError) as err:
        parse_string(f"set visits to 5\nif visits {op} 5\nprint \"x\"\nend", normalise=False)
    assert err.value.line == 2
    assert (f"did you mean {hint}?" in str(err.value)) if hint else "did you mean" not in str(err.value)


def test_a_value_of_several_words_is_compared_whole():
    runtime = _run('create object t\nset t.label to "big box"\nset seen to 0\n'
                   'if t.label == "big box"\nset seen to 1\nend')
    assert runtime.state["seen"] == 1


def test_the_six_operators_still_work():
    for op, expected in (("==", 1), ("!=", 0), (">", 0), ("<", 0), (">=", 1), ("<=", 1)):
        runtime = _run(f"set n to 3\nset hit to 0\nif n {op} 3\nset hit to 1\nend")
        assert runtime.state["hit"] == expected, op


@pytest.mark.parametrize("line, said", [('on e say "hello"', "hello"), ("on e say 'hi there'", "hi there"),
                                        ("on e say plain words", "plain words"), ('on e print "x y"', "x y")])
def test_the_one_line_on_reads_quotes_as_its_own_line_does(line, said):
    # BUGS.md 26 Oct: `on e say "hello"` said the quote marks too.
    import io
    runtime = Runtime()
    runtime.output = io.StringIO()
    for statement in parse_string(f"event e\n{line}\nsend e", normalise=False).statements:
        runtime.execute(statement)
    assert runtime.output.getvalue() == said + "\n"


def test_an_on_without_an_action_names_all_seven():
    # BUGS.md 27 Oct: the message listed four of them.
    with pytest.raises(ParseError) as err:
        parse_string("event e\non e fly away", normalise=False)
    assert err.value.line == 2 and "set, send, say, print, destroy, do, play" in str(err.value)


def test_an_event_name_with_go_in_it_is_still_one_name():
    # Making `go` an action renamed `ready_go` to `ready`.
    statement = parse_string("on ready go say hello", normalise=False).statements[0]
    assert (statement.event, statement.action) == ("ready_go", "say")
