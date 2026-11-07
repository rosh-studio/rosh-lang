"""Execute the compiled surface, including its existing visible output path."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

import pytest

from rosh_lang.core.parser import parse_string
from rosh_lang.targets._js_codegen import compile_programme
from rosh_lang.targets._js_runtime import JS_RUNTIME


CASES = json.loads((Path(__file__).parents[1] / "conformance/cases.json").read_text())["cases"]
REGRESSIONS = {
    "ref-holds-name", "ref-released", "ref-holder-gone", "do-arg-sees-old-value",
    "when-send", "on-send", "event-payload", "list-add-each", "list-remove",
    "foreach-waits-empty", "do-undefined", "if-number-on-left", "if-value-on-right",
    "arith-chain", "arith-precedence", "text-join-chain",
}


def execute(source):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is required for compiled semantics tests")
    compiled = compile_programme(parse_string(source))
    # The same bootstrap order as web.py and compiled_js.cjs. Function
    # declarations must be available before the init calls at source positions.
    script = r'''
const output = {textContent: "", style: {}};
const canvas = {querySelectorAll() { return []; }, addEventListener() {}};
const document = {
  getElementById(id) { return id === "output" ? output : canvas; },
  addEventListener() {}
};
''' + JS_RUNTIME + '\nlet error = null;\ntry {\n' + (
        'rosh.runWithBudget(function() {\n' + compiled.init_code + '\n' +
        compiled.handler_code + '\n});\nrosh.send("start", {});\n'
    ) + r'''
} catch (e) { error = {name: e.name, message: e.message}; }
console.log(JSON.stringify({state: rosh.state, output: output.textContent, error}));
'''
    result = subprocess.run([node], input=script, text=True, capture_output=True, check=True)
    return json.loads(result.stdout)


def assert_state(state, expected):
    for path, value in expected.items():
        actual = state
        for part in path.split("."):
            actual = actual[part]
        assert actual == value, path


@pytest.mark.parametrize("case", [c for c in CASES if c["id"] in REGRESSIONS], ids=lambda c: c["id"])
def test_compiled_conformance_regressions(case):
    result = execute(case["code"])
    if case["expect"].get("refused"):
        assert result["error"]["name"] == "Error"
        assert "nothing_here" in result["error"]["message"]
        assert "line " in result["error"]["message"]
        assert "Rosh error:" in result["output"]
        assert result["error"]["message"] in result["output"]
    else:
        assert result["error"] is None
    assert_state(result["state"], case["expect"].get("state", {}))


@pytest.mark.parametrize("source, expected", [
    # Sends before a declaration must not reach it; later sends must.
    ('set n to 0\nsend ping\nwhen ping\nset n to n + 1\nend\nsend ping', {"n": 1}),
    ('set n to 0\nsend ping\non ping set n to n + 1\nsend ping', {"n": 1}),
    ('on ping set n to 1\nsend ping\non ping set n to n + 10\nsend ping', {"n": 11}),
    ('set value to 99\nevent ping value\nwhen ping\nset seen to value\nend\nsend ping value=8',
     {"seen": 8, "value": 99}),
    ('when ping\nset seen to value\nend\nsend ping value=missing', {"seen": "missing"}),
    ('set phase to "playing"\nif phase == playing\nset ok to true\nend', {"ok": True}),
    ('set n to 7\non ping when 5 < n set ok to true\nsend ping', {"ok": True}),
    ('set a to 7\nset b to 5\non ping when a > b set ok to true\nsend ping', {"ok": True}),
    ('set n to 20 - 6 / 2 * 3 + 1', {"n": 12}),
    ('set n to "a - b"', {"n": "a - b"}),
    ('set n to "a - b" + "c" + "d"', {"n": "a - bcd"}),
    ('set n to "a" + "b"', {"n": "ab"}),
    ('add 1 to items\nadd 1 to items\nremove 1 from items', {"items": [1]}),
    ('set n to 9\ncreate list items\nfor each v in items\nset n to 0\nend', {"n": 9}),
])
def test_compiled_semantic_edges(source, expected):
    result = execute(source)
    assert result["error"] is None
    assert_state(result["state"], expected)


@pytest.mark.parametrize("source, message", [
    ('set items to 1\nadd 2 to items', "add: 'items' is not a list"),
    ('set items to 1\nfor each v in items\nprint v\nend', "for each: 'items' is not a list"),
    ('add 1 to m.items', "add: 'm.items' is not a list"),
    ('when ping\ndo missing_proc\nend\nsend ping', "nothing called 'missing_proc'"),
    ('on ping do missing_proc\nsend ping', "nothing called 'missing_proc'"),
    ('set n to missing + 1 + 2', "missing has no value yet"),
])
def test_compiled_refusal_is_visible_once(source, message):
    result = execute(source)
    assert result["error"]["name"] == "Error"
    assert message in result["error"]["message"]
    assert "line " in result["error"]["message"]
    assert result["output"].count("Rosh error:") == 1
    assert message in result["output"]


def test_compiled_print_keeps_to_the_text_limit():
    result = execute('set s to "x"\nrepeat 16\nset s to s + s\nend\nprint "{s}{s}"')
    assert "100,000" in result["error"]["message"]


@pytest.mark.parametrize("source, words", [
    ('set n to 8\nif n < "9"\nset ok to false\nend', "can't compare a number with text"),
    ('if nosuch > 1\nset ok to false\nend', "nosuch has no value yet"),
    ('set n to 9\nset n to 1 + 2 / 0', "divided by zero"),
    ('set n to 9\nset n to "a" - 1 + 2', "can't work out"),
    ('repeat 20000\nset n to 1\nend', "10,000"),
    ('set t to "a"\nrepeat t\nset n to 1\nend', "isn't a number of times"),
    ('set n to 5\nset n to "hi"', "holds a number, so it can't take text"),
])
def test_compiled_refuses_what_cant_be_done(source, words):
    assert words in execute(source)["error"]["message"]
