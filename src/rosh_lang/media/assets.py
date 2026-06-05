# licence: MIT
"""Asset file resolution — find spritesheets and other assets.

Search order mirrors widget resolution:
1. Relative to source .rosh file directory
2. ./assets/ subdirectory of source file
3. Each path in search_paths list
4. Bundled assets: rosh_lang/media/assets/ package directory
"""

from __future__ import annotations

from pathlib import Path


def get_bundled_assets_path() -> Path:
    """Return the path to the bundled assets shipped with rosh-lang."""
    return Path(__file__).parent / "assets"


def resolve_asset(
    name: str,
    search_paths: list[Path] | None = None,
    source_dir: Path | None = None,
) -> Path | None:
    """Find an asset file by name across search paths.

    Args:
        name: Filename or relative path to the asset.
        search_paths: Additional directories to search.
        source_dir: Directory of the source .rosh file (highest priority).

    Returns:
        Path to the asset file, or None if not found.
    """
    candidates: list[Path] = []

    # 1. Relative to source file directory
    if source_dir is not None:
        candidates.append(source_dir / name)
        candidates.append(source_dir / "assets" / name)

    # 2. Each path in search_paths
    if search_paths:
        for sp in search_paths:
            candidates.append(sp / name)

    # 3. Bundled assets
    candidates.append(get_bundled_assets_path() / name)

    for path in candidates:
        if path.is_file():
            return path

    return None
