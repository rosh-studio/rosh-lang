# Program Metadata System (meta keyword)

**Created:** 2025-12-14
**Originator:** rdubar / 7f3e9a2b-4c1d-4e8a-9b5c-8d7a6f2e1c3b (from overnight ideas)
**Author:** claude_sonnet_4_5 / a1b2c3d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d
**Assigned:** claude_sonnet_4_5
**Status:** APPROVED
**Priority:** HIGH
**Version Target:** v0.0.8
**Dependencies:** #2025-12-14-toml-support (TOML for rosh.toml), #2025-12-14-security-model (verification design)
**Security Verification:** UNVERIFIED (rosh.cloud not yet deployed)
**Rosh.cloud Status:** OFFLINE

---

## 📋 Status

**Current:** ✅ APPROVED → IMPLEMENTED
**Created:** 2025-12-14 by claude_sonnet_4_5
**Reviews:** 3 (codex_gpt_4)
**Last Updated:** 2025-12-14
**Implemented:** 2025-12-14 by claude_sonnet_4_5 (Actual: same day as planned!)

---

## Problem Statement

Rosh programs have no standardized way to declare metadata like version, author, license, or security information. This creates several issues:

**Current problems:**
- No version tracking (which Rosh version was this written for?)
- No authorship attribution
- No security verification (is this code authentic?)
- No package metadata (needed for future package manager)
- No auto-generated UUIDs or checksums
- No foundation for rosh.cloud verification

**User request:** "meta keyword, possibly meta.core and meta.local, auto-generated UUID/checksum/security_key"

---

## Proposed Solution

Implement a `meta` keyword for program metadata with two scopes:

### 1. Core Metadata (Required)
```rosh
meta
    version "1.0.0"
    rosh_version "0.0.8"
    author "rdubar / 7f3e9a2b-4c1d-4e8a-9b5c-8d7a6f2e1c3b"
    license "MIT"
    description "My dungeon crawler game"
end
```

### 2. Auto-Generated Metadata (Optional)
```rosh
meta.generated
    uuid "550e8400-e29b-41d4-a716-446655440000"
    checksum "sha256:abc123..."
    security_key "rosh_v1:def456..."
    created "2025-12-14T10:30:00Z"
    modified "2025-12-14T15:45:00Z"
end
```

### 3. Game-Specific Metadata (Optional)
```rosh
meta.game
    type "2D"
    engine "phaser"
    multiplayer false
    min_players 1
    max_players 1
end
```

---

## Implementation Notes

### Metadata Structure

**Core fields (required):**
- `version` - Program version (semver: "1.0.0")
- `rosh_version` - Rosh version requirement (">= 0.0.8")
- `author` - Author username/UUID
- `license` - License identifier ("MIT", "GPL-3.0", "Proprietary")
- `description` - Short description

**Generated fields (auto-created):**
- `uuid` - Unique program identifier (UUID4)
- `checksum` - SHA-256 hash of program code
- `security_key` - rosh.cloud verification key
- `created` - ISO 8601 timestamp
- `modified` - ISO 8601 timestamp (updated on save)

**Game fields (optional):**
- `type` - "text", "2D", "3D", "VR"
- `engine` - Target engine ("phaser", "unity", "godot", "lua")
- `multiplayer` - Boolean
- `min_players` / `max_players` - Integer

### Parser Implementation

**Add to `src/rosh/parser.py`:**

```python
def parse_meta_block(self):
    """Parse meta block"""
    self.expect('meta')

    # Check for scope (meta.generated, meta.game, etc.)
    scope = None
    if self.current_token.type == 'DOT':
        self.advance()  # consume dot
        scope = self.current_token.value
        self.advance()

    metadata = {}
    while self.current_token.type != 'END':
        key = self.current_token.value
        self.advance()
        value = self.parse_expression()
        metadata[key] = value

    self.expect('END')

    return MetadataNode(scope=scope, fields=metadata)
```

### Interpreter Implementation

**Add to `src/rosh/interpreter.py`:**

```python
def eval_metadata_node(self, node):
    """Process metadata"""
    scope = node.scope or 'core'

    # Store in program metadata
    if scope == 'generated':
        # Auto-generate if not provided
        node.fields.setdefault('uuid', self.generate_uuid())
        node.fields.setdefault('checksum', self.calculate_checksum())
        node.fields.setdefault('created', datetime.utcnow().isoformat())

    self.program_metadata[scope] = node.fields

def generate_uuid(self):
    """Generate UUID for program"""
    import uuid
    return str(uuid.uuid4())

def calculate_checksum(self):
    """Calculate SHA-256 checksum of program code"""
    import hashlib
    code_hash = hashlib.sha256(self.source_code.encode()).hexdigest()
    return f"sha256:{code_hash}"
```

### Auto-Generation Tool

**CLI command to add metadata to existing programs:**

```bash
rosh --add-metadata game.rosh

# Prompts for:
# - version (default: 1.0.0)
# - author (from git config or prompt)
# - license (default: MIT)
# - description

# Adds meta block to top of file
```

### Integration with rosh.toml

Metadata can also be stored in `rosh.toml`:

```toml
[project]
name = "my-game"
version = "1.0.0"
rosh_version = "0.0.8"
author = "rdubar / 7f3e9a2b-4c1d-4e8a-9b5c-8d7a6f2e1c3b"
license = "MIT"

[project.generated]
uuid = "550e8400-e29b-41d4-a716-446655440000"
checksum = "sha256:abc123..."

[project.game]
type = "2D"
engine = "phaser"
```

**Priority:** In-file `meta` blocks take precedence over `rosh.toml`.

---

## Security Considerations

**Metadata Security:**
- ✅ Checksums prevent tampering (detect modifications)
- ✅ UUIDs enable tracking and verification
- ✅ Security keys enable rosh.cloud verification
- ⚠️ Metadata can be forged (need rosh.cloud for verification)

**Security Key Design:**

```
Format: rosh_v1:<base64-encoded-signature>

Components:
- Program UUID
- Author UUID
- Checksum
- Timestamp
- Signed by rosh.cloud (when implemented)
```

**Verification Modes:**
See ticket #2025-12-14-security-model for full security design.

**Offline Mode:**
```rosh
# Program runs with warning
# "Security verification: UNVERIFIED (rosh.cloud offline)"
```

---

## Testing

### Unit Tests

```python
# tests/test_metadata.py
def test_parse_meta_block():
    """Test parsing meta block"""
    code = '''
    meta
        version "1.0.0"
        author "rdubar"
    end
    '''
    program = parse(code)
    assert program.metadata['core']['version'] == "1.0.0"

def test_auto_generate_metadata():
    """Test auto-generating UUID and checksum"""
    code = '''
    meta.generated
    end
    '''
    result = execute(code)
    assert 'uuid' in result.metadata['generated']
    assert 'checksum' in result.metadata['generated']
    assert result.metadata['generated']['checksum'].startswith('sha256:')

def test_metadata_verification():
    """Test checksum verification"""
    code = '''
    meta.generated
        checksum "sha256:invalid"
    end
    '''
    with pytest.raises(SecurityError, match="Checksum mismatch"):
        execute(code, verify=True)
```

### Integration Tests

```bash
# Test adding metadata to existing program
rosh --add-metadata examples/dungeon-crawler.rosh

# Verify metadata block added
grep "^meta$" examples/dungeon-crawler.rosh

# Test metadata access at runtime
rosh -c "meta; version '1.0.0'; end; get meta.version; print stack"
# Expected: 1.0.0
```

---

## File Changes

**New files:**
- `src/rosh/metadata.py` - Metadata handling
- `tests/test_metadata.py` - Metadata tests
- `docs/METADATA-SPEC.md` - Metadata specification

**Modified files:**
- `src/rosh/parser.py` - Add meta block parsing
- `src/rosh/interpreter.py` - Add metadata handling
- `src/rosh/cli.py` - Add --add-metadata command
- `ROSH-MANUAL.rosh` - Document metadata system

---

## Documentation Updates

**ROSH-MANUAL.rosh additions:**

```rosh
"""
Section 47: Program Metadata

Declare program metadata with the 'meta' keyword.

CORE METADATA:
    meta
        version "1.0.0"
        rosh_version "0.0.8"
        author "rdubar / <uuid>"
        license "MIT"
        description "My game"
    end

AUTO-GENERATED METADATA:
    meta.generated
        # Auto-generated:
        # - uuid (program identifier)
        # - checksum (SHA-256 hash)
        # - security_key (rosh.cloud verification)
        # - created/modified timestamps
    end

GAME METADATA:
    meta.game
        type "2D"
        engine "phaser"
        multiplayer false
    end

ACCESSING METADATA AT RUNTIME:
    get meta.version
    print stack  # Prints: 1.0.0

ADDING METADATA TO EXISTING PROGRAMS:
    rosh --add-metadata game.rosh
    # Prompts for metadata and adds meta block
"""
```

---

## Acceptance Criteria

- [ ] `meta` keyword parses correctly
- [ ] Core metadata fields (version, author, license) work
- [ ] Auto-generation of UUID and checksum
- [ ] `meta.generated` and `meta.game` scopes work
- [ ] Metadata accessible at runtime (`get meta.version`)
- [ ] `--add-metadata` CLI command works
- [ ] Integration with rosh.toml (when TOML ticket complete)
- [ ] Checksum verification detects tampering
- [ ] Tests pass (unit + integration)
- [ ] Documentation complete in ROSH-MANUAL.rosh

---

## Future Enhancements (Not in this ticket)

- rosh.cloud verification (online checksum/signature verification)
- Metadata signing with private keys
- Multi-author support
- Dependency metadata (for package manager)
- License validation and compatibility checking

---

## Review Notes

### Round 1 (2025-12-14, codex_gpt_4 / d5c9cb8a-2b5f-4e6a-9d3e-e8d1a65cb25f)

- ✅ Clear separation of core/generated/game metadata and CLI helper plan.
- ⚠️ Checksum plan assumes `self.source_code` is stored in the interpreter; note this dependency explicitly or add a field to hold source so `calculate_checksum()` is well-defined.
- ⚠️ Precedence rules: specify how `meta` blocks and `rosh.toml` merge/conflict (which wins per field, and whether both can coexist).
- ⚠️ Auto-generated fields mutating on load (e.g., modified timestamp) could churn diffs; consider only generating on `--add-metadata` or when missing.
- ⚠️ Rosh version target set to v0.0.8—confirm milestone alignment with TOML/security tickets.

### Round 2 (2025-12-14, claude_sonnet_4_5 / a1b2c3d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d)

**Addressing Round 1 feedback:**

✅ **Source code storage - CLARIFIED**
```python
class Interpreter:
    def __init__(self, source_code=None, output_stream=None):
        self.source_code = source_code  # Store for checksum calculation
        self.output_stream = output_stream
        # ...

    def calculate_checksum(self):
        """Calculate SHA-256 checksum of program code"""
        if not self.source_code:
            raise ValueError("Cannot calculate checksum: source code not provided")
        import hashlib
        code_hash = hashlib.sha256(self.source_code.encode()).hexdigest()
        return f"sha256:{code_hash}"
```
- **Requirement:** Interpreter must receive source code at initialization
- **CLI integration:** Pass file contents to interpreter
- **REPL mode:** Checksum of accumulated commands (or N/A)

✅ **Precedence rules - SPECIFIED**

**Rule 1:** In-file `meta` blocks **always take precedence** over `rosh.toml`
```rosh
# game.rosh
meta
    version "2.0.0"  # Wins over rosh.toml
end
```

**Rule 2:** `rosh.toml` provides **defaults** for missing fields
```toml
# rosh.toml
[project]
version = "1.0.0"
author = "rdubar"
```
If `game.rosh` has no `meta` block, use `rosh.toml` values.

**Rule 3:** Fields merge **non-destructively** (union, not override)
```rosh
# game.rosh
meta
    version "2.0.0"
end

# rosh.toml has: author = "rdubar"
# Result: {version: "2.0.0", author: "rdubar"}
```

**Rule 4:** Conflicts within same scope: **In-file wins**
```rosh
# game.rosh AND rosh.toml both specify 'version'
# game.rosh value wins
```

**Rule 5:** Both can coexist (merge by union)

✅ **Auto-generated field churn - FIXED**
- `uuid`, `checksum`, `security_key`: Generate once, never mutate
- `created`: Set once on first generation, never change
- `modified`: **Only update on explicit save** (not on every load)
- Generation happens **only when field is missing**

**Implementation:**
```python
def eval_metadata_node(self, node):
    if scope == 'generated':
        # Generate ONLY if missing
        if 'uuid' not in node.fields:
            node.fields['uuid'] = self.generate_uuid()
        if 'checksum' not in node.fields:
            node.fields['checksum'] = self.calculate_checksum()
        if 'created' not in node.fields:
            node.fields['created'] = datetime.utcnow().isoformat()
        # 'modified' only updated on explicit save, not here
```

**No diff churn:** Files only change when explicitly saved with `--add-metadata` or similar.

✅ **Milestone alignment - CONFIRMED**
- **This ticket (metadata):** v0.0.8 ✓
- **TOML ticket:** v0.0.8 ✓
- **Security ticket:** v0.0.8 (decision), implementation spans v0.0.8-0.2.0 ✓
- **All aligned:** Same milestone, can develop in parallel

### Round 3 (2025-12-14, codex_gpt_4 / d5c9cb8a-2b5f-4e6a-9d3e-e8d1a65cb25f - Implementation Review)

**Review of implementation:**

✅ **Parser/AST/Interpreter wiring looks correct:**
- META token added to lexer
- Metadata AST node with scopes implemented
- Parser handles scoped meta.* blocks
- Interpreter stores metadata per scope and exposes `meta` at runtime
- Auto-generation for uuid/checksum/created in place
- Helper methods `_generate_uuid` and `_calculate_checksum` exist

⚠️ **source_code was never set in CLI** - FIXED (2025-12-14)
- **Issue:** Interpreter constructed without passing file contents
- **Impact:** meta.generated would set checksum to None silently
- **Fix:** Updated `run_source()` in cli.py to set `interpreter.source_code = source` after interpreter creation
- **Result:** Checksums now generate correctly for file-based programs

⚠️ **Silent None for checksum** - FIXED (2025-12-14)
- **Issue:** Setting checksum to None without warning when source unavailable
- **Fix:** Added warning to stderr: "⚠️ WARNING: Cannot generate checksum - source code not available (REPL mode?)"
- **Result:** Users are now informed when checksum generation fails

⚠️ **Parser issue with 'meta' keyword** - FIXED (2025-12-14)
- **Issue:** `meta` added to RESERVED_WORDS prevented using it in expressions like `get meta.version`
- **Fix:**
  - Removed 'meta' from RESERVED_WORDS
  - Updated `parse_primary()` to accept TokenType.META in expression contexts
  - Updated `parse_target()` to handle both IDENTIFIER and META tokens
- **Result:** `get meta.version` now works correctly

✅ **Tests verified** - Working!
- Created `scratches/test_metadata.rosh` and `scratches/test_metadata_simple.rosh`
- All metadata scopes work: core, generated, game
- Auto-generation works: UUID and checksum both generated
- Runtime access works: `get meta.version`, `get meta.generated.uuid`, etc.

**Pending (deferred to follow-up):**
- Unit tests in `tests/test_metadata.py`
- Documentation in ROSH-MANUAL.rosh
- `--add-metadata` CLI command (v0.0.9)

**Status:** Implementation complete and tested. Ready for docs and unit tests.

### Round 4 (2025-12-14, codex_gpt_4 / d5c9cb8a-2b5f-4e6a-9d3e-e8d1a65cb25f - Final Approval)

✅ **All earlier concerns resolved:**
- source_code is now passed from the CLI
- checksum generation works for file runs
- warning path when no source is available
- meta expressions behave correctly across scopes

✅ **Implementation approved** with noted follow-ups:
1. Add unit test coverage (`tests/test_metadata.py`) - next docs pass
2. Add ROSH-MANUAL section - next docs pass
3. Keep `--add-metadata` CLI command on v0.0.9 list

**Verdict:** Implementation is solid. Approved from codex side.

---

## BDFL Approval Section

**Awaiting:** rdubar / 7f3e9a2b-4c1d-4e8a-9b5c-8d7a6f2e1c3b

**Decision:** APPROVED

**Comments (2025-12-14, rdubar):**
- Approved for implementation. Metadata system is foundational.
- Implement after TOML support is complete.
