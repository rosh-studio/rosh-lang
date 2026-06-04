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
  state._keys = {};
  state._paused = 0;
  var objects = {};
  var handlers = {};
  var sendDepth = 0;
  var MAX_DEPTH = 10;

  // ── State manager ─────────────────────────────────────
  function get(key) {
    // Special case: _keys.X where X is the literal key name (may contain dots)
    if (key.indexOf("_keys.") === 0) {
      var kn = key.slice(6);
      return state._keys ? state._keys[kn] : undefined;
    }
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
  // Mirrors runtime.py _eval_set_value: nothing → quoted → random → clamp → arithmetic → int → float → raw
  function evalSetValue(target, raw) {
    if (typeof raw !== "string") return raw;

    // nothing: explicit absence
    if (raw.toLowerCase() === "nothing" || raw.toLowerCase() === "none") return null;

    // Quoted string
    if ((raw[0] === '"' && raw[raw.length-1] === '"') ||
        (raw[0] === "'" && raw[raw.length-1] === "'")) {
      return raw.slice(1, -1);
    }

    // Random: "random" or "random min max"
    if (raw === "random") return Math.random();
    if (raw.indexOf("random ") === 0) {
      var rparts = raw.split(" ");
      if (rparts.length === 3) {
        var rlo = parseFloat(rparts[1]), rhi = parseFloat(rparts[2]);
        if (!isNaN(rlo) && !isNaN(rhi)) return rlo + Math.random() * (rhi - rlo);
      }
    }

    // Clamp: "clamp field min max"
    if (raw.indexOf("clamp ") === 0) {
      var cparts = raw.split(" ");
      if (cparts.length === 4) {
        var cval = get(cparts[1]);
        if (typeof cval === "number") {
          var clo = parseFloat(cparts[2]), chi = parseFloat(cparts[3]);
          if (!isNaN(clo) && !isNaN(chi)) return Math.max(clo, Math.min(chi, cval));
        }
      }
    }

    // Expression: atom op atom — mirrors runtime.py _try_arithmetic
    // Multi-char ops tried before single-char to avoid ambiguous splits.
    function resolveAtom(s) {
      if ((s[0] === '"' && s[s.length-1] === '"') ||
          (s[0] === "'" && s[s.length-1] === "'")) return s.slice(1, -1);
      if (s.toLowerCase() === "true") return true;
      if (s.toLowerCase() === "false") return false;
      if (/^-?\\d+$/.test(s)) return parseInt(s, 10);
      if (/^-?\\d+\\.\\d+$/.test(s)) return parseFloat(s);
      return get(s);
    }
    var ops = [">=", "<=", "==", "!=", ">", "<", "+", "-", "*", "/"];
    for (var oi = 0; oi < ops.length; oi++) {
      var op = ops[oi];
      var sep = " " + op + " ";
      var idx = raw.indexOf(sep);
      if (idx === -1) continue;
      var lraw = raw.substring(0, idx);
      var rraw = raw.substring(idx + sep.length);
      var lval = resolveAtom(lraw);
      var rval = resolveAtom(rraw);
      if (op === "+") {
        if (typeof lval === "string" || typeof rval === "string") {
          if (lval == null || rval == null) continue;
          return String(lval) + String(rval);
        }
        if (typeof lval === "number" && typeof rval === "number") return lval + rval;
        continue;
      }
      if (op === "-" || op === "*" || op === "/") {
        if (typeof lval !== "number" || typeof rval !== "number") continue;
        if (op === "-") return lval - rval;
        if (op === "*") return lval * rval;
        if (op === "/" && rval !== 0) return lval / rval;
        continue;
      }
      // Comparison operators
      if (lval == null || rval == null) continue;
      if (op === "==") return lval == rval;
      if (op === "!=") return lval != rval;
      if (op === "<") return lval < rval;
      if (op === ">") return lval > rval;
      if (op === "<=") return lval <= rval;
      if (op === ">=") return lval >= rval;
    }

    // Integer
    if (/^-?\\d+$/.test(raw)) return parseInt(raw, 10);

    // Float
    if (/^-?\\d+\\.\\d+$/.test(raw)) return parseFloat(raw);

    // Boolean
    if (raw.toLowerCase() === "true") return true;
    if (raw.toLowerCase() === "false") return false;

    // Variable reference: resolve dotted name to its current value
    var resolved = get(raw);
    if (resolved != null && typeof resolved !== "object") return resolved;

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

  // ── Animation engine ──────────────────────────────────
  var _animData = {};  // name → {frames:[uri...], speed, mode, _frame, _elapsed, _dir}
  var _spriteDataRef = {};  // set to mod._spriteData after module construction

  function registerAnimation(name, config) {
    _animData[name] = {
      frames: config.frames || [],
      speed: config.speed || 8,
      mode: config.mode || "loop",
      _frame: 0,
      _elapsed: 0,
      _dir: 1  // 1=forward, -1=backward (for bounce)
    };
  }

  var _IMAGE_EXTS = /\\.(png|jpg|jpeg|gif|svg|webp)($|\\?)/i;

  function setBackground(value) {
    // Detect image vs colour: file extensions or URLs
    if (_IMAGE_EXTS.test(value) || value.startsWith("http://") || value.startsWith("https://") || value.startsWith("data:")) {
      state._background = value;
      state._backgroundType = "image";
    } else {
      state._background = value;
      state._backgroundType = "color";
    }
  }

  function tickVelocity(dt) {
    for (var name in objects) {
      var obj = get(name);
      if (!obj || typeof obj !== "object") continue;
      if (typeof obj.vx === "number") set(name + ".x", (obj.x || 0) + obj.vx * dt);
      if (typeof obj.vy === "number") set(name + ".y", (obj.y || 0) + obj.vy * dt);
    }
  }

  function tickPools(dt) {
    // Auto-spawn: pools with _spawn_rate fire periodically
    for (var key in state) {
      if (!state[key] || typeof state[key] !== "object") continue;
      if (typeof state[key]._pool_count !== "number") continue;
      var rate = state[key]._spawn_rate;
      if (typeof rate !== "number" || rate <= 0) continue;
      state[key]._spawn_timer = (state[key]._spawn_timer || 0) + (dt || 0);
      if (state[key]._spawn_timer >= rate) {
        state[key]._spawn_timer = 0;
        state[key]._fire = 1;
        state[key]._x = Math.random();
        state[key]._y = -0.05;
      }
    }
    for (var key in state) {
      if (!state[key] || typeof state[key] !== "object") continue;
      var poolCount = state[key]._pool_count;
      if (typeof poolCount !== "number") continue;
      if (!state[key]._fire) continue;

      var prefix = key;
      var count = poolCount;
      var startIdx = state[prefix]._next || 0;
      var next = -1;
      for (var i = 0; i < count; i++) {
        var idx = (startIdx + i) % count;
        var bobj = get(prefix + ".b" + idx);
        if (bobj && bobj.y <= -1) { next = idx; break; }
      }
      state[prefix]._fire = 0;
      if (next < 0) continue;  // all bullets in flight — skip

      var name = prefix + ".b" + next;
      set(name + ".x", state[prefix]._x || 0);
      set(name + ".y", state[prefix]._y || 0);
      set(name + ".vx", state[prefix]._vx || 0);
      set(name + ".vy", state[prefix]._vy || 0);
      state[prefix]._next = (next + 1) % count;
      // Reset velocity overrides to pool defaults
      state[prefix]._vx = state[prefix]._pool_vx || 0;
      state[prefix]._vy = state[prefix]._pool_vy || 0;
    }
    // Recycle out-of-bounds bullets and update _active counters
    for (var key in state) {
      if (!state[key] || typeof state[key] !== "object") continue;
      var poolCount = state[key]._pool_count;
      if (typeof poolCount !== "number") continue;
      var active = 0;
      for (var i = 0; i < poolCount; i++) {
        var bobj = get(key + ".b" + i);
        if (!bobj) continue;
        // Recycle bullets that left the canvas
        if (bobj.y > -1 && (bobj.y < -0.05 || bobj.y > 1.05 || bobj.x < -0.05 || bobj.x > 1.05)) {
          var bname = key + ".b" + i;
          set(bname + ".x", -1);
          set(bname + ".y", -1);
          set(bname + ".vx", 0);
          set(bname + ".vy", 0);
          continue;
        }
        if (bobj.y > -1) active++;
      }
      state[key]._active = active;
    }
  }

  function tickTimers(dt) {
    for (var key in state) {
      if (!state[key] || typeof state[key] !== "object") continue;
      var total = state[key]._timer_total;
      if (typeof total !== "number") continue;
      if (!state[key]._timer_running) continue;
      var prev = state[key].seconds;
      if (typeof prev !== "number" || prev <= 0) continue;
      var next = prev - dt;
      if (next <= 0) {
        state[key].seconds = 0;
        state[key]._timer_running = 0;
        send("timer_done", {name: key});
      } else {
        state[key].seconds = Math.round(next * 100) / 100;
      }
    }
  }

  function tickAnimations(dt) {
    for (var name in _animData) {
      var anim = _animData[name];
      if (!anim.frames || !anim.frames.length) continue;
      anim._elapsed += dt;
      var interval = 1.0 / anim.speed;
      if (anim._elapsed >= interval) {
        anim._elapsed -= interval;
        var len = anim.frames.length;
        if (anim.mode === "bounce") {
          anim._frame += anim._dir;
          if (anim._frame >= len - 1) { anim._frame = len - 1; anim._dir = -1; }
          if (anim._frame <= 0) { anim._frame = 0; anim._dir = 1; }
        } else if (anim.mode === "once") {
          if (anim._frame < len - 1) anim._frame++;
        } else {
          anim._frame = (anim._frame + 1) % len;
        }
        // Swap active sprite to current frame
        _spriteDataRef[name] = anim.frames[anim._frame];
      }
    }
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

  var mod = {
    state: state,
    objects: objects,
    handlers: handlers,
    scenes: scenes,
    _spriteData: {},
    _audioData: _audioData,
    _animData: _animData,
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
    registerAnimation: registerAnimation,
    setBackground: setBackground,
    tickVelocity: tickVelocity,
    tickPools: tickPools,
    tickTimers: tickTimers,
    tickAnimations: tickAnimations,
    createScene: createScene,
    setSceneProp: setSceneProp,
    goScene: goScene,
    // Stubs — renderer layers (DOM/Phaser/Three.js) override these
    _outputBuffer: [],
    appendOutput: function(text) { mod._outputBuffer.push(text); },
    syncAll: function() {},
    startLoop: function() {}
  };
  // Wire animation engine to the module's sprite data
  _spriteDataRef = mod._spriteData;
  return mod;
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
    // 3D mode: web (CSS/div) target can't render world-unit coordinates.
    if (rosh.state._view === "3d") {
      if (!canvas._3dNotice) {
        // Remove any pre-rendered object divs (from static Python render)
        var existing = canvas.querySelectorAll(".rosh-object");
        for (var i = 0; i < existing.length; i++) existing[i].remove();
        canvas.style.cssText = "background:#0a0a14;display:flex;align-items:center;justify-content:center;width:100%;height:100%;";
        var notice = document.createElement("div");
        notice.style.cssText = "color:#c084fc;font-family:monospace;font-size:18px;text-align:center;padding:40px;";
        notice.textContent = "3D mode — switch target to Three.js";
        canvas.appendChild(notice);
        canvas._3dNotice = true;
      }
      return;
    }
    // Apply background if changed
    var bg = rosh.state._background;
    if (bg && bg !== canvas._appliedBg) {
      if (rosh.state._backgroundType === "image") {
        canvas.style.backgroundImage = "url(" + bg + ")";
        canvas.style.backgroundSize = "cover";
        canvas.style.backgroundPosition = "center";
        canvas.style.backgroundRepeat = "no-repeat";
        canvas.style.backgroundColor = "";
      } else {
        canvas.style.backgroundColor = bg;
        canvas.style.backgroundImage = "";
      }
      canvas._appliedBg = bg;
    }
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

      // Visibility check: visible === 0 or visible === false hides the object
      if (obj.visible === 0 || obj.visible === false) {
        div.style.display = "none";
        continue;
      }

      // Group visibility: if any parent namespace has visible === 0, hide
      var _gParts = name.split(".");
      var _gHidden = false;
      for (var _gi = 1; _gi < _gParts.length; _gi++) {
        var _gParent = rosh.get(_gParts.slice(0, _gi).join("."));
        if (_gParent && (_gParent.visible === 0 || _gParent.visible === false)) {
          _gHidden = true;
          break;
        }
      }
      if (_gHidden) {
        div.style.display = "none";
        continue;
      }

      var x = obj.x;
      var y = obj.y;

      // Hide pool objects parked off-screen (either axis well below 0)
      if ((typeof x === "number" && x < -0.5) || (typeof y === "number" && y < -0.5)) {
        div.style.display = "none";
        continue;
      }
      var w = obj.width != null ? obj.width : 0.1;
      var h = obj.height != null ? obj.height : 0.1;
      var color = obj.color || "#444";
      var rawLabel = obj.label != null ? obj.label : "";
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
      // Rotation (degrees, 0 = up, clockwise positive)
      if (obj.rotation != null) {
        div.style.transform = "rotate(" + obj.rotation + "deg)";
      } else {
        div.style.transform = "";
      }
      // Sprite overlay
      var spriteDesc = obj.sprite;
      var spriteUri = rosh._spriteData && rosh._spriteData[name];
      if (spriteUri) {
        div.style.backgroundColor = "transparent";
        div.style.backgroundImage = "url(" + spriteUri + ")";
        // URL sprites: contain preserves aspect ratio; procedural: fill the box
        var isUrl = spriteUri.indexOf("http") === 0;
        div.style.backgroundSize = isUrl ? "contain" : "100% 100%";
        div.style.backgroundRepeat = "no-repeat";
        div.style.backgroundPosition = "center";
        div.style.imageRendering = isUrl ? "auto" : "pixelated";
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
      div.style.borderRadius = (obj.shape === "circle" || obj.shape === "sphere" || obj.shape === "ball") ? "50%" : "4px";
      div.style.color = obj.text_color || "#fff";
      div.style.fontSize = obj.font_size || "14px";
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
    var max = rosh.state._max_output;
    if (typeof max === "number" && max > 0) {
      var lines = output.textContent.split("\\n");
      if (lines.length > max + 1) {
        output.textContent = lines.slice(lines.length - max - 1).join("\\n");
      }
    }
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
        if (oa.visible === 0 || oa.visible === false) continue;
        if (ob.visible === 0 || ob.visible === false) continue;
        if (oa.x == null || oa.y == null || ob.x == null || ob.y == null) continue;
        if (oa.x < -0.5 || oa.y < -0.5) continue;
        if (ob.x < -0.5 || ob.y < -0.5) continue;
        var aw = oa.width || 0.1, ah = oa.height || 0.1;
        var bw = ob.width || 0.1, bh = ob.height || 0.1;
        if (oa.x < ob.x + bw && oa.x + aw > ob.x &&
            oa.y < ob.y + bh && oa.y + ah > ob.y) {
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
    if (e.key.startsWith("Arrow") || e.key === " ") e.preventDefault();
    rosh.state._keys[e.key] = 1;
    rosh.send("keydown", {key: e.key});
    if (!loopRunning) syncAll();
  });

  document.addEventListener("keyup", function(e) {
    if (e.key.startsWith("Arrow") || e.key === " ") e.preventDefault();
    rosh.state._keys[e.key] = 0;
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
    if (rosh.state._paused) {
      syncAll();
      requestAnimationFrame(tick);
      return;
    }
    rosh.send("update", {dt: dt});
    rosh.tickVelocity(dt);
    rosh.tickPools(dt);
    rosh.tickTimers(dt);
    rosh.tickAnimations(dt);
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

# ── Touch controls (shared across all JS targets) ────────────────
#
# Auto-detected on touch devices via @media (pointer: coarse).
# Renders a translucent d-pad that sets _keys state, so all existing
# controller/keyboard logic works unchanged.

JS_TOUCH_CONTROLS = """\

// ── Touch controls — 8-way joystick + fire buttons ──
(function() {
  // Only inject if a controller widget is present
  if (rosh.get("controller.speed") == null) return;

  var style = document.createElement("style");
  style.textContent = [
    ".rosh-tc { display:none; position:fixed; bottom:0; left:0; right:0; height:160px; z-index:9999; touch-action:none; user-select:none; -webkit-user-select:none; pointer-events:none; }",
    "@media (pointer:coarse) { .rosh-tc { display:block; } }",

    // Joystick base (left side)
    ".rosh-joy { position:absolute; left:24px; bottom:20px; width:120px; height:120px; background:rgba(99,102,241,0.12); border:1px solid rgba(99,102,241,0.25); border-radius:50%; pointer-events:auto; }",
    ".rosh-joy-thumb { position:absolute; left:50%; top:50%; width:48px; height:48px; margin:-24px 0 0 -24px; background:rgba(99,102,241,0.4); border:1px solid rgba(99,102,241,0.6); border-radius:50%; transition:transform 0.05s; }",

    // Fire buttons (right side)
    ".rosh-fire { position:absolute; right:24px; bottom:36px; display:flex; gap:12px; pointer-events:auto; }",
    ".rosh-fire-btn { width:64px; height:64px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:14px; font-weight:700; font-family:system-ui,sans-serif; letter-spacing:0.5px; }",
    ".rosh-fire-a { background:rgba(239,68,68,0.2); border:2px solid rgba(239,68,68,0.5); color:rgba(239,68,68,0.9); }",
    ".rosh-fire-b { background:rgba(59,130,246,0.2); border:2px solid rgba(59,130,246,0.5); color:rgba(59,130,246,0.9); }",
    ".rosh-fire-btn.active { transform:scale(0.9); }",
    ".rosh-fire-a.active { background:rgba(239,68,68,0.4); }",
    ".rosh-fire-b.active { background:rgba(59,130,246,0.4); }",
  ].join("\\n");
  document.head.appendChild(style);

  // Read controller config
  var hasFire = rosh.get("controller._help_fire") != null;
  var fireKey = " ";
  var helpFire = rosh.get("controller._help_fire");
  if (helpFire && typeof helpFire === "string") {
    fireKey = helpFire.replace(/['"]/g, "").trim() || " ";
  }
  // Second fire button: check for controller._fire2_key
  var fire2Key = rosh.get("controller._fire2_key");
  var hasFire2 = fire2Key != null && fire2Key !== "";

  // Container
  var container = document.createElement("div");
  container.className = "rosh-tc";

  // ── Joystick ──
  var joyBase = document.createElement("div");
  joyBase.className = "rosh-joy";
  var joyThumb = document.createElement("div");
  joyThumb.className = "rosh-joy-thumb";
  joyBase.appendChild(joyThumb);
  container.appendChild(joyBase);

  var joyDir = {left: false, right: false, up: false, down: false};
  var joyTouchId = null;
  var joyRect = null;
  var DEADZONE = 15;  // pixels from center before registering direction

  function updateJoystick(touchX, touchY) {
    if (!joyRect) joyRect = joyBase.getBoundingClientRect();
    var cx = joyRect.left + joyRect.width / 2;
    var cy = joyRect.top + joyRect.height / 2;
    var dx = touchX - cx;
    var dy = touchY - cy;
    var dist = Math.sqrt(dx * dx + dy * dy);
    var maxDist = joyRect.width / 2 - 10;

    // Clamp thumb to circle
    if (dist > maxDist) {
      dx = dx / dist * maxDist;
      dy = dy / dist * maxDist;
    }
    joyThumb.style.transform = "translate(" + dx + "px," + dy + "px)";

    // 8-way direction from angle (22.5° zones)
    var prev = {left: joyDir.left, right: joyDir.right, up: joyDir.up, down: joyDir.down};
    if (dist < DEADZONE) {
      joyDir.left = joyDir.right = joyDir.up = joyDir.down = false;
    } else {
      var angle = Math.atan2(dy, dx) * 180 / Math.PI;
      joyDir.right = angle > -67.5 && angle < 67.5;
      joyDir.left  = angle > 112.5 || angle < -112.5;
      joyDir.down  = angle > 22.5 && angle < 157.5;
      joyDir.up    = angle > -157.5 && angle < -22.5;
    }

    // Emit key events for state changes
    syncKey("ArrowLeft", prev.left, joyDir.left);
    syncKey("ArrowRight", prev.right, joyDir.right);
    syncKey("ArrowUp", prev.up, joyDir.up);
    syncKey("ArrowDown", prev.down, joyDir.down);
  }

  function resetJoystick() {
    joyThumb.style.transform = "translate(0,0)";
    var prev = {left: joyDir.left, right: joyDir.right, up: joyDir.up, down: joyDir.down};
    joyDir.left = joyDir.right = joyDir.up = joyDir.down = false;
    syncKey("ArrowLeft", prev.left, false);
    syncKey("ArrowRight", prev.right, false);
    syncKey("ArrowUp", prev.up, false);
    syncKey("ArrowDown", prev.down, false);
    joyTouchId = null;
  }

  function syncKey(key, was, is) {
    if (was === is) return;
    rosh.state._keys[key] = is ? 1 : 0;
    rosh.send(is ? "keydown" : "keyup", {key: key});
  }

  joyBase.addEventListener("touchstart", function(e) {
    e.preventDefault();
    if (joyTouchId !== null) return;  // already tracking
    var t = e.changedTouches[0];
    joyTouchId = t.identifier;
    joyRect = joyBase.getBoundingClientRect();
    updateJoystick(t.clientX, t.clientY);
  }, {passive: false});

  document.addEventListener("touchmove", function(e) {
    if (joyTouchId === null) return;
    for (var i = 0; i < e.changedTouches.length; i++) {
      if (e.changedTouches[i].identifier === joyTouchId) {
        e.preventDefault();
        updateJoystick(e.changedTouches[i].clientX, e.changedTouches[i].clientY);
        return;
      }
    }
  }, {passive: false});

  document.addEventListener("touchend", function(e) {
    if (joyTouchId === null) return;
    for (var i = 0; i < e.changedTouches.length; i++) {
      if (e.changedTouches[i].identifier === joyTouchId) {
        resetJoystick();
        return;
      }
    }
  });
  document.addEventListener("touchcancel", function(e) {
    if (joyTouchId === null) return;
    for (var i = 0; i < e.changedTouches.length; i++) {
      if (e.changedTouches[i].identifier === joyTouchId) {
        resetJoystick();
        return;
      }
    }
  });

  // ── Vertical buttons (3D up/down — uses fire button slots) ──
  var vertUp = rosh.get("controller._vertical_up_key");
  var vertDown = rosh.get("controller._vertical_down_key");
  var hasVertical = rosh.get("controller._vertical") === "on" && vertUp && vertDown;

  // ── Fire buttons (or vertical buttons) ──
  if (hasFire || hasFire2 || hasVertical) {
    var fireDiv = document.createElement("div");
    fireDiv.className = "rosh-fire";

    function makeFireBtn(key, label, cssClass) {
      var btn = document.createElement("div");
      btn.className = "rosh-fire-btn " + cssClass;
      btn.textContent = label;
      btn.addEventListener("touchstart", function(e) {
        e.preventDefault();
        btn.classList.add("active");
        rosh.state._keys[key] = 1;
        rosh.send("keydown", {key: key});
      }, {passive: false});
      btn.addEventListener("touchend", function(e) {
        e.preventDefault();
        btn.classList.remove("active");
        rosh.state._keys[key] = 0;
        rosh.send("keyup", {key: key});
      }, {passive: false});
      btn.addEventListener("touchcancel", function(e) {
        btn.classList.remove("active");
        rosh.state._keys[key] = 0;
        rosh.send("keyup", {key: key});
      });
      return btn;
    }

    if (hasVertical) {
      fireDiv.appendChild(makeFireBtn(vertUp, "\\u25B2", "rosh-fire-a"));
      fireDiv.appendChild(makeFireBtn(vertDown, "\\u25BC", "rosh-fire-b"));
    }
    if (hasFire) {
      fireDiv.appendChild(makeFireBtn(fireKey, "A", "rosh-fire-a"));
    }
    if (hasFire2) {
      fireDiv.appendChild(makeFireBtn(fire2Key, "B", "rosh-fire-b"));
    }
    container.appendChild(fireDiv);
  }

  document.body.appendChild(container);
})();
"""

# ── Combined runtime ──────────────────────────────────────────────

JS_RUNTIME = JS_RUNTIME_CORE + JS_RUNTIME_DOM
