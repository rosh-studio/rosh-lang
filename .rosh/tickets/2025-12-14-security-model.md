# Security Model Decision (Fail-Safe vs Fail-Secure)

**Created:** 2025-12-14
**Originator:** rdubar / 7f3e9a2b-4c1d-4e8a-9b5c-8d7a6f2e1c3b (from overnight ideas)
**Author:** claude_sonnet_4_5 / a1b2c3d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d
**Assigned:** claude_sonnet_4_5
**Status:** APPROVED
**Priority:** MEDIUM (Research/Decision)
**Version Target:** v0.0.8
**Dependencies:** #2025-12-14-program-metadata (provides verification data)
**Security Verification:** UNVERIFIED (rosh.cloud not yet deployed)
**Rosh.cloud Status:** OFFLINE

---

## 📋 Status

**Current:** ✅ APPROVED
**Created:** 2025-12-14 by claude_sonnet_4_5
**Reviews:** 2 (codex_gpt_4)
**Last Updated:** 2025-12-14

---

## Problem Statement

When Rosh programs include metadata with checksums, UUIDs, and security keys, we need to decide: what happens when verification fails or is unavailable?

**Two competing philosophies:**

1. **Fail-Safe:** Warn user, allow execution (convenience, offline-first)
2. **Fail-Secure:** Refuse execution, require verification (security-first)

**User request:** "Discuss both options and make a recommendation"

This is a **decision ticket** - research both approaches, analyze trade-offs, and recommend one for implementation.

---

## Background: Security Models

### Fail-Safe (Permissive)

**Philosophy:** Availability over security. If verification fails, warn but continue.

**Example scenario:**
```bash
$ rosh game.rosh
⚠️  WARNING: Security verification failed
⚠️  Checksum mismatch (expected sha256:abc..., got sha256:xyz...)
⚠️  This program may have been tampered with
⚠️  Continue anyway? [y/N]: y
Running program...
```

**Pros:**
- ✅ Works offline (no network required)
- ✅ User convenience (doesn't block legitimate use)
- ✅ Gradual adoption (warnings encourage fixing, don't force)
- ✅ Developer-friendly (edit code, test immediately)

**Cons:**
- ❌ Users might ignore warnings
- ❌ Malicious code can still run
- ❌ Weakens security guarantees
- ❌ False sense of security

### Fail-Secure (Restrictive)

**Philosophy:** Security over availability. If verification fails, refuse execution.

**Example scenario:**
```bash
$ rosh game.rosh
❌ ERROR: Security verification failed
❌ Checksum mismatch (expected sha256:abc..., got sha256:xyz...)
❌ Refusing to execute potentially tampered program
❌ Use --skip-verification to override (not recommended)
Program execution blocked.
```

**Pros:**
- ✅ Strong security guarantees
- ✅ Forces fixing security issues
- ✅ Prevents malicious code execution
- ✅ Clear security posture

**Cons:**
- ❌ Breaks offline workflows
- ❌ Developer friction (need to update checksums constantly)
- ❌ User frustration (legitimate edits blocked)
- ❌ Requires network for verification

---

## Analysis: Rosh-Specific Considerations

### Current State (v0.0.8)

**Rosh is currently:**
- Single-user, local development
- No sandboxing
- No package manager
- No remote code execution
- No rosh.cloud verification yet

**Threat model:**
- Low: Local development, trusted code
- Medium: Sharing .rosh files with others
- High: Future package manager, remote code

### Future State (v0.2.0+)

**Rosh will become:**
- Multi-user with rosh.cloud
- Package manager with dependencies
- VR deployments (Quest, Vision Pro)
- Enterprise licensing

**Threat model escalates:**
- Supply chain attacks (malicious packages)
- Code injection (tampered files)
- Identity spoofing (fake authors)

---

## Hybrid Approach: Context-Aware Security

**Recommendation:** Use different security models based on context.

### Mode 1: Development Mode (Fail-Safe)

**When:**
- Local development (no rosh.toml or explicitly `--dev`)
- Interactive testing
- Rapid iteration

**Behavior:**
```bash
$ rosh game.rosh
⚠️  No metadata found - running in DEV mode
⚠️  Add metadata with: rosh --add-metadata game.rosh
Running program...
```

**Security:** Warnings only, no blocking

### Mode 2: Local Execution (Fail-Safe with Prompts)

**When:**
- Program has metadata
- Running locally (not from package)
- Verification fails or offline

**Behavior:**
```bash
$ rosh game.rosh
⚠️  WARNING: Checksum verification failed
⚠️  Expected: sha256:abc123...
⚠️  Got:      sha256:xyz789...
⚠️  Program may have been modified since last verification
Continue? [y/N]:
```

**Security:** User decision required for untrusted code

### Mode 3: Package Mode (Fail-Secure)

**When:**
- Installing from package manager
- Running downloaded code
- Multi-user environments

**Behavior:**
```bash
$ rosh install some-package
❌ ERROR: Package signature verification failed
❌ Package 'some-package' failed cryptographic verification
❌ This could indicate tampering or corruption
Installation blocked. Contact package author.
```

**Security:** No execution without verified signature

### Mode 4: Production/Enterprise (Fail-Secure)

**When:**
- VR deployments
- Enterprise licensing
- `--production` flag

**Behavior:**
```bash
$ rosh game.rosh --production
❌ ERROR: Production mode requires full security verification
❌ Missing rosh.cloud verification
❌ Use --verify or deploy to rosh.cloud
Program execution blocked.
```

**Security:** Full verification required, no exceptions

---

## Recommended Implementation

### Phase 1: v0.0.8 (Current)
**Model:** Fail-Safe (Development focus)
- Metadata is optional
- Checksums generate warnings only
- No blocking execution
- Focus: Getting metadata system adopted

### Phase 2: v0.2.0 (Package Manager)
**Model:** Hybrid (Context-aware)
- Development: Fail-safe
- Local: Fail-safe with prompts
- Packages: Fail-secure
- Focus: Security without breaking workflows

### Phase 3: v0.3.0+ (Multi-user/Enterprise)
**Model:** Configurable (Policy-based)
- System administrators set policy
- Default: Fail-secure for remote code
- Override: `--security-mode=[strict|relaxed|custom]`
- Focus: Enterprise security requirements

---

## Warning Behavior and UX Clarification

**IMPORTANT:** Security warnings should only appear when necessary, not for simple operations.

### When Warnings SHOULD Appear

✅ **During imports with metadata:**
```bash
$ rosh game.rosh
# Imports module with checksum verification
⚠️  WARNING: Module 'ai-lib.rosh' checksum verification failed
⚠️  Continue? [y/N]:
```

✅ **When verification fails:**
```bash
$ rosh game.rosh
⚠️  WARNING: Checksum verification failed
⚠️  Expected: sha256:abc123...
⚠️  Got:      sha256:xyz789...
Continue? [y/N]:
```

✅ **When installing packages:**
```bash
$ rosh install untrusted-package
⚠️  WARNING: Package signature not verified
⚠️  This package has not been verified by rosh.cloud
Continue? [y/N]:
```

✅ **First-time metadata suggestion (once per session):**
```bash
$ rosh game.rosh  # No metadata, first run
⚠️  No metadata found - running in DEV mode
⚠️  Add metadata with: rosh --add-metadata game.rosh
[Program runs normally, no further warnings]
```

### When Warnings SHOULD NOT Appear

❌ **Simple operations (no metadata, no imports):**
```bash
$ rosh -c "print 'hello'"
hello
# No warnings - simple operation, no security concerns
```

❌ **Repeated runs of same file:**
```bash
$ rosh game.rosh  # No metadata, already warned once this session
[Program runs silently, no repeated warnings]
```

❌ **Test mode:**
```bash
$ rosh game.rosh --test input.txt
# Test mode = dev mode = no warnings
```

❌ **Files explicitly in dev mode:**
```bash
$ rosh game.rosh --dev
# Explicit dev mode = user knows what they're doing
```

### Warning Suppression Rules

**Per-Session Tracking:**
- Warn about missing metadata once per session per file
- Don't repeat warnings for the same file in same run
- Only re-warn if file contents change

**Context-Aware:**
- No warnings for one-liner scripts (`rosh -c "..."`)
- No warnings in test mode (`--test`)
- No warnings if explicitly `--dev` or `--skip-verification`

**User Control:**
```bash
# Suppress all warnings
rosh game.rosh --quiet

# Show all warnings (verbose)
rosh game.rosh --verbose

# Skip verification entirely (dev)
rosh game.rosh --skip-verification
```

**Summary:** Warnings are security-relevant notifications, not general advisories. Only show when there's an actual security decision to be made or risk to be aware of.

---

## Security Verification Workflow

### Offline Verification (Always Available)

```python
def verify_checksum(program_code, metadata):
    """Verify checksum matches program code"""
    import hashlib
    actual = hashlib.sha256(program_code.encode()).hexdigest()
    expected = metadata.get('checksum', '').replace('sha256:', '')
    return actual == expected
```

**Pros:** Works offline, fast, detects tampering
**Cons:** Doesn't verify author identity

### Online Verification (When rosh.cloud Available)

```python
def verify_with_rosh_cloud(program_uuid, security_key):
    """Verify program with rosh.cloud"""
    response = requests.post('https://rosh.cloud/verify', json={
        'uuid': program_uuid,
        'security_key': security_key
    })
    return response.json()['verified']
```

**Pros:** Verifies author, detects stolen UUIDs
**Cons:** Requires network, slower

### Hybrid Verification (Recommended)

```python
def verify_program(program_code, metadata, online=True):
    """Hybrid verification"""
    # Step 1: Always check checksum (offline)
    if not verify_checksum(program_code, metadata):
        return VerificationResult.CHECKSUM_FAILED

    # Step 2: Try online verification if available
    if online:
        try:
            if verify_with_rosh_cloud(metadata['uuid'], metadata['security_key']):
                return VerificationResult.VERIFIED
            else:
                return VerificationResult.SIGNATURE_FAILED
        except NetworkError:
            # Offline - fall back to checksum only
            return VerificationResult.OFFLINE_VERIFIED

    return VerificationResult.OFFLINE_VERIFIED
```

---

## CLI Flags

**User control over verification:**

```bash
# Skip verification (development)
rosh game.rosh --skip-verification

# Force verification (production)
rosh game.rosh --verify --verify-online

# Set security mode
rosh game.rosh --security-mode=strict
```

---

## Testing

### Unit Tests

```python
# tests/test_security_model.py
def test_fail_safe_mode():
    """Test fail-safe allows execution with warnings"""
    code_with_bad_checksum = '''
    meta.generated
        checksum "sha256:invalid"
    end
    print "Hello"
    '''
    output = run_rosh(code_with_bad_checksum, security_mode='relaxed')
    assert "WARNING" in output
    assert "Hello" in output  # Program ran despite bad checksum

def test_fail_secure_mode():
    """Test fail-secure blocks execution"""
    code_with_bad_checksum = '''
    meta.generated
        checksum "sha256:invalid"
    end
    print "Hello"
    '''
    with pytest.raises(SecurityError):
        run_rosh(code_with_bad_checksum, security_mode='strict')
```

---

## Documentation Updates

**docs/SECURITY.md (new file):**

```markdown
# Rosh Security Model

## Overview

Rosh uses a **context-aware security model** that balances developer convenience with production security.

## Security Modes

1. **Development Mode** (fail-safe)
   - Local development
   - Warnings only, no blocking
   - Fast iteration

2. **Local Execution** (fail-safe with prompts)
   - Running local .rosh files
   - Prompts on verification failure
   - User decides whether to continue

3. **Package Mode** (fail-secure)
   - Installing packages
   - Blocks execution on verification failure
   - Protects against supply chain attacks

4. **Production Mode** (fail-secure)
   - VR deployments, enterprise
   - Requires full verification
   - No exceptions

## CLI Flags

- `--skip-verification`: Skip all verification (dev only)
- `--verify`: Force verification
- `--verify-online`: Require rosh.cloud verification
- `--security-mode=[strict|relaxed]`: Override mode
```

---

## Acceptance Criteria

- [ ] Research complete: Fail-safe vs fail-secure analyzed
- [ ] Recommendation made with rationale (hybrid context-aware)
- [ ] Terminology standardized (dev/local/package/production)
- [ ] Default mode per command specified
- [ ] Context-aware security model designed
- [ ] Verification workflow specified (offline + online)
- [ ] CLI flags designed (`--security-mode=<mode>`)
- [ ] Implementation plan for each phase
- [ ] Linked to metadata ticket (#2025-12-14-program-metadata)
- [ ] Test mode interaction specified (test = dev mode)
- [ ] Exit codes defined (0/1/2/130)
- [ ] UX prompts specified ("Continue? [y/N]")
- [ ] Warning/error format specified (⚠️/❌)
- [ ] Security documentation written (docs/SECURITY.md)
- [ ] BDFL decision on recommended approach

---

## Recommendation Summary

**Recommended Approach:** **Hybrid Context-Aware Security**

**Rationale:**
1. **Current phase (v0.0.8):** Fail-safe for developer adoption
2. **Package manager (v0.2.0):** Fail-secure for remote code
3. **Production (v0.3.0+):** Configurable based on deployment

**Key insight:** Security requirements vary by context. Single approach (pure fail-safe OR pure fail-secure) doesn't fit all use cases.

**Implementation priority:**
1. v0.0.8: Basic checksum verification with warnings (fail-safe)
2. v0.2.0: Package verification with blocking (fail-secure for packages only)
3. v0.3.0+: Full policy-based system

---

## Review Notes

### Round 1 (2025-12-14, codex_gpt_4 / d5c9cb8a-2b5f-4e6a-9d3e-e8d1a65cb25f)

- ✅ Hybrid, context-aware recommendation makes sense for Rosh's phases (dev vs packages vs production).
- ⚠️ Please align terminology for flags/modes (strict/relaxed vs fail-safe/fail-secure vs dev/local/package/production) so CLI, docs, and code match one set of names.
- ⚠️ Define the default mode per command (e.g., `rosh file.rosh` in local single-user = relaxed?) and what happens if metadata is absent.
- ⚠️ Make explicit which ticket will implement checksum generation/storage (link to metadata ticket) and how verification interacts with test mode/CI.
- ⚠️ Acceptance criteria should include UX for prompts/warnings and exit codes for blocked runs.

### Round 2 (2025-12-14, claude_sonnet_4_5 / a1b2c3d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d)

**Addressing Round 1 feedback:**

✅ **Terminology alignment - STANDARDIZED**

**Canonical terminology:**
- **Modes:** `dev`, `local`, `package`, `production` (context-based)
- **Flags:** `--security-mode=[dev|local|package|production]`
- **Behavior:** `warn-only` or `verify-required`
- **No more:** "strict/relaxed" or "fail-safe/fail-secure" in user-facing CLI

**Updated mapping:**
| Mode | CLI Flag | Old Name | Behavior |
|------|----------|----------|----------|
| dev | `--security-mode=dev` | fail-safe | Warn only, no blocking |
| local | `--security-mode=local` | fail-safe + prompt | Warn + user decision |
| package | `--security-mode=package` | fail-secure | Block on verification failure |
| production | `--security-mode=production` | fail-secure | Block + require online verification |

**Documentation uses:** dev/local/package/production exclusively
**Code uses:** Same terminology throughout

✅ **Default mode per command - SPECIFIED**

```bash
# Default: auto-detect based on context
rosh file.rosh                    # Mode: local (has metadata? verify. none? warn-only)
rosh file.rosh --dev              # Mode: dev (shortcuts to dev mode)
rosh install package              # Mode: package (auto-detects package command)
rosh file.rosh --production       # Mode: production (explicit)

# Test mode interaction
rosh file.rosh --test input.txt   # Mode: dev (test implies dev)
```

**Auto-detection logic:**
1. If `--test` flag: Use `dev` mode (skip verification)
2. If package command (`install`, `run package_name`): Use `package` mode
3. If `--production` flag: Use `production` mode
4. If no metadata in file: Use `dev` mode (warn only)
5. If metadata present: Use `local` mode (verify + prompt on failure)

**When metadata is absent:**
```bash
$ rosh game.rosh  # No meta block
⚠️  WARNING: No metadata found
⚠️  Running in DEV mode (no security verification)
⚠️  Add metadata with: rosh --add-metadata game.rosh
[Program runs normally]
```

✅ **Checksum implementation ticket - LINKED**

**Implementation ticket:** `#2025-12-14-program-metadata`
- Metadata ticket implements: UUID, checksum, security_key generation
- This ticket (security) defines: **how to verify** those checksums
- **Dependency:** Security model depends on metadata ticket

**Verification interaction with test mode:**
```bash
# Test mode skips verification (dev mode)
rosh game.rosh --test input.txt
# No security checks, focuses on testing

# Production + test = error (conflicting modes)
rosh game.rosh --test input.txt --production
# ERROR: Cannot use --test with --production mode
```

✅ **Acceptance criteria updated - ADDED UX specs**

Added to acceptance criteria:
- [ ] Prompts for `local` mode specify: "Continue? [y/N]"
- [ ] Exit codes defined:
  - `0` = Success
  - `1` = Security verification failed (blocked)
  - `2` = Invalid arguments
  - `130` = User declined security prompt
- [ ] Warning format: `⚠️  WARNING: <message>`
- [ ] Error format: `❌ ERROR: <message>`
- [ ] Prompt includes checksum details (expected vs actual)

---

## BDFL Approval Section

**Awaiting:** rdubar / 7f3e9a2b-4c1d-4e8a-9b5c-8d7a6f2e1c3b

**Decision:** APPROVED

**Comments (2025-12-14, rdubar):**
- Approved. Hybrid context-aware approach is the right choice.
- Implement phased approach as specified (v0.0.8 fail-safe, v0.2.0 hybrid, v0.3.0+ configurable).

---

## Implementation Decision (2025-12-14)

**Status:** DEFERRED TO BACKLOG

**Rationale:**
- Security model is well-designed and approved
- **Not critical for single-user MVP** (current focus)
- No package distribution yet (nothing to secure)
- Checksums and metadata system already implemented (v0.0.8)
- Actual verification behavior can wait

**Documented in:**
- BACKLOG.md - "Security Model" section
- ROADMAP.md - v0.0.8 marked as deferred
- This ticket remains in `.rosh/tickets/` as reference (not archived)

**Revisit when:**
- v0.3.0 Package System is being implemented
- Package distribution becomes a priority
- Multi-user or untrusted code scenarios emerge

**Next Steps:**
- Implementation design is complete (use this ticket as spec)
- When ready to implement, all decisions are documented here
- No further design work needed
