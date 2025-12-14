# Rosh Development Backlog

**Purpose:** Track features, improvements, and ideas that are valuable but not currently scheduled
**Last Updated:** 2025-12-14

---

## How This Works

**Backlog items are:**
- Features that have been discussed and deemed valuable
- Work that's been deferred from active milestones
- Ideas that need more research or user feedback before scheduling

**Backlog items are NOT:**
- Active work (that goes in ROADMAP.md)
- Bugs (those go in ISSUES.md)
- Rough ideas (those go in IDEAS.md)

**Moving items OUT of backlog:**
- When user demand is clear → Move to ROADMAP.md
- When research is complete → Move to ROADMAP.md
- When priority increases → Move to ROADMAP.md

---

## Backlog Items

### Making TOON Default Format

**Status:** BACKLOG (Unassigned future decision)
**Current State:** TOON fully implemented (encoder + decoder in v0.0.9)

**What's Complete:**
- ✅ TOON encoder and decoder (v0.0.9)
- ✅ Full round-trip support (save/load .toon files)
- ✅ 37 comprehensive unit tests
- ✅ Complete documentation

**What's Deferred:**
- Making TOON the default format for extensionless saves
  - Currently: `save "state"` → creates state.json (default)
  - Proposed: `save "state"` → creates state.toon (TOON as default)

**Why Deferred:**
- JSON is familiar and well-understood
- Need real-world usage data before changing defaults
- No urgency - users can explicitly use .toon extension
- More user feedback needed on TOON format

**Criteria to Move to Active Roadmap:**
- Significant TOON file usage in the wild
- User requests for TOON as default
- Clear benefit demonstrated (token savings, LLM integration patterns)
- Community consensus on format preference

**Estimated Effort:** 1-2 days (change default, update docs, migration guide)

**References:**
- TOON Spec: https://github.com/toon-format/toon
- Implemented in: v0.0.9

---

### Unity Transpiler (VR/AR Deployment)

**Status:** BACKLOG (Planned for v0.4.0, 2027)
**Depends On:** Browser transpiler (Phaser) proving the concept

**Description:**
Transpile Rosh → Unity C# for VR/AR platforms (Quest, Vision Pro)

**Why Backlog:**
- Need to prove transpilation concept with simpler target first (JavaScript/Phaser)
- VR market still maturing
- Focus on getting single-player experiences solid first

**What Needs to Happen First:**
- v0.2.0: Phaser transpiler working
- v0.2.0: Voice demo proving the concept
- User feedback on transpiled games

**Estimated Effort:** 6-8 weeks

---

### Multi-User Engine (rosh.cloud)

**Status:** BACKLOG (Planned for v0.5.0, 2027)

**Description:**
- User authentication and sessions
- Networked message passing
- Shared world state
- Event synchronization across clients

**Why Backlog:**
- Single-player experiences must be solid first
- Requires infrastructure investment (hosting, etc.)
- Need stable language features before multi-user complexity

**What Needs to Happen First:**
- v0.2.0: Phaser transpiler + voice demo
- v0.3.0: Package system
- Stable v1.0.0 language spec

**Estimated Effort:** 3-4 months

---

### Package Manager Enhancements

**Status:** BACKLOG (Beyond v0.3.0)

**Description:**
- Package registry/repository
- Semantic versioning enforcement
- Dependency conflict resolution
- Private packages
- Package signing/verification

**Why Backlog:**
- Basic package system (v0.3.0) comes first
- Need ecosystem growth before advanced features matter
- Security model must be finalized first

**What Needs to Happen First:**
- v0.3.0: Basic package system working
- User feedback on package pain points
- Security model fully implemented

---

### Rust Core Rewrite

**Status:** BACKLOG (Optional, v2.0.0+, 2028+)

**Description:**
Rewrite Rosh interpreter core in Rust for:
- Better performance
- Better sandboxing
- Multi-platform deployment
- Memory safety

**Why Backlog:**
- Python implementation works fine for current needs
- Focus on language features and ecosystem first
- Major undertaking that only makes sense after v1.0.0
- Backward compatibility with v1.x required

**What Needs to Happen First:**
- v1.0.0: Language stable and frozen
- Clear performance bottlenecks identified
- User base large enough to justify the effort

**Estimated Effort:** 6-12 months

---

## Recently Moved From Backlog

*Items that moved from backlog to active development:*

**None yet** - This backlog was just created on 2025-12-14

---

## Review Process

**Monthly Review:**
- Check if any items have met their "move to active" criteria
- Update status based on user feedback
- Add new items as features are deferred
- Remove items that are no longer relevant

**Quarterly Review:**
- Evaluate priorities based on user feedback
- Update effort estimates
- Reassess dependencies
- Sync with ROADMAP.md milestones

---

*For active development, see ROADMAP.md*
*For current issues/bugs, see ISSUES.md*
*For rough ideas, see IDEAS.md*
