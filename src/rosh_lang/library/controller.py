# licence: Rosh-BSL
"""controller — Universal input controller widget.

Provides keyboard and touch input for any target object.
Does NOT create objects — purely handles input.

Usage:
    use controller target player keys arrows touch on speed 0.03
    use controller target ship keys both move x fire on
    use controller target player mode 3d             # arrows=xz, ,/.=y
    use controller target player mode 3d up_key . down_key ,
    use controller target player mode 3d vertical on # adds up/down touch buttons
"""

from __future__ import annotations

from rosh_lang.model import (
    CreateStatement,
    EndStatement,
    EventStatement,
    IfStatement,
    OnStatement,
    SendStatement,
    SetStatement,
    Statement,
    WhenStatement,
)

METADATA = {
    "widget": "controller",
    "version": "0.1",
    "description": "Universal input controller (keyboard + touch) for any target object",
    "config": {
        "target": "",
        "keys": "arrows",
        "mode": "2d",
        "touch": "off",
        "touch_style": "dpad",
        "speed": "0.02",
        "move": "xy",
        "help": "on",
        "help_key": "?",
        "fire": "off",
        "fire_key": '" "',
        "fire_event": "fire",
        "fire2": "off",
        "fire2_key": '"x"',
        "fire2_event": "fire2",
        "clamp": "on",
        "clamp_x_min": "0.02",
        "clamp_x_max": "0.88",
        "clamp_y_min": "0.02",
        "clamp_y_max": "0.92",
        "up_key": ".",
        "down_key": ",",
        "vertical": "off",
    },
    "licence": "Rosh-BSL",
}


GLOBALS: list[str] = []  # Populated dynamically by generate() — target object bypasses prefixing


def generate(config: dict[str, str], user_config: dict[str, str] | None = None) -> list[Statement]:
    """Generate controller statements for the target object."""
    target = config.get("target", "")
    if not target:
        return []  # No target = nothing to control

    # Declare target as global so it bypasses namespace prefixing
    GLOBALS.clear()
    GLOBALS.append(target)

    keys = config.get("keys", "arrows")
    mode = config.get("mode", "2d")
    speed = config.get("speed", "0.02")
    uc = user_config or {}
    # In 3D mode: world-space movement, floor clamp, different defaults
    if mode == "3d":
        speed = uc.get("speed", speed) if "speed" in uc else "0.1"
        move = uc["move"] if "move" in uc else "xyz"
        clamp = uc["clamp"] if "clamp" in uc else "on"
    else:
        move = config.get("move", "xy")
        clamp = config.get("clamp", "on")
    cx_min = config.get("clamp_x_min", "0.02")
    cx_max = config.get("clamp_x_max", "0.88")
    cy_min = config.get("clamp_y_min", "0.02")
    cy_max = config.get("clamp_y_max", "0.92")
    up_key = config.get("up_key", ".")
    down_key = config.get("down_key", ",")
    fire = config.get("fire", "off")
    fire_key = config.get("fire_key", '" "')
    fire_event = config.get("fire_event", "fire")
    fire2 = config.get("fire2", "off")
    fire2_key = config.get("fire2_key", '"x"')
    fire2_event = config.get("fire2_event", "fire2")
    touch = config.get("touch", "off")
    touch_style = config.get("touch_style", "dpad")
    help_on = config.get("help", "on")
    help_key = config.get("help_key", "?")
    vertical = config.get("vertical", "off")

    stmts: list[Statement] = []

    # Speed value (accessible as controller.speed)
    stmts.append(CreateStatement(kind="number", name="speed"))
    stmts.append(SetStatement(target="speed", value=speed))

    # Touch config (picked up by JS runtime)
    if touch == "on":
        stmts.append(CreateStatement(kind="string", name="_touch"))
        stmts.append(SetStatement(target="_touch", value=touch_style))
        stmts.append(CreateStatement(kind="string", name="_touch_target"))
        stmts.append(SetStatement(target="_touch_target", value=target))

    # Help config (picked up by JS runtime)
    if help_on == "on":
        stmts.append(CreateStatement(kind="string", name="_help"))
        stmts.append(SetStatement(target="_help", value="on"))
        stmts.append(CreateStatement(kind="string", name="_help_key"))
        stmts.append(SetStatement(target="_help_key", value=help_key))
        stmts.append(CreateStatement(kind="string", name="_help_keys"))
        stmts.append(SetStatement(target="_help_keys", value=keys))
        stmts.append(CreateStatement(kind="string", name="_help_move"))
        stmts.append(SetStatement(target="_help_move", value=move))
        if fire == "on":
            stmts.append(CreateStatement(kind="string", name="_help_fire"))
            stmts.append(SetStatement(target="_help_fire", value=fire_key))
        if fire2 == "on":
            stmts.append(CreateStatement(kind="string", name="_fire2_key"))
            stmts.append(SetStatement(target="_fire2_key", value=fire2_key))

    # Vertical controls config (picked up by touch controls in 3D mode)
    if vertical == "on":
        stmts.append(CreateStatement(kind="string", name="_vertical"))
        stmts.append(SetStatement(target="_vertical", value="on"))
        stmts.append(CreateStatement(kind="string", name="_vertical_up_key"))
        stmts.append(SetStatement(target="_vertical_up_key", value=up_key))
        stmts.append(CreateStatement(kind="string", name="_vertical_down_key"))
        stmts.append(SetStatement(target="_vertical_down_key", value=down_key))

    # Movement handlers — when update + if _keys checks
    # These use the TARGET object's properties directly (not _self)
    if move != "none":
        key_map = _get_key_map(keys, speed, move, target, mode, up_key, down_key)
        if key_map:
            stmts.append(WhenStatement(event="update", args=[]))
            for key_name, target_prop, delta in key_map:
                stmts.append(IfStatement(
                    condition=f"_keys.{key_name} == 1",
                    then_body=[SetStatement(
                        target=target_prop,
                        value=f"{target_prop} {delta}",
                    )],
                    else_body=[],
                ))
            stmts.append(EndStatement())

    # Boundary clamping
    if clamp == "on":
        if mode == "3d":
            # 3D: clamp y >= 0 (floor) by default, no x/z bounds
            floor_min = uc.get("clamp_y_min", "0")
            floor_max = uc.get("clamp_y_max", "20")
            if move in ("xyz", "y"):
                stmts.append(OnStatement(
                    event="update", action="set",
                    args=f"{target}.y to clamp {target}.y {floor_min} {floor_max}",
                ))
        else:
            # 2D: clamp x and y to screen bounds
            if move in ("xy", "x"):
                stmts.append(OnStatement(
                    event="update", action="set",
                    args=f"{target}.x to clamp {target}.x {cx_min} {cx_max}",
                ))
            if move in ("xy", "y"):
                stmts.append(OnStatement(
                    event="update", action="set",
                    args=f"{target}.y to clamp {target}.y {cy_min} {cy_max}",
                ))

    # Fire action
    if fire == "on":
        # Clean the fire_key value (remove quotes if present)
        clean_key = fire_key.strip('"').strip("'")
        stmts.append(EventStatement(name=fire_event, payload_fields=[]))
        stmts.append(OnStatement(
            event="keydown", action="send", args=fire_event,
            condition=f"key == \"{clean_key}\"",
        ))

    # Fire2 action (second button)
    if fire2 == "on":
        clean_key2 = fire2_key.strip('"').strip("'")
        stmts.append(EventStatement(name=fire2_event, payload_fields=[]))
        stmts.append(OnStatement(
            event="keydown", action="send", args=fire2_event,
            condition=f"key == \"{clean_key2}\"",
        ))

    return stmts


def _get_key_map(
    keys: str, speed: str, move: str, target: str,
    mode: str = "2d", up_key: str = ".", down_key: str = ",",
) -> list[tuple[str, str, str]]:
    """Return (key_name, target_property, delta_expr) tuples.

    In 2d mode: arrows/wasd control x and y.
    In 3d mode: arrows/wasd control x and z (ground plane),
                up_key/down_key control y (vertical).
    """
    result: list[tuple[str, str, str]] = []

    if mode == "3d":
        # 3D: arrows = x (left/right) and z (forward/back)
        if keys in ("arrows", "both"):
            if move in ("xyz", "xz", "x"):
                result.extend([
                    ("ArrowLeft", f"{target}.x", f"- {speed}"),
                    ("ArrowRight", f"{target}.x", f"+ {speed}"),
                ])
            if move in ("xyz", "xz", "z"):
                result.extend([
                    ("ArrowUp", f"{target}.z", f"- {speed}"),
                    ("ArrowDown", f"{target}.z", f"+ {speed}"),
                ])
        if keys in ("wasd", "both"):
            if move in ("xyz", "xz", "x"):
                result.extend([
                    ("a", f"{target}.x", f"- {speed}"),
                    ("d", f"{target}.x", f"+ {speed}"),
                ])
            if move in ("xyz", "xz", "z"):
                result.extend([
                    ("w", f"{target}.z", f"- {speed}"),
                    ("s", f"{target}.z", f"+ {speed}"),
                ])
        # Vertical (y) via up_key/down_key
        if move in ("xyz", "y"):
            result.extend([
                (up_key, f"{target}.y", f"+ {speed}"),
                (down_key, f"{target}.y", f"- {speed}"),
            ])
    else:
        # 2D: arrows/wasd control x and y
        if keys in ("arrows", "both"):
            if move in ("xy", "x"):
                result.extend([
                    ("ArrowLeft", f"{target}.x", f"- {speed}"),
                    ("ArrowRight", f"{target}.x", f"+ {speed}"),
                ])
            if move in ("xy", "y"):
                result.extend([
                    ("ArrowUp", f"{target}.y", f"- {speed}"),
                    ("ArrowDown", f"{target}.y", f"+ {speed}"),
                ])
        if keys in ("wasd", "both"):
            if move in ("xy", "x"):
                result.extend([
                    ("a", f"{target}.x", f"- {speed}"),
                    ("d", f"{target}.x", f"+ {speed}"),
                ])
            if move in ("xy", "y"):
                result.extend([
                    ("w", f"{target}.y", f"- {speed}"),
                    ("s", f"{target}.y", f"+ {speed}"),
                ])

    return result
