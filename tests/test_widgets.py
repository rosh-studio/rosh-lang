"""Tests for widget loader — search, namespace prefixing, config, fuzzy match."""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from rosh_lang.core.model import (
    AddStatement,
    AfterStatement,
    CreateStatement,
    DestroyStatement,
    DefineStatement,
    DoStatement,
    ForEachStatement,
    IfStatement,
    OnStatement,
    PlayStatement,
    PrintStatement,
    RemoveStatement,
    RepeatStatement,
    SayStatement,
    SendStatement,
    SetStatement,
    SoundStatement,
    SpriteStatement,
    WhenStatement,
)
from rosh_lang.core.parser import parse_string
from rosh_lang.core.runtime import Runtime
from rosh_lang.core.widgets import (
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

    def test_path_traversal_blocked(self, tmp_path: Path):
        """Widget names like ../../evil must not escape the search path."""
        widgets_dir = tmp_path / "widgets"
        widgets_dir.mkdir()
        # Place a "malicious" widget one level above the search path
        evil = tmp_path / "evil.rosh"
        evil.write_text('print "pwned"')

        with pytest.warns(UserWarning):
            result = find_widget("../evil", search_paths=[widgets_dir])
        assert result is None

    def test_path_traversal_py_blocked(self, tmp_path: Path):
        """Python factory path traversal is also blocked."""
        widgets_dir = tmp_path / "widgets"
        widgets_dir.mkdir()
        evil = tmp_path / "evil.py"
        evil.write_text('METADATA = {"widget": "evil", "version": "0", "config": {}, "licence": "Rosh-BSL", "provides": [], "requires": [], "exposes": []}')

        with pytest.warns(UserWarning):
            result = find_widget("../evil", search_paths=[widgets_dir])
        assert result is None


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

    def test_callable_interface_data_preserved_and_prefixed(self):
        prog = parse_string(
            "define greet with name\n  print {name}\nend\n"
            "do greet name=visitor"
        )
        define, call = prefix_programme(prog, "ns")
        assert isinstance(define, DefineStatement)
        assert define.params == ["ns.name"]
        assert isinstance(call, DoStatement)
        assert call.args == {"ns.name": "ns.visitor"}

    def test_callable_literal_argument_is_not_prefixed(self):
        prog = parse_string(
            'define greet with name\n  print {name}\nend\n'
            'do greet name="Roger"'
        )
        call = prefix_programme(prog, "ns")[1]
        assert isinstance(call, DoStatement)
        assert call.args == {"ns.name": '"Roger"'}

    def test_prefixed_callable_binds_and_restores_nested_params(self):
        prog = parse_string(
            "define greet with name\n  print {name}\nend\n"
            "do greet name=visitor"
        )
        rt = Runtime(output=io.StringIO())
        rt.state["ns"] = {"visitor": "Roger", "name": "original"}

        rt.run(type(prog)(statements=prefix_programme(prog, "ns")))

        assert rt.output.getvalue() == "Roger\n"
        assert rt.state["ns"]["name"] == "original"
        assert "ns.name" not in rt.state

    def test_collection_statements_prefixed(self):
        prog = parse_string(
            "create list items\n"
            "add item to items\n"
            "remove item from items\n"
            "for each item in items\n  print {item}\nend"
        )
        result = prefix_programme(prog, "ns")
        assert isinstance(result[1], AddStatement)
        assert result[1].item == "ns.item"
        assert result[1].target == "ns.items"
        assert isinstance(result[2], RemoveStatement)
        assert result[2].target == "ns.items"
        loop = result[3]
        assert isinstance(loop, ForEachStatement)
        assert loop.var == "ns.item"
        assert loop.target == "ns.items"
        assert isinstance(loop.body[0], PrintStatement)
        assert loop.body[0].text == "{ns.item}"

    def test_collection_literal_item_is_not_prefixed(self):
        result = prefix_programme(parse_string(
            'add "guest" to visitors\n'
            'add welcome home to messages'
        ), "ns")
        assert isinstance(result[0], AddStatement)
        assert result[0].item == '"guest"'
        assert result[0].target == "ns.visitors"
        assert result[1].item == "welcome home"
        assert result[1].target == "ns.messages"

    def test_repeat_body_and_names_prefixed(self):
        prog = parse_string("repeat count as i\n  print {i}\nend")
        loop = prefix_programme(prog, "ns")[0]
        assert isinstance(loop, RepeatStatement)
        assert loop.count == "ns.count"
        assert loop.var == "ns.i"
        assert loop.body[0].text == "{ns.i}"

    def test_set_count_expression_and_quoted_comparison_prefixed(self):
        result = prefix_programme(parse_string(
            'set total to count of items\n'
            'set ready to status == "ready"'
        ), "ns")
        assert result[0].value == "count of ns.items"
        assert result[1].value == 'ns.status == "ready"'


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
        stmts = load_widget("player", search_paths=[BUNDLED_DIR])
        creates = [s for s in stmts if isinstance(s, CreateStatement)]
        assert any(c.name == "player" for c in creates)  # _self → player
        assert any(c.name == "player.speed" for c in creates)

    def test_config_override_applied_after_widget(self):
        stmts = load_widget("player", config={"speed": "0.05"}, search_paths=[BUNDLED_DIR])
        # Config set should be the last statement
        sets = [s for s in stmts if isinstance(s, SetStatement)]
        last_speed = [s for s in sets if s.target == "player.speed"]
        assert last_speed[-1].value == "0.05"


# ── Named alias (use X as Y) ─────────────────────────────────────


class TestLoadWidgetAlias:
    """use score as hud1 — namespace prefix uses the alias, not the component name."""

    def test_alias_replaces_namespace(self):
        stmts = load_widget("counter", namespace="clicks", search_paths=[BUNDLED_DIR])
        names = [s.name for s in stmts if isinstance(s, CreateStatement)]
        assert all(n.startswith("clicks.") for n in names)
        assert not any(n.startswith("counter.") for n in names)

    def test_alias_set_targets_use_alias(self):
        stmts = load_widget("counter", namespace="clicks", search_paths=[BUNDLED_DIR])
        targets = [s.target for s in stmts if isinstance(s, SetStatement)]
        assert all(t.startswith("clicks.") for t in targets)

    def test_no_alias_uses_component_name(self):
        stmts = load_widget("counter", search_paths=[BUNDLED_DIR])
        names = [s.name for s in stmts if isinstance(s, CreateStatement)]
        assert all(n.startswith("counter.") for n in names)

    def test_alias_with_config_uses_alias_in_set(self):
        stmts = load_widget("counter", config={"start": "5"}, namespace="clicks",
                            search_paths=[BUNDLED_DIR])
        config_sets = [s for s in stmts if isinstance(s, SetStatement) and s.target == "clicks.start"]
        assert len(config_sets) == 1
        assert config_sets[0].value == "5"

    def test_two_aliases_are_independent(self):
        a = load_widget("counter", namespace="a_counter", search_paths=[BUNDLED_DIR])
        b = load_widget("counter", namespace="b_counter", search_paths=[BUNDLED_DIR])
        a_names = {s.name for s in a if isinstance(s, CreateStatement)}
        b_names = {s.name for s in b if isinstance(s, CreateStatement)}
        assert all(n.startswith("a_counter.") for n in a_names)
        assert all(n.startswith("b_counter.") for n in b_names)
        assert a_names.isdisjoint(b_names)


# ── Bundled library discovery ──────────────────────────────────────


class TestBundledLibrary:
    def test_bundled_path_exists(self):
        assert BUNDLED_DIR.is_dir()

    def test_bundled_score_widget_exists(self):
        assert (BUNDLED_DIR / "score.py").is_file()

    def test_find_bundled_widget(self):
        """Widgets found even from arbitrary CWD (bundled path is absolute)."""
        result = find_widget("score", search_paths=[BUNDLED_DIR])
        assert result is not None
        assert result.name == "score.py"

    def test_bundled_widgets_count(self):
        """At least 10 widgets bundled (.rosh + .py)."""
        widgets = list(BUNDLED_DIR.glob("*.rosh")) + list(BUNDLED_DIR.glob("*.py"))
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
        meta = parse_metadata(BUNDLED_DIR / "score.py")
        assert meta["widget"] == "score"
        assert meta["version"] == "0.3"
        assert meta["description"] == "Score display with current value and label"
        assert "x" in meta["config"]
        assert "anchor" in meta["config"]
        assert "theme" in meta["config"]

    def test_parse_player_metadata(self):
        meta = parse_metadata(BUNDLED_DIR / "player.py")
        assert meta["widget"] == "player"
        assert "speed" in meta["config"]
        assert meta["config"]["speed"] == "0.02"

    def test_parse_licence_field(self):
        """Bundled widgets should declare Rosh-BSL licence."""
        meta = parse_metadata(BUNDLED_DIR / "score.py")
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

    def test_interface_fields_present_by_default(self):
        """parse_metadata always returns provides/requires/exposes even for .rosh files."""
        meta = parse_metadata(BUNDLED_DIR / "score.py")
        assert "provides" in meta
        assert "requires" in meta
        assert "exposes" in meta

    def test_interface_fields_are_lists(self):
        meta = parse_metadata(BUNDLED_DIR / "score.py")
        assert isinstance(meta["provides"], list)
        assert isinstance(meta["requires"], list)
        assert isinstance(meta["exposes"], list)

    def test_rosh_file_gets_empty_interface_fields(self, tmp_path: Path):
        """A plain .rosh widget with no METADATA gets empty lists for interface fields."""
        widget = tmp_path / "bare.rosh"
        widget.write_text('print "hello"')
        meta = parse_metadata(widget)
        assert meta["provides"] == []
        assert meta["requires"] == []
        assert meta["exposes"] == []


# ── Phase 1b: component interface metadata ───────────────────────────


class TestComponentInterfaceMetadata:
    """All bundled Python factory components must declare provides/requires/exposes."""

    ALL_PY_WIDGETS = [
        p.stem for p in BUNDLED_DIR.glob("*.py") if not p.name.startswith("_")
    ]

    def test_all_py_widgets_have_provides(self):
        for name in self.ALL_PY_WIDGETS:
            meta = parse_metadata(BUNDLED_DIR / f"{name}.py")
            assert "provides" in meta, f"{name}: missing 'provides'"
            assert isinstance(meta["provides"], list), f"{name}: 'provides' must be a list"

    def test_all_py_widgets_have_requires(self):
        for name in self.ALL_PY_WIDGETS:
            meta = parse_metadata(BUNDLED_DIR / f"{name}.py")
            assert "requires" in meta, f"{name}: missing 'requires'"
            assert isinstance(meta["requires"], list), f"{name}: 'requires' must be a list"

    def test_all_py_widgets_have_exposes(self):
        for name in self.ALL_PY_WIDGETS:
            meta = parse_metadata(BUNDLED_DIR / f"{name}.py")
            assert "exposes" in meta, f"{name}: missing 'exposes'"
            assert isinstance(meta["exposes"], list), f"{name}: 'exposes' must be a list"

    def test_score_exposes_value(self):
        meta = parse_metadata(BUNDLED_DIR / "score.py")
        assert "value" in meta["exposes"]

    def test_timer_provides_timer_done(self):
        meta = parse_metadata(BUNDLED_DIR / "timer.py")
        assert "timer_done" in meta["provides"]

    def test_timer_exposes_seconds(self):
        meta = parse_metadata(BUNDLED_DIR / "timer.py")
        assert "seconds" in meta["exposes"]

    def test_lives_provides_game_over(self):
        meta = parse_metadata(BUNDLED_DIR / "lives.py")
        assert "game-over" in meta["provides"]

    def test_lives_exposes_count(self):
        meta = parse_metadata(BUNDLED_DIR / "lives.py")
        assert "count" in meta["exposes"]

    def test_game_lifecycle_provides_game_start(self):
        meta = parse_metadata(BUNDLED_DIR / "game-lifecycle.rosh")
        assert "game_start" in meta["provides"]

    def test_game_lifecycle_requires_game_over(self):
        meta = parse_metadata(BUNDLED_DIR / "game-lifecycle.rosh")
        assert "game_over" in meta["requires"]

    def test_game_lifecycle_exposes_phase(self):
        meta = parse_metadata(BUNDLED_DIR / "game-lifecycle.rosh")
        assert "phase" in meta["exposes"]

    def test_controller_provides_fire_events(self):
        meta = parse_metadata(BUNDLED_DIR / "controller.py")
        assert "fire" in meta["provides"]
        assert "fire2" in meta["provides"]

    def test_bullet_exposes_fire_flag(self):
        meta = parse_metadata(BUNDLED_DIR / "bullet.py")
        assert "_fire" in meta["exposes"]

    def test_health_bar_exposes_current_and_max(self):
        meta = parse_metadata(BUNDLED_DIR / "health-bar.py")
        assert "current" in meta["exposes"]
        assert "max" in meta["exposes"]

    def test_player_exposes_ship(self):
        meta = parse_metadata(BUNDLED_DIR / "player.py")
        assert "ship" in meta["exposes"]

    def test_ball_exposes_ball(self):
        meta = parse_metadata(BUNDLED_DIR / "ball.py")
        assert "ball" in meta["exposes"]


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
from rosh_lang.core.model import CreateStatement, SetStatement

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
from rosh_lang.core.model import CreateStatement

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
from rosh_lang.core.model import SetStatement

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


class TestNativeConfigBinding:
    def test_label_and_message_are_native_rosh_components(self):
        for name in ("label", "message", "title-screen", "game-lifecycle"):
            assert (BUNDLED_DIR / f"{name}.rosh").is_file()
            assert not (BUNDLED_DIR / f"{name}.py").exists()

    def test_declared_defaults_bound_before_body(self):
        stmts = load_widget("label", search_paths=[BUNDLED_DIR])
        config_index = next(
            i for i, s in enumerate(stmts)
            if isinstance(s, SetStatement) and s.target == "label.config.text"
        )
        display_index = next(
            i for i, s in enumerate(stmts)
            if isinstance(s, SetStatement) and s.target == "label.display.label"
        )
        assert config_index < display_index

    def test_caller_config_changes_component_output(self):
        out = io.StringIO()
        runtime = Runtime(output=out, search_paths=[BUNDLED_DIR])
        runtime.run(parse_string('use label as title text "Welcome home" x 0.2'))
        assert runtime.state["title"]["display"]["label"] == "Welcome home"
        assert runtime.state["title"]["display"]["x"] == 0.2
        assert runtime.state["title"]["config"]["text"] == "Welcome home"

    def test_native_interface_metadata(self):
        meta = parse_metadata(BUNDLED_DIR / "label.rosh")
        assert meta["exposes"] == ["display"]

    def test_all_native_components_have_required_metadata(self):
        for path in BUNDLED_DIR.glob("*.rosh"):
            meta = parse_metadata(path)
            assert meta["widget"], f"{path.name}: missing widget"
            assert meta["version"], f"{path.name}: missing version"
            assert meta["description"], f"{path.name}: missing description"
            assert meta["licence"] == "Rosh-BSL", f"{path.name}: missing Rosh-BSL licence"

    def test_all_native_components_load_standalone(self):
        for path in BUNDLED_DIR.glob("*.rosh"):
            stmts = load_widget(path.stem, search_paths=[BUNDLED_DIR])
            assert stmts, f"{path.name}: did not load"


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

    def test_declared_config_changes_title(self):
        runtime = Runtime(output=io.StringIO(), search_paths=[BUNDLED_DIR])
        runtime.run(parse_string('use title-screen title "Space Invaders"'))
        assert runtime.state["title-screen"]["heading"]["label"] == "Space Invaders"


class TestExplosionWidget:
    def test_load_default_creates_3_flashes(self):
        stmts = load_widget("explosion", search_paths=[BUNDLED_DIR])
        creates = [s for s in stmts if isinstance(s, CreateStatement)]
        obj_creates = [c for c in creates if c.name.startswith("explosion.b")]
        assert len(obj_creates) == 3

    def test_config_override_count(self):
        stmts = load_widget("explosion", config={"count": "5"}, search_paths=[BUNDLED_DIR])
        creates = [s for s in stmts if isinstance(s, CreateStatement)]
        obj_creates = [c for c in creates if c.name.startswith("explosion.b")]
        assert len(obj_creates) == 5

    def test_pool_metadata(self):
        stmts = load_widget("explosion", search_paths=[BUNDLED_DIR])
        sets = [s for s in stmts if isinstance(s, SetStatement)]
        pool_count = [s for s in sets if s.target == "explosion._pool_count"]
        assert len(pool_count) == 1
        assert pool_count[0].value == "3"

    def test_has_sound(self):
        stmts = load_widget("explosion", search_paths=[BUNDLED_DIR])
        sounds = [s for s in stmts if isinstance(s, SoundStatement)]
        assert any(s.name == "explosion.boom" for s in sounds)

    def test_has_on_statements(self):
        stmts = load_widget("explosion", search_paths=[BUNDLED_DIR])
        ons = [s for s in stmts if isinstance(s, OnStatement)]
        assert len(ons) >= 2

    def test_is_python_factory(self):
        path = find_widget("explosion", search_paths=[BUNDLED_DIR])
        assert path is not None
        assert path.suffix == ".py"

    def test_metadata(self):
        meta = parse_metadata(BUNDLED_DIR / "explosion.py")
        assert meta["widget"] == "explosion"
        assert meta["config"]["count"] == "3"
        assert meta["licence"] == "Rosh-BSL"


class TestBulletWidget:
    def test_load_default_creates_3_bullets(self):
        stmts = load_widget("bullet", search_paths=[BUNDLED_DIR])
        creates = [s for s in stmts if isinstance(s, CreateStatement)]
        obj_creates = [c for c in creates if c.name.startswith("bullet.b")]
        assert len(obj_creates) == 3
        assert obj_creates[0].name == "bullet.b0"
        assert obj_creates[1].name == "bullet.b1"
        assert obj_creates[2].name == "bullet.b2"

    def test_config_override_count(self):
        stmts = load_widget("bullet", config={"count": "5"}, search_paths=[BUNDLED_DIR])
        creates = [s for s in stmts if isinstance(s, CreateStatement)]
        obj_creates = [c for c in creates if c.name.startswith("bullet.b")]
        assert len(obj_creates) == 5

    def test_pool_metadata(self):
        stmts = load_widget("bullet", search_paths=[BUNDLED_DIR])
        sets = [s for s in stmts if isinstance(s, SetStatement)]
        pool_count = [s for s in sets if s.target == "bullet._pool_count"]
        assert len(pool_count) == 1
        assert pool_count[0].value == "3"

    def test_has_sound(self):
        stmts = load_widget("bullet", search_paths=[BUNDLED_DIR])
        sounds = [s for s in stmts if isinstance(s, SoundStatement)]
        assert any(s.name == "bullet.pew" for s in sounds)

    def test_no_boundary_on_statements(self):
        """Boundary cleanup is handled by tickPools, not on-statements."""
        stmts = load_widget("bullet", search_paths=[BUNDLED_DIR])
        ons = [s for s in stmts if isinstance(s, OnStatement)]
        assert len(ons) == 0

    def test_is_python_factory(self):
        path = find_widget("bullet", search_paths=[BUNDLED_DIR])
        assert path is not None
        assert path.suffix == ".py"

    def test_metadata(self):
        meta = parse_metadata(BUNDLED_DIR / "bullet.py")
        assert meta["widget"] == "bullet"
        assert meta["config"]["count"] == "3"
        assert meta["licence"] == "Rosh-BSL"


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


# ── AfterStatement prefix passthrough ────────────────────────────


class TestAfterWidgetPrefix:
    def test_after_event_not_prefixed(self):
        """after event names should stay global (not prefixed) — like send."""
        from rosh_lang.core.widgets import _prefix_statement

        stmt = AfterStatement(delay=2.0, event="wave_2")
        result = _prefix_statement(stmt, "game")
        assert isinstance(result, AfterStatement)
        assert result.event == "wave_2"
        assert result.delay == 2.0


# ── New widget tests ───────────────────────────────────────────────


class TestTimerWidget:
    def test_load(self):
        stmts = load_widget("timer", search_paths=[BUNDLED_DIR])
        creates = [s for s in stmts if isinstance(s, CreateStatement)]
        assert any(c.name == "timer.seconds" for c in creates)
        assert any(c.name == "timer._timer_total" for c in creates)
        assert any(c.name == "timer._timer_running" for c in creates)

    def test_config_total(self):
        stmts = load_widget("timer", config={"total": "30"}, search_paths=[BUNDLED_DIR])
        sets = [s for s in stmts if isinstance(s, SetStatement)]
        total_sets = [s for s in sets if s.target == "timer._timer_total"]
        assert total_sets[-1].value == "30"

    def test_display_has_text_color(self):
        stmts = load_widget("timer", config={"text_color": "#ffcc00"}, search_paths=[BUNDLED_DIR])
        sets = [s for s in stmts if isinstance(s, SetStatement)]
        tc = [s for s in sets if s.target == "timer.display.text_color"]
        assert tc[-1].value == "#ffcc00"


class TestGameLifecycleWidget:
    def test_load(self):
        stmts = load_widget("game-lifecycle", search_paths=[BUNDLED_DIR])
        creates = [s for s in stmts if isinstance(s, CreateStatement)]
        names = [c.name for c in creates]
        assert "game-lifecycle.phase" in names
        assert "game-lifecycle.title_heading" in names
        assert "game-lifecycle.over_heading" in names

    def test_phase_starts_title(self):
        stmts = load_widget("game-lifecycle", search_paths=[BUNDLED_DIR])
        sets = [s for s in stmts if isinstance(s, SetStatement)]
        phase_sets = [s for s in sets if s.target == "game-lifecycle.phase"]
        assert phase_sets[0].value == '"title"'

    def test_config_title(self):
        runtime = Runtime(output=io.StringIO(), search_paths=[BUNDLED_DIR])
        runtime.run(parse_string('use game-lifecycle title "Space Pong"'))
        assert runtime.state["game-lifecycle"]["title_heading"]["label"] == "Space Pong"

    def test_native_interface_metadata(self):
        meta = parse_metadata(BUNDLED_DIR / "game-lifecycle.rosh")
        assert meta["provides"] == ["game_start", "game_restart"]
        assert meta["requires"] == ["game_over"]
        assert meta["exposes"] == ["phase"]

    def test_native_lifecycle_transitions(self):
        runtime = Runtime(output=io.StringIO(), search_paths=[BUNDLED_DIR])
        runtime.run(parse_string(
            "use game-lifecycle\n"
            "send keydown\n"
            "send game_over\n"
            "send keydown"
        ))
        lifecycle = runtime.state["game-lifecycle"]
        assert lifecycle["phase"] == "title"
        assert lifecycle["title_heading"]["visible"] == 1
        assert lifecycle["over_heading"]["visible"] == 0


class TestBallWidget:
    def test_load(self):
        stmts = load_widget("ball", search_paths=[BUNDLED_DIR])
        creates = [s for s in stmts if isinstance(s, CreateStatement)]
        assert any(c.name == "ball" for c in creates)

    def test_wall_bounce_all(self):
        """Default 'all' walls should produce 8 on-statements (4 walls × 2)."""
        stmts = load_widget("ball", search_paths=[BUNDLED_DIR])
        ons = [s for s in stmts if isinstance(s, OnStatement)]
        assert len(ons) == 8

    def test_wall_bounce_top_sides(self):
        """'top-sides' walls should produce 6 on-statements (3 walls × 2)."""
        stmts = load_widget("ball", config={"walls": "top-sides"}, search_paths=[BUNDLED_DIR])
        ons = [s for s in stmts if isinstance(s, OnStatement)]
        assert len(ons) == 6

    def test_bounce_sound(self):
        stmts = load_widget("ball", search_paths=[BUNDLED_DIR])
        sounds = [s for s in stmts if isinstance(s, SoundStatement)]
        assert any(s.name == "ball.bounce" for s in sounds)


class TestPlayerWidget:
    def test_load(self):
        stmts = load_widget("player", search_paths=[BUNDLED_DIR])
        creates = [s for s in stmts if isinstance(s, CreateStatement)]
        assert any(c.name == "player" for c in creates)
        assert any(c.name == "player.speed" for c in creates)

    def test_movement_handlers(self):
        """Default arrows keys should generate 4 IfStatements in a when-update block."""
        stmts = load_widget("player", search_paths=[BUNDLED_DIR])
        ifs = [s for s in stmts if isinstance(s, IfStatement)]
        assert len(ifs) == 4
        # Verify _keys is NOT prefixed (it's a global)
        assert any("_keys.ArrowLeft" in i.condition for i in ifs)

    def test_clamp_statements(self):
        stmts = load_widget("player", search_paths=[BUNDLED_DIR])
        ons = [s for s in stmts if isinstance(s, OnStatement)]
        assert any("clamp player.x" in o.args for o in ons)
        assert any("clamp player.y" in o.args for o in ons)

    def test_horizontal_only(self):
        stmts = load_widget("player", config={"move": "x"}, search_paths=[BUNDLED_DIR])
        ifs = [s for s in stmts if isinstance(s, IfStatement)]
        assert len(ifs) == 2
        assert all("x" in i.then_body[0].target for i in ifs if isinstance(i, IfStatement))

    def test_no_movement(self):
        stmts = load_widget("player", config={"move": "none"}, search_paths=[BUNDLED_DIR])
        ifs = [s for s in stmts if isinstance(s, IfStatement)]
        assert len(ifs) == 0

    def test_wasd_keys(self):
        stmts = load_widget("player", config={"keys": "wasd"}, search_paths=[BUNDLED_DIR])
        ifs = [s for s in stmts if isinstance(s, IfStatement)]
        assert any("_keys.a" in i.condition for i in ifs)
        assert any("_keys.w" in i.condition for i in ifs)


class TestLivesWidget:
    def test_auto_gameover_default(self):
        """Lives widget should generate check-lives → game-over by default."""
        stmts = load_widget("lives", search_paths=[BUNDLED_DIR])
        ons = [s for s in stmts if isinstance(s, OnStatement)]
        assert any(
            o.event == "check-lives" and "game-over" in o.args and "lives.count <= 0" in o.condition
            for o in ons
        )

    def test_auto_gameover_disabled(self):
        stmts = load_widget("lives", config={"auto_gameover": "0"}, search_paths=[BUNDLED_DIR])
        ons = [s for s in stmts if isinstance(s, OnStatement)]
        assert not any(o.event == "check-lives" for o in ons)


class TestHazardWidget:
    def test_load(self):
        stmts = load_widget("hazard", search_paths=[BUNDLED_DIR])
        creates = [s for s in stmts if isinstance(s, CreateStatement)]
        obj_creates = [c for c in creates if c.name.startswith("hazard.b")]
        assert len(obj_creates) == 5

    def test_spawn_rate(self):
        stmts = load_widget("hazard", search_paths=[BUNDLED_DIR])
        sets = [s for s in stmts if isinstance(s, SetStatement)]
        rate = [s for s in sets if s.target == "hazard._spawn_rate"]
        assert rate[0].value == "0.8"

    def test_config_count(self):
        stmts = load_widget("hazard", config={"count": "3"}, search_paths=[BUNDLED_DIR])
        creates = [s for s in stmts if isinstance(s, CreateStatement)]
        obj_creates = [c for c in creates if c.name.startswith("hazard.b")]
        assert len(obj_creates) == 3


class TestPrefixRandomClamp:
    """Verify that random and clamp values survive widget prefixing."""

    def test_prefix_random_bare(self):
        from rosh_lang.core.widgets import _prefix_set_value
        result = _prefix_set_value("x", "random", "ns")
        assert result == "random"

    def test_prefix_random_range(self):
        from rosh_lang.core.widgets import _prefix_set_value
        result = _prefix_set_value("x", "random 0.1 0.9", "ns")
        assert result == "random 0.1 0.9"

    def test_prefix_clamp(self):
        from rosh_lang.core.widgets import _prefix_set_value
        result = _prefix_set_value("x", "clamp paddle.x 0.02 0.8", "ns")
        assert result == "clamp ns.paddle.x 0.02 0.8"


class TestTextColorFontSize:
    """Verify text_color and font_size in compiled output."""

    def test_score_widget_has_text_color(self):
        stmts = load_widget("score", search_paths=[BUNDLED_DIR])
        sets = [s for s in stmts if isinstance(s, SetStatement)]
        tc = [s for s in sets if s.target == "score.display.text_color"]
        assert len(tc) >= 1

    def test_score_config_font_size(self):
        stmts = load_widget("score", config={"font_size": "20px"}, search_paths=[BUNDLED_DIR])
        sets = [s for s in stmts if isinstance(s, SetStatement)]
        fs = [s for s in sets if s.target == "score.display.font_size"]
        assert fs[-1].value == "20px"


class TestHUDAnchorTheme:
    """Test the HUD anchor, theme, and stacking system."""

    def test_anchor_top_left(self):
        from rosh_lang.core.widgets import compute_hud_position, reset_hud_stack
        reset_hud_stack()
        x, y, bg, tc, fs = compute_hud_position({"anchor": "top-left"})
        assert x == "0.02"
        assert y == "0.02"

    def test_anchor_top_right(self):
        from rosh_lang.core.widgets import compute_hud_position, reset_hud_stack
        reset_hud_stack()
        x, y, _, _, _ = compute_hud_position({"anchor": "top-right"})
        assert x == "0.78"
        assert y == "0.02"

    def test_anchor_bottom_left(self):
        from rosh_lang.core.widgets import compute_hud_position, reset_hud_stack
        reset_hud_stack()
        x, y, _, _, _ = compute_hud_position({"anchor": "bottom-left"})
        assert x == "0.02"
        assert y == "0.90"

    def test_stacking_top_left(self):
        from rosh_lang.core.widgets import compute_hud_position, reset_hud_stack
        reset_hud_stack()
        _, y1, _, _, _ = compute_hud_position({"anchor": "top-left"})
        _, y2, _, _, _ = compute_hud_position({"anchor": "top-left"})
        _, y3, _, _, _ = compute_hud_position({"anchor": "top-left"})
        # Each subsequent item should be lower (top anchors stack downward)
        assert float(y1) < float(y2) < float(y3)

    def test_stacking_bottom_right(self):
        from rosh_lang.core.widgets import compute_hud_position, reset_hud_stack
        reset_hud_stack()
        _, y1, _, _, _ = compute_hud_position({"anchor": "bottom-right"})
        _, y2, _, _, _ = compute_hud_position({"anchor": "bottom-right"})
        # Each subsequent item should be higher (bottom anchors stack upward)
        assert float(y1) > float(y2)

    def test_theme_dark(self):
        from rosh_lang.core.widgets import compute_hud_position, reset_hud_stack
        reset_hud_stack()
        _, _, bg, tc, _ = compute_hud_position({"theme": "dark"})
        assert bg == "#333"
        assert tc == "#fff"

    def test_theme_retro(self):
        from rosh_lang.core.widgets import compute_hud_position, reset_hud_stack
        reset_hud_stack()
        _, _, bg, tc, _ = compute_hud_position({"theme": "retro"})
        assert bg == "#001100"
        assert tc == "#0f0"

    def test_theme_minimal(self):
        from rosh_lang.core.widgets import compute_hud_position, reset_hud_stack
        reset_hud_stack()
        _, _, bg, _, _ = compute_hud_position({"theme": "minimal"})
        assert bg == "transparent"

    def test_theme_with_override(self):
        from rosh_lang.core.widgets import compute_hud_position, reset_hud_stack
        reset_hud_stack()
        _, _, bg, tc, _ = compute_hud_position({"theme": "dark", "bg": "#ff0000"})
        assert bg == "#ff0000"  # explicit override wins
        assert tc == "#fff"     # theme default still applies

    def test_no_anchor_backward_compatible(self):
        from rosh_lang.core.widgets import compute_hud_position, reset_hud_stack
        reset_hud_stack()
        x, y, _, _, _ = compute_hud_position({"x": "0.5", "y": "0.9"})
        assert x == "0.5"
        assert y == "0.9"

    def test_score_with_anchor(self):
        from rosh_lang.core.widgets import reset_hud_stack
        reset_hud_stack()
        stmts = load_widget("score", config={"anchor": "top-right"}, search_paths=[BUNDLED_DIR])
        sets = [s for s in stmts if isinstance(s, SetStatement)]
        x_set = [s for s in sets if s.target == "score.display.x"]
        assert x_set[-1].value == "0.78"

    def test_lives_with_theme(self):
        from rosh_lang.core.widgets import reset_hud_stack
        reset_hud_stack()
        stmts = load_widget("lives", config={"theme": "retro"}, search_paths=[BUNDLED_DIR])
        sets = [s for s in stmts if isinstance(s, SetStatement)]
        bg_set = [s for s in sets if s.target == "lives.display.color"]
        assert bg_set[-1].value == "#001100"

    def test_score_custom_label(self):
        from rosh_lang.core.widgets import reset_hud_stack
        reset_hud_stack()
        stmts = load_widget("score", config={"label": "Points:"}, search_paths=[BUNDLED_DIR])
        sets = [s for s in stmts if isinstance(s, SetStatement)]
        label_set = [s for s in sets if s.target == "score.display.label"]
        assert "Points:" in label_set[0].value
