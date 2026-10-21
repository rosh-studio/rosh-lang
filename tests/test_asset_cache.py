"""Tests for the local 3D asset cache (asset_cache.py)."""

from __future__ import annotations

from pathlib import Path
import pytest

from rosh_lang.media import asset_cache as mod


@pytest.fixture(autouse=True)
def _patch_cache_root(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "_CACHE_ROOT", tmp_path / "cache3d")


def test_get_cache_dir_creates_directory():
    d = mod.get_cache_dir()
    assert d.is_dir()


def test_cached_path_returns_expected_name():
    path = mod.cached_path("torch_wall")
    assert path.name == "torch_wall.glb"
    assert path.parent.is_dir()


def test_cached_path_sanitises_id():
    path = mod.cached_path("abc/def?x=1")
    assert "/" not in path.name
    assert "?" not in path.name


def test_cache_asset_writes_file():
    path = mod.cache_asset("stone", b"fake-glb-data")
    assert path.exists()
    assert path.read_bytes() == b"fake-glb-data"


def test_cache_asset_respects_ext():
    path = mod.cache_asset("stone", b"gltf-data", "gltf")
    assert path.suffix == ".gltf"


def test_is_cached_false_before_write():
    assert not mod.is_cached("missing_asset")


def test_is_cached_true_after_write():
    mod.cache_asset("brooch", b"data")
    assert mod.is_cached("brooch")


def test_list_cached_returns_name_and_size():
    mod.cache_asset("key", b"a" * 100)
    mod.cache_asset("door", b"b" * 200)
    items = mod.list_cached()
    assert len(items) == 2
    names = {n for n, _ in items}
    assert "key.glb" in names
    assert "door.glb" in names
    sizes = {n: s for n, s in items}
    assert sizes["key.glb"] == 100
    assert sizes["door.glb"] == 200


def test_list_cached_empty_when_nothing_cached():
    assert mod.list_cached() == []


def test_clear_cache_removes_all_files():
    mod.cache_asset("a", b"1")
    mod.cache_asset("b", b"2")
    n = mod.clear_cache()
    assert n == 2
    assert mod.list_cached() == []


def test_clear_cache_returns_zero_when_empty():
    assert mod.clear_cache() == 0
