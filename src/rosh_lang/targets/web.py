"""Web target — render a Rosh programme as an HTML page.

Two entry points:
- render_html(programme) → str   (testable, no I/O)
- serve_web(programme, auto_open) (starts HTTP server)

Static programmes produce the same output as before (no JS).
Interactive programmes (any WhenStatement) emit a self-contained
HTML+JS page using the JS runtime and codegen layers.
"""

from __future__ import annotations

import http.server
import io
import re
import socketserver
import webbrowser
from html import escape
from typing import Any

from rosh_lang import __version__
from pathlib import Path

from rosh_lang.core.model import (
    AnimateStatement,
    BackgroundStatement,
    PrintStatement,
    Programme,
    SayStatement,
    SoundStatement,
    UseStatement,
    WhenStatement,
)
from rosh_lang.core.runtime import Runtime
from rosh_lang.media.sounds import generate_sound_params
from rosh_lang.media.sprites import generate_sprite
from rosh_lang.targets._js_codegen import compile_programme
from rosh_lang.targets._js_runtime import JS_RUNTIME, JS_TOUCH_CONTROLS

COPYRIGHT = f"(c) Rosh Studio 2026 — rosh.cloud"

_VISUAL_PROPS = {"x", "y", "width", "height", "color", "label", "sprite"}

# ── HTML generation ───────────────────────────────────────────


def _css_value(value: float | int) -> str:
    """Convert a numeric value to a CSS length.

    Per spec:
    - 0.0–1.0 → percentage of viewport
    - >1.0 → pixels
    """
    if isinstance(value, (int, float)):
        if 0.0 <= value <= 1.0:
            return f"{value * 100}%"
        return f"{value}px"
    return "0%"


def _generate_sprite_data(
    objects: list[tuple[str, dict[str, Any]]],
) -> dict[str, str]:
    """Generate data URIs for all objects that have a sprite description."""
    sprite_data: dict[str, str] = {}
    for name, obj in objects:
        desc = obj.get("sprite")
        if desc and isinstance(desc, str):
            sprite_data[name] = generate_sprite(name, desc)
    return sprite_data


def _generate_audio_data(programme: Programme) -> dict[str, dict[str, Any]]:
    """Generate synthesis parameters for all sound statements in a programme."""
    audio_data: dict[str, dict[str, Any]] = {}
    for stmt in programme.statements:
        if isinstance(stmt, SoundStatement):
            audio_data[stmt.name] = generate_sound_params(stmt.name, stmt.description)
        elif isinstance(stmt, WhenStatement):
            # Sound statements can also appear inside when/end blocks —
            # walk ahead to collect them (the compile step handles codegen,
            # but we still need to register the params data for injection)
            pass
    # Also check the runtime's audio_registry (it captured sounds from
    # when-block bodies and use-widget expansions during .run())
    return audio_data


def _generate_animation_data(
    programme: Programme,
    runtime: Runtime,
    search_paths: list[Path] | None = None,
    source_dir: Path | None = None,
) -> dict[str, dict[str, Any]]:
    """Slice spritesheets and build animation data for all animate statements.

    Returns: {name: {frames: [uri...], speed: N, mode: "loop"}}
    """
    from rosh_lang.media.assets import resolve_asset
    from rosh_lang.media.sheets import slice_spritesheet

    anim_data: dict[str, dict[str, Any]] = {}

    # Collect from programme statements
    for stmt in programme.statements:
        if isinstance(stmt, AnimateStatement):
            _process_animate(stmt, anim_data, search_paths, source_dir)

    # Collect from runtime registry (animate inside when blocks / use widgets)
    for name, info in runtime.animation_registry.items():
        if name not in anim_data:
            sheet_path = resolve_asset(
                info["sheet"], search_paths=search_paths, source_dir=source_dir,
            )
            if sheet_path:
                frames = slice_spritesheet(sheet_path, info["frames"])
                anim_data[name] = {
                    "frames": frames,
                    "speed": info["speed"],
                    "mode": info["mode"],
                }

    return anim_data


def _process_animate(
    stmt: AnimateStatement,
    anim_data: dict[str, dict[str, Any]],
    search_paths: list[Path] | None = None,
    source_dir: Path | None = None,
) -> None:
    """Process a single AnimateStatement into animation data."""
    from rosh_lang.media.assets import resolve_asset
    from rosh_lang.media.sheets import slice_spritesheet

    sheet_path = resolve_asset(
        stmt.sheet, search_paths=search_paths, source_dir=source_dir,
    )
    if sheet_path is None:
        import warnings
        warnings.warn(f"Spritesheet not found: {stmt.sheet!r}")
        return

    frames = slice_spritesheet(sheet_path, stmt.frames)
    anim_data[stmt.name] = {
        "frames": frames,
        "speed": stmt.speed,
        "mode": stmt.mode,
    }


def _render_object(
    name: str, obj: dict[str, Any], sprite_data: dict[str, str] | None = None
) -> str:
    """Render a single object as an absolutely-positioned div."""
    x = obj.get("x", None)
    y = obj.get("y", None)
    w = obj.get("width", 0.1)
    h = obj.get("height", 0.1)
    color = obj.get("color", "#444")
    label = obj.get("label", "")

    has_position = x is not None or y is not None

    styles: list[str] = []
    if has_position:
        styles.append("position: absolute")
        styles.append(f"left: {_css_value(x if x is not None else 0)}")
        styles.append(f"top: {_css_value(y if y is not None else 0)}")
    styles.append(f"width: {_css_value(w)}")
    styles.append(f"height: {_css_value(h)}")
    # Sprite overlay (if available)
    data_uri = (sprite_data or {}).get(name)
    if data_uri:
        styles.append("background-color: transparent")
        styles.append(f"background-image: url({data_uri})")
        styles.append("background-size: 100% 100%")
        styles.append("background-repeat: no-repeat")
        styles.append("background-position: center")
        styles.append("image-rendering: pixelated")
    else:
        styles.append(f"background-color: {escape(str(color))}")
    styles.append("display: flex")
    styles.append("align-items: center")
    styles.append("justify-content: center")
    styles.append("box-sizing: border-box")
    shape = obj.get("shape", "")
    styles.append("border-radius: 50%" if shape in ("circle", "sphere", "ball") else "border-radius: 4px")
    text_color = obj.get("text_color", "#fff")
    font_size = obj.get("font_size", "14px")
    styles.append(f"color: {escape(str(text_color))}")
    styles.append(f"font-size: {escape(str(font_size))}")
    styles.append("font-family: system-ui, sans-serif")

    if not has_position:
        styles.append("position: relative")
        styles.append("margin: 8px auto")

    style_str = "; ".join(styles)
    escaped_label = escape(str(label)) if not data_uri else ""
    escaped_name = escape(name)
    return f'    <div class="rosh-object" data-name="{escaped_name}" style="{style_str}">{escaped_label}</div>'


def _collect_objects(state: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """Collect renderable objects from state, including inside namespaces.

    A dict containing nested sub-objects (dicts with visual props) is a
    namespace — look inside it for the actual renderable objects.
    A dict with visual properties but no nested objects is itself renderable.
    """
    objects: list[tuple[str, dict[str, Any]]] = []
    for key, value in state.items():
        if key.startswith("_"):
            continue
        if isinstance(value, dict):
            # Check for nested sub-objects first — if any exist, this is a namespace
            nested = [
                (subkey, subval)
                for subkey, subval in value.items()
                if isinstance(subval, dict) and (subval.keys() & _VISUAL_PROPS)
            ]
            if nested:
                # Namespace — collect the nested objects
                for subkey, subval in nested:
                    objects.append((f"{key}.{subkey}", subval))
            elif value.keys() & _VISUAL_PROPS:
                # Leaf object with visual properties
                objects.append((key, value))
    return objects


def _is_interactive(programme: Programme) -> bool:
    """Check if a programme has any when/end event handlers or use statements."""
    return any(
        isinstance(s, (WhenStatement, UseStatement))
        for s in programme.statements
    )


def render_html(
    programme: Programme,
    search_paths: list[Path] | None = None,
) -> str:
    """Render a programme as HTML. Routes to static or interactive path."""
    if _is_interactive(programme):
        return _render_interactive(programme, search_paths)
    return _render_static(programme, search_paths)


def _render_static(
    programme: Programme,
    search_paths: list[Path] | None = None,
) -> str:
    """Render a static programme — no JS, identical to pre-Step-6 output."""
    buf = io.StringIO()
    rt = Runtime(output=buf, search_paths=search_paths)
    rt.run(programme)

    text_output = buf.getvalue()

    # Collect renderable objects from state (handles namespaces)
    objects = _collect_objects(rt.state)

    # Generate sprite data URIs for objects with sprite descriptions
    sprite_data = _generate_sprite_data(objects)

    # Build object divs
    object_divs = "\n".join(
        _render_object(name, obj, sprite_data) for name, obj in objects
    )

    # Build HTML
    escaped_output = escape(text_output)
    canvas_bg = rt.state.get("_background", "#16213e")

    return _html_page(object_divs, escaped_output, canvas_bg=canvas_bg)


def _render_interactive(
    programme: Programme,
    search_paths: list[Path] | None = None,
) -> str:
    """Render an interactive programme — embeds JS runtime + codegen output."""
    # Run Python runtime for initial state (top-level creates/sets).
    # Filter out print/say — JS codegen already emits appendOutput() for those.
    filtered = Programme(
        statements=[
            s for s in programme.statements
            if not isinstance(s, (PrintStatement, SayStatement))
        ],
        source=programme.source,
    )
    buf = io.StringIO()
    rt = Runtime(output=buf, search_paths=search_paths)
    rt.run(filtered)

    text_output = buf.getvalue()

    # Initial object divs (from Python runtime, handles namespaces)
    objects = _collect_objects(rt.state)
    sprite_data = _generate_sprite_data(objects)
    object_divs = "\n".join(
        _render_object(name, obj, sprite_data) for name, obj in objects
    )

    # Collect audio data from top-level sound statements + runtime registry
    audio_data = _generate_audio_data(programme)
    # Merge in any sounds discovered during runtime (from when blocks, use widgets)
    for name, desc in rt.audio_registry.items():
        if name not in audio_data:
            audio_data[name] = generate_sound_params(name, desc)

    # Compile to JS
    compiled = compile_programme(programme, search_paths=search_paths)
    escaped_output = escape(text_output)

    # Build script block
    script_parts = [JS_RUNTIME, "", "// ── Init ──", compiled.init_code]

    # Inject sprite data URIs for JS runtime syncAll()
    if sprite_data:
        pairs = ", ".join(
            f'"{escape(k)}": "{v}"' for k, v in sprite_data.items()
        )
        script_parts.append(f"rosh._spriteData = {{{pairs}}};")

    # Inject audio data for JS runtime playAudio()
    if audio_data:
        import json

        audio_pairs = ", ".join(
            f'"{escape(k)}": {json.dumps(v, separators=(",", ":"))}'
            for k, v in audio_data.items()
        )
        script_parts.append(f"rosh._audioData = {{{audio_pairs}}};")

    # Inject animation data (sliced spritesheet frames)
    anim_data = _generate_animation_data(
        programme, rt, search_paths=search_paths,
    )
    if anim_data:
        import json

        anim_init_lines: list[str] = []
        for anim_name, anim_info in anim_data.items():
            frames_json = json.dumps(anim_info["frames"], separators=(",", ":"))
            anim_init_lines.append(
                f'rosh._animData["{escape(anim_name)}"] = '
                f'{{"frames": {frames_json}, '
                f'"speed": {anim_info["speed"]}, '
                f'"mode": "{escape(anim_info["mode"])}", '
                f'"_frame": 0, "_elapsed": 0, "_dir": 1}};'
            )
            # Set initial sprite to frame 0
            anim_init_lines.append(
                f'rosh._spriteData["{escape(anim_name)}"] = {json.dumps(anim_info["frames"][0])};'
            )
        script_parts.extend(anim_init_lines)

    if compiled.has_handlers:
        script_parts.extend(["", "// ── Handlers ──", compiled.handler_code])
    # Fire "start" event after all handlers are registered
    script_parts.append('rosh.send("start", {});')
    if compiled.needs_loop:
        script_parts.extend(["", "// ── Start game loop ──", "rosh.startLoop();"])
    else:
        script_parts.extend(["", "// ── Initial sync ──", "rosh.syncAll();"])
    script_parts.append(JS_TOUCH_CONTROLS)
    script_block = "\n".join(script_parts)

    canvas_bg = rt.state.get("_background", "#16213e")

    return _html_page(object_divs, escaped_output, script_block, canvas_bg=canvas_bg)


_BG_DEFAULT = "#16213e"
_HEX_RE = re.compile(r"^#[0-9a-fA-F]{3,8}$")
_NAMED_RE = re.compile(r"^[a-zA-Z]{1,30}$")
_RGB_RE = re.compile(r"^rgba?\([\d\s,.%/]+\)$")
_HSL_RE = re.compile(r"^hsla?\([\d\s,.%/]+\)$")
_URL_UNSAFE = re.compile(r"""['"<>{|}\\^`\[\]\x00-\x1f]""")
_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}


def _sanitize_background(value: str) -> str:
    """Return value if it is a safe CSS background value, else return the default.

    Prevents CSS injection via } ; { when the value lands in a <style> block,
    and prevents single-quote injection in url('...').
    Accepted forms: hex colour, named colour, rgb/rgba/hsl/hsla, http/https URL,
    data: URI, local image file path.
    """
    v = value.strip()
    if not v:
        return _BG_DEFAULT
    if _HEX_RE.match(v):
        return v
    if _NAMED_RE.match(v):
        return v
    if _RGB_RE.match(v) or _HSL_RE.match(v):
        return v
    if v.startswith("data:image/"):
        return v
    is_url = v.startswith("http://") or v.startswith("https://")
    is_local_image = any(v.lower().endswith(ext) for ext in _IMAGE_EXTS)
    if (is_url or is_local_image) and not _URL_UNSAFE.search(v):
        return v
    return _BG_DEFAULT


def _html_page(
    object_divs: str, escaped_output: str, script: str = "",
    canvas_bg: str = "#16213e",
) -> str:
    """Build the full HTML page shell."""
    script_tag = f"\n  <script>\n{script}\n  </script>" if script else ""

    safe_bg = _sanitize_background(canvas_bg)
    is_image = (
        any(safe_bg.lower().endswith(ext) for ext in _IMAGE_EXTS)
        or safe_bg.startswith("http://")
        or safe_bg.startswith("https://")
        or safe_bg.startswith("data:")
    )
    if is_image:
        bg_css = (
            f"background-image: url('{safe_bg}');\n"
            f"      background-size: cover;\n"
            f"      background-position: center;\n"
            f"      background-repeat: no-repeat"
        )
    else:
        bg_css = f"background: {safe_bg}"

    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>rosh</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      background: #1a1a2e;
      color: #e0e0e0;
      font-family: system-ui, -apple-system, sans-serif;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }}
    #canvas {{
      position: relative;
      width: 100%;
      flex: 1;
      min-height: 60vh;
      {bg_css};
      overflow: hidden;
    }}
    #output {{
      background: #0f3460;
      color: #e0e0e0;
      padding: 16px 24px;
      font-family: "SF Mono", "Fira Code", "Cascadia Code", monospace;
      font-size: 14px;
      line-height: 1.6;
      white-space: pre-wrap;
      min-height: 40px;
    }}
    #output:empty {{
      display: none;
    }}
    footer {{
      background: #1a1a2e;
      color: #555;
      text-align: center;
      padding: 12px;
      font-size: 12px;
      font-family: system-ui, sans-serif;
    }}
    footer a {{
      color: #777;
      text-decoration: none;
    }}
    .rosh-object {{
      image-rendering: pixelated;
      image-rendering: -moz-crisp-edges;
      image-rendering: crisp-edges;
    }}
  </style>
</head>
<body>
  <div id="canvas">
{object_divs}
  </div>
  <pre id="output">{escaped_output}</pre>
  <footer>{escape(COPYRIGHT)}</footer>{script_tag}
</body>
</html>"""


# ── HTTP server ───────────────────────────────────────────────


def serve_web(
    programme: Programme,
    *,
    auto_open: bool = False,
    search_paths: list[Path] | None = None,
) -> None:
    """Start an HTTP server that serves the rendered programme."""
    html = render_html(programme, search_paths=search_paths)
    html_bytes = html.encode("utf-8")

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html_bytes)))
            self.end_headers()
            self.wfile.write(html_bytes)

        def log_message(self, format: str, *args: Any) -> None:
            pass  # suppress request logging

    with socketserver.TCPServer(("", 0), Handler) as httpd:
        port = httpd.server_address[1]
        url = f"http://localhost:{port}"
        print(f"Serving at {url} — Ctrl-C to stop")

        if auto_open:
            webbrowser.open(url)

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")
