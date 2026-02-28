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
import socketserver
import webbrowser
from html import escape
from typing import Any

from rosh_lang import __version__
from pathlib import Path

from rosh_lang.model import Programme, SoundStatement, UseStatement, WhenStatement
from rosh_lang.runtime import Runtime
from rosh_lang.sounds import generate_sound_params
from rosh_lang.sprites import generate_sprite
from rosh_lang.targets._js_codegen import compile_programme
from rosh_lang.targets._js_runtime import JS_RUNTIME

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


def _render_object(
    name: str, obj: dict[str, Any], sprite_data: dict[str, str] | None = None
) -> str:
    """Render a single object as an absolutely-positioned div."""
    x = obj.get("x", None)
    y = obj.get("y", None)
    w = obj.get("width", 0.1)
    h = obj.get("height", 0.1)
    color = obj.get("color", "#444")
    label = obj.get("label", name)

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
    styles.append("border-radius: 4px")
    styles.append("color: #fff")
    styles.append("font-size: 14px")
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

    return _html_page(object_divs, escaped_output)


def _render_interactive(
    programme: Programme,
    search_paths: list[Path] | None = None,
) -> str:
    """Render an interactive programme — embeds JS runtime + codegen output."""
    # Run Python runtime for initial state (top-level creates/sets/prints)
    buf = io.StringIO()
    rt = Runtime(output=buf, search_paths=search_paths)
    rt.run(programme)

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

    if compiled.has_handlers:
        script_parts.extend(["", "// ── Handlers ──", compiled.handler_code])
    if compiled.needs_loop:
        script_parts.extend(["", "// ── Start game loop ──", "rosh.startLoop();"])
    else:
        script_parts.extend(["", "// ── Initial sync ──", "rosh.syncAll();"])
    script_block = "\n".join(script_parts)

    return _html_page(object_divs, escaped_output, script_block)


def _html_page(
    object_divs: str, escaped_output: str, script: str = ""
) -> str:
    """Build the full HTML page shell."""
    script_tag = f"\n  <script>\n{script}\n  </script>" if script else ""

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
      background: #16213e;
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
