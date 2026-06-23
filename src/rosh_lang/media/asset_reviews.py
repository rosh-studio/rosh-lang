# licence: MIT
"""Candidate review format for the Rosh asset pipeline.

A review file is a JSON list where each entry records a human decision about
which provider candidate to accept for one asset request.  The file is
produced by ``rosh assets search --save`` and consumed by
``rosh assets register``.

Typical workflow::

    # 1. Search and save a review template
    rosh assets search requests.json --provider sketchfab --save review.json

    # 2. Open review.json, change "decision": "pending" → "accept" or "reject"

    # 3. Register accepted candidates as draft manifests
    rosh assets register review.json --output-dir draft_manifests/

    # 4. Inspect draft manifests, adjust scale/tags, move to asset_manifests/
    #    when satisfied — then set review_status to "featured".
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Licence classification
# ---------------------------------------------------------------------------

# Licences safe for bundled distribution with no usage restriction.
# Includes Sketchfab display labels ("CC Attribution") and slugs ("cc-by")
# as aliases so review files written by the provider pipeline pass validation.
PERMISSIVE_LICENCES: frozenset[str] = frozenset({
    "cc0",
    "public domain",
    # CC BY — canonical + Sketchfab label + Sketchfab slug
    "cc by",
    "cc by 4.0",
    "cc by 3.0",
    "cc attribution",
    "cc-by",
    # CC BY-SA — canonical + slug
    "cc by-sa",
    "cc by-sa 4.0",
    "cc by-sa 3.0",
    "cc-by-sa",
})

# Non-commercial licences are blocked: assets in the Rosh library are
# distributed under MIT and must be freely usable without use-case restrictions.
NC_LICENCES: frozenset[str] = frozenset({
    "cc by-nc",
    "cc by-nc 4.0",
    "cc by-nc 3.0",
    "cc by-nc-sa",
    "cc by-nc-sa 4.0",
    "cc-by-nc",
    "cc-by-nc-sa",
})


class AssetReviewError(ValueError):
    """Raised when a review file is malformed."""


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class CandidateReview:
    """A human decision about one provider candidate for one asset request."""

    request: str            # rosh object name, e.g. "necklace"
    query: str              # search phrase used, e.g. "amber bead necklace"
    target: str             # renderer target, e.g. "threejs"
    decision: str           # "accept" | "reject" | "defer" | "pending"
    candidate_id: str       # provider-specific model UID
    candidate_name: str     # human-readable model name
    provider: str           # "sketchfab" | "mock"
    licence: str            # e.g. "CC BY 4.0"
    source_url: str         # link to the model page
    author: str             # creator name for attribution
    formats: list[str]      # available formats, e.g. ["glb", "gltf"]
    downloadable: bool      # whether the model can be downloaded
    proposed_manifest_id: str  # manifest id to write (defaults to request)
    notes: str = ""         # free-text notes from the human reviewer


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_candidate_reviews(path: Path) -> list[CandidateReview]:
    """Load a review file and return one ``CandidateReview`` per entry."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AssetReviewError(f"{path}: invalid JSON: {exc}") from exc
    except OSError as exc:
        raise AssetReviewError(f"{path}: {exc}") from exc

    if not isinstance(data, list):
        raise AssetReviewError(f"{path}: expected a JSON list of review entries")

    reviews: list[CandidateReview] = []
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            raise AssetReviewError(f"{path}: entry {index} must be an object")
        reviews.append(_parse_entry(item, index, path))
    return reviews


def _parse_entry(item: dict[str, Any], index: int, path: Path) -> CandidateReview:
    request = str(item.get("request") or "").strip()
    if not request:
        raise AssetReviewError(f"{path}: entry {index}: 'request' field is required")
    proposed = str(item.get("proposed_manifest_id") or request).strip()
    return CandidateReview(
        request=request,
        query=str(item.get("query") or request),
        target=str(item.get("target") or "threejs"),
        decision=str(item.get("decision") or "pending").lower().strip(),
        candidate_id=str(item.get("candidate_id") or ""),
        candidate_name=str(item.get("candidate_name") or ""),
        provider=str(item.get("provider") or ""),
        licence=str(item.get("licence") or ""),
        source_url=str(item.get("source_url") or ""),
        author=str(item.get("author") or ""),
        formats=[str(f) for f in (item.get("formats") or [])],
        downloadable=bool(item.get("downloadable", False)),
        proposed_manifest_id=proposed,
        notes=str(item.get("notes") or ""),
    )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_review(review: CandidateReview) -> list[str]:
    """Check an accepted review entry for blockers and warnings.

    Returns a list of strings.  Each starts with ``BLOCK:`` (prevents
    registration) or ``WARN:`` (human should acknowledge).  An empty list
    means the review is clean.
    """
    problems: list[str] = []

    if not review.candidate_id:
        problems.append("BLOCK: candidate_id is empty")

    if not review.downloadable:
        problems.append("BLOCK: candidate is not marked downloadable by the author")

    available = {f.lower() for f in review.formats}
    if "glb" not in available and "gltf" not in available:
        fmt_list = ", ".join(review.formats) if review.formats else "none"
        problems.append(f"WARN: no glb/gltf format available — found: {fmt_list}")

    licence_key = review.licence.lower().strip()
    if not licence_key:
        problems.append("BLOCK: licence field is empty — cannot register without licence")
    elif licence_key in NC_LICENCES:
        problems.append(
            f"BLOCK: '{review.licence}' is non-commercial — Rosh library assets must be"
            " freely usable; use a CC BY or CC0 alternative, or reject this candidate"
        )
    elif licence_key not in PERMISSIVE_LICENCES:
        problems.append(
            f"BLOCK: '{review.licence}' is not a known permissive licence"
            " — add it to PERMISSIVE_LICENCES or reject this candidate"
        )

    return problems


# ---------------------------------------------------------------------------
# Draft manifest generation
# ---------------------------------------------------------------------------

def review_to_draft_manifest(review: CandidateReview) -> dict[str, Any]:
    """Produce a draft manifest dict from an accepted candidate review.

    The manifest has ``review_status: "draft"`` and ``visibility: "private"``
    so it is never served as a default until promoted.

    ``representations.threejs.model`` is blank — to be filled after acquire.
    ``representations.threejs.scale`` is ``[1.0, 1.0, 1.0]`` — a placeholder
    that must be set after visual QA (downloaded models vary wildly in scale).
    """
    licence_note = review.licence
    if "by" in review.licence.lower():
        licence_note = f"{review.licence} (attribution required: {review.author or 'see source_url'})"

    copyright_str = (
        f"© {review.author} via {review.provider.title()} ({review.licence})"
        if review.author
        else f"via {review.provider.title()} ({review.licence})"
    )

    tags = _build_tags(review)
    readable_name = review.candidate_name or review.request.replace("_", " ").title()
    readable_kind = review.request.replace("_", " ")

    return {
        "id": review.proposed_manifest_id,
        "name": readable_name,
        "version": "0.1",
        "description": f"Draft: {readable_name} sourced from {review.provider}. Review scale and description before promoting.",
        "licence": licence_note,
        "source": review.provider,
        "source_url": review.source_url,
        "visibility": "private",
        "review_status": "draft",
        "author": review.author,
        "copyright": copyright_str,
        "tags": tags,
        "aliases": [readable_kind] if readable_kind != review.proposed_manifest_id else [],
        "semantic": {
            "kind": review.request,
            "scale_hint": "unknown",
            "inspectable": True,
        },
        "defaults": {
            "color": "grey",
            "shape": "box",
            "collision": "static",
        },
        "representations": {
            "text": {
                "description": f"A {readable_kind} is here.",
            },
            "threejs": {
                "fallback_shape": "box",
                "model": "",
                "scale": [1.0, 1.0, 1.0],
            },
            "phaser": {
                "fallback_shape": "rectangle",
            },
        },
    }


def _build_tags(review: CandidateReview) -> list[str]:
    seen: set[str] = set()
    tags: list[str] = []
    for word in [review.request] + review.query.split():
        w = word.replace("_", " ").lower().strip()
        if w and w not in seen:
            seen.add(w)
            tags.append(w)
    return tags


# ---------------------------------------------------------------------------
# Review template generation (used by ``rosh assets search --save``)
# ---------------------------------------------------------------------------

def candidates_to_review_template(
    search_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Convert ``search_asset_requests`` output into a review template list.

    Picks the top candidate per request (highest score).  Sets
    ``decision: "pending"`` so the human must explicitly accept or reject.
    """
    template: list[dict[str, Any]] = []
    for result in search_results:
        request_obj = result.get("request") or {}
        request_name = str(request_obj.get("object") or request_obj.get("query") or "")
        query = str(result.get("query") or request_name)
        target = str(request_obj.get("target") or "threejs")
        candidates = result.get("candidates") or []

        if not candidates:
            template.append({
                "request": request_name,
                "query": query,
                "target": target,
                "decision": "no_candidates",
                "candidate_id": "",
                "candidate_name": "",
                "provider": str(result.get("provider") or ""),
                "licence": "",
                "source_url": "",
                "author": "",
                "formats": [],
                "downloadable": False,
                "proposed_manifest_id": request_name,
                "notes": "No candidates found — try a different query.",
            })
            continue

        top = candidates[0]
        meta = top.get("metadata") or {}
        template.append({
            "request": request_name,
            "query": query,
            "target": target,
            "decision": "pending",
            "candidate_id": str(top.get("id") or ""),
            "candidate_name": str(top.get("name") or ""),
            "provider": str(top.get("provider") or result.get("provider") or ""),
            "licence": str(top.get("licence") or ""),
            "source_url": str(top.get("source_url") or ""),
            "author": str(meta.get("author") or ""),
            "formats": list(top.get("formats") or []),
            "downloadable": bool(meta.get("is_downloadable", False)),
            "proposed_manifest_id": request_name,
            "notes": "",
        })
    return template
