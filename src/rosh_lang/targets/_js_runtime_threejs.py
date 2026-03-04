"""Three.js renderer layer for 3D Rosh programmes.

Replaces JS_RUNTIME_DOM / JS_RUNTIME_PHASER when targeting Three.js.
Plugs into the same JS_RUNTIME_CORE (state, events, interpolation, audio).

Usage:
    JS_RUNTIME_CORE + JS_RUNTIME_THREEJS  →  Three.js 3D scene in HTML
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

  // ── Geometry factory ─────────────────────────────────────
  function createGeometry(shape) {
    switch ((shape || "cube").toLowerCase()) {
      case "sphere":   return new THREE.SphereGeometry(0.5, 24, 24);
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

  // Grid helper
  var grid = new THREE.GridHelper(20, 20, 0x444444, 0x333333);
  scene.add(grid);

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

      // Update transform
      m.position.set(x, y, z);
      m.scale.set(w, h, d);

      // Rotation
      if (obj.rx != null) m.rotation.x = obj.rx;
      if (obj.ry != null) m.rotation.y = obj.ry;
      if (obj.rz != null) m.rotation.z = obj.rz;

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
    }

    // Remove meshes for destroyed objects
    for (var d in meshes) {
      if (!(d in rosh.objects)) {
        scene.remove(meshes[d]);
        delete meshes[d];
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
