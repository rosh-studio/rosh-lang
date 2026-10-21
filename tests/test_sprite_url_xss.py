"""Regression test for a stored-XSS vulnerability found live on rosh.cloud
during today's pre-launch security QA (16-Aug-2026, see rosh-dev/BUGS.md).

media/sprites.py's generate_sprite() passes any "http(s)://..." sprite
description straight through, verbatim, as the sprite's data URI (this is
intentional — it's how a program points at a real external image). But
targets/web.py's _render_object() interpolated that string, unescaped,
directly into a style="..." attribute — every other object property
rendered there (color, label, text_color, font_size) goes through
html.escape(), this one branch didn't. A sprite URL containing a `"`
closed the attribute early; a `>` after that closed the whole <div> tag;
anything after that became genuine sibling HTML, e.g. an
`<input autofocus onfocus=...>` that fires with zero user interaction.
Confirmed live: published via a real account, reachable at the
documented, unsandboxed `/p/{user}/{slug}/play?raw=1` embed URL.

Fixed by only trusting a sprite's data_uri into that unescaped url(...) if
_is_safe_style_url() (reusing _sanitize_background's existing character
blocklist) confirms it's a real data: URI or a clean http(s) URL — anything
else falls back to the plain colour-box rendering every object already has
for when there's no sprite at all.
"""

from __future__ import annotations

from rosh_lang.targets.web import _render_object

# The exact exploit shape found live: break out of the style attribute,
# close the div, inject a self-firing element.
MALICIOUS_SPRITE_URL = (
    'https://evil.example.com/x.png" onload="alert(1)">'
    '<input autofocus onfocus=alert(document.domain)>'
)


class TestSpriteURLNotXSSable:
    def test_malicious_sprite_url_does_not_break_out_of_style_attribute(self):
        html = _render_object("thing", {"label": "hi"}, {"thing": MALICIOUS_SPRITE_URL})
        assert "<input" not in html, "attacker HTML must not appear as a live sibling element"
        assert "onfocus=" not in html, "the injected event handler must not survive into the output"
        # The div's own style attribute must still be a single, well-formed
        # attribute — i.e. exactly two double-quotes belong to style="...",
        # not more (which would mean the value broke out and re-opened).
        assert html.count('style="') == 1

    def test_malicious_sprite_url_falls_back_to_plain_colour_box(self):
        html = _render_object("thing", {"label": "hi", "color": "#ff0000"}, {"thing": MALICIOUS_SPRITE_URL})
        assert "background-color: #ff0000" in html, "rejecting the sprite should fall back to the object's colour"
        assert "background-image" not in html

    def test_legitimate_https_image_url_still_works(self):
        clean_url = "https://cdn.example.com/sprites/ship.png"
        html = _render_object("thing", {}, {"thing": clean_url})
        assert f"background-image: url({clean_url})" in html

    def test_legitimate_data_uri_sprite_still_works(self):
        data_uri = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAAB"
        html = _render_object("thing", {}, {"thing": data_uri})
        assert f"background-image: url({data_uri})" in html


class TestSpriteDataJSInjection:
    """Round two of this bug, found by an independent external review the
    same day, after the fix above shipped: _is_safe_style_url() only
    protects _render_object's CSS `background-image: url(...)` sink. It
    does nothing for interactive programmes (any `when`/`on` handler),
    which additionally serialise the *entire, unvalidated* sprite_data
    dict into a JS object literal — `rosh._spriteData = {"name": "<raw
    value>"};` — for the JS runtime's syncAll(). That interpolation had
    *zero* escaping on the value (the adjacent, otherwise-identical
    audio_data injection a few lines below it already used json.dumps
    correctly — this one just didn't). A sprite value containing a
    literal `"` closed the JS string outright, and anything after it ran
    as live JavaScript, not markup — confirmed with a payload that
    produces literal `alert(1)` as executable code in the compiled
    output. Same underlying issue in targets/phaser.py's identical
    pattern. Fixed by switching both to json.dumps for key and value,
    matching the already-correct audio_data code right next to each.
    """

    MALICIOUS_JS_BREAKOUT = 'https://evil.example/x.png","pwn":alert(1),"x":"x'

    def test_web_target_sprite_data_is_json_safe(self):
        from rosh_lang.core.parser import parse_string
        from rosh_lang.targets.web import render_html

        code = (
            'create object thing\n'
            f'sprite thing "{self.MALICIOUS_JS_BREAKOUT}"\n'
            "when click\n"
            "  print \"hi\"\n"
            "end"
        )
        html = render_html(parse_string(code))
        # The unambiguous check: rosh._spriteData's value must be a single
        # well-formed JSON string literal — if the payload broke out, this
        # parse either fails outright or the dict has extra top-level keys
        # ("pwn", "x") instead of one clean "thing" entry.
        import json
        import re

        m = re.search(r"rosh\._spriteData = (\{.*?\});", html)
        assert m, "sprite data block not found in compiled output"
        parsed = json.loads(m.group(1))
        assert parsed["thing"] == self.MALICIOUS_JS_BREAKOUT

    def test_phaser_target_sprite_data_is_json_safe(self):
        from rosh_lang.core.parser import parse_string
        from rosh_lang.targets.phaser import render_phaser

        code = (
            'create object thing\n'
            f'sprite thing "{self.MALICIOUS_JS_BREAKOUT}"\n'
            "when click\n"
            "  print \"hi\"\n"
            "end"
        )
        html = render_phaser(parse_string(code))
        import json
        import re

        m = re.search(r"rosh\._spriteData = (\{.*?\});", html)
        assert m, "sprite data block not found in compiled phaser output"
        parsed = json.loads(m.group(1))
        assert parsed["thing"] == self.MALICIOUS_JS_BREAKOUT


def _parsed_input_elements(html: str) -> list[dict]:
    """Feed html through a real HTML parser (stdlib html.parser, the same
    class of tool a browser's HTML tokenizer is) and return every <input>
    element it finds. Used to prove no attacker-controlled element
    survives — not just that the embedded JS object round-trips as valid
    JSON, which proves nothing about how the *browser* parses the
    surrounding HTML document."""
    from html.parser import HTMLParser

    class _InputFinder(HTMLParser):
        def __init__(self):
            super().__init__()
            self.inputs: list[dict] = []

        def handle_starttag(self, tag, attrs):
            if tag == "input":
                self.inputs.append(dict(attrs))

    parser = _InputFinder()
    parser.feed(html)
    return parser.inputs


class TestSpriteDataScriptTagBreakout:
    """Round three of this bug, found by a second independent external
    review, after round two's json.dumps() fix shipped: json.dumps()
    correctly escapes what's needed for valid JS-*string* syntax, but
    that is not the same thing as "safe to embed inside an HTML
    <script>...</script> block". The HTML parser runs before the JS
    parser and has no concept of JS string literals — a literal
    "</script>" anywhere in the JSON text, even one that's a perfectly
    well-formed, harmless JS string as far as the JS engine is concerned,
    closes the enclosing <script> tag right there, and everything after
    it becomes real, parsed HTML. round two's own tests (above) only
    proved the embedded object round-trips through json.loads() — that
    catches JS-string breakout, but is blind to this class of bug by
    construction, since it never considers the HTML document the JSON is
    sitting inside.

    Fixed with _json_for_inline_script() (web.py), which additionally
    escapes every literal "<" — closing the door on "</script>",
    "<script", "<style", or any other tag-opening/closing sequence, not
    just the one payload shape demonstrated. These tests parse the FULL
    compiled document with a real HTML parser (matching how the review
    verified the bug) and assert no attacker-controlled element appears —
    not just that the JS payload happens to parse as valid JSON.
    """

    SCRIPT_BREAKOUT_URL = 'https://evil.example/x.png</script><input autofocus onfocus=alert(1)>'

    def _program(self) -> str:
        return (
            'create object thing\n'
            f'sprite thing "{self.SCRIPT_BREAKOUT_URL}"\n'
            "when click\n"
            "  print \"hi\"\n"
            "end"
        )

    def test_web_target_no_attacker_element_parses_out(self):
        from rosh_lang.core.parser import parse_string
        from rosh_lang.targets.web import render_html

        html = render_html(parse_string(self._program()))
        inputs = _parsed_input_elements(html)
        assert not inputs, f"attacker-controlled <input> element parsed as real HTML: {inputs}"

    def test_phaser_target_no_attacker_element_parses_out(self):
        from rosh_lang.core.parser import parse_string
        from rosh_lang.targets.phaser import render_phaser

        html = render_phaser(parse_string(self._program()))
        inputs = _parsed_input_elements(html)
        assert not inputs, f"attacker-controlled <input> element parsed as real HTML: {inputs}"


class TestThreejsAssetDefaultsScriptTagBreakout:
    """A FOURTH round, found by a spawned adversarial self-review of round
    three's fix (before anything was deployed) — same underlying bug
    class, different attacker-controlled field and a different file the
    round-three sweep never touched: `_js_codegen.py`'s
    `_threejs_asset_defaults()` builds `request_json =
    json.dumps(request, ...)` (this file's own request dict, containing
    `request["object"] = name` verbatim) with a raw, UNESCAPED
    json.dumps() call — not even this file's own, narrower `_escape_js`
    "</" -> "<\\/" protection, which is applied to every OTHER string in
    the same function. `create object <name>` accepts any non-whitespace
    characters for the name, including "<", "/", etc. — an object named
    `x</script><img src=x onerror=alert(1)>` (no registry match, so it
    hits this exact code path) survives into
    `rosh.addToList("_assetRequests", {request_json});` and a real HTML
    parser confirms a live <img onerror=...> element parses out — same
    fix as round three: _json_for_inline_script(), duplicated locally in
    _js_codegen.py matching this file's existing per-file-helper
    convention (_escape_js is likewise file-local, not imported)."""

    def test_threejs_no_attacker_element_parses_out_via_object_name(self):
        from rosh_lang.core.parser import parse_string
        from rosh_lang.targets.threejs import render_threejs

        # No registry match for this name (deliberately nonsensical), so
        # this reaches _threejs_asset_defaults's no-match / vulnerable branch.
        code = 'create object x</script><img src=x onerror=alert(1)>'
        html = render_threejs(parse_string(code))
        imgs = _parsed_img_elements(html)
        assert not imgs, f"attacker-controlled <img> element parsed as real HTML: {imgs}"


def _parsed_img_elements(html: str) -> list[dict]:
    from html.parser import HTMLParser

    class _ImgFinder(HTMLParser):
        def __init__(self):
            super().__init__()
            self.imgs: list[dict] = []

        def handle_starttag(self, tag, attrs):
            if tag == "img":
                self.imgs.append(dict(attrs))

    parser = _ImgFinder()
    parser.feed(html)
    return parser.imgs
