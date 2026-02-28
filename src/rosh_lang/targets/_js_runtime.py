"""JavaScript runtime strings for interactive Rosh programmes.

Two layers, per BUILDING-ROSH.md reusability mandate:

- JS_RUNTIME_CORE: target-agnostic (state, expressions, interpolation, events)
- JS_RUNTIME_DOM:  web-specific (DOM sync, hit-test, CSS, event listeners, game loop)
- JS_RUNTIME:      combined (core + DOM) — used by web target

Future targets (e.g. Phaser) import JS_RUNTIME_CORE + provide their own renderer.
"""

# ── Target-agnostic core ──────────────────────────────────────────
#
# Mirrors runtime.py: state manager, expression evaluator,
# interpolation, event dispatcher with depth guard.

JS_RUNTIME_CORE = """\
var rosh = (function() {
  var state = {};
  var objects = {};
  var handlers = {};
  var sendDepth = 0;
  var MAX_DEPTH = 10;

  // ── State manager ─────────────────────────────────────
  function get(key) {
    var parts = key.split(".");
    var obj = state;
    for (var i = 0; i < parts.length; i++) {
      if (obj == null || typeof obj !== "object") return undefined;
      obj = obj[parts[i]];
    }
    return obj;
  }

  function set(key, val) {
    var parts = key.split(".");
    // Route scene property sets to scene data
    if (parts.length >= 2 && scenes[parts[0]]) {
      var prop = parts.slice(1).join(".");
      if (prop === "exits" && typeof val === "string") {
        scenes[parts[0]].exits = val.split(/\\s+/);
      } else {
        scenes[parts[0]][prop] = val;
      }
      return;
    }
    if (parts.length === 1) {
      state[key] = val;
      return;
    }
    var obj = state;
    for (var i = 0; i < parts.length - 1; i++) {
      if (obj[parts[i]] == null || typeof obj[parts[i]] !== "object") {
        obj[parts[i]] = {};
      }
      obj = obj[parts[i]];
    }
    obj[parts[parts.length - 1]] = val;
  }

  function create(kind, name) {
    // Use set() to navigate dots — "player.ship" → state.player.ship
    if (kind === "object") {
      set(name, get(name) || {});
      objects[name] = true;
    } else if (kind === "number") {
      set(name, 0);
    } else if (kind === "string") {
      set(name, "");
    } else if (kind === "list") {
      set(name, []);
    } else {
      set(name, get(name) || {});
      objects[name] = true;
    }
  }

  function destroy(name) {
    var existed = get(name) != null;
    // Navigate dots to delete: "player.ship" → delete state.player.ship
    var parts = name.split(".");
    if (parts.length === 1) {
      delete state[name];
    } else {
      var obj = state;
      for (var i = 0; i < parts.length - 1; i++) {
        if (obj == null || typeof obj !== "object") break;
        obj = obj[parts[i]];
      }
      if (obj) delete obj[parts[parts.length - 1]];
    }
    delete objects[name];
    if (existed) send("destroy", {name: name});
  }

  // ── Expression evaluator ──────────────────────────────
  // Mirrors runtime.py _eval_set_value: quoted → arithmetic → int → float → raw
  function evalSetValue(target, raw) {
    if (typeof raw !== "string") return raw;

    // Quoted string
    if ((raw[0] === '"' && raw[raw.length-1] === '"') ||
        (raw[0] === "'" && raw[raw.length-1] === "'")) {
      return raw.slice(1, -1);
    }

    // Arithmetic: left op right (variables or literals)
    var ops = ["+", "-", "*", "/"];
    for (var oi = 0; oi < ops.length; oi++) {
      var op = ops[oi];
      var sep = " " + op + " ";
      var idx = raw.indexOf(sep);
      if (idx !== -1) {
        var left = raw.substring(0, idx);
        var right = raw.substring(idx + sep.length);
        var rval = parseFloat(right);
        if (isNaN(rval)) {
          var resolved = get(right);
          if (typeof resolved === "number") rval = resolved;
          else continue;
        }
        var cur = get(left);
        if (typeof cur === "number") {
          if (op === "+") return cur + rval;
          if (op === "-") return cur - rval;
          if (op === "*") return cur * rval;
          if (op === "/" && rval !== 0) return cur / rval;
        }
      }
    }

    // Integer
    if (/^-?\\d+$/.test(raw)) return parseInt(raw, 10);

    // Float
    if (/^-?\\d+\\.\\d+$/.test(raw)) return parseFloat(raw);

    // Boolean
    if (raw.toLowerCase() === "true") return true;
    if (raw.toLowerCase() === "false") return false;

    return raw;
  }

  // ── Interpolation ─────────────────────────────────────
  function interpolate(template) {
    return template.replace(/\\{([^}]+)\\}/g, function(match, key) {
      var val = get(key);
      return (val != null) ? String(val) : match;
    });
  }

  // ── Event dispatcher ──────────────────────────────────
  function on(event, args, fn) {
    if (!handlers[event]) handlers[event] = [];
    handlers[event].push({args: args, fn: fn});
  }

  function send(event, payload) {
    if (sendDepth >= MAX_DEPTH) return;
    sendDepth++;
    try {
      // Inject payload into state
      var originals = {};
      var missing = [];
      if (payload) {
        for (var k in payload) {
          if (k in state) originals[k] = state[k];
          else missing.push(k);
          state[k] = payload[k];
        }
      }
      try {
        var list = handlers[event] || [];
        for (var i = 0; i < list.length; i++) {
          list[i].fn(payload || {});
        }
      } finally {
        // Restore originals
        if (payload) {
          for (var k in payload) {
            if (k in originals) state[k] = originals[k];
            else delete state[k];
          }
        }
      }
    } finally {
      sendDepth--;
    }
  }

  // ── Audio engine ──────────────────────────────────────
  var _audioData = {};
  var _audioCtx = null;
  var _activeLoops = {};
  var _noiseBuffer = null;

  function _ensureAudioCtx() {
    if (!_audioCtx) {
      _audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (_audioCtx.state === "suspended") {
      _audioCtx.resume();
    }
    return _audioCtx;
  }

  function _getNoiseBuffer(ctx) {
    if (_noiseBuffer) return _noiseBuffer;
    var sr = ctx.sampleRate;
    var len = sr;  // 1 second of noise
    _noiseBuffer = ctx.createBuffer(1, len, sr);
    var data = _noiseBuffer.getChannelData(0);
    for (var i = 0; i < len; i++) {
      data[i] = Math.random() * 2 - 1;
    }
    return _noiseBuffer;
  }

  function _playLayer(ctx, layer) {
    var dur = layer.duration || 0.2;
    var vol = layer.volume || 0.3;
    var attack = layer.attack || 0.005;
    var decay = layer.decay || dur;
    var freq = layer.frequency || 440;
    var sweep = layer.sweep || 0;
    var sweepTime = layer.sweep_time || dur;
    var now = ctx.currentTime;

    // Gain envelope
    var gain = ctx.createGain();
    gain.gain.setValueAtTime(0.0001, now);
    gain.gain.linearRampToValueAtTime(vol, now + attack);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + attack + decay);
    gain.connect(ctx.destination);

    var source;
    if (layer.waveform === "noise") {
      source = ctx.createBufferSource();
      source.buffer = _getNoiseBuffer(ctx);
      source.loop = false;
    } else {
      source = ctx.createOscillator();
      source.type = layer.waveform || "sine";
      source.frequency.setValueAtTime(freq, now);
      if (sweep !== 0) {
        source.frequency.linearRampToValueAtTime(
          Math.max(20, freq + sweep), now + sweepTime
        );
      }
    }

    source.connect(gain);
    source.start(now);
    source.stop(now + dur + 0.05);
    return source;
  }

  function playAudio(name, mode) {
    var params = _audioData[name];
    if (!params) return;
    if (mode === "stop") {
      var active = _activeLoops[name];
      if (active) {
        for (var si = 0; si < active.length; si++) {
          try { active[si].stop(); } catch(e) {}
        }
        delete _activeLoops[name];
      }
      return;
    }
    var ctx = _ensureAudioCtx();
    var layers = params.layers || [params];
    var sources = [];
    for (var li = 0; li < layers.length; li++) {
      sources.push(_playLayer(ctx, layers[li]));
    }
    if (mode === "loop") {
      _activeLoops[name] = sources;
    }
  }

  function registerSound(name, params) {
    _audioData[name] = params;
  }

  // ── Scenes ─────────────────────────────────────────────
  var scenes = {};

  function createScene(name) {
    scenes[name] = {};
  }

  function setSceneProp(name, prop, val) {
    if (!scenes[name]) scenes[name] = {};
    if (prop === "exits" && typeof val === "string") {
      scenes[name].exits = val.split(/\\s+/);
    } else {
      scenes[name][prop] = val;
    }
  }

  function goScene(target) {
    if (target === "back") {
      target = get("_prev_scene");
      if (!target) return;
    }
    if (!scenes[target]) return;
    var current = get("_scene") || "";
    if (current) send("scene_exit", {scene: current});
    set("_prev_scene", current);
    set("_scene", target);
    // Apply scene overrides
    var sd = scenes[target];
    for (var k in sd) {
      if (k !== "exits") state[k] = sd[k];
    }
    send("scene_enter", {scene: target});
  }

  return {
    state: state,
    objects: objects,
    scenes: scenes,
    _spriteData: {},
    _audioData: _audioData,
    get: get,
    set: set,
    create: create,
    destroy: destroy,
    evalSetValue: evalSetValue,
    interpolate: interpolate,
    on: on,
    send: send,
    playAudio: playAudio,
    registerSound: registerSound,
    createScene: createScene,
    setSceneProp: setSceneProp,
    goScene: goScene
  };
})();
"""

# ── Web-specific DOM layer ────────────────────────────────────────
#
# Syncs rosh.state → DOM divs, handles click/keydown,
# runs game loop + AABB collision detection.

JS_RUNTIME_DOM = """\

(function() {
  var canvas = document.getElementById("canvas");
  var output = document.getElementById("output");
  var divs = {};
  var prevCollisions = {};

  // Adopt pre-rendered static divs so syncAll reuses them (no ghost imprints)
  var existing = canvas.querySelectorAll(".rosh-object[data-name]");
  for (var ei = 0; ei < existing.length; ei++) {
    divs[existing[ei].dataset.name] = existing[ei];
  }

  // ── CSS conversion ────────────────────────────────────
  function cssValue(v) {
    if (typeof v === "number") {
      if (v >= 0 && v <= 1) return (v * 100) + "%";
      return v + "px";
    }
    return "0%";
  }

  // ── DOM sync ──────────────────────────────────────────
  function syncAll() {
    // Create/update divs for all objects
    for (var name in rosh.objects) {
      var obj = rosh.get(name);
      if (!obj || typeof obj !== "object") {
        // Object was destroyed
        if (divs[name]) {
          divs[name].remove();
          delete divs[name];
        }
        delete rosh.objects[name];
        continue;
      }

      var div = divs[name];
      if (!div) {
        div = document.createElement("div");
        div.className = "rosh-object";
        div.dataset.name = name;
        canvas.appendChild(div);
        divs[name] = div;
      }

      var x = obj.x;
      var y = obj.y;
      var w = obj.width != null ? obj.width : 0.1;
      var h = obj.height != null ? obj.height : 0.1;
      var color = obj.color || "#444";
      var rawLabel = obj.label != null ? obj.label : name;
      var label = (typeof rawLabel === "string") ? rosh.interpolate(rawLabel) : rawLabel;
      var hasPos = x != null || y != null;

      div.style.position = hasPos ? "absolute" : "relative";
      if (hasPos) {
        div.style.left = cssValue(x != null ? x : 0);
        div.style.top = cssValue(y != null ? y : 0);
      } else {
        div.style.margin = "8px auto";
      }
      div.style.width = cssValue(w);
      div.style.height = cssValue(h);
      // Sprite overlay
      var spriteDesc = obj.sprite;
      var spriteUri = rosh._spriteData && rosh._spriteData[name];
      if (spriteUri) {
        div.style.backgroundColor = "transparent";
        div.style.backgroundImage = "url(" + spriteUri + ")";
        div.style.backgroundSize = "100% 100%";
        div.style.backgroundRepeat = "no-repeat";
        div.style.backgroundPosition = "center";
        div.style.imageRendering = "pixelated";
        div.textContent = "";
      } else {
        div.style.backgroundColor = color;
        div.style.backgroundImage = "";
        div.textContent = spriteDesc ? "" : label;
      }
      div.style.display = "flex";
      div.style.alignItems = "center";
      div.style.justifyContent = "center";
      div.style.boxSizing = "border-box";
      div.style.borderRadius = "4px";
      div.style.color = "#fff";
      div.style.fontSize = "14px";
      div.style.fontFamily = "system-ui, sans-serif";
    }

    // Remove divs for destroyed objects
    for (var dname in divs) {
      if (!(dname in rosh.objects)) {
        divs[dname].remove();
        delete divs[dname];
      }
    }
  }

  // ── Output ────────────────────────────────────────────
  function appendOutput(text) {
    output.textContent += text + "\\n";
    output.style.display = "block";
  }

  // ── Hit testing ───────────────────────────────────────
  function hitTest(clientX, clientY, name) {
    var div = divs[name];
    if (!div) return false;
    var r = div.getBoundingClientRect();
    return clientX >= r.left && clientX <= r.right &&
           clientY >= r.top && clientY <= r.bottom;
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
        var aw = oa.width || 0.1, ah = oa.height || 0.1;
        var bw = ob.width || 0.1, bh = ob.height || 0.1;
        if (oa.x < ob.x + bw && oa.x + aw > ob.x &&
            oa.y < ob.y + bh && oa.y + ah > ob.y) {
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

  // ── Event listeners ───────────────────────────────────
  canvas.addEventListener("click", function(e) {
    var rect = canvas.getBoundingClientRect();
    var nx = (e.clientX - rect.left) / rect.width;
    var ny = (e.clientY - rect.top) / rect.height;

    // Check named object clicks first
    for (var name in rosh.objects) {
      if (hitTest(e.clientX, e.clientY, name)) {
        rosh.send("click_" + name, {x: nx, y: ny});
      }
    }
    // Global click
    rosh.send("click", {x: nx, y: ny});
    if (!loopRunning) syncAll();
  });

  document.addEventListener("keydown", function(e) {
    rosh.send("keydown", {key: e.key});
    if (!loopRunning) syncAll();
  });

  document.addEventListener("keyup", function(e) {
    rosh.send("keyup", {key: e.key});
    if (!loopRunning) syncAll();
  });

  // ── Game loop ─────────────────────────────────────────
  var loopRunning = false;
  var lastTime = 0;

  function startLoop() {
    if (loopRunning) return;
    loopRunning = true;
    lastTime = performance.now();
    requestAnimationFrame(tick);
  }

  function tick(now) {
    if (!loopRunning) return;
    var dt = (now - lastTime) / 1000;
    if (dt > 0.1) dt = 0.1;  // cap delta
    lastTime = now;
    rosh.send("update", {dt: dt});
    checkCollisions();
    syncAll();
    requestAnimationFrame(tick);
  }

  // Expose DOM helpers on rosh
  rosh.syncAll = syncAll;
  rosh.appendOutput = appendOutput;
  rosh.startLoop = startLoop;
})();
"""

# ── Combined runtime ──────────────────────────────────────────────

JS_RUNTIME = JS_RUNTIME_CORE + JS_RUNTIME_DOM
