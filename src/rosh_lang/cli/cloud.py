# licence: Rosh-BSL
"""rosh cloud — create with AI and publish to rosh.cloud.

Commands:
    rosh create "space invaders"          → AI generates a .rosh file
    rosh publish game.rosh                → upload to rosh.cloud
    rosh publish game.rosh --target phaser
    rosh config --key rosh_k1_...         → save API key
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

CONFIG_DIR = Path.home() / ".rosh"
CONFIG_FILE = CONFIG_DIR / "config.json"
CLOUD_BASE = "https://rosh.cloud"
_TRANSIENT_HTTP_ERRORS = {502, 503, 504, 522, 524}
_GET_ATTEMPTS = 3


def _load_config() -> dict:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}


def _save_config(config: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_DIR.chmod(0o700)
    CONFIG_FILE.touch(mode=0o600, exist_ok=True)
    CONFIG_FILE.chmod(0o600)
    CONFIG_FILE.write_text(json.dumps(config, indent=2))


def _get_api_key() -> str:
    """Get API key from config or environment."""
    key = os.environ.get("ROSH_API_KEY", "") or _load_config().get("api_key", "")
    if not key:
        print("No API key configured. Run: rosh config --key rosh_k1_...")
        print("Or set ROSH_API_KEY environment variable.")
        sys.exit(1)
    return key


def _api_request(method: str, path: str, data: dict | None = None, api_key: str = "") -> dict:
    """Make an API request to rosh.cloud."""
    url = f"{CLOUD_BASE}{path}"
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "rosh-cli/0.8.0",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    body = json.dumps(data).encode() if data else None
    req = Request(url, data=body, headers=headers, method=method)

    attempts = _GET_ATTEMPTS if method == "GET" else 1
    for attempt in range(1, attempts + 1):
        try:
            with urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except HTTPError as e:
            if e.code in _TRANSIENT_HTTP_ERRORS and attempt < attempts:
                print(f"Temporary error {e.code}; retrying ({attempt}/{attempts - 1})...")
                time.sleep(attempt)
                continue
            detail = _http_error_detail(e)
            if e.code in _TRANSIENT_HTTP_ERRORS:
                noun = "attempt" if attempts == 1 else "attempts"
                detail = f"rosh.cloud temporarily unavailable after {attempts} {noun}"
            print(f"Error {e.code}: {detail}")
            sys.exit(1)
        except URLError as e:
            if attempt < attempts:
                print(f"Connection error; retrying ({attempt}/{attempts - 1})...")
                time.sleep(attempt)
                continue
            print(f"Connection error after {attempts} attempts: {e.reason}")
            sys.exit(1)

    raise AssertionError("unreachable")


def _http_error_detail(error: HTTPError) -> str:
    """Return a useful message for JSON and non-JSON HTTP errors."""
    try:
        detail = json.loads(error.read().decode())
    except Exception:
        return str(error.reason or "unknown error")
    if isinstance(detail, dict):
        return str(detail.get("detail") or detail.get("message") or error.reason or detail)
    return str(detail)


def _fetch_docs(api_key: str) -> dict:
    """Fetch the structured language reference from rosh.cloud."""
    return _api_request("GET", "/api/v1/docs", api_key=api_key)


def _build_create_prompt(description: str, docs: dict) -> str:
    """Build a prompt for AI code generation using the API docs."""
    # Pick a palette
    palettes = docs.get("colour_palettes", {})
    palette_info = ""
    for name, p in palettes.items():
        palette_info += f"  {name}: {', '.join(p['colors'])}\n"

    keywords_info = ""
    for kw in docs.get("keywords", []):
        keywords_info += f"  {kw['name']}: {kw['syntax']} — {kw['description']}\n"

    widgets_info = ""
    for w in docs.get("widgets", []):
        widgets_info += f"  use {w['name']} {w['config']} — {w['description']}\n"

    patterns_info = ""
    for name, code in docs.get("patterns", {}).items():
        patterns_info += f"--- {name} ---\n{code}\n\n"

    sprites = ", ".join(docs.get("sprite_descriptions", []))
    tips = "\n".join(f"- {t}" for t in docs.get("tips", []))

    return f"""You are a Rosh programmer. Write a complete .rosh program based on this description:

"{description}"

## Rosh Language Reference (v{docs.get('version', '?')})

### Keywords
{keywords_info}

### Widgets (compose with 'use')
{widgets_info}

### Code Patterns
{patterns_info}

### Good Sprite Descriptions
{sprites}

### Colour Palettes (pick one and use consistently)
{palette_info}

### Tips
{tips}

## Rules
1. Output ONLY valid .rosh code. No markdown, no explanation, no backticks.
2. Start with a comment: # <title>
3. Second line: # <one-line description>
4. Use widgets for HUD elements (score, lives, timer).
5. Use sprites for visual objects: sprite ship "blue spaceship"
6. Use sounds for audio feedback: sound laser "laser shoot"
7. Pick ONE colour palette and use its colours throughout.
8. Set _max_output to 3 for games.
9. Keep it under 80 lines.
10. Make it interactive and fun — clicks, keys, collisions.
"""


def cmd_register(args: list[str]) -> None:
    """Handle: rosh register — open registration page in browser."""
    import webbrowser
    url = f"{CLOUD_BASE}/register"
    print(f"Opening {url} ...")
    webbrowser.open(url)


def cmd_login(args: list[str]) -> None:
    """Handle: rosh login — open login page in browser."""
    import webbrowser
    url = f"{CLOUD_BASE}/login"
    print(f"Opening {url} ...")
    webbrowser.open(url)
    print("Once logged in, create an API key at Settings > API Keys,")
    print("then run: rosh config --key rosh_k1_...")


def cmd_logout(args: list[str]) -> None:
    """Handle: rosh logout — clear local API key."""
    config = _load_config()
    if config.get("api_key"):
        del config["api_key"]
        _save_config(config)
        print("Logged out. API key removed.")
    else:
        print("Not logged in (no API key configured).")


def _call_ai(prompt: str) -> str:
    """Call an AI engine to generate code. Tries engines in order:
    1. Generic OpenAI-compatible (ROSH_AI_BASE_URL + ROSH_AI_API_KEY)
    2. Anthropic (ANTHROPIC_API_KEY)
    3. OpenAI (OPENAI_API_KEY)
    """
    # Option 1: Generic OpenAI-compatible endpoint
    base_url = os.environ.get("ROSH_AI_BASE_URL", "")
    ai_key = os.environ.get("ROSH_AI_API_KEY", "")
    model = os.environ.get("ROSH_AI_MODEL", "")
    if base_url and ai_key:
        return _call_openai_compat(prompt, base_url, ai_key, model or "default")

    # Option 2: Anthropic
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            import anthropic
        except ImportError:
            print("AI generation requires the 'ai' extra:")
            print("  uv tool install 'rosh-lang[ai]'")
            sys.exit(1)
        client = anthropic.Anthropic()
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text.strip()  # type: ignore[union-attr]

    # Option 3: OpenAI
    if os.environ.get("OPENAI_API_KEY"):
        return _call_openai_compat(
            prompt, "https://api.openai.com/v1",
            os.environ["OPENAI_API_KEY"], "gpt-4o-mini"
        )

    print("No AI engine configured. Set one of:")
    print("  ANTHROPIC_API_KEY    — Anthropic (Claude)")
    print("  OPENAI_API_KEY       — OpenAI (GPT)")
    print("  ROSH_AI_BASE_URL + ROSH_AI_API_KEY — any OpenAI-compatible API")
    sys.exit(1)


def _call_openai_compat(prompt: str, base_url: str, api_key: str, model: str) -> str:
    """Call any OpenAI-compatible chat completions endpoint."""
    import json as _json
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError

    url = f"{base_url.rstrip('/')}/chat/completions"
    body = _json.dumps({
        "model": model,
        "max_tokens": 2048,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()

    req = Request(url, data=body, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    })

    try:
        with urlopen(req, timeout=60) as resp:
            data = _json.loads(resp.read().decode())
            return data["choices"][0]["message"]["content"].strip()
    except HTTPError as e:
        detail = e.read().decode()[:200]
        print(f"AI engine error {e.code}: {detail}")
        sys.exit(1)


def cmd_config(args: list[str]) -> None:
    """Handle: rosh config --key <key>"""
    if len(args) >= 2 and args[0] == "--key":
        key = args[1]
        if not key.startswith("rosh_k1_"):
            print("API key should start with rosh_k1_")
            sys.exit(1)
        config = _load_config()
        config["api_key"] = key
        _save_config(config)
        print(f"API key saved to {CONFIG_FILE}")
        return

    # Show current config
    config = _load_config()
    if config.get("api_key"):
        prefix = config["api_key"][:16]
        print(f"API key: {prefix}...")
    else:
        print("No API key configured.")
    print(f"Config: {CONFIG_FILE}")


def cmd_create(args: list[str]) -> None:
    """Handle: rosh create "description" [--target web|phaser|threejs]"""
    if not args:
        print("Usage: rosh create \"space invaders\" [--target phaser] [--save game.rosh]")
        sys.exit(1)

    # Parse args
    description = ""
    target = "web"
    save_path = None
    publish = False
    i = 0
    while i < len(args):
        if args[i] == "--target" and i + 1 < len(args):
            target = args[i + 1]
            i += 2
        elif args[i] == "--save" and i + 1 < len(args):
            save_path = args[i + 1]
            i += 2
        elif args[i] == "--publish":
            publish = True
            i += 1
        else:
            description += (" " + args[i]) if description else args[i]
            i += 1

    if not description:
        print("Please provide a description: rosh create \"space invaders\"")
        sys.exit(1)

    api_key = _get_api_key()

    # Fetch language docs
    print(f"Fetching language reference...")
    docs = _fetch_docs(api_key)

    # Build prompt and call AI engine
    print(f"Generating: {description} ({target} target)...")
    prompt = _build_create_prompt(description, docs)
    code = _call_ai(prompt)

    # Remove markdown fences if present
    if code.startswith("```"):
        lines = code.split("\n")
        code = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    print(f"\n--- Generated ({len(code.splitlines())} lines) ---")
    print(code)
    print("---\n")

    # Save locally
    if save_path:
        Path(save_path).write_text(code)
        print(f"Saved to {save_path}")

    # Compile to verify
    print("Compiling...")
    result = _api_request("POST", "/api/compile", {"code": code, "target": target})
    if result.get("success"):
        print("Compilation successful!")
    else:
        print(f"Compilation failed: {result.get('error', 'unknown error')}")
        return

    # Publish if requested
    if publish:
        # Extract title from first comment
        title = description[:50]
        for line in code.splitlines():
            if line.startswith("# ") and not line.startswith("# description"):
                title = line[2:].strip()
                break

        print(f"Publishing: {title}...")
        result = _api_request("POST", "/api/v1/programs", {
            "title": title,
            "code": code,
            "target": target,
            "description": description,
        }, api_key=api_key)

        if result.get("success"):
            owner = result.get("owner", "?")
            slug = result.get("slug", "?")
            print(f"Published! https://rosh.cloud/p/{owner}/{slug}")
        else:
            print(f"Publish failed: {result}")
    elif not save_path:
        # Auto-save if nothing else specified
        slug = description.lower().replace(" ", "-")[:30]
        slug = "".join(c for c in slug if c.isalnum() or c == "-")
        filename = f"{slug}.rosh"
        Path(filename).write_text(code)
        print(f"Saved to {filename}")
        print(f"Run: rosh {filename} --target {target} --run")
        print(f"Publish: rosh publish {filename} --target {target}")


def cmd_publish(args: list[str]) -> None:
    """Handle: rosh publish file.rosh [--target web] [--title "My Game"]"""
    if not args:
        print("Usage: rosh publish game.rosh [--target phaser] [--title \"My Game\"]")
        sys.exit(1)

    # Parse args
    filepath = None
    target = "web"
    title = None
    description = ""
    i = 0
    while i < len(args):
        if args[i] == "--target" and i + 1 < len(args):
            target = args[i + 1]
            i += 2
        elif args[i] == "--title" and i + 1 < len(args):
            title = args[i + 1]
            i += 2
        elif args[i] == "--description" and i + 1 < len(args):
            description = args[i + 1]
            i += 2
        else:
            filepath = args[i]
            i += 1

    if not filepath:
        print("Please provide a file: rosh publish game.rosh")
        sys.exit(1)

    path = Path(filepath)
    if not path.exists():
        print(f"File not found: {filepath}")
        sys.exit(1)

    code = path.read_text()

    # Extract title from comments if not provided
    if not title:
        title = path.stem.replace("-", " ").replace("_", " ").title()
        for line in code.splitlines()[:3]:
            if line.startswith("# ") and "description" not in line.lower():
                title = line[2:].strip()
                break

    api_key = _get_api_key()

    # Compile first
    print(f"Compiling {path.name} ({target})...")
    result = _api_request("POST", "/api/compile", {"code": code, "target": target})
    if not result.get("success"):
        print(f"Compilation failed: {result.get('error', 'unknown')}")
        sys.exit(1)
    print("Compilation successful!")

    # Publish
    print(f"Publishing: {title}...")
    result = _api_request("POST", "/api/v1/programs", {
        "title": title,
        "code": code,
        "target": target,
        "description": description,
    }, api_key=api_key)

    if result.get("success"):
        owner = result.get("owner", "?")
        slug = result.get("slug", "?")
        print(f"Published! https://rosh.cloud/p/{owner}/{slug}")
    else:
        print(f"Publish failed: {result}")
        sys.exit(1)
