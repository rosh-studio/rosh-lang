/**
 * Rosh Core - Base REPL Infrastructure
 *
 * =============================================================================
 * LAYER 1: Pure REPL Shell (of 3 layers)
 * =============================================================================
 *
 * This is the base layer containing:
 *   - Console UI (HTML/CSS rendering)
 *   - Command history (up/down arrows)
 *   - Undo/redo stack management
 *   - Command routing (to subclass implementations)
 *   - Fuzzy spelling correction
 *   - Utility functions (singularize, nextName)
 *
 * NO object manipulation - that's in rosh-3d.js (Layer 2).
 * NO engine-specific code - that's in adapters (Layer 3).
 *
 * =============================================================================
 * KEY DOCUMENTS - READ BEFORE MODIFYING
 * =============================================================================
 * - rosh-dev/proposals/IR-VERSIONING-POLICY.md - Python is source of truth
 * - rosh-dev/proposals/JS-RUNTIME-ARCHITECTURE.md - This three-layer design
 * - src/rosh/cli.py - Python REPL (SOURCE OF TRUTH for features)
 * - src/rosh/runtime/PYTHON-SYNC.md - Feature sync tracking
 *
 * THREE-LAYER ARCHITECTURE:
 *   Layer 1: rosh-core.js (this file) - Base REPL shell
 *   Layer 2: rosh-3d.js - 3D object commands (extends this)
 *   Layer 3: threejs-adapter.js - Engine-specific (implements adapter interface)
 *
 * ⚠️  DO NOT MANUALLY ADD COMMANDS - Build the generator first!
 * See: JS-RUNTIME-ARCHITECTURE.md → "MANDATORY: Before Any New Features"
 * Bug example: `dump` command was missing because of manual sync.
 * =============================================================================
 *
 * @version 0.1.1
 * @implements IR 0.1.1
 */

const ROSH_CORE_VERSION = "0.1.1";
const IMPLEMENTS_IR_VERSION = "0.1.1";

// =============================================================================
// Adapter Interface Definition
// =============================================================================
// Each engine (Three.js, Phaser, Babylon) must implement this interface.
//
// Required methods:
//   getObject(name: string): Object | null
//   getAllObjects(): Object[]
//   createObject(type: string, name: string, props: object): Object
//   deleteObject(obj: Object): void
//   setProperty(obj: Object, prop: string, value: any): void
//   getProperty(obj: Object, prop: string): any
//   getObjectName(obj: Object): string
//   getObjectType(obj: Object): string
//   getObjectPosition(obj: Object): {x, y, z}
//   setObjectPosition(obj: Object, x, y, z): void
//   setObjectVisible(obj: Object, visible: boolean): void
//   setObjectColor(obj: Object, color: number): void
//   getObjectColor(obj: Object): number
//   setObjectScale(obj: Object, scale: number): void
//   getObjectScale(obj: Object): number
// =============================================================================

class RoshCore {
    constructor(adapter, options = {}) {
        this.adapter = adapter;
        this.options = {
            confirmThreshold: 10,  // Confirm for bulk ops >= this
            bulkLogLimit: 10,      // Show first N items in bulk mode
            maxUndoStack: 100,
            ...options
        };

        // State
        this.undoStack = [];
        this.redoStack = [];
        this.undoGroup = 0;
        this.commandHistory = [];
        this.historyIndex = -1;
        this.lastUserCommand = null;
        this.pendingOp = null;
        this.bulkMode = false;
        this.bulkCount = 0;
        this.currentObject = null;
        this.currentObjectName = null;
        this.currentSelection = [];
        this.currentSelectionType = null;

        // Console elements (set by initConsole)
        this.consoleDiv = null;
        this.outputDiv = null;
        this.inputEl = null;

        // Known objects database
        this.knownObjects = {};

        // Sequential naming counters per type
        this.typeCounters = {};

        // Multi-line block support
        this.multiLineBuffer = [];
        this.inBlock = false;
        this.blockContext = null;  // { type: 'create', objType, objName }
    }

    // =========================================================================
    // Initialization
    // =========================================================================

    init() {
        this.initConsole();
        this.initKeyboardShortcuts();
        this.log("Rosh Console v" + ROSH_CORE_VERSION + " ready. Type 'help' for commands.", 'ok');
    }

    nextName(typeName) {
        // Generate sequential name: box-1, box-2, ball-1, etc.
        const key = typeName.toLowerCase();
        if (!this.typeCounters[key]) {
            this.typeCounters[key] = 0;
        }
        this.typeCounters[key]++;
        return key + '-' + this.typeCounters[key];
    }

    initConsole() {
        // Create console CSS
        const style = document.createElement('style');
        style.textContent = `
            #rosh-console {
                position: fixed; bottom: 0; left: 0; width: 100%; height: 250px;
                background: rgba(0,0,0,0.95); color: #0f0;
                font-family: monospace; font-size: 14px;
                border-top: 2px solid #0f0;
                display: none; flex-direction: column; z-index: 10000;
            }
            #rosh-console.visible { display: flex; }
            #rosh-output { flex: 1; overflow-y: auto; padding: 10px; }
            #rosh-output .cmd { color: #ff0; }
            #rosh-output .ok { color: #3f3; }
            #rosh-output .err { color: #f33; }
            #rosh-output .cyan { color: #0ff; }
            #rosh-output .dim { color: #888; }
            #rosh-output .warn { color: #fa0; }
            #rosh-input-line {
                padding: 10px; border-top: 1px solid #0f0;
                display: flex; gap: 8px; align-items: center;
            }
            #rosh-input-line input {
                flex: 1; background: #111; border: 1px solid #0f0;
                color: #0f0; padding: 8px; font-family: inherit;
            }
        `;
        document.head.appendChild(style);

        // Create console HTML
        this.consoleDiv = document.createElement('div');
        this.consoleDiv.id = 'rosh-console';
        this.consoleDiv.innerHTML = `
            <div style="padding:8px;background:#111;border-bottom:1px solid #0f0">
                <strong>ROSH CONSOLE</strong>
                <small style="color:#888">Press \` to toggle</small>
            </div>
            <div id="rosh-output"></div>
            <div id="rosh-input-line">
                <span style="color:#0f0">rosh></span>
                <input type="text" id="rosh-input" placeholder="type command..." autocomplete="off">
            </div>
        `;
        document.body.appendChild(this.consoleDiv);

        this.outputDiv = document.getElementById('rosh-output');
        this.inputEl = document.getElementById('rosh-input');

        // Input handling
        this.inputEl.addEventListener('keydown', (e) => this.handleInput(e));
    }

    initKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Backtick toggles console (key or keyCode for compatibility)
            if (e.key === '`' || e.key === '~' || e.keyCode === 192 || e.code === 'Backquote') {
                e.preventDefault();
                this.toggleConsole();
            }
        });
        console.log('Rosh: Keyboard shortcuts initialized. Press ` to toggle console.');
    }

    toggleConsole() {
        this.consoleDiv.classList.toggle('visible');
        if (this.consoleDiv.classList.contains('visible')) {
            this.inputEl.focus();
        }
    }

    // =========================================================================
    // Logging
    // =========================================================================

    log(msg, cls = '') {
        const div = document.createElement('div');
        div.className = cls;
        div.textContent = msg;
        this.outputDiv.appendChild(div);
        this.outputDiv.scrollTop = this.outputDiv.scrollHeight;
    }

    // =========================================================================
    // Undo/Redo
    // =========================================================================

    pushUndo(description, undoFn, redoFn) {
        if (typeof undoFn !== 'function') return;
        this.undoStack.push({
            description: description || 'change',
            undo: undoFn,
            redo: typeof redoFn === 'function' ? redoFn : null,
            group: this.undoGroup
        });
        if (this.undoStack.length > this.options.maxUndoStack) {
            this.undoStack.shift();
        }
        this.redoStack.length = 0;
    }

    performUndo(count = 1) {
        if (!this.undoStack.length) {
            this.log('Nothing to undo', 'err');
            return;
        }
        for (let step = 0; step < count; step++) {
            if (!this.undoStack.length) break;
            const targetGroup = this.undoStack[this.undoStack.length - 1].group;
            const groupEntries = [];
            while (this.undoStack.length &&
                   this.undoStack[this.undoStack.length - 1].group === targetGroup) {
                groupEntries.push(this.undoStack.pop());
            }
            let undoCount = 0;
            for (const entry of groupEntries) {
                try {
                    entry.undo();
                    undoCount++;
                    if (entry.redo) this.redoStack.push(entry);
                } catch (err) {
                    this.log('Undo failed: ' + (err.message || err), 'err');
                }
            }
            if (undoCount > 1) {
                this.log('Undo: ' + groupEntries[0].description + ' (' + undoCount + ' ops)', 'ok');
            } else if (undoCount === 1) {
                this.log('Undo: ' + groupEntries[0].description, 'ok');
            }
        }
    }

    performRedo(count = 1) {
        if (!this.redoStack.length) {
            this.log('Nothing to redo', 'err');
            return;
        }
        const steps = Math.min(count, this.redoStack.length);
        for (let i = 0; i < steps; i++) {
            const entry = this.redoStack.pop();
            if (!entry || typeof entry.redo !== 'function') continue;
            try {
                entry.redo();
                this.log('Redo: ' + entry.description, 'ok');
                this.undoStack.push(entry);
            } catch (err) {
                this.log('Redo failed: ' + (err.message || err), 'err');
                break;
            }
        }
    }

    // =========================================================================
    // Input Handling
    // =========================================================================

    handleInput(e) {
        if (e.key === 'Enter') {
            const line = this.inputEl.value.trim();
            this.inputEl.value = '';

            if (this.inBlock) {
                // In multi-line mode
                if (line.toLowerCase() === 'end') {
                    this.log('... end', 'dim');
                    this.executeBlock();
                } else {
                    this.multiLineBuffer.push(line);
                    this.log('...   ' + line, 'dim');
                }
                return;
            }

            // Apply fuzzy correction BEFORE block detection
            const corrected = this.fuzzyCorrect(line);
            if (corrected.corrections.length > 0) {
                this.log('[corrected: ' + corrected.corrections.join(', ') + ']', 'dim');
            }
            const correctedLine = corrected.cmd;

            // Check if this starts a block (create object X, define X as, etc.)
            const blockStart = correctedLine.match(/^create\s+(?:object\s+)?(\w+)$/i) ||
                               correctedLine.match(/^define\s+(\w+)\s+as$/i);
            if (blockStart) {
                this.inBlock = true;
                this.multiLineBuffer = [];
                this.blockContext = {
                    type: 'create',
                    objType: blockStart[1],
                    objName: this.nextName(blockStart[1])
                };
                this.log('> ' + correctedLine, 'cmd');
                this.log('... (multiline mode, type "end" to finish)', 'dim');
                return;
            }

            // Normal single-line command
            if (line) {
                this.commandHistory.push(line);
                this.historyIndex = this.commandHistory.length;
                this.execCommand(line);
            }
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            if (this.historyIndex > 0) {
                this.historyIndex--;
                this.inputEl.value = this.commandHistory[this.historyIndex];
            }
        } else if (e.key === 'ArrowDown') {
            e.preventDefault();
            if (this.historyIndex < this.commandHistory.length - 1) {
                this.historyIndex++;
                this.inputEl.value = this.commandHistory[this.historyIndex];
            } else {
                this.historyIndex = this.commandHistory.length;
                this.inputEl.value = '';
            }
        }
    }

    // Override in subclass
    executeBlock() {
        this.log('Block execution not implemented in core', 'err');
        this.inBlock = false;
        this.blockContext = null;
        this.multiLineBuffer = [];
    }

    // =========================================================================
    // Command Execution (Base Routing)
    // =========================================================================

    execCommand(cmd, isUserCommand = true) {
        if (isUserCommand) this.undoGroup++;

        // Apply fuzzy correction
        const corrected = this.fuzzyCorrect(cmd);
        if (corrected.corrections.length > 0) {
            this.log('[corrected: ' + corrected.corrections.join(', ') + ']', 'dim');
        }
        cmd = corrected.cmd;
        this.log('> ' + cmd, 'cmd');

        // Track for :repeat
        const nonSubstantive = /^(undo|redo|help|:repeat|\?|history)/i;
        if (isUserCommand && !nonSubstantive.test(cmd.trim())) {
            this.lastUserCommand = cmd;
        }

        const parts = cmd.trim().toLowerCase().split(/\s+/);

        try {
            // Confirmation handling
            if ((parts[0] === 'go' || parts[0] === 'confirm' || parts[0] === 'yes') && this.pendingOp) {
                this.pendingOp.execute();
                this.pendingOp = null;
                return;
            }
            if (this.pendingOp) {
                this.log('Cancelled pending operation', 'dim');
                this.pendingOp = null;
            }

            // Route commands - core commands handled here, rest delegated
            if (parts[0] === 'help') {
                this.cmdHelp(parts.slice(1));
            } else if (parts[0] === 'version') {
                this.log('Rosh Core v' + ROSH_CORE_VERSION + ' (IR ' + IMPLEMENTS_IR_VERSION + ')', 'cyan');
            } else if (parts[0] === 'undo' || parts[0] === 'oops') {
                const count = parseInt(parts[1]) || 1;
                this.performUndo(count);
            } else if (parts[0] === 'redo') {
                const count = parseInt(parts[1]) || 1;
                this.performRedo(count);
            } else if (parts[0] === ':repeat' || parts[0] === ':r') {
                if (this.lastUserCommand) {
                    this.execCommand(this.lastUserCommand, true);
                } else {
                    this.log('No previous command to repeat', 'err');
                }
            } else if (parts[0] === 'credits') {
                this.cmdCredits();
            } else if (parts[0] === 'meta') {
                this.cmdMeta(parts.slice(1));
            } else {
                // Delegate to subclass for object commands
                this.execObjectCommand(cmd, parts);
            }
        } catch (err) {
            this.log('Error: ' + (err.message || err), 'err');
        }
    }

    // Override in subclass for object manipulation commands
    execObjectCommand(cmd, parts) {
        this.log('Unknown command: ' + parts[0] + ". Type 'help' for commands.", 'err');
    }

    // =========================================================================
    // Core Commands
    // =========================================================================

    cmdHelp(args) {
        if (args.length === 0) {
            this.log('Rosh Console Commands:', 'cyan');
            this.log('  create <type>       - Create an object');
            this.log('  set <obj> <prop> to <value>');
            this.log('  move <obj> to <x> <y> - Set position');
            this.log('  make <obj> bigger   - Relative changes');
            this.log('  get <obj>           - Select object');
            this.log('  list                - List all objects');
            this.log('  look/x <obj>        - Inspect object');
            this.log('  clone <obj>         - Duplicate object');
            this.log('  hide/show <obj>     - Toggle visibility');
            this.log('  delete <obj>        - Remove object');
            this.log('  undo [N]            - Undo last N changes');
            this.log('  redo [N]            - Redo last N undos');
            this.log('  :repeat             - Repeat last command');
            this.log('  credits             - Show credits');
            this.log("Type 'help <cmd>' for details", 'dim');
        } else {
            const topic = args[0];
            // Topic-specific help would go here
            this.log('Help for: ' + topic, 'cyan');
        }
    }

    cmdCredits() {
        this.log('Rosh - One language. Many worlds.', 'cyan');
        this.log('https://rosh.cloud', 'dim');
        this.log('Core v' + ROSH_CORE_VERSION, 'dim');
    }

    cmdMeta(args) {
        // Meta settings: quiet, floor, grid, etc.
        if (args.length === 0) {
            this.log('Meta settings:', 'cyan');
            this.log('  quiet: ' + (this.options.quiet ? 'on' : 'off'), 'dim');
            this.log('Usage: meta <setting> [on|off]', 'dim');
            return;
        }

        const setting = args[0].toLowerCase();
        const value = args[1] ? args[1].toLowerCase() : 'toggle';

        if (setting === 'quiet') {
            if (value === 'on' || value === 'true') {
                this.options.quiet = true;
                this.log('Quiet mode enabled.', 'ok');
            } else if (value === 'off' || value === 'false') {
                this.options.quiet = false;
                this.log('Verbose mode enabled.', 'ok');
            } else {
                this.options.quiet = !this.options.quiet;
                this.log('Quiet mode: ' + (this.options.quiet ? 'on' : 'off'), 'ok');
            }
        } else if (setting === 'list') {
            this.log('Meta settings:', 'cyan');
            this.log('  quiet: ' + (this.options.quiet ? 'on' : 'off'), 'dim');
        } else {
            this.log('Unknown meta setting: ' + setting, 'err');
            this.log('Available: quiet, list', 'dim');
        }
    }

    // =========================================================================
    // Utilities
    // =========================================================================

    singularize(word) {
        if (!word) return word;
        word = word.toLowerCase();
        if (word.endsWith('ies')) return word.slice(0, -3) + 'y';
        if (word.endsWith('es')) return word.slice(0, -2);
        if (word.endsWith('s') && !word.endsWith('ss')) return word.slice(0, -1);
        return word;
    }

    fuzzyCorrect(cmd, isVoice = false) {
        const corrections = [];

        // Voice escapes: ALWAYS process (useful for demos)
        // "dot" → . (joins adjacent words)
        // "underscore" → _ (joins adjacent words)
        // "equals" → = (keeps spaces)
        // "plus" → + (keeps spaces)
        const voiceEscapes = { 'dot': '.', 'underscore': '_', 'equals': '=', 'plus': '+' };
        const parts = cmd.split(/\s+/);
        const escapedParts = [];
        for (let i = 0; i < parts.length; i++) {
            const lower = parts[i].toLowerCase();
            if (voiceEscapes[lower]) {
                const char = voiceEscapes[lower];
                corrections.push(parts[i] + '→' + char);
                if ((char === '.' || char === '_') && escapedParts.length > 0 && i + 1 < parts.length) {
                    // Join with previous and next word
                    const prev = escapedParts.pop();
                    const next = parts[i + 1];
                    escapedParts.push(prev + char + next);
                    i++; // Skip next word
                } else if (char === '=' || char === '+') {
                    escapedParts.push(char);
                } else {
                    escapedParts.push(char);
                }
            } else {
                escapedParts.push(parts[i]);
            }
        }
        cmd = escapedParts.join(' ');

        // Voice-only corrections (typos, spellings)
        // Only apply when isVoice=true to avoid unwanted corrections on keyboard input
        if (isVoice) {
            const typos = {
                'creat': 'create', 'crate': 'create', 'craete': 'create',
                'delte': 'delete', 'deleet': 'delete', 'remov': 'remove',
                'lst': 'list', 'lsit': 'list',
                'hdie': 'hide', 'hsow': 'show', 'shwo': 'show',
                'udno': 'undo', 'redo': 'redo',
                'hlep': 'help', 'hep': 'help',
                'mak': 'make', 'maek': 'make',
                'st': 'set', 'ste': 'set', 'est': 'set',
                'mov': 'move', 'moev': 'move', 'mvoe': 'move',
                'clon': 'clone', 'cloen': 'clone', 'coyp': 'copy',
            };

            // Fix command typos at start of line
            const cmdParts = cmd.split(/\s+/);
            if (cmdParts[0] && typos[cmdParts[0].toLowerCase()]) {
                const fixed = typos[cmdParts[0].toLowerCase()];
                corrections.push(cmdParts[0] + '→' + fixed);
                cmdParts[0] = fixed;
                cmd = cmdParts.join(' ');
            }

            // British spellings
            cmd = cmd.replace(/colour/gi, () => { corrections.push('colour→color'); return 'color'; });
            cmd = cmd.replace(/centre/gi, () => { corrections.push('centre→center'); return 'center'; });
        }

        return { cmd, corrections };
    }
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { RoshCore, ROSH_CORE_VERSION, IMPLEMENTS_IR_VERSION };
}
