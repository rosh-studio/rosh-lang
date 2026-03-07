"""Tests for Step 26: Controller widget."""

from __future__ import annotations

import io
from pathlib import Path

from rosh_lang.model import (
    CreateStatement,
    EventStatement,
    IfStatement,
    OnStatement,
    SetStatement,
    WhenStatement,
)
from rosh_lang.parser import parse_string
from rosh_lang.runtime import Runtime
from rosh_lang.widgets import load_widget

BUNDLED_DIR = Path(__file__).parent.parent / "src" / "rosh_lang" / "library"


class TestControllerBasic:
    def test_no_target_returns_empty(self):
        stmts = load_widget("controller", config={}, search_paths=[BUNDLED_DIR])
        # With no target, should be empty (no object to control)
        assert stmts == []

    def test_basic_arrows(self):
        stmts = load_widget(
            "controller",
            config={"target": "ship"},
            search_paths=[BUNDLED_DIR],
        )
        # Should have movement handlers
        when_stmts = [s for s in stmts if isinstance(s, WhenStatement)]
        assert len(when_stmts) >= 1
        assert when_stmts[0].event == "update"

    def test_creates_speed(self):
        stmts = load_widget(
            "controller",
            config={"target": "ship", "speed": "0.05"},
            search_paths=[BUNDLED_DIR],
        )
        creates = [s for s in stmts if isinstance(s, CreateStatement)]
        speed_creates = [c for c in creates if "speed" in c.name]
        assert len(speed_creates) >= 1

    def test_custom_speed(self):
        stmts = load_widget(
            "controller",
            config={"target": "ship", "speed": "0.05"},
            search_paths=[BUNDLED_DIR],
        )
        sets = [s for s in stmts if isinstance(s, SetStatement)]
        speed_sets = [s for s in sets if "speed" in s.target]
        assert any(s.value == "0.05" for s in speed_sets)

    def test_wasd_keys(self):
        stmts = load_widget(
            "controller",
            config={"target": "ship", "keys": "wasd"},
            search_paths=[BUNDLED_DIR],
        )
        # Should have if-statements checking wasd keys
        ifs = [s for s in stmts if isinstance(s, IfStatement)]
        conditions = [i.condition for i in ifs]
        assert any("_keys.a" in c for c in conditions)
        assert any("_keys.d" in c for c in conditions)
        assert any("_keys.w" in c for c in conditions)
        assert any("_keys.s" in c for c in conditions)

    def test_both_keys(self):
        stmts = load_widget(
            "controller",
            config={"target": "ship", "keys": "both"},
            search_paths=[BUNDLED_DIR],
        )
        ifs = [s for s in stmts if isinstance(s, IfStatement)]
        conditions = [i.condition for i in ifs]
        assert any("ArrowLeft" in c for c in conditions)
        assert any("_keys.a" in c for c in conditions)

    def test_move_x_only(self):
        stmts = load_widget(
            "controller",
            config={"target": "ship", "move": "x"},
            search_paths=[BUNDLED_DIR],
        )
        ifs = [s for s in stmts if isinstance(s, IfStatement)]
        conditions = [i.condition for i in ifs]
        assert any("ArrowLeft" in c for c in conditions)
        assert not any("ArrowUp" in c for c in conditions)

    def test_clamp_on(self):
        stmts = load_widget(
            "controller",
            config={"target": "ship"},
            search_paths=[BUNDLED_DIR],
        )
        ons = [s for s in stmts if isinstance(s, OnStatement)]
        clamp_ons = [o for o in ons if "clamp" in o.args]
        assert len(clamp_ons) >= 2  # x and y clamp

    def test_clamp_off(self):
        stmts = load_widget(
            "controller",
            config={"target": "ship", "clamp": "off"},
            search_paths=[BUNDLED_DIR],
        )
        ons = [s for s in stmts if isinstance(s, OnStatement)]
        clamp_ons = [o for o in ons if "clamp" in o.args]
        assert len(clamp_ons) == 0


class TestControllerFire:
    def test_fire_off_by_default(self):
        stmts = load_widget(
            "controller",
            config={"target": "ship"},
            search_paths=[BUNDLED_DIR],
        )
        events = [s for s in stmts if isinstance(s, EventStatement)]
        fire_events = [e for e in events if e.name == "fire"]
        assert len(fire_events) == 0

    def test_fire_on(self):
        stmts = load_widget(
            "controller",
            config={"target": "ship", "fire": "on"},
            search_paths=[BUNDLED_DIR],
        )
        events = [s for s in stmts if isinstance(s, EventStatement)]
        fire_events = [e for e in events if e.name == "fire"]
        assert len(fire_events) == 1

    def test_custom_fire_event(self):
        stmts = load_widget(
            "controller",
            config={"target": "ship", "fire": "on", "fire_event": "shoot"},
            search_paths=[BUNDLED_DIR],
        )
        events = [s for s in stmts if isinstance(s, EventStatement)]
        shoot_events = [e for e in events if e.name == "shoot"]
        assert len(shoot_events) == 1


class TestControllerTouch:
    def test_touch_off_by_default(self):
        stmts = load_widget(
            "controller",
            config={"target": "ship"},
            search_paths=[BUNDLED_DIR],
        )
        creates = [s for s in stmts if isinstance(s, CreateStatement)]
        touch_creates = [c for c in creates if "_touch" in c.name]
        assert len(touch_creates) == 0

    def test_touch_on(self):
        stmts = load_widget(
            "controller",
            config={"target": "ship", "touch": "on"},
            search_paths=[BUNDLED_DIR],
        )
        sets = [s for s in stmts if isinstance(s, SetStatement)]
        touch_sets = [s for s in sets if "_touch" in s.target and "_touch_target" not in s.target]
        assert any(s.value == "dpad" for s in touch_sets)

    def test_touch_joystick(self):
        stmts = load_widget(
            "controller",
            config={"target": "ship", "touch": "on", "touch_style": "joystick"},
            search_paths=[BUNDLED_DIR],
        )
        sets = [s for s in stmts if isinstance(s, SetStatement)]
        touch_sets = [s for s in sets if "_touch" in s.target and "_touch_target" not in s.target]
        assert any(s.value == "joystick" for s in touch_sets)


class TestControllerHelp:
    def test_help_on_by_default(self):
        stmts = load_widget(
            "controller",
            config={"target": "ship"},
            search_paths=[BUNDLED_DIR],
        )
        sets = [s for s in stmts if isinstance(s, SetStatement)]
        help_sets = [s for s in sets if "_help" == s.target.split(".")[-1]]
        assert any(s.value == "on" for s in help_sets)

    def test_help_off(self):
        stmts = load_widget(
            "controller",
            config={"target": "ship", "help": "off"},
            search_paths=[BUNDLED_DIR],
        )
        creates = [s for s in stmts if isinstance(s, CreateStatement)]
        help_creates = [c for c in creates if "_help" in c.name]
        assert len(help_creates) == 0


class TestControllerTargetBinding:
    """Verify the controller moves the TARGET object, not itself."""

    def test_movement_targets_ship(self):
        stmts = load_widget(
            "controller",
            config={"target": "ship"},
            search_paths=[BUNDLED_DIR],
        )
        ifs = [s for s in stmts if isinstance(s, IfStatement)]
        for if_stmt in ifs:
            for s in if_stmt.then_body:
                if isinstance(s, SetStatement):
                    # After prefixing, target should reference ship
                    # (pre-prefix, it references the raw target name)
                    assert "ship" in s.target

    def test_target_not_double_prefixed(self):
        """Target object should NOT get controller. prefix — it's external."""
        stmts = load_widget(
            "controller",
            config={"target": "ship"},
            search_paths=[BUNDLED_DIR],
        )
        ifs = [s for s in stmts if isinstance(s, IfStatement)]
        for if_stmt in ifs:
            for s in if_stmt.then_body:
                if isinstance(s, SetStatement):
                    # Should be "ship.x" not "controller.ship.x"
                    assert not s.target.startswith("controller.ship")

    def test_clamp_targets_ship(self):
        stmts = load_widget(
            "controller",
            config={"target": "ship"},
            search_paths=[BUNDLED_DIR],
        )
        ons = [s for s in stmts if isinstance(s, OnStatement)]
        clamp_ons = [o for o in ons if "clamp" in o.args]
        for o in clamp_ons:
            assert "ship" in o.args


class TestControllerIntegration:
    """Test controller in a full programme via runtime."""

    def test_runtime_integration(self):
        code = (
            "create object ship\n"
            "set ship.x to 0.5\n"
            "set ship.y to 0.5\n"
            "use controller target ship keys arrows speed 0.1\n"
        )
        out = io.StringIO()
        rt = Runtime(output=out)
        rt.run(parse_string(code))
        assert rt.state["ship"]["x"] == 0.5
        assert "controller" in rt.state  # controller namespace exists
