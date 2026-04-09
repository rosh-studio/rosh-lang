"""Tests for the Three.js target — HTML generation only (no server)."""

from __future__ import annotations

from pathlib import Path

from rosh_lang.parser import parse_string
from rosh_lang.targets.threejs import render_threejs

WIDGETS_DIR = Path(__file__).parent.parent / "examples" / "widgets"
SHOWCASE_DIR = Path(__file__).parent.parent / "examples" / "showcase"


# ── Page structure ────────────────────────────────────────────


class TestThreejsPageStructure:
    """Three.js HTML page should have correct structure."""

    def test_doctype(self):
        html = render_threejs(parse_string('print "hello"'))
        assert html.startswith("<!DOCTYPE html>")

    def test_has_threejs_cdn(self):
        html = render_threejs(parse_string('print "hello"'))
        assert "three@0.128.0" in html

    def test_has_orbit_controls_cdn(self):
        html = render_threejs(parse_string('print "hello"'))
        assert "OrbitControls.js" in html

    def test_has_gltf_loader_cdn(self):
        html = render_threejs(parse_string('print "hello"'))
        assert "GLTFLoader.js" in html

    def test_has_scene_container(self):
        html = render_threejs(parse_string('print "hello"'))
        assert 'id="scene-container"' in html

    def test_no_phaser_refs(self):
        """Three.js target should NOT reference Phaser CDN or runtime."""
        html = render_threejs(parse_string('print "hello"'))
        assert "phaser@" not in html.lower()
        assert "Phaser.Game" not in html
        assert "GameScene" not in html

    def test_no_game_container(self):
        """Three.js target should NOT have game-container (that's Phaser)."""
        html = render_threejs(parse_string('print "hello"'))
        assert 'id="game-container"' not in html

    def test_has_footer_branding(self):
        html = render_threejs(parse_string('print "hello"'))
        assert "Rosh Studio" in html
        assert "rosh.cloud" in html

    def test_dark_theme(self):
        html = render_threejs(parse_string('print "hello"'))
        assert "#1a1a2e" in html

    def test_uses_js_runtime_core(self):
        """Should embed JS_RUNTIME_CORE."""
        html = render_threejs(parse_string('print "hello"'))
        assert "var rosh" in html
        assert "function get(" in html

    def test_does_not_contain_dom_runtime(self):
        """Should NOT contain the DOM sync layer."""
        html = render_threejs(parse_string('print "hello"'))
        assert 'document.getElementById("canvas")' not in html


# ── JS runtime content ───────────────────────────────────────


class TestThreejsRuntimeContent:
    """Three.js renderer should contain expected 3D constructs."""

    def test_has_scene(self):
        from rosh_lang.targets._js_runtime_threejs import JS_RUNTIME_THREEJS
        assert "THREE.Scene" in JS_RUNTIME_THREEJS

    def test_has_perspective_camera(self):
        from rosh_lang.targets._js_runtime_threejs import JS_RUNTIME_THREEJS
        assert "PerspectiveCamera" in JS_RUNTIME_THREEJS

    def test_has_webgl_renderer(self):
        from rosh_lang.targets._js_runtime_threejs import JS_RUNTIME_THREEJS
        assert "WebGLRenderer" in JS_RUNTIME_THREEJS

    def test_no_dom_canvas(self):
        from rosh_lang.targets._js_runtime_threejs import JS_RUNTIME_THREEJS
        assert 'getElementById("canvas")' not in JS_RUNTIME_THREEJS

    def test_has_lighting(self):
        from rosh_lang.targets._js_runtime_threejs import JS_RUNTIME_THREEJS
        assert "AmbientLight" in JS_RUNTIME_THREEJS
        assert "DirectionalLight" in JS_RUNTIME_THREEJS

    def test_has_grid_helper(self):
        from rosh_lang.targets._js_runtime_threejs import JS_RUNTIME_THREEJS
        assert "GridHelper" in JS_RUNTIME_THREEJS

    def test_has_orbit_controls(self):
        from rosh_lang.targets._js_runtime_threejs import JS_RUNTIME_THREEJS
        assert "OrbitControls" in JS_RUNTIME_THREEJS

    def test_has_gltf_loader(self):
        from rosh_lang.targets._js_runtime_threejs import JS_RUNTIME_THREEJS
        assert "GLTFLoader" in JS_RUNTIME_THREEJS

    def test_has_geometry_primitives(self):
        from rosh_lang.targets._js_runtime_threejs import JS_RUNTIME_THREEJS
        assert "BoxGeometry" in JS_RUNTIME_THREEJS
        assert "SphereGeometry" in JS_RUNTIME_THREEJS
        assert "CylinderGeometry" in JS_RUNTIME_THREEJS
        assert "ConeGeometry" in JS_RUNTIME_THREEJS
        assert "TorusGeometry" in JS_RUNTIME_THREEJS
        assert "PlaneGeometry" in JS_RUNTIME_THREEJS

    def test_has_raycaster(self):
        from rosh_lang.targets._js_runtime_threejs import JS_RUNTIME_THREEJS
        assert "Raycaster" in JS_RUNTIME_THREEJS

    def test_has_vz_handling(self):
        from rosh_lang.targets._js_runtime_threejs import JS_RUNTIME_THREEJS
        assert "obj.vz" in JS_RUNTIME_THREEJS

    def test_has_box3_collision(self):
        from rosh_lang.targets._js_runtime_threejs import JS_RUNTIME_THREEJS
        assert "Box3" in JS_RUNTIME_THREEJS
        assert "intersectsBox" in JS_RUNTIME_THREEJS


# ── Static programmes ────────────────────────────────────────


class TestThreejsStaticProgrammes:
    """Even static programmes produce a valid Three.js page."""

    def test_simple_print(self):
        html = render_threejs(parse_string('print "hello world"'))
        assert "hello world" in html

    def test_empty_programme(self):
        html = render_threejs(parse_string(""))
        assert "<!DOCTYPE html>" in html
        assert "THREE.Scene" in html


# ── Interactive programmes ───────────────────────────────────


class TestThreejsInteractive:
    """Programmes with when blocks should have handlers in JS."""

    def test_click_handler(self):
        prog = parse_string('when click\n  print "clicked"\nend')
        html = render_threejs(prog)
        assert 'rosh.on("click"' in html

    def test_update_handler(self):
        prog = parse_string("when update\n  set x to x + 1\nend")
        html = render_threejs(prog)
        assert 'rosh.on("update"' in html

    def test_keydown_handler(self):
        prog = parse_string('when keydown ArrowRight\n  print "right"\nend')
        html = render_threejs(prog)
        assert 'rosh.on("keydown"' in html
        assert "ArrowRight" in html

    def test_collision_handler(self):
        prog = parse_string('when collision hero enemy\n  print "hit"\nend')
        html = render_threejs(prog)
        assert 'rosh.on("collision"' in html


# ── Sound ────────────────────────────────────────────────────


class TestThreejsSound:
    """Sound data should be injected for Web Audio synthesis."""

    def test_sound_data_injected(self):
        prog = parse_string(
            'sound laser "laser blast"\n'
            'when click\n  play laser\nend'
        )
        html = render_threejs(prog)
        assert "rosh._audioData" in html
        assert '"layers"' in html

    def test_no_sound_no_audio_data(self):
        prog = parse_string(
            "create object box\n"
            'when click\n  print "hi"\nend'
        )
        html = render_threejs(prog)
        assert '"layers"' not in html


# ── 3D features ──────────────────────────────────────────────


class TestThreejs3DFeatures:
    """Three.js-specific 3D features."""

    def test_no_sprite_data_in_3d(self):
        """3D target should not include 2D sprite data."""
        prog = parse_string(
            "create object player\n"
            "set player.x to 0.5\n"
            "set player.y to 0.5\n"
            'sprite player "blue spaceship"\n'
            'when click\n  print "clicked"\nend'
        )
        html = render_threejs(prog)
        assert "data:image/png;base64," not in html

    def test_contains_threejs_renderer_comment(self):
        html = render_threejs(parse_string('print "hello"'))
        assert "// ── Three.js renderer ──" in html

    def test_mesh_standard_material(self):
        from rosh_lang.targets._js_runtime_threejs import JS_RUNTIME_THREEJS
        assert "MeshStandardMaterial" in JS_RUNTIME_THREEJS

    def test_scene_background_color(self):
        from rosh_lang.targets._js_runtime_threejs import JS_RUNTIME_THREEJS
        assert "0x16213e" in JS_RUNTIME_THREEJS


# ── Key hold state ───────────────────────────────────────────


class TestThreejsKeyHoldState:
    """Three.js runtime should track held keys in state._keys."""

    def test_keydown_sets_key(self):
        from rosh_lang.targets._js_runtime_threejs import JS_RUNTIME_THREEJS
        assert "rosh.state._keys[e.key] = 1" in JS_RUNTIME_THREEJS

    def test_keyup_clears_key(self):
        from rosh_lang.targets._js_runtime_threejs import JS_RUNTIME_THREEJS
        assert "rosh.state._keys[e.key] = 0" in JS_RUNTIME_THREEJS


# ── Pause check ──────────────────────────────────────────────


class TestThreejsGamePause:
    """Three.js runtime should support pausing via _paused state."""

    def test_pause_check_in_loop(self):
        from rosh_lang.targets._js_runtime_threejs import JS_RUNTIME_THREEJS
        assert "rosh.state._paused" in JS_RUNTIME_THREEJS


# ── Start event ──────────────────────────────────────────────


class TestThreejsStartEvent:
    """Three.js target should fire the start event after setup."""

    def test_start_event_in_runtime(self):
        prog = parse_string('when start\n  print "go"\nend')
        html = render_threejs(prog)
        assert 'rosh.send("start"' in html


# ── Coordinate system ────────────────────────────────────────


class TestThreejsCoordinates:
    """Coordinate system: 0-1 normalised is canonical cross-target.
    `set _view to "3d"` opts into world-unit mode explicitly."""

    def test_single_obj_normalised_triggers_2d_detection(self):
        """Single object with 0-1 coords should trigger 2D auto-detection
        (objCount >= 1, not >= 2). Regression: was broken for single objects."""
        from rosh_lang.targets._js_runtime_threejs import JS_RUNTIME_THREEJS
        # Auto-detection code must use >= 1, not >= 2
        assert "objCount >= 1" in JS_RUNTIME_THREEJS

    def test_explicit_3d_view_in_runtime(self):
        """_view == '3d' must keep perspective camera (world-unit mode)."""
        from rosh_lang.targets._js_runtime_threejs import JS_RUNTIME_THREEJS
        assert '_view === "3d"' in JS_RUNTIME_THREEJS

    def test_explicit_2d_view_in_runtime(self):
        """_view == '2d' must switch to orthographic/flat camera."""
        from rosh_lang.targets._js_runtime_threejs import JS_RUNTIME_THREEJS
        assert '_view === "2d"' in JS_RUNTIME_THREEJS
