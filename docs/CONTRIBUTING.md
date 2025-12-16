# Contributing to Rosh

**Status:** Internal development only
**When public:** Contributions welcome after v0.1.0

---

## 🏗 Language Design Philosophy

### What Rosh Is

Rosh is a **modern, AI-native control language for live worlds**.

It sits in the tradition of older control languages rather than modern application languages:

| Tradition | What Rosh Inherits |
|-----------|-------------------|
| **Smalltalk, Emacs Lisp** | Live systems that can be inspected and changed while running |
| **Logo, HyperTalk** | Human-readable, intent-focused commands |
| **Tcl, Unix shells** | Glue layer embedded in larger systems |
| **PostScript, SQL** | Describes *what* should change, not *how* |
| **LPC, Inform** | Meaning-first, world-centric, hot-modifiable |

**Key insight:** Rosh is not a replacement for game engines or systems languages.
It is a **semantic layer** that lets humans and AI safely reshape running environments.

### Design Principles

1. **Spoken-first** - Optimize for dictation and voice input
2. **Natural English** - Sounds like talking to a person
3. **Minimal punctuation** - Voice-friendly, no brackets or semicolons
4. **AI-native** - Works seamlessly with AI assistants
5. **Live worlds** - Inspect and modify running systems in real-time
6. **Engine-agnostic** - Same Rosh code runs in Phaser, Pygame, Unity, etc.
7. **Computers do the work** - Guess intelligently, ask if uncertain, never block on ambiguity

### The "Computers Do The Work" Rule

If Rosh isn't sure what to do:
- Make a reasonable guess
- Inform the user what was assumed
- Offer to change if they disagree
- Never block on uncertainty if a safe default exists

Examples:
- Missing asset? Use placeholder + warning (already implemented)
- Ambiguous syntax? Pick most likely interpretation, suggest correction
- Type mismatch? Coerce if safe, warn if risky

**Philosophy:** Optimize for user flow, not language purity.

---

## 📝 Feature Addition Rules

Every new feature must:

1. ✅ Be documented in `ROSH-MANUAL.rosh`
2. ✅ Have natural language syntax
3. ✅ Work with voice input
4. ✅ Include help documentation
5. ✅ Pass all tests after addition

**After each update:**
- Run all tests (manual + unit tests)
- Update `ROSH-MANUAL.rosh` with examples
- Update command help text in interpreter
- Update `CHANGELOG.md`
- Verify nothing broke

---

## 🎫 Ticket Workflow (AI-Assisted Development)

**Since:** v0.0.7+ (2025-12-14)
**Purpose:** Systematic documentation, AI collaboration, and quality control

### Overview

All significant changes go through a ticket-based workflow:

1. **Create Ticket** - Document problem and proposed solution
2. **Implement** - Make changes, reference ticket
3. **Review** - AI or human reviews implementation
4. **Iterate** - Back-and-forth until resolved
5. **Approve** - BDFL (rdubar) final approval
6. **Archive** - Move to archive when implemented

### Ticket Structure

**Active tickets:** `.rosh/tickets/YYYY-MM-DD-short-title.md`
**Archive:** `docs/tickets/archive/YYYY/`
**Index:** `docs/tickets/INDEX.md` (quick reference)

### When to Create a Ticket

**Always create tickets for:**
- New features (event system, TOML support, etc.)
- Breaking changes
- Security decisions
- Architecture changes
- Significant refactoring

**Skip tickets for:**
- Typo fixes
- Comment updates
- Minor documentation tweaks
- Obvious bug fixes (< 10 lines)

### Ticket Format

```markdown
# [Title]

**Created:** YYYY-MM-DD
**Author:** [AI Model + UUID or username + UUID]
**Assigned:** [Who's implementing]
**Status:** [DRAFT | IN_REVIEW | RESOLVED | APPROVED | ARCHIVED]
**Priority:** [CRITICAL | HIGH | MEDIUM | LOW]
**Version Target:** vX.X.X
**Dependencies:** [Ticket references, if any]

---

## Problem Statement
[What needs solving]

## Proposed Solution
[How to solve it]

## Implementation Notes
[Technical details, files changed, design decisions]

## Testing
[How to verify it works]

## Review Comments
[AI/human feedback, iteration discussion]
```

### Identity System

**AI Contributors:**
- Claude Sonnet 4.5: `a1b2c3d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d`
- Other AIs self-identify with model name + UUID

**Human Contributors:**
- rdubar (BDFL): `7f3e9a2b-4c1d-4e8a-9b5c-8d7a6f2e1c3b`

AI always self-identifies in tickets created or reviewed.

### Review Process

**AI Review:**
1. Different AI model reviews implementation
2. Checks against ticket specification
3. Suggests improvements or approves
4. Iterates with implementer until resolved

**Human Review (BDFL):**
1. Final approval required for all tickets
2. Can request changes at any stage
3. Marks ticket as APPROVED when ready
4. Ticket then archived to `docs/tickets/archive/YYYY/`

### Context Management

**To prevent bloat:**
- Keep tickets < 1000 lines
- Archive implemented tickets by year
- Use INDEX.md for quick reference
- Cross-reference related tickets

**See:** `.rosh/tickets/2025-12-14-ai-ticket-review-system.md` for complete specification

### Error and Confusion Documentation Policy

**Policy (Added 2025-12-14):** All errors, misunderstandings, and confusions during development MUST be documented in ticket history.

**Why:** Transparency helps future contributors understand decision-making and avoid repeating mistakes.

**When to document:**
- ❌ **Misinterpreted requirements** - Document what was misunderstood and how it was resolved
- ❌ **Implementation mistakes** - Explain what went wrong and the fix
- ❌ **Breaking changes** - Document impact and migration path
- ❌ **API changes** - Record old vs new behavior
- ⚠️ **Ambiguous specifications** - Document clarifications from BDFL

**Where to document:**
1. **In the ticket** - Add "Implementation Notes (Post-Implementation)" section
2. **In CHANGELOG.md** - Note breaking changes and corrections
3. **In commit messages** - Reference the confusion in relevant commits

**Example:** See `2025-12-14-toml-support.md` for the TOML/TOON flag name confusion documentation.

**Format:**
```markdown
## Implementation Notes (Post-Implementation)

**IMPORTANT: [Brief Title] - RESOLVED (YYYY-MM-DD)**

**Issue:** [What was misunderstood]

**What happened:** [Chronological explanation]

**Resolution:** [How it was fixed]

**Lesson learned:** [What to do differently next time]

**Policy updated:** [If this led to a policy change]
```

### How to Log a Review

**For AI reviewers:**
1. Add a new section under `## Review Notes` with heading format:
   ```markdown
   ### Round N (YYYY-MM-DD, ai_username / uuid)
   ```
2. Always self-identify with your model username and UUID:
   - `claude_sonnet_4_5` / `a1b2c3d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d`
   - `codex_gpt_4` / `d5c9cb8a-2b5f-4e6a-9d3e-e8d1a65cb25f`
3. Provide constructive feedback on:
   - Implementation correctness
   - Adherence to ticket spec
   - Code quality and style
   - Missing test coverage
   - Documentation completeness
4. Mark issues as ✅ (approved), ⚠️ (needs attention), or ❌ (blocking)

**For human reviewers:**
1. Same format, use your Rosh username and UUID
2. Final approval authority rests with BDFL (rdubar)

**Example:**
```markdown
### Round 2 (2025-12-14, codex_gpt_4 / d5c9cb8a-...)
- ✅ Implementation matches spec
- ⚠️ Missing edge case tests for empty input
- ✅ Documentation is clear
```

---

## 🧪 Testing Policy

### Test File Organization
- **scratches/** - Temporary testing during development
- Never commit test files to root directory
- Test file patterns: `test_*.rosh`, `demo_*.rosh`, `scratch_*.rosh`
- Use `trash` CLI for cleanup (not `rm`)

### After Feature Documentation
1. Verify feature added to `ROSH-MANUAL.rosh`
2. Run `rosh ROSH-MANUAL.rosh` successfully
3. Trash all scratch files: `trash scratches/*.rosh`
4. Commit only documented feature

### Test Suite
- `ROSH-MANUAL.rosh` IS the integration test suite
- Unit tests in `tests/` directory (pytest)
- All tests must pass before merge
- Target: 100+ automated tests by v1.0

---

## 📦 Version Numbering

**Semantic Versioning (v0.x.y)**
- `v0.x.0` - Major feature additions (milestones)
- `v0.0.y` - Minor features, bug fixes
- `v1.0.0` - Production-ready, stable syntax
- `v2.0.0` - Major architectural changes (e.g., Rust core)

---

## 🔤 Naming Conventions

### Project Names
- **Rosh** - Always capitalize (proper noun)
- **rosh** - Lowercase only in code/commands (`rosh compile`)
- **ROSH-MANUAL.rosh** - All caps for emphasis (file name)

### Technology Names
- **JavaScript** (not Javascript, JS in casual context)
- **TypeScript** (not Typescript)
- **VS Code** (not VSCode)
- **GitHub** (not Github)

### File Extensions
- `.rosh` - Rosh source files
- `.md` - Markdown documentation
- `.json` - Configuration files

### Command Naming
- Use natural language: `create`, `set`, `print`
- Avoid abbreviations unless standard: `props` (properties)
- Aliases documented clearly: `exit` = `stop`

---

## 🔀 Git Workflow

### Branch Strategy
- **main** - Stable, tagged releases
- Feature branches: `feature/event-system`
- Hotfix branches: `hotfix/parser-bug`

### Commit Messages
Follow conventional commits:
```
feat: Add event system (when/trigger syntax)
fix: Parser error on nested if statements
docs: Update ROSH-MANUAL with Section 28
test: Add tests for list slicing
chore: Clean up test files
```

### Pull Requests
- One feature per PR
- Include tests and documentation
- Update `CHANGELOG.md`
- Ensure `ROSH-MANUAL.rosh` runs successfully

---

## 🚀 Release Process

1. Update version in `pyproject.toml`
2. Run `rosh ROSH-MANUAL.rosh` successfully
3. Run all unit tests: `pytest`
4. Update `CHANGELOG.md` with release notes
5. Tag release: `git tag v0.0.X`
6. Push tag: `git push --tags`
7. Update `ROADMAP.md` status

---

## 📊 Documentation Standards

### Markdown Style
- Use GitHub-flavored Markdown
- Headers: `#` for H1, `##` for H2, etc.
- Code blocks: Triple backticks with language
- Links: Descriptive text, not raw URLs
- Lists: `-` for unordered, `1.` for ordered

### Code Examples
- Always include working examples
- Show input and expected output
- Use realistic scenarios (MUD/game contexts)
- Test examples before publishing

### Date Format
- ISO 8601: YYYY-MM-DD (2025-12-13)
- Consistency across all documents

---

## 🔐 Security

**Current Status (v0.0.x):**
- ⚠️ Single-user, local development only
- No sandboxing yet
- Full filesystem access
- AI code requires confirmation but runs unrestricted

**Before Multi-User (v0.1.0) MUST implement:**
1. Complete sandboxing for all code execution
2. User space isolation
3. Code verification (hash/signature)
4. Professional security audit
5. Safe mode by default

---

## 🏃 Development Setup

See `docs/DEVELOPMENT.md` for complete setup instructions.

**Quick Start:**
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and setup
git clone <repo>
cd rosh-lang
uv sync

# Run tests
uv run pytest
uv run rosh ROSH-MANUAL.rosh
```

---

## 💡 Getting Help

- **Technical questions:** Check `ROSH-MANUAL.rosh`
- **Setup issues:** See `docs/DEVELOPMENT.md`
- **Feature proposals:** Create issue with proposal template
- **Bug reports:** Create issue with reproduction steps

---

## 📄 License

MIT License - See `LICENSE` file for details.

Free for commercial use. Modify and distribute freely.

---

*For complete project policies including business strategy, see `../rosh-corporate/docs/POLICIES.md` (private repo only)*
