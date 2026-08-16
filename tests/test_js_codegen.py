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

    def test_create_object_no_asset_defaults_for_web(self):
        prog = parse_string("create object stone")
        result = compile_programme(prog)
        assert 'rosh.set("stone._asset.id"' not in result.init_code

    def test_create_object_asset_defaults_for_threejs(self):
        prog = parse_string("create object stone")
        result = compile_programme(prog, target="threejs")
        assert 'rosh.create("object", "stone")' in result.init_code
        assert 'rosh.set("stone._asset.id", "stone");' in result.init_code
        assert 'rosh.set("stone.shape", "box");' in result.init_code

    def test_create_unknown_object_emits_asset_request_for_threejs(self):
        prog = parse_string("create object blargle")
        result = compile_programme(prog, target="threejs")
        assert 'rosh.set("blargle._asset.status", "missing");' in result.init_code
        assert 'rosh.set("blargle._asset.query", "blargle");' in result.init_code
        assert 'rosh.set("blargle._asset.reason", "no_match");' in result.init_code
        assert 'rosh.set("blargle.shape", "box");' in result.init_code
        assert 'rosh.set("blargle.color", "grey");' in result.init_code
        assert 'rosh.addToList("_assetRequests"' in result.init_code

    def test_unknown_threejs_asset_request_executes(self):
        node = shutil.which("node")
        if node is None:
            pytest.skip("node is required for generated JS execution tests")

        compiled = compile_programme(
            parse_string("create object blargle"),
            target="threejs",
        )
        script = "\n".join([
            JS_RUNTIME_CORE,
            compiled.init_code,
            "console.log(JSON.stringify(rosh.state._assetRequests));",
        ])
        result = subprocess.run(
            [node],
            input=script,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        requests = json.loads(result.stdout.strip().splitlines()[-1])
        assert requests == [{
            "object": "blargle",
            "query": "blargle",
            "target": "threejs",
            "status": "open",
            "reason": "no_match",
            "needed": ["model", "thumbnail", "renderer_defaults"],
        }]

    def test_known_threejs_asset_does_not_request_asset(self):
        result = compile_programme(parse_string("create object stone"), target="threejs")
        assert 'rosh.addToList("_assetRequests"' not in result.init_code

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

    def test_one_line_on_update_sets_needs_loop(self):
        """16-Aug-2026 regression: the one-line "on <event> <action>" form
        (OnStatement) never set needs_loop, only the block "when ... end"
        form did — so a programme using only one-line `on update ...`
        reactors (no block-form when/animate) compiled with needs_loop
        False, web.py never emitted rosh.startLoop(), and the handler was
        registered but never once invoked. The bundled `ball` widget's
        entire wall-bounce implementation is exactly this shape — this bug
        made `use ball` (and any "on update ..."-only programme) silently
        never animate at all. Confirmed live via rosh.cloud's describe-to-
        run flow generating a "bouncing ball" that never moved."""
        prog = parse_string("on update set x to x + 0.01")
        result = compile_programme(prog)
        assert result.has_handlers
        assert result.needs_loop
        assert 'rosh.on("update"' in result.handler_code

    def test_one_line_on_collision_sets_needs_loop(self):
        """Bare "on collision <action>" (no name filter) parses to the
        literal event "collision" and is a real, functional pattern —
        unlike "on collision <name> <action>", which parses to a combined
        event name like "collision_ball" that the runtime never actually
        fires (only bare "collision" is ever rosh.send()'d) and is a
        separate, pre-existing bug not addressed by this fix; see
        rosh-dev/BUGS.md 16-Aug-2026."""
        prog = parse_string("on collision set score to score + 1")
        result = compile_programme(prog)
        assert result.needs_loop

    def test_ball_widget_alone_sets_needs_loop(self):
        """End-to-end proof for the exact real-world shape that broke:
        `use ball` alone must produce a compiled programme whose script
        actually calls rosh.startLoop(), not just registers dead handlers."""
        from rosh_lang.targets.web import render_html

        prog = parse_string('use ball color "red"')
        html = render_html(prog)
        assert "startLoop()" in html

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

    def test_on_play(self):
        """on click play boom → JS handler with playAudio.

        2026-07-03: "play" wasn't in _emit_on's action dispatch at all, so
        "on <event> play <sound>" — an extremely natural pattern for
        reactive sound feedback — silently produced no JS whatsoever.
        """
        prog = parse_string("event click\non click play boom")
        result = compile_programme(prog)
        assert 'rosh.playAudio("boom", "once")' in result.handler_code

    def test_on_play_with_mode(self):
        prog = parse_string("event alarm\non alarm play siren loop")
        result = compile_programme(prog)
        assert 'rosh.playAudio("siren", "loop")' in result.handler_code

    def test_on_with_condition(self):
        """on check when level > 3 set message to 'high' → conditional handler."""
        prog = parse_string(
            'event check\non check when level > 3 set message to "high"'
        )
        result = compile_programme(prog)
        assert 'rosh.get("level")' in result.handler_code
        assert "> 3" in result.handler_code

    def test_on_condition_with_invalid_operator_raises(self):
        """16-Aug-2026 regression: 'on update when collision ball player1
        set ...' (mixing the one-line reactor form with "collision" used
        as if it were a condition operator, instead of the correct block
        form "when collision A B ... end") used to silently compile field=
        "collision", op="ball", val="player1" into literally invalid
        JavaScript (`if (_v ball player1)`), which aborted the entire
        <script> block at parse time — a completely blank page with no
        error surfaced anywhere, even though the API reported success.
        Confirmed live via a describe-to-run "pong" prompt. It must now
        raise instead, so a bad condition fails loudly at compile time
        rather than shipping broken JS — see rosh-dev/BUGS.md 16-Aug-2026."""
        import pytest

        prog = parse_string(
            "event tick\non tick when collision ball player1 set score to score + 1"
        )
        with pytest.raises(ValueError, match="not a valid comparison operator"):
            compile_programme(prog)

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

    def test_if_with_invalid_operator_raises(self):
        """Same class of bug as OnStatement's condition handling (see
        test_on_condition_with_invalid_operator_raises) reached via the
        block "if" form instead — the parser doesn't validate the operator
        token either, so this must be caught at codegen time."""
        import pytest

        prog = parse_string('if score bogus 10\n  print "x"\nend')
        with pytest.raises(ValueError, match="not a valid comparison operator"):
            compile_programme(prog)


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

    def test_payload_emitted(self):
        prog = parse_string("after 0.5 send scored value=5")
        result = compile_programme(prog)
        assert 'rosh.send("scored", {"value": "5"});' in result.init_code


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


# ── define/do function-name code injection (round 5, 16-Aug-2026) ─────
#
# _parse_define/_parse_do (core/parser.py) accept any non-whitespace token
# as a function name — unlike every other user-controlled string in this
# module, _safe_fn_name() spliced that name directly into generated JS
# *source code* (`f"function {name}() {{...}}"`), not into a string or
# JSON value. None of the JSON/string escaping fixed earlier the same day
# (_json_for_inline_script, _escape_js) applies to a code-generation sink:
# a name like `x(){};(function(){...})();function y` closes the function
# declaration early, runs an IIFE as a top-level statement, and re-opens a
# new function so the rest still parses — no string-breakout involved at
# any point. Found by an external review; confirmed here by actually
# executing the generated JS in Node (matching how the review proved it),
# not just by string-matching the output, since a naive substring check
# for the payload is blind to "present but inert vs. actually executed".
class TestSafeFnNameCodeInjection:
    MALICIOUS_NAME = 'x(){};(function(){globalThis["__ROSH_PWNED__"]=true})();function/**/y'

    def _program(self) -> str:
        return (
            f'define {self.MALICIOUS_NAME}\n'
            '  print "hi"\n'
            'end\n'
            'when click\n'
            '  print "hi"\n'
            'end'
        )

    def test_safe_fn_name_only_contains_identifier_characters(self):
        from rosh_lang.targets._js_codegen import _safe_fn_name
        import re

        safe = _safe_fn_name(self.MALICIOUS_NAME)
        assert re.fullmatch(r"[A-Za-z0-9_]+", safe), safe

    def test_malicious_define_name_does_not_execute_as_js(self):
        node = shutil.which("node")
        if node is None:
            pytest.skip("node is required for generated JS execution tests")

        compiled = compile_programme(parse_string(self._program()))
        script = "\n".join([
            JS_RUNTIME_CORE,
            compiled.init_code,
            compiled.handler_code,
            'console.log(JSON.stringify({pwned: globalThis.__ROSH_PWNED__ === true}));',
        ])
        result = subprocess.run(
            [node], input=script, capture_output=True, text=True, check=False,
        )
        # A syntax error here would mean the sanitised name produced
        # invalid JS, not just unsafe JS — also a bug, so don't swallow it.
        assert result.returncode == 0, result.stderr
        parsed = json.loads(result.stdout.strip().splitlines()[-1])
        assert parsed["pwned"] is False, "injected payload executed as live JS"


# ── repeat-as save-slot code injection (round 6, 16-Aug-2026) ─────────
#
# Found by a spawned adversarial review explicitly asked to hunt for OTHER
# instances of round 5's bug shape (a name spliced into JS *code*, not a
# string/JSON value) — `_emit_repeat`'s save-slot variable had the exact
# same incomplete mitigation `_safe_fn_name` had before its round-5 fix
# (only "-"/"." replaced), spliced unquoted into `var _had_{safe} = ...,
# _prev_{safe} = ...`. `repeat N as <var>` accepts any non-whitespace
# token for <var> (core/parser.py's _parse_repeat), so a name using the
# comma operator inside the `var` declarator's initializer runs arbitrary
# code with the loop still executing normally afterwards — no visible
# sign anything happened. Fixed with the same [A-Za-z0-9_] whitelist.
class TestRepeatAsCodeInjection:
    MALICIOUS_VAR = "z=(PWNEDMARKER=1,1),q"

    def _program(self) -> str:
        return f'repeat 3 as {self.MALICIOUS_VAR}\n  print "hi"\nend'

    def test_malicious_repeat_var_does_not_execute_as_js(self):
        node = shutil.which("node")
        if node is None:
            pytest.skip("node is required for generated JS execution tests")

        compiled = compile_programme(parse_string(self._program()))
        script = "\n".join([
            JS_RUNTIME_CORE,
            compiled.init_code,
            'console.log(JSON.stringify({'
            'pwned: typeof PWNEDMARKER !== "undefined" && PWNEDMARKER === 1, '
            'output: rosh._outputBuffer'
            '}));',
        ])
        result = subprocess.run(
            [node], input=script, capture_output=True, text=True, check=False,
        )
        assert result.returncode == 0, result.stderr
        parsed = json.loads(result.stdout.strip().splitlines()[-1])
        assert parsed["pwned"] is False, "injected repeat-as var executed as live JS"
        # The loop itself must still behave normally — proves the fix
        # sanitised the name rather than breaking the feature outright.
        assert parsed["output"] == ["hi", "hi", "hi"]
