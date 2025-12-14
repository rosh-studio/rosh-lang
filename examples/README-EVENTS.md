# Event System Testing Guide

**Rosh v0.0.7** introduces a powerful event system for reactive game logic!

## Quick Start

### Option 1: Simple Tests (Validation)
**Best for:** Verifying the event system works correctly

```bash
rosh examples/test-events-simple.rosh
```

**Expected output:** All 8 tests should show `✓ PASS`

**Tests cover:**
- ✓ Basic event registration and triggering
- ✓ Parameter passing
- ✓ Multiple handlers per event
- ✓ Nested events (events triggering events)
- ✓ Object modification via events
- ✓ Graceful handling of missing handlers
- ✓ Null binding for missing arguments
- ✓ String interpolation in handlers

### Option 2: Interactive MUD Demo (Real-World Example)
**Best for:** Seeing events in action in a game

```bash
rosh examples/dungeon-events-demo.rosh
```

**What you'll see:**
- ⚔️ Combat system with attack/damage/death events
- 💎 Quest system with collection/completion events
- 📈 Progression system with XP/level-up events
- 🏰 Room events with traps and treasures
- 🔄 Nested events cascading through the game
- 🎵 Multiple handlers responding to same event

**Demo scenarios:**
1. **Goblin Encounter** - Basic combat with event-driven damage
2. **Gem Quest** - Collecting 3 gems triggers quest completion
3. **Traps & Treasure** - Room events that modify player state
4. **Dragon Boss** - Epic battle demonstrating complex event chains

## How Events Work

### 1. Register Handlers

```rosh
when event_name param1 param2 then
    print "Event fired with {param1} and {param2}!"
    # Your handler code here
end
```

### 2. Trigger Events

```rosh
trigger event_name with value1 value2
```

### 3. Key Features

**Multiple Handlers:**
```rosh
when victory then
    print "You won!"
end

when victory then
    print "Score: 1000"
end

trigger victory  # Both handlers execute!
```

**Nested Events:**
```rosh
when player_damaged amount then
    set player.health to player.health minus amount
    if player.health is below 1 then
        trigger player_died  # Nested!
    end
end

when player_died then
    print "Game Over!"
end

trigger player_damaged with 100  # Cascades to player_died
```

**Object Modification:**
```rosh
create object player
    set health to 100
end

when take_damage target amount then
    set target.health to target.health minus amount
    print "{target.name}: {target.health} HP"
end

trigger take_damage with player 25  # player.health now 75
```

## Understanding the Demo Output

When you run `dungeon-events-demo.rosh`, watch for:

1. **Event Registration Phase**
   - Handlers registered at start
   - No output during registration

2. **Combat Events Chain**
   ```
   ⚔️  COMBAT BEGINS!         ← combat_start event
   ⚡ Hero attacks...         ← attack event
   💔 Goblin takes damage     ← take_damage event
   💀 Goblin defeated!        ← entity_died event
   🎉 Victory!                ← enemy_died event
   ✨ Gained experience!      ← gain_experience event
   ```

3. **Multiple Handlers Firing**
   ```
   🎊 LEVEL UP!               ← level_up handler #1
   ❤️  Max Health +20         ← level_up handler #1 (continued)
   🎺 Fanfare plays!          ← level_up handler #2
   📢 The gods smile...       ← level_up handler #3
   ```

4. **Nested Event Cascade**
   ```
   take_damage
     └─> entity_died
          └─> enemy_died
               └─> gain_experience
                    └─> level_up
   ```

## Common Patterns

### Combat System
```rosh
when attack attacker defender damage then
    trigger take_damage with defender damage attacker
end

when take_damage target amount source then
    set target.health to target.health minus amount
    if target.health is below 1 then
        trigger entity_died with target source
    end
end
```

### Quest System
```rosh
set gems_collected to 0

when gem_found then
    set gems_collected to gems_collected plus 1
    if gems_collected is equal to 3 then
        trigger quest_complete with "Find 3 Gems"
    end
end
```

### NPC Reactions
```rosh
when player_speaks npc_name message then
    if npc_name is equal to "merchant" then
        trigger merchant_response with message
    else if npc_name is equal to "guard" then
        trigger guard_response with message
    end
end
```

## Debugging Events

### Check if Handler Registered
```rosh
when test_event then
    print "Handler is registered!"
end

trigger test_event  # Should print message
```

### Check Parameter Passing
```rosh
when debug_params a b c then
    print "a={a}, b={b}, c={c}"
end

trigger debug_params with 1 2 3  # Prints: a=1, b=2, c=3
```

### Trace Event Execution
```rosh
when some_event then
    print "=== some_event handler started ==="
    # Your code
    print "=== some_event handler finished ==="
end
```

## Next Steps

1. ✅ Run `test-events-simple.rosh` - Verify everything works
2. 🎮 Run `dungeon-events-demo.rosh` - See events in action
3. 📖 Read the event handlers in `dungeon-events-demo.rosh`
4. 🛠️ Modify the demo - Add your own handlers
5. 🎨 Build your own event-driven game!

## Event System Benefits

**Why use events?**

✨ **Decoupled Code**
- Handlers separate from triggers
- Easy to add new reactions
- No spaghetti code

🔄 **Reactive Logic**
- Game feels alive
- NPCs respond naturally
- Complex behaviors emerge

🎯 **Composable**
- Multiple handlers per event
- Events trigger events
- Build complex systems from simple pieces

📚 **Readable**
- Clear cause and effect
- Self-documenting game logic
- Natural language syntax

## Examples in ROSH-MANUAL.rosh

The complete Rosh manual (Section 31) includes more event examples:
```bash
rosh ROSH-MANUAL.rosh
```

Look for "31. EVENT SYSTEM" section.

## Game Loop + Events (Reactive NPCs/Rooms)

The stdlib provides a simple game loop helper for reactive game logic:

```bash
rosh examples/reactive-npc-demo.rosh
```

**What it demonstrates:**
- 🎮 Game loop with `game_tick` event
- 🧙 NPC reactions (Priestess heals when player health is low)
- 🏰 Room ambient effects (Dark chamber atmosphere)
- ⏱️ Time-based events (poison damage every 2 ticks)
- 🔄 Periodic effects using `every(N, tick)` helper

**Pattern:**
```rosh
import "stdlib/game-loop-simple.rosh"

# Define tick handler
when game_tick tick then
    # Check conditions
    if player.health is below 30 then
        trigger player_critical
    end

    # Periodic events
    if call every 5 tick then
        trigger ambient_sound
    end
end

# Main game loop
while game_running is equal to true then
    trigger game_tick with tick_count
    set tick_count to tick_count plus 1
end
```

**Benefits:**
- ✅ NPCs react automatically to game state
- ✅ Rooms have ambient behaviors
- ✅ Easy to add time-based effects
- ✅ Decoupled reactive logic

## Questions?

- Check `ROADMAP.md` for v0.0.7 milestone details
- See `docs/proposals/EVENT-SYSTEM.md` for specification
- Read the test suite: `tests/test_events.py`
- Try the demos: `test-events-simple.rosh`, `dungeon-events-demo.rosh`, `reactive-npc-demo.rosh`

Happy event-driven game development! 🎮✨
