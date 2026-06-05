"""Tests for JS codegen — AST → JavaScript code generation."""

from __future__ import annotations

import json
import shutil
import subprocess
import textwrap

import pytest

from rosh_lang.core.parser import parse_string
from rosh_lang.targets._js_codegen import compile_programme, _escape_js
from rosh_lang.targets._js_runtime import JS_RUNTIME_CORE


def _execute_js(source: str, interaction: str = "") -> dict:
    """Run generated JS against JS_RUNTIME_CORE and return observable state."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is required for generated JS execution tests")

    compiled = compile_programme(parse_string(source))
    script = "\n".join([
        JS_RUNTIME_CORE,
        "// -- generated init --",
        compiled.init_code,
        "// -- generated handlers --",
        compiled.handler_code,
        "// -- test interaction --",
        interaction,
        textwrap.dedent(
            """
            console.log(JSON.stringify({
              state: rosh.state,
              output: rosh._outputBuffer,
              handlers: Object.keys(rosh.handlers).sort()
            }));
            """
        ),
    ])
    result = subprocess.run(
        [node],
        input=script,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout.strip().splitlines()[-1])


# ── Statement emitters ────────────────────────────────────────────


class TestEmitPrint:
    def test_simple_print(self):
        prog = parse_string('print "hello"')
        result = compile_programme(prog)
        assert 'rosh.appendOutput(rosh.interpolate("hello"))' in result.init_code

    def test_print_with_interpolation(self):
        prog = parse_string('print "Score: {score}"')
        result = compile_programme(prog)
        assert "Score: {score}" in result.init_code


class TestEmitCreate:
    def test_create_object(self):
        prog = parse_string("create object box")
        result = compile_programme(prog)
        assert 'rosh.create("object", "box")' in result.init_code

    def test_create_number(self):
        prog = parse_string("create number score")
        result = compile_programme(prog)
        assert 'rosh.create("number", "score")' in result.init_code


class TestEmitSet:
    def test_set_simple(self):
        prog = parse_string("create number score\nset score to 42")
        result = compile_programme(prog)
        assert 'rosh.set("score", rosh.evalSetValue("score", "42"))' in result.init_code

    def test_set_dotted(self):
        prog = parse_string('create object box\nset box.color to "red"')
        result = compile_programme(prog)
        assert 'rosh.set("box.color"' in result.init_code

    def test_set_arithmetic(self):
        prog = parse_string("create number score\nset score to score + 1")
        result = compile_programme(prog)
        assert "score + 1" in result.init_code

    def test_set_random(self):
        prog = parse_string("set x to random")
        result = compile_programme(prog)
        assert '"random"' in result.init_code

    def test_set_random_range(self):
        prog = parse_string("set x to random 0.1 0.9")
        result = compile_programme(prog)
        assert '"random 0.1 0.9"' in result.init_code

    def test_set_clamp(self):
        prog = parse_string("create number x\nset x to clamp x 0.0 1.0")
        result = compile_programme(prog)
        assert '"clamp x 0.0 1.0"' in result.init_code

    def test_set_count_expression(self):
        result = compile_programme(parse_string("set n to count of items"))
        assert '"count of items"' in result.init_code


class TestEmitDestroy:
    def test_destroy(self):
        prog = parse_string("create object box\ndestroy box")
        result = compile_programme(prog)
        assert 'rosh.destroy("box")' in result.init_code


class TestEmitSend:
    def test_send_simple(self):
        prog = parse_string("event boom\nsend boom")
        result = compile_programme(prog)
        assert 'rosh.send("boom")' in result.init_code

    def test_send_with_payload(self):
        prog = parse_string("event scored\nsend scored points=10")
        result = compile_programme(prog)
        assert 'rosh.send("scored"' in result.init_code
        assert '"points"' in result.init_code


class TestEmitSay:
    def test_say_uses_rosh_say(self):
        prog = parse_string("say hello world")
        result = compile_programme(prog)
        assert 'rosh.say(rosh.interpolate("hello world"))' in result.init_code

    def test_say_does_not_use_append_output_directly(self):
        prog = parse_string("say hello world")
        result = compile_programme(prog)
        assert 'rosh.appendOutput(rosh.interpolate("hello world"))' not in result.init_code


# ── compile_programme ─────────────────────────────────────────────


class TestCompileProgramme:
    def test_static_programme(self):
        prog = parse_string('create object box\nprint "hi"')
        result = compile_programme(prog)
        assert not result.has_handlers
        assert not result.needs_loop

    def test_click_handler(self):
        prog = parse_string(
            'when click\n  print "clicked"\nend'
        )
        result = compile_programme(prog)
        assert result.has_handlers
        assert not result.needs_loop
        assert 'rosh.on("click"' in result.handler_code

    def test_named_click_handler(self):
        prog = parse_string(
            'when click box\n  print "box clicked"\nend'
        )
        result = compile_programme(prog)
        assert result.has_handlers
        assert 'rosh.on("click_box"' in result.handler_code

    def test_keydown_handler(self):
        prog = parse_string(
            'when keydown\n  print "key pressed"\nend'
        )
        result = compile_programme(prog)
        assert result.has_handlers
        assert 'rosh.on("keydown"' in result.handler_code

    def test_update_sets_needs_loop(self):
        prog = parse_string(
            "when update\n  set score to score + 1\nend"
        )
        result = compile_programme(prog)
        assert result.has_handlers
        assert result.needs_loop
        assert 'rosh.on("update"' in result.handler_code

    def test_collision_sets_needs_loop(self):
        prog = parse_string(
            'when collision hero enemy\n  print "hit!"\nend'
        )
        result = compile_programme(prog)
        assert result.has_handlers
        assert result.needs_loop
        assert 'rosh.on("collision"' in result.handler_code
        assert "payload.a" in result.handler_code
        assert "hero" in result.handler_code
        assert "enemy" in result.handler_code

    def test_collision_wildcard(self):
        """when collision bullet.* enemy → startsWith filter."""
        prog = parse_string(
            'when collision bullet.* enemy\n  print "hit!"\nend'
        )
        result = compile_programme(prog)
        assert result.has_handlers
        assert result.needs_loop
        assert 'startsWith("bullet.")' in result.handler_code
        assert '"enemy"' in result.handler_code

    def test_collision_wildcard_both_sides(self):
        """when collision bullet.* enemy.* → both sides use startsWith."""
        prog = parse_string(
            'when collision bullet.* enemy.*\n  print "hit!"\nend'
        )
        result = compile_programme(prog)
        assert 'startsWith("bullet.")' in result.handler_code
        assert 'startsWith("enemy.")' in result.handler_code

    def test_collision_exact_unchanged(self):
        """Exact collision names still use === comparison."""
        prog = parse_string(
            'when collision hero enemy\n  print "hit!"\nend'
        )
        result = compile_programme(prog)
        assert 'payload.a === "hero"' in result.handler_code
        assert 'payload.b === "enemy"' in result.handler_code

    def test_handler_body_contains_statements(self):
        prog = parse_string(
            'when click\n  set score to score + 1\n  print "Score: {score}"\nend'
        )
        result = compile_programme(prog)
        assert 'rosh.set("score"' in result.handler_code
        assert "rosh.appendOutput" in result.handler_code

    def test_comments_and_blanks_ignored(self):
        prog = parse_string("# comment\n\ncreate object box")
        result = compile_programme(prog)
        assert 'rosh.create("object", "box")' in result.init_code
        assert "comment" not in result.init_code

    def test_mixed_init_and_handlers(self):
        prog = parse_string(
            "create object box\n"
            "set box.x to 0.5\n"
            'when click box\n  print "clicked"\nend'
        )
        result = compile_programme(prog)
        assert 'rosh.create("object", "box")' in result.init_code
        assert 'rosh.set("box.x"' in result.init_code
        assert result.has_handlers
        assert 'rosh.on("click_box"' in result.handler_code

    def test_named_component_alias_used_in_js(self):
        result = compile_programme(parse_string("use counter as clicks"))
        assert '"clicks.value"' in result.init_code
        assert '"counter.value"' not in result.init_code


class TestGeneratedJsExecution:
    def test_executes_init_state_and_output(self):
        result = _execute_js(
            'create object box\n'
            'set box.color to "red"\n'
            'create number score\n'
            'set score to 41\n'
            'set score to score + 1\n'
            'print "Score: {score}"'
        )

        assert result["state"]["box"]["color"] == "red"
        assert result["state"]["score"] == 42
        assert result["output"] == ["Score: 42"]

    def test_executes_when_handler_and_restores_payload(self):
        result = _execute_js(
            'create number score\n'
            'set score to 0\n'
            'when scored\n'
            '  set score to score + amount\n'
            '  print "Score: {score}"\n'
            'end',
            'rosh.send("scored", {amount: 5});',
        )

        assert result["handlers"] == ["scored"]
        assert result["state"]["score"] == 5
        assert "amount" not in result["state"]
        assert result["output"] == ["Score: 5"]

    def test_executes_if_else_and_repeat_cleanup(self):
        result = _execute_js(
            'create number total\n'
            'repeat 3 as i\n'
            '  set total to total + i\n'
            'end\n'
            'if total == 6\n'
            '  print "ok"\n'
            'else\n'
            '  print "bad"\n'
            'end'
        )

        assert result["state"]["total"] == 6
        assert "i" not in result["state"]
        assert result["output"] == ["ok"]

    def test_executes_list_mutation_and_foreach_cleanup(self):
        result = _execute_js(
            'create list items\n'
            'add "Ada" to items\n'
            'add "Grace" to items\n'
            'remove "Ada" from items\n'
            'for each name in items\n'
            '  print "Hello {name}"\n'
            'end'
        )

        assert result["state"]["items"] == ["Grace"]
        assert "name" not in result["state"]
        assert result["output"] == ["Hello Grace"]


class TestCollectionCodegen:
    def test_add_remove_and_foreach_emit(self):
        result = compile_programme(parse_string(
            "create list items\n"
            "add 1 to items\n"
            "remove 1 from items\n"
            "for each item in items\n  print {item}\nend"
        ))
        assert 'rosh.addToList("items"' in result.init_code
        assert 'rosh.removeFromList("items"' in result.init_code
        assert 'rosh.forEach("items", "item"' in result.init_code
        assert "rosh.appendOutput" in result.init_code

    def test_nothing_condition_emits_null(self):
        result = compile_programme(parse_string(
            "if value == nothing\n  print absent\nend"
        ))
        assert 'rosh.get("value") == null' in result.init_code

    def test_nothing_inequality_emits_null(self):
        result = compile_programme(parse_string(
            "if value != nothing\n  print present\nend"
        ))
        assert 'rosh.get("value") != null' in result.init_code


# ── Per-key event filtering ──────────────────────────────────────


class TestKeyFiltering:
    def test_keydown_with_key_name(self):
        """when keydown ArrowRight → filters by key in handler body."""
        prog = parse_string(
            'when keydown ArrowRight\n  print "right"\nend'
        )
        result = compile_programme(prog)
        assert result.has_handlers
        assert 'rosh.on("keydown"' in result.handler_code
        assert 'payload.key !== "ArrowRight"' in result.handler_code

    def test_keydown_without_key_name(self):
        """when keydown (no args) → fires on all keys, no filter."""
        prog = parse_string(
            'when keydown\n  print "any key"\nend'
        )
        result = compile_programme(prog)
        assert 'rosh.on("keydown"' in result.handler_code
        assert "payload.key !===" not in result.handler_code

    def test_keyup_with_key_name(self):
        """when keyup ArrowLeft → filters by key."""
        prog = parse_string(
            'when keyup ArrowLeft\n  print "released"\nend'
        )
        result = compile_programme(prog)
        assert result.has_handlers
        assert 'rosh.on("keyup"' in result.handler_code
        assert 'payload.key !== "ArrowLeft"' in result.handler_code

    def test_keydown_multiple_handlers(self):
        """Multiple per-key handlers compile independently."""
        prog = parse_string(
            'when keydown ArrowLeft\n  print "left"\nend\n'
            'when keydown ArrowRight\n  print "right"\nend'
        )
        result = compile_programme(prog)
        assert result.handler_code.count('rosh.on("keydown"') == 2
        assert "ArrowLeft" in result.handler_code
        assert "ArrowRight" in result.handler_code

    def test_keydown_does_not_set_needs_loop(self):
        """keydown handlers don't require the game loop."""
        prog = parse_string(
            'when keydown ArrowRight\n  print "right"\nend'
        )
        result = compile_programme(prog)
        assert not result.needs_loop


# ── On-statement (one-line event reactors) ───────────────────────


class TestOnStatement:
    def test_on_set(self):
        """on alarm set status to triggered → JS handler with set."""
        prog = parse_string(
            'event alarm\non alarm set status to "triggered"'
        )
        result = compile_programme(prog)
        assert result.has_handlers
        assert 'rosh.on("alarm"' in result.handler_code
        assert 'rosh.set("status"' in result.handler_code

    def test_on_send(self):
        """on hit send explosion → JS handler with send."""
        prog = parse_string("event hit\non hit send explosion")
        result = compile_programme(prog)
        assert 'rosh.send("explosion")' in result.handler_code

    def test_on_print(self):
        """on hit print 'Ouch!' → JS handler with appendOutput."""
        prog = parse_string('event hit\non hit print "Ouch!"')
        result = compile_programme(prog)
        assert "rosh.appendOutput" in result.handler_code
        assert "Ouch!" in result.handler_code

    def test_on_say(self):
        """on hit say 'Ouch!' → rosh.say() in JS (fires say event, tracks _last_said)."""
        prog = parse_string('event hit\non hit say "Ouch!"')
        result = compile_programme(prog)
        assert "rosh.say" in result.handler_code
        assert "Ouch!" in result.handler_code

    def test_on_destroy(self):
        """on explode destroy enemy → JS handler with destroy."""
        prog = parse_string("event explode\non explode destroy enemy")
        result = compile_programme(prog)
        assert 'rosh.destroy("enemy")' in result.handler_code

    def test_on_with_condition(self):
        """on check when level > 3 set message to 'high' → conditional handler."""
        prog = parse_string(
            'event check\non check when level > 3 set message to "high"'
        )
        result = compile_programme(prog)
        assert 'rosh.get("level")' in result.handler_code
        assert "> 3" in result.handler_code

    def test_event_declaration_is_noop(self):
        """event declarations produce no JS output."""
        prog = parse_string("event alarm")
        result = compile_programme(prog)
        assert result.init_code == ""
        assert result.handler_code == ""
        assert not result.has_handlers


# ── Sprite codegen ───────────────────────────────────────────────


class TestSoundCodegen:
    def test_sound_emits_register(self):
        """sound laser 'short blast' → rosh.registerSound('laser', {...})."""
        prog = parse_string('sound laser "short laser blast"')
        result = compile_programme(prog)
        assert 'rosh.registerSound("laser"' in result.init_code
        assert '"layers"' in result.init_code

    def test_sound_preset_params(self):
        """Sound with a known preset keyword emits correct params."""
        prog = parse_string('sound zap "laser shoot"')
        result = compile_programme(prog)
        assert '"square"' in result.init_code
        assert '"frequency":800' in result.init_code

    def test_play_emits_play_audio(self):
        """play laser → rosh.playAudio('laser', 'once')."""
        prog = parse_string('sound laser "laser"\nplay laser')
        result = compile_programme(prog)
        assert 'rosh.playAudio("laser", "once")' in result.init_code

    def test_play_loop_mode(self):
        """play music loop → rosh.playAudio('music', 'loop')."""
        prog = parse_string('sound music "background"\nplay music loop')
        result = compile_programme(prog)
        assert 'rosh.playAudio("music", "loop")' in result.init_code

    def test_play_stop_mode(self):
        """play music stop → rosh.playAudio('music', 'stop')."""
        prog = parse_string('sound music "background"\nplay music stop')
        result = compile_programme(prog)
        assert 'rosh.playAudio("music", "stop")' in result.init_code

    def test_sound_in_handler(self):
        """sound inside a when block should emit in handler body."""
        prog = parse_string(
            'when click\n  sound ding "coin collect"\nend'
        )
        result = compile_programme(prog)
        assert 'rosh.registerSound("ding"' in result.handler_code

    def test_play_in_handler(self):
        """play inside a when block should emit in handler body."""
        prog = parse_string(
            'when click\n  play laser\nend'
        )
        result = compile_programme(prog)
        assert 'rosh.playAudio("laser"' in result.handler_code

    def test_sound_no_handlers(self):
        """Top-level sound doesn't create handlers or game loop."""
        prog = parse_string('sound laser "laser blast"')
        result = compile_programme(prog)
        assert not result.has_handlers
        assert not result.needs_loop


class TestSpriteCodegen:
    def test_sprite_emits_set(self):
        """sprite player 'blue spaceship' → rosh.set('player.sprite', ...)."""
        prog = parse_string('sprite player "blue spaceship"')
        result = compile_programme(prog)
        assert 'rosh.set("player.sprite", "blue spaceship")' in result.init_code

    def test_sprite_in_handler(self):
        """sprite inside a when block should emit in handler body."""
        prog = parse_string(
            'when click\n  sprite player "red ship"\nend'
        )
        result = compile_programme(prog)
        assert 'rosh.set("player.sprite", "red ship")' in result.handler_code

    def test_sprite_no_handlers(self):
        """Top-level sprite doesn't create handlers or game loop."""
        prog = parse_string('sprite enemy "green alien"')
        result = compile_programme(prog)
        assert not result.has_handlers
        assert not result.needs_loop


# ── Variable arithmetic in JS runtime ────────────────────────────


class TestJSVariableArithmetic:
    """Test that evalSetValue handles variable references in arithmetic."""

    def test_variable_right_operand(self):
        """set x to x + drift — variable right operand resolves via get()."""
        prog = parse_string(
            "create number x\nset x to 10\n"
            "create number drift\nset drift to 3\n"
            "set x to x + drift"
        )
        result = compile_programme(prog)
        # The codegen should emit evalSetValue with the raw expression
        assert '"x + drift"' in result.init_code

    def test_cross_reference_left(self):
        """set x to y + 1 — cross-reference left operand."""
        prog = parse_string(
            "create number x\ncreate number y\n"
            "set y to 20\nset x to y + 1"
        )
        result = compile_programme(prog)
        assert '"y + 1"' in result.init_code

    def test_both_variable(self):
        """set x to y + z — both operands are variables."""
        prog = parse_string(
            "create number x\ncreate number y\ncreate number z\n"
            "set x to y + z"
        )
        result = compile_programme(prog)
        assert '"y + z"' in result.init_code

    def test_literal_arithmetic_still_works(self):
        """Existing literal arithmetic codegen is unchanged."""
        prog = parse_string("create number score\nset score to score + 1")
        result = compile_programme(prog)
        assert '"score + 1"' in result.init_code


class TestIfCodegen:
    """Tests for if/else JS codegen."""

    def test_if_simple(self):
        prog = parse_string(
            'create number score\n'
            'set score to 20\n'
            'if score > 10\n'
            '  print "high"\n'
            'end\n'
        )
        result = compile_programme(prog)
        assert 'if (rosh.get("score") > 10)' in result.init_code
        assert 'rosh.appendOutput' in result.init_code

    def test_if_else(self):
        prog = parse_string(
            'if lives == 0\n'
            '  print "game over"\n'
            'else\n'
            '  print "playing"\n'
            'end\n'
        )
        result = compile_programme(prog)
        assert '} else {' in result.init_code
        assert 'rosh.get("lives") === 0' in result.init_code

    def test_if_in_handler(self):
        prog = parse_string(
            'when start\n'
            '  if score > 10\n'
            '    print "high"\n'
            '  end\n'
            'end\n'
        )
        result = compile_programme(prog)
        assert 'if (rosh.get("score") > 10)' in result.handler_code

    def test_if_string_comparison(self):
        prog = parse_string(
            'if status == ready\n'
            '  print "go"\n'
            'end\n'
        )
        result = compile_programme(prog)
        assert 'rosh.get("status") === "ready"' in result.init_code

    def test_if_quoted_string_comparison_strips_source_quotes(self):
        """Quoted RHS values must not become strings containing literal quote characters."""
        prog = parse_string(
            'if phase == "playing"\n'
            '  print "go"\n'
            'end\n'
        )
        result = compile_programme(prog)
        assert 'rosh.get("phase") === "playing"' in result.init_code
        assert '\\"playing\\"' not in result.init_code

    def test_else_if_chain(self):
        prog = parse_string(
            'if x > 5\n'
            '  print "big"\n'
            'else if x > 3\n'
            '  print "medium"\n'
            'else\n'
            '  print "small"\n'
            'end\n'
        )
        result = compile_programme(prog)
        assert 'rosh.get("x") > 5' in result.init_code
        assert '} else {' in result.init_code
        assert 'rosh.get("x") > 3' in result.init_code


class TestSceneCodegen:
    """Tests for scene (go/look) JS codegen."""

    def test_create_scene(self):
        prog = parse_string('create scene lobby')
        result = compile_programme(prog)
        assert 'rosh.createScene("lobby")' in result.init_code

    def test_go_scene(self):
        prog = parse_string(
            'create scene lobby\n'
            'go lobby\n'
        )
        result = compile_programme(prog)
        assert 'rosh.goScene("lobby")' in result.init_code

    def test_go_back(self):
        prog = parse_string('go back')
        result = compile_programme(prog)
        assert 'rosh.goScene("back")' in result.init_code


# ── Animate ────────────────────────────────────────────────


class TestEmitAnimate:
    def test_basic(self):
        prog = parse_string('animate player sheet "walk.png" frames 4')
        result = compile_programme(prog)
        assert 'rosh.registerAnimation("player"' in result.init_code
        assert '"frames":4' in result.init_code
        assert '"speed":8' in result.init_code
        assert '"mode":"loop"' in result.init_code

    def test_custom_speed_and_mode(self):
        prog = parse_string('animate hero sheet "hero.png" frames 6 speed 12 mode bounce')
        result = compile_programme(prog)
        assert '"speed":12' in result.init_code
        assert '"mode":"bounce"' in result.init_code


# ── after ──────────────────────────────────────────────────────


class TestEmitAfter:
    def test_basic_set_timeout(self):
        prog = parse_string("after 2 send wave_2")
        result = compile_programme(prog)
        assert 'setTimeout(function() { rosh.send("wave_2", {}); }, 2000)' in result.init_code

    def test_float_delay(self):
        prog = parse_string("after 0.5 send spawn")
        result = compile_programme(prog)
        assert 'setTimeout(function() { rosh.send("spawn", {}); }, 500)' in result.init_code

    def test_inside_handler_body(self):
        prog = parse_string(
            'when collision bullet.* enemy\n'
            '  after 0.5 send spawn_replacement\n'
            'end'
        )
        result = compile_programme(prog)
        assert "setTimeout" in result.handler_code
        assert 'rosh.send("spawn_replacement"' in result.handler_code

    def test_no_loop_required(self):
        """after alone should not trigger a game loop."""
        prog = parse_string("after 2 send wave_2")
        result = compile_programme(prog)
        assert not result.needs_loop


class TestEmitBackground:
    def test_background_colour(self):
        prog = parse_string('background "#ff0000"')
        result = compile_programme(prog)
        assert 'rosh.setBackground("#ff0000")' in result.init_code

    def test_background_image(self):
        prog = parse_string('background "sky.png"')
        result = compile_programme(prog)
        assert 'rosh.setBackground("sky.png")' in result.init_code

    def test_background_url(self):
        prog = parse_string('background "https://example.com/bg.jpg"')
        result = compile_programme(prog)
        assert 'rosh.setBackground("https://example.com/bg.jpg")' in result.init_code


# ── Security: _escape_js ──────────────────────────────────────────


class TestEscapeJs:
    def test_escapes_script_close_tag(self):
        """</script> in a string value must not close the enclosing <script> block."""
        assert "<\\/script>" in _escape_js("</script>")

    def test_escapes_all_slash_less_than(self):
        assert "<\\/" in _escape_js("</")

    def test_escapes_backslash(self):
        assert "\\\\" in _escape_js("\\")

    def test_escapes_double_quote(self):
        assert '\\"' in _escape_js('"')

    def test_escapes_single_quote(self):
        assert "\\'" in _escape_js("'")

    def test_escapes_newline(self):
        assert "\\n" in _escape_js("\n")

    def test_script_injection_in_print(self):
        """print with </script> payload must not break out of the script tag."""
        prog = parse_string('print "</script><script>alert(1)</script>"')
        result = compile_programme(prog)
        assert "</script>" not in result.init_code
        assert "<\\/script>" in result.init_code

    def test_script_injection_in_say(self):
        prog = parse_string('say "</script>evil"')
        result = compile_programme(prog)
        assert "</script>" not in result.init_code

    def test_script_injection_in_set(self):
        prog = parse_string('set label to "</script>evil"')
        result = compile_programme(prog)
        assert "</script>" not in result.init_code


# ── Repeat variable cleanup ───────────────────────────────────────


class TestRepeatVarCleanup:
    def test_repeat_with_var_saves_and_restores(self):
        """JS repeat-as must save the prior value and restore it after the loop."""
        prog = parse_string('repeat 3 as i\n  print "{i}"\nend')
        result = compile_programme(prog)
        # Save/restore pattern must be present
        assert 'rosh.has("i")' in result.init_code
        assert 'rosh.get("i")' in result.init_code
        # Restore branch
        assert 'rosh.set("i"' in result.init_code
        # Delete branch (when variable did not exist before loop)
        assert 'rosh.unset("i")' in result.init_code
        assert 'rosh.set("i", undefined)' not in result.init_code

    def test_repeat_var_save_slot_is_name_scoped(self):
        """Nested repeat-as loops must not clobber each other's save slots."""
        prog = parse_string(
            'repeat 2 as outer\n'
            '  repeat 2 as inner\n'
            '    print "{outer}.{inner}"\n'
            '  end\n'
            'end'
        )
        result = compile_programme(prog)
        # Each var gets its own save slot
        assert '_had_outer' in result.init_code
        assert '_had_inner' in result.init_code
        assert '_prev_outer' in result.init_code
        assert '_prev_inner' in result.init_code

    def test_repeat_without_var_no_unset(self):
        prog = parse_string('repeat 3\n  print "hi"\nend')
        result = compile_programme(prog)
        assert "rosh.unset" not in result.init_code
