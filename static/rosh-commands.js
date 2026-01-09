/**
 * Rosh Commands Module - Shared command parsing and normalization
 *
 * Parses console commands into structured intents. Execution is handled
 * by engine-specific adapters.
 *
 * Usage:
 *   const intent = RoshCommands.parse('create big red cube');
 *   // intent = { action: 'create', type: 'cube', modifiers: { size: 'big', color: 'red' } }
 *
 * Version: 0.1.0
 */

const RoshCommands = (function() {
  'use strict';

  // Command aliases - normalize to canonical form
  const COMMAND_ALIASES = {
    // List
    'ls': 'list',
    'objects': 'list',
    'dir': 'list',

    // Look/examine
    'x': 'look',
    'ex': 'look',
    'examine': 'look',
    'inspect': 'look',

    // Delete
    'remove': 'delete',
    'destroy': 'delete',
    'rm': 'delete',

    // Show/hide
    'unhide': 'show',
    'reveal': 'show',

    // Scene navigation
    'goto': 'go',
    'scene': 'go',
    'room': 'go',

    // Scenes list
    'rooms': 'scenes',
    'levels': 'scenes',

    // Select
    'sel': 'select',
    'pick': 'select',

    // Deselect
    'desel': 'deselect',
    'unpick': 'deselect',

    // Help
    '?': 'help',

    // Repeat
    ':r': 'repeat',
    ':repeat': 'repeat',

    // Twin/networking
    'twin': 'connect',
    'who': 'users'
  };

  // Size modifiers with their scale multipliers
  const SIZE_MODIFIERS = {
    'tiny': 0.25,
    'small': 0.5,
    'medium': 1,
    'big': 2,
    'large': 2,
    'huge': 4,
    'giant': 6,
    'massive': 8
  };

  // Number words to numeric values
  const NUMBER_WORDS = {
    'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
    'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10
  };

  // Articles to skip in parsing
  const ARTICLES = ['a', 'an', 'the', 'some', 'my', 'this'];

  // All known commands (for fuzzy matching)
  const KNOWN_COMMANDS = [
    'create', 'make', 'delete', 'clone', 'list', 'look', 'set', 'get',
    'hide', 'show', 'move', 'go', 'scenes', 'select', 'deselect', 'edit',
    'undo', 'redo', 'repeat', 'save', 'load', 'count', 'clear', 'help',
    'gravity', 'ground', 'control', 'speed', 'keys',
    'connect', 'disconnect', 'say', 'users', 'credits'
  ];

  /**
   * Normalize command (resolve aliases)
   * @param {string} cmd - Command verb
   * @returns {string} Canonical command name
   */
  function normalizeCommand(cmd) {
    const lower = cmd.toLowerCase();
    return COMMAND_ALIASES[lower] || lower;
  }

  /**
   * Parse a command string into a structured intent
   * @param {string} input - Raw command string
   * @returns {object} Parsed intent
   */
  function parse(input) {
    if (!input || typeof input !== 'string') {
      return { action: null, error: 'Empty command' };
    }

    const trimmed = input.trim();
    if (!trimmed) {
      return { action: null, error: 'Empty command' };
    }

    // Tokenize
    const tokens = trimmed.split(/\s+/);
    const action = normalizeCommand(tokens[0]);
    const args = tokens.slice(1);

    // Build base intent
    const intent = {
      action: action,
      raw: trimmed,
      tokens: tokens,
      args: args
    };

    // Route to specific parsers based on action
    switch (action) {
      case 'create':
      case 'make':
        return parseCreateIntent(intent, args);

      case 'set':
        return parseSetIntent(intent, args, trimmed);

      case 'move':
        return parseMoveIntent(intent, args, trimmed);

      case 'delete':
        return parseDeleteIntent(intent, args);

      case 'look':
      case 'get':
      case 'select':
        return parseTargetIntent(intent, args);

      default:
        intent.args = args;
        return intent;
    }
  }

  /**
   * Parse CREATE/MAKE command
   * "create big red cube" -> { action: 'create', type: 'cube', modifiers: { size: 'big', color: 'red' } }
   * "create three balls" -> { action: 'create', type: 'ball', count: 3 }
   * "create the red ball" -> { action: 'create', type: 'ball', modifiers: { color: 'red' } }
   */
  function parseCreateIntent(intent, args) {
    const modifiers = {};
    let type = null;
    let count = 1;

    // Check for bulk create: "create 5 cubes"
    if (args.length > 0 && /^\d+$/.test(args[0])) {
      count = parseInt(args[0], 10);
      args = args.slice(1);
    }
    // Check for number word: "create three cubes"
    else if (args.length > 0 && NUMBER_WORDS[args[0].toLowerCase()]) {
      count = NUMBER_WORDS[args[0].toLowerCase()];
      args = args.slice(1);
    }

    // Extract modifiers and type from remaining args
    for (const arg of args) {
      const lower = arg.toLowerCase();

      // Skip articles
      if (ARTICLES.includes(lower)) {
        continue;
      }

      // Size modifier?
      if (SIZE_MODIFIERS[lower] !== undefined) {
        modifiers.size = lower;
        modifiers.scale = SIZE_MODIFIERS[lower];
        continue;
      }

      // Color? (check if RoshColors is available)
      if (typeof RoshColors !== 'undefined' && RoshColors.isColorName(lower)) {
        modifiers.color = lower;
        continue;
      }

      // Otherwise it's the type (last non-modifier wins)
      type = singularize(lower);
    }

    intent.type = type || 'cube';  // Default to cube
    intent.modifiers = modifiers;
    intent.count = count;

    return intent;
  }

  /**
   * Parse SET command
   * "set cube color to red" -> { action: 'set', target: 'cube', property: 'color', value: 'red' }
   */
  function parseSetIntent(intent, args, raw) {
    // Try: set <obj> <prop> [to] <value>
    const match = raw.match(/^set\s+(\S+)\s+(\S+)\s+(?:to\s+)?(.+)$/i);
    if (match) {
      intent.target = match[1];
      intent.property = match[2];
      intent.value = match[3];
    } else {
      // Try: set <prop> [to] <value> (target from selection)
      const shortMatch = raw.match(/^set\s+(\S+)\s+(?:to\s+)?(.+)$/i);
      if (shortMatch) {
        intent.target = null;  // Use selected object
        intent.property = shortMatch[1];
        intent.value = shortMatch[2];
      } else {
        intent.error = 'Usage: set <object> <property> [to] <value>';
      }
    }
    return intent;
  }

  /**
   * Parse MOVE command
   * "move cube up 5" or "move cube to 0 10 0"
   */
  function parseMoveIntent(intent, args, raw) {
    // Try absolute: move <obj> to <x> <y> [z]
    const absMatch = raw.match(/^move\s+(\S+)\s+to\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s*(-?\d+\.?\d*)?$/i);
    if (absMatch) {
      intent.target = absMatch[1];
      intent.mode = 'absolute';
      intent.position = {
        x: parseFloat(absMatch[2]),
        y: parseFloat(absMatch[3]),
        z: absMatch[4] ? parseFloat(absMatch[4]) : undefined
      };
      return intent;
    }

    // Try relative: move <obj> <direction> <amount>
    const relMatch = raw.match(/^move\s+(\S+)\s+(forward|back|backward|left|right|up|down)\s+(-?\d+\.?\d*)$/i);
    if (relMatch) {
      intent.target = relMatch[1];
      intent.mode = 'relative';
      intent.direction = relMatch[2].toLowerCase();
      intent.amount = parseFloat(relMatch[3]);
      return intent;
    }

    intent.error = 'Usage: move <obj> <direction> <amount> OR move <obj> to <x> <y> [z]';
    return intent;
  }

  /**
   * Parse DELETE command
   */
  function parseDeleteIntent(intent, args) {
    if (args.length === 0) {
      intent.target = null;  // Use selection
      intent.confirmed = false;
    } else if (args[0].toLowerCase() === 'confirmed') {
      intent.target = null;
      intent.confirmed = true;
    } else {
      intent.target = args.join(' ');
      intent.confirmed = false;
    }
    return intent;
  }

  /**
   * Parse target-only commands (look, get, select)
   */
  function parseTargetIntent(intent, args) {
    intent.target = args.join(' ') || null;
    return intent;
  }

  /**
   * Singularize a word (basic plurals only)
   */
  function singularize(word) {
    const w = word.toLowerCase();
    // Exceptions that end in 's' but aren't plural
    const exceptions = ['torus', 'bus', 'plus', 'radius', 'canvas', 'axis', 'lewis', 'chris', 'paris', 'harris', 'morris', 'dennis', 'texas', 'kansas', 'christmas'];
    if (exceptions.includes(w)) return w;
    // Words ending in 'is' are usually not plural (basis, thesis, lewis)
    if (w.endsWith('is')) return w;
    if (w.endsWith('ies')) return w.slice(0, -3) + 'y';
    if (w.endsWith('es') && !w.endsWith('ses')) return w.slice(0, -2);
    if (w.endsWith('s') && !w.endsWith('ss')) return w.slice(0, -1);
    return w;
  }

  /**
   * Check if a string is a known command
   */
  function isCommand(str) {
    const lower = str.toLowerCase();
    return KNOWN_COMMANDS.includes(lower) || Object.keys(COMMAND_ALIASES).includes(lower);
  }

  /**
   * Get all known command names (for autocomplete/fuzzy matching)
   */
  function getCommands() {
    return KNOWN_COMMANDS.slice();
  }

  /**
   * Check if a word is a size modifier
   */
  function isSizeModifier(word) {
    return SIZE_MODIFIERS[word.toLowerCase()] !== undefined;
  }

  /**
   * Get scale value for a size modifier
   */
  function getSizeScale(word) {
    return SIZE_MODIFIERS[word.toLowerCase()] || 1;
  }

  // Public API
  /**
   * Check if a word is a number word (one-ten)
   */
  function isNumberWord(word) {
    return NUMBER_WORDS[word.toLowerCase()] !== undefined;
  }

  /**
   * Get numeric value for a number word
   */
  function getNumberValue(word) {
    return NUMBER_WORDS[word.toLowerCase()] || null;
  }

  /**
   * Check if a word is an article
   */
  function isArticle(word) {
    return ARTICLES.includes(word.toLowerCase());
  }

  return {
    parse: parse,
    normalizeCommand: normalizeCommand,
    singularize: singularize,
    isCommand: isCommand,
    getCommands: getCommands,
    isSizeModifier: isSizeModifier,
    getSizeScale: getSizeScale,
    isNumberWord: isNumberWord,
    getNumberValue: getNumberValue,
    isArticle: isArticle,
    // Direct access
    COMMAND_ALIASES: COMMAND_ALIASES,
    SIZE_MODIFIERS: SIZE_MODIFIERS,
    KNOWN_COMMANDS: KNOWN_COMMANDS,
    NUMBER_WORDS: NUMBER_WORDS,
    ARTICLES: ARTICLES
  };
})();

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = RoshCommands;
}
