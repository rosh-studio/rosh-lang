# Rosh Changelog

**Policy:** See docs/POLICIES.md for changelog guidelines

> Single chronological log of ALL changes. Never delete, only append.

---

## [Unreleased]

### Next Steps
- Record 60-second demo video ("Actual footage. Not faked.")
- ~~Simple landing page (slogan + signup only)~~ ✅ Done
- Outreach to contacts (Gregor Hofer, Soluis, etc.)
- ~~Update existing demos to use percentage-based coordinates~~ ✅ Done

---

## [0.1.18] - 2025-12-20 - Core Language Commands & REPL Improvements

### Added
- **Core Language Commands** (work in scripts AND REPLs)
  - `count` - Count all objects or by type (`count`, `count ball`)
  - `move <obj> to x, y` - Move object to coordinates

- **Known Objects System**
  - `create banana` now uses known object properties (not just empty object)
  - `create apple golden` creates "golden" of type "apple"
  - `clone banana` creates banana from known_objects.toml if doesn't exist
  - 37 known object types with pre-defined shapes/colors for 2D and 3D

- **REPL Help System** (CLI and Three.js)
  - `help create` - Shows create syntax and lists all known object types
  - `help make` - Shows make command usage
  - Commands without arguments show usage hints (e.g., `set` shows examples)

- **REPL-Only Commands** (documented in ISSUES.md)
  - `make <obj> bigger/smaller` - Relative scaling (×1.5 / ÷1.5)
  - `make <obj> <color>` - Change color
  - `make <obj> visible/hidden` - Show/hide

### Fixed
- Three.js: `create a banana` now creates "banana" (skips articles a/an/the)
- Three.js: `help create` now works in console
- CLI: `create <type> <name>` now correctly names the object
- Serialization: Changed `_type` property to `object_type` to avoid conflict

### Changed
- Usage hints for 15+ commands when called without arguments

---

## [0.1.12] - 2025-12-18 - Three.js Console Fixes & Meta Tests

### Added
- **Three.js Console Commands**
  - `create <description>` - Natural language object creation ("create big yellow ball")
  - `prompt <description>` - AI-style command interpretation
  - `examine` as alias for `look`/`inspect`
  - Object naming: created objects get meaningful names (ball, cube, sphere) with auto-increment

- **Implicit Meta Object Tests** (`tests/test_implicit_meta.py`)
  - 10 tests covering meta object behavior
  - Tests for: exists implicitly, set properties, nested properties, cannot create/delete, conditions
  - Protection is at parser level (syntax error, not runtime)

### Fixed
- **Three.js Emitter**
  - `meta` object now initialized (`const meta = { userData: {} }`)
  - `init_actions` now emitted (e.g., `set meta.phase to 1`)
  - `font_size` changes redraw text sprites in animation loop
  - `font_size` changes work in REPL console (`set logo font_size to 20`)
  - `color` changes preserve current font_size when redrawing
  - `look`/`examine` shows all userData properties including font_size

### Changed
- Help text updated to show `look/examine` instead of just `inspect`

---

## [2025-12-18] - Invisible State Objects & Save/Load

### Added
- **Save/Load Commands** - Persistence in REPL and console
  - Interpreter: `save`, `load`, `save as toon`, `save as json`
  - Three.js console: `save [slot]`, `load [slot]` using localStorage
  - Text sprite colors properly saved and restored

- **Console Improvements** (Three.js in-game REPL)
  - Command history with up/down arrows
  - `to` keyword optional in set command (`set logo color to yellow`)
  - Text color changes now work (`set logo color red`)

### Changed
- **Implicit `meta` Object** (Planned)
  - Global game state via `meta.property` syntax
  - Never rendered, always inspectable
  - No need to create fake state objects

### Fixed
- Cycle detection in `RoshObject.to_json()` prevents recursion errors
- Initial `visible: false` now applied at object creation in Three.js

---

## [2025-12-18] - Scene/Level System ("Dimensions, Not Modes")

### Added
- **Scene/Level Coordinates** - Roshonic "Dimensions, Not Modes" pattern
  - Objects can belong to scenes (named) and levels (numbered)
  - `set scene to "title"` - Object only visible in title scene
  - `set level to 1` - Object only visible in level 1
  - Objects without scene/level are always visible (HUD, backgrounds)
  - Syntax: `goto scene <name>`, `goto level <n>`, `goto scene <name> level <n>`

- **Scene/Level in All Emitters** - Same code works everywhere
  - Phaser: `this.currentScene`, `this.currentLevel`, `updateSceneVisibility()`
  - Pygame: `self.current_scene`, `self.current_level`, `update_scene_visibility()`
  - Three.js: `currentScene`, `currentLevel`, `updateSceneVisibility()`

- **GotoScene AST Node** - New AST node for scene navigation
  - Parser handles: `goto scene X`, `goto level Y`, `goto scene X level Y`
  - IR transformer creates goto action with scene/level params

### Changed
- **Level Property Semantics** - `level` alone is a regular property
  - Only treat `level` as coordinate when `scene` is also present
  - Allows games to use `level` for game state (e.g., space-shooter)
  - Roshonic: "Computers Do The Work" - guess intent from context

### Documentation
- Updated ROSHONIC.md with "Dimensions, Not Modes" principle
- Added scene/level spec to IDEAS.md

---

## [2025-12-18] - Pygame Emitter Polish & Demo Fixes

### Added
- **Pygame Emitter Improvements** - Full feature parity with Phaser
  - `_write_with_markers()` helper for proper Python indentation
  - `call` action support for function invocations
  - Sprite scaling via `pygame.transform.scale()` to match object dimensions
  - Text rendering with `pygame.font.Font` (was colored rectangles)
  - Visibility checks (`obj_visible`) for all game objects
  - Update event handlers (`when update then`)
  - Player detection via both `parent_type` and object name

- **Sound Asset Support** - Complete audio handling
  - CLI now copies both `sprite_assets` and `sound_assets`
  - Emitter scans function bodies for asset references
  - Finds assets like `laser1.ogg` inside `fire_bullet` function

- **Deploy Script** - `scripts/deploy-demos.sh`
  - Phaser builds → `rosh.cloud/demos/*-phaser/` (for web upload)
  - Pygame builds → `rosh.cloud/dist/*-pygame/` (local testing only)
  - Clear separation of web-ready and development builds

### Fixed
- **Pygame coordinate conversion** - Percentage values now convert to pixels
  - `_format_value()` accepts `context` parameter (x, y, width, height)
  - `set x to 50` correctly becomes `400` pixels, not `0.5`

- **Multiple key handlers** - Same key can have multiple event handlers
  - Changed `keydown_events` from `Dict[str, list]` to `Dict[str, List[list]]`
  - SPACE key can trigger both title→game and level1→level2 transitions

- **Block-pusher movement after level complete** - BUG-018
  - Added `if win_text.visible is equal to false then` to all movement handlers
  - Player can no longer move after "Level Complete!" message

- **Block-pusher sprite** - Restored correct player sprite
  - Found original 40x40 green smiley from git history (cd4aa24)
  - Replaced incorrect spaceship sprite

### Changed
- `demos/index.html` updated to point to `block-pusher-phaser/`
- Removed old `block-pusher/` folder (without suffix)
- `demos/rosh-intro/game.rosh` updated to use explicit `%` for centered text

### Removed
- **Dead Transpiler Code** - 200KB of legacy code removed
  - Deleted `src/rosh/transpilers/` folder entirely
  - Old files: `phaser.py` (97KB), `pygame_transpiler.py` (30KB), `threejs.py` (72KB), `base.py` (2KB)
  - Templates moved to `src/rosh/emitters/templates/`
  - CLI updated to use emitters path for templates
  - All targets now use clean IR-based emitter architecture

### Documentation
- **Coordinate Semantics Clarified** - Pixels by default, percentages explicit
  - Bare numbers are pixels: `set x to 400` = 400 pixels
  - Explicit percentages: `set x to 50%` = center of screen
  - Recommended pattern:
    - Use `%` for UI elements that should adapt to screen size
    - Use bare numbers for game logic with fixed coordinates (grids, etc.)
- **CLAUDE.md Updated** - Now defers to `rosh-dev/ROADMAP.md` for priorities
- **ROADMAP.md Updated** - Added v0.1.11 milestone, marked landing page complete

---

## [2025-12-18] - IR Architecture & Percentage Coordinates

### Added
- **Rosh IR (Intermediate Representation)** - LLVM-inspired architecture
  - `src/rosh/ir.py` - IR node dataclasses (IR_Program, IR_Object, IR_Event, etc.)
  - `src/rosh/ir_transformer.py` - AST → IR transformation with normalization
  - `src/rosh/emitters/` - New emitter package for IR → target code
  - `src/rosh/emitters/phaser.py` - Phaser 3 emitter (now used by CLI!)
  - Objects get UUIDs for stable identity across save/load
  - Coordinates normalized to 0.0-1.0 in IR, denormalized by emitters

- **IR Emitter Wired to CLI** - `rosh build --target phaser` now uses IR path
  - Flow: Parser → AST → IR Transformer → IR → Phaser Emitter → JavaScript
  - While loops now supported in Phaser builds (was unsupported before)
  - String interpolation `{var}` → JavaScript template literal `${this.var}`
  - Simple AABB collision detection (no Phaser physics needed)

- **Pygame IR Emitter** - `rosh build --target pygame` now uses IR path
  - `src/rosh/emitters/pygame.py` - Complete Pygame emitter from IR
  - Same IR produces both Phaser (JavaScript) and Pygame (Python)
  - Player movement, collision detection, HUD, sound all working

- **Three.js IR Emitter** - `rosh build --target threejs` now uses IR path
  - `src/rosh/emitters/threejs.py` - Complete Three.js emitter from IR
  - 3D scene with camera, lights, OrbitControls
  - Objects as 3D meshes (cubes, spheres, planes)
  - Player movement: Arrow keys (XZ) + . / (Y rise/fall)
  - Camera movement: WASD + QE (up/down)
  - Collision detection (distance-based)
  - HUD display (canvas text sprites)
  - Sound support (Three.js AudioListener)
  - In-game REPL console (press ` to toggle)
  - All three targets now use unified IR architecture

- **Percentage-Based Coordinates** - Engine-agnostic by default
  - `set x to 50` now means 50% (center), not 50 pixels
  - Same Rosh code works on Phaser (800px), Three.js (16 units), Unity, etc.
  - `set x to 400px` for explicit pixels when needed
  - `set x to 50%` also works (explicit percentage)
  - Both `400px` and `400 px` accepted (formatter normalizes to `400px`)

- **Natural Syntax Preferred** - Documented design decision
  - Prefer `set player color to green` over `set player.color to green`
  - Both parse identically, but natural form is spoken-friendly
  - AI-generated code should use natural form

### Changed
- Lexer now tokenizes `NUMBER_PX` (400px) and `NUMBER_PERCENT` (50%)
- Parser creates Literal nodes with type 'pixel' or 'percentage'
- IR transformer interprets bare numbers as percentages for coordinates
- Updated example files to use percentage-based coordinates:
  - `examples/games/simple-game.rosh` - uses bare numbers as percentages
  - `examples/games/hero-game.rosh` - uses bare numbers as percentages
  - `examples/tests/test-percentages.rosh` - demonstrates all syntax options

### Tests
- 283 tests passing (+52 new IR/emitter tests)

---

## [2025-12-18] - Case Insensitivity, main.rosh & Architecture Planning

### Added
- **Case-Insensitive Language** - Rosh now ignores case for keywords and identifiers
  - `CREATE OBJECT Hero` and `create object hero` are equivalent
  - `SET`, `Set`, `set` all work the same
  - Object names normalized to lowercase for consistent access
  - String literals preserve original case (only identifiers/keywords normalized)
  - Enables spoken-first/dictation-friendly coding

- **main.rosh Convention** - Run projects from directories
  - `rosh run my-game/` now runs `my-game/main.rosh` automatically
  - `rosh build my-game/ --target phaser` builds from main.rosh
  - Clear error message if directory has no main.rosh
  - Standard convention like package.json, main.py, etc.

- **_meta/ Folder Configuration** - Project settings via TOML files
  - `_meta/project.toml` for general project settings
  - `_meta/{target}.toml` for target-specific overrides (e.g., `phaser.toml`)
  - Canvas dimensions configurable: `[canvas] width = 1024, height = 768`
  - Target settings merge with project settings (deep merge)
  - Works with all transpilers (Phaser, Pygame, Three.js)

### Documentation
- Added `LANGUAGE-ARCHITECTURE-DISCUSSION.md` - Future architecture vision
- Added `IMPLEMENTATION-PLAN-PHASE1.md` - Quick wins roadmap
- Demos moved to `rosh.cloud/demos/` (hosted, password-protected)

---

## [2025-12-17] - AI Prompt & Context-Aware Commands

### Added
- **🤖 AI Prompt Command (Main REPL)** - Natural language with real AI
  - `prompt exec create a goblin` → generates Rosh code, asks confirmation, executes
  - `prompt create a goblin` → shows AI suggestion (no execution)
  - Works without quotes: `prompt create a big blue ball` (no need for `"..."`)
  - Rosh-aware system prompt - AI knows Rosh syntax, generates valid code
  - Safety: requires user confirmation before executing AI-generated code

- **🤖 AI Prompt Command (Three.js)** - Phase 1 demo with fuzzy matching
  - `prompt create a big blue ball` → creates blue sphere
  - Fuzzy keyword matching for demo ("big", "blue", "ball" → sphere)
  - Shows generated Rosh command before execution
  - Hardcoded responses for video demo (Phase 2 will add real AI)

- **Runtime Object Creation** - `create object` command in Three.js console
  - `create object ball` (default cube)
  - `create object ball with type sphere color blue radius 2`
  - Supports: cube, sphere, plane
  - Properties: type, color, radius, width, height, depth, x, y, z
  - Auto-generates UUID for each object

- **Context-Aware Commands** - `get` sets current object for subsequent commands
  - Works in: Main REPL, Three.js console, Phaser REPL
  - `get logo` → sets logo as current object
  - `set color green` → applies to current object (no need to specify)
  - Matches natural command flow

- **Flexible `set` Syntax** - `to` keyword now optional
  - `set logo color green` works (without "to")
  - `set logo color to green` also works (with "to")
  - `set color green` works after `get logo`

- **Simple Homepage** - rosh.cloud landing page
  - Logo + tagline "One language. Many worlds."
  - Email signup form (Buttondown integration)
  - Minimalist design, mobile-friendly

### Fixed
- **BUG-001:** Main REPL `set` now updates object properties after `get`
- **BUG-002:** Three.js console `set` command now works
- **BUG-003:** `get <object>` now sets current context (all REPLs)
- **BUG-004:** `set` no longer requires `to` keyword (all REPLs)
- **JS Syntax Error:** Escaped backtick in template literal
- **Prompt parsing:** `prompt` command now accepts unquoted text

### Technical
- Modified: `src/rosh/interpreter.py`
  - Added `current_object` and `current_object_name` tracking
  - Added Rosh-aware system prompt for AI responses
- Modified: `src/rosh/parser.py`
  - `prompt` command now collects unquoted text as message
- Modified: `src/rosh/transpilers/threejs.py`
  - Added `currentObject` tracking, `create object`, `prompt` commands
  - Changed CSS class `info` → `cyan` to avoid conflicts
- Modified: `src/rosh/transpilers/phaser.py`
  - Added `currentObject` tracking, flexible `set` syntax

---

## [2025-12-15] - In-Game REPL Phase 1 Complete (Ticket #009)

### Added
- **🎮 In-Game REPL Console** - Live coding inside Phaser games (dev-only feature)
  - `--repl` flag for build command enables console overlay
  - Natural language commands: list, set, get, create, properties, trigger, help, clear
  - Multiple aliases per command (list/look/ls/show/objects)
  - Fuzzy matching for typo correction (Levenshtein distance)
  - Percentage support (`set hero.x to 50%`)
  - "middle" alias for 50% (`set hero.x to middle`)
  - Toggle with backtick (`) or F12 key
  - Terminal-style UI (green-on-black, scrollable output)
  - Command history (up/down arrows)
  - Error handling (commands never crash game)
  - All commands tested in Chrome & Safari

- **Shorthand Position Syntax** - Comma-optional coordinates
  - `create object hero at 100 300` (works in both source files and REPL)
  - `create object hero at 100, 300` (also works)
  - Added `AT` token to lexer
  - Parser support for position shorthand

- **Polished Demo** - Professional demo with Kenney.nl graphics
  - `demos/repl-demo/` with hero, enemies, coins sprites
  - Player controls (arrow keys)
  - Comprehensive README.md with consultancy pitch
  - Asset attribution in examples/games/assets/CREDITS.md

- **Demo Quality Policy** - Added to POLICIES.md
  - Requirement: Polish demos before committing
  - Use professional graphics (Kenney.nl assets, not colored rectangles)
  - Test in multiple browsers (Chrome + Safari minimum)
  - Complete documentation with commands and use cases

- **REPL Documentation** - Added to examples/games/README.md
  - Complete "Live Coding with the Rosh Console" section
  - Command reference with examples
  - Use cases (prototyping, debugging, live demos)
  - Security warnings (dev-only)
  - Link to polished demo

### Fixed
- **Sprite Display** - Sprites now render at correct size
  - Added `setDisplaySize()` call after image creation
  - Sprite loading with `.png` extension auto-appending
  - Proper fallback to rectangles if sprites missing

### Technical
- Modified files:
  - `src/rosh/lexer.py` - Added AT token
  - `src/rosh/parser.py` - Shorthand position syntax
  - `src/rosh/transpilers/phaser.py` - REPL generation (~400 lines)
  - `rosh-corporate/docs/POLICIES.md` - Demo quality standards
  - `examples/games/README.md` - REPL documentation
  - `demos/repl-demo/game.rosh` - Professional demo
  - `demos/repl-demo/README.md` - Demo documentation

### User Validation
- **Status:** Phase 1 COMPLETE and user-validated
- **Feedback:** "fuck me this is impressive" - "What other gaming systems out there allow you to make up a 2d game as you go along?"
- **Impact:** "Great progress after 3 days"

### Deferred to Future Tickets
- Function support in Phaser transpiler (required for `define function` / `call` pattern)
- Meta settings support (required for `set meta show_console to true`)

---

## [2025-12-14] - Documentation & Strategic Planning

### Added
- **IN-GAME-REPL-PROPOSAL.md** - Comprehensive proposal for live coding inside games
  - Three implementation approaches (JavaScript prototype, WebSocket server, standalone)
  - Use cases: live development, teaching, debugging, demos, multiplayer
  - Implementation timeline and phases
  - THE original inspiration for Rosh (especially multiplayer 3D worlds)

- **MVP-ANALYSIS.md** - Strategic analysis of priorities
  - In-game REPL vs Phaser polish comparison
  - Recommendation: Build REPL prototype (1-2 days)
  - Risk/reward analysis
  - Platform progression strategy

### Updated
- **IDEAS.md** - Advanced game features brainstorming
  - Game state management (levels/scenes)
  - Pause/resume/restart mechanics
  - Save/load strategies
  - Complex mechanics (physics, AI, audio, UI, multiplayer)
  - Strategic roadmap phases

---

## [v0.1.7] - 2025-12-14

**Sprite/Image Support** - Transform Rosh from colored boxes to real game graphics!

### Added
- **Sprite property support**
  - Syntax: `set sprite to "hero.png"`
  - Must use literal strings (transpiler limitation)
  - Works with all object types (player, character, object)

- **Automatic asset preloading**
  - Generates Phaser `preload()` method
  - Loads all referenced sprites before game starts
  - Prevents missing texture errors

- **Graceful fallback rendering**
  - Missing sprites → colored rectangles (game still works!)
  - Console warnings: `⚠️ Texture not found: hero.png`
  - No fatal errors from missing assets

- **Smart asset copying**
  - New `--copy-assets` flag
  - Selectively copies ONLY referenced sprites
  - Organized output: `dist/assets/hero.png`
  - Clear console output: `📦 Copied: hero.png`

- **6300+ free game assets included**
  - Kenney's asset collection (kenney.nl)
  - Selection from zapcoder's compilation
  - Characters, enemies, items, environments, UI
  - All organized in `examples/games/assets/`
  - Full attribution in CREDITS.md

- **Python web server workflow**
  - ALWAYS shown (prevents CORS issues)
  - Instructions: `cd dist/ && python3 -m http.server 8000`
  - Works offline, no external dependencies

### Changed
- CLI output always shows web server instructions (not just when sprites detected)
- Prevents user confusion when they add sprites later

### Documentation
- **examples/games/README.md**
  - Added "Phaser Transpiler Limitations" section
  - Documented sprite literal string requirement
  - Troubleshooting guide for sprite loading
  - Clear warnings about MUD examples (don't transpile!)

- **docs/tickets/SPRITE-SYSTEM-TICKET.md**
  - Moved from root to organized location
  - Added Codex review feedback section
  - Complete testing documentation (8 tests)
  - Status: Complete and Reviewed

### Testing
- **8 new comprehensive tests** (32 total Phaser tests)
  - `test_sprite_preload_generation` - Preload method creation
  - `test_sprite_fallback_rendering` - Graceful fallback logic
  - `test_sprite_assets_tracking` - Asset dictionary tracking
  - `test_mixed_sprites_and_rectangles` - Hybrid objects
  - `test_no_sprites_no_preload` - Conditional preload
  - `test_sprite_with_player_auto_controls` - Integration with player system
  - `test_multiple_sprites_preload` - Multi-asset games
  - `test_sprite_literal_string_only` - Validation of limitation

### Impact
**Transforms Rosh from "toy examples with colored boxes" to "real games with professional graphics."**

Before v0.1.7: Only colored rectangles
After v0.1.7: Real game graphics with 6300+ free assets!

---

## [v0.1.6] - 2025-12-14

**Input + Events in Phaser** - Auto-controllable player objects with smart defaults!

### Added
- **Event system (`when/trigger`) in Phaser transpiler**
  - Transpiles interpreter event syntax to Phaser events
  - Event handler registration in `create()`
  - Update loop with event triggering
  - Property mutations in event handlers work
  - Trigger statements with parameters

- **Object inheritance (`create object X from Y`)**
  - Syntax: `create object hero from player`
  - Base types: `player`, `character`, `object`
  - Smart defaults by type
  - Property override (not addition)

- **Player auto-controls - JUST WORKS!**
  - Arrow keys automatically move player objects
  - Space bar triggers 'fire' event
  - ZERO event handlers needed for basic games
  - Uses `speed` property for movement (default: 5)

- **Smart defaults for player objects**
  - `lives: 3`, `score: 0`, `speed: 5`
  - Auto-generated HUD display (lives/score)
  - Can override any default

- **Special properties**
  - `fixed: true` - Object doesn't get auto-controls
  - `lives`, `score` - Auto-display in HUD
  - `speed` - Movement speed for player objects

- **Keyboard input**
  - Automatic keyboard setup in `create()`
  - Arrow keys, space bar, and custom keys
  - Events: `key_pressed`, `space_pressed`, `update`

### Examples
```rosh
# This is ALL you need for a controllable player!
create object hero from player
    set x to 400
    set y to 300
end

# Automatically gets:
# - Arrow key movement
# - Space bar fire
# - Lives/score HUD
# - All with ZERO event handlers!
```

### Testing
- **20+ new tests** for events, inheritance, auto-controls, HUD
- All 35+ Phaser tests passing

### Impact
**80% less code for simple games!**

Before: 50+ lines of keyboard handling
After: 3 lines to create controllable player

---

## [v0.1.5] - 2025-12-14

**Phaser Transpiler MVP** - Rosh games run in ANY browser, zero install!

### Added
- **JavaScript/Phaser transpiler** (`rosh build --target phaser`)
  - Full transpiler architecture in `src/rosh/transpilers/phaser.py`
  - Objects → Phaser colored rectangles
  - Print statements → `console.log()` with string interpolation
  - Fail-fast error handling (unsupported features error immediately)

- **Browser deployment**
  - Zero-install (runs in any browser)
  - Generates `game.js`, `index.html`
  - Uses Phaser 3.70.0 from CDN
  - Works offline after first load

- **String interpolation support**
  - `"Hello {name}"` → `` `Hello ${name}` ``
  - Works in both interpreter and transpiler
  - Nested expressions supported

- **Validation system**
  - Pre-transpile AST validation
  - Clear error messages for unsupported features
  - Lists all validation errors at once

### Documentation
- **examples/games/README.md** - Phaser game development guide
- **examples/games/mvp-demo.rosh** - Working example game

### Testing
- **15 comprehensive unit tests**
- **7 integration tests**
- JavaScript validation with `node --check`
- Browser testing workflow

### Example
```bash
# Write Rosh code
create object goblin
    set x to 100
    set y to 200
end

# Transpile to Phaser
rosh build game.rosh --target phaser --output dist/

# Open in browser → See colored rectangle at (100, 200)!
```

### Impact
**Rosh games can now run anywhere without installing anything!**

---

## [v0.0.9] - 2025-12-14

**TOON Format Support** - 40% fewer tokens than JSON for AI-native serialization!

### Added
- **TOON encoder** (`src/rosh/toon_encoder.py`)
  - Converts Python values to TOON format
  - Supports: str, int, float, bool, None, list, dict, objects
  - Smart indentation and formatting
  - Special handling for Rosh objects

- **TOON decoder** (`src/rosh/toon_decoder.py`)
  - Parses TOON format back to Python values
  - Robust error handling with line numbers
  - Validates TOON syntax

- **File operations**
  - `save game to "state.toon"` - Saves as TOON
  - `load game from "state.toon"` - Loads TOON files
  - Auto-detection: `.toon` extension → TOON format
  - Default remains JSON (explicit `.toon` required)

- **Round-trip support**
  - All Rosh types serialize and deserialize correctly
  - Preserves object structure and properties
  - Maintains data integrity

### Testing
- **37 comprehensive unit tests**
  - Encoder tests (primitives, collections, objects)
  - Decoder tests (parsing, validation, errors)
  - Round-trip tests (JSON parity)
  - File operations tests

### Impact
**40% token reduction for AI context!**

Example state:
- JSON: 450 tokens
- TOON: 270 tokens (40% savings!)

---

## [v0.0.7] - 2025-12-14

**Event System** - Reactive programming for game logic!

### Added
- **Event-driven programming**
  - Syntax: `when <event> then ... end`
  - Register event handlers
  - Trigger events with parameters: `trigger player_damaged with 15`
  - Lexical scoping for event handlers

- **Event loop stdlib helpers**
  - `every(seconds, event_name)` - Periodic events
  - `stop_loop()` - Stop event loop
  - Timer-based event triggering

- **Built-in event handlers**
  - `when start` - Game initialization
  - `when update` - Every frame
  - `when key_pressed` - Keyboard input
  - Custom events via `trigger`

### Examples
```rosh
when player_damaged then
    set player.health to player.health minus damage
    if player.health is below 0 then
        trigger game_over
    end
end

trigger player_damaged with 15
```

### Testing
- **21 comprehensive event tests**
- All pass successfully

### Impact
**Enables reactive game logic without polling loops!**

---

## [v0.0.6] - 2025-12-13

**Quality of Life Release** - Massive improvements to language usability based on real-world usage!

### New Features ✨

### Added
- **String interpolation** 🎉
  - Syntax: `"Hello {name}, you are {age} years old!"`
  - Works with any expression: `"{x plus y}"`
  - Works with object properties: `"{player.health}/{player.max_health}"`
  - Implemented via interpreter-level regex parsing
  - Added Section 28 to ROSH-MANUAL.rosh
  - Resolves issue #113 from dungeon crawler pain points

- **`input` command for user input** 🎮
  - Syntax: `input variable_name`
  - Reads line from stdin and stores in variable
  - Essential for interactive games
  - Added TOKEN type, parser support, interpreter eval_input
  - Added Section 29 to ROSH-MANUAL.rosh (commented examples)
  - Resolves issue #96 from dungeon crawler pain points

- **`else if` syntax support** 🌿
  - Natural conditional chaining without deep nesting
  - Works as syntactic sugar for nested if statements
  - Example: `if x then ... else if y then ... else ... end`
  - Parser modification to parse_if method
  - Updated Section 5 in ROSH-MANUAL.rosh
  - Resolves issue #132 from dungeon crawler pain points

- **Modulo operator** 🔢
  - Syntax: `set remainder to x modulo y`
  - Returns remainder after division
  - Includes division-by-zero protection
  - Example: `17 modulo 5` → `2`

- **Increment/Decrement shortcuts** ⚡
  - Syntax: `increment x` and `decrement x`
  - Much cleaner than `set x to x plus 1`
  - Works with both variables and object properties
  - Examples:
    - `increment score`
    - `decrement player.health`
    - `increment game.level`

### Fixed
- **`not` in compound boolean expressions** ✅
  - Fixed parser to allow: `if x and not y then`
  - Fixed parser to allow: `if not x or y then`
  - Fixed parser to allow: `if x is above 3 and not y is below 5 then`
  - Created `parse_condition_term()` helper for proper NOT handling
  - Updated Section 4 in ROSH-MANUAL.rosh with examples
  - Resolves issue #76 from dungeon crawler pain points

### Changed
- Updated feature summary in ROSH-MANUAL.rosh
  - Added string interpolation to feature list
  - Added input command to feature list
  - Updated conditionals entry to mention "else if"
  - Updated boolean logic entry to mention "NOT in compound expressions"
- Version bumped from v0.0.5 to v0.0.6 in pyproject.toml

### Documentation
- Updated ISSUES.md:
  - Moved 4 issues to Resolved (not, input, string interpolation, else if)
  - Updated "Active Issues" to show no critical blockers
  - Added detailed resolution information for each fix
- Updated IDEAS.md:
  - Marked all v0.0.6 features as ✅ DONE!
  - Updated pain points section with resolution date

### Testing
- Verified ROSH-MANUAL.rosh runs successfully with all new features
- Created and tested:
  - test_not_compound.rosh (NOT in compound expressions)
  - test_input.rosh (input command)
  - test_interpolation.rosh (string interpolation)
  - test_else_if.rosh (else if syntax)
- All tests passed successfully

### Impact
This release addresses the top pain points discovered while building the dungeon-crawler.rosh demo:
- String interpolation reduces message code from 5+ lines to 1 line
- `input` command enables truly interactive games
- `else if` eliminates deep nesting hell
- `not` in compounds allows natural boolean logic

Before v0.0.6, printing a formatted message required:
```rosh
print "Health: "
get player.health
print stack
print " / "
get player.max_health
print stack
```

After v0.0.6:
```rosh
print "Health: {player.health} / {player.max_health}"
```

**This makes Rosh actually usable for real game development!**

---

### Documentation (2024-12-12)
- Created comprehensive POLICIES.md
- Created ISSUES.md for bug tracking
- Created CHANGELOG.md (this file)
- Renamed rosh_ideas_direction.md to IDEAS.md
- Created docs/proposals/EVENT-SYSTEM.md specification
- Created docs/TRANSPILER-ROADMAP.md
- Created docs/HOSTING-PLATFORMS.md
- Updated PROJECT-PLAN.md with:
  - Transpiler priorities (JavaScript, Lua, GDScript, Python)
  - Rust migration strategy (v2.0+)
  - Event system (v0.0.7)
  - Hosting strategy (rosh.cloud)
  - Multi-user roadmap (v0.1.0)

---

## [v0.0.5] - 2024-12-12

### Added
- **Function return value assignment** (Commit: d32df9c)
  - Can now do: `set value to call double 15`
  - Parser supports `call` in expressions
  - Updated ROSH-MANUAL.rosh with examples

- **Stack operations** (Commit: d32df9c)
  - New `stack` command to view data stack
  - Non-destructive stack viewing
  - Updated ROSH-MANUAL.rosh Section 27

- **REPL improvements** (Commit: d32df9c)
  - Type variable name alone to see value
  - No need for `print` in REPL
  - Example: `rosh> x` shows value of x

- **Comprehensive help system** (Commit: d32df9c)
  - Help for all 45+ commands
  - Clear alias documentation (stop=exit, say=print, etc.)
  - Organized into categories

- **For loop list iteration** (v0.0.5 release)
  - Syntax: `for item in my_list then`
  - Iterate over list elements
  - Updated ROSH-MANUAL.rosh

- **String methods** (v0.0.5 release)
  - split: `split text by delimiter`
  - substring: `substring of text from start length len`
  - uppercase/lowercase: Case conversion
  - trim: Remove whitespace
  - indexOf/lastIndexOf: Search strings
  - Updated ROSH-MANUAL.rosh

### Changed
- Updated ROSH-MANUAL.rosh to v0.0.5
  - Added Section 27 (Stack Operations)
  - Updated feature summary
  - Added type annotations examples
  - All 756 lines run successfully

- Simplified README.md installation
  - Single installation path (uv tool install)
  - Removed duplication
  - Clear upgrade instructions

### Documentation
- Created QUICK-START.md
  - User-friendly installation
  - Developer setup separate
  - Easy upgrade path

- Updated PROJECT-PLAN.md
  - Testing policy added
  - Recent accomplishments tracked
  - Status reflects v0.0.5 features

- Testing policy established
  - All scratch files in scratches/ directory
  - Never commit test files to root
  - Use `trash` CLI for cleanup

### Fixed
- Parser now recognizes `call` in expressions
- Stack viewing without destructive pop
- REPL variable evaluation works
- Removed premature `stop` command from manual

---

## [v0.0.4] - 2024-11-30

### Added
- For loops (ranges and collections)
- Lists with bracket notation
- List indexing and modification
- Break and continue statements
- Object cloning and deletion
- Properties command
- Boolean operators (and/or/not)

---

## [v0.0.3] - 2024-11-15

### Added
- Single and multiple inheritance
- Property stacks (push/pop)
- While loops
- 13+ math functions (abs, min, max, round, floor, ceil, sqrt, pow, sin, cos, tan)
- Random numbers
- Alias system
- Command history
- Tab completion
- MUD builder system

---

## [v0.0.2] - 2024-11-01

### Added
- AI Integration
  - `prompt` command with context
  - `prompt exec` for code generation
  - `eval` for dynamic execution
  - AI-powered error recovery
- File I/O (read/write/import)
- OpenAI and Anthropic support

---

## [v0.0.1] - 2024-10-15

### Added
- Initial release
- Lexer, parser, AST interpreter
- Basic data types (number, string, boolean, null)
- Objects with properties
- Functions with parameters
- Conditionals (if/then/else)
- Stack operations (get, add, subtract, multiply, divide, dup, swap, drop)
- REPL with CLI
- VS Code extension (syntax highlighting, snippets)

---

## Version History

| Version | Date | Milestone | Key Features |
|---------|------|-----------|--------------|
| v0.1.7 | 2025-12-14 | Sprite System | Sprite/image support, asset preloading, 6300+ free assets, smart copying |
| v0.1.6 | 2025-12-14 | Input + Events in Phaser | Player auto-controls, object inheritance, keyboard input, smart defaults |
| v0.1.5 | 2025-12-14 | Phaser Transpiler MVP | JavaScript/Phaser transpiler, browser deployment, zero-install games |
| v0.0.9 | 2025-12-14 | TOON Format | TOON encoder/decoder, 40% token savings, round-trip serialization |
| v0.0.8 | 2025-12-14 | Infrastructure | TOML support, test mode, metadata system, AI tickets (In Progress) |
| v0.0.7 | 2025-12-14 | Event System | when/trigger syntax, event loop, reactive programming |
| v0.0.6 | 2025-12-13 | Quality of Life | String interpolation, input command, else if, NOT in compounds |
| v0.0.5 | 2024-12-12 | String Operations | List iteration, string methods, function return assignment, stack viewing |
| v0.0.4 | 2024-11-30 | Collections & Control Flow | For loops, lists, break/continue, object cloning |
| v0.0.3 | 2024-11-15 | Inheritance & Enhancement | Inheritance, while loops, math functions, random |
| v0.0.2 | 2024-11-01 | AI Integration | prompt, prompt exec, eval, file I/O |
| v0.0.1 | 2024-10-15 | Core Interpreter | Lexer, parser, objects, functions, REPL |

---

## Upcoming

### v0.2.0 (Proposed - 2025)
- **In-game REPL** (live coding inside games) - ORIGINAL VISION
  - JavaScript prototype (1-2 days)
  - WebSocket server (1 week)
  - Multiplayer collaborative worlds
  - Voice integration path

### v0.1.8 (Planned - 2025)
- Audio & animation for Phaser
- Game state management (pause/resume/restart)
- Background music & sound effects
- Sprite animation (sprite sheets)

### v0.1.9 (Planned - 2025)
- Multiple scenes/levels in Phaser
- Scene transitions
- Level progression

### v0.3.0+ (2026)
- Second transpiler: Godot 2D (GDScript)
- Third transpiler: Godot 3D
- Fourth transpiler: Minecraft (Java mods)
- Fifth transpiler: Unity (C#)

### Future Features (Deferred)
- Error handling (try/catch)
- Dictionary/map data structures
- List comprehensions
- Lambda functions
- Package system with manifests
- Multi-user MUD support
- WebSocket server (for in-game REPL)
- rosh.cloud deployment

### v2.0+ (2027+)
- Optional Rust core rewrite
- WASM compilation
- 10-100x performance

---

## Links

- [GitHub Repository](https://github.com/rdubar/rosh)
- [Documentation](docs/)
- [Issues](ISSUES.md)
- [Project Plan](PROJECT-PLAN.md)

---

*Format: Based on [Keep a Changelog](https://keepachangelog.com/)*
*Versioning: [Semantic Versioning](https://semver.org/)*
