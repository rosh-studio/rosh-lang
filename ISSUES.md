# Rosh Issues & Known Limitations

**Last Updated:** 2024-12-15
**Policy:** See docs/POLICIES.md for issue tracking guidelines

> Dated issues tracking - bugs, limitations, and planned fixes.

---

## 🐛 Active Issues

(No active critical issues!)

---

## ⚠️ Known Limitations (By Design)

### **Security (Pre-Multi-User)**
**Status:** Expected until v0.1.0
**Discovered:** 2024-12-01

- No sandboxing for code execution
- Full filesystem access
- AI-generated code runs with user permissions
- Only safe for single-user, local development

**Resolution Plan:**
- Milestone 9 (v0.1.0) will add sandboxing
- See docs/proposals/SECURITY-PLAN.md

---

### **No Event System Yet**
**Status:** Planned for v0.0.7
**Discovered:** 2024-12-12

- Cannot create event handlers (when/trigger syntax)
- Combat systems require manual checking
- Room navigation needs tight coupling

**Resolution Plan:**
- Milestone 7 (v0.0.7) will add event system
- See docs/proposals/EVENT-SYSTEM.md

---

### **No Multiline Comments**
**Status:** Planned for v0.0.6
**Discovered:** 2024-12-10

- Only single-line comments with `#`
- No """ or ### block comments

**Resolution Plan:**
- Milestone 6 (v0.0.6)

---

---

### **No Dictionary/Map Type**
**Status:** Planned for v0.0.7
**Discovered:** 2024-11-20

- Only lists and objects
- No key-value pair collections

**Resolution Plan:**
- Milestone 7 (v0.0.7)
- Syntax: `set config to {key: value}`

---

### **No Object Collections for Game Objects**
**Status:** Design needed
**Discovered:** 2024-12-15

Creating multiple similar game objects requires numbered names:

```rosh
# Current approach - must create each separately
create object bullet1
    set active to 0
    set sprite to "laser.png"
end
create object bullet2
    set active to 0
    set sprite to "laser.png"
end
# ... repeat for bullet3, bullet4, bullet5
```

This leads to:
- Repetitive code (5 bullets = 5 nearly-identical blocks)
- Verbose collision detection (5 bullets × 4 enemies = 20 checks)
- No way to iterate over "all bullets"

**Resolution Plan:**
- Add object collection syntax: `create 5 objects bullet`
- Add iteration: `for each bullet then ... end`
- See docs/proposals/EVENT-SYSTEM.md for collision events proposal

**Workaround (current):**
Use numbered objects and check each explicitly.

---

## ✅ Resolved Issues

### **`not` in compound boolean expressions fails**
**Discovered:** 2024-12-12
**Resolved:** 2024-12-13 (v0.0.6)

**Problem:**
```rosh
if x and not y then  # Was a syntax error
```

**Fix:** Modified parser to support NOT in compound expressions by creating `parse_condition_term()` helper that handles NOT as a prefix operator at any level.

**Now works:**
```rosh
if x and not y then  # Works!
if not x or y then   # Works!
if x is above 3 and not y is below 5 then  # Works!
```

---

### **No `input` command**
**Discovered:** 2024-12-12
**Resolved:** 2024-12-13 (v0.0.6)

**Problem:** No way to get user input from stdin.

**Fix:** Added `input <variable_name>` command that reads a line from stdin and stores it in the specified variable.

**Usage:**
```rosh
print "What is your name? "
input name
print "Hello {name}!"
```

---

### **No String Interpolation**
**Discovered:** 2024-11-28
**Resolved:** 2024-12-13 (v0.0.6)

**Problem:** Had to use verbose concatenation for dynamic strings.

**Fix:** Added automatic string interpolation with `{expression}` syntax.

**Usage:**
```rosh
set name to "Alice"
set age to 25
print "Hello {name}, you are {age} years old!"
print "x + y = {x plus y}"
print "Health: {player.health} / {player.max_health}"
```

---

### **No `else if` / `elif`**
**Discovered:** 2024-12-12
**Resolved:** 2024-12-13 (v0.0.6)

**Problem:** Had to use deep nesting for multiple conditions.

**Fix:** Added `else if` support by making it parse as a nested if statement.

**Usage:**
```rosh
if grade is above 90 then
    print "A"
else if grade is above 80 then
    print "B"
else if grade is above 70 then
    print "C"
else
    print "F"
end
```

---

### **`print <expression>` doesn't work - FALSE ALARM**
**Discovered:** 2024-12-12
**Resolved:** 2024-12-13
**Status:** NOT A BUG - Already works in v0.0.5

**Original report:**
```rosh
print player.health  # Reported as not working
```

**Testing revealed:** `print <expression>` DOES work! Test file proved:
```rosh
set x to 42
print x  # Works! Prints: 42

create object player
    set health to 100
end
print player.health  # Works! Prints: 100
```

**Root cause:** User confusion in dungeon crawler example. The `get`/`print stack` pattern is only needed when you want to manipulate the stack directly, not for simple printing.

**Resolution:** Documentation clarification - `print` already accepts expressions directly.

---

### **Function Return Values Not Assignable**
**Discovered:** 2024-12-12
**Resolved:** 2024-12-12 (v0.0.5)
**Commit:** d32df9c

Previously could not do:
```rosh
set value to call double 15
```

Now works! Parser supports `call` in expressions.

---

### **No Stack Viewing Command**
**Discovered:** 2024-12-12
**Resolved:** 2024-12-12 (v0.0.5)
**Commit:** d32df9c

Added `stack` command to view data stack non-destructively.

---

### **REPL Doesn't Evaluate Variables Alone**
**Discovered:** 2024-12-12
**Resolved:** 2024-12-12 (v0.0.5)
**Commit:** d32df9c

Previously had to do:
```rosh
rosh> print x
```

Now can just type variable name:
```rosh
rosh> x
42
```

---

### **No List Iteration**
**Discovered:** 2024-11-28
**Resolved:** 2024-11-30 (v0.0.5)

Added `for item in my_list then` syntax.

---

### **No String Methods**
**Discovered:** 2024-11-28
**Resolved:** 2024-11-30 (v0.0.5)

Added: split, substring, uppercase, lowercase, trim, indexOf, lastIndexOf

---

## 📋 Issue Reporting

**For new issues:**
1. Add to "Active Issues" section above
2. Include:
   - Date discovered
   - Clear description
   - Steps to reproduce (if bug)
   - Expected vs actual behavior
3. Link to relevant code/files
4. Propose resolution if possible

**When resolving:**
1. Move to "Resolved Issues" section
2. Add resolution date and commit
3. Keep for historical reference
4. Never delete resolved issues

---

## 🔗 Related Documents

- PROJECT-PLAN.md - Roadmap and milestones
- CHANGELOG.md - Version history
- docs/POLICIES.md - Issue tracking policy

---

*Last updated: 2024-12-15*
