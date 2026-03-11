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

    preload() {
      // Use Phaser's loader for URL sprites (handles CORS properly)
      this.load.setCORS("anonymous");
      for (var name in rosh._spriteData) {
        var uri = rosh._spriteData[name];
        if (uri.startsWith("http://") || uri.startsWith("https://")) {
          this.load.image("spr_" + name, uri);
        }
      }
    }

    create() {
      scene = this;

      // Register pre-decoded data-URI sprite textures (non-URL ones)
      for (var name in _spriteImages) {
        if (!this.textures.exists("spr_" + name)) {
          this.textures.addImage("spr_" + name, _spriteImages[name]);
        }
      }

      // Output text object (pinned at bottom)
      outputText = scene.add.text(16, H - 16, "", {
        fontFamily: '"SF Mono", "Fira Code", "Cascadia Code", monospace',
        fontSize: "13px",
        color: "#e0e0e0",
        wordWrap: { width: W - 32 }
      });
      outputText.setOrigin(0, 1);
      outputText.setDepth(1000);
      outputText.setScrollFactor(0);

      syncAll();

      // Keyboard input → rosh events
      this.input.keyboard.on("keydown", function(e) {
        rosh.state._keys[e.key] = 1;
        rosh.send("keydown", {key: e.key});
      });
      this.input.keyboard.on("keyup", function(e) {
        rosh.state._keys[e.key] = 0;
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

      // Flush any output buffered before Phaser scene was ready
      if (rosh._outputBuffer && rosh._outputBuffer.length) {
        rosh._outputBuffer.forEach(function(t) { rosh.appendOutput(t); });
        rosh._outputBuffer = [];
      }

      // Fire start event after scene is ready
      rosh.send("start", {});
    }

    update(time, delta) {
      var dt = delta / 1000;
      if (dt > 0.1) dt = 0.1;
      if (rosh.state._paused) {
        syncAll();
        return;
      }
      rosh.send("update", {dt: dt});
      rosh.tickVelocity(dt);
      rosh.tickPools(dt);
      rosh.tickTimers(dt);
      rosh.tickAnimations(dt);
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
    // Apply background if changed
    var bg = rosh.state._background;
    if (bg && bg !== scene._appliedBg) {
      if (rosh.state._backgroundType === "image") {
        // Load image as background — use Phaser loader
        var bgKey = "_rosh_bg";
        if (!scene.textures.exists(bgKey)) {
          var bgImg = new Image();
          bgImg.onload = function() {
            scene.textures.addImage(bgKey, bgImg);
            var bgSprite = scene.add.image(W / 2, H / 2, bgKey);
            bgSprite.setDisplaySize(W, H);
            bgSprite.setDepth(-1000);
          };
          bgImg.src = bg;
        }
      } else {
        scene.cameras.main.setBackgroundColor(bg);
      }
      scene._appliedBg = bg;
    }
    // Create/update Phaser game objects from rosh.state
    for (var name in rosh.objects) {
      var obj = rosh.get(name);
      if (!obj || typeof obj !== "object") {
        // Object was destroyed
        if (sprites[name]) { destroySprite(name); }
        delete rosh.objects[name];
        continue;
      }

      // Visibility check: visible === 0 or visible === false hides the object
      var isVisible = !(obj.visible === 0 || obj.visible === false);
      // Group visibility: if any parent namespace has visible === 0, hide
      if (isVisible) {
        var _gParts = name.split(".");
        for (var _gi = 1; _gi < _gParts.length; _gi++) {
          var _gParent = rosh.get(_gParts.slice(0, _gi).join("."));
          if (_gParent && (_gParent.visible === 0 || _gParent.visible === false)) {
            isVisible = false;
            break;
          }
        }
      }
      // Hide pool objects parked off-screen (either axis well below 0)
      if ((typeof obj.x === "number" && obj.x < -0.5) || (typeof obj.y === "number" && obj.y < -0.5)) {
        isVisible = false;
      }
      if (sprites[name]) {
        sprites[name].setVisible(isVisible);
        if (labels[name]) labels[name].setVisible(isVisible);
      }
      if (!isVisible) continue;

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
          s._roshSpriteUri = rosh._spriteData[name];  // prevent false frame-change on first tick
        } else {
          s = scene.add.rectangle(x, y, w, h, parseColor(obj.color || "#444"));
        }
        s.setOrigin(0, 0);  // top-left origin (matches CSS positioning)
        sprites[name] = s;
      }

      // Update position and size
      s.setPosition(x, y);
      // URL sprites: scale uniformly (contain) to preserve aspect ratio
      if (s.texture && s.texture.key !== "__DEFAULT" && rosh._spriteData[name] &&
          (rosh._spriteData[name].indexOf("http") === 0)) {
        var tw = s.texture.getSourceImage().width || w;
        var th = s.texture.getSourceImage().height || h;
        var scale = Math.min(w / tw, h / th);
        s.setScale(scale);
      } else {
        s.setDisplaySize(w, h);
      }

      // Rotation (degrees, 0 = up, clockwise positive)
      if (obj.rotation != null) {
        s.setAngle(obj.rotation);
      }

      // Check if animated sprite frame changed — re-register texture
      if (rosh._spriteData[name] && s._roshSpriteUri !== rosh._spriteData[name]) {
        var newUri = rosh._spriteData[name];
        var newKey = "spr_" + name + "_" + (s._roshTexIdx = (s._roshTexIdx || 0) + 1);
        var tempImg = new Image();
        if (newUri.startsWith("http://") || newUri.startsWith("https://")) {
          tempImg.crossOrigin = "anonymous";
        }
        tempImg.onload = (function(k, sp, nk) {
          return function() {
            if (scene.textures.exists(nk)) return;
            scene.textures.addImage(nk, tempImg);
            sp.setTexture(nk);
          };
        })(name, s, newKey);
        tempImg.src = newUri;
        s._roshSpriteUri = newUri;
      }

      // Update color (rectangles only)
      if (s.setFillStyle) {
        s.setFillStyle(parseColor(obj.color || "#444"));
      }

      // Label text (non-sprite objects)
      var rawLabel = obj.label != null ? obj.label : "";
      var labelText = (typeof rawLabel === "string") ? rosh.interpolate(rawLabel) : String(rawLabel);
      var hasSprite = rosh._spriteData[name];

      if (!hasSprite && labelText) {
        if (!labels[name]) {
          labels[name] = scene.add.text(x, y, labelText, {
            fontFamily: "system-ui, sans-serif",
            fontSize: obj.font_size || "14px",
            color: obj.text_color || "#ffffff",
            align: "center"
          });
          labels[name].setOrigin(0, 0);
        }
        labels[name].setPosition(x + 4, y + 4);
        labels[name].setText(labelText);
        labels[name].setStyle({fontSize: obj.font_size || "14px", color: obj.text_color || "#ffffff"});
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
        if (oa.visible === 0 || oa.visible === false) continue;
        if (ob.visible === 0 || ob.visible === false) continue;
        if (oa.x == null || oa.y == null || ob.x == null || ob.y == null) continue;
        if (oa.x < -0.5 || oa.y < -0.5) continue;
        if (ob.x < -0.5 || ob.y < -0.5) continue;
        var ax = px(oa.x, W), ay = px(oa.y, H);
        var aw = px(oa.width || 0.1, W), ah = px(oa.height || 0.1, H);
        var bx = px(ob.x, W), by = px(ob.y, H);
        var bw = px(ob.width || 0.1, W), bh = px(ob.height || 0.1, H);
        if (ax < bx + bw && ax + aw > bx &&
            ay < by + bh && ay + ah > by) {
          var pair = a + ":" + b;
          current[pair] = true;
          if (!prevCollisions[pair]) {
            rosh.send("collision", {a: a, b: b, a_x: oa.x, a_y: oa.y, b_x: ob.x, b_y: ob.y});
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
      var full = cur + text + "\\n";
      var max = rosh.state._max_output;
      if (typeof max === "number" && max > 0) {
        var lines = full.split("\\n");
        if (lines.length > max + 1) {
          full = lines.slice(lines.length - max - 1).join("\\n");
        }
      }
      outputText.setText(full);
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
      backgroundColor: (rosh.state._backgroundType === "color" && rosh.state._background) ? rosh.state._background : "#16213e",
      scene: [GameScene],
      banner: false
    });
  }

  if (_spritesTotal === 0) {
    startGame();
  } else {
    for (var _k in rosh._spriteData) {
      (function(key) {
        var uri = rosh._spriteData[key];
        // Skip URL sprites — they're loaded by Phaser's preload()
        if (uri.startsWith("http://") || uri.startsWith("https://")) {
          _spritesReady++;
          if (_spritesReady >= _spritesTotal) startGame();
          return;
        }
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
        img.src = uri;
      })(_k);
    }
  }
})();
"""
