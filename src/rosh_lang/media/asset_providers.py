# licence: MIT
"""External asset provider contract and offline mock provider."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any, Callable, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from rosh_lang.media.asset_registry import normalise_asset_text


class AssetProviderError(RuntimeError):
    """Raised when a provider cannot inspect or acquire an asset."""


@dataclass(frozen=True)
class AssetCandidate:
    """Search result from an external or local asset provider."""

    provider: str
    id: str
    name: str
    description: str
    licence: str
    source_url: str
    formats: tuple[str, ...]
    tags: tuple[str, ...] = ()
    score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AssetAcquisition:
    """Provider acquisition record ready to become a Rosh manifest."""

    provider: str
    candidate_id: str
    local_files: dict[str, str]
    candidate: AssetCandidate
    status: str = "acquired"
    notes: str = ""


class AssetProvider(Protocol):
    """Provider interface for agent-driven asset acquisition."""

    name: str
    supports_acquire: bool

    def search(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
    ) -> list[AssetCandidate]:
        """Return provider candidates for a query."""

    def inspect(self, candidate_id: str) -> AssetCandidate:
        """Return full metadata for a provider candidate."""

    def acquire(self, candidate_id: str) -> AssetAcquisition:
        """Acquire a candidate into local provider-managed files."""


class MockAssetProvider:
    """Deterministic offline provider used to exercise the asset pipeline."""

    name = "mock"
    supports_acquire = True

    def __init__(self, candidates: list[AssetCandidate] | None = None) -> None:
        self._candidates = {
            candidate.id: candidate
            for candidate in (candidates or _default_candidates())
        }

    def search(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
    ) -> list[AssetCandidate]:
        """Search candidates by normalized name/tag overlap."""
        target = str((filters or {}).get("target") or "").strip().lower()
        query_tokens = set(normalise_asset_text(query).split())
        if not query_tokens:
            return []

        matches: list[AssetCandidate] = []
        for candidate in self._candidates.values():
            if target and target not in candidate.formats:
                continue
            labels = [candidate.name, candidate.description, *candidate.tags]
            haystack = set()
            for label in labels:
                haystack.update(normalise_asset_text(label).split())
            overlap = query_tokens & haystack
            if not overlap:
                continue
            score = len(overlap) / max(len(query_tokens), 1)
            matches.append(_with_score(candidate, score))

        return sorted(matches, key=lambda candidate: candidate.score, reverse=True)

    def inspect(self, candidate_id: str) -> AssetCandidate:
        """Return metadata for a candidate."""
        try:
            return self._candidates[candidate_id]
        except KeyError as exc:
            raise AssetProviderError(f"Unknown mock asset: {candidate_id}") from exc

    def acquire(self, candidate_id: str) -> AssetAcquisition:
        """Return a local acquisition record without touching the network."""
        candidate = self.inspect(candidate_id)
        local_files: dict[str, str] = {}
        if "threejs" in candidate.formats:
            local_files["threejs.model"] = f"mock://assets/{candidate.id}.glb"
        if "thumbnail" in candidate.formats:
            local_files["thumbnail.image"] = f"mock://assets/{candidate.id}.png"
        return AssetAcquisition(
            provider=self.name,
            candidate_id=candidate.id,
            local_files=local_files,
            candidate=candidate,
            status="mock",
            notes="Mock acquisition; no network or file download performed.",
        )


class SketchfabAssetProvider:
    """Sketchfab Data API provider — search, inspect, and download CC models."""

    name = "sketchfab"
    supports_acquire = True

    def __init__(
        self,
        *,
        api_token: str = "",
        base_url: str = "https://api.sketchfab.com/v3",
        transport: Callable[[str, dict[str, str]], dict[str, Any]] | None = None,
        download_transport: Callable[[str], bytes] | None = None,
    ) -> None:
        self.api_token = api_token
        self.base_url = base_url.rstrip("/")
        self._transport = transport or _http_get_json
        self._download_transport = download_transport or _http_download_bytes
        self._cache: dict[str, AssetCandidate] = {}

    def search(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
    ) -> list[AssetCandidate]:
        """Search downloadable Sketchfab models and return metadata candidates."""
        filters = filters or {}
        target = str(filters.get("target") or "").strip().lower()
        if target and target not in {"threejs", "3d", "model", "thumbnail"}:
            return []
        params: dict[str, Any] = {
            "type": "models",
            "q": query,
            "downloadable": "true",
            "count": min(int(filters.get("count", 12) or 12), 24),
        }
        licences = filters.get("licences") or filters.get("licenses")
        if licences:
            params["licenses"] = ",".join(licences) if isinstance(licences, list) else str(licences)
        category = filters.get("category")
        if category:
            params["categories"] = str(category)
        sort_by = filters.get("sort_by")
        if sort_by:
            params["sort_by"] = str(sort_by)

        data = self._get("/search", params)
        candidates = [
            self._candidate_from_model(item)
            for item in data.get("results", [])
            if isinstance(item, dict)
        ]
        for candidate in candidates:
            self._cache[candidate.id] = candidate
        return candidates

    def inspect(self, candidate_id: str) -> AssetCandidate:
        """Inspect one Sketchfab model by uid."""
        if candidate_id in self._cache:
            return self._cache[candidate_id]
        safe_id = quote(candidate_id, safe="")
        data = self._get(f"/models/{safe_id}", None)
        candidate = self._candidate_from_model(data)
        self._cache[candidate.id] = candidate
        return candidate

    def acquire(self, candidate_id: str) -> AssetAcquisition:
        """Download a Sketchfab model's GLB to the local asset cache."""
        from rosh_lang.media.asset_cache import cache_asset

        safe_id = quote(candidate_id, safe="")
        try:
            download_info = self._get(f"/models/{safe_id}/download", None)
        except AssetProviderError as exc:
            raise AssetProviderError(
                f"Could not get download URL for {candidate_id}: {exc}"
            ) from exc

        # Prefer GLB; fall back to GLTF
        url_entry = download_info.get("glb") or download_info.get("gltf")
        if not url_entry or not url_entry.get("url"):
            raise AssetProviderError(
                f"No downloadable GLB/GLTF available for {candidate_id}"
            )

        download_url = str(url_entry["url"])
        fmt = "glb" if "glb" in download_info else "gltf"

        candidate = self.inspect(candidate_id)
        data = self._download_transport(download_url)
        local_path = cache_asset(candidate_id, data, fmt)

        return AssetAcquisition(
            provider=self.name,
            candidate_id=candidate_id,
            local_files={f"{fmt}.model": str(local_path)},
            candidate=candidate,
            status="acquired",
            notes=f"Downloaded {len(data):,} bytes ({fmt.upper()}) from Sketchfab",
        )

    def _get(self, path: str, params: dict[str, Any] | None) -> dict[str, Any]:
        query = f"?{urlencode(params)}" if params else ""
        return self._transport(f"{self.base_url}{path}{query}", self._headers())

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.api_token:
            headers["Authorization"] = f"Token {self.api_token}"
        return headers

    def _candidate_from_model(self, data: dict[str, Any]) -> AssetCandidate:
        uid = str(data.get("uid") or "").strip()
        if not uid:
            raise AssetProviderError("Sketchfab model is missing uid")
        name = str(data.get("name") or uid).strip()
        description = str(data.get("description") or f"Sketchfab model {name}").strip()
        licence = _licence_label(data.get("license"))
        tags = _tags(data.get("tags"))
        thumbnail = _thumbnail_url(data.get("thumbnails"))
        raw_url = str(data.get("viewerUrl") or data.get("embedUrl") or data.get("uri") or "").strip()
        # Sketchfab search returns URLs like /3d-models/none-{uid} when the slug is absent.
        # Fall back to a clean UID-only URL in that case.
        viewer_url = raw_url if raw_url and f"/none-{uid}" not in raw_url else ""
        downloadable = bool(data.get("isDownloadable", False))
        formats = ["thumbnail"]
        if downloadable:
            formats.append("glb")
        metadata = {
            "viewer_url": viewer_url,
            "thumbnail": thumbnail,
            "is_downloadable": downloadable,
            "like_count": data.get("likeCount"),
            "view_count": data.get("viewCount"),
            "vertex_count": data.get("vertexCount"),
            "face_count": data.get("faceCount"),
            "author": _author_name(data.get("user")),
        }
        return AssetCandidate(
            provider=self.name,
            id=uid,
            name=name,
            description=description,
            licence=licence,
            source_url=viewer_url or f"https://sketchfab.com/3d-models/{uid}",
            formats=tuple(formats),
            tags=tags,
            score=float(data.get("likeCount") or 0),
            metadata=metadata,
        )


def manifest_from_acquisition(
    acquisition: AssetAcquisition,
    *,
    asset_id: str | None = None,
    visibility: str = "private",
    review_status: str = "needs_review",
) -> dict[str, Any]:
    """Create a Rosh asset manifest dictionary from an acquisition record."""
    candidate = acquisition.candidate
    manifest_id = asset_id or _slug(candidate.name)
    representations: dict[str, Any] = {
        "text": {"description": candidate.description},
    }
    model = acquisition.local_files.get("threejs.model")
    if model:
        representations["threejs"] = {
            "model": model,
            "fallback_shape": "box",
            "scale": [1.0, 1.0, 1.0],
        }
    thumb = acquisition.local_files.get("thumbnail.image")
    if thumb:
        representations["thumbnail"] = {"image": thumb}

    return {
        "id": manifest_id,
        "name": candidate.name,
        "version": "0.1",
        "description": candidate.description,
        "licence": candidate.licence,
        "source": f"{candidate.provider}:{candidate.id}",
        "source_url": candidate.source_url,
        "owner": "rosh",
        "author": str(candidate.metadata.get("author") or candidate.provider),
        "copyright": str(candidate.metadata.get("copyright") or "See source licence"),
        "visibility": visibility,
        "review_status": review_status,
        "tags": list(candidate.tags or (_slug(candidate.name),)),
        "aliases": [candidate.name.lower()],
        "semantic": {"kind": manifest_id},
        "defaults": {
            "color": str(candidate.metadata.get("color") or "grey"),
            "shape": str(candidate.metadata.get("shape") or "box"),
            "collision": "static",
        },
        "representations": representations,
        "provenance": {
            "provider": acquisition.provider,
            "candidate_id": acquisition.candidate_id,
            "status": acquisition.status,
            "notes": acquisition.notes,
        },
    }


def fulfil_asset_request(
    request: dict[str, Any],
    provider: AssetProvider,
) -> dict[str, Any] | None:
    """Search a provider for one request and return a draft manifest if found."""
    query = str(request.get("query") or request.get("object") or "").strip()
    target = str(request.get("target") or "").strip()
    filters = {"target": target} if target else None
    candidates = provider.search(query, filters=filters)
    if not candidates:
        return None
    if not getattr(provider, "supports_acquire", False):
        return None
    try:
        acquisition = provider.acquire(candidates[0].id)
    except AssetProviderError:
        return None
    return manifest_from_acquisition(
        acquisition,
        asset_id=_slug(query),
        visibility="private",
        review_status="needs_review",
    )


def _default_candidates() -> list[AssetCandidate]:
    return [
        AssetCandidate(
            provider="mock",
            id="mock_pictish_stone",
            name="Mock Pictish Standing Stone",
            description="A carved standing stone placeholder for heritage worlds.",
            licence="CC0-1.0",
            source_url="mock://assets/mock_pictish_stone",
            formats=("threejs", "thumbnail"),
            tags=("pictish", "stone", "standing", "heritage", "museum"),
            metadata={"color": "grey", "shape": "box"},
        ),
        AssetCandidate(
            provider="mock",
            id="mock_wooden_door",
            name="Mock Wooden Door",
            description="A simple wooden door placeholder.",
            licence="CC0-1.0",
            source_url="mock://assets/mock_wooden_door",
            formats=("threejs", "thumbnail"),
            tags=("wooden", "door", "entrance"),
            metadata={"color": "brown", "shape": "box"},
        ),
    ]


def _with_score(candidate: AssetCandidate, score: float) -> AssetCandidate:
    return AssetCandidate(
        provider=candidate.provider,
        id=candidate.id,
        name=candidate.name,
        description=candidate.description,
        licence=candidate.licence,
        source_url=candidate.source_url,
        formats=candidate.formats,
        tags=candidate.tags,
        score=score,
        metadata=candidate.metadata,
    )


def _normalise(value: str) -> str:
    return normalise_asset_text(value)


def _slug(value: str) -> str:
    normalized = _normalise(value)
    return normalized.replace(" ", "_") or "asset"


def _http_get_json(url: str, headers: dict[str, str]) -> dict[str, Any]:
    request = Request(url, headers=headers, method="GET")
    try:
        with urlopen(request, timeout=20) as response:
            body = response.read().decode("utf-8")
    except HTTPError as exc:
        if exc.code == 429:
            raise AssetProviderError("Sketchfab API rate limit reached") from exc
        raise AssetProviderError(f"Sketchfab API returned HTTP {exc.code}") from exc
    except URLError as exc:
        raise AssetProviderError(f"Sketchfab API request failed: {exc.reason}") from exc
    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise AssetProviderError("Sketchfab API returned invalid JSON") from exc
    if not isinstance(data, dict):
        raise AssetProviderError("Sketchfab API returned unexpected JSON")
    return data


def _licence_label(value: Any) -> str:
    if isinstance(value, dict):
        for key in ("label", "slug", "fullName", "name"):
            item = value.get(key)
            if isinstance(item, str) and item.strip():
                return item.strip()
    if isinstance(value, str) and value.strip():
        return value.strip()
    return "unknown"


def _tags(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    tags: list[str] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            tags.append(item.strip())
        elif isinstance(item, dict):
            label = item.get("name") or item.get("slug")
            if isinstance(label, str) and label.strip():
                tags.append(label.strip())
    return tuple(dict.fromkeys(tags))


def _thumbnail_url(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    images = value.get("images")
    if not isinstance(images, list) or not images:
        return ""
    best = max(
        (image for image in images if isinstance(image, dict)),
        key=lambda image: int(image.get("width") or 0),
        default={},
    )
    url = best.get("url")
    return str(url).strip() if isinstance(url, str) else ""


def _http_download_bytes(url: str) -> bytes:
    """Download a binary file from *url* without authentication."""
    req = Request(url, method="GET")
    try:
        with urlopen(req, timeout=120) as resp:
            return resp.read()
    except HTTPError as exc:
        raise AssetProviderError(f"Download failed: HTTP {exc.code}") from exc
    except URLError as exc:
        raise AssetProviderError(f"Download failed: {exc.reason}") from exc


def _author_name(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    for key in ("displayName", "username"):
        item = value.get(key)
        if isinstance(item, str) and item.strip():
            return item.strip()
    return ""
