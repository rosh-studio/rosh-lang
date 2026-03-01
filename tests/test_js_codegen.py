"""Tests for JS codegen — AST → JavaScript code generation."""

from __future__ import annotations

from rosh_lang.parser import parse_string
from rosh_lang.targets._js_codegen import compile_programme


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
    def test_say(self):
        prog = parse_string("say hello world")
        result = compile_programme(prog)
        assert 'rosh.appendOutput(rosh.interpolate("hello world"))' in result.init_code


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
        """on hit say 'Ouch!' → same as print in JS."""
        prog = parse_string('event hit\non hit say "Ouch!"')
        result = compile_programme(prog)
        assert "rosh.appendOutput" in result.handler_code

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
