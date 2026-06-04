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
import shlex
import warnings
from pathlib import Path
from typing import Any

from rosh_lang.core.model import (
    AddStatement,
    AfterStatement,
    AnimateStatement,
    CreateStatement,
    DefineStatement,
    DestroyStatement,
    DoStatement,
    ForEachStatement,
    IfStatement,
    OnStatement,
    PlayStatement,
    PrintStatement,
    Programme,
    RemoveStatement,
    RepeatStatement,
    SayStatement,
    SendStatement,
    SetStatement,
    SoundStatement,
    SpriteStatement,
    Statement,
    UseStatement,
    WhenStatement,
)
from rosh_lang.core.parser import parse_file

_INTERP_RE = re.compile(r"\{([^}]+)\}")
_META_RE = re.compile(
    r"^#\s*(widget|version|description|config|licence|provides|requires|exposes):\s*(.+)$"
)

# ── HUD anchor/theme system ──────────────────────────────────

_HUD_ANCHORS: dict[str, tuple[str, str]] = {
    "top-left":      ("0.02", "0.02"),
    "top-center":    ("0.40", "0.02"),
    "top-right":     ("0.78", "0.02"),
    "bottom-left":   ("0.02", "0.90"),
    "bottom-center": ("0.40", "0.90"),
    "bottom-right":  ("0.78", "0.90"),
}

_HUD_THEMES: dict[str, dict[str, str]] = {
    "dark":    {"bg": "#333",    "text_color": "#fff", "font_size": "14px"},
    "light":   {"bg": "#eee",    "text_color": "#222", "font_size": "14px"},
    "retro":   {"bg": "#001100", "text_color": "#0f0", "font_size": "14px"},
    "minimal": {"bg": "transparent", "text_color": "#fff", "font_size": "14px"},
}

_HUD_STACK_HEIGHT = 0.07  # vertical offset per stacked item

# Tracks how many widgets are at each anchor position (module-level, reset per programme)
_hud_stack_counts: dict[str, int] = {}


def reset_hud_stack() -> None:
    """Reset the HUD anchor stack counter. Call at the start of each programme."""
    _hud_stack_counts.clear()


def compute_hud_position(
    config: dict[str, str],
    user_config: dict[str, str] | None = None,
) -> tuple[str, str, str, str, str]:
    """Compute (x, y, bg, text_color, font_size) from anchor/theme config.

    If no anchor is set, returns the explicit x/y from config (backward compatible).
    user_config, when provided, contains only keys the user explicitly set
    (allowing theme to override factory defaults while user overrides win).
    """
    # Theme defaults — theme overrides factory defaults but user overrides win
    theme_name = config.get("theme", "")
    theme = _HUD_THEMES.get(theme_name, {})

    # When user_config is provided (factory path), use it to detect user overrides.
    # When not provided (direct call), treat config as the user's values.
    user = user_config if user_config is not None else config

    # Priority: user explicit > theme > factory default (config)
    bg = user.get("bg", theme.get("bg", config.get("bg", "#333")))
    text_color = user.get("text_color", theme.get("text_color", config.get("text_color", "#fff")))
    font_size = user.get("font_size", theme.get("font_size", config.get("font_size", "14px")))

    anchor = config.get("anchor", "")
    if anchor and anchor in _HUD_ANCHORS:
        base_x, base_y = _HUD_ANCHORS[anchor]
        stack_idx = _hud_stack_counts.get(anchor, 0)
        _hud_stack_counts[anchor] = stack_idx + 1

        # Stack direction: top anchors stack downward, bottom stack upward
        offset = stack_idx * _HUD_STACK_HEIGHT
        y_val = float(base_y)
        if anchor.startswith("bottom"):
            y_val -= offset
        else:
            y_val += offset

        return base_x, f"{y_val:.2f}", bg, text_color, font_size

    # No anchor — use explicit x/y (backward compatible)
    x = config.get("x", "0.02")
    y = config.get("y", "0.02")
    return x, y, bg, text_color, font_size


def get_bundled_library_path() -> Path:
    """Return the path to the bundled widget library shipped with rosh-lang."""
    return Path(__file__).parent.parent / "library"


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

    Returns dict with keys: widget, version, description, config, licence, provides, requires, exposes.
    """
    meta: dict[str, Any] = {
        "widget": path.stem, "version": "", "description": "", "config": {}, "licence": "",
        "provides": [], "requires": [], "exposes": [],
    }

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
            for pair in shlex.split(value):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    meta["config"][k] = v
        elif key in ("provides", "requires", "exposes"):
            meta[key] = [item for item in re.split(r"[\s,]+", value) if item]
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
    for key in ("provides", "requires", "exposes"):
        if key in raw and isinstance(raw[key], list):
            meta[key] = raw[key]
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
    namespace: str | None = None,
    search_paths: list[Path] | None = None,
    _loading: set[str] | None = None,
) -> list[Statement]:
    """Load a widget: find, parse, prefix, apply config.

    Returns a list of namespace-prefixed statements ready to execute.
    Returns empty list if widget not found (graceful fallback).

    namespace: when set (e.g. from `use score as hud1`), all name prefixes
    use this value instead of the component name. The component file is still
    found by name. Circular-dependency tracking always uses the component name.
    """
    ns = namespace or name

    # Circular dependency guard (always keyed on component name, not alias)
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
            return _load_python_factory(path, ns, config or {})

        programme = parse_file(path)
        meta = parse_metadata(path)
        declared_config = dict(meta.get("config", {}))
        merged_config = dict(declared_config)
        merged_config.update(config or {})

        # Resolve nested use statements, then prefix everything
        expanded: list[Statement] = []
        for stmt in programme.statements:
            if isinstance(stmt, UseStatement):
                # Load nested widget — returns statements already prefixed
                # with the nested widget's namespace
                nested = load_widget(
                    stmt.name,
                    config=stmt.config if stmt.config else None,
                    namespace=stmt.alias,
                    search_paths=search_paths,
                    _loading=_loading,
                )
                expanded.extend(nested)
            else:
                expanded.append(stmt)

        # Prefix everything with the resolved namespace
        prefixed = [_prefix_statement(s, ns) for s in expanded]

        # Declared config is available before the component body at ns.config.*.
        config_stmts = [
            SetStatement(target=f"{ns}.config.{key}", value=value)
            for key, value in merged_config.items()
        ]

        # Caller keys also remain direct post-load overrides for compatibility,
        # especially existing components and dotted paths such as display.x.
        direct_overrides = [
            SetStatement(target=f"{ns}.{key}", value=value)
            for key, value in (config or {}).items()
        ]

        return config_stmts + prefixed + direct_overrides
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

    # Pass user_config so factories can distinguish user overrides from defaults
    import inspect
    sig = inspect.signature(generate_fn)
    if len(sig.parameters) >= 2:
        raw_stmts: list[Statement] = generate_fn(merged_config, config)
    else:
        raw_stmts = generate_fn(merged_config)
    # Allow factories to declare external names that bypass prefixing
    widget_globals = set(getattr(module, "GLOBALS", []))
    if widget_globals:
        _GLOBAL_NAMES_EXTRA.update(widget_globals)
    try:
        prefixed = [_prefix_statement(s, name) for s in raw_stmts]
    finally:
        if widget_globals:
            _GLOBAL_NAMES_EXTRA.difference_update(widget_globals)

    # Apply config overrides as set statements for keys not in METADATA config
    # (e.g. dotted-path overrides like "box.label" or "display.x")
    factory_keys = set(meta.get("config", {}).keys())
    config_stmts: list[Statement] = []
    for key, value in config.items():
        if key not in factory_keys:
            config_stmts.append(SetStatement(target=f"{name}.{key}", value=value))
    prefixed.extend(config_stmts)

    return prefixed


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
            name=_prefix_name(stmt.name, ns),
            parent=_prefix_name(stmt.parent, ns) if stmt.parent else "",
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

    if isinstance(stmt, DefineStatement):
        return DefineStatement(
            name=_prefix_name(stmt.name, ns),
            params=[_prefix_name(p, ns) for p in stmt.params],
            body=[_prefix_statement(s, ns) for s in stmt.body],
            line=stmt.line,
        )

    if isinstance(stmt, DoStatement):
        return DoStatement(
            name=_prefix_name(stmt.name, ns),
            args={
                _prefix_name(k, ns): _prefix_value_reference(v, ns)
                for k, v in stmt.args.items()
            },
            line=stmt.line,
        )

    if isinstance(stmt, RepeatStatement):
        return RepeatStatement(
            count=_prefix_value_reference(stmt.count, ns),
            var=_prefix_name(stmt.var, ns) if stmt.var else "",
            body=[_prefix_statement(s, ns) for s in stmt.body],
            line=stmt.line,
        )

    if isinstance(stmt, AddStatement):
        return AddStatement(
            item=_prefix_value_reference(stmt.item, ns),
            target=_prefix_name(stmt.target, ns),
            line=stmt.line,
        )

    if isinstance(stmt, RemoveStatement):
        return RemoveStatement(
            item=_prefix_value_reference(stmt.item, ns),
            target=_prefix_name(stmt.target, ns),
            line=stmt.line,
        )

    if isinstance(stmt, ForEachStatement):
        return ForEachStatement(
            var=_prefix_name(stmt.var, ns),
            target=_prefix_name(stmt.target, ns),
            body=[_prefix_statement(s, ns) for s in stmt.body],
            line=stmt.line,
        )

    # Comments, blanks, end, event declarations, etc. — pass through
    return stmt


# Runtime globals that should never be namespace-prefixed inside widgets.
_GLOBAL_NAMES = frozenset({"_keys", "_paused", "_max_output", "_scene", "_prev_scene"})
# Event payload field names that should not be prefixed in conditions
_PAYLOAD_FIELDS = frozenset({"key", "x", "y", "a", "b", "scene", "name"})
# Per-widget extra globals (set temporarily during factory prefixing via GLOBALS metadata)
_GLOBAL_NAMES_EXTRA: set[str] = set()


def _prefix_name(name: str, ns: str) -> str:
    """Prefix a name: 'value' → 'ns.value', 'display.x' → 'ns.display.x'.

    Special case: '_self' maps to the namespace root, so factories can create
    objects that live directly at the namespace level instead of nested inside it.
    '_self' → 'ns', '_self.x' → 'ns.x'.

    Global runtime names (_keys, _paused, etc.) are never prefixed.
    """
    if name == "_self":
        return ns
    if name.startswith("_self."):
        return f"{ns}.{name[6:]}"
    # Don't prefix global runtime names or widget-declared globals
    root = name.split(".")[0]
    if root in _GLOBAL_NAMES or root in _GLOBAL_NAMES_EXTRA:
        return name
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

    # Random: "random" stays as-is, "random min max" stays as-is (no names to prefix)
    if value == "random" or (value.startswith("random ") and len(value.split()) == 3):
        return value

    if value.startswith("count of "):
        list_name = value[len("count of "):].strip()
        return f"count of {_prefix_name(list_name, ns)}"

    # Clamp: "clamp field min max" — prefix the field reference
    if value.startswith("clamp "):
        parts = value.split()
        if len(parts) == 4:
            return f"clamp {_prefix_name(parts[1], ns)} {parts[2]} {parts[3]}"

    # Arithmetic: "target + 1" → "ns.target + 1", "target + drift" → "ns.target + ns.drift"
    for op in (">=", "<=", "==", "!=", ">", "<", "+", "-", "*", "/"):
        sep = f" {op} "
        if sep in value:
            parts = value.split(sep, 1)
            left = _prefix_value_reference(parts[0].strip(), ns)
            right = _prefix_value_reference(parts[1].strip(), ns)
            return f"{left}{sep}{right}"

    # Interpolation in unquoted strings
    if "{" in value:
        return _prefix_interpolation(value, ns)

    if "." in value:
        return _prefix_value_reference(value, ns)
    return value


def _prefix_value_reference(value: str, ns: str) -> str:
    """Prefix a bare value only when it is a state reference."""
    if (value.startswith('"') and value.endswith('"')) or \
       (value.startswith("'") and value.endswith("'")):
        inner = _prefix_interpolation(value[1:-1], ns)
        return value[0] + inner + value[-1]
    if value.lower() in ("true", "false", "nothing", "none"):
        return value
    try:
        float(value)
        return value
    except ValueError:
        pass
    if any(char.isspace() for char in value):
        return value
    if value.startswith("#"):
        return value
    return _prefix_name(value, ns)


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

    if action == "do":
        # Prefix the function name
        return _prefix_name(args.strip(), ns)

    return args


def _prefix_on_condition(condition: str, ns: str) -> str:
    """Prefix the field name in an on-when condition.

    Condition format: "field op value" — prefix the field, keep op and value literal.
    Event payload fields (key, x, y, a, b, scene, name) are NOT prefixed
    since they're injected by the runtime during event dispatch.
    """
    parts = condition.split(None, 2)
    if len(parts) < 3:
        return condition
    field, op, value = parts
    # Don't prefix event payload fields
    if field in _PAYLOAD_FIELDS:
        return condition
    return f"{_prefix_name(field, ns)} {op} {value}"


def _prefix_interpolation(text: str, ns: str) -> str:
    """Prefix {name} references in text: {value} → {ns.value}."""

    def _replace(match: re.Match[str]) -> str:
        key = match.group(1)
        return "{" + _prefix_name(key, ns) + "}"

    return _INTERP_RE.sub(_replace, text)
