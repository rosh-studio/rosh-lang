# Rosh Ideas & Brainstorming Log

**Format:** Daily timestamped entries for ideas, pain points, and strategic direction

**Purpose:** Capture thinking as it happens, keep dated records, organize project vision

---

## 14-Dec-2025: Overnight Ideas - Documentation, Metadata & Tooling

**Context:** After completing v0.0.7 event system and code review fixes, focusing on project infrastructure and quality-of-life improvements.

### 1. Date Policy
**Decision:** Standardize on UK date format or ISO 8601 in all documentation
- Example: 14-Dec-2025 or 2025-12-14
- Consistency across tickets, changelogs, documentation
- Makes chronological sorting reliable

### 2. TOML Support (--toon flag)
**Priority:** First-order (high priority)
- TOML as JSON alternative for configuration
- `--toon` flag for TOML output mode
- Project manifests: `rosh.toml` (or `rosh.toon`)
- Modern, readable format for config files

### 3. Test Mode for Interactive Code
**Problem:** Can't run games with `input` in CI/CD
**Solution:** Test mode with mock inputs
- Mock `input` command for automated testing
- Mock `stop` command for clean test termination
- Enable CI/CD testing of interactive programs
- `rosh --test` flag or similar

### 4. AI Ticket/Review/Documentation System ⭐ HIGHEST PRIORITY
**Vision:** Self-documenting collaborative development with AI

**Workflow:**
1. AI creates ticket with self-identification
2. AI implements feature/fix
3. AI reviewer (different model) reviews work
4. Back-and-forth iteration until resolved
5. BDFL (human) final approval
6. Auto-documentation generation at scale

**Structure:**
- Tickets: `.rosh/tickets/YYYY-MM-DD-short-title.md`
- Archive: `docs/tickets/archive/YYYY/`
- Index: `docs/tickets/INDEX.md` (context management)

**Identity Tracking:**
- AI self-identifies in tickets (UUID + model)
- Human identified by Rosh username
- rdubar: `7f3e9a2b-4c1d-4e8a-9b5c-8d7a6f2e1c3b`
- Claude Sonnet 4.5: `a1b2c3d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d`

**Context Management:**
- Keep tickets < 1000 lines
- Archive implemented tickets
- INDEX.md for quick reference
- Prevents context bloat as project grows

### 5. Program Metadata System
**Goal:** Version tracking, security, package management foundation

**Proposed Structure:**
```rosh
meta
    version "1.0.0"
    rosh_version "0.0.7"
    author "rdubar"
    license "MIT"
    description "My game"
    uuid "auto-generated"
    checksum "auto-generated"
    security_key "auto-generated"
end

meta.game
    type "2D"
    engine "phaser"
end
```

**Considerations:**
- `meta.core` vs `meta.local` separation
- Public vs private/secret metadata
- Rosh.cloud integration for verification
- Offline operation with warnings
- Checksum + UUID + security_key validation

**Security Models to Evaluate:**
- **Fail-safe:** Warn user, allow continuation (convenience)
- **Fail-secure:** Refuse execution without verification (security)
- Network-optional verification
- Make recommendation in ticket

### 6. Project Folder Format
**Structure:**
```
my-game/
  rosh.toml          # Project manifest
  main.rosh          # Entry point
  src/               # Source files
  stdlib/            # Local stdlib extensions
  .rosh/
    tickets/         # Development tickets
    meta/            # Project metadata
```

**Benefits:**
- Clear organization
- Package management ready
- Multi-file projects
- Separates code from meta

### 7. get/set/go Paradigm
**Concept:** "go" means implement/run/reload
- get: retrieve value
- set: assign value
- go: execute changes, run program, reload state
- Natural command flow

### 8. dump Command
**Purpose:** Save current game state AND code together
**Addresses:** Ongoing serialization challenges
**Use Case:**
```rosh
dump game to "savegame.rosh"  # Saves state + code
load game from "savegame.rosh"
```
- Combined state/code serialization
- Easy save/load for games
- Debugging tool (snapshot runtime)

### 9. when Keyword ✅
**Status:** DONE in v0.0.7
- Event-driven programming
- Reactive game logic
- Already implemented with lexical scoping

### 10. spawn Keyword
**Purpose:** Process/thread management
**Future feature:** Multi-processing support
**Use Cases:**
- Spawn background processes
- Parallel game systems
- Multi-user server architecture

---

## Implementation Priority (14-Dec-2025)

**Immediate (v0.0.7+):**
1. ⭐ AI ticket/review system (infrastructure for all future work)
2. TOML support (--toon, rosh.toml manifests)
3. Test mode (CI/CD compatibility)
4. Metadata system (meta keyword, auto-generation)

**Near-term (v0.0.8-0.0.9):**
5. dump command (serialization)
6. Project folder structure
7. Security model decision & implementation

**Future:**
8. spawn keyword (multi-processing)
9. get/set/go paradigm refinement

---

## 14-Dec-2025: Advanced Game Features (Phaser Transpiler)

**Context:** After implementing sprite system (v0.1.7), thinking ahead about more complex game development needs.

### Game State Management

**Levels/Scenes:**
- Multiple game scenes (menu, level1, level2, game-over)
- Scene transitions with state preservation
- Level progression and unlocking

**Possible approaches:**
```rosh
# Option 1: Multi-file with scene objects
create scene main_menu
    set background to "menu.png"
end

create scene level1
    set background to "forest.png"
    set next_scene to level2
end

# Option 2: Scene switching with events
when level_complete then
    trigger switch_scene with "level2"
end

# Option 3: Import-based levels
import "levels/level1.rosh"
import "levels/level2.rosh"
```

**Challenges:**
- Phaser transpiler doesn't support imports (interpreter-only)
- May need scene bundling or code generation approach
- State persistence between scenes

### Pause/Resume/Restart

**Essential for real games:**
- Pause menu (Esc key, pause button)
- Resume game (unpause)
- Restart level (reset state)
- Quit to menu

**Possible approaches:**
```rosh
# Option 1: Built-in game states
when pause_pressed then
    pause game
end

when unpause_pressed then
    resume game
end

when restart_pressed then
    restart scene
end

# Option 2: Manual state management
create object game_state
    set paused to false
    set current_level to 1
end

when key_esc then
    set game_state.paused to not game_state.paused
end

# Option 3: Phaser scene methods (generated)
# Transpiler generates: this.scene.pause()
```

**Implementation considerations:**
- Need to generate Phaser scene lifecycle methods
- Pause should stop update loop but keep rendering
- Need UI overlay for pause menu

### Save/Load Game Progress

**User expectations:**
- Save progress (level, score, unlocks)
- Load saved game on restart
- Multiple save slots?

**Challenges:**
- Browser localStorage vs file system
- Phaser uses localStorage by default
- Rosh interpreter uses save/load commands (file-based)
- Need transpiler-specific save/load that uses localStorage

**Possible approach:**
```rosh
# In Phaser, save to localStorage
when level_complete then
    save_browser current_level to "progress"
end

# On game start, load from localStorage
when game_start then
    load_browser "progress" into saved_level
    if saved_level exists then
        set current_level to saved_level
    end
end
```

### More Complex Mechanics

**Physics & Collision:**
- Gravity, jumping, platforms
- Complex collision shapes (not just rectangles)
- Phaser Arcade Physics integration

**AI/Pathfinding:**
- Enemy AI (patrol, chase, flee)
- Pathfinding algorithms
- Behavior trees

**Particle Effects:**
- Explosions, trails, sparkles
- Phaser particle emitters

**Audio:**
- Background music
- Sound effects
- Volume control

**UI Systems:**
- Health bars, progress bars
- Dialog boxes, tooltips
- Inventory screens
- Skill trees

**Multiplayer:**
- Local multiplayer (split screen, hot seat)
- Online multiplayer (WebSockets)
- Turn-based vs real-time

### Strategic Direction

**Phase 1 (Current - v0.1.7):**
- ✅ Single scene games
- ✅ Basic sprites
- ✅ Simple collision
- ✅ Keyboard input

**Phase 2 (Next - v0.1.8?):**
- Pause/resume/restart
- localStorage save/load
- Background music & sound effects
- Sprite animation (sprite sheets)

**Phase 3 (Future - v0.2.x):**
- Multiple scenes/levels
- Advanced physics (gravity, jumping)
- Particle effects
- More complex UI

**Phase 4 (Later - v0.3.x+):**
- AI/pathfinding
- Multiplayer basics
- Advanced game mechanics

### Open Questions

1. **Scene management:** How do we handle multi-scene games without imports?
   - Generate all scenes in one file?
   - Build step that concatenates scenes?
   - Phaser scene manager integration?

2. **State persistence:** Browser vs interpreter differences
   - Unify save/load API?
   - Separate browser-specific commands?
   - Auto-detect environment?

3. **Physics:** When to add Phaser Physics?
   - Wait for user demand?
   - Add when we do platformers?
   - Optional opt-in flag?

4. **Complexity ceiling:** How far should Rosh Phaser go?
   - Simple games only?
   - Full game engine competitor?
   - Find the right balance?

**Decision:** Document these, get user feedback, prioritize based on real needs.

---

## Notes

- All ideas dated for chronological tracking
- Cross-reference with ROADMAP.md for scheduling
- Ticket system enables collaborative AI development
- Focus on infrastructure that scales with AI assistance
- Keep everything written down, dated, and organized
