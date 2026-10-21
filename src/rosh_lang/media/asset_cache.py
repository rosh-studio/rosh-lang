# licence: MIT
"""Local 3D asset cache — downloaded GLB/GLTF files stored at ~/.rosh/cache/3d/."""

from __future__ import annotations

from pathlib import Path


_CACHE_ROOT = Path.home() / ".rosh" / "cache" / "3d"


def get_cache_dir() -> Path:
    """Return the local 3D model cache directory, creating it if needed."""
    _CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    return _CACHE_ROOT


def cached_path(asset_id: str, ext: str = "glb") -> Path:
    """Return the expected cache path for *asset_id*, without creating it."""
    safe_id = _safe_id(asset_id)
    return get_cache_dir() / f"{safe_id}.{ext}"


def cache_asset(asset_id: str, data: bytes, ext: str = "glb") -> Path:
    """Write *data* to the cache under *asset_id* and return the path."""
    path = cached_path(asset_id, ext)
    path.write_bytes(data)
    return path


def is_cached(asset_id: str, ext: str = "glb") -> bool:
    return cached_path(asset_id, ext).exists()


def list_cached() -> list[tuple[str, int]]:
    """Return (filename, size_bytes) pairs for every file in the cache."""
    cache_dir = get_cache_dir()
    return sorted(
        (f.name, f.stat().st_size)
        for f in cache_dir.iterdir()
        if f.is_file()
    )


def clear_cache() -> int:
    """Delete all cached assets. Returns the number of files removed."""
    cache_dir = get_cache_dir()
    count = 0
    for f in cache_dir.iterdir():
        if f.is_file():
            f.unlink()
            count += 1
    return count


def _safe_id(asset_id: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in asset_id)
