"""Tests for loading and searching asset request queues."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from rosh_lang.media.asset_providers import MockAssetProvider
from rosh_lang.media.asset_requests import (
    AssetRequestError,
    load_asset_requests,
    search_asset_requests,
)


def test_loads_raw_request_list(tmp_path: Path):
    path = tmp_path / "requests.json"
    path.write_text(json.dumps([{"query": "pictish stone"}]), encoding="utf-8")

    requests = load_asset_requests(path)

    assert requests == [{"query": "pictish stone"}]


def test_loads_state_asset_requests(tmp_path: Path):
    path = tmp_path / "state.json"
    path.write_text(
        json.dumps({"_assetRequests": [{"query": "wooden door"}]}),
        encoding="utf-8",
    )

    requests = load_asset_requests(path)

    assert requests == [{"query": "wooden door"}]


def test_loads_wrapped_state_asset_requests(tmp_path: Path):
    path = tmp_path / "wrapped.json"
    path.write_text(
        json.dumps({"state": {"_assetRequests": [{"object": "pictish_stone"}]}}),
        encoding="utf-8",
    )

    requests = load_asset_requests(path)

    assert requests == [{"object": "pictish_stone"}]


def test_rejects_missing_asset_requests(tmp_path: Path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"state": {}}), encoding="utf-8")

    with pytest.raises(AssetRequestError, match="_assetRequests"):
        load_asset_requests(path)


def test_rejects_request_without_query_or_object(tmp_path: Path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps([{"target": "threejs"}]), encoding="utf-8")

    with pytest.raises(AssetRequestError, match="query or object"):
        load_asset_requests(path)


def test_search_asset_requests_returns_reviewable_candidates():
    requests = [{"query": "pictish stone", "target": "threejs", "status": "open"}]

    results = search_asset_requests(requests, MockAssetProvider(), limit=1)

    assert len(results) == 1
    assert results[0]["provider"] == "mock"
    assert results[0]["query"] == "pictish stone"
    assert results[0]["request"] == requests[0]
    assert len(results[0]["candidates"]) == 1
    candidate = results[0]["candidates"][0]
    assert candidate["id"] == "mock_pictish_stone"
    assert candidate["licence"] == "CC0-1.0"
    assert "threejs" in candidate["formats"]


def test_search_asset_requests_keeps_empty_candidate_lists():
    requests = [{"query": "glass submarine", "target": "threejs"}]

    results = search_asset_requests(requests, MockAssetProvider())

    assert results[0]["candidates"] == []
