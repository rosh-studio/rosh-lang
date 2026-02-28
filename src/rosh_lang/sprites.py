"""Procedural pixel-art sprite generator.

Turns a name + description into a deterministic data:image/png;base64,…
URI. No external dependencies — uses struct + zlib for raw PNG encoding.

Algorithm (per zfedoran/pixel-sprite-generator pattern):
  1. Hash name → seed a Random instance (deterministic).
  2. Parse color from description keywords; fall back to hash-derived color.
  3. Generate a small logical grid (7 wide × 9 tall) with graduated
     fill probability — center columns dense, edges sparse.
  4. Mirror the left half for bilateral symmetry.
  5. Detect edges (empty cells adjacent to filled) → outline color.
  6. Scale up each logical cell into chunky pixel blocks.
  7. Encode as RGBA PNG with transparent background.

Each sprite is ~500-1500 bytes as base64. Use `image-rendering: pixelated`
CSS to keep it crisp at any scale.
"""

from __future__ import annotations

import base64
import hashlib
import random
import struct
import zlib

# ── Color table ───────────────────────────────────────────────

_COLOR_MAP: dict[str, tuple[int, int, int]] = {
    "red": (231, 76, 60),
    "blue": (52, 152, 219),
    "green": (46, 204, 113),
    "yellow": (241, 196, 15),
    "gold": (243, 156, 18),
    "orange": (230, 126, 34),
    "purple": (155, 89, 182),
    "pink": (232, 67, 147),
    "white": (236, 240, 241),
    "black": (44, 62, 80),
    "gray": (149, 165, 166),
    "grey": (149, 165, 166),
    "cyan": (26, 188, 156),
    "teal": (0, 206, 209),
    "brown": (160, 106, 66),
}


def _extract_color(
    description: str, rng: random.Random
) -> tuple[int, int, int]:
    """Extract a color from the description, or derive one from the RNG."""
    desc_lower = description.lower()
    for keyword, rgb in _COLOR_MAP.items():
        if keyword in desc_lower:
            return rgb
    # Derive a vibrant color from the RNG
    h = rng.random()
    # HSV → RGB with S=0.7, V=0.85 for vibrant but not neon colors
    s, v = 0.7, 0.85
    return _hsv_to_rgb(h, s, v)


def _hsv_to_rgb(h: float, s: float, v: float) -> tuple[int, int, int]:
    """Convert HSV (0-1 range) to RGB (0-255 range)."""
    if s == 0.0:
        r = g = b = int(v * 255)
        return (r, g, b)
    i = int(h * 6.0)
    f = (h * 6.0) - i
    p = v * (1.0 - s)
    q = v * (1.0 - s * f)
    t = v * (1.0 - s * (1.0 - f))
    i %= 6
    if i == 0:
        r, g, b = v, t, p
    elif i == 1:
        r, g, b = q, v, p
    elif i == 2:
        r, g, b = p, v, t
    elif i == 3:
        r, g, b = p, q, v
    elif i == 4:
        r, g, b = t, p, v
    else:
        r, g, b = v, p, q
    return (int(r * 255), int(g * 255), int(b * 255))


# ── Logical grid dimensions ──────────────────────────────────

# Small logical grid → scaled up to output size for chunky pixel art.
# 7 wide (half=4) × 9 tall is the sweet spot — recognisable shapes
# like the classic space invader generators.
_LOGICAL_W = 7  # columns after mirror (half = 4)
_LOGICAL_H = 9  # rows

# Fill probability per half-column (index 0 = center, 3 = edge).
# Center is dense, edges are sparse → body-shaped silhouettes.
_FILL_PROB = [0.7, 0.55, 0.35, 0.2]

# Top/bottom rows are sparser for head/feet shaping.
_ROW_WEIGHT = [0.3, 0.6, 0.8, 1.0, 1.0, 1.0, 0.8, 0.6, 0.3]


# ── Grid generation ───────────────────────────────────────────


def _generate_grid(rng: random.Random) -> list[list[bool]]:
    """Generate a bilaterally symmetric logical grid.

    Uses graduated fill probability (center dense, edges sparse)
    with row weighting (top/bottom sparse) to produce body-shaped
    silhouettes. Generates half-width, then mirrors.
    """
    half_w = (_LOGICAL_W + 1) // 2  # 4

    grid: list[list[bool]] = []
    for row_idx in range(_LOGICAL_H):
        row_w = _ROW_WEIGHT[row_idx]
        row: list[bool] = []
        for col_idx in range(half_w):
            prob = _FILL_PROB[col_idx] * row_w
            row.append(rng.random() < prob)
        grid.append(row)

    # Mirror to full width (odd: center column not duplicated)
    full_grid: list[list[bool]] = []
    for row in grid:
        # row = [center, col1, col2, edge]
        # mirror: [edge, col2, col1, center, col1, col2, edge]
        full_row = row[::-1] + row[1:]
        full_grid.append(full_row)

    return full_grid


def _has_filled_neighbor(
    grid: list[list[bool]], r: int, c: int, rows: int, cols: int
) -> bool:
    """Check if any adjacent cell is filled (for outline detection)."""
    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        nr, nc = r + dr, c + dc
        if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc]:
            return True
    return False


# ── PNG encoding ──────────────────────────────────────────────


def _make_png(
    pixels: list[list[tuple[int, int, int, int]]], width: int, height: int
) -> bytes:
    """Encode RGBA pixel data as a PNG file (no Pillow needed).

    Minimal valid PNG: signature + IHDR + IDAT + IEND.
    """

    def _chunk(chunk_type: bytes, data: bytes) -> bytes:
        c = chunk_type + data
        crc = zlib.crc32(c) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + c + struct.pack(">I", crc)

    # IHDR: width, height, bit_depth=8, color_type=6 (RGBA)
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)

    # IDAT: raw pixel rows, each prefixed with filter byte 0 (None)
    raw_rows = b""
    for row in pixels:
        raw_rows += b"\x00"  # filter: None
        for r, g, b, a in row:
            raw_rows += struct.pack("BBBB", r, g, b, a)

    idat_data = zlib.compress(raw_rows)

    png = b"\x89PNG\r\n\x1a\n"  # PNG signature
    png += _chunk(b"IHDR", ihdr_data)
    png += _chunk(b"IDAT", idat_data)
    png += _chunk(b"IEND", b"")

    return png


# ── Public API ────────────────────────────────────────────────


def generate_sprite(name: str, description: str = "") -> str:
    """Generate a procedural pixel-art sprite as a data URI.

    The PNG is output at the logical grid size (7x9). CSS
    ``image-rendering: pixelated`` with ``background-size: 100% 100%``
    handles upscaling in the browser via nearest-neighbour — crisp
    and guaranteed symmetric.

    Args:
        name: Object name — used as seed for deterministic generation.
        description: Optional description for color hints
                     (e.g. "blue spaceship", "red alien").

    Returns:
        A ``data:image/png;base64,...`` string ready for CSS background-image.
    """
    # Seed RNG deterministically from the name
    digest = hashlib.md5(name.encode("utf-8")).hexdigest()
    rng = random.Random(digest)

    color = _extract_color(description, rng)
    grid = _generate_grid(rng)

    # Darken color for outline
    outline = (max(0, color[0] - 60), max(0, color[1] - 60), max(0, color[2] - 60))

    # Build RGBA pixel array at logical grid size
    pixels: list[list[tuple[int, int, int, int]]] = []
    for r in range(_LOGICAL_H):
        px_row: list[tuple[int, int, int, int]] = []
        for c in range(_LOGICAL_W):
            if grid[r][c]:
                px_row.append((*color, 255))
            elif _has_filled_neighbor(grid, r, c, _LOGICAL_H, _LOGICAL_W):
                px_row.append((*outline, 255))
            else:
                px_row.append((0, 0, 0, 0))
        pixels.append(px_row)

    png_bytes = _make_png(pixels, _LOGICAL_W, _LOGICAL_H)
    b64 = base64.b64encode(png_bytes).decode("ascii")
    return f"data:image/png;base64,{b64}"
