"""Three.js renderer layer for 3D Rosh programmes.

Replaces JS_RUNTIME_DOM / JS_RUNTIME_PHASER when targeting Three.js.
Plugs into the same JS_RUNTIME_CORE (state, events, interpolation, audio).

Usage:
    JS_RUNTIME_CORE + JS_RUNTIME_THREEJS               →  Three.js 3D scene
    JS_RUNTIME_CORE + JS_RUNTIME_THREEJS + JS_VOICE    →  + voice input (V key)
"""

# ── Three.js-specific renderer ──────────────────────────────
#
# Syncs rosh.state → THREE.Object3D meshes, handles input,
# runs Box3 AABB collision detection (edge-triggered, same as DOM/Phaser).

JS_RUNTIME_THREEJS = """\

(function() {
  var W = 800, H = 600;
  var meshes = {};       // name → THREE.Mesh / THREE.Group
  var prevCollisions = {};
  var scene, camera, renderer, controls;
  var outputDiv;

  // ── 2D-in-3D detection ────────────────────────────────────
  // If _view=="2d", objects use 0-1 normalised coords (same as web/phaser).
  // We map them to a visible plane: x*SCALE, (1-y)*SCALE, z=0.
  // If _view is not set, auto-detect from object coordinates on first frame.
  var is2D = false;
  var _autoDetected = false;
  var SCALE2D = 10;  // 0-1 maps to 0-10 world units

  // ── Color parsing ────────────────────────────────────────
  var colorMap = {
    "red": 0xff0000, "green": 0x00ff00, "blue": 0x0000ff,
    "yellow": 0xffff00, "cyan": 0x00ffff, "magenta": 0xff00ff,
    "white": 0xffffff, "black": 0x000000, "orange": 0xff8800,
    "purple": 0x800080, "pink": 0xff69b4, "gray": 0x888888,
    "grey": 0x888888
  };

  function parseColor(c) {
    if (typeof c === "string" && c[0] === "#") {
      return parseInt(c.slice(1), 16);
    }
    if (colorMap[c]) return colorMap[c];
    return 0x444444;
  }

  // ── Text label sprite factory ───────────────────────────
  var labelSprites = {};  // name → THREE.Sprite

  function makeLabel(text, textColor, fontSize) {
    var canvas = document.createElement("canvas");
    var ctx = canvas.getContext("2d");
    var size = parseInt(fontSize) || 14;
    var px = Math.max(size * 3, 42);
    var font = "bold " + px + "px system-ui, sans-serif";
    // Measure with correct font
    ctx.font = font;
    var tw = ctx.measureText(text).width;
    canvas.width = Math.ceil(tw + 32);
    canvas.height = Math.ceil(px * 1.4);
    // Re-set font after resize (canvas resize clears state)
    ctx.font = font;
    ctx.fillStyle = textColor || "#ffffff";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(text, canvas.width / 2, canvas.height / 2);
    var tex = new THREE.CanvasTexture(canvas);
    tex.minFilter = THREE.LinearFilter;
    var mat = new THREE.SpriteMaterial({map: tex, transparent: true, depthTest: false});
    var sprite = new THREE.Sprite(mat);
    sprite._labelText = text;
    sprite._labelColor = textColor;
    // Scale sprite to match text width in world units
    var aspect = canvas.width / canvas.height;
    var spriteH = 0.8;
    sprite.scale.set(spriteH * aspect, spriteH, 1);
    return sprite;
  }

  // ── Geometry factory ─────────────────────────────────────
  function createGeometry(shape) {
    switch ((shape || "cube").toLowerCase()) {
      case "sphere":
      case "circle":
      case "ball":
      case "orb":      return new THREE.SphereGeometry(0.5, 24, 24);
      case "cylinder": return new THREE.CylinderGeometry(0.5, 0.5, 1, 24);
      case "cone":     return new THREE.ConeGeometry(0.5, 1, 24);
      case "torus":    return new THREE.TorusGeometry(0.35, 0.15, 16, 32);
      case "plane":    return new THREE.PlaneGeometry(1, 1);
      default:         return new THREE.BoxGeometry(1, 1, 1);
    }
  }

  // ── GLB model loader ─────────────────────────────────────
  function loadModel(name, url, obj) {
    if (typeof THREE.GLTFLoader === "undefined") {
      console.warn("GLTFLoader not available — using placeholder for", name);
      return;
    }
    var loader = new THREE.GLTFLoader();
    loader.load(url, function(gltf) {
      var model = gltf.scene;
      var w = obj.width != null ? obj.width : 1;
      var h = obj.height != null ? obj.height : 1;
      var d = obj.depth != null ? obj.depth : w;
      model.scale.set(w, h, d);
      model.position.set(obj.x || 0, obj.y || 0, obj.z || 0);
      // Replace placeholder
      if (meshes[name]) {
        scene.remove(meshes[name]);
      }
      scene.add(model);
      meshes[name] = model;
      meshes[name]._isModel = true;
    }, undefined, function(err) {
      console.error("Failed to load model for", name, err);
    });
  }

  // ── Scene setup ──────────────────────────────────────────
  scene = new THREE.Scene();
  scene.background = new THREE.Color(0x16213e);

  // Default: perspective camera for 3D scenes
  camera = new THREE.PerspectiveCamera(60, W / H, 0.1, 1000);
  camera.position.set(0, 5, 10);
  camera.lookAt(0, 0, 0);

  var container = document.getElementById("scene-container");
  renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setSize(W, H);
  renderer.setPixelRatio(window.devicePixelRatio);
  container.appendChild(renderer.domElement);

  // OrbitControls (optional — only if loaded)
  if (typeof THREE.OrbitControls !== "undefined") {
    controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
  }

  // Lighting
  var ambient = new THREE.AmbientLight(0xffffff, 0.6);
  scene.add(ambient);
  var directional = new THREE.DirectionalLight(0xffffff, 0.8);
  directional.position.set(5, 10, 7);
  scene.add(directional);

  // Grid helper (hidden in 2D mode)
  var grid = new THREE.GridHelper(20, 20, 0x444444, 0x333333);
  scene.add(grid);

  // ── Switch to 2D camera ────────────────────────────────────
  function switchTo2D() {
    if (is2D) return;
    is2D = true;

    var cx = SCALE2D / 2;  // center of play area
    var cz = SCALE2D / 2;

    // 2.5D: perspective camera at a slight angle, fixed position
    // Gives depth while keeping gameplay clear
    camera = new THREE.PerspectiveCamera(45, W / H, 0.1, 100);
    camera.position.set(cx, 14, SCALE2D + 6);  // above and slightly behind
    camera.lookAt(cx, 0, cz - 0.5);  // look at centre, slightly above

    // Disable orbit controls in 2D mode (prevents camera confusion)
    if (controls) {
      controls.dispose();
      controls = null;
    }
    // Hide grid in 2D mode — add a subtle ground plane instead
    grid.visible = false;
    var groundGeo = new THREE.PlaneGeometry(SCALE2D * 1.5, SCALE2D * 1.5);
    var groundMat = new THREE.MeshStandardMaterial({color: 0x16213e, roughness: 0.9});
    var ground = new THREE.Mesh(groundGeo, groundMat);
    ground.rotation.x = -Math.PI / 2;
    ground.position.set(cx, -0.16, cz);
    scene.add(ground);
  }

  // Output overlay
  outputDiv = document.createElement("div");
  outputDiv.id = "output";
  outputDiv.style.cssText = "position:fixed;bottom:40px;left:16px;right:16px;" +
    "color:#e0e0e0;font-family:\\"SF Mono\\",\\"Fira Code\\",monospace;" +
    "font-size:13px;white-space:pre-wrap;pointer-events:none;max-height:120px;overflow:hidden;";
  document.body.appendChild(outputDiv);

  // ── Raycaster for click hit-test ─────────────────────────
  var raycaster = new THREE.Raycaster();
  var mouse = new THREE.Vector2();

  renderer.domElement.addEventListener("click", function(e) {
    var rect = renderer.domElement.getBoundingClientRect();
    mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
    raycaster.setFromCamera(mouse, camera);

    var clickables = [];
    for (var n in meshes) { clickables.push(meshes[n]); }
    var hits = raycaster.intersectObjects(clickables, true);
    if (hits.length > 0) {
      // Find which named mesh was hit
      for (var name in meshes) {
        var m = meshes[name];
        for (var hi = 0; hi < hits.length; hi++) {
          if (hits[hi].object === m || (m.children && hits[hi].object.parent === m)) {
            rosh.send("click_" + name, {x: hits[hi].point.x, y: hits[hi].point.y, z: hits[hi].point.z});
            break;
          }
        }
      }
    }
    rosh.send("click", {x: mouse.x, y: mouse.y});
  });

  // ── Keyboard input ───────────────────────────────────────
  document.addEventListener("keydown", function(e) {
    rosh.state._keys[e.key] = 1;
    rosh.send("keydown", {key: e.key});
  });
  document.addEventListener("keyup", function(e) {
    rosh.state._keys[e.key] = 0;
    rosh.send("keyup", {key: e.key});
  });

  // ── Monkey-patch tickVelocity for vz ─────────────────────
  var _origTickVelocity = rosh.tickVelocity;
  rosh.tickVelocity = function(dt) {
    _origTickVelocity(dt);
    for (var name in rosh.objects) {
      var obj = rosh.get(name);
      if (obj && typeof obj === "object" && typeof obj.vz === "number" && obj.vz !== 0) {
        var z = (typeof obj.z === "number") ? obj.z : 0;
        rosh.set(name + ".z", z + obj.vz * dt);
      }
    }
  };

  // ── Sync state → Three.js objects ────────────────────────
  function syncAll() {
    // Auto-detect 2D mode on first meaningful frame
    if (!_autoDetected) {
      // Check if _view is explicitly set
      if (rosh.state._view === "2d" || rosh.state._view === "2.5d") {
        switchTo2D();
        _autoDetected = true;
      } else if (rosh.state._view === "orbit") {
        // 2D game but with orbit controls enabled (game-on-a-table)
        switchTo2D();
        if (typeof THREE.OrbitControls !== "undefined") {
          controls = new THREE.OrbitControls(camera, renderer.domElement);
          controls.enableDamping = true;
          controls.dampingFactor = 0.05;
          controls.target.set(SCALE2D / 2, 0, SCALE2D / 2);
        }
        _autoDetected = true;
      } else if (rosh.state._view === "3d") {
        _autoDetected = true;  // keep perspective camera
      } else {
        // Auto-detect: if objects exist and none have z > 0, and coords are 0-1 range
        var objCount = 0;
        var hasExplicitZ = false;
        var hasNormCoords = false;
        for (var n in rosh.objects) {
          var o = rosh.get(n);
          if (!o || typeof o !== "object") continue;
          // Skip internal/meta objects (prefixed with _)
          if (n[0] === "_") continue;
          objCount++;
          if (typeof o.z === "number" && o.z > 0.01) hasExplicitZ = true;
          if (typeof o.x === "number" && o.x >= 0 && o.x <= 1.1) hasNormCoords = true;
        }
        if (objCount >= 1 && !hasExplicitZ && hasNormCoords) {
          switchTo2D();
          _autoDetected = true;
        } else if (objCount >= 1) {
          _autoDetected = true;
        }
      }
    }

    // Apply background if changed
    var bg = rosh.state._background;
    if (bg && bg !== scene._appliedBg) {
      if (rosh.state._backgroundType === "image") {
        new THREE.TextureLoader().load(bg, function(tex) {
          scene.background = tex;
        });
      } else {
        scene.background = new THREE.Color(bg);
      }
      scene._appliedBg = bg;
    }
    for (var name in rosh.objects) {
      var obj = rosh.get(name);
      if (!obj || typeof obj !== "object") {
        if (meshes[name]) {
          scene.remove(meshes[name]);
          delete meshes[name];
        }
        delete rosh.objects[name];
        continue;
      }

      // Visibility check
      var isVisible = !(obj.visible === 0 || obj.visible === false);
      if (isVisible) {
        var gParts = name.split(".");
        for (var gi = 1; gi < gParts.length; gi++) {
          var gParent = rosh.get(gParts.slice(0, gi).join("."));
          if (gParent && (gParent.visible === 0 || gParent.visible === false)) {
            isVisible = false;
            break;
          }
        }
      }

      if (meshes[name]) {
        meshes[name].visible = isVisible;
      }
      if (!isVisible) continue;

      var x = obj.x != null ? obj.x : 0;
      var y = obj.y != null ? obj.y : 0;
      var z = obj.z != null ? obj.z : 0;
      var w = obj.width != null ? obj.width : 1;
      var h = obj.height != null ? obj.height : 1;
      var d = obj.depth != null ? obj.depth : w;

      // In 2D mode: remap normalised coords to world space
      // x → x*SCALE (left to right), y → mapped to z*SCALE (top to bottom), height → 0
      if (is2D) {
        // Parked pool objects (at -1,-1 or similar negative coords) → move far off-screen
        if (x < -0.5 || y < -0.5) {
          x = -100; y = -100; z = -100;
          w = 0.01; h = 0.01; d = 0.01;
        } else {
          var wx = x * SCALE2D;
          var wz = y * SCALE2D;  // 2D y maps to 3D z (top-down view)
          x = wx;
          y = 0;  // flat on ground plane
          z = wz;
          w = (obj.width != null ? obj.width : 0.1) * SCALE2D;
          h = 0.3;  // thin slab height
          d = (obj.height != null ? obj.height : 0.1) * SCALE2D;
        }
      }

      var m = meshes[name];
      if (!m) {
        // Check for GLB model
        if (obj.model && typeof obj.model === "string") {
          // Create placeholder while loading
          var placeholderGeo = createGeometry("cube");
          var placeholderMat = new THREE.MeshStandardMaterial({color: parseColor(obj.color || "#444")});
          m = new THREE.Mesh(placeholderGeo, placeholderMat);
          scene.add(m);
          meshes[name] = m;
          loadModel(name, obj.model, obj);
        } else {
          // Primitive shape
          var geo = createGeometry(obj.shape);
          var mat = new THREE.MeshStandardMaterial({color: parseColor(obj.color || "#444")});
          m = new THREE.Mesh(geo, mat);
          scene.add(m);
          meshes[name] = m;
        }
      }

      // Update transform (coords already remapped if 2D mode)
      m.position.set(x, y, z);
      m.scale.set(Math.max(w, 0.01), Math.max(h, 0.01), Math.max(d, 0.01));

      // Rotation (rx/ry/rz in radians for 3D; rotation in degrees for 2D — 0=up, clockwise)
      if (obj.rx != null) m.rotation.x = obj.rx;
      if (obj.ry != null) m.rotation.y = obj.ry;
      if (obj.rz != null) m.rotation.z = obj.rz;
      if (obj.rotation != null && obj.rx == null && obj.ry == null && obj.rz == null) {
        // 2D rotation property: degrees → radians, applied to Y axis in 2.5D (ground plane spin)
        m.rotation.y = -(obj.rotation * Math.PI / 180);
      }

      // Update color (meshes with material)
      if (m.material && !m._isModel) {
        var newColor = parseColor(obj.color || "#444");
        if (m.material.color.getHex() !== newColor) {
          m.material.color.setHex(newColor);
        }
      }

      // Model swap: if model URL changed, reload
      if (obj.model && m._roshModelUrl !== obj.model) {
        m._roshModelUrl = obj.model;
        loadModel(name, obj.model, obj);
      }

      // Label text (canvas sprite floating above object)
      var rawLabel = obj.label != null ? String(obj.label).replace(/^"|"$/g, "") : "";
      var label = rawLabel ? rosh.interpolate(rawLabel) : "";
      var textColor = obj.text_color || "#ffffff";
      var existingLabel = labelSprites[name];
      if (label) {
        if (!existingLabel || existingLabel._labelText !== label || existingLabel._labelColor !== textColor) {
          // Create or recreate label
          if (existingLabel) scene.remove(existingLabel);
          var sprite = makeLabel(label, textColor, obj.font_size);
          scene.add(sprite);
          labelSprites[name] = sprite;
        }
        // Position label above the object
        var lbl = labelSprites[name];
        if (lbl) {
          lbl.position.set(x + Math.max(w, 0.01) / 2, y + Math.max(h, 0.01) + 0.3, z + Math.max(d, 0.01) / 2);
          lbl.visible = isVisible;
        }
      } else if (existingLabel) {
        scene.remove(existingLabel);
        delete labelSprites[name];
      }
    }

    // Remove meshes and labels for destroyed objects
    for (var dn in meshes) {
      if (!(dn in rosh.objects)) {
        scene.remove(meshes[dn]);
        delete meshes[dn];
        if (labelSprites[dn]) {
          scene.remove(labelSprites[dn]);
          delete labelSprites[dn];
        }
      }
    }
  }

  // ── Collision detection (Box3 AABB, edge-triggered) ──────
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
        var ma = meshes[a], mb = meshes[b];
        if (!ma || !mb) continue;
        var boxA = new THREE.Box3().setFromObject(ma);
        var boxB = new THREE.Box3().setFromObject(mb);
        if (boxA.intersectsBox(boxB)) {
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

  // ── Expose on rosh ───────────────────────────────────────
  rosh._controls = function() { return controls; };
  rosh.syncAll = syncAll;
  rosh.appendOutput = function(text) {
    if (outputDiv) {
      outputDiv.textContent += text + "\\n";
      var max = rosh.state._max_output;
      if (typeof max === "number" && max > 0) {
        var lines = outputDiv.textContent.split("\\n");
        if (lines.length > max + 1) {
          outputDiv.textContent = lines.slice(lines.length - max - 1).join("\\n");
        }
      }
    }
  };
  rosh.startLoop = function() { /* Three.js handles the loop */ };

  // Flush any output buffered before renderer was ready
  if (rosh._outputBuffer && rosh._outputBuffer.length) {
    rosh._outputBuffer.forEach(function(t) { rosh.appendOutput(t); });
    rosh._outputBuffer = [];
  }

  // ── Animation loop ───────────────────────────────────────
  var lastTime = 0;
  function animate(time) {
    requestAnimationFrame(animate);
    var dt = (time - lastTime) / 1000;
    lastTime = time;
    if (dt > 0.1) dt = 0.1;
    if (dt <= 0) { renderer.render(scene, camera); return; }

    if (!rosh.state._paused) {
      rosh.send("update", {dt: dt});
      rosh.tickVelocity(dt);
      rosh.tickPools(dt);
      rosh.tickTimers(dt);
      rosh.tickAnimations(dt);
      checkCollisions();
    }
    syncAll();
    if (controls) controls.update();
    renderer.render(scene, camera);
  }

  requestAnimationFrame(animate);
  rosh.send("start", {});
})();
"""

# ── Live Rosh console overlay ───────────────────────────────────────────────
#
# Always injected into Three.js output. Backtick (`) to toggle.
# Parses and executes Rosh statements live against the running scene.
# Supported: set / create / destroy / say / print / look / clear

JS_RUNTIME_CONSOLE = """\
(function() {
  var ACCENT    = "#6366f1";
  var OUTPUT_C  = "#c084fc";
  var ERROR_C   = "#f87171";
  var SUCCESS_C = "#86efac";
  var BG        = "rgba(0,0,0,0.93)";
  var BORDER    = "rgba(99,102,241,0.4)";

  var consoleOpen = false;
  var history = [];
  var historyIdx = -1;

  // ── Build DOM ────────────────────────────────────────────
  var overlay = document.createElement("div");
  overlay.id = "rosh-console";
  overlay.style.cssText = [
    "position:fixed",
    "bottom:0",
    "left:0",
    "right:0",
    "height:260px",
    "background:" + BG,
    "border-top:1px solid " + BORDER,
    "font-family:\\"SF Mono\\",\\"Fira Code\\",\\"Cascadia Code\\",monospace",
    "font-size:13px",
    "z-index:99999",
    "flex-direction:column"
  ].join(";");
  overlay.style.display = "none";

  var logPanel = document.createElement("div");
  logPanel.style.cssText = [
    "flex:1",
    "overflow-y:auto",
    "padding:8px 12px 4px 12px",
    "color:" + OUTPUT_C,
    "line-height:1.6"
  ].join(";");

  var inputRow = document.createElement("div");
  inputRow.style.cssText = [
    "display:flex",
    "align-items:center",
    "padding:6px 12px",
    "border-top:1px solid " + BORDER,
    "gap:6px"
  ].join(";");

  var promptEl = document.createElement("span");
  promptEl.textContent = "rosh>";
  promptEl.style.cssText = "color:" + ACCENT + ";font-weight:bold;user-select:none;flex-shrink:0;";

  var inputEl = document.createElement("input");
  inputEl.type = "text";
  inputEl.autocomplete = "off";
  inputEl.spellcheck = false;
  inputEl.placeholder = "type Rosh — set / create / look / clear";
  inputEl.style.cssText = [
    "flex:1",
    "background:transparent",
    "border:none",
    "outline:none",
    "color:#e0e0e0",
    "font-family:inherit",
    "font-size:inherit",
    "caret-color:" + ACCENT
  ].join(";");

  inputRow.appendChild(promptEl);
  inputRow.appendChild(inputEl);
  overlay.appendChild(logPanel);
  overlay.appendChild(inputRow);
  document.body.appendChild(overlay);

  // ── Logging ──────────────────────────────────────────────
  function log(text, color) {
    var line = document.createElement("div");
    line.style.color = color || "#e0e0e0";
    line.style.whiteSpace = "pre-wrap";
    line.textContent = text;
    logPanel.appendChild(line);
    logPanel.scrollTop = logPanel.scrollHeight;
  }
  function logCmd(t)  { log("  " + t, "#9ca3af"); }
  function logOk(t)   { log(t, SUCCESS_C); }
  function logErr(t)  { log("Error: " + t, ERROR_C); }

  // ── Mini-parser ──────────────────────────────────────────
  // Normalise: "set box x to 1" → "set box.x to 1"
  //            "set box.x 1"    → "set box.x to 1"  (to optional)
  function normalise(cmd) {
    // "set <obj> <prop> [to] <value>" with space separator → dot notation
    var spaceSet = cmd.match(/^set\\s+(\\S+)\\s+([a-zA-Z_][\\w]*)\\s+(?:to\\s+)?([^.].*)$/);
    if (spaceSet && spaceSet[1].indexOf(".") === -1) {
      cmd = "set " + spaceSet[1] + "." + spaceSet[2] + " to " + spaceSet[3].trim();
    }
    // "set <target> <value>" → inject "to" if missing
    var missingTo = cmd.match(/^set\\s+(\\S+\\.\\S+)\\s+(?!to\\s)(.+)$/);
    if (missingTo) {
      cmd = "set " + missingTo[1] + " to " + missingTo[2].trim();
    }
    return cmd;
  }

  function execCommand(raw) {
    var cmd = raw.trim();
    if (!cmd) return;

    if (history[0] !== cmd) history.unshift(cmd);
    if (history.length > 100) history.pop();
    historyIdx = -1;

    logCmd(cmd);
    cmd = normalise(cmd);

    // clear
    if (cmd === "clear") {
      while (logPanel.firstChild) logPanel.removeChild(logPanel.firstChild);
      return;
    }

    // help
    if (cmd === "help" || cmd === "?") {
      log("  set <obj.prop> <value>    — set box.color to red", "#d1d5db");
      log("  set <obj> <prop> <value>  — set box color red", "#d1d5db");
      log("  create object <name>      — create object ball", "#d1d5db");
      log("  destroy <name>            — destroy ball", "#d1d5db");
      log("  say <text>                — say hello world", "#d1d5db");
      log("  print <text>              — print hello", "#d1d5db");
      log("  look                      — list objects + state", "#d1d5db");
      log("  clear                     — clear console", "#d1d5db");
      log("  ArrowUp/Down: history  Escape: close", "#6b7280");
      return;
    }

    // look
    if (cmd === "look") {
      var names = Object.keys(rosh.objects);
      if (!names.length) {
        log("  (no objects)", "#9ca3af");
      } else {
        names.forEach(function(n) {
          var obj = rosh.get(n);
          try { log("  " + n + ": " + JSON.stringify(obj), OUTPUT_C); }
          catch(e) { log("  " + n + ": [unprintable]", OUTPUT_C); }
        });
      }
      var stateLines = [];
      for (var k in rosh.state) {
        if (k[0] === "_") continue;
        var v = rosh.state[k];
        if (typeof v !== "object") stateLines.push(k + " = " + v);
      }
      if (stateLines.length) log("  state: " + stateLines.join(", "), "#d1d5db");
      return;
    }

    // print <text>
    var m;
    m = cmd.match(/^print\\s+(.+)$/);
    if (m) { log(m[1].replace(/^"|"$/g, ""), "#e0e0e0"); return; }

    // set <target> to <value>  (dot form, "to" now guaranteed by normalise)
    m = cmd.match(/^set\\s+(\\S+)\\s+to\\s+(.+)$/);
    if (m) {
      var tgt = m[1], rawVal = m[2].trim();
      try {
        var result = rosh.evalSetValue(tgt, rawVal);
        rosh.set(tgt, result);
        logOk("  " + tgt + " = " + JSON.stringify(result));
      } catch(e) { logErr(String(e)); }
      return;
    }

    // create [object|number|string|list] <name>  ("object" is default)
    m = cmd.match(/^create\\s+(?:(object|number|string|list)\\s+)?(\\S+)$/);
    if (m) {
      var kind = m[1] || "object", name = m[2];
      try { rosh.create(kind, name); logOk("  created " + kind + " \\"" + name + "\\""); }
      catch(e) { logErr(String(e)); }
      return;
    }

    // destroy <name>
    m = cmd.match(/^destroy\\s+(\\S+)$/);
    if (m) {
      try { rosh.destroy(m[1]); logOk("  destroyed \\"" + m[1] + "\\""); }
      catch(e) { logErr(String(e)); }
      return;
    }

    // say <text>
    m = cmd.match(/^say\\s+(.+)$/);
    if (m) {
      var sayText = m[1].replace(/^"|"$/g, "");
      rosh.send("say", {text: sayText});
      logOk("  " + sayText);
      return;
    }

    logErr("unknown — type \\"help\\" for commands");
  }

  // ── Open / close ─────────────────────────────────────────
  function getControls() { return rosh._controls ? rosh._controls() : null; }

  function openConsole() {
    consoleOpen = true;
    overlay.style.display = "flex";
    var ctrl = getControls();
    if (ctrl) ctrl.enabled = false;
    inputEl.value = "";
    historyIdx = -1;
    inputEl.focus();
  }

  function closeConsole() {
    consoleOpen = false;
    overlay.style.display = "none";
    var ctrl = getControls();
    if (ctrl) ctrl.enabled = true;
    inputEl.blur();
  }

  // ── Keyboard handling (capture phase) ────────────────────
  document.addEventListener("keydown", function(e) {
    if (e.key === "`" || e.code === "Backquote") {
      e.preventDefault();
      e.stopImmediatePropagation();
      if (consoleOpen) closeConsole(); else openConsole();
      return;
    }
    if (!consoleOpen) return;
    e.stopImmediatePropagation();
    if (e.key === "Enter") {
      execCommand(inputEl.value);
      inputEl.value = "";
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      if (historyIdx < history.length - 1) { historyIdx++; inputEl.value = history[historyIdx]; }
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      if (historyIdx > 0) { historyIdx--; inputEl.value = history[historyIdx]; }
      else { historyIdx = -1; inputEl.value = ""; }
    } else if (e.key === "Escape") {
      closeConsole();
    }
  }, true);

  document.addEventListener("keyup", function(e) {
    if (consoleOpen) e.stopImmediatePropagation();
  }, true);

  // ── Banner ───────────────────────────────────────────────
  log("Rosh console  \\u0060 to close", ACCENT);
  log("set  create  destroy  say  print  look  clear", "#6b7280");
})();
"""
