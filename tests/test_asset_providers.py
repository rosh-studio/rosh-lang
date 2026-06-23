"""Tests for asset provider connectors and request fulfilment."""

from __future__ import annotations

import json

import pytest

from rosh_lang.media.asset_providers import (
    AssetProviderError,
    MockAssetProvider,
    SketchfabAssetProvider,
    fulfil_asset_request,
    manifest_from_acquisition,
)
from rosh_lang.media.asset_registry import AssetRegistry, load_asset_manifest


def test_mock_provider_searches_by_query_and_target():
    provider = MockAssetProvider()

    results = provider.search("pictish stone", filters={"target": "threejs"})

    assert results
    assert results[0].id == "mock_pictish_stone"
    assert results[0].score > 0


def test_mock_provider_search_respects_target_filter():
    provider = MockAssetProvider()

    results = provider.search("pictish stone", filters={"target": "phaser"})

    assert results == []


def test_mock_provider_inspect_unknown_fails():
    provider = MockAssetProvider()

    with pytest.raises(AssetProviderError, match="Unknown mock asset"):
        provider.inspect("missing")


def test_mock_provider_acquire_returns_local_file_record():
    provider = MockAssetProvider()

    acquisition = provider.acquire("mock_pictish_stone")

    assert acquisition.provider == "mock"
    assert acquisition.candidate_id == "mock_pictish_stone"
    assert acquisition.status == "mock"
    assert acquisition.local_files["threejs.model"].endswith(".glb")
    assert acquisition.local_files["thumbnail.image"].endswith(".png")


def test_manifest_from_acquisition_has_required_metadata():
    provider = MockAssetProvider()
    acquisition = provider.acquire("mock_pictish_stone")

    manifest = manifest_from_acquisition(acquisition, asset_id="pictish_stone")

    assert manifest["id"] == "pictish_stone"
    assert manifest["licence"] == "CC0-1.0"
    assert manifest["source"] == "mock:mock_pictish_stone"
    assert manifest["author"] == "mock"
    assert manifest["copyright"] == "See source licence"
    assert manifest["visibility"] == "private"
    assert manifest["review_status"] == "needs_review"
    assert manifest["representations"]["threejs"]["model"].endswith(".glb")
    assert manifest["provenance"]["provider"] == "mock"


def test_manifest_from_acquisition_can_load_into_registry(tmp_path):
    provider = MockAssetProvider()
    acquisition = provider.acquire("mock_pictish_stone")
    manifest = manifest_from_acquisition(acquisition, asset_id="pictish_stone")
    path = tmp_path / "pictish_stone.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")

    asset = load_asset_manifest(path)
    registry = AssetRegistry([asset])
    match = registry.find("pictish stone", visible_to=None)

    assert match is not None
    assert match.asset.id == "pictish_stone"


def test_fulfil_asset_request_returns_draft_manifest():
    request = {
        "object": "blargle",
        "query": "pictish stone",
        "target": "threejs",
        "status": "open",
        "reason": "no_match",
    }
    provider = MockAssetProvider()

    manifest = fulfil_asset_request(request, provider)

    assert manifest is not None
    assert manifest["id"] == "pictish_stone"
    assert manifest["source"] == "mock:mock_pictish_stone"
    assert manifest["review_status"] == "needs_review"


def test_fulfil_asset_request_returns_none_when_no_candidate():
    request = {"query": "glass submarine", "target": "threejs"}
    provider = MockAssetProvider()

    assert fulfil_asset_request(request, provider) is None


def test_fulfil_asset_request_returns_none_when_acquire_fails():
    request = {"query": "pictish stone", "target": "threejs"}
    # Transport handles search but returns no download URLs → acquire raises
    provider = SketchfabAssetProvider(
        transport=lambda url, _h: (
            {"results": [_sketchfab_model()]} if "search" in url else {}
        ),
        download_transport=lambda _url: b"",
    )

    assert fulfil_asset_request(request, provider) is None


def _sketchfab_model(uid: str = "abc123") -> dict[str, object]:
    return {
        "uid": uid,
        "name": "Pictish Stone",
        "description": "A carved heritage stone.",
        "license": {"label": "CC Attribution", "slug": "cc-by"},
        "isDownloadable": True,
        "viewerUrl": "https://sketchfab.com/3d-models/pictish-stone-abc123",
        "likeCount": 42,
        "viewCount": 1000,
        "vertexCount": 500,
        "faceCount": 250,
        "tags": [{"name": "Pictish"}, {"slug": "stone"}],
        "user": {"displayName": "Museum Maker"},
        "thumbnails": {
            "images": [
                {"url": "https://example.test/small.jpg", "width": 128},
                {"url": "https://example.test/large.jpg", "width": 512},
            ]
        },
    }


def test_sketchfab_search_maps_results_and_headers():
    calls: list[tuple[str, dict[str, str]]] = []

    def transport(url: str, headers: dict[str, str]) -> dict[str, object]:
        calls.append((url, headers))
        return {"results": [_sketchfab_model()]}

    provider = SketchfabAssetProvider(api_token="skfb_token", transport=transport)

    results = provider.search(
        "pictish stone",
        filters={"count": 99, "licenses": ["cc-by"], "target": "threejs"},
    )

    assert len(results) == 1
    candidate = results[0]
    assert candidate.provider == "sketchfab"
    assert candidate.id == "abc123"
    assert candidate.name == "Pictish Stone"
    assert candidate.licence == "CC Attribution"
    assert candidate.source_url.endswith("abc123")
    assert candidate.formats == ("thumbnail", "glb")
    assert candidate.tags == ("Pictish", "stone")
    assert candidate.metadata["thumbnail"] == "https://example.test/large.jpg"
    assert candidate.metadata["author"] == "Museum Maker"
    url, headers = calls[0]
    assert url.startswith("https://api.sketchfab.com/v3/search?")
    assert "q=pictish+stone" in url
    assert "type=models" in url
    assert "downloadable=true" in url
    assert "count=24" in url
    assert "licenses=cc-by" in url
    assert headers["Authorization"] == "Token skfb_token"


def test_sketchfab_inspect_uses_cache_after_search():
    calls = 0

    def transport(url: str, headers: dict[str, str]) -> dict[str, object]:
        nonlocal calls
        calls += 1
        return {"results": [_sketchfab_model()]}

    provider = SketchfabAssetProvider(transport=transport)
    provider.search("pictish stone")
    candidate = provider.inspect("abc123")

    assert candidate.name == "Pictish Stone"
    assert calls == 1


def test_sketchfab_inspect_fetches_uncached_model():
    calls: list[str] = []

    def transport(url: str, headers: dict[str, str]) -> dict[str, object]:
        calls.append(url)
        return _sketchfab_model("uncached")

    provider = SketchfabAssetProvider(transport=transport)

    candidate = provider.inspect("uncached")

    assert candidate.id == "uncached"
    assert calls == ["https://api.sketchfab.com/v3/models/uncached"]


def test_sketchfab_inspect_quotes_candidate_id():
    calls: list[str] = []

    def transport(url: str, headers: dict[str, str]) -> dict[str, object]:
        calls.append(url)
        return _sketchfab_model("safe")

    provider = SketchfabAssetProvider(transport=transport)

    provider.inspect("../search")

    assert calls == ["https://api.sketchfab.com/v3/models/..%2Fsearch"]


def test_sketchfab_search_respects_unsupported_target_filter():
    provider = SketchfabAssetProvider(
        transport=lambda _url, _headers: {"results": [_sketchfab_model()]}
    )

    assert provider.search("pictish stone", filters={"target": "phaser"}) == []


def test_sketchfab_non_downloadable_candidate_has_thumbnail_only():
    model = _sketchfab_model()
    model["isDownloadable"] = False

    provider = SketchfabAssetProvider(transport=lambda _url, _headers: {"results": [model]})

    candidate = provider.search("pictish stone")[0]

    assert candidate.formats == ("thumbnail",)


def test_sketchfab_missing_downloadable_flag_is_not_downloadable():
    model = _sketchfab_model()
    del model["isDownloadable"]

    provider = SketchfabAssetProvider(transport=lambda _url, _headers: {"results": [model]})

    candidate = provider.search("pictish stone")[0]

    assert candidate.formats == ("thumbnail",)


def test_sketchfab_acquire_downloads_glb(tmp_path, monkeypatch):
    import rosh_lang.media.asset_cache as cache_mod

    monkeypatch.setattr(cache_mod, "_CACHE_ROOT", tmp_path)

    fake_glb = b"GLBDATA"
    api_calls: list[str] = []

    def transport(url: str, headers: dict[str, str]) -> dict[str, object]:
        api_calls.append(url)
        if "/download" in url:
            return {"glb": {"url": "https://s3.example.com/model.glb", "size": len(fake_glb)}}
        return _sketchfab_model("abc123")

    provider = SketchfabAssetProvider(
        api_token="tok",
        transport=transport,
        download_transport=lambda _url: fake_glb,
    )

    acquisition = provider.acquire("abc123")

    assert acquisition.provider == "sketchfab"
    assert acquisition.candidate_id == "abc123"
    assert acquisition.status == "acquired"
    assert "glb.model" in acquisition.local_files
    glb_path = tmp_path / "abc123.glb"
    assert glb_path.exists()
    assert glb_path.read_bytes() == fake_glb
    assert any("/download" in u for u in api_calls)


def test_sketchfab_acquire_prefers_glb_over_gltf(tmp_path, monkeypatch):
    import rosh_lang.media.asset_cache as cache_mod

    monkeypatch.setattr(cache_mod, "_CACHE_ROOT", tmp_path)

    def transport(url: str, headers: dict[str, str]) -> dict[str, object]:
        if "/download" in url:
            return {
                "gltf": {"url": "https://s3.example.com/model.gltf", "size": 10},
                "glb": {"url": "https://s3.example.com/model.glb", "size": 20},
            }
        return _sketchfab_model("abc123")

    provider = SketchfabAssetProvider(
        transport=transport,
        download_transport=lambda _url: b"GLBDATA",
    )

    acquisition = provider.acquire("abc123")

    assert "glb.model" in acquisition.local_files
    assert acquisition.local_files["glb.model"].endswith(".glb")


def test_sketchfab_acquire_raises_when_no_download_url(tmp_path, monkeypatch):
    import rosh_lang.media.asset_cache as cache_mod

    monkeypatch.setattr(cache_mod, "_CACHE_ROOT", tmp_path)

    provider = SketchfabAssetProvider(
        transport=lambda url, _h: {} if "/download" in url else _sketchfab_model("abc123"),
        download_transport=lambda _url: b"",
    )

    with pytest.raises(AssetProviderError, match="No downloadable"):
        provider.acquire("abc123")
