"""Three.js target — render a Rosh programme as a 3D scene in HTML.

Two entry points:
- render_threejs(programme) → str   (testable, no I/O)
- serve_threejs(programme, auto_open) (starts HTTP server)

Uses JS_RUNTIME_CORE (shared) + JS_RUNTIME_THREEJS (Three.js renderer).
No 2D sprites or spritesheet animations — objects use color materials or GLB models.
"""

from __future__ import annotations

import http.server
import io
import json
import socketserver
import webbrowser
from html import escape
from typing import Any

from pathlib import Path

from rosh_lang.core.model import PrintStatement, Programme, SayStatement
from rosh_lang.core.runtime import Runtime
from rosh_lang.media.sounds import generate_sound_params
from rosh_lang.targets._js_codegen import compile_programme
from rosh_lang.targets._js_runtime import JS_RUNTIME_CORE, JS_TOUCH_CONTROLS
from rosh_lang.targets._js_runtime_threejs import JS_RUNTIME_THREEJS, JS_RUNTIME_CONSOLE
from rosh_lang.targets.web import _generate_audio_data

THREEJS_CDN = "https://cdn.jsdelivr.net/npm/three@0.128.0/build/three.min.js"
ORBIT_CDN = "https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"
GLTF_CDN = "https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/GLTFLoader.js"
COPYRIGHT = "(c) Rosh Studio 2026 — rosh.cloud"

# rosh-natural.js — shared NLP layer; inlined at build time so standalone demos
# (uploaded to R2) carry it without needing the portal as a dependency.
_ROSH_NATURAL_PATH = Path(__file__).parents[4] / "rosh-portal/static/js/rosh-natural.js"
ROSH_NATURAL_JS = _ROSH_NATURAL_PATH.read_text() if _ROSH_NATURAL_PATH.exists() else ""


# ── HTML generation ───────────────────────────────────────────


def render_threejs(
    programme: Programme,
    search_paths: list[Path] | None = None,
) -> str:
    """Render a programme as a Three.js 3D scene in HTML."""
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

    # Collect audio data (no sprites/animation in 3D)
    audio_data = _generate_audio_data(programme)
    for name, desc in rt.audio_registry.items():
        if name not in audio_data:
            audio_data[name] = generate_sound_params(name, desc)

    # Compile to JS
    compiled = compile_programme(programme, search_paths=search_paths, target="threejs")

    # Build script block
    script_parts = [JS_RUNTIME_CORE, "", "// ── Init ──", compiled.init_code]

    # Inject audio data
    if audio_data:
        audio_pairs = ", ".join(
            f'"{escape(k)}": {json.dumps(v, separators=(",", ":"))}'
            for k, v in audio_data.items()
        )
        script_parts.append(f"rosh._audioData = {{{audio_pairs}}};")

    if compiled.has_handlers:
        script_parts.extend(["", "// ── Handlers ──", compiled.handler_code])

    # Three.js renderer layer (always included — it creates the scene)
    script_parts.extend(["", "// ── Three.js renderer ──", JS_RUNTIME_THREEJS])
    script_parts.append(JS_TOUCH_CONTROLS)
    script_parts.extend(["", "// ── Live console ──", JS_RUNTIME_CONSOLE])

    script_block = "\n".join(script_parts)

    return _threejs_html_page(script_block)


def _threejs_html_page(script: str) -> str:
    """Build the full Three.js HTML page shell."""
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
      align-items: center;
    }}
    #scene-container {{
      margin-top: 16px;
    }}
    #scene-container canvas {{
      display: block;
      border-radius: 4px;
      max-width: 100%;
      height: auto;
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
  </style>
</head>
<body>
  <div id="scene-container"></div>
  <footer>{escape(COPYRIGHT)}</footer>
  <script src="{THREEJS_CDN}"></script>
  <script src="{ORBIT_CDN}"></script>
  <script src="{GLTF_CDN}"></script>
  <script>
{ROSH_NATURAL_JS}
  </script>
  <script>
if (typeof THREE === "undefined") {{
  document.body.innerHTML = '<p style="color:red;padding:20px">Error: Three.js failed to load from CDN</p>';
}} else {{
try {{
{script}
}} catch(e) {{
  document.body.innerHTML = '<pre style="color:red;padding:20px">' + e.stack + '</pre>';
  console.error(e);
}}
}}
  </script>
</body>
</html>"""


# ── HTTP server ───────────────────────────────────────────────


def serve_threejs(
    programme: Programme,
    *,
    auto_open: bool = False,
    search_paths: list[Path] | None = None,
) -> None:
    """Start an HTTP server that serves the Three.js-rendered programme."""
    html = render_threejs(programme, search_paths=search_paths)
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
        print(f"Serving Three.js scene at {url} — Ctrl-C to stop")

        if auto_open:
            webbrowser.open(url)

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")
