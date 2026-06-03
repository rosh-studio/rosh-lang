"""Hytopia target — generate a voxel world from a Rosh programme.

Entry points:
  render_hytopia(programme) -> dict      testable, no I/O
  serve_hytopia(programme, auto_open)    writes files, optionally starts server

Pipeline:
  .rosh → Runtime → world descriptor (rooms + objects)
       → map.json (Hytopia block format)
       → world.json (semantic descriptor for live commands)
       → optionally: start rosh-hytopia Node server
"""

from __future__ import annotations

import json
import subprocess
import webbrowser
from pathlib import Path
from typing import Any

from rosh_lang.core.model import (
    CreateStatement,
    GoStatement,
    Programme,
    SetStatement,
)

# ── Constants ────────────────────────────────────────────────────────────────

# Path to the rosh-hytopia package inside the monorepo
_PACKAGE_DIR = Path(__file__).parents[5] / "rosh-hytopia"

PLAY_URL = "https://hytopia.com/play/?join=localhost:8080"

# Block type IDs — must match rosh-hytopia/src/blocks.js
_BLOCK_TYPES = [
    {"id": 1, "name": "grass",       "textureUri": "blocks/grass-block"},
    {"id": 2, "name": "stone",       "textureUri": "blocks/stone.png"},
    {"id": 3, "name": "wood",        "textureUri": "blocks/oak-log"},
    {"id": 4, "name": "sand",        "textureUri": "blocks/sand.png"},
    {"id": 5, "name": "leaves",      "textureUri": "blocks/oak-leaves.png"},
    {"id": 6, "name": "cobblestone", "textureUri": "blocks/cobblestone.png"},
    {"id": 7, "name": "bricks",      "textureUri": "blocks/bricks.png"},
    {"id": 8, "name": "spruce",      "textureUri": "blocks/spruce-log"},
    {"id": 9, "name": "andesite",    "textureUri": "blocks/andesite.png"},
]

_MATERIAL_TO_ID: dict[str, int] = {bt["name"]: bt["id"] for bt in _BLOCK_TYPES}
_MATERIAL_TO_ID.update({
    "oak": 3, "log": 3, "rock": 2, "dirt": 1, "ground": 1,
})

ROOM_SIZE    = 16
ROOM_SPACING = 20


# ── World extraction ─────────────────────────────────────────────────────────

def _strip_quotes(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] in ('"', "'") and s[-1] == s[0]:
        return s[1:-1]
    return s


def extract_world(programme: Programme) -> dict[str, Any]:
    """Walk statements to build rooms and objects structure."""
    rooms: dict[str, dict] = {}
    objects: dict[str, dict] = {}
    current_room: str | None = None

    for stmt in programme.statements:
        if isinstance(stmt, CreateStatement) and stmt.kind.lower() == "object":
            name = stmt.name
            objects[name] = {"name": name, "room": current_room}

        elif isinstance(stmt, SetStatement):
            dot = stmt.target.find(".")
            if dot == -1:
                continue
            obj_name = stmt.target[:dot]
            prop      = stmt.target[dot + 1:]
            val       = _strip_quotes(stmt.value)

            target_dict = objects.get(obj_name) or rooms.get(obj_name)
            if target_dict is None:
                continue

            target_dict[prop] = val

            # Promote object → room when set type to room
            if obj_name in objects and prop == "type" and val == "room":
                rooms[obj_name] = objects.pop(obj_name)

        elif isinstance(stmt, GoStatement):
            dest = stmt.target
            current_room = dest
            if dest not in rooms:
                rooms[dest] = {"name": dest, "type": "room"}

    return {"rooms": rooms, "objects": objects}


# ── Map generation ────────────────────────────────────────────────────────────

def _get_material_id(name: str | None) -> int:
    if not name:
        return 2  # stone default
    return _MATERIAL_TO_ID.get(name.lower(), 2)


def build_map(world: dict) -> dict:
    """Convert a world descriptor into a Hytopia map.json structure."""
    blocks: dict[str, int] = {}
    rooms  = world["rooms"]
    objects = world["objects"]

    room_list = list(rooms.keys())

    if not room_list:
        _place_floor(blocks, 0, 0, ROOM_SIZE, ROOM_SIZE, 1)
        return {"blockTypes": _BLOCK_TYPES, "blocks": blocks}

    for idx, room_name in enumerate(room_list):
        ox = 0
        oz = idx * ROOM_SPACING
        _place_room(blocks, rooms[room_name], ox, oz)

        room_objs = [o for o in objects.values() if o.get("room") == room_name]
        for i, obj in enumerate(room_objs):
            col = i % 4
            row = i // 4
            bx  = ox + 3 + col * 3
            bz  = oz + 3 + row * 3
            _place_object(blocks, obj, bx, bz)

    return {"blockTypes": _BLOCK_TYPES, "blocks": blocks}


def _place_floor(
    blocks: dict, ox: int, oz: int, w: int, d: int, block_id: int
) -> None:
    for x in range(w):
        for z in range(d):
            blocks[f"{ox + x},0,{oz + z}"] = block_id


def _place_room(blocks: dict, _room: dict, ox: int, oz: int) -> None:
    _place_floor(blocks, ox, oz, ROOM_SIZE, ROOM_SIZE, 1)  # grass floor


def _place_object(blocks: dict, obj: dict, x: int, z: int) -> None:
    material_id = _get_material_id(obj.get("material"))
    scale       = obj.get("scale", "")
    height      = 4 if scale == "tall" else 2 if scale in ("large", "big") else 1

    for y in range(1, height + 1):
        blocks[f"{x},{y},{z}"] = material_id

    # Leaf crown for tall wood objects (trees)
    if scale == "tall" and obj.get("material") in ("wood", "oak", "log"):
        for dx in range(-1, 2):
            for dz in range(-1, 2):
                blocks[f"{x + dx},{height + 1},{z + dz}"] = 5  # leaves
        blocks[f"{x},{height + 2},{z}"] = 5


# ── Public API ────────────────────────────────────────────────────────────────

def render_hytopia(programme: Programme) -> dict:
    """Extract world + build map — no I/O, fully testable."""
    world = extract_world(programme)
    return {
        "world":    world,
        "map":      build_map(world),
    }


def serve_hytopia(programme: Programme, auto_open: bool = False) -> None:
    """Write world.json + map.json to rosh-hytopia/assets/ and optionally start server."""
    from rich.console import Console
    rc = Console()

    result = render_hytopia(programme)
    assets_dir = _PACKAGE_DIR / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    world_path = assets_dir / "world.json"
    map_path   = assets_dir / "map.json"

    world_path.write_text(json.dumps(result["world"], indent=2))
    map_path.write_text(json.dumps(result["map"], separators=(",", ":")))

    rooms   = result["world"]["rooms"]
    objects = result["world"]["objects"]
    rc.print(f"[bold magenta]Rosh → Hytopia[/]  {len(rooms)} room(s), {len(objects)} object(s)")
    rc.print(f"  wrote {world_path}")
    rc.print(f"  wrote {map_path}")

    if not _PACKAGE_DIR.exists():
        rc.print("[yellow]Warning:[/] rosh-hytopia package not found at", _PACKAGE_DIR)
        rc.print("  Clone the rosh repo to use this target locally.")
        return

    # Check npm is available
    npm = subprocess.run(["npm", "--version"], capture_output=True, text=True)
    if npm.returncode != 0:
        rc.print("[yellow]npm not found.[/] Install Node.js to start the server automatically.")
        rc.print(f"  Then: cd {_PACKAGE_DIR} && npm install && npx hytopia run server.ts")
        return

    rc.print(f"\n[bold green]Starting Hytopia server…[/]")
    rc.print(f"  Play: [cyan]{PLAY_URL}[/]")
    rc.print("  First run generates a texture atlas (~30s). Subsequent runs use the cache.\n")

    if auto_open:
        webbrowser.open(PLAY_URL)

    # npm install if needed (installs hytopia + @hytopia.com/assets)
    if not (_PACKAGE_DIR / "node_modules").exists():
        rc.print("  Installing dependencies…")
        subprocess.run(["npm", "install"], cwd=_PACKAGE_DIR, check=True)

    # Start server via hytopia CLI (compiles TS + runs)
    subprocess.run(["npx", "hytopia", "run", "server.ts"], cwd=_PACKAGE_DIR)
