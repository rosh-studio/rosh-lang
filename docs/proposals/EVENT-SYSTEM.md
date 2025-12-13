# Rosh Event System Specification

**Version:** v0.0.7 (Planned)
**Status:** Design Phase
**Last Updated:** 2024-12-12

> Events are **critical** for building real MUDs, even in single-player mode. This document specifies the event system design for Rosh.

---

## 🎯 Goals

**Primary:**
- Enable reactive programming for MUDs
- Natural language syntax for events
- Voice-friendly (easy to dictate)
- Simple mental model

**Use Cases:**
- Combat systems (attack, damage, death)
- Room navigation (enter, exit, look)
- Item interactions (pickup, drop, use)
- Quest systems (start, progress, complete)
- NPC behaviors (talk, trade, attack)
- Time-based events (tick, day/night)

---

## 📝 Syntax Design

### **Option A: When/Then Pattern** ⭐ **RECOMMENDED**

```rosh
# Define event handler
when <event_name> then
    <statements>
end

# Define event handler with parameters
when <event_name> <param1> <param2> then
    <statements>
end

# Trigger event
trigger <event_name>

# Trigger event with arguments
trigger <event_name> with <arg1> <arg2>
```

**Examples:**

```rosh
# Simple event (no parameters)
when game_started then
    print "Welcome to the dungeon!"
    set player.health to 100
end

trigger game_started

# Event with parameters
when player_takes_damage amount source then
    set player.health to player.health minus amount
    print "Took"
    print amount
    print "damage from"
    print source

    if player.health is below 1 then
        trigger player_died
    end
end

trigger player_takes_damage with 25 "goblin"

# Multiple handlers for same event
when player_died then
    print "Game Over!"
end

when player_died then
    call save_high_score player.score
end

trigger player_died
# Both handlers execute
```

---

## 🏗 Implementation Architecture

### **AST Nodes**

```python
# ast_nodes.py

@dataclass
class WhenStatement(ASTNode):
    """Event handler definition: when <event> then ... end"""
    event_name: str
    parameters: list[str]  # Parameter names
    body: list[ASTNode]
    line: int = 0

@dataclass
class TriggerEvent(ASTNode):
    """Event emission: trigger <event> with <args>"""
    event_name: str
    arguments: list[ASTNode]  # Expressions to evaluate
    line: int = 0
```

### **Lexer Changes**

```python
# lexer.py

class TokenType(Enum):
    # ... existing tokens ...
    WHEN = auto()
    TRIGGER = auto()

KEYWORDS = {
    # ... existing keywords ...
    'when': TokenType.WHEN,
    'trigger': TokenType.TRIGGER,
}
```

### **Parser Changes**

```python
# parser.py

def parse_statement(self):
    # ... existing statement parsing ...
    elif token.type == TokenType.WHEN:
        return self.parse_when()
    elif token.type == TokenType.TRIGGER:
        return self.parse_trigger()

def parse_when(self):
    """Parse: when <event_name> [params] then <body> end"""
    self.expect(TokenType.WHEN)

    # Parse event name
    event_name = self.expect(TokenType.IDENTIFIER).value

    # Parse optional parameters
    parameters = []
    while self.current_token().type == TokenType.IDENTIFIER:
        parameters.append(self.expect(TokenType.IDENTIFIER).value)

    # Parse 'then'
    self.expect(TokenType.THEN)

    # Parse body
    body = []
    while not self.check(TokenType.END):
        body.append(self.parse_statement())

    self.expect(TokenType.END)

    return WhenStatement(
        event_name=event_name,
        parameters=parameters,
        body=body,
        line=self.current_token().line
    )

def parse_trigger(self):
    """Parse: trigger <event_name> [with <args>]"""
    self.expect(TokenType.TRIGGER)

    # Parse event name
    event_name = self.expect(TokenType.IDENTIFIER).value

    # Parse optional arguments
    arguments = []
    if self.check(TokenType.WITH):
        self.expect(TokenType.WITH)

        # Parse argument list
        arguments.append(self.parse_expression())
        while not self.at_end() and self.current_token().type != TokenType.NEWLINE:
            arguments.append(self.parse_expression())

    return TriggerEvent(
        event_name=event_name,
        arguments=arguments,
        line=self.current_token().line
    )
```

### **Interpreter Implementation**

```python
# interpreter.py

class Interpreter:
    def __init__(self):
        # ... existing initialization ...
        self.event_handlers = {}  # event_name -> list of handlers

    def eval_when_statement(self, node: WhenStatement) -> None:
        """Register an event handler"""
        if node.event_name not in self.event_handlers:
            self.event_handlers[node.event_name] = []

        # Store handler definition
        handler = {
            'parameters': node.parameters,
            'body': node.body,
            'environment': self.current_env  # Capture closure
        }

        self.event_handlers[node.event_name].append(handler)

    def eval_trigger_event(self, node: TriggerEvent) -> None:
        """Trigger an event, executing all registered handlers"""
        event_name = node.event_name

        # Check if event has handlers
        if event_name not in self.event_handlers:
            # Silent no-op (no handlers registered)
            return

        # Evaluate arguments
        args = [self.eval_expression(arg) for arg in node.arguments]

        # Execute each handler
        for handler in self.event_handlers[event_name]:
            # Check parameter count
            if len(args) != len(handler['parameters']):
                raise RuntimeError(
                    f"Event '{event_name}' expects {len(handler['parameters'])} "
                    f"arguments, got {len(args)}"
                )

            # Create new environment for handler
            handler_env = Environment(parent=handler['environment'])

            # Bind parameters to arguments
            for param_name, arg_value in zip(handler['parameters'], args):
                handler_env.set(param_name, arg_value)

            # Save current environment
            prev_env = self.current_env
            self.current_env = handler_env

            # Execute handler body
            try:
                for stmt in handler['body']:
                    result = self.eval_statement(stmt)

                    # Handle control flow
                    if isinstance(result, ReturnException):
                        break  # Return from handler (not event)
                    elif isinstance(result, BreakException):
                        raise RuntimeError("'break' not allowed in event handler")
                    elif isinstance(result, ContinueException):
                        raise RuntimeError("'continue' not allowed in event handler")
                    elif isinstance(result, StopException):
                        raise result  # Propagate stop
            finally:
                # Restore environment
                self.current_env = prev_env

    def eval_statement(self, node: ASTNode) -> Any:
        # ... existing statement evaluation ...
        elif isinstance(node, WhenStatement):
            return self.eval_when_statement(node)
        elif isinstance(node, TriggerEvent):
            return self.eval_trigger_event(node)
        # ... rest of cases ...
```

---

## 🎮 Built-in MUD Events

### **Standard Event Conventions**

For consistency, define standard event names:

```rosh
# Room Navigation
when player_enters_room room then
    print room.description
end

when player_exits_room room then
    # Cleanup logic
end

# Combat
when combat_starts enemy then
    print "Combat begins with"
    print enemy.name
end

when player_attacks target then
    create number damage to random 5 to 15
    trigger enemy_takes_damage with target damage
end

when enemy_takes_damage target amount then
    set target.health to target.health minus amount
    if target.health is below 1 then
        trigger enemy_dies with target
    end
end

when enemy_dies target then
    print target.name
    print "has been defeated!"
    trigger combat_ends
end

when combat_ends then
    set player.in_combat to false
end

# Items
when player_picks_up item then
    append item to player.inventory
    print "Picked up"
    print item.name
end

when player_drops item then
    remove item from player.inventory
    print "Dropped"
    print item.name
end

when player_uses item then
    call item.use_effect player
    remove item from player.inventory
end

# Quests
when quest_started quest_name then
    print "Quest started:"
    print quest_name
end

when quest_progress quest_name step then
    print "Quest progress:"
    print quest_name
    print "step"
    print step
end

when quest_completed quest_name then
    print "Quest completed!"
    set player.score to player.score plus 100
end

# NPCs
when player_talks_to npc then
    print npc.greeting
    call show_dialogue_options npc
end

when player_trades_with npc then
    call show_trade_menu npc
end

# Time
when game_tick then
    # Called every game loop iteration
    call update_all_entities
end

when day_changes day_number then
    print "Day"
    print day_number
end

when time_passes hours then
    # Time-based events
    if hours is equal to 0 then
        print "Midnight..."
    end
end
```

---

## 📚 Examples

### **Example 1: Simple Combat System**

```rosh
# Setup
create object player
    set health to 100
    set attack to 10
end

create object goblin
    set health to 30
    set attack to 5
    set name to "Goblin"
end

# Event handlers
when combat_turn attacker defender then
    create number damage to attacker.attack
    set defender.health to defender.health minus damage

    print attacker.name
    print "attacks for"
    print damage
    print "damage!"

    if defender.health is below 1 then
        trigger entity_dies with defender
    end
end

when entity_dies entity then
    print entity.name
    print "has died!"

    if entity is equal to player then
        trigger game_over
    end
end

when game_over then
    print "=== GAME OVER ==="
    stop
end

# Game loop
print "Combat begins!"
while player.health is above 0 and goblin.health is above 0 then
    trigger combat_turn with player goblin
    if goblin.health is above 0 then
        trigger combat_turn with goblin player
    end
end
```

### **Example 2: Room Navigation System**

```rosh
# Create rooms
create object entrance
    set name to "Entrance Hall"
    set description to "A grand entrance with marble floors."
    set north to "dungeon"
end

create object dungeon
    set name to "Dark Dungeon"
    set description to "A damp, dark dungeon. You hear dripping water."
    set south to "entrance"
    set has_monster to true
end

create object current_room
set current_room to entrance

# Event handlers
when player_moves direction then
    # Check if direction exists
    create string next_room_name to get_property current_room direction

    if next_room_name is equal to null then
        print "You cannot go that way."
    else
        # Trigger exit event
        trigger player_exits_room with current_room

        # Move to new room
        # (simplified - would need room lookup)

        # Trigger enter event
        trigger player_enters_room with current_room
    end
end

when player_enters_room room then
    print "==="
    print room.name
    print "==="
    print room.description
    print

    if room.has_monster then
        print "A monster lurks here!"
        trigger combat_starts with room.monster
    end
end

when player_exits_room room then
    print "You leave"
    print room.name
    set room.visited to true
end

# Game commands
trigger player_enters_room with entrance
trigger player_moves with "north"
```

### **Example 3: Quest System**

```rosh
# Quest tracking
create object active_quests
set active_quests to []

create object completed_quests
set completed_quests to []

# Event handlers
when quest_started quest_name then
    append quest_name to active_quests
    print "New Quest:"
    print quest_name
    print "Check your quest log!"
end

when quest_objective_completed quest_name objective then
    print "Objective completed:"
    print objective

    # Check if all objectives done
    call check_quest_completion quest_name
end

when quest_completed quest_name then
    remove quest_name from active_quests
    append quest_name to completed_quests

    print "=== QUEST COMPLETED ==="
    print quest_name
    print

    # Rewards
    set player.experience to player.experience plus 100
    set player.gold to player.gold plus 50

    print "Rewards:"
    print "  +100 XP"
    print "  +50 Gold"
end

# Example usage
trigger quest_started with "Slay the Dragon"
trigger quest_objective_completed with "Slay the Dragon" "Find the dragon's lair"
trigger quest_objective_completed with "Slay the Dragon" "Defeat the dragon"
trigger quest_completed with "Slay the Dragon"
```

---

## 🔄 Event Execution Order

**Multiple handlers for the same event execute in registration order:**

```rosh
when player_damaged amount then
    print "Handler 1"
end

when player_damaged amount then
    print "Handler 2"
end

when player_damaged amount then
    print "Handler 3"
end

trigger player_damaged with 10
# Output:
# Handler 1
# Handler 2
# Handler 3
```

**Events can trigger other events (event chains):**

```rosh
when enemy_takes_damage target amount then
    set target.health to target.health minus amount
    if target.health is below 1 then
        trigger enemy_dies with target  # Triggers another event
    end
end

when enemy_dies target then
    print "Enemy defeated!"
    trigger combat_ends  # Triggers another event
end

when combat_ends then
    print "Combat is over"
end

trigger enemy_takes_damage with goblin 50
# Chain: enemy_takes_damage → enemy_dies → combat_ends
```

---

## 🚫 Limitations (v0.0.7)

**Not supported in single-player version:**
- Event bubbling (parent/child propagation)
- Event cancellation/prevention
- Async events (all synchronous)
- Event priorities/ordering
- Object-specific event namespacing

**These will be added in multi-user version (v0.1.0+)**

---

## 🧪 Testing Strategy

Add to `ROSH-MANUAL.rosh`:

```rosh
# ========================================
# 28. EVENT SYSTEM
# ========================================
print "--- 28. Event System ---"

# Simple event
when test_event then
    print "Event triggered!"
end

trigger test_event

# Event with parameters
when player_scored points then
    print "Scored"
    print points
    print "points!"
end

trigger player_scored with 100

# Multiple handlers
create number counter to 0

when increment then
    set counter to counter plus 1
end

when increment then
    set counter to counter plus 1
end

trigger increment
print "Counter (should be 2):"
print counter

# Event chains
when start_chain then
    print "Chain started"
    trigger middle_chain
end

when middle_chain then
    print "Chain middle"
    trigger end_chain
end

when end_chain then
    print "Chain ended"
end

trigger start_chain
print
```

---

## 📅 Implementation Timeline

**v0.0.7 (Planned - Q1 2025):**

**Week 1-2: Core Implementation**
- Add WHEN and TRIGGER tokens to lexer
- Implement WhenStatement and TriggerEvent AST nodes
- Add parser support for when/trigger syntax
- Implement event handler registry in interpreter
- Add event triggering logic

**Week 3: Testing & Examples**
- Add event system tests
- Update ROSH-MANUAL.rosh with Section 28
- Create example MUDs using events
- Test event chains and multiple handlers

**Week 4: Documentation & Polish**
- Update help system with event commands
- Write EVENT-SYSTEM.md (this document)
- Create example games in examples/ directory
- Update PROJECT-PLAN.md

---

## 🎯 Success Criteria

**Must have:**
- ✅ `when <event> then ... end` works
- ✅ `trigger <event>` works
- ✅ Events with parameters work
- ✅ Multiple handlers per event work
- ✅ Event chains work (events triggering events)
- ✅ Examples in ROSH-MANUAL.rosh
- ✅ Help documentation complete

**Nice to have (defer to v0.1.0):**
- Event bubbling
- Event cancellation
- Async events
- Priority ordering

---

## 🔗 Related Documents

- `PROJECT-PLAN.md` - Roadmap (Milestone 7)
- `ROSH-MANUAL.rosh` - Tutorial with examples
- `docs/proposals/MULTI-USER.md` - Future event enhancements

---

**Status:** Ready for implementation in v0.0.7
**Priority:** HIGH - Critical for building real MUDs
