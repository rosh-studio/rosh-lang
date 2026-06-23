# licence: MIT
"""Tests for the candidate review format and draft manifest generation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from rosh_lang.media.asset_reviews import (
    AssetReviewError,
    CandidateReview,
    candidates_to_review_template,
    load_candidate_reviews,
    review_to_draft_manifest,
    validate_review,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_review(**kwargs) -> CandidateReview:
    defaults = dict(
        request="necklace",
        query="amber bead necklace",
        target="threejs",
        decision="accept",
        candidate_id="abc123",
        candidate_name="Amber Bead Necklace",
        provider="sketchfab",
        licence="CC0",
        source_url="https://sketchfab.com/3d-models/abc123",
        author="artist",
        formats=["glb", "gltf"],
        downloadable=True,
        proposed_manifest_id="necklace",
    )
    defaults.update(kwargs)
    return CandidateReview(**defaults)


def _write_review_file(tmp_path: Path, entries: list[dict]) -> Path:
    p = tmp_path / "review.json"
    p.write_text(json.dumps(entries), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def test_load_valid_review_file(tmp_path):
    p = _write_review_file(tmp_path, [{
        "request": "necklace",
        "query": "amber bead necklace",
        "target": "threejs",
        "decision": "accept",
        "candidate_id": "abc123",
        "candidate_name": "Amber Bead Necklace",
        "provider": "sketchfab",
        "licence": "CC0",
        "source_url": "https://sketchfab.com/3d-models/abc123",
        "author": "artist",
        "formats": ["glb"],
        "downloadable": True,
        "proposed_manifest_id": "necklace",
        "notes": "looks good",
    }])
    reviews = load_candidate_reviews(p)
    assert len(reviews) == 1
    r = reviews[0]
    assert r.request == "necklace"
    assert r.decision == "accept"
    assert r.candidate_id == "abc123"
    assert r.downloadable is True
    assert r.notes == "looks good"


def test_load_defaults_missing_optional_fields(tmp_path):
    p = _write_review_file(tmp_path, [{"request": "sword"}])
    reviews = load_candidate_reviews(p)
    assert reviews[0].decision == "pending"
    assert reviews[0].query == "sword"
    assert reviews[0].target == "threejs"
    assert reviews[0].proposed_manifest_id == "sword"
    assert reviews[0].downloadable is False


def test_load_multiple_entries(tmp_path):
    p = _write_review_file(tmp_path, [
        {"request": "necklace", "decision": "accept"},
        {"request": "brooch", "decision": "reject"},
        {"request": "sword", "decision": "pending"},
    ])
    reviews = load_candidate_reviews(p)
    assert len(reviews) == 3
    assert [r.decision for r in reviews] == ["accept", "reject", "pending"]


def test_load_rejects_non_list(tmp_path):
    p = tmp_path / "review.json"
    p.write_text('{"request": "necklace"}', encoding="utf-8")
    with pytest.raises(AssetReviewError, match="expected a JSON list"):
        load_candidate_reviews(p)


def test_load_rejects_invalid_json(tmp_path):
    p = tmp_path / "review.json"
    p.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(AssetReviewError, match="invalid JSON"):
        load_candidate_reviews(p)


def test_load_rejects_missing_request_field(tmp_path):
    p = _write_review_file(tmp_path, [{"decision": "accept"}])
    with pytest.raises(AssetReviewError, match="'request' field is required"):
        load_candidate_reviews(p)


def test_load_rejects_non_object_entry(tmp_path):
    p = _write_review_file(tmp_path, ["not_an_object"])
    with pytest.raises(AssetReviewError, match="must be an object"):
        load_candidate_reviews(p)


def test_load_missing_file_raises(tmp_path):
    with pytest.raises(AssetReviewError):
        load_candidate_reviews(tmp_path / "nonexistent.json")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def test_validate_clean_cc0():
    review = _make_review(licence="CC0")
    assert validate_review(review) == []


def test_validate_clean_cc_by():
    review = _make_review(licence="CC BY 4.0")
    assert validate_review(review) == []


def test_validate_warns_nc_licence():
    review = _make_review(licence="CC BY-NC 4.0")
    problems = validate_review(review)
    assert any("WARN:" in p and "non-commercial" in p for p in problems)
    assert not any("BLOCK:" in p for p in problems)


def test_validate_blocks_unknown_licence():
    review = _make_review(licence="Sketchfab Standard")
    problems = validate_review(review)
    assert any("BLOCK:" in p and "not a known permissive" in p for p in problems)


def test_validate_blocks_empty_licence():
    review = _make_review(licence="")
    problems = validate_review(review)
    assert any("BLOCK:" in p and "licence field is empty" in p for p in problems)


def test_validate_blocks_non_downloadable():
    review = _make_review(downloadable=False)
    problems = validate_review(review)
    assert any("BLOCK:" in p and "not marked downloadable" in p for p in problems)


def test_validate_blocks_empty_candidate_id():
    review = _make_review(candidate_id="")
    problems = validate_review(review)
    assert any("BLOCK:" in p and "candidate_id is empty" in p for p in problems)


def test_validate_warns_no_glb_format():
    review = _make_review(formats=["fbx", "obj"])
    problems = validate_review(review)
    assert any("WARN:" in p and "no glb/gltf" in p for p in problems)
    assert not any("BLOCK:" in p for p in problems)


def test_validate_accepts_gltf_without_glb():
    review = _make_review(formats=["gltf"])
    problems = validate_review(review)
    assert not any("glb/gltf" in p for p in problems)


def test_validate_multiple_blockers():
    review = _make_review(candidate_id="", downloadable=False, licence="")
    problems = validate_review(review)
    assert sum(1 for p in problems if p.startswith("BLOCK:")) >= 2


# ---------------------------------------------------------------------------
# Draft manifest generation
# ---------------------------------------------------------------------------

def test_draft_manifest_has_required_fields():
    review = _make_review()
    m = review_to_draft_manifest(review)
    for field in ("id", "name", "version", "licence", "source", "source_url",
                  "visibility", "review_status", "author", "copyright",
                  "tags", "aliases", "semantic", "defaults", "representations"):
        assert field in m, f"missing field: {field}"


def test_draft_manifest_is_private_draft():
    m = review_to_draft_manifest(_make_review())
    assert m["visibility"] == "private"
    assert m["review_status"] == "draft"


def test_draft_manifest_uses_proposed_id():
    m = review_to_draft_manifest(_make_review(proposed_manifest_id="necklace_sketchfab"))
    assert m["id"] == "necklace_sketchfab"


def test_draft_manifest_has_empty_model_path():
    m = review_to_draft_manifest(_make_review())
    assert m["representations"]["threejs"]["model"] == ""


def test_draft_manifest_has_placeholder_scale():
    m = review_to_draft_manifest(_make_review())
    assert m["representations"]["threejs"]["scale"] == [1.0, 1.0, 1.0]


def test_draft_manifest_source_is_provider():
    m = review_to_draft_manifest(_make_review(provider="sketchfab"))
    assert m["source"] == "sketchfab"


def test_draft_manifest_includes_source_url():
    url = "https://sketchfab.com/3d-models/abc123"
    m = review_to_draft_manifest(_make_review(source_url=url))
    assert m["source_url"] == url


def test_draft_manifest_attribution_note_for_cc_by():
    m = review_to_draft_manifest(_make_review(licence="CC BY 4.0", author="sculptor"))
    assert "attribution" in m["licence"].lower() or "sculptor" in m["licence"]


def test_draft_manifest_cc0_no_attribution_note():
    m = review_to_draft_manifest(_make_review(licence="CC0", author="sculptor"))
    assert "attribution" not in m["licence"].lower()


def test_draft_manifest_tags_include_request():
    m = review_to_draft_manifest(_make_review(request="brooch", query="silver brooch celtic"))
    assert "brooch" in m["tags"]


def test_draft_manifest_fallback_shape_is_box():
    m = review_to_draft_manifest(_make_review())
    assert m["representations"]["threejs"]["fallback_shape"] == "box"
    assert m["representations"]["phaser"]["fallback_shape"] == "rectangle"


# ---------------------------------------------------------------------------
# Review template generation
# ---------------------------------------------------------------------------

def _make_search_result(request_name: str, candidates: list[dict]) -> dict:
    return {
        "request": {"object": request_name, "query": request_name, "target": "threejs"},
        "provider": "mock",
        "query": request_name,
        "candidates": candidates,
    }


def _make_candidate(score: float = 1.0) -> dict:
    return {
        "id": "abc123",
        "name": "Test Object",
        "provider": "mock",
        "licence": "CC0",
        "source_url": "https://example.com",
        "formats": ["glb"],
        "tags": ["test"],
        "score": score,
        "metadata": {"is_downloadable": True, "author": "tester"},
    }


def test_template_picks_top_candidate():
    results = [_make_search_result("sword", [_make_candidate(0.9), _make_candidate(0.5)])]
    template = candidates_to_review_template(results)
    assert len(template) == 1
    assert template[0]["candidate_id"] == "abc123"
    assert template[0]["decision"] == "pending"


def test_template_sets_pending_decision():
    results = [_make_search_result("sword", [_make_candidate()])]
    template = candidates_to_review_template(results)
    assert template[0]["decision"] == "pending"


def test_template_no_candidates_marks_as_such():
    results = [_make_search_result("blargle", [])]
    template = candidates_to_review_template(results)
    assert template[0]["decision"] == "no_candidates"
    assert template[0]["candidate_id"] == ""


def test_template_extracts_author_from_metadata():
    candidate = _make_candidate()
    candidate["metadata"]["author"] = "famous_sculptor"
    results = [_make_search_result("statue", [candidate])]
    template = candidates_to_review_template(results)
    assert template[0]["author"] == "famous_sculptor"


def test_template_extracts_downloadable_from_metadata():
    candidate = _make_candidate()
    candidate["metadata"]["is_downloadable"] = False
    results = [_make_search_result("locked_model", [candidate])]
    template = candidates_to_review_template(results)
    assert template[0]["downloadable"] is False


def test_template_preserves_proposed_manifest_id():
    results = [_make_search_result("my_sword", [_make_candidate()])]
    template = candidates_to_review_template(results)
    assert template[0]["proposed_manifest_id"] == "my_sword"


def test_template_multiple_requests():
    results = [
        _make_search_result("sword", [_make_candidate()]),
        _make_search_result("shield", []),
    ]
    template = candidates_to_review_template(results)
    assert len(template) == 2
    assert template[0]["request"] == "sword"
    assert template[1]["request"] == "shield"
    assert template[1]["decision"] == "no_candidates"
