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
