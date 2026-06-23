"""Tests for the semantic asset registry."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from rosh_lang.media.asset_registry import (
    AssetManifestError,
    AssetRegistry,
    load_asset_manifest,
    load_bundled_registry,
)


def _write_manifest(path: Path, **overrides: object) -> Path:
    data: dict[str, object] = {
        "id": "test_asset",
        "name": "Test Asset",
        "version": "0.1",
        "description": "A test asset.",
        "licence": "MIT",
        "source": "test",
        "author": "Test Author",
        "copyright": "Copyright (c) Test Author",
        "visibility": "private",
        "review_status": "needs_review",
        "tags": ["test", "asset"],
        "aliases": ["sample asset"],
        "representations": {
            "text": {"description": "A test asset is here."},
            "threejs": {"fallback_shape": "box"},
        },
    }
    data.update(overrides)
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_loads_bundled_registry():
    registry = load_bundled_registry()

    assert len(registry.assets) >= 10
    assert registry.get("stone") is not None


def test_bundled_assets_have_licences_and_representations():
    registry = load_bundled_registry()

    for asset in registry.assets:
        assert asset.licence
        assert asset.source
        assert asset.visibility
        assert asset.review_status
        assert asset.author
        assert asset.copyright
        assert asset.representation("text") is not None


def test_load_manifest_validates_required_fields(tmp_path: Path):
    path = _write_manifest(tmp_path / "bad.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    del data["licence"]
    path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(AssetManifestError, match="licence"):
        load_asset_manifest(path)


def test_load_manifest_rejects_empty_tags(tmp_path: Path):
    path = _write_manifest(tmp_path / "bad.json", tags=[])

    with pytest.raises(AssetManifestError, match="tags"):
        load_asset_manifest(path)


def test_load_manifest_rejects_missing_representations(tmp_path: Path):
    path = _write_manifest(tmp_path / "bad.json", representations={})

    with pytest.raises(AssetManifestError, match="representations"):
        load_asset_manifest(path)


def test_load_manifest_allows_missing_aliases(tmp_path: Path):
    path = _write_manifest(tmp_path / "valid.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    del data["aliases"]
    path.write_text(json.dumps(data), encoding="utf-8")

    asset = load_asset_manifest(path)

    assert asset.aliases == ()


def test_load_manifest_requires_attribution_for_non_bundled_source(tmp_path: Path):
    path = _write_manifest(tmp_path / "bad.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    del data["author"]
    path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(AssetManifestError, match="author and copyright"):
        load_asset_manifest(path)


def test_find_by_exact_id():
    registry = load_bundled_registry()

    match = registry.find("stone")

    assert match is not None
    assert match.asset.id == "stone"
    assert match.reason == "id"


def test_find_by_name_with_punctuation_and_case():
    registry = load_bundled_registry()

    match = registry.find("Standing-Stone")

    assert match is not None
    assert match.asset.id == "stone"
    assert match.reason == "name"


def test_find_by_alias():
    registry = load_bundled_registry()

    match = registry.find("wooden door")

    assert match is not None
    assert match.asset.id == "door"
    assert match.reason == "alias"


def test_find_by_semantic_tag_phrase():
    registry = load_bundled_registry()

    match = registry.find("framed art picture")

    assert match is not None
    assert match.asset.id == "painting"
    assert "semantic match" in match.reason


def test_find_prefers_specific_alias_over_broad_tag():
    registry = load_bundled_registry()

    match = registry.find("pictish stone")

    assert match is not None
    assert match.asset.id == "stone"
    assert match.reason == "alias"


def test_find_by_tag_returns_matching_assets():
    registry = load_bundled_registry()

    assets = registry.find_by_tag("museum")
    ids = {asset.id for asset in assets}

    assert {"stone", "painting"} <= ids


def test_find_hides_private_assets_by_default(tmp_path: Path):
    path = _write_manifest(tmp_path / "private.json", id="private_stone", tags=["stone"])
    asset = load_asset_manifest(path)
    registry = AssetRegistry([asset])

    assert registry.find("private stone") is None
    assert registry.find("private stone", visible_to=None) is not None


def test_find_prefers_more_precise_match_over_longer_label(tmp_path: Path):
    broad = load_asset_manifest(_write_manifest(
        tmp_path / "broad.json",
        id="broad",
        name="Broad",
        visibility="featured",
        tags=["wooden crate"],
        aliases=["wooden crate"],
    ))
    precise = load_asset_manifest(_write_manifest(
        tmp_path / "precise.json",
        id="precise",
        name="Precise",
        visibility="featured",
        tags=["wood"],
        aliases=["wood"],
    ))
    registry = AssetRegistry([broad, precise])

    match = registry.find("wood")

    assert match is not None
    assert match.asset.id == "precise"


def test_duplicate_ids_fail(tmp_path: Path):
    _write_manifest(tmp_path / "a.json", id="duplicate")
    _write_manifest(tmp_path / "b.json", id="duplicate", name="Other")

    with pytest.raises(AssetManifestError, match="Duplicate asset id"):
        AssetRegistry.from_directory(tmp_path)
