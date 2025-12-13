# Rosh Development Roadmap

**Current Version:** v0.0.6
**Last Updated:** 2025-12-13

> Technical milestones for the Rosh programming language.

---

## ✅ Completed Milestones

### v0.0.1 - Foundation (2024-10)
- Basic lexer, parser, interpreter
- Object creation and property management
- Stack-based operations
- REPL and file execution

### v0.0.2 - Control Flow (2024-10)
- if/then/else conditionals
- while loops
- Functions and parameters

### v0.0.3 - MUD Primitives (2024-10)
- Room navigation (goto, look, examine)
- Object relationships (connect, link)
- MUD standard library

### v0.0.4 - AI Integration (2024-11)
- prompt command for AI text generation
- prompt exec for AI code generation
- OpenAI integration
- AI error recovery

### v0.0.5 - String & List Operations (2024-12)
- String methods (split, substring, uppercase, lowercase, trim)
- String searching (indexOf, lastIndexOf)
- String concatenation, length, contains
- List append/remove/contains
- For loop list iteration

### v0.0.6 - Quality of Life (2024-12-13) ✅ COMPLETE
- ✅ String interpolation (`"Hello {name}!"`)
- ✅ User input command (`input`)
- ✅ else if conditionals
- ✅ NOT in compound expressions
- ✅ Multiline comments (`"""` and `###`)
- ✅ Type checking functions (is_number, is_string, is_list, is_object, is_null, is_boolean)
- ✅ List slicing (`my_list[1:3]`)
- ✅ Interactive mode (`-i` flag)
- ✅ Reserved word protection
- ✅ Complete documentation in ROSH-MANUAL.rosh

---

## 🚀 Upcoming Milestones

### v0.0.7 - Event System (Q1 2026) 🔄 IN PROGRESS
**Priority: HIGH - Enables reactive game logic**

**Goal:** Add event-driven programming for NPCs, rooms, and game state reactions

**Features:**
- [ ] `when <condition> then ... end` syntax
- [ ] `on <event> do ... end` syntax
- [ ] Event loop in stdlib (single-user, deterministic)
- [ ] Built-in MUD events (combat_start, player_move, item_taken)
- [ ] NPC reaction system
- [ ] Room ambient behaviors

**Example:**
```rosh
when player.health is below 20 then
    play sound "warning_beep"
    print "Health critical!"
end

on combat_start do
    set enemy.aggressive to true
    play music "battle_theme"
end
```

**Why now:** Events make games feel alive. NPCs react, rooms have behaviors, combat flows naturally.

**Timeline:** 2-3 weeks

---

### v0.0.8 - Voice → Game Demo (Q1 2026)
**Priority: HIGH - Proves AI-assisted creation**

**Goal:** Demonstrate natural language → playable game in 60-90 seconds

**Features:**
- [ ] Voice input integration (Web Speech API or Whisper)
- [ ] Prompt engineering for game generation
- [ ] AI → Rosh code generation (GPT-4 or Claude)
- [ ] Immediate execution (terminal or web client)
- [ ] Demo video recording and editing

**Demo Flow:**
```
User (voice): "Create a dungeon with a goblin and treasure"
AI: [Generates Rosh code in real-time]
Terminal: [Game runs immediately]
User: "north, attack goblin, open chest"
Game: [Playable dungeon crawler]
```

**Why now:**
- Proves VR vision WITHOUT needing VR hardware
- Shows AI-assisted creation (Roshbosh vision)
- Creates shareable content for social media
- Perfect for Product Hunt / investor demos

**Timeline:** 2-4 weeks (mostly prompt engineering)

---

### v0.0.9 - Phaser Transpiler MVP (Q2 2026)
**Priority: HIGH - Proves cross-platform transpilation**

**Goal:** Same Rosh code runs in terminal AND browser with graphics

**Features:**
- [ ] JavaScript code generation from Rosh AST
- [ ] Phaser.js runtime bindings
- [ ] 2D sprite rendering
- [ ] Mouse/touch input mapping
- [ ] Sound effects integration
- [ ] CLI: `rosh transpile --target phaser`

**Demo:**
```bash
rosh run dungeon.rosh           # Terminal: ASCII graphics
rosh transpile --target phaser  # Browser: sprites + sound
open index.html                 # Same game, visual!
```

**Why Phaser first:**
- ✅ JavaScript (simpler than C#/GDScript)
- ✅ Browser-based (zero install)
- ✅ 2D (easier than 3D)
- ✅ Proves transpilation concept

**Timeline:** 4-6 weeks

---

### v0.1.0 - Unity Transpiler MVP (Q3 2026)
**Priority: CRITICAL - Enables VR deployment**

**Goal:** Transpile Rosh → Unity C# for VR/AR platforms

**Features:**
- [ ] Unity C# code generation
- [ ] MonoBehaviour class mapping
- [ ] VR input handling (Quest, Vision Pro)
- [ ] 3D scene integration
- [ ] Voice command support in-headset

**Why now:** After browser proves concept, Unity enables VR deployment for enterprise

**Timeline:** 6-8 weeks (see TRANSPILER-UNITY-PLAN.md)

---

### v0.2.0 - Package System (Q4 2026)
**Priority: MEDIUM - Enables code sharing**

**Features:**
- [ ] Package manifest (rosh.manifest.json)
- [ ] Local import/export
- [ ] Dependency resolution
- [ ] Package verification

**Deferred from earlier:** Multiplayer comes first, packages can wait

---

### v0.3.0 - Multi-User Engine (2027)
**Priority: HIGH - Enables rosh.cloud**

**Features:**
- [ ] User authentication and sessions
- [ ] Networked message passing
- [ ] Shared world state
- [ ] Event synchronization across clients

**Deferred:** Single-user demos must be solid first

---

## 🔮 Future Milestones

### v0.4.0 - Lua Transpiler (2027)
**Goal:** Roblox and Love2D support
- Lua code generation
- Roblox API bindings
- Love2D game framework integration

### v0.5.0 - GDScript Transpiler (2027)
**Goal:** Godot Engine support
- GDScript code generation
- Godot scene integration
- Open source game engine deployment

### v0.6.0 - roshbosh Platform Beta (Q2 2027)
**Goal:** "Instagram for remixable mini-games"
- AI-powered game creation interface
- One-click remix functionality
- Social sharing and discovery
- Asset marketplace

### v1.0.0 - Language Stability (2027+)
- Frozen syntax (no more breaking changes)
- Complete language specification
- Production transpilers (Unity, Phaser, Lua)
- Comprehensive documentation

### v1.5.0 - rosh.cloud Enterprise Platform (2027+)
- Multi-user VR world hosting
- Enterprise licensing and billing
- Transpiler API services
- Team collaboration tools

### v2.0.0 - Rust Core (Optional, 2028+)
- High-performance core engine
- Better sandboxing and security
- Multi-platform deployment
- Backward compatible with v1.x

---

## 📊 Milestone Status

| Version | Feature | Status | Target | Timeline |
|---------|---------|--------|--------|----------|
| v0.0.6 | Quality of Life | ✅ Complete | 2025-12-13 | - |
| v0.0.7 | Event System | 🔄 In Progress | Q1 2026 | 2-3 weeks |
| v0.0.8 | Voice Demo | 📋 Planned | Q1 2026 | 2-4 weeks |
| v0.0.9 | Phaser Transpiler | 📋 Planned | Q2 2026 | 4-6 weeks |
| v0.1.0 | Unity Transpiler | 📋 Planned | Q3 2026 | 6-8 weeks |
| v0.2.0 | Package System | 📋 Planned | Q4 2026 | - |
| v0.3.0 | Multi-User | 🎯 Goal | 2027 | - |

---

## 🔧 Technical Debt & Cleanup

**Before v1.0:**
- [ ] Comprehensive error messages for all failure modes
- [ ] 100% test coverage for core features
- [ ] Performance profiling and optimization
- [ ] Memory leak detection and fixes
- [ ] Code documentation (docstrings)

---

## 📝 Documentation

**Key Technical Documents:**
- `ROSH-MANUAL.rosh` - Comprehensive tutorial (THE source of truth)
- `docs/DEVELOPMENT.md` - Development setup and workflow
- `docs/CONTRIBUTING.md` - Contribution guidelines
- `docs/ARCHITECTURE.md` - System architecture
- `docs/proposals/` - Feature proposals and designs

---

## 🎯 Focus & Niche

Rosh is specifically designed for:

1. **Interactive Fiction & MUDs**
   - Text-based adventures
   - Multi-user dungeons
   - Narrative-driven games

2. **Teaching Programming**
   - Natural language syntax
   - Voice-friendly (accessibility)
   - Gradual complexity

3. **Rapid Prototyping**
   - Game logic and narrative
   - AI-assisted development
   - Quick iteration cycles

**Not designed for:**
- ❌ High-performance computing
- ❌ Systems programming
- ❌ Large-scale enterprise applications

---

## 🤝 Contributing

See `docs/CONTRIBUTING.md` for development guidelines.

**Current Status:** Internal development only. External contributions will be accepted after v0.1.0.

---

*For complete roadmap with business context, see `../rosh-corporate/BUSINESS-PLAN.md` (private repo only)*
