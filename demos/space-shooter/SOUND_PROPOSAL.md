# Sound Support Proposal

**Feature:** Basic sound effects for Pygame transpiler
**Effort:** 1-2 hours
**Priority:** HIGH (big impact, low effort)

---

## Proposed Rosh Syntax

### Option A: Simple Inline (Recommended)

```rosh
# Play a sound effect
play sound "shoot.wav"

# In context
when space_pressed then
    call fire_bullet
    play sound "shoot.wav"
end

when update then
    # When bullet hits enemy
    if bullet_hit is equal to 1 then
        play sound "explosion.wav"
        set state.score to state.score plus 10
    end
end
```

**Pros:**
- Minimal syntax, easy to read aloud
- No preloading boilerplate needed
- Matches Rosh's "spoken-first" philosophy

**Cons:**
- Transpiler must handle caching internally
- Less control over volume/looping

### Option B: Named Sound Objects

```rosh
create sound shoot_sound
    set file to "shoot.wav"
    set volume to 0.5
end

play shoot_sound
```

**Pros:**
- More control (volume, looping)
- Explicit asset declaration

**Cons:**
- More boilerplate
- Overkill for simple sound effects

### Recommendation: Option A for Phase 1

Simple `play sound "file"` covers 90% of use cases. Add Option B later if needed.

---

## Transpiler Implementation

### 1. Parser Changes

Add new statement type `PlaySound`:

```python
# In ast_nodes.py
@dataclass
class PlaySound(ASTNode):
    """play sound 'filename'"""
    filename: str
    line: int = 0
```

Parser recognizes: `play sound "filename.wav"`

### 2. Transpiler: Sound Initialization

```python
# Generated Python - after pygame.init()
pygame.mixer.init()

# Sound cache (generated if sounds used)
_sounds = {}
def play_sound(filename):
    if filename not in _sounds:
        try:
            _sounds[filename] = pygame.mixer.Sound(ASSETS_DIR / filename)
        except:
            print(f"Warning: Could not load sound {filename}")
            return
    _sounds[filename].play()
```

### 3. Transpiler: Play Statement

```python
# Rosh: play sound "shoot.wav"
# Generated Python:
play_sound("shoot.wav")
```

### 4. Sound Asset Detection

Transpiler scans for `play sound` statements and:
- Lists required sound files
- Warns if assets missing (at transpile time or runtime)

---

## Example: Space Shooter with Sound

```rosh
# Fire bullet with sound
when space_pressed then
    if state.level is above 0 then
        call fire_bullet
        play sound "shoot.wav"
    end
end

# Enemy destroyed
when update then
    # ... collision detection ...
    if bullet_hit is equal to 1 then
        play sound "explosion.wav"
        set state.score to state.score plus 10
    end
end

# Game over
define function game_over
    play sound "gameover.wav"
    set game_over_text.visible to true
end
```

---

## Scope & Limitations (Phase 1)

**In Scope:**
- Single sound effect playback
- WAV and OGG formats (pygame native)
- Auto-caching (same sound doesn't reload)
- Graceful fallback if sound missing

**Out of Scope (Future):**
- Background music / looping
- Volume control
- Sound stopping/pausing
- 3D positional audio
- Multiple simultaneous instances limit

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/rosh/ast_nodes.py` | Add `PlaySound` class |
| `src/rosh/lexer.py` | Add `PLAY` and `SOUND` keywords |
| `src/rosh/parser.py` | Parse `play sound "file"` statement |
| `src/rosh/transpilers/pygame_transpiler.py` | Emit mixer init + play_sound function |

---

## Test Plan

1. Add sounds to space-shooter demo
2. Verify: shoot sound on space press
3. Verify: explosion on enemy hit
4. Verify: graceful handling of missing sound file
5. Verify: same sound played rapidly doesn't crash

---

## Sound Assets

Free sounds from OpenGameArt/Kenney:
- `shoot.wav` - laser/pew sound
- `explosion.wav` - enemy destroyed
- `gameover.wav` - defeat jingle
- `powerup.wav` - bonus pickup (future)

---

## Decision Needed

1. **Syntax**: Option A (simple) or Option B (objects)?
2. **Proceed**: Implement now or defer?

---

*Proposal created: 2025-12-15*
*Author: claude-opus-4-5*
