"""Tests for the web target — HTML generation only (no server)."""

from __future__ import annotations

from pathlib import Path

from rosh_lang.parser import parse_string
from rosh_lang.targets.web import render_html

WIDGETS_DIR = Path(__file__).parent.parent / "examples" / "widgets"


# ── Print output ──────────────────────────────────────────────


class TestPrintOutput:
    """print statements should appear in the HTML output."""

    def test_simple_print(self):
        html = render_html(parse_string('print "hello world"'))
        assert "hello world" in html

    def test_multiple_prints_in_order(self):
        prog = parse_string('print "first"\nprint "second"\nprint "third"')
        html = render_html(prog)
        pos_first = html.index("first")
        pos_second = html.index("second")
        pos_third = html.index("third")
        assert pos_first < pos_second < pos_third

    def test_interpolation_in_print(self):
        prog = parse_string('create number score\nset score to 42\nprint "Score: {score}"')
        html = render_html(prog)
        assert "Score: 42" in html

    def test_empty_programme(self):
        html = render_html(parse_string(""))
        assert "<!DOCTYPE html>" in html
        assert "rosh" in html


# ── Visual objects ────────────────────────────────────────────


class TestVisualObjects:
    """create/set should produce positioned divs in the HTML."""

    def test_object_renders_as_div(self):
        prog = parse_string(
            'create object box\n'
            'set box.color to "red"'
        )
        html = render_html(prog)
        assert "rosh-object" in html
        assert 'data-name="box"' in html

    def test_positioned_object_css(self):
        prog = parse_string(
            "create object box\n"
            "set box.x to 0.5\n"
            "set box.y to 0.3\n"
            'set box.color to "blue"'
        )
        html = render_html(prog)
        assert "left: 50.0%" in html
        assert "top: 30.0%" in html
        assert "background-color: blue" in html

    def test_pixel_coordinates(self):
        prog = parse_string(
            "create object sprite\n"
            "set sprite.x to 200\n"
            "set sprite.y to 150\n"
        )
        html = render_html(prog)
        assert "200px" in html
        assert "150px" in html

    def test_object_dimensions(self):
        prog = parse_string(
            "create object box\n"
            "set box.width to 0.2\n"
            "set box.height to 0.15\n"
        )
        html = render_html(prog)
        assert "width: 20.0%" in html
        assert "height: 15.0%" in html

    def test_object_without_position(self):
        """Objects without x/y should not break layout."""
        prog = parse_string(
            'create object widget\n'
            'set widget.color to "green"'
        )
        html = render_html(prog)
        assert "rosh-object" in html
        assert "background-color: green" in html

    def test_multiple_objects(self):
        prog = parse_string(
            "create object a\n"
            'set a.color to "red"\n'
            "create object b\n"
            'set b.color to "blue"\n'
        )
        html = render_html(prog)
        assert 'data-name="a"' in html
        assert 'data-name="b"' in html

    def test_object_label(self):
        prog = parse_string(
            "create object box\n"
            'set box.label to "Hello"'
        )
        html = render_html(prog)
        assert "Hello" in html


# ── Page structure ────────────────────────────────────────────


class TestPageStructure:
    """HTML page should have correct structure and branding."""

    def test_doctype(self):
        html = render_html(parse_string('print "test"'))
        assert html.startswith("<!DOCTYPE html>")

    def test_has_canvas(self):
        html = render_html(parse_string('print "test"'))
        assert 'id="canvas"' in html

    def test_has_output_section(self):
        html = render_html(parse_string('print "test"'))
        assert 'id="output"' in html

    def test_has_footer_branding(self):
        html = render_html(parse_string('print "test"'))
        assert "Rosh Studio" in html
        assert "rosh.cloud" in html

    def test_dark_theme(self):
        html = render_html(parse_string('print "test"'))
        assert "#1a1a2e" in html  # dark background

    def test_html_escapes_output(self):
        prog = parse_string('print "<script>alert(1)</script>"')
        html = render_html(prog)
        assert "<script>" not in html
        assert "&lt;script&gt;" in html


# ── Mixed content ─────────────────────────────────────────────


class TestMixedContent:
    """Programmes with both objects and print output."""

    def test_objects_and_print(self):
        prog = parse_string(
            "create object box\n"
            'set box.color to "red"\n'
            "set box.x to 0.5\n"
            "set box.y to 0.5\n"
            'print "Score: 42"'
        )
        html = render_html(prog)
        assert "rosh-object" in html
        assert "Score: 42" in html
        assert "background-color: red" in html

    def test_game_example(self):
        """The game.rosh example should render correctly."""
        prog = parse_string(
            "create object box\n"
            "set box.x to 0.5\n"
            "set box.y to 0.5\n"
            "set box.width to 0.1\n"
            "set box.height to 0.1\n"
            'set box.color to "red"\n'
            'set box.label to "box"\n'
            "create number score\n"
            "set score to 42\n"
            'print "Score: 42"\n'
            'print "Game ready."'
        )
        html = render_html(prog)
        assert "left: 50.0%" in html
        assert "top: 50.0%" in html
        assert "background-color: red" in html
        assert "Score: 42" in html
        assert "Game ready." in html


# ── Interactive programmes ───────────────────────────────────────


class TestInteractiveRouting:
    """Programmes with when blocks should take the interactive path."""

    def test_static_programme_has_no_script(self):
        prog = parse_string('print "hello"')
        html = render_html(prog)
        assert "<script>" not in html

    def test_interactive_programme_has_script(self):
        prog = parse_string('when click\n  print "clicked"\nend')
        html = render_html(prog)
        assert "<script>" in html

    def test_interactive_preserves_page_structure(self):
        prog = parse_string('when click\n  print "clicked"\nend')
        html = render_html(prog)
        assert "<!DOCTYPE html>" in html
        assert 'id="canvas"' in html
        assert 'id="output"' in html
        assert "Rosh Studio" in html

    def test_interactive_preserves_dark_theme(self):
        prog = parse_string('when click\n  print "clicked"\nend')
        html = render_html(prog)
        assert "#1a1a2e" in html


class TestInteractiveJSRuntime:
    """Interactive HTML should contain the JS runtime."""

    def test_contains_rosh_object(self):
        prog = parse_string('when click\n  print "clicked"\nend')
        html = render_html(prog)
        assert "var rosh" in html

    def test_contains_state_manager(self):
        prog = parse_string('when click\n  print "clicked"\nend')
        html = render_html(prog)
        assert "rosh.get" in html or "function get(" in html

    def test_contains_event_dispatcher(self):
        prog = parse_string('when click\n  print "clicked"\nend')
        html = render_html(prog)
        assert "rosh.send" in html

    def test_contains_dom_sync(self):
        prog = parse_string('when click\n  print "clicked"\nend')
        html = render_html(prog)
        assert "syncAll" in html


class TestVisibilityInRuntime:
    """The JS runtime should support a visible property on objects."""

    def test_runtime_contains_visible_check(self):
        prog = parse_string('when click\n  print "clicked"\nend')
        html = render_html(prog)
        assert "obj.visible" in html

    def test_tickpools_in_runtime(self):
        prog = parse_string('when click\n  print "clicked"\nend')
        html = render_html(prog)
        assert "tickPools" in html

    def test_evalsetvalue_resolves_variable_references(self):
        """evalSetValue should resolve dotted name references to their values."""
        prog = parse_string('when click\n  print "clicked"\nend')
        html = render_html(prog)
        # The JS runtime should contain variable resolution in evalSetValue
        assert "var resolved = get(raw)" in html

    def test_collision_payload_includes_positions(self):
        """Collision send should include a_x, a_y, b_x, b_y."""
        prog = parse_string('when collision a b\n  print "hit"\nend')
        html = render_html(prog)
        assert "a_x: oa.x" in html
        assert "a_y: oa.y" in html
        assert "b_x: ob.x" in html
        assert "b_y: ob.y" in html


class TestInteractiveCodegen:
    """Interactive HTML should contain compiled JS from codegen."""

    def test_click_handler_wired(self):
        prog = parse_string('when click\n  print "clicked"\nend')
        html = render_html(prog)
        assert 'rosh.on("click"' in html

    def test_named_click_handler_wired(self):
        prog = parse_string(
            "create object box\n"
            'when click box\n  print "box clicked"\nend'
        )
        html = render_html(prog)
        assert 'rosh.on("click_box"' in html

    def test_keydown_handler_wired(self):
        prog = parse_string('when keydown\n  print "key"\nend')
        html = render_html(prog)
        assert 'rosh.on("keydown"' in html

    def test_keydown_per_key_filter(self):
        """when keydown ArrowRight → filters by key name."""
        prog = parse_string(
            'when keydown ArrowRight\n  print "right"\nend'
        )
        html = render_html(prog)
        assert 'rosh.on("keydown"' in html
        assert 'payload.key !== "ArrowRight"' in html

    def test_keyup_handler_wired(self):
        """when keyup → handler registered for keyup event."""
        prog = parse_string('when keyup Space\n  print "released"\nend')
        html = render_html(prog)
        assert 'rosh.on("keyup"' in html
        assert 'payload.key !== "Space"' in html

    def test_keyup_in_runtime(self):
        """JS runtime includes keyup event listener."""
        prog = parse_string('when keyup a\n  print "a up"\nend')
        html = render_html(prog)
        assert "keyup" in html

    def test_update_starts_game_loop(self):
        prog = parse_string("when update\n  set score to score + 1\nend")
        html = render_html(prog)
        assert "rosh.startLoop()" in html

    def test_collision_starts_game_loop(self):
        prog = parse_string('when collision a b\n  print "hit"\nend')
        html = render_html(prog)
        assert "rosh.startLoop()" in html

    def test_start_event_fired_after_handlers(self):
        """start event should be sent after all handlers are registered."""
        prog = parse_string('when start\n  print "go"\nend')
        html = render_html(prog)
        assert 'rosh.send("start"' in html
        # start event must come after handler registration
        handler_pos = html.index('rosh.on("start"')
        start_pos = html.index('rosh.send("start"')
        assert start_pos > handler_pos

    def test_start_event_before_game_loop(self):
        """start event should fire before startLoop."""
        prog = parse_string('when update\n  print "tick"\nend')
        html = render_html(prog)
        assert 'rosh.send("start"' in html
        start_pos = html.index('rosh.send("start"')
        loop_pos = html.index("rosh.startLoop()")
        assert start_pos < loop_pos

    def test_no_loop_without_update_or_collision(self):
        prog = parse_string('when click\n  print "clicked"\nend')
        html = render_html(prog)
        assert "rosh.startLoop()" not in html
        assert "rosh.syncAll()" in html

    def test_initial_state_rendered(self):
        """Top-level creates/sets should produce initial divs."""
        prog = parse_string(
            "create object box\n"
            "set box.x to 0.5\n"
            'set box.color to "red"\n'
            'when click box\n  print "clicked"\nend'
        )
        html = render_html(prog)
        assert 'data-name="box"' in html
        assert "background-color: red" in html

    def test_init_code_in_script(self):
        """Top-level statements should appear as JS init code too."""
        prog = parse_string(
            "create object box\n"
            'when click\n  print "clicked"\nend'
        )
        html = render_html(prog)
        assert 'rosh.create("object", "box")' in html

    def test_handler_body_in_script(self):
        prog = parse_string(
            "create number score\n"
            "when click\n  set score to score + 1\nend"
        )
        html = render_html(prog)
        assert 'rosh.set("score"' in html


class TestInteractiveSpecExample:
    """The spec verification programme should render correctly."""

    def test_click_box_example(self):
        prog = parse_string(
            "create object box\n"
            "set box x to 0.4\n"
            "set box y to 0.4\n"
            "set box width to 0.2\n"
            "set box height to 0.2\n"
            'set box color to "red"\n'
            "\n"
            "create number clicks\n"
            "set clicks to 0\n"
            "\n"
            "when click box\n"
            "  set clicks to clicks + 1\n"
            '  set box color to "green"\n'
            '  print "Clicked {clicks} times!"\n'
            "end"
        )
        html = render_html(prog)
        # Has JS runtime
        assert "<script>" in html
        # Initial state: red box at 40%, 40%
        assert "background-color: red" in html
        assert "left: 40.0%" in html
        assert "top: 40.0%" in html
        # Click handler registered
        assert 'rosh.on("click_box"' in html
        # Handler body has set + print
        assert "clicks + 1" in html
        assert "Clicked {clicks} times!" in html


# ── Widget composition on web target ─────────────────────────


class TestWebWidgets:
    """use keyword should work with both static and interactive web paths."""

    def test_use_static_widget_renders(self):
        prog = parse_string("use score\nset score.value to 99")
        html = render_html(prog, search_paths=[WIDGETS_DIR])
        # Should have the score display object (namespaced)
        assert "rosh-object" in html
        assert 'data-name="score.display"' in html

    def test_use_interactive_widget_has_js(self):
        prog = parse_string("use counter")
        html = render_html(prog, search_paths=[WIDGETS_DIR])
        # Counter has a when click handler — should be interactive
        assert "<script>" in html
        assert 'rosh.on("click"' in html

    def test_use_widget_init_code_in_js(self):
        prog = parse_string("use score")
        html = render_html(prog, search_paths=[WIDGETS_DIR])
        # Score widget create/set should appear in JS init
        assert 'rosh.create(' in html
        assert "score.value" in html

    def test_composed_programme_renders(self):
        prog = parse_string(
            "use score\n"
            "set score.value to 42\n"
            'print "Score: {score.value}"\n'
            "when click score.display\n"
            "  set score.value to score.value + 1\n"
            "end"
        )
        html = render_html(prog, search_paths=[WIDGETS_DIR])
        assert "<script>" in html
        # Print handled by JS codegen (interpolated at runtime, not in <pre>)
        assert "Score: {score.value}" in html
        assert 'rosh.on("click_score.display"' in html


# ── Sprites on web target ────────────────────────────────────────


class TestSpritesStatic:
    """Sprite statements in static programmes should embed pixel art."""

    def test_sprite_produces_data_uri(self):
        prog = parse_string(
            "create object player\n"
            "set player.x to 0.5\n"
            "set player.y to 0.5\n"
            'sprite player "blue spaceship"'
        )
        html = render_html(prog)
        assert "data:image/png;base64," in html

    def test_sprite_has_pixelated_css(self):
        prog = parse_string(
            "create object player\n"
            'sprite player "blue spaceship"'
        )
        html = render_html(prog)
        assert "image-rendering: pixelated" in html

    def test_sprite_removes_background_color(self):
        """background-color should be transparent when sprite is present."""
        prog = parse_string(
            "create object player\n"
            'set player.color to "red"\n'
            'sprite player "blue spaceship"'
        )
        html = render_html(prog)
        assert "background-color: transparent" in html
        assert "background-image: url(data:image/png" in html

    def test_sprite_hides_label(self):
        """When sprite is present, label text should be empty."""
        prog = parse_string(
            "create object player\n"
            'set player.label to "Ship"\n'
            'sprite player "blue spaceship"'
        )
        html = render_html(prog)
        assert 'data-name="player"' in html
        assert ">Ship<" not in html

    def test_no_sprite_no_data_uri(self):
        """Objects without sprite should not have background-image."""
        prog = parse_string(
            "create object box\n"
            'set box.color to "red"'
        )
        html = render_html(prog)
        assert "data:image/png" not in html

    def test_sprite_deterministic_across_renders(self):
        prog = parse_string(
            "create object player\n"
            'sprite player "blue spaceship"'
        )
        html_a = render_html(prog)
        html_b = render_html(prog)
        assert html_a == html_b


class TestSpritesInteractive:
    """Sprite data should be available in interactive JS pages."""

    def test_interactive_sprite_has_sprite_data(self):
        prog = parse_string(
            "create object player\n"
            "set player.x to 0.5\n"
            "set player.y to 0.5\n"
            'sprite player "blue spaceship"\n'
            'when click\n  print "clicked"\nend'
        )
        html = render_html(prog)
        assert "rosh._spriteData" in html
        assert "data:image/png;base64," in html

    def test_interactive_sprite_in_script(self):
        prog = parse_string(
            "create object player\n"
            'sprite player "green alien"\n'
            "when update\n  set player.x to player.x + 0.01\nend"
        )
        html = render_html(prog)
        assert "<script>" in html
        assert "_spriteData" in html

    def test_no_sprite_no_sprite_data(self):
        """Interactive page without sprites should not emit _spriteData."""
        prog = parse_string(
            "create object box\n"
            'when click\n  print "hi"\nend'
        )
        html = render_html(prog)
        # _spriteData is in the runtime init but no assignment with data URIs
        assert "data:image/png;base64," not in html


# ── Sound on web target ──────────────────────────────────────────


class TestSoundInteractive:
    """Sound statements in interactive programmes should inject audio data."""

    def test_sound_injects_audio_data(self):
        prog = parse_string(
            'sound laser "laser blast"\n'
            'when click\n  play laser\nend'
        )
        html = render_html(prog)
        assert "rosh._audioData" in html
        assert '"layers"' in html

    def test_sound_emits_register_call(self):
        """Codegen should emit rosh.registerSound in the script."""
        prog = parse_string(
            'sound zap "laser shoot"\n'
            'when click\n  play zap\nend'
        )
        html = render_html(prog)
        assert 'rosh.registerSound("zap"' in html

    def test_play_emits_play_audio_call(self):
        """Codegen should emit rosh.playAudio in the script."""
        prog = parse_string(
            'sound zap "laser"\n'
            'when click\n  play zap\nend'
        )
        html = render_html(prog)
        assert 'rosh.playAudio("zap"' in html

    def test_no_sound_no_audio_data(self):
        """Interactive page without sounds should not emit _audioData assignment."""
        prog = parse_string(
            "create object box\n"
            'when click\n  print "hi"\nend'
        )
        html = render_html(prog)
        # _audioData is in runtime init but no populated assignment
        assert '"layers"' not in html

    def test_multiple_sounds(self):
        """Multiple sound statements should all appear in audio data."""
        prog = parse_string(
            'sound laser "laser blast"\n'
            'sound coin "coin collect"\n'
            'when click\n  play laser\nend'
        )
        html = render_html(prog)
        assert '"laser"' in html
        assert '"coin"' in html

    def test_sound_has_preset_params(self):
        """Known preset keyword should produce correct params in HTML."""
        prog = parse_string(
            'sound zap "laser blast"\n'
            'when click\n  play zap\nend'
        )
        html = render_html(prog)
        assert '"square"' in html  # laser preset uses square wave

    def test_js_runtime_has_play_audio(self):
        """JS runtime should contain playAudio function."""
        prog = parse_string(
            'sound zap "laser"\n'
            'when click\n  play zap\nend'
        )
        html = render_html(prog)
        assert "playAudio" in html

    def test_js_runtime_has_register_sound(self):
        """JS runtime should contain registerSound function."""
        prog = parse_string(
            'sound zap "laser"\n'
            'when click\n  play zap\nend'
        )
        html = render_html(prog)
        assert "registerSound" in html


# ── Animation ──────────────────────────────────────────────


class TestAnimationDataInjection:
    def test_animate_injects_anim_data(self):
        """Animate statement should inject _animData into rendered HTML."""
        from pathlib import Path
        import struct, zlib

        # Create a tiny test spritesheet (2 frames, 4x2px)
        def _make_png(w, h):
            def _chunk(ct, d):
                c = ct + d
                crc = zlib.crc32(c) & 0xFFFFFFFF
                return struct.pack(">I", len(d)) + c + struct.pack(">I", crc)
            ihdr = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)
            raw = b""
            for _ in range(h):
                raw += b"\x00" + b"\xff\x00\x00\xff" * w
            return b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", zlib.compress(raw)) + _chunk(b"IEND", b"")

        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            sheet_path = Path(tmpdir) / "test-sheet.png"
            sheet_path.write_bytes(_make_png(4, 2))

            prog = parse_string(
                'create object player\n'
                'set player.x to 0.5\n'
                'set player.y to 0.5\n'
                f'animate player sheet "test-sheet.png" frames 2 speed 10\n'
                'when click\n  set player.x to 0.6\nend'
            )
            html = render_html(prog, search_paths=[Path(tmpdir)])
            assert "rosh._animData" in html
            assert "data:image/png;base64," in html
            assert "registerAnimation" in html
            assert "tickAnimations" in html


# ── Duplicate print fix ──────────────────────────────────────────


class TestDuplicatePrintFix:
    """Interactive print/say should appear only once (JS), not in <pre> too."""

    def test_interactive_print_not_in_pre(self):
        """Print in interactive programme should not appear in <pre> output."""
        prog = parse_string(
            'create object box\n'
            'set box.x to 0.5\n'
            'print "hello"\n'
            'when click\n  print "clicked"\nend'
        )
        html = render_html(prog)
        # The <pre> output section should NOT contain the print text
        pre_start = html.index('<pre id="output">')
        pre_end = html.index("</pre>")
        pre_content = html[pre_start:pre_end]
        assert "hello" not in pre_content
        # But JS codegen should still have it
        assert 'appendOutput(rosh.interpolate("hello"))' in html

    def test_interactive_say_not_in_pre(self):
        """Say in interactive programme should not appear in <pre> output."""
        prog = parse_string(
            'say "welcome"\n'
            'when click\n  print "clicked"\nend'
        )
        html = render_html(prog)
        pre_start = html.index('<pre id="output">')
        pre_end = html.index("</pre>")
        pre_content = html[pre_start:pre_end]
        assert "welcome" not in pre_content

    def test_static_print_still_works(self):
        """Static programmes (no when blocks) should still show print in <pre>."""
        prog = parse_string('print "hello world"')
        html = render_html(prog)
        assert "<script>" not in html
        assert "hello world" in html

    def test_print_inside_when_start_works(self):
        """Print inside when start block should appear via JS."""
        prog = parse_string(
            'when start\n  print "started"\nend'
        )
        html = render_html(prog)
        assert 'appendOutput(rosh.interpolate("started"))' in html

    def test_create_set_still_produce_divs(self):
        """Create/set should still produce initial state divs in interactive path."""
        prog = parse_string(
            'create object box\n'
            'set box.x to 0.5\n'
            'set box.color to "red"\n'
            'print "info"\n'
            'when click\n  print "clicked"\nend'
        )
        html = render_html(prog)
        assert 'data-name="box"' in html
        assert "background-color: red" in html

    def test_multiple_prints_not_duplicated(self):
        """Multiple prints in interactive programme should not appear in <pre>."""
        prog = parse_string(
            'print "line 1"\n'
            'print "line 2"\n'
            'when click\n  print "clicked"\nend'
        )
        html = render_html(prog)
        pre_start = html.index('<pre id="output">')
        pre_end = html.index("</pre>")
        pre_content = html[pre_start:pre_end]
        assert "line 1" not in pre_content
        assert "line 2" not in pre_content


# ── Key-hold state tracking ──────────────────────────────────────


class TestKeyHoldState:
    """JS runtime should track held keys in state._keys."""

    def test_keys_init_in_core(self):
        """state._keys should be initialized in JS_RUNTIME_CORE."""
        from rosh_lang.targets._js_runtime import JS_RUNTIME_CORE
        assert "state._keys = {}" in JS_RUNTIME_CORE

    def test_keydown_sets_key_to_1(self):
        """DOM keydown listener should set _keys[e.key] = 1."""
        from rosh_lang.targets._js_runtime import JS_RUNTIME_DOM
        assert "rosh.state._keys[e.key] = 1" in JS_RUNTIME_DOM

    def test_keyup_sets_key_to_0(self):
        """DOM keyup listener should set _keys[e.key] = 0."""
        from rosh_lang.targets._js_runtime import JS_RUNTIME_DOM
        assert "rosh.state._keys[e.key] = 0" in JS_RUNTIME_DOM

    def test_key_hold_in_rendered_html(self):
        """Rendered interactive HTML should contain key-hold tracking."""
        prog = parse_string('when click\n  print "hi"\nend')
        html = render_html(prog)
        assert "state._keys = {}" in html
        assert "_keys[e.key] = 1" in html
        assert "_keys[e.key] = 0" in html


# ── Game pause ───────────────────────────────────────────────────


class TestGamePause:
    """JS runtime should support pausing the game loop via _paused state."""

    def test_paused_init_in_core(self):
        """state._paused should be initialized to 0 in JS_RUNTIME_CORE."""
        from rosh_lang.targets._js_runtime import JS_RUNTIME_CORE
        assert "state._paused = 0" in JS_RUNTIME_CORE

    def test_pause_check_in_dom_tick(self):
        """DOM tick() should check _paused and skip logic when paused."""
        from rosh_lang.targets._js_runtime import JS_RUNTIME_DOM
        assert "rosh.state._paused" in JS_RUNTIME_DOM

    def test_pause_in_rendered_html(self):
        """Rendered interactive HTML should contain pause support."""
        prog = parse_string('when click\n  print "hi"\nend')
        html = render_html(prog)
        assert "state._paused = 0" in html
        assert "rosh.state._paused" in html
