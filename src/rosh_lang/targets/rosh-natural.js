/**
 * Rosh Natural — Human-friendly layer for Rosh
 *
 * Converts natural speech/text into valid Rosh syntax using local pattern
 * matching. No AI dependency — runs entirely in the browser.
 *
 * Pipeline: escapes → politeness → articles → phrases → aliases → words →
 *           implied-to → infer-property → punctuation cleanup
 *
 * Based on Rosh 0.2.0 voice spec (rosh-voice.toml).
 *
 * Usage:
 *   const result = RoshNatural.normalize("please create a red ball");
 *   // result.text = 'sprite ball "red ball"\nset ball.x to 0.45\nset ball.y to 0.4'
 *   // result.changes = ["stripped: please", "phrase: create a red ball → sprite..."]
 *
 *   // Simple form:
 *   const code = RoshNatural.toRosh("set background blue");
 *   // code = 'background "blue"'
 *
 * Version: 1.0.0
 */

const RoshNatural = (function () {
  "use strict";

  // =========================================================================
  // VOICE ESCAPES — processed FIRST to preserve intent
  // =========================================================================
  // Spoken word → literal syntax character

  const ESCAPES_JOIN = { dot: ".", underscore: "_" }; // join adjacent words
  const ESCAPES_SPACE = { equals: "=", plus: "+" };   // keep as operator

  function applyEscapes(text) {
    const words = text.split(/\s+/);
    const result = [];
    const changes = [];
    let i = 0;

    while (i < words.length) {
      const wl = words[i].toLowerCase();

      if (wl in ESCAPES_JOIN) {
        const ch = ESCAPES_JOIN[wl];
        changes.push("escape: " + words[i] + " → " + ch);
        if (result.length && i + 1 < words.length) {
          result.push(result.pop() + ch + words[++i]);
        } else if (result.length) {
          result.push(result.pop() + ch);
        } else if (i + 1 < words.length) {
          result.push(ch + words[++i]);
        }
        i++;
        continue;
      }

      if (wl in ESCAPES_SPACE) {
        const ch = ESCAPES_SPACE[wl];
        changes.push("escape: " + words[i] + " → " + ch);
        result.push(ch);
        i++;
        continue;
      }

      result.push(words[i]);
      i++;
    }

    return { text: result.join(" "), changes };
  }

  // =========================================================================
  // POLITENESS STRIPPING
  // =========================================================================

  const POLITENESS = [
    /^please\s+/i,
    /^can\s+you\s+/i,
    /^could\s+you\s+/i,
    /^would\s+you\s+/i,
    /^i\s+want\s+to\s+/i,
    /^i\s+want\s+you\s+to\s+/i,
    /^i'd\s+like\s+to\s+/i,
    /^go\s+ahead\s+and\s+/i,
  ];

  function stripPoliteness(text) {
    for (const p of POLITENESS) {
      if (p.test(text)) {
        return { text: text.replace(p, ""), changed: true };
      }
    }
    return { text, changed: false };
  }

  // =========================================================================
  // ARTICLE STRIPPING
  // =========================================================================
  // Only in specific verb contexts to avoid removing articles from strings

  const ARTICLE_PATTERNS = [
    [/\b(create|make|add|draw|spawn|new)\s+(?:a|an|the)\s+/gi, "$1 "],
    [/\b(delete|remove|destroy|eliminate)\s+(?:a|an|the)\s+/gi, "$1 "],
    [/\b(move|hide|show|clone)\s+(?:a|an|the)\s+/gi, "$1 "],
    [/\b(set)\s+(?:a|an|the)\s+/gi, "$1 "],
    [/\blook\s+at\s+(?:a|an|the)\s+/gi, "look "],
    [/\b(?:get\s+rid\s+of|take\s+away)\s+(?:a|an|the)\s+/gi, "delete "],
  ];

  function stripArticles(text) {
    let result = text;
    let changed = false;
    for (const [pat, rep] of ARTICLE_PATTERNS) {
      const before = result;
      result = result.replace(pat, rep);
      if (result !== before) changed = true;
    }
    return { text: result, changed };
  }

  // =========================================================================
  // SHAPE SYNONYMS — natural names → sprite description keywords
  // =========================================================================
  // Maps common spoken shape names to keywords that sprites.py recognizes.
  // sprites.py shape families: spaceship, ship, ball, orb, alien, invader,
  //   bullet, crystal, gem, star
  // Plus these synonyms from v0.2.0 for natural speech:

  // Geometric shapes — rendered as actual shapes (circle, rectangle, etc.)
  // These use the `shape` property on the object, not procedural sprites.
  const GEOMETRIC_SHAPES = {
    ball: "circle", circle: "circle", sphere: "sphere", round: "circle",
    orb: "circle",
    square: "rectangle", rectangle: "rectangle", box: "rectangle",
    cube: "cube", block: "rectangle",
  };

  // Game object sprites — rendered as procedural pixel art via sprites.py
  const SPRITE_SHAPES = {
    spaceship: "spaceship", ship: "ship", rocket: "spaceship",
    alien: "alien", invader: "invader", ufo: "alien", monster: "alien",
    enemy: "alien", player: "spaceship", hero: "spaceship",
    bullet: "bullet", projectile: "bullet", missile: "bullet", arrow: "bullet",
    crystal: "crystal", gem: "gem", jewel: "gem",
    diamond: "gem", rock: "crystal", asteroid: "crystal",
    star: "star",
  };

  /**
   * Check if a noun is a geometric shape (renders as actual shape, not pixel art).
   */
  function isGeometric(name) {
    return name.toLowerCase() in GEOMETRIC_SHAPES;
  }

  /**
   * Resolve a shape name — returns { geometric: true/false, shape: "circle"/etc }
   */
  function resolveShape(name) {
    const lower = name.toLowerCase();
    if (lower in GEOMETRIC_SHAPES) {
      return { geometric: true, shape: GEOMETRIC_SHAPES[lower] };
    }
    if (lower in SPRITE_SHAPES) {
      return { geometric: false, shape: SPRITE_SHAPES[lower] };
    }
    return { geometric: false, shape: name };
  }

  // =========================================================================
  // NATURAL PHRASE PATTERNS — maps speech to valid Rosh syntax
  // =========================================================================
  // Order matters: more specific patterns first

  const PHRASE_PATTERNS = [
    // "create/make/add/draw a [adj] [noun] at X Y"
    [/\b(?:create|make|add|draw|spawn)\s+(\w+)\s+(\w+)\s+at\s+(\d+)\s*[,\s]\s*(\d+)\b/gi,
      (_, adj, noun, x, y) => {
        const r = resolveShape(noun);
        if (r.geometric) {
          return `create object ${noun}\nset ${noun}.color to ${adj}\nset ${noun}.shape to ${r.shape}\nset ${noun}.x to 0.${x}\nset ${noun}.y to 0.${y}`;
        }
        return `sprite ${noun} "${adj} ${r.shape}"\nset ${noun}.color to ${adj}\nset ${noun}.x to 0.${x}\nset ${noun}.y to 0.${y}`;
      }],

    // "create/make/add/draw a [adj] [noun]" — centered (0.5 works on all targets)
    [/\b(?:create|make|add|draw|spawn)\s+(\w+)\s+(\w+)\b/gi,
      (_, adj, noun) => {
        const r = resolveShape(noun);
        if (r.geometric) {
          return `create object ${noun}\nset ${noun}.color to ${adj}\nset ${noun}.shape to ${r.shape}\nset ${noun}.x to 0.5\nset ${noun}.y to 0.5`;
        }
        return `sprite ${noun} "${adj} ${r.shape}"\nset ${noun}.color to ${adj}\nset ${noun}.x to 0.5\nset ${noun}.y to 0.5`;
      }],

    // "set background to [color]" / "background [color]"
    [/\b(?:set\s+)?background\s+(?:to\s+)?(\w+)\b/gi,
      (_, color) => `background "${color}"`],

    // "move [obj] [direction]" — wire up arrow key
    [/\bmove\s+(\w+)\s+(left|right|up|down)\b/gi,
      (_, obj, dir) => `when ${dir} move ${obj} ${dir} 2`],

    // "what color is [obj]" / "where is [obj]" / "how big is [obj]"
    [/\bwhat\s+color\s+is\s+(\w+)\b/gi, (_, o) => `get ${o} color`],
    [/\bwhere\s+is\s+(\w+)\b/gi, (_, o) => `get ${o} position`],
    [/\bhow\s+big\s+is\s+(\w+)\b/gi, (_, o) => `get ${o} size`],
    [/\bhow\s+many\b/gi, () => "count"],

    // "what's the [prop]" / "what is the [prop]"
    [/\bwhat(?:'s|\s+is)\s+the\s+(\w+)\b/gi, (_, p) => `get ${p}`],

    // "put it at X Y"
    [/\bput\s+(?:it\s+)?at\s+(\d+)\s*[,\s]\s*(\d+)\b/gi,
      (_, x, y) => `move to ${x} ${y}`],

    // "bring back [obj]"
    [/\bbring\s+back\s+(\w+)\b/gi, (_, o) => `show ${o}`],

    // "get rid of [obj]" / "take away [obj]"
    [/\b(?:get\s+rid\s+of|take\s+away)\s+(\w+)\b/gi, (_, o) => `delete ${o}`],

    // "print [text]" — wrap in quotes if not already
    [/\bprint\s+(?!")([\w\s]+)/gi, (_, text) => `print "${text.trim()}"`],
  ];

  function applyPhrases(text) {
    let result = text;
    const changes = [];
    for (const [pat, rep] of PHRASE_PATTERNS) {
      const before = result;
      result = result.replace(pat, rep);
      if (result !== before) {
        changes.push("phrase");
      }
    }
    return { text: result, changes };
  }

  // =========================================================================
  // COMMAND ALIASES — single-word natural synonyms → Rosh keywords
  // =========================================================================

  const ALIASES = {
    // Creation
    new: "create", add: "create", spawn: "create",
    // Deletion
    remove: "delete", destroy: "delete", eliminate: "delete",
    // Inspection
    examine: "look", inspect: "look", check: "look", describe: "look",
    // Visibility
    reveal: "show", unhide: "show", display: "show",
    conceal: "hide", disappear: "hide",
    // Navigation
    travel: "goto", visit: "goto", enter: "goto",
    // Undo
    oops: "undo", whoops: "undo", nevermind: "undo", revert: "undo",
  };

  function applyAliases(text) {
    let result = text;
    const changes = [];
    for (const [alias, cmd] of Object.entries(ALIASES)) {
      const re = new RegExp("\\b" + alias + "\\b", "gi");
      if (re.test(result)) {
        result = result.replace(re, cmd);
        changes.push(alias + " → " + cmd);
      }
    }
    return { text: result, changes };
  }

  // =========================================================================
  // WORD CORRECTIONS — common speech-to-text mishearings
  // =========================================================================

  const CORRECTIONS = {
    // Brand
    rush: "rosh", rash: "rosh", ross: "rosh", roush: "rosh",
    raush: "rosh", rawsh: "rosh",

    // Rosh keywords
    sit: "set", sat: "set", said: "set",
    spright: "sprite", spread: "sprite", spite: "sprite", spirit: "sprite",
    wen: "when", wend: "when",
    moved: "move", moov: "move", mov: "move", mvoe: "move",
    principal: "print", prince: "print",
    sides: "size", sighs: "size",
    repete: "repeat", repat: "repeat",
    divined: "define", divine: "define",
    collusion: "collision",
    "lay bell": "label",
    creat: "create", crate: "create", craete: "create",
    delte: "delete", deleet: "delete",
    cloen: "clone",
    lst: "list", lok: "look", lool: "look",
    hlep: "help", hepl: "help",
    unod: "undo", reod: "redo",
    shwo: "show", hdie: "hide",
    mak: "make", maek: "make",
    coutn: "count",
    tow: "to", inn: "in", iff: "if", els: "else",
    wile: "while", ennd: "end",

    // Colors
    read: "red", reed: "red", blew: "blue", blow: "blue", blu: "blue",
    grey: "gray", gry: "gray",
    wait: "white", weight: "white", wet: "white", whit: "white",
    lack: "black", block: "black", blak: "black",
    screen: "green", grain: "green", gren: "green",
    fellow: "yellow", yell: "yellow", yello: "yellow", yelloe: "yellow",
    science: "cyan", sign: "cyan",
    arrange: "orange", orang: "orange",
    ping: "pink",
    perple: "purple", people: "purple", purpl: "purple", purpel: "purple",

    // Properties
    collar: "color", colour: "color", cooler: "color",
    fund: "font", front: "font", funt: "font",
    with: "width", whith: "width",
    hight: "height",
    "fizzy ball": "visible",
    skill: "scale", polls: "pulse", pulls: "pulse", pals: "pulse",

    // Coordinates
    ex: "x", eggs: "x", why: "y", wie: "y",
    see: "z", zee: "z", zed: "z",

    // Fonts
    enter: "Inter", inner: "Inter",
    aerial: "Arial", area: "Arial",

    // British spellings
    centre: "center", colours: "colors",
    favourite: "favorite", behaviour: "behavior",
    organised: "organized", realise: "realize",

    // Numbers
    zero: "0", one: "1", won: "1", two: "2", three: "3",
    four: "4", five: "5", six: "6", seven: "7",
    eight: "8", ate: "8", nine: "9", ten: "10",

    // Phrases
    "new line": "\n",
  };

  // User-added corrections (merged at runtime)
  let _customCorrections = {};

  function applyWordCorrections(text) {
    let result = text;
    const changes = [];
    const all = { ...CORRECTIONS, ..._customCorrections };

    // Sort by length (longest first) so multi-word patterns match before singles
    const sorted = Object.entries(all).sort((a, b) => b[0].length - a[0].length);

    for (const [from, to] of sorted) {
      const escaped = from.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      const re = new RegExp("\\b" + escaped + "\\b", "gi");
      if (re.test(result)) {
        result = result.replace(re, to);
        changes.push(from + " → " + to);
      }
    }

    return { text: result, changes };
  }

  // =========================================================================
  // IMPLIED "to" — adds missing keyword in set/move commands
  // =========================================================================

  function addImpliedTo(text) {
    // Process line by line
    const lines = text.split("\n");
    const changes = [];
    const result = lines.map((line) => {
      if (/\bto\b/i.test(line)) return line; // already has "to"

      // "set obj.prop value" or "set obj prop value"
      const setMatch = line.match(
        /^(set\s+[\w.]+(?:\s+[\w.]+)?)\s+(\S.*)$/i
      );
      if (setMatch) {
        const value = setMatch[2];
        if (!/^to\s/i.test(value)) {
          changes.push("implied: to");
          return setMatch[1] + " to " + value;
        }
      }

      // "move obj X Y"
      const moveMatch = line.match(
        /^(move\s+\w+)\s+(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)(.*)$/i
      );
      if (moveMatch) {
        changes.push("implied: to");
        return (
          moveMatch[1] + " to " + moveMatch[2] + " " + moveMatch[3] + moveMatch[4]
        );
      }

      return line;
    });

    return { text: result.join("\n"), changes };
  }

  // =========================================================================
  // PROPERTY INFERENCE — "set box red" → "set box color to red"
  // =========================================================================

  const COLOR_NAMES = new Set([
    "red", "green", "blue", "yellow", "cyan", "magenta",
    "white", "black", "orange", "purple", "pink",
    "gray", "grey", "gold", "silver", "brown",
    "navy", "teal", "coral", "salmon", "lime",
    "indigo", "violet", "crimson", "maroon",
  ]);

  function inferProperty(text) {
    const lines = text.split("\n");
    const changes = [];
    const result = lines.map((line) => {
      // "set obj <color>" → "set obj color to <color>"
      const m1 = line.match(/^set\s+(\w+)\s+(\w+)$/i);
      if (m1 && COLOR_NAMES.has(m1[2].toLowerCase())) {
        changes.push("inferred: color");
        return `set ${m1[1]} color to ${m1[2]}`;
      }
      // "set obj to <color>" → "set obj color to <color>"
      const m2 = line.match(/^set\s+(\w+)\s+to\s+(\w+)$/i);
      if (m2 && COLOR_NAMES.has(m2[2].toLowerCase())) {
        changes.push("inferred: color");
        return `set ${m2[1]} color to ${m2[2]}`;
      }
      return line;
    });

    return { text: result.join("\n"), changes };
  }

  // =========================================================================
  // PUNCTUATION CLEANUP — strip speech-to-text punctuation noise
  // =========================================================================

  function cleanPunctuation(text) {
    return text
      .replace(/[.!?]+$/gm, "")        // trailing sentence punctuation per line
      .replace(/,\s*/g, " ")            // commas → space (unless in quotes)
      .replace(/\s{2,}/g, " ")          // collapse whitespace
      .trim();
  }

  // =========================================================================
  // MAIN PIPELINE
  // =========================================================================

  /**
   * Full normalization pipeline.
   * @param {string} input - Raw speech/text input
   * @param {object} [opts] - Options
   * @param {boolean} [opts.quiet=false] - Suppress change messages
   * @returns {{ text: string, changes: string[] }}
   */
  function normalize(input, opts) {
    if (!input || !input.trim()) return { text: "", changes: [] };

    const quiet = opts && opts.quiet;
    let text = input.trim().toLowerCase();
    const changes = [];

    function collect(step) {
      if (!quiet && step.changes) {
        for (const c of step.changes) changes.push(c);
      }
      if (step.changed && !quiet) changes.push("stripped");
      text = step.text;
    }

    // 1. Voice escapes (dot, underscore, equals, plus)
    collect(applyEscapes(text));

    // 2. Politeness ("please create a box" → "create a box")
    collect(stripPoliteness(text));

    // 3. Articles ("create a box" → "create box")
    collect(stripArticles(text));

    // 4. Natural phrases ("create red ball" → sprite syntax)
    collect(applyPhrases(text));

    // 5. Command aliases ("remove ball" → "delete ball")
    collect(applyAliases(text));

    // 6. Word corrections (mishearings + spellings + numbers)
    collect(applyWordCorrections(text));

    // 7. Implied "to" ("set x 100" → "set x to 100")
    collect(addImpliedTo(text));

    // 8. Property inference ("set box red" → "set box color to red")
    collect(inferProperty(text));

    // 9. Punctuation cleanup
    text = cleanPunctuation(text);

    return { text, changes };
  }

  /**
   * Simple form — returns just the normalized text.
   * @param {string} input
   * @returns {string}
   */
  function toRosh(input) {
    return normalize(input).text;
  }

  /**
   * Add a custom word correction.
   * @param {string} wrong - Misheard word
   * @param {string} right - Correct word
   */
  function addCorrection(wrong, right) {
    _customCorrections[wrong.toLowerCase()] = right;
  }

  /**
   * Set custom corrections dict (replaces all custom corrections).
   * @param {object} dict - { wrong: right, ... }
   */
  function setCustomCorrections(dict) {
    _customCorrections = { ...dict };
  }

  /**
   * Get all corrections (built-in + custom).
   * @returns {object}
   */
  function getCorrections() {
    return { ...CORRECTIONS, ..._customCorrections };
  }

  /**
   * Get built-in corrections only.
   * @returns {object}
   */
  function getBuiltinCorrections() {
    return { ...CORRECTIONS };
  }

  /**
   * Check if a word is a known color.
   * @param {string} word
   * @returns {boolean}
   */
  function isColor(word) {
    return COLOR_NAMES.has(word.toLowerCase());
  }

  // Public API
  return {
    normalize,
    toRosh,
    addCorrection,
    setCustomCorrections,
    getCorrections,
    getBuiltinCorrections,
    isColor,
    resolveShape,
    // Direct access for advanced use
    applyEscapes,
    stripPoliteness,
    stripArticles,
    applyPhrases,
    applyAliases,
    applyWordCorrections,
    addImpliedTo,
    inferProperty,
    cleanPunctuation,
    COLOR_NAMES,
    CORRECTIONS,
    ALIASES,
    GEOMETRIC_SHAPES,
    SPRITE_SHAPES,
    VERSION: "1.1.0",
  };
})();

// Export for module systems
if (typeof module !== "undefined" && module.exports) {
  module.exports = RoshNatural;
}
