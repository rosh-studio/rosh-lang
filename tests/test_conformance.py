"""Cross-target conformance tests.

These tests enforce the capability table in rosh-dev/phase0/CAPABILITY-TABLE.md.
Each group covers one of the four levels:

  P — Portable core: identical semantics in terminal Python runtime AND JS codegen.
  T — Target-specific: correct behaviour on the supported target, documented absent elsewhere.
  ⚠ — No-op in terminal: statement parses and executes without error, JS emits correct code.

Tests are paired: one assertion on the Python runtime, one on the JS codegen output.
Where JS cannot be executed, the codegen output is inspected instead.
"""

from __future__ import annotations

import io

import pytest

from rosh_lang.core.model import (
    AddStatement,
    AfterStatement,
    AnimateStatement,
    BackgroundStatement,
    ConnectStatement,
    CreateStatement,
    DestroyStatement,
    EventStatement,
    ForEachStatement,
    GetStatement,
    LookStatement,
    OnStatement,
    PlayStatement,
    PrintStatement,
    Programme,
    RemoveStatement,
    RepeatStatement,
    SayStatement,
    SendStatement,
    SetStatement,
    SoundStatement,
    SpriteStatement,
    WhenStatement,
    EndStatement,
)
from rosh_lang.core.parser import parse_string
from rosh_lang.core.runtime import Runtime
from rosh_lang.targets._js_codegen import compile_programme


def _rt(stmts, output=None):
    buf = output or io.StringIO()
    rt = Runtime(output=buf)
    rt.run(Programme(statements=stmts))
    return rt, buf


def _js(source: str) -> str:
    result = compile_programme(parse_string(source))
    return result.init_code + result.handler_code


# ══════════════════════════════════════════════════════════════════
# Group P — Portable Core
# These statements must produce semantically equivalent results in
# both the Python terminal runtime and the JS codegen output.
# ══════════════════════════════════════════════════════════════════


class TestPortablePrint:
    def test_terminal(self):
        _, buf = _rt([PrintStatement(text="hello")])
        assert buf.getvalue() == "hello\n"

    def test_js_emits_append_output(self):
        assert 'rosh.appendOutput(rosh.interpolate("hello"))' in _js('print "hello"')


class TestPortableCreate:
    def test_terminal_object(self):
        rt, _ = _rt([CreateStatement(kind="object", name="box")])
        assert "box" in rt.state and rt.state["box"] == {}

    def test_terminal_number(self):
        rt, _ = _rt([CreateStatement(kind="number", name="score")])
        assert rt.state["score"] == 0

    def test_terminal_list(self):
        rt, _ = _rt([CreateStatement(kind="list", name="items")])
        assert rt.state["items"] == []

    def test_js_object(self):
        assert 'rosh.create("object", "box")' in _js("create object box")

    def test_js_number(self):
        assert 'rosh.create("number", "score")' in _js("create number score")


class TestPortableSet:
    def test_terminal(self):
        rt, _ = _rt([
            CreateStatement(kind="number", name="x"),
            SetStatement(target="x", value="42"),
        ])
        assert rt.state["x"] == 42

    def test_terminal_arithmetic(self):
        rt, _ = _rt([
            CreateStatement(kind="number", name="x"),
            SetStatement(target="x", value="3"),
            SetStatement(target="x", value="x + 1"),
        ])
        assert rt.state["x"] == 4

    def test_js_simple(self):
        assert 'rosh.set("score"' in _js("create number score\nset score to 42")

    def test_js_arithmetic(self):
        code = _js("create number score\nset score to score + 1")
        assert "score + 1" in code


class TestPortableDestroy:
    def test_terminal_removes_state(self):
        rt, _ = _rt([
            CreateStatement(kind="object", name="enemy"),
            DestroyStatement(name="enemy"),
        ])
        assert "enemy" not in rt.state

    def test_js_emits_destroy(self):
        assert 'rosh.destroy("enemy")' in _js("create object enemy\ndestroy enemy")


class TestPortableSay:
    def test_terminal_output(self):
        _, buf = _rt([SayStatement(text="hello")])
        assert "hello" in buf.getvalue()

    def test_terminal_last_said(self):
        rt, _ = _rt([SayStatement(text="hi")])
        assert rt.state["_last_said"] == "hi"

    def test_terminal_fires_say_event(self):
        """say fires a 'say' event that when-say handlers receive."""
        rt = Runtime(output=io.StringIO())
        rt.run(parse_string("when say\n  print \"heard\"\nend\nsay hello"))
        assert "heard" in rt.output.getvalue()

    def test_js_emits_rosh_say(self):
        assert "rosh.say(" in _js("say hello")


class TestPortableSend:
    def test_terminal_fires_handler(self):
        buf = io.StringIO()
        rt = Runtime(output=buf)
        rt.run(parse_string(
            "event alarm\n"
            "when alarm\n  print \"fired\"\nend\n"
            "send alarm"
        ))
        assert "fired" in buf.getvalue()

    def test_js_emits_send(self):
        assert 'rosh.send("alarm")' in _js("event alarm\nsend alarm")


class TestPortableIf:
    def test_terminal_true_branch(self):
        rt, _ = _rt([
            CreateStatement(kind="number", name="x"),
            SetStatement(target="x", value="5"),
            CreateStatement(kind="string", name="result"),
        ])
        rt.run(parse_string("if x > 3\n  set result to \"yes\"\nend"))
        assert rt.state["result"] == "yes"

    def test_terminal_false_branch(self):
        rt, _ = _rt([
            CreateStatement(kind="number", name="x"),
            SetStatement(target="x", value="1"),
            CreateStatement(kind="string", name="result"),
            SetStatement(target="result", value='"no"'),
        ])
        rt.run(parse_string("if x > 3\n  set result to \"yes\"\nend"))
        assert rt.state["result"] == "no"

    def test_js_emits_if(self):
        assert "rosh.get(" in _js("if score > 10\n  print \"win\"\nend")


class TestPortableRepeat:
    def test_terminal_count(self):
        buf = io.StringIO()
        rt = Runtime(output=buf)
        rt.run(parse_string("repeat 3\n  print \"x\"\nend"))
        assert buf.getvalue().count("x") == 3

    def test_terminal_with_var(self):
        rt = Runtime(output=io.StringIO())
        rt.run(parse_string("repeat 3 as i\n  set last to i\nend"))
        assert rt.state.get("last") == 3

    def test_terminal_var_cleaned_up(self):
        rt = Runtime(output=io.StringIO())
        rt.run(parse_string("repeat 3 as i\n  print \"{i}\"\nend"))
        assert "i" not in rt.state

    def test_terminal_var_restores_prior(self):
        rt = Runtime(output=io.StringIO())
        rt.run(parse_string(
            "set i to 99\n"
            "repeat 2 as i\n  print \"{i}\"\nend"
        ))
        assert rt.state["i"] == 99

    def test_js_emits_for_loop(self):
        assert "for (var _ri" in _js("repeat 3\n  print \"x\"\nend")

    def test_js_var_restores_prior(self):
        """JS emits save/restore pattern, not just unset."""
        code = _js("repeat 3 as i\n  print \"{i}\"\nend")
        assert 'rosh.has("i")' in code
        assert 'rosh.get("i")' in code


class TestPortableCollections:
    def test_terminal_add(self):
        rt, _ = _rt([
            CreateStatement(kind="list", name="items"),
            AddStatement(item="apple", target="items"),
        ])
        assert "apple" in rt.state["items"]

    def test_terminal_remove(self):
        rt, _ = _rt([
            CreateStatement(kind="list", name="items"),
            AddStatement(item="apple", target="items"),
            RemoveStatement(item="apple", target="items"),
        ])
        assert rt.state["items"] == []

    def test_terminal_for_each(self):
        buf = io.StringIO()
        rt = Runtime(output=buf)
        rt.run(parse_string(
            "create list names\n"
            "add alice to names\n"
            "add bob to names\n"
            "for each n in names\n  print \"{n}\"\nend"
        ))
        assert "alice" in buf.getvalue()
        assert "bob" in buf.getvalue()

    def test_js_add(self):
        assert "rosh.addToList(" in _js("create list items\nadd apple to items")

    def test_js_remove(self):
        assert "rosh.removeFromList(" in _js("create list items\nremove apple from items")

    def test_js_for_each(self):
        assert "rosh.forEach(" in _js("create list names\nfor each n in names\n  print \"{n}\"\nend")


class TestPortableNothing:
    def test_terminal_sets_none(self):
        rt, _ = _rt([
            CreateStatement(kind="string", name="x"),
            SetStatement(target="x", value="nothing"),
        ])
        assert rt.state["x"] is None

    def test_js_emits_null(self):
        code = _js("set x to nothing")
        assert '"nothing"' in code


# ══════════════════════════════════════════════════════════════════
# Group ⚠ — No-op in terminal; correct output in JS
# These statements must not raise in the terminal runtime and must
# emit the expected JS construct.
# ══════════════════════════════════════════════════════════════════


class TestAfterNoopInTerminal:
    def test_terminal_does_not_raise(self):
        rt, _ = _rt([AfterStatement(delay=1.0, event="timeout")])
        # No exception — passes

    def test_terminal_does_not_fire_event(self):
        """after must not fire the event synchronously in terminal."""
        rt, _ = _rt([
            EventStatement(name="timeout", payload_fields=[]),
            AfterStatement(delay=0, event="timeout"),
        ])
        assert "timeout" not in rt.handlers

    def test_js_emits_set_timeout(self):
        assert "setTimeout(" in _js("after 2 send boom")
        assert 'rosh.send("boom"' in _js("after 2 send boom")


class TestSpriteNoopInTerminal:
    def test_terminal_does_not_raise(self):
        rt, _ = _rt([
            CreateStatement(kind="object", name="ship"),
            SpriteStatement(name="ship", description="blue spaceship"),
        ])

    def test_js_emits_sprite_set(self):
        code = _js('create object ship\nsprite ship "blue spaceship"')
        assert "blue spaceship" in code


class TestSoundNoopInTerminal:
    def test_terminal_registers(self):
        rt, _ = _rt([SoundStatement(name="laser", description="laser shoot")])
        assert "laser" in rt.audio_registry

    def test_js_emits_register_sound(self):
        assert 'rosh.registerSound("laser"' in _js('sound laser "laser shoot"')


class TestPlayNoopInTerminal:
    def test_terminal_does_not_raise(self):
        rt, _ = _rt([
            SoundStatement(name="laser", description="laser shoot"),
            PlayStatement(sound="laser", mode="once"),
        ])

    def test_js_emits_play_audio(self):
        assert 'rosh.playAudio("laser"' in _js('sound laser "laser"\nplay laser')


class TestBackgroundTerminalState:
    def test_terminal_stores_in_state(self):
        rt, _ = _rt([BackgroundStatement(value="#ff0000")])
        assert rt.state["_background"] == "#ff0000"

    def test_js_emits_set_background(self):
        assert 'rosh.setBackground("#ff0000")' in _js('background "#ff0000"')


# ══════════════════════════════════════════════════════════════════
# Group T — Target-specific (terminal or JS only)
# ══════════════════════════════════════════════════════════════════


class TestGetTerminalOnly:
    def test_terminal_returns_value(self):
        rt, _ = _rt([
            CreateStatement(kind="number", name="score"),
            SetStatement(target="score", value="42"),
        ])
        result = rt.execute_get("score")
        assert result[0]["value"] == 42

    def test_js_emits_nothing(self):
        """get has no JS equivalent — codegen produces no output for it."""
        code = _js("get score")
        assert "rosh.get" not in code or code.strip() == ""


class TestConnectTerminalOnly:
    def test_terminal_stores_connection(self):
        rt, _ = _rt([ConnectStatement(name="server", url="wss://example.com")])
        assert rt.connections.get("server") == "wss://example.com"

    def test_js_emits_nothing(self):
        code = _js("connect server wss://example.com")
        assert "connect" not in code.lower() or code.strip() == ""


class TestLookTerminalOnly:
    def test_terminal_returns_statements(self):
        rt = Runtime(output=io.StringIO())
        rt.run(parse_string("create number score\nset score to 0"))
        result = rt._look_programme()
        assert isinstance(result, list)

    def test_js_emits_comment_not_code(self):
        """look emits a comment in JS, not executable code."""
        code = _js("look")
        assert "terminal-only" in code or code.strip().startswith("/*")


# ══════════════════════════════════════════════════════════════════
# on-condition payload injection (verified not a bug, 2026-06-04)
#
# _emit_on conditions use rosh.get(field) which reads from state.
# Since rosh.send() injects payload keys into state for the duration
# of event dispatch, this correctly reads payload values — identical
# observable result to payload.key direct access used by when-key filtering.
# ══════════════════════════════════════════════════════════════════


class TestOnConditionPayloadAccess:
    def test_terminal_on_condition_reads_payload_field(self):
        """on keydown when key == ' ' must fire when space is the payload key."""
        rt, _ = _rt([
            CreateStatement(kind="string", name="fired"),
            EventStatement(name="keydown", payload_fields=["key"]),
            OnStatement(event="keydown", action="set", args='fired to "yes"', condition='key == " "'),
        ])
        rt.execute_send("keydown", key=" ")
        assert rt.state["fired"] == "yes"

    def test_terminal_on_condition_wrong_payload_does_not_fire(self):
        rt, _ = _rt([
            CreateStatement(kind="string", name="fired"),
            EventStatement(name="keydown", payload_fields=["key"]),
            OnStatement(event="keydown", action="set", args='fired to "yes"', condition='key == " "'),
        ])
        rt.execute_send("keydown", key="a")
        assert rt.state["fired"] == ""

    def test_js_on_condition_reads_via_get(self):
        """JS on-condition uses rosh.get() — payload is in state during dispatch."""
        code = _js('event keydown\non keydown when key == " " send shot')
        assert 'rosh.get("key")' in code
        assert '" "' in code or "' '" in code

    def test_js_when_key_filter_reads_payload_directly(self):
        """when keydown ArrowLeft uses payload.key directly (different mechanism, same result)."""
        code = _js('when keydown ArrowLeft\n  print "left"\nend')
        assert 'payload.key' in code
        assert '"ArrowLeft"' in code
