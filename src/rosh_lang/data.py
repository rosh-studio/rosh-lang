"""Data documents to Rosh and back, exactly (Task 19, roadmap step 1).

A data document is `{"objects": {name: {prop: value}}, "meta": {fact: value}}`.
A value is a string, an integer, a float, true/false, null, a flat list of
those, or a reference `{"$ref": name}` as a property value. Anything else is an
error that says where, never a quiet change: Rosh's promise is honesty, and it
applies to its own data first.

Reading uses the canonical parser (`normalise=False`): the plain-English
normaliser is for people, and on data it changes values.
"""

from __future__ import annotations

import json
import math
import re
from decimal import Decimal
from typing import Any

from rosh_lang.core.normalise import _strip_inline_comment
from rosh_lang.core.parser import parse_string
from rosh_lang.core.runtime import Runtime


class DataError(ValueError):
    """A document or a Rosh text outside the data subset."""


_NAME_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]*\Z")
# Words the parser reads as grammar inside a statement (`create object from`
# fails: `_parse_create`), plus every statement keyword. Case doesn't matter.
RESERVED = frozenset({
    "object", "objects", "from", "as", "to", "into", "of", "true", "false", "null", "nothing", "none",
    "random", "clamp", "count", "print", "create", "set", "when", "end", "if", "else", "get", "say",
    "send", "event", "on", "go", "look", "connect", "destroy", "forget", "sprite", "sound", "play",
    "animate", "use", "after", "background", "define", "do", "repeat", "add", "remove", "for",
})
# The characters str.splitlines() breaks on: a value holding one can't be one line.
_LINE_BREAKS = "\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029"
# Integers are 64-bit here, as JSON tools and databases expect.
_INT_LIMIT = 2 ** 63


# ── Writing ───────────────────────────────────────────────────


def _check_name(name: Any, where: str, *, object_name: bool = False) -> str:
    if not isinstance(name, str) or not _NAME_RE.match(name):
        raise DataError(f"{where}: {name!r} isn't a Rosh name (a letter, then letters, digits or _)")
    # Only object names are read as grammar (`create object from`); a property
    # or fact name comes after a dot, where any name is just a name.
    if object_name and (name.lower() in RESERVED or name.lower() == "room"):
        raise DataError(f"{where}: {name!r} is a word Rosh reserves")
    return name


def _number(value: Any, where: str) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        if not -_INT_LIMIT <= value < _INT_LIMIT:
            raise DataError(f"{where}: integers here are 64-bit, and this one is larger")
        return str(value)
    if not math.isfinite(value):
        raise DataError(f"{where}: {value} isn't a finite number")
    text = repr(value)
    if "e" in text or "E" in text:
        text = format(Decimal(text), "f")
    if "." not in text:
        text += ".0"   # a float stays a float: 1e20 is 100000000000000000000.0
    return text


def _scalar(value: Any, where: str, *, in_list: bool = False) -> str:
    if value is None:
        return "null"
    if isinstance(value, (bool, int, float)):
        return _number(value, where)
    if isinstance(value, str):
        if any(c in value for c in _LINE_BREAKS):
            raise DataError(f"{where}: the text holds a line break, and a Rosh line holds one value")
        # In a list the runtime reads JSON. On its own a string escapes its
        # backslashes and quotes, so a `#` inside can't be taken for a comment (#34).
        if in_list:
            return json.dumps(value, ensure_ascii=False)
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    raise DataError(f"{where}: a {type(value).__name__} can't be a Rosh value here")


def _value(value: Any, where: str, objects: dict) -> str:
    if isinstance(value, dict):
        if set(value) == {"$ref"}:
            target = value["$ref"]
            if not isinstance(target, str) or target not in objects:
                raise DataError(f"{where}: refers to {target!r}, which isn't in the document")
            return f"object {target}"
        raise DataError(f"{where}: an object inside an object can't be written as one Rosh value")
    if isinstance(value, list):
        items = []
        for i, item in enumerate(value):
            if isinstance(item, (list, dict)):
                raise DataError(f"{where}[{i}]: a list can't hold a list or an object")
            items.append(_scalar(item, f"{where}[{i}]", in_list=True))
        return "[" + ", ".join(items) + "]"
    return _scalar(value, where)


def to_rosh(doc: dict) -> str:
    """The document as Rosh: every object created first, so references can point anywhere."""
    if not isinstance(doc, dict) or set(doc) != {"objects", "meta"}:
        raise DataError('a data document has "objects" and "meta" and nothing else')
    objects, meta = doc["objects"], doc["meta"]
    if not isinstance(objects, dict) or not isinstance(meta, dict):
        raise DataError('"objects" and "meta" must each be a mapping')
    lines = [f"create object {_check_name(name, name, object_name=True)}" for name in objects]
    for name, props in objects.items():
        if not isinstance(props, dict):
            raise DataError(f"{name}: an object's properties must be a mapping")
        for prop, value in props.items():
            where = f"{name}.{prop}"
            _check_name(prop, where)
            lines.append(f"set {name}.{prop} to {_value(value, where, objects)}")
    for fact, value in meta.items():
        where = f"room.{fact}"
        _check_name(fact, where)
        if isinstance(value, dict):
            raise DataError(f"{where}: a room fact can't be a reference or an object")
        lines.append(f"set room.{fact} to {_value(value, where, objects)}")
    return "\n".join(lines) + "\n"


# ── Reading ───────────────────────────────────────────────────

_CREATE_RE = re.compile(r"create object (\S+)\Z")
_SET_RE = re.compile(r"set ([A-Za-z]\w*)\.([A-Za-z]\w*) to (.+)\Z", re.S)
_NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?\Z")


def _literal_ok(raw: str, objects: set) -> str | None:
    """Why `raw` isn't a data literal, or None if it is."""
    if len(raw) >= 2 and raw[0] == '"' and raw[-1] == '"':
        return None
    if _NUMBER_RE.match(raw):
        if "." not in raw:
            return None if len(raw) <= 21 and -_INT_LIMIT <= int(raw) < _INT_LIMIT else \
                f"{raw[:20]}… is larger than a 64-bit integer"
        return None if math.isfinite(float(raw)) else f"{raw[:20]}… isn't a finite number"
    if raw in ("true", "false", "null"):
        return None
    if raw.startswith("[") and raw.endswith("]"):
        try:
            items = json.loads(raw)
        except (ValueError, RecursionError):
            return f"{raw[:40]} isn't a list Rosh can read"
        for item in items:
            if isinstance(item, (list, dict)):
                return "a list can't hold a list or an object"
            if isinstance(item, float) and not math.isfinite(item):
                return f"{item} isn't a finite number"
            if isinstance(item, int) and not isinstance(item, bool) and not -_INT_LIMIT <= item < _INT_LIMIT:
                return "an integer in the list is larger than 64-bit"
            if isinstance(item, str) and any(c in item for c in _LINE_BREAKS):
                return "text in a list can't hold a line break"
        return None
    ref = re.fullmatch(r"object (\S+)", raw)
    if ref:
        return None if ref.group(1) in objects else f"refers to {ref.group(1)!r}, which no earlier line created"
    return f"{raw} isn't a value: data takes quoted text, numbers, true, false, null, lists or object <name>"


def from_rosh(text: str) -> dict:
    """Read Rosh written by `to_rosh` (or by hand, within the subset) back into a document."""
    objects: list[str] = []
    for number, line in enumerate(text.splitlines(), start=1):
        stripped = _strip_inline_comment(line.strip())
        if not stripped or stripped.startswith("#"):
            continue
        if create := _CREATE_RE.fullmatch(stripped):
            name = create.group(1)
            try:
                _check_name(name, f"line {number}", object_name=True)
            except DataError as exc:
                raise DataError(str(exc)) from None
            objects.append(name)
            continue
        if found := _SET_RE.fullmatch(stripped):
            target, _prop, raw = found.groups()
            if target != "room" and target not in objects:
                raise DataError(f"line {number}: {target!r} wasn't created by an earlier line")
            why = _literal_ok(raw.strip(), set(objects))
            if target == "room" and raw.strip().startswith("object "):
                why = "a room fact can't be a reference"
            if why:
                raise DataError(f"line {number}: {why}")
            continue
        raise DataError(f"line {number}: data holds only create object, set and comments, not {stripped!r}")

    runtime = Runtime()
    try:
        runtime.run(parse_string(text, source="<data>", normalise=False))
    except Exception as exc:  # noqa: BLE001 — said with its line, not swallowed
        raise DataError(str(exc)) from None
    references = getattr(runtime, "references", {}) or {}
    meta = runtime.state.get("room") if isinstance(runtime.state.get("room"), dict) else {}
    doc_objects: dict[str, dict] = {}
    for name in objects:
        props = runtime.state.get(name)
        if not isinstance(props, dict):
            raise DataError(f"{name}: not an object after reading")
        doc_objects[name] = {prop: ({"$ref": references[f"{name}.{prop}"]}
                                    if f"{name}.{prop}" in references else value)
                             for prop, value in props.items()}
    return {"objects": doc_objects, "meta": dict(meta)}


def same(a: Any, b: Any) -> bool:
    """Equal, types included: 1 is not 1.0 is not True; null is not "null"."""
    if isinstance(a, dict) and isinstance(b, dict):   # a mapping is a mapping, subclass or not
        return a.keys() == b.keys() and all(same(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return type(a) is type(b) and a == b
