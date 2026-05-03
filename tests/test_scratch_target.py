"""Tests for the Scratch target."""

from __future__ import annotations

import json
import zipfile
from io import BytesIO
from pathlib import Path

from rosh_lang.parser import parse_file, parse_string
from rosh_lang.targets.scratch import build_scratch_project, render_scratch_sb3

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def _project_from_sb3(data: bytes) -> tuple[dict, list[str]]:
    with zipfile.ZipFile(BytesIO(data)) as zf:
        names = zf.namelist()
        return json.loads(zf.read("project.json")), names


def _opcodes(target: dict) -> list[str]:
    return [block["opcode"] for block in target["blocks"].values()]


def _assert_block_graph_valid(project: dict) -> None:
    for target in project["targets"]:
        blocks = target["blocks"]
        for block_id, block in blocks.items():
            next_id = block.get("next")
            if next_id is not None:
                assert next_id in blocks, f"{target['name']} block {block_id} has missing next {next_id}"
                assert blocks[next_id]["parent"] == block_id
            parent_id = block.get("parent")
            if parent_id is not None:
                assert parent_id in blocks, f"{target['name']} block {block_id} has missing parent {parent_id}"
            for input_value in block.get("inputs", {}).values():
                _assert_input_references_exist(target["name"], block_id, input_value, blocks)


def _assert_input_references_exist(
    target_name: str,
    block_id: str,
    input_value: object,
    blocks: dict,
) -> None:
    if not isinstance(input_value, list):
        return
    for part in input_value[1:]:
        if isinstance(part, str):
            assert part in blocks, f"{target_name} block {block_id} references missing input {part}"
            assert blocks[part]["parent"] == block_id
        elif isinstance(part, list) and part and part[0] in {1, 2, 3}:
            _assert_input_references_exist(target_name, block_id, part, blocks)


def test_render_scratch_sb3_creates_zip_with_project_and_assets():
    programme = parse_string(
        'background "sky blue"\n'
        "create object ball\n"
        "set ball.shape to circle\n"
        "set ball.color to red\n"
        "set ball.x to 0.5\n"
        "set ball.y to 0.5\n"
    )

    project, names = _project_from_sb3(render_scratch_sb3(programme))

    assert "project.json" in names
    assert any(name.endswith(".svg") for name in names)
    assert project["targets"][0]["isStage"] is True
    sprite = next(t for t in project["targets"] if t["name"] == "ball")
    assert sprite["x"] == 0
    assert sprite["y"] == 0
    assert sprite["size"] == 100
    assert sprite["costumes"][0]["dataFormat"] == "svg"
    opcodes = _opcodes(sprite)
    assert "event_whenflagclicked" in opcodes
    assert "motion_setx" in opcodes
    assert "motion_sety" in opcodes


def test_render_scratch_sample_has_valid_block_graph():
    programme = parse_file(EXAMPLES / "scratch-ball.rosh")

    project, _names = _project_from_sb3(render_scratch_sb3(programme))

    _assert_block_graph_valid(project)


def test_build_scratch_project_compiles_start_set_to_green_flag_blocks():
    programme = parse_string(
        "create object ball\n"
        "set ball.x to 0.2\n"
        "when start\n"
        "  set ball.x to 0.8\n"
        "  set ball.y to 0.25\n"
        "end\n"
    )

    project, _assets = build_scratch_project(programme)

    sprite = next(t for t in project["targets"] if t["name"] == "ball")
    opcodes = _opcodes(sprite)
    assert "event_whenflagclicked" in opcodes
    assert "motion_setx" in opcodes
    assert "motion_sety" in opcodes


def test_build_scratch_project_compiles_start_say_to_first_sprite_script():
    programme = parse_string(
        "create object ball\n"
        "set ball.shape to circle\n"
        "set ball.color to red\n"
        'when start\n'
        '  say "hello Scratch"\n'
        "end\n"
    )

    project, _assets = build_scratch_project(programme)

    sprite = next(t for t in project["targets"] if t["name"] == "ball")
    opcodes = _opcodes(sprite)
    assert "event_whenflagclicked" in opcodes
    assert "looks_say" in opcodes


def test_build_scratch_project_compiles_start_say_to_stage_when_no_sprite():
    programme = parse_string(
        'when start\n'
        '  say "hello Scratch"\n'
        "end\n"
    )

    project, _assets = build_scratch_project(programme)

    stage = project["targets"][0]
    opcodes = _opcodes(stage)
    assert "event_whenflagclicked" in opcodes
    assert "looks_say" in opcodes


def test_build_scratch_project_compiles_click_sprite_handler():
    programme = parse_string(
        "create object ball\n"
        "set ball.shape to circle\n"
        "set ball.color to red\n"
        "when click ball\n"
        '  say "clicked"\n'
        "end\n"
    )

    project, _assets = build_scratch_project(programme)

    sprite = next(t for t in project["targets"] if t["name"] == "ball")
    opcodes = _opcodes(sprite)
    assert "event_whenthisspriteclicked" in opcodes
    assert "looks_say" in opcodes


def test_build_scratch_project_compiles_stage_click_handler():
    programme = parse_string(
        "when click\n"
        '  say "stage clicked"\n'
        "end\n"
    )

    project, _assets = build_scratch_project(programme)

    stage = project["targets"][0]
    opcodes = _opcodes(stage)
    assert "event_whenstageclicked" in opcodes
    assert "looks_say" in opcodes


def test_build_scratch_project_compiles_keydown_handler_to_key_hat():
    programme = parse_string(
        "create object ball\n"
        "set ball.shape to circle\n"
        "set ball.color to red\n"
        "when keydown space\n"
        '  say "jump"\n'
        "end\n"
    )

    project, _assets = build_scratch_project(programme)

    sprite = next(t for t in project["targets"] if t["name"] == "ball")
    blocks = sprite["blocks"]
    key_hats = [
        block for block in blocks.values()
        if block["opcode"] == "event_whenkeypressed"
    ]
    assert len(key_hats) == 1
    assert key_hats[0]["fields"]["KEY_OPTION"] == ["space", None]
    assert "looks_say" in _opcodes(sprite)


def test_build_scratch_project_expands_controller_to_key_movement_blocks():
    programme = parse_string(
        "create object ship\n"
        'sprite ship "green spaceship"\n'
        "set ship.x to center\n"
        "use controller target ship keys both speed 0.03 move x help off\n"
    )

    project, _assets = build_scratch_project(programme)

    ship = next(t for t in project["targets"] if t["name"] == "ship")
    blocks = ship["blocks"]
    key_options = [
        block["fields"]["KEY_OPTION"][0]
        for block in blocks.values()
        if block["opcode"] == "event_whenkeypressed"
    ]
    assert "left arrow" in key_options
    assert "right arrow" in key_options
    assert "a" in key_options
    assert "d" in key_options
    assert "motion_changexby" in _opcodes(ship)


def test_build_scratch_project_compiles_relative_motion_to_change_blocks():
    programme = parse_string(
        "create object ball\n"
        "set ball.shape to circle\n"
        "set ball.color to red\n"
        "when keydown ArrowRight\n"
        "  set ball.x to ball.x + 0.1\n"
        "  set ball.y to ball.y - 0.1\n"
        "end\n"
    )

    project, _assets = build_scratch_project(programme)

    sprite = next(t for t in project["targets"] if t["name"] == "ball")
    opcodes = _opcodes(sprite)
    assert "motion_changexby" in opcodes
    assert "motion_changeyby" in opcodes


def test_build_scratch_project_compiles_update_handler_to_forever_loop():
    programme = parse_string(
        "create object ball\n"
        "set ball.shape to circle\n"
        "when update\n"
        "  set ball.x to ball.x + 0.01\n"
        "  set ball.size to ball.size + 0.01\n"
        "end\n"
    )

    project, _assets = build_scratch_project(programme)

    _assert_block_graph_valid(project)
    ball = next(t for t in project["targets"] if t["name"] == "ball")
    opcodes = _opcodes(ball)
    assert "event_whenflagclicked" in opcodes
    assert "control_forever" in opcodes
    assert "motion_changexby" in opcodes
    assert "looks_changesizeby" in opcodes


def test_build_scratch_project_compiles_repeat_to_repeat_block():
    programme = parse_string(
        "create object ball\n"
        "set ball.shape to circle\n"
        "when click ball\n"
        "  repeat 3\n"
        "    set ball.x to ball.x + 0.01\n"
        "  end\n"
        "end\n"
    )

    project, _assets = build_scratch_project(programme)

    ball = next(t for t in project["targets"] if t["name"] == "ball")
    opcodes = _opcodes(ball)
    assert "event_whenthisspriteclicked" in opcodes
    assert "control_repeat" in opcodes
    assert "motion_changexby" in opcodes


def test_build_scratch_project_compiles_variable_count_repeat():
    programme = parse_string(
        "create number turns\n"
        "set turns to 3\n"
        "create object ball\n"
        "set ball.shape to circle\n"
        "when click ball\n"
        "  repeat turns\n"
        "    set ball.x to ball.x + 0.01\n"
        "  end\n"
        "end\n"
    )

    project, _assets = build_scratch_project(programme)

    ball = next(t for t in project["targets"] if t["name"] == "ball")
    opcodes = _opcodes(ball)
    assert "control_repeat" in opcodes
    assert "data_variable" in opcodes
    assert "motion_changexby" in opcodes


def test_build_scratch_project_compiles_define_do_to_custom_blocks():
    programme = parse_string(
        "create object ball\n"
        "set ball.shape to circle\n"
        "define jump\n"
        "  set ball.y to ball.y - 0.1\n"
        "end\n"
        "when click ball\n"
        "  do jump\n"
        "end\n"
    )

    project, _assets = build_scratch_project(programme)

    ball = next(t for t in project["targets"] if t["name"] == "ball")
    opcodes = _opcodes(ball)
    assert "procedures_definition" in opcodes
    assert "procedures_prototype" in opcodes
    assert "procedures_call" in opcodes
    assert "motion_changeyby" in opcodes


def test_build_scratch_project_compiles_simple_condition_to_if_block():
    programme = parse_string(
        "create object ball\n"
        "set ball.shape to circle\n"
        "when update\n"
        "  if ball.x > 0.8\n"
        "    set ball.x to left\n"
        "  end\n"
        "end\n"
    )

    project, _assets = build_scratch_project(programme)

    ball = next(t for t in project["targets"] if t["name"] == "ball")
    opcodes = _opcodes(ball)
    assert "control_forever" in opcodes
    assert "control_if" in opcodes
    assert "operator_gt" in opcodes
    assert "motion_xposition" in opcodes
    assert "motion_setx" in opcodes


def test_build_scratch_project_compiles_negated_condition_operators():
    programme = parse_string(
        "create number score\n"
        "set score to 0\n"
        "create object ball\n"
        "set ball.shape to circle\n"
        "when update\n"
        "  if ball.x >= 0.8\n"
        "    set ball.x to left\n"
        "  end\n"
        "  if ball.y <= 0.2\n"
        "    set ball.y to bottom\n"
        "  end\n"
        "  if score != 0\n"
        '    say "score"\n'
        "  end\n"
        "end\n"
    )

    project, _assets = build_scratch_project(programme)

    _assert_block_graph_valid(project)
    ball = next(t for t in project["targets"] if t["name"] == "ball")
    opcodes = _opcodes(ball)
    assert opcodes.count("operator_not") == 3
    assert "operator_lt" in opcodes
    assert "operator_gt" in opcodes
    assert "operator_equals" in opcodes
    assert "data_variable" in opcodes


def test_build_scratch_project_compiles_variables_to_scratch_data_blocks():
    programme = parse_string(
        "create number score\n"
        "set score to 0\n"
        "create object ball\n"
        "set ball.shape to circle\n"
        "when click ball\n"
        "  set score to score + 1\n"
        "end\n"
        "when update\n"
        "  if score > 4\n"
        '    say "winner"\n'
        "  end\n"
        "end\n"
    )

    project, _assets = build_scratch_project(programme)

    stage = project["targets"][0]
    variable_names = [value[0] for value in stage["variables"].values()]
    assert "score" in variable_names
    monitor_names = [monitor["params"]["VARIABLE"] for monitor in project["monitors"]]
    assert "score" in monitor_names
    ball = next(t for t in project["targets"] if t["name"] == "ball")
    opcodes = _opcodes(ball)
    assert "data_changevariableby" in opcodes
    assert "data_variable" in opcodes
    assert "operator_gt" in opcodes
    assert "looks_say" in opcodes


def test_build_scratch_project_exposes_visual_widget_scalars_as_variables():
    programme = parse_string(
        "use score label Score:\n"
        "create object ball\n"
        "set ball.shape to circle\n"
        "when click ball\n"
        "  set score.value to score.value + 1\n"
        "end\n"
        "when update\n"
        "  if score.value >= 5\n"
        "    set ball.ghost to 20\n"
        "  end\n"
        "end\n"
    )

    project, _assets = build_scratch_project(programme)

    stage = project["targets"][0]
    variable_names = [value[0] for value in stage["variables"].values()]
    assert "score.value" in variable_names
    assert "controller.speed" not in variable_names
    monitor_names = [monitor["params"]["VARIABLE"] for monitor in project["monitors"]]
    assert "score.value" in monitor_names
    ball = next(t for t in project["targets"] if t["name"] == "ball")
    opcodes = _opcodes(ball)
    assert "data_changevariableby" in opcodes
    assert "data_variable" in opcodes
    assert "operator_not" in opcodes
    assert "operator_lt" in opcodes


def test_build_scratch_project_compiles_lives_and_coin_components():
    programme = parse_string(
        "use lives count 3\n"
        "use coin x 0.7 y 0.2\n"
        "create object player\n"
        "set player.shape to circle\n"
        "when collision player coin.gem\n"
        "  set lives.count to lives.count - 1\n"
        "  destroy coin.gem\n"
        "end\n"
    )

    project, _assets = build_scratch_project(programme)

    target_names = [target["name"] for target in project["targets"]]
    assert "lives display" in target_names
    assert "coin gem" in target_names
    stage = project["targets"][0]
    variable_names = [value[0] for value in stage["variables"].values()]
    assert "lives.count" in variable_names
    player = next(t for t in project["targets"] if t["name"] == "player")
    coin = next(t for t in project["targets"] if t["name"] == "coin gem")
    assert "data_changevariableby" in _opcodes(player)
    assert "looks_hide" in _opcodes(coin)


def test_build_scratch_project_compiles_scratch_native_motion_extras():
    programme = parse_string(
        "create object ball\n"
        "set ball.shape to circle\n"
        "when click ball\n"
        "  set ball.direction to ball.direction + 15\n"
        "  set ball.rotation to ball.rotation - 10\n"
        "  set ball.go_to to mouse-pointer\n"
        "  set ball.point_towards to mouse-pointer\n"
        "end\n"
    )

    project, _assets = build_scratch_project(programme)

    _assert_block_graph_valid(project)
    ball = next(t for t in project["targets"] if t["name"] == "ball")
    opcodes = _opcodes(ball)
    assert "motion_turnright" in opcodes
    assert "motion_turnleft" in opcodes
    assert "motion_goto" in opcodes
    assert "motion_goto_menu" in opcodes
    assert "motion_pointtowards" in opcodes
    assert "motion_pointtowards_menu" in opcodes


def test_build_scratch_project_compiles_custom_events_to_broadcast_blocks():
    programme = parse_string(
        "create object ball\n"
        "set ball.shape to circle\n"
        "when click ball\n"
        "  send shoot\n"
        "end\n"
        "when shoot\n"
        '  say "bang"\n'
        "end\n"
    )

    project, _assets = build_scratch_project(programme)

    stage = project["targets"][0]
    assert "shoot" in stage["broadcasts"].values()
    ball = next(t for t in project["targets"] if t["name"] == "ball")
    opcodes = _opcodes(ball)
    assert "event_broadcast" in opcodes
    assert "event_broadcast_menu" in opcodes
    assert "event_whenbroadcastreceived" in opcodes
    assert "looks_say" in opcodes


def test_build_scratch_project_compiles_controller_fire_to_key_broadcast():
    programme = parse_string(
        "create object ship\n"
        'sprite ship "green spaceship"\n'
        "use controller target ship keys arrows speed 0.03 move x fire on fire_event shoot\n"
        "when shoot\n"
        '  say "pew"\n'
        "end\n"
    )

    project, _assets = build_scratch_project(programme)

    stage = project["targets"][0]
    assert "shoot" in stage["broadcasts"].values()
    ship = next(t for t in project["targets"] if t["name"] == "ship")
    key_options = [
        block["fields"]["KEY_OPTION"][0]
        for block in ship["blocks"].values()
        if block["opcode"] == "event_whenkeypressed"
    ]
    assert "space" in key_options
    opcodes = _opcodes(ship)
    assert "event_broadcast" in opcodes
    assert "event_whenbroadcastreceived" in opcodes


def test_build_scratch_project_compiles_after_to_wait_then_broadcast():
    programme = parse_string(
        "create object ball\n"
        "set ball.shape to circle\n"
        "when click ball\n"
        "  after 0.5 send scored\n"
        "end\n"
        "when scored\n"
        '  say "later"\n'
        "end\n"
    )

    project, _assets = build_scratch_project(programme)

    _assert_block_graph_valid(project)
    stage = project["targets"][0]
    assert "scored" in stage["broadcasts"].values()
    ball = next(t for t in project["targets"] if t["name"] == "ball")
    opcodes = _opcodes(ball)
    assert "control_wait" in opcodes
    assert "event_broadcast" in opcodes
    assert "event_whenbroadcastreceived" in opcodes


def test_build_scratch_project_compiles_visibility_and_destroy_to_hide_show():
    programme = parse_string(
        "create object ball\n"
        "set ball.shape to circle\n"
        "set ball.color to red\n"
        "when click ball\n"
        "  set ball.visible to false\n"
        "end\n"
        "when keydown space\n"
        "  set ball.visible to true\n"
        "  destroy ball\n"
        "end\n"
    )

    project, _assets = build_scratch_project(programme)

    sprite = next(t for t in project["targets"] if t["name"] == "ball")
    opcodes = _opcodes(sprite)
    assert "looks_hide" in opcodes
    assert "looks_show" in opcodes


def test_render_scratch_sb3_includes_generated_wav_for_play_sound():
    programme = parse_string(
        'sound pop "short pop"\n'
        "create object ball\n"
        "set ball.shape to circle\n"
        "set ball.color to red\n"
        "when click ball\n"
        "  play pop\n"
        "end\n"
    )

    project, names = _project_from_sb3(render_scratch_sb3(programme))

    assert any(name.endswith(".wav") for name in names)
    sprite = next(t for t in project["targets"] if t["name"] == "ball")
    assert sprite["sounds"][0]["name"] == "pop"
    opcodes = _opcodes(sprite)
    assert "sound_playuntildone" in opcodes
    assert "sound_sounds_menu" in opcodes


def test_build_scratch_project_compiles_play_modes_to_sound_blocks():
    programme = parse_string(
        'sound music "soft loop"\n'
        "create object ball\n"
        "set ball.shape to circle\n"
        "when click ball\n"
        "  play music loop\n"
        "end\n"
        "when keydown s\n"
        "  play music stop\n"
        "end\n"
    )

    project, _assets = build_scratch_project(programme)

    ball = next(t for t in project["targets"] if t["name"] == "ball")
    opcodes = _opcodes(ball)
    assert "sound_play" in opcodes
    assert "sound_stopallsounds" in opcodes
    assert "sound_sounds_menu" in opcodes


def test_build_scratch_project_compiles_collision_to_touching_loop():
    programme = parse_string(
        "create object player\n"
        "set player.shape to circle\n"
        "set player.color to blue\n"
        "create object gem\n"
        "set gem.shape to gem\n"
        "set gem.color to purple\n"
        "when collision player gem\n"
        '  say "collected"\n'
        "  destroy gem\n"
        "end\n"
    )

    project, _assets = build_scratch_project(programme)

    player = next(t for t in project["targets"] if t["name"] == "player")
    opcodes = _opcodes(player)
    assert "control_forever" in opcodes
    assert "control_if" in opcodes
    assert "sensing_touchingobject" in opcodes
    assert "sensing_touchingobjectmenu" in opcodes
    assert "looks_say" in opcodes


def test_build_scratch_project_compiles_direction_and_rotation_style():
    programme = parse_string(
        "create object ship\n"
        'sprite ship "green spaceship"\n'
        "set ship.direction to 45\n"
        'set ship.rotation_style to "left-right"\n'
    )

    project, _assets = build_scratch_project(programme)

    ship = next(t for t in project["targets"] if t["name"] == "ship")
    opcodes = _opcodes(ship)
    assert "motion_pointindirection" in opcodes
    assert "motion_setrotationstyle" in opcodes


def test_build_scratch_project_compiles_common_looks_sensing_and_sound_properties():
    programme = parse_string(
        "create object ball\n"
        "set ball.shape to circle\n"
        "set ball.layer to front\n"
        "set ball.draggable to true\n"
        "set ball.volume to 0.5\n"
        "when start\n"
        "  set ball.ghost to 40\n"
        "  set ball.brightness to 20\n"
        "  set ball.layer to back\n"
        "  set ball.draggable to false\n"
        "  set ball.volume to 75\n"
        "end\n"
    )

    project, _assets = build_scratch_project(programme)

    ball = next(t for t in project["targets"] if t["name"] == "ball")
    opcodes = _opcodes(ball)
    assert ball["draggable"] is True
    assert ball["volume"] == 50
    assert "looks_gotofrontback" in opcodes
    assert "sensing_setdragmode" in opcodes
    assert "sound_setvolumeto" in opcodes
    assert "looks_seteffectto" in opcodes


def test_build_scratch_project_compiles_named_positions_for_scratch():
    programme = parse_string(
        "create object ball\n"
        "set ball.shape to circle\n"
        "set ball.color to red\n"
        "set ball.x to left\n"
        "set ball.y to top\n"
    )

    project, _assets = build_scratch_project(programme)

    ball = next(t for t in project["targets"] if t["name"] == "ball")
    assert ball["x"] == -200
    assert ball["y"] == 140


def test_render_scratch_sb3_generates_richer_costume_svg_for_spaceship():
    programme = parse_string(
        "create object ship\n"
        'sprite ship "green spaceship"\n'
    )

    _project, names = _project_from_sb3(render_scratch_sb3(programme))

    with zipfile.ZipFile(BytesIO(render_scratch_sb3(programme))) as zf:
        svg_names = [name for name in names if name.endswith(".svg")]
        svg_text = "\n".join(zf.read(name).decode("utf-8") for name in svg_names)
    assert "polygon" in svg_text
    assert "circle" in svg_text
