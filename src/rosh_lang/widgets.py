"""Widget loader — find, load, namespace-prefix, and configure widgets.

Roshonic: it should just work.
- Exact match → use it
- No exact match → fuzzy match → list options
- No matches → warn + continue gracefully

Widgets are .rosh files or .py factory files. Any Rosh programme can be a widget.
Python factories export generate(config) → list[Statement] for programmatic generation.
"""

from __future__ import annotations

import difflib
import importlib.util
import re
import warnings
from pathlib import Path
from typing import Any

from rosh_lang.model import (
    AfterStatement,
    AnimateStatement,
    CreateStatement,
    DestroyStatement,
    IfStatement,
    OnStatement,
    PlayStatement,
    PrintStatement,
    Programme,
    SayStatement,
    SendStatement,
    SetStatement,
    SoundStatement,
    SpriteStatement,
    Statement,
    UseStatement,
    WhenStatement,
)
from rosh_lang.parser import parse_file

_INTERP_RE = re.compile(r"\{([^}]+)\}")
_META_RE = re.compile(r"^#\s*(widget|version|description|config|licence):\s*(.+)$")


def get_bundled_library_path() -> Path:
    """Return the path to the bundled widget library shipped with rosh-lang."""
    return Path(__file__).parent / "library"


# Default search paths: project-local → global → bundled (last = lowest priority)
DEFAULT_SEARCH_PATHS = [
    Path("./widgets"),
    Path.home() / ".rosh" / "library",
    get_bundled_library_path(),
]


def parse_metadata(path: Path) -> dict[str, Any]:
    """Parse metadata from a widget file (.rosh comment header or .py METADATA dict).

    For .rosh files, looks for comment-header lines like:
        # widget: score
        # version: 0.1
        # description: Score display with label
        # config: max=999 min=0

    For .py factory files, imports the module and reads the METADATA dict.

    Returns dict with keys: widget, version, description, config, licence.
    """
    meta: dict[str, Any] = {"widget": path.stem, "version": "", "description": "", "config": {}, "licence": ""}

    if path.suffix == ".py":
        return _parse_python_metadata(path, meta)

    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return meta

    for line in text.splitlines():
        m = _META_RE.match(line.strip())
        if not m:
            # Stop at first non-comment, non-blank line
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                break
            continue
        key, value = m.group(1), m.group(2).strip()
        if key == "config":
            # Parse "max=999 min=0" → {"max": "999", "min": "0"}
            for pair in value.split():
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    meta["config"][k] = v
        else:
            meta[key] = value
    return meta


def _parse_python_metadata(path: Path, meta: dict[str, Any]) -> dict[str, Any]:
    """Extract METADATA dict from a Python factory module."""
    try:
        module = _import_factory_module(path)
    except Exception:
        return meta

    raw = getattr(module, "METADATA", None)
    if not isinstance(raw, dict):
        return meta

    for key in ("widget", "version", "description", "licence"):
        if key in raw:
            meta[key] = raw[key]
    if "config" in raw and isinstance(raw["config"], dict):
        meta["config"] = raw["config"]
    return meta


def find_widget(name: str, search_paths: list[Path] | None = None) -> Path | None:
    """Find a widget file by name (.rosh or .py factory).

    Returns the path if found (exact or fuzzy), None if not found.
    Emits warnings for fuzzy matches and not-found.
    """
    paths = search_paths or DEFAULT_SEARCH_PATHS

    # 1. Exact match — .rosh first, then .py factory
    for base in paths:
        candidate_rosh = base / f"{name}.rosh"
        if candidate_rosh.is_file():
            return candidate_rosh
        candidate_py = base / f"{name}.py"
        if candidate_py.is_file():
            return candidate_py

    # 2. Fuzzy match — collect all available widgets
    available = _list_available(paths)
    if available:
        close = difflib.get_close_matches(name, list(available.keys()), n=3, cutoff=0.5)
        if close:
            suggestions = ", ".join(close)
            warnings.warn(
                f"Widget '{name}' not found. Did you mean: {suggestions}?"
            )
            return None

    # 3. No matches at all
    warnings.warn(
        f"Widget '{name}' not found. "
        f"Create it at ./widgets/{name}.rosh"
    )
    return None


def _list_available(search_paths: list[Path]) -> dict[str, Path]:
    """List all available widget names → paths."""
    available: dict[str, Path] = {}
    for base in search_paths:
        if not base.is_dir():
            continue
        for ext in ("*.rosh", "*.py"):
            for f in base.glob(ext):
                # Skip __init__.py and other non-widget Python files
                if f.name.startswith("_"):
                    continue
                widget_name = f.stem
                if widget_name not in available:
                    available[widget_name] = f
    return available


def load_widget(
    name: str,
    config: dict[str, str] | None = None,
    search_paths: list[Path] | None = None,
    _loading: set[str] | None = None,
) -> list[Statement]:
    """Load a widget: find, parse, prefix, apply config.

    Returns a list of namespace-prefixed statements ready to execute.
    Returns empty list if widget not found (graceful fallback).

    The _loading set tracks widgets currently being loaded to detect
    circular dependencies. On circular dep: warn and skip (Roshonic).
    """
    # Circular dependency guard
    if _loading is None:
        _loading = set()

    if name in _loading:
        warnings.warn(f"Circular dependency: widget '{name}' is already loading, skipping")
        return []

    path = find_widget(name, search_paths)
    if path is None:
        return []

    _loading.add(name)
    try:
        # Python factory — call generate(), get raw statements
        if path.suffix == ".py":
            return _load_python_factory(path, name, config or {})

        programme = parse_file(path)

        # Resolve nested use statements, then prefix everything
        expanded: list[Statement] = []
        for stmt in programme.statements:
            if isinstance(stmt, UseStatement):
                # Load nested widget — returns statements already prefixed
                # with the nested widget's namespace
                nested = load_widget(
                    stmt.name,
                    config=stmt.config if stmt.config else None,
                    search_paths=search_paths,
                    _loading=_loading,
                )
                expanded.extend(nested)
            else:
                expanded.append(stmt)

        # Prefix everything with this widget's namespace
        prefixed = [_prefix_statement(s, name) for s in expanded]

        # Apply config overrides as set statements
        if config:
            config_stmts: list[Statement] = []
            for key, value in config.items():
                config_stmts.append(SetStatement(target=f"{name}.{key}", value=value))
            prefixed.extend(config_stmts)

        return prefixed
    finally:
        _loading.discard(name)


def _import_factory_module(path: Path) -> Any:
    """Import a Python factory module from an arbitrary path."""
    spec = importlib.util.spec_from_file_location(f"rosh_widget_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load factory module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_python_factory(
    path: Path,
    name: str,
    config: dict[str, str],
) -> list[Statement]:
    """Load a Python widget factory: import, call generate(), prefix output."""
    module = _import_factory_module(path)

    generate_fn = getattr(module, "generate", None)
    if generate_fn is None:
        warnings.warn(f"Widget factory '{name}' has no generate() function")
        return []

    # Merge module default config with caller overrides
    meta = getattr(module, "METADATA", {})
    merged_config = dict(meta.get("config", {}))
    merged_config.update(config)

    raw_stmts: list[Statement] = generate_fn(merged_config)
    return [_prefix_statement(s, name) for s in raw_stmts]


def prefix_programme(programme: Programme, namespace: str) -> list[Statement]:
    """Apply namespace prefix to all names in a programme's statements.

    Rules (per proposal):
    - All bare names in create/set/destroy/when-args get prefixed
    - Dotted names get prefix before first part
    - Interpolation references get prefixed
    - Event names in when/send stay global
    """
    return [_prefix_statement(stmt, namespace) for stmt in programme.statements]


def _prefix_statement(stmt: Statement, ns: str) -> Statement:
    """Prefix a single statement's names."""
    if isinstance(stmt, CreateStatement):
        return CreateStatement(
            kind=stmt.kind,
            name=f"{ns}.{stmt.name}",
            parent=f"{ns}.{stmt.parent}" if stmt.parent else "",
            count=stmt.count,
            line=stmt.line,
        )

    if isinstance(stmt, SetStatement):
        return SetStatement(
            target=_prefix_name(stmt.target, ns),
            value=_prefix_set_value(stmt.target, stmt.value, ns),
            line=stmt.line,
        )

    if isinstance(stmt, DestroyStatement):
        return DestroyStatement(
            name=_prefix_name(stmt.name, ns),
            line=stmt.line,
        )

    if isinstance(stmt, WhenStatement):
        # Event name stays global; args (object names) get prefixed
        return WhenStatement(
            event=stmt.event,
            args=[_prefix_name(a, ns) for a in stmt.args],
            line=stmt.line,
        )

    if isinstance(stmt, SendStatement):
        # Event name stays global; payload keys stay as-is
        return SendStatement(
            event=stmt.event,
            payload=stmt.payload,
            line=stmt.line,
        )

    if isinstance(stmt, PrintStatement):
        return PrintStatement(
            text=_prefix_interpolation(stmt.text, ns),
            line=stmt.line,
        )

    if isinstance(stmt, SayStatement):
        return SayStatement(
            text=_prefix_interpolation(stmt.text, ns),
            line=stmt.line,
        )

    if isinstance(stmt, SpriteStatement):
        return SpriteStatement(
            name=_prefix_name(stmt.name, ns),
            description=stmt.description,
            line=stmt.line,
        )

    if isinstance(stmt, SoundStatement):
        return SoundStatement(
            name=_prefix_name(stmt.name, ns),
            description=stmt.description,
            line=stmt.line,
        )

    if isinstance(stmt, PlayStatement):
        return PlayStatement(
            sound=_prefix_name(stmt.sound, ns),
            mode=stmt.mode,
            line=stmt.line,
        )

    if isinstance(stmt, OnStatement):
        new_args = _prefix_on_args(stmt.action, stmt.args, ns)
        new_condition = _prefix_on_condition(stmt.condition, ns) if stmt.condition else ""
        return OnStatement(
            event=stmt.event,
            action=stmt.action,
            args=new_args,
            condition=new_condition,
            line=stmt.line,
        )

    if isinstance(stmt, AnimateStatement):
        return AnimateStatement(
            name=_prefix_name(stmt.name, ns),
            sheet=stmt.sheet,
            frames=stmt.frames,
            speed=stmt.speed,
            mode=stmt.mode,
            line=stmt.line,
        )

    if isinstance(stmt, IfStatement):
        return IfStatement(
            condition=_prefix_on_condition(stmt.condition, ns) if stmt.condition else "",
            then_body=[_prefix_statement(s, ns) for s in stmt.then_body],
            else_body=[_prefix_statement(s, ns) for s in stmt.else_body],
            line=stmt.line,
        )

    if isinstance(stmt, AfterStatement):
        # Event names stay global (like send), delay unchanged
        return stmt

    # Comments, blanks, end, event declarations, etc. — pass through
    return stmt


def _prefix_name(name: str, ns: str) -> str:
    """Prefix a name: 'value' → 'ns.value', 'display.x' → 'ns.display.x'."""
    return f"{ns}.{name}"


def _prefix_set_value(target: str, value: str, ns: str) -> str:
    """Prefix references in a set value expression.

    Handles: quoted strings (no prefix), arithmetic (prefix target ref),
    interpolation, bare references.
    """
    # Quoted strings — don't touch (but prefix interpolation inside)
    if (value.startswith('"') and value.endswith('"')) or \
       (value.startswith("'") and value.endswith("'")):
        inner = value[1:-1]
        prefixed_inner = _prefix_interpolation(inner, ns)
        return value[0] + prefixed_inner + value[-1]

    # Arithmetic: "target + 1" → "ns.target + 1", "target + drift" → "ns.target + ns.drift"
    for op in ("+", "-", "*", "/"):
        sep = f" {op} "
        if sep in value:
            parts = value.split(sep, 1)
            left = parts[0].strip()
            right = parts[1].strip()
            # Prefix the left operand (always a name reference)
            prefixed_left = _prefix_name(left, ns)
            # Prefix the right operand if it's a name (not a numeric literal)
            try:
                float(right)
            except ValueError:
                right = _prefix_name(right, ns)
            return f"{prefixed_left}{sep}{right}"

    # Interpolation in unquoted strings
    if "{" in value:
        return _prefix_interpolation(value, ns)

    return value


def _prefix_on_args(action: str, args: str, ns: str) -> str:
    """Prefix references in an OnStatement's args based on the action type."""
    if not args:
        return args

    if action == "set":
        # Format: "target to value" — prefix target and value refs
        if " to " in args:
            target_part, value_part = args.split(" to ", 1)
            prefixed_target = _prefix_name(target_part.strip(), ns)
            prefixed_value = _prefix_set_value(target_part.strip(), value_part.strip(), ns)
            return f"{prefixed_target} to {prefixed_value}"
        return args

    if action == "send":
        # Event name stays global
        return args

    if action in ("say", "print"):
        # Prefix interpolation {name} → {ns.name}
        return _prefix_interpolation(args, ns)

    if action == "destroy":
        # Prefix the object name
        return _prefix_name(args.strip(), ns)

    return args


def _prefix_on_condition(condition: str, ns: str) -> str:
    """Prefix the field name in an on-when condition.

    Condition format: "field op value" — prefix the field, keep op and value literal.
    """
    parts = condition.split(None, 2)
    if len(parts) < 3:
        return condition
    field, op, value = parts
    return f"{_prefix_name(field, ns)} {op} {value}"


def _prefix_interpolation(text: str, ns: str) -> str:
    """Prefix {name} references in text: {value} → {ns.value}."""

    def _replace(match: re.Match[str]) -> str:
        key = match.group(1)
        return "{" + _prefix_name(key, ns) + "}"

    return _INTERP_RE.sub(_replace, text)
