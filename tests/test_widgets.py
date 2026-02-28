"""Tests for widget loader — search, namespace prefixing, config, fuzzy match."""

from __future__ import annotations

from pathlib import Path

import pytest

from rosh_lang.model import (
    CreateStatement,
    DestroyStatement,
    OnStatement,
    PlayStatement,
    PrintStatement,
    SayStatement,
    SendStatement,
    SetStatement,
    SoundStatement,
    SpriteStatement,
    WhenStatement,
)
from rosh_lang.parser import parse_string
from rosh_lang.widgets import (
    find_widget,
    get_bundled_library_path,
    load_widget,
    parse_metadata,
    prefix_programme,
)

# Path to example widgets shipped with the project
WIDGETS_DIR = Path(__file__).parent.parent / "examples" / "widgets"
BUNDLED_DIR = get_bundled_library_path()


# ── find_widget ──────────────────────────────────────────────────


class TestFindWidget:
    def test_exact_match(self):
        result = find_widget("score", search_paths=[WIDGETS_DIR])
        assert result is not None
        assert result.name == "score.rosh"

    def test_not_found_returns_none(self):
        with pytest.warns(UserWarning, match="not found"):
            result = find_widget("nonexistent", search_paths=[WIDGETS_DIR])
        assert result is None

    def test_fuzzy_match_suggests(self):
        with pytest.warns(UserWarning, match="Did you mean"):
            result = find_widget("scor", search_paths=[WIDGETS_DIR])
        assert result is None

    def test_searches_multiple_paths(self, tmp_path: Path):
        # Widget in second path should be found
        (tmp_path / "my-widget.rosh").write_text('print "hello"')
        result = find_widget("my-widget", search_paths=[Path("/nonexistent"), tmp_path])
        assert result is not None

    def test_first_path_wins(self, tmp_path: Path):
        dir1 = tmp_path / "a"
        dir2 = tmp_path / "b"
        dir1.mkdir()
        dir2.mkdir()
        (dir1 / "w.rosh").write_text('print "from a"')
        (dir2 / "w.rosh").write_text('print "from b"')
        result = find_widget("w", search_paths=[dir1, dir2])
        assert result is not None
        assert result.parent == dir1


# ── prefix_programme ─────────────────────────────────────────────


class TestPrefixProgramme:
    def test_create_name_prefixed(self):
        prog = parse_string("create object box")
        result = prefix_programme(prog, "widget")
        stmt = result[0]
        assert isinstance(stmt, CreateStatement)
        assert stmt.name == "widget.box"

    def test_create_parent_prefixed(self):
        prog = parse_string("create object child from parent")
        result = prefix_programme(prog, "ns")
        stmt = result[0]
        assert isinstance(stmt, CreateStatement)
        assert stmt.parent == "ns.parent"

    def test_set_target_prefixed(self):
        prog = parse_string("set score to 42")
        result = prefix_programme(prog, "ns")
        stmt = result[0]
        assert isinstance(stmt, SetStatement)
        assert stmt.target == "ns.score"

    def test_set_dotted_target_prefixed(self):
        prog = parse_string("set box.x to 0.5")
        result = prefix_programme(prog, "ns")
        stmt = result[0]
        assert isinstance(stmt, SetStatement)
        assert stmt.target == "ns.box.x"

    def test_set_arithmetic_left_prefixed(self):
        prog = parse_string("set score to score + 1")
        result = prefix_programme(prog, "ns")
        stmt = result[0]
        assert isinstance(stmt, SetStatement)
        assert "ns.score" in stmt.value
        # Right operand stays as literal
        assert "+ 1" in stmt.value

    def test_set_arithmetic_variable_right_prefixed(self):
        """Variable right operands must be prefixed: obj.x + drift → ns.obj.x + ns.drift."""
        prog = parse_string("set obj.x to obj.x + drift")
        result = prefix_programme(prog, "ns")
        stmt = result[0]
        assert isinstance(stmt, SetStatement)
        assert stmt.value == "ns.obj.x + ns.drift"

    def test_set_quoted_string_interpolation_prefixed(self):
        prog = parse_string('set label to "{score}"')
        result = prefix_programme(prog, "ns")
        stmt = result[0]
        assert isinstance(stmt, SetStatement)
        assert "{ns.score}" in stmt.value

    def test_destroy_prefixed(self):
        prog = parse_string("create object bullet\ndestroy bullet")
        result = prefix_programme(prog, "ns")
        stmt = result[1]
        assert isinstance(stmt, DestroyStatement)
        assert stmt.name == "ns.bullet"

    def test_when_args_prefixed(self):
        prog = parse_string('when click box\n  print "hit"\nend')
        result = prefix_programme(prog, "ns")
        when_stmt = result[0]
        assert isinstance(when_stmt, WhenStatement)
        # Event stays global
        assert when_stmt.event == "click"
        # Args (object names) get prefixed
        assert when_stmt.args == ["ns.box"]

    def test_when_event_stays_global(self):
        prog = parse_string('when update\n  print "tick"\nend')
        result = prefix_programme(prog, "ns")
        stmt = result[0]
        assert isinstance(stmt, WhenStatement)
        assert stmt.event == "update"

    def test_send_event_stays_global(self):
        prog = parse_string("event boom\nsend boom")
        result = prefix_programme(prog, "ns")
        send_stmt = result[1]
        assert isinstance(send_stmt, SendStatement)
        assert send_stmt.event == "boom"

    def test_print_interpolation_prefixed(self):
        prog = parse_string('print "Score: {value}"')
        result = prefix_programme(prog, "score")
        stmt = result[0]
        assert isinstance(stmt, PrintStatement)
        assert "{score.value}" in stmt.text

    def test_say_interpolation_prefixed(self):
        prog = parse_string("say Hello {name}")
        result = prefix_programme(prog, "ns")
        stmt = result[0]
        assert isinstance(stmt, SayStatement)
        assert "{ns.name}" in stmt.text


# ── load_widget ──────────────────────────────────────────────────


class TestLoadWidget:
    def test_load_score_widget(self):
        stmts = load_widget("score", search_paths=[WIDGETS_DIR])
        assert len(stmts) > 0
        # First non-comment should be namespaced create
        creates = [s for s in stmts if isinstance(s, CreateStatement)]
        assert any(c.name == "score.value" for c in creates)
        assert any(c.name == "score.display" for c in creates)

    def test_load_with_config_override(self):
        stmts = load_widget("score", config={"max": "100"}, search_paths=[WIDGETS_DIR])
        # Should have a config set statement at the end
        sets = [s for s in stmts if isinstance(s, SetStatement)]
        config_set = [s for s in sets if s.target == "score.max"]
        assert len(config_set) == 1
        assert config_set[0].value == "100"

    def test_load_missing_widget_returns_empty(self):
        with pytest.warns(UserWarning, match="not found"):
            stmts = load_widget("nonexistent", search_paths=[WIDGETS_DIR])
        assert stmts == []

    def test_load_player_widget(self):
        stmts = load_widget("player", search_paths=[WIDGETS_DIR])
        creates = [s for s in stmts if isinstance(s, CreateStatement)]
        assert any(c.name == "player.ship" for c in creates)
        assert any(c.name == "player.speed" for c in creates)

    def test_config_override_applied_after_widget(self):
        stmts = load_widget("player", config={"speed": "0.05"}, search_paths=[WIDGETS_DIR])
        # Config set should be the last statement
        sets = [s for s in stmts if isinstance(s, SetStatement)]
        last_speed = [s for s in sets if s.target == "player.speed"]
        assert last_speed[-1].value == "0.05"


# ── Bundled library discovery ──────────────────────────────────────


class TestBundledLibrary:
    def test_bundled_path_exists(self):
        assert BUNDLED_DIR.is_dir()

    def test_bundled_score_widget_exists(self):
        assert (BUNDLED_DIR / "score.rosh").is_file()

    def test_find_bundled_widget(self):
        """Widgets found even from arbitrary CWD (bundled path is absolute)."""
        result = find_widget("score", search_paths=[BUNDLED_DIR])
        assert result is not None
        assert result.name == "score.rosh"

    def test_bundled_widgets_count(self):
        """At least 10 widgets bundled."""
        widgets = list(BUNDLED_DIR.glob("*.rosh"))
        assert len(widgets) >= 10

    def test_local_overrides_bundled(self, tmp_path: Path):
        """Project-local widget takes priority over bundled."""
        (tmp_path / "score.rosh").write_text('print "local score"')
        result = find_widget("score", search_paths=[tmp_path, BUNDLED_DIR])
        assert result is not None
        assert result.parent == tmp_path


# ── Metadata parser ─────────────────────────────────────────────────


class TestParseMetadata:
    def test_parse_score_metadata(self):
        meta = parse_metadata(BUNDLED_DIR / "score.rosh")
        assert meta["widget"] == "score"
        assert meta["version"] == "0.1"
        assert meta["description"] == "Score display with current value and label"
        assert meta["config"] == {"max": "999"}

    def test_parse_player_metadata(self):
        meta = parse_metadata(BUNDLED_DIR / "player.rosh")
        assert meta["widget"] == "player"
        assert meta["config"] == {"speed": "0.02"}

    def test_parse_licence_field(self):
        """Bundled widgets should declare Rosh-BSL licence."""
        meta = parse_metadata(BUNDLED_DIR / "score.rosh")
        assert meta["licence"] == "Rosh-BSL"

    def test_parse_no_metadata(self, tmp_path: Path):
        widget = tmp_path / "bare.rosh"
        widget.write_text('print "hello"')
        meta = parse_metadata(widget)
        assert meta["widget"] == "bare"
        assert meta["version"] == ""
        assert meta["config"] == {}

    def test_parse_missing_file(self, tmp_path: Path):
        meta = parse_metadata(tmp_path / "ghost.rosh")
        assert meta["widget"] == "ghost"
        assert meta["version"] == ""

    def test_parse_multi_config(self, tmp_path: Path):
        widget = tmp_path / "multi.rosh"
        widget.write_text('# widget: multi\n# config: a=1 b=2 c=3\nprint "hi"')
        meta = parse_metadata(widget)
        assert meta["config"] == {"a": "1", "b": "2", "c": "3"}


# ── Nested use ──────────────────────────────────────────────────────


class TestNestedUse:
    def test_widget_a_uses_widget_b(self, tmp_path: Path):
        """Widget A uses widget B — B's objects land under A.B.* namespace."""
        (tmp_path / "inner.rosh").write_text("create number value\nset value to 10")
        (tmp_path / "outer.rosh").write_text("create number count\nuse inner")
        stmts = load_widget("outer", search_paths=[tmp_path])
        creates = [s for s in stmts if isinstance(s, CreateStatement)]
        names = [c.name for c in creates]
        assert "outer.count" in names
        assert "outer.inner.value" in names

    def test_circular_dependency_warns(self, tmp_path: Path):
        """Circular dep A→B→A is detected gracefully."""
        (tmp_path / "alpha.rosh").write_text("create number x\nuse beta")
        (tmp_path / "beta.rosh").write_text("create number y\nuse alpha")
        with pytest.warns(UserWarning, match="Circular dependency"):
            stmts = load_widget("alpha", search_paths=[tmp_path])
        # Should still get alpha's own statements
        creates = [s for s in stmts if isinstance(s, CreateStatement)]
        assert any(c.name == "alpha.x" for c in creates)
        # Beta's objects should be there (before it tried to re-load alpha)
        assert any(c.name == "alpha.beta.y" for c in creates)

    def test_self_reference_warns(self, tmp_path: Path):
        """Widget using itself is caught."""
        (tmp_path / "loop.rosh").write_text("create number x\nuse loop")
        with pytest.warns(UserWarning, match="Circular dependency"):
            stmts = load_widget("loop", search_paths=[tmp_path])
        creates = [s for s in stmts if isinstance(s, CreateStatement)]
        assert any(c.name == "loop.x" for c in creates)


# ── Sprite/Sound/Play prefixing ───────────────────────────────────


class TestSpritesSoundsPlayPrefixing:
    def test_sprite_name_prefixed(self):
        prog = parse_string('sprite hero "pixel art spaceship"')
        result = prefix_programme(prog, "ns")
        stmt = result[0]
        assert isinstance(stmt, SpriteStatement)
        assert stmt.name == "ns.hero"
        assert stmt.description == "pixel art spaceship"

    def test_sound_name_prefixed(self):
        prog = parse_string('sound laser "short sci-fi laser blast"')
        result = prefix_programme(prog, "ns")
        stmt = result[0]
        assert isinstance(stmt, SoundStatement)
        assert stmt.name == "ns.laser"
        assert stmt.description == "short sci-fi laser blast"

    def test_play_sound_prefixed(self):
        prog = parse_string("play boom")
        result = prefix_programme(prog, "ns")
        stmt = result[0]
        assert isinstance(stmt, PlayStatement)
        assert stmt.sound == "ns.boom"

    def test_play_sound_with_mode_prefixed(self):
        prog = parse_string("play music loop")
        result = prefix_programme(prog, "ns")
        stmt = result[0]
        assert isinstance(stmt, PlayStatement)
        assert stmt.sound == "ns.music"
        assert stmt.mode == "loop"

    def test_sprite_in_widget_file(self, tmp_path: Path):
        (tmp_path / "ship.rosh").write_text(
            'create object obj\nsprite obj "pixel spaceship"'
        )
        stmts = load_widget("ship", search_paths=[tmp_path])
        sprites = [s for s in stmts if isinstance(s, SpriteStatement)]
        assert len(sprites) == 1
        assert sprites[0].name == "ship.obj"

    def test_sound_in_widget_file(self, tmp_path: Path):
        (tmp_path / "fx.rosh").write_text(
            'sound zap "laser zap"\nplay zap'
        )
        stmts = load_widget("fx", search_paths=[tmp_path])
        sounds = [s for s in stmts if isinstance(s, SoundStatement)]
        plays = [s for s in stmts if isinstance(s, PlayStatement)]
        assert sounds[0].name == "fx.zap"
        assert plays[0].sound == "fx.zap"


# ── OnStatement prefixing ──────────────────────────────────────────


class TestOnStatementPrefixing:
    def test_on_set_action_prefixes_target_and_value(self):
        prog = parse_string("on click set score to score + 1")
        result = prefix_programme(prog, "ns")
        stmt = result[0]
        assert isinstance(stmt, OnStatement)
        assert stmt.event == "click"  # event stays global
        assert "ns.score to ns.score + 1" == stmt.args

    def test_on_set_variable_right_operand_prefixed(self):
        """Variable right operands in on-set must be prefixed (enemy drift bug)."""
        prog = parse_string("on update set obj.x to obj.x + drift")
        result = prefix_programme(prog, "ns")
        stmt = result[0]
        assert isinstance(stmt, OnStatement)
        assert stmt.args == "ns.obj.x to ns.obj.x + ns.drift"

    def test_on_set_literal_value(self):
        prog = parse_string('on reset set health to 100')
        result = prefix_programme(prog, "ns")
        stmt = result[0]
        assert isinstance(stmt, OnStatement)
        assert stmt.args == "ns.health to 100"

    def test_on_send_event_stays_global(self):
        prog = parse_string("on click send boom")
        result = prefix_programme(prog, "ns")
        stmt = result[0]
        assert isinstance(stmt, OnStatement)
        assert stmt.args == "boom"

    def test_on_say_interpolation_prefixed(self):
        prog = parse_string("on click say Score is {value}")
        result = prefix_programme(prog, "ns")
        stmt = result[0]
        assert isinstance(stmt, OnStatement)
        assert "{ns.value}" in stmt.args

    def test_on_print_interpolation_prefixed(self):
        prog = parse_string('on click print "Score: {value}"')
        result = prefix_programme(prog, "ns")
        stmt = result[0]
        assert isinstance(stmt, OnStatement)
        assert "{ns.value}" in stmt.args

    def test_on_destroy_prefixed(self):
        prog = parse_string("on timeout destroy bullet")
        result = prefix_programme(prog, "ns")
        stmt = result[0]
        assert isinstance(stmt, OnStatement)
        assert stmt.args == "ns.bullet"

    def test_on_condition_field_prefixed(self):
        prog = parse_string("on update when health < 0 set status to dead")
        result = prefix_programme(prog, "ns")
        stmt = result[0]
        assert isinstance(stmt, OnStatement)
        assert stmt.condition == "ns.health < 0"
        assert "ns.status to dead" == stmt.args

    def test_on_event_stays_global(self):
        """Events should NOT be prefixed — cross-widget communication."""
        prog = parse_string("on caught set score to score + 1")
        result = prefix_programme(prog, "ns")
        stmt = result[0]
        assert stmt.event == "caught"


# ── Python widget factories ────────────────────────────────────────


class TestPythonWidgetFactory:
    def _write_factory(self, tmp_path: Path, name: str, code: str) -> Path:
        """Helper to write a factory .py file."""
        p = tmp_path / f"{name}.py"
        p.write_text(code)
        return p

    def test_find_py_factory(self, tmp_path: Path):
        self._write_factory(tmp_path, "my-factory", "METADATA = {}\ndef generate(config): return []")
        result = find_widget("my-factory", search_paths=[tmp_path])
        assert result is not None
        assert result.suffix == ".py"

    def test_rosh_takes_priority_over_py(self, tmp_path: Path):
        """If both .rosh and .py exist, .rosh wins."""
        (tmp_path / "dual.rosh").write_text('print "rosh"')
        self._write_factory(tmp_path, "dual", "METADATA = {}\ndef generate(config): return []")
        result = find_widget("dual", search_paths=[tmp_path])
        assert result is not None
        assert result.suffix == ".rosh"

    def test_load_factory_generates_statements(self, tmp_path: Path):
        self._write_factory(tmp_path, "boxes", """\
from rosh_lang.model import CreateStatement, SetStatement

METADATA = {
    "widget": "boxes",
    "version": "0.1",
    "description": "Test factory",
    "config": {"count": "2"},
    "licence": "Rosh-BSL",
}

def generate(config):
    count = int(config.get("count", "2"))
    stmts = []
    for i in range(count):
        stmts.append(CreateStatement(kind="object", name=f"box{i}"))
        stmts.append(SetStatement(target=f"box{i}.x", value=str(0.1 * i)))
    return stmts
""")
        stmts = load_widget("boxes", search_paths=[tmp_path])
        creates = [s for s in stmts if isinstance(s, CreateStatement)]
        assert len(creates) == 2
        assert creates[0].name == "boxes.box0"
        assert creates[1].name == "boxes.box1"

    def test_factory_config_override(self, tmp_path: Path):
        self._write_factory(tmp_path, "items", """\
from rosh_lang.model import CreateStatement

METADATA = {"config": {"count": "2"}}

def generate(config):
    count = int(config.get("count", "2"))
    return [CreateStatement(kind="object", name=f"item{i}") for i in range(count)]
""")
        stmts = load_widget("items", config={"count": "3"}, search_paths=[tmp_path])
        creates = [s for s in stmts if isinstance(s, CreateStatement)]
        assert len(creates) == 3

    def test_factory_metadata_parsing(self, tmp_path: Path):
        self._write_factory(tmp_path, "meta-test", """\
METADATA = {
    "widget": "meta-test",
    "version": "0.2",
    "description": "Test metadata",
    "config": {"rows": "3"},
    "licence": "Rosh-BSL",
}

def generate(config):
    return []
""")
        meta = parse_metadata(tmp_path / "meta-test.py")
        assert meta["widget"] == "meta-test"
        assert meta["version"] == "0.2"
        assert meta["description"] == "Test metadata"
        assert meta["config"] == {"rows": "3"}
        assert meta["licence"] == "Rosh-BSL"

    def test_factory_prefixing_applied(self, tmp_path: Path):
        """Factory output gets namespace-prefixed like .rosh widgets."""
        self._write_factory(tmp_path, "pfx", """\
from rosh_lang.model import SetStatement

METADATA = {}

def generate(config):
    return [SetStatement(target="value", value="42")]
""")
        stmts = load_widget("pfx", search_paths=[tmp_path])
        sets = [s for s in stmts if isinstance(s, SetStatement)]
        assert sets[0].target == "pfx.value"

    def test_list_available_includes_py(self, tmp_path: Path):
        """_list_available() should find both .rosh and .py widgets."""
        (tmp_path / "a.rosh").write_text('print "hi"')
        self._write_factory(tmp_path, "b", "METADATA = {}\ndef generate(c): return []")
        result = find_widget("b", search_paths=[tmp_path])
        assert result is not None


# ── Bundled widget tests — new widgets ──────────────────────────────


class TestEnemyGridWidget:
    def test_load_default(self):
        stmts = load_widget("enemy-grid", search_paths=[BUNDLED_DIR])
        creates = [s for s in stmts if isinstance(s, CreateStatement)]
        # 2 rows × 5 cols = 10 objects
        assert len(creates) == 10
        assert creates[0].name == "enemy-grid.e0_0"
        assert creates[-1].name == "enemy-grid.e1_4"

    def test_config_override_rows_cols(self):
        stmts = load_widget("enemy-grid", config={"rows": "3", "cols": "2"}, search_paths=[BUNDLED_DIR])
        creates = [s for s in stmts if isinstance(s, CreateStatement)]
        assert len(creates) == 6

    def test_has_positions(self):
        stmts = load_widget("enemy-grid", search_paths=[BUNDLED_DIR])
        sets = [s for s in stmts if isinstance(s, SetStatement)]
        x_sets = [s for s in sets if s.target.endswith(".x")]
        assert len(x_sets) == 10

    def test_metadata(self):
        meta = parse_metadata(BUNDLED_DIR / "enemy-grid.py")
        assert meta["widget"] == "enemy-grid"
        assert meta["config"]["rows"] == "2"
        assert meta["config"]["cols"] == "5"


class TestStarfieldWidget:
    def test_load_default(self):
        stmts = load_widget("starfield", search_paths=[BUNDLED_DIR])
        creates = [s for s in stmts if isinstance(s, CreateStatement)]
        assert len(creates) == 15

    def test_config_override_count(self):
        stmts = load_widget("starfield", config={"count": "5"}, search_paths=[BUNDLED_DIR])
        creates = [s for s in stmts if isinstance(s, CreateStatement)]
        assert len(creates) == 5

    def test_deterministic(self):
        """Starfield should produce the same output on repeated calls."""
        stmts1 = load_widget("starfield", search_paths=[BUNDLED_DIR])
        stmts2 = load_widget("starfield", search_paths=[BUNDLED_DIR])
        sets1 = [(s.target, s.value) for s in stmts1 if isinstance(s, SetStatement)]
        sets2 = [(s.target, s.value) for s in stmts2 if isinstance(s, SetStatement)]
        assert sets1 == sets2


class TestGridWidget:
    def test_load_default(self):
        stmts = load_widget("grid", search_paths=[BUNDLED_DIR])
        creates = [s for s in stmts if isinstance(s, CreateStatement)]
        # 3×3 = 9 cells
        assert len(creates) == 9
        assert creates[0].name == "grid.cell_0_0"
        assert creates[-1].name == "grid.cell_2_2"

    def test_config_override(self):
        stmts = load_widget("grid", config={"rows": "2", "cols": "2"}, search_paths=[BUNDLED_DIR])
        creates = [s for s in stmts if isinstance(s, CreateStatement)]
        assert len(creates) == 4

    def test_is_python_factory(self):
        """Grid should now be a .py factory, not .rosh."""
        path = find_widget("grid", search_paths=[BUNDLED_DIR])
        assert path is not None
        assert path.suffix == ".py"


class TestMessageWidget:
    def test_load(self):
        stmts = load_widget("message", search_paths=[BUNDLED_DIR])
        creates = [s for s in stmts if isinstance(s, CreateStatement)]
        assert any(c.name == "message.box" for c in creates)

    def test_config_override_text(self):
        stmts = load_widget("message", config={"box.label": "Game Over"}, search_paths=[BUNDLED_DIR])
        sets = [s for s in stmts if isinstance(s, SetStatement)]
        label_sets = [s for s in sets if s.target == "message.box.label"]
        assert label_sets[-1].value == "Game Over"

    def test_metadata(self):
        meta = parse_metadata(BUNDLED_DIR / "message.rosh")
        assert meta["widget"] == "message"
        assert meta["licence"] == "Rosh-BSL"


class TestTitleScreenWidget:
    def test_load(self):
        stmts = load_widget("title-screen", search_paths=[BUNDLED_DIR])
        creates = [s for s in stmts if isinstance(s, CreateStatement)]
        names = [c.name for c in creates]
        assert "title-screen.heading" in names
        assert "title-screen.sub" in names
        assert "title-screen.prompt" in names

    def test_config_override_title(self):
        stmts = load_widget("title-screen", config={"heading.label": "Space Invaders"}, search_paths=[BUNDLED_DIR])
        sets = [s for s in stmts if isinstance(s, SetStatement)]
        title_sets = [s for s in sets if s.target == "title-screen.heading.label"]
        assert title_sets[-1].value == "Space Invaders"

    def test_metadata(self):
        meta = parse_metadata(BUNDLED_DIR / "title-screen.rosh")
        assert meta["widget"] == "title-screen"


class TestExplosionWidget:
    def test_load(self):
        stmts = load_widget("explosion", search_paths=[BUNDLED_DIR])
        creates = [s for s in stmts if isinstance(s, CreateStatement)]
        assert any(c.name == "explosion.flash" for c in creates)

    def test_has_sound(self):
        stmts = load_widget("explosion", search_paths=[BUNDLED_DIR])
        sounds = [s for s in stmts if isinstance(s, SoundStatement)]
        assert any(s.name == "explosion.boom" for s in sounds)

    def test_has_on_statements(self):
        stmts = load_widget("explosion", search_paths=[BUNDLED_DIR])
        ons = [s for s in stmts if isinstance(s, OnStatement)]
        assert len(ons) >= 2


class TestBulletWidget:
    def test_load(self):
        stmts = load_widget("bullet", search_paths=[BUNDLED_DIR])
        creates = [s for s in stmts if isinstance(s, CreateStatement)]
        assert any(c.name == "bullet.obj" for c in creates)

    def test_has_sound(self):
        stmts = load_widget("bullet", search_paths=[BUNDLED_DIR])
        sounds = [s for s in stmts if isinstance(s, SoundStatement)]
        assert any(s.name == "bullet.pew" for s in sounds)

    def test_on_statements_prefixed(self):
        stmts = load_widget("bullet", search_paths=[BUNDLED_DIR])
        ons = [s for s in stmts if isinstance(s, OnStatement)]
        assert len(ons) >= 1
        # The "set obj.y to obj.y - 0.02" should be prefixed
        set_ons = [o for o in ons if o.action == "set"]
        assert any("bullet.obj.y" in o.args for o in set_ons)


class TestCoinWidget:
    def test_load(self):
        stmts = load_widget("coin", search_paths=[BUNDLED_DIR])
        creates = [s for s in stmts if isinstance(s, CreateStatement)]
        assert any(c.name == "coin.gem" for c in creates)

    def test_has_sprite(self):
        stmts = load_widget("coin", search_paths=[BUNDLED_DIR])
        sprites = [s for s in stmts if isinstance(s, SpriteStatement)]
        assert any(s.name == "coin.gem" for s in sprites)

    def test_has_sound(self):
        stmts = load_widget("coin", search_paths=[BUNDLED_DIR])
        sounds = [s for s in stmts if isinstance(s, SoundStatement)]
        assert any(s.name == "coin.chime" for s in sounds)
