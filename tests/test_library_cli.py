"""Tests for rosh library CLI — list and info subcommands."""

from __future__ import annotations

import subprocess
import sys

import pytest


def _run_rosh(*args: str) -> subprocess.CompletedProcess[str]:
    """Run `rosh` CLI with given args."""
    return subprocess.run(
        [sys.executable, "-m", "rosh_lang", *args],
        capture_output=True,
        text=True,
        timeout=10,
    )


class TestLibraryList:
    def test_list_shows_widgets(self):
        result = _run_rosh("library", "list")
        assert result.returncode == 0
        assert "score" in result.stdout
        assert "player" in result.stdout
        assert "counter" in result.stdout
        assert "timer" in result.stdout

    def test_list_shows_bundled_source(self):
        result = _run_rosh("library", "list")
        assert "bundled" in result.stdout

    def test_list_shows_descriptions(self):
        result = _run_rosh("library", "list")
        assert "Score display" in result.stdout

    def test_list_default_subcommand(self):
        """'rosh library' with no subcommand defaults to list."""
        result = _run_rosh("library")
        assert result.returncode == 0
        assert "score" in result.stdout


class TestLibraryInfo:
    def test_info_score(self):
        result = _run_rosh("library", "info", "score")
        assert result.returncode == 0
        assert "score" in result.stdout
        assert "0.3" in result.stdout
        assert "bundled" in result.stdout
        assert "text_color" in result.stdout

    def test_info_missing_widget(self):
        result = _run_rosh("library", "info", "nonexistent")
        assert result.returncode != 0

    def test_info_no_name_errors(self):
        result = _run_rosh("library", "info")
        assert result.returncode != 0

    def test_unknown_subcommand_errors(self):
        result = _run_rosh("library", "blarg")
        assert result.returncode != 0
