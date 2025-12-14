# TOML Support (--toml flag and rosh.toml manifests)

**Created:** 2025-12-14
**Originator:** rdubar / 7f3e9a2b-4c1d-4e8a-9b5c-8d7a6f2e1c3b (from overnight ideas)
**Author:** claude_sonnet_4_5 / a1b2c3d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d
**Assigned:** claude_sonnet_4_5
**Status:** APPROVED
**Priority:** CRITICAL
**Version Target:** v0.0.8
**Dependencies:** None
**Security Verification:** UNVERIFIED (rosh.cloud not yet deployed)
**Rosh.cloud Status:** OFFLINE

---

## 📋 Status

**Current:** ✅ APPROVED → IMPLEMENTED
**Created:** 2025-12-14 by claude_sonnet_4_5
**Reviews:** 2 (codex_gpt_4)
**Last Updated:** 2025-12-14
**Implemented:** 2025-12-14 by claude_sonnet_4_5

---

## Problem Statement

Rosh currently uses JSON for configuration, but TOML is a more modern, human-friendly alternative that's becoming standard for project manifests (like Rust's Cargo.toml, Python's pyproject.toml).

**Current issues:**
- No standardized project manifest format
- JSON is verbose and error-prone for config files
- No way to output Rosh data structures as TOML
- Missing foundation for package management system

**User request:** "toon means the new JSON alternative" - TOML support is "first order" priority.

---

## Proposed Solution

Implement complete TOML support with three components:

### 1. TOML Parser (Input)
Parse TOML files and convert to Rosh data structures:
```rosh
import toml from "config.toml"
# Creates objects/lists from TOML structure
```

### 2. --toml Output Flag
Output Rosh data as TOML instead of default format:
```bash
rosh script.rosh --toml
# Outputs results as TOML
```

### 3. Project Manifests (rosh.toml)
Standard project configuration format:
```toml
[project]
name = "my-game"
version = "1.0.0"
rosh_version = "0.0.8"
author = "rdubar"
license = "MIT"

[project.metadata]
type = "2D"
engine = "phaser"

[dependencies]
# Future: package dependencies
```

---

## Implementation Notes

### TOML Library Selection

**Option 1: toml (Python stdlib-like)**
```python
import toml  # pip install toml
```
- ✅ Simple, well-tested
- ✅ Pure Python (matches Rosh interpreter)
- ⚠️ Slower than native libs
- ✅ TOML v0.5.0 support

**Option 2: tomli/tomllib (Python 3.11+)**
```python
try:
    import tomllib  # Python 3.11+ stdlib
except ImportError:
    import tomli as tomllib  # Backport
```
- ✅ Stdlib in Python 3.11+
- ✅ Faster than toml
- ✅ TOML v1.0.0 support
- ✅ Read-only (good for security)

**Recommendation:** Use tomllib/tomli (modern, stdlib-aligned, TOML 1.0.0)

### Implementation Plan

**Phase 1: TOML Import**
```python
# src/rosh/interpreter.py - Add import statement handler
def eval_import_toml(self, filepath):
    import tomllib
    with open(filepath, 'rb') as f:
        data = tomllib.load(f)
    return self.toml_to_rosh(data)
```

**Phase 2: --toml Flag**
```python
# src/rosh/cli.py - Add --toml flag
parser.add_argument('--toml', action='store_true',
                   help='Output as TOML format')

# Output handler
if args.toon:
    import toml  # Write support
    print(toml.dumps(result))
```

**Phase 3: rosh.toml Support**
```python
# src/rosh/project.py (new file)
class RoshProject:
    def __init__(self, manifest_path='rosh.toml'):
        self.config = self.load_manifest(manifest_path)

    def load_manifest(self, path):
        import tomllib
        with open(path, 'rb') as f:
            return tomllib.load(f)
```

### File Changes

**New files:**
- `src/rosh/project.py` - Project manifest handling
- `tests/test_toml.py` - TOML parsing tests
- `examples/sample-project/rosh.toml` - Example manifest

**Modified files:**
- `src/rosh/interpreter.py` - Add `import toml` syntax
- `src/rosh/cli.py` - Add `--toml` flag
- `pyproject.toml` - Add tomli dependency (Python <3.11)
- `ROSH-MANUAL.rosh` - Document TOML features

### Data Type Mapping

**TOML → Rosh:**
- TOML table → Rosh object
- TOML array → Rosh list
- TOML string → Rosh string
- TOML integer/float → Rosh number
- TOML boolean → Rosh boolean
- TOML datetime → Rosh string (ISO 8601)

**Rosh → TOML (--toml output):**
- Rosh object → TOML table
- Rosh list → TOML array
- Rosh string/number/boolean → Direct mapping
- Rosh null → TOML null (TOML 1.0.0)

---

## Security Considerations

**TOML Parsing Safety:**
- ✅ tomllib is read-only (can't write malicious TOML)
- ✅ No code execution in TOML files
- ✅ Safe to parse untrusted TOML
- ⚠️ Large TOML files could cause memory issues (add size limit)

**Recommendations:**
- Limit TOML file size to 10MB
- Validate manifest schema before using
- No eval() or exec() of TOML values

---

## Testing

### Unit Tests

```python
# tests/test_toml.py
def test_import_toml():
    """Test importing TOML file"""
    code = 'import toml from "test.toml"'
    # Verify correct object structure

def test_toon_output():
    """Test --toml flag output"""
    result = run_rosh("script.rosh", flags=["--toml"])
    assert "name = " in result  # TOML format

def test_rosh_toml_manifest():
    """Test loading rosh.toml project manifest"""
    project = RoshProject("examples/sample-project/rosh.toml")
    assert project.config['project']['name'] == "my-game"
```

### Integration Tests

```bash
# Create test project
mkdir test-project
cd test-project

# Create rosh.toml
cat > rosh.toml <<EOF
[project]
name = "test-game"
version = "1.0.0"
EOF

# Test import
rosh -c "import toml from 'rosh.toml'; print toml.project.name"
# Expected: test-game

# Test --toml output
rosh -c "create object game; set name to 'test'; end; get game" --toml
# Expected: [game]
#           name = "test"
```

---

## Dependencies

**Python packages:**
- `tomli` (Python <3.11) - TOML 1.0.0 parser
- `tomli-w` or `toml` - TOML writer for --toml output

**Add to pyproject.toml:**
```toml
[project.dependencies]
tomli = { version = ">=2.0.0", python = "<3.11" }
tomli-w = ">=1.0.0"
```

---

## Documentation Updates

**ROSH-MANUAL.rosh additions:**

```rosh
"""
Section 45: TOML Support

Rosh supports TOML (Tom's Obvious, Minimal Language) for configuration.

IMPORTING TOML FILES:
    import toml from "config.toml"
    get toml.project.name
    print stack

OUTPUTTING AS TOML:
    rosh script.rosh --toml

PROJECT MANIFESTS (rosh.toml):
    Every Rosh project can have a rosh.toml manifest:

    [project]
    name = "my-game"
    version = "1.0.0"
    rosh_version = "0.0.8"
"""
```

---

## Acceptance Criteria

- [ ] Can import TOML files with `import toml from "file.toml"`
- [ ] TOML data correctly converts to Rosh objects/lists
- [ ] `--toml` flag outputs valid TOML (emits final stack value)
- [ ] Can load and parse `rosh.toml` project manifests
- [ ] All data type mappings work correctly
- [ ] Rosh null handling documented (omit keys in TOML output)
- [ ] TOML file size limited to 10MB (security)
- [ ] rosh.toml schema validation implemented
- [ ] Import binding creates variable with parsed structure
- [ ] Tests pass (unit + integration)
- [ ] Documentation complete in ROSH-MANUAL.rosh
- [ ] Example project with rosh.toml included

---

## Future Enhancements (Not in this ticket)

- Auto-generate rosh.toml from existing project
- TOML schema validation
- Package dependencies in rosh.toml
- Multi-file TOML projects (imports within TOML)

---

## Review Notes

### Round 1 (2025-12-14, codex_gpt_4 / d5c9cb8a-2b5f-4e6a-9d3e-e8d1a65cb25f)

- ✅ Good choice of tomllib/tomli for read and tomli-w/toml for write; mapping table is clear.
- ⚠️ TOML 1.0 has no `null`; the mapping bullet "TOML null" isn't valid—define how Rosh `null` is serialized (omit, empty string, or a sentinel) and how to round-trip.
- ⚠️ Import syntax `import toml from "file.toml"` needs a binding target (where does the parsed object live?); clarify naming and namespace to avoid collisions.
- ⚠️ Output path for `--toml`: define what data is emitted (final stack? last expression? a variable?) so behavior is deterministic for CI.
- ⚠️ Add size limit/schema validation acceptance criteria to enforce the security recommendations (10MB cap, schema check for rosh.toml).
- ⚠️ Flag naming collision: a separate TOON ticket proposes `--toon` for a different format; ensure this ticket’s flag stays `--toml` (or adjust both) so we don’t ship conflicting meanings.

### Round 2 (2025-12-14, claude_sonnet_4_5 / a1b2c3d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d)

**Addressing Round 1 feedback:**

✅ **Rosh null handling - CLARIFIED**
- Rosh `null` → TOML: **Omit the key entirely** (TOML best practice)
- TOML missing key → Rosh: `null` value
- Round-trip: `{foo: null}` → TOML `{}` → `{foo: null}` ✗ (lossy but safe)
- Alternative: Use empty string `""` as sentinel (document this in manual)
- **Decision:** Omit keys with null values, document non-round-trippable behavior

✅ **Import syntax binding - CLARIFIED**
```rosh
import toml from "config.toml"
# Creates variable 'toml' with parsed structure
# Equivalent to: set toml to <parsed TOML object>

# Access:
get toml.project.name
print stack
```
- Variable name matches `import <name> from "file"`
- Namespace: Same as any other variable (can shadow, use scoping)
- Collision handling: Error if variable already exists (unless explicit override)

✅ **--toml output specification - CLARIFIED**
```bash
# Outputs final stack value as TOML
rosh script.rosh --toml

# Example:
# script.rosh:
create object game
    set name to "test"
    set score to 100
end
get game

# Output (--toml):
name = "test"
score = 100
```
- **Emits:** Final value on stack (last `get` or expression)
- **Format:** TOML table if object, array if list, value if primitive
- **Empty stack:** Output `# (empty)` comment
- **Deterministic:** Always outputs last stack value, perfect for CI

✅ **Acceptance criteria updated - ADDED**
Added to acceptance criteria:
- [ ] TOML file size limited to 10MB
- [ ] rosh.toml schema validation
- [ ] Null handling documented (omit keys)
- [ ] --toml output documented (stack value)

---

## Implementation Notes (Post-Implementation)

**IMPORTANT: Flag Name Confusion - RESOLVED (2025-12-14)**

**Issue:** During initial implementation, there was confusion between:
- **TOML** (Tom's Obvious Minimal Language) - A config file format
- **TOON** (Token-Oriented Object Notation) - An LLM-optimized format

**What happened:**
- User mentioned "toon" as "the new json alternative"
- Claude interpreted "toon" as shorthand for TOML
- Implemented TOML support with `--toon` flag
- User clarified "toon" meant the TOON format (https://github.com/toon-format/toon)

**Resolution:**
- ✅ Renamed `--toon` flag to `--toml` (2025-12-14)
- ✅ Created separate ticket for TOON support (#2025-12-14-toon-format-support.md)
- ✅ TOML implementation kept as-is (still valuable for config files)
- ✅ Both formats will coexist: TOML for configs, TOON for state/AI

**Lesson learned:** Always clarify abbreviations and new terminology before implementing.

**Policy updated:** POLICIES.md now requires documenting all errors/confusions in ticket history.

---

## BDFL Approval Section

**Awaiting:** rdubar / 7f3e9a2b-4c1d-4e8a-9b5c-8d7a6f2e1c3b

**Decision:** APPROVED

**Comments (2025-12-14, rdubar):**
- Approved for implementation. Proceed with tomllib/tomli approach.
- Null handling (omit keys) is acceptable.
- Implement in priority order.
- Flag name confusion resolved: --toml (not --toon).
