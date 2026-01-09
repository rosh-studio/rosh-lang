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
 * Version: 0.2.9
 * Spec: rosh-console.toml v0.2.5
 */

const ROSH_VERSION = '0.2.9';
const ROSH_BUILD_TIME = '__BUILD_TIME__';  // Replaced by Python at build time

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

  // Project Twin - shared world state
  let twinSocket = null;
  let twinUserId = null;
  let twinWorldId = null;
  let isNetworkCommand = false;  // True when executing a command received from network
  // Always use production WebSocket server for Project Twin
  // Local Python HTTP servers don't support WebSockets, so always connect to rosh.cloud
  const TWIN_SERVER = 'wss://rosh.cloud/ws/world/';

  // Project Twin - broadcast helpers
  function twinBroadcastCreate(name, objType, x, y, z, color, size) {
    if (twinSocket && twinSocket.readyState === WebSocket.OPEN) {
      const msg = {
        type: 'CREATE',
        id: name,
        object_type: objType,
        x: x,
        y: y,
        z: z,
        color: color,
        size: size
      };
      console.log('[Twin SEND]', JSON.stringify(msg));
      twinSocket.send(JSON.stringify(msg));
    }
  }

  function twinBroadcastDelete(name) {
    if (twinSocket && twinSocket.readyState === WebSocket.OPEN) {
      const msg = { type: 'DELETE', id: name };
      console.log('[Twin SEND]', JSON.stringify(msg));
      twinSocket.send(JSON.stringify(msg));
    }
  }

  function twinBroadcastMove(name, x, y, z, rawCommand) {
    if (isNetworkCommand) return;  // Don't re-broadcast received commands
    if (twinSocket && twinSocket.readyState === WebSocket.OPEN) {
      const msg = {
        type: 'MOVE',
        id: name,
        x: x,
        y: y,
        z: z,
        command: rawCommand || null
      };
      console.log('[Twin SEND]', JSON.stringify(msg));
      twinSocket.send(JSON.stringify(msg));
    }
  }

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
      /* Mobile console FAB - visible on touch devices */
      #rosh-console-fab { position: fixed; bottom: 20px; right: 20px; width: 48px; height: 48px;
        background: rgba(0,0,0,0.7); border: 2px solid #0f0; border-radius: 50%;
        color: #0f0; font-family: monospace; font-size: 18px; font-weight: bold;
        cursor: pointer; z-index: 9999; display: none; align-items: center; justify-content: center;
        box-shadow: 0 2px 10px rgba(0,255,0,0.3); transition: all 0.2s; }
      #rosh-console-fab:hover { background: rgba(0,50,0,0.9); transform: scale(1.1); }
      #rosh-console-fab.console-open { bottom: 260px; }
      @media (pointer: coarse) { #rosh-console-fab { display: flex; } }
      @media (max-width: 768px) { #rosh-console-fab { display: flex; } }
    `;
    document.head.appendChild(style);

    // HTML - engine name will be updated when init() is called
    const consoleDiv = document.createElement('div');
    consoleDiv.id = 'rosh-console';
    consoleDiv.innerHTML = `
      <div id="rosh-console-header" style="padding:8px;background:#111;border-bottom:1px solid #0f0">
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

    // Mobile FAB button
    const fab = document.createElement('button');
    fab.id = 'rosh-console-fab';
    fab.innerHTML = '&gt;_';
    fab.title = 'Open Console';
    fab.addEventListener('click', toggleConsole);
    document.body.appendChild(fab);

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

    // Move FAB up when console is open
    const fab = document.getElementById('rosh-console-fab');
    if (fab) fab.classList.toggle('console-open', consoleVisible);

    // Sync with global consoleVisible (for emitter's WASD handler)
    if (typeof window !== 'undefined') {
      window.consoleVisible = consoleVisible;
    }
  }

  // ==========================================================================
  // HEADER UPDATE
  // ==========================================================================

  function updateConsoleHeader(platform) {
    const header = document.getElementById('rosh-console-header');
    if (header) {
      const engineLabel = platform ? ` <span style="color:#0ff">[${platform}]</span>` : '';
      header.innerHTML = `<strong>ROSH CONSOLE</strong>${engineLabel} <small style="color:#888">Press \` to toggle</small>`;
    }
  }

  // ==========================================================================
  // LOGGING
  // ==========================================================================

  function log(msg, cls = '') {
    // Queue messages if console not ready yet (early print statements)
    if (!outputEl) {
      if (!window._roshPendingLogs) window._roshPendingLogs = [];
      window._roshPendingLogs.push({ msg, cls });
      return;
    }
    const div = document.createElement('div');
    div.className = cls;
    div.textContent = msg;
    outputEl.appendChild(div);
    outputEl.scrollTop = outputEl.scrollHeight;
  }

  // Expose log for adapter (click-to-select feedback)
  window.roshLog = log;

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
    'set', 'get', 'list', 'create', 'delete', 'destroy', 'remove', 'reset',
    'hide', 'show', 'clone', 'look', 'examine', 'inspect', 'x', 'ex',
    'help', 'save', 'load', 'undo', 'redo', 'count', 'move', 'make',
    'clear', 'repeat', ':repeat', ':r', 'go', 'goto', 'scene', 'scenes',
    'rooms', 'credits', 'camera', 'capabilities',
    'connect', 'disconnect', 'twin', 'say', 'users', 'who'
  ];

  /**
   * Find objects by fuzzy substring matching
   * Returns array of matching objects (name, object)
   */
  function fuzzyFindObjects(searchName) {
    if (!adapter.getAllObjects) return [];

    const allObjects = adapter.getAllObjects();
    const lowerSearch = searchName.toLowerCase();
    const matches = [];

    for (const obj of allObjects) {
      const objName = obj.name || (obj.userData && obj.userData._name) || '';
      if (!objName || objName.startsWith('_')) continue;  // Skip hidden objects

      const lowerObjName = objName.toLowerCase();

      // Check if search term is contained in object name or vice versa
      if (lowerObjName.includes(lowerSearch) || lowerSearch.includes(lowerObjName)) {
        matches.push({ name: objName, object: obj });
      }
    }

    return matches;
  }

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
    // Skip for CREATE/MAKE commands - don't correct type names to object names
    const isCreateCmd = ['create', 'make'].includes(parts[0]?.toLowerCase());
    if (adapter && adapter.getObjectNames && parts.length > 1 && !isCreateCmd) {
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
    // Words that end in 's' but aren't plural
    const exceptions = ['torus', 'bus', 'plus', 'radius', 'canvas', 'axis', 'lewis', 'chris', 'paris', 'harris', 'morris', 'dennis', 'texas', 'kansas', 'christmas'];
    if (exceptions.includes(w)) return w;
    // Words ending in 'is' are usually not plural (basis, thesis, lewis)
    if (w.endsWith('is')) return w;
    if (w.endsWith('ies')) return w.slice(0, -3) + 'y';
    if (w.endsWith('es') && !w.endsWith('ses')) return w.slice(0, -2);
    if (w.endsWith('s') && !w.endsWith('ss')) return w.slice(0, -1);
    return w;
  }

  function parseColor(str) {
    // Delegate to RoshColors if available
    if (typeof RoshColors !== 'undefined') {
      return RoshColors.parse(str);
    }
    // Fallback for standalone use
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
          handleCreate(cmd, parts.slice(1));
          break;

        case 'make':
          handleMake(cmd, parts.slice(1));
          break;

        case 'delete':
        case 'remove':
        case 'destroy':
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

        case 'select':
        case 'sel':
          if (adapter.selectByName) {
            const name = parts.slice(1).join(' ');
            if (name) {
              const result = adapter.selectByName(name);
              if (result) {
                log('Selected: ' + result, 'ok');
              } else {
                log('Object not found: ' + name, 'err');
              }
            } else {
              log('Usage: select <name> (or just click an object)', 'dim');
            }
          }
          break;

        case 'deselect':
        case 'desel':
          if (adapter.deselect) {
            adapter.deselect();
            log('Deselected', 'dim');
          }
          break;

        case 'edit':
          if (adapter.enableEditMode && adapter.disableEditMode) {
            const arg = parts[1]?.toLowerCase();
            if (arg === 'on' || arg === 'true' || arg === '1') {
              adapter.enableEditMode();
              log('Edit mode ON - click to select objects, use "control" to move them', 'ok');
            } else if (arg === 'off' || arg === 'false' || arg === '0') {
              adapter.disableEditMode();
              log('Edit mode OFF - view only', 'ok');
            } else if (!arg) {
              const isEdit = adapter.isEditMode ? adapter.isEditMode() : false;
              log('Edit mode: ' + (isEdit ? 'ON' : 'OFF'), 'dim');
              log('Usage: edit on | edit off', 'dim');
            } else {
              log('Usage: edit on | edit off', 'err');
            }
          } else {
            log('Edit mode not supported by this adapter', 'err');
          }
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
                log('Click-to-move enabled (no object set - use "control <name>")', 'ok');
              }
            }
          } else {
            log('Click-to-move not supported by this adapter', 'err');
          }
          break;

        case 'control':
        case 'player':  // Alias for backwards compatibility
          if (adapter.setPlayer) {
            let name = parts[1];
            // Use selected object if no name given
            if (!name && adapter.getSelectedObject) {
              name = adapter.getSelectedObject();
              if (name) log('(using selected: ' + name + ')', 'dim');
            }
            if (name) {
              adapter.setPlayer(name);
              // Also enable keyboard control
              if (adapter.enablePlayerKeyboard) {
                adapter.enablePlayerKeyboard(name);
                log('Controlling: ' + name + ' (arrows + ./ to move)', 'ok');
              } else {
                log('Controlling: ' + name, 'ok');
              }
            } else {
              log('Usage: control <name> (or click to select first)', 'dim');
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

        // ====================================================================
        // PROJECT TWIN - SHARED WORLDS
        // ====================================================================

        case 'connect':
        case 'twin':
          {
            const worldId = parts[1] || 'default';
            if (twinSocket && twinSocket.readyState === WebSocket.OPEN) {
              log('Already connected to world: ' + twinWorldId, 'warn');
              log('Use "disconnect" first to leave current world', 'dim');
              break;
            }
            log('Connecting to shared world: ' + worldId + '...', 'cyan');
            try {
              twinSocket = new WebSocket(TWIN_SERVER + worldId);
              twinWorldId = worldId;
              twinSocket.onopen = () => log('WebSocket connected', 'dim');
              twinSocket.onerror = (e) => {
                log('Connection failed - server may be offline', 'err');
                log('You can still work offline. Use "save" to keep your work.', 'dim');
              };
              twinSocket.onclose = () => {
                log('Disconnected from shared world', 'warn');
                twinSocket = null;
                twinUserId = null;
                twinWorldId = null;
              };
              twinSocket.onmessage = (event) => {
                try {
                  const msg = JSON.parse(event.data);
                  // RAW: Log every message before processing
                  console.log('[Twin RAW]', JSON.stringify(msg));
                  if (msg.type === 'CONNECTED') {
                    twinUserId = msg.user_id;
                    log('Connected to "' + worldId + '" as user ' + msg.user_id, 'ok');
                    log('Objects you create will be shared with others!', 'cyan');
                  } else if (msg.type === 'OBJECT_CREATED') {
                    if (msg.by !== twinUserId) {
                      const data = msg.data || {};
                      // Build human-readable command description
                      const sizeWord = data.size ? data.size + ' ' : '';
                      const colorWord = data.color ? data.color + ' ' : '';
                      const typeWord = data.type || 'object';
                      const cmdDesc = 'create a ' + sizeWord + colorWord + typeWord;

                      // Log clearly what was received
                      log('[' + msg.by.slice(0,6) + '] sent: ' + cmdDesc, 'cyan');

                      // Attempt to render
                      if (adapter.createObject) {
                        adapter.createObject(data.type || 'sphere', msg.id, {
                          x: data.x, y: data.y, z: data.z,
                          color: data.color,
                          size: data.size
                        });
                      } else {
                        log('  (cannot render - no adapter)', 'dim');
                      }
                    }
                  } else if (msg.type === 'OBJECT_DELETED') {
                    if (msg.by !== twinUserId) {
                      log('[' + msg.by.slice(0,6) + '] sent: delete ' + msg.id, 'cyan');
                      if (adapter.deleteObject) {
                        adapter.deleteObject(msg.id);
                      }
                    }
                  } else if (msg.type === 'OBJECT_MOVED') {
                    if (msg.by !== twinUserId) {
                      // If raw command provided, execute it locally (each engine interprets in own coords)
                      if (msg.command) {
                        log('[' + msg.by.slice(0,6) + '] sent: ' + msg.command, 'cyan');
                        isNetworkCommand = true;
                        try { execCommand(msg.command, false); } finally { isNetworkCommand = false; }
                      } else {
                        // Fallback to coordinate-based move (legacy)
                        log('[' + msg.by.slice(0,6) + '] sent: move ' + msg.id + ' to (' + msg.x + ', ' + msg.y + ')', 'cyan');
                        if (adapter.moveObject) {
                          adapter.moveObject(msg.id, { x: msg.x, y: msg.y, z: msg.z });
                        }
                      }
                    }
                  } else if (msg.type === 'CHAT') {
                    log('[' + msg.by + ']: ' + msg.message, 'cyan');
                  } else if (msg.type === 'WORLD_STATE') {
                    const objects = msg.objects || {};
                    const count = Object.keys(objects).length;
                    if (count > 0) {
                      log('Loading ' + count + ' shared object(s) from world...', 'dim');
                      for (const [id, data] of Object.entries(objects)) {
                        // Build human-readable description
                        const sizeWord = data.size ? data.size + ' ' : '';
                        const colorWord = data.color ? data.color + ' ' : '';
                        const typeWord = data.type || 'object';
                        log('  - ' + id + ': ' + sizeWord + colorWord + typeWord, 'dim');

                        if (adapter.createObject) {
                          adapter.createObject(data.type || 'sphere', id, {
                            x: data.x, y: data.y, z: data.z,
                            color: data.color,
                            size: data.size
                          });
                        }
                      }
                    } else {
                      log('World is empty - you can create objects!', 'dim');
                    }
                  } else if (msg.type === 'USERS_LIST') {
                    log('=== Users in "' + msg.world_id + '" (' + msg.count + ') ===', 'cyan');
                    for (const user of msg.users) {
                      const youTag = user.is_you ? ' (you)' : '';
                      log('  ' + user.id + youTag, user.is_you ? 'ok' : 'dim');
                    }
                  } else if (msg.type === 'USER_JOINED') {
                    log('[' + msg.user_id + '] joined (' + msg.user_count + ' users)', 'cyan');
                  } else if (msg.type === 'USER_LEFT') {
                    log('[' + msg.user_id + '] left (' + msg.user_count + ' users)', 'dim');
                  }
                } catch (e) {
                  console.error('Twin message error:', e);
                }
              };
            } catch (e) {
              log('Failed to connect: ' + e.message, 'err');
            }
          }
          break;

        case 'disconnect':
          if (twinSocket) {
            twinSocket.close();
            log('Disconnected from shared world: ' + twinWorldId, 'ok');
            twinSocket = null;
            twinUserId = null;
            twinWorldId = null;
          } else {
            log('Not connected to any shared world', 'dim');
          }
          break;

        case 'clearworld':
        case 'resetworld':
          if (!twinSocket || twinSocket.readyState !== WebSocket.OPEN) {
            log('Not connected. Use "connect" first.', 'err');
          } else {
            twinSocket.send(JSON.stringify({ type: 'CLEAR_WORLD' }));
            log('Sent clear world request...', 'dim');
          }
          break;

        case 'say':
          {
            const message = parts.slice(1).join(' ');
            if (!twinSocket || twinSocket.readyState !== WebSocket.OPEN) {
              log('Not connected. Use "connect" first.', 'err');
              break;
            }
            if (!message) {
              log('Usage: say <message>', 'dim');
              break;
            }
            twinSocket.send(JSON.stringify({ type: 'CHAT', message }));
            log('[you]: ' + message, 'ok');
          }
          break;

        case 'users':
        case 'who':
          console.log('[DEBUG] users/who command hit, twinSocket:', twinSocket, 'readyState:', twinSocket?.readyState);
          if (!twinSocket || twinSocket.readyState !== WebSocket.OPEN) {
            log('Not connected. Use "connect" first.', 'err');
          } else {
            console.log('[DEBUG] Sending USERS message');
            twinSocket.send(JSON.stringify({ type: 'USERS' }));
            log('Requesting user list...', 'dim');
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
      log('--- Physics (Three.js) ---', 'cyan');
      log('gravity [on|off]  - Toggle gravity', 'ok');
      log('ground <level>    - Set ground Y level', 'ok');
      log('clickmove [name]  - Enable click-to-move', 'ok');
      log('control <name>    - Control object with keys', 'ok');
      log('speed <value>     - Set move speed', 'ok');
      log('--- Shared Worlds ---', 'cyan');
      log('connect [world]   - Join a shared world', 'ok');
      log('disconnect        - Leave shared world', 'ok');
      log('say <message>     - Chat with other users', 'ok');
      log('', '');
      log('Type "help <command>" for details', 'dim');
    } else {
      const topic = args[0].toLowerCase();
      showDetailedHelp(topic);
    }
  }

  function showDetailedHelp(topic) {
    switch (topic) {
      case 'create':
      case 'clone':
        log('=== create - Create objects ===', 'cyan');
        log('', '');
        log('You can create any object:', 'ok');
        log('  create ball           - Create object "ball"', 'dim');
        log('  create red cube       - Create red cube', 'dim');
        log('  create big blue ball  - With size and color', 'dim');
        log('  create 5 cubes        - Create multiple', 'dim');
        log('  create three balls    - Number words work too', 'dim');
        log('  clone ball            - Clone existing object', 'dim');
        log('', '');
        log('Supported types: cube, sphere, ball, box, cylinder,', 'ok');
        log('  cone, torus, plane, capsule, pyramid, tetrahedron', 'dim');
        log('', '');
        log('Size modifiers: tiny, small, medium, big, large, huge, giant, massive', 'ok');
        log('Color modifiers: red, green, blue, yellow, orange, purple, pink,', 'ok');
        log('  cyan, white, black, gray, brown, gold, silver', 'dim');
        break;

      case 'make':
        log('=== make - Adjust object properties ===', 'cyan');
        log('', '');
        log('Usage:', 'ok');
        log('  make <obj> bigger     - Scale up by 1.5x', 'dim');
        log('  make <obj> smaller    - Scale down by 0.67x', 'dim');
        log('  make <obj> red        - Change color', 'dim');
        log('  make <obj> scale 2    - Set exact scale', 'dim');
        log('  make big red ball     - Create if not exists', 'dim');
        log('', '');
        log('"make" is upsert: sets property if object exists,', 'ok');
        log('creates object if it doesn\'t exist.', 'dim');
        break;

      case 'set':
        log('=== set - Set object properties ===', 'cyan');
        log('', '');
        log('Usage:', 'ok');
        log('  set <obj> <prop> to <value>', 'dim');
        log('  set ball color to red', 'dim');
        log('  set cube x to 100', 'dim');
        log('  set sphere scale to 2', 'dim');
        log('', '');
        log('Common properties: x, y, z, color, scale, visible,', 'ok');
        log('  rotation, opacity, speed, group', 'dim');
        break;

      case 'get':
        log('=== get - Select/examine objects ===', 'cyan');
        log('', '');
        log('Usage:', 'ok');
        log('  get <name>            - Select single object', 'dim');
        log('  get all cubes         - Select all of type', 'dim');
        log('  get all red balls     - With color modifier', 'dim');
        log('  get all where x > 0   - Filter by condition', 'dim');
        log('', '');
        log('After selecting, use "it" or "this" to reference.', 'dim');
        break;

      case 'delete':
      case 'destroy':
      case 'remove':
        log('=== delete - Remove objects ===', 'cyan');
        log('', '');
        log('Usage:', 'ok');
        log('  delete <name>         - Delete single object', 'dim');
        log('  delete all cubes      - Delete all of type', 'dim');
        log('  delete all red balls  - With color modifier', 'dim');
        log('', '');
        log('Bulk deletes require confirmation (type "go" or "yes").', 'dim');
        break;

      case 'move':
        log('=== move - Move objects ===', 'cyan');
        log('', '');
        log('Relative movement:', 'ok');
        log('  move <obj> up 5       - Move up by 5', 'dim');
        log('  move <obj> left 10    - Move left by 10', 'dim');
        log('  move <obj> forward 3  - Move forward by 3', 'dim');
        log('', '');
        log('Absolute position:', 'ok');
        log('  move <obj> to 0 10 0  - Move to x=0, y=10, z=0', 'dim');
        log('', '');
        log('Directions: up, down, left, right, forward, back', 'dim');
        break;

      case 'hide':
      case 'show':
        log('=== hide/show - Toggle visibility ===', 'cyan');
        log('', '');
        log('Usage:', 'ok');
        log('  hide <name>           - Hide single object', 'dim');
        log('  show <name>           - Show single object', 'dim');
        log('  hide all cubes        - Hide all of type', 'dim');
        log('  show all red balls    - Show with modifier', 'dim');
        log('', '');
        log('Bulk operations require confirmation.', 'dim');
        break;

      case 'list':
      case 'ls':
        log('=== list - List objects ===', 'cyan');
        log('', '');
        log('Usage:', 'ok');
        log('  list                  - List all objects', 'dim');
        log('  list cubes            - List objects of type', 'dim');
        log('  list all              - Include hidden objects', 'dim');
        break;

      case 'connect':
      case 'twin':
        log('=== connect - Join shared world ===', 'cyan');
        log('', '');
        log('Usage:', 'ok');
        log('  connect               - Join default world', 'dim');
        log('  connect myworld       - Join named world', 'dim');
        log('  disconnect            - Leave world', 'dim');
        log('  say hello             - Chat with others', 'dim');
        log('  users                 - List connected users', 'dim');
        log('', '');
        log('Objects created/moved are synced to all users.', 'dim');
        break;

      default:
        log('No detailed help for: ' + topic, 'warn');
        log('Type "help" to see all commands.', 'dim');
    }
  }

  function listObjects(args) {
    if (!adapter.getObjects) return;

    const objects = adapter.getObjects();
    const searchTerm = args[0] ? args[0].toLowerCase() : null;

    // Filter by visibility (only show objects in current scene)
    // Also hide objects starting with _ (hidden/internal objects)
    let filtered = objects.filter(o => o.visible !== false && !o.name.startsWith('_'));

    // Filter by type if specified
    if (searchTerm) {
      // Helper to check if object matches a term
      const matchesTerm = (o, term) => {
        const name = (o.name || '').toLowerCase();
        const type = (o.type || '').toLowerCase();
        return name === term ||
               type === term ||
               name.includes(term) ||
               type.includes(term) ||
               name.startsWith(term + '-');
      };

      // First try exact/contains match with original term
      let matches = filtered.filter(o => matchesTerm(o, searchTerm));

      // If no matches, try singularized version
      if (matches.length === 0) {
        const singular = singularize(searchTerm);
        if (singular !== searchTerm) {
          matches = filtered.filter(o => matchesTerm(o, singular));
        }
      }

      filtered = matches;
    }

    if (filtered.length === 0) {
      log(searchTerm ? 'No ' + searchTerm + ' objects found' : 'No objects', 'dim');
      return;
    }

    log('Objects' + (searchTerm ? ' (' + searchTerm + ')' : '') + ':', 'cyan');
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

    // Number words mapping
    const numberWords = { one: 1, two: 2, three: 3, four: 4, five: 5,
                          six: 6, seven: 7, eight: 8, nine: 9, ten: 10 };
    // Articles to filter out
    const articles = ['a', 'an', 'the', 'some', 'my', 'this'];

    // Check for bulk create: create N type (numeric)
    const bulkMatch = cmd.match(/^create\s+(\d+)\s+(.+)$/i);
    // Check for bulk create: create three cubes (number word)
    const wordMatch = cmd.match(/^create\s+(one|two|three|four|five|six|seven|eight|nine|ten)\s+(.+)$/i);

    if (bulkMatch || wordMatch) {
      const match = bulkMatch || wordMatch;
      const count = bulkMatch ? parseInt(match[1], 10) : numberWords[match[1].toLowerCase()];
      // Filter articles from type/modifiers
      const typeAndMods = match[2].trim().split(/\s+/).filter(w => !articles.includes(w.toLowerCase()));
      const typeName = singularize(typeAndMods[typeAndMods.length - 1] || 'cube');
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

    // Single create - filter articles
    const filteredArgs = args.filter(w => !articles.includes(w.toLowerCase()));
    const typeName = singularize(filteredArgs[filteredArgs.length - 1] || 'cube');
    const modifiers = filteredArgs.slice(0, -1);

    const result = adapter.createObject(typeName, null, { modifiers });
    if (result.success) {
      log('✔ Created object: ' + result.name, 'ok');
      currentObject = result.object;
      currentObjectName = result.name;

      // Show original input as description (without the command word)
      const description = cmd.replace(/^(create|make)\s+/i, '');
      log('   Description: "' + description + '"', 'dim');

      // Show interpreted properties as JSON-like object
      const props = [];
      props.push('type: "' + typeName + '"');
      if (result.color && result.color !== 'gray') props.push('color: "' + result.color + '"');
      if (result.size && result.size !== 1) props.push('scale: ' + result.size);
      log('   Interpreted as: { ' + props.join(', ') + ' }', 'dim');

      // Warn if type wasn't recognized
      if (result.knownType === false) {
        const supported = adapter.getSupportedTypes ? adapter.getSupportedTypes() : [];
        log('   ⚠ Unknown type "' + typeName + '" - created as cube', 'err');
        if (supported.length > 0) {
          log('   Supported types: ' + supported.join(', '), 'dim');
        }
      }

      // Broadcast to shared world if connected
      const obj = result.object;
      const x = obj?.position?.x || 0;
      const y = obj?.position?.y || 0;
      const z = obj?.position?.z || 0;
      const color = result.color || null;
      const size = result.size || 1;
      twinBroadcastCreate(result.name, typeName, x, y, z, color, size);

      pushUndo('create ' + result.name,
        () => adapter.deleteObject(result.name),
        () => adapter.createObject(typeName, result.name, { modifiers })
      );
    } else {
      log(result.error || 'Failed to create ' + typeName, 'err');
    }
  }

  function handleMake(cmd, args) {
    // "make" is upsert: set property if object exists, create if not
    // Examples:
    //   make banana scale 4     → set banana's scale to 4 (or create banana, then set)
    //   make banana red         → set banana's color to red (or create red banana)
    //   make big red ball       → create a big red ball (no object named "big")
    //   make banana             → create banana if doesn't exist

    if (args.length === 0) {
      log('Usage: make <object> [property] [value]', 'err');
      return;
    }

    // Get list of existing objects
    const existingNames = adapter.getObjectNames ? adapter.getObjectNames() : [];
    const existingLower = existingNames.map(n => n.toLowerCase());

    // Check if first word matches an existing object
    const firstWord = args[0].toLowerCase();
    const matchIdx = existingLower.findIndex(n => n === firstWord || n.startsWith(firstWord + '-'));

    // Size modifiers
    const SIZE_MODIFIERS = {
      tiny: 0.25, small: 0.5, big: 2, large: 2, huge: 4,
      bigger: 1.5, smaller: 0.67, larger: 1.5
    };
    const COLORS = ['red', 'green', 'blue', 'yellow', 'cyan', 'magenta', 'white', 'black', 'orange', 'purple', 'pink', 'gray', 'grey', 'gold', 'silver'];

    if (matchIdx !== -1) {
      // Object exists - treat as "set" command
      const objName = existingNames[matchIdx];
      const restArgs = args.slice(1);

      if (restArgs.length === 0) {
        // Just "make banana" - select it
        currentObjectName = objName;
        if (adapter.getObject) {
          const obj = adapter.getObject(objName);
          if (obj) currentObject = obj.object;
        }
        log('Selected: ' + objName, 'ok');
        return;
      }

      // Check for size modifier: "make ball big" -> multiply scale
      const firstArg = restArgs[0].toLowerCase();
      if (SIZE_MODIFIERS[firstArg] && restArgs.length === 1) {
        const multiplier = SIZE_MODIFIERS[firstArg];
        const currentScale = adapter.getProperty ? adapter.getProperty(objName, 'scale') : 1;
        const newScale = (currentScale || 1) * multiplier;
        adapter.setProperty(objName, 'scale', newScale);
        log(objName + '.scale = ' + newScale.toFixed(2), 'ok');
        return;
      }

      // Check for color modifier: "make ball red" -> set color
      if (COLORS.includes(firstArg) && restArgs.length === 1) {
        adapter.setProperty(objName, 'color', firstArg);
        log(objName + '.color = ' + firstArg, 'ok');
        return;
      }

      // "make banana scale 4" or other property setting
      // Reconstruct as set command
      const setCmd = 'set ' + objName + ' ' + restArgs.join(' ');
      log('[→ ' + setCmd + ']', 'dim');
      handleSet(setCmd, [objName].concat(restArgs));
    } else {
      // Object doesn't exist - treat as "create" command
      const createCmd = 'create ' + args.join(' ');
      log('[→ ' + createCmd + ']', 'dim');
      handleCreate(createCmd, args);
    }
  }

  function handleDelete(args) {
    if (!adapter.deleteObject) return;
    let name = args.join(' ');

    // Handle bulk delete: delete all [modifiers] <type>
    if (args[0]?.toLowerCase() === 'all' && args.length > 1) {
      handleDeleteAll(args.slice(1));
      return;
    }

    // Handle selection-based deletion: destroy / destroy confirmed
    if (!name || name.toLowerCase() === 'confirmed') {
      const isConfirmed = name.toLowerCase() === 'confirmed';

      // If we have a multi-selection from query, operate on that
      if (currentSelection && currentSelection.length > 0) {
        const count = currentSelection.length;
        if (!isConfirmed) {
          log('⚠ destroy affects ' + count + ' object(s). Use "destroy confirmed" to proceed.', 'warn');
          return;
        }

        // Confirmed: delete all selected objects
        let deleted = 0;
        for (const item of currentSelection) {
          const objName = item.name;
          const result = adapter.deleteObject(objName);
          if (result.success) {
            deleted++;
            twinBroadcastDelete(objName);
          }
        }
        currentSelection = [];
        log('destroyed ' + deleted + ' object(s)', 'ok');
        return;
      }

      // No selection - try using single selected object
      if (adapter.getSelectedObject) {
        name = adapter.getSelectedObject();
        if (name) {
          log('(using selected: ' + name + ')', 'dim');
        }
      }
    }

    if (!name || name.toLowerCase() === 'confirmed') {
      log('Usage: delete <name>, or use "get all where..." then "destroy confirmed"', 'err');
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
      // Deselect if we deleted the selected object
      if (adapter.getSelectedObject && adapter.getSelectedObject() === name && adapter.deselect) {
        adapter.deselect();
      }

      // Broadcast to shared world if connected
      twinBroadcastDelete(name);

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
    // Also support: set <prop> [to] <value> (uses selected object)
    let match = cmd.match(/^set\s+(\S+)\s+(\S+)\s+(?:to\s+)?(.+)$/i);
    let objName, prop, value;

    if (match) {
      [, objName, prop, value] = match;
    } else {
      // Try parsing without object name: set <prop> [to] <value>
      const shortMatch = cmd.match(/^set\s+(\S+)\s+(?:to\s+)?(.+)$/i);
      if (shortMatch && adapter.getSelectedObject) {
        objName = adapter.getSelectedObject();
        if (objName) {
          [, prop, value] = shortMatch;
          log('(using selected: ' + objName + ')', 'dim');
        }
      }
    }

    if (!objName || !prop || !value) {
      log('Usage: set <object> <property> [to] <value>', 'err');
      log('Or click an object first, then: set <property> [to] <value>', 'dim');
      return;
    }

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
      if (result.success && result.objects.length > 0) {
        if (result.objects.length === 1) {
          currentObject = result.objects[0].object;
          currentObjectName = result.objects[0].name;
          log('Selected: ' + currentObjectName, 'ok');
        } else {
          currentSelection = result.objects;
          log('Found ' + result.objects.length + ' matches:', 'ok');
          for (const o of result.objects.slice(0, 5)) {
            log('  ' + o.name, 'dim');
          }
          if (result.objects.length > 5) {
            log('  ... and ' + (result.objects.length - 5) + ' more', 'dim');
          }
        }
        return;
      }
      // Fall through to fuzzy matching if deepSearch found nothing
    }

    // Simple name lookup first
    let obj = adapter.getObject(name);

    // If not found, try fuzzy matching (same as look command)
    if (!obj && adapter.getAllObjects) {
      const matches = fuzzyFindObjects(name);
      if (matches.length === 1) {
        log('[resolved: "' + name + '" -> "' + matches[0].name + '"]', 'dim');
        obj = adapter.getObject(matches[0].name);
      } else if (matches.length > 1) {
        log('Multiple matches for "' + name + '":', 'cyan');
        for (const m of matches.slice(0, 8)) {
          log('  ' + m.name, 'dim');
        }
        if (matches.length > 8) {
          log('  ... and ' + (matches.length - 8) + ' more', 'dim');
        }
        log('Which one did you mean?', 'dim');
        return;
      }
    }

    if (obj) {
      currentObject = obj.object;
      currentObjectName = obj.name;
      log('Selected: ' + currentObjectName, 'ok');
    } else {
      log('No matches found', 'err');
    }
  }

  function handleGetAll(args) {
    if (!adapter.getObjectsByType) return;

    // Check for 'where' clause: get all [type] where <condition>
    const whereIndex = args.findIndex(a => a.toLowerCase() === 'where');

    if (whereIndex !== -1) {
      // Parse: get all [type] where <property> <op> <value>
      const typePart = args.slice(0, whereIndex);
      const conditionPart = args.slice(whereIndex + 1);

      // Get candidates - either by type or all objects
      let candidates;
      if (typePart.length > 0) {
        const typeName = singularize(typePart.join(' '));
        candidates = adapter.getObjectsByType(typeName);
      } else {
        // Get all objects
        candidates = adapter.getAllObjects ? adapter.getAllObjects() : [];
      }

      // Parse condition: <property> <op> <value>
      // Supported: x is above 5, group is enemies, y is below 0
      if (conditionPart.length < 3) {
        log('Usage: get all where <property> is <op> <value>', 'err');
        return;
      }

      const propName = conditionPart[0];
      const opParts = conditionPart.slice(1);

      // Parse operator and value
      let op, valueStr;
      if (opParts[0] === 'is' && opParts.length >= 2) {
        if (opParts[1] === 'above' || opParts[1] === 'greater' || opParts[1] === 'over') {
          op = '>';
          valueStr = opParts.slice(2).join(' ');
        } else if (opParts[1] === 'below' || opParts[1] === 'less' || opParts[1] === 'under') {
          op = '<';
          valueStr = opParts.slice(2).join(' ');
        } else {
          // "is <value>" means equals
          op = '==';
          valueStr = opParts.slice(1).join(' ');
        }
      } else {
        op = '==';
        valueStr = opParts.join(' ');
      }

      // Parse value (number or string)
      let value = parseFloat(valueStr);
      if (isNaN(value)) {
        value = valueStr.replace(/^["']|["']$/g, ''); // Remove quotes
      }

      // Filter candidates
      const matching = candidates.filter(obj => {
        const objData = obj.object || obj;
        let propValue;

        // Check userData first (for properties set via console)
        if (objData.userData && objData.userData[propName] !== undefined) {
          propValue = objData.userData[propName];
        }
        // Special handling for color - check userData.color first, then material
        else if (propName === 'color') {
          if (objData.userData && objData.userData.color) {
            propValue = objData.userData.color;
          } else if (objData.material && objData.material.color) {
            // Convert hex to color name for comparison
            const hexNum = objData.material.color.getHex();
            // Use RoshColors if available for reverse lookup
            if (typeof RoshColors !== 'undefined') {
              propValue = RoshColors.getName(hexNum) || RoshColors.toHexString(hexNum);
            } else {
              propValue = '#' + objData.material.color.getHexString();
            }
          }
        }
        // Then check position/scale/rotation
        else if (propName === 'x' && objData.position) propValue = objData.position.x;
        else if (propName === 'y' && objData.position) propValue = objData.position.y;
        else if (propName === 'z' && objData.position) propValue = objData.position.z;
        else if (propName === 'scale' && objData.scale) propValue = objData.scale.x; // Use x for uniform
        else if (objData[propName] !== undefined) propValue = objData[propName];
        else return false;

        // Apply comparison
        if (op === '>') return propValue > value;
        if (op === '<') return propValue < value;
        if (op === '>=') return propValue >= value;
        if (op === '<=') return propValue <= value;
        if (op === '==') return propValue == value;
        if (op === '!=') return propValue != value;
        return false;
      });

      currentSelection = matching;
      if (matching.length === 0) {
        log('No matches found', 'err');
      } else {
        log('selected ' + matching.length + ' object(s):', 'ok');
        for (const o of matching.slice(0, 5)) {
          log('  ' + o.name, 'dim');
        }
        if (matching.length > 5) {
          log('  ... and ' + (matching.length - 5) + ' more', 'dim');
        }
      }
      return;
    }

    // Original behavior: get all <type>
    const rawTypeName = args.join(' ');
    // Try exact match first, then singularize
    let objects = adapter.getObjectsByType(rawTypeName);
    let typeName = rawTypeName;

    if (objects.length === 0) {
      const singularized = singularize(rawTypeName);
      if (singularized !== rawTypeName) {
        objects = adapter.getObjectsByType(singularized);
        typeName = singularized;
      }
    }

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

    // Handle bulk hide: hide all [modifiers] <type>
    if (args[0]?.toLowerCase() === 'all' && args.length > 1) {
      handleHideAll(args.slice(1));
      return;
    }

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

    // Handle bulk show: show all [modifiers] <type>
    if (args[0]?.toLowerCase() === 'all' && args.length > 1) {
      handleShowAll(args.slice(1));
      return;
    }

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

  // Bulk operations helper: find objects matching type and modifiers
  function findMatchingObjects(args) {
    if (!adapter.getAllObjects) return { objects: [], desc: args.join(' ') };

    const allObjects = adapter.getAllObjects();
    const colors = ['red', 'green', 'blue', 'yellow', 'orange', 'purple', 'pink',
                    'cyan', 'white', 'black', 'gray', 'grey', 'brown', 'gold', 'silver'];
    const sizes = { big: 2, large: 2, huge: 4, small: 0.5, tiny: 0.25 };

    // Parse args into modifiers and type
    let targetColor = null;
    let targetSize = null;
    let targetTypeOriginal = null;

    for (const arg of args) {
      const lower = arg.toLowerCase();
      if (colors.includes(lower)) {
        targetColor = lower;
      } else if (sizes[lower] !== undefined) {
        targetSize = lower;
      } else {
        targetTypeOriginal = lower;  // Keep original, singularize later if needed
      }
    }

    // Filter helper - matches objects with given type (and color/size modifiers)
    const filterWithType = (type) => allObjects.filter(obj => {
      const objType = (obj.userData?.type || obj.name?.split('-')[0] || '').toLowerCase();
      const objColor = (obj.userData?.color || '').toLowerCase();
      const objScale = obj.userData?.scale || obj.scale?.x || 1;

      if (type && objType !== type) return false;
      if (targetColor && objColor !== targetColor) return false;
      if (targetSize) {
        if (targetSize === 'big' || targetSize === 'large' || targetSize === 'huge') {
          if (objScale < 1.5) return false;
        } else if (targetSize === 'small' || targetSize === 'tiny') {
          if (objScale > 0.75) return false;
        }
      }
      return true;
    });

    // Try exact type match first
    let matching = filterWithType(targetTypeOriginal);
    let targetType = targetTypeOriginal;

    // If no matches with exact type, try singularized
    if (matching.length === 0 && targetTypeOriginal) {
      const singularized = singularize(targetTypeOriginal);
      if (singularized !== targetTypeOriginal) {
        matching = filterWithType(singularized);
        targetType = singularized;
      }
    }

    // Build description
    const descParts = [];
    if (targetColor) descParts.push(targetColor);
    if (targetSize) descParts.push(targetSize);
    if (targetType) descParts.push(targetType + (matching.length !== 1 ? 's' : ''));
    const desc = descParts.join(' ') || 'objects';

    return { objects: matching, desc };
  }

  function handleDeleteAll(args) {
    const { objects, desc } = findMatchingObjects(args);

    if (objects.length === 0) {
      log('No ' + desc + ' found', 'warn');
      return;
    }

    // Set up pending operation with confirmation
    pendingOp = {
      desc: 'delete ' + objects.length + ' ' + desc,
      execute: () => {
        let deleted = 0;
        for (const obj of objects) {
          const name = obj.userData?._name || obj.name;
          if (name && adapter.deleteObject) {
            const result = adapter.deleteObject(name);
            if (result.success) {
              deleted++;
              twinBroadcastDelete(name);
            }
          }
        }
        log('Deleted ' + deleted + ' ' + desc, 'ok');
      }
    };

    log('⚠ About to delete ' + objects.length + ' ' + desc + '. Type "go" or "yes" to confirm.', 'warn');
  }

  function handleHideAll(args) {
    const { objects, desc } = findMatchingObjects(args);

    if (objects.length === 0) {
      log('No ' + desc + ' found', 'warn');
      return;
    }

    // Set up pending operation with confirmation
    pendingOp = {
      desc: 'hide ' + objects.length + ' ' + desc,
      execute: () => {
        let hidden = 0;
        for (const obj of objects) {
          const name = obj.userData?._name || obj.name;
          if (name && adapter.setVisible) {
            const result = adapter.setVisible(name, false);
            if (result.success) hidden++;
          }
        }
        log('Hid ' + hidden + ' ' + desc, 'ok');
      }
    };

    log('⚠ About to hide ' + objects.length + ' ' + desc + '. Type "go" or "yes" to confirm.', 'warn');
  }

  function handleShowAll(args) {
    const { objects, desc } = findMatchingObjects(args);

    if (objects.length === 0) {
      log('No ' + desc + ' found', 'warn');
      return;
    }

    // Set up pending operation with confirmation
    pendingOp = {
      desc: 'show ' + objects.length + ' ' + desc,
      execute: () => {
        let shown = 0;
        for (const obj of objects) {
          const name = obj.userData?._name || obj.name;
          if (name && adapter.setVisible) {
            const result = adapter.setVisible(name, true);
            if (result.success) shown++;
          }
        }
        log('Showed ' + shown + ' ' + desc, 'ok');
      }
    };

    log('⚠ About to show ' + objects.length + ' ' + desc + '. Type "go" or "yes" to confirm.', 'warn');
  }

  // Fuzzy match object reference (e.g., "red ball" -> "ball-1" with color red)
  function fuzzyMatchObject(objRef) {
    if (!adapter.getAllObjects) return objRef;

    const allObjects = adapter.getAllObjects();
    const refWords = objRef.toLowerCase().split(/\s+/);

    // First try exact match
    for (const obj of allObjects) {
      const name = obj.name || (obj.userData && obj.userData._name) || '';
      if (name.toLowerCase() === objRef.toLowerCase()) return name;
    }

    // Fuzzy match by type and color
    let bestMatch = null;
    let bestScore = 0;

    for (const obj of allObjects) {
      const name = obj.name || (obj.userData && obj.userData._name) || '';
      if (!name || name.startsWith('_')) continue;

      const objType = (obj.userData && obj.userData._type) || '';
      const objColor = (obj.userData && obj.userData.color) || '';
      const nameLower = name.toLowerCase();

      let score = 0;
      for (const word of refWords) {
        if (word === objType.toLowerCase() || word === objType.toLowerCase() + 's') score += 10;
        if (word === objColor.toLowerCase()) score += 5;
        if (nameLower.includes(word)) score += 3;
      }

      if (score > bestScore) {
        bestScore = score;
        bestMatch = name;
      }
    }

    if (bestMatch && bestScore > 0) {
      log('[matched: "' + objRef + '" → "' + bestMatch + '"]', 'dim');
      return bestMatch;
    }

    return objRef;  // Return original if no match
  }

  function handleMove(cmd, args) {
    if (!adapter.moveObject) return;

    // Parse: move <obj_ref> to <x> <y> [z] (obj_ref can be multi-word)
    const toMatch = cmd.match(/^move\s+(.+?)\s+to\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s*(-?\d+\.?\d*)?$/i);
    if (toMatch) {
      const [, objRef, x, y, z] = toMatch;
      const name = fuzzyMatchObject(objRef);
      const oldPos = adapter.getPosition ? adapter.getPosition(name) : null;

      const result = adapter.moveObject(name, { x: parseFloat(x), y: parseFloat(y), z: z ? parseFloat(z) : undefined });
      if (result.success) {
        log('Moved ' + name + ' to ' + x + ', ' + y + (z ? ', ' + z : ''), 'ok');
        // Broadcast move to network with raw command
        twinBroadcastMove(name, parseFloat(x), parseFloat(y), z ? parseFloat(z) : 0, cmd);
        if (oldPos) {
          pushUndo('move ' + name,
            () => adapter.moveObject(name, oldPos),
            () => adapter.moveObject(name, { x: parseFloat(x), y: parseFloat(y), z: z ? parseFloat(z) : undefined })
          );
        }
      }
      return;
    }

    // Relative movement: move <obj_ref> <dir> <amount> (obj_ref can be multi-word)
    const relMatch = cmd.match(/^move\s+(.+?)\s+(forward|back|backward|left|right|up|down)\s+(-?\d+\.?\d*)$/i);
    if (relMatch) {
      const [, objRef, dir, amt] = relMatch;
      const name = fuzzyMatchObject(objRef);
      const amount = parseFloat(amt);
      const oldPos = adapter.getPosition ? adapter.getPosition(name) : null;

      const result = adapter.moveObjectRelative(name, dir.toLowerCase(), amount);
      if (result.success) {
        log('Moved ' + name + ' ' + dir + ' ' + amt, 'ok');
        // Broadcast new position to network with raw command
        const newPos = adapter.getPosition ? adapter.getPosition(name) : null;
        if (newPos) {
          twinBroadcastMove(name, newPos.x, newPos.y, newPos.z || 0, cmd);
        }
        if (oldPos) {
          pushUndo('move ' + name + ' ' + dir,
            () => adapter.moveObject(name, oldPos),
            () => adapter.moveObjectRelative(name, dir.toLowerCase(), amount)
          );
        }
      } else {
        log('Failed to move ' + name + ': ' + (result.error || 'object not found'), 'err');
      }
      return;
    }

    log('Usage: move <obj> <direction> <amount> OR move <obj> to <x> <y> [z]', 'err');
  }

  function handleLook(args) {
    let name = args.join(' ') || currentObjectName;
    // Use selected object if no name given
    if (!name && adapter.getSelectedObject) {
      name = adapter.getSelectedObject();
      if (name) log('(using selected: ' + name + ')', 'dim');
    }
    if (!name) {
      log('Usage: look <name> (or click to select first)', 'err');
      return;
    }

    if (!adapter.getObjectDetails) {
      log('Object inspection not supported', 'err');
      return;
    }

    let details = adapter.getObjectDetails(name);

    // If not found, try fuzzy matching
    if (!details && adapter.getAllObjects) {
      const matches = fuzzyFindObjects(name);

      if (matches.length === 1) {
        log('[resolved: "' + name + '" -> "' + matches[0].name + '"]', 'dim');
        name = matches[0].name;
        details = adapter.getObjectDetails(name);
      } else if (matches.length > 1) {
        // Multiple matches - ask user to clarify
        log('Multiple matches for "' + name + '":', 'cyan');
        for (const m of matches.slice(0, 8)) {
          log('  ' + m.name, 'dim');
        }
        if (matches.length > 8) {
          log('  ... and ' + (matches.length - 8) + ' more', 'dim');
        }
        log('Which one did you mean?', 'dim');
        return;
      } else {
        // No matches - show suggestions
        const allObjects = adapter.getAllObjects();
        const available = allObjects
          .map(obj => obj.name || (obj.userData && obj.userData._name) || '')
          .filter(n => n && !n.startsWith('_'))
          .slice(0, 10);
        log('Object not found: ' + name, 'err');
        if (available.length > 0) {
          log('Available: ' + available.join(', ') + (allObjects.length > 10 ? '...' : ''), 'dim');
        }
        return;
      }
    } else if (!details) {
      log('Object not found: ' + name, 'err');
      return;
    }

    log('=== ' + name + ' ===', 'cyan');
    // Show description first if available (natural language)
    if (details.description) {
      log('  "' + details.description + '"', 'dim');
    }
    for (const [key, value] of Object.entries(details)) {
      if (key === 'description') continue;  // Already shown above
      if (value === null) continue;  // Skip null values
      const formatted = typeof value === 'object' ? JSON.stringify(value) : value;
      log('  ' + key + ': ' + formatted, 'ok');
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
      const platform = adapter && adapter.platform ? adapter.platform : 'unknown';
      updateConsoleHeader(platform);  // Display engine name in header
      log('Rosh v' + ROSH_VERSION + ' | ' + platform + ' | Build ' + ROSH_BUILD_TIME, 'cyan');
      log('Type help for commands. Press ` to toggle console.', 'dim');
      // Flush any pending logs from early print statements
      if (window._roshPendingLogs) {
        window._roshPendingLogs.forEach(item => log(item.msg, item.cls));
        delete window._roshPendingLogs;
      }
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
