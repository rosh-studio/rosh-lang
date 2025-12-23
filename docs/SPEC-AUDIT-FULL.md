# Rosh Complete Specification Audit

**Purpose:** Exhaustive list of every command, syntax, and feature with edge case behavior.
**Status:** Items marked 🤖 are AI-generated specs awaiting human review.

---

## Rosh Design Principles

1. **Sensible Defaults** - When values are missing, choose the most likely intent
2. **Always Warn** - Never silently guess; inform the user what we assumed
3. **Normalize Input** - Accept variations (spacing, casing) but normalize with warning
4. **Fail Gracefully** - Invalid input shows helpful syntax, not cryptic errors
5. **Offset Collisions** - Objects created at same position are auto-offset

---

## 1. CLI REPL Commands (`rosh-cli.toml` → `cli.py`)

### 1.1 Object Management

| Command | Syntax | Edge Case | Behavior | Status |
|---------|--------|-----------|----------|--------|
| create object | `create object <name> ... end` | Name contains spaces | 🤖 Normalize to underscore: `my box` → `my_box` with warning | AI |
| create object | `create object <name>` | Empty body | ✅ Valid - creates empty object | Spec'd |
| create with type | `create <type> <name>` | Unknown type | 🤖 Treat as object name, warn: "Unknown type 'foo', creating as object" | AI |
| create shorthand | `create <name>` | No name | 🤖 Show syntax: "Usage: create <name> [at x y]" | AI |
| create with article | `create a <name>` | Just article: `create a` | 🤖 Show syntax: "Usage: create <name> [at x y]" | AI |
| create bulk | `create 100 balls` | Count = 0 | 🤖 Warn: "Count must be positive", do nothing | AI |
| create bulk | `create 100 balls` | Count negative | 🤖 Warn: "Count must be positive", do nothing | AI |
| create bulk | `create 100 balls` | Count very large (>1000) | 🤖 Warn: "Creating 1000 (max)", cap at 1000 | AI |
| create bulk + mods | `create 50 green balls` | Modifier order | 🤖 Order doesn't matter: `green big` = `big green` | AI |
| delete | `delete <name>` | Object doesn't exist | 🤖 Warn: "Object not found: foo" | AI |
| delete | `delete` | No name | 🤖 Show syntax: "Usage: delete <object>" | AI |
| delete bulk | `delete 20 balls` | Which 20? | 🤖 Delete most recently created first (LIFO) | AI |

### 1.2 Property Setting

| Command | Syntax | Edge Case | Behavior | Status |
|---------|--------|-----------|----------|--------|
| set property | `set <obj> <prop> to <value>` | Extra spaces | 🤖 Normalize: `set  box   x  to  5` → `set box x to 5` with warning | AI |
| set property | `set <obj>.<prop> to <value>` | Mixed syntax | ✅ Both dot and space syntax work | Spec'd |
| set color shorthand | `set <obj> <color>` | Unknown color | 🤖 Try as hex, if invalid warn: "Unknown color: foo" | AI |
| set text with spaces | `set logo text to hello world` | Multi-word value | 🤖 Everything after "to" is the value: text="hello world" | AI |
| set invalid prop | `set <obj> <invalid> to X` | Unknown property | 🤖 Warn: "Unknown property: foo", attempt anyway | AI |
| set invalid obj | `set <invalid> x to 5` | Unknown object | 🤖 Error: "Object not found: invalid" | AI |
| set percentage | `set x to 50%` | What's 100%? | 🤖 100% = screen/viewport size for x/y | AI |
| set percentage | `set x to 150%` | Over 100% | 🤖 Allow - object goes off-screen | AI |
| set percentage | `set x to -50%` | Negative percent | 🤖 Allow - object goes off-screen left/top | AI |
| set negative | `set width to -100` | Negative size | 🤖 Warn: "Width cannot be negative, using 0", clamp to 0 | AI |
| set missing value | `set x to` | No value | 🤖 Error: "Missing value. Usage: set <obj> <prop> to <value>" | AI |

### 1.3 Inspection

| Command | Syntax | Edge Case | Behavior | Status |
|---------|--------|-----------|----------|--------|
| look | `look <obj>` | Object exists | ✅ Shows properties | Spec'd |
| look aliases | `l`, `examine`, `x` | All aliases | ✅ All work identically | Spec'd |
| look invalid | `look <invalid>` | Unknown object | 🤖 Error: "Object not found: invalid" | AI |
| look | `look` | No object | 🤖 List all objects (same as `list`) | AI |
| list | `list` | No objects | 🤖 Show: "No objects. Use 'create <name>' to create one." | AI |
| list aliases | `ls`, `objects` | All aliases | ✅ All work identically | Spec'd |
| dump | `dump <obj>` | Format | 🤖 JSON, single line: `{"name":"box","x":100,"y":200}` | AI |
| dump | `dump` | No object | 🤖 Dump all objects as JSON array | AI |

### 1.4 Visibility

| Command | Syntax | Edge Case | Behavior | Status |
|---------|--------|-----------|----------|--------|
| hide | `hide <obj>` | Already hidden | 🤖 Silent success (idempotent) | AI |
| show | `show <obj>` | Already visible | 🤖 Silent success (idempotent) | AI |
| hide | `hide` | No object | 🤖 Error: "Usage: hide <object>" | AI |
| show | `show` | No object | 🤖 Error: "Usage: show <object>" | AI |
| hide/show | `hide all` | All objects | 🤖 Hide/show all objects | AI |

---

## 2. In-Game Console (`rosh-console.toml` → emitters)

### 2.1 Create Command - Modifier Parsing

| Input | Name | Color | Size | Shape | Notes | Status |
|-------|------|-------|------|-------|-------|--------|
| `create box` | box | green | 1.0 | box | Basic | ✅ |
| `create blue box` | box | blue | 1.0 | box | Color modifier | ✅ |
| `create big box` | box | green | 2.0 | box | Size modifier | ✅ |
| `create big blue box` | box | blue | 2.0 | box | Multiple mods | ✅ |
| `create a box` | box | green | 1.0 | box | Skip article | ✅ |
| `create the big blue box` | box | blue | 2.0 | box | Skip article | ✅ |
| `create blue` | blue | green | 1.0 | box | 🤖 "blue" is name (no shape word) | AI |
| `create big` | big | green | 1.0 | box | 🤖 "big" is name (conflicts!), warn: "Name 'big' conflicts with size modifier" | AI |
| `create a` | object | green | 1.0 | box | 🤖 Only article → default name + warn: "No name provided, using 'object'" | AI |
| `create` | - | - | - | - | 🤖 Show syntax: "Usage: create [modifiers] <name> [at x y]" | AI |
| `create big blue` | object | blue | 2.0 | box | 🤖 All modifiers → default name + warn: "No name provided, using 'object'" | AI |
| `create ball` | ball | green | 1.0 | sphere | Shape word = name | ✅ |
| `create red ball` | ball | red | 1.0 | sphere | Shape + color | ✅ |
| `create sphere` | sphere | green | 1.0 | sphere | Shape word | ✅ |
| `create big red sphere at 5 5` | sphere | red | 2.0 | sphere | With position | ✅ |
| `create box at` | box | green | 1.0 | box | 🤖 Incomplete "at" → ignore, warn: "Position incomplete, using center" | AI |
| `create box at 5` | box | green | 1.0 | box | 🤖 Only X → use center Y, warn: "Y not provided, using center" | AI |
| `create box at 5 5 5 5` | box | green | 1.0 | box | 🤖 Extra coords → ignore extras, warn: "Extra coordinates ignored" | AI |
| `create box at hello` | box | green | 1.0 | box | 🤖 Non-numeric → use center, warn: "Invalid position 'hello', using center" | AI |
| `create BOX` | box | green | 1.0 | box | 🤖 Normalize to lowercase, warn: "Name normalized: BOX → box" | AI |
| `create Box` | box | green | 1.0 | box | 🤖 Normalize to lowercase, warn: "Name normalized: Box → box" | AI |
| `create my box` | my_box | green | 1.0 | box | 🤖 Spaces → underscore, warn: "Name normalized: my box → my_box" | AI |
| `create box` (exists) | box2 | green | 1.0 | box | Auto-number if exists | ✅ |
| `create box` (at same pos) | box2 | green | 1.0 | box | 🤖 Offset by (60, 0) to avoid stacking | AI |

### 2.2 Color Values

| Input | Parsed Color | Notes | Status |
|-------|--------------|-------|--------|
| `red` | #ff0000 | Named color | ✅ |
| `green` | #00ff00 | Named color | ✅ |
| `blue` | #0000ff | Named color | ✅ |
| `yellow` | #ffff00 | Named color | ✅ |
| `cyan` | #00ffff | Named color | ✅ |
| `magenta` | #ff00ff | Named color | ✅ |
| `white` | #ffffff | Named color | ✅ |
| `black` | #000000 | Named color | ✅ |
| `orange` | #ff8800 | Named color | ✅ |
| `purple` | #8800ff | Named color | ✅ |
| `pink` | #ff88ff | Named color | ✅ |
| `gray` / `grey` | #888888 | Both spellings | ✅ |
| `#ff0000` | #ff0000 | 🤖 Hex format | AI |
| `#f00` | #ff0000 | 🤖 Short hex → expand | AI |
| `#FF0000` | #ff0000 | 🤖 Case insensitive | AI |
| `rgb(255,0,0)` | #ff0000 | 🤖 RGB format | AI |
| `rgb(255, 0, 0)` | #ff0000 | 🤖 RGB with spaces | AI |
| `rgba(255,0,0,0.5)` | #ff0000 @ 50% | 🤖 RGBA with alpha | AI |
| `notacolor` | green | 🤖 Invalid → default + warn: "Unknown color 'notacolor', using green" | AI |
| `#xyz` | green | 🤖 Invalid hex → default + warn | AI |

### 2.3 Boolean Values

| Input | Parsed Value | Notes | Status |
|-------|--------------|-------|--------|
| `true` | true | Standard | ✅ |
| `false` | false | Standard | ✅ |
| `1` | true | 🤖 Numeric + warn: "Normalized: 1 → true" | AI |
| `0` | false | 🤖 Numeric + warn: "Normalized: 0 → false" | AI |
| `yes` | true | 🤖 String + warn: "Normalized: yes → true" | AI |
| `no` | false | 🤖 String + warn: "Normalized: no → false" | AI |
| `on` | true | 🤖 String + warn: "Normalized: on → true" | AI |
| `off` | false | 🤖 String + warn: "Normalized: off → false" | AI |
| `TRUE` | true | 🤖 Case insensitive | AI |
| `Yes` | true | 🤖 Case insensitive | AI |
| `maybe` | true | 🤖 Invalid → default true + warn: "Unknown boolean 'maybe', using true" | AI |

### 2.4 Numeric Values

| Input | Parsed Value | Notes | Status |
|-------|--------------|-------|--------|
| `100` | 100 | Integer | ✅ |
| `100.5` | 100.5 | Float | ✅ |
| `-50` | -50 | 🤖 Negative allowed for position | AI |
| `-50` (for size) | 0 | 🤖 Negative size → clamp to 0 + warn | AI |
| `1e6` | 1000000 | 🤖 Scientific notation supported | AI |
| `1_000` | 1000 | 🤖 Underscore separators supported | AI |
| `infinity` | MAX_FLOAT | 🤖 → very large number + warn | AI |
| `NaN` | 0 | 🤖 → 0 + warn: "Invalid number 'NaN', using 0" | AI |
| `hello` | 0 | 🤖 → 0 + warn: "Invalid number 'hello', using 0" | AI |
| `` (empty) | 0 | 🤖 → 0 + warn: "Missing value, using 0" | AI |

### 2.5 Set Command - Value Parsing

| Input | Behavior | Status |
|-------|----------|--------|
| `set box x to 100` | x = 100 | ✅ |
| `set box x to 100.5` | x = 100.5 | ✅ |
| `set box x to -50` | x = -50 | 🤖 Negative position allowed | AI |
| `set box width to -50` | width = 0, warn | 🤖 Negative size clamped | AI |
| `set box color to red` | color = red | ✅ |
| `set box color to #ff0000` | color = #ff0000 | 🤖 Hex supported | AI |
| `set box color to rgb(255,0,0)` | color = #ff0000 | 🤖 RGB supported | AI |
| `set box visible to true` | visible = true | ✅ |
| `set box visible to 1` | visible = true, warn | 🤖 Numeric bool normalized | AI |
| `set box visible to yes` | visible = true, warn | 🤖 String bool normalized | AI |
| `set box text to hello` | text = "hello" | ✅ |
| `set box text to hello world` | text = "hello world" | 🤖 Everything after "to" | AI |
| `set box text to ""` | text = "" | 🤖 Empty string valid | AI |
| `set box text to` | text = "", warn | 🤖 Missing → empty + warn | AI |
| `set box x` | Error: missing "to" | 🤖 Show syntax | AI |
| `set box` | Error: missing prop | 🤖 Show syntax | AI |
| `set` | Error: missing all | 🤖 Show syntax | AI |

### 2.6 Move Command

| Input | Behavior | Status |
|-------|----------|--------|
| `move box to 100 200` | x=100, y=200 | ✅ |
| `move box to 100 200 300` | x=100, y=200, z=300 | ✅ 3D |
| `move box to 100` | x=100, y=center, warn | 🤖 Missing Y → center | AI |
| `move box 100 200` | Error: missing "to" | 🤖 Show syntax | AI |
| `move box to` | Error: missing coords | 🤖 Show syntax | AI |
| `move to 100 200` | Error: missing object | 🤖 Show syntax | AI |
| `move` | Error: missing all | 🤖 Show syntax | AI |
| `move nonexistent to 100 200` | Error: not found | 🤖 Object not found error | AI |
| `move box to hello world` | Error: invalid coords | 🤖 Non-numeric error | AI |

### 2.7 Delete Command

| Input | Behavior | Status |
|-------|----------|--------|
| `delete box` | Remove box | ✅ |
| `delete box2` | Remove box2 | ✅ Runtime object |
| `delete logo` | 🤖 Remove (static objects can be deleted) | AI |
| `delete nonexistent` | Error: "Object not found: nonexistent" | 🤖 |
| `delete` | Error: "Usage: delete <object>" | 🤖 |
| `delete all` | 🤖 Delete all runtime objects, warn: "Deleted N objects" | AI |
| `rm box` | Remove box | ✅ Alias |
| `destroy box` | Remove box | ✅ Alias |
| `remove box` | Remove box | ✅ Alias |

### 2.8 Undo/Redo

| Input | Behavior | Status |
|-------|----------|--------|
| `undo` | Undo last action | ✅ |
| `undo 3` | 🤖 Undo last 3 actions | AI |
| `undo` (nothing) | 🤖 Warn: "Nothing to undo" | AI |
| `undo stack` | 🤖 Show undo history | AI |
| `redo` | Redo last undo | ✅ |
| `redo 3` | 🤖 Redo last 3 | AI |
| `redo` (nothing) | 🤖 Warn: "Nothing to redo" | AI |
| `redo stack` | 🤖 Show redo history | AI |
| `oops` | Same as undo | ✅ Alias |

---

## 3. Parser Syntax (`parser.py`)

### 3.1 Create Statements

| Syntax | Parsed As | Status |
|--------|-----------|--------|
| `create object foo ... end` | CreateObject(name="foo") | ✅ |
| `create foo ... end` | 🤖 CreateObject(name="foo") - implied object | AI |
| `create text foo ... end` | 🤖 CreateObject(name="foo", type="text") | AI - NEEDS FIX |
| `create sprite foo ... end` | 🤖 CreateObject(name="foo", type="sprite") | AI |
| `create sound foo ... end` | 🤖 CreateObject(name="foo", type="sound") | AI |
| `create foo` (no end) | CreateObject(name="foo", body=[]) | ✅ |
| `create foo to 5` | CreateValue(name="foo", value=5) | ✅ |
| `create foo: number to 5` | CreateValue(name="foo", type=number, value=5) | ✅ |
| `create foo to` | 🤖 Error: "Missing value after 'to'" | AI |
| `create` | 🤖 Error: "Usage: create <name>" | AI |

### 3.2 Set Statements

| Syntax | Parsed As | Status |
|--------|-----------|--------|
| `set x to 5` | SetProperty(target=x, value=5) | ✅ |
| `set obj.x to 5` | SetProperty(target=obj.x, value=5) | ✅ |
| `set obj x to 5` | SetProperty(target=obj.x, value=5) | ✅ |
| `set meta.title to "Game"` | SetProperty(target=meta.title, value="Game") | ✅ |
| `set x` | 🤖 Error: "Missing 'to' and value" | AI |
| `set to 5` | 🤖 Error: "Missing target" | AI |
| `set` | 🤖 Error: "Usage: set <target> to <value>" | AI |

### 3.3 Event Handlers

| Syntax | Parsed As | Status |
|--------|-----------|--------|
| `on start ... end` | Event(trigger="start") | ✅ |
| `on key "space" ... end` | Event(trigger="key", key="space") | ✅ |
| `on key space ... end` | 🤖 Event(trigger="key", key="space") - quotes optional | AI |
| `on click ... end` | Event(trigger="click") | ✅ |
| `on click obj ... end` | 🤖 Event(trigger="click", target="obj") | AI |
| `on collision obj1 obj2 ... end` | 🤖 Event(trigger="collision", objects=["obj1","obj2"]) | AI |
| `on timer 1000 ... end` | 🤖 Event(trigger="timer", interval=1000) | AI |
| `on voice "jump" ... end` | 🤖 Event(trigger="voice", phrase="jump") | AI |
| `on ... end` (no trigger) | 🤖 Error: "Missing event trigger" | AI |

### 3.4 Control Flow

| Syntax | Parsed As | Status |
|--------|-----------|--------|
| `if x > 5 ... end` | Conditional(condition=x>5) | ✅ |
| `if x > 5 ... else ... end` | Conditional(condition=x>5, else_body) | ✅ |
| `if x > 5 ... elif y < 3 ... end` | 🤖 Chained conditionals | AI |
| `if x > 5 ... elif y < 3 ... else ... end` | 🤖 Full chain | AI |
| `for i in 1 to 10 ... end` | ForLoop(var=i, start=1, end=10) | ✅ |
| `for i from 1 to 10 ... end` | 🤖 Alternative syntax | AI |
| `for item in items ... end` | ForEach(var=item, collection=items) | ✅ |
| `while x > 0 ... end` | 🤖 WhileLoop(condition=x>0) | AI |
| `repeat 5 times ... end` | 🤖 RepeatLoop(count=5) | AI |
| `repeat forever ... end` | 🤖 RepeatLoop(count=infinity) | AI |
| `break` | 🤖 BreakStatement | AI |
| `continue` | 🤖 ContinueStatement | AI |

---

## 4. 2D Properties (`rosh-2d.toml`)

### 4.1 Position

| Property | Type | Default | Valid Range | Edge Case Behavior | Status |
|----------|------|---------|-------------|-------------------|--------|
| x | number | center | any | 🤖 Negative = off-screen left, allowed | AI |
| y | number | center | any | 🤖 Negative = off-screen top, allowed | AI |
| x (percent) | string | - | any% | 🤖 >100% = off-screen right, allowed | AI |
| y (percent) | string | - | any% | 🤖 >100% = off-screen bottom, allowed | AI |
| x (missing) | - | center | - | 🤖 Default to screen center | AI |
| y (missing) | - | center | - | 🤖 Default to screen center | AI |

### 4.2 Size

| Property | Type | Default | Valid Range | Edge Case Behavior | Status |
|----------|------|---------|-------------|-------------------|--------|
| width | number | 50 | ≥0 | 🤖 Negative → 0 + warn | AI |
| height | number | 50 | ≥0 | 🤖 Negative → 0 + warn | AI |
| scale | number | 1.0 | ≥0 | 🤖 Negative → 0 + warn, 0 = invisible | AI |
| width | number | - | >10000 | 🤖 Cap at 10000 + warn | AI |
| height | number | - | >10000 | 🤖 Cap at 10000 + warn | AI |

### 4.3 Appearance

| Property | Type | Default | Valid Values | Edge Case Behavior | Status |
|----------|------|---------|--------------|-------------------|--------|
| color | string | "green" | names, hex, rgb | 🤖 Invalid → green + warn | AI |
| visible | boolean | true | true/false/1/0/yes/no | 🤖 Normalize + warn if not true/false | AI |
| opacity | number | 1.0 | 0.0-1.0 | 🤖 <0 → 0, >1 → 1 + warn | AI |
| rotation | number | 0 | any degrees | 🤖 Normalize to 0-360 internally | AI |
| z_index | number | 0 | any integer | 🤖 Higher = in front | AI |

### 4.4 Text

| Property | Type | Default | Valid Values | Edge Case Behavior | Status |
|----------|------|---------|--------------|-------------------|--------|
| text | string | "" | any | 🤖 Max 10000 chars, truncate + warn | AI |
| font_size | number | 16 | 1-1000 | 🤖 <1 → 1, >1000 → 1000 + warn | AI |
| font_family | string | "Inter" | font names | 🤖 Not found → system default + warn | AI |
| text_align | string | "center" | left/center/right | 🤖 Invalid → center + warn | AI |
| line_height | number | 1.2 | ≥0.5 | 🤖 <0.5 → 0.5 + warn | AI |

---

## 5. 3D Properties (`rosh-3d.toml`)

### 5.1 Position

| Property | Type | Default | Valid Range | Edge Case Behavior | Status |
|----------|------|---------|-------------|-------------------|--------|
| x | number | 0 | any | 🤖 Negative allowed (left of origin) | AI |
| y | number | 1 | any | 🤖 0 = on ground, negative = below ground | AI |
| z | number | 0 | any | 🤖 Negative = behind origin | AI |
| position missing | - | (0, 1, 0) | - | 🤖 Default: origin, slightly above ground | AI |

### 5.2 Rotation

| Property | Type | Default | Valid Range | Edge Case Behavior | Status |
|----------|------|---------|-------------|-------------------|--------|
| rotationX | number | 0 | degrees | 🤖 Normalize to 0-360 | AI |
| rotationY | number | 0 | degrees | 🤖 Normalize to 0-360 | AI |
| rotationZ | number | 0 | degrees | 🤖 Normalize to 0-360 | AI |
| rotation | number | 0 | degrees | 🤖 Alias for rotationY (common case) | AI |

### 5.3 Scale

| Property | Type | Default | Valid Range | Edge Case Behavior | Status |
|----------|------|---------|-------------|-------------------|--------|
| scale | number | 1.0 | ≥0 | 🤖 Uniform scale, negative → 0 + warn | AI |
| scaleX | number | 1.0 | ≥0 | 🤖 Negative → 0 + warn | AI |
| scaleY | number | 1.0 | ≥0 | 🤖 Negative → 0 + warn | AI |
| scaleZ | number | 1.0 | ≥0 | 🤖 Negative → 0 + warn | AI |

### 5.4 3D-Specific Appearance

| Property | Type | Default | Valid Values | Edge Case Behavior | Status |
|----------|------|---------|--------------|-------------------|--------|
| material | string | "standard" | standard/unlit/wireframe | 🤖 Invalid → standard + warn | AI |
| metalness | number | 0.0 | 0.0-1.0 | 🤖 Clamp to range | AI |
| roughness | number | 0.5 | 0.0-1.0 | 🤖 Clamp to range | AI |
| castShadow | boolean | true | true/false | 🤖 Normalize booleans | AI |
| receiveShadow | boolean | true | true/false | 🤖 Normalize booleans | AI |

---

## 6. Voice Input (`rosh-voice.toml`)

### 6.1 Spelling Corrections

| Mishearing | Corrected To | Status |
|------------|--------------|--------|
| raush, rush, rawsh, roush | rosh | ✅ |
| colour | color | ✅ |
| grey | gray | ✅ |
| centre | center | ✅ |
| 🤖 roche, roach | rosh | AI |
| 🤖 create, kreate | create | AI |
| 🤖 read, red (for color) | red | AI - context-dependent |
| 🤖 blew, blue | blue | AI |
| 🤖 too, to | to | AI |
| 🤖 4, four, for | context-dependent | AI |

### 6.2 Voice Command Synonyms

| Voice Input | Interpreted As | Status |
|-------------|----------------|--------|
| "create a box" | `create box` | ✅ |
| 🤖 "make a box" | `create box` | AI |
| 🤖 "add a box" | `create box` | AI |
| 🤖 "new box" | `create box` | AI |
| 🤖 "remove the box" | `delete box` | AI |
| 🤖 "get rid of box" | `delete box` | AI |
| 🤖 "put it at 100 200" | `move <last> to 100 200` | AI |
| 🤖 "move it over there" | Error: "Please specify position" | AI |
| 🤖 "delete that" | `delete <last>` | AI |
| 🤖 "undo that" | `undo` | AI |
| 🤖 "go back" | `undo` | AI |
| 🤖 "never mind" | `undo` | AI |

---

## 7. Sound/Audio (`rosh-audio.toml` - PROPOSED)

### 7.1 Sound Commands

| Command | Syntax | Behavior | Status |
|---------|--------|----------|--------|
| 🤖 play | `play <sound>` | Play sound once | AI |
| 🤖 play loop | `play <sound> loop` | Loop continuously | AI |
| 🤖 stop | `stop <sound>` | Stop playing | AI |
| 🤖 stop all | `stop all` | Stop all sounds | AI |
| 🤖 pause | `pause <sound>` | Pause (resumable) | AI |
| 🤖 resume | `resume <sound>` | Resume paused | AI |
| 🤖 volume | `set <sound> volume to 0.5` | 0.0-1.0 | AI |
| 🤖 mute | `mute` / `unmute` | Toggle all audio | AI |

### 7.2 Sound Properties

| Property | Type | Default | Valid Range | Status |
|----------|------|---------|-------------|--------|
| 🤖 volume | number | 1.0 | 0.0-1.0 | AI |
| 🤖 loop | boolean | false | true/false | AI |
| 🤖 autoplay | boolean | false | true/false | AI |
| 🤖 pitch | number | 1.0 | 0.5-2.0 | AI |

---

## 8. Animation/Tweening (`rosh-animation.toml` - PROPOSED)

### 8.1 Animation Commands

| Command | Syntax | Behavior | Status |
|---------|--------|----------|--------|
| 🤖 animate | `animate <obj> <prop> to <val> over <time>` | Tween property | AI |
| 🤖 animate | `animate box x to 500 over 2s` | Move over 2 seconds | AI |
| 🤖 animate | `animate box color to red over 1s` | Color transition | AI |
| 🤖 animate easing | `animate box x to 500 over 2s ease-in` | With easing | AI |

### 8.2 Easing Functions

| Easing | Description | Status |
|--------|-------------|--------|
| 🤖 linear | Constant speed | AI |
| 🤖 ease-in | Start slow | AI |
| 🤖 ease-out | End slow | AI |
| 🤖 ease-in-out | Start and end slow | AI |
| 🤖 bounce | Bouncy effect | AI |
| 🤖 elastic | Elastic effect | AI |

---

## 9. Emitter Parity Matrix

### 9.1 Console Commands

| Command | Phaser | Pygame | Three.js | Godot | Notes |
|---------|--------|--------|----------|-------|-------|
| list | ✅ | ✅ | ✅ | ✅ | |
| look | ✅ | ✅ | ✅ | ✅ | |
| set | ✅ | ✅ | ✅ | ✅ | |
| hide | ✅ | ✅ | ✅ | ✅ | |
| show | ✅ | ✅ | ✅ | ✅ | |
| create | ✅ | ✅ | ✅ | ✅ | |
| create + modifiers | ❌ | ❓ | ✅ | ✅ | Phaser needs update |
| delete | ✅ | ❓ | ✅ | ✅ | |
| move | ✅ | ❓ | ✅ | ✅ | |
| undo | ❓ | ❓ | ✅ | ✅ | |
| redo | ❓ | ❓ | ✅ | ✅ | |
| clear | ✅ | ✅ | ✅ | ✅ | |
| help | ✅ | ✅ | ✅ | ✅ | |

### 9.2 Value Formats

| Format | Phaser | Pygame | Three.js | Godot | Notes |
|--------|--------|--------|----------|-------|-------|
| Named colors | ✅ | ✅ | ✅ | ✅ | |
| Hex colors | ❓ | ❓ | ✅ | ❓ | 🤖 Add to all |
| RGB colors | ❓ | ❓ | ❓ | ❓ | 🤖 Add to all |
| Percentages | ✅ | ✅ | ❓ | ❓ | 🤖 Standardize |
| Boolean normalization | ❓ | ❓ | ❓ | ❓ | 🤖 Add to all |

### 9.3 Features

| Feature | Phaser | Pygame | Three.js | Godot | Notes |
|---------|--------|--------|----------|-------|-------|
| Text objects | ✅ | ✅ | ✅ | ✅ | |
| Sprites | ✅ | ✅ | ❓ | ❓ | |
| Shapes (rect) | ✅ | ✅ | ✅ | ✅ | |
| 3D meshes | ❌ | ❌ | ✅ | ✅ | |
| Camera controls | ❌ | ❌ | ✅ | ✅ | |
| Animation | ✅ | ❓ | ✅ | ❌ | 🤖 Needs spec |
| Physics | ❓ | ❓ | ❓ | ❓ | 🤖 Needs spec |
| Sound | ❓ | ❓ | ❓ | ❓ | 🤖 Needs spec |
| Voice input | ✅ | ❌ | ✅ | ❓ | Browser only |

---

## 10. Error Message Standards

### 10.1 Error Format

All error messages follow this format:
```
[type]: [message]

Examples:
Error: Object not found: foo
Warning: Name normalized: BOX → box
Syntax: Usage: create <name> [at x y]
```

### 10.2 Error Types

| Type | Color | When Used |
|------|-------|-----------|
| Error | red | Operation failed, cannot continue |
| Warning | yellow | Operation succeeded but with assumptions |
| Syntax | cyan | Invalid syntax, showing correct usage |
| Info | dim/gray | Informational, no action needed |

### 10.3 Standard Error Messages

| Situation | Message | Status |
|-----------|---------|--------|
| Object not found | `Error: Object not found: <name>` | 🤖 |
| Invalid syntax | `Syntax: Usage: <correct syntax>` | 🤖 |
| Invalid value | `Error: Invalid value '<val>' for <prop>` | 🤖 |
| Value normalized | `Warning: Normalized: <from> → <to>` | 🤖 |
| Missing required | `Error: Missing <what>` | 🤖 |
| Clamped value | `Warning: <prop> clamped to <range>` | 🤖 |
| Default used | `Warning: <prop> not provided, using <default>` | 🤖 |

---

## 11. Implementation Priority

### 11.1 Critical (Blocks Demo)

1. ~~Fix parser: `create text name` should work~~ (workaround: use `create object`)
2. Add hex color support to all emitters
3. Standardize boolean normalization

### 11.2 Important (User Experience)

4. Add consistent error messages across emitters
5. Implement undo/redo in Phaser and Pygame
6. Add modifier parsing to Phaser

### 11.3 Nice to Have

7. RGB color format
8. Animation/tweening
9. Sound/audio
10. Physics/collision

---

*Generated: 2024-12-23*
*🤖 = AI-generated specification, awaiting human review*
