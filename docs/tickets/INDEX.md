# Ticket Index

**Last Updated:** 2025-12-14
**Purpose:** Quick reference for all development tickets (active and archived)
**Workflow:** DRAFT → IN_REVIEW → APPROVED (stays in `.rosh/tickets/`) → IMPLEMENTED (moves to `docs/tickets/archive/YYYY/`)

---

## Active Tickets (In .rosh/tickets/)

**MEDIUM Priority:**
- `2025-12-14-security-model.md` - Security model decision (dev/local/package/production) (✅ APPROVED, deferred to backlog)

---

## Archived Tickets

### 2025 (In docs/tickets/archive/2025/)

- `2025-12-14-ai-ticket-review-system.md` - ✅ Ticket workflow infrastructure (IMPLEMENTED 2025-12-14)
- `2025-12-14-toml-support.md` - ✅ TOML support (IMPLEMENTED 2025-12-14)
- `2025-12-14-test-mode.md` - ✅ Test mode for CI/CD (IMPLEMENTED 2025-12-14)
- `2025-12-14-program-metadata.md` - ✅ Program metadata system (IMPLEMENTED 2025-12-14)
- `2025-12-14-toon-format-support.md` - ✅ TOON encoder (IMPLEMENTED 2025-12-14, decoder deferred)
- `2025-12-14-ticket-history-section.md` - ✅ Ticket status visibility (IMPLEMENTED 2025-12-14)

---

## Ticket Statistics

- **Total Active:** 1 (security model - deferred to backlog)
- **Total Archived:** 6
- **Implemented 2025-12-14:** 6

---

## Search Tips

**Find tickets by:**
- Priority: `grep "Priority: CRITICAL" .rosh/tickets/*.md`
- Status: `grep "Status: IN_REVIEW" .rosh/tickets/*.md`
- Author: `grep "Author: Claude" .rosh/tickets/*.md`
- Date: Filename format `YYYY-MM-DD-title.md`

**AI Context Usage:**
When AI needs context about a specific area, reference relevant ticket(s) by filename. This avoids re-reading entire codebase.

---

*This index is manually updated when tickets are created, approved, or archived.*
