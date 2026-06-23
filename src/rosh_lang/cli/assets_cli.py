# licence: MIT
"""rosh assets — inspect asset requests and register provider candidates.

Usage:
    rosh assets search requests.json --provider mock
    rosh assets search state.json --provider sketchfab --limit 5
    rosh assets search requests.json --provider sketchfab --save review.json
    rosh assets register review.json
    rosh assets register review.json --output-dir draft_manifests/
    rosh assets acquire review.json          # download all accepted entries
    rosh assets acquire <candidate_id> --provider sketchfab --asset-id NAME
    rosh assets cache list
    rosh assets cache clear
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from rosh_lang.media.asset_providers import (
    AssetProvider,
    AssetProviderError,
    MockAssetProvider,
    SketchfabAssetProvider,
)
from rosh_lang.media.asset_requests import (
    AssetRequestError,
    load_asset_requests,
    search_asset_requests,
)
from rosh_lang.media.asset_reviews import (
    AssetReviewError,
    candidates_to_review_template,
    load_candidate_reviews,
    review_to_draft_manifest,
    validate_review,
)


def assets_main(args: list[str]) -> None:
    """Route ``rosh assets`` subcommands."""
    if not args or args[0] in {"help", "-h", "--help"}:
        _usage()
        return
    command = args[0]
    if command == "search":
        _cmd_search(args[1:])
    elif command == "register":
        _cmd_register(args[1:])
    elif command == "acquire":
        _cmd_acquire(args[1:])
    elif command == "cache":
        _cmd_cache(args[1:])
    else:
        print(f"Unknown assets command: {command!r}", file=sys.stderr)
        _usage()
        sys.exit(1)


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------

def _cmd_search(args: list[str]) -> None:
    if not args:
        print("Usage: rosh assets search <requests.json> [options]", file=sys.stderr)
        sys.exit(1)

    path = Path(args[0])
    provider_name = "mock"
    limit = 3
    save_path: Path | None = None
    i = 1
    while i < len(args):
        if args[i] == "--provider" and i + 1 < len(args):
            provider_name = args[i + 1]
            i += 2
        elif args[i] == "--limit" and i + 1 < len(args):
            try:
                limit = max(1, int(args[i + 1]))
            except ValueError:
                print("--limit must be an integer", file=sys.stderr)
                sys.exit(1)
            i += 2
        elif args[i] == "--save" and i + 1 < len(args):
            save_path = Path(args[i + 1])
            i += 2
        else:
            print(f"Unknown option: {args[i]}", file=sys.stderr)
            sys.exit(1)

    try:
        requests = load_asset_requests(path)
        provider = _provider(provider_name)
        if provider.name == "sketchfab":
            print("Searching Sketchfab...", file=sys.stderr)
        results = search_asset_requests(requests, provider, limit=limit)
    except (AssetProviderError, AssetRequestError, OSError) as exc:
        print(f"AssetError: {exc}", file=sys.stderr)
        sys.exit(1)

    if save_path is not None:
        template = candidates_to_review_template(results)
        save_path.write_text(json.dumps(template, indent=2), encoding="utf-8")
        print(
            f"Review template saved to {save_path} — edit 'decision' fields then run:",
            file=sys.stderr,
        )
        print(f"  rosh assets register {save_path}", file=sys.stderr)
    else:
        print(json.dumps(results, indent=2))


# ---------------------------------------------------------------------------
# register
# ---------------------------------------------------------------------------

def _cmd_register(args: list[str]) -> None:
    if not args:
        print("Usage: rosh assets register <review.json> [--output-dir DIR]", file=sys.stderr)
        sys.exit(1)

    path = Path(args[0])
    output_dir = Path("draft_manifests")
    i = 1
    while i < len(args):
        if args[i] == "--output-dir" and i + 1 < len(args):
            output_dir = Path(args[i + 1])
            i += 2
        else:
            print(f"Unknown option: {args[i]}", file=sys.stderr)
            sys.exit(1)

    try:
        reviews = load_candidate_reviews(path)
    except AssetReviewError as exc:
        print(f"ReviewError: {exc}", file=sys.stderr)
        sys.exit(1)

    accepted = [r for r in reviews if r.decision == "accept"]
    skipped = len(reviews) - len(accepted)

    if not accepted:
        statuses = {r.decision for r in reviews}
        print(
            f"No accepted entries in {path} — found decisions: {', '.join(sorted(statuses))}",
            file=sys.stderr,
        )
        print("Set 'decision': 'accept' on the entries you want to register.", file=sys.stderr)
        sys.exit(0)

    output_dir.mkdir(parents=True, exist_ok=True)
    registered = 0
    blocked = 0

    for review in accepted:
        problems = validate_review(review)
        blockers = [p for p in problems if p.startswith("BLOCK:")]
        warnings = [p for p in problems if p.startswith("WARN:")]

        if blockers:
            print(f"\n[SKIP] {review.request!r} — blocked:", file=sys.stderr)
            for b in blockers:
                print(f"  {b}", file=sys.stderr)
            blocked += 1
            continue

        if warnings:
            print(f"\n[WARN] {review.request!r}:", file=sys.stderr)
            for w in warnings:
                print(f"  {w}", file=sys.stderr)

        manifest = review_to_draft_manifest(review)
        out_path = output_dir / f"{review.proposed_manifest_id}.json"

        if out_path.exists():
            print(
                f"[SKIP] {out_path} already exists — rename proposed_manifest_id to avoid collision",
                file=sys.stderr,
            )
            blocked += 1
            continue

        out_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(f"[OK]   {out_path} — review_status=draft, visibility=private")
        registered += 1

    print(
        f"\n{registered} draft manifest(s) written to {output_dir}/."
        f" {blocked} blocked. {skipped} skipped (pending/reject/defer).",
        file=sys.stderr,
    )
    if registered:
        print(
            "Next steps: inspect manifests, set scale in representations.threejs.scale,\n"
            "then move to asset_manifests/ and set review_status=featured to promote.",
            file=sys.stderr,
        )


# ---------------------------------------------------------------------------
# acquire
# ---------------------------------------------------------------------------

def _cmd_acquire(args: list[str]) -> None:
    if not args:
        print(
            "Usage:\n"
            "  rosh assets acquire <review.json>             # download all 'accept' entries\n"
            "  rosh assets acquire <candidate_id> [--provider sketchfab] [--asset-id NAME]",
            file=sys.stderr,
        )
        sys.exit(1)

    provider_name = "sketchfab"
    asset_id_override: str | None = None
    i = 1
    while i < len(args):
        if args[i] == "--provider" and i + 1 < len(args):
            provider_name = args[i + 1]
            i += 2
        elif args[i] == "--asset-id" and i + 1 < len(args):
            asset_id_override = args[i + 1]
            i += 2
        else:
            print(f"Unknown option: {args[i]}", file=sys.stderr)
            sys.exit(1)

    target = args[0]
    target_path = Path(target)

    try:
        provider = _provider(provider_name)
    except AssetRequestError as exc:
        print(f"ProviderError: {exc}", file=sys.stderr)
        sys.exit(1)

    if not getattr(provider, "supports_acquire", False):
        print(f"Provider {provider_name!r} does not support acquire", file=sys.stderr)
        sys.exit(1)

    if target_path.suffix == ".json" and target_path.exists():
        _acquire_from_review(target_path, provider)
    else:
        _acquire_single(target, asset_id_override or target, provider)


def _acquire_single(candidate_id: str, asset_id: str, provider: AssetProvider) -> None:
    from rosh_lang.media.asset_cache import cache_asset, get_cache_dir

    print(f"Downloading {candidate_id} from {provider.name}...", file=sys.stderr)
    try:
        acquisition = provider.acquire(candidate_id)
    except AssetProviderError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        sys.exit(1)

    cache_dir = get_cache_dir()
    for key, path_str in acquisition.local_files.items():
        src = Path(path_str)
        ext = src.suffix.lstrip(".") or "glb"
        dest = cache_dir / f"{asset_id}.{ext}"
        if dest != src:
            dest.write_bytes(src.read_bytes())
        size = dest.stat().st_size
        print(f"[OK] {dest}  ({size / 1024:.0f} KB)")

    _print_next_steps(asset_id, cache_dir)


def _acquire_from_review(review_path: Path, provider: AssetProvider) -> None:
    from rosh_lang.media.asset_cache import cache_asset, get_cache_dir

    try:
        raw = json.loads(review_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Error reading {review_path}: {exc}", file=sys.stderr)
        sys.exit(1)

    entries = raw if isinstance(raw, list) else [raw]
    accepted = [e for e in entries if isinstance(e, dict) and e.get("decision") == "accept"]
    if not accepted:
        decisions = {e.get("decision", "?") for e in entries if isinstance(e, dict)}
        print(
            f"No 'accept' entries in {review_path} — found: {', '.join(sorted(decisions))}",
            file=sys.stderr,
        )
        print("Set 'decision': 'accept' on entries to download.", file=sys.stderr)
        sys.exit(0)

    print(f"Acquiring {len(accepted)} asset(s) from {review_path}...", file=sys.stderr)
    cache_dir = get_cache_dir()
    ok = 0
    for entry in accepted:
        candidate_id = str(entry.get("candidate_id") or "").strip()
        asset_id = str(entry.get("proposed_manifest_id") or candidate_id).strip()
        if not candidate_id:
            print("  [SKIP] entry has no candidate_id")
            continue
        print(f"  Downloading {candidate_id} → {asset_id}...", file=sys.stderr)
        try:
            acquisition = provider.acquire(candidate_id)
        except AssetProviderError as exc:
            print(f"  [FAIL] {candidate_id}: {exc}")
            continue

        for key, path_str in acquisition.local_files.items():
            src = Path(path_str)
            ext = src.suffix.lstrip(".") or "glb"
            dest = cache_dir / f"{asset_id}.{ext}"
            if dest != src:
                dest.write_bytes(src.read_bytes())
            size = dest.stat().st_size
            print(f"  [OK] {dest.name}  ({size / 1024:.0f} KB)")
        ok += 1

    print(f"\n{ok}/{len(accepted)} acquired.", file=sys.stderr)
    _print_next_steps("*", cache_dir)


def _print_next_steps(asset_id: str, cache_dir: Path) -> None:
    print(
        f"\nNext steps:",
        file=sys.stderr,
    )
    print(
        f"  1. rosh-world serves these at /assets/3d/{asset_id}.glb",
        file=sys.stderr,
    )
    print(
        f"  2. Set model in your manifest's representations.threejs to /assets/3d/{asset_id}.glb",
        file=sys.stderr,
    )
    print(
        f"  3. After R2 upload, update model to https://assets.rosh.cloud/3d/{asset_id}.glb",
        file=sys.stderr,
    )


# ---------------------------------------------------------------------------
# cache
# ---------------------------------------------------------------------------

def _cmd_cache(args: list[str]) -> None:
    from rosh_lang.media.asset_cache import clear_cache, get_cache_dir, list_cached

    subcmd = args[0] if args else "list"

    if subcmd in {"list", "ls"}:
        items = list_cached()
        cache_dir = get_cache_dir()
        if not items:
            print(f"Cache is empty: {cache_dir}")
            return
        total = sum(s for _, s in items)
        print(f"Cached assets in {cache_dir} ({len(items)} file(s), {total / 1024:.0f} KB total):\n")
        for name, size in items:
            print(f"  {name:<44}  {size / 1024:>6.0f} KB")

    elif subcmd == "clear":
        n = clear_cache()
        print(f"Cleared {n} cached asset(s) from {get_cache_dir()}")

    elif subcmd in {"help", "-h", "--help"}:
        print("Usage: rosh assets cache [list|clear]")

    else:
        print(f"Unknown cache command: {subcmd!r} — try list or clear", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _provider(name: str) -> AssetProvider:
    key = name.strip().lower()
    if key == "mock":
        return MockAssetProvider()
    if key == "sketchfab":
        return SketchfabAssetProvider(api_token=os.environ.get("SKETCHFAB_API_TOKEN", ""))
    raise AssetRequestError(f"unknown provider: {name!r}")


def _usage() -> None:
    print(
        "Usage:\n"
        "  rosh assets search <requests.json> [--provider mock|sketchfab] [--limit N] [--save review.json]\n"
        "  rosh assets register <review.json> [--output-dir DIR]\n"
        "  rosh assets acquire <review.json>                # download all 'accept' entries\n"
        "  rosh assets acquire <candidate_id> [--provider sketchfab] [--asset-id NAME]\n"
        "  rosh assets cache list\n"
        "  rosh assets cache clear",
        file=sys.stderr,
    )
