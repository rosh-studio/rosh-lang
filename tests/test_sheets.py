"""Tests for the spritesheet slicer."""

from __future__ import annotations

import base64
import struct
import zlib
from pathlib import Path

import pytest

from rosh_lang.media.assets import get_bundled_assets_path
from rosh_lang.media.sheets import slice_spritesheet


def _make_test_png(width: int, height: int, color: tuple[int, int, int, int] = (255, 0, 0, 255)) -> bytes:
    """Create a minimal RGBA PNG file with a solid color."""

    def _chunk(chunk_type: bytes, data: bytes) -> bytes:
        c = chunk_type + data
        crc = zlib.crc32(c) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + c + struct.pack(">I", crc)

    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)

    raw_rows = b""
    for _ in range(height):
        raw_rows += b"\x00"  # filter: None
        for _ in range(width):
            raw_rows += struct.pack("BBBB", *color)

    idat_data = zlib.compress(raw_rows)

    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", ihdr_data)
    png += _chunk(b"IDAT", idat_data)
    png += _chunk(b"IEND", b"")
    return png


class TestSliceSpritesheet:
    def test_basic_slice(self, tmp_path: Path) -> None:
        """Slice a 4-frame strip into 4 individual frames."""
        png = _make_test_png(40, 10)
        path = tmp_path / "strip.png"
        path.write_bytes(png)

        frames = slice_spritesheet(path, 4)
        assert len(frames) == 4
        for frame in frames:
            assert frame.startswith("data:image/png;base64,")

    def test_single_frame(self, tmp_path: Path) -> None:
        """Slice with frame_count=1 returns the whole image."""
        png = _make_test_png(10, 10)
        path = tmp_path / "single.png"
        path.write_bytes(png)

        frames = slice_spritesheet(path, 1)
        assert len(frames) == 1

    def test_two_frames(self, tmp_path: Path) -> None:
        """Slice a 2-frame strip."""
        png = _make_test_png(20, 10)
        path = tmp_path / "two.png"
        path.write_bytes(png)

        frames = slice_spritesheet(path, 2)
        assert len(frames) == 2
        # Both frames should be valid base64 PNGs
        for frame in frames:
            b64_data = frame.split(",", 1)[1]
            raw = base64.b64decode(b64_data)
            assert raw[:8] == b"\x89PNG\r\n\x1a\n"

    def test_invalid_frame_count(self, tmp_path: Path) -> None:
        """frame_count=0 raises ValueError."""
        png = _make_test_png(10, 10)
        path = tmp_path / "test.png"
        path.write_bytes(png)

        with pytest.raises(ValueError, match="frame_count must be >= 1"):
            slice_spritesheet(path, 0)

    def test_width_not_divisible(self, tmp_path: Path) -> None:
        """Width not divisible by frame_count raises ValueError."""
        png = _make_test_png(10, 10)
        path = tmp_path / "odd.png"
        path.write_bytes(png)

        with pytest.raises(ValueError, match="not divisible"):
            slice_spritesheet(path, 3)

    def test_file_not_found(self, tmp_path: Path) -> None:
        """Missing file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            slice_spritesheet(tmp_path / "missing.png", 4)

    def test_real_spritesheet(self) -> None:
        """Test with the bundled player-sheet.png if available."""
        sheet_path = get_bundled_assets_path() / "player-sheet.png"
        if not sheet_path.exists():
            pytest.skip("player-sheet.png not found")

        frames = slice_spritesheet(sheet_path, 4)
        assert len(frames) == 4
        for frame in frames:
            assert frame.startswith("data:image/png;base64,")
            # Each frame should be a reasonable size
            assert len(frame) > 100
