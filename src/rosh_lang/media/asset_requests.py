# licence: MIT
"""Helpers for reading asset request queues and searching providers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rosh_lang.media.asset_providers import AssetCandidate, AssetProvider


class AssetRequestError(ValueError):
    """Raised when asset request input is malformed."""


def load_asset_requests(path: Path) -> list[dict[str, Any]]:
    """Load asset requests from JSON.

    Accepted shapes:
    - a raw list: ``[{...}]``
    - a state object: ``{"_assetRequests": [...]}``
    - a wrapper: ``{"state": {"_assetRequests": [...]}}``
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AssetRequestError(f"{path}: invalid JSON: {exc}") from exc

    if isinstance(data, list):
        raw_requests = data
    elif isinstance(data, dict) and isinstance(data.get("_assetRequests"), list):
        raw_requests = data["_assetRequests"]
    elif (
        isinstance(data, dict)
        and isinstance(data.get("state"), dict)
        and isinstance(data["state"].get("_assetRequests"), list)
    ):
        raw_requests = data["state"]["_assetRequests"]
    else:
        raise AssetRequestError(
            f"{path}: expected a request list or object containing _assetRequests"
        )

    requests: list[dict[str, Any]] = []
    for index, item in enumerate(raw_requests):
        if not isinstance(item, dict):
            raise AssetRequestError(f"{path}: request {index} must be an object")
        query = str(item.get("query") or item.get("object") or "").strip()
        if not query:
            raise AssetRequestError(f"{path}: request {index} needs query or object")
        requests.append(dict(item))
    return requests


def search_asset_requests(
    requests: list[dict[str, Any]],
    provider: AssetProvider,
    *,
    limit: int = 3,
) -> list[dict[str, Any]]:
    """Search a provider for each request and return reviewable candidates."""
    results: list[dict[str, Any]] = []
    for request in requests:
        query = str(request.get("query") or request.get("object") or "").strip()
        target = str(request.get("target") or "").strip()
        filters: dict[str, Any] = {"count": limit}
        if target:
            filters["target"] = target
        candidates = provider.search(query, filters=filters)[:limit]
        results.append({
            "request": request,
            "provider": provider.name,
            "query": query,
            "candidates": [_candidate_to_dict(candidate) for candidate in candidates],
        })
    return results


def _candidate_to_dict(candidate: AssetCandidate) -> dict[str, Any]:
    return {
        "provider": candidate.provider,
        "id": candidate.id,
        "name": candidate.name,
        "description": candidate.description,
        "licence": candidate.licence,
        "source_url": candidate.source_url,
        "formats": list(candidate.formats),
        "tags": list(candidate.tags),
        "score": candidate.score,
        "metadata": candidate.metadata,
    }
