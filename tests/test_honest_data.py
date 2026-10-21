"""Rosh must not lose or blur data quietly (roadmap step 1, 15 Oct 2026).

Found by the Rosh-vs-JSON pass: creating an existing name silently wiped all
its properties, and a bare `null` was stored as the text "null", so the two
couldn't be told apart. Principle 11 applies to the language first.
"""
from __future__ import annotations

import io

import pytest

from rosh_lang.core.parser import parse_string
from rosh_lang.core.runtime import run


def _run(src: str):
    out = io.StringIO()
    rt = run(parse_string(src), output=out)
    return rt, out.getvalue()


def test_creating_an_existing_object_is_refused_not_wiped():
    src = 'create object a\nset a.colour to "red"\ncreate object a\n'
    with pytest.raises(KeyError) as err:
        _run(src)
    message = err.value.args[0]
    assert "'a' already exists" in message and "line 3" in message
    assert "set" in message and "destroy" in message


def test_create_after_destroy_starts_again():
    rt, _ = _run('create object a\nset a.colour to "red"\ndestroy a\ncreate object a\n')
    assert rt.state["a"] == {}


def test_bare_null_is_nothing_and_quoted_null_is_text():
    rt, out = _run(
        'create object a\n'
        'set a.real to null\n'
        'set a.word to "null"\n'
        'if a.real is null\n  print "real is nothing"\nend\n'
        'if a.word is null\n  print "WRONG"\nelse\n  print "word is text"\nend\n'
    )
    assert rt.state["a"]["real"] is None
    assert rt.state["a"]["word"] == "null"
    assert "real is nothing" in out and "word is text" in out and "WRONG" not in out


def test_null_nothing_and_none_mean_the_same():
    rt, _ = _run('create object a\nset a.x to null\nset a.y to nothing\nset a.z to none\n')
    assert rt.state["a"]["x"] is None and rt.state["a"]["y"] is None and rt.state["a"]["z"] is None


def test_a_written_out_list_is_a_real_list():
    rt, out = _run('create object a\nset a.tags to ["p", "q", 3, true, null]\nset n to count of a.tags\nprint "n={n}"\n')
    assert rt.state["a"]["tags"] == ["p", "q", 3, True, None]
    assert "n=5" in out


def test_a_malformed_list_is_an_error_with_its_line():
    with pytest.raises(ValueError) as err:
        _run('create object a\nset a.tags to ["p", "q",]\n')
    assert "line 2" in err.value.args[0] and "as a list" in err.value.args[0]


def test_a_reference_must_point_at_an_existing_object():
    rt, _ = _run('create object b\ncreate object a\nset a.parent to object b\n')
    assert rt.state["a"]["parent"] == "b"  # stored as the name, so exports stay plain
    with pytest.raises(KeyError) as err:
        _run('create object a\nset a.cites to object missing\n')
    assert "no object 'missing'" in err.value.args[0] and "line 2" in err.value.args[0]


def test_a_referenced_object_cannot_be_destroyed_until_released():
    with pytest.raises(KeyError) as err:
        _run('create object b\ncreate object a\nset a.parent to object b\ndestroy b\n')
    assert "a.parent" in err.value.args[0]
    # Releasing the reference, or destroying the referrer, frees it.
    _run('create object b\ncreate object a\nset a.parent to object b\nset a.parent to nothing\ndestroy b\n')
    _run('create object b\ncreate object a\nset a.parent to object b\ndestroy a\ndestroy b\n')


def test_plain_words_are_still_plain_words():
    rt, _ = _run('create object ball\nset ball.color to red\n')
    assert rt.state["ball"]["color"] == "red"
