# licence: MIT
"""Spritesheet slicer — horizontal-strip PNG → list of per-frame data URIs.

Pure Python, no external dependencies (struct + zlib, mirrors sprites.py).
Supports 8-bit and 16-bit RGB/RGBA PNG spritesheets.
"""

from __future__ import annotations

import base64
import struct
import zlib
from pathlib import Path


def slice_spritesheet(path: Path | str, frame_count: int) -> list[str]:
    """Read a horizontal-strip PNG spritesheet, return per-frame data URIs.

    Args:
        path: Path to the spritesheet PNG file.
        frame_count: Number of equal-width frames in the horizontal strip.

    Returns:
        List of ``data:image/png;base64,...`` strings, one per frame.

    Raises:
        ValueError: If frame_count < 1 or image width not divisible by frame_count.
        FileNotFoundError: If the file doesn't exist.
    """
    path = Path(path)
    if frame_count < 1:
        raise ValueError("frame_count must be >= 1")

    raw = path.read_bytes()
    width, height, bit_depth, color_type, pixels = _decode_png(raw)

    if width % frame_count != 0:
        raise ValueError(
            f"Image width {width} not divisible by frame_count {frame_count}"
        )

    frame_width = width // frame_count
    frames: list[str] = []

    for f in range(frame_count):
        x_start = f * frame_width
        frame_pixels = _extract_frame(pixels, width, height, x_start, frame_width, color_type, bit_depth)
        png_bytes = _encode_png(frame_pixels, frame_width, height)
        b64 = base64.b64encode(png_bytes).decode("ascii")
        frames.append(f"data:image/png;base64,{b64}")

    return frames


# ── PNG decoder (minimal, read-only) ──────────────────────────


def _decode_png(data: bytes) -> tuple[int, int, int, int, list[list[tuple[int, ...]]]]:
    """Decode a PNG file into pixel rows.

    Returns: (width, height, bit_depth, color_type, pixels)
    where pixels is a list of rows, each row a list of RGBA tuples (0-255).
    """
    # Verify PNG signature
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Not a valid PNG file")

    pos = 8
    width = height = bit_depth = color_type = 0
    idat_chunks: list[bytes] = []

    while pos < len(data):
        length = struct.unpack(">I", data[pos : pos + 4])[0]
        chunk_type = data[pos + 4 : pos + 8]
        chunk_data = data[pos + 8 : pos + 8 + length]
        pos += 12 + length  # 4 (len) + 4 (type) + data + 4 (crc)

        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type = struct.unpack(
                ">IIBB", chunk_data[:10]
            )
        elif chunk_type == b"IDAT":
            idat_chunks.append(chunk_data)
        elif chunk_type == b"IEND":
            break

    if width == 0 or height == 0:
        raise ValueError("Missing IHDR chunk")

    # Decompress all IDAT data
    raw_data = zlib.decompress(b"".join(idat_chunks))

    # Determine bytes per pixel based on color type and bit depth
    channels = {0: 1, 2: 3, 4: 2, 6: 4}.get(color_type)
    if channels is None:
        raise ValueError(f"Unsupported color type: {color_type}")

    bytes_per_channel = bit_depth // 8
    bpp = channels * bytes_per_channel
    stride = width * bpp + 1  # +1 for filter byte

    # Reconstruct scanlines with filter reversal
    pixels: list[list[tuple[int, ...]]] = []
    prev_row_bytes = b"\x00" * (width * bpp)

    for y in range(height):
        row_start = y * stride
        filter_byte = raw_data[row_start]
        scanline = bytearray(raw_data[row_start + 1 : row_start + stride])

        _unfilter(scanline, prev_row_bytes, bpp, filter_byte)
        prev_row_bytes = bytes(scanline)

        # Parse pixels from scanline
        row: list[tuple[int, ...]] = []
        for x in range(width):
            offset = x * bpp
            if bytes_per_channel == 1:
                components = tuple(scanline[offset : offset + channels])
            else:
                # 16-bit: read as big-endian, scale to 8-bit
                components = tuple(
                    struct.unpack(">H", scanline[offset + c * 2 : offset + c * 2 + 2])[0] >> 8
                    for c in range(channels)
                )

            # Normalize to RGBA
            if color_type == 0:  # Grayscale
                g = components[0]
                row.append((g, g, g, 255))
            elif color_type == 2:  # RGB
                row.append((components[0], components[1], components[2], 255))
            elif color_type == 4:  # Grayscale + Alpha
                g = components[0]
                row.append((g, g, g, components[1]))
            elif color_type == 6:  # RGBA
                row.append(components)

        pixels.append(row)

    return width, height, bit_depth, color_type, pixels


def _unfilter(
    scanline: bytearray, prev_row: bytes, bpp: int, filter_type: int
) -> None:
    """Reverse PNG scanline filter in-place."""
    row_len = len(scanline)

    if filter_type == 0:  # None
        return
    elif filter_type == 1:  # Sub
        for i in range(bpp, row_len):
            scanline[i] = (scanline[i] + scanline[i - bpp]) & 0xFF
    elif filter_type == 2:  # Up
        for i in range(row_len):
            scanline[i] = (scanline[i] + prev_row[i]) & 0xFF
    elif filter_type == 3:  # Average
        for i in range(row_len):
            a = scanline[i - bpp] if i >= bpp else 0
            b = prev_row[i]
            scanline[i] = (scanline[i] + (a + b) // 2) & 0xFF
    elif filter_type == 4:  # Paeth
        for i in range(row_len):
            a = scanline[i - bpp] if i >= bpp else 0
            b = prev_row[i]
            c = prev_row[i - bpp] if i >= bpp else 0
            scanline[i] = (scanline[i] + _paeth_predictor(a, b, c)) & 0xFF


def _paeth_predictor(a: int, b: int, c: int) -> int:
    """Paeth predictor function (PNG spec)."""
    p = a + b - c
    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


# ── Frame extraction ──────────────────────────────────────────


def _extract_frame(
    pixels: list[list[tuple[int, ...]]],
    full_width: int,
    height: int,
    x_start: int,
    frame_width: int,
    color_type: int,
    bit_depth: int,
) -> list[list[tuple[int, ...]]]:
    """Extract a rectangular frame from the decoded pixel grid."""
    frame: list[list[tuple[int, ...]]] = []
    for row in pixels:
        frame.append(row[x_start : x_start + frame_width])
    return frame


# ── PNG encoder ───────────────────────────────────────────────


def _encode_png(
    pixels: list[list[tuple[int, ...]]],
    width: int,
    height: int,
) -> bytes:
    """Encode RGBA pixel data as a PNG file. Always outputs 8-bit RGBA."""

    def _chunk(chunk_type: bytes, data: bytes) -> bytes:
        c = chunk_type + data
        crc = zlib.crc32(c) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + c + struct.pack(">I", crc)

    # IHDR: 8-bit RGBA
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)

    # IDAT: raw pixel rows with filter byte 0 (None)
    raw_rows = b""
    for row in pixels:
        raw_rows += b"\x00"
        for pixel in row:
            r, g, b, a = pixel[0], pixel[1], pixel[2], pixel[3] if len(pixel) > 3 else 255
            raw_rows += struct.pack("BBBB", r, g, b, a)

    idat_data = zlib.compress(raw_rows)

    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", ihdr_data)
    png += _chunk(b"IDAT", idat_data)
    png += _chunk(b"IEND", b"")
    return png
