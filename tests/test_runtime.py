"""Tests for the Rosh runtime — all 16 keywords + compliance tests.

Follows BUILDING-ROSH.md Section 12 compliance tests inline.
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from rosh_lang.model import (
    AfterStatement,
    AnimateStatement,
    BackgroundStatement,
    BlankStatement,
    CommentStatement,
    ConnectStatement,
    CreateStatement,
    DestroyStatement,
    EndStatement,
    EventStatement,
    GetStatement,
    GoStatement,
    LookStatement,
    OnStatement,
    PlayStatement,
    PrintStatement,
    Programme,
    SayStatement,
    SendStatement,
    SetStatement,
    SoundStatement,
    SpriteStatement,
    WhenStatement,
)
from rosh_lang.runtime import Runtime, run


def _run(stmts: list, *, output: io.StringIO | None = None) -> Runtime:
    """Helper: run a list of statements, return the runtime."""
    buf = output or io.StringIO()
    rt = Runtime(output=buf)
    rt.run(Programme(statements=stmts))
    rt.output = buf
    return rt


def _output(rt: Runtime) -> str:
    """Get output text from a runtime whose output is a StringIO."""
    return rt.output.getvalue()


def _run_with_scenes(
    stmts: list,
    scenes: dict[str, dict],
    initial_scene: str = "",
) -> Runtime:
    """Helper: run with pre-configured scenes."""
    buf = io.StringIO()
    rt = Runtime(output=buf)
    rt.scenes = scenes
    if initial_scene:
        rt.state["_scene"] = initial_scene
    rt.run(Programme(statements=stmts))
    rt.output = buf
    return rt


# ══════════════════════════════════════════════════════════════
# Group 1: print, create, set, when/end
# ══════════════════════════════════════════════════════════════


class TestPrintExecution:
    def test_hello_world(self) -> None:
        rt = _run([PrintStatement(text="hello world")])
        assert _output(rt) == "hello world\n"

    def test_print_multiple(self) -> None:
        rt = _run([
            PrintStatement(text="line one"),
            PrintStatement(text="line two"),
        ])
        assert _output(rt) == "line one\nline two\n"

    def test_print_interpolation(self) -> None:
        rt = _run([
            CreateStatement(kind="number", name="score"),
            SetStatement(target="score", value="42"),
            PrintStatement(text="Score: {score}"),
        ])
        assert _output(rt) == "Score: 42\n"

    def test_print_dot_interpolation(self) -> None:
        rt = _run([
            CreateStatement(kind="object", name="player"),
            SetStatement(target="player.health", value="100"),
            PrintStatement(text="HP: {player.health}"),
        ])
        assert _output(rt) == "HP: 100\n"

    def test_print_missing_var(self) -> None:
        """Missing vars are left as {name} — no crash."""
        rt = _run([PrintStatement(text="Hello {nobody}")])
        assert _output(rt) == "Hello {nobody}\n"

    # Compliance P1
    def test_compliance_p1_basic_output(self) -> None:
        rt = _run([PrintStatement(text="hello")])
        assert _output(rt) == "hello\n"

    # Compliance P2
    def test_compliance_p2_interpolation(self) -> None:
        rt = _run([
            CreateStatement(kind="number", name="x"),
            SetStatement(target="x", value="42"),
            PrintStatement(text="x is {x}"),
        ])
        assert _output(rt) == "x is 42\n"

    # Compliance P3
    def test_compliance_p3_missing_var(self) -> None:
        rt = _run([PrintStatement(text="{ghost}")])
        assert _output(rt) == "{ghost}\n"


class TestCreateExecution:
    def test_create_object(self) -> None:
        rt = _run([CreateStatement(kind="object", name="player")])
        assert rt.state["player"] == {}

    def test_create_number(self) -> None:
        rt = _run([CreateStatement(kind="number", name="score")])
        assert rt.state["score"] == 0

    def test_create_string(self) -> None:
        rt = _run([CreateStatement(kind="string", name="name")])
        assert rt.state["name"] == ""

    def test_create_list(self) -> None:
        rt = _run([CreateStatement(kind="list", name="items")])
        assert rt.state["items"] == []

    def test_create_with_parent(self) -> None:
        rt = _run([
            CreateStatement(kind="object", name="base"),
            SetStatement(target="base.health", value="100"),
            CreateStatement(kind="object", name="hero", parent="base"),
        ])
        assert rt.state["hero"] == {"health": 100}
        assert rt.state["hero"] is not rt.state["base"]

    def test_create_unknown_kind_defaults_to_object(self) -> None:
        rt = _run([CreateStatement(kind="widget", name="w")])
        assert rt.state["w"] == {}


class TestSetExecution:
    def test_set_simple(self) -> None:
        rt = _run([SetStatement(target="x", value="100")])
        assert rt.state["x"] == 100

    def test_set_property(self) -> None:
        rt = _run([
            CreateStatement(kind="object", name="player"),
            SetStatement(target="player.health", value="75"),
        ])
        assert rt.state["player"]["health"] == 75

    def test_set_string_value(self) -> None:
        rt = _run([SetStatement(target="name", value='"Alice"')])
        assert rt.state["name"] == "Alice"

    def test_set_number_coercion(self) -> None:
        rt = _run([SetStatement(target="x", value="100")])
        assert isinstance(rt.state["x"], int)

    def test_set_float_coercion(self) -> None:
        rt = _run([SetStatement(target="speed", value="3.14")])
        assert rt.state["speed"] == 3.14

    def test_set_boolean_true(self) -> None:
        rt = _run([SetStatement(target="flag", value="true")])
        assert rt.state["flag"] is True

    def test_set_deep_property(self) -> None:
        rt = _run([
            CreateStatement(kind="object", name="player"),
            SetStatement(target="player.pos.x", value="10"),
        ])
        assert rt.state["player"]["pos"]["x"] == 10

    # Arithmetic
    def test_set_arithmetic_add(self) -> None:
        rt = _run([
            CreateStatement(kind="number", name="score"),
            SetStatement(target="score", value="10"),
            SetStatement(target="score", value="score + 5"),
        ])
        assert rt.state["score"] == 15

    def test_set_arithmetic_subtract(self) -> None:
        rt = _run([
            CreateStatement(kind="number", name="health"),
            SetStatement(target="health", value="100"),
            SetStatement(target="health", value="health - 25"),
        ])
        assert rt.state["health"] == 75

    def test_set_arithmetic_multiply(self) -> None:
        rt = _run([
            CreateStatement(kind="number", name="speed"),
            SetStatement(target="speed", value="5"),
            SetStatement(target="speed", value="speed * 2"),
        ])
        assert rt.state["speed"] == 10

    def test_set_arithmetic_divide(self) -> None:
        rt = _run([
            CreateStatement(kind="number", name="half"),
            SetStatement(target="half", value="10"),
            SetStatement(target="half", value="half / 2"),
        ])
        assert rt.state["half"] == 5.0

    def test_set_arithmetic_float(self) -> None:
        rt = _run([
            CreateStatement(kind="number", name="x"),
            SetStatement(target="x", value="0"),
            SetStatement(target="x", value="x + 0.01"),
        ])
        assert rt.state["x"] == pytest.approx(0.01)

    def test_set_arithmetic_dotted_target(self) -> None:
        rt = _run([
            CreateStatement(kind="object", name="player"),
            SetStatement(target="player.health", value="100"),
            SetStatement(target="player.health", value="player.health - 10"),
        ])
        assert rt.state["player"]["health"] == 90

    def test_set_arithmetic_non_numeric_noop(self) -> None:
        """Arithmetic on non-numeric value is a no-op."""
        rt = _run([
            SetStatement(target="name", value='"Alice"'),
            SetStatement(target="name", value="name + 1"),
        ])
        # Should fall back to raw string since Alice isn't numeric
        assert rt.state["name"] == "name + 1"

    def test_set_arithmetic_undefined_left_falls_through(self) -> None:
        """Left operand that doesn't resolve falls through to raw string."""
        rt = _run([
            CreateStatement(kind="number", name="a"),
            SetStatement(target="a", value="5"),
            SetStatement(target="a", value="b + 1"),
        ])
        # "b" doesn't exist so not arithmetic — stored as raw string
        assert rt.state["a"] == "b + 1"

    def test_set_arithmetic_variable_right_operand(self) -> None:
        """set x to x + drift — variable right operand."""
        rt = _run([
            CreateStatement(kind="number", name="x"),
            SetStatement(target="x", value="10"),
            CreateStatement(kind="number", name="drift"),
            SetStatement(target="drift", value="3"),
            SetStatement(target="x", value="x + drift"),
        ])
        assert rt.state["x"] == 13

    def test_set_arithmetic_cross_reference_left(self) -> None:
        """set x to y + 1 — cross-reference left, literal right."""
        rt = _run([
            CreateStatement(kind="number", name="x"),
            CreateStatement(kind="number", name="y"),
            SetStatement(target="y", value="20"),
            SetStatement(target="x", value="y + 1"),
        ])
        assert rt.state["x"] == 21

    def test_set_arithmetic_both_variable(self) -> None:
        """set x to y + z — both variable operands."""
        rt = _run([
            CreateStatement(kind="number", name="x"),
            CreateStatement(kind="number", name="y"),
            SetStatement(target="y", value="7"),
            CreateStatement(kind="number", name="z"),
            SetStatement(target="z", value="3"),
            SetStatement(target="x", value="y + z"),
        ])
        assert rt.state["x"] == 10

    def test_set_arithmetic_variable_right_dotted(self) -> None:
        """set obj.x to obj.x + drift — dotted names with variable right."""
        rt = _run([
            CreateStatement(kind="object", name="obj"),
            SetStatement(target="obj.x", value="0.5"),
            CreateStatement(kind="number", name="drift"),
            SetStatement(target="drift", value="0.003"),
            SetStatement(target="obj.x", value="obj.x + drift"),
        ])
        assert rt.state["obj"]["x"] == pytest.approx(0.503)

    # Random
    def test_set_random_bare(self) -> None:
        """set x to random — produces float in [0, 1)."""
        rt = _run([SetStatement(target="x", value="random")])
        assert isinstance(rt.state["x"], float)
        assert 0.0 <= rt.state["x"] < 1.0

    def test_set_random_range(self) -> None:
        """set x to random 0.1 0.9 — produces float in [0.1, 0.9)."""
        rt = _run([SetStatement(target="x", value="random 0.1 0.9")])
        assert isinstance(rt.state["x"], float)
        assert 0.1 <= rt.state["x"] < 0.9

    # Clamp
    def test_set_clamp(self) -> None:
        """set x to clamp x 0.0 1.0 — constrains to range."""
        rt = _run([
            SetStatement(target="x", value="1.5"),
            SetStatement(target="x", value="clamp x 0.0 1.0"),
        ])
        assert rt.state["x"] == 1.0

    def test_set_clamp_lower(self) -> None:
        """Clamp enforces minimum."""
        rt = _run([
            SetStatement(target="x", value="-0.5"),
            SetStatement(target="x", value="clamp x 0.0 1.0"),
        ])
        assert rt.state["x"] == 0.0

    def test_set_clamp_within_range(self) -> None:
        """Clamp leaves values within range unchanged."""
        rt = _run([
            SetStatement(target="x", value="0.5"),
            SetStatement(target="x", value="clamp x 0.0 1.0"),
        ])
        assert rt.state["x"] == 0.5


class TestWhenExecution:
    def test_when_registers_handler(self) -> None:
        rt = _run([
            WhenStatement(event="start"),
            PrintStatement(text="started"),
            EndStatement(),
        ])
        assert _output(rt) == ""
        assert "start" in rt.handlers

    def test_send_event(self) -> None:
        buf = io.StringIO()
        rt = _run(
            [
                WhenStatement(event="start"),
                PrintStatement(text="go!"),
                EndStatement(),
            ],
            output=buf,
        )
        assert buf.getvalue() == ""
        rt.send("start")
        assert buf.getvalue() == "go!\n"

    def test_handler_body(self) -> None:
        buf = io.StringIO()
        rt = _run(
            [
                CreateStatement(kind="number", name="x"),
                WhenStatement(event="tick"),
                SetStatement(target="x", value="42"),
                PrintStatement(text="x is {x}"),
                EndStatement(),
            ],
            output=buf,
        )
        assert rt.state["x"] == 0
        rt.send("tick")
        assert rt.state["x"] == 42
        assert buf.getvalue() == "x is 42\n"


# ══════════════════════════════════════════════════════════════
# Checkpoint 1: State and Output
# ══════════════════════════════════════════════════════════════


class TestCheckpoint1:
    def test_state_and_output(self) -> None:
        """create number score / set score to 42 / print 'Score: {score}'"""
        rt = _run([
            CreateStatement(kind="number", name="score"),
            SetStatement(target="score", value="42"),
            PrintStatement(text="Score: {score}"),
        ])
        assert _output(rt) == "Score: 42\n"

    def test_arithmetic_checkpoint(self) -> None:
        """set score to score + 1 works."""
        rt = _run([
            CreateStatement(kind="number", name="score"),
            SetStatement(target="score", value="10"),
            SetStatement(target="score", value="score + 5"),
            PrintStatement(text="Score: {score}"),
        ])
        assert _output(rt) == "Score: 15\n"


# ══════════════════════════════════════════════════════════════
# Group 2: get, say, send, event, on
# ══════════════════════════════════════════════════════════════


class TestGetExecution:
    # Compliance G1
    def test_get_returns_value(self) -> None:
        rt = _run([
            CreateStatement(kind="number", name="score"),
            SetStatement(target="score", value="42"),
        ])
        result = rt.execute_get("score")
        assert result == [{"key": "score", "value": 42, "type": "int"}]

    # Compliance G2
    def test_get_unknown_raises(self) -> None:
        rt = _run([])
        with pytest.raises(KeyError):
            rt.execute_get("nonexistent")

    # Compliance G3
    def test_get_never_mutates(self) -> None:
        rt = _run([
            CreateStatement(kind="number", name="score"),
            SetStatement(target="score", value="42"),
        ])
        rt.execute_get("score")
        assert rt.state["score"] == 42

    def test_get_all(self) -> None:
        rt = _run([
            CreateStatement(kind="number", name="x"),
            SetStatement(target="x", value="1"),
            CreateStatement(kind="string", name="y"),
            SetStatement(target="y", value='"hello"'),
        ])
        result = rt.execute_get("all")
        keys = {r["key"] for r in result}
        assert "x" in keys
        assert "y" in keys

    def test_get_all_typed(self) -> None:
        rt = _run([
            CreateStatement(kind="number", name="a"),
            SetStatement(target="a", value="1"),
            CreateStatement(kind="string", name="b"),
            SetStatement(target="b", value='"hi"'),
        ])
        result = rt.execute_get("all int")
        assert len(result) == 1
        assert result[0]["key"] == "a"

    def test_get_dotted(self) -> None:
        rt = _run([
            CreateStatement(kind="object", name="player"),
            SetStatement(target="player.health", value="100"),
        ])
        result = rt.execute_get("player.health")
        assert result == [{"key": "player.health", "value": 100, "type": "int"}]

    def test_get_all_hides_internal(self) -> None:
        rt = _run([
            SayStatement(text="hello"),
        ])
        result = rt.execute_get("all")
        keys = {r["key"] for r in result}
        assert "_last_said" not in keys
        assert "_say_count" not in keys


class TestSayExecution:
    # Compliance S1
    def test_say_writes_and_logs(self) -> None:
        rt = _run([SayStatement(text="Hello everyone")])
        assert "Hello everyone" in _output(rt)
        assert rt.state["_last_said"] == "Hello everyone"
        assert rt.state["_say_count"] == 1

    # Compliance S2
    def test_say_interpolates(self) -> None:
        rt = _run([
            CreateStatement(kind="number", name="gold"),
            SetStatement(target="gold", value="50"),
            SayStatement(text="You have {gold} gold"),
        ])
        assert rt.state["_last_said"] == "You have 50 gold"

    def test_say_count_increments(self) -> None:
        rt = _run([
            SayStatement(text="one"),
            SayStatement(text="two"),
        ])
        assert rt.state["_say_count"] == 2

    def test_say_output(self) -> None:
        rt = _run([SayStatement(text="Broadcast")])
        assert _output(rt) == "Broadcast\n"


class TestEventExecution:
    def test_event_declares(self) -> None:
        rt = _run([EventStatement(name="alarm", payload_fields=[])])
        assert "alarm" in rt.event_registry

    def test_event_with_fields(self) -> None:
        rt = _run([EventStatement(name="score_changed", payload_fields=["old", "new"])])
        assert rt.event_registry["score_changed"] == ["old", "new"]

    def test_event_duplicate_is_idempotent(self) -> None:
        """Duplicate event declarations are allowed (widgets may auto-declare)."""
        rt = _run([
            EventStatement(name="alarm", payload_fields=[]),
            EventStatement(name="alarm", payload_fields=["source"]),
        ])
        # Last declaration wins
        assert rt.event_registry["alarm"] == ["source"]


class TestSendExecution:
    def test_send_undeclared_raises(self) -> None:
        """Compliance SEO2: send undeclared event raises error."""
        rt = _run([])
        with pytest.raises(KeyError, match="Undeclared event"):
            rt.execute_send("ghost_event")

    def test_send_universal_no_declaration_needed(self) -> None:
        """Universal events don't need declaration."""
        buf = io.StringIO()
        rt = _run(
            [
                WhenStatement(event="start"),
                PrintStatement(text="go!"),
                EndStatement(),
            ],
            output=buf,
        )
        rt.send("start")  # no error
        assert buf.getvalue() == "go!\n"

    def test_send_no_listeners_noop(self) -> None:
        rt = _run([EventStatement(name="quiet", payload_fields=[])])
        rt.execute_send("quiet")  # no error

    def test_send_with_payload(self) -> None:
        buf = io.StringIO()
        rt = _run(
            [
                EventStatement(name="score_changed", payload_fields=["old", "new"]),
                WhenStatement(event="score_changed"),
                PrintStatement(text="Changed from {old} to {new}"),
                EndStatement(),
            ],
            output=buf,
        )
        rt.send("score_changed", old=50, new=100)
        assert buf.getvalue() == "Changed from 50 to 100\n"

    def test_payload_injection_restores_state(self) -> None:
        rt = _run([
            CreateStatement(kind="string", name="name"),
            SetStatement(target="name", value='"original"'),
            EventStatement(name="test", payload_fields=["name"]),
            WhenStatement(event="test"),
            PrintStatement(text="During: {name}"),
            EndStatement(),
        ])
        buf = io.StringIO()
        rt.output = buf
        rt.send("test", name="injected")
        assert buf.getvalue() == "During: injected\n"
        # Original restored
        assert rt.state["name"] == "original"

    def test_payload_injection_removes_new_keys(self) -> None:
        rt = _run([EventStatement(name="test", payload_fields=["temp"])])
        rt.send("test", temp="val")
        assert "temp" not in rt.state

    def test_send_max_depth(self) -> None:
        """Cascading events capped at depth 10."""
        rt = _run([
            EventStatement(name="loop", payload_fields=[]),
            WhenStatement(event="loop"),
            SendStatement(event="loop"),
            EndStatement(),
        ])
        # Should not infinitely recurse
        rt.execute_send("loop")  # reaches depth 10 then stops


class TestOnExecution:
    # Compliance SEO1
    def test_event_on_send_cycle(self) -> None:
        """event declares, on listens, send triggers."""
        rt = _run([
            CreateStatement(kind="string", name="status"),
            EventStatement(name="alarm", payload_fields=[]),
            OnStatement(event="alarm", action="set", args='status to "triggered"'),
        ])
        rt.execute_send("alarm")
        assert rt.state["status"] == "triggered"

    # Compliance SEO3
    def test_on_with_condition(self) -> None:
        rt = _run([
            CreateStatement(kind="number", name="level"),
            SetStatement(target="level", value="5"),
            CreateStatement(kind="string", name="msg"),
            EventStatement(name="check", payload_fields=[]),
            OnStatement(event="check", action="set", args='msg to "high"', condition="level > 3"),
        ])
        rt.execute_send("check")
        assert rt.state["msg"] == "high"

    def test_on_condition_false(self) -> None:
        rt = _run([
            CreateStatement(kind="number", name="level"),
            SetStatement(target="level", value="1"),
            CreateStatement(kind="string", name="msg"),
            EventStatement(name="check", payload_fields=[]),
            OnStatement(event="check", action="set", args='msg to "high"', condition="level > 3"),
        ])
        rt.execute_send("check")
        assert rt.state["msg"] == ""

    def test_on_send_action(self) -> None:
        buf = io.StringIO()
        rt = _run(
            [
                EventStatement(name="a", payload_fields=[]),
                EventStatement(name="b", payload_fields=[]),
                OnStatement(event="a", action="send", args="b"),
                WhenStatement(event="b"),
                PrintStatement(text="b fired"),
                EndStatement(),
            ],
            output=buf,
        )
        rt.execute_send("a")
        assert buf.getvalue() == "b fired\n"

    def test_on_say_action(self) -> None:
        rt = _run([
            EventStatement(name="alarm", payload_fields=[]),
            OnStatement(event="alarm", action="say", args="Alert!"),
        ])
        buf = io.StringIO()
        rt.output = buf
        rt.execute_send("alarm")
        assert "Alert!" in buf.getvalue()
        assert rt.state["_last_said"] == "Alert!"

    def test_on_print_action(self) -> None:
        rt = _run([
            EventStatement(name="alarm", payload_fields=[]),
            OnStatement(event="alarm", action="print", args="Warning!"),
        ])
        buf = io.StringIO()
        rt.output = buf
        rt.execute_send("alarm")
        assert buf.getvalue() == "Warning!\n"

    def test_multiple_listeners_fire_in_order(self) -> None:
        buf = io.StringIO()
        rt = _run(
            [
                EventStatement(name="test", payload_fields=[]),
                OnStatement(event="test", action="print", args="first"),
                OnStatement(event="test", action="print", args="second"),
            ],
            output=buf,
        )
        rt.execute_send("test")
        assert buf.getvalue() == "first\nsecond\n"


# ══════════════════════════════════════════════════════════════
# Checkpoint 2: Events
# ══════════════════════════════════════════════════════════════


class TestCheckpoint2:
    def test_events_checkpoint(self) -> None:
        """create string status / event alarm / on alarm set status to 'triggered' / send alarm / print 'Status: {status}'"""
        rt = _run([
            CreateStatement(kind="string", name="status"),
            EventStatement(name="alarm", payload_fields=[]),
            OnStatement(event="alarm", action="set", args='status to "triggered"'),
            SendStatement(event="alarm"),
            PrintStatement(text="Status: {status}"),
        ])
        assert _output(rt) == "Status: triggered\n"


# ══════════════════════════════════════════════════════════════
# Group 3: go, look
# ══════════════════════════════════════════════════════════════


class TestGoExecution:
    # Compliance GO1
    def test_go_navigates(self) -> None:
        rt = _run_with_scenes(
            [GoStatement(target="corridor")],
            scenes={"entrance": {}, "corridor": {"room_description": "A dark corridor"}},
            initial_scene="entrance",
        )
        assert rt.state["_scene"] == "corridor"
        assert rt.state["_prev_scene"] == "entrance"

    # Compliance GO2
    def test_go_back(self) -> None:
        rt = _run_with_scenes(
            [GoStatement(target="corridor")],
            scenes={"entrance": {}, "corridor": {}},
            initial_scene="entrance",
        )
        rt.execute(GoStatement(target="back"))
        assert rt.state["_scene"] == "entrance"

    # Compliance GO3
    def test_go_unknown_raises(self) -> None:
        rt = _run_with_scenes(
            [],
            scenes={"entrance": {}},
            initial_scene="entrance",
        )
        with pytest.raises(KeyError, match="not found"):
            rt.execute(GoStatement(target="nonexistent"))

    def test_go_applies_overrides(self) -> None:
        rt = _run_with_scenes(
            [GoStatement(target="treasure")],
            scenes={
                "entrance": {},
                "treasure": {"room_description": "Gold everywhere", "gold": 100},
            },
            initial_scene="entrance",
        )
        assert rt.state["gold"] == 100

    def test_go_respects_exits(self) -> None:
        rt = _run_with_scenes(
            [],
            scenes={
                "entrance": {"exits": ["corridor"]},
                "corridor": {},
                "secret": {},
            },
            initial_scene="entrance",
        )
        with pytest.raises(KeyError, match="Cannot go"):
            rt.execute(GoStatement(target="secret"))

    def test_go_back_no_previous_raises(self) -> None:
        rt = _run_with_scenes(
            [],
            scenes={"entrance": {}},
        )
        with pytest.raises(KeyError, match="No previous"):
            rt.execute(GoStatement(target="back"))

    def test_go_fires_scene_events(self) -> None:
        buf = io.StringIO()
        rt = Runtime(output=buf)
        rt.scenes = {"entrance": {}, "corridor": {}}
        rt.state["_scene"] = "entrance"
        # Register handlers for scene events
        rt.handlers["scene_exit"] = [[PrintStatement(text="exiting")]]
        rt.handlers["scene_enter"] = [[PrintStatement(text="entering")]]
        rt.execute(GoStatement(target="corridor"))
        assert "exiting" in buf.getvalue()
        assert "entering" in buf.getvalue()


class TestLookExecution:
    def test_look_bare(self) -> None:
        buf = io.StringIO()
        rt = Runtime(output=buf)
        rt.scenes = {"hall": {"room_description": "A grand hall", "exits": ["garden"]}}
        rt.state["_scene"] = "hall"
        result = rt.execute(LookStatement(target=""))
        assert buf.getvalue().startswith("[hall]")
        assert "A grand hall" in buf.getvalue()

    def test_look_target(self) -> None:
        rt = _run([
            CreateStatement(kind="object", name="player"),
            SetStatement(target="player.health", value="100"),
        ])
        result = rt.execute(LookStatement(target="player"))
        assert result[0]["value"] == {"health": 100}

    def test_look_unknown_raises(self) -> None:
        rt = _run([])
        with pytest.raises(KeyError, match="Unknown"):
            rt.execute(LookStatement(target="ghost"))


# ══════════════════════════════════════════════════════════════
# Group 4: connect, destroy
# ══════════════════════════════════════════════════════════════


class TestConnectExecution:
    def test_connect_register(self) -> None:
        rt = _run([ConnectStatement(name="api", url="https://example.com")])
        assert rt.connections["api"] == "https://example.com"

    def test_connect_update(self) -> None:
        rt = _run([
            ConnectStatement(name="api", url="https://old.com"),
            ConnectStatement(name="api", url="https://new.com"),
        ])
        assert rt.connections["api"] == "https://new.com"

    def test_connect_disconnect(self) -> None:
        rt = _run([
            ConnectStatement(name="api", url="https://example.com"),
            ConnectStatement(name="api", url="disconnect"),
        ])
        assert "api" not in rt.connections

    def test_disconnect_nonexistent_raises(self) -> None:
        with pytest.raises(KeyError, match="not found"):
            _run([ConnectStatement(name="ghost", url="disconnect")])

    def test_connect_list_noop(self) -> None:
        rt = _run([ConnectStatement(name="", url="")])
        assert rt.connections == {}


class TestDestroyExecution:
    # Compliance D1
    def test_destroy_removes(self) -> None:
        rt = _run([
            CreateStatement(kind="object", name="bullet"),
            DestroyStatement(name="bullet"),
        ])
        assert "bullet" not in rt.state

    # Compliance D2
    def test_destroy_nonexistent_noop(self) -> None:
        rt = _run([DestroyStatement(name="ghost")])  # no error

    # Compliance D3
    def test_destroy_fires_event(self) -> None:
        buf = io.StringIO()
        rt = _run(
            [
                CreateStatement(kind="object", name="marker"),
                WhenStatement(event="destroy"),
                PrintStatement(text="destroyed: {name}"),
                EndStatement(),
            ],
            output=buf,
        )
        rt.execute(DestroyStatement(name="marker"))
        assert "destroyed: marker" in buf.getvalue()
        assert "marker" not in rt.state


# ══════════════════════════════════════════════════════════════
# Group 5: sprite, sound, play
# ══════════════════════════════════════════════════════════════


class TestSpriteExecution:
    def test_sprite_sets_property(self) -> None:
        rt = _run([
            CreateStatement(kind="object", name="player"),
            SpriteStatement(name="player", description="pixel art spaceship"),
        ])
        assert rt.state["player"]["sprite"] == "pixel art spaceship"

    def test_sprite_nonexistent_creates(self) -> None:
        rt = _run([SpriteStatement(name="alien", description="green alien")])
        assert rt.state["alien"]["sprite"] == "green alien"


class TestSoundExecution:
    def test_sound_registers(self) -> None:
        rt = _run([SoundStatement(name="laser", description="pew pew")])
        assert rt.audio_registry["laser"] == "pew pew"


class TestPlayExecution:
    def test_play_existing_noop(self) -> None:
        rt = _run([
            SoundStatement(name="boom", description="explosion"),
            PlayStatement(sound="boom"),
        ])
        # No error — stub no-op

    def test_play_nonexistent_noop(self) -> None:
        rt = _run([PlayStatement(sound="ghost")])
        # No error — no-op if sound doesn't exist


# ══════════════════════════════════════════════════════════════
# Skipped statements
# ══════════════════════════════════════════════════════════════


class TestSkippedStatements:
    def test_comments_and_blanks_ignored(self) -> None:
        rt = _run([
            CommentStatement(text="this is a comment"),
            BlankStatement(),
            PrintStatement(text="hello"),
        ])
        assert _output(rt) == "hello\n"


# ══════════════════════════════════════════════════════════════
# use (widget composition)
# ══════════════════════════════════════════════════════════════

WIDGETS_DIR = Path(__file__).parent.parent / "examples" / "widgets"


class TestUseExecution:
    def test_use_loads_widget_state(self) -> None:
        from rosh_lang.parser import parse_string
        prog = parse_string("use score")
        buf = io.StringIO()
        rt = Runtime(output=buf, search_paths=[WIDGETS_DIR])
        rt.run(prog)
        # Score widget creates score.value and score.display (nested under "score")
        assert "score" in rt.state
        assert rt.state["score"]["value"] == 0

    def test_use_namespaces_objects(self) -> None:
        from rosh_lang.parser import parse_string
        prog = parse_string("use score")
        buf = io.StringIO()
        rt = Runtime(output=buf, search_paths=[WIDGETS_DIR])
        rt.run(prog)
        assert isinstance(rt.state["score"]["display"], dict)

    def test_use_config_override(self) -> None:
        from rosh_lang.parser import parse_string
        prog = parse_string("use player speed 0.05")
        buf = io.StringIO()
        rt = Runtime(output=buf, search_paths=[WIDGETS_DIR])
        rt.run(prog)
        assert rt.state["player"]["speed"] == 0.05

    def test_use_then_set(self) -> None:
        from rosh_lang.parser import parse_string
        prog = parse_string("use score\nset score.value to 42")
        buf = io.StringIO()
        rt = Runtime(output=buf, search_paths=[WIDGETS_DIR])
        rt.run(prog)
        assert rt.state["score"]["value"] == 42

    def test_use_then_print_interpolation(self) -> None:
        from rosh_lang.parser import parse_string
        prog = parse_string(
            "use score\n"
            "set score.value to 42\n"
            'print "Score: {score.value}"'
        )
        buf = io.StringIO()
        rt = Runtime(output=buf, search_paths=[WIDGETS_DIR])
        rt.run(prog)
        assert "Score: 42" in buf.getvalue()

    def test_use_missing_widget_warns_and_continues(self) -> None:
        from rosh_lang.parser import parse_string
        prog = parse_string('use nonexistent\nprint "still runs"')
        buf = io.StringIO()
        rt = Runtime(output=buf, search_paths=[WIDGETS_DIR])
        with pytest.warns(UserWarning, match="not found"):
            rt.run(prog)
        assert "still runs" in buf.getvalue()

    def test_use_multiple_widgets(self) -> None:
        from rosh_lang.parser import parse_string
        prog = parse_string("use score\nuse player")
        buf = io.StringIO()
        rt = Runtime(output=buf, search_paths=[WIDGETS_DIR])
        rt.run(prog)
        assert "score" in rt.state
        assert "player" in rt.state
        assert rt.state["score"]["value"] == 0
        assert isinstance(rt.state["player"]["ship"], dict)

    def test_use_widget_with_when_handler(self) -> None:
        from rosh_lang.parser import parse_string
        prog = parse_string("use counter")
        buf = io.StringIO()
        rt = Runtime(output=buf, search_paths=[WIDGETS_DIR])
        rt.run(prog)
        # Counter widget has a when click handler
        assert rt.state["counter"]["value"] == 0
        assert "click" in rt.handlers

    def test_use_widget_handler_fires(self) -> None:
        from rosh_lang.parser import parse_string
        prog = parse_string("use counter")
        buf = io.StringIO()
        rt = Runtime(output=buf, search_paths=[WIDGETS_DIR])
        rt.run(prog)
        # Fire the click event — counter should increment
        rt.send("click")
        assert rt.state["counter"]["value"] == 1
        assert "Count: 1" in buf.getvalue()


# ══════════════════════════════════════════════════════════════
# End-to-end file execution
# ══════════════════════════════════════════════════════════════

EXAMPLES = Path(__file__).parent.parent / "examples"


class TestRunFile:
    def test_run_hello_rosh(self) -> None:
        from rosh_lang.parser import parse_file
        buf = io.StringIO()
        prog = parse_file(EXAMPLES / "hello.rosh")
        run(prog, output=buf)
        assert buf.getvalue() == "hello world\n"

    def test_run_counter_rosh(self) -> None:
        from rosh_lang.parser import parse_file
        buf = io.StringIO()
        prog = parse_file(EXAMPLES / "counter.rosh")
        run(prog, output=buf)
        assert buf.getvalue() == "Count is: 1\n"

    def test_run_player_rosh(self) -> None:
        from rosh_lang.parser import parse_file
        buf = io.StringIO()
        prog = parse_file(EXAMPLES / "player.rosh")
        run(prog, output=buf)
        assert buf.getvalue() == "Player created at (50, 90) with 100 HP\n"


class TestConvenienceRun:
    def test_run_returns_runtime(self) -> None:
        buf = io.StringIO()
        rt = run(Programme(statements=[PrintStatement(text="hi")]), output=buf)
        assert isinstance(rt, Runtime)
        assert buf.getvalue() == "hi\n"


# ══════════════════════════════════════════════════════════════
# End-to-end checkpoint programmes (parsed from text)
# ══════════════════════════════════════════════════════════════


class TestCheckpointProgrammes:
    def test_checkpoint1_from_text(self) -> None:
        from rosh_lang.parser import parse_string
        prog = parse_string(
            'create number score\n'
            'set score to 42\n'
            'print "Score: {score}"\n'
        )
        buf = io.StringIO()
        run(prog, output=buf)
        assert buf.getvalue() == "Score: 42\n"

    def test_checkpoint2_from_text(self) -> None:
        from rosh_lang.parser import parse_string
        prog = parse_string(
            'create string status\n'
            'event alarm\n'
            'on alarm set status to "triggered"\n'
            'send alarm\n'
            'print "Status: {status}"\n'
        )
        buf = io.StringIO()
        run(prog, output=buf)
        assert buf.getvalue() == "Status: triggered\n"

    def test_arithmetic_from_text(self) -> None:
        from rosh_lang.parser import parse_string
        prog = parse_string(
            'create number score\n'
            'set score to 10\n'
            'set score to score + 5\n'
            'print "Score: {score}"\n'
        )
        buf = io.StringIO()
        run(prog, output=buf)
        assert buf.getvalue() == "Score: 15\n"


class TestIfExecution:
    """Tests for if/else execution."""

    def test_if_true_branch(self) -> None:
        from rosh_lang.parser import parse_string
        prog = parse_string(
            'create number score\n'
            'set score to 20\n'
            'if score > 10\n'
            '  print "high"\n'
            'end\n'
        )
        buf = io.StringIO()
        run(prog, output=buf)
        assert buf.getvalue() == "high\n"

    def test_if_false_skips(self) -> None:
        from rosh_lang.parser import parse_string
        prog = parse_string(
            'create number score\n'
            'set score to 5\n'
            'if score > 10\n'
            '  print "high"\n'
            'end\n'
        )
        buf = io.StringIO()
        run(prog, output=buf)
        assert buf.getvalue() == ""

    def test_if_else_true(self) -> None:
        from rosh_lang.parser import parse_string
        prog = parse_string(
            'create number score\n'
            'set score to 20\n'
            'if score > 10\n'
            '  print "high"\n'
            'else\n'
            '  print "low"\n'
            'end\n'
        )
        buf = io.StringIO()
        run(prog, output=buf)
        assert buf.getvalue() == "high\n"

    def test_if_else_false(self) -> None:
        from rosh_lang.parser import parse_string
        prog = parse_string(
            'create number score\n'
            'set score to 5\n'
            'if score > 10\n'
            '  print "high"\n'
            'else\n'
            '  print "low"\n'
            'end\n'
        )
        buf = io.StringIO()
        run(prog, output=buf)
        assert buf.getvalue() == "low\n"

    def test_if_equals_string(self) -> None:
        from rosh_lang.parser import parse_string
        prog = parse_string(
            'create string status\n'
            'set status to "ready"\n'
            'if status == ready\n'
            '  print "go"\n'
            'end\n'
        )
        buf = io.StringIO()
        run(prog, output=buf)
        assert buf.getvalue() == "go\n"

    def test_if_inside_when(self) -> None:
        from rosh_lang.parser import parse_string
        prog = parse_string(
            'create number score\n'
            'set score to 20\n'
            'when start\n'
            '  if score > 10\n'
            '    print "high"\n'
            '  else\n'
            '    print "low"\n'
            '  end\n'
            'end\n'
        )
        buf = io.StringIO()
        rt = Runtime(output=buf)
        rt.run(prog)
        rt.send("start")
        assert buf.getvalue() == "high\n"

    def test_if_nested(self) -> None:
        from rosh_lang.parser import parse_string
        prog = parse_string(
            'create number x\n'
            'set x to 5\n'
            'create number y\n'
            'set y to 3\n'
            'if x > 0\n'
            '  if y > 0\n'
            '    print "both positive"\n'
            '  end\n'
            'end\n'
        )
        buf = io.StringIO()
        run(prog, output=buf)
        assert buf.getvalue() == "both positive\n"

    def test_if_with_set(self) -> None:
        from rosh_lang.parser import parse_string
        prog = parse_string(
            'create number lives\n'
            'set lives to 0\n'
            'create string status\n'
            'if lives == 0\n'
            '  set status to "gameover"\n'
            'else\n'
            '  set status to "playing"\n'
            'end\n'
        )
        buf = io.StringIO()
        rt = Runtime(output=buf)
        rt.run(prog)
        assert rt.state["status"] == "gameover"

    def test_if_dotted_field(self) -> None:
        from rosh_lang.parser import parse_string
        prog = parse_string(
            'create object player\n'
            'set player.health to 0\n'
            'if player.health <= 0\n'
            '  print "dead"\n'
            'end\n'
        )
        buf = io.StringIO()
        run(prog, output=buf)
        assert buf.getvalue() == "dead\n"

    def test_else_if_first_branch(self) -> None:
        from rosh_lang.parser import parse_string
        prog = parse_string(
            'create number x\n'
            'set x to 10\n'
            'if x > 5\n'
            '  print "big"\n'
            'else if x > 3\n'
            '  print "medium"\n'
            'else\n'
            '  print "small"\n'
            'end\n'
        )
        buf = io.StringIO()
        run(prog, output=buf)
        assert buf.getvalue() == "big\n"

    def test_else_if_middle_branch(self) -> None:
        from rosh_lang.parser import parse_string
        prog = parse_string(
            'create number x\n'
            'set x to 4\n'
            'if x > 5\n'
            '  print "big"\n'
            'else if x > 3\n'
            '  print "medium"\n'
            'else\n'
            '  print "small"\n'
            'end\n'
        )
        buf = io.StringIO()
        run(prog, output=buf)
        assert buf.getvalue() == "medium\n"

    def test_else_if_last_branch(self) -> None:
        from rosh_lang.parser import parse_string
        prog = parse_string(
            'create number x\n'
            'set x to 1\n'
            'if x > 5\n'
            '  print "big"\n'
            'else if x > 3\n'
            '  print "medium"\n'
            'else\n'
            '  print "small"\n'
            'end\n'
        )
        buf = io.StringIO()
        run(prog, output=buf)
        assert buf.getvalue() == "small\n"


class TestSceneExecution:
    """Tests for scene (go/look) execution."""

    def test_create_scene(self) -> None:
        from rosh_lang.parser import parse_string
        prog = parse_string('create scene lobby')
        buf = io.StringIO()
        rt = Runtime(output=buf)
        rt.run(prog)
        assert "lobby" in rt.scenes

    def test_set_scene_description(self) -> None:
        from rosh_lang.parser import parse_string
        prog = parse_string(
            'create scene lobby\n'
            'set lobby.description to "A grand entrance hall"\n'
        )
        buf = io.StringIO()
        rt = Runtime(output=buf)
        rt.run(prog)
        assert rt.scenes["lobby"]["description"] == "A grand entrance hall"

    def test_go_scene(self) -> None:
        from rosh_lang.parser import parse_string
        prog = parse_string(
            'create scene lobby\n'
            'go lobby\n'
        )
        buf = io.StringIO()
        rt = Runtime(output=buf)
        rt.run(prog)
        assert rt.state["_scene"] == "lobby"

    def test_go_back(self) -> None:
        from rosh_lang.parser import parse_string
        prog = parse_string(
            'create scene lobby\n'
            'create scene corridor\n'
            'go lobby\n'
            'go corridor\n'
            'go back\n'
        )
        buf = io.StringIO()
        rt = Runtime(output=buf)
        rt.run(prog)
        assert rt.state["_scene"] == "lobby"

    def test_go_fires_events(self) -> None:
        from rosh_lang.parser import parse_string
        prog = parse_string(
            'create scene lobby\n'
            'create scene corridor\n'
            'create string log\n'
            'when scene_enter\n'
            '  set log to "entered"\n'
            'end\n'
            'go lobby\n'
        )
        buf = io.StringIO()
        rt = Runtime(output=buf)
        rt.run(prog)
        assert rt.state["log"] == "entered"

    def test_scene_exits_restriction(self) -> None:
        from rosh_lang.parser import parse_string
        prog = parse_string(
            'create scene lobby\n'
            'set lobby.exits to "corridor"\n'
            'create scene corridor\n'
            'create scene secret\n'
            'go lobby\n'
            'go secret\n'
        )
        buf = io.StringIO()
        rt = Runtime(output=buf)
        with pytest.raises(KeyError, match="Cannot go"):
            rt.run(prog)

    def test_look_outputs_scene(self) -> None:
        from rosh_lang.parser import parse_string
        prog = parse_string(
            'create scene lobby\n'
            'set lobby.description to "A grand hall"\n'
            'go lobby\n'
            'look\n'
        )
        buf = io.StringIO()
        rt = Runtime(output=buf)
        rt.run(prog)
        assert "[lobby]" in buf.getvalue()
        assert "A grand hall" in buf.getvalue()

    def test_scene_overrides_state(self) -> None:
        from rosh_lang.parser import parse_string
        prog = parse_string(
            'create scene lobby\n'
            'set lobby.music to "jazz"\n'
            'go lobby\n'
        )
        buf = io.StringIO()
        rt = Runtime(output=buf)
        rt.run(prog)
        assert rt.state["music"] == "jazz"


# ── Animate ────────────────────────────────────────────────


class TestAnimate:
    def test_exec_animate_records_registry(self) -> None:
        """_exec_animate stores metadata in animation_registry."""
        rt = _run([
            AnimateStatement(
                name="player", sheet="walk.png", frames=4, speed=8, mode="loop",
            ),
        ])
        assert "player" in rt.animation_registry
        info = rt.animation_registry["player"]
        assert info["sheet"] == "walk.png"
        assert info["frames"] == 4
        assert info["speed"] == 8
        assert info["mode"] == "loop"

    def test_exec_animate_once_mode(self) -> None:
        """Animation with mode 'once' is recorded correctly."""
        rt = _run([
            AnimateStatement(
                name="explosion", sheet="boom.png", frames=9, speed=15, mode="once",
            ),
        ])
        assert rt.animation_registry["explosion"]["mode"] == "once"

    def test_exec_animate_bounce_mode(self) -> None:
        """Animation with mode 'bounce' is recorded correctly."""
        rt = _run([
            AnimateStatement(
                name="flag", sheet="flag.png", frames=3, speed=4, mode="bounce",
            ),
        ])
        assert rt.animation_registry["flag"]["mode"] == "bounce"


# ── after statement (noop in terminal) ───────────────────────────


class TestAfterTerminal:
    def test_after_is_noop(self) -> None:
        """after should not raise in terminal — just silently skip."""
        rt = _run([AfterStatement(delay=2.0, event="wave_2")])


class TestBackground:
    def test_background_colour_sets_state(self) -> None:
        rt = _run([BackgroundStatement(value="#ff0000")])
        assert rt.state["_background"] == "#ff0000"

    def test_background_named_colour(self) -> None:
        rt = _run([BackgroundStatement(value="darkblue")])
        assert rt.state["_background"] == "darkblue"

    def test_background_image_path(self) -> None:
        rt = _run([BackgroundStatement(value="sky.png")])
        assert rt.state["_background"] == "sky.png"

    def test_background_last_wins(self) -> None:
        rt = _run([
            BackgroundStatement(value="#ff0000"),
            BackgroundStatement(value="#00ff00"),
        ])
        assert rt.state["_background"] == "#00ff00"
