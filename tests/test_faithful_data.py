"""Task 19: a data document goes to Rosh and back exactly (roadmap step 1, part).

The 15 Oct fixes themselves are pinned in test_honest_data.py; this is the
document round trip. Fixtures are shared with the portal's vendored copy
(rosh-portal/tests/test_faithful_data_vendored.py).
"""

import json
import math
from pathlib import Path

import pytest

from rosh_lang.data import DataError, from_rosh, same, to_rosh

FIXTURES = Path(__file__).parent / "fixtures" / "faithful"
GOOD = sorted((FIXTURES / "good").glob("*.json"))
BAD = sorted((FIXTURES / "bad").glob("*.json"))


@pytest.mark.parametrize("path", GOOD, ids=[p.stem for p in GOOD])
def test_a_document_comes_back_exactly(path):
    doc = json.loads(path.read_text())
    back = from_rosh(to_rosh(doc))
    assert same(back, doc), (back, doc)


@pytest.mark.parametrize("path", BAD, ids=[p.stem for p in BAD])
def test_outside_the_subset_is_an_error_that_says_where(path):
    case = json.loads(path.read_text())
    with pytest.raises(DataError) as caught:
        if "doc" in case:
            to_rosh(case["doc"])
        else:
            from_rosh(case["rosh"])
    assert case["error"] in str(caught.value)


def test_same_minds_types():
    assert not same(1, 1.0) and not same(1, True) and not same(None, "null")
    assert not same([1], [1.0]) and same({"a": [1.0]}, {"a": [1.0]})


def test_the_canonical_path_skips_the_normaliser():
    # The normaliser renames `colour` and cut a string at `" #` (1 Nov).
    from rosh_lang.core.parser import parse_string
    from rosh_lang.core.runtime import Runtime
    runtime = Runtime()
    runtime.run(parse_string('create object a\nset a.colour to "a\\" # b"', normalise=False))
    assert runtime.state["a"] == {"colour": 'a" # b'}


def test_floats_stay_floats():
    text = to_rosh({"objects": {"a": {"x": 1e20}}, "meta": {}})
    assert "100000000000000000000.0" in text
    assert isinstance(from_rosh(text)["objects"]["a"]["x"], float)
    with pytest.raises(DataError):
        to_rosh({"objects": {"a": {"x": math.inf}}, "meta": {}})
