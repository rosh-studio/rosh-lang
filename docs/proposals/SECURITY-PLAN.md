# Security Considerations for Rosh

**Version:** 0.0.4
**Last Updated:** 2024-12-11

## ⚠️ Important Security Warnings

Rosh is designed for **interactive exploration and AI-assisted programming**. Several features intentionally prioritize flexibility and ease-of-use over sandboxing. **Do not run untrusted Rosh code** without understanding these risks.

## Critical Security Risks

### 1. `prompt exec` - AI Code Execution

**Risk Level:** 🟡 **MEDIUM** (⬇️ Reduced from CRITICAL in v0.0.4)

The `prompt exec` command generates and can execute AI code with **full file system access** and **Python module import capabilities**.

**Example:**
```rosh
prompt exec "write a Python script to delete all my files" into code
```

**Attack Scenarios:**
- AI hallucinates destructive commands (`rm -rf /`, file deletion)
- Prompt injection causes unintended operations
- Network requests to malicious endpoints
- Data exfiltration

**Mitigations (v0.0.4+):**
- ✅ **USER CONFIRMATION REQUIRED** - Code is displayed before execution
- ✅ **Review step** - User sees generated code and can cancel
- ✅ **Save on cancel** - Rejected code saved to variable for later review
- ⚠️ **NO SANDBOX** - Code runs with full interpreter permissions if user confirms
- ⚠️ **NO ALLOWLIST** - Any Python code can execute

**How it works now (v0.0.4+):**
```rosh
prompt exec "create a hello world script" into code
# Output:
# 🤖 AI generated code:
# ────────────────────────────────────────
# print "Hello, World!"
# ────────────────────────────────────────
#
# Execute this AI-generated code? [y/N]:
```

**Recommendations:**
```rosh
# SAFER: Review before executing
prompt "write code to..." into code
# Inspect 'code' variable first!
eval code  # Only after review

# NOW SAFER: Confirmation required (v0.0.4+)
prompt exec "..." into result  # ✓ Shows code, asks for confirmation
```

### 2. `import` - Remote Code Execution

**Risk Level:** 🟡 **MEDIUM** (⬇️ Reduced from CRITICAL in v0.0.4)

The `import` command can fetch and execute code over **HTTP/HTTPS**.

**Example:**
```rosh
import "https://example.com/module.rosh"
```

**Attack Scenarios:**
- Supply chain attacks (compromised remote modules)
- Man-in-the-middle attacks (unencrypted HTTP)
- Slow network causing hangs (timeout: 10s)
- Malicious code injection

**Mitigations (v0.0.4+):**
- ✅ **USER CONFIRMATION REQUIRED** - Interactive prompt before fetching
- ✅ **Security warning** - Clear display of URL and risks
- ✅ **Cached modules trusted** - No re-confirmation for cached modules
- ✅ **10-second timeout** - Prevents indefinite hangs
- ⚠️ **No checksum verification** - Planned for v0.0.5
- ⚠️ **No signature validation** - Planned for v0.0.5

**How it works now (v0.0.4+):**
```rosh
import "https://example.com/module.rosh"
# Output:
# ⚠️  SECURITY WARNING: Remote import requested
# URL: https://example.com/module.rosh
#
# This will fetch and execute code from the internet.
# Only proceed if you trust this source.
#
# Download and execute this module? [y/N]:
```

**Recommendations:**
- ✅ **Use local imports:** `import "stdlib/mud.rosh"` (trusted)
- ✅ **Use HTTPS** (not HTTP) for remote imports
- ✅ **Review confirmation prompts carefully**
- ✅ **Cached modules skip confirmation** (already vetted)

**Future Improvements (v0.0.5+):**
- Hash/signature verification
- Optional automatic updates
- Content security policy

### 3. `eval` - Arbitrary Code Execution

**Risk Level:** 🟠 **HIGH**

The `eval` command executes arbitrary Rosh code from strings:

```rosh
create string malicious as "delete important-data"
eval malicious
# ⚠️ Executes whatever is in the string!
```

**Risk:** Any code generation or user input passed to `eval` runs immediately.

**Mitigation:** Only `eval` code you trust and have reviewed.

### 4. `read` / `write` - File System Access

**Risk Level:** 🟡 **MEDIUM**

Full file system access with **no path restrictions**:

```rosh
# Can read ANY file
read "/etc/passwd" into data
read "~/.ssh/id_rsa" into private_key

# Can write ANYWHERE
write malicious to "/important/config"
```

**Mitigation:**
- Run Rosh with **minimal user permissions**
- Avoid running as root/administrator
- Review file paths in untrusted scripts

### 5. State Persistence - Improved in v0.0.4

**Risk Level:** 🟢 **LOW** (⬇️ Improved from MEDIUM in v0.0.4)

`save`/`load` commands now properly handle most state.

**Fixed in v0.0.4:**
- ✅ Instance tracking now persisted (`instance_counters`)
- ✅ `instances` and `uuid_map` rebuilt on load
- ✅ Functions show warning but don't break load
- ✅ After `load`, instance features work correctly

**Remaining Limitations:**
- ⚠️ Functions cannot be serialized (shows warning, skips gracefully)
- ⚠️ Function bodies not restored (re-import modules after load)

**Current Behavior:**
```rosh
create object ball
end
create ball
create ball
save "state.json"
# Later...
load "state.json"
# ✓ Instance tracking fully restored!
# ⚠️ Warning: Function 'myfunc' was not restored (re-import modules)
```

**Workaround:** After loading, re-import any modules that define functions

## Best Practices

### For Users

1. **Never run untrusted Rosh code**
   - Review all scripts before execution
   - Inspect remote imports manually
   - Be cautious with AI-generated code

2. **Use `prompt` carefully**
   - Avoid `prompt exec` for potentially destructive operations
   - Review AI responses before `eval`
   - Use specific, constrained prompts

3. **Limit permissions**
   - Run Rosh as non-privileged user
   - Use virtual environments
   - Restrict network access if possible

4. **Validate inputs**
   - Don't `eval` user input directly
   - Sanitize file paths
   - Check AI-generated code before execution

### For Developers

1. **Remote Import Hardening (TODO)**
   ```python
   # Future: Add hash verification
   import "https://example.com/module.rosh" checksum "sha256:abc123..."

   # Future: User confirmation
   import "https://..." confirm  # Prompts user

   # Future: Timeouts
   import "https://..." timeout 5  # 5 second timeout
   ```

2. **Execution Guards (TODO)**
   ```python
   # Future: Opt-in for dangerous features
   import dangerous  # Enables prompt exec
   prompt exec "..." into result  # Only works after import
   ```

3. **Sandboxing (Future)**
   - RestrictedPython integration
   - File system allowlists
   - Network restrictions
   - Resource limits (CPU, memory)

## Vulnerability Reporting

If you discover a security vulnerability in Rosh:

1. **Do NOT** create a public GitHub issue
2. Email: [To be determined - private disclosure]
3. Include:
   - Description of vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

We will acknowledge receipt within 48 hours and work with you on a fix.

## Security Roadmap

**v0.0.4 (COMPLETED):**
- ✅ Document security risks (SECURITY.md)
- ✅ Cycle detection in inheritance
- ✅ User confirmation for remote imports
- ✅ User confirmation for `prompt exec`
- ✅ State persistence improvements
- ✅ Test infrastructure

**v0.0.5 (Planned):**
- ⬜ Remote import checksums/hash verification
- ⬜ Optional sandboxing for `prompt exec`
- ⬜ File system allowlists
- ⬜ Execution guards/permission system

**v0.1.0 (Planned):**
- ⬜ Full sandboxing implementation
- ⬜ Resource limits (CPU, memory)
- ⬜ Security audit
- ⬜ Penetration testing

## Disclaimer

Rosh is **experimental software** for **interactive development** and **AI exploration**. It is **not designed for production use** or **untrusted input**.

The developers make **no security guarantees**. Use at your own risk.

---

**Remember:** With great flexibility comes great responsibility. Review code, limit permissions, and never run untrusted scripts.
