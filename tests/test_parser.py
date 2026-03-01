"""Tests for the Rosh programme parser — all 16 keywords.

Tests follow the build order from BUILDING-ROSH.md Section 12.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from rosh_lang.model import (
    AfterStatement,
    AnimateStatement,
    BlankStatement,
    CommentStatement,
    ConnectStatement,
    CreateStatement,
    DestroyStatement,
    EndStatement,
    EventStatement,
    GetStatement,
    GoStatement,
    IfStatement,
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
    UseStatement,
    WhenStatement,
)
from rosh_lang.parser import ParseError, parse_file, parse_string


# ── Group 1: print, create, set, when/end ─────────────────────


class TestPrint:
    def test_print_quoted(self) -> None:
        prog = parse_string('print "hello world"')
        stmt = prog.statements[0]
        assert isinstance(stmt, PrintStatement)
        assert stmt.text == "hello world"

    def test_print_single_quoted(self) -> None:
        prog = parse_string("print 'hello world'")
        assert isinstance(prog.statements[0], PrintStatement)
        assert prog.statements[0].text == "hello world"

    def test_print_unquoted(self) -> None:
        prog = parse_string("print hello world")
        assert isinstance(prog.statements[0], PrintStatement)
        assert prog.statements[0].text == "hello world"

    def test_print_with_interpolation(self) -> None:
        prog = parse_string('print "Score: {score}"')
        assert prog.statements[0].text == "Score: {score}"

    def test_print_with_dot_interpolation(self) -> None:
        prog = parse_string('print "Health: {player.health}"')
        assert prog.statements[0].text == "Health: {player.health}"

    def test_print_empty_raises(self) -> None:
        with pytest.raises(ParseError, match="print requires text"):
            parse_string("print")

    def test_print_case_insensitive(self) -> None:
        prog = parse_string('PRINT "hello"')
        assert isinstance(prog.statements[0], PrintStatement)

    def test_print_line_number(self) -> None:
        prog = parse_string('\nprint "hello"')
        stmt = prog.statements[1]
        assert isinstance(stmt, PrintStatement)
        assert stmt.line == 2


class TestCreate:
    def test_create_object(self) -> None:
        prog = parse_string("create object player")
        stmt = prog.statements[0]
        assert isinstance(stmt, CreateStatement)
        assert stmt.kind == "object"
        assert stmt.name == "player"
        assert stmt.count == 1
        assert stmt.parent == ""

    def test_create_number(self) -> None:
        prog = parse_string("create number score as 0")
        stmt = prog.statements[0]
        assert isinstance(stmt, CreateStatement)
        assert stmt.kind == "number"
        assert stmt.name == "score"

    def test_create_string(self) -> None:
        prog = parse_string("create string name")
        stmt = prog.statements[0]
        assert isinstance(stmt, CreateStatement)
        assert stmt.kind == "string"
        assert stmt.name == "name"

    def test_create_with_parent(self) -> None:
        prog = parse_string("create object hero from player")
        stmt = prog.statements[0]
        assert isinstance(stmt, CreateStatement)
        assert stmt.name == "hero"
        assert stmt.parent == "player"

    def test_create_multiple(self) -> None:
        prog = parse_string("create 5 objects as bullets")
        stmt = prog.statements[0]
        assert isinstance(stmt, CreateStatement)
        assert stmt.count == 5
        assert stmt.kind == "object"
        assert stmt.name == "bullets"

    def test_create_missing_name(self) -> None:
        with pytest.raises(ParseError, match="create requires"):
            parse_string("create object")

    def test_create_too_short(self) -> None:
        with pytest.raises(ParseError):
            parse_string("create")


class TestSet:
    def test_set_with_to(self) -> None:
        prog = parse_string("set x to 100")
        stmt = prog.statements[0]
        assert isinstance(stmt, SetStatement)
        assert stmt.target == "x"
        assert stmt.value == "100"

    def test_set_property_with_to(self) -> None:
        prog = parse_string("set player health to 75")
        stmt = prog.statements[0]
        assert isinstance(stmt, SetStatement)
        assert stmt.target == "player.health"
        assert stmt.value == "75"

    def test_set_dot_notation(self) -> None:
        prog = parse_string("set player.health to 75")
        stmt = prog.statements[0]
        assert stmt.target == "player.health"
        assert stmt.value == "75"

    def test_set_without_to(self) -> None:
        prog = parse_string("set x 100")
        stmt = prog.statements[0]
        assert stmt.target == "x"
        assert stmt.value == "100"

    def test_set_string_value(self) -> None:
        prog = parse_string('set name to "Hero"')
        stmt = prog.statements[0]
        assert stmt.target == "name"
        assert stmt.value == '"Hero"'

    def test_set_expression_value(self) -> None:
        prog = parse_string('set score_text.text to "Score: {state.score}"')
        stmt = prog.statements[0]
        assert stmt.value == '"Score: {state.score}"'

    def test_set_arithmetic_value(self) -> None:
        prog = parse_string("set score to score + 1")
        stmt = prog.statements[0]
        assert stmt.target == "score"
        assert stmt.value == "score + 1"

    def test_set_deep_property(self) -> None:
        prog = parse_string("set player position x to 100")
        stmt = prog.statements[0]
        assert stmt.target == "player.position.x"
        assert stmt.value == "100"

    def test_set_empty_raises(self) -> None:
        with pytest.raises(ParseError, match="set requires"):
            parse_string("set")

    def test_set_no_value_raises(self) -> None:
        with pytest.raises(ParseError, match="set requires"):
            parse_string("set x")


class TestWhen:
    def test_when_simple(self) -> None:
        prog = parse_string("when update then")
        stmt = prog.statements[0]
        assert isinstance(stmt, WhenStatement)
        assert stmt.event == "update"
        assert stmt.args == []

    def test_when_without_then(self) -> None:
        prog = parse_string("when start")
        stmt = prog.statements[0]
        assert isinstance(stmt, WhenStatement)
        assert stmt.event == "start"

    def test_when_collision(self) -> None:
        prog = parse_string("when collision hero enemy then")
        stmt = prog.statements[0]
        assert stmt.event == "collision"
        assert stmt.args == ["hero", "enemy"]

    def test_when_key_event(self) -> None:
        prog = parse_string("when space_pressed then")
        stmt = prog.statements[0]
        assert stmt.event == "space_pressed"

    def test_when_empty_raises(self) -> None:
        with pytest.raises(ParseError, match="when requires"):
            parse_string("when then")

    def test_end(self) -> None:
        prog = parse_string("end")
        assert isinstance(prog.statements[0], EndStatement)


# ── Group 2: get, say, send, event, on ────────────────────────


class TestGet:
    def test_get_simple(self) -> None:
        prog = parse_string("get score")
        stmt = prog.statements[0]
        assert isinstance(stmt, GetStatement)
        assert stmt.target == "score"

    def test_get_dotted(self) -> None:
        prog = parse_string("get player.health")
        stmt = prog.statements[0]
        assert stmt.target == "player.health"

    def test_get_all(self) -> None:
        prog = parse_string("get all")
        stmt = prog.statements[0]
        assert stmt.target == "all"

    def test_get_all_typed(self) -> None:
        prog = parse_string("get all bool")
        stmt = prog.statements[0]
        assert stmt.target == "all bool"

    def test_get_empty_raises(self) -> None:
        with pytest.raises(ParseError, match="get requires"):
            parse_string("get")


class TestSay:
    def test_say_unquoted(self) -> None:
        prog = parse_string("say Welcome to the dungeon")
        stmt = prog.statements[0]
        assert isinstance(stmt, SayStatement)
        assert stmt.text == "Welcome to the dungeon"

    def test_say_quoted(self) -> None:
        prog = parse_string('say "Hello everyone"')
        stmt = prog.statements[0]
        assert stmt.text == "Hello everyone"

    def test_say_interpolation(self) -> None:
        prog = parse_string("say You have {gold} gold")
        stmt = prog.statements[0]
        assert stmt.text == "You have {gold} gold"

    def test_say_empty_raises(self) -> None:
        with pytest.raises(ParseError, match="say requires"):
            parse_string("say")


class TestSend:
    def test_send_simple(self) -> None:
        prog = parse_string("send timer_expired")
        stmt = prog.statements[0]
        assert isinstance(stmt, SendStatement)
        assert stmt.event == "timer_expired"
        assert stmt.payload == {}

    def test_send_with_payload(self) -> None:
        prog = parse_string("send score_changed old=50 new=100")
        stmt = prog.statements[0]
        assert stmt.event == "score_changed"
        assert stmt.payload == {"old": "50", "new": "100"}

    def test_send_empty_raises(self) -> None:
        with pytest.raises(ParseError, match="send requires"):
            parse_string("send")


class TestEvent:
    def test_event_simple(self) -> None:
        prog = parse_string("event timer_expired")
        stmt = prog.statements[0]
        assert isinstance(stmt, EventStatement)
        assert stmt.name == "timer_expired"
        assert stmt.payload_fields == []

    def test_event_with_fields(self) -> None:
        prog = parse_string("event score_changed old new")
        stmt = prog.statements[0]
        assert stmt.name == "score_changed"
        assert stmt.payload_fields == ["old", "new"]

    def test_event_empty_raises(self) -> None:
        with pytest.raises(ParseError, match="event requires"):
            parse_string("event")


class TestOn:
    def test_on_set(self) -> None:
        prog = parse_string('on alarm set status to "triggered"')
        stmt = prog.statements[0]
        assert isinstance(stmt, OnStatement)
        assert stmt.event == "alarm"
        assert stmt.action == "set"
        assert stmt.args == 'status to "triggered"'

    def test_on_send(self) -> None:
        prog = parse_string("on player_died send game_over")
        stmt = prog.statements[0]
        assert stmt.event == "player_died"
        assert stmt.action == "send"
        assert stmt.args == "game_over"

    def test_on_say(self) -> None:
        prog = parse_string("on alarm_triggered say Security breach detected!")
        stmt = prog.statements[0]
        assert stmt.event == "alarm_triggered"
        assert stmt.action == "say"
        assert stmt.args == "Security breach detected!"

    def test_on_with_condition(self) -> None:
        prog = parse_string('on check when level > 3 set message to "high"')
        stmt = prog.statements[0]
        assert isinstance(stmt, OnStatement)
        assert stmt.event == "check"
        assert stmt.condition == "level > 3"
        assert stmt.action == "set"
        assert stmt.args == 'message to "high"'

    def test_on_empty_raises(self) -> None:
        with pytest.raises(ParseError, match="on requires"):
            parse_string("on")

    def test_on_space_key_condition(self) -> None:
        """on keydown when key == ' ' send fire → condition should preserve the space."""
        prog = parse_string('on keydown when key == " " send fire')
        stmt = prog.statements[0]
        assert isinstance(stmt, OnStatement)
        assert stmt.event == "keydown"
        assert stmt.condition == 'key == " "'
        assert stmt.action == "send"
        assert stmt.args == "fire"

    def test_on_unquoted_condition_unchanged(self) -> None:
        """Normal unquoted conditions should still work."""
        prog = parse_string("on update when score > 100 send win")
        stmt = prog.statements[0]
        assert stmt.condition == "score > 100"
        assert stmt.action == "send"
        assert stmt.args == "win"


# ── Group 3: go, look ─────────────────────────────────────────


class TestGo:
    def test_go_scene(self) -> None:
        prog = parse_string("go corridor")
        stmt = prog.statements[0]
        assert isinstance(stmt, GoStatement)
        assert stmt.target == "corridor"

    def test_go_back(self) -> None:
        prog = parse_string("go back")
        stmt = prog.statements[0]
        assert stmt.target == "back"

    def test_go_empty_raises(self) -> None:
        with pytest.raises(ParseError, match="go requires"):
            parse_string("go")


class TestLook:
    def test_look_bare(self) -> None:
        prog = parse_string("look")
        stmt = prog.statements[0]
        assert isinstance(stmt, LookStatement)
        assert stmt.target == ""

    def test_look_target(self) -> None:
        prog = parse_string("look player")
        stmt = prog.statements[0]
        assert stmt.target == "player"


# ── Group 4: connect, destroy ──────────────────────────────────


class TestConnect:
    def test_connect_register(self) -> None:
        prog = parse_string("connect api https://api.example.com")
        stmt = prog.statements[0]
        assert isinstance(stmt, ConnectStatement)
        assert stmt.name == "api"
        assert stmt.url == "https://api.example.com"

    def test_connect_disconnect(self) -> None:
        prog = parse_string("connect api disconnect")
        stmt = prog.statements[0]
        assert stmt.name == "api"
        assert stmt.url == "disconnect"

    def test_connect_list(self) -> None:
        prog = parse_string("connect")
        stmt = prog.statements[0]
        assert isinstance(stmt, ConnectStatement)
        assert stmt.name == ""


class TestDestroy:
    def test_destroy(self) -> None:
        prog = parse_string("destroy bullet_7")
        stmt = prog.statements[0]
        assert isinstance(stmt, DestroyStatement)
        assert stmt.name == "bullet_7"

    def test_destroy_empty_raises(self) -> None:
        with pytest.raises(ParseError, match="destroy requires"):
            parse_string("destroy")


# ── Group 5: sprite, sound, play ───────────────────────────────


class TestSprite:
    def test_sprite_with_description(self) -> None:
        prog = parse_string('sprite player "pixel art spaceship, 32x32"')
        stmt = prog.statements[0]
        assert isinstance(stmt, SpriteStatement)
        assert stmt.name == "player"
        assert stmt.description == "pixel art spaceship, 32x32"

    def test_sprite_unquoted(self) -> None:
        prog = parse_string("sprite player pixel art spaceship")
        stmt = prog.statements[0]
        assert stmt.name == "player"
        assert stmt.description == "pixel art spaceship"

    def test_sprite_empty_raises(self) -> None:
        with pytest.raises(ParseError, match="sprite requires"):
            parse_string("sprite")


class TestSound:
    def test_sound_with_description(self) -> None:
        prog = parse_string('sound laser "short sci-fi laser blast"')
        stmt = prog.statements[0]
        assert isinstance(stmt, SoundStatement)
        assert stmt.name == "laser"
        assert stmt.description == "short sci-fi laser blast"

    def test_sound_unquoted(self) -> None:
        prog = parse_string("sound laser pew pew")
        stmt = prog.statements[0]
        assert stmt.name == "laser"
        assert stmt.description == "pew pew"

    def test_sound_empty_raises(self) -> None:
        with pytest.raises(ParseError, match="sound requires"):
            parse_string("sound")


class TestPlay:
    def test_play_once(self) -> None:
        prog = parse_string("play explosion")
        stmt = prog.statements[0]
        assert isinstance(stmt, PlayStatement)
        assert stmt.sound == "explosion"
        assert stmt.mode == ""

    def test_play_loop(self) -> None:
        prog = parse_string("play music loop")
        stmt = prog.statements[0]
        assert stmt.sound == "music"
        assert stmt.mode == "loop"

    def test_play_stop(self) -> None:
        prog = parse_string("play music stop")
        stmt = prog.statements[0]
        assert stmt.mode == "stop"

    def test_play_empty_raises(self) -> None:
        with pytest.raises(ParseError, match="play requires"):
            parse_string("play")


# ── use ──────────────────────────────────────────────────────


class TestUse:
    def test_use_simple(self) -> None:
        prog = parse_string("use score")
        stmt = prog.statements[0]
        assert isinstance(stmt, UseStatement)
        assert stmt.name == "score"
        assert stmt.config == {}

    def test_use_with_config(self) -> None:
        prog = parse_string("use player speed 0.02")
        stmt = prog.statements[0]
        assert isinstance(stmt, UseStatement)
        assert stmt.name == "player"
        assert stmt.config == {"speed": "0.02"}

    def test_use_with_multiple_config(self) -> None:
        prog = parse_string("use enemy-grid rows 2 cols 5")
        stmt = prog.statements[0]
        assert isinstance(stmt, UseStatement)
        assert stmt.name == "enemy-grid"
        assert stmt.config == {"rows": "2", "cols": "5"}

    def test_use_hyphenated_name(self) -> None:
        prog = parse_string("use game-lifecycle")
        stmt = prog.statements[0]
        assert isinstance(stmt, UseStatement)
        assert stmt.name == "game-lifecycle"

    def test_use_empty_raises(self) -> None:
        with pytest.raises(ParseError, match="use requires"):
            parse_string("use")


# ── Comments, blanks, multi-line ───────────────────────────────


class TestCommentsAndBlanks:
    def test_comment(self) -> None:
        prog = parse_string("# this is a comment")
        stmt = prog.statements[0]
        assert isinstance(stmt, CommentStatement)
        assert stmt.text == "this is a comment"

    def test_blank_line(self) -> None:
        prog = parse_string("\n")
        assert isinstance(prog.statements[0], BlankStatement)

    def test_indented_blank(self) -> None:
        prog = parse_string("   ")
        assert isinstance(prog.statements[0], BlankStatement)

    def test_indented_code(self) -> None:
        prog = parse_string("    set x to 100")
        stmt = prog.statements[0]
        assert isinstance(stmt, SetStatement)
        assert stmt.target == "x"


class TestMultiLine:
    def test_hello_world(self) -> None:
        prog = parse_string('print "Hello, World!"')
        assert len(prog.statements) == 1
        assert prog.statements[0].text == "Hello, World!"

    def test_simple_programme(self) -> None:
        prog = parse_string(
            '# Simple hello world program\n'
            '\n'
            'print "Hello, World!"\n'
        )
        assert len(prog.statements) == 3
        assert isinstance(prog.statements[0], CommentStatement)
        assert isinstance(prog.statements[1], BlankStatement)
        assert isinstance(prog.statements[2], PrintStatement)

    def test_event_handler(self) -> None:
        code = (
            "when start then\n"
            '    print "Game started!"\n'
            "end\n"
        )
        prog = parse_string(code)
        assert len(prog.statements) == 3
        assert isinstance(prog.statements[0], WhenStatement)
        assert isinstance(prog.statements[1], PrintStatement)
        assert isinstance(prog.statements[2], EndStatement)


# ── File loading ───────────────────────────────────────────────


class TestFileLoading:
    def test_parse_file(self, tmp_path: Path) -> None:
        p = tmp_path / "test.rosh"
        p.write_text('print "hello"\n')
        prog = parse_file(p)
        assert len(prog.statements) == 1
        assert prog.source == str(p)

    def test_parse_hello_example(self) -> None:
        hello_path = Path(__file__).parent.parent / "examples" / "hello.rosh"
        if hello_path.exists():
            prog = parse_file(hello_path)
            prints = [s for s in prog.statements if isinstance(s, PrintStatement)]
            assert len(prints) == 1
            assert prints[0].text == "hello world"


# ── Error reporting ────────────────────────────────────────────


class TestIf:
    def test_if_simple(self) -> None:
        prog = parse_string('if score > 10\n  print "yes"\nend')
        stmt = prog.statements[0]
        assert isinstance(stmt, IfStatement)
        assert stmt.condition == "score > 10"
        assert len(stmt.then_body) == 1
        assert isinstance(stmt.then_body[0], PrintStatement)
        assert stmt.else_body == []

    def test_if_else(self) -> None:
        prog = parse_string('if lives == 0\n  print "game over"\nelse\n  print "keep going"\nend')
        stmt = prog.statements[0]
        assert isinstance(stmt, IfStatement)
        assert stmt.condition == "lives == 0"
        assert len(stmt.then_body) == 1
        assert len(stmt.else_body) == 1
        assert isinstance(stmt.else_body[0], PrintStatement)

    def test_if_with_then_keyword(self) -> None:
        prog = parse_string('if score > 10 then\n  print "high"\nend')
        stmt = prog.statements[0]
        assert isinstance(stmt, IfStatement)
        assert stmt.condition == "score > 10"

    def test_if_nested(self) -> None:
        code = "if x > 0\n  if y > 0\n    print \"both positive\"\n  end\nend"
        prog = parse_string(code)
        outer = prog.statements[0]
        assert isinstance(outer, IfStatement)
        inner = outer.then_body[0]
        assert isinstance(inner, IfStatement)
        assert inner.condition == "y > 0"

    def test_if_inside_when(self) -> None:
        code = "when start\n  if score > 10\n    print \"high\"\n  end\nend"
        prog = parse_string(code)
        # when/end are still flat — collected at runtime
        # But the if/else/end inside should be collected by parser
        from rosh_lang.model import WhenStatement, EndStatement
        assert isinstance(prog.statements[0], WhenStatement)
        assert isinstance(prog.statements[1], IfStatement)
        assert isinstance(prog.statements[2], EndStatement)

    def test_if_no_condition_error(self) -> None:
        with pytest.raises(ParseError, match="if requires a condition"):
            parse_string("if\n  print \"x\"\nend")

    def test_if_no_end_error(self) -> None:
        with pytest.raises(ParseError, match="no matching end"):
            parse_string("if score > 0\n  print \"x\"")

    def test_if_multi_body(self) -> None:
        code = 'if health <= 0\n  print "dead"\n  set status to "gameover"\nelse\n  print "alive"\nend'
        prog = parse_string(code)
        stmt = prog.statements[0]
        assert isinstance(stmt, IfStatement)
        assert len(stmt.then_body) == 2
        assert len(stmt.else_body) == 1


class TestErrors:
    def test_unknown_keyword(self) -> None:
        with pytest.raises(ParseError, match="Unknown keyword"):
            parse_string("frobnicate everything")

    def test_error_includes_line_number(self) -> None:
        with pytest.raises(ParseError, match=":2:"):
            parse_string('print "hello"\nfrobnicate')

    def test_error_includes_source(self) -> None:
        with pytest.raises(ParseError, match="test.rosh"):
            parse_string("frobnicate", source="test.rosh")


# ── Animate ────────────────────────────────────────────────


class TestAnimate:
    def test_basic(self) -> None:
        prog = parse_string('animate player sheet "player-sheet.png" frames 4')
        stmt = prog.statements[0]
        assert isinstance(stmt, AnimateStatement)
        assert stmt.name == "player"
        assert stmt.sheet == "player-sheet.png"
        assert stmt.frames == 4
        assert stmt.speed == 8  # default
        assert stmt.mode == "loop"  # default

    def test_with_speed(self) -> None:
        prog = parse_string('animate hero sheet "hero.png" frames 6 speed 12')
        stmt = prog.statements[0]
        assert isinstance(stmt, AnimateStatement)
        assert stmt.speed == 12

    def test_with_mode(self) -> None:
        prog = parse_string('animate explosion sheet "boom.png" frames 9 mode once')
        stmt = prog.statements[0]
        assert isinstance(stmt, AnimateStatement)
        assert stmt.mode == "once"

    def test_with_all_options(self) -> None:
        prog = parse_string('animate player sheet "walk.png" frames 4 speed 10 mode bounce')
        stmt = prog.statements[0]
        assert isinstance(stmt, AnimateStatement)
        assert stmt.frames == 4
        assert stmt.speed == 10
        assert stmt.mode == "bounce"

    def test_missing_sheet(self) -> None:
        with pytest.raises(ParseError, match="sheet"):
            parse_string("animate player frames 4")

    def test_missing_frames(self) -> None:
        with pytest.raises(ParseError, match="frames"):
            parse_string('animate player sheet "test.png"')

    def test_missing_name(self) -> None:
        with pytest.raises(ParseError, match="animate requires"):
            parse_string("animate")


# ── after ──────────────────────────────────────────────────────


class TestAfter:
    def test_basic_after(self) -> None:
        prog = parse_string("after 2 send wave_2")
        stmt = prog.statements[0]
        assert isinstance(stmt, AfterStatement)
        assert stmt.delay == 2.0
        assert stmt.event == "wave_2"

    def test_float_delay(self) -> None:
        prog = parse_string("after 0.5 send spawn")
        stmt = prog.statements[0]
        assert isinstance(stmt, AfterStatement)
        assert stmt.delay == 0.5
        assert stmt.event == "spawn"

    def test_missing_send(self) -> None:
        with pytest.raises(ParseError, match="send"):
            parse_string("after 2 fire wave")

    def test_missing_event(self) -> None:
        with pytest.raises(ParseError, match="after requires"):
            parse_string("after 2 send")

    def test_non_numeric_delay(self) -> None:
        with pytest.raises(ParseError, match="number"):
            parse_string("after soon send wave")
