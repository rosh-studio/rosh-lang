# Rosh Language Reference

> "One script, many worlds."

Rosh is a plain-English programming language. The same `.rosh` file runs in a terminal, a browser, a 2D game, a 3D scene, or a live networked world. You describe what you want; the target decides how to render it.

---

## Contents

1. [Getting Started](#getting-started)
2. [Core Concepts](#core-concepts)
3. [Syntax Reference](#syntax-reference)
4. [Object Properties](#object-properties)
5. [Events](#events)
6. [Control Flow](#control-flow)
7. [Functions](#functions)
8. [Scenes](#scenes)
9. [Media — Sprites](#media--sprites)
10. [Media — Sounds](#media--sounds)
11. [Media — 3D Assets](#media--3d-assets)
12. [Widgets](#widgets)
13. [Targets](#targets)
14. [Asset Registry and CLI](#asset-registry-and-cli)
15. [Patterns and Examples](#patterns-and-examples)

---

## Getting Started

### Install

```bash
pip install rosh-lang          # or: uv tool install rosh-lang
```

### Run a file

```bash
rosh hello.rosh                        # print to terminal
rosh hello.rosh --target web --run     # open in browser (self-contained HTML)
rosh hello.rosh --target phaser --run  # Phaser 2D game
rosh hello.rosh --target threejs --run # Three.js 3D scene
rosh hello.rosh --target scratch       # export Scratch .sb3
```

### REPL

```bash
rosh            # interactive line-by-line
```

### Scaffold a starter

```bash
rosh new hello my-first      # minimal hello-world template
rosh new game my-shooter     # game template (title screen, score, lives)
rosh new app my-app          # interactive web app template
```

---

## Core Concepts

**Objects** are named state containers. Create them with `create object`, then get and set their properties with `set` and `get`.

**Events** drive everything — `start`, `update`, `click`, `keydown`, and user-defined events via `event` / `send`.

**Targets** render the same programme differently. A `create object player` becomes a CSS div on web, a Phaser sprite in a game, a Three.js mesh in 3D. The language is the same; the renderer adapts.

**Widgets** are pre-built composable components — a score display, a player controller, a timer — configured inline with `use score label "Points"`.

**Assets** are named real-world objects (a torch, a stone, a brooch) resolved through the asset registry into target-appropriate representations.

---

## Syntax Reference

All statements are one line, or a block closed with `end`.

### Output

```rosh
print "Hello, world!"          # print text; {variable} interpolation
print "Score: {score.value}"   # reference any state variable
print                          # blank line
say hello                      # broadcast text to connected clients (world target)
```

### Objects

```rosh
create object player           # create an object (default type)
create number score            # create a number variable
create string name             # create a string variable
create list items              # create a list
```

Objects persist in state for the lifetime of the programme. Properties are accessed with dot notation.

### Set and Get

```rosh
set player.x to 0.5            # assign a value
set player.x to player.x + 1  # arithmetic: +  -  *  /
set x to random                # random float 0.0–1.0
set x to random 0.1 0.9        # random float in range
set x to clamp x 0.02 0.8      # constrain to [min, max]

get player                     # query and print object state
get score into saved           # capture result into a state variable
get all into items             # all visible state as a structured list
get count of visitors into n   # list length as an integer
```

### Look (inspection)

```rosh
look                           # inspect the current scene
look player into info          # capture inspection result into state
look programme into stmts      # capture statement list (use with repeat/for each)
```

`into` capture is terminal/REPL-first. Browser and game targets have deferred capture paths.

### Destroy

```rosh
destroy enemy                  # remove an object from the scene
```

### Connect

```rosh
connect server wss://example.com/ws    # register a WebSocket connection
```

---

## Object Properties

Properties are set with `set obj.property to value` and read with `{obj.property}` in strings or in expressions.

| Property | Type | Description |
|----------|------|-------------|
| `x` | float | Horizontal position. 0.0–1.0 = fraction of container; >1 = pixels |
| `y` | float | Vertical position. Same units as `x` |
| `z` | float | Depth (Three.js / world targets only) |
| `width` | float | Width. Default `0.1` (10% of container) |
| `height` | float | Height. Default `0.1` |
| `depth` | float | Depth size (Three.js only). Defaults to `width` |
| `color` | string | Named colour (`red`, `cyan`) or hex (`#ff0000`) |
| `label` | string | Text rendered on the object. Empty by default |
| `sprite` | string | Procedural description (`"blue spaceship"`) or image URL |
| `shape` | string | Primitive shape: `box`, `sphere`, `cylinder`, `cone`, `torus`, `plane` |
| `rotation` | float | 2D rotation in degrees (0 = up, clockwise positive) |
| `rx`, `ry`, `rz` | float | 3D rotation in radians (Three.js / world targets) |
| `visible` | int | `0` hides; any other value shows. Cascades to children |
| `vx`, `vy` | float | Velocity per second (web/phaser; applied by runtime) |
| `text_color` | string | Text colour. Default `#fff` |
| `font_size` | string | Font size. Default `14px` |
| `model` | string | URL to a GLB/GLTF 3D model (Three.js target) |
| `_max_output` | int | Maximum console lines; excess trimmed from top |

---

## Events

Events are handled with `when <event>` (block) or `on <event>` (one-liner).

### Built-in events

| Event | Args | Fires when |
|-------|------|------------|
| `start` | — | Programme first runs |
| `update` | `dt` | Every frame (approx. 60 fps). `dt` = delta seconds |
| `click` | `x, y` | Canvas clicked anywhere |
| `click_<name>` | `x, y` | Specific object clicked |
| `keydown` | `key` | Key pressed. `key` is the KeyboardEvent key string |
| `keyup` | `key` | Key released |
| `collision` | `a, b` | Two objects overlap |
| `scene_enter` | `scene` | Scene navigation arrived |
| `scene_exit` | `scene` | Scene navigation departed |
| `destroy` | `name` | Object was destroyed |
| `timer_done` | `name` | Timer widget reached zero |
| `game_start` | — | Game lifecycle started |
| `game_over` | — | Game lifecycle ended (auto-fires when `lives.count` hits 0) |
| `game_restart` | — | Player restarted after game over |

### User-defined events

```rosh
event scored value        # declare an event with a payload variable
send scored 10            # emit it; handlers receive value=10

when scored
  set score.value to score.value + value
end
```

### Delayed events

```rosh
after 3 send timeout      # fire 'timeout' after 3 seconds
after 0.5 send scored 5   # fire with payload
```

### Key-hold detection

Check `_keys.ArrowLeft == 1` inside a `when update` block:

```rosh
on update
  if _keys.ArrowLeft == 1
    set player.x to player.x - 0.01
  end
end
```

### Conditional listeners

```rosh
on keydown when key == " " play laser
on update when score.value > 100 send level_up
```

### Collision wildcard

`bullet.*` matches all pool members — either argument can be a wildcard:

```rosh
when collision bullet.* enemy
  set score.value to score.value + 1
end
```

---

## Control Flow

### If / else

```rosh
if score > 10
  print "win!"
else if score > 5
  print "close!"
else
  print "keep going"
end
```

One `end` closes the whole chain.

Operators: `>`, `<`, `>=`, `<=`, `==`, `!=`

### Repeat

```rosh
repeat 5
  print "hello"
end

repeat 3 as i            # i counts from 1 to 3
  print "Round {i}"
end
```

### For each (over a captured list)

```rosh
get all into items
repeat items as item
  print "{item.name}"
end
```

---

## Functions

```rosh
define fire_bullet
  set bullet._x to player.x
  set bullet._y to player.y
  set bullet._fire to 1
end

do fire_bullet                          # call it
on keydown when key == " " do fire_bullet   # call from event
```

Functions share the global state space — they read and write the same variables as the main programme.

---

## Scenes

```rosh
create scene title
  print "Press space to start"
  when keydown
    go game
  end
end

create scene game
  use player speed 0.03
  use score
end

go title                  # navigate to a scene
```

`go` triggers `scene_exit` on the current scene and `scene_enter` on the target.

```rosh
background "#1a1a2e"       # set scene/canvas background (colour or image URL)
```

---

## Media — Sprites

Sprites attach images to objects.

### Procedural

```rosh
sprite ship "blue spaceship"
sprite gem "red crystal"
sprite enemy "green alien"
```

Keywords generate 7×9 pixel art. Colour keywords: `red`, `blue`, `green`, `yellow`, `orange`, `purple`, `white`, `black`, `grey`, `cyan`, `magenta`. Shape keywords: `spaceship`, `alien`, `ball`, `bullet`, `crystal`, `star`, `robot`, `shield`.

Sprites fill the entire `width × height` box with pixelated upscaling (crisp edges).

### URL

```rosh
sprite ship "https://example.com/ship.png"
sprite coin "https://cdn.jsdelivr.net/..."
```

Any `http://` or `https://` URL is loaded directly. URL sprites are `contain`-fitted (preserves aspect ratio, smooth rendering). If the URL fails to load the object falls back to a coloured rectangle.

Both modes can be mixed in the same programme.

### Spritesheet animation

```rosh
animate player sheet "player-sheet.png" frames 4
animate player sheet "player-sheet.png" frames 4 speed 0.1 mode loop
```

`mode` options: `loop` (default), `once`, `pingpong`.

---

## Media — Sounds

```rosh
sound laser "laser shoot"    # declare a sound
play laser                   # play once
play laser loop              # loop
play laser stop              # stop looping
```

Nine preset sound families matched by keyword in the description: `laser`, `explosion`, `coin`, `jump`, `hit`, `powerup`, `gameover`, `click`, `win`. The synthesiser generates Web Audio waveforms — no audio files required.

---

## Media — 3D Assets

When using the Three.js or world targets, objects can reference named real-world assets.

The asset registry resolves plain names to 3D representations. If a GLB model is available it loads asynchronously; a primitive fallback shape renders immediately and is replaced on success. If the model fails to load (offline, 404) the fallback stays visible — nothing blocks.

### How it works

```rosh
# target: threejs
create object stone          # registry finds stone.json → fallback_shape=box, color=grey
create object display_case   # registry finds display_case.json → fallback_shape=box, color=lightblue
create object torch          # registry finds torch.json → fallback_shape=cylinder, color=orange
```

Object names and aliases are fuzzy-matched. `"ancient carved stone"`, `"carving"`, and `"stone"` all resolve to the `stone` manifest.

### Asset manifests

Manifests live in `rosh-lang/src/rosh_lang/media/asset_manifests/` as JSON. Each has:

```json
{
  "id": "torch",
  "name": "Torch",
  "version": "0.1",
  "visibility": "featured",
  "review_status": "featured",
  "tags": ["torch", "light", "fire", "museum"],
  "defaults": { "color": "orange", "shape": "cylinder" },
  "representations": {
    "text": { "description": "A flaming torch mounted on a wall." },
    "threejs": {
      "fallback_shape": "cylinder",
      "model": "",
      "scale": [0.08, 0.7, 0.08]
    }
  }
}
```

`model` is empty until a GLB is downloaded and either uploaded to the CDN (`https://assets.rosh.cloud/3d/`) or served locally at `/assets/3d/`.

### Bundled manifests (18)

**General**: `ball`, `box`, `coin`, `door`, `key`, `painting`, `person`, `platform`, `stone`, `tree`

**Museum / heritage**: `display_case`, `pedestal`, `exhibit_label`, `carved_relief`, `necklace`, `brooch`, `torch`, `spotlight`

---

## Widgets

Widgets are pre-built composable components. They install themselves into the programme — their behaviour (event handlers, state) runs alongside your code.

```rosh
use <widget> [key value ...]
```

Config pairs are space-separated after the widget name. All keys are optional; defaults apply.

### Full widget reference

| Widget | Config keys | Default | Purpose |
|--------|-------------|---------|---------|
| `score` | `label x y bg text_color font_size anchor theme` | label="Score", x=0.01, y=0.01 | HUD score display |
| `player` | `speed keys move x y width height color clamp_x clamp_y` | speed=0.05, keys=arrows | Keyboard-controlled ship/avatar |
| `controller` | `target keys touch touch_style speed move help fire fire_key fire_event clamp` | — | Universal input — keyboard + touch |
| `lives` | `count auto_gameover x y bg text_color font_size` | count=3, auto_gameover=true | Lives counter; fires `game_over` at 0 |
| `timer` | `total running x y bg text_color font_size` | total=60, running=false | Countdown; fires `timer_done` when done |
| `health-bar` | `max current x y bg text_color font_size` | max=100, current=100 | Health display |
| `bullet` | `count vx vy color` | count=3, vy=-0.5 | Pooled projectile objects |
| `explosion` | `count color` | count=5 | Pooled explosion particles |
| `hazard` | `count vx vy color width height sprite spawn_rate` | count=5 | Auto-spawning obstacle pool |
| `ball` | `x y size color vx vy walls` | size=0.05, walls=true | Bouncing ball with wall reflection |
| `starfield` | `count` | count=50 | Background scrolling stars |
| `grid` | `rows cols size gap color` | rows=8, cols=8 | Cell grid overlay |
| `enemy-grid` | `rows cols size gap color` | rows=3, cols=8 | Enemy formation |
| `animation` | `target sheet frames speed mode` | speed=0.1, mode=loop | Spritesheet animator |
| `fps` | `x y bg text_color font_size` | x=0.85, y=0.01 | FPS counter |
| `score` | see above | | |
| `button` | (configure by setting button.label etc.) | — | Clickable button |
| `label` | `text x y bg text_color font_size` | — | Static text label |
| `message` | `text x y bg text_color font_size` | — | Overlay message |
| `title-screen` | `title subtitle bg text_color font_size` | — | Full-canvas title screen |
| `game-lifecycle` | `title subtitle bg text_color font_size` | — | Title → playing → game over flow |
| `counter` | (bare widget; click to increment) | — | Click counter |
| `coin` | (bare widget; collectible) | — | Collectible coin |

### Widget examples

```rosh
use score label "Points" x 0.01 y 0.01
use lives count 5
use timer total 90
use player speed 0.04 move x clamp_x true
use controller target player touch true fire true fire_key " "
use bullet count 5 vy -0.6 color "#ff0"
use hazard count 8 sprite "red asteroid" spawn_rate 2
```

---

## Targets

### Terminal

```bash
rosh hello.rosh
```

`print` writes to stdout. Events are not active (no game loop). Good for scripts and REPL exploration.

### Web

```bash
rosh hello.rosh --target web --run
```

Generates a self-contained HTML file. Objects are CSS `div` elements positioned by percentage. All events active. The output file has no dependencies — share it as a single `.html`.

### Phaser (2D game)

```bash
rosh hello.rosh --target phaser --run
```

Renders via [Phaser 3](https://phaser.io) on a `<canvas>`. Physics, collision detection, and input are all Phaser-native. Same `.rosh` syntax — the compiler emits Phaser API calls.

### Three.js (3D scene)

```bash
rosh hello.rosh --target threejs --run
```

Renders via [Three.js](https://threejs.org). Objects become 3D meshes. Additional properties active:

| Property | Description |
|----------|-------------|
| `z` | Depth position |
| `shape` | `box`, `sphere`, `cylinder`, `cone`, `torus`, `plane` |
| `rx`, `ry`, `rz` | Rotation in radians |
| `model` | URL to a GLB model file |

The scene includes orbit controls — drag to rotate, scroll to zoom.

**Model loading**: if `model` is set, Three.js loads it via `GLTFLoader` asynchronously. The primitive fallback shape renders immediately and is replaced when the model loads. On failure (offline, 404), the fallback stays — nothing blocks.

### Scratch

```bash
rosh hello.rosh --target scratch
```

Exports a `.sb3` file for import into [Scratch 3](https://scratch.mit.edu). Covers `print`, `create`, `set`, basic `when` handlers, and `say`.

### World (rosh-world)

The world target is a live networked 3D/2D world backed by a persistent server. Objects are authored via the REPL and live in a named world. Multiple viewers can connect simultaneously.

The world uses a separate launcher, `rosh-world/bin/roshworld`, that wraps the server and REPL — named distinctly from `rosh` so it never shadows the real rosh-lang CLI, even with `rosh-world/bin` on your `PATH`.

```bash
# rosh-lang CLI (always available, always what bare `rosh` runs)
rosh hello.rosh --target world   # run a .rosh file against a world server
rosh --version                    # print rosh-lang version
rosh                              # local interactive REPL — build, then `push <slug>` to rosh.cloud

# rosh-world launcher (requires rosh-world/bin on PATH — separate command, never shadows `rosh`)
roshworld                         # REPL connected to default world (rosh/museum)
roshworld gsa/demo-2026           # REPL connected to a specific world
roshworld --start                 # start the rosh-world server in background
roshworld --open rosh/museum      # open 3D viewer in browser
roshworld --stop                  # stop the background server
```

---

## Asset Registry and CLI

The asset system lets you build up a library of named 3D models that your programmes can reference by plain name.

### Pipeline overview

```
1. Discover    →  rosh assets search requests.json --provider sketchfab --save review.json
2. Review      →  edit review.json, set "decision": "accept" on chosen candidates
3. Download    →  rosh assets acquire review.json
4. Register    →  rosh assets register review.json --output-dir drafts/
5. Promote     →  move draft manifest to asset_manifests/, set review_status=featured
```

### Search

```bash
rosh assets search requests.json --provider sketchfab --limit 5 --save review.json
```

`requests.json` is a list of `{"object": "torch", "query": "medieval wall torch", "target": "threejs"}` objects. The search hits the Sketchfab API (requires `SKETCHFAB_API_TOKEN` in `.env`) and writes a review template.

### Review file format

```json
[
  {
    "request": "torch",
    "query": "medieval wall torch",
    "decision": "accept",
    "candidate_id": "77db436da2844cbfb4dde0bb9b396835",
    "candidate_name": "Medieval Wall Torch",
    "provider": "sketchfab",
    "licence": "CC Attribution",
    "source_url": "https://sketchfab.com/...",
    "author": "SomeArtist",
    "formats": ["thumbnail", "glb"],
    "downloadable": true,
    "proposed_manifest_id": "torch_wall",
    "notes": "Game-ready, 1.7k faces"
  }
]
```

`decision` values: `"pending"` (default), `"accept"`, `"reject"`, `"defer"`.

### Acquire (download)

```bash
rosh assets acquire review.json          # download all accepted entries
rosh assets acquire <candidate_id> --asset-id torch_wall   # single download
```

GLB files are saved to `~/.rosh/cache/3d/`. The rosh-world server serves them at `/assets/3d/`.

### Register (create draft manifests)

```bash
rosh assets register review.json --output-dir drafts/
```

Validates licences (blocks non-commercial, warns on NC), writes draft JSON manifests with `visibility=private`, `review_status=draft`, and an empty `model` field.

### Cache management

```bash
rosh assets cache list       # show cached files and sizes
rosh assets cache clear      # remove all cached GLBs
```

### Manifest model URL convention

| Context | URL format |
|---------|------------|
| Local dev (rosh-world running) | `/assets/3d/torch_wall.glb` |
| Production (after R2 upload) | `https://assets.rosh.cloud/3d/torch_wall.glb` |
| Not yet uploaded | `""` (empty — fallback shape renders) |

Set the `representations.threejs.model` field in the manifest after acquiring and reviewing the model.

### Licence policy

| Licence | Status |
|---------|--------|
| CC0, Public Domain | Permitted |
| CC BY, CC BY-SA | Permitted (attribution required) |
| CC BY-NC, CC BY-NC-SA | Blocked (non-commercial restriction) |
| All Rights Reserved | Blocked |

---

## Patterns and Examples

### Hello world (terminal)

```rosh
print "Hello, world!"
```

### Counter (web)

```rosh
create object count
set count.value to 0
set count.x to 0.4
set count.y to 0.4
set count.label to "0"

when click
  set count.value to count.value + 1
  set count.label to "{count.value}"
end
```

### Minimal game (Phaser)

```rosh
use score
use lives count 3
use player speed 0.03 move x
sprite player "green spaceship"
use bullet count 3 vy -0.5 color "#ffff00"

create object enemy
set enemy.x to 0.45
set enemy.y to 0.1
set enemy.width to 0.08
sprite enemy "red alien"

sound laser "laser shoot"

on keydown when key == " " set bullet._x to player.x
on keydown when key == " " set bullet._y to player.y
on keydown when key == " " set bullet._fire to 1
on keydown when key == " " play laser

when collision bullet.* enemy
  set score.value to score.value + 1
end

when game_over
  print "Game over — Score: {score.value}"
end
```

Run: `rosh game.rosh --target phaser --run`

### 3D spinning objects (Three.js)

```rosh
# target: threejs

create object cube
set cube.x to -2
set cube.y to 1
set cube.shape to "box"
set cube.color to "cyan"

create object sphere
set sphere.x to 2
set sphere.y to 1
set sphere.shape to "sphere"
set sphere.color to "orange"

on update set cube.ry to cube.ry + 0.02
on update set sphere.ry to sphere.ry + 0.03
```

Run: `rosh scene.rosh --target threejs --run`

### Museum scene (Three.js with assets)

```rosh
# target: threejs

create object display_case
set display_case.x to 0
set display_case.y to 0

create object brooch
set brooch.x to 0
set brooch.y to 1.5

create object exhibit_label
set exhibit_label.x to 0
set exhibit_label.y to -0.5
set exhibit_label.label to "Rhynie Brooch, 6th c."

create object spotlight
set spotlight.x to 0
set spotlight.y to 3

print "Welcome to the museum."
```

### Scenes with navigation

```rosh
create scene title
  use title-screen title "My Game" subtitle "Press space"
  on keydown when key == " " go game
end

create scene game
  use score
  use player speed 0.04
end

go title
```

### Looping timer

```rosh
use timer total 30

create object warning
set warning.visible to 0
set warning.label to "Time running out!"

when timer_done
  set warning.visible to 1
  print "Time is up!"
end
```

---

## Licence

Rosh is MIT licensed. All bundled widgets and asset manifests carry their own licence declarations. Third-party 3D models carry their upstream licences (CC Attribution, CC0, etc.) — see each manifest's `licence` and `source_url` fields.

---

*This document is the canonical Rosh language reference. The parser is the ground truth for what parses; this document is the ground truth for what should parse. If they disagree, that's a bug.*
