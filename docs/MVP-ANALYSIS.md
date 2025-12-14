# MVP Analysis: What Should We Build Next?

**Date:** 2025-12-14
**Decision Needed:** In-Game REPL vs Polishing Phaser Games

---

## TL;DR Recommendation

**Build the in-game REPL prototype (1-2 days).**

**Why:** It's the original vision, it's a killer differentiator, it's low-risk, and it's what makes Rosh unique. If the prototype works, invest a week in the full implementation. If not, pivot to game templates.

---

## The Question

We've completed v0.1.7 (sprite system). What's the MVP for v0.1.8+?

**Option A:** In-game REPL (live coding inside games)
**Option B:** Polish Phaser (audio, scenes, game states, templates)

---

## Option A: In-Game REPL

### What It Is
A Quake-style console overlay in games where you type Rosh commands and see immediate results.

```
Press ` → Console appears
> create object dragon at 400, 300
✓ Created dragon
> set dragon.sprite to "dragon.png"
✓ dragon.sprite = "dragon.png"
> trigger fire
✓ Triggered fire
```

### Why It's the MVP

1. **It's the original inspiration for Rosh**
   - User's words: "This always was my insoration for rosh, btw, epeciallt in multi player 3d workds"
   - Everything else is tactics; this is strategy

2. **It's a killer differentiator**
   - Many languages compile to games
   - FEW let you code INSIDE the game
   - Immediate "wow" factor in demos

3. **It's low-risk, high-reward**
   - Prototype in 1-2 days
   - If it works → amazing feature
   - If it doesn't → we learned something, pivot quickly

4. **It's useful immediately**
   - We'll use it ourselves to develop faster
   - Iterate on games in real-time (no rebuild loop)
   - Debug issues live

5. **It unlocks the future**
   - Foundation for multiplayer collaborative worlds
   - Path to voice-driven development
   - Critical for VR/AR vision

6. **It aligns with demos**
   - Live coding on stage is memorable
   - Audio is nice, but THIS is special

### Timeline
- **Prototype:** 1-2 days (JavaScript-only, limited commands)
- **Full implementation:** 1 week (WebSocket server, full Rosh support)
- **Multi-platform:** Future (Godot, Minecraft, Unity)

### What You Get
✅ Killer demo feature
✅ Original vision validated
✅ Multiplayer foundation
✅ Useful development tool
✅ Unique differentiator
✅ Voice integration path

### What You Don't Get
❌ More game features (audio, scenes)
❌ Second transpiler target
❌ Game templates library

---

## Option B: Polish Phaser Games

### Sub-Options

**B1: Audio & Animation**
- Background music, sound effects
- Sprite animation (sprite sheets)
- Particle effects
- Timeline: 1 week

**B2: Game States**
- Pause/resume/restart
- Game over / win screens
- Main menu
- Timeline: 3-4 days

**B3: Multiple Scenes/Levels**
- Scene transitions
- Level progression
- State preservation
- Timeline: 1 week

**B4: Game Templates Library**
- Asteroids (<100 lines)
- Space Invaders
- Breakout
- Snake
- Timeline: 1 week for 4 templates

### Why It's Important

1. **More complete game engine**
   - Users can build "real" games
   - Not just tech demos

2. **Better demos**
   - Game templates show Rosh capability
   - Each template is a working example

3. **User onboarding**
   - More examples to learn from
   - Shows what's possible

### Timeline
- **Audio/Animation:** 1 week
- **Game States:** 3-4 days
- **Scenes/Levels:** 1 week
- **Templates:** 1 week

### What You Get
✅ More complete engine
✅ Better examples
✅ User onboarding
✅ Marketing demos

### What You Don't Get
❌ Original vision (REPL)
❌ Killer differentiator
❌ Multiplayer foundation
❌ Voice integration path

---

## Side-by-Side Comparison

| Criterion | In-Game REPL | Polish Phaser |
|-----------|--------------|---------------|
| **Aligns with original vision?** | ✅ Yes - THE inspiration | ❌ No - supporting feature |
| **Differentiates Rosh?** | ✅✅✅ Unique | ⚠️ Nice to have |
| **Demo wow factor?** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Enables multiplayer?** | ✅ Yes | ❌ No |
| **Enables voice integration?** | ✅ Critical path | ❌ Unrelated |
| **Time to prototype?** | 1-2 days | 3-7 days |
| **Risk level?** | Low (quick test) | Medium (bigger investment) |
| **Makes games more fun?** | ⚠️ Indirectly | ✅ Directly |
| **Production-ready?** | ⚠️ Needs iteration | ✅ Expected features |

---

## The Strategic Question

**What is Rosh?**

**If Rosh is "a game programming language":**
→ Polish Phaser (audio, scenes, templates)
→ Second transpiler (Godot)
→ Build the best game engine

**If Rosh is "live coding in your world":**
→ In-game REPL (prototype NOW)
→ Multiplayer collaborative worlds
→ Voice-driven development

**User's own words reveal the answer:**
> "This always was my insoration for rosh, btw, epeciallt in multi player 3d workds"

**Rosh is about live coding in multiplayer 3D worlds.**

The games are a vehicle for that vision, not the end goal.

---

## Recommended Strategy

### Phase 1: Validate the Vision (This Week - 1-2 Days)
**Build in-game REPL prototype**
- JavaScript-only
- Simple commands (set, create, trigger, get)
- Add to sprite-demo.rosh
- Record demo video

**Decision point:**
- If impressive → invest 1 week in full implementation
- If underwhelming → pivot to game templates

### Phase 2: Full Implementation (Next Week - If Prototype Succeeds)
**Build WebSocket-based REPL**
- Python server with full Rosh interpreter
- Browser client with state sync
- Multiplayer support (broadcast)
- Release as v0.2.0

### Phase 3: Polish & Examples (Following Weeks)
**Game templates library**
- Asteroids, Invaders, Breakout, Snake
- Each demonstrates REPL usage
- Marketing demos with "wow" factor

### Phase 4: Multi-Platform (v0.3.0+)
**Port REPL to all platforms**
- Godot (in-editor console)
- Minecraft (Java plugin commands)
- Unity (C# console)
- Voice integration

---

## Why This Strategy Works

1. **Low-risk validation** - 1-2 days proves/disproves the concept
2. **Aligns with vision** - Original inspiration gets tested first
3. **Fast feedback** - Know quickly if it's worth pursuing
4. **Flexible pivot** - If REPL fails, move to templates immediately
5. **Compound benefits** - REPL + templates = killer combo

**If REPL prototype succeeds:**
- Use REPL to build game templates faster
- Demos show live coding AND finished games
- "Build Asteroids in 10 minutes with REPL" video

**If REPL prototype fails:**
- We learned what doesn't work
- Pivot to game templates
- Only lost 1-2 days

---

## Alternative: Two-Track Approach

**Track 1 (Days 1-2):** Build REPL prototype
**Track 2 (Days 3-5):** Build 2 game templates

**Result after 1 week:**
- ✅ REPL prototype tested
- ✅ 2 game examples ready
- ✅ Decision data for full REPL implementation

**This maximizes optionality while validating the core vision.**

---

## Final Recommendation

**Build the in-game REPL prototype (1-2 days).**

**Why:**
- It's the original vision
- It's what makes Rosh unique
- It's low-risk to test
- It's the path to multiplayer + voice
- It's more impressive than audio/scenes

**After prototype:**
- If it works → full implementation (1 week)
- If it doesn't → game templates (1 week)

**Either way, we learn fast and build something valuable.**

---

## User Decision Needed

**Question:** Should we build the in-game REPL prototype this week (1-2 days)?

**Yes →** Start today, demo by end of week
**No →** Pivot to game templates or second transpiler

**What do you think?**
