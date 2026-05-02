"""Scratch target - compile a Rosh programme to a Scratch 3 .sb3 file.

This is the first conservative slice of the Rosh -> Scratch compiler. It
exports visible Rosh objects as Scratch sprites, stage background as a backdrop,
and simple green-flag scripts for start handlers.
"""

from __future__ import annotations

import hashlib
import io
import json
import math
import re
import struct
import wave
import zipfile
from dataclasses import dataclass, field
from html import escape
from typing import Any

from rosh_lang import __version__
from rosh_lang.model import (
    BackgroundStatement,
    DestroyStatement,
    EndStatement,
    PrintStatement,
    Programme,
    PlayStatement,
    SayStatement,
    SetStatement,
    SoundStatement,
    Statement,
    WhenStatement,
)
from rosh_lang.runtime import Runtime
from rosh_lang.targets.web import _collect_objects

STAGE_WIDTH = 480
STAGE_HEIGHT = 360

_COLOR_WORDS = {
    "black": "#111111",
    "blue": "#3366ff",
    "brown": "#8b5a2b",
    "cyan": "#22d3ee",
    "gray": "#888888",
    "grey": "#888888",
    "green": "#22c55e",
    "orange": "#ff8a33",
    "pink": "#ff66aa",
    "purple": "#8b5cf6",
    "red": "#ef4444",
    "white": "#ffffff",
    "yellow": "#facc15",
}


@dataclass
class _Asset:
    name: str
    data: bytes
    data_format: str = "svg"

    @property
    def asset_id(self) -> str:
        return hashlib.md5(self.data).hexdigest()

    @property
    def md5ext(self) -> str:
        return f"{self.asset_id}.{self.data_format}"


@dataclass
class _SpriteBuild:
    target: dict[str, Any]
    asset: _Asset
    setup_steps: list[Statement] = field(default_factory=list)


def render_scratch_sb3(
    programme: Programme,
    search_paths: list[Any] | None = None,
) -> bytes:
    """Compile a Rosh programme to Scratch 3 .sb3 bytes."""
    project, assets = build_scratch_project(programme, search_paths=search_paths)
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("project.json", json.dumps(project, separators=(",", ":")))
        for asset in assets:
            zf.writestr(asset.md5ext, asset.data)
    return payload.getvalue()


def build_scratch_project(
    programme: Programme,
    search_paths: list[Any] | None = None,
) -> tuple[dict[str, Any], list[_Asset]]:
    """Build the Scratch project.json structure and SVG assets."""
    top_level, start_body, click_handlers, key_handlers = _split_event_bodies(programme.statements)
    rt = Runtime(output=io.StringIO(), search_paths=search_paths)
    rt.run(Programme(statements=top_level, source=programme.source))

    background = _find_background(top_level) or rt.state.get("_background", "#ffffff")
    backdrop_asset = _Asset("backdrop", _stage_svg(str(background)))
    assets: list[_Asset] = [backdrop_asset]
    sound_assets = _collect_sound_assets(programme.statements)
    assets.extend(sound_assets.values())
    sound_infos = [_sound_info(asset) for asset in sound_assets.values()]
    targets: list[dict[str, Any]] = [_stage_target(backdrop_asset, sound_infos)]

    object_items = _collect_objects(rt.state)
    top_level_setup = _top_level_sprite_setup(top_level)
    sprite_builds: dict[str, _SpriteBuild] = {}
    for index, (name, obj) in enumerate(object_items, start=1):
        asset = _Asset(name, _sprite_svg(name, obj))
        target = _sprite_target(name, obj, asset, index, sound_infos)
        sprite_builds[name] = _SpriteBuild(
            target=target,
            asset=asset,
            setup_steps=top_level_setup.get(name, []),
        )
        assets.append(asset)

    _attach_start_scripts(start_body, sprite_builds, targets[0])
    _attach_click_scripts(click_handlers, sprite_builds, targets[0])
    _attach_key_scripts(key_handlers, sprite_builds, targets[0])
    targets.extend(build.target for build in sprite_builds.values())

    return {
        "targets": targets,
        "monitors": [],
        "extensions": [],
        "meta": {
            "semver": "3.0.0",
            "vm": "0.2.0",
            "agent": f"Rosh {__version__}",
        },
    }, assets


def _split_event_bodies(
    statements: list[Statement],
) -> tuple[
    list[Statement],
    list[Statement],
    list[tuple[str, list[Statement]]],
    list[tuple[str, list[Statement]]],
]:
    top_level: list[Statement] = []
    start_body: list[Statement] = []
    click_handlers: list[tuple[str, list[Statement]]] = []
    key_handlers: list[tuple[str, list[Statement]]] = []
    i = 0
    while i < len(statements):
        stmt = statements[i]
        if isinstance(stmt, WhenStatement):
            body: list[Statement] = []
            i += 1
            while i < len(statements) and not isinstance(statements[i], EndStatement):
                body.append(statements[i])
                i += 1
            i += 1
            if stmt.event == "start":
                start_body.extend(body)
            elif stmt.event == "click":
                target = stmt.args[0] if stmt.args else ""
                click_handlers.append((target, body))
            elif stmt.event == "keydown":
                key = stmt.args[0] if stmt.args else "space"
                key_handlers.append((key, body))
            continue
        top_level.append(stmt)
        i += 1
    return top_level, start_body, click_handlers, key_handlers


def _find_background(statements: list[Statement]) -> str:
    for stmt in statements:
        if isinstance(stmt, BackgroundStatement):
            return stmt.value
    return ""


def _top_level_sprite_setup(statements: list[Statement]) -> dict[str, list[Statement]]:
    setup: dict[str, list[Statement]] = {}
    for stmt in statements:
        if isinstance(stmt, SetStatement) and "." in stmt.target:
            owner = stmt.target.split(".", 1)[0]
            setup.setdefault(owner, []).append(stmt)
    return setup


def _stage_target(asset: _Asset, sounds: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "isStage": True,
        "name": "Stage",
        "variables": {},
        "lists": {},
        "broadcasts": {},
        "blocks": {},
        "comments": {},
        "currentCostume": 0,
        "costumes": [_costume(asset.name, asset, STAGE_WIDTH / 2, STAGE_HEIGHT / 2)],
        "sounds": sounds,
        "volume": 100,
        "layerOrder": 0,
        "tempo": 60,
        "videoTransparency": 50,
        "videoState": "on",
        "textToSpeechLanguage": None,
    }


def _sprite_target(
    name: str,
    obj: dict[str, Any],
    asset: _Asset,
    layer_order: int,
    sounds: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "isStage": False,
        "name": _scratch_name(name),
        "variables": {},
        "lists": {},
        "broadcasts": {},
        "blocks": {},
        "comments": {},
        "currentCostume": 0,
        "costumes": [_costume("costume1", asset, 50, 50)],
        "sounds": sounds,
        "volume": 100,
        "layerOrder": layer_order,
        "visible": bool(obj.get("visible", True)),
        "x": _scratch_x(obj.get("x", 0.5)),
        "y": _scratch_y(obj.get("y", 0.5)),
        "size": _scratch_size(obj),
        "direction": float(obj.get("direction", obj.get("rotation", 90))),
        "draggable": False,
        "rotationStyle": "all around",
    }


def _costume(name: str, asset: _Asset, cx: float, cy: float) -> dict[str, Any]:
    return {
        "name": name,
        "bitmapResolution": 1,
        "dataFormat": "svg",
        "assetId": asset.asset_id,
        "md5ext": asset.md5ext,
        "rotationCenterX": cx,
        "rotationCenterY": cy,
    }


def _attach_start_scripts(
    start_body: list[Statement],
    sprite_builds: dict[str, _SpriteBuild],
    stage_target: dict[str, Any],
) -> None:
    per_sprite: dict[str, list[Statement]] = {name: [] for name in sprite_builds}
    stage_steps: list[Statement] = []
    default_sprite = next(iter(sprite_builds), "")
    for stmt in start_body:
        if isinstance(stmt, SetStatement):
            owner = stmt.target.split(".", 1)[0]
            if owner in per_sprite:
                per_sprite[owner].append(stmt)
            else:
                stage_steps.append(stmt)
        elif isinstance(stmt, (PrintStatement, SayStatement)):
            if default_sprite:
                per_sprite[default_sprite].append(stmt)
            else:
                stage_steps.append(stmt)
        else:
            stage_steps.append(stmt)

    if stage_steps and not stage_target["blocks"]:
        stage_target["blocks"].update(_script_blocks(stage_steps, None, x=40, y=40))

    for name, steps in per_sprite.items():
        all_steps = sprite_builds[name].setup_steps + steps
        if not all_steps:
            continue
        sprite_builds[name].target["blocks"].update(
            _script_blocks(all_steps, name, x=40, y=40, script_key="start")
        )


def _attach_click_scripts(
    click_handlers: list[tuple[str, list[Statement]]],
    sprite_builds: dict[str, _SpriteBuild],
    stage_target: dict[str, Any],
) -> None:
    for index, (target, body) in enumerate(click_handlers):
        if target and target in sprite_builds:
            sprite_builds[target].target["blocks"].update(
                _script_blocks(
                    body,
                    target,
                    x=260,
                    y=40 + index * 140,
                    hat_opcode="event_whenthisspriteclicked",
                    script_key=f"click:{target}:{index}",
                )
            )
        elif not target:
            stage_target["blocks"].update(
                _script_blocks(
                    body,
                    None,
                    x=260,
                    y=40 + index * 140,
                    hat_opcode="event_whenstageclicked",
                    script_key=f"click:stage:{index}",
                )
            )


def _attach_key_scripts(
    key_handlers: list[tuple[str, list[Statement]]],
    sprite_builds: dict[str, _SpriteBuild],
    stage_target: dict[str, Any],
) -> None:
    default_sprite = next(iter(sprite_builds), "")
    for index, (key, body) in enumerate(key_handlers):
        owner = _infer_script_owner(body, sprite_builds, default_sprite)
        target = sprite_builds[owner].target if owner else stage_target
        target["blocks"].update(
            _script_blocks(
                body,
                owner or None,
                x=480,
                y=40 + index * 140,
                hat_opcode="event_whenkeypressed",
                hat_fields={"KEY_OPTION": [_scratch_key(key), None]},
                script_key=f"key:{key}:{index}",
            )
        )


def _infer_script_owner(
    body: list[Statement],
    sprite_builds: dict[str, _SpriteBuild],
    default_sprite: str,
) -> str:
    for stmt in body:
        if isinstance(stmt, SetStatement):
            owner = stmt.target.split(".", 1)[0]
            if owner in sprite_builds:
                return owner
        if isinstance(stmt, DestroyStatement) and stmt.name in sprite_builds:
            return stmt.name
    return default_sprite


def _script_blocks(
    statements: list[Statement],
    sprite_name: str | None,
    *,
    x: int,
    y: int,
    hat_opcode: str = "event_whenflagclicked",
    hat_fields: dict[str, Any] | None = None,
    script_key: str = "start",
) -> dict[str, dict[str, Any]]:
    actions: list[tuple[str, dict[str, Any]]] = []
    for stmt in statements:
        action = _statement_action(stmt, sprite_name)
        if action:
            actions.append(action)
    if not actions:
        return {}

    blocks: dict[str, dict[str, Any]] = {}
    owner = sprite_name or "stage"
    hat_id = _block_id(hat_opcode, owner, script_key, "hat")
    first_id = _block_id(actions[0][0], owner, script_key, "0")
    blocks[hat_id] = {
        "opcode": hat_opcode,
        "next": first_id,
        "parent": None,
        "inputs": {},
        "fields": hat_fields or {},
        "shadow": False,
        "topLevel": True,
        "x": x,
        "y": y,
    }

    previous_id = hat_id
    for index, (opcode, payload) in enumerate(actions):
        block_id = _block_id(opcode, owner, script_key, str(index))
        next_id = (
            _block_id(actions[index + 1][0], owner, script_key, str(index + 1))
            if index + 1 < len(actions) else None
        )
        blocks[block_id] = {
            "opcode": opcode,
            "next": next_id,
            "parent": previous_id,
            "inputs": payload.get("inputs", {}),
            "fields": payload.get("fields", {}),
            "shadow": False,
            "topLevel": False,
        }
        if "sound" in payload:
            menu_id = _block_id("sound_menu", owner, script_key, str(index))
            blocks[block_id]["inputs"] = {"SOUND_MENU": [1, menu_id]}
            blocks[menu_id] = {
                "opcode": "sound_sounds_menu",
                "next": None,
                "parent": block_id,
                "inputs": {},
                "fields": {"SOUND_MENU": [payload["sound"], None]},
                "shadow": True,
                "topLevel": False,
            }
        previous_id = block_id
    return blocks


def _statement_action(
    stmt: Statement,
    sprite_name: str | None,
) -> tuple[str, dict[str, Any]] | None:
    if isinstance(stmt, SetStatement) and sprite_name:
        prop = stmt.target.split(".", 1)[1] if "." in stmt.target else stmt.target
        value = _clean_literal(stmt.value)
        relative = _relative_change(stmt)
        if relative and relative[0] == "x":
            return "motion_changexby", {"inputs": {"DX": _number_input(relative[1])}}
        if relative and relative[0] == "y":
            return "motion_changeyby", {"inputs": {"DY": _number_input(relative[1])}}
        if relative and relative[0] == "size":
            return "looks_changesizeby", {"inputs": {"CHANGE": _number_input(relative[1])}}
        if prop == "x":
            return "motion_setx", {"inputs": {"X": _number_input(_scratch_x(value))}}
        if prop == "y":
            return "motion_sety", {"inputs": {"Y": _number_input(_scratch_y(value))}}
        if prop in ("size", "width", "height"):
            return "looks_setsizeto", {"inputs": {"SIZE": _number_input(_scratch_size_value(value))}}
        if prop == "visible":
            return ("looks_show" if str(value).lower() != "false" else "looks_hide"), {}
        if prop in ("color", "shape", "sprite"):
            return None
    if isinstance(stmt, SayStatement):
        return "looks_say", {"inputs": {"MESSAGE": _text_input(stmt.text)}}
    if isinstance(stmt, PrintStatement):
        return "looks_say", {"inputs": {"MESSAGE": _text_input(stmt.text)}}
    if isinstance(stmt, DestroyStatement) and sprite_name and stmt.name == sprite_name:
        return "looks_hide", {}
    if isinstance(stmt, PlayStatement):
        return "sound_playuntildone", {"sound": stmt.sound}
    return None


def _relative_change(stmt: SetStatement) -> tuple[str, float] | None:
    if "." not in stmt.target:
        return None
    prop = stmt.target.split(".", 1)[1]
    raw = stmt.value.strip()
    match = re.fullmatch(rf"{re.escape(stmt.target)}\s*([+\-])\s*(-?\d+(?:\.\d+)?)", raw)
    if not match:
        return None
    sign = 1 if match.group(1) == "+" else -1
    amount = sign * float(match.group(2))
    if prop == "x":
        return "x", _scratch_delta_x(amount)
    if prop == "y":
        return "y", _scratch_delta_y(amount)
    if prop in {"size", "width", "height"}:
        return "size", _scratch_delta_size(amount)
    return None


def _number_input(value: Any) -> list[Any]:
    return [1, [4, str(value)]]


def _text_input(value: str) -> list[Any]:
    return [1, [10, value]]


def _scratch_key(key: str) -> str:
    aliases = {
        " ": "space",
        "spacebar": "space",
        "arrowup": "up arrow",
        "up": "up arrow",
        "arrowdown": "down arrow",
        "down": "down arrow",
        "arrowleft": "left arrow",
        "left": "left arrow",
        "arrowright": "right arrow",
        "right": "right arrow",
        "enter": "enter",
        "return": "enter",
    }
    cleaned = key.strip().lower()
    return aliases.get(cleaned, cleaned)


def _block_id(*parts: str) -> str:
    raw = ":".join(parts)
    return "rosh_" + hashlib.md5(raw.encode("utf-8")).hexdigest()[:16]


def _scratch_name(name: str) -> str:
    cleaned = name.replace(".", " ")
    return cleaned[:100] or "Rosh Sprite"


def _scratch_x(value: Any) -> float:
    value = _to_float(value, 0.5)
    if 0 <= value <= 1:
        return round((value * STAGE_WIDTH) - (STAGE_WIDTH / 2), 3)
    return round(value, 3)


def _scratch_y(value: Any) -> float:
    value = _to_float(value, 0.5)
    if 0 <= value <= 1:
        return round((STAGE_HEIGHT / 2) - (value * STAGE_HEIGHT), 3)
    return round(value, 3)


def _scratch_delta_x(value: Any) -> float:
    value = _to_float(value, 0)
    if -1 <= value <= 1:
        return round(value * STAGE_WIDTH, 3)
    return round(value, 3)


def _scratch_delta_y(value: Any) -> float:
    value = _to_float(value, 0)
    if -1 <= value <= 1:
        return round(value * -STAGE_HEIGHT, 3)
    return round(value, 3)


def _scratch_size(obj: dict[str, Any]) -> float:
    if "size" in obj:
        return _scratch_size_value(obj["size"])
    width = _to_float(obj.get("width", 0.1), 0.1)
    height = _to_float(obj.get("height", 0.1), 0.1)
    return _scratch_size_value(max(width, height))


def _scratch_size_value(value: Any) -> float:
    value = _to_float(value, 100)
    if 0 < value <= 2:
        return round(value * 1000, 3)
    return round(value, 3)


def _scratch_delta_size(value: Any) -> float:
    value = _to_float(value, 0)
    if -2 <= value <= 2:
        return round(value * 1000, 3)
    return round(value, 3)


def _to_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clean_literal(value: str) -> str:
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    return value


def _stage_svg(background: str) -> bytes:
    fill = _color(background, "#ffffff")
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{STAGE_WIDTH}" '
        f'height="{STAGE_HEIGHT}" viewBox="0 0 {STAGE_WIDTH} {STAGE_HEIGHT}">'
        f'<rect width="{STAGE_WIDTH}" height="{STAGE_HEIGHT}" fill="{fill}"/>'
        "</svg>"
    )
    return svg.encode("utf-8")


def _collect_sound_assets(statements: list[Statement]) -> dict[str, _Asset]:
    assets: dict[str, _Asset] = {}
    for stmt in statements:
        if isinstance(stmt, SoundStatement) and stmt.name not in assets:
            assets[stmt.name] = _Asset(
                stmt.name,
                _sound_wav(stmt.name, stmt.description),
                data_format="wav",
            )
    return assets


def _sound_info(asset: _Asset) -> dict[str, Any]:
    return {
        "name": asset.name,
        "assetId": asset.asset_id,
        "dataFormat": "wav",
        "format": "",
        "rate": 44100,
        "sampleCount": 4410,
        "md5ext": asset.md5ext,
    }


def _sound_wav(name: str, description: str) -> bytes:
    """Generate a tiny mono WAV so exported Scratch projects have a real sound."""
    desc = f"{name} {description}".lower()
    freq = 660
    if any(word in desc for word in ("low", "boom", "explosion")):
        freq = 180
    elif any(word in desc for word in ("laser", "zap", "coin", "pop")):
        freq = 880

    rate = 44100
    duration = 0.1
    frames = int(rate * duration)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        for i in range(frames):
            t = i / rate
            envelope = max(0.0, 1.0 - (i / frames))
            sample = int(math.sin(2 * math.pi * freq * t) * envelope * 16000)
            wav.writeframesraw(struct.pack("<h", sample))
    return buf.getvalue()


def _sprite_svg(name: str, obj: dict[str, Any]) -> bytes:
    desc = str(obj.get("sprite", ""))
    shape = str(obj.get("shape", "") or _shape_from_description(desc)).lower()
    fill = _color(str(obj.get("color", "")) or _color_from_description(desc), "#ff8a33")
    label = escape(str(obj.get("label", "")))

    if shape in {"circle", "sphere", "ball", "orb"}:
        body = f'<circle cx="50" cy="50" r="36" fill="{fill}"/>'
    elif shape in {"triangle", "pyramid"}:
        body = f'<polygon points="50,12 88,86 12,86" fill="{fill}"/>'
    elif shape in {"star"}:
        body = f'<polygon points="50,9 61,37 91,37 67,56 76,88 50,70 24,88 33,56 9,37 39,37" fill="{fill}"/>'
    else:
        body = f'<rect x="14" y="18" width="72" height="64" rx="8" fill="{fill}"/>'

    text = ""
    if label:
        text = (
            '<text x="50" y="55" text-anchor="middle" '
            'font-family="Arial, sans-serif" font-size="14" fill="#111">'
            f"{label}</text>"
        )

    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" '
        'viewBox="0 0 100 100">'
        f"{body}{text}"
        f'<title>{escape(name)}</title>'
        "</svg>"
    )
    return svg.encode("utf-8")


def _color(value: str, default: str) -> str:
    raw = value.strip().strip('"').strip("'").lower()
    if raw in _COLOR_WORDS:
        return _COLOR_WORDS[raw]
    if re.fullmatch(r"#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?", raw):
        return raw
    return default


def _color_from_description(desc: str) -> str:
    words = re.findall(r"[a-zA-Z]+", desc.lower())
    for word in words:
        if word in _COLOR_WORDS:
            return word
    return ""


def _shape_from_description(desc: str) -> str:
    words = set(re.findall(r"[a-zA-Z]+", desc.lower()))
    for shape in ("circle", "sphere", "ball", "orb", "triangle", "star", "rectangle", "square"):
        if shape in words:
            return shape
    return "rectangle"


__all__ = ["build_scratch_project", "render_scratch_sb3"]
