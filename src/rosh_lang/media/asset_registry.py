# licence: MIT
"""Semantic asset registry for bundled and project-provided assets."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import json
from pathlib import Path
import re
from typing import Any, Iterable


REQUIRED_FIELDS = {
    "id",
    "name",
    "version",
    "description",
    "licence",
    "source",
    "visibility",
    "tags",
    "representations",
}


class AssetManifestError(ValueError):
    """Raised when an asset manifest is missing required data."""


@dataclass(frozen=True)
class Asset:
    """A semantic asset entry with optional renderer-specific representations."""

    id: str
    name: str
    version: str
    description: str
    licence: str
    source: str
    visibility: str
    tags: tuple[str, ...]
    aliases: tuple[str, ...] = ()
    review_status: str = "needs_review"
    author: str = ""
    copyright: str = ""
    provenance: dict[str, Any] = field(default_factory=dict)
    semantic: dict[str, Any] = field(default_factory=dict)
    defaults: dict[str, Any] = field(default_factory=dict)
    representations: dict[str, Any] = field(default_factory=dict)
    manifest_path: Path | None = None

    def representation(self, target: str) -> dict[str, Any] | None:
        """Return representation metadata for a renderer or surface."""
        value = self.representations.get(target)
        return value if isinstance(value, dict) else None


@dataclass(frozen=True)
class AssetMatch:
    """A registry lookup result with a human-readable reason."""

    asset: Asset
    reason: str


class AssetRegistry:
    """In-memory index of semantic assets."""

    def __init__(self, assets: list[Asset] | tuple[Asset, ...]) -> None:
        self.assets = tuple(assets)
        self._by_id = {asset.id: asset for asset in self.assets}
        if len(self._by_id) != len(self.assets):
            raise AssetManifestError("Duplicate asset id in registry")

    @classmethod
    def from_directory(cls, path: Path) -> "AssetRegistry":
        """Load all JSON manifests in a directory."""
        assets = [
            load_asset_manifest(manifest)
            for manifest in sorted(path.glob("*.json"))
        ]
        return cls(assets)

    def get(self, asset_id: str) -> Asset | None:
        """Return an asset by id."""
        return self._by_id.get(asset_id)

    def find(
        self,
        phrase: str,
        *,
        visible_to: Iterable[str] | None = ("featured", "public"),
    ) -> AssetMatch | None:
        """Find the best asset for a user phrase.

        Matching is intentionally conservative for the first cut:
        id/name/alias matches beat tag matches, and all matching is normalized
        with punctuation collapsed to spaces.
        """
        query = _normalise(phrase)
        if not query:
            return None

        candidates = self._visible_assets(visible_to)

        for asset in candidates:
            if query == _normalise(asset.id):
                return AssetMatch(asset, "id")
            if query == _normalise(asset.name):
                return AssetMatch(asset, "name")
            if query in {_normalise(alias) for alias in asset.aliases}:
                return AssetMatch(asset, "alias")

        query_tokens = set(query.split())
        best: tuple[int, Asset, str] | None = None
        for asset in candidates:
            labels = [asset.name, *asset.aliases, *asset.tags]
            for label in labels:
                label_norm = _normalise(label)
                if not label_norm:
                    continue
                label_tokens = set(label_norm.split())
                if query == label_norm:
                    score = 100
                elif label_norm in query or query in label_norm:
                    score = 50 - abs(len(label_tokens) - len(query_tokens))
                else:
                    overlap = query_tokens & label_tokens
                    if not overlap:
                        continue
                    score = len(overlap) / max(len(label_tokens), len(query_tokens))
                if best is None or score > best[0]:
                    best = (score, asset, f"semantic match: {label}")

        if best is None:
            return None
        return AssetMatch(best[1], best[2])

    def find_by_tag(
        self,
        tag: str,
        *,
        visible_to: Iterable[str] | None = ("featured", "public"),
    ) -> list[Asset]:
        """Return assets whose tags include the given tag."""
        needle = _normalise(tag)
        return [
            asset for asset in self._visible_assets(visible_to)
            if needle in {_normalise(item) for item in asset.tags}
        ]

    def _visible_assets(self, visible_to: Iterable[str] | None) -> tuple[Asset, ...]:
        if visible_to is None:
            return self.assets
        allowed = {item.strip().lower() for item in visible_to}
        return tuple(
            asset for asset in self.assets
            if asset.visibility.strip().lower() in allowed
        )


def get_bundled_manifest_path() -> Path:
    """Return the bundled semantic asset manifest directory."""
    return Path(__file__).parent / "asset_manifests"


@lru_cache(maxsize=1)
def load_bundled_registry() -> AssetRegistry:
    """Load the default semantic asset registry shipped with rosh-lang."""
    return AssetRegistry.from_directory(get_bundled_manifest_path())


def load_asset_manifest(path: Path) -> Asset:
    """Load and validate a single asset manifest."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AssetManifestError(f"{path}: invalid JSON: {exc}") from exc

    missing = REQUIRED_FIELDS - set(data)
    if missing:
        fields = ", ".join(sorted(missing))
        raise AssetManifestError(f"{path}: missing required fields: {fields}")

    tags = _string_tuple(data["tags"], "tags", path)
    aliases = _string_tuple(data["aliases"], "aliases", path) if data.get("aliases") else ()
    representations = data["representations"]
    if not isinstance(representations, dict) or not representations:
        raise AssetManifestError(f"{path}: representations must be a non-empty object")

    licence = _required_string(data, "licence", path)
    if not licence:
        raise AssetManifestError(f"{path}: licence must not be empty")
    source = _required_string(data, "source", path)
    author = _optional_string(data, "author", path)
    copyright_notice = _optional_string(data, "copyright", path)
    if source != "bundled" and (not author or not copyright_notice):
        raise AssetManifestError(
            f"{path}: author and copyright are required when source is not bundled"
        )

    return Asset(
        id=_required_string(data, "id", path),
        name=_required_string(data, "name", path),
        version=_required_string(data, "version", path),
        description=_required_string(data, "description", path),
        licence=licence,
        source=source,
        visibility=_required_string(data, "visibility", path),
        tags=tags,
        aliases=aliases,
        review_status=_optional_string(data, "review_status", path) or "needs_review",
        author=author,
        copyright=copyright_notice,
        provenance=_dict_field(data.get("provenance", {}), "provenance", path),
        semantic=_dict_field(data.get("semantic", {}), "semantic", path),
        defaults=_dict_field(data.get("defaults", {}), "defaults", path),
        representations=representations,
        manifest_path=path,
    )


def _required_string(data: dict[str, Any], key: str, path: Path) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise AssetManifestError(f"{path}: {key} must be a non-empty string")
    return value.strip()


def _optional_string(data: dict[str, Any], key: str, path: Path) -> str:
    value = data.get(key, "")
    if value is None:
        return ""
    if not isinstance(value, str):
        raise AssetManifestError(f"{path}: {key} must be a string")
    return value.strip()


def _string_tuple(value: Any, key: str, path: Path) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise AssetManifestError(f"{path}: {key} must be a non-empty list")
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise AssetManifestError(f"{path}: {key} must contain non-empty strings")
    return tuple(item.strip() for item in value)


def _dict_field(value: Any, key: str, path: Path) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AssetManifestError(f"{path}: {key} must be an object")
    return value


def normalise_asset_text(value: str) -> str:
    """Normalize asset names, tags, and user queries for matching."""
    lowered = value.replace("_", " ").replace("-", " ").lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", lowered)).strip()


def _normalise(value: str) -> str:
    return normalise_asset_text(value)
