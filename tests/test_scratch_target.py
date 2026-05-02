"""Tests for the Scratch target."""

from __future__ import annotations

import json
import zipfile
from io import BytesIO

from rosh_lang.parser import parse_string
from rosh_lang.targets.scratch import build_scratch_project, render_scratch_sb3


def _project_from_sb3(data: bytes) -> tuple[dict, list[str]]:
    with zipfile.ZipFile(BytesIO(data)) as zf:
        names = zf.namelist()
        return json.loads(zf.read("project.json")), names


def _opcodes(target: dict) -> list[str]:
    return [block["opcode"] for block in target["blocks"].values()]


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
