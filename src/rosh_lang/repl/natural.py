"""Natural-language shell lowering for the terminal REPL."""

from __future__ import annotations

from dataclasses import dataclass

_CREATE_VERBS = {"create", "make", "add", "draw", "spawn"}
_STRICT_CREATE_KINDS = {"object", "objects", "number", "string", "list", "scene"}
_ARTICLES = {"a", "an", "the"}

_COLOR_NAMES = {
    "red", "green", "blue", "yellow", "cyan", "magenta",
    "white", "black", "orange", "purple", "pink", "gray",
    "grey", "gold", "silver", "brown", "navy", "teal",
    "coral", "salmon", "lime", "indigo", "violet", "crimson",
    "maroon",
}

_SIZE_WORDS = {
    "tiny": 0.04,
    "small": 0.07,
    "big": 0.16,
    "large": 0.16,
    "huge": 0.24,
}

_RELATIVE_SIZE_WORDS = {
    "smaller": 0.75,
    "bigger": 1.25,
}

_DIRECTION_DELTAS = {
    "left": ("x", -0.1),
    "right": ("x", 0.1),
    "up": ("y", -0.1),
    "down": ("y", 0.1),
}

_GEOMETRIC_SHAPES = {
    "ball": "circle",
    "circle": "circle",
    "sphere": "sphere",
    "round": "circle",
    "orb": "circle",
    "square": "rectangle",
    "rectangle": "rectangle",
    "box": "rectangle",
    "cube": "cube",
    "block": "rectangle",
}

_SPRITE_SHAPES = {
    "spaceship": "spaceship",
    "ship": "ship",
    "rocket": "spaceship",
    "alien": "alien",
    "invader": "invader",
    "ufo": "alien",
    "monster": "alien",
    "enemy": "alien",
    "player": "spaceship",
    "hero": "spaceship",
    "bullet": "bullet",
    "projectile": "bullet",
    "missile": "bullet",
    "arrow": "bullet",
    "crystal": "crystal",
    "gem": "gem",
    "jewel": "gem",
    "diamond": "gem",
    "rock": "crystal",
    "asteroid": "crystal",
    "star": "star",
}


@dataclass(frozen=True, slots=True)
class LoweredInput:
    original: str
    text: str
    changed: bool = False
    subject: str | None = None


def lower_shell_input(text: str, *, current_subject: str | None = None) -> LoweredInput:
    """Lower a natural shell phrase into strict Rosh when it's safe to do so."""
    stripped = text.strip()
    if not stripped:
        return LoweredInput(original=text, text=text, changed=False)

    lowered = _lower_create_phrase(stripped)
    if lowered is not None:
        return LoweredInput(original=text, text=lowered, changed=True, subject=_subject_from_lowered(lowered))

    lowered = _lower_make_phrase(stripped, current_subject=current_subject)
    if lowered is not None:
        return LoweredInput(original=text, text=lowered, changed=True, subject=_subject_from_lowered(lowered))

    lowered = _lower_move_phrase(stripped, current_subject=current_subject)
    if lowered is not None:
        return LoweredInput(original=text, text=lowered, changed=True, subject=_subject_from_lowered(lowered))

    return LoweredInput(original=text, text=text, changed=False)


def _lower_create_phrase(text: str) -> str | None:
    tokens = text.split()
    if len(tokens) < 2:
        return None

    verb = tokens[0].lower()
    if verb not in _CREATE_VERBS:
        return None

    remainder = [token.lower() for token in tokens[1:]]
    if remainder[0] in _STRICT_CREATE_KINDS:
        return None

    if remainder[0] in _ARTICLES:
        remainder = remainder[1:]
        if not remainder:
            return None

    noun = remainder[-1]
    modifiers = remainder[:-1]

    color: str | None = None
    size: float | None = None

    for token in modifiers:
        if token in _SIZE_WORDS and size is None:
            size = _SIZE_WORDS[token]
            continue
        if token in _COLOR_NAMES and color is None:
            color = "gray" if token == "grey" else token
            continue
        return None

    geometric_shape = _GEOMETRIC_SHAPES.get(noun)
    sprite_shape = _SPRITE_SHAPES.get(noun)

    lines: list[str]
    if geometric_shape is not None:
        lines = [f"create object {noun}", f"set {noun}.shape to {geometric_shape}"]
    elif sprite_shape is not None:
        description = f"{color} {sprite_shape}".strip() if color else sprite_shape
        lines = [f'sprite {noun} "{description}"']
    else:
        lines = [f"create object {noun}"]

    if color is not None:
        lines.append(f"set {noun}.color to {color}")

    if size is not None:
        lines.append(f"set {noun}.width to {size}")
        lines.append(f"set {noun}.height to {size}")
        lines.append(f"set {noun}.depth to {size}")

    if geometric_shape is not None or sprite_shape is not None:
        lines.append(f"set {noun}.x to 0.5")
        lines.append(f"set {noun}.y to 0.5")

    return "\n".join(lines)


def _lower_make_phrase(text: str, *, current_subject: str | None) -> str | None:
    tokens = text.split()
    if len(tokens) < 3 or tokens[0].lower() != "make":
        return None

    target, consumed = _resolve_target_tokens(tokens[1:], current_subject)
    if target is None:
        return None

    modifier_tokens = tokens[1 + consumed:]
    if len(modifier_tokens) != 1:
        return None

    modifier = modifier_tokens[0].lower()
    if modifier in _COLOR_NAMES:
        color = "gray" if modifier == "grey" else modifier
        return f"set {target}.color to {color}"

    if modifier in _SIZE_WORDS:
        size = _SIZE_WORDS[modifier]
        return "\n".join([
            f"set {target}.width to {size}",
            f"set {target}.height to {size}",
            f"set {target}.depth to {size}",
        ])

    if modifier in _RELATIVE_SIZE_WORDS:
        factor = _RELATIVE_SIZE_WORDS[modifier]
        return "\n".join([
            f"set {target}.width to {target}.width * {factor}",
            f"set {target}.height to {target}.height * {factor}",
            f"set {target}.depth to {target}.depth * {factor}",
        ])

    return None


def _lower_move_phrase(text: str, *, current_subject: str | None) -> str | None:
    tokens = text.split()
    if len(tokens) < 3 or tokens[0].lower() not in {"move", "put", "place"}:
        return None

    target, consumed = _resolve_target_tokens(tokens[1:], current_subject)
    if target is None:
        return None

    rest = [token.lower() for token in tokens[1 + consumed:]]
    if len(rest) == 1 and rest[0] in _DIRECTION_DELTAS:
        axis, delta = _DIRECTION_DELTAS[rest[0]]
        sign = "+" if delta > 0 else "-"
        amount = abs(delta)
        return f"set {target}.{axis} to {target}.{axis} {sign} {amount}"

    if rest[0] not in {"to", "at"}:
        return None

    if len(rest) == 2 and rest[1] == "center":
        return "\n".join([
            f"set {target}.x to 0.5",
            f"set {target}.y to 0.5",
        ])

    if len(rest) == 3:
        x = _normalise_coordinate(rest[1])
        y = _normalise_coordinate(rest[2])
        if x is None or y is None:
            return None
        return "\n".join([
            f"set {target}.x to {x}",
            f"set {target}.y to {y}",
        ])

    return None


def _resolve_target(raw: str, current_subject: str | None) -> str | None:
    lower = raw.lower()
    if lower in {"it", "them"}:
        return current_subject
    if lower in _ARTICLES:
        return None
    return lower


def _resolve_target_tokens(tokens: list[str], current_subject: str | None) -> tuple[str | None, int]:
    if not tokens:
        return None, 0

    first = tokens[0].lower()
    if first in {"it", "them"}:
        return current_subject, 1

    if first in _ARTICLES:
        if len(tokens) < 2:
            return None, 0
        return tokens[1].lower(), 2

    return first, 1


def _normalise_coordinate(token: str) -> str | None:
    try:
        value = float(token)
    except ValueError:
        return None

    if value > 1:
        value = value / 100

    if value.is_integer():
        return str(int(value))
    return f"{value:.4f}".rstrip("0").rstrip(".")


def _subject_from_lowered(lowered: str) -> str | None:
    for line in lowered.splitlines():
        tokens = line.split()
        if len(tokens) >= 3 and tokens[0] == "create" and tokens[1] in _STRICT_CREATE_KINDS:
            return tokens[2]
        if len(tokens) >= 2 and tokens[0] in {"sprite", "set"}:
            head = tokens[1]
            return head.split(".", 1)[0]
    return None
