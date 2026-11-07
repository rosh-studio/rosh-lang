"""Make good/museum.json: the museum as the portal seeds it, kept to the data subset.

Run from rosh-lang:  uv run python tests/fixtures/faithful/make_museum.py
Regenerate only on purpose (Task 19). What doesn't fit the subset is listed in
museum.dropped.txt, so the snapshot says what it left out.
"""

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).parent
PORTAL = HERE.parents[3] / "rosh-portal"
sys.path.insert(0, str(PORTAL))
os.environ.pop("DATABASE_URL", None)
os.environ.setdefault("SECRET_KEY", "fixture-only")

import main  # noqa: E402  (the portal, for its template and its seeding)
from rosh_lang.core.runtime import Runtime  # noqa: E402
from rosh_lang.data import DataError, to_rosh  # noqa: E402

runtime = Runtime()
meta: dict = {}
main._seed_runtime_from_world_code(runtime, main.PLAY_WORLDS_CONFIG["museum"]["code"], meta)
references = getattr(runtime, "references", {}) or {}

objects, dropped = {}, []
for name, record in runtime.state.items():
    if name.startswith("_") or not isinstance(record, dict):
        continue
    props = {}
    for prop, value in record.items():
        ref = references.get(f"{name}.{prop}")
        candidate = {"$ref": ref} if ref else value
        try:
            to_rosh({"objects": {name: {prop: candidate}, **({ref: {}} if ref else {})}, "meta": {}})
        except DataError as exc:
            dropped.append(f"{name}.{prop}: {exc}")
            continue
        props[prop] = candidate
    try:
        to_rosh({"objects": {name: {}}, "meta": {}})
    except DataError as exc:
        dropped.append(f"{name}: {exc}")
        continue
    objects[name] = props
facts = {}
for fact, value in meta.items():
    try:
        to_rosh({"objects": {}, "meta": {fact: value}})
        facts[fact] = value
    except DataError as exc:
        dropped.append(f"room.{fact}: {exc}")

doc = {"objects": objects, "meta": facts}
to_rosh(doc)  # the whole snapshot must be writable
(HERE / "good" / "museum.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
(HERE / "museum.dropped.txt").write_text("".join(f"{line}\n" for line in dropped) or "(nothing dropped)\n")
print(f"{len(objects)} objects, {len(facts)} facts, {len(dropped)} dropped")
