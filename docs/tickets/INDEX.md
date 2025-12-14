# Ticket Index

**Last Updated:** 2025-12-14
**Purpose:** Quick reference for all development tickets (active and archived)
**Workflow:** DRAFT → IN_REVIEW → APPROVED (stays in `.rosh/tickets/`) → IMPLEMENTED (moves to `docs/tickets/archive/YYYY/`)

---

## Active Tickets (In .rosh/tickets/)

**CRITICAL Priority:**
- `2025-12-14-toml-support.md` - TOML support (--toml flag, rosh.toml manifests) (✅ APPROVED → IMPLEMENTED)

**HIGH Priority:**
- `2025-12-14-test-mode.md` - Test mode for CI/CD (mock input/stop) (✅ APPROVED → IMPLEMENTED)
- `2025-12-14-program-metadata.md` - Program metadata system (meta keyword) (✅ APPROVED → IMPLEMENTED)

**MEDIUM Priority:**
- `2025-12-14-toon-format-support.md` - TOON format support (--toon flag, .toon state files) (🔄 IN_REVIEW)
- `2025-12-14-security-model.md` - Security model decision (dev/local/package/production) (✅ APPROVED)

**LOW Priority:**
- `2025-12-14-ticket-history-section.md` - Ticket status visibility (✅ APPROVED → IMPLEMENTED)

---

## Archived Tickets

### 2025 (In docs/tickets/archive/2025/)

- `2025-12-14-ai-ticket-review-system.md` - ✅ Ticket workflow infrastructure (IMPLEMENTED 2025-12-14)

---

## Ticket Statistics

- **Total Active:** 6
- **Total Archived:** 1
- **In Review:** 1
- **Approved:** 1
- **Approved → Implemented:** 4

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
