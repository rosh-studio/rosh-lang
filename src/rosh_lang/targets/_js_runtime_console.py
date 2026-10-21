"""Live Rosh console overlay for Three.js output.

Always injected alongside JS_RUNTIME_THREEJS. Backtick (`) to toggle.
Mirrors the terminal REPL's safe shell sugar where practical:
aliases, help, object inspection, recovery hints, and curated
natural-language lowering that stays inside strict Rosh semantics.
"""

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
  var currentSubject = null;

  var EXACT_ALIASES = {
    "?": "help",
    "ls": "list objects",
    "objects": "list objects"
  };

  var PREFIX_ALIASES = [
    ["examine ", "look "],
    ["inspect ", "look "],
    ["x ", "look "],
    ["delete ", "destroy "],
    ["remove ", "destroy "]
  ];

  var HELP_TOPICS = {
    "help": {
      usage: "help [command]",
      summary: "Show available commands or detailed help",
      examples: ["help", "help set", "help look"],
      aliases: ["?"],
      acceptsNoArgs: true
    },
    "state": {
      usage: "state",
      summary: "Show current top-level state",
      examples: ["state"],
      aliases: [],
      acceptsNoArgs: true
    },
    "list": {
      usage: "list | list objects | list events",
      summary: "Show state, objects, or events",
      examples: ["list", "list objects", "list events"],
      aliases: ["ls", "objects"],
      acceptsNoArgs: true
    },
    "look": {
      usage: "look [target]",
      summary: "Inspect the scene, an object, or a property",
      examples: ["look", "look ball", "look ball.color"],
      aliases: ["examine", "inspect", "x"],
      acceptsNoArgs: true
    },
    "get": {
      usage: "get <target>",
      summary: "Read a state value or object field",
      examples: ["get ball", "get ball.color"],
      aliases: [],
      acceptsNoArgs: false
    },
    "set": {
      usage: "set <target> to <value>",
      summary: "Set a value or object property",
      examples: ["set ball.color to red", "set score to score + 1"],
      aliases: [],
      acceptsNoArgs: false
    },
    "create": {
      usage: "create <name> | create object <name> | create <name> as <shape>",
      summary: "Create a new object and optionally give it a shape",
      examples: ["create object ball", "create ball as sphere"],
      aliases: [],
      acceptsNoArgs: false
    },
    "destroy": {
      usage: "destroy <name>",
      summary: "Remove an object from state",
      examples: ["destroy ball"],
      aliases: ["delete", "remove"],
      acceptsNoArgs: false
    },
    "print": {
      usage: 'print "text"',
      summary: "Write text into the console",
      examples: ['print "hello"'],
      aliases: [],
      acceptsNoArgs: false
    },
    "say": {
      usage: 'say "text"',
      summary: "Broadcast text into the running world",
      examples: ['say "hello"'],
      aliases: [],
      acceptsNoArgs: false
    },
    "clear": {
      usage: "clear",
      summary: "Clear the console output",
      examples: ["clear"],
      aliases: [],
      acceptsNoArgs: true
    }
  };

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
  inputEl.placeholder = "just try this — create a big red ball";
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

  var SHAPES = ["cube","sphere","cylinder","cone","torus","plane"];
  var COLORS = ["red","green","blue","yellow","cyan","magenta","white","black","orange","purple","pink","gray"];
  var DEFAULT_COLORS = ["cyan","orange","magenta","yellow","green","pink","purple"];
  var CREATE_VERBS = {"create": true, "make": true, "add": true, "draw": true, "spawn": true};
  var STRICT_CREATE_KINDS = {"object": true, "objects": true, "number": true, "string": true, "list": true, "scene": true};
  var ARTICLES = {"a": true, "an": true, "the": true};
  var SIZE_WORDS = {"tiny": 0.04, "small": 0.07, "big": 0.16, "large": 0.16, "huge": 0.24};
  var RELATIVE_SIZE_WORDS = {"smaller": 0.75, "bigger": 1.25};
  var DIRECTION_DELTAS = {
    "left": ["x", -0.1],
    "right": ["x", 0.1],
    "up": ["y", -0.1],
    "down": ["y", 0.1]
  };
  var GEOMETRIC_SHAPES = {
    "ball": "circle",
    "circle": "circle",
    "sphere": "sphere",
    "round": "circle",
    "orb": "circle",
    "square": "rectangle",
    "rectangle": "rectangle",
    "box": "rectangle",
    "cube": "cube",
    "block": "rectangle"
  };
  var _createCount = 0;

  function canonicalHelpTopic(topic) {
    if (!topic) return null;
    var lowered = topic.trim().toLowerCase();
    if (!lowered) return null;
    if (HELP_TOPICS[lowered]) return lowered;
    for (var name in HELP_TOPICS) {
      var aliases = HELP_TOPICS[name].aliases || [];
      for (var i = 0; i < aliases.length; i++) {
        if (aliases[i] === lowered) return name;
      }
    }
    return lowered;
  }

  function showHelp(topic) {
    if (!topic) {
      log("  Commands:", "#a78bfa");
      var order = ["help", "list", "look", "get", "set", "create", "destroy", "print", "say", "clear"];
      for (var oi = 0; oi < order.length; oi++) {
        var entry = HELP_TOPICS[order[oi]];
        log("  " + entry.usage + " — " + entry.summary, "#d1d5db");
      }
      log("  Shapes: " + SHAPES.join(", "), "#6b7280");
      log("  Colors: " + COLORS.join(", "), "#6b7280");
      log("  Try: create a big red ball", "#6b7280");
      log("  ArrowUp/Down: history   Escape: close", "#6b7280");
      return;
    }

    var canonical = canonicalHelpTopic(topic);
    var entry = canonical ? HELP_TOPICS[canonical] : null;
    if (!entry) {
      logErr('no help for "' + topic + '"');
      return;
    }

    log("  " + entry.usage, "#a78bfa");
    log("  " + entry.summary, "#d1d5db");
    if (entry.aliases && entry.aliases.length) {
      log("  aliases: " + entry.aliases.join(", "), "#6b7280");
    }
    if (entry.examples && entry.examples.length) {
      log("  examples:", "#6b7280");
      for (var ei = 0; ei < entry.examples.length; ei++) {
        log("    " + entry.examples[ei], "#d1d5db");
      }
    }
  }

  function logGuidance(lines) {
    if (!lines || !lines.length) return;
    log("  Try:", "#fbbf24");
    for (var i = 0; i < lines.length; i++) {
      log("    " + lines[i], "#fbbf24");
    }
  }

  function usageGuidanceForCommand(command) {
    var canonical = canonicalHelpTopic(command);
    var entry = canonical ? HELP_TOPICS[canonical] : null;
    if (!entry || entry.acceptsNoArgs) return null;
    return [entry.usage].concat(entry.examples || []);
  }

  function editDistance(a, b) {
    var dp = [];
    for (var i = 0; i <= a.length; i++) {
      dp[i] = [i];
    }
    for (var j = 1; j <= b.length; j++) {
      dp[0][j] = j;
    }
    for (var ai = 1; ai <= a.length; ai++) {
      for (var bj = 1; bj <= b.length; bj++) {
        var cost = a.charAt(ai - 1) === b.charAt(bj - 1) ? 0 : 1;
        dp[ai][bj] = Math.min(
          dp[ai - 1][bj] + 1,
          dp[ai][bj - 1] + 1,
          dp[ai - 1][bj - 1] + cost
        );
      }
    }
    return dp[a.length][b.length];
  }

  function closestMatch(value, candidates) {
    if (!value || !candidates || !candidates.length) return null;
    var lowered = value.toLowerCase();
    var best = null;
    var bestDistance = Infinity;
    for (var i = 0; i < candidates.length; i++) {
      var candidate = candidates[i];
      if (!candidate) continue;
      var loweredCandidate = candidate.toLowerCase();
      if (loweredCandidate === lowered) return candidate;
      var distance = editDistance(lowered, loweredCandidate);
      if (distance < bestDistance) {
        bestDistance = distance;
        best = candidate;
      }
    }
    return bestDistance <= 2 ? best : null;
  }

  function commandCandidates() {
    var names = Object.keys(HELP_TOPICS);
    for (var i = 0; i < PREFIX_ALIASES.length; i++) {
      names.push(PREFIX_ALIASES[i][0].trim());
    }
    names.push("?", "ls", "objects");
    return names;
  }

  function formatValue(name, value) {
    if (value === undefined) {
      return name + " = undefined";
    }
    if (value === null) {
      return name + " = null";
    }
    if (Array.isArray(value)) {
      return name + " = " + JSON.stringify(value) + " (list)";
    }
    if (typeof value === "object") {
      return name + " = " + JSON.stringify(value) + " (object)";
    }
    return name + " = " + JSON.stringify(value) + " (" + typeof value + ")";
  }

  function stateKeys() {
    var keys = Object.keys(rosh.state).filter(function(key) {
      return key !== "_keys" && key.charAt(0) !== "_";
    });
    keys.sort();
    return keys;
  }

  function listState() {
    var keys = stateKeys();
    if (!keys.length) {
      log("  (state is empty)", "#9ca3af");
      return;
    }
    for (var i = 0; i < keys.length; i++) {
      log("  " + formatValue(keys[i], rosh.get(keys[i])), OUTPUT_C);
    }
  }

  function listObjects() {
    var names = Object.keys(rosh.objects).sort();
    if (!names.length) {
      log("  (no objects yet — try: create a big red ball)", "#9ca3af");
      return;
    }
    for (var i = 0; i < names.length; i++) {
      var name = names[i];
      var obj = rosh.get(name);
      log("  " + formatValue(name, obj), OUTPUT_C);
    }
  }

  function listEvents() {
    var names = Object.keys(rosh.handlers || {}).sort();
    if (!names.length) {
      log("  (no events registered yet)", "#9ca3af");
      return;
    }
    for (var i = 0; i < names.length; i++) {
      log("  " + names[i], OUTPUT_C);
    }
  }

  function inspectTarget(target) {
    var value = rosh.get(target);
    if (value !== undefined) {
      log("  " + formatValue(target, value), OUTPUT_C);
      return true;
    }

    if (target.indexOf(".") !== -1) {
      var dotIdx = target.indexOf(".");
      var objectName = target.slice(0, dotIdx);
      var propertyName = target.slice(dotIdx + 1);
      var obj = rosh.get(objectName);
      if (obj && typeof obj === "object") {
        var propertyNames = Object.keys(obj);
        var suggestion = closestMatch(propertyName, propertyNames);
        logErr('"' + target + '" does not exist.');
        if (suggestion) {
          log("  Did you mean: " + objectName + "." + suggestion + "?", "#fbbf24");
        }
        return true;
      }
    }

    var objectSuggestion = closestMatch(target, Object.keys(rosh.objects));
    if (objectSuggestion) {
      logErr('"' + target + '" does not exist.');
      log("  Did you mean: " + objectSuggestion + "?", "#fbbf24");
      return true;
    }

    return false;
  }

  function applyAliases(cmd) {
    var lowered = cmd.toLowerCase();
    if (EXACT_ALIASES[lowered]) {
      return EXACT_ALIASES[lowered];
    }
    for (var i = 0; i < PREFIX_ALIASES.length; i++) {
      var prefix = PREFIX_ALIASES[i][0];
      if (lowered.indexOf(prefix) === 0) {
        return PREFIX_ALIASES[i][1] + cmd.slice(prefix.length).trim();
      }
    }
    return cmd;
  }

  // Normalise: "set box x to 1" → "set box.x to 1"
  //            "set box.x 1"    → "set box.x to 1"
  function normalise(cmd) {
    cmd = applyAliases(cmd);
    var spaceSet = cmd.match(/^set\\s+(\\S+)\\s+([a-zA-Z_][\\w]*)\\s+(?:to\\s+)?([^.].*)$/);
    if (spaceSet && spaceSet[1].indexOf(".") === -1) {
      cmd = "set " + spaceSet[1] + "." + spaceSet[2] + " to " + spaceSet[3].trim();
    }
    var missingTo = cmd.match(/^set\\s+(\\S+\\.\\S+)\\s+(?!to\\s)(.+)$/);
    if (missingTo) {
      cmd = "set " + missingTo[1] + " to " + missingTo[2].trim();
    }
    return cmd;
  }

  function resolveTargetTokens(tokens) {
    if (!tokens.length) return {target: null, consumed: 0};
    var first = tokens[0].toLowerCase();
    if (first === "it" || first === "them") {
      return {target: currentSubject, consumed: 1};
    }
    if (ARTICLES[first]) {
      if (tokens.length < 2) return {target: null, consumed: 0};
      return {target: tokens[1].toLowerCase(), consumed: 2};
    }
    return {target: first, consumed: 1};
  }

  function normaliseCoordinate(raw) {
    var value = parseFloat(raw);
    if (isNaN(value)) return null;
    if (value > 1 || value < 0) {
      value = value / 100;
    }
    return Math.max(0, Math.min(1, value));
  }

  function inferSubject(cmd) {
    var createMatch = cmd.match(/^create\\s+(?:(?:object|number|string|list)\\s+)?(\\S+)/i);
    if (createMatch) return createMatch[1].split(".", 1)[0];
    var targetMatch = cmd.match(/^(?:look|get|destroy)\\s+(\\S+)/i);
    if (targetMatch) return targetMatch[1].split(".", 1)[0];
    var setMatch = cmd.match(/^set\\s+(\\S+)/i);
    if (setMatch) return setMatch[1].split(".", 1)[0];
    return null;
  }

  function lowerCreatePhrase(cmd) {
    var tokens = cmd.trim().split(/\\s+/);
    if (tokens.length < 2) return null;
    var verb = tokens[0].toLowerCase();
    if (!CREATE_VERBS[verb]) return null;

    var remainder = tokens.slice(1).map(function(token) { return token.toLowerCase(); });
    if (STRICT_CREATE_KINDS[remainder[0]]) return null;
    if (ARTICLES[remainder[0]]) {
      remainder = remainder.slice(1);
      if (!remainder.length) return null;
    }

    var noun = remainder[remainder.length - 1];
    var modifiers = remainder.slice(0, -1);
    var color = null;
    var size = null;
    for (var i = 0; i < modifiers.length; i++) {
      if (SIZE_WORDS[modifiers[i]] != null && size == null) {
        size = SIZE_WORDS[modifiers[i]];
        continue;
      }
      if (COLORS.indexOf(modifiers[i]) !== -1 && color == null) {
        color = modifiers[i] === "grey" ? "gray" : modifiers[i];
        continue;
      }
      return null;
    }

    var shape = GEOMETRIC_SHAPES[noun];
    var lines = ["create object " + noun];
    if (shape) {
      lines.push("set " + noun + ".shape to " + shape);
    }
    if (color) {
      lines.push("set " + noun + ".color to " + color);
    }
    if (size != null) {
      lines.push("set " + noun + ".width to " + size);
      lines.push("set " + noun + ".height to " + size);
      lines.push("set " + noun + ".depth to " + size);
    }
    if (shape) {
      lines.push("set " + noun + ".x to 0.5");
      lines.push("set " + noun + ".y to 0.5");
    }

    return {text: lines.join("\\n"), subject: noun};
  }

  function lowerMakePhrase(cmd) {
    var tokens = cmd.trim().split(/\\s+/);
    if (tokens.length < 3 || tokens[0].toLowerCase() !== "make") return null;
    var resolved = resolveTargetTokens(tokens.slice(1));
    if (!resolved.target) return null;
    var modifierTokens = tokens.slice(1 + resolved.consumed);
    if (modifierTokens.length !== 1) return null;

    var modifier = modifierTokens[0].toLowerCase();
    if (COLORS.indexOf(modifier) !== -1) {
      return {text: "set " + resolved.target + ".color to " + modifier, subject: resolved.target};
    }
    if (SIZE_WORDS[modifier] != null) {
      var size = SIZE_WORDS[modifier];
      return {
        text: [
          "set " + resolved.target + ".width to " + size,
          "set " + resolved.target + ".height to " + size,
          "set " + resolved.target + ".depth to " + size
        ].join("\\n"),
        subject: resolved.target
      };
    }
    if (RELATIVE_SIZE_WORDS[modifier] != null) {
      var factor = RELATIVE_SIZE_WORDS[modifier];
      return {
        text: [
          "set " + resolved.target + ".width to " + resolved.target + ".width * " + factor,
          "set " + resolved.target + ".height to " + resolved.target + ".height * " + factor,
          "set " + resolved.target + ".depth to " + resolved.target + ".depth * " + factor
        ].join("\\n"),
        subject: resolved.target
      };
    }
    return null;
  }

  function lowerMovePhrase(cmd) {
    var tokens = cmd.trim().split(/\\s+/);
    if (tokens.length < 3) return null;
    var verb = tokens[0].toLowerCase();
    if (verb !== "move" && verb !== "put" && verb !== "place") return null;

    var resolved = resolveTargetTokens(tokens.slice(1));
    if (!resolved.target) return null;
    var rest = tokens.slice(1 + resolved.consumed).map(function(token) { return token.toLowerCase(); });
    if (!rest.length) return null;

    if (rest.length === 1 && DIRECTION_DELTAS[rest[0]]) {
      var delta = DIRECTION_DELTAS[rest[0]];
      var sign = delta[1] > 0 ? "+" : "-";
      return {
        text: "set " + resolved.target + "." + delta[0] + " to " + resolved.target + "." + delta[0] + " " + sign + " " + Math.abs(delta[1]),
        subject: resolved.target
      };
    }

    if (rest[0] !== "to" && rest[0] !== "at") return null;
    if (rest.length === 2 && rest[1] === "center") {
      return {
        text: ["set " + resolved.target + ".x to 0.5", "set " + resolved.target + ".y to 0.5"].join("\\n"),
        subject: resolved.target
      };
    }
    if (rest.length === 3) {
      var x = normaliseCoordinate(rest[1]);
      var y = normaliseCoordinate(rest[2]);
      if (x == null || y == null) return null;
      return {
        text: ["set " + resolved.target + ".x to " + x, "set " + resolved.target + ".y to " + y].join("\\n"),
        subject: resolved.target
      };
    }
    return null;
  }

  function lowerNatural(cmd) {
    return lowerCreatePhrase(cmd) || lowerMakePhrase(cmd) || lowerMovePhrase(cmd);
  }

  function suggestFix(raw, normalised) {
    var trimmed = raw.toLowerCase().trim();
    var tokens = normalised.split(/\\s+/);
    var command = tokens[0].toLowerCase();

    var mSet = raw.match(/^set\\s+(\\S+)\\s+(\\S+)\\s+(.+)$/i);
    if (mSet && mSet[1].indexOf(".") === -1) {
      log("  Did you mean: set " + mSet[1] + "." + mSet[2] + " to " + mSet[3] + "?", "#fbbf24");
      return;
    }

    var guidance = usageGuidanceForCommand(command);
    if (guidance) {
      logGuidance(guidance);
      return;
    }

    var closestCommand = closestMatch(command, commandCandidates());
    if (closestCommand) {
      log("  Did you mean: " + closestCommand + "?", "#fbbf24");
      return;
    }

    if (trimmed.indexOf("create") !== -1 || trimmed.indexOf("make") !== -1) {
      log("  Try: create object ball", "#fbbf24");
      log("  Or: create a big red ball", "#fbbf24");
      return;
    }

    log('  Type "help" for a list of commands.', "#6b7280");
  }

  function executeStrictCommand(normalised) {
    var m;

    if (normalised === "state" || normalised === "list") {
      listState();
      return true;
    }

    if (normalised === "list objects") {
      listObjects();
      return true;
    }

    if (normalised === "list events") {
      listEvents();
      return true;
    }

    if (normalised === "help" || normalised === "?") {
      showHelp();
      return true;
    }

    m = normalised.match(/^help\\s+(.+)$/);
    if (m) {
      showHelp(m[1]);
      return true;
    }

    if (normalised === "look") {
      listObjects();
      return true;
    }

    m = normalised.match(/^(?:look|get)\\s+(.+)$/);
    if (m) {
      if (inspectTarget(m[1])) {
        currentSubject = m[1].split(".", 1)[0];
        return true;
      }
      logErr('"' + m[1] + '" does not exist.');
      var objectSuggestion = closestMatch(m[1].split(".", 1)[0], Object.keys(rosh.objects));
      if (objectSuggestion) {
        log("  Did you mean: " + objectSuggestion + "?", "#fbbf24");
      } else {
        logGuidance(["list objects", "look <object>", "get <object>"]);
      }
      return true;
    }

    if (normalised === "clear") {
      while (logPanel.firstChild) logPanel.removeChild(logPanel.firstChild);
      return true;
    }

    m = normalised.match(/^print\\s+(.+)$/);
    if (m) {
      log(m[1].replace(/^["']|["']$/g, ""), "#e0e0e0");
      return true;
    }

    m = normalised.match(/^say\\s+(.+)$/);
    if (m) {
      var sayText = m[1].replace(/^["']|["']$/g, "");
      rosh.send("say", {text: sayText});
      log("  " + sayText, SUCCESS_C);
      return true;
    }

    m = normalised.match(/^set\\s+(\\S+)\\s+to\\s+(.+)$/);
    if (m) {
      var tgt = m[1];
      var rawVal = m[2].trim();
      var dotIdx = tgt.indexOf(".");
      if (dotIdx !== -1) {
        var objName = tgt.slice(0, dotIdx);
        var propName = tgt.slice(dotIdx + 1);
        var obj = rosh.get(objName);
        if (!obj || typeof obj !== "object") {
          logErr('"' + objName + '" does not exist.');
          var targetSuggestion = closestMatch(objName, Object.keys(rosh.objects));
          if (targetSuggestion) {
            log("  Did you mean: " + targetSuggestion + "?", "#fbbf24");
          } else {
            logGuidance(["create object " + objName, "list objects"]);
          }
          return true;
        }
        if (!(propName in obj)) {
          var propertySuggestion = closestMatch(propName, Object.keys(obj));
          if (propertySuggestion) {
            log("  Did you mean: set " + objName + "." + propertySuggestion + " to " + rawVal + "?", "#fbbf24");
          }
        }
      }
      try {
        var result = rosh.evalSetValue(tgt, rawVal);
        rosh.set(tgt, result);
        currentSubject = tgt.split(".", 1)[0];
        logOk("  " + tgt + " = " + JSON.stringify(result));
      } catch (e) {
        logErr(String(e));
      }
      return true;
    }

    m = normalised.match(/^create\\s+(?:(object|number|string|list)\\s+)?(\\S+)(?:\\s+as\\s+(\\S+))?$/);
    if (m) {
      var kind = m[1] || "object";
      var name = m[2];
      var shape = m[3] || "cube";
      if (SHAPES.indexOf(shape) === -1 && m[3]) {
        logErr('"' + shape + '" is not a shape.');
        log("  Shapes: " + SHAPES.join(", "), "#fbbf24");
        return true;
      }
      if (rosh.get(name) !== undefined) {
        logErr('"' + name + '" already exists.');
        logGuidance(["set " + name + ".color to red", "destroy " + name]);
        return true;
      }
      try {
        rosh.create(kind, name);
        currentSubject = name;
        if (kind === "object") {
          var spread = _createCount % 5;
          var xPos = (spread - 2) * 2.5;
          var color = DEFAULT_COLORS[_createCount % DEFAULT_COLORS.length];
          _createCount++;
          rosh.set(name + ".shape", shape);
          rosh.set(name + ".color", color);
          rosh.set(name + ".x", xPos);
          rosh.set(name + ".y", 1);
          rosh.set(name + ".z", 0);
          rosh.set(name + ".width", 1);
          rosh.set(name + ".height", 1);
          logOk('  created "' + name + '" — ' + shape + ", " + color + ", at x=" + xPos);
          log("  try: set " + name + ".color to red", "#6b7280");
        } else {
          logOk('  created "' + name + '" (' + kind + ")");
        }
      } catch (e) {
        logErr(String(e));
      }
      return true;
    }

    m = normalised.match(/^destroy\\s+(\\S+)$/);
    if (m) {
      if (rosh.get(m[1]) === undefined) {
        logErr('"' + m[1] + '" does not exist.');
        var destroySuggestion = closestMatch(m[1], Object.keys(rosh.objects));
        if (destroySuggestion) {
          log("  Did you mean: destroy " + destroySuggestion + "?", "#fbbf24");
        }
        return true;
      }
      try {
        rosh.destroy(m[1]);
        if (currentSubject === m[1]) currentSubject = null;
        logOk('  destroyed "' + m[1] + '"');
      } catch (e) {
        logErr(String(e));
      }
      return true;
    }

    return false;
  }

  function execCommand(raw) {
    var cmd = raw.trim();
    if (!cmd) return;

    if (history[0] !== cmd) history.unshift(cmd);
    if (history.length > 100) history.pop();
    historyIdx = -1;

    logCmd(cmd);
    var lowered = lowerNatural(cmd);
    if (lowered) {
      if (lowered.subject && lowered.text.indexOf("create object " + lowered.subject) === 0 && rosh.get(lowered.subject) !== undefined) {
        logErr('"' + lowered.subject + '" already exists.');
        logGuidance(["set " + lowered.subject + ".color to red", "destroy " + lowered.subject]);
        return;
      }
      var lines = lowered.text.split(/\\n+/);
      for (var li = 0; li < lines.length; li++) {
        var line = normalise(lines[li].trim());
        if (line) executeStrictCommand(line);
      }
      currentSubject = lowered.subject || currentSubject;
      return;
    }

    var normalised = normalise(cmd);
    var tokens = normalised.split(/\\s+/);
    if (tokens.length === 1) {
      var usage = usageGuidanceForCommand(tokens[0]);
      if (usage) {
        logErr(tokens[0] + " needs more information.");
        logGuidance(usage);
        return;
      }
      if (rosh.get(tokens[0]) !== undefined) {
        inspectTarget(tokens[0]);
        currentSubject = tokens[0];
        return;
      }
    }

    if (executeStrictCommand(normalised)) {
      var inferred = inferSubject(normalised);
      if (inferred) currentSubject = inferred;
      return;
    }

    logErr("unknown command");
    suggestFix(cmd, normalised);
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

  // ── Voice + console-button overlay ───────────────────────
  (function() {
    // Console toggle button — reliable fallback for the backtick key
    var conBtn = document.createElement("button");
    conBtn.innerHTML = ">_";
    conBtn.title = "Toggle Rosh console (or press `)";
    conBtn.style.cssText = "position:fixed;bottom:100px;right:16px;width:48px;height:48px;border-radius:10px;border:2px solid rgba(99,102,241,0.6);background:rgba(0,0,0,0.85);color:#6366f1;font-size:0.85rem;font-family:'SF Mono',monospace;font-weight:bold;cursor:pointer;z-index:99998;display:flex;align-items:center;justify-content:center;transition:all 0.2s;backdrop-filter:blur(4px);padding:0;";
    conBtn.addEventListener("click", function() { if (consoleOpen) closeConsole(); else openConsole(); });
    document.body.appendChild(conBtn);

    var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) return;

    var micBtn = document.createElement("button");
    micBtn.innerHTML = "&#x1F3A4;";
    micBtn.title = "Voice command — tap and speak";
    micBtn.style.cssText = "position:fixed;bottom:44px;right:16px;width:48px;height:48px;border-radius:50%;border:2px solid rgba(99,102,241,0.6);background:rgba(0,0,0,0.85);color:#6366f1;font-size:1.35rem;cursor:pointer;z-index:99998;display:flex;align-items:center;justify-content:center;transition:all 0.2s;backdrop-filter:blur(4px);padding:0;";
    document.body.appendChild(micBtn);

    var bubble = document.createElement("div");
    bubble.style.cssText = "position:fixed;bottom:160px;right:10px;max-width:200px;padding:6px 10px;background:rgba(0,0,0,0.9);border:1px solid rgba(99,102,241,0.4);border-radius:8px;color:#c084fc;font-family:'SF Mono',monospace;font-size:11px;z-index:99998;display:none;word-break:break-word;text-align:right;";
    document.body.appendChild(bubble);

    var pStyle = document.createElement("style");
    pStyle.textContent = "@keyframes rosh-mic-pulse{0%,100%{box-shadow:0 0 0 0 rgba(239,68,68,0.4)}50%{box-shadow:0 0 0 10px rgba(239,68,68,0)}}";
    document.head.appendChild(pStyle);

    var rec = new SR();
    rec.continuous = false;
    rec.interimResults = true;
    rec.lang = "en-GB";
    var listening = false;
    var bubbleTimer = null;

    function showBubble(text, color) {
      bubble.textContent = text;
      bubble.style.color = color || "#c084fc";
      bubble.style.display = "block";
      clearTimeout(bubbleTimer);
      bubbleTimer = setTimeout(function() { bubble.style.display = "none"; }, 3000);
    }

    function voiceToCommands(raw) {
      // Use rosh-natural.js if inlined by the build; minimal fallback otherwise
      if (typeof RoshNatural !== "undefined") {
        var lines = RoshNatural.normalize(raw).text.split("\\n");
        var SHAPE_2D_TO_3D = { circle: "sphere", rectangle: "cube" };
        var cmds = [];
        for (var i = 0; i < lines.length; i++) {
          var line = lines[i].trim();
          if (!line) continue;
          if (/^set \\w+\\.[xy] to /.test(line)) continue;
          var sm = line.match(/^(set \\w+\\.shape to )(\\w+)$/);
          if (sm) line = sm[1] + (SHAPE_2D_TO_3D[sm[2]] || sm[2]);
          line = line.replace(/^delete\\b/, "destroy");
          cmds.push(line);
        }
        return cmds.length ? cmds : [RoshNatural.cleanPunctuation(raw)];
      }
      // Fallback: strip politeness/articles, basic synonyms
      var t = raw.trim().toLowerCase().replace(/[.,!?]+$/, "");
      t = t.replace(/^(please|can you|could you)\\s+/i, "");
      t = t.replace(/\\b(a|an|the)\\s+/g, "");
      t = t.replace(/^(make|add|spawn)\\b/, "create");
      t = t.replace(/^(remove|delete)\\b/, "destroy");
      t = t.replace(/\\bcolou?r\\b/, "color");
      return [t];
    }

    rec.onresult = function(event) {
      var interim = "", finalText = "";
      for (var i = event.resultIndex; i < event.results.length; i++) {
        var t = event.results[i][0].transcript;
        if (event.results[i].isFinal) finalText += t;
        else interim = t;
      }
      if (interim) showBubble("..." + interim, "#71717a");
      if (finalText.trim()) {
        showBubble(finalText.trim(), "#86efac");
        openConsole();
        var cmds = voiceToCommands(finalText.trim());
        cmds.forEach(function(cmd) { execCommand(cmd); });
        stopListening();
      }
    };

    rec.onend = function() { if (listening) { try { rec.start(); } catch(e) {} } };

    rec.onerror = function(event) {
      if (event.error === "not-allowed") showBubble("Mic access denied", "#f87171");
      else if (event.error !== "aborted" && event.error !== "no-speech") showBubble("Error: " + event.error, "#f87171");
      stopListening();
    };

    function startListening() {
      listening = true;
      micBtn.style.borderColor = "#ef4444";
      micBtn.style.color = "#ef4444";
      micBtn.style.background = "rgba(239,68,68,0.15)";
      micBtn.style.animation = "rosh-mic-pulse 1.5s infinite";
      showBubble("Listening...", "#6366f1");
      try { rec.start(); } catch(e) {}
    }

    function stopListening() {
      listening = false;
      micBtn.style.borderColor = "rgba(99,102,241,0.6)";
      micBtn.style.color = "#6366f1";
      micBtn.style.background = "rgba(0,0,0,0.85)";
      micBtn.style.animation = "";
      try { rec.stop(); } catch(e) {}
    }

    micBtn.addEventListener("click", function() {
      if (listening) stopListening(); else startListening();
    });
  })();

  // ── Banner ───────────────────────────────────────────────
  log("Rosh console  \\u0060 to close", ACCENT);
  log("help  list  look  set  create  destroy  clear", "#6b7280");
  log("just try this: create a big red ball", "#6b7280");
})();
"""
