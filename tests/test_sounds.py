"""Tests for the procedural sound parameter generator."""

from __future__ import annotations

from rosh_lang.sounds import generate_sound_params


# ── Preset matching ──────────────────────────────────────────


class TestPresetMatching:
    """Description keywords should select the correct preset."""

    def test_laser_preset(self):
        params = generate_sound_params("zap", "laser blast")
        assert params["layers"][0]["waveform"] == "square"
        assert params["layers"][0]["frequency"] == 800

    def test_shoot_preset(self):
        params = generate_sound_params("gun", "shoot sound")
        assert params["layers"][0]["waveform"] == "square"

    def test_explosion_preset_has_two_layers(self):
        params = generate_sound_params("boom", "explosion")
        assert len(params["layers"]) == 2
        waveforms = {l["waveform"] for l in params["layers"]}
        assert "noise" in waveforms
        assert "sine" in waveforms

    def test_coin_preset(self):
        params = generate_sound_params("ding", "coin collect")
        assert params["layers"][0]["waveform"] == "triangle"
        assert params["layers"][0]["frequency"] == 987

    def test_jump_preset(self):
        params = generate_sound_params("hop", "jump sound")
        assert params["layers"][0]["waveform"] == "sine"
        assert params["layers"][0]["sweep"] > 0  # up-sweep

    def test_hit_preset(self):
        params = generate_sound_params("ouch", "hit damage")
        assert params["layers"][0]["waveform"] == "square"
        assert params["layers"][0]["duration"] == 0.08

    def test_powerup_preset(self):
        params = generate_sound_params("up", "powerup")
        assert params["layers"][0]["waveform"] == "triangle"
        assert params["layers"][0]["sweep"] > 0

    def test_gameover_preset(self):
        params = generate_sound_params("end", "gameover")
        assert params["layers"][0]["waveform"] == "sine"
        assert params["layers"][0]["sweep"] < 0  # down-sweep

    def test_click_preset(self):
        params = generate_sound_params("btn", "click")
        assert params["layers"][0]["waveform"] == "sine"
        assert params["layers"][0]["duration"] == 0.05

    def test_win_preset(self):
        params = generate_sound_params("yay", "victory win")
        assert params["layers"][0]["waveform"] == "triangle"
        assert params["layers"][0]["sweep"] > 0

    def test_case_insensitive(self):
        params = generate_sound_params("zap", "LASER blast")
        assert params["layers"][0]["waveform"] == "square"

    def test_hyphenated_keyword(self):
        """game-over should match gameover preset."""
        params = generate_sound_params("end", "game-over")
        assert params["layers"][0]["waveform"] == "sine"
        assert params["layers"][0]["sweep"] < 0

    def test_underscored_keyword(self):
        """level_up should match levelup preset."""
        params = generate_sound_params("up", "level_up sound")
        assert params["layers"][0]["waveform"] == "triangle"

    def test_catch_matches_coin(self):
        """'catch' keyword → coin family."""
        params = generate_sound_params("grab", "catch sound")
        assert params["layers"][0]["waveform"] == "triangle"
        assert params["layers"][0]["frequency"] == 987


# ── Determinism ──────────────────────────────────────────────


class TestDeterminism:
    """Same name should always produce the same parameters."""

    def test_same_name_same_output(self):
        a = generate_sound_params("laser", "laser blast")
        b = generate_sound_params("laser", "laser blast")
        assert a == b

    def test_fallback_deterministic(self):
        """Unknown descriptions use hash-based fallback — still deterministic."""
        a = generate_sound_params("mystery", "something unknown")
        b = generate_sound_params("mystery", "something unknown")
        assert a == b

    def test_different_names_different_fallback(self):
        """Different names produce different fallback params."""
        a = generate_sound_params("sound_a", "something")
        b = generate_sound_params("sound_b", "something")
        assert a != b


# ── Parameter validation ────────────────────────────────────


class TestParameterValidation:
    """All generated params should have valid structure and ranges."""

    def test_has_layers_key(self):
        params = generate_sound_params("test", "laser")
        assert "layers" in params
        assert isinstance(params["layers"], list)
        assert len(params["layers"]) >= 1

    def test_layer_has_required_keys(self):
        required = {"waveform", "frequency", "duration", "attack", "decay", "volume", "sweep", "sweep_time"}
        params = generate_sound_params("test", "laser")
        for layer in params["layers"]:
            assert required <= set(layer.keys()), f"Missing keys: {required - set(layer.keys())}"

    def test_valid_waveform(self):
        valid = {"sine", "square", "sawtooth", "triangle", "noise"}
        for desc in ["laser", "explosion", "coin", "jump", "hit", "powerup", "gameover", "click", "victory"]:
            params = generate_sound_params(f"test_{desc}", desc)
            for layer in params["layers"]:
                assert layer["waveform"] in valid, f"Invalid waveform {layer['waveform']} for {desc}"

    def test_duration_positive(self):
        params = generate_sound_params("test", "laser")
        for layer in params["layers"]:
            assert layer["duration"] > 0

    def test_volume_range(self):
        params = generate_sound_params("test", "laser")
        for layer in params["layers"]:
            assert 0 < layer["volume"] <= 1.0

    def test_attack_less_than_duration(self):
        params = generate_sound_params("test", "laser")
        for layer in params["layers"]:
            assert layer["attack"] < layer["duration"]

    def test_fallback_valid_waveform(self):
        """Fallback params should use standard oscillator waveforms (not noise)."""
        valid = {"sine", "square", "sawtooth", "triangle"}
        params = generate_sound_params("unknown", "something unmatched")
        for layer in params["layers"]:
            assert layer["waveform"] in valid

    def test_fallback_frequency_in_range(self):
        params = generate_sound_params("unknown", "something unmatched")
        for layer in params["layers"]:
            assert 200 <= layer["frequency"] <= 1200

    def test_fallback_duration_in_range(self):
        params = generate_sound_params("unknown", "something unmatched")
        for layer in params["layers"]:
            assert 0.1 <= layer["duration"] <= 0.4

    def test_all_presets_produce_valid_params(self):
        """Every preset keyword should produce valid params."""
        all_keywords = [
            "laser", "shoot", "zap", "beam",
            "explosion", "boom", "blast", "explode",
            "coin", "collect", "pickup", "catch", "gem",
            "jump", "bounce", "hop",
            "hit", "damage", "hurt", "ouch",
            "powerup", "upgrade", "levelup",
            "gameover", "lose", "fail", "death",
            "click", "select", "menu", "tap",
            "win", "victory", "success",
        ]
        for kw in all_keywords:
            params = generate_sound_params(f"test_{kw}", kw)
            assert "layers" in params
            assert len(params["layers"]) >= 1
            for layer in params["layers"]:
                assert layer["duration"] > 0
                assert layer["volume"] > 0


# ── Empty description ────────────────────────────────────────


class TestEmptyDescription:
    """Empty or missing descriptions should use fallback."""

    def test_empty_description(self):
        params = generate_sound_params("test")
        assert "layers" in params
        assert len(params["layers"]) == 1

    def test_empty_string_description(self):
        params = generate_sound_params("test", "")
        assert "layers" in params
