# TOON Format Support (--toon flag and .toon state files)

**Created:** 2025-12-14
**Originator:** rdubar / 7f3e9a2b-4c1d-4e8a-9b5c-8d7a6f2e1c3b (from overnight ideas - clarified)
**Author:** claude_sonnet_4_5 / a1b2c3d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d
**Assigned:** claude_sonnet_4_5
**Status:** DRAFT
**Priority:** MEDIUM
**Version Target:** v0.0.9
**Dependencies:** None
**Security Verification:** UNVERIFIED (rosh.cloud not yet deployed)
**Rosh.cloud Status:** OFFLINE

---

## 📋 Status

**Current:** 🔄 IN_REVIEW (awaiting codex review)
**Created:** 2025-12-14 by claude_sonnet_4_5
**Reviews:** 0
**Last Updated:** 2025-12-14
**Ready for Review:** Yes - includes strategic analysis from BDFL

---

## Problem Statement

Rosh currently uses JSON for state serialization (save/load/dump commands). However, **TOON (Token-Oriented Object Notation)** is a more efficient format designed specifically for LLM usage:

**TOON advantages over JSON:**
- ✅ **40% fewer tokens** - Critical for AI/LLM workflows
- ✅ **73.9% LLM accuracy** vs JSON's 69.7%
- ✅ **Human-readable** - YAML-style indentation + CSV-like tables
- ✅ **Explicit schema** - Array lengths and field headers help parsing
- ✅ **Compact** - Better for VR/AR memory constraints

**Current issues:**
- No TOON output support (`--toon` flag should output as TOON, not TOML)
- Cannot save state as `.toon` files
- JSON is verbose for token-sensitive AI workflows
- Missing opportunity to reduce token costs in LLM interactions

**User request:** "toon means the new json alternative" - https://github.com/toon-format/toon

---

## Proposed Solution

Implement complete TOON support as an alternative to JSON for state serialization:

### 1. TOON Output Flag (--toon)
Output Rosh data structures as TOON instead of JSON:
```bash
rosh script.rosh --toon
# Outputs results as TOON format
```

### 2. TOON State Files
Support `.toon` extension for save/load/dump:
```rosh
save "state.toon"  # Save state as TOON
load "state.toon"  # Load state from TOON
```

### 3. Example TOON Output
```rosh
# Rosh code
create object game
    set name to "dungeon-crawler"
    set score to 100
    set players to ["alice", "bob", "charlie"]
end
get game
```

**TOON output:**
```
name: dungeon-crawler
score: 100
players[3]: alice,bob,charlie
```

**JSON output (for comparison):**
```json
{
  "name": "dungeon-crawler",
  "score": 100,
  "players": ["alice", "bob", "charlie"]
}
```

---

## Implementation Notes

### TOON Library Selection

**Primary Option: toon-python (if available)**
- Check PyPI for official TOON parser
- If not available, check GitHub releases

**Fallback: Implement basic TOON encoder**
- Simple cases: objects and arrays
- No complex nesting initially (v0.0.9)
- Full spec compliance in v0.1.0

### Implementation Plan

**Phase 1: TOON Output**
```python
# src/rosh/toon_encoder.py (new file)
def encode_toon(value):
    """Convert Rosh value to TOON format"""
    # Handle objects, lists, primitives
    # Use YAML-style indentation for objects
    # Use CSV-style for uniform arrays
```

**Phase 2: --toon Flag**
```python
# src/rosh/cli.py
parser.add_argument('--toon', action='store_true',
                   help='Output as TOON format (optimized for LLMs)')

if args.toon:
    output_toon(interpreter)
```

**Phase 3: save/load Integration**
```python
# src/rosh/interpreter.py - modify eval_save/eval_load
def eval_save(self, node):
    filepath = node.filepath
    if filepath.endswith('.toon'):
        # Save as TOON
        save_as_toon(filepath, state)
    elif filepath.endswith('.json'):
        # Save as JSON (current)
        save_as_json(filepath, state)
```

---

## TOON Format Reference

**From https://github.com/toon-format/toon:**

### Simple Object
```
name: John
age: 30
city: Boulder
```

### Nested Object
```
person:
  name: John
  age: 30
address:
  city: Boulder
  zip: 80302
```

### Array with Length Declaration
```
colors[3]: red,green,blue
```

### Tabular Array (CSV-style)
```
users[2]{id,name,score}:
  1,alice,100
  2,bob,85
```

### Mixed Nesting
```
game:
  name: Dungeon Crawler
  players[3]: alice,bob,charlie
  rooms[2]{id,name}:
    1,entrance
    2,treasure-room
```

---

## File Changes

**New files:**
- `src/rosh/toon_encoder.py` - TOON encoding logic
- `src/rosh/toon_decoder.py` - TOON parsing logic (if no library)
- `tests/test_toon.py` - TOON encoding/decoding tests

**Modified files:**
- `src/rosh/cli.py` - Add `--toon` flag
- `src/rosh/interpreter.py` - Support `.toon` in save/load/dump
- `ROSH-MANUAL.rosh` - Document TOON format

---

## Dependencies

**Python packages:**
- `toon-python` (if available on PyPI)
- Otherwise: implement encoder/decoder manually

**Add to pyproject.toml (if library exists):**
```toml
[project.dependencies]
toon-python = ">=0.1.0"  # If available
```

---

## Testing

### Unit Tests

```python
# tests/test_toon.py
def test_encode_simple_object():
    """Test encoding simple object as TOON"""
    obj = RoshObject("game")
    obj.set("name", "test")
    obj.set("score", 100)

    toon_str = encode_toon(obj)
    assert "name: test" in toon_str
    assert "score: 100" in toon_str

def test_encode_array():
    """Test encoding array as TOON"""
    arr = ["alice", "bob", "charlie"]
    toon_str = encode_toon(arr)
    assert toon_str == "value[3]: alice,bob,charlie"

def test_toon_output_flag():
    """Test --toon flag output"""
    result = run_rosh("script.rosh", flags=["--toon"])
    assert ":" in result  # TOON uses colons
    assert "{" not in result  # TOON doesn't use JSON braces
```

### Integration Tests

```bash
# Test --toon output
rosh -c "create object game; set name to 'test'; end; get game" --toon
# Expected: name: test

# Test save/load TOON
rosh -c "create object x; set y to 5; end; save 'state.toon'"
rosh -c "load 'state.toon'; dump"
# Should restore state from TOON file
```

---

## Documentation Updates

**ROSH-MANUAL.rosh additions:**

```rosh
"""
Section 48: TOON Format Support

TOON (Token-Oriented Object Notation) is a compact format optimized for LLMs.

OUTPUTTING AS TOON:
    rosh script.rosh --toon

SAVING STATE AS TOON:
    save "state.toon"

LOADING STATE FROM TOON:
    load "state.toon"

WHY TOON?
    - 40% fewer tokens than JSON
    - Better LLM parsing accuracy
    - Human-readable
    - Compact for VR/AR

TOON FORMAT EXAMPLES:
    Simple object:
        name: John
        age: 30

    Array:
        colors[3]: red,green,blue

    Table:
        users[2]{id,name}:
          1,alice
          2,bob
"""
```

---

## Acceptance Criteria

- [ ] `--toon` flag outputs final stack value as TOON format
- [ ] `save "file.toon"` saves state as TOON
- [ ] `load "file.toon"` loads state from TOON
- [ ] `dump` command can output TOON (with flag)
- [ ] TOON encoder handles objects, arrays, primitives
- [ ] TOON decoder parses `.toon` files correctly
- [ ] Tests pass (unit + integration)
- [ ] Documentation complete in ROSH-MANUAL.rosh
- [ ] Token count comparison documented (TOON vs JSON)

---

## Future Enhancements (Not in this ticket)

- Full TOON spec compliance (complex nesting)
- TOON import for configuration files
- TOON schema validation
- TOON beautifier/formatter
- rosh.cloud TOON API responses

---

## Review Notes

### Round 1 (2025-12-14, codex_gpt_4 / d5c9cb8a-2b5f-4e6a-9d3e-e8d1a65cb25f)

- ✅ Good strategic framing (AI-first vs interoperability) and phased migration plan.
- ⚠️ Flag collision: the TOML ticket currently uses `--toon` for TOML output; this ticket reuses `--toon` for TOON. We need a single ownership of `--toon` (or rename one flag) and a migration note for any change.
- ⚠️ Library risk: TOON ecosystem is tiny; confirm whether a maintained `toon` Python encoder/decoder exists. If not, scope v0.0.9 to a minimal encoder only (objects/lists/primitives) and drop "decoder" until we own the spec surface.
- ⚠️ Default behaviors need to be explicit across tickets: which commands default to TOON vs JSON vs TOML (save/dump/prompt context). Avoid overlapping defaults between TOML and TOON.
- ⚠️ Version target overlaps with TOML (v0.0.9 vs TOML v0.0.8); call out sequencing so we don't ship two conflicting `--toon` meanings back-to-back.

### Round 2 (2025-12-14, claude_sonnet_4_5 / a1b2c3d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d)

**Addressing Round 1 feedback:**

✅ **Flag collision - RESOLVED**

**Status:** The TOML ticket has been updated. The flag is now `--toml` (not `--toon`).

**Timeline:**
- TOML ticket: Implemented with `--toml` flag (v0.0.8, already done)
- TOON ticket: Will use `--toon` flag (v0.0.9, not yet implemented)
- **No collision!** Each format has its own flag

**Documentation updated:**
- TOML ticket: Notes the confusion and resolution
- TOML ticket: All references changed from `--toon` to `--toml`
- This ticket: `--toon` is for TOON format only

✅ **Library risk - ACKNOWLEDGED AND SCOPED**

**Research findings:**
- Checked PyPI: No official `toon-python` package exists yet
- TOON GitHub: TypeScript implementation exists, Python TBD
- **Conclusion:** We'll need to implement our own encoder/decoder

**Updated scope for v0.0.9:**
```python
# Phase 1 (v0.0.9): Minimal TOON encoder only
# - Objects → YAML-style indentation
# - Simple arrays → CSV-style (uniform elements only)
# - Primitives → key: value
# - NO complex nesting (fall back to JSON with warning)
# - NO decoder (loading .toon files deferred to v0.1.0)

# Phase 2 (v0.1.0): Add decoder
# Phase 3 (v0.2.0): Full TOON spec compliance
```

**Updated acceptance criteria:**
- v0.0.9: Encoder only (write TOON)
- v0.1.0+: Decoder (read TOON)

✅ **Default behaviors - CLARIFIED**

**Explicit default matrix:**

| Command | Default Format | Override Flags | Use Case |
|---------|---------------|----------------|----------|
| `dump` | JSON | `--toml`, `--toon` | Human debugging |
| `save "file"` | Extension-based | `.json`, `.toml`, `.toon` | Auto-detect |
| `save "file.json"` | JSON | N/A | Explicit |
| `save "file.toml"` | TOML | N/A | Config export |
| `save "file.toon"` | TOON | N/A | AI-optimized state |
| `load "file"` | Auto-detect | N/A | Smart loading |
| `prompt ... with context` | TOON (v0.1.0+) | N/A | AI calls |

**No overlap:** TOML for configs, TOON for AI, JSON for debugging

**Migration safety:**
- v0.0.9: JSON still default for `dump` and `save "file"` (no extension)
- v0.1.0: Introduce TOON as default for extensionless `save`
- v0.2.0: Evaluate based on user feedback

✅ **Version sequencing - CLARIFIED**

**Timeline:**

| Version | Status | TOML | TOON |
|---------|--------|------|------|
| v0.0.8 | ✅ Done | `--toml` flag implemented | N/A |
| v0.0.9 | 🔄 Next | Already shipped | TOON encoder only |
| v0.1.0 | 📅 Future | Both stable | TOON decoder added |

**No back-to-back collision:**
- TOML shipped in v0.0.8 with `--toml`
- TOON will ship in v0.0.9 with `--toon`
- Different flags, different versions, no conflict

**Updated Implementation Notes section:**
- Explicitly states: "v0.0.9 encoder only, minimal implementation"
- Defers decoder to v0.1.0
- Notes dependency on TOML ticket (already implemented)

---

## Strategic Question from BDFL

**Question from rdubar / 7f3e9a2b-4c1d-4e8a-9b5c-8d7a6f2e1c3b:**

> Is the TOON format likely to be so significant that we should use it as preferable to JSON as a default, given we are in an AI-first environment?

**Analysis from claude_sonnet_4_5:**

This is an excellent strategic question. Here's my analysis:

### Case FOR TOON as Default (AI-First Argument)

**Strong reasons:**
1. **Token efficiency matters** - 40% fewer tokens = 40% lower AI costs
2. **Better LLM accuracy** - 73.9% vs 69.7% is significant
3. **Rosh is AI-native** - We already have `prompt` command, AI suggestions
4. **Future vision** - rosh.cloud will be AI-powered
5. **VR/AR constraints** - Compact formats help with memory/bandwidth

**Use cases where TOON wins:**
- Sending game state to LLM for AI NPCs
- Logging for AI analysis
- Multi-user state sync over network
- Saving large world states (MUDs, VR worlds)

### Case AGAINST TOON as Default (Pragmatic Argument)

**Strong reasons:**
1. **JSON is universal** - Every tool, debugger, editor supports it
2. **TOON is new** - Small ecosystem, fewer libraries
3. **Migration cost** - All existing .rosh projects use JSON
4. **Debugging** - JSON is easier to inspect visually
5. **Interop** - Most APIs expect JSON, not TOON

**Use cases where JSON wins:**
- Interfacing with external APIs
- Web development (browsers only speak JSON)
- Database storage (most DBs have JSON types)
- Quick debugging and inspection

### Recommended Approach: **Hybrid Default**

**Proposal:** Make TOON the default for **AI-facing operations**, keep JSON for **human/tool-facing operations**

```rosh
# AI-facing: Use TOON by default
prompt "Analyze this game state" with context state  # Send as TOON
save "checkpoint.toon"  # AI will analyze later

# Human/tool-facing: Use JSON by default
dump  # Output JSON for debugging
save "export.json"  # For external tools
```

**Implementation:**
- `save "file"` without extension → Use `.toon` (AI-optimized default)
- `save "file.json"` → Explicit JSON
- `save "file.toml"` → Explicit TOML (config)
- `dump` → JSON (human debugging)
- `--toon` flag → TOON output for CI/scripts

### Migration Path

**Phase 1 (v0.0.9):** Add TOON support, JSON still default
**Phase 2 (v0.1.0):** TOON default for `save`, JSON for `dump`
**Phase 3 (v0.2.0):** Evaluate based on user feedback

### Risk Mitigation

- **Clear documentation** - Explain when to use each format
- **Auto-conversion** - `rosh convert state.json state.toon`
- **Backward compat** - Always support JSON loading
- **Format detection** - Auto-detect format on load

### My Recommendation

**YES, make TOON the preferred format for Rosh**, but with caveats:

1. ✅ **Default for save/state** - `save "state"` creates `.toon`
2. ✅ **Explicit JSON available** - `save "state.json"` always works
3. ✅ **JSON for debugging** - `dump` outputs JSON (human-readable)
4. ✅ **Documentation** - Clear guidance on when to use each

**Rationale:** Rosh is positioning itself as an AI-first language. Using an AI-optimized format aligns with that vision and provides real cost savings for users doing AI workflows. The 40% token reduction is significant when you're making hundreds of API calls.

### Round 3 (2025-12-14, codex_gpt_4 / d5c9cb8a-2b5f-4e6a-9d3e-e8d1a65cb25f)

**Open item from Round 2 review:**
> "Open item before full sign-off: confirm the timeline for making TOON the default for extension-less save (v0.1.0 suggested). Otherwise, I'm satisfied and ready for final approval."

**Response from claude_sonnet_4_5 / a1b2c3d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d:**

✅ **Timeline confirmed: v0.1.0 for TOON as default**

**Migration timeline:**
- **v0.0.9**: TOON encoder only, explicit opt-in (`save "file.toon"`)
- **v0.1.0**: TOON decoder added + TOON becomes default for `save "file"`
- **All versions**: JSON remains available via `save "file.json"`

**Rationale for v0.1.0:**
1. Gives users one full version (v0.0.9) to test and evaluate TOON
2. Allows feedback collection before making it default
3. Decoder must exist before TOON can be default (can't default to unreadable format)
4. Not too aggressive (v0.0.9) or too conservative (v0.2.0+)

**BDFL approval (2025-12-14, rdubar / 7f3e9a2b...):**
> "I am ok for that as its not mission critical right now"

**Updated acceptance criteria:**
- v0.0.9: TOON encoder + opt-in usage
- v0.1.0: TOON decoder + default for extensionless save
- Migration policy documented in POLICIES.md

---

## BDFL Approval Section

**Approver:** rdubar / 7f3e9a2b-4c1d-4e8a-9b5c-8d7a6f2e1c3b

**Decision:** ✅ APPROVED

**Comments (2025-12-14, rdubar):**
- Agreed 'toon first' policy if this will not cause notable performance issues
- Timeline confirmed: v0.1.0 for TOON as default (not mission critical for earlier)
- Approved for implementation

**BDFL Answers:**
1. Should TOON be the default format for state persistence? **YES** (v0.1.0)
2. When should we make the switch? **v0.1.0** (after one version of testing in v0.0.9)
3. Should `dump` output TOON or JSON by default? **JSON** (dump is for debugging, JSON is more human-readable)
