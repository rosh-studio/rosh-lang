# Dungeon Crawler Demo - Pain Points & Learnings

**Created:** 2024-12-12
**Purpose:** Document real issues discovered building a complete MUD with Rosh v0.0.5

---

## 🐛 Critical Issues Found

### **Issue #1: `get` + `print` doesn't work as expected**
**Severity:** HIGH - Makes the language almost unusable for real programs

**Problem:**
```rosh
get player.health
print
# Prints blank line, not the value!
```

**What we expected:**
```rosh
print player.health  # Just print the value directly!
```

**Current workaround:**
```rosh
get player.health
print stack  # Pop from stack and print
```

**Root cause:** `get` pushes to stack, `print` with no args prints blank line. Need `print stack` to pop.

**Fix needed:** Make `print <expression>` work directly without needing `get` + `print stack`

**Impact:** MASSIVE - Every single print statement needs this pattern. Makes code 2-3x more verbose.

---

### **Issue #2: `not` in compound boolean expressions fails**
**Severity:** HIGH

**Problem:**
```rosh
if room.has_enemy and not room.visited then  # SYNTAX ERROR!
```

**Current workaround:**
```rosh
if room.has_enemy then
    if room.visited is equal to false then
        # ...
    end
end
```

**Fix needed:** Support `not` in compound expressions, or add `and not`, `or not` operators

**Impact:** Forces deep nesting, makes code harder to read

---

### **Issue #3: No string interpolation**
**Severity:** MEDIUM - Already knew this, but painfully obvious now

**Problem:**
```rosh
print "Health: "
get player.health
print stack
print " / "
get player.max_health
print stack
# Takes 5 lines for one message!
```

**What we need:**
```rosh
print "Health: {player.health} / {player.max_health}"
# One line, clear and readable
```

**Impact:** Every message requires 3-5 lines. Code becomes unreadable.

---

### **Issue #4: No dictionary/map type**
**Severity:** MEDIUM

**Problem:**
```rosh
# Need to map room names to room objects
# Currently requires this ugly chain:
define function get_room room_name
    if room_name is equal to "entrance" then
        return entrance
    end
    if room_name is equal to "armory" then
        return armory
    end
    # ... 6 more if statements!
end
```

**What we need:**
```rosh
set rooms to {
    "entrance": entrance,
    "armory": armory,
    "dungeon": dungeon
}

set room to rooms[player.current_room]
```

**Impact:** Simple lookups become 20+ lines of code

---

### **Issue #5: No `input` command**
**Severity:** HIGH - Can't make real interactive games!

**Problem:** Demo had to be scripted because there's no way to get user input

**What we need:**
```rosh
print "What do you do? "
input command
# Now 'command' contains user's input
```

**Impact:** Can't build real interactive MUDs without this

---

### **Issue #6: No `else if` / `elif`**
**Severity:** MEDIUM

**Problem:**
```rosh
if grade is above 90 then
    print "A"
else
    if grade is above 80 then  # Nested!
        print "B"
    else
        if grade is above 70 then  # Triple nested!
            print "C"
        end
    end
end
```

**What we need:**
```rosh
if grade is above 90 then
    print "A"
else if grade is above 80 then
    print "B"
else if grade is above 70 then
    print "C"
end
```

**Impact:** Deep nesting makes code hard to read

---

### **Issue #7: Events desperately needed**
**Severity:** HIGH for complex games

**Problem:** Combat code is 50+ lines of manual state checking:
```rosh
define function combat_turn action
    if action is equal to "attack" then
        # Calculate damage
        # Update health
        # Check if enemy died
            # Award gold
            # Award score
            # Check if boss
                # Win game
        # Enemy attacks
        # Calculate damage
        # Update health
        # Check if player died
            # Lose game
    end
end
```

**What we need:**
```rosh
when enemy_takes_damage target amount then
    set target.health to target.health minus amount
    if target.health is below 1 then
        trigger enemy_dies with target
    end
end

when enemy_dies target then
    trigger award_gold with target.gold_drop
    trigger award_score with target.score_value
end
```

**Impact:** Code becomes unmaintainable for complex systems

---

### **Issue #8: Checking if item in list is verbose**
**Severity:** MEDIUM

**Problem:**
```rosh
# Want to check: does player have health potion?
create number has_potion to false
for item in player.inventory then
    if item is equal to "Health Potion" then
        set has_potion to true
    end
end

if has_potion then
    # ...
end
```

**What we need:**
```rosh
if player.inventory contains "Health Potion" then
    # ...
end
```

**Actually:** Wait, we DO have `contains`! Let me check...

**UPDATE:** `contains` works for lists! Issue is that I forgot it existed. This is a **documentation issue**, not a language issue.

**Fix needed:** Better examples in manual, better help text

---

## 📊 Pain Point Priority

| Priority | Issue | Fix in Version |
|----------|-------|----------------|
| 🔴 #1 | `print <expression>` doesn't work | v0.0.6 |
| 🔴 #2 | `input` command missing | v0.0.6 |
| 🔴 #3 | Events system | v0.0.7 |
| 🟡 #4 | String interpolation | v0.0.6 |
| 🟡 #5 | `not` in compound expressions | v0.0.6 |
| 🟡 #6 | `else if` / `elif` | v0.0.6 |
| 🟡 #7 | Dictionary/map type | v0.0.7 |
| 🟢 #8 | Better documentation for `contains` | v0.0.6 docs |

---

## ✅ What Worked Well

**Good features we used successfully:**

1. **Objects and properties** - Perfect for rooms, enemies, items
2. **Lists** - Inventory system works great
3. **Functions** - Code organization is clean
4. **For loops** - Iterating over inventory works
5. **While loops** - Main game loop works
6. **Contains operator** - Works for lists (we just forgot!)
7. **Cloning** - Enemy templates work well
8. **String concatenation** - Verbose but functional

---

## 🎯 Recommendations for v0.0.6

Based on building this real MUD, **absolute must-haves** for v0.0.6:

### **Top Priority (Blockers):**
1. **`print <expression>`** - Make this work like every other language
2. **`input` command** - Can't build interactive games without it
3. **String interpolation** - Quality of life, desperately needed

### **High Priority (Major pain points):**
4. **`else if` / `elif`** - Reduce nesting hell
5. **Fix `not` in compound expressions** - Current workaround is ugly

### **Can Wait (Nice to have):**
6. Multiline comments
7. Increment/decrement shortcuts
8. Type checking functions

---

## 🎮 What We Built

Despite the pain points, we successfully created:

- ✅ 6 interconnected rooms with navigation
- ✅ Turn-based combat system
- ✅ Inventory management
- ✅ NPC merchant with shop
- ✅ Item effects (weapons, armor, potions)
- ✅ Quest system (collect 3 gems)
- ✅ Locked doors puzzle
- ✅ Boss fight
- ✅ Win/lose conditions
- ✅ Score tracking

**This proves Rosh v0.0.5 CAN build real games, but the pain points make it harder than it should be.**

---

## 📝 Next Steps

1. **Fix `print <expression>`** - Highest impact
2. **Add `input` command** - Required for real games
3. **Implement string interpolation** - Huge quality of life
4. **Add `else if`** - Reduce nesting
5. **Fix `not` in compound expressions** - Small but important
6. **Implement events** (v0.0.7) - Game-changer for complex systems

---

**Conclusion:** Building a real MUD revealed exactly what we need to prioritize. The language works, but needs quality-of-life improvements before it's truly usable.
