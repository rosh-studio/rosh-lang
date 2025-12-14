# Ticket: Transpiler MVP - Phaser (Browser Games)

**Status:** DRAFT
**Priority:** CRITICAL
**Created:** 2025-12-14
**Author:** Claude Sonnet 4.5
**BDFL Approval:** PENDING

---

## Vision Context

**Roshbosh End Goal:**
Users should be able to:
1. Use a **simple properties editor** (GUI) to define game objects
2. Write **Rosh code directly** for behavior
3. Generate **Rosh code from AI** prompts
4. **Compile quickly** to different game engines (Phaser, Unity, Godot, etc.)

**This Ticket:** First step toward that vision - Rosh → Phaser transpiler MVP

---

## Strategic Question: Python vs Rust for Transpiler?

### Python Transpiler (RECOMMENDED FOR MVP)

**Pros:**
- ✅ Same language as interpreter (reuse AST, parsing, existing code)
- ✅ Fast iteration and prototyping
- ✅ Easy AI integration (OpenAI/Anthropic APIs already working)
- ✅ Can get working in days, not weeks
- ✅ Good enough for MVP and initial demos

**Cons:**
- ⚠️ Slower compilation (but irrelevant for small games - subsecond)
- ⚠️ Distribution requires Python runtime (acceptable for dev tools)

### Rust Transpiler (FUTURE - v2.0+)

**Pros:**
- ✅ Fast compilation (milliseconds)
- ✅ Single binary distribution (no runtime needed)
- ✅ Can compile to WASM (run transpiler in browser!)
- ✅ Better for production/enterprise tooling

**Cons:**
- ⚠️ Would take weeks to implement from scratch
- ⚠️ Can't reuse existing Python AST structures
- ⚠️ Delays getting to market

### Recommendation: Python Now, Rust Later

**Phase 1 (This Ticket):** Python transpiler for MVP
- Get working quickly
- Validate approach
- Gather user feedback
- Prove the concept

**Phase 2 (v2.0+):** Rust rewrite if needed
- After we know it works
- After we have users
- When performance matters
- Already in BACKLOG.md

**Decision:** Python for MVP. Rust is premature optimization.

---

## Scope: Ultra-Minimal MVP

**Philosophy:** "Not here to build Rome in one day"

### What This Ticket WILL Do

✅ Transpile a **simple Rosh program** to **working Phaser JavaScript**

**Example Input (Rosh):**
```rosh
# Simple game: Goblin guarding a chest
create object goblin
    set x to 100
    set y to 200
    set sprite to "goblin.png"
end

create object chest
    set x to 400
    set y to 200
    set sprite to "chest.png"
end

print "Game created! Goblin at ({goblin.x}, {goblin.y})"
```

**Example Output (Phaser JavaScript):**
```javascript
// Auto-generated from Rosh code
class GameScene extends Phaser.Scene {
    create() {
        // Goblin object
        this.goblin = this.add.sprite(100, 200, 'goblin');

        // Chest object
        this.chest = this.add.sprite(400, 200, 'chest');

        // Print statement → console.log
        console.log(`Game created! Goblin at (${this.goblin.x}, ${this.goblin.y})`);
    }
}
```

**Acceptance Criteria:**
- [ ] Transpiler generates valid Phaser code
- [ ] Generated code runs in browser
- [ ] Can see goblin sprite at (100, 200)
- [ ] Can see chest sprite at (400, 200)
- [ ] Console shows interpolated print statement

### What This Ticket Will NOT Do

❌ Events (`when`/`trigger`) - Deferred to v0.1.6
❌ User input - Deferred to v0.1.6
❌ Animation - Deferred to v0.1.6
❌ Multiple transpiler targets (Pygame, Unity) - Deferred to v0.5.5+
❌ Optimization - Deferred to v2.0
❌ Full Rosh language coverage - Incremental

**Covered in MVP:**
- Objects (`create object ... end`)
- Properties (`set x to 100`)
- String interpolation (`"Goblin at ({goblin.x}, {goblin.y})"`)
- Basic positioning

**Deferred to later versions:**
- Control flow (if/else, loops)
- Functions
- Events
- AI integration
- Properties editor GUI

---

## Implementation Approach

### 1. Architecture

```
Rosh Code (.rosh)
    ↓
Lexer → Tokens
    ↓
Parser → AST (already exists!)
    ↓
Transpiler (NEW!) → Phaser JavaScript
    ↓
Phaser Game (runs in browser)
```

**Key Insight:** We already have lexer, parser, and AST. Just need to walk the AST and emit JavaScript instead of interpreting it.

### 2. File Structure

```
src/rosh/
├── transpilers/
│   ├── __init__.py
│   ├── base.py           # Base transpiler class
│   └── phaser.py         # Phaser-specific transpiler
└── cli.py                # Add --transpile flag
```

### 3. Core Transpiler Logic

**Approach:** Visitor pattern over AST

```python
class PhaserTranspiler:
    def transpile(self, ast_nodes):
        """Convert AST to Phaser JavaScript"""
        # Generate Phaser boilerplate
        # Walk AST nodes
        # Emit JavaScript for each node
        pass

    def visit_create_object(self, node):
        """Convert: create object goblin → this.goblin = ..."""
        pass

    def visit_set_property(self, node):
        """Convert: set x to 100 → this.goblin.x = 100"""
        pass
```

### 4. Graphics: Programmer Art First, AI Later

**For MVP:**
- Use colored rectangles (Phaser can draw these)
- Or simple emoji sprites (🧙 for goblin, 📦 for chest)
- Focus on transpiler working, not pretty graphics

**For v0.2.0 (Voice Demo):**
- Integrate DALL-E/Stable Diffusion
- Generate sprites from AI prompts
- "Draw me a goblin sprite" → goblin.png
- This aligns with Roshbosh vision

**Example MVP without custom graphics:**
```javascript
// Programmer art: colored rectangles
this.goblin = this.add.rectangle(100, 200, 50, 50, 0x00ff00); // Green square
this.chest = this.add.rectangle(400, 200, 60, 40, 0x8B4513);  // Brown rectangle
```

### 5. Development Process

**Phase 1: Spike (1 day)**
- Hand-write expected Phaser output for "goblin and chest"
- Verify it runs in browser
- Understand Phaser API

**Phase 2: Transpiler (2-3 days)**
- Implement AST walker
- Implement object creation
- Implement property setting
- Generate working JavaScript

**Phase 3: Integration (1 day)**
- Add `--transpile phaser` CLI flag
- Add `rosh build` command
- Generate HTML template with Phaser boilerplate

**Phase 4: Testing (1 day)**
- Test with "goblin and chest" example
- Test with multiple objects
- Test with string interpolation
- Verify browser execution

**Total Estimate:** 5-6 days focused work

---

## Success Metrics

### Must Have (MVP)
- [ ] `rosh build game.rosh --target phaser` generates JavaScript
- [ ] Generated code runs in browser without errors
- [ ] Can see multiple game objects rendered
- [ ] String interpolation works in console.log

### Should Have (Nice to Have)
- [ ] Generated code is readable (not minified)
- [ ] HTML template includes Phaser CDN
- [ ] Error messages if unsupported Rosh features used

### Won't Have (Deferred)
- Events/triggers
- User input
- Animation
- Sound
- Multiple scenes
- Save/load

---

## Technical Decisions

### Decision 1: Phaser Version
**Choice:** Phaser 3.x (latest stable)
**Rationale:** Modern, well-documented, actively maintained

### Decision 2: JavaScript Target
**Choice:** ES6+ (modern JavaScript)
**Rationale:** Cleaner code, easier to read, all modern browsers support it

### Decision 3: Bundling
**Choice:** No bundler for MVP (single .js file)
**Rationale:** Simpler, easier to debug, good enough for demos

### Decision 4: Asset Loading
**Choice:** Assume assets exist, no asset pipeline for MVP
**Rationale:** Focus on transpiler, not build tools

### Decision 5: Error Handling
**Choice:** Basic validation, fail fast
**Rationale:** Don't transpile unsupported features, clear error messages

---

## Example Workflow (User Perspective)

**Step 1: Write Rosh code**
```bash
# game.rosh
create object goblin
    set x to 100
    set y to 200
end

create object chest
    set x to 400
    set y to 200
end
```

**Step 2: Transpile to Phaser**
```bash
rosh build game.rosh --target phaser --output game.js
# Generates:
#   game.js          (Phaser code)
#   game.html        (HTML template)
#   assets/          (placeholder for sprites)
```

**Step 3: Open in browser**
```bash
open game.html
# Browser shows: Green square (goblin) and brown rectangle (chest)
```

**Step 4 (Future): Add AI-generated sprites**
```bash
rosh generate-sprite goblin "medieval goblin sprite, pixel art"
# Uses DALL-E to create goblin.png
```

---

## Risks & Mitigations

### Risk 1: Phaser API Complexity
**Risk:** Phaser has a large API, might be overwhelming
**Mitigation:** Start with minimal subset (sprites, positioning)

### Risk 2: AST Coverage
**Risk:** Not all Rosh constructs map cleanly to Phaser
**Mitigation:** Start with subset, error on unsupported features

### Risk 3: Debugging Transpiled Code
**Risk:** Generated JavaScript might be hard to debug
**Mitigation:** Emit readable code with comments

### Risk 4: Scope Creep
**Risk:** "Just one more feature" leads to bloat
**Mitigation:** Strict MVP scope, defer everything else

---

## Alternatives Considered

### Alternative 1: Pygame First
**Pros:** Python → Python, easier
**Cons:** Desktop deployment, requires installation
**Decision:** Deferred to v0.5.5

### Alternative 2: Both Pygame and Phaser POC
**Pros:** Compare approaches
**Cons:** Takes longer, user already excited about Phaser
**Decision:** Just do Phaser for MVP

### Alternative 3: Full Rosh Coverage
**Pros:** More complete
**Cons:** Takes weeks, delays feedback
**Decision:** Minimal MVP, iterate based on usage

---

## Dependencies

### Required Before This Ticket
- ✅ AST structure (already exists)
- ✅ Parser (already exists)
- ✅ String interpolation (v0.0.6)
- ✅ Object system (v0.0.1)

### Blocks Future Work
- v0.1.6: Events in Phaser
- v0.2.0: Voice demo with Phaser
- v0.5.5: Second transpiler (Pygame)

---

## Codex Review (2025-12-14)

**Reviewer:** codex_gpt_4 (d5c9cb8a-2b5f-4e6a-9d3e-e8d1a65cb25f)
**Status:** Good to approve with clarifications

**✅ Approved Elements:**
- Tight scope (objects, props, string interpolation, positioning)
- Clear success criteria
- AST visitor architecture
- Programmer art MVP approach
- Risk identification

**📋 Clarifications Needed:**

### 1. Pygame POC Placement
**Codex Note:** "Pygame is deferred to v0.5.5; per your earlier ask, maybe slot a Pygame POC earlier"

**BDFL Decision (2025-12-14):** ✅ Option A - Phaser-only MVP (faster to market)
- Get Phaser working first
- Pygame comes next after Phaser works (v0.5.5)
- No POC comparison needed - ship faster

**Codex Note:** "Option B (POC) is low-cost but Phaser-only is fine for speed. Given how different JS vs Python transpilation is, a small POC could be useful, but I'd accept Phaser-only to ship faster."

### 2. CLI UX Clarity
**Codex Note:** "Pick one flag/command and document it"

**Proposed Command:**
```bash
rosh build game.rosh --target phaser --output dist/
```

**Rationale:**
- `build` subcommand (clear intent: "compile for deployment")
- `--target phaser` (extensible: `--target pygame`, `--target unity` later)
- `--output dist/` (where to put generated files)

**Generated Files:**
```
dist/
├── game.js          # Generated Phaser code
├── index.html       # HTML boilerplate with Phaser CDN
└── assets/          # Placeholder for sprites (empty in MVP)
```

**Alternative considered:** `--transpile phaser` (rejected: less clear than `build`)

### 3. Error Handling Policy
**Codex Note:** "Fail fast on unsupported constructs; don't emit partial code"

**Proposed Policy:**
```
STRICT MODE (MVP):
- Unsupported feature → Clear error message + halt
- No partial transpilation
- No silent failures

Example error:
  Error: Transpiler does not support 'when/trigger' events yet
  This feature is planned for v0.1.6
  Use objects and properties only for v0.1.5

Supported features in v0.1.5:
  ✅ create object
  ✅ set property
  ✅ print (→ console.log)
  ✅ String interpolation
  ❌ when/trigger (deferred to v0.1.6)
  ❌ User input (deferred to v0.1.6)
```

### 4. Asset Story Confirmation
**Codex Note:** "Confirm rectangles/emoji sprites are acceptable or define default sprite pattern"

**Proposed MVP Asset Strategy:**
```javascript
// Option 1: Colored rectangles (RECOMMENDED FOR MVP)
this.goblin = this.add.rectangle(100, 200, 50, 50, 0x00ff00); // Green
this.chest = this.add.rectangle(400, 200, 60, 40, 0x8B4513);  // Brown

// Option 2: Emoji text (fallback)
this.goblin = this.add.text(100, 200, '👺', { fontSize: '48px' });
this.chest = this.add.text(400, 200, '📦', { fontSize: '48px' });
```

**Acceptance Criteria:**
- MVP must render SOMETHING visible in browser
- Colored rectangles are sufficient (no custom sprites needed)
- AI-generated sprites deferred to v0.2.0

**BDFL Decision (2025-12-14):** ✅ Colored rectangles (emojis only if trivial)
**Codex Recommendation:** Rectangles keep Phaser code minimal and unambiguous

### 5. Testing Plan
**Codex Note:** "Add automated check (generate JS and grep for expected sprite calls)"

**Proposed Testing:**
```bash
# Test 1: Transpiler generates valid JavaScript
rosh build test.rosh --target phaser --output test-output/
grep -q "this.goblin = this.add.rectangle" test-output/game.js
grep -q "this.chest = this.add.rectangle" test-output/game.js

# Test 2: Generated code is valid JS (syntax check)
node --check test-output/game.js

# Test 3: HTML boilerplate includes Phaser CDN
grep -q "phaser.min.js" test-output/index.html

# Add to CI/CD pipeline
```

**Automated Test Suite (pytest):**
- `tests/test_transpiler_phaser.py`
- Transpile simple Rosh programs
- Verify output contains expected Phaser API calls
- Check for syntax errors in generated code

---

## BDFL Decisions (2025-12-14)

**All questions resolved - APPROVED TO PROCEED:**

1. ✅ **Pygame POC?** → Option A (Phaser-only MVP, faster to market)
2. ✅ **Asset MVP?** → Colored rectangles (emojis only if trivial)
3. ✅ **CLI command?** → `rosh build --target phaser --output dist/`
4. ✅ **Error handling?** → Fail fast with clear messages (strict mode)
5. ✅ **Generated code style?** → Verbose/readable with comments

**Codex on code style:** "Start verbose/readable with comments. It's an MVP; terseness can come later if needed."

---

## Next Steps (After Approval)

1. **Create implementation plan** (in plan mode if desired)
2. **Spike: Hand-write target Phaser code**
3. **Implement transpiler**
4. **Test with "goblin and chest" example**
5. **Document in ROSH-MANUAL.rosh**
6. **Demo!**

---

## References

- Phaser 3 Docs: https://photonstorm.github.io/phaser3-docs/
- Existing AST: `src/rosh/ast_nodes.py`
- Existing Interpreter: `src/rosh/interpreter.py`
- Transpiler Roadmap: `ROADMAP.md` v0.1.0

---

## Approvals

**BDFL:** ✅ APPROVED (2025-12-14)
- Phaser-only MVP (Option A)
- Colored rectangles for sprites
- `rosh build --target phaser` CLI
- Fail-fast error handling
- Verbose/readable generated code

**Codex Review:** ✅ APPROVED (2025-12-14)
- Reviewer: codex_gpt_4 (d5c9cb8a-2b5f-4e6a-9d3e-e8d1a65cb25f)
- All clarifications addressed
- Ready to proceed with implementation

---

**Status:** ✅ APPROVED (2025-12-14) - Ready for implementation
