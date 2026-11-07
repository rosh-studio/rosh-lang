"""The first value fixes what kind of thing a name holds."""
import io

import pytest

from rosh_lang.core.parser import parse_string
from rosh_lang.core.runtime import Runtime


def run(source):
    runtime = Runtime(output=io.StringIO())
    runtime.run(parse_string(source))
    return runtime.state


@pytest.mark.parametrize("source, words", [
    ('set n to 5\nset n to "hi"', "n holds a number, so it can't take text"),
    ('set n to "hi"\nset n to 5', "n holds text, so it can't take a number"),
    ('set n to true\nset n to 5', "n holds true or false, so it can't take a number"),
    ('set xs to [1]\nset xs to 2', "xs holds a list, so it can't take a number"),
    ('create object m\nset m to 2', "m holds a thing, so it can't take a number"),
    ('create object m\nset m.label to "a"\nset m.label to 5', "m.label holds text"),
    ('set n to 5\nset n to n + "a"', "n holds a number, so it can't take text"),
])
def test_a_different_kind_is_refused(source, words):
    with pytest.raises(ValueError, match=words):
        run(source)


def test_the_refusal_names_the_line_and_the_way_out():
    with pytest.raises(ValueError, match=r"set n \(line 2\).*Use a new name, or set n to nothing first"):
        run('set n to 5\nset n to "hi"')


@pytest.mark.parametrize("source, name, value", [
    ("set n to 5\nset n to 2.5", "n", 2.5),
    ('set n to 5\nset n to nothing\nset n to "hi"', "n", "hi"),
    ("set n to nothing\nset n to 5", "n", 5),
    ('set t to "a"\nset t to t + 1', "t", "a1"),
])
def test_the_same_kind_or_a_freed_name_is_fine(source, name, value):
    assert run(source)[name] == value


def test_a_listener_can_still_wait_for_state_not_set_yet():
    source = "set hits to 0\nevent ping\non ping when score > 1 set hits to 1\nsend ping"
    assert run(source)["hits"] == 0


def test_an_if_with_no_value_is_an_error_but_equal_has_an_answer():
    with pytest.raises(ValueError, match="nosuch has no value yet"):
        run("if nosuch > 1\nset n to 1\nend")
    assert run("set n to 0\nif nosuch == 1\nset n to 1\nend")["n"] == 0


def test_a_handler_can_wait_for_a_value_not_set_yet():
    source = "set hits to 0\nwhen ping\nif score > 1\nset hits to 1\nend\nend\nsend ping"
    assert run(source)["hits"] == 0


def test_a_handler_still_cant_compare_a_number_with_text():
    with pytest.raises(ValueError, match="can't compare"):
        run('set t to "a"\nwhen ping\nif t > 1\nset n to 1\nend\nend\nsend ping')


def test_a_loop_over_the_limit_never_starts():
    with pytest.raises(ValueError, match="10,000"):
        run("set n to 0\nrepeat 10001\nset n to n + 1\nend")
    assert run("set n to 0\nrepeat 10000\nset n to n + 1\nend")["n"] == 10_000


def test_a_value_cant_quietly_become_a_thing():
    with pytest.raises(ValueError, match="n holds a number, so it can't have a .x"):
        run("set n to 4\nset n.x to 1")


def test_a_checked_reference_keeps_the_rule_too():
    with pytest.raises(ValueError, match="n holds a number"):
        run("create object ball\nset n to 4\nset n to object ball")


def test_no_value_is_different_from_a_number():
    assert run("set n to 0\nif nosuch != 1\nset n to 1\nend")["n"] == 1


def test_nothing_has_no_order():
    with pytest.raises(ValueError, match="nothing has no order"):
        run("if 1 > nothing\nset n to 1\nend")


def test_a_listener_cant_compare_a_number_with_text():
    with pytest.raises(ValueError, match="can't compare"):
        run('set t to "a"\nevent ping\non ping when t > 1 set hits to 1\nsend ping')


def test_a_one_line_rule_says_when_not_if():
    with pytest.raises(Exception, match="when"):
        run("on ping if t > 1 set hits to 1")
