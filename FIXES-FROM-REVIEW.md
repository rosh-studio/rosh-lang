# Fixes from Code Review

**Date:** 2025-12-13
**Version:** v0.0.7

## Summary

Three issues identified in code review have been addressed:

1. ✅ **MEDIUM:** Event handler lexical scoping
2. ✅ **LOW:** stdlib import banner pollution
3. ✅ **LOW:** every() function validation

---

## 1. Event Handler Lexical Scoping (MEDIUM)

### Problem
Event handlers didn't capture their defining environment - they ran with the current environment at trigger time. If you defined a handler inside a function using local variables and triggered it after the function returned, those locals would be undefined and raise errors.

### Example of the Bug
```rosh
define function setup_greeter name
    when greet then
        print "Hello {name}!"  # Would fail - 'name' undefined!
    end
end

call setup_greeter "Alice"
trigger greet  # ERROR: 'name' not found
```

### Solution
Implemented **lexical scoping** - handlers now capture their defining environment at registration time.

**Changes:**
- `interpreter.py:eval_when_statement()` - Store `captured_env` with handler
- `interpreter.py:eval_trigger_event()` - Use `captured_env` as parent environment

### Now Works Correctly
```rosh
define function setup_greeter name
    when greet then
        print "Hello {name}!"  # Works! Captures 'name'
    end
end

call setup_greeter "Alice"
trigger greet  # Prints: Hello Alice!
```

### Tests Added
`tests/test_event_scoping.py` - 8 comprehensive tests:
- ✅ Handler captures local variables
- ✅ Handler captures multiple locals
- ✅ Multiple handlers with different closures
- ✅ Handler with nested scope
- ✅ Handler modifies captured variables
- ✅ Handler with objects from closure
- ✅ Handler parameters shadow captured vars
- ✅ Handler accesses globals after local function

**All tests passing:** 8/8

---

## 2. stdlib Import Banner Pollution (LOW)

### Problem
`stdlib/game-loop-simple.rosh` printed a banner on import:
```
✓ Simple game loop stdlib loaded
  Available:
    - game_running (set to false to stop)
    ...
```

This polluted output for programs that just wanted loop utilities.

### Solution
Removed all `print` statements from stdlib import.

**Changed banner to comments:**
```rosh
# Library loaded - no banner output
# Available:
#   - game_running (set to false to stop)
#   - tick_count (current tick)
#   ...
```

### Before/After

**Before:**
```bash
$ rosh my-game.rosh
✓ Simple game loop stdlib loaded
  Available:
    - game_running (set to false to stop)
=== MY GAME ===
...
```

**After:**
```bash
$ rosh my-game.rosh
=== MY GAME ===
...
```

Clean output! ✨

---

## 3. every() Function Validation (LOW)

### Problem
`every(interval, current)` used modulo without guarding against:
- Zero interval (division by zero)
- Non-numeric inputs (type errors)
- Negative intervals (nonsensical)

```rosh
call every 0 10      # Would crash!
call every "bad" 5   # Would crash!
```

### Solution
Added comprehensive validation with helpful error messages.

**New validation checks:**
```rosh
define function every interval current
    # Type validation
    if call is_number interval is equal to false then
        print "ERROR: every() interval must be a number"
        return false
    end

    if call is_number current is equal to false then
        print "ERROR: every() current must be a number"
        return false
    end

    # Zero check
    if interval is equal to 0 then
        print "ERROR: every() interval cannot be zero"
        return false
    end

    # Negative interval check
    if interval is below 0 then
        print "ERROR: every() interval must be positive"
        return false
    end

    # Safe to use modulo now
    set remainder to current modulo interval
    ...
end
```

### Tests Added
`tests/test_stdlib_validation.py` - 6 validation tests:
- ✅ Valid numeric inputs work
- ✅ Zero interval rejected
- ✅ Negative interval rejected
- ✅ Non-numeric interval rejected
- ✅ Non-numeric current rejected
- ✅ Works correctly in game loop

**All tests passing:** 6/6

---

## Test Results

**Total tests:** 137 (was 123, added 14)

**Breakdown:**
- Original event tests: 21
- New scoping tests: 8
- New validation tests: 6
- Other existing tests: 102

**All passing:** ✅ 137/137

**Test execution time:** ~0.4 seconds

---

## Files Changed

### Core Interpreter
- `src/rosh/interpreter.py`
  - `eval_when_statement()` - Capture lexical environment
  - `eval_trigger_event()` - Use captured environment

### stdlib
- `stdlib/game-loop-simple.rosh`
  - Removed import banner (print statements → comments)
  - Added validation to `every()` function

### Tests (New)
- `tests/test_event_scoping.py` - Lexical scoping tests
- `tests/test_stdlib_validation.py` - Validation tests

### Documentation
- `FIXES-FROM-REVIEW.md` - This file

---

## Migration Guide

### For Existing Code

**99% of code will work unchanged.** The fixes are improvements that don't break existing functionality:

1. **Lexical scoping** - Makes more code work (handlers in functions)
2. **No import banner** - Just removes noise
3. **every() validation** - Adds safety, doesn't change valid usage

### Edge Cases

If you were somehow **relying on dynamic scoping** (extremely unlikely):
```rosh
set global_var to "outer"

when test then
    print global_var  # Now prints value from registration time
end

set global_var to "inner"
trigger test  # Prints "outer" (was "inner" before fix)
```

**This is the correct behavior** (lexical scoping is standard in modern languages).

---

## Verification

### Run All Tests
```bash
pytest tests/ -v
# Should show: 137 passed
```

### Test Lexical Scoping
```bash
rosh tests/test_event_scoping.py
# All 8 tests should pass
```

### Test Validation
```bash
rosh tests/test_stdlib_validation.py
# All 6 tests should pass
```

### Test Demos Still Work
```bash
rosh examples/reactive-npc-demo.rosh
# Should run without banner, clean output
```

---

## Review Response

**All three issues addressed:**

✅ **MEDIUM - Lexical scoping:** FIXED
   - Handlers now capture defining environment
   - 8 comprehensive tests added
   - Works like closures in JavaScript/Python

✅ **LOW - Import banner:** FIXED
   - No more pollution on import
   - Clean output for production code

✅ **LOW - every() validation:** FIXED
   - Type checking (is_number)
   - Zero guard
   - Negative interval guard
   - Clear error messages
   - 6 validation tests added

**Test coverage increased:** +14 tests (137 total, all passing)

---

## Credits

Thanks to the code reviewer for catching these issues! 🙏

The lexical scoping fix in particular is important - it makes event handlers behave like proper closures, which is essential for advanced game patterns.
