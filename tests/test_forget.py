"""`forget thing.property`: the thing no longer has that property (31 Oct).

`set` can only add or change, so undoing a colour on something that had none
could only write a colour nobody chose.
"""

import pytest

from rosh_lang.core.parser import ParseError, parse_string
from rosh_lang.core.runtime import Runtime


def run(source: str) -> Runtime:
    rt = Runtime()
    rt.run(parse_string(source))
    return rt


def test_forget_removes_the_property():
    rt = run("create object torc\nset torc.color to gold\nset torc.size to 2\nforget torc.color")
    assert "color" not in rt.state["torc"]
    assert rt.state["torc"]["size"] == 2


def test_forget_a_property_it_never_had_is_quiet():
    rt = run("create object torc\nforget torc.color")
    assert rt.state["torc"] == {}


def test_forget_a_multi_word_name():
    rt = run("create object ancient_oak\nset ancient_oak.color to red\nforget ancient oak.color")
    assert "color" not in rt.state["ancient_oak"]


def test_forget_needs_an_object_that_exists():
    with pytest.raises(KeyError, match="no object 'ghost'"):
        run("forget ghost.color")


@pytest.mark.parametrize("line", ["forget", "forget torc", "forget torc.", "forget torc.color now",
                                  "forget torc. locked", "forget torc .locked"])
def test_forget_needs_a_thing_and_one_property(line):
    with pytest.raises(ParseError, match="forget torc.color"):
        parse_string(line)


def test_forget_drops_a_reference():
    rt = run("create object a\ncreate object b\nset a.parent to object b\nforget a.parent\ndestroy b")
    assert "parent" not in rt.state["a"]
    assert "b" not in rt.state
