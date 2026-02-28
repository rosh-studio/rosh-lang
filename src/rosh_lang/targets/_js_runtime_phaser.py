"""Phaser renderer layer for interactive Rosh programmes.

Replaces JS_RUNTIME_DOM when targeting Phaser.  Plugs into the same
JS_RUNTIME_CORE (state, events, interpolation, audio synthesis).

Usage:
    JS_RUNTIME_CORE + JS_RUNTIME_PHASER  →  Phaser game in HTML
"""

# ── Phaser-specific renderer ──────────────────────────────────
#
# Syncs rosh.state → Phaser game objects, handles input,
# runs AABB collision detection (edge-triggered, same as DOM).

JS_RUNTIME_PHASER = """\

(function() {
  var W = 800, H = 600;
  var sprites = {};       // name → Phaser.GameObjects
  var labels = {};        // name → Phaser.Text (for labeled objects)
  var prevCollisions = {};
  var scene;
  var outputText;

  // Coord conversion: 0-1 → pixels, >1 → raw pixels
  function px(v, dim) { return (v >= 0 && v <= 1) ? v * dim : v; }

  // Color: "#ff0000" → 0xff0000
  function parseColor(c) {
    if (typeof c === "string" && c[0] === "#") {
      return parseInt(c.slice(1), 16);
    }
    // Named color fallback — let Phaser handle it via a canvas trick
    var map = {
      "red": 0xff0000, "green": 0x00ff00, "blue": 0x0000ff,
      "yellow": 0xffff00, "cyan": 0x00ffff, "magenta": 0xff00ff,
      "white": 0xffffff, "black": 0x000000, "orange": 0xff8800,
      "purple": 0x800080, "pink": 0xff69b4, "gray": 0x888888,
      "grey": 0x888888
    };
    if (map[c]) return map[c];
    return 0x444444;
  }

  // Pre-decode sprite images before Phaser starts
  var _spriteImages = {};
  var _spritesReady = 0;
  var _spritesTotal = 0;
  for (var _sn in rosh._spriteData) { _spritesTotal++; }

  class GameScene extends Phaser.Scene {
    constructor() { super({ key: "GameScene" }); }

    create() {
      scene = this;

      // Register pre-decoded sprite textures
      for (var name in _spriteImages) {
        if (!this.textures.exists("spr_" + name)) {
          this.textures.addImage("spr_" + name, _spriteImages[name]);
        }
      }

      // Output text object (pinned at bottom)
      outputText = scene.add.text(16, H - 24, "", {
        fontFamily: '"SF Mono", "Fira Code", "Cascadia Code", monospace',
        fontSize: "13px",
        color: "#e0e0e0",
        wordWrap: { width: W - 32 }
      });
      outputText.setOrigin(0, 1);
      outputText.setDepth(1000);

      syncAll();

      // Keyboard input → rosh events
      this.input.keyboard.on("keydown", function(e) {
        rosh.send("keydown", {key: e.key});
      });
      this.input.keyboard.on("keyup", function(e) {
        rosh.send("keyup", {key: e.key});
      });

      // Click input → rosh events (normalized coords + hit test)
      this.input.on("pointerdown", function(pointer) {
        var nx = pointer.x / W, ny = pointer.y / H;
        for (var name in rosh.objects) {
          var s = sprites[name];
          if (s && s.getBounds().contains(pointer.x, pointer.y)) {
            rosh.send("click_" + name, {x: nx, y: ny});
          }
        }
        rosh.send("click", {x: nx, y: ny});
      });
    }

    update(time, delta) {
      var dt = delta / 1000;
      if (dt > 0.1) dt = 0.1;
      rosh.send("update", {dt: dt});
      checkCollisions();
      syncAll();
    }
  }

  function destroySprite(name) {
    if (sprites[name]) {
      sprites[name].destroy();
      delete sprites[name];
    }
    if (labels[name]) {
      labels[name].destroy();
      delete labels[name];
    }
  }

  function syncAll() {
    // Create/update Phaser game objects from rosh.state
    for (var name in rosh.objects) {
      var obj = rosh.get(name);
      if (!obj || typeof obj !== "object") {
        // Object was destroyed
        if (sprites[name]) { destroySprite(name); }
        delete rosh.objects[name];
        continue;
      }

      var x = px(obj.x != null ? obj.x : 0, W);
      var y = px(obj.y != null ? obj.y : 0, H);
      var w = px(obj.width != null ? obj.width : 0.1, W);
      var h = px(obj.height != null ? obj.height : 0.1, H);

      var s = sprites[name];
      if (!s) {
        // Create new: sprite texture or colored rectangle
        var texKey = "spr_" + name;
        if (rosh._spriteData[name] && scene.textures.exists(texKey)) {
          s = scene.add.sprite(x, y, texKey);
          s.setDisplaySize(w, h);
        } else {
          s = scene.add.rectangle(x, y, w, h, parseColor(obj.color || "#444"));
        }
        s.setOrigin(0, 0);  // top-left origin (matches CSS positioning)
        sprites[name] = s;
      }

      // Update position and size
      s.setPosition(x, y);
      s.setDisplaySize(w, h);

      // Update color (rectangles only)
      if (s.setFillStyle) {
        s.setFillStyle(parseColor(obj.color || "#444"));
      }

      // Label text (non-sprite objects)
      var rawLabel = obj.label != null ? obj.label : name;
      var labelText = (typeof rawLabel === "string") ? rosh.interpolate(rawLabel) : String(rawLabel);
      var hasSprite = rosh._spriteData[name];

      if (!hasSprite && labelText) {
        if (!labels[name]) {
          labels[name] = scene.add.text(x, y, labelText, {
            fontFamily: "system-ui, sans-serif",
            fontSize: "14px",
            color: "#ffffff",
            align: "center"
          });
          labels[name].setOrigin(0, 0);
        }
        labels[name].setPosition(x + 4, y + 4);
        labels[name].setText(labelText);
      } else if (labels[name]) {
        labels[name].destroy();
        delete labels[name];
      }
    }

    // Remove sprites for destroyed objects
    for (var d in sprites) {
      if (!(d in rosh.objects)) destroySprite(d);
    }
  }

  // ── Collision detection (AABB, edge-triggered) ────────
  function checkCollisions() {
    var names = Object.keys(rosh.objects);
    var current = {};
    for (var i = 0; i < names.length; i++) {
      for (var j = i + 1; j < names.length; j++) {
        var a = names[i], b = names[j];
        var oa = rosh.get(a), ob = rosh.get(b);
        if (!oa || !ob) continue;
        if (oa.x == null || oa.y == null || ob.x == null || ob.y == null) continue;
        var ax = px(oa.x, W), ay = px(oa.y, H);
        var aw = px(oa.width || 0.1, W), ah = px(oa.height || 0.1, H);
        var bx = px(ob.x, W), by = px(ob.y, H);
        var bw = px(ob.width || 0.1, W), bh = px(ob.height || 0.1, H);
        if (ax < bx + bw && ax + aw > bx &&
            ay < by + bh && ay + ah > by) {
          var pair = a + ":" + b;
          current[pair] = true;
          if (!prevCollisions[pair]) {
            rosh.send("collision", {a: a, b: b});
          }
        }
      }
    }
    prevCollisions = current;
  }

  // Expose on rosh (same interface as DOM layer)
  rosh.syncAll = syncAll;
  rosh.appendOutput = function(text) {
    if (outputText) {
      var cur = outputText.text || "";
      outputText.setText(cur + text + "\\n");
    }
  };
  rosh.startLoop = function() { /* Phaser handles the loop */ };

  // Pre-decode base64 sprites, then start Phaser
  function startGame() {
    new Phaser.Game({
      type: Phaser.AUTO,
      width: W,
      height: H,
      parent: "game-container",
      backgroundColor: "#16213e",
      scene: [GameScene],
      banner: false
    });
  }

  if (_spritesTotal === 0) {
    startGame();
  } else {
    for (var _k in rosh._spriteData) {
      (function(key) {
        var img = new Image();
        img.onload = function() {
          _spriteImages[key] = img;
          _spritesReady++;
          if (_spritesReady >= _spritesTotal) startGame();
        };
        img.onerror = function() {
          _spritesReady++;
          if (_spritesReady >= _spritesTotal) startGame();
        };
        img.src = rosh._spriteData[key];
      })(_k);
    }
  }
})();
"""
