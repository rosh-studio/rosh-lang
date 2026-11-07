"""Permissions as data (P-052 §8): the levels, the two presets, and what they allow."""

import pytest

from rosh_lang.core.policy import ACTIONS, LEVELS, PRESETS, allowed, level_named, threshold


def test_the_four_named_levels():
    assert LEVELS == {"look": 0, "build": 3, "edit": 5, "own": 9}
    assert level_named("edit") == 5


# The whole table, as P-052 §8.3 gives it. Changing a number here is changing
# who may do something in every room: it should be a decision, not a typo.
TABLE = {
    #  action               shared museum
    "build":              (3, 3),
    "create_visible":     (3, 9),
    "create_raw":         (3, 9),
    "edit_record":        (3, 9),
    "change_others":      (9, 9),
    "remove_room_things": (9, 9),
    "remove_locked":      (9, 9),
    "lock":               (9, 9),
    "appears_as":         (9, 9),
    "room_words":         (5, 5),
    "reset_room":         (9, 9),
    "save_code":          (5, 5),
}


def test_every_action_in_both_presets():
    assert set(ACTIONS) == set(TABLE)
    for action, (shared, museum) in TABLE.items():
        assert threshold(action) == shared, action
        assert threshold(action, {"rules": "shared"}) == shared, action
        assert threshold(action, {"rules": "museum"}) == museum, action


def test_a_level_passes_at_its_threshold_and_not_below():
    museum = {"rules": "museum"}
    assert allowed("create_visible", 9, museum)
    assert not allowed("create_visible", 8, museum)
    assert allowed("create_visible", 3)
    assert not allowed("build", 0)


def test_a_typo_is_an_error_not_a_default():
    with pytest.raises(KeyError):
        threshold("create_visibel")
    with pytest.raises(KeyError):
        threshold("build", {"rules": "musuem"})


def test_presets_are_complete():
    for rows in PRESETS.values():
        assert set(rows) == set(ACTIONS)


def test_a_room_changes_single_rows_but_never_below_a_floor():
    assert threshold("create_visible", {"rules": "shared", "rule": {"create_visible": 5}}) == 5
    assert threshold("build", {"rule": {"create_visible": 5}}) == 3
    assert threshold("lock", {"rule": {"lock": 0}}) == 5


def test_what_is_wrong_with_a_rule():
    from rosh_lang.core.policy import room_rule_problem
    assert room_rule_problem("rules", '"Museum"') is None
    assert room_rule_problem("rule.lock", "5") is None
    assert room_rule_problem("title", "anything") is None
    assert "no rules called" in room_rule_problem("rules", "musuem")
    assert "no action called" in room_rule_problem("rule.fly", "3")
    assert "from 0 to 9" in room_rule_problem("rule.build", "10")
    assert "below 5" in room_rule_problem("rule.remove_locked", "4")


def test_a_level_is_one_digit_however_it_is_written():
    from rosh_lang.core.policy import level_in
    assert [level_in(v) for v in ("5", "05", "0", "000", '"7"')] == [5, 5, 0, 0, 7]
    assert [level_in(v) for v in ("10", "²", "-1", "1" * 5000, "")] == [None] * 5
