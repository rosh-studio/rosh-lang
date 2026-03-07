#!/usr/bin/env python3
"""Build the Rosh showcase page — one HTML file with embedded interactive demos.

Reads .rosh files from examples/showcase/, compiles each to HTML via
render_html(), and assembles a single showcase page with <iframe srcdoc>
embedding. Each demo has a live preview alongside its source code.

Usage:
    cd rosh-lang
    python tools/build_showcase.py
    open dist/showcase.html
"""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path

# Ensure rosh-lang/src is importable
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from rosh_lang.parser import parse_string  # noqa: E402
from rosh_lang.targets.web import render_html  # noqa: E402
from rosh_lang.targets.threejs import render_threejs  # noqa: E402
from rosh_lang.widgets import get_bundled_library_path  # noqa: E402

SHOWCASE_DIR = ROOT / "examples" / "showcase"
DIST_DIR = ROOT / "dist"
OUTPUT = DIST_DIR / "showcase.html"

# Metadata regex — # demo:, # description:, # badges:
_META_RE = re.compile(r"^#\s*(demo|description|badges|target):\s*(.+)$")

# Rosh keywords for syntax highlighting
_KEYWORDS = frozenset({
    "print", "create", "set", "when", "end", "use", "on",
    "event", "send", "destroy", "get", "say", "go", "look",
    "connect", "sprite", "sound", "play", "if", "else", "animate",
    "define", "do", "after", "background",
})


# ── Metadata ──────────────────────────────────────────────────


def _parse_demo_metadata(text: str) -> dict[str, str]:
    """Extract # demo:, # description:, # badges: from source header."""
    meta: dict[str, str] = {"demo": "", "description": "", "badges": "", "target": ""}
    for line in text.splitlines():
        stripped = line.strip()
        m = _META_RE.match(stripped)
        if m:
            meta[m.group(1)] = m.group(2).strip()
        elif stripped and not stripped.startswith("#"):
            break
    return meta


# ── Source highlighting ───────────────────────────────────────


def _highlight_source(text: str) -> str:
    """Simple syntax highlighting for Rosh source — returns HTML."""
    lines: list[str] = []
    for raw_line in text.splitlines():
        stripped = raw_line.strip()

        # Comments
        if stripped.startswith("#"):
            lines.append(f'<span class="cmt">{html.escape(raw_line)}</span>')
            continue

        # Blank lines
        if not stripped:
            lines.append("")
            continue

        # Split into leading whitespace + content
        indent = html.escape(raw_line[: len(raw_line) - len(raw_line.lstrip())])
        tokens = stripped.split(None, 1)
        first_word = tokens[0]
        rest = tokens[1] if len(tokens) > 1 else ""

        parts: list[str] = [indent]

        # Keyword highlight
        if first_word.lower() in _KEYWORDS:
            parts.append(f'<span class="kw">{html.escape(first_word)}</span>')
        else:
            parts.append(html.escape(first_word))

        # Rest of line — highlight strings
        if rest:
            parts.append(" ")
            rest_esc = html.escape(rest)
            rest_esc = re.sub(
                r"(&quot;.*?&quot;)",
                r'<span class="str">\1</span>',
                rest_esc,
            )
            parts.append(rest_esc)

        lines.append("".join(parts))

    return "\n".join(lines)


# ── Demo card ─────────────────────────────────────────────────


def _build_demo_card(
    source: str,
    meta: dict[str, str],
    rendered_html: str,
    index: int,
) -> str:
    """Build one demo card as HTML."""
    title = meta.get("demo") or f"Demo {index}"
    description = meta.get("description", "")
    badges_raw = meta.get("badges", "")
    badges = [b.strip() for b in badges_raw.split(",") if b.strip()]

    needs_interaction = any(
        b.lower() in ("click", "keyboard", "game loop", "events")
        for b in badges
    )
    needs_keyboard = any(b.lower() in ("keyboard", "game loop") for b in badges)

    badge_html = " ".join(
        f'<span class="badge">{html.escape(b)}</span>' for b in badges
    )

    # Escape rendered HTML for srcdoc attribute
    srcdoc = html.escape(rendered_html, quote=True)

    # Highlighted source
    highlighted = _highlight_source(source)

    # Click-to-interact overlay
    overlay = ""
    if needs_interaction:
        label = "Click here, then press keys" if needs_keyboard else "Click to interact"
        overlay = (
            '<div class="overlay" onclick="'
            "this.style.display='none';"
            "this.parentElement.querySelector('iframe').focus();"
            f'">{html.escape(label)}</div>'
        )

    # Three.js demos need allow-same-origin to load CDN scripts
    target = meta.get("target", "").strip()
    sandbox = "allow-scripts allow-same-origin" if target == "threejs" else "allow-scripts"

    return f"""\
    <div class="demo-card">
      <div class="demo-header">
        <h2>{html.escape(title)}</h2>
        <div class="badges">{badge_html}</div>
      </div>
      <div class="demo-body">
        <div class="demo-preview">
          {overlay}
          <iframe srcdoc="{srcdoc}" sandbox="{sandbox}" loading="lazy"></iframe>
        </div>
        <div class="demo-source">
          <pre><code>{highlighted}</code></pre>
        </div>
      </div>
      <p class="demo-description">{html.escape(description)}</p>
    </div>"""


# ── Page assembly ─────────────────────────────────────────────

_PAGE_CSS = """\
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      background: #1a1a2e;
      color: #e0e0e0;
      font-family: system-ui, -apple-system, sans-serif;
      line-height: 1.6;
    }
    header {
      text-align: center;
      padding: 48px 24px 32px;
    }
    header h1 {
      font-size: 2.2rem;
      font-weight: 700;
      color: #fff;
      margin-bottom: 8px;
    }
    header .tagline {
      color: #888;
      font-size: 1.1rem;
    }
    .demos {
      max-width: 1200px;
      margin: 0 auto;
      padding: 0 24px 48px;
    }
    .demo-card {
      background: #16213e;
      border-radius: 12px;
      margin-bottom: 32px;
      overflow: hidden;
      border: 1px solid #1a1a3e;
    }
    .demo-header {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 16px 24px;
      border-bottom: 1px solid #1a1a2e;
    }
    .demo-header h2 {
      font-size: 1.2rem;
      font-weight: 600;
      color: #fff;
    }
    .badges {
      display: flex;
      gap: 6px;
    }
    .badge {
      background: #533483;
      color: #e0e0e0;
      padding: 2px 10px;
      border-radius: 12px;
      font-size: 0.75rem;
      font-weight: 500;
    }
    .demo-body {
      display: flex;
    }
    .demo-preview {
      flex: 0 0 60%;
      position: relative;
      background: #0f1a2e;
    }
    .demo-preview iframe {
      width: 100%;
      aspect-ratio: 4 / 3;
      border: none;
      display: block;
    }
    .overlay {
      position: absolute;
      inset: 0;
      background: rgba(0, 0, 0, 0.5);
      display: flex;
      align-items: center;
      justify-content: center;
      color: #fff;
      font-size: 1.1rem;
      cursor: pointer;
      z-index: 1;
      transition: opacity 0.2s;
    }
    .overlay:hover {
      background: rgba(0, 0, 0, 0.35);
    }
    .demo-source {
      flex: 0 0 40%;
      overflow: auto;
      background: #0d1117;
      max-height: 400px;
    }
    .demo-source pre {
      padding: 16px 20px;
      font-family: "SF Mono", "Fira Code", "Cascadia Code", monospace;
      font-size: 13px;
      line-height: 1.5;
      color: #c9d1d9;
      white-space: pre;
    }
    .demo-source .kw {
      color: #ff7b72;
      font-weight: 600;
    }
    .demo-source .str {
      color: #a5d6ff;
    }
    .demo-source .cmt {
      color: #8b949e;
      font-style: italic;
    }
    .demo-description {
      padding: 12px 24px 16px;
      color: #888;
      font-size: 0.9rem;
    }
    footer {
      text-align: center;
      padding: 24px;
      color: #555;
      font-size: 0.85rem;
      border-top: 1px solid #1a1a3e;
    }
    footer a {
      color: #777;
      text-decoration: none;
    }"""


def _build_page(cards_html: str) -> str:
    """Assemble the full showcase HTML page."""
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Rosh Language Showcase</title>
  <style>
{_PAGE_CSS}
  </style>
</head>
<body>
  <header>
    <h1>Rosh Language Showcase</h1>
    <p class="tagline">One script, many worlds &mdash; plain English that runs everywhere</p>
  </header>
  <div class="demos">
{cards_html}
  </div>
  <footer>&copy; Rosh Studio 2026 &mdash; rosh.cloud</footer>
</body>
</html>"""


# ── Main ──────────────────────────────────────────────────────


def main() -> None:
    print(f"Building showcase from {SHOWCASE_DIR}")

    demos = sorted(SHOWCASE_DIR.glob("*.rosh"))
    if not demos:
        print(f"  No .rosh files found in {SHOWCASE_DIR}")
        sys.exit(1)

    search_paths = [SHOWCASE_DIR, get_bundled_library_path()]

    cards: list[str] = []
    for i, path in enumerate(demos, 1):
        source = path.read_text(encoding="utf-8")
        meta = _parse_demo_metadata(source)
        name = meta.get("demo") or path.stem

        print(f"  [{i}/{len(demos)}] {name}...", end=" ", flush=True)

        programme = parse_string(source, source=str(path))
        target = meta.get("target", "").strip()
        if target == "threejs":
            rendered = render_threejs(programme, search_paths=search_paths)
        else:
            rendered = render_html(programme, search_paths=search_paths)
        card = _build_demo_card(source, meta, rendered, i)
        cards.append(card)

        print("OK")

    DIST_DIR.mkdir(parents=True, exist_ok=True)
    page = _build_page("\n".join(cards))
    OUTPUT.write_text(page, encoding="utf-8")

    print(f"\nWrote {OUTPUT} ({len(page):,} bytes)")
    print(f"Open: file://{OUTPUT}")


if __name__ == "__main__":
    main()
