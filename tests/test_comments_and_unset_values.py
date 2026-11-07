"""Nothing lost quietly, in either direction."""

import io
import json
import random
import shutil
import subprocess

import pytest

from rosh_lang.core.parser import parse_string
from rosh_lang.core.runtime import Runtime
from rosh_lang.data import from_rosh, same, to_rosh
from rosh_lang.repl.kernel import ReplKernel
from rosh_lang.repl.runtime_adapter import RuntimeAdapter
from rosh_lang.targets._js_codegen import compile_programme
from rosh_lang.targets._js_runtime import JS_RUNTIME_CORE


def _state(text, normalise=False):
    rt = Runtime(output=io.StringIO())
    rt.run(parse_string(text, normalise=normalise))
    return rt.state


# ── #34: `# note` after code is a comment ────────────────────


@pytest.mark.parametrize("normalise", [False, True])
def test_a_comment_after_code_isnt_part_of_the_name(normalise):
    assert set(_state("create object chair  # note", normalise)) == {"chair"}


@pytest.mark.parametrize("normalise", [False, True])
def test_a_comment_after_a_value_isnt_part_of_it(normalise):
    assert _state('create object a\nset a.x to 12  # from the left', normalise)["a"]["x"] == 12
    assert _state('create object a\nset a.t to "hi"  # note', normalise)["a"]["t"] == "hi"


@pytest.mark.parametrize("normalise", [False, True])
def test_a_hash_in_quotes_is_text(normalise):
    assert _state('create object a\nset a.t to "no # note"', normalise)["a"]["t"] == "no # note"
    assert _state('create object a\nset a.t to "a\\" # b"', normalise)["a"]["t"] == 'a" # b'


def test_a_hex_colour_isnt_a_comment():
    assert _state("create object a\nset a.color to #00ff88")["a"]["color"] == "#00ff88"


def test_an_apostrophe_doesnt_hide_a_comment():
    assert _state("create object a\nset a.t to Rosh's  # note")["a"]["t"] == "Rosh's"


def test_other_backslashes_stay_as_written():
    assert _state('create object a\nset a.t to "C:\\new"')["a"]["t"] == "C:\\new"


def test_say_and_print_read_the_same_escapes():
    rt = Runtime(output=io.StringIO())
    rt.run(parse_string('print "she said \\"hi\\""  # note', normalise=False))
    assert rt.output.getvalue().strip() == 'she said "hi"'


def test_data_keeps_every_awkward_string():
    awkward = ['a" # b', 'a\\', '\\"', '"', "#", " # ", 'x\\" # y', "\\\\", 'end\\" ', "it's # fine", "#00ff88"]
    doc = {"objects": {"a": {f"p{i}": v for i, v in enumerate(awkward)}}, "meta": {}}
    assert same(from_rosh(to_rosh(doc)), doc)


def test_data_keeps_random_strings():
    rng = random.Random(34)
    for _ in range(500):
        value = "".join(rng.choice('ab"\\# \'') for _ in range(rng.randint(0, 12)))
        doc = {"objects": {"a": {"t": value, "l": [value, "z"]}}, "meta": {}}
        assert same(from_rosh(to_rosh(doc)), doc), repr(value)


def test_data_read_by_hand_takes_a_comment():
    assert from_rosh('create object a  # one\nset a.t to "x"  # two')["objects"]["a"]["t"] == "x"


# ── #33: an expression with no value is an error ─────────────


def test_a_score_with_no_value_is_an_error_that_names_it():
    with pytest.raises(ValueError, match=r"set score \(line 1\): score has no value yet"):
        _state("set score to score + 1")


def test_the_score_works_once_it_has_a_value():
    assert _state("set score to 0\nset score to score + 1")["score"] == 1
    assert _state("create number score\nset score to score + 1")["score"] == 1


def test_text_with_an_operator_says_to_quote_it():
    with pytest.raises(ValueError, match="put text in quotes"):
        _state("set title to Room A - B")
    assert _state('set title to "Room A - B"')["title"] == "Room A - B"


def test_text_times_a_number_is_an_error():
    with pytest.raises(ValueError, match="can't work out a \\* 2"):
        _state('set a to "x"\nset a to a * 2')


def test_two_operators_arent_a_missing_value():
    # More than one operator works now (6 Nov); it used to leave the 7 alone.
    assert _state("set total to 7\nset total to 1 + 2 + 3")["total"] == 6
    with pytest.raises(ValueError, match="b has no value yet"):
        _state("set total to b + 2 + 3")


def test_a_handler_says_so_when_it_runs():
    rt = Runtime(output=io.StringIO())
    rt.run(parse_string("when click\n  set score to score + 1\nend", normalise=False))
    with pytest.raises(ValueError, match="score has no value yet"):
        rt.execute_send("click")


# ── The REPL sends a number for what was never set ───────────


@pytest.mark.parametrize("line,prop,value", [
    ("make it bigger", "width", 0.125),
    ("make it bigger", "depth", 0.125),
    ("make it smaller", "height", 0.075),
    ("move it left", "x", 0.4),
    ("move it down", "y", 0.6),
])
def test_repl_changes_what_was_never_set(line, prop, value):
    kernel = ReplKernel(RuntimeAdapter())
    assert kernel.process_line("create object chair").status == "ok"
    kernel.current_subject = "chair"
    assert kernel.process_line(line).status == "ok"
    assert kernel.adapter.runtime.state["chair"][prop] == value


def test_repl_still_scales_what_was_set():
    kernel = ReplKernel(RuntimeAdapter())
    kernel.process_line("create a big red ball")
    assert kernel.process_line("make it bigger").status == "ok"
    assert kernel.adapter.runtime.state["ball"]["width"] == pytest.approx(0.2)


def test_repl_reports_a_score_with_no_value():
    response = ReplKernel(RuntimeAdapter()).process_line("set score to score + 1")
    assert response.status == "error"
    assert "score has no value yet" in str(response.error)


# ── The same in generated pages ──────────────────────────────


def _js(source):
    """Run `source` as a generated page would: (state, error message or None)."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is required for generated JS execution tests")
    compiled = compile_programme(parse_string(source))
    script = "\n".join([
        JS_RUNTIME_CORE,
        "var failed = null;",
        "try { rosh.runWithBudget(function() {",
        compiled.init_code,
        compiled.handler_code,
        "}); } catch (e) { failed = e.message; }",
        "console.log(JSON.stringify({state: rosh.state, failed: failed}));",
    ])
    done = subprocess.run([node], input=script, capture_output=True, text=True, check=False)
    assert done.returncode == 0, done.stderr
    out = json.loads(done.stdout.strip().splitlines()[-1])
    return out["state"], out["failed"]


def test_page_says_a_score_has_no_value():
    state, failed = _js("set score to score + 1")
    assert "score has no value yet" in failed
    assert "score" not in state or state["score"] != "score + 1"


def test_page_counts_once_there_is_a_score():
    state, failed = _js("set score to 0\nset score to score + 1")
    assert failed is None and state["score"] == 1


def test_page_refuses_text_times_a_number():
    state, failed = _js('set a to "x"\nset a to a * 2')
    assert "can't work out a * 2" in failed and state["a"] == "x"


def test_page_doesnt_call_two_operators_a_missing_value():
    state, failed = _js("set total to 7\nset total to 1 + 2 + 3")
    assert failed is None and state["total"] == 6


def test_page_reads_escapes_as_python_does():
    source = 'create object a\nset a.t to "she said \\"hi\\" \\\\ # no"  # note'
    state, failed = _js(source)
    assert failed is None
    assert state["a"]["t"] == _state(source)["a"]["t"] == 'she said "hi" \\ # no'
