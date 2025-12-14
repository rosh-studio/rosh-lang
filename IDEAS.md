# Rosh Ideas & Brainstorming Log

**Format:** Daily timestamped entries for ideas, pain points, and strategic direction

**Purpose:** Capture thinking as it happens, keep dated records, organize project vision

---

## 14-Dec-2025: Overnight Ideas - Documentation, Metadata & Tooling

**Context:** After completing v0.0.7 event system and code review fixes, focusing on project infrastructure and quality-of-life improvements.

### 1. Date Policy
**Decision:** Standardize on UK date format or ISO 8601 in all documentation
- Example: 14-Dec-2025 or 2025-12-14
- Consistency across tickets, changelogs, documentation
- Makes chronological sorting reliable

### 2. TOML Support (--toon flag)
**Priority:** First-order (high priority)
- TOML as JSON alternative for configuration
- `--toon` flag for TOML output mode
- Project manifests: `rosh.toml` (or `rosh.toon`)
- Modern, readable format for config files

### 3. Test Mode for Interactive Code
**Problem:** Can't run games with `input` in CI/CD
**Solution:** Test mode with mock inputs
- Mock `input` command for automated testing
- Mock `stop` command for clean test termination
- Enable CI/CD testing of interactive programs
- `rosh --test` flag or similar

### 4. AI Ticket/Review/Documentation System ⭐ HIGHEST PRIORITY
**Vision:** Self-documenting collaborative development with AI

**Workflow:**
1. AI creates ticket with self-identification
2. AI implements feature/fix
3. AI reviewer (different model) reviews work
4. Back-and-forth iteration until resolved
5. BDFL (human) final approval
6. Auto-documentation generation at scale

**Structure:**
- Tickets: `.rosh/tickets/YYYY-MM-DD-short-title.md`
- Archive: `docs/tickets/archive/YYYY/`
- Index: `docs/tickets/INDEX.md` (context management)

**Identity Tracking:**
- AI self-identifies in tickets (UUID + model)
- Human identified by Rosh username
- rdubar: `7f3e9a2b-4c1d-4e8a-9b5c-8d7a6f2e1c3b`
- Claude Sonnet 4.5: `a1b2c3d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d`

**Context Management:**
- Keep tickets < 1000 lines
- Archive implemented tickets
- INDEX.md for quick reference
- Prevents context bloat as project grows

### 5. Program Metadata System
**Goal:** Version tracking, security, package management foundation

**Proposed Structure:**
```rosh
meta
    version "1.0.0"
    rosh_version "0.0.7"
    author "rdubar"
    license "MIT"
    description "My game"
    uuid "auto-generated"
    checksum "auto-generated"
    security_key "auto-generated"
end

meta.game
    type "2D"
    engine "phaser"
end
```

**Considerations:**
- `meta.core` vs `meta.local` separation
- Public vs private/secret metadata
- Rosh.cloud integration for verification
- Offline operation with warnings
- Checksum + UUID + security_key validation

**Security Models to Evaluate:**
- **Fail-safe:** Warn user, allow continuation (convenience)
- **Fail-secure:** Refuse execution without verification (security)
- Network-optional verification
- Make recommendation in ticket

### 6. Project Folder Format
**Structure:**
```
my-game/
  rosh.toml          # Project manifest
  main.rosh          # Entry point
  src/               # Source files
  stdlib/            # Local stdlib extensions
  .rosh/
    tickets/         # Development tickets
    meta/            # Project metadata
```

**Benefits:**
- Clear organization
- Package management ready
- Multi-file projects
- Separates code from meta

### 7. get/set/go Paradigm
**Concept:** "go" means implement/run/reload
- get: retrieve value
- set: assign value
- go: execute changes, run program, reload state
- Natural command flow

### 8. dump Command
**Purpose:** Save current game state AND code together
**Addresses:** Ongoing serialization challenges
**Use Case:**
```rosh
dump game to "savegame.rosh"  # Saves state + code
load game from "savegame.rosh"
```
- Combined state/code serialization
- Easy save/load for games
- Debugging tool (snapshot runtime)

### 9. when Keyword ✅
**Status:** DONE in v0.0.7
- Event-driven programming
- Reactive game logic
- Already implemented with lexical scoping

### 10. spawn Keyword
**Purpose:** Process/thread management
**Future feature:** Multi-processing support
**Use Cases:**
- Spawn background processes
- Parallel game systems
- Multi-user server architecture

---

## Implementation Priority (14-Dec-2025)

**Immediate (v0.0.7+):**
1. ⭐ AI ticket/review system (infrastructure for all future work)
2. TOML support (--toon, rosh.toml manifests)
3. Test mode (CI/CD compatibility)
4. Metadata system (meta keyword, auto-generation)

**Near-term (v0.0.8-0.0.9):**
5. dump command (serialization)
6. Project folder structure
7. Security model decision & implementation

**Future:**
8. spawn keyword (multi-processing)
9. get/set/go paradigm refinement

---

## Notes

- All ideas dated for chronological tracking
- Cross-reference with ROADMAP.md for scheduling
- Ticket system enables collaborative AI development
- Focus on infrastructure that scales with AI assistance
- Keep everything written down, dated, and organized
