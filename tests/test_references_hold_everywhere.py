"""A checked reference means the same thing in both engines, and points at
something real after every change. Temporary names leave on every way out.

"""
import io
import random
import runpy
from pathlib import Path

import pytest

from rosh_lang.core.parser import parse_string
from rosh_lang.core.runtime import Runtime

execute_js = runpy.run_path(str(Path(__file__).with_name("test_js_semantics.py")))["execute"]


def python(source):
    runtime = Runtime(output=io.StringIO())
    error = None
    try:
        runtime.run(parse_string(source))
    except Exception as exc:
        error = str(exc)
    return runtime, {k: v for k, v in runtime.state.items() if not k.startswith("_")}, error


def both(source):
    _, py_state, py_error = python(source)
    js = execute_js(source)
    js_state = {k: v for k, v in js["state"].items() if not k.startswith("_")}
    js_error = (js["error"] or {}).get("message")
    return py_state, py_error, js_state, js_error


PAIR = "create object lamp\ncreate object table\nset lamp.parent to object table\n"
INNER = "create object lamp\ncreate object b\ncreate object b.child\nset lamp.parent to object b.child\n"


@pytest.mark.parametrize("source, words", [
    (PAIR + "destroy table", "lamp.parent still refers"),
    (PAIR + "set table to nothing", "lamp.parent still refers"),
    (INNER + "destroy b", "lamp.parent still refers"),
    (INNER + "set b to nothing", "lamp.parent still refers"),
    (INNER + "destroy b.child", "lamp.parent still refers"),
    ("create object lamp\nset lamp.parent to object nowhere", "no object 'nowhere'"),
    (PAIR + "event ping\non ping destroy table\nsend ping", "lamp.parent still refers"),
])
def test_both_engines_refuse_what_would_break_a_reference(source, words):
    py_state, py_error, js_state, js_error = both(source)
    assert py_error and words in py_error
    assert js_error and words in js_error
    assert py_state == js_state


@pytest.mark.parametrize("source, gone", [
    (PAIR + "set lamp.parent to nothing\ndestroy table", "table"),
    (PAIR + 'set lamp.parent to "x"\ndestroy table', "table"),
    (PAIR + "set lamp to nothing\ndestroy table", "table"),
    (PAIR + "destroy lamp\ndestroy table", "table"),
    ("create object table\nset n to object table\ndestroy n\ndestroy table", "table"),
])
def test_once_nothing_points_at_it_it_can_go(source, gone):
    py_state, py_error, js_state, js_error = both(source)
    assert py_error is None and js_error is None, (py_error, js_error)
    assert gone not in py_state and gone not in js_state
    assert py_state == js_state


def test_both_engines_store_the_name():
    py_state, _, js_state, _ = both(PAIR)
    assert py_state["lamp"]["parent"] == "table" == js_state["lamp"]["parent"]


def test_a_reference_can_be_refused_like_any_other_change_of_kind():
    py_state, py_error, js_state, js_error = both("create object t\nset n to 4\nset n to object t")
    assert "holds a number" in py_error and "holds a number" in js_error
    assert py_state["n"] == 4 == js_state["n"]


def test_forget_keeps_the_reference_honest():
    _, _, error = python("create object a\ncreate object a.b\ncreate object c\nset c.p to object a.b\nforget a.b")
    assert error and "c.p still refers" in error
    runtime, _, error = python("create object a\ncreate object t\nset a.p.q to object t\nforget a.p\ndestroy t")
    assert error is None and runtime.references == {}


def _steps():
    names = ["a", "b", "a.x", "b.x"]
    return [f"set {t} to object {n}" for t in ("a.p", "b.p", "a.x.p") for n in names] + \
           [f"destroy {n}" for n in names] + [f"set {n} to nothing" for n in names] + \
           ["set a.p to nothing", "set b.p to 5", "create object a", "create object b",
            "create object a.x", "create object b.x"]


def _broken(runtime):
    return [(t, n) for t, n in runtime.references.items()
            if runtime._resolve(t) != n or not isinstance(runtime._resolve(n), dict)]


@pytest.mark.parametrize("seed", range(40))
def test_no_order_of_changes_leaves_a_broken_reference(seed):
    chooser = random.Random(seed)
    runtime = Runtime(output=io.StringIO())
    runtime.run(parse_string("create object a\ncreate object b\ncreate object a.x\ncreate object b.x"))
    steps = _steps()
    for _ in range(80):
        line = chooser.choice(steps)
        try:
            runtime.run(parse_string(line))
        except Exception:
            pass
        assert not _broken(runtime), (line, runtime.references, runtime.state)


# Temporary names


BODY_FAILS = "set value to 99\ndefine f with value\ndo missing_proc\nend\ndo f value=7"
ARG_FAILS = "set first to 10\nset second to 20\ndefine f with first second\nset touched to 1\nend\ndo f first=1 second=1e309"
ABSENT = "define f with fresh\ndo missing_proc\nend\ndo f fresh=7"
NESTED = "set v to 1\ndefine inner with v\ndo missing_proc\nend\ndefine outer with v\ndo inner v=3\nend\ndo outer v=2"


@pytest.mark.parametrize("source, want", [
    (BODY_FAILS, {"value": 99}),
    (ARG_FAILS, {"first": 10, "second": 20}),
    (NESTED, {"v": 1}),
])
def test_a_failed_call_puts_every_name_back(source, want):
    py_state, py_error, js_state, js_error = both(source)
    assert py_error and js_error
    for name, value in want.items():
        assert py_state[name] == value == js_state[name], name
    assert "touched" not in py_state and "touched" not in js_state


def test_a_name_that_was_not_there_stays_not_there():
    py_state, _, js_state, _ = both(ABSENT)
    assert "fresh" not in py_state and "fresh" not in js_state


def test_arguments_are_worked_out_before_any_of_them_is_bound():
    source = "set a to 1\nset seen to 0\ndefine f with a b\nset seen to b\nend\ndo f a=5 b=a"
    py_state, py_error, js_state, js_error = both(source)
    assert py_error is None and js_error is None
    assert py_state["seen"] == 1 == js_state["seen"]
    assert py_state["a"] == 1 == js_state["a"]


# Temporary names and scenes


def test_a_parameter_gives_back_the_reference_it_hid():
    source = ("create object table\nset p to object table\ndefine f with p\nset p to 3\nend\n"
              "do f p=1\ndestroy table")
    py_state, py_error, js_state, js_error = both(source)
    assert py_error and "p still refers" in py_error
    assert js_error and "p still refers" in js_error
    assert py_state["p"] == "table" == js_state["p"]


@pytest.mark.parametrize("source", [
    "set items to [1]\nfor each table in items\nset table to nothing\nend",
    "define f with table\nset table to nothing\nend\ndo f table=1",
    "repeat 2 as table\nset table to nothing\nend",
    "event ping table\nwhen ping\nset table to nothing\nend\nsend ping table=1",
])
def test_a_temporary_name_isnt_the_thing_it_hides(source):
    py_state, py_error, js_state, js_error = both("create object table\nset p to object table\n" + source)
    assert py_error is None and js_error is None, (py_error, js_error)
    assert isinstance(py_state["table"], dict) and isinstance(js_state["table"], dict)


def test_a_reference_to_a_temporary_name_goes_with_it():
    runtime, _, error = python("create object lamp\ndefine f with thing\nset lamp.p to object thing\nend\ndo f")
    assert error and "no object" in error
    assert runtime.references == {}


def test_entering_a_scene_cant_take_away_what_a_reference_needs():
    source = "create object table\nset p to object table\ncreate scene hall\nset hall.table to nothing\ngo hall"
    runtime, py_state, py_error = python(source)
    js = execute_js(source)
    assert py_error and "p still refers" in py_error
    assert js["error"] and "p still refers" in js["error"]["message"]
    assert isinstance(py_state["table"], dict) and isinstance(js["state"]["table"], dict)


def test_a_reference_in_a_scene_stays_in_the_scene():
    runtime, py_state, py_error = python("create scene hall\ncreate object table\nset hall.parent to object table")
    assert py_error is None and "hall" not in py_state
    assert runtime.scenes["hall"]["parent"] == "table"
    runtime.prune_references()
    assert runtime.references == {"hall.parent": "table"}
    _, _, error = python("create scene hall\ncreate object table\nset hall.parent to object table\ndestroy table")
    assert error and "hall.parent still refers" in error


# Procedures in source order


def test_a_call_above_its_definition_is_refused_everywhere():
    py_state, py_error, js_state, js_error = both("do later\ndefine later\nset result to 1\nend")
    assert "nothing called 'later'" in py_error and "nothing called 'later'" in js_error
    assert "result" not in py_state and "result" not in js_state


def test_a_later_definition_replaces_from_there_on():
    source = "define f\nset a to 1\nend\ndo f\nset first to a\ndefine f\nset a to 2\nend\ndo f"
    py_state, py_error, js_state, js_error = both(source)
    assert py_error is None and js_error is None
    assert (py_state["first"], py_state["a"]) == (1, 2) == (js_state["first"], js_state["a"])


def test_a_handler_may_call_what_is_defined_by_the_time_it_runs():
    source = "event ping\nwhen ping\ndo later\nend\ndefine later\nset done to 1\nend\nsend ping"
    py_state, py_error, js_state, js_error = both(source)
    assert py_error is None and js_error is None
    assert py_state["done"] == 1 == js_state["done"]


def test_a_procedure_cant_call_itself_in_either_engine():
    py_state, py_error, js_state, js_error = both("define f\ndo f\nend\ndo f")
    assert "ecursive call" in py_error and "ecursive call" in js_error


@pytest.mark.parametrize("name", ["__proto__", "constructor", "a-b", "x.y"])
def test_odd_procedure_names_are_just_names(name):
    py_state, py_error, js_state, js_error = both(f"do {name}")
    assert py_error and js_error and "has been defined" in js_error
    py_state, py_error, js_state, js_error = both(f"define {name}\nset done to 1\nend\ndo {name}")
    assert py_error is None and js_error is None and js_state["done"] == 1
