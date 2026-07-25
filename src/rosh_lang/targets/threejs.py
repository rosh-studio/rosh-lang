"""Three.js target — render a Rosh programme as a 3D scene in HTML.

Two entry points:
- render_threejs(programme) → str   (testable, no I/O)
- serve_threejs(programme, auto_open) (starts HTTP server)

Uses JS_RUNTIME_CORE (shared) + JS_RUNTIME_THREEJS (Three.js renderer).
No 2D sprites or spritesheet animations — objects use color materials or GLB models.
"""

from __future__ import annotations

import http.server
import importlib.resources
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
#
# This used to be located by counting a fixed number of parent directories
# from this file and reaching sideways into a sibling "rosh-portal/" — which
# breaks differently depending on how deep this file ends up being deployed:
# it raised IndexError when flattened into a Docker image at
# /app/rosh_lang/..., and silently resolved to a wrong, nonexistent path
# (empty string, no error at all) when installed from a wheel into a venv's
# site-packages, as rosh-world does — three real deployment shapes, three
# different failure modes, all for one file. Bundling the file directly
# inside the package and loading it via importlib.resources removes the
# guesswork: it works identically for an editable source checkout, a file
# vendored/copied into another app, or a wheel installed into site-packages.
def _find_rosh_natural_js() -> str:
    try:
        return (
            importlib.resources.files("rosh_lang.targets")
            .joinpath("rosh-natural.js")
            .read_text()
        )
    except (FileNotFoundError, ModuleNotFoundError):
        return ""


ROSH_NATURAL_JS = _find_rosh_natural_js()


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

    _ASSET_CACHE = Path.home() / ".rosh" / "cache" / "3d"
    _MIME = {".glb": "model/gltf-binary", ".gltf": "model/gltf+json"}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            # Serve GLB/GLTF assets from local cache
            if self.path.startswith("/assets/3d/"):
                fname = self.path[len("/assets/3d/"):]
                fpath = _ASSET_CACHE / fname
                if fpath.exists() and fpath.is_file():
                    data = fpath.read_bytes()
                    mime = _MIME.get(fpath.suffix, "application/octet-stream")
                    self.send_response(200)
                    self.send_header("Content-Type", mime)
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
                self.send_response(404)
                self.end_headers()
                return
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
        # flush=True: see web.py's serve_web for why this matters — stdout
        # is fully buffered when not a TTY, and serve_forever() never
        # returns to flush it otherwise.
        print(f"Serving Three.js scene at {url} — Ctrl-C to stop", flush=True)

        if auto_open:
            webbrowser.open(url)

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")
