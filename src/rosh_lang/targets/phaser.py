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

from rosh_lang.core.model import PrintStatement, Programme, SayStatement
from rosh_lang.core.runtime import Runtime
from rosh_lang.media.sounds import generate_sound_params
from rosh_lang.targets._js_codegen import compile_programme
from rosh_lang.targets._js_runtime import JS_RUNTIME_CORE, JS_TOUCH_CONTROLS
from rosh_lang.targets._js_runtime_phaser import JS_RUNTIME_PHASER
from rosh_lang.targets.web import (
    _collect_objects,
    _generate_animation_data,
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

    # Inject sprite data URIs. See web.py's identical fix for why this must
    # be json.dumps, not raw string interpolation — sprite() lets an
    # attacker-influenced http(s):// URL through verbatim as this value.
    if sprite_data:
        pairs = ", ".join(
            f"{json.dumps(k)}: {json.dumps(v)}" for k, v in sprite_data.items()
        )
        script_parts.append(f"rosh._spriteData = {{{pairs}}};")

    # Inject audio data
    if audio_data:
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
        anim_init_lines: list[str] = []
        for anim_name, anim_info in anim_data.items():
            frames_json = json.dumps(anim_info["frames"], separators=(",", ":"))
            anim_init_lines.append(
                f'rosh._animData["{anim_name}"] = '
                f'{{"frames": {frames_json}, '
                f'"speed": {anim_info["speed"]}, '
                f'"mode": "{anim_info["mode"]}", '
                f'"_frame": 0, "_elapsed": 0, "_dir": 1}};'
            )
            # Set initial sprite to frame 0
            anim_init_lines.append(
                f'rosh._spriteData["{anim_name}"] = {json.dumps(anim_info["frames"][0])};'
            )
        script_parts.extend(anim_init_lines)

    if compiled.has_handlers:
        script_parts.extend(["", "// ── Handlers ──", compiled.handler_code])

    # Phaser renderer layer (always included — it creates the game)
    script_parts.extend(["", "// ── Phaser renderer ──", JS_RUNTIME_PHASER])
    script_parts.append(JS_TOUCH_CONTROLS)

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
        # flush=True: see web.py's serve_web for why this matters — stdout
        # is fully buffered when not a TTY, and serve_forever() never
        # returns to flush it otherwise.
        print(f"Serving Phaser game at {url} — Ctrl-C to stop", flush=True)

        if auto_open:
            webbrowser.open(url)

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")
