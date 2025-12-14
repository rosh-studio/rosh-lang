# In-Game REPL System Proposal

**Status:** Proposed for v0.2.0
**Author:** Claude Sonnet 4.5 (with rdubar)
**Date:** 2025-12-14
**Priority:** HIGH - Original inspiration for Rosh

---

## Executive Summary

**The Vision:** Live coding directly inside running games - edit objects, trigger events, debug state, and create content in real-time without leaving the game world.

**The Original Inspiration:** This is what Rosh was created for - especially in multiplayer 3D worlds where players can collaboratively program their environment using natural language.

**The Proposal:** Build a Quake-style console overlay for Phaser games that lets you type Rosh commands and see immediate results. Start with a JavaScript prototype (1-2 days), evolve to full WebSocket-based interpreter (1 week), eventually port to all platforms.

**Why Now:** We have all the pieces in place - Phaser transpiler working, event system complete, sprite support ready. The in-game REPL would be a **killer demo feature** that shows what makes Rosh unique.

---

## The Original Vision

**User's words:** "This always was my insoration for rosh, btw, epeciallt in multi player 3d workds."

### What This Enables

**Single Player:**
- Debug games while playing (inspect variables, test events)
- Rapid iteration (change sprite, adjust speed, add objects - no rebuild)
- Learning environment (experiment with commands, see results instantly)
- Demo wow factor (code a game live on stage)

**Multiplayer:**
- Collaborative world building (players create together)
- Live GM powers (dungeon master spawns enemies, changes environment)
- Educational environments (teacher demonstrates concepts, students try)
- Creative sandbox (Minecraft-style creativity with code instead of blocks)

**Future Vision (VR/AR):**
- Voice input → in-game REPL → instant world changes
- "Create a dragon" → appears in front of you
- "Make it breathe fire" → adds fire particle effect
- All in natural language, all in real-time

---

## Technical Architecture

### Three Implementation Approaches

#### Approach 1: Direct JavaScript REPL (Prototype - Recommended First)

**Timeline:** 1-2 days
**Complexity:** Low
**Power:** Limited but sufficient for MVP

**How it works:**
1. Add DOM console overlay (backtick key toggles visibility)
2. Implement simple Rosh command parser in JavaScript
3. Execute commands directly on Phaser scene objects
4. Display results in console output

**Supported commands:**
```rosh
# Object creation
create object enemy at 200, 150

# Property changes
set player.x to 400
set enemy.speed to 10

# Event triggering
trigger damage with 15

# Inspection
get player.health
list objects
describe player
```

**Example code:**
```javascript
class RoshConsole {
    constructor(scene) {
        this.scene = scene;
        this.createUI();
        this.setupInput();
    }

    executeCommand(command) {
        // Parse simple Rosh commands
        if (command.startsWith('set ')) {
            // set player.x to 400
            const [_, target, value] = this.parseSetCommand(command);
            this.scene[target] = eval(value);
            return `✓ ${target} = ${value}`;
        }

        if (command.startsWith('create object ')) {
            // create object enemy at 200, 150
            const [_, name, x, y] = this.parseCreateCommand(command);
            this.scene[name] = this.scene.add.rectangle(x, y, 50, 50, 0xff0000);
            return `✓ Created ${name}`;
        }

        if (command.startsWith('trigger ')) {
            // trigger damage with 15
            const [_, event, params] = this.parseTriggerCommand(command);
            this.scene.triggerEvent(event, params);
            return `✓ Triggered ${event}`;
        }

        // ... more commands
    }
}
```

**Pros:**
- ✅ Fast to implement (1-2 days)
- ✅ Zero network latency
- ✅ Works offline
- ✅ Good for demos
- ✅ Proves the concept

**Cons:**
- ❌ Limited to simple commands
- ❌ Can't use full Rosh syntax
- ❌ No function definitions, loops, etc.
- ❌ JavaScript eval() security concerns (single-player only)

---

#### Approach 2: WebSocket to Rosh Server (Full Power - Recommended v0.2.0)

**Timeline:** 1 week
**Complexity:** Medium
**Power:** Full Rosh interpreter

**How it works:**
1. Python WebSocket server runs Rosh interpreter
2. Browser connects via WebSocket
3. Console sends Rosh commands to server
4. Server executes in real interpreter
5. Server sends back results and state changes
6. Browser updates game objects based on state

**Architecture:**
```
Browser (Phaser Game)          WebSocket Server (Python)
┌─────────────────┐            ┌────────────────────┐
│  DOM Console    │──command──>│  Rosh Interpreter  │
│  (UI Overlay)   │<──result───│  (Full Python)     │
│                 │            │                    │
│  Phaser Scene   │<──state────│  Game State Store  │
│  (Rendering)    │            │  (Objects, Props)  │
└─────────────────┘            └────────────────────┘
```

**Example Python server:**
```python
# rosh_repl_server.py
import asyncio
import websockets
import json
from rosh.interpreter import Interpreter

class RoshREPLServer:
    def __init__(self):
        self.interpreter = Interpreter()
        self.clients = set()

    async def handle_client(self, websocket):
        self.clients.add(websocket)
        try:
            async for message in websocket:
                # Parse command
                data = json.loads(message)
                command = data['command']

                # Execute in Rosh interpreter
                result = self.interpreter.execute(command)

                # Send back result
                await websocket.send(json.dumps({
                    'result': str(result),
                    'state': self.interpreter.get_state_diff()
                }))

                # Broadcast to all clients (multiplayer!)
                await self.broadcast_state()

        finally:
            self.clients.remove(websocket)

    async def broadcast_state(self):
        """Send state updates to all connected clients"""
        state = self.interpreter.get_state()
        message = json.dumps({'type': 'state_update', 'state': state})

        await asyncio.gather(
            *[client.send(message) for client in self.clients]
        )

# Run server
asyncio.run(websockets.serve(RoshREPLServer().handle_client, 'localhost', 8765))
```

**Example browser client:**
```javascript
class RoshREPLClient {
    constructor(scene) {
        this.scene = scene;
        this.ws = new WebSocket('ws://localhost:8765');

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);

            if (data.type === 'state_update') {
                this.updateGameState(data.state);
            } else {
                this.displayResult(data.result);
            }
        };
    }

    executeCommand(command) {
        this.ws.send(JSON.stringify({ command }));
    }

    updateGameState(state) {
        // Update Phaser objects based on interpreter state
        for (const [name, obj] of Object.entries(state.objects)) {
            if (!this.scene[name]) {
                // Create new object
                this.scene[name] = this.scene.add.rectangle(
                    obj.x, obj.y, obj.width, obj.height, obj.color
                );
            } else {
                // Update existing object
                this.scene[name].x = obj.x;
                this.scene[name].y = obj.y;
            }
        }
    }
}
```

**Pros:**
- ✅ Full Rosh language support
- ✅ All features work (functions, loops, imports, etc.)
- ✅ Multiplayer support built-in (broadcast state)
- ✅ Can save/load state via interpreter
- ✅ Consistent with standalone Rosh behavior

**Cons:**
- ❌ Requires Python server running
- ❌ Network latency (minimal for localhost)
- ❌ More complex setup
- ❌ Not offline-capable

---

#### Approach 3: Transpile-on-the-Fly (Future - Standalone Browser)

**Timeline:** 2-3 weeks
**Complexity:** High
**Power:** Full Rosh (browser-native)

**How it works:**
1. Port Rosh transpiler to JavaScript/TypeScript
2. Run transpiler in browser as Web Worker
3. Console sends Rosh code to transpiler
4. Transpiler generates JavaScript code
5. Browser eval()s generated code
6. Game updates immediately

**Pros:**
- ✅ No server needed
- ✅ Works offline
- ✅ Full Rosh language
- ✅ Can be embedded in any site

**Cons:**
- ❌ Large effort to port transpiler
- ❌ Need to maintain two codebases (Python + JS)
- ❌ Still uses eval() (security concerns)

**Recommendation:** Defer this until we have more transpiler targets. Once we have Phaser + Godot + Pygame, the patterns will be clearer for a shared transpiler core.

---

## Recommended Implementation Plan

### Phase 1: Prototype (v0.1.8 - 1-2 days)

**Goal:** Prove the concept with minimal viable REPL

**Deliverables:**
1. DOM console overlay (backtick toggles)
2. Command input with history (up/down arrows)
3. Simple command parser (set, create, trigger, get)
4. Integration with existing Phaser transpiler output
5. Example demo game with REPL enabled

**Demo script:**
```rosh
# Build game with REPL
rosh build examples/games/sprite-demo.rosh --target phaser --repl --output dist/

# Open in browser, press backtick, type:
create object powerup at 300, 200
set powerup.sprite to "coin.png"
set player.speed to 20
trigger damage with 50
get player.health
```

**Success criteria:**
- [ ] Console appears/disappears smoothly
- [ ] Basic commands execute and show results
- [ ] Game updates in real-time
- [ ] No crashes or performance issues
- [ ] Wow factor for demos ✨

**Test with users:**
- Show prototype to potential users
- Get feedback on command syntax
- Identify most-used commands
- Decide if worth building full version

---

### Phase 2: Full Implementation (v0.2.0 - 1 week)

**Goal:** Production-ready in-game REPL with full Rosh support

**Deliverables:**
1. Python WebSocket server with Rosh interpreter
2. Robust browser client with reconnection
3. State synchronization (server ↔ browser)
4. Multiplayer support (broadcast to all clients)
5. Command history saved to localStorage
6. Help system (`help`, `commands`, `describe`)
7. Security controls (localhost-only by default)
8. Documentation and examples

**New features:**
- Full Rosh syntax support
- Function definitions in REPL
- Import stdlib in REPL
- Save/load REPL session
- Auto-complete suggestions
- Syntax highlighting in console

**Demo script (advanced):**
```rosh
# Start server
rosh repl-server --port 8765

# Build game with REPL client
rosh build game.rosh --target phaser --repl ws://localhost:8765 --output dist/

# In browser console:
define function spawn_enemy as
    create object enemy from character
        set x to random 0 to 800
        set y to random 0 to 600
        set sprite to "enemy.png"
    end
    trigger enemy_spawned with enemy
end

# Call it multiple times
call spawn_enemy
call spawn_enemy
call spawn_enemy
```

**Success criteria:**
- [ ] WebSocket connection stable
- [ ] All Rosh features work in REPL
- [ ] Multiplayer sync works
- [ ] Performance acceptable (<50ms latency)
- [ ] Security model defined
- [ ] User documentation complete

---

### Phase 3: Multi-Platform (v0.3.0+ - Future)

**Goal:** In-game REPL for all platforms

**Platforms:**
1. **Phaser (browser)** - WebSocket or standalone
2. **Godot** - GDScript REPL via plugin
3. **Pygame** - Python REPL (easiest - native Python!)
4. **Minecraft** - Java plugin with command interpreter
5. **Unity** - C# REPL via plugin

**Multiplayer 3D worlds:**
- VR/AR headsets with voice input
- "Create a castle" → Rosh interprets → builds structure
- Collaborative world building
- Educational experiences

---

## Benefits & Use Cases

### 1. Live Game Development

**Scenario:** You're building a platformer and the jump height feels wrong.

**Without REPL:**
1. Stop game
2. Edit source code
3. Rebuild
4. Relaunch
5. Test jump
6. Repeat 10 times

**With REPL:**
1. Press backtick
2. Type: `set player.jump_strength to 15`
3. Try jump
4. Type: `set player.jump_strength to 18`
5. Try jump
6. Perfect! Copy value to source code

**Time saved:** 90% reduction in iteration time

---

### 2. Teaching & Learning

**Scenario:** Teaching kids to program with Rosh.

**Teacher demonstrates:**
- Projects game on screen
- Opens REPL
- Types commands in real-time
- Students see immediate results
- "Now you try on your computers!"

**Student explores:**
- Experiments with commands
- Makes mistakes safely (no permanent damage)
- Learns cause and effect immediately
- Shares discoveries ("Look what I made!")

---

### 3. Debugging & Inspection

**Scenario:** Bug in game - enemy health not decreasing.

**REPL session:**
```rosh
> get enemy.health
100

> describe enemy
Enemy object:
  x: 150
  y: 200
  health: 100
  max_health: 100
  armor: 50   # <-- Aha! Armor blocking damage

> set enemy.armor to 0
✓ enemy.armor = 0

> trigger damage with 20
✓ Triggered damage

> get enemy.health
80   # Now it works!
```

**Fix identified:** Forgot to subtract armor from damage calculation.

---

### 4. Demos & Presentations

**Scenario:** Presenting Rosh at a conference.

**Demo flow:**
1. Show simple game running
2. Press backtick (audience: "Ooh, what's that?")
3. Type: `create object dragon at 400, 300`
4. Dragon appears (audience: "Whoa!")
5. Type: `set dragon.sprite to "dragon.png"`
6. Colored box becomes dragon sprite (audience: "That's cool!")
7. Type: `when fire then trigger dragon_attack end`
8. Press space, dragon attacks (audience: "Amazing!")

**Wow factor:** ✨✨✨✨✨

---

### 5. Multiplayer Collaboration

**Scenario:** Two players building a world together.

**Player 1:**
```rosh
create object castle at 400, 200
set castle.sprite to "castle.png"
```

**Player 2 sees castle appear:**
```rosh
create object moat from object
    set x to 400
    set y to 350
    set sprite to "water.png"
end
```

**Player 1 sees moat appear:**
```rosh
create object drawbridge from object
    set x to 400
    set y to 325
    set sprite to "bridge.png"
end
```

**Together they've built a castle with moat and drawbridge - all in real-time, all with natural language code!**

---

### 6. Voice Integration (Future)

**Scenario:** VR headset with voice input.

**User speaks:**
- "Create enemy at my position"
- "Give player ten health potions"
- "Start wave two"

**Voice → Rosh REPL → Game state changes**

**Combined with Rosh's natural language syntax:**
- No awkward "commands" like `/spawn enemy 10 20`
- Just speak naturally: "create object enemy at 10, 20"
- AI can help translate: "make it bigger" → `set enemy.scale to 2`

---

## MVP Analysis: In-Game REPL vs Phaser Polish

### Option A: Build In-Game REPL (Prototype)

**Timeline:** 1-2 days for prototype
**Effort:** Low-Medium
**Impact:** HIGH

**What you get:**
- ✅ Killer demo feature (wow factor!)
- ✅ Validates original Rosh vision
- ✅ Useful for development immediately
- ✅ Differentiates Rosh from other languages
- ✅ Multiplayer foundation laid
- ✅ Fast iteration for future work

**What you don't get:**
- More polished game features
- Second transpiler target
- Game templates library

**Risks:**
- Prototype might not be impressive enough
- Could be too limited (frustrating)
- May need full implementation to be useful

**Recommendation:** Build prototype. If it's as cool as we think, invest in full implementation. If not, pivot to other priorities.

---

### Option B: Polish Phaser Games

**Sub-options:**

**B1: Audio & Animation (v0.1.8)**
- Background music & sound effects
- Sprite animation (sprite sheets)
- Particle effects

**Timeline:** 1 week
**Impact:** Medium

**B2: Game States (v0.1.8)**
- Pause/resume/restart
- Game over / win screens
- Main menu

**Timeline:** 3-4 days
**Impact:** Medium

**B3: Multiple Scenes/Levels (v0.1.9)**
- Scene transitions
- Level progression
- State preservation between scenes

**Timeline:** 1 week
**Impact:** Medium-High

**B4: Game Templates Library**
- Asteroids clone (<100 lines)
- Space Invaders clone
- Breakout clone
- Snake clone

**Timeline:** 1 week (for 4 templates)
**Impact:** High (for marketing)

**What you get:**
- ✅ More complete game engine
- ✅ Example games for demos
- ✅ Better user onboarding
- ✅ Demonstrates Rosh capability

**What you don't get:**
- The original vision (in-world REPL)
- Killer differentiating feature
- Multiplayer foundation

---

### Option C: Second Transpiler Target

**C1: Godot 2D (GDScript)**
**Timeline:** 2 weeks
**Impact:** High (proves portability)

**C2: Pygame (Python)**
**Timeline:** 1 week
**Impact:** Medium (easier to build, less impressive)

**What you get:**
- ✅ Proves Rosh is portable
- ✅ Reaches new audiences (desktop, mobile)
- ✅ Validates transpiler architecture
- ✅ More platforms = more users

**What you don't get:**
- In-game REPL
- More polished Phaser
- The "wow" factor

---

## Recommendation: Build In-Game REPL Prototype (1-2 Days)

**Why:**

1. **It's the original vision.** This is what Rosh was created for. Everything else is tactics - this is strategy.

2. **It's a killer demo feature.** Audio is nice, but live coding a game on stage? That's memorable.

3. **It's low-risk, high-reward.** 1-2 days to prototype. If it works, it's amazing. If not, we learned something and move on.

4. **It's useful immediately.** We'll use it ourselves to develop games faster.

5. **It unlocks multiplayer.** WebSocket architecture is foundational for multi-user Rosh.

6. **It differentiates Rosh.** Many languages compile to games. Few let you code inside the game.

7. **It aligns with voice vision.** Voice → REPL → game changes. This is the path to voice-driven game development.

**Concrete plan:**

**Days 1-2 (This Week):**
- Build JavaScript REPL prototype
- Add to sprite-demo.rosh example
- Test with simple commands
- Record demo video

**Decision Point:**
- If prototype is impressive → invest 1 week in full WebSocket implementation
- If prototype is underwhelming → pivot to game templates or Godot

**Days 3-7 (Next Week if prototype succeeds):**
- Build WebSocket server
- Implement state sync
- Add full Rosh language support
- Document and release as v0.2.0

**Later (v0.3.0+):**
- Port to Godot (in-editor console)
- Port to Minecraft (Java plugin commands)
- Voice integration (speech → REPL)
- Multiplayer 3D worlds

---

## Comparison Table

| Feature | In-Game REPL | Audio/Animation | Game States | Second Platform | Game Templates |
|---------|--------------|-----------------|-------------|-----------------|----------------|
| **Timeline** | 1-2 days (proto) | 1 week | 3-4 days | 1-2 weeks | 1 week |
| **Wow Factor** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Original Vision** | ✅ Yes | ❌ No | ❌ No | ⚠️ Supports | ❌ No |
| **Demo Impact** | Very High | Medium | Low | High | High |
| **User Value** | Very High | Medium | Medium | High | Medium |
| **Complexity** | Low (proto) | Medium | Low | High | Medium |
| **Multiplayer** | ✅ Enables | ❌ No | ❌ No | ❌ No | ❌ No |
| **Voice Future** | ✅ Critical | ❌ No | ❌ No | ❌ No | ❌ No |
| **Differentiator** | ✅✅✅ Unique | ⚠️ Common | ⚠️ Expected | ⚠️ Common | ⚠️ Nice |

---

## Next Steps

**If approved:**

1. **Immediate (Today):**
   - Create `examples/games/repl-demo.rosh` (copy of sprite-demo)
   - Add `--repl` flag to CLI
   - Scaffold RoshConsole JavaScript class

2. **Day 1:**
   - Implement DOM console UI (CSS + HTML)
   - Add keyboard listener (backtick toggle)
   - Build simple command parser
   - Test with `set`, `create`, `get` commands

3. **Day 2:**
   - Add command history
   - Implement `trigger`, `list`, `describe` commands
   - Polish UI (syntax highlighting, auto-complete)
   - Record demo video

4. **Demo:**
   - Show prototype to stakeholders
   - Gather feedback
   - Decide: full implementation or pivot?

**If rejected:**

Alternative priorities (in order):
1. Game templates library (Asteroids, Invaders, etc.)
2. Godot 2D transpiler (GDScript)
3. Audio & animation for Phaser
4. Multiple scenes/levels for Phaser

---

## Conclusion

**The in-game REPL is what Rosh was created for.**

It's the feature that makes Rosh unique. It's the path to voice-driven development. It's the foundation for multiplayer collaborative worlds. It's the "wow" moment in demos.

**And it's achievable in 1-2 days for a prototype.**

Low risk, high reward. Let's build it.

---

**Questions for User:**

1. Should we build the REPL prototype (1-2 days)?
2. If yes, which demo game should we use? (sprite-demo or create new?)
3. Should we plan for WebSocket server (full implementation) or keep it client-side only?
4. Any specific commands you want to prioritize for prototype?

**Ready to start immediately upon approval.**
