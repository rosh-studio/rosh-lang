"""Tests for the Phaser target — HTML generation only (no server)."""

from __future__ import annotations

from pathlib import Path

from rosh_lang.core.parser import parse_string
from rosh_lang.targets.phaser import render_phaser
from rosh_lang.core.widgets import get_bundled_library_path

BUNDLED_WIDGETS_DIR = get_bundled_library_path()
SHOWCASE_DIR = Path(__file__).parent.parent / "examples" / "showcase"


# ── Page structure ────────────────────────────────────────────


class TestPhaserPageStructure:
    """Phaser HTML page should have correct structure."""

    def test_doctype(self):
        html = render_phaser(parse_string('print "hello"'))
        assert html.startswith("<!DOCTYPE html>")

    def test_has_phaser_cdn(self):
        html = render_phaser(parse_string('print "hello"'))
        assert "phaser@3.70.0" in html

    def test_has_game_container(self):
        html = render_phaser(parse_string('print "hello"'))
        assert 'id="game-container"' in html

    def test_no_css_canvas_div(self):
        """Phaser target should NOT have the CSS div canvas."""
        html = render_phaser(parse_string('print "hello"'))
        assert 'id="canvas"' not in html

    def test_has_footer_branding(self):
        html = render_phaser(parse_string('print "hello"'))
        assert "Rosh Studio" in html
        assert "rosh.cloud" in html

    def test_dark_theme(self):
        html = render_phaser(parse_string('print "hello"'))
        assert "#1a1a2e" in html

    def test_uses_js_runtime_core(self):
        """Should embed JS_RUNTIME_CORE (not JS_RUNTIME_DOM)."""
        html = render_phaser(parse_string('print "hello"'))
        assert "var rosh" in html
        assert "function get(" in html

    def test_does_not_contain_dom_runtime(self):
        """Should NOT contain the DOM sync layer."""
        html = render_phaser(parse_string('print "hello"'))
        assert 'document.getElementById("canvas")' not in html

    def test_contains_phaser_renderer(self):
        """Should contain the Phaser renderer layer."""
        html = render_phaser(parse_string('print "hello"'))
        assert "GameScene" in html
        assert "Phaser.Game" in html


# ── Static programmes ────────────────────────────────────────


class TestPhaserStaticProgrammes:
    """Even static programmes produce a valid Phaser page."""

    def test_simple_print(self):
        html = render_phaser(parse_string('print "hello world"'))
        assert "hello world" in html

    def test_empty_programme(self):
        html = render_phaser(parse_string(""))
        assert "<!DOCTYPE html>" in html
        assert "Phaser.Game" in html


# ── Interactive programmes ───────────────────────────────────


class TestPhaserInteractive:
    """Programmes with when blocks should have handlers in JS."""

    def test_click_handler(self):
        prog = parse_string('when click\n  print "clicked"\nend')
        html = render_phaser(prog)
        assert 'rosh.on("click"' in html

    def test_update_handler(self):
        prog = parse_string("when update\n  set x to x + 1\nend")
        html = render_phaser(prog)
        assert 'rosh.on("update"' in html

    def test_keydown_handler(self):
        prog = parse_string('when keydown ArrowRight\n  print "right"\nend')
        html = render_phaser(prog)
        assert 'rosh.on("keydown"' in html
        assert "ArrowRight" in html

    def test_collision_handler(self):
        prog = parse_string('when collision hero enemy\n  print "hit"\nend')
        html = render_phaser(prog)
        assert 'rosh.on("collision"' in html


# ── Sprites ──────────────────────────────────────────────────


class TestPhaserSprites:
    """Sprite data should be injected for Phaser texture loading."""

    def test_sprite_data_injected(self):
        prog = parse_string(
            "create object player\n"
            "set player.x to 0.5\n"
            "set player.y to 0.5\n"
            'sprite player "blue spaceship"\n'
            'when click\n  print "clicked"\nend'
        )
        html = render_phaser(prog)
        assert "rosh._spriteData" in html
        assert "data:image/png;base64," in html

    def test_no_sprite_no_data(self):
        prog = parse_string(
            "create object box\n"
            'when click\n  print "hi"\nend'
        )
        html = render_phaser(prog)
        assert "data:image/png;base64," not in html


# ── Sound ────────────────────────────────────────────────────


class TestPhaserSound:
    """Sound data should be injected for Web Audio synthesis."""

    def test_sound_data_injected(self):
        prog = parse_string(
            'sound laser "laser blast"\n'
            'when click\n  play laser\nend'
        )
        html = render_phaser(prog)
        assert "rosh._audioData" in html
        assert '"layers"' in html

    def test_no_sound_no_audio_data(self):
        prog = parse_string(
            "create object box\n"
            'when click\n  print "hi"\nend'
        )
        html = render_phaser(prog)
        assert '"layers"' not in html


# ── Showcase demos ───────────────────────────────────────────


class TestPhaserStartEvent:
    """Phaser target should fire the start event after scene is ready."""

    def test_start_event_in_phaser_runtime(self):
        prog = parse_string('when start\n  print "go"\nend')
        html = render_phaser(prog)
        assert 'rosh.send("start"' in html

    def test_collision_payload_includes_positions(self):
        """Phaser collision send should include position keys."""
        prog = parse_string('when collision a b\n  print "hit"\nend')
        html = render_phaser(prog)
        assert "a_x: oa.x" in html
        assert "b_x: ob.x" in html


class TestPhaserShowcaseDemos:
    """All 9 showcase demos should compile to Phaser HTML without error."""

    def test_all_showcase_demos_compile(self):
        from rosh_lang.core.parser import parse_file

        demos = sorted(SHOWCASE_DIR.glob("*.rosh"))
        assert len(demos) >= 9, f"Expected >=9 demos, found {len(demos)}"

        for demo in demos:
            prog = parse_file(demo)
            html = render_phaser(
                prog,
                search_paths=[BUNDLED_WIDGETS_DIR],
            )
            assert "<!DOCTYPE html>" in html, f"{demo.name} failed"
            assert "Phaser.Game" in html, f"{demo.name} missing Phaser"


# ── Duplicate print fix ──────────────────────────────────────────


class TestPhaserDuplicatePrintFix:
    """Phaser print should appear only once — via JS codegen, not Python re-emission."""

    def test_phaser_print_not_duplicated(self):
        """Print in Phaser programme should appear via JS appendOutput only."""
        prog = parse_string(
            'print "hello phaser"\n'
            'when click\n  print "clicked"\nend'
        )
        html = render_phaser(prog)
        # JS codegen should have the print
        assert 'appendOutput(rosh.interpolate("hello phaser"))' in html
        # There should be no duplicate re-emission after Phaser renderer
        # (no standalone appendOutput("hello phaser") calls outside handler code)
        phaser_idx = html.index("// ── Phaser renderer ──")
        after_phaser = html[phaser_idx:]
        assert 'appendOutput("hello phaser")' not in after_phaser


# ── Key-hold state tracking ──────────────────────────────────────


class TestPhaserKeyHoldState:
    """Phaser runtime should track held keys in state._keys."""

    def test_phaser_keydown_sets_key(self):
        """Phaser keydown listener should set _keys[e.key] = 1."""
        from rosh_lang.targets._js_runtime_phaser import JS_RUNTIME_PHASER
        assert "rosh.state._keys[e.key] = 1" in JS_RUNTIME_PHASER

    def test_phaser_keyup_sets_key(self):
        """Phaser keyup listener should set _keys[e.key] = 0."""
        from rosh_lang.targets._js_runtime_phaser import JS_RUNTIME_PHASER
        assert "rosh.state._keys[e.key] = 0" in JS_RUNTIME_PHASER


# ── Game pause ───────────────────────────────────────────────────


class TestPhaserGamePause:
    """Phaser runtime should support pausing via _paused state."""

    def test_phaser_pause_check_in_update(self):
        """Phaser update() should check _paused and skip logic when paused."""
        from rosh_lang.targets._js_runtime_phaser import JS_RUNTIME_PHASER
        assert "rosh.state._paused" in JS_RUNTIME_PHASER
