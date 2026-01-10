"""
Runtime Feature Parity Tests

Three-way check between:
  1. Spec TOML (spec/v0.3.0/rosh-spec.toml [runtime_features])
  2. JS Runtime (static/rosh-runtime.js @parity tags)
  3. Python Interpreter (src/rosh/interpreter.py @parity tags)

If any source has features the others don't, the test fails.
This catches drift when features are added to one runtime but not the other.

Usage: pytest tests/test_runtime_parity.py -v
"""

import pytest
from pathlib import Path
import tomllib
import re


def extract_parity_tags(content: str) -> set:
    """Extract @parity feature names from file content."""
    pattern = r'@parity\s+(\w+)'
    return set(re.findall(pattern, content))


@pytest.fixture
def spec_features():
    """Get feature names from spec TOML."""
    spec_path = Path(__file__).parent.parent / "spec" / "v0.3.0" / "rosh-spec.toml"
    with open(spec_path, "rb") as f:
        spec = tomllib.load(f)

    features = spec.get("runtime_features", {})
    # Filter out non-dict entries (the section header)
    return {k for k, v in features.items() if isinstance(v, dict)}


@pytest.fixture
def js_features():
    """Get @parity tags from JS runtime."""
    path = Path(__file__).parent.parent / "static" / "rosh-runtime.js"
    return extract_parity_tags(path.read_text())


@pytest.fixture
def py_features():
    """Get @parity tags from Python interpreter."""
    path = Path(__file__).parent.parent / "src" / "rosh" / "interpreter.py"
    return extract_parity_tags(path.read_text())


class TestThreeWayParity:
    """Test that spec, JS, and Python all declare the same features."""

    def test_js_matches_spec(self, spec_features, js_features):
        """JS runtime declares all spec features."""
        missing = spec_features - js_features
        extra = js_features - spec_features

        if missing:
            pytest.fail(f"JS missing features from spec: {missing}\n"
                       f"Add @parity tags to static/rosh-runtime.js")
        if extra:
            pytest.fail(f"JS has features not in spec: {extra}\n"
                       f"Add to spec/v0.3.0/rosh-spec.toml [runtime_features]")

    def test_python_matches_spec(self, spec_features, py_features):
        """Python interpreter declares all spec features."""
        missing = spec_features - py_features
        extra = py_features - spec_features

        if missing:
            pytest.fail(f"Python missing features from spec: {missing}\n"
                       f"Add @parity tags to src/rosh/interpreter.py")
        if extra:
            pytest.fail(f"Python has features not in spec: {extra}\n"
                       f"Add to spec/v0.3.0/rosh-spec.toml [runtime_features]")

    def test_js_matches_python(self, js_features, py_features):
        """JS and Python declare the same features."""
        js_only = js_features - py_features
        py_only = py_features - js_features

        if js_only:
            pytest.fail(f"Features in JS but not Python: {js_only}\n"
                       f"Implement in src/rosh/interpreter.py and add @parity tag")
        if py_only:
            pytest.fail(f"Features in Python but not JS: {py_only}\n"
                       f"Implement in static/rosh-runtime.js and add @parity tag")

    def test_all_three_match(self, spec_features, js_features, py_features):
        """All three sources declare exactly the same features."""
        all_features = spec_features | js_features | py_features

        for feature in all_features:
            in_spec = feature in spec_features
            in_js = feature in js_features
            in_py = feature in py_features

            if not (in_spec and in_js and in_py):
                sources = []
                if in_spec: sources.append("spec")
                if in_js: sources.append("JS")
                if in_py: sources.append("Python")
                missing = []
                if not in_spec: missing.append("spec")
                if not in_js: missing.append("JS")
                if not in_py: missing.append("Python")

                pytest.fail(f"Feature '{feature}' in {sources} but missing from {missing}")


class TestFeatureCount:
    """Basic sanity checks."""

    def test_spec_has_features(self, spec_features):
        """Spec defines at least some features."""
        assert len(spec_features) >= 3, "Spec should define runtime features"

    def test_js_has_parity_tags(self, js_features):
        """JS file has @parity tags."""
        assert len(js_features) >= 3, "JS should have @parity tags in header"

    def test_python_has_parity_tags(self, py_features):
        """Python file has @parity tags."""
        assert len(py_features) >= 3, "Python should have @parity tags in docstring"
