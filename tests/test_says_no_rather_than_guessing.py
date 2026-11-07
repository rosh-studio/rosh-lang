"""Lines that used to do something quietly different now say so (6 Nov conformance matrix)."""
import io

import pytest

from rosh_lang.core.parser import ParseError, parse_string
from rosh_lang.core.runtime import Runtime


def test_set_with_nothing_after_to_is_refused():
    with pytest.raises(ParseError, match="nothing after 'to'"):
        parse_string("set m.y to", source="t")


def test_old_two_word_set_still_works():
    rt = Runtime(output=io.StringIO())
    rt.run(parse_string("create object m\nset m.y 3", source="t"))
    assert rt.state["m"]["y"] == 3


def test_send_needs_a_named_value():
    with pytest.raises(ParseError, match="value=8"):
        parse_string("send scored 8", source="t")


def test_a_named_value_reaches_the_handler():
    out = io.StringIO()
    rt = Runtime(output=out)
    rt.run(parse_string('event scored value\nwhen scored\nprint "v={value}"\nend\nsend scored value=8', source="t"))
    assert out.getvalue() == "v=8\n"


def _state(code):
    rt = Runtime(output=io.StringIO())
    rt.run(parse_string(code, source="t"))
    return rt.state


def test_a_number_can_go_on_the_left_of_a_comparison():
    assert _state("create object m\nset m.x to 7\nif 5 < m.x\nset m.y to 1\nend")["m"]["y"] == 1
    assert "y" not in _state("create object m\nset m.x to 3\nif 5 < m.x\nset m.y to 1\nend")["m"]


def test_a_comparison_can_use_a_value_on_the_right():
    assert _state("set n to 5\ncreate object m\nset m.x to 7\nif m.x > n\nset m.y to 1\nend")["m"]["y"] == 1


def test_a_bare_word_with_no_value_is_still_text():
    assert _state('set phase to "go"\ncreate object m\nif phase == go\nset m.y to 1\nend')["m"]["y"] == 1


def test_arithmetic_with_more_than_one_operator():
    assert _state("create object m\nset m.x to 1\nset m.x to m.x + 1 + 1")["m"]["x"] == 3
    assert _state("create object m\nset m.x to 2 + 3 * 4")["m"]["x"] == 14
    assert _state("create object m\nset m.x to 20 - 2 * 3 - 4")["m"]["x"] == 10
    assert _state('create object m\nset m.label to "a" + "b" + "c"')["m"]["label"] == "abc"


def test_a_chain_with_no_value_names_it():
    with pytest.raises(ValueError, match="nosuch"):
        _state("create object m\nset m.x to 1 + nosuch + 1")


def test_a_minus_inside_quotes_is_not_arithmetic():
    assert _state('create object m\nset m.label to "a - b - c"')["m"]["label"] == "a - b - c"


@pytest.mark.parametrize("code", ["else", "end", 'print "a"\nelse\nprint "b"', "when ping\nset m.y to 2",
                                  'if 1 > 0\nprint "y"\nend\nelse\nprint "n"'])
def test_a_block_word_that_belongs_to_nothing_is_refused(code):
    with pytest.raises(ParseError):
        parse_string(code, source="t")


@pytest.mark.parametrize("code", ['set s to "xxxxxxxxxx"\nrepeat 25\nset s to s + s + s\nend',
                                  'set s to "xxxxxxxxxx"\nrepeat 25\nset s to s + s\nend',
                                  "set n to 3\nrepeat 40\nset n to n * n\nend"])
def test_a_value_cannot_grow_without_limit(code):
    with pytest.raises(ValueError, match="too (long|big)"):
        _state(code)


def test_one_line_cannot_name_any_number_of_values():
    with pytest.raises(ValueError, match="over 64"):
        _state("create object m\nset m.x to " + " + ".join(["1"] * 16000))


def test_a_very_long_line_is_quick():
    import time
    start = time.perf_counter()
    with pytest.raises(ValueError):
        _state("create object m\nset m.x to " + " + ".join(["1"] * 200000))
    assert time.perf_counter() - start < 1


def test_a_list_cannot_hold_itself():
    with pytest.raises(ValueError, match="list can hold"):
        _state("add 1 to items\nadd items to items")


def test_escaped_quotes_stay_inside_text():
    assert _state('create object m\nset m.label to "a + b \\" c"')["m"]["label"] == 'a + b " c'


def test_joined_numbers_read_as_they_do_elsewhere():
    assert _state('set n to "x" + 1.0 + 2')["n"] == "x12"


def test_a_list_has_limits():
    with pytest.raises(ValueError, match="1,000 characters"):
        _state('add "%s" to xs' % ("x" * 1001))
    with pytest.raises(ValueError, match="as many as a list can hold"):
        _state('create object a\nset a.items to []\nrepeat 10000\nadd "x" to a.items\nend\nadd "x" to a.items')


@pytest.mark.parametrize("code", ["set a to 1e309", "create object a\nset a.v to 5\nset a.v to clamp a.v 1e309 1e309"])
def test_infinity_is_never_kept(code):
    with pytest.raises(ValueError, match="too big"):
        _state(code)


def test_the_words_nan_and_infinity_are_words():
    assert _state("set a to nan\nset b to infinity") == {"a": "nan", "b": "infinity"}


def test_interpolation_and_literals_are_within_the_limit():
    with pytest.raises(ValueError):
        _state('set s to "%s"' % ("x" * 100001))
    with pytest.raises(ValueError):
        _state('set s to "%s"\nsay {s}{s}' % ("x" * 60000))


def test_a_refused_value_leaves_a_checked_reference_standing():
    rt = Runtime(output=io.StringIO())
    rt.run(parse_string("create object a\ncreate object b\nset a.parent to object b", source="t"))
    with pytest.raises(ValueError):
        rt.run(parse_string("set a.parent to missing + 1", source="t"))
    assert rt.references["a.parent"] == "b"


def test_joined_true_reads_as_written():
    assert _state('set a to "x"\nset b to true\nset c to a + b')["c"] == "xtrue"


def test_a_written_list_has_the_same_limits():
    with pytest.raises(ValueError, match="1,000 characters"):
        _state('set xs to ["%s"]' % ("x" * 1001))
    with pytest.raises(ValueError, match="10,000 items"):
        _state("set xs to [%s]" % ", ".join(["0"] * 10001))
