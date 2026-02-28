"""Phaser target — render a Rosh programme as a Phaser game in HTML.

Two entry points:
- render_phaser(programme) → str   (testable, no I/O)
- serve_phaser(programme, auto_open) (starts HTTP server)

Uses JS_RUNTIME_CORE (shared) + JS_RUNTIME_PHASER (Phaser renderer).
Reuses helper functions from web.py (_collect_objects, _generate_sprite_data,
_generate_audio_data, _is_interactive).
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

from rosh_lang.model import Programme
from rosh_lang.runtime import Runtime
from rosh_lang.sounds import generate_sound_params
from rosh_lang.targets._js_codegen import compile_programme
from rosh_lang.targets._js_runtime import JS_RUNTIME_CORE
from rosh_lang.targets._js_runtime_phaser import JS_RUNTIME_PHASER
from rosh_lang.targets.web import (
    _collect_objects,
    _generate_audio_data,
    _generate_sprite_data,
)

PHASER_CDN = "https://cdn.jsdelivr.net/npm/phaser@3.70.0/dist/phaser.min.js"
COPYRIGHT = "(c) Rosh Studio 2026 — rosh.cloud"


# ── HTML generation ───────────────────────────────────────────


def render_phaser(
    programme: Programme,
    search_paths: list[Path] | None = None,
) -> str:
    """Render a programme as a Phaser game in HTML."""
    # Run Python runtime for initial state
    buf = io.StringIO()
    rt = Runtime(output=buf, search_paths=search_paths)
    rt.run(programme)

    text_output = buf.getvalue()

    # Collect renderable objects and their assets
    objects = _collect_objects(rt.state)
    sprite_data = _generate_sprite_data(objects)

    # Collect audio data
    audio_data = _generate_audio_data(programme)
    for name, desc in rt.audio_registry.items():
        if name not in audio_data:
            audio_data[name] = generate_sound_params(name, desc)

    # Compile to JS
    compiled = compile_programme(programme, search_paths=search_paths)

    # Build script block
    script_parts = [JS_RUNTIME_CORE, "", "// ── Init ──", compiled.init_code]

    # Inject sprite data URIs
    if sprite_data:
        pairs = ", ".join(
            f'"{escape(k)}": "{v}"' for k, v in sprite_data.items()
        )
        script_parts.append(f"rosh._spriteData = {{{pairs}}};")

    # Inject audio data
    if audio_data:
        audio_pairs = ", ".join(
            f'"{escape(k)}": {json.dumps(v, separators=(",", ":"))}'
            for k, v in audio_data.items()
        )
        script_parts.append(f"rosh._audioData = {{{audio_pairs}}};")

    if compiled.has_handlers:
        script_parts.extend(["", "// ── Handlers ──", compiled.handler_code])

    # Phaser renderer layer (always included — it creates the game)
    script_parts.extend(["", "// ── Phaser renderer ──", JS_RUNTIME_PHASER])

    # Print output injected after Phaser init via appendOutput
    if text_output.strip():
        lines = text_output.rstrip("\n").split("\n")
        for line in lines:
            script_parts.append(
                f'rosh.appendOutput("{_escape_js(line)}");'
            )

    script_block = "\n".join(script_parts)

    return _phaser_html_page(script_block)


def _phaser_html_page(script: str) -> str:
    """Build the full Phaser HTML page shell."""
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
    #game-container {{
      margin-top: 16px;
    }}
    #game-container canvas {{
      display: block;
      border-radius: 4px;
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
  <div id="game-container"></div>
  <footer>{escape(COPYRIGHT)}</footer>
  <script src="{PHASER_CDN}"></script>
  <script>
if (typeof Phaser === "undefined") {{
  document.body.innerHTML = '<p style="color:red;padding:20px">Error: Phaser failed to load from CDN</p>';
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


def _escape_js(s: str) -> str:
    """Escape a string for embedding in a JS string literal."""
    return (
        s.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("'", "\\'")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )


# ── HTTP server ───────────────────────────────────────────────


def serve_phaser(
    programme: Programme,
    *,
    auto_open: bool = False,
    search_paths: list[Path] | None = None,
) -> None:
    """Start an HTTP server that serves the Phaser-rendered programme."""
    html = render_phaser(programme, search_paths=search_paths)
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
        print(f"Serving Phaser game at {url} — Ctrl-C to stop")

        if auto_open:
            webbrowser.open(url)

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")
