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

### v0.0.7 - Event System (Q1 2025)
**Priority: HIGH - Enables complex game logic**

- [ ] Event syntax: `when condition then action end`
- [ ] Built-in MUD events (combat, navigation, quests)
- [ ] Event handlers and triggers
- [ ] Modulo operator
- [ ] Smart print inference (optional quotes)
- [ ] Sophisticated error recovery (multi-pass parsing)

**Example:**
```rosh
when player.health is below 0 then
    print "You died!"
    goto start_room
end
```

### v0.0.8 - Package System (Q2 2025)
**Priority: HIGH - Enables code sharing and distribution**

- [ ] Package manifest (rosh.manifest.json)
- [ ] Package manager commands (install, verify, publish)
- [ ] Hash verification for security
- [ ] Dependency resolution
- [ ] Package registry (hosted)

### v0.0.8.5 - AI Safety & Compliance (Q1 2025)
**Priority: CRITICAL - Required before multi-user**

- [ ] AI prompt vetting and sanitization
- [ ] Safety scanner for malicious content
- [ ] Audit logging system
- [ ] User warnings and education

### v0.0.9 - Multi-User Engine (Q2 2025)
**Priority: HIGH - Enables rosh.cloud**

- [ ] User authentication and sessions
- [ ] Networked message passing
- [ ] Concurrent user execution
- [ ] Shared world state
- [ ] User isolation and sandboxing
- [ ] Complete security audit

### v0.1.0 - Production Multi-User (Q2 2025)
**First production-ready release**

- [ ] Stable multi-user API
- [ ] Comprehensive testing (100+ automated tests)
- [ ] Performance optimization
- [ ] Production deployment to rosh.cloud
- [ ] Documentation and tutorials

---

## 🔮 Future Milestones

### v0.2.0 - Web Platform
- Web-based IDE
- Browser-based execution
- Real-time collaboration
- rosh.cloud public launch

### Milestones 10-14 - Transpilers (2026)
**Enable Rosh → Multiple Target Languages**

- **v0.3.0** - JavaScript transpiler (browser games, Phaser)
- **v0.4.0** - Lua transpiler (Love2D, Roblox)
- **v0.5.0** - GDScript transpiler (Godot engine)
- **v0.6.0** - Python transpiler (education, Pygame)

### v1.0.0 - Language Stability (2026+)
- Frozen syntax (no more breaking changes)
- Complete language specification
- Performance optimizations
- Production-ready for all use cases

### v1.5.0 - AI Game Studio (roshbosh) (2027+)
- Natural language game generation
- Template-based game creation
- AI-assisted coding
- Game gallery and sharing

### v2.0.0 - Rust Core (Optional, 2027+)
- High-performance core engine
- Better sandboxing and security
- Multi-platform deployment
- Backward compatible with v1.x

---

## 📊 Milestone Status

| Version | Status | Target | Priority |
|---------|--------|--------|----------|
| v0.0.6 | ✅ Complete | 2024-12-13 | - |
| v0.0.7 | 🔄 Planning | Q1 2025 | HIGH |
| v0.0.8 | 📋 Spec'd | Q2 2025 | HIGH |
| v0.0.8.5 | 📋 Spec'd | Q1 2025 | CRITICAL |
| v0.0.9 | 📋 Spec'd | Q2 2025 | HIGH |
| v0.1.0 | 🎯 Goal | Q2 2025 | CRITICAL |

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
