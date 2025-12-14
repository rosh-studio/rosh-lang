# Rosh Examples - Self-Teaching Tutorial

Welcome to Rosh! These examples are organized to help you learn progressively, from basics to advanced features.

## 🎯 Quick Start Guide

**Never used Rosh before?** Start here:
1. Read [basics/hello.rosh](basics/hello.rosh) - Your first program
2. Try [basics/counter.rosh](basics/counter.rosh) - Learn variables
3. Build [games/simple-game.rosh](games/simple-game.rosh) - Your first game!

**Want to build games?** Jump to:
- [games/](games/) - Browser games with Phaser

**Want to build text adventures?** Check out:
- [mud/](mud/) - Multi-User Dungeon (MUD) games

## 📚 Learning Path

### Level 1: Fundamentals (30 minutes)
**Folder:** [basics/](basics/)

Learn Rosh interpreter basics:
- ✅ [hello.rosh](basics/hello.rosh) - Hello World
- ✅ [counter.rosh](basics/counter.rosh) - Variables and math
- ✅ [conditional.rosh](basics/conditional.rosh) - If/else statements
- ✅ [loop-basic.rosh](basics/loop-basic.rosh) - While loops
- ✅ [math.rosh](basics/math.rosh) - Arithmetic operations

**After this level, you can:** Write simple programs with variables, loops, and conditionals.

[📖 Read the Basics Guide](basics/README.md)

---

### Level 2: Browser Games (1 hour)
**Folder:** [games/](games/)

Build interactive games that run in the browser:
- 🎮 [simple-game.rosh](games/simple-game.rosh) - Static objects
- 🎮 [hero-game.rosh](games/hero-game.rosh) - Player controls
- 🎮 [demo-percentages-hud.rosh](games/demo-percentages-hud.rosh) - Layout & UI
- 🎮 [mvp-demo.rosh](games/mvp-demo.rosh) - Complete game ⭐

**After this level, you can:** Create playable browser games with player controls, collisions, and HUD.

**How to build:**
```bash
rosh build examples/games/simple-game.rosh --target phaser --output dist/
open dist/index.html
```

[📖 Read the Games Guide](games/README.md)

---

### Level 3: Text Adventures (1-2 hours)
**Folder:** [mud/](mud/)

Create interactive fiction and text-based adventures:
- 📖 [mud-demo-complete.rosh](mud/mud-demo-complete.rosh) - Basic MUD
- 📖 [mud-world.rosh](mud/mud-world.rosh) - World building
- 📖 [dungeon-crawler.rosh](mud/dungeon-crawler.rosh) - Complete adventure ⭐

**After this level, you can:** Build complex text adventures with rooms, items, NPCs, combat, and quests.

**How to play:**
```bash
rosh examples/mud/dungeon-crawler.rosh
```

[📖 Read the MUD Guide](mud/README.md)

---

### Level 4: Advanced Features (2+ hours)
**Folder:** [advanced/](advanced/)

Master advanced Rosh concepts:
- 🔧 [inheritance-single.rosh](advanced/inheritance-single.rosh) - Object inheritance
- 🔧 [for-loops.rosh](advanced/for-loops.rosh) - For loop iteration
- 🔧 [type-annotations-demo.rosh](advanced/type-annotations-demo.rosh) - Type system
- 🔧 [object-management.rosh](advanced/object-management.rosh) - Object lifecycle

**After this level, you can:** Build sophisticated programs with inheritance, types, and advanced patterns.

[📖 Read the Advanced Guide](advanced/README.md)

---

### Level 5: AI Integration (30 minutes)
**Folder:** [ai/](ai/)

Learn how Rosh's natural syntax works with AI assistants:
- 🤖 [ai-hello.rosh](ai/ai-hello.rosh) - AI-generated code
- 🤖 [ai-codegen.rosh](ai/ai-codegen.rosh) - Complex generation
- 🤖 [ai-context.rosh](ai/ai-context.rosh) - Context-aware AI

**After this level, you can:** Effectively collaborate with AI to build games faster.

[📖 Read the AI Guide](ai/README.md)

---

## 🎓 Recommended Learning Paths

### Path A: Game Developer
1. **basics/** - Learn fundamentals (30 min)
2. **games/** - Build browser games (1 hour)
3. **advanced/** - Master advanced features (2 hours)
4. **ai/** - Supercharge with AI (30 min)

**Total time:** ~4 hours to game development mastery

### Path B: Interactive Fiction Writer
1. **basics/** - Learn fundamentals (30 min)
2. **mud/** - Build text adventures (2 hours)
3. **advanced/** - Add complexity (1 hour)
4. **ai/** - AI assistance (30 min)

**Total time:** ~4 hours to interactive fiction mastery

### Path C: Quick Start
1. [basics/hello.rosh](basics/hello.rosh) (2 min)
2. [games/simple-game.rosh](games/simple-game.rosh) (10 min)
3. [games/mvp-demo.rosh](games/mvp-demo.rosh) (20 min)
4. Build your own game! (∞)

**Total time:** 30 minutes to first game

---

## 🗂️ Folder Structure

```
examples/
├── basics/          # Interpreter fundamentals
│   ├── hello.rosh          - Hello World
│   ├── counter.rosh        - Variables
│   ├── conditional.rosh    - If/else
│   ├── loop-basic.rosh     - Loops
│   └── ... (15 examples)
│
├── games/           # Browser games (Phaser)
│   ├── simple-game.rosh         - Static scene
│   ├── hero-game.rosh           - Player controls
│   ├── demo-percentages-hud.rosh - Layout & UI
│   └── mvp-demo.rosh            - Complete game ⭐
│
├── mud/             # Text adventures
│   ├── mud-demo-complete.rosh   - Basic MUD
│   ├── mud-world.rosh           - World building
│   └── dungeon-crawler.rosh     - Complete adventure ⭐
│
├── advanced/        # Advanced features
│   ├── inheritance-single.rosh  - Inheritance
│   ├── for-loops.rosh           - Iteration
│   ├── type-annotations-demo.rosh - Types
│   └── ... (9 examples)
│
├── ai/              # AI integration
│   ├── ai-hello.rosh      - AI generation
│   ├── ai-codegen.rosh    - Code generation
│   └── ... (5 examples)
│
└── tests/           # Internal testing
    └── test-*.rosh        - Feature tests
```

---

## 🚀 Quick Commands

```bash
# Run an interpreter example
rosh examples/basics/hello.rosh

# Build a browser game
rosh build examples/games/mvp-demo.rosh --target phaser --output dist/

# Play a text adventure
rosh examples/mud/dungeon-crawler.rosh

# Interactive mode (REPL)
rosh

# Get help
rosh --help
```

---

## 📖 Documentation

Each folder has a detailed README:
- [basics/README.md](basics/README.md) - Interpreter fundamentals
- [games/README.md](games/README.md) - Browser games guide
- [mud/README.md](mud/README.md) - Text adventures guide
- [advanced/README.md](advanced/README.md) - Advanced features
- [ai/README.md](ai/README.md) - AI integration

Each game example has:
- **Header comment** explaining what it demonstrates
- **How to run** instructions
- **What you'll see** description
- **Key concepts** highlighted

---

## 💡 Tips for Success

1. **Start small** - Don't jump to complex examples
2. **Run every example** - Reading isn't enough, run the code!
3. **Modify examples** - Change values, add features
4. **Read the code** - Rosh is designed to be readable
5. **Use AI** - Ask AI to explain unfamiliar concepts
6. **Build something** - Apply what you learn immediately

---

## 🎯 Example Projects to Try

After completing the tutorials, try building:

### Beginner Projects
- 🎮 Pong game with player vs AI
- 📖 Choose-your-own-adventure story
- 🎲 Dice rolling game with scoring

### Intermediate Projects
- 🎮 Space shooter with enemies and power-ups
- 📖 Mystery game with clues and suspects
- 🎮 Platformer with jumping and obstacles

### Advanced Projects
- 🎮 RPG with combat, items, and progression
- 📖 Interactive fiction with branching narratives
- 🎮 Multiplayer game (future: rosh.cloud)

---

## 🐛 Troubleshooting

**Example doesn't run?**
```bash
# Check Rosh version
rosh --version

# Try verbose mode
rosh -v examples/basics/hello.rosh
```

**Browser game not working?**
```bash
# Verify JavaScript syntax
node --check dist/game.js

# Check browser console (F12)
# Look for error messages
```

**Confused about syntax?**
- Read the example's header comments
- Check the folder's README.md
- Ask an AI assistant to explain
- Read the Rosh manual

---

## 🤝 Contributing

Found an issue or want to add an example?
1. Test files go in `tests/`
2. Learning examples go in appropriate folders
3. Add header comments explaining the example
4. Update the folder's README.md

---

## 🎉 Ready to Start?

Pick your path:
- **Complete beginner?** → Start with [basics/hello.rosh](basics/hello.rosh)
- **Want games now?** → Jump to [games/simple-game.rosh](games/simple-game.rosh)
- **Love stories?** → Try [mud/dungeon-crawler.rosh](mud/dungeon-crawler.rosh)
- **Advanced user?** → Explore [advanced/](advanced/)

**Most important:** Have fun and build something awesome! 🚀

---

*All examples are self-documented and designed for self-teaching. No external tutorials needed!*
