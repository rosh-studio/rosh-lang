"""Public repository and editor-extension release regressions."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).parents[1]
EXTENSION = ROOT / "editor" / "vscode"


def test_vscode_extension_metadata_is_current() -> None:
    package = json.loads((EXTENSION / "package.json").read_text())
    grammar = json.loads((EXTENSION / "syntaxes" / "rosh.tmLanguage.json").read_text())
    snippets = json.loads((EXTENSION / "snippets" / "rosh.json").read_text())

    assert package["version"] == "0.8.0"
    assert package["repository"]["url"] == "https://github.com/rosh-studio/rosh-lang"
    assert "nothing" in str(grammar)
    assert "add|remove|destroy" in str(grammar)
    assert "game_over" in str(snippets)
    assert "game-over" not in str(snippets)


def test_source_distribution_excludes_local_release_hazards() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text()
    gitignore = (ROOT / ".gitignore").read_text()

    for path in ("/.uv-cache", "/.venv", "/dist", "/test-verify.rosh"):
        assert path in pyproject
    assert ".uv-cache/" in gitignore
    assert "test-verify.rosh" in gitignore


def test_standalone_public_ci_exists() -> None:
    workflow = ROOT / ".github" / "workflows" / "ci.yml"

    assert workflow.exists()
    text = workflow.read_text()
    assert 'python-version: ["3.10", "3.12"]' in text
    assert "uv build --no-sources" in text
