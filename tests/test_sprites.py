"""Tests for the procedural pixel-art sprite generator."""

from __future__ import annotations

import base64
import struct
import zlib

from rosh_lang.media.sprites import generate_sprite, _LOGICAL_W, _LOGICAL_H


# ── PNG validity ─────────────────────────────────────────────


class TestPNGValidity:
    """Generated sprites should be valid PNG images."""

    def test_returns_data_uri(self):
        uri = generate_sprite("player", "blue spaceship")
        assert uri.startswith("data:image/png;base64,")

    def test_valid_base64(self):
        uri = generate_sprite("player", "blue spaceship")
        b64 = uri.split(",", 1)[1]
        data = base64.b64decode(b64)
        assert len(data) > 0

    def test_valid_png_signature(self):
        uri = generate_sprite("player", "blue spaceship")
        data = base64.b64decode(uri.split(",", 1)[1])
        assert data[:8] == b"\x89PNG\r\n\x1a\n"

    def test_has_ihdr_chunk(self):
        uri = generate_sprite("player", "blue spaceship")
        data = base64.b64decode(uri.split(",", 1)[1])
        assert data[12:16] == b"IHDR"

    def test_has_iend_chunk(self):
        uri = generate_sprite("player", "blue spaceship")
        data = base64.b64decode(uri.split(",", 1)[1])
        assert data[-8:-4] == b"IEND"

    def test_ihdr_dimensions(self):
        """PNG dimensions match the logical grid size."""
        uri = generate_sprite("player", "blue spaceship")
        data = base64.b64decode(uri.split(",", 1)[1])
        width, height = struct.unpack(">II", data[16:24])
        assert width == _LOGICAL_W
        assert height == _LOGICAL_H

    def test_ihdr_rgba_color_type(self):
        uri = generate_sprite("player", "blue spaceship")
        data = base64.b64decode(uri.split(",", 1)[1])
        bit_depth = data[24]
        color_type = data[25]
        assert bit_depth == 8
        assert color_type == 6  # RGBA

    def test_pixels_decompressible(self):
        """IDAT chunk should decompress to valid pixel data."""
        uri = generate_sprite("player", "blue spaceship")
        data = base64.b64decode(uri.split(",", 1)[1])
        offset = 8
        while offset < len(data):
            length = struct.unpack(">I", data[offset : offset + 4])[0]
            chunk_type = data[offset + 4 : offset + 8]
            if chunk_type == b"IDAT":
                compressed = data[offset + 8 : offset + 8 + length]
                raw = zlib.decompress(compressed)
                # H rows × (1 filter byte + W×4 RGBA)
                expected = _LOGICAL_H * (1 + _LOGICAL_W * 4)
                assert len(raw) == expected
                break
            offset += 12 + length


# ── Determinism ──────────────────────────────────────────────


class TestDeterminism:
    """Same name should always produce the same sprite."""

    def test_same_name_same_output(self):
        a = generate_sprite("player", "blue spaceship")
        b = generate_sprite("player", "blue spaceship")
        assert a == b

    def test_same_name_different_description_same_shape(self):
        """Shape is seeded by name only — description changes color but not shape."""
        a = generate_sprite("player", "blue spaceship")
        b = generate_sprite("player", "red spaceship")
        assert a != b
        assert a.startswith("data:image/png;base64,")
        assert b.startswith("data:image/png;base64,")

    def test_different_name_different_output(self):
        a = generate_sprite("player", "blue spaceship")
        b = generate_sprite("enemy", "blue spaceship")
        assert a != b

    def test_empty_description(self):
        uri = generate_sprite("player")
        assert uri.startswith("data:image/png;base64,")

    def test_empty_description_deterministic(self):
        a = generate_sprite("player")
        b = generate_sprite("player")
        assert a == b


# ── Color extraction ─────────────────────────────────────────


class TestColorExtraction:
    """Description keywords should influence sprite color."""

    def test_blue_keyword(self):
        a = generate_sprite("test", "blue spaceship")
        b = generate_sprite("test", "red spaceship")
        assert a != b

    def test_color_keywords_all_valid(self):
        for color in [
            "red", "blue", "green", "yellow", "gold", "orange",
            "purple", "pink", "white", "black", "gray", "cyan",
            "teal", "brown",
        ]:
            uri = generate_sprite("test_obj", f"{color} thing")
            assert uri.startswith("data:image/png;base64,"), f"Failed for {color}"

    def test_no_color_keyword_still_works(self):
        uri = generate_sprite("player", "spaceship")
        assert uri.startswith("data:image/png;base64,")


# ── Symmetry ─────────────────────────────────────────────────


class TestSymmetry:
    """Sprites should be bilaterally symmetric."""

    def _get_pixels(self, uri: str) -> list[list[tuple[int, int, int, int]]]:
        """Decode PNG pixel data."""
        data = base64.b64decode(uri.split(",", 1)[1])
        w, h = struct.unpack(">II", data[16:24])
        offset = 8
        while offset < len(data):
            length = struct.unpack(">I", data[offset : offset + 4])[0]
            chunk_type = data[offset + 4 : offset + 8]
            if chunk_type == b"IDAT":
                compressed = data[offset + 8 : offset + 8 + length]
                raw = zlib.decompress(compressed)
                rows: list[list[tuple[int, int, int, int]]] = []
                for r in range(h):
                    row_start = r * (1 + w * 4) + 1
                    row: list[tuple[int, int, int, int]] = []
                    for c in range(w):
                        px_start = row_start + c * 4
                        row.append((raw[px_start], raw[px_start + 1],
                                    raw[px_start + 2], raw[px_start + 3]))
                    rows.append(row)
                return rows
            offset += 12 + length
        return []

    def test_horizontal_symmetry(self):
        uri = generate_sprite("player", "blue spaceship")
        pixels = self._get_pixels(uri)
        for row_idx, row in enumerate(pixels):
            for i in range(len(row) // 2):
                assert row[i] == row[-(i + 1)], (
                    f"Row {row_idx} asymmetric at column {i}"
                )

    def test_has_transparent_pixels(self):
        uri = generate_sprite("player", "blue spaceship")
        pixels = self._get_pixels(uri)
        has_transparent = any(
            px[3] == 0 for row in pixels for px in row
        )
        assert has_transparent, "Sprite has no transparent pixels"

    def test_has_opaque_pixels(self):
        uri = generate_sprite("player", "blue spaceship")
        pixels = self._get_pixels(uri)
        has_opaque = any(
            px[3] == 255 for row in pixels for px in row
        )
        assert has_opaque, "Sprite has no opaque pixels"

    def test_has_body_and_outline_pixels(self):
        """Sprite should have both body (bright) and outline (dark) pixels."""
        uri = generate_sprite("player", "blue spaceship")
        pixels = self._get_pixels(uri)
        colors = set()
        for row in pixels:
            for px in row:
                if px[3] == 255:
                    colors.add(px[:3])
        # At least 2 distinct opaque colors (body + outline)
        assert len(colors) >= 2, "Expected body and outline colors"


# ── Output size ──────────────────────────────────────────────


class TestOutputSize:
    """Data URIs should be small — tiny logical grid, CSS does the scaling."""

    def test_small_data_uri(self):
        """A 7x9 sprite should be well under 1KB as base64."""
        uri = generate_sprite("player", "blue spaceship")
        assert len(uri) < 1024

    def test_many_sprites_reasonable(self):
        """Different sprites should all be small."""
        for name in ["player", "enemy", "bullet", "gem", "ship", "boss"]:
            uri = generate_sprite(name, "blue thing")
            assert len(uri) < 1024, f"Sprite for {name} too large"
