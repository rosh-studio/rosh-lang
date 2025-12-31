/**
 * Rosh Runtime - Shared REPL/Console for all emitters
 *
 * This runtime provides the core REPL functionality that works across
 * Three.js, Phaser, and other emitters. Engine-specific code is delegated
 * to adapter objects.
 *
 * Usage:
 *   1. Include this script
 *   2. Create a RoshAdapter object with engine-specific methods
 *   3. Call RoshRuntime.init(adapter)
 *
 * Version: 0.1.0
 * Spec: rosh-console.toml v0.2.5
 */

const RoshRuntime = (function() {
  'use strict';

  // ==========================================================================
  // STATE
  // ==========================================================================

  let adapter = null;           // Engine adapter (Three.js, Phaser, etc.)
  let consoleVisible = false;
  let currentObject = null;     // Currently selected object reference
  let currentObjectName = null; // Name of currently selected object
  let currentSelection = [];    // For multi-select (get all X)
  let currentSelectionType = null;

  const cmdHistory = [];
  let historyIdx = -1;

  const undoStack = [];
  const redoStack = [];
  let undoGroup = 0;

  let lastUserCommand = null;   // For :repeat
  let pendingOp = null;         // For confirmation dialogs

  let bulkCreateMode = false;
  let bulkCreateCount = 0;
  const BULK_LOG_LIMIT = 10;

  // DOM elements
  let outputEl = null;
  let inputEl = null;

  // ==========================================================================
  // CONSOLE UI
  // ==========================================================================

  function createConsoleUI() {
    // CSS
    const style = document.createElement('style');
    style.textContent = `
      #rosh-console { position: fixed; bottom: 0; left: 0; width: 100%; height: 250px;
        background: rgba(0,0,0,0.95); color: #0f0; font-family: monospace; font-size: 14px;
        border-top: 2px solid #0f0; display: none; flex-direction: column; z-index: 10000; }
      #rosh-console.visible { display: flex; }
      #rosh-output { flex: 1; overflow-y: auto; padding: 10px; }
      #rosh-output .cmd { color: #ff0; }
      #rosh-output .ok { color: #3f3; }
      #rosh-output .err { color: #f33; }
      #rosh-output .warn { color: #fa0; }
      #rosh-output .dim { color: #888; }
      #rosh-output .cyan { color: #0ff; }
      #rosh-input-line { padding: 10px; border-top: 1px solid #0f0; display: flex; gap: 8px; align-items: center; }
      #rosh-input-line input { flex: 1; background: #111; border: 1px solid #0f0;
        color: #0f0; padding: 8px; font-family: inherit; }
      #rosh-voice { width: 24px; height: 24px; cursor: pointer; opacity: 0.5; transition: all 0.2s; }
      #rosh-voice:hover { opacity: 0.8; }
      #rosh-voice.listening { opacity: 1; animation: rosh-pulse 1s infinite; }
      @keyframes rosh-pulse { 0%,100% { transform: scale(1); } 50% { transform: scale(1.2); } }
    `;
    document.head.appendChild(style);

    // HTML
    const consoleDiv = document.createElement('div');
    consoleDiv.id = 'rosh-console';
    consoleDiv.innerHTML = `
      <div style="padding:8px;background:#111;border-bottom:1px solid #0f0">
        <strong>ROSH CONSOLE</strong> <small style="color:#888">Press \` to toggle</small>
      </div>
      <div id="rosh-output"></div>
      <div id="rosh-input-line">
        <span style="color:#0f0">rosh></span>
        <input type="text" id="rosh-input" placeholder="type or Ctrl+Space for voice" autocomplete="off">
        <svg id="rosh-voice" viewBox="0 0 24 24" fill="#0f0" title="Click or Ctrl+Space to speak">
          <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm-1-9c0-.55.45-1 1-1s1 .45 1 1v6c0 .55-.45 1-1 1s-1-.45-1-1V5zm6 6c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
        </svg>
      </div>
    `;
    document.body.appendChild(consoleDiv);

    outputEl = document.getElementById('rosh-output');
    inputEl = document.getElementById('rosh-input');

    // Event handlers
    document.addEventListener('keydown', handleGlobalKeydown);
    inputEl.addEventListener('keydown', handleInputKeydown);

    // Voice button
    const voiceBtn = document.getElementById('rosh-voice');
    if (voiceBtn) {
      voiceBtn.addEventListener('click', toggleVoice);
    }
  }

  function handleGlobalKeydown(e) {
    if (e.key === '`' || e.key === '~') {
      e.preventDefault();
      toggleConsole();
    }
    // Ctrl+Space for voice anywhere
    if (e.ctrlKey && e.code === 'Space') {
      e.preventDefault();
      toggleVoice();
    }
  }

  function handleInputKeydown(e) {
    if (e.key === 'Enter') {
      const cmd = inputEl.value.trim();
      if (cmd) {
        cmdHistory.push(cmd);
        historyIdx = cmdHistory.length;
        execCommand(cmd);
        inputEl.value = '';
      }
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (historyIdx > 0) {
        historyIdx--;
        inputEl.value = cmdHistory[historyIdx] || '';
      }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (historyIdx < cmdHistory.length - 1) {
        historyIdx++;
        inputEl.value = cmdHistory[historyIdx] || '';
      } else {
        historyIdx = cmdHistory.length;
        inputEl.value = '';
      }
    } else if (e.key === 'Escape') {
      toggleConsole();
    }
  }

  function toggleConsole() {
    const el = document.getElementById('rosh-console');
    if (!el) return;
    consoleVisible = !consoleVisible;
    el.classList.toggle('visible', consoleVisible);
    if (consoleVisible && inputEl) inputEl.focus();

    // Sync with global consoleVisible (for emitter's WASD handler)
    if (typeof window !== 'undefined') {
      window.consoleVisible = consoleVisible;
    }
  }

  // ==========================================================================
  // LOGGING
  // ==========================================================================

  function log(msg, cls = '') {
    if (!outputEl) return;
    const div = document.createElement('div');
    div.className = cls;
    div.textContent = msg;
    outputEl.appendChild(div);
    outputEl.scrollTop = outputEl.scrollHeight;
  }

  function clearOutput() {
    if (outputEl) outputEl.innerHTML = '';
  }

  // ==========================================================================
  // UNDO/REDO
  // ==========================================================================

  function pushUndo(description, undoFn, redoFn) {
    if (typeof undoFn !== 'function') return;
    undoStack.push({
      description: description || 'change',
      undo: undoFn,
      redo: typeof redoFn === 'function' ? redoFn : null,
      group: undoGroup
    });
    if (undoStack.length > 100) undoStack.shift();
    redoStack.length = 0;
  }

  function performUndo(count = 1) {
    if (!undoStack.length) {
      log('Nothing to undo', 'err');
      return;
    }
    for (let step = 0; step < count; step++) {
      if (!undoStack.length) break;
      const targetGroup = undoStack[undoStack.length - 1].group;
      const groupEntries = [];
      while (undoStack.length && undoStack[undoStack.length - 1].group === targetGroup) {
        groupEntries.push(undoStack.pop());
      }
      let undoCount = 0;
      for (const entry of groupEntries) {
        try {
          entry.undo();
          undoCount++;
          if (entry.redo) redoStack.push(entry);
        } catch (err) {
          log('Undo failed: ' + (err && err.message ? err.message : err), 'err');
        }
      }
      if (undoCount > 1) {
        log('Undo: ' + groupEntries[0].description + ' (' + undoCount + ' operations)', 'ok');
      } else if (undoCount === 1) {
        log('Undo: ' + groupEntries[0].description, 'ok');
      }
    }
  }

  function performRedo(count = 1) {
    if (!redoStack.length) {
      log('Nothing to redo', 'err');
      return;
    }
    const steps = Math.min(Math.max(1, count), redoStack.length);
    for (let i = 0; i < steps; i++) {
      const entry = redoStack.pop();
      if (!entry || typeof entry.redo !== 'function') continue;
      try {
        entry.redo();
        log('Redo: ' + entry.description, 'ok');
        undoStack.push(entry);
      } catch (err) {
        log('Redo failed: ' + (err && err.message ? err.message : err), 'err');
        break;
      }
    }
  }

  // ==========================================================================
  // FUZZY MATCHING
  // ==========================================================================

  function levenshtein(a, b) {
    const m = a.length, n = b.length;
    if (m === 0) return n;
    if (n === 0) return m;
    const dp = Array.from({ length: m + 1 }, () => Array(n + 1).fill(0));
    for (let i = 0; i <= m; i++) dp[i][0] = i;
    for (let j = 0; j <= n; j++) dp[0][j] = j;
    for (let i = 1; i <= m; i++) {
      for (let j = 1; j <= n; j++) {
        dp[i][j] = a[i-1] === b[j-1]
          ? dp[i-1][j-1]
          : 1 + Math.min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1]);
      }
    }
    return dp[m][n];
  }

  function fuzzyMatch(input, candidates, maxDistance = 2) {
    const lower = input.toLowerCase();
    let best = null, bestDist = Infinity;
    for (const c of candidates) {
      const dist = levenshtein(lower, c.toLowerCase());
      if (dist < bestDist && dist <= maxDistance) {
        best = c;
        bestDist = dist;
      }
    }
    return best;
  }

  // Known commands for fuzzy matching
  const KNOWN_COMMANDS = [
    'set', 'get', 'list', 'create', 'delete', 'remove', 'reset',
    'hide', 'show', 'clone', 'look', 'examine', 'inspect', 'x', 'ex',
    'help', 'save', 'load', 'undo', 'redo', 'count', 'move', 'make',
    'clear', 'repeat', ':repeat', ':r', 'go', 'goto', 'scene', 'scenes',
    'rooms', 'credits', 'camera', 'capabilities'
  ];

  function fuzzyCorrectCommand(cmd) {
    const parts = cmd.trim().split(/\s+/);
    const corrections = [];

    // Try to correct the first word (command)
    if (parts.length > 0) {
      const first = parts[0].toLowerCase();
      if (!KNOWN_COMMANDS.includes(first)) {
        const match = fuzzyMatch(first, KNOWN_COMMANDS);
        if (match && match !== first) {
          corrections.push(first + ' → ' + match);
          parts[0] = match;
        }
      }
    }

    // Try to correct object names (if adapter provides object list)
    if (adapter && adapter.getObjectNames && parts.length > 1) {
      const objectNames = adapter.getObjectNames();
      const skipWords = ['to', 'the', 'a', 'an', 'is', 'are', 'color', 'size', 'x', 'y', 'z'];
      for (let i = 1; i < parts.length; i++) {
        const word = parts[i].toLowerCase();
        if (skipWords.includes(word)) continue;
        if (!objectNames.map(n => n.toLowerCase()).includes(word)) {
          const match = fuzzyMatch(word, objectNames);
          if (match && match.toLowerCase() !== word) {
            corrections.push(word + ' → ' + match);
            parts[i] = match;
          }
        }
      }
    }

    return { cmd: parts.join(' '), corrections };
  }

  // ==========================================================================
  // HELPERS
  // ==========================================================================

  function singularize(word) {
    const w = word.toLowerCase();
    if (w.endsWith('ies')) return w.slice(0, -3) + 'y';
    if (w.endsWith('es') && !w.endsWith('ses')) return w.slice(0, -2);
    if (w.endsWith('s') && !w.endsWith('ss')) return w.slice(0, -1);
    return w;
  }

  function parseColor(str) {
    const colorMap = {
      red: 0xff0000, green: 0x00ff00, blue: 0x0000ff,
      yellow: 0xffff00, cyan: 0x00ffff, magenta: 0xff00ff,
      white: 0xffffff, black: 0x000000, orange: 0xff8800,
      purple: 0x8800ff, pink: 0xff88ff, gray: 0x888888,
      grey: 0x888888, gold: 0xffd700, silver: 0xc0c0c0
    };
    const lower = str.toLowerCase();
    if (colorMap[lower] !== undefined) return colorMap[lower];
    if (str.startsWith('#')) return parseInt(str.slice(1), 16);
    if (str.startsWith('0x')) return parseInt(str, 16);
    return null;
  }

  // ==========================================================================
  // VOICE INPUT
  // ==========================================================================

  let recognition = null;
  let isListening = false;

  function initVoice() {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
      return false;
    }
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onresult = function(event) {
      const transcript = event.results[0][0].transcript;
      log('[voice] ' + transcript, 'dim');
      execCommand(transcript);
    };

    recognition.onend = function() {
      isListening = false;
      const btn = document.getElementById('rosh-voice');
      if (btn) btn.classList.remove('listening');
    };

    recognition.onerror = function(event) {
      log('Voice error: ' + event.error, 'err');
      isListening = false;
      const btn = document.getElementById('rosh-voice');
      if (btn) btn.classList.remove('listening');
    };

    return true;
  }

  function toggleVoice() {
    if (!recognition && !initVoice()) {
      log('Voice input not supported in this browser', 'err');
      return;
    }
    if (isListening) {
      recognition.stop();
    } else {
      recognition.start();
      isListening = true;
      const btn = document.getElementById('rosh-voice');
      if (btn) btn.classList.add('listening');
      log('Listening...', 'dim');
    }
  }

  // ==========================================================================
  // COMMAND EXECUTION
  // ==========================================================================

  function execCommand(cmd, isUserCommand = true) {
    if (!adapter) {
      log('No adapter configured', 'err');
      return;
    }

    // Increment undo group for each user command
    if (isUserCommand) undoGroup++;

    // Apply fuzzy matching
    const fuzzyResult = fuzzyCorrectCommand(cmd);
    const originalCmd = cmd;
    cmd = fuzzyResult.cmd;
    if (fuzzyResult.corrections.length > 0) {
      log('[corrected: ' + fuzzyResult.corrections.join(', ') + ']', 'dim');
    }
    log('> ' + cmd, 'cmd');

    // Normalize British spellings
    cmd = cmd.replace(/colour/gi, 'color').replace(/centre/gi, 'center');

    // Resolve 'it' and 'this' to current object
    if (currentObjectName && /\b(it|this)\b/i.test(cmd)) {
      cmd = cmd.replace(/\b(it|this)\b/gi, currentObjectName);
      log('[resolved: it/this → ' + currentObjectName + ']', 'dim');
    }

    // Track last substantive command for :repeat
    const nonSubstantive = /^(undo|redo|help|:repeat|\?|history)/i;
    if (isUserCommand && !nonSubstantive.test(cmd.trim())) {
      lastUserCommand = originalCmd;
    }

    const parts = cmd.trim().toLowerCase().split(/\s+/);

    try {
      // Handle confirmation for pending operations
      if ((parts[0] === 'go' || parts[0] === 'confirm' || parts[0] === 'yes') && pendingOp) {
        pendingOp.execute();
        pendingOp = null;
        return;
      }

      // Cancel pending op on other commands
      if (pendingOp && !['go', 'confirm', 'yes'].includes(parts[0])) {
        log('Cancelled pending operation', 'dim');
        pendingOp = null;
      }

      // Route commands
      switch (parts[0]) {
        case 'help':
        case '?':
          showHelp(parts.slice(1));
          break;

        case 'clear':
          clearOutput();
          break;

        case 'list':
        case 'ls':
        case 'objects':
          listObjects(parts.slice(1));
          break;

        case 'scenes':
        case 'rooms':
          listScenes();
          break;

        case 'go':
        case 'goto':
        case 'scene':
          if (parts[1]) {
            gotoScene(parts.slice(1).join(' '));
          } else {
            log('Usage: go <scene>', 'err');
          }
          break;

        case 'create':
        case 'make':
          handleCreate(cmd, parts.slice(1));
          break;

        case 'delete':
        case 'remove':
          handleDelete(parts.slice(1));
          break;

        case 'clone':
          handleClone(parts.slice(1));
          break;

        case 'set':
          handleSet(cmd, parts.slice(1));
          break;

        case 'get':
          handleGet(parts.slice(1));
          break;

        case 'hide':
          handleHide(parts.slice(1));
          break;

        case 'show':
        case 'unhide':
          handleShow(parts.slice(1));
          break;

        case 'move':
          handleMove(cmd, parts.slice(1));
          break;

        case 'look':
        case 'examine':
        case 'inspect':
        case 'x':
        case 'ex':
          handleLook(parts.slice(1));
          break;

        case 'undo':
          const undoCount = parseInt(parts[1]) || 1;
          performUndo(undoCount);
          break;

        case 'redo':
          const redoCount = parseInt(parts[1]) || 1;
          performRedo(redoCount);
          break;

        case ':repeat':
        case ':r':
        case 'repeat':
          if (lastUserCommand) {
            log('[repeating: ' + lastUserCommand + ']', 'dim');
            execCommand(lastUserCommand, false);
          } else {
            log('No command to repeat', 'err');
          }
          break;

        case 'save':
          if (adapter.saveGame) {
            const slot = parts[1] || 'default';
            adapter.saveGame(slot);
            log('Game saved to slot: ' + slot, 'ok');
          }
          break;

        case 'load':
          if (adapter.loadGame) {
            const slot = parts[1] || 'default';
            if (adapter.loadGame(slot)) {
              log('Game loaded from slot: ' + slot, 'ok');
            } else {
              log('No save found in slot: ' + slot, 'err');
            }
          }
          break;

        case 'count':
          if (adapter.countObjects) {
            const typeName = parts[1] ? singularize(parts[1]) : null;
            const count = adapter.countObjects(typeName);
            if (typeName) {
              log(typeName + ': ' + count, 'ok');
            } else {
              log('Total objects: ' + count, 'ok');
            }
          }
          break;

        case 'credits':
          log('Rosh Runtime v0.1.0', 'cyan');
          log('https://rosh.io', 'dim');
          break;

        // ====================================================================
        // PHYSICS COMMANDS (ThreeJS-first)
        // ====================================================================

        case 'gravity':
          if (adapter.enableGravity) {
            const arg = parts[1]?.toLowerCase();
            if (arg === 'off' || arg === 'false' || arg === '0') {
              adapter.disableGravity();
              log('Gravity disabled', 'ok');
            } else if (arg === 'on' || arg === 'true' || arg === '1' || !arg) {
              const strength = parts[2] ? parseFloat(parts[2]) : undefined;
              const result = adapter.enableGravity(strength);
              log('Gravity enabled (strength: ' + result.gravity + ')', 'ok');
            } else {
              // Assume it's a number for strength
              const strength = parseFloat(arg);
              if (!isNaN(strength)) {
                adapter.enableGravity(strength);
                log('Gravity enabled (strength: ' + strength + ')', 'ok');
              } else {
                log('Usage: gravity [on|off|<strength>]', 'dim');
              }
            }
          } else {
            log('Gravity not supported by this adapter', 'err');
          }
          break;

        case 'ground':
          if (adapter.setGroundLevel) {
            const level = parts[1] ? parseFloat(parts[1]) : 0;
            adapter.setGroundLevel(level);
            log('Ground level set to: ' + level, 'ok');
          }
          break;

        case 'clickmove':
        case 'click-move':
        case 'clicktomove':
          if (adapter.enableClickToMove) {
            const arg = parts[1]?.toLowerCase();
            if (arg === 'off' || arg === 'false' || arg === '0') {
              adapter.disableClickToMove();
              log('Click-to-move disabled', 'ok');
            } else {
              // arg could be 'on' or a player name
              const playerName = (arg === 'on' || arg === 'true' || arg === '1') ? parts[2] : arg;
              const result = adapter.enableClickToMove(playerName);
              if (playerName) {
                log('Click-to-move enabled for: ' + playerName, 'ok');
              } else {
                log('Click-to-move enabled (no player set - use "player <name>")', 'ok');
              }
            }
          } else {
            log('Click-to-move not supported by this adapter', 'err');
          }
          break;

        case 'player':
          if (adapter.setPlayer) {
            const name = parts[1];
            if (name) {
              adapter.setPlayer(name);
              // Also enable keyboard control for the player
              if (adapter.enablePlayerKeyboard) {
                adapter.enablePlayerKeyboard(name);
                log('Player set to: ' + name + ' (arrow keys to move)', 'ok');
              } else {
                log('Player set to: ' + name, 'ok');
              }
            } else {
              log('Usage: player <object-name>', 'dim');
            }
          }
          break;

        case 'keys':
        case 'keyboard':
          if (adapter.enablePlayerKeyboard) {
            const arg = parts[1]?.toLowerCase();
            if (arg === 'off' || arg === 'false' || arg === '0') {
              adapter.disablePlayerKeyboard();
              log('Keyboard control disabled', 'ok');
            } else {
              const playerName = (arg === 'on' || arg === 'true' || arg === '1') ? parts[2] : arg;
              adapter.enablePlayerKeyboard(playerName);
              log('Keyboard control enabled (arrow keys)', 'ok');
            }
          }
          break;

        case 'speed':
        case 'movespeed':
          if (adapter.setMoveSpeed) {
            const speed = parts[1] ? parseFloat(parts[1]) : 5;
            adapter.setMoveSpeed(speed);
            log('Move speed set to: ' + speed, 'ok');
          }
          break;

        default:
          // Try adapter's custom command handler
          if (adapter.handleCustomCommand) {
            const handled = adapter.handleCustomCommand(cmd, parts);
            if (!handled) {
              log('Unknown command: ' + parts[0], 'err');
              log('Type "help" for available commands', 'dim');
            }
          } else {
            log('Unknown command: ' + parts[0], 'err');
          }
      }
    } catch (err) {
      log('Error: ' + (err.message || err), 'err');
      console.error('Rosh command error:', err);
    }
  }

  // ==========================================================================
  // COMMAND HANDLERS
  // ==========================================================================

  function showHelp(args) {
    if (args.length === 0) {
      log('=== Rosh Console Commands ===', 'cyan');
      log('create <type>     - Create an object', 'ok');
      log('delete <name>     - Delete an object', 'ok');
      log('clone <name>      - Clone an object', 'ok');
      log('set <obj> <prop> to <val> - Set property', 'ok');
      log('get <obj>         - Select/examine object', 'ok');
      log('list [type]       - List objects', 'ok');
      log('hide/show <obj>   - Toggle visibility', 'ok');
      log('move <obj> <dir> <amt> - Move object', 'ok');
      log('go <scene>        - Go to scene', 'ok');
      log('scenes            - List scenes', 'ok');
      log('undo/redo         - Undo/redo last action', 'ok');
      log(':repeat           - Repeat last command', 'ok');
      log('save/load [slot]  - Save/load game', 'ok');
      log('clear             - Clear console', 'ok');
      log('--- Physics (ThreeJS) ---', 'cyan');
      log('gravity [on|off]  - Toggle gravity', 'ok');
      log('ground <level>    - Set ground Y level', 'ok');
      log('clickmove [name]  - Enable click-to-move', 'ok');
      log('player <name>     - Set player object', 'ok');
      log('speed <value>     - Set move speed', 'ok');
      log('', '');
      log('Type "help <command>" for details', 'dim');
    } else {
      const topic = args[0].toLowerCase();
      // Could expand with detailed help per command
      log('Help for: ' + topic, 'cyan');
      log('(Detailed help not yet implemented)', 'dim');
    }
  }

  function listObjects(args) {
    if (!adapter.getObjects) return;

    const objects = adapter.getObjects();
    const typeName = args[0] ? singularize(args[0]) : null;

    // Filter by visibility (only show objects in current scene)
    let filtered = objects.filter(o => o.visible !== false);

    // Filter by type if specified
    if (typeName) {
      filtered = filtered.filter(o =>
        o.type === typeName ||
        o.name === typeName ||
        o.name.startsWith(typeName + '-')
      );
    }

    if (filtered.length === 0) {
      log(typeName ? 'No ' + typeName + ' objects found' : 'No objects', 'dim');
      return;
    }

    log('Objects' + (typeName ? ' (' + typeName + ')' : '') + ':', 'cyan');
    for (const obj of filtered) {
      const info = obj.type ? obj.name + ' [' + obj.type + ']' : obj.name;
      log('  ' + info, 'ok');
    }
    log('Total: ' + filtered.length, 'dim');
  }

  function listScenes() {
    if (!adapter.getScenes) {
      log('Scenes not supported', 'err');
      return;
    }
    const scenes = adapter.getScenes();
    const current = adapter.getCurrentScene ? adapter.getCurrentScene() : null;

    if (scenes.length === 0) {
      log('No scenes defined', 'dim');
      return;
    }

    log('Scenes:', 'cyan');
    for (const s of scenes) {
      const marker = (s === current) ? ' (current)' : '';
      log('  ' + s + marker, 'ok');
    }
  }

  function gotoScene(sceneName) {
    if (!adapter.gotoScene) {
      log('Scene navigation not supported', 'err');
      return;
    }
    const result = adapter.gotoScene(sceneName);
    if (result.success) {
      log('Now in: ' + result.scene, 'ok');
    } else {
      log(result.error || 'Scene not found: ' + sceneName, 'err');
    }
  }

  function handleCreate(cmd, args) {
    if (!adapter.createObject) return;

    // Check for bulk create: create N type
    const bulkMatch = cmd.match(/^create\s+(\d+)\s+(.+)$/i);
    if (bulkMatch) {
      const count = parseInt(bulkMatch[1], 10);
      const typeAndMods = bulkMatch[2].trim().split(/\s+/);
      const typeName = singularize(typeAndMods[typeAndMods.length - 1]);
      const modifiers = typeAndMods.slice(0, -1);

      if (count >= 10) {
        log('Creating ' + count + ' ' + typeName + '(s)...', 'dim');
      }

      bulkCreateMode = count >= 10;
      bulkCreateCount = 0;

      for (let i = 0; i < count; i++) {
        const result = adapter.createObject(typeName, null, { modifiers });
        if (result.success) {
          if (!bulkCreateMode || bulkCreateCount < BULK_LOG_LIMIT) {
            log('Created ' + result.name, 'ok');
          }
          bulkCreateCount++;
          // Set up undo
          const name = result.name;
          pushUndo('create ' + name,
            () => adapter.deleteObject(name),
            () => adapter.createObject(typeName, name, { modifiers })
          );
        }
      }

      if (bulkCreateMode && count > BULK_LOG_LIMIT) {
        log('  ... and ' + (count - BULK_LOG_LIMIT) + ' more', 'dim');
      }
      log('Created ' + count + ' ' + typeName + '(s)', 'ok');
      bulkCreateMode = false;
      return;
    }

    // Single create
    const typeName = singularize(args[args.length - 1] || 'cube');
    const modifiers = args.slice(0, -1);

    const result = adapter.createObject(typeName, null, { modifiers });
    if (result.success) {
      log('Created ' + result.name, 'ok');
      currentObject = result.object;
      currentObjectName = result.name;

      pushUndo('create ' + result.name,
        () => adapter.deleteObject(result.name),
        () => adapter.createObject(typeName, result.name, { modifiers })
      );
    } else {
      log(result.error || 'Failed to create ' + typeName, 'err');
    }
  }

  function handleDelete(args) {
    if (!adapter.deleteObject) return;
    const name = args.join(' ');
    if (!name) {
      log('Usage: delete <name>', 'err');
      return;
    }

    // Get object state for undo
    const obj = adapter.getObject ? adapter.getObject(name) : null;

    const result = adapter.deleteObject(name);
    if (result.success) {
      log('Deleted ' + name, 'ok');
      if (currentObjectName === name) {
        currentObject = null;
        currentObjectName = null;
      }

      if (obj) {
        pushUndo('delete ' + name,
          () => adapter.restoreObject(name, obj),
          () => adapter.deleteObject(name)
        );
      }
    } else {
      log(result.error || 'Object not found: ' + name, 'err');
    }
  }

  function handleClone(args) {
    if (!adapter.cloneObject) return;
    const name = args[0];
    if (!name) {
      log('Usage: clone <name>', 'err');
      return;
    }

    const result = adapter.cloneObject(name);
    if (result.success) {
      log('Cloned ' + name + ' → ' + result.name, 'ok');
      currentObject = result.object;
      currentObjectName = result.name;

      pushUndo('clone ' + name,
        () => adapter.deleteObject(result.name),
        () => adapter.cloneObject(name)
      );
    } else {
      log(result.error || 'Failed to clone ' + name, 'err');
    }
  }

  function handleSet(cmd, args) {
    if (!adapter.setProperty) return;

    // Parse: set <obj> <prop> [to] <value> - "to" is optional
    const match = cmd.match(/^set\s+(\S+)\s+(\S+)\s+(?:to\s+)?(.+)$/i);
    if (!match) {
      log('Usage: set <object> <property> [to] <value>', 'err');
      return;
    }

    const [, objName, prop, value] = match;

    // Get old value for undo
    const oldValue = adapter.getProperty ? adapter.getProperty(objName, prop) : null;

    const result = adapter.setProperty(objName, prop, value);
    if (result.success) {
      log('Set ' + objName + '.' + prop + ' = ' + value, 'ok');

      pushUndo('set ' + objName + '.' + prop,
        () => adapter.setProperty(objName, prop, oldValue),
        () => adapter.setProperty(objName, prop, value)
      );
    } else {
      log(result.error || 'Failed to set property', 'err');
    }
  }

  function handleGet(args) {
    if (!adapter.getObject) return;
    const name = args.join(' ');
    if (!name) {
      log('Usage: get <name>', 'err');
      return;
    }

    // Check for type search: get all spheres, get blue cube
    if (args[0] === 'all' && args[1]) {
      handleGetAll(args.slice(1));
      return;
    }

    // Deep search with modifiers
    if (adapter.deepSearch) {
      const result = adapter.deepSearch(args);
      if (result.success) {
        if (result.objects.length === 1) {
          currentObject = result.objects[0].object;
          currentObjectName = result.objects[0].name;
          log('Selected: ' + currentObjectName, 'ok');
        } else if (result.objects.length > 1) {
          currentSelection = result.objects;
          log('Found ' + result.objects.length + ' matches:', 'ok');
          for (const o of result.objects.slice(0, 5)) {
            log('  ' + o.name, 'dim');
          }
          if (result.objects.length > 5) {
            log('  ... and ' + (result.objects.length - 5) + ' more', 'dim');
          }
        } else {
          log('No matches found', 'err');
        }
        return;
      }
    }

    // Simple name lookup
    const obj = adapter.getObject(name);
    if (obj) {
      currentObject = obj.object;
      currentObjectName = obj.name;
      log('Selected: ' + currentObjectName, 'ok');
    } else {
      log('Object not found: ' + name, 'err');
    }
  }

  function handleGetAll(args) {
    if (!adapter.getObjectsByType) return;
    const typeName = singularize(args.join(' '));
    const objects = adapter.getObjectsByType(typeName);

    if (objects.length === 0) {
      log('No ' + typeName + ' objects found', 'err');
      return;
    }

    currentSelection = objects;
    currentSelectionType = typeName;
    log('Selected ' + objects.length + ' ' + typeName + '(s)', 'ok');
  }

  function handleHide(args) {
    if (!adapter.setVisible) return;
    const names = args.length ? args : (currentObjectName ? [currentObjectName] : []);

    if (names.length === 0) {
      log('Usage: hide <name> or select an object first', 'err');
      return;
    }

    for (const name of names) {
      const result = adapter.setVisible(name, false);
      if (result.success) {
        log('Hid ' + name, 'ok');
        pushUndo('hide ' + name,
          () => adapter.setVisible(name, true),
          () => adapter.setVisible(name, false)
        );
      } else {
        log(result.error || 'Failed to hide ' + name, 'err');
      }
    }
  }

  function handleShow(args) {
    if (!adapter.setVisible) return;
    const names = args.length ? args : (currentObjectName ? [currentObjectName] : []);

    if (names.length === 0) {
      log('Usage: show <name> or select an object first', 'err');
      return;
    }

    for (const name of names) {
      const result = adapter.setVisible(name, true);
      if (result.success) {
        log('Showed ' + name, 'ok');
        pushUndo('show ' + name,
          () => adapter.setVisible(name, false),
          () => adapter.setVisible(name, true)
        );
      } else {
        log(result.error || 'Failed to show ' + name, 'err');
      }
    }
  }

  function handleMove(cmd, args) {
    if (!adapter.moveObject) return;

    // Parse: move <obj> <direction> <amount>
    // or: move <obj> to <x> <y> [z]
    const toMatch = cmd.match(/^move\s+(\S+)\s+to\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s*(-?\d+\.?\d*)?$/i);
    if (toMatch) {
      const [, name, x, y, z] = toMatch;
      const oldPos = adapter.getPosition ? adapter.getPosition(name) : null;

      const result = adapter.moveObject(name, { x: parseFloat(x), y: parseFloat(y), z: z ? parseFloat(z) : undefined });
      if (result.success) {
        log('Moved ' + name + ' to ' + x + ', ' + y + (z ? ', ' + z : ''), 'ok');
        if (oldPos) {
          pushUndo('move ' + name,
            () => adapter.moveObject(name, oldPos),
            () => adapter.moveObject(name, { x: parseFloat(x), y: parseFloat(y), z: z ? parseFloat(z) : undefined })
          );
        }
      }
      return;
    }

    // Relative movement: move <obj> <dir> <amount>
    const relMatch = cmd.match(/^move\s+(\S+)\s+(forward|back|backward|left|right|up|down)\s+(-?\d+\.?\d*)$/i);
    if (relMatch) {
      const [, name, dir, amt] = relMatch;
      const amount = parseFloat(amt);
      const oldPos = adapter.getPosition ? adapter.getPosition(name) : null;

      const result = adapter.moveObjectRelative(name, dir.toLowerCase(), amount);
      if (result.success) {
        log('Moved ' + name + ' ' + dir + ' ' + amt, 'ok');
        if (oldPos) {
          pushUndo('move ' + name + ' ' + dir,
            () => adapter.moveObject(name, oldPos),
            () => adapter.moveObjectRelative(name, dir.toLowerCase(), amount)
          );
        }
      }
      return;
    }

    log('Usage: move <obj> <direction> <amount> OR move <obj> to <x> <y> [z]', 'err');
  }

  function handleLook(args) {
    const name = args.join(' ') || currentObjectName;
    if (!name) {
      log('Usage: look <name> or select an object first', 'err');
      return;
    }

    if (!adapter.getObjectDetails) {
      log('Object inspection not supported', 'err');
      return;
    }

    const details = adapter.getObjectDetails(name);
    if (!details) {
      log('Object not found: ' + name, 'err');
      return;
    }

    log('=== ' + name + ' ===', 'cyan');
    for (const [key, value] of Object.entries(details)) {
      log('  ' + key + ': ' + JSON.stringify(value), 'ok');
    }
  }

  // ==========================================================================
  // PUBLIC API
  // ==========================================================================

  return {
    init: function(adapterObj) {
      adapter = adapterObj;
      createConsoleUI();
      initVoice();
      log('Rosh Console ready. Press ` to toggle.', 'dim');
    },

    exec: execCommand,
    log: log,
    toggleConsole: toggleConsole,
    pushUndo: pushUndo,

    // State accessors
    getCurrentObject: () => ({ object: currentObject, name: currentObjectName }),
    getSelection: () => currentSelection,

    // For adapter use
    setCurrentObject: (obj, name) => {
      currentObject = obj;
      currentObjectName = name;
    }
  };
})();

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = RoshRuntime;
}
