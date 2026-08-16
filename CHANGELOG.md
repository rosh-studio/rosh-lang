# Changelog

All notable changes to `rosh-lang` are documented here.

The core grammar (parser/runtime statement surface) is treated as stable
once documented in [LANGUAGE.md](LANGUAGE.md) — see CONTRIBUTING.md's rule
that new keywords require discussion first. Undocumented internals (e.g.
widget-specific properties like `.material`) may change without a version
bump until they're promoted into the public spec.

## 0.9.4 - 2026-08-16

### Changed

- README/LANGUAGE.md/pyproject reworked around the canonical `uv tool install
  rosh-lang` first-run path (terminal → browser), dropping the GitHub install
  command now that this repo is public. Portal docs/site synced to match
  (version strings, target/widget/test counts, MCP install instructions).

## 0.9.3 - 2026-08-12

### Fixed

- `normalise`: a quoted multi-word value passed to `set X.material to "..."`
  or `turn X into '...'` left a stray trailing quote baked into the material
  noun (e.g. `ivory"`). Quotes are now stripped before the material/desc
  split.
- `normalise`: a trailing `# comment` on an otherwise-valid line (e.g.
  `play laser # once`) was never stripped, so the comment text was parsed
  as real arguments instead of being ignored. Inline comments are now
  stripped, respecting quoted strings (so `background "#1a1a2e"` and
  `print "score #1"` are unaffected).
- `after <seconds> send <event>`: payload support was documented
  (`after 0.5 send scored value=5`) but never implemented — the model had
  no payload field and any extra tokens after the event name were silently
  dropped on every target. `AfterStatement` now carries a `payload` dict,
  parsed the same way as `send`, and emitted correctly in compiled JS
  (web/Phaser/Three.js targets).
- `normalise`: the inline-comment stripper above treated any bare apostrophe
  as opening a quoted string, so a possessive or contraction with no actual
  quotes (`say Rosh's world # note`, `say don't stop # note`) made the
  scanner think it was still "inside a string" for the rest of the line —
  the trailing comment was never stripped. A `'` now only opens a quote when
  it's preceded by whitespace or starts the line, which a real quote always
  is and a contraction never is.

### Docs

- LANGUAGE.md's Scenes section documented `create scene ... end` as if it
  scoped the statements inside it to that scene. It doesn't — `create scene`
  only registers the scene, and everything between it and its `end` executes
  immediately and unconditionally like any other top-level code. The section
  now documents the real, tested pattern: register scenes, set properties
  (`room_description`, `exits`), and gate per-scene behavior with a global
  `when scene_enter` handler checked against the `scene` payload value.
- LANGUAGE.md documented `repeat items as item` for iterating a captured
  list. `repeat` only accepts a numeric count (or `as <var>` for a counter);
  it silently no-ops on a list. The working, tested mechanism is
  `for each item in items`, which is now what's documented.
- The corrected `for each` example also fixed a second inaccuracy: captured
  list items from `get all into items` have the shape
  `{key, value, type}`, not `{name, ...}` — `{item.name}` never resolved.
  The example now uses `{item.key}`.
- `send`/`after` payload examples used a bare positional value
  (`send scored 10`) implying it binds to the event's declared payload
  field. It doesn't — only `key=value` tokens are read into the payload; a
  bare value is parsed but silently dropped. Examples now use
  `send scored value=10`.
- The `event`/`when`/`send` example had the `send` before the matching
  `when` block in program order. Handler registration happens as the
  runtime scans forward through top-level statements, so a `send` that
  fires before its `when` is reached has no handler to call — the example
  now declares `when scored` before `send`ing it.
- The Web target section claimed `--target web` "generates a self-contained
  HTML file... share it as a single `.html`". It doesn't — the CLI only
  serves the rendered page from a local HTTP server; nothing is written to
  disk. The section now describes the real behavior and points to
  `rosh_lang.targets.web.render_html()` for anyone who wants the raw string
  to save themselves.
- The Asset Registry section claimed `"ancient carved stone"`, `"carving"`,
  and `"stone"` all fuzzy-match to the `stone` manifest. `"carving"` alone
  actually resolves to the separate `carved_relief` manifest (it's a tag
  there, not on `stone`). Swapped the example for `"pictish stone"`, which
  does resolve to `stone`, and noted the near-miss.

### Release process

- Added a `publish-pypi` job to `.github/workflows/ci.yml`: on a `v*` tag
  push, it downloads the exact wheel/sdist the `release-artifacts` job
  already built and verified (not a fresh rebuild), checks the tag matches
  the wheel's version (refuses to publish on a mismatch), then publishes to
  PyPI via Trusted Publishing (OIDC) — no stored token.
- The private/generated-file leak check now scans the built wheel as well
  as the sdist; previously only the sdist was checked.
- Removed a stale, contradictory `uv.lock` entry from `.gitignore` — the
  lockfile is (correctly) tracked in git, so ignoring it had no effect.

## 0.9.2 and earlier

Not tracked retroactively in this file.
