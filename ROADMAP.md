# Rosh Development Roadmap

**Current Version:** v0.0.7
**Last Updated:** 2025-12-14

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

### v0.0.7 - Event System (2024-12-13) ✅ COMPLETE
- ✅ `when <event> then ... end` syntax
- ✅ `trigger <event>` command with parameters
- ✅ Lexical scoping (event handlers capture defining environment)
- ✅ Event loop stdlib (`stdlib/game-loop-simple.rosh`)
- ✅ Helper functions (`every()`, `stop_loop()`, `reset_ticks()`)
- ✅ Code review fixes (scoping, validation, import banner)
- ✅ Comprehensive test suite (137 total tests, 21 event-specific)

---

## 🚀 Upcoming Milestones

### v0.0.7 - Event System (Q1 2026) ✅ COMPLETE
**Priority: HIGH - Enables reactive game logic**

**Goal:** Add event-driven programming for NPCs, rooms, and game state reactions

**Features:**
- ✅ `when <event> then ... end` syntax
- ✅ `trigger <event>` command
- ✅ Event parameters (`when event param then`)
- ✅ Lexical scoping (handlers capture defining environment)
- ✅ Event loop stdlib (game-loop-simple.rosh)
- ✅ Helper functions (`every()`, `stop_loop()`, `reset_ticks()`)
- ✅ Comprehensive test suite (21 tests)

**Example:**
```rosh
when player_damaged health then
    if health is below 20 then
        print "Health critical!"
    end
end

trigger player_damaged with 15
```

**Status:** Implemented 2025-12-13, code review fixes 2025-12-14

---

### v0.0.8 - Infrastructure & Format Support (Q1 2026) ✅ COMPLETE
**Priority: CRITICAL - Foundation for AI-assisted development**

**Goal:** Systematic documentation, quality-of-life improvements, and modern format support

**Features:**
- ✅ AI ticket/review/documentation system
  - Ticket workflow in `.rosh/tickets/`
  - AI self-identification (UUIDs)
  - Cross-AI review process
  - BDFL approval workflow
  - Context management strategy
- ✅ TOML support (--toml flag)
  - TOML parser integration (tomllib/tomli)
  - `rosh.toml` project manifests
  - `--toml` output mode
  - Import TOML files as objects
- ✅ Test mode for CI/CD
  - Mock `input` command
  - `--test` and `--test-input` flags
  - Automated testing support
- ✅ Program metadata system
  - `meta` keyword with scopes (core, generated, game)
  - Auto-generated UUID, checksum, timestamps
  - Runtime access via `get meta.version`
  - Three scopes: core (version/author/license), generated (uuid/checksum), game (type/engine)
  - Implemented 2025-12-14 (same day as planned!)
- ✅ BACKLOG.md created for deferred features
- 🔄 Security model decision → DEFERRED TO BACKLOG
  - Not critical for single-user MVP
  - Revisit with v0.3.0 package system
- 🔄 Enhanced dump command → DEFERRED TO BACKLOG
  - Current dump works fine for now
  - Enhancements can wait for user feedback

**Why now:** These improvements enable scalable AI-assisted development and make Rosh more practical for real projects.

**Status:** Core infrastructure complete (2025-12-14). Security model and dump enhancements deferred to backlog.

---

### v0.0.9 - TOON Format Support (Q1 2026) ✅ COMPLETE
**Priority: HIGH - AI-first format optimization**

**Goal:** Add TOON (Token-Oriented Object Notation) support for AI-optimized state serialization

**Features:**
- ✅ TOON encoder implementation (Implemented 2025-12-14)
  - 40% fewer tokens than JSON
  - YAML-style indentation + CSV tables
  - `--toon` output flag
  - `save "file.toon"` support
- ✅ TOON decoder implementation (Implemented 2025-12-14)
  - Full round-trip support (save and load .toon files)
  - `load "file.toon"` support
  - Parses all TOON formats (primitives, arrays, objects, RoshObjects)
- ✅ TOON as opt-in format (Implemented 2025-12-14)
  - Explicit: `save "state.toon"` / `load "state.toon"`
  - JSON remains default for extensionless saves
  - User testing and feedback collection
- ✅ Comprehensive test suite (37 unit tests passing)
  - Encoder tests (16 tests)
  - Decoder tests (12 tests)
  - Round-trip tests (6 tests)
  - File operations tests (3 tests)
- ✅ Complete documentation in ROSH-MANUAL

**Why TOON:**
- 40% token reduction for AI/LLM workflows
- 73.9% vs 69.7% LLM parsing accuracy
- Human-readable, VR/AR memory efficient
- Aligns with AI-first language vision

**Timeline:** v0.0.9 full implementation (encoder + decoder)

**BDFL Decision (2025-12-14):**
- Full TOON support implemented (encoder + decoder)
- JSON remains default for extensionless saves
- TOON used explicitly via .toon extension
- Making TOON default for extensionless saves → Unassigned future decision

**Status:** ✅ COMPLETE (2025-12-14) - Full encoder and decoder support

---

### v0.1.0 - Transpiler Foundation (Q2-Q3 2026)
**Priority: HIGH - Cross-platform deployment**

**Goal:** Begin cross-platform transpilation to prove language portability

**Features:**
- [ ] Transpiler foundation (JavaScript/Phaser)
  - AST → JavaScript code generation
  - Phaser.js runtime bindings
  - Initial 2D game support
  - Same Rosh code runs in terminal (ASCII) and browser (graphics)

**Why this milestone:**
- Proves Rosh can target multiple platforms
- Enables browser deployment (zero install barrier)
- Foundation for future Unity/VR transpilation
- Browser games demonstrate AI-assisted creation potential

---

### v0.2.0 - Voice Demo + Phaser Transpiler (Q3 2026)
**Priority: HIGH - Proves AI-assisted creation**

**Goal:** Demonstrate natural language → playable game with visual output

**Features:**
- [ ] Voice input integration (Web Speech API or Whisper)
- [ ] Prompt engineering for game generation
- [ ] AI → Rosh code generation (GPT-4 or Claude)
- [ ] Phaser transpiler MVP
  - Browser-based 2D games
  - Sprite rendering and audio
  - Same code: terminal ASCII + browser graphics
- [ ] Demo video recording and editing

**Demo Flow:**
```
User (voice): "Create a dungeon with a goblin and treasure"
AI: [Generates Rosh code in real-time]
Terminal: [Text-based game runs]
Browser: [Same game with graphics via Phaser]
```

**Why now:**
- Proves VR vision WITHOUT needing VR hardware
- Shows AI-assisted creation (Roshbosh vision)
- Browser deployment = zero install barrier

**Timeline:** 4-6 weeks

---

### v0.3.0 - Package System (Q4 2026)
**Priority: MEDIUM - Enables code sharing**

**Goal:** Package manager and dependency resolution

**Features:**
- [ ] Package manifest (rosh.toml format)
- [ ] Local import/export
- [ ] Dependency resolution
- [ ] Package verification with checksums
- [ ] `rosh install` command
- [ ] Package repository (initial)

**Why now:** TOML + metadata system provides foundation

---

### v0.4.0 - Unity Transpiler MVP (2027)
**Priority: CRITICAL - Enables VR deployment**

**Goal:** Transpile Rosh → Unity C# for VR/AR platforms

**Features:**
- [ ] Unity C# code generation
- [ ] MonoBehaviour class mapping
- [ ] VR input handling (Quest, Vision Pro)
- [ ] 3D scene integration
- [ ] Voice command support in-headset

**Why now:** After browser proves concept, Unity enables VR deployment for enterprise

**Timeline:** 6-8 weeks

---

### v0.5.0 - Multi-User Engine (2027)
**Priority: HIGH - Enables rosh.cloud**

**Features:**
- [ ] User authentication and sessions
- [ ] Networked message passing
- [ ] Shared world state
- [ ] Event synchronization across clients

**Deferred:** Single-user demos must be solid first

---

## 🔮 Future Milestones

### v0.6.0 - Lua Transpiler (2027)
**Goal:** Roblox and Love2D support
- Lua code generation
- Roblox API bindings
- Love2D game framework integration

### v0.7.0 - GDScript Transpiler (2027)
**Goal:** Godot Engine support
- GDScript code generation
- Godot scene integration
- Open source game engine deployment

### v0.8.0 - roshbosh Platform Beta (Q2 2027)
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
| v0.0.7 | Event System | ✅ Complete | 2025-12-14 | - |
| v0.0.8 | Infrastructure & Format Support | ✅ Complete | 2025-12-14 | Security/dump→backlog |
| v0.0.9 | TOON Format (Encoder) | ✅ Complete | 2025-12-14 | Encoder complete (decoder→backlog) |
| v0.1.0 | Transpiler Foundation | 📋 Planned | Q2-Q3 2026 | JavaScript/Phaser transpiler |
| v0.2.0 | Voice Demo + Phaser | 📋 Planned | Q3 2026 | 4-6 weeks |
| v0.3.0 | Package System | 📋 Planned | Q4 2026 | - |
| v0.4.0 | Unity Transpiler | 📋 Planned | 2027 | 6-8 weeks |
| v0.5.0 | Multi-User | 🎯 Goal | 2027 | - |

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
