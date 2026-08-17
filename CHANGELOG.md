# Changelog

All notable changes to `rosh-lang` are documented here.

The core grammar (parser/runtime statement surface) is treated as stable
once documented in [LANGUAGE.md](LANGUAGE.md) — see CONTRIBUTING.md's rule
that new keywords require discussion first. Undocumented internals (e.g.
widget-specific properties like `.material`) may change without a version
bump until they're promoted into the public spec.

## 0.9.11 - 2026-08-17

### Security

- **Closed two bypasses in the generated-JavaScript execution budget.**
  A `send` issued during top-level initialisation reset the counter on
  every call, and `for each` iterations did not charge the counter at
  all. Either path could still multiply nested 10,000-iteration loops
  into 100 million synchronous operations on page load. Initialisation
  and handler registration now run in one explicit budget scope, nested
  sends inherit their caller's scope, and every `for each` item charges
  the same 200,000-step total budget.

### Fixed

- Replaced process-specific `id(stmt)` loop identifiers with deterministic,
  block-scoped `let` variables. Nested repeats — including repeats that reuse
  the same loop-variable name — now restore their original state correctly,
  including when the execution budget aborts a loop.

## 0.9.10 - 2026-08-17

### Security

This release closes every remaining gap from the `</script>`-breakout and
code-injection bug class first found in 0.9.6/0.9.9 below, plus two new
findings from a subsequent external review. **Anyone who installed
`rosh-lang` between 0.9.9 and this release should upgrade immediately** —
0.9.9 only contains the first two rounds of this fix (the CSS-attribute
and JS-string-escaping sinks); everything below was fixed in source and
on the live rosh.cloud portal (which vendors its own copy of this
package) well before this release, but never previously published here.

- **`</script>`-breakout XSS, two more sinks.** 0.9.9's `json.dumps()`
  fix correctly escapes what's needed for valid JS-*string* syntax, but
  that's not the same as "safe to embed inside an HTML
  `<script>...</script>` block" — the HTML parser runs before the JS
  parser and has no concept of JS string literals, so a literal
  `</script>` anywhere in the JSON text closes the enclosing tag
  regardless of how well-formed the JS string around it is. Fixed with a
  new `_json_for_inline_script()` helper (escapes every literal `<` to
  its Unicode escape) across two sinks: the sprite/audio data injected
  into `web`/`phaser` targets, and a separate, previously-unfixed
  `_threejs_asset_defaults()` sink in `threejs` reachable via an
  object's own name.
- **Raw JS code injection via `define`/`do` function names.**
  `_safe_fn_name()` only replaced `-` and `.` before splicing a
  `define <name>`/`do <name>` name directly into generated JS *source
  code* — not a string context, so none of the above escaping applied.
  A name like `x(){};(function(){...})();function y` closed the
  function declaration early and ran arbitrary code immediately on
  script load, no `do` call needed. Fixed by whitelisting the sanitised
  identifier to `[A-Za-z0-9_]` only.
- **The identical code-injection shape in `repeat N as <var>`'s
  save-slot variable**, found by a follow-up review of the fix above —
  same incomplete `-`/`.`-only sanitisation, same fix.
- **Nested-loop DoS: no execution budget on generated JavaScript.** Each
  `repeat` was independently capped at 10,000 iterations, but nesting
  multiplies rather than adds — `repeat 10000 as i / repeat 10000 as j
  / ...` is 100,000,000 loop iterations, not 20,000. Generated `web`
  pages auto-dispatch a `start` event, so simply opening a malicious
  published program could freeze a visitor's browser tab. Fixed with a
  shared, per-event execution-step budget (`rosh.checkStepBudget()`,
  200,000 iterations, reset once per outermost `send()` dispatch so a
  long-lived page's legitimate cumulative work across many separate
  events/ticks is never punished) — mirrors the equivalent budget
  already added to the Python `Runtime` class for server-side execution
  (e.g. a shared multiplayer world's live command handler), which
  generated JS had no equivalent of until now.
- **Nested `repeat` loops produced different, wrong results in
  generated JavaScript versus the Python runtime.** Every generated
  loop reused the literal variable name `_ri`; harmless for sibling
  loops (they run sequentially) but a genuine correctness bug for
  nested ones — `var` is function-scoped, not block-scoped, so an inner
  loop's `_ri` overwrites its outer loop's, corrupting the outer loop's
  own condition check the moment the inner loop exits. A direct 3×4
  nested `repeat` returned 12 in the Python runtime but only 4 in
  generated JS. Fixed by giving each `repeat` AST node its own loop
  variable.

## 0.9.9 - 2026-08-16

### Security

- **Fixed a second, separate stored-XSS sink over sprite image URLs**,
  found by external review of the 0.9.6 fix. That fix only protected the
  CSS `background-image: url(...)` attribute; any interactive programme
  (a `when`/`on` handler) also serialised sprite data into a JS object
  literal with no escaping on the value at all — worse than the first
  sink, since it ran as live JavaScript rather than HTML. Both the `web`
  and `phaser` targets are affected; both are now fixed with `json.dumps`.

## 0.9.8 - 2026-08-16

### Fixed

- **An invalid comparison operator in a condition (e.g. mixing the
  one-line `on <event> when <condition> <action>` form with `collision`
  used as a condition rather than the correct block form `when collision
  A B ... end`) used to silently compile to invalid JavaScript**, which
  aborted the entire generated script at parse time with no error
  surfaced anywhere. Both places this could happen (`on ... when`
  conditions, and block-form `if`) now raise a clear error at compile
  time instead.

## 0.9.7 - 2026-08-16

### Fixed

- **The one-line `on update`/`on collision` reactor form never started
  the game loop.** `compile_programme()` only set the internal flag that
  triggers `rosh.startLoop()` (the only thing that fires the `"update"`
  event, or runs `tickTimers`/`tickVelocity`/`checkCollisions`) for the
  block-form `when update/collision ... end` and `animate` statements —
  never for the one-line `on <event> <action>` form, even though it's a
  first-class, documented syntax. This silently broke the bundled `ball`
  widget (its wall-bounce physics is built entirely from one-line
  `on update ...` statements), the `timer` widget's auto-decrement, and
  any hand-written `on update`/`on collision` code, whenever a program
  didn't *also* contain an unrelated block-form trigger elsewhere.

## 0.9.6 - 2026-08-16

### Security

- **Fixed a stored XSS via sprite image URLs.** `sprite <name> "https://..."`
  descriptions were passed through unescaped into the compiled web target's
  `style="..."` attribute — a URL containing a `"` could close the
  attribute and inject arbitrary HTML/JS into the compiled page. Any
  application compiling and serving untrusted `.rosh` source (e.g. a
  hosted playground) was affected. Fixed at the render sink: sprite URLs
  are now validated (real `data:image/` URI, or a clean `http(s)://` URL
  with no quotes/angle-brackets/control characters) before being trusted
  into unescaped CSS; anything else falls back to a plain colour box.

## 0.9.5 - 2026-08-16

### Fixed

- `examples/widgets/` renamed to `examples/widget-demos/` — it was shadowing
  the bundled widget library for anyone running a bundled example from
  inside `rosh-lang/examples/`, since the default search path checks
  `./widgets` before the bundled library. Widget demo scripts sharing a
  name with a real widget (e.g. `explosion.rosh`) self-referenced their
  own name, tripping the circular-dependency guard and silently returning
  no widget — `breakout.rosh` rendered zero bricks and zero explosions
  when run this way, with no error.

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
