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
import warnings
import zipfile
from dataclasses import dataclass, field
from html import escape
from typing import Any

from rosh_lang import __version__
from rosh_lang.core.model import (
    AfterStatement,
    BackgroundStatement,
    CreateStatement,
    DefineStatement,
    DestroyStatement,
    DoStatement,
    EndStatement,
    IfStatement,
    OnStatement,
    PrintStatement,
    Programme,
    PlayStatement,
    RepeatStatement,
    SayStatement,
    SendStatement,
    SetStatement,
    SoundStatement,
    Statement,
    UseStatement,
    WhenStatement,
)
from rosh_lang.core.runtime import Runtime

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

_SCRATCH_VISUAL_PROPS = {
    "x",
    "y",
    "width",
    "height",
    "size",
    "color",
    "label",
    "sprite",
    "shape",
    "visible",
    "direction",
    "rotation",
    "rotation_style",
    "layer",
    "z_order",
    "draggable",
    "volume",
    "ghost",
    "brightness",
    "color_effect",
    "fisheye",
    "whirl",
    "pixelate",
    "mosaic",
}

_SCRATCH_BUILTIN_EVENTS = {
    "start",
    "click",
    "keydown",
    "collision",
    "update",
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
    statements = _expand_use_statements(programme.statements, search_paths)
    (
        top_level,
        start_body,
        click_handlers,
        key_handlers,
        collision_handlers,
        update_handlers,
        broadcast_handlers,
    ) = _split_event_bodies(statements)
    key_handlers.extend(_key_handlers_from_update(update_handlers))
    key_handlers.extend(_key_handlers_from_on(top_level))
    rt = Runtime(output=io.StringIO(), search_paths=search_paths)
    rt.run(Programme(statements=top_level, source=programme.source))

    background = _find_background(top_level) or rt.state.get("_background", "#ffffff")
    backdrop_asset = _Asset("backdrop", _stage_svg(str(background)))
    assets: list[_Asset] = [backdrop_asset]
    sound_assets = _collect_sound_assets(statements)
    assets.extend(sound_assets.values())
    sound_infos = [_sound_info(asset) for asset in sound_assets.values()]
    variables = _collect_scratch_variables(rt.state, statements)
    broadcasts = _collect_broadcasts(statements)
    targets: list[dict[str, Any]] = [
        _stage_target(backdrop_asset, sound_infos, variables, broadcasts)
    ]

    object_items = _collect_scratch_objects(rt.state)
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
    _attach_update_scripts(update_handlers, sprite_builds, targets[0])
    _attach_collision_scripts(collision_handlers, sprite_builds)
    _attach_broadcast_scripts(broadcast_handlers, sprite_builds, targets[0])
    _attach_function_scripts(top_level, sprite_builds, targets[0])
    targets.extend(build.target for build in sprite_builds.values())

    return {
        "targets": targets,
        "monitors": _variable_monitors(variables),
        "extensions": [],
        "meta": {
            "semver": "3.0.0",
            "vm": "0.2.0",
            "agent": f"Rosh {__version__}",
        },
    }, assets


def _expand_use_statements(
    statements: list[Statement],
    search_paths: list[Any] | None,
) -> list[Statement]:
    from rosh_lang.core.widgets import load_widget, reset_hud_stack

    reset_hud_stack()
    expanded: list[Statement] = []
    for stmt in statements:
        if isinstance(stmt, UseStatement):
            expanded.extend(
                load_widget(
                    stmt.name,
                    config=stmt.config if stmt.config else None,
                    search_paths=search_paths,
                )
            )
        else:
            expanded.append(stmt)
    return expanded


def _split_event_bodies(
    statements: list[Statement],
) -> tuple[
    list[Statement],
    list[Statement],
    list[tuple[str, list[Statement]]],
    list[tuple[str, list[Statement]]],
    list[tuple[str, str, list[Statement]]],
    list[list[Statement]],
    list[tuple[str, list[Statement]]],
]:
    top_level: list[Statement] = []
    start_body: list[Statement] = []
    click_handlers: list[tuple[str, list[Statement]]] = []
    key_handlers: list[tuple[str, list[Statement]]] = []
    collision_handlers: list[tuple[str, str, list[Statement]]] = []
    update_handlers: list[list[Statement]] = []
    broadcast_handlers: list[tuple[str, list[Statement]]] = []
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
            elif stmt.event == "collision" and len(stmt.args) >= 2:
                collision_handlers.append((stmt.args[0], stmt.args[1], body))
            elif stmt.event == "update":
                update_handlers.append(body)
            elif stmt.event not in _SCRATCH_BUILTIN_EVENTS:
                broadcast_handlers.append((stmt.event, body))
            continue
        top_level.append(stmt)
        i += 1
    return (
        top_level,
        start_body,
        click_handlers,
        key_handlers,
        collision_handlers,
        update_handlers,
        broadcast_handlers,
    )


def _key_handlers_from_update(
    update_handlers: list[list[Statement]],
) -> list[tuple[str, list[Statement]]]:
    key_handlers: list[tuple[str, list[Statement]]] = []
    for body in update_handlers:
        for stmt in body:
            if not isinstance(stmt, IfStatement):
                continue
            key = _key_from_pressed_condition(stmt.condition)
            if key and stmt.then_body:
                key_handlers.append((key, stmt.then_body))
    return key_handlers


def _key_from_pressed_condition(condition: str) -> str:
    match = re.fullmatch(r"_keys\.(.+?)\s*==\s*1", condition.strip())
    if not match:
        return ""
    return match.group(1)


def _key_handlers_from_on(statements: list[Statement]) -> list[tuple[str, list[Statement]]]:
    key_handlers: list[tuple[str, list[Statement]]] = []
    for stmt in statements:
        if not isinstance(stmt, OnStatement):
            continue
        if stmt.event != "keydown" or stmt.action != "send" or not stmt.args:
            continue
        key = _key_from_payload_condition(stmt.condition)
        if key:
            key_handlers.append((key, [SendStatement(event=stmt.args)]))
    return key_handlers


def _key_from_payload_condition(condition: str) -> str:
    match = re.fullmatch(r"key\s*==\s*(.+)", condition.strip())
    if not match:
        return ""
    return _clean_literal(match.group(1).strip())


def _find_background(statements: list[Statement]) -> str:
    for stmt in statements:
        if isinstance(stmt, BackgroundStatement):
            return stmt.value
    return ""


def _collect_scratch_objects(state: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    objects: list[tuple[str, dict[str, Any]]] = []
    for key, value in state.items():
        if key.startswith("_") or not isinstance(value, dict):
            continue
        nested = [
            (subkey, subval)
            for subkey, subval in value.items()
            if isinstance(subval, dict) and (subval.keys() & _SCRATCH_VISUAL_PROPS)
        ]
        if nested:
            for subkey, subval in nested:
                objects.append((f"{key}.{subkey}", subval))
        elif value.keys() & _SCRATCH_VISUAL_PROPS:
            objects.append((key, value))
    return objects


def _top_level_sprite_setup(statements: list[Statement]) -> dict[str, list[Statement]]:
    setup: dict[str, list[Statement]] = {}
    for stmt in statements:
        if isinstance(stmt, SetStatement) and "." in stmt.target:
            owner = stmt.target.split(".", 1)[0]
            setup.setdefault(owner, []).append(stmt)
    return setup


def _collect_scratch_variables(
    state: dict[str, Any],
    statements: list[Statement],
) -> dict[str, Any]:
    names: dict[str, Any] = {
        key: value
        for key, value in state.items()
        if _is_scratch_variable(key, value)
    }
    for stmt in statements:
        if (
            isinstance(stmt, CreateStatement)
            and stmt.kind in {"number", "string"}
            and "." not in stmt.name
        ):
            names.setdefault(stmt.name, 0 if stmt.kind == "number" else "")
        elif isinstance(stmt, SetStatement) and "." not in stmt.target:
            names.setdefault(stmt.target, 0)
    for key, value in state.items():
        if key.startswith("_") or not isinstance(value, dict):
            continue
        has_visual_child = any(
            isinstance(subval, dict) and (subval.keys() & _SCRATCH_VISUAL_PROPS)
            for subval in value.values()
        )
        if not has_visual_child:
            continue
        for subkey, subval in value.items():
            dotted = f"{key}.{subkey}"
            if _is_scratch_variable(dotted, subval):
                names.setdefault(dotted, subval)
    return names


def _is_scratch_variable(name: str, value: Any) -> bool:
    return (
        not name.startswith("_")
        and not isinstance(value, (dict, list, tuple, set))
    )


def _stage_variables(variables: dict[str, Any]) -> dict[str, list[Any]]:
    return {
        _variable_id(name): [name, value]
        for name, value in sorted(variables.items())
    }


def _variable_monitors(variables: dict[str, Any]) -> list[dict[str, Any]]:
    monitors: list[dict[str, Any]] = []
    for index, (name, value) in enumerate(sorted(variables.items())):
        monitors.append({
            "id": _variable_id(name),
            "mode": "default",
            "opcode": "data_variable",
            "params": {"VARIABLE": name},
            "spriteName": None,
            "value": value,
            "width": 0,
            "height": 0,
            "x": 5,
            "y": 5 + index * 26,
            "visible": True,
            "sliderMin": 0,
            "sliderMax": 100,
            "isDiscrete": True,
        })
    return monitors


def _collect_broadcasts(statements: list[Statement]) -> dict[str, str]:
    names: set[str] = set()
    for stmt in statements:
        if isinstance(stmt, SendStatement):
            names.add(stmt.event)
        elif isinstance(stmt, AfterStatement):
            names.add(stmt.event)
        elif isinstance(stmt, WhenStatement) and stmt.event not in _SCRATCH_BUILTIN_EVENTS:
            names.add(stmt.event)
    return {
        _broadcast_id(name): name
        for name in sorted(names)
    }


def _stage_target(
    asset: _Asset,
    sounds: list[dict[str, Any]],
    variables: dict[str, Any],
    broadcasts: dict[str, str],
) -> dict[str, Any]:
    return {
        "isStage": True,
        "name": "Stage",
        "variables": _stage_variables(variables),
        "lists": {},
        "broadcasts": broadcasts,
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
        "layerOrder": layer_order,
        "visible": bool(obj.get("visible", True)),
        "x": _scratch_x(obj.get("x", 0.5)),
        "y": _scratch_y(obj.get("y", 0.5)),
        "size": _scratch_size(obj),
        "direction": float(obj.get("direction", obj.get("rotation", 90))),
        "draggable": _is_truthy(obj.get("draggable", False)),
        "rotationStyle": _rotation_style(str(obj.get("rotation_style", "all around"))),
        "volume": _scratch_volume(obj.get("volume", 100)),
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
    y_offsets: dict[str, int] = {}
    for index, (target, body) in enumerate(click_handlers):
        if target and target in sprite_builds:
            y = y_offsets.get(target, 40)
            sprite_builds[target].target["blocks"].update(
                _script_blocks(
                    body,
                    target,
                    x=260,
                    y=y,
                    hat_opcode="event_whenthisspriteclicked",
                    script_key=f"click:{target}:{index}",
                )
            )
            y_offsets[target] = y + _estimate_script_height(body)
        elif not target:
            y = y_offsets.get("stage", 40)
            stage_target["blocks"].update(
                _script_blocks(
                    body,
                    None,
                    x=260,
                    y=y,
                    hat_opcode="event_whenstageclicked",
                    script_key=f"click:stage:{index}",
                )
            )
            y_offsets["stage"] = y + _estimate_script_height(body)


def _attach_key_scripts(
    key_handlers: list[tuple[str, list[Statement]]],
    sprite_builds: dict[str, _SpriteBuild],
    stage_target: dict[str, Any],
) -> None:
    default_sprite = next(iter(sprite_builds), "")
    y_offsets: dict[str, int] = {}
    for index, (key, body) in enumerate(key_handlers):
        owner = _infer_script_owner(body, sprite_builds, default_sprite)
        target = sprite_builds[owner].target if owner else stage_target
        owner_key = owner or "stage"
        y = y_offsets.get(owner_key, 40)
        target["blocks"].update(
            _script_blocks(
                body,
                owner or None,
                x=480,
                y=y,
                hat_opcode="event_whenkeypressed",
                hat_fields={"KEY_OPTION": [_scratch_key(key), None]},
                script_key=f"key:{key}:{index}",
            )
        )
        y_offsets[owner_key] = y + _estimate_script_height(body)


def _attach_collision_scripts(
    collision_handlers: list[tuple[str, str, list[Statement]]],
    sprite_builds: dict[str, _SpriteBuild],
) -> None:
    y_offsets: dict[str, int] = {}
    for index, (a, b, body) in enumerate(collision_handlers):
        if a not in sprite_builds or b not in sprite_builds:
            missing = a if a not in sprite_builds else b
            warnings.warn(
                f"Scratch export: collision handler references unknown sprite {missing!r} - skipped",
                stacklevel=2,
            )
            continue
        owner_body = _collision_body_for_owner(body, a)
        if not owner_body:
            owner_body = body
        y_a = y_offsets.get(a, 40)
        sprite_builds[a].target["blocks"].update(
            _collision_script_blocks(
                owner_body,
                owner=a,
                touching=b,
                x=700,
                y=y_a,
                script_key=f"collision:{a}:{b}:{index}",
            )
        )
        y_offsets[a] = y_a + _estimate_script_height(owner_body) + 96
        secondary_body = _collision_body_for_owner(body, b)
        if secondary_body:
            y_b = y_offsets.get(b, 40)
            sprite_builds[b].target["blocks"].update(
                _collision_script_blocks(
                    secondary_body,
                    owner=b,
                    touching=a,
                    x=700,
                    y=y_b,
                    script_key=f"collision:{b}:{a}:{index}",
                )
            )
            y_offsets[b] = y_b + _estimate_script_height(secondary_body) + 96


def _collision_body_for_owner(
    body: list[Statement],
    owner: str,
) -> list[Statement]:
    result: list[Statement] = []
    for stmt in body:
        if isinstance(stmt, SetStatement) and stmt.target.startswith(f"{owner}."):
            result.append(stmt)
        elif isinstance(stmt, DestroyStatement) and stmt.name == owner:
            result.append(stmt)
        elif isinstance(stmt, IfStatement):
            then_body = _collision_body_for_owner(stmt.then_body, owner)
            else_body = _collision_body_for_owner(stmt.else_body, owner)
            if then_body or else_body:
                result.append(IfStatement(
                    condition=stmt.condition,
                    then_body=then_body,
                    else_body=else_body,
                    line=stmt.line,
                ))
        elif isinstance(stmt, RepeatStatement):
            nested_body = _collision_body_for_owner(stmt.body, owner)
            if nested_body:
                result.append(RepeatStatement(
                    count=stmt.count,
                    var=stmt.var,
                    body=nested_body,
                    line=stmt.line,
                ))
    return result


def _attach_update_scripts(
    update_handlers: list[list[Statement]],
    sprite_builds: dict[str, _SpriteBuild],
    stage_target: dict[str, Any],
) -> None:
    default_sprite = next(iter(sprite_builds), "")
    y_offsets: dict[str, int] = {}
    for index, body in enumerate(update_handlers):
        owner = _infer_script_owner(body, sprite_builds, default_sprite)
        target = sprite_builds[owner].target if owner else stage_target
        owner_key = owner or "stage"
        y = y_offsets.get(owner_key, 40)
        target["blocks"].update(
            _forever_script_blocks(
                body,
                owner or None,
                x=920,
                y=y,
                script_key=f"update:{index}",
            )
        )
        y_offsets[owner_key] = y + _estimate_script_height(body) + 48


def _attach_broadcast_scripts(
    broadcast_handlers: list[tuple[str, list[Statement]]],
    sprite_builds: dict[str, _SpriteBuild],
    stage_target: dict[str, Any],
) -> None:
    default_sprite = next(iter(sprite_builds), "")
    y_offsets: dict[str, int] = {}
    for index, (event, body) in enumerate(broadcast_handlers):
        owner = _infer_script_owner(body, sprite_builds, default_sprite)
        target = sprite_builds[owner].target if owner else stage_target
        owner_key = owner or "stage"
        y = y_offsets.get(owner_key, 40)
        target["blocks"].update(
            _script_blocks(
                body,
                owner or None,
                x=1140,
                y=y,
                hat_opcode="event_whenbroadcastreceived",
                hat_fields={"BROADCAST_OPTION": [event, _broadcast_id(event)]},
                script_key=f"broadcast:{event}:{index}",
            )
        )
        y_offsets[owner_key] = y + _estimate_script_height(body)


def _attach_function_scripts(
    statements: list[Statement],
    sprite_builds: dict[str, _SpriteBuild],
    stage_target: dict[str, Any],
) -> None:
    default_sprite = next(iter(sprite_builds), "")
    definitions = [stmt for stmt in statements if isinstance(stmt, DefineStatement)]
    y_offsets: dict[str, int] = {}
    for index, stmt in enumerate(definitions):
        owner = _infer_script_owner(stmt.body, sprite_builds, default_sprite)
        target = sprite_builds[owner].target if owner else stage_target
        owner_key = owner or "stage"
        y = y_offsets.get(owner_key, 40)
        target["blocks"].update(
            _procedure_definition_blocks(
                stmt,
                owner or None,
                x=1360,
                y=y,
            )
        )
        y_offsets[owner_key] = y + _estimate_script_height(stmt.body) + 48


def _procedure_definition_blocks(
    stmt: DefineStatement,
    sprite_name: str | None,
    *,
    x: int,
    y: int,
) -> dict[str, dict[str, Any]]:
    owner = sprite_name or "stage"
    script_key = f"define:{stmt.name}"
    body = _script_blocks(
        stmt.body,
        sprite_name,
        x=x,
        y=y,
        script_key=f"{script_key}:body",
        include_hat=False,
    )
    definition_id = _block_id("procedures_definition", owner, script_key)
    prototype_id = _block_id("procedures_prototype", owner, script_key)
    first_body_id = None
    if body:
        first_body_id = next(
            block_id for block_id, block in body.items()
            if block["parent"] is None
        )
        body[first_body_id]["parent"] = definition_id

    return {
        definition_id: {
            "opcode": "procedures_definition",
            "next": first_body_id,
            "parent": None,
            "inputs": {"custom_block": [1, prototype_id]},
            "fields": {},
            "shadow": False,
            "topLevel": True,
            "x": x,
            "y": y,
        },
        prototype_id: {
            "opcode": "procedures_prototype",
            "next": None,
            "parent": definition_id,
            "inputs": {},
            "fields": {},
            "shadow": True,
            "topLevel": False,
            "mutation": _procedure_mutation(stmt.name),
        },
        **body,
    }


def _forever_script_blocks(
    statements: list[Statement],
    sprite_name: str | None,
    *,
    x: int,
    y: int,
    script_key: str,
) -> dict[str, dict[str, Any]]:
    body = _script_blocks(
        statements,
        sprite_name,
        x=x,
        y=y,
        hat_opcode="event_whenflagclicked",
        script_key=f"{script_key}:body",
        include_hat=False,
    )
    if not body:
        return {}

    first_body_id = next(
        block_id for block_id, block in body.items()
        if block["parent"] is None
    )
    owner = sprite_name or "stage"
    hat_id = _block_id("event_whenflagclicked", owner, script_key, "hat")
    forever_id = _block_id("control_forever", owner, script_key, "forever")
    body[first_body_id]["parent"] = forever_id

    return {
        hat_id: {
            "opcode": "event_whenflagclicked",
            "next": forever_id,
            "parent": None,
            "inputs": {},
            "fields": {},
            "shadow": False,
            "topLevel": True,
            "x": x,
            "y": y,
        },
        forever_id: {
            "opcode": "control_forever",
            "next": None,
            "parent": hat_id,
            "inputs": {"SUBSTACK": [2, first_body_id]},
            "fields": {},
            "shadow": False,
            "topLevel": False,
        },
        **body,
    }


def _collision_script_blocks(
    statements: list[Statement],
    *,
    owner: str,
    touching: str,
    x: int,
    y: int,
    script_key: str,
) -> dict[str, dict[str, Any]]:
    body = _script_blocks(
        statements,
        owner,
        x=x,
        y=y,
        hat_opcode="event_whenflagclicked",
        script_key=f"{script_key}:body",
        include_hat=False,
    )
    if not body:
        return {}

    first_body_id = next(
        block_id for block_id, block in body.items()
        if block["parent"] is None
    )
    hat_id = _block_id("event_whenflagclicked", owner, script_key, "hat")
    forever_id = _block_id("control_forever", owner, script_key, "forever")
    if_id = _block_id("control_if", owner, script_key, "if")
    touching_id = _block_id("sensing_touchingobject", owner, script_key, "touching")
    menu_id = _block_id("sensing_touchingobjectmenu", owner, script_key, "menu")

    body[first_body_id]["parent"] = if_id

    return {
        hat_id: {
            "opcode": "event_whenflagclicked",
            "next": forever_id,
            "parent": None,
            "inputs": {},
            "fields": {},
            "shadow": False,
            "topLevel": True,
            "x": x,
            "y": y,
        },
        forever_id: {
            "opcode": "control_forever",
            "next": None,
            "parent": hat_id,
            "inputs": {"SUBSTACK": [2, if_id]},
            "fields": {},
            "shadow": False,
            "topLevel": False,
        },
        if_id: {
            "opcode": "control_if",
            "next": None,
            "parent": forever_id,
            "inputs": {
                "CONDITION": [2, touching_id],
                "SUBSTACK": [2, first_body_id],
            },
            "fields": {},
            "shadow": False,
            "topLevel": False,
        },
        touching_id: {
            "opcode": "sensing_touchingobject",
            "next": None,
            "parent": if_id,
            "inputs": {"TOUCHINGOBJECTMENU": [1, menu_id]},
            "fields": {},
            "shadow": False,
            "topLevel": False,
        },
        menu_id: {
            "opcode": "sensing_touchingobjectmenu",
            "next": None,
            "parent": touching_id,
            "inputs": {},
            "fields": {"TOUCHINGOBJECTMENU": [_scratch_name(touching), None]},
            "shadow": True,
            "topLevel": False,
        },
        **body,
    }


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
        if isinstance(stmt, IfStatement):
            owner = _infer_script_owner(stmt.then_body + stmt.else_body, sprite_builds, "")
            if owner:
                return owner
        if isinstance(stmt, RepeatStatement):
            owner = _infer_script_owner(stmt.body, sprite_builds, "")
            if owner:
                return owner
        if isinstance(stmt, DefineStatement):
            owner = _infer_script_owner(stmt.body, sprite_builds, "")
            if owner:
                return owner
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
    include_hat: bool = True,
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
    first_id = _block_id(_block_opcode(actions[0][0]), owner, script_key, "0")
    previous_id: str | None = None
    if include_hat:
        hat_id = _block_id(hat_opcode, owner, script_key, "hat")
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
        block_opcode = _block_opcode(opcode)
        block_id = _block_id(block_opcode, owner, script_key, str(index))
        next_id = (
            _block_id(
                _block_opcode(actions[index + 1][0]),
                owner,
                script_key,
                str(index + 1),
            )
            if index + 1 < len(actions) else None
        )
        if opcode == "__if__":
            condition_id, condition_blocks = _condition_blocks(
                payload["condition"],
                sprite_name,
                owner,
                script_key,
                index,
            )
            substack = _script_blocks(
                payload["then_body"],
                sprite_name,
                x=x,
                y=y,
                script_key=f"{script_key}:if:{index}",
                include_hat=False,
            )
            if not condition_id or not substack:
                continue
            first_substack_id = next(
                nested_id for nested_id, nested in substack.items()
                if nested["parent"] is None
            )
            substack[first_substack_id]["parent"] = block_id
            blocks[block_id] = {
                "opcode": block_opcode,
                "next": next_id,
                "parent": previous_id,
                "inputs": {
                    "CONDITION": [2, condition_id],
                    "SUBSTACK": [2, first_substack_id],
                },
                "fields": {},
                "shadow": False,
                "topLevel": False,
            }
            blocks.update(condition_blocks)
            blocks.update(substack)
            previous_id = block_id
            continue
        if opcode == "__repeat__":
            times_input, times_blocks = _repeat_times_blocks(
                payload["count"],
                owner,
                script_key,
                index,
                block_id,
            )
            substack = _script_blocks(
                payload["body"],
                sprite_name,
                x=x,
                y=y,
                script_key=f"{script_key}:repeat:{index}",
                include_hat=False,
            )
            if not substack:
                continue
            first_substack_id = next(
                nested_id for nested_id, nested in substack.items()
                if nested["parent"] is None
            )
            substack[first_substack_id]["parent"] = block_id
            blocks[block_id] = {
                "opcode": block_opcode,
                "next": next_id,
                "parent": previous_id,
                "inputs": {
                    "TIMES": times_input,
                    "SUBSTACK": [2, first_substack_id],
                },
                "fields": {},
                "shadow": False,
                "topLevel": False,
            }
            blocks.update(times_blocks)
            blocks.update(substack)
            previous_id = block_id
            continue
        if opcode == "__after__":
            broadcast_id = _block_id("event_broadcast", owner, script_key, str(index), "broadcast")
            menu_id = _block_id("broadcast_menu", owner, script_key, str(index))
            blocks[block_id] = {
                "opcode": block_opcode,
                "next": broadcast_id,
                "parent": previous_id,
                "inputs": {"DURATION": _number_input(payload["delay"])},
                "fields": {},
                "shadow": False,
                "topLevel": False,
            }
            blocks[broadcast_id] = {
                "opcode": "event_broadcast",
                "next": next_id,
                "parent": block_id,
                "inputs": {"BROADCAST_INPUT": [1, menu_id]},
                "fields": {},
                "shadow": False,
                "topLevel": False,
            }
            blocks[menu_id] = {
                "opcode": "event_broadcast_menu",
                "next": None,
                "parent": broadcast_id,
                "inputs": {},
                "fields": {
                    "BROADCAST_OPTION": [
                        payload["event"],
                        _broadcast_id(payload["event"]),
                    ]
                },
                "shadow": True,
                "topLevel": False,
            }
            previous_id = broadcast_id
            continue
        blocks[block_id] = {
            "opcode": block_opcode,
            "next": next_id,
            "parent": previous_id,
            "inputs": payload.get("inputs", {}),
            "fields": payload.get("fields", {}),
            "shadow": False,
            "topLevel": False,
        }
        if "mutation" in payload:
            blocks[block_id]["mutation"] = payload["mutation"]
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
        if "broadcast" in payload:
            menu_id = _block_id("broadcast_menu", owner, script_key, str(index))
            blocks[block_id]["inputs"] = {"BROADCAST_INPUT": [1, menu_id]}
            blocks[menu_id] = {
                "opcode": "event_broadcast_menu",
                "next": None,
                "parent": block_id,
                "inputs": {},
                "fields": {
                    "BROADCAST_OPTION": [
                        payload["broadcast"],
                        _broadcast_id(payload["broadcast"]),
                    ]
                },
                "shadow": True,
                "topLevel": False,
            }
        if "goto" in payload:
            menu_id = _block_id("goto_menu", owner, script_key, str(index))
            blocks[block_id]["inputs"] = {"TO": [1, menu_id]}
            blocks[menu_id] = {
                "opcode": "motion_goto_menu",
                "next": None,
                "parent": block_id,
                "inputs": {},
                "fields": {"TO": [payload["goto"], None]},
                "shadow": True,
                "topLevel": False,
            }
        if "towards" in payload:
            menu_id = _block_id("towards_menu", owner, script_key, str(index))
            blocks[block_id]["inputs"] = {"TOWARDS": [1, menu_id]}
            blocks[menu_id] = {
                "opcode": "motion_pointtowards_menu",
                "next": None,
                "parent": block_id,
                "inputs": {},
                "fields": {"TOWARDS": [payload["towards"], None]},
                "shadow": True,
                "topLevel": False,
            }
        previous_id = block_id
    return blocks


def _block_opcode(opcode: str) -> str:
    aliases = {
        "__if__": "control_if",
        "__repeat__": "control_repeat",
        "__after__": "control_wait",
    }
    return aliases.get(opcode, opcode)


def _statement_action(
    stmt: Statement,
    sprite_name: str | None,
) -> tuple[str, dict[str, Any]] | None:
    if isinstance(stmt, IfStatement):
        if _condition_parts(stmt.condition, sprite_name) and _has_script_actions(
            stmt.then_body,
            sprite_name,
        ):
            return "__if__", {
                "condition": stmt.condition,
                "then_body": stmt.then_body,
            }
        if not _condition_parts(stmt.condition, sprite_name):
            warnings.warn(
                f"Scratch export: cannot compile condition {stmt.condition!r} - if block skipped"
                " (only simple comparisons like 'x > 0.5' are supported)",
                stacklevel=2,
            )
    if isinstance(stmt, RepeatStatement):
        if _repeat_count(stmt.count) is not None and _has_script_actions(
            stmt.body,
            sprite_name,
        ):
            return "__repeat__", {
                "count": _repeat_count(stmt.count),
                "body": stmt.body,
            }
    if isinstance(stmt, AfterStatement):
        return "__after__", {"delay": stmt.delay, "event": stmt.event}
    if isinstance(stmt, SetStatement) and _is_variable_set_target(stmt.target, sprite_name):
        variable_change = _variable_change(stmt)
        if variable_change is not None:
            return "data_changevariableby", {
                "fields": {"VARIABLE": [stmt.target, _variable_id(stmt.target)]},
                "inputs": {"VALUE": _number_input(variable_change)},
            }
        return "data_setvariableto", {
            "fields": {"VARIABLE": [stmt.target, _variable_id(stmt.target)]},
            "inputs": {"VALUE": _literal_input(_clean_literal(stmt.value))},
        }
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
        if relative and relative[0] == "direction":
            opcode = "motion_turnright" if relative[1] >= 0 else "motion_turnleft"
            return opcode, {"inputs": {"DEGREES": _number_input(abs(relative[1]))}}
        if prop == "x":
            return "motion_setx", {"inputs": {"X": _number_input(_scratch_x(value))}}
        if prop == "y":
            return "motion_sety", {"inputs": {"Y": _number_input(_scratch_y(value))}}
        if prop in ("direction", "rotation"):
            return "motion_pointindirection", {"inputs": {"DIRECTION": _number_input(value)}}
        if prop in {"go_to", "goto"}:
            return "motion_goto", {"goto": _motion_target(value)}
        if prop in {"point_towards", "point_toward"}:
            return "motion_pointtowards", {"towards": _motion_target(value)}
        if prop == "rotation_style":
            return "motion_setrotationstyle", {"fields": {"STYLE": [_rotation_style(value), None]}}
        if prop in {"layer", "z_order"}:
            layer = _scratch_layer(value)
            if layer:
                return "looks_gotofrontback", {"fields": {"FRONT_BACK": [layer, None]}}
        if prop == "draggable":
            return "sensing_setdragmode", {"fields": {"DRAG_MODE": [_drag_mode(value), None]}}
        if prop == "volume":
            return "sound_setvolumeto", {"inputs": {"VOLUME": _number_input(_scratch_volume(value))}}
        if prop in {"ghost", "brightness", "color_effect", "fisheye", "whirl", "pixelate", "mosaic"}:
            return "looks_seteffectto", {
                "fields": {"EFFECT": [_scratch_effect(prop), None]},
                "inputs": {"VALUE": _number_input(value)},
            }
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
        if stmt.mode == "stop":
            return "sound_stopallsounds", {}
        if stmt.mode == "loop":
            return "sound_play", {"sound": stmt.sound}
        return "sound_playuntildone", {"sound": stmt.sound}
    if isinstance(stmt, SendStatement):
        return "event_broadcast", {"broadcast": stmt.event}
    if isinstance(stmt, DoStatement):
        return "procedures_call", {"mutation": _procedure_mutation(stmt.name)}
    return None


def _estimate_script_height(statements: list[Statement], with_hat: bool = True) -> int:
    """Estimate compiled block stack height in pixels to avoid layout overlaps."""
    BLOCK_PX = 48
    count = 1 if with_hat else 0
    for stmt in statements:
        if isinstance(stmt, IfStatement):
            count += 1 + _estimate_script_height(stmt.then_body, False) // BLOCK_PX
        elif isinstance(stmt, RepeatStatement):
            count += 1 + _estimate_script_height(stmt.body, False) // BLOCK_PX
        elif isinstance(stmt, AfterStatement):
            count += 2
        else:
            count += 1
    return count * BLOCK_PX + 40


def _has_script_actions(statements: list[Statement], sprite_name: str | None) -> bool:
    return any(_statement_action(stmt, sprite_name) for stmt in statements)


def _is_variable_set_target(target: str, sprite_name: str | None) -> bool:
    if "." not in target:
        return True
    if sprite_name and (target == sprite_name or target.startswith(f"{sprite_name}.")):
        return False
    prop = target.rsplit(".", 1)[1]
    return prop not in _SCRATCH_VISUAL_PROPS


def _condition_blocks(
    condition: str,
    sprite_name: str | None,
    owner: str,
    script_key: str,
    index: int,
) -> tuple[str, dict[str, dict[str, Any]]]:
    parts = _condition_parts(condition, sprite_name)
    if not parts:
        return "", {}
    prop, op, value = parts
    comparison_operator = {
        ">": "operator_gt",
        "<": "operator_lt",
        "==": "operator_equals",
        "=": "operator_equals",
        ">=": "operator_lt",
        "<=": "operator_gt",
        "!=": "operator_equals",
    }[op]
    operator_id = _block_id(comparison_operator, owner, script_key, str(index), "condition")
    reporter_id = _block_id(prop, owner, script_key, str(index), "reporter")
    reporter_opcode = _property_reporter(prop)
    variable_id = _variable_id(prop)
    reporter_fields = (
        {"VARIABLE": [prop, variable_id]}
        if reporter_opcode == "data_variable"
        else {}
    )
    comparison_block = {
        operator_id: {
            "opcode": comparison_operator,
            "next": None,
            "parent": _block_id("control_if", owner, script_key, str(index))
            if op not in {">=", "<=", "!="}
            else _block_id("operator_not", owner, script_key, str(index), "condition"),
            "inputs": {
                "OPERAND1": [2, reporter_id],
                "OPERAND2": _comparison_input(prop, value),
            },
            "fields": {},
            "shadow": False,
            "topLevel": False,
        },
    }
    reporter_block = {
        reporter_id: {
            "opcode": reporter_opcode,
            "next": None,
            "parent": operator_id,
            "inputs": {},
            "fields": reporter_fields,
            "shadow": False,
            "topLevel": False,
        },
    }
    if op not in {">=", "<=", "!="}:
        return operator_id, {**comparison_block, **reporter_block}

    not_id = _block_id("operator_not", owner, script_key, str(index), "condition")
    return not_id, {
        not_id: {
            "opcode": "operator_not",
            "next": None,
            "parent": _block_id("control_if", owner, script_key, str(index)),
            "inputs": {"OPERAND": [2, operator_id]},
            "fields": {},
            "shadow": False,
            "topLevel": False,
        },
        **comparison_block,
        **reporter_block,
    }


def _condition_parts(
    condition: str,
    sprite_name: str | None,
) -> tuple[str, str, str] | None:
    if sprite_name:
        match = re.fullmatch(
            rf"{re.escape(sprite_name)}\.(x|y|size|direction|rotation)\s*(>=|<=|!=|==|=|>|<)\s*(.+)",
            condition.strip(),
        )
        if match:
            prop, op, value = match.groups()
            return prop, op, _clean_literal(value.strip())
    match = re.fullmatch(
        r"([A-Za-z_][A-Za-z0-9_-]*(?:\.[A-Za-z_][A-Za-z0-9_-]*)?)\s*(>=|<=|!=|==|=|>|<)\s*(.+)",
        condition.strip(),
    )
    if match:
        prop, op, value = match.groups()
        return prop, op, _clean_literal(value.strip())
    return None


def _property_reporter(prop: str) -> str:
    if prop == "x":
        return "motion_xposition"
    if prop == "y":
        return "motion_yposition"
    if prop == "size":
        return "looks_size"
    if prop in {"direction", "rotation"}:
        return "motion_direction"
    return "data_variable"


def _comparison_input(prop: str, value: str) -> list[Any]:
    if prop == "x":
        return _number_input(_scratch_x(value))
    if prop == "y":
        return _number_input(_scratch_y(value))
    if prop == "size":
        return _number_input(_scratch_size_value(value))
    if prop in {"direction", "rotation"}:
        return _number_input(value)
    return _literal_input(value)


def _variable_change(stmt: SetStatement) -> float | None:
    raw = stmt.value.strip()
    match = re.fullmatch(rf"{re.escape(stmt.target)}\s*([+\-])\s*(-?\d+(?:\.\d+)?)", raw)
    if not match:
        return None
    sign = 1 if match.group(1) == "+" else -1
    return sign * float(match.group(2))


def _repeat_count(value: str) -> int | str | None:
    try:
        count = int(value)
    except ValueError:
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*", value):
            return value
        return None
    return max(0, count)


def _repeat_times_blocks(
    count: int | str,
    owner: str,
    script_key: str,
    index: int,
    parent_id: str,
) -> tuple[list[Any], dict[str, dict[str, Any]]]:
    if isinstance(count, int):
        return _number_input(count), {}
    reporter_id = _block_id("repeat_count", owner, script_key, str(index))
    return [2, reporter_id], {
        reporter_id: {
            "opcode": "data_variable",
            "next": None,
            "parent": parent_id,
            "inputs": {},
            "fields": {"VARIABLE": [count, _variable_id(count)]},
            "shadow": False,
            "topLevel": False,
        }
    }


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
    if prop in {"direction", "rotation"}:
        return "direction", amount
    return None


def _number_input(value: Any) -> list[Any]:
    return [1, [4, str(value)]]


def _text_input(value: str) -> list[Any]:
    return [1, [10, value]]


def _literal_input(value: Any) -> list[Any]:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return _text_input(str(value))
    if numeric.is_integer():
        return _number_input(int(numeric))
    return _number_input(numeric)


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
    if key == " ":
        return "space"
    cleaned = key.strip().lower()
    if not cleaned:
        return "space"
    return aliases.get(cleaned, cleaned)


def _motion_target(value: str) -> str:
    aliases = {
        "mouse": "_mouse_",
        "mouse-pointer": "_mouse_",
        "mouse_pointer": "_mouse_",
        "random": "_random_",
        "random-position": "_random_",
        "random_position": "_random_",
    }
    cleaned = value.strip().strip('"').strip("'").lower().replace(" ", "_")
    return aliases.get(cleaned, _scratch_name(value))


def _rotation_style(value: str) -> str:
    aliases = {
        "all": "all around",
        "all_around": "all around",
        "around": "all around",
        "left-right": "left-right",
        "leftright": "left-right",
        "horizontal": "left-right",
        "none": "don't rotate",
        "dont_rotate": "don't rotate",
        "fixed": "don't rotate",
    }
    cleaned = value.strip().lower().replace(" ", "_")
    return aliases.get(cleaned, value)


def _scratch_layer(value: str) -> str:
    aliases = {
        "front": "front",
        "top": "front",
        "forward": "front",
        "back": "back",
        "bottom": "back",
        "behind": "back",
    }
    return aliases.get(value.strip().lower(), "")


def _drag_mode(value: str) -> str:
    return "draggable" if _is_truthy(value) else "not draggable"


def _scratch_effect(prop: str) -> str:
    aliases = {
        "ghost": "GHOST",
        "brightness": "BRIGHTNESS",
        "color_effect": "COLOR",
        "fisheye": "FISHEYE",
        "whirl": "WHIRL",
        "pixelate": "PIXELATE",
        "mosaic": "MOSAIC",
    }
    return aliases[prop]


def _block_id(*parts: str) -> str:
    raw = ":".join(parts)
    return "rosh_" + hashlib.md5(raw.encode("utf-8")).hexdigest()[:16]


def _variable_id(name: str) -> str:
    return _block_id("variable", name)


def _broadcast_id(name: str) -> str:
    return _block_id("broadcast", name)


def _procedure_mutation(name: str) -> dict[str, Any]:
    return {
        "tagName": "mutation",
        "children": [],
        "proccode": name,
        "argumentids": "[]",
        "argumentnames": "[]",
        "argumentdefaults": "[]",
        "warp": "false",
    }


def _scratch_name(name: str) -> str:
    cleaned = name.replace(".", " ")
    return cleaned[:100] or "Rosh Sprite"


def _scratch_x(value: Any) -> float:
    if isinstance(value, str):
        named = {
            "left": -200,
            "centre": 0,
            "center": 0,
            "middle": 0,
            "right": 200,
        }.get(value.strip().lower())
        if named is not None:
            return named
    value = _to_float(value, 0.5)
    if 0 <= value <= 1:
        return round((value * STAGE_WIDTH) - (STAGE_WIDTH / 2), 3)
    return round(value, 3)


def _scratch_y(value: Any) -> float:
    if isinstance(value, str):
        named = {
            "top": 140,
            "centre": 0,
            "center": 0,
            "middle": 0,
            "bottom": -140,
        }.get(value.strip().lower())
        if named is not None:
            return named
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


def _scratch_volume(value: Any) -> float:
    value = _to_float(value, 100)
    if 0 <= value <= 1:
        return round(value * 100, 3)
    return max(0, min(100, round(value, 3)))


def _is_truthy(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().strip('"').strip("'").lower() not in {
            "",
            "0",
            "false",
            "no",
            "off",
        }
    return bool(value)


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
    elif shape in {"spaceship", "ship", "rocket"}:
        body = (
            f'<polygon points="50,6 82,88 50,72 18,88" fill="{fill}"/>'
            '<circle cx="50" cy="40" r="9" fill="#dbeafe"/>'
            '<polygon points="35,76 24,96 44,86" fill="#f97316"/>'
            '<polygon points="65,76 76,96 56,86" fill="#f97316"/>'
        )
    elif shape in {"alien", "monster", "invader"}:
        body = (
            f'<rect x="20" y="28" width="60" height="46" rx="16" fill="{fill}"/>'
            '<circle cx="38" cy="48" r="7" fill="#111"/>'
            '<circle cx="62" cy="48" r="7" fill="#111"/>'
            f'<rect x="30" y="75" width="10" height="16" rx="4" fill="{fill}"/>'
            f'<rect x="60" y="75" width="10" height="16" rx="4" fill="{fill}"/>'
        )
    elif shape in {"gem", "crystal", "diamond"}:
        body = (
            f'<polygon points="50,8 86,34 70,88 30,88 14,34" fill="{fill}"/>'
            '<polyline points="14,34 50,48 86,34" fill="none" stroke="#ffffff" stroke-opacity="0.55" stroke-width="4"/>'
            '<line x1="50" y1="8" x2="50" y2="88" stroke="#ffffff" stroke-opacity="0.35" stroke-width="4"/>'
        )
    elif shape in {"bullet", "projectile", "arrow"}:
        body = f'<polygon points="82,50 26,20 38,50 26,80" fill="{fill}"/>'
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
    for shape in (
        "circle", "sphere", "ball", "orb", "triangle", "star",
        "rectangle", "square", "spaceship", "ship", "rocket",
        "alien", "monster", "invader", "gem", "crystal", "diamond",
        "bullet", "projectile", "arrow",
    ):
        if shape in words:
            return shape
    return "rectangle"


__all__ = ["build_scratch_project", "render_scratch_sb3"]
