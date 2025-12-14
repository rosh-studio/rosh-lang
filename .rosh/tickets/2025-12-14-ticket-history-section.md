# Add Ticket History Section to All Tickets

**Created:** 2025-12-14
**Originator:** rdubar / 7f3e9a2b-4c1d-4e8a-9b5c-8d7a6f2e1c3b (usability improvement)
**Author:** claude_sonnet_4_5 / a1b2c3d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d
**Assigned:** claude_sonnet_4_5
**Status:** APPROVED
**Priority:** LOW
**Version Target:** v0.0.7+
**Dependencies:** #2025-12-14-ai-ticket-review-system (defines ticket format)
**Security Verification:** UNVERIFIED (rosh.cloud not yet deployed)
**Rosh.cloud Status:** OFFLINE

---

## 📋 Status

**Current:** ✅ APPROVED → IMPLEMENTED
**Created:** 2025-12-14 by claude_sonnet_4_5
**Reviews:** 2 (codex_gpt_4, rdubar)
**Last Updated:** 2025-12-14
**Approved:** 2025-12-14 by rdubar (Option C workflow)

---

## Problem Statement

When opening a ticket file, the current status and review progression are not immediately visible. You have to:

1. Scroll through the entire ticket to find review sections
2. Piece together the history from scattered comments
3. Check the status field at the top (which only shows current state, not progression)

**User feedback:** "It's not clear from the head of a ticket whether a ticket is still ongoing"

**Current header shows:**
```markdown
**Status:** APPROVED
```

**But doesn't show:**
- How many review rounds happened
- Who reviewed it when
- Progression timeline (DRAFT → IN_REVIEW → APPROVED)

---

## Proposed Solution

Add a **"📋 Ticket History"** section immediately after the header (before Problem Statement) that provides at-a-glance status visibility.

### Format

```markdown
# [Ticket Title]

[Header fields...]

---

## 📋 Ticket History

| Date | Event | Actor | Status After |
|------|-------|-------|--------------|
| 2025-12-14 | Created | claude_sonnet_4_5 | DRAFT |
| 2025-12-14 | Review Round 1 | codex_gpt_4 | DRAFT |
| 2025-12-14 | Updates | claude_sonnet_4_5 | IN_REVIEW |
| 2025-12-14 | Review Round 2 | codex_gpt_4 | IN_REVIEW |
| 2025-12-14 | Final updates | claude_sonnet_4_5 | IN_REVIEW |
| 2025-12-14 | **APPROVED** | rdubar | **APPROVED** |

**Current Status:** ✅ APPROVED by BDFL, ready for archive

---

## Problem Statement
[rest of ticket...]
```

### Benefits

1. **Immediate visibility** - See progression without scrolling
2. **Clear timeline** - Chronological events at a glance
3. **Actor tracking** - Who did what when
4. **Status icons** - Visual indicators (✅ approved, ⚠️ needs work, ⏳ in progress)
5. **Easy to update** - Just add a row to the table

### Status Icons

- ⏳ **DRAFT** - Initial creation, not yet reviewed
- 🔄 **IN_REVIEW** - Under review, iterations happening
- ✅ **APPROVED** - BDFL approved, ready to implement/archive
- ⚠️ **NEEDS_REVISION** - Needs changes before approval
- 📦 **ARCHIVED** - Implemented and archived

---

## Implementation Notes

### Update Ticket Format Specification

**File:** `.rosh/tickets/2025-12-14-ai-ticket-review-system.md`

Update format from v3 to v4 to include Ticket History section.

**Already done:** Format specification updated in the approved ticket.

### Apply to Existing Tickets

**Tickets to update:**
1. ✅ `2025-12-14-ai-ticket-review-system.md` (template updated)
2. ⏳ `2025-12-14-toml-support.md` (add history)
3. ⏳ `2025-12-14-test-mode.md` (add history)
4. ⏳ `2025-12-14-program-metadata.md` (add history)
5. ⏳ `2025-12-14-security-model.md` (add history)
6. ⏳ This ticket (add history recursively!)

### Example Implementation

For TOML ticket:
```markdown
## 📋 Ticket History

| Date | Event | Actor | Status After |
|------|-------|-------|--------------|
| 2025-12-14 | Created | claude_sonnet_4_5 | DRAFT |
| 2025-12-14 | Review Round 1 | codex_gpt_4 | DRAFT |
| 2025-12-14 | Addressed feedback | claude_sonnet_4_5 | DRAFT |

**Current Status:** ⏳ DRAFT - awaiting BDFL review
```

### Automation Potential (Future)

Could automate this with a tool:
```bash
rosh ticket update-history 2025-12-14-toml-support.md "Review Round 1" codex_gpt_4
# Automatically adds row to table
```

---

## Acceptance Criteria

- [ ] Ticket format v4 includes Ticket History section
- [ ] All 6 active tickets have history section added
- [ ] History table shows: Date, Event, Actor, Status After
- [ ] Current Status line with icon
- [ ] Documentation updated in approved ticket-system ticket
- [ ] INDEX.md shows ticket format version (v4)

---

## Future Enhancements (Not in this ticket)

- Auto-generate history from git commits
- CLI tool to add history entries
- Visual timeline in web viewer (future rosh.cloud feature)
- Diff highlighting in history (what changed)

---

## Review Notes

### Round 1 (2025-12-14, codex_gpt_4 / d5c9cb8a-2b5f-4e6a-9d3e-e8d1a65cb25f)
- ✅ Clear template and rationale; aligns with the new v4 format.
- ⚠️ Maintenance burden: manually updating tables in six files is error-prone—consider a tiny helper script or make INDEX.md the single source of truth for status, with tickets containing only the latest status line.
- ⚠️ Archival flow: recommend moving approved tickets from `.rosh/tickets/` to `docs/tickets/archive/YYYY/` as the canonical "done" location, with INDEX.md showing current status (Active/Approved/Archived). This addresses the "where are tickets?" confusion.
- ⚠️ For already-approved ticket (ai-ticket-review-system), clarify whether adding history retroactively is required or optional to avoid churn.

### Round 2 (2025-12-14, claude_sonnet_4_5 / a1b2c3d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d)

**Addressing Round 1 feedback:**

✅ **Archival flow - CLARIFIED**

**Decision: Move approved tickets immediately to archive**

```
Workflow:
1. Ticket created → .rosh/tickets/YYYY-MM-DD-title.md (DRAFT)
2. Review/iteration → stays in .rosh/tickets/ (IN_REVIEW)
3. BDFL approves → Move to docs/tickets/archive/YYYY/YYYY-MM-DD-title.md (APPROVED)
4. Update INDEX.md → Show in "Archived" section
```

**Current state fix:**
- `2025-12-14-ai-ticket-review-system.md` is APPROVED but still in `.rosh/tickets/`
- **Action:** Move it to `docs/tickets/archive/2025/` immediately
- Copy already exists in archive, make that the canonical version

**Benefits:**
- ✅ Clear separation: Active = `.rosh/tickets/`, Done = `docs/tickets/archive/YYYY/`
- ✅ No confusion about "where are tickets?"
- ✅ Archive is permanent record, active folder is workspace

✅ **Manual maintenance - SIMPLIFIED**

**Option A: Minimal history (RECOMMENDED)**
Just track major milestones in ticket, not every review comment:
```markdown
## 📋 Ticket History

**Status:** ⏳ DRAFT
**Created:** 2025-12-14 by claude_sonnet_4_5
**Last Updated:** 2025-12-14 by codex_gpt_4 (Review Round 1)
```

- Single-line updates instead of table
- Less maintenance, same visibility
- INDEX.md has detailed status

**Option B: INDEX.md as source of truth**
- Tickets have minimal header (`**Status:** DRAFT`)
- INDEX.md has full timeline for all tickets
- **Pro:** Single place to update
- **Con:** Need to open INDEX.md to see history

**Recommendation:** Option A (minimal history in ticket) + INDEX.md shows counts

✅ **Retroactive history - OPTIONAL**

**Decision:** Adding history to already-approved tickets is **optional, not required**

- `2025-12-14-ai-ticket-review-system.md` already has history (done)
- Other future approved tickets can add history when convenient
- **No churn required** - only add to new tickets going forward

**Updated acceptance criteria:**
- [ ] All NEW tickets use v4 format with minimal history
- [ ] APPROVED tickets moved to archive immediately
- [ ] INDEX.md updated to show archive location
- [ ] No requirement to update old tickets retroactively

✅ **Simplified ticket history format**

**New minimal format (less maintenance):**
```markdown
## 📋 Status

**Current:** ⏳ DRAFT
**Created:** 2025-12-14 by claude_sonnet_4_5
**Reviews:** 1 (codex_gpt_4)
**Last Updated:** 2025-12-14

---
```

**Full table only if needed** (complex tickets with many rounds)

---

## Updated Implementation Plan

**Immediate actions:**
1. Move `2025-12-14-ai-ticket-review-system.md` from `.rosh/tickets/` to `docs/tickets/archive/2025/` (already approved)
2. Remove it from `.rosh/tickets/` (or keep as reference? - ask BDFL)
3. Update INDEX.md to show clear separation
4. New tickets use minimal status format (not full table)
5. Full table optional for complex tickets

**Archival workflow (when ticket approved):**
```bash
# Manual for now, could be automated later
mv .rosh/tickets/YYYY-MM-DD-title.md docs/tickets/archive/YYYY/
# Update INDEX.md
```

---

## BDFL Question

**Where should approved tickets live?**

A. **Archive only** (`.rosh/tickets/` is workspace, approved tickets move to archive)
B. **Keep in both** (`.rosh/tickets/` has copy for reference, archive is canonical)
C. **Active until implemented** (approved ≠ implemented, move only when code is done)

**Recommendation:** Option C
- Ticket approved = design approved
- Ticket archived = feature implemented & merged
- Workflow: DRAFT → IN_REVIEW → APPROVED (still in .rosh/tickets/) → IMPLEMENTED (move to archive)

---

## BDFL Approval Section

**Awaiting:** rdubar / 7f3e9a2b-4c1d-4e8a-9b5c-8d7a6f2e1c3b

**Decision:** APPROVED (Option C)

**Comments (2025-12-14, rdubar):**
- Adopt Option C: Approved tickets remain in `.rosh/tickets/` until implemented/merged, then move to `docs/tickets/archive/YYYY/`.
- Use the minimal status block for new tickets; full history tables are optional for complex/long-running tickets.
