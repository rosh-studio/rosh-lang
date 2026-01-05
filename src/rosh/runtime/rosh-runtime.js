/**
 * Rosh Runtime - Backward Compatibility Wrapper
 *
 * =============================================================================
 * DEPRECATED: Use rosh-core.js + rosh-3d.js directly
 * =============================================================================
 *
 * This file exists for backward compatibility with existing code that uses:
 *   const runtime = new RoshRuntime(adapter, options);
 *
 * The actual implementation is now split into three layers:
 *   1. rosh-core.js  - Base REPL infrastructure
 *   2. rosh-3d.js    - 3D object commands (extends core)
 *   3. *-adapter.js  - Engine-specific implementations
 *
 * New code should use:
 *   const runtime = new Rosh3DRuntime(adapter, options);
 *
 * =============================================================================
 * ⚠️  DO NOT MANUALLY ADD COMMANDS TO THIS FILE  ⚠️
 * =============================================================================
 * SOURCE OF TRUTH: Python cli.py
 *
 * This file MUST be GENERATED from Python (src/rosh/emitters/runtime_js.py).
 * Manual sync causes bugs - e.g., `dump` command was missing until 2025-12-21.
 *
 * See: JS-RUNTIME-ARCHITECTURE.md → "MANDATORY: Before Any New Features"
 *
 * Key documents:
 * - rosh-dev/proposals/IR-VERSIONING-POLICY.md
 * - rosh-dev/proposals/JS-RUNTIME-ARCHITECTURE.md
 *
 * @version 0.1.1
 * @implements IR 0.1.1
 * @deprecated Use Rosh3DRuntime from rosh-3d.js instead
 */

const ROSH_RUNTIME_VERSION = "0.1.1";
const IMPLEMENTS_IR_VERSION = "0.1.1";

// =============================================================================
// Backward Compatibility
// =============================================================================
// RoshRuntime is now an alias for Rosh3DRuntime.
// This requires rosh-core.js and rosh-3d.js to be loaded first.
//
// For standalone usage (when layers aren't loaded separately), this file
// includes the full implementation inline below.
// =============================================================================

// Check if layers are already loaded
if (typeof Rosh3DRuntime !== 'undefined') {
    // Layers are loaded - just create alias
    var RoshRuntime = Rosh3DRuntime;
} else if (typeof RoshCore !== 'undefined') {
    // Only core is loaded - this shouldn't happen in normal usage
    console.warn('Rosh: rosh-core.js loaded but rosh-3d.js missing');
    var RoshRuntime = RoshCore;
} else {
    // Standalone mode - include full implementation
    // This is the fallback for when layers aren't loaded separately

    // =============================================================================
    // Inline Core Implementation (for standalone usage)
    // =============================================================================

    // Use var (not class) so RoshRuntime is hoisted to global scope
    var RoshRuntime = class {
        constructor(adapter, options = {}) {
            this.adapter = adapter;
            this.options = {
                confirmThreshold: 10,
                bulkLogLimit: 10,
                maxUndoStack: 100,
                ...options
            };

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
            this.consoleDiv = null;
            this.outputDiv = null;
            this.inputEl = null;
            this.knownObjects = {};
            this.typeCounters = {};
            this.multiLineBuffer = [];
            this.inBlock = false;
            this.blockContext = null;
        }

        init() {
            this.initConsole();
            this.initKeyboardShortcuts();
            this.log("Rosh Console v" + ROSH_RUNTIME_VERSION + " ready. Type 'help' for commands.", 'ok');
        }

        nextName(typeName) {
            const key = typeName.toLowerCase();
            if (!this.typeCounters[key]) this.typeCounters[key] = 0;
            this.typeCounters[key]++;
            return key + '-' + this.typeCounters[key];
        }

        initConsole() {
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
            this.inputEl.addEventListener('keydown', (e) => this.handleInput(e));
        }

        initKeyboardShortcuts() {
            document.addEventListener('keydown', (e) => {
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

        log(msg, cls = '') {
            const div = document.createElement('div');
            div.className = cls;
            div.textContent = msg;
            this.outputDiv.appendChild(div);
            this.outputDiv.scrollTop = this.outputDiv.scrollHeight;
        }

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

        handleInput(e) {
            if (e.key === 'Enter') {
                const line = this.inputEl.value.trim();
                this.inputEl.value = '';

                if (this.inBlock) {
                    if (line.toLowerCase() === 'end') {
                        this.log('... end', 'dim');
                        this.executeBlock();
                    } else {
                        this.multiLineBuffer.push(line);
                        this.log('...   ' + line, 'dim');
                    }
                    return;
                }

                const corrected = this.fuzzyCorrect(line);
                if (corrected.corrections.length > 0) {
                    this.log('[corrected: ' + corrected.corrections.join(', ') + ']', 'dim');
                }
                const correctedLine = corrected.cmd;

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

        executeBlock() {
            const ctx = this.blockContext;
            this.inBlock = false;
            this.blockContext = null;

            if (!ctx) {
                this.log('Block error: no context', 'err');
                return;
            }

            const props = {};
            for (const line of this.multiLineBuffer) {
                const match = line.match(/^(?:set\s+)?(\w+)\s+to\s+(.+)$/i);
                if (match) {
                    const prop = match[1].toLowerCase();
                    const value = this.parseValue(match[2].trim());
                    props[prop] = value;
                }
            }

            const obj = this.adapter.createObject(ctx.objType, ctx.objName, props);
            if (!obj) {
                this.log('Failed to create ' + ctx.objType, 'err');
                return;
            }

            for (const [prop, value] of Object.entries(props)) {
                this.adapter.setProperty(obj, prop, value);
            }

            this.log("Created '" + ctx.objName + "' (" + ctx.objType + ") with " +
                     Object.keys(props).length + " properties", 'ok');

            this.pushUndo(
                "create '" + ctx.objName + "'",
                () => this.adapter.deleteObject(obj),
                () => {
                    const newObj = this.adapter.createObject(ctx.objType, ctx.objName, props);
                    for (const [prop, value] of Object.entries(props)) {
                        this.adapter.setProperty(newObj, prop, value);
                    }
                }
            );

            this.multiLineBuffer = [];
        }

        execCommand(cmd, isUserCommand = true) {
            if (isUserCommand) this.undoGroup++;

            const corrected = this.fuzzyCorrect(cmd);
            if (corrected.corrections.length > 0) {
                this.log('[corrected: ' + corrected.corrections.join(', ') + ']', 'dim');
            }
            cmd = corrected.cmd;
            this.log('> ' + cmd, 'cmd');

            const nonSubstantive = /^(undo|redo|help|:repeat|\?|history)/i;
            if (isUserCommand && !nonSubstantive.test(cmd.trim())) {
                this.lastUserCommand = cmd;
            }

            const parts = cmd.trim().toLowerCase().split(/\s+/);

            try {
                if ((parts[0] === 'go' || parts[0] === 'confirm' || parts[0] === 'yes') && this.pendingOp) {
                    this.pendingOp.execute();
                    this.pendingOp = null;
                    return;
                }
                if (this.pendingOp) {
                    this.log('Cancelled pending operation', 'dim');
                    this.pendingOp = null;
                }

                if (parts[0] === 'help') {
                    this.cmdHelp(parts.slice(1));
                } else if (parts[0] === 'version') {
                    this.log('Rosh Runtime v' + ROSH_RUNTIME_VERSION + ' (IR ' + IMPLEMENTS_IR_VERSION + ')', 'cyan');
                } else if (parts[0] === 'list' || parts[0] === 'ls' || parts[0] === 'objects') {
                    this.cmdList(parts.slice(1));
                } else if (parts[0] === 'create') {
                    this.cmdCreate(cmd, parts.slice(1));
                } else if (parts[0] === 'set') {
                    this.cmdSet(cmd, parts.slice(1));
                } else if (parts[0] === 'get') {
                    this.cmdGet(parts.slice(1));
                } else if (parts[0] === 'delete' || parts[0] === 'remove') {
                    this.cmdDelete(parts.slice(1));
                } else if (parts[0] === 'hide') {
                    this.cmdHide(parts[1]);
                } else if (parts[0] === 'show') {
                    this.cmdShow(parts[1]);
                } else if (parts[0] === 'undo' || parts[0] === 'oops') {
                    const count = parseInt(parts[1]) || 1;
                    this.performUndo(count);
                } else if (parts[0] === 'redo') {
                    const count = parseInt(parts[1]) || 1;
                    this.performRedo(count);
                } else if (parts[0] === 'look' || parts[0] === 'l' || parts[0] === 'examine' ||
                           parts[0] === 'inspect' || parts[0] === 'x' || parts[0] === 'ex' ||
                           parts[0] === 'dump' || parts[0] === 'properties' || parts[0] === 'props') {
                    this.cmdLook(parts.slice(1).join(' '));
                } else if (parts[0] === 'count') {
                    this.cmdCount(parts[1]);
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
                } else if (parts[0] === 'make') {
                    this.cmdMake(cmd, parts.slice(1));
                } else if (parts[0] === 'move') {
                    this.cmdMove(cmd, parts.slice(1));
                } else if (parts[0] === 'clone' || parts[0] === 'copy' || parts[0] === 'duplicate') {
                    this.cmdClone(parts.slice(1).join(' '));
                } else {
                    this.log('Unknown command: ' + parts[0] + ". Type 'help' for commands.", 'err');
                }
            } catch (err) {
                this.log('Error: ' + (err.message || err), 'err');
            }
        }

        // Command implementations (abbreviated for compatibility layer)
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
                this.log('Help for: ' + args[0], 'cyan');
            }
        }

        cmdList(args) {
            const objects = this.adapter.getAllObjects();
            if (objects.length === 0) {
                this.log('No objects in scene', 'dim');
                return;
            }
            this.log('Objects (' + objects.length + '):', 'cyan');
            const limit = Math.min(objects.length, 20);
            for (let i = 0; i < limit; i++) {
                const obj = objects[i];
                const name = this.adapter.getObjectName(obj);
                const type = this.adapter.getObjectType(obj);
                const pos = this.adapter.getObjectPosition(obj);
                this.log('  ' + name + ' (' + type + ') at [' +
                         pos.x.toFixed(0) + ', ' + pos.y.toFixed(0) + ', ' + pos.z.toFixed(0) + ']');
            }
            if (objects.length > 20) {
                this.log('  ... and ' + (objects.length - 20) + ' more', 'dim');
            }
        }

        cmdCreate(fullCmd, args) {
            if (args.length === 0) {
                this.log('Usage: create <type> [name]', 'err');
                return;
            }
            const bulkMatch = fullCmd.match(/^create\s+(\d+)\s+(\w+)$/i);
            if (bulkMatch) {
                const count = parseInt(bulkMatch[1]);
                const typeName = this.singularize(bulkMatch[2]);
                if (count > this.options.confirmThreshold) {
                    this.log('Create ' + count + ' ' + typeName + 's? Type "go" to confirm.', 'cyan');
                    this.pendingOp = { execute: () => this.createBulk(typeName, count) };
                    return;
                }
                this.createBulk(typeName, count);
                return;
            }
            const typeName = this.singularize(args[args.length - 1]);
            const name = this.nextName(typeName);
            const obj = this.adapter.createObject(typeName, name, {});
            if (obj) {
                this.log("Created '" + name + "' (" + typeName + ")", 'ok');
                this.pushUndo("create '" + name + "'",
                    () => this.adapter.deleteObject(obj),
                    () => this.adapter.createObject(typeName, name, {}));
            } else {
                this.log('Failed to create object', 'err');
            }
        }

        createBulk(typeName, count) {
            const created = [];
            for (let i = 0; i < count; i++) {
                const name = this.nextName(typeName);
                const obj = this.adapter.createObject(typeName, name, {});
                if (obj) {
                    const angle = (i / count) * Math.PI * 2;
                    const radius = 50 + count * 2;
                    this.adapter.setProperty(obj, 'x', Math.cos(angle) * radius);
                    this.adapter.setProperty(obj, 'z', Math.sin(angle) * radius);
                    created.push({ obj, name });
                }
            }
            this.log('Created ' + created.length + ' ' + typeName + 's', 'ok');
            this.pushUndo('create ' + count + ' ' + typeName + 's',
                () => created.forEach(c => this.adapter.deleteObject(c.obj)),
                () => this.createBulk(typeName, count));
        }

        cmdSet(fullCmd, args) {
            const knownProps = 'x|y|z|color|scale|visible|rotation|speed|health|text|name|width|height|size|font_size|opacity|alpha';
            const bulkMatch = fullCmd.match(new RegExp('^set\\s+all\\s+(\\w+)\\s+(' + knownProps + ')\\s+to\\s+(.+)$', 'i'));
            if (bulkMatch) {
                const typeName = this.singularize(bulkMatch[1]);
                const prop = bulkMatch[2].toLowerCase();
                const valueStr = bulkMatch[3].trim();
                const newValue = this.parseValue(valueStr);
                const allObjects = this.adapter.getAllObjects();
                const targets = allObjects.filter(obj => {
                    const type = this.adapter.getObjectType(obj);
                    const name = this.adapter.getObjectName(obj);
                    return type === typeName || name.includes(typeName);
                });
                if (targets.length === 0) {
                    this.log('No ' + typeName + ' objects found', 'err');
                    return;
                }
                targets.forEach(obj => this.adapter.setProperty(obj, prop, newValue));
                this.log('Set ' + prop + ' to ' + valueStr + ' on ' + targets.length + ' ' + typeName + 's', 'ok');
                return;
            }
            let objInput, prop, valueStr;
            const explicitMatch = fullCmd.match(new RegExp('^set\\s+(.+)\\s+(' + knownProps + ')\\s+to\\s+(.+)$', 'i'));
            if (explicitMatch) {
                objInput = explicitMatch[1].trim();
                prop = explicitMatch[2].toLowerCase();
                valueStr = explicitMatch[3].trim();
            } else {
                const implicitMatch = fullCmd.match(/^set\s+(.+)\s+to\s+(.+)$/i);
                if (!implicitMatch) {
                    this.log('Usage: set <object> [property] to <value>', 'err');
                    return;
                }
                objInput = implicitMatch[1].trim();
                valueStr = implicitMatch[2].trim();
                prop = this.inferProperty(valueStr);
                if (!prop) {
                    this.log("Can't guess property for '" + valueStr + "'", 'err');
                    this.log('Try: set <object> x|y|z|color|scale to ' + valueStr, 'dim');
                    return;
                }
                this.log('[inferred: ' + prop + ']', 'dim');
            }
            const resolved = this.resolveObject(objInput);
            if (!resolved.obj) {
                this.log('Object not found: ' + objInput, 'err');
                return;
            }
            if (resolved.correction) this.log('[resolved: ' + resolved.correction + ']', 'dim');
            const obj = resolved.obj;
            const objName = resolved.resolvedName;

            // Show normalization echo if natural language was used
            // (input differs from canonical dot notation form)
            const canonicalCmd = 'set ' + objName + '.' + prop + ' to ' + valueStr;
            const inputNormalized = fullCmd.toLowerCase().replace(/\s+/g, ' ').trim();
            const canonicalNormalized = canonicalCmd.toLowerCase().replace(/\s+/g, ' ').trim();
            if (inputNormalized !== canonicalNormalized) {
                this.log('[→ ' + canonicalCmd + ']', 'cyan');
            }

            const oldValue = this.adapter.getProperty(obj, prop);
            const newValue = this.parseValue(valueStr);
            this.adapter.setProperty(obj, prop, newValue);
            this.log(objName + '.' + prop + ' = ' + valueStr, 'ok');
            this.pushUndo("set " + objName + "." + prop,
                () => this.adapter.setProperty(obj, prop, oldValue),
                () => this.adapter.setProperty(obj, prop, newValue));
        }

        cmdMake(fullCmd, args) {
            const modifiers = {
                bigger: { prop: 'scale', factor: 1.5 }, larger: { prop: 'scale', factor: 1.5 },
                smaller: { prop: 'scale', factor: 0.5 }, tiny: { prop: 'scale', factor: 0.25 },
                huge: { prop: 'scale', factor: 3.0 }, faster: { prop: 'speed', factor: 1.5 },
                slower: { prop: 'speed', factor: 0.5 }, brighter: { prop: 'brightness', factor: 1.5 },
                darker: { prop: 'brightness', factor: 0.5 },
            };
            let modifier = null, modKey = null;
            for (const [key, mod] of Object.entries(modifiers)) {
                if (fullCmd.toLowerCase().includes(key)) { modifier = mod; modKey = key; break; }
            }
            if (!modifier) {
                this.log('Usage: make <object(s)> bigger|smaller|faster|slower', 'err');
                return;
            }
            const match = fullCmd.match(new RegExp('make\\s+(.+?)\\s+' + modKey, 'i'));
            if (!match) {
                this.log('Usage: make <object(s)> ' + modKey, 'err');
                return;
            }
            const objSpec = match[1].trim();
            let targets = [];
            const allMatch = objSpec.match(/^all\s+(.+)$/i);
            if (allMatch) {
                const typeName = this.singularize(allMatch[1].trim());
                const allObjects = this.adapter.getAllObjects();
                targets = allObjects.filter(obj => {
                    const type = this.adapter.getObjectType(obj);
                    const name = this.adapter.getObjectName(obj);
                    return type === typeName || name.includes(typeName);
                });
                if (targets.length === 0) {
                    this.log('No ' + typeName + ' objects found', 'err');
                    return;
                }
            } else {
                const resolved = this.resolveObject(objSpec);
                if (!resolved.obj) { this.log('Object not found: ' + objSpec, 'err'); return; }
                if (resolved.correction) this.log('[resolved: ' + resolved.correction + ']', 'dim');
                targets = [resolved.obj];
            }
            const undoOps = [];
            for (const obj of targets) {
                const oldValue = this.adapter.getProperty(obj, modifier.prop) || 1;
                const newValue = oldValue * modifier.factor;
                this.adapter.setProperty(obj, modifier.prop, newValue);
                undoOps.push({ obj, prop: modifier.prop, oldValue, newValue });
            }
            if (targets.length === 1) {
                this.log(this.adapter.getObjectName(targets[0]) + ' is now ' + modKey, 'ok');
            } else {
                this.log('Made ' + targets.length + ' objects ' + modKey, 'ok');
            }
            this.pushUndo('make ' + objSpec + ' ' + modKey,
                () => undoOps.forEach(op => this.adapter.setProperty(op.obj, op.prop, op.oldValue)),
                () => undoOps.forEach(op => this.adapter.setProperty(op.obj, op.prop, op.newValue)));
        }

        cmdMove(fullCmd, args) {
            const match = fullCmd.match(/^move\s+(.+?)\s+to\s+(.+)$/i);
            if (!match) { this.log('Usage: move <object> to <x> <y> [z]', 'err'); return; }
            const objInput = match[1].trim();
            const posStr = match[2].trim();
            const posValues = posStr.split(/[\s,]+/).map(v => this.parseValue(v.trim()));
            const resolved = this.resolveObject(objInput);
            if (!resolved.obj) { this.log('Object not found: ' + objInput, 'err'); return; }
            if (resolved.correction) this.log('[resolved: ' + resolved.correction + ']', 'dim');
            const obj = resolved.obj;
            const objName = resolved.resolvedName;
            const oldX = this.adapter.getProperty(obj, 'x');
            const oldY = this.adapter.getProperty(obj, 'y');
            const oldZ = this.adapter.getProperty(obj, 'z');
            if (posValues[0] !== undefined) this.adapter.setProperty(obj, 'x', posValues[0]);
            if (posValues[1] !== undefined) this.adapter.setProperty(obj, 'y', posValues[1]);
            if (posValues[2] !== undefined) this.adapter.setProperty(obj, 'z', posValues[2]);
            this.log('Moved ' + objName + ' to ' + posStr, 'ok');
            this.pushUndo('move ' + objName,
                () => { this.adapter.setProperty(obj, 'x', oldX); this.adapter.setProperty(obj, 'y', oldY); this.adapter.setProperty(obj, 'z', oldZ); },
                () => { if (posValues[0] !== undefined) this.adapter.setProperty(obj, 'x', posValues[0]); if (posValues[1] !== undefined) this.adapter.setProperty(obj, 'y', posValues[1]); if (posValues[2] !== undefined) this.adapter.setProperty(obj, 'z', posValues[2]); });
        }

        cmdClone(objInput) {
            if (!objInput) { this.log('Usage: clone <object>', 'err'); return; }
            const resolved = this.resolveObject(objInput);
            if (!resolved.obj) { this.log('Object not found: ' + objInput, 'err'); return; }
            if (resolved.correction) this.log('[resolved: ' + resolved.correction + ']', 'dim');
            const srcObj = resolved.obj;
            const srcName = resolved.resolvedName;
            const srcType = this.adapter.getObjectType(srcObj);
            const props = {};
            if (srcObj.userData) {
                for (const [key, val] of Object.entries(srcObj.userData)) {
                    if (!key.startsWith('_')) props[key] = val;
                }
            }
            const pos = this.adapter.getObjectPosition(srcObj);
            const offsetX = typeof pos.x === 'number' ? pos.x + 30 : pos.x;
            const newName = this.nextName(srcType);
            const newObj = this.adapter.createObject(srcType, newName, props);
            this.adapter.setProperty(newObj, 'x', offsetX);
            if (pos.y !== undefined) this.adapter.setProperty(newObj, 'y', pos.y);
            if (pos.z !== undefined) this.adapter.setProperty(newObj, 'z', pos.z);
            const color = this.adapter.getObjectColor(srcObj);
            if (color !== undefined) this.adapter.setProperty(newObj, 'color', color);
            const scale = this.adapter.getObjectScale(srcObj);
            if (scale !== undefined && scale !== 1) this.adapter.setProperty(newObj, 'scale', scale);
            this.log("Cloned '" + srcName + "' -> '" + newName + "'", 'ok');
            this.pushUndo('clone ' + srcName,
                () => this.adapter.deleteObject(newObj),
                () => { const obj = this.adapter.createObject(srcType, newName, props); this.adapter.setProperty(obj, 'x', offsetX); });
        }

        cmdGet(args) {
            if (args.length === 0) { this.log('Usage: get <object>', 'err'); return; }
            const resolved = this.resolveObject(args.join(' '));
            if (resolved.obj) {
                if (resolved.correction) this.log('[resolved: ' + resolved.correction + ']', 'dim');
                this.currentObject = resolved.obj;
                this.currentObjectName = resolved.resolvedName;
                this.log("Selected '" + resolved.resolvedName + "'", 'ok');
            } else {
                this.log('Object not found: ' + args.join(' '), 'err');
            }
        }

        cmdDelete(args) {
            if (args.length === 0) { this.log('Usage: delete <object> or delete all <type>', 'err'); return; }
            const input = args.join(' ');
            const allMatch = input.match(/^all\s+(\w+)$/i);
            if (allMatch) {
                const typeName = this.singularize(allMatch[1]);
                const allObjects = this.adapter.getAllObjects();
                const targets = allObjects.filter(obj => {
                    const type = this.adapter.getObjectType(obj);
                    const name = this.adapter.getObjectName(obj);
                    return type === typeName || name.includes(typeName);
                });
                if (targets.length === 0) { this.log('No ' + typeName + ' objects found', 'err'); return; }
                if (targets.length > this.options.confirmThreshold) {
                    this.log('Delete ' + targets.length + ' ' + typeName + 's? Type "go" to confirm.', 'cyan');
                    this.pendingOp = { execute: () => { targets.forEach(obj => this.adapter.deleteObject(obj)); this.log('Deleted ' + targets.length + ' ' + typeName + 's', 'ok'); } };
                    return;
                }
                targets.forEach(obj => this.adapter.deleteObject(obj));
                this.log('Deleted ' + targets.length + ' ' + typeName + 's', 'ok');
                return;
            }
            const resolved = this.resolveObject(input);
            if (resolved.obj) {
                if (resolved.correction) this.log('[resolved: ' + resolved.correction + ']', 'dim');
                this.adapter.deleteObject(resolved.obj);
                this.log("Deleted '" + resolved.resolvedName + "'", 'ok');
                this.pushUndo("delete '" + resolved.resolvedName + "'", () => {}, () => this.adapter.deleteObject(resolved.obj));
            } else {
                this.log('Object not found: ' + input, 'err');
            }
        }

        cmdHide(name) {
            if (!name) { this.log('Usage: hide <object>', 'err'); return; }
            const resolved = this.resolveObject(name);
            if (resolved.obj) {
                if (resolved.correction) this.log('[resolved: ' + resolved.correction + ']', 'dim');
                this.adapter.setObjectVisible(resolved.obj, false);
                this.log("Hid '" + resolved.resolvedName + "'", 'ok');
                this.pushUndo("hide '" + resolved.resolvedName + "'",
                    () => this.adapter.setObjectVisible(resolved.obj, true),
                    () => this.adapter.setObjectVisible(resolved.obj, false));
            } else {
                this.log('Object not found: ' + name, 'err');
            }
        }

        cmdShow(name) {
            if (!name) { this.log('Usage: show <object>', 'err'); return; }
            const resolved = this.resolveObject(name);
            if (resolved.obj) {
                if (resolved.correction) this.log('[resolved: ' + resolved.correction + ']', 'dim');
                this.adapter.setObjectVisible(resolved.obj, true);
                this.log("Showed '" + resolved.resolvedName + "'", 'ok');
                this.pushUndo("show '" + resolved.resolvedName + "'",
                    () => this.adapter.setObjectVisible(resolved.obj, false),
                    () => this.adapter.setObjectVisible(resolved.obj, true));
            } else {
                this.log('Object not found: ' + name, 'err');
            }
        }

        cmdLook(name) {
            if (!name) { this.log('Usage: look <object>', 'err'); return; }
            const resolved = this.resolveObject(name);
            if (resolved.obj) {
                if (resolved.correction) this.log('[resolved: ' + resolved.correction + ']', 'dim');
                const obj = resolved.obj;
                const objName = resolved.resolvedName;
                const type = this.adapter.getObjectType(obj);
                const pos = this.adapter.getObjectPosition(obj);
                const color = this.adapter.getObjectColor(obj);
                const scale = this.adapter.getObjectScale(obj);
                this.log(objName + ' (' + type + '):', 'cyan');
                const fmtPos = (v) => {
                    if (v && typeof v === 'object' && v.percent !== undefined) return v.percent + '%';
                    if (typeof v === 'number') return v.toFixed(1);
                    return String(v);
                };
                this.log('  position: [' + fmtPos(pos.x) + ', ' + fmtPos(pos.y) + ', ' + fmtPos(pos.z) + ']');
                if (color !== undefined) this.log('  color: #' + color.toString(16).padStart(6, '0'));
                if (scale !== undefined && scale !== 1) this.log('  scale: ' + scale.toFixed(2));
                if (obj.userData) {
                    for (const [key, val] of Object.entries(obj.userData)) {
                        if (!key.startsWith('_')) {
                            const display = typeof val === 'string' ? '"' + val + '"' : val;
                            this.log('  ' + key + ': ' + display);
                        }
                    }
                }
            } else {
                this.log('Object not found: ' + name, 'err');
            }
        }

        cmdCount(typeName) {
            const objects = this.adapter.getAllObjects();
            if (!typeName) { this.log('Total objects: ' + objects.length, 'ok'); return; }
            const singular = this.singularize(typeName);
            let count = 0;
            for (const obj of objects) {
                const type = this.adapter.getObjectType(obj);
                const name = this.adapter.getObjectName(obj);
                if (type === singular || name === singular || name.startsWith(singular + '-')) count++;
            }
            this.log(singular + ': ' + count, 'ok');
        }

        cmdCredits() {
            this.log('Rosh - One language. Many worlds.', 'cyan');
            this.log('https://rosh.cloud', 'dim');
            this.log('Runtime v' + ROSH_RUNTIME_VERSION, 'dim');
        }

        cmdMeta(args) {
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

        // Utilities
        inferProperty(valueStr) {
            const v = valueStr.toLowerCase().trim();
            const colorNames = ['red', 'green', 'blue', 'yellow', 'cyan', 'magenta', 'white', 'black', 'orange', 'purple', 'pink', 'gray', 'grey', 'gold', 'silver', 'brown', 'lime', 'navy', 'teal', 'coral', 'crimson', 'violet', 'indigo', 'maroon', 'olive', 'aqua'];
            if (colorNames.includes(v)) return 'color';
            if (/^#?[0-9a-f]{6}$/i.test(v)) return 'color';
            if (v === 'visible' || v === 'hidden' || v === 'invisible') return 'visible';
            return null;
        }

        singularize(word) {
            if (!word) return word;
            word = word.toLowerCase();
            if (word.endsWith('ies')) return word.slice(0, -3) + 'y';
            if (word.endsWith('es')) return word.slice(0, -2);
            if (word.endsWith('s') && !word.endsWith('ss')) return word.slice(0, -1);
            return word;
        }

        resolveObject(input) {
            if (!input) return { obj: null };
            const original = input.trim();
            const lower = original.toLowerCase();
            const words = lower.split(/\s+/);
            let obj = this.adapter.getObject(original);
            if (obj) return { obj, resolvedName: original, correction: null };
            obj = this.adapter.getObject(lower);
            if (obj) return { obj, resolvedName: lower, correction: null };
            if (words.length > 1) {
                const noSpaces = words.join('');
                obj = this.adapter.getObject(noSpaces);
                if (obj) return { obj, resolvedName: noSpaces, correction: `"${original}" -> "${noSpaces}"` };
                const hyphenated = words.join('-');
                obj = this.adapter.getObject(hyphenated);
                if (obj) return { obj, resolvedName: hyphenated, correction: `"${original}" -> "${hyphenated}"` };
            }
            if (words.length > 1) {
                const typeName = this.singularize(words[words.length - 1]);
                const modifiers = words.slice(0, -1);
                const allObjects = this.adapter.getAllObjects();
                for (const candidate of allObjects) {
                    const name = this.adapter.getObjectName(candidate).toLowerCase();
                    const type = this.adapter.getObjectType(candidate).toLowerCase();
                    if (type === typeName || name.includes(typeName)) {
                        const hasAllModifiers = modifiers.every(mod => name.includes(mod));
                        if (hasAllModifiers) {
                            return { obj: candidate, resolvedName: this.adapter.getObjectName(candidate), correction: `"${original}" -> "${this.adapter.getObjectName(candidate)}"` };
                        }
                    }
                }
            }
            const allObjects = this.adapter.getAllObjects();
            for (const candidate of allObjects) {
                const name = this.adapter.getObjectName(candidate).toLowerCase();
                if (name.includes(lower) || lower.includes(name)) {
                    return { obj: candidate, resolvedName: this.adapter.getObjectName(candidate), correction: `"${original}" -> "${this.adapter.getObjectName(candidate)}"` };
                }
            }
            return { obj: null };
        }

        parseValue(str) {
            str = str.trim();
            const pctMatch = str.match(/^(-?\d+(?:\.\d+)?)\s*%$/);
            if (pctMatch) { const pct = parseFloat(pctMatch[1]); return { percent: pct, normalized: pct / 100 }; }
            if (/^-?\d+(\.\d+)?$/.test(str)) return parseFloat(str);
            if (str === 'true') return true;
            if (str === 'false') return false;
            if (str === 'visible') return true;
            if (str === 'hidden' || str === 'invisible') return false;
            const colors = { red: 0xff0000, green: 0x00ff00, blue: 0x0000ff, yellow: 0xffff00, cyan: 0x00ffff, magenta: 0xff00ff, white: 0xffffff, black: 0x000000, orange: 0xff8800, purple: 0x8800ff, pink: 0xff69b4, gray: 0x888888, grey: 0x888888, gold: 0xffd700, silver: 0xc0c0c0, brown: 0x8b4513, lime: 0x00ff00, navy: 0x000080, teal: 0x008080, coral: 0xff7f50, crimson: 0xdc143c, violet: 0xee82ee, indigo: 0x4b0082, maroon: 0x800000, olive: 0x808000, aqua: 0x00ffff };
            if (colors[str.toLowerCase()]) return colors[str.toLowerCase()];
            if (/^#?[0-9a-f]{6}$/i.test(str)) return parseInt(str.replace('#', ''), 16);
            if ((str.startsWith('"') && str.endsWith('"')) || (str.startsWith("'") && str.endsWith("'"))) return str.slice(1, -1);
            return str;
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
                const typos = { 'creat': 'create', 'crate': 'create', 'craete': 'create', 'delte': 'delete', 'deleet': 'delete', 'remov': 'remove', 'lst': 'list', 'lsit': 'list', 'hdie': 'hide', 'hsow': 'show', 'shwo': 'show', 'udno': 'undo', 'redo': 'redo', 'hlep': 'help', 'hep': 'help', 'mak': 'make', 'maek': 'make', 'st': 'set', 'ste': 'set', 'est': 'set', 'mov': 'move', 'moev': 'move', 'mvoe': 'move', 'clon': 'clone', 'cloen': 'clone', 'coyp': 'copy' };
                const cmdParts = cmd.split(/\s+/);
                if (cmdParts[0] && typos[cmdParts[0].toLowerCase()]) {
                    const fixed = typos[cmdParts[0].toLowerCase()];
                    corrections.push(cmdParts[0] + '→' + fixed);
                    cmdParts[0] = fixed;
                    cmd = cmdParts.join(' ');
                }
                cmd = cmd.replace(/colour/gi, () => { corrections.push('colour→color'); return 'color'; });
                cmd = cmd.replace(/centre/gi, () => { corrections.push('centre→center'); return 'center'; });
            }
            return { cmd, corrections };
        }
    }
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { RoshRuntime, ROSH_RUNTIME_VERSION, IMPLEMENTS_IR_VERSION };
}
