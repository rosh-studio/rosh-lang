# Rosh Specification Chain

**Purpose:** This document defines the complete dependency chain from specifications to output. Every component knows what it consumes (upstream) and what consumes it (downstream).

**Audience:** AI assistants and human developers working on Rosh.

---

## The Chain at a Glance

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SPECIFICATIONS (TOML)                              │
│                         spec/v0.2.0/*.toml                                   │
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ rosh-cli.toml│  │rosh-console. │  │ rosh-2d.toml │  │ rosh-3d.toml │     │
│  │              │  │    toml      │  │              │  │              │     │
│  │ CLI REPL     │  │ In-game      │  │ 2D object    │  │ 3D object    │     │
│  │ commands     │  │ console cmds │  │ properties   │  │ properties   │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                 │                 │                 │              │
│         │                 │                 └────────┬────────┘              │
│         │                 │                          │                       │
│  ┌──────────────┐         │                          │                       │
│  │rosh-voice.   │         │                          │                       │
│  │    toml      │         │                          │                       │
│  │ Voice/typo   │         │                          │                       │
│  │ corrections  │         │                          │                       │
│  └──────┬───────┘         │                          │                       │
└─────────┼─────────────────┼──────────────────────────┼───────────────────────┘
          │                 │                          │
          ▼                 │                          ▼
┌─────────────────────┐     │          ┌─────────────────────────────────────┐
│   CLI INTERPRETER   │     │          │           PARSER / IR                │
│   src/rosh/cli.py   │     │          │                                      │
│   src/rosh/voice.py │     │          │  src/rosh/parser.py      (AST)       │
│                     │     │          │  src/rosh/ir.py          (IR types)  │
│  Consumes:          │     │          │  src/rosh/ir_transformer (AST→IR)    │
│  - rosh-cli.toml    │     │          │                                      │
│  - rosh-voice.toml  │     │          │  Consumes:                           │
│                     │     │          │  - rosh-2d.toml (property defaults)  │
│  Provides:          │     │          │  - rosh-3d.toml (property defaults)  │
│  - `rosh repl`      │     │          │                                      │
│  - `rosh build`     │     │          │  Produces:                           │
│                     │     │          │  - IR_Program with objects, events   │
└─────────────────────┘     │          └──────────────────┬──────────────────┘
                            │                             │
                            │                             │
                            ▼                             ▼
          ┌─────────────────────────────────────────────────────────────────┐
          │                         EMITTERS                                 │
          │                   src/rosh/emitters/                             │
          │                                                                  │
          │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐          │
          │  │ phaser.py   │    │ pygame.py   │    │ threejs.py  │          │
          │  │ (Browser 2D)│    │ (Desktop 2D)│    │ (Browser 3D)│          │
          │  └─────────────┘    └─────────────┘    └─────────────┘          │
          │                                                                  │
          │  Consumes:                                                       │
          │  - IR_Program (from parser)                                      │
          │  - rosh-console.toml (runtime console commands)                  │
          │  - rosh-2d.toml or rosh-3d.toml (property names)                 │
          │                                                                  │
          │  Produces:                                                       │
          │  - Target code (game.js, game.py)                                │
          │  - Embedded runtime console                                      │
          └──────────────────────────────┬──────────────────────────────────┘
                                         │
                                         ▼
          ┌─────────────────────────────────────────────────────────────────┐
          │                          OUTPUT                                  │
          │                                                                  │
          │  /tmp/output/game.js   (Phaser)                                  │
          │  /tmp/output/game.py   (Pygame)                                  │
          │  /tmp/output/game.js   (Three.js)                                │
          │                                                                  │
          │  Each contains:                                                  │
          │  - Game logic from IR                                            │
          │  - Runtime console (from rosh-console.toml)                      │
          └─────────────────────────────────────────────────────────────────┘
```

---

## Specification Files

| File | Purpose | Consumed By | Must Match |
|------|---------|-------------|------------|
| `rosh-cli.toml` | CLI REPL commands | `cli.py` | N/A |
| `rosh-console.toml` | In-game console commands | All emitters | All emitters must have parity |
| `rosh-2d.toml` | 2D object properties | `ir_transformer.py`, `phaser.py`, `pygame.py` | N/A |
| `rosh-3d.toml` | 3D object properties | `ir_transformer.py`, `threejs.py` | N/A |
| `rosh-voice.toml` | Voice/typo corrections | `voice.py` | N/A |

---

## Component Responsibilities

### 1. Specifications (`spec/v0.2.0/*.toml`)

**What they are:** Source of truth for all behavior.

**Rules:**
- Specs are AUTHORITATIVE. Code must match specs, not vice versa.
- When specs change, all dependent code must update.
- Version specs together (all v0.2.0 specs are compatible).

---

### 2. Parser & IR (`src/rosh/parser.py`, `ir.py`, `ir_transformer.py`)

**Upstream (consumes):**
- `.rosh` source files
- `rosh-2d.toml` / `rosh-3d.toml` for property defaults

**Downstream (produces):**
- `IR_Program` containing objects, events, functions, metadata

**Rules:**
- Parser handles syntax only
- IR Transformer handles semantics (defaults, validation)
- IR is the contract between parser and emitters

---

### 3. CLI Interpreter (`src/rosh/cli.py`, `voice.py`)

**Upstream (consumes):**
- `rosh-cli.toml` for command definitions
- `rosh-voice.toml` for input normalization

**Downstream (produces):**
- Interactive REPL session
- Calls to parser/emitters for `rosh build`

**Rules:**
- Commands in CLI must match `rosh-cli.toml`
- Voice normalization applies to CLI input only (not in-game console)

---

### 4. Emitters (`src/rosh/emitters/*.py`)

**Upstream (consumes):**
- `IR_Program` from parser
- `rosh-console.toml` for runtime console commands
- `rosh-2d.toml` or `rosh-3d.toml` for property names

**Downstream (produces):**
- Target code (JavaScript or Python)
- Embedded runtime console

**Rules:**
- ALL emitters must implement ALL required commands from `rosh-console.toml`
- Emitters are mechanical translators - no semantic decisions
- Console command behavior must be identical across emitters

---

## Audit Verification

The audit tool (`src/rosh/spec/audit.py`) verifies:

1. **CLI Audit:** Does `cli.py` implement all commands from `rosh-cli.toml`?
2. **Console Audit:** Do ALL emitters implement all commands from `rosh-console.toml`?
3. **Property Audit:** Do emitters handle all properties from `rosh-2d.toml`/`rosh-3d.toml`?

**Run:** `uv run python -m rosh.spec.audit`

---

## Change Process

### Adding a new CLI command:
1. Add to `rosh-cli.toml`
2. Implement in `cli.py`
3. Run audit to verify

### Adding a new console command:
1. Add to `rosh-console.toml`
2. Implement in ALL emitters (`phaser.py`, `pygame.py`, `threejs.py`)
3. Run audit to verify parity

### Adding a new object property:
1. Add to `rosh-2d.toml` and/or `rosh-3d.toml`
2. Update `ir_transformer.py` for defaults
3. Update relevant emitters
4. Run audit to verify

---

## FAQ

**Q: Where do new features go first?**
A: Always spec first (`*.toml`), then implement.

**Q: Why didn't the audit catch missing console commands?**
A: The audit only checks what's in specs. No spec = nothing to check. That's why `rosh-console.toml` was created.

**Q: Can emitters add extra commands not in the spec?**
A: Yes, but they're not guaranteed across targets. Only spec'd commands are portable.

**Q: What if Phaser can do something Pygame can't?**
A: Mark it `required = false` in the spec. Document the limitation.

---

---

## Voice Support Matrix

| Target | Console | Voice Input | Reason |
|--------|---------|-------------|--------|
| Three.js | Yes | **Yes** (Web Speech API) | Browser-native, full support |
| Phaser | Yes | **Yes** (Web Speech API) | Browser-native, full support |
| Pygame | Yes | **No** | Desktop Python, no browser APIs |

### Pygame Voice Limitation

**Technical Reason:** Pygame runs as a desktop Python application without access to browser APIs. To add voice support would require:

1. External dependencies: `speechrecognition`, `pyaudio`
2. System-level audio configuration (microphone permissions)
3. Platform-specific setup (Windows vs macOS vs Linux)
4. Network connectivity for cloud speech services (Google, Azure)

**Decision:** Voice support in Pygame is deferred. The complexity of cross-platform audio setup outweighs the benefit for the current demo scope. Users wanting voice control should use browser targets (Phaser, Three.js).

**Future Option:** If voice becomes critical for Pygame:
- Use `vosk` for offline speech recognition
- Or create a companion web interface that bridges to the Pygame app

### Voice Corrections

All voice-enabled consoles apply these corrections (from `rosh-voice.toml`):

| Mishearing | Corrected To |
|------------|--------------|
| raush, rush, rawsh, roush | rosh |
| colour | color |
| grey | gray |
| centre | center |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 0.2.0 | 2024-12-22 | Initial spec chain documentation |
| 0.2.0 | 2024-12-22 | Added voice support matrix and limitations |
