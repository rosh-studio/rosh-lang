/**
 * Rosh 3D - Object Manipulation Layer
 *
 * =============================================================================
 * LAYER 2: 3D Object Commands (of 3 layers)
 * =============================================================================
 *
 * Extends RoshCore with object manipulation commands:
 *   - create, delete, clone
 *   - set, get, make, move
 *   - hide, show, look/inspect/dump
 *   - list, count
 *   - Bulk operations (create N, delete all, set all)
 *
 * Also includes:
 *   - Value parsing (colors, percentages, numbers)
 *   - Object resolution (smart name matching)
 *   - Property inference
 *   - Multi-line block execution
 *
 * Shared by: Three.js, Babylon.js, PlayCanvas, etc.
 * Requires: rosh-core.js loaded first
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
 *   Layer 1: rosh-core.js - Base REPL shell (parent class)
 *   Layer 2: rosh-3d.js (this file) - 3D object commands
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

const ROSH_3D_VERSION = "0.1.1";

class Rosh3DRuntime extends RoshCore {
    constructor(adapter, options = {}) {
        super(adapter, options);
    }

    // =========================================================================
    // Block Execution (Override from Core)
    // =========================================================================

    executeBlock() {
        // Process buffered multi-line block
        const ctx = this.blockContext;
        this.inBlock = false;
        this.blockContext = null;

        if (!ctx) {
            this.log('Block error: no context', 'err');
            return;
        }

        // Parse properties from buffered lines
        const props = {};
        for (const line of this.multiLineBuffer) {
            // Parse "set <prop> to <value>" or just "<prop> to <value>"
            const match = line.match(/^(?:set\s+)?(\w+)\s+to\s+(.+)$/i);
            if (match) {
                const prop = match[1].toLowerCase();
                const value = this.parseValue(match[2].trim());
                props[prop] = value;
            }
        }

        // Create the object
        const obj = this.adapter.createObject(ctx.objType, ctx.objName, props);
        if (!obj) {
            this.log('Failed to create ' + ctx.objType, 'err');
            return;
        }

        // Apply properties that weren't handled by createObject
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

    // =========================================================================
    // Object Command Routing (Override from Core)
    // =========================================================================

    execObjectCommand(cmd, parts) {
        if (parts[0] === 'list' || parts[0] === 'ls' || parts[0] === 'objects') {
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
        } else if (parts[0] === 'look' || parts[0] === 'l' || parts[0] === 'examine' ||
                   parts[0] === 'inspect' || parts[0] === 'x' || parts[0] === 'ex' ||
                   parts[0] === 'dump' || parts[0] === 'properties' || parts[0] === 'props') {
            this.cmdLook(parts.slice(1).join(' '));
        } else if (parts[0] === 'count') {
            this.cmdCount(parts[1]);
        } else if (parts[0] === 'make') {
            this.cmdMake(cmd, parts.slice(1));
        } else if (parts[0] === 'move') {
            this.cmdMove(cmd, parts.slice(1));
        } else if (parts[0] === 'clone' || parts[0] === 'copy' || parts[0] === 'duplicate') {
            this.cmdClone(parts.slice(1).join(' '));
        } else {
            this.log('Unknown command: ' + parts[0] + ". Type 'help' for commands.", 'err');
        }
    }

    // =========================================================================
    // Object Commands
    // =========================================================================

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

        // Check for "create N <type>" pattern
        const bulkMatch = fullCmd.match(/^create\s+(\d+)\s+(\w+)$/i);
        if (bulkMatch) {
            const count = parseInt(bulkMatch[1]);
            const typeName = this.singularize(bulkMatch[2]);

            if (count > this.options.confirmThreshold) {
                this.log('Create ' + count + ' ' + typeName + 's? Type "go" to confirm.', 'cyan');
                this.pendingOp = {
                    execute: () => this.createBulk(typeName, count)
                };
                return;
            }
            this.createBulk(typeName, count);
            return;
        }

        // Parse: create [a] [modifiers] type [name]
        // Filter out articles
        const filtered = args.filter(w => !['a', 'an', 'the'].includes(w.toLowerCase()));

        // Known modifiers
        const sizeModifiers = { tiny: 0.25, small: 0.5, medium: 1.0, big: 2.0, large: 2.0, huge: 4.0 };
        const colorNames = ['red', 'green', 'blue', 'yellow', 'cyan', 'magenta',
                           'white', 'black', 'orange', 'purple', 'pink', 'gray', 'grey', 'gold', 'silver'];

        // Extract modifiers and type
        const props = {};
        let typeName = null;

        for (const word of filtered) {
            const lower = word.toLowerCase();
            if (sizeModifiers[lower] !== undefined) {
                props.scale = sizeModifiers[lower];
            } else if (colorNames.includes(lower)) {
                props.color = lower;
            } else {
                // Last non-modifier word is the type
                typeName = this.singularize(lower);
            }
        }

        if (!typeName) {
            this.log('Usage: create [a] [big/small] [color] <type>', 'err');
            return;
        }

        const name = this.nextName(typeName);
        const obj = this.adapter.createObject(typeName, name, props);

        if (obj) {
            // Apply properties
            if (props.scale) this.adapter.setProperty(obj, 'scale', props.scale);
            if (props.color) this.adapter.setObjectColor(obj, this.colorNameToHex(props.color));

            // Build description
            const desc = [];
            if (props.scale && props.scale !== 1.0) {
                const sizeName = Object.entries(sizeModifiers).find(([k,v]) => v === props.scale)?.[0] || '';
                if (sizeName) desc.push(sizeName);
            }
            if (props.color) desc.push(props.color);
            desc.push(typeName);

            this.log("Created '" + name + "'", 'ok');
            this.log("  " + desc.join(' '), 'dim');
            if (props.color) this.log("  color: " + props.color, 'dim');
            if (props.scale) this.log("  scale: " + props.scale, 'dim');

            this.pushUndo(
                "create '" + name + "'",
                () => this.adapter.deleteObject(obj),
                () => {
                    const newObj = this.adapter.createObject(typeName, name, props);
                    if (props.scale) this.adapter.setProperty(newObj, 'scale', props.scale);
                    if (props.color) this.adapter.setObjectColor(newObj, this.colorNameToHex(props.color));
                }
            );
        } else {
            this.log('Failed to create object', 'err');
        }
    }

    colorNameToHex(name) {
        const colors = {
            red: 0xff0000, green: 0x00ff00, blue: 0x0000ff,
            yellow: 0xffff00, cyan: 0x00ffff, magenta: 0xff00ff,
            white: 0xffffff, black: 0x000000, orange: 0xff8800,
            purple: 0x8800ff, pink: 0xff88ff, gray: 0x888888,
            grey: 0x888888, gold: 0xffd700, silver: 0xc0c0c0
        };
        return colors[name.toLowerCase()] || 0x00ff00;
    }

    createBulk(typeName, count) {
        const created = [];
        for (let i = 0; i < count; i++) {
            const name = this.nextName(typeName);
            const obj = this.adapter.createObject(typeName, name, {});
            if (obj) {
                // Spread them out a bit
                const angle = (i / count) * Math.PI * 2;
                const radius = 50 + count * 2;
                this.adapter.setProperty(obj, 'x', Math.cos(angle) * radius);
                this.adapter.setProperty(obj, 'z', Math.sin(angle) * radius);
                created.push({ obj, name });
            }
        }
        this.log('Created ' + created.length + ' ' + typeName + 's', 'ok');

        this.pushUndo(
            'create ' + count + ' ' + typeName + 's',
            () => created.forEach(c => this.adapter.deleteObject(c.obj)),
            () => this.createBulk(typeName, count)
        );
    }

    cmdSet(fullCmd, args) {
        // Check for "set all <type> <prop> to <value>" pattern
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

        // Try two patterns:
        // 1. "set <obj> <prop> to <value>" (explicit property)
        // 2. "set <obj> to <value>" (infer property from value type)

        let objInput, prop, valueStr;

        // Try explicit property first: "set redbox color to pink"
        const explicitMatch = fullCmd.match(new RegExp('^set\\s+(.+)\\s+(' + knownProps + ')\\s+to\\s+(.+)$', 'i'));
        if (explicitMatch) {
            objInput = explicitMatch[1].trim();
            prop = explicitMatch[2].toLowerCase();
            valueStr = explicitMatch[3].trim();
        } else {
            // Try implicit: "set red box to pink" -> infer color
            const implicitMatch = fullCmd.match(/^set\s+(.+)\s+to\s+(.+)$/i);
            if (!implicitMatch) {
                this.log('Usage: set <object> [property] to <value>', 'err');
                return;
            }
            objInput = implicitMatch[1].trim();
            valueStr = implicitMatch[2].trim();

            // Infer property from value type
            prop = this.inferProperty(valueStr);
            if (!prop) {
                this.log("Can't guess property for '" + valueStr + "'", 'err');
                this.log('Try: set <object> x|y|z|color|scale to ' + valueStr, 'dim');
                return;
            }
            this.log('[inferred: ' + prop + ']', 'dim');
        }

        // Smart object resolution
        const resolved = this.resolveObject(objInput);
        if (!resolved.obj) {
            this.log('Object not found: ' + objInput, 'err');
            return;
        }

        if (resolved.correction) {
            this.log('[resolved: ' + resolved.correction + ']', 'dim');
        }

        const obj = resolved.obj;
        const objName = resolved.resolvedName;
        const oldValue = this.adapter.getProperty(obj, prop);
        const newValue = this.parseValue(valueStr);

        this.adapter.setProperty(obj, prop, newValue);
        this.log(objName + '.' + prop + ' = ' + valueStr, 'ok');

        this.pushUndo(
            "set " + objName + "." + prop,
            () => this.adapter.setProperty(obj, prop, oldValue),
            () => this.adapter.setProperty(obj, prop, newValue)
        );
    }

    cmdMake(fullCmd, args) {
        // Natural language: "make all boxes bigger", "make redbox smaller"
        // Relative modifiers that adjust current values
        const modifiers = {
            bigger:  { prop: 'scale', factor: 1.5 },
            larger:  { prop: 'scale', factor: 1.5 },
            smaller: { prop: 'scale', factor: 0.5 },
            tiny:    { prop: 'scale', factor: 0.25 },
            huge:    { prop: 'scale', factor: 3.0 },
            faster:  { prop: 'speed', factor: 1.5 },
            slower:  { prop: 'speed', factor: 0.5 },
            brighter:{ prop: 'brightness', factor: 1.5 },
            darker:  { prop: 'brightness', factor: 0.5 },
        };

        // Find the modifier in the command
        let modifier = null;
        let modKey = null;
        for (const [key, mod] of Object.entries(modifiers)) {
            if (fullCmd.toLowerCase().includes(key)) {
                modifier = mod;
                modKey = key;
                break;
            }
        }

        if (!modifier) {
            this.log('Usage: make <object(s)> bigger|smaller|faster|slower', 'err');
            return;
        }

        // Extract object specifier (everything between "make" and the modifier)
        const match = fullCmd.match(new RegExp('make\\s+(.+?)\\s+' + modKey, 'i'));
        if (!match) {
            this.log('Usage: make <object(s)> ' + modKey, 'err');
            return;
        }

        const objSpec = match[1].trim();
        let targets = [];

        // Handle "all <type>" pattern
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
            // Single object
            const resolved = this.resolveObject(objSpec);
            if (!resolved.obj) {
                this.log('Object not found: ' + objSpec, 'err');
                return;
            }
            if (resolved.correction) {
                this.log('[resolved: ' + resolved.correction + ']', 'dim');
            }
            targets = [resolved.obj];
        }

        // Apply the modifier to all targets
        const undoOps = [];
        for (const obj of targets) {
            const name = this.adapter.getObjectName(obj);
            const oldValue = this.adapter.getProperty(obj, modifier.prop) || 1;
            const newValue = oldValue * modifier.factor;
            this.adapter.setProperty(obj, modifier.prop, newValue);
            undoOps.push({ obj, prop: modifier.prop, oldValue, newValue });
        }

        if (targets.length === 1) {
            const name = this.adapter.getObjectName(targets[0]);
            this.log(name + ' is now ' + modKey, 'ok');
        } else {
            this.log('Made ' + targets.length + ' objects ' + modKey, 'ok');
        }

        this.pushUndo(
            'make ' + objSpec + ' ' + modKey,
            () => undoOps.forEach(op => this.adapter.setProperty(op.obj, op.prop, op.oldValue)),
            () => undoOps.forEach(op => this.adapter.setProperty(op.obj, op.prop, op.newValue))
        );
    }

    cmdMove(fullCmd, args) {
        // Natural language: "move logo to 50% 50%", "move ball to 100 200"
        const match = fullCmd.match(/^move\s+(.+?)\s+to\s+(.+)$/i);
        if (!match) {
            this.log('Usage: move <object> to <x> <y> [z]', 'err');
            return;
        }

        const objInput = match[1].trim();
        const posStr = match[2].trim();

        // Parse position values (space or comma separated)
        const posValues = posStr.split(/[\s,]+/).map(v => this.parseValue(v.trim()));

        const resolved = this.resolveObject(objInput);
        if (!resolved.obj) {
            this.log('Object not found: ' + objInput, 'err');
            return;
        }
        if (resolved.correction) {
            this.log('[resolved: ' + resolved.correction + ']', 'dim');
        }

        const obj = resolved.obj;
        const objName = resolved.resolvedName;

        // Store old values for undo
        const oldX = this.adapter.getProperty(obj, 'x');
        const oldY = this.adapter.getProperty(obj, 'y');
        const oldZ = this.adapter.getProperty(obj, 'z');

        // Apply new position
        if (posValues[0] !== undefined) this.adapter.setProperty(obj, 'x', posValues[0]);
        if (posValues[1] !== undefined) this.adapter.setProperty(obj, 'y', posValues[1]);
        if (posValues[2] !== undefined) this.adapter.setProperty(obj, 'z', posValues[2]);

        this.log('Moved ' + objName + ' to ' + posStr, 'ok');

        this.pushUndo(
            'move ' + objName,
            () => {
                this.adapter.setProperty(obj, 'x', oldX);
                this.adapter.setProperty(obj, 'y', oldY);
                this.adapter.setProperty(obj, 'z', oldZ);
            },
            () => {
                if (posValues[0] !== undefined) this.adapter.setProperty(obj, 'x', posValues[0]);
                if (posValues[1] !== undefined) this.adapter.setProperty(obj, 'y', posValues[1]);
                if (posValues[2] !== undefined) this.adapter.setProperty(obj, 'z', posValues[2]);
            }
        );
    }

    cmdClone(objInput) {
        if (!objInput) {
            this.log('Usage: clone <object>', 'err');
            return;
        }

        const resolved = this.resolveObject(objInput);
        if (!resolved.obj) {
            this.log('Object not found: ' + objInput, 'err');
            return;
        }
        if (resolved.correction) {
            this.log('[resolved: ' + resolved.correction + ']', 'dim');
        }

        const srcObj = resolved.obj;
        const srcName = resolved.resolvedName;
        const srcType = this.adapter.getObjectType(srcObj);

        // Copy properties from source
        const props = {};
        if (srcObj.userData) {
            for (const [key, val] of Object.entries(srcObj.userData)) {
                if (!key.startsWith('_')) {
                    props[key] = val;
                }
            }
        }

        // Get position and offset slightly
        const pos = this.adapter.getObjectPosition(srcObj);
        const offsetX = typeof pos.x === 'number' ? pos.x + 30 : pos.x;
        const offsetY = typeof pos.y === 'number' ? pos.y : pos.y;

        // Create clone with new name
        const newName = this.nextName(srcType);
        const newObj = this.adapter.createObject(srcType, newName, props);

        // Copy position with offset
        this.adapter.setProperty(newObj, 'x', offsetX);
        if (pos.y !== undefined) this.adapter.setProperty(newObj, 'y', pos.y);
        if (pos.z !== undefined) this.adapter.setProperty(newObj, 'z', pos.z);

        // Copy color if applicable
        const color = this.adapter.getObjectColor(srcObj);
        if (color !== undefined) {
            this.adapter.setProperty(newObj, 'color', color);
        }

        // Copy scale
        const scale = this.adapter.getObjectScale(srcObj);
        if (scale !== undefined && scale !== 1) {
            this.adapter.setProperty(newObj, 'scale', scale);
        }

        this.log("Cloned '" + srcName + "' -> '" + newName + "'", 'ok');

        this.pushUndo(
            'clone ' + srcName,
            () => this.adapter.deleteObject(newObj),
            () => {
                const obj = this.adapter.createObject(srcType, newName, props);
                this.adapter.setProperty(obj, 'x', offsetX);
            }
        );
    }

    cmdGet(args) {
        if (args.length === 0) {
            this.log('Usage: get <object>', 'err');
            return;
        }
        const resolved = this.resolveObject(args.join(' '));
        if (resolved.obj) {
            if (resolved.correction) {
                this.log('[resolved: ' + resolved.correction + ']', 'dim');
            }
            this.currentObject = resolved.obj;
            this.currentObjectName = resolved.resolvedName;
            this.log("Selected '" + resolved.resolvedName + "'", 'ok');
        } else {
            this.log('Object not found: ' + args.join(' '), 'err');
        }
    }

    cmdDelete(args) {
        if (args.length === 0) {
            this.log('Usage: delete <object> or delete all <type>', 'err');
            return;
        }

        const input = args.join(' ');

        // Check for "all <type>" pattern
        const allMatch = input.match(/^all\s+(\w+)$/i);
        if (allMatch) {
            const typeName = this.singularize(allMatch[1]);
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

            if (targets.length > this.options.confirmThreshold) {
                this.log('Delete ' + targets.length + ' ' + typeName + 's? Type "go" to confirm.', 'cyan');
                this.pendingOp = {
                    execute: () => {
                        targets.forEach(obj => this.adapter.deleteObject(obj));
                        this.log('Deleted ' + targets.length + ' ' + typeName + 's', 'ok');
                    }
                };
                return;
            }

            targets.forEach(obj => this.adapter.deleteObject(obj));
            this.log('Deleted ' + targets.length + ' ' + typeName + 's', 'ok');
            return;
        }

        // Single object delete
        const resolved = this.resolveObject(input);
        if (resolved.obj) {
            if (resolved.correction) {
                this.log('[resolved: ' + resolved.correction + ']', 'dim');
            }
            this.adapter.deleteObject(resolved.obj);
            this.log("Deleted '" + resolved.resolvedName + "'", 'ok');
            this.pushUndo(
                "delete '" + resolved.resolvedName + "'",
                () => { /* would need to recreate - complex */ },
                () => this.adapter.deleteObject(resolved.obj)
            );
        } else {
            this.log('Object not found: ' + input, 'err');
        }
    }

    cmdHide(name) {
        if (!name) {
            this.log('Usage: hide <object>', 'err');
            return;
        }
        const resolved = this.resolveObject(name);
        if (resolved.obj) {
            if (resolved.correction) {
                this.log('[resolved: ' + resolved.correction + ']', 'dim');
            }
            this.adapter.setObjectVisible(resolved.obj, false);
            this.log("Hid '" + resolved.resolvedName + "'", 'ok');
            this.pushUndo(
                "hide '" + resolved.resolvedName + "'",
                () => this.adapter.setObjectVisible(resolved.obj, true),
                () => this.adapter.setObjectVisible(resolved.obj, false)
            );
        } else {
            this.log('Object not found: ' + name, 'err');
        }
    }

    cmdShow(name) {
        if (!name) {
            this.log('Usage: show <object>', 'err');
            return;
        }
        const resolved = this.resolveObject(name);
        if (resolved.obj) {
            if (resolved.correction) {
                this.log('[resolved: ' + resolved.correction + ']', 'dim');
            }
            this.adapter.setObjectVisible(resolved.obj, true);
            this.log("Showed '" + resolved.resolvedName + "'", 'ok');
            this.pushUndo(
                "show '" + resolved.resolvedName + "'",
                () => this.adapter.setObjectVisible(resolved.obj, false),
                () => this.adapter.setObjectVisible(resolved.obj, true)
            );
        } else {
            this.log('Object not found: ' + name, 'err');
        }
    }

    cmdLook(name) {
        if (!name) {
            this.log('Usage: look <object>', 'err');
            return;
        }
        const resolved = this.resolveObject(name);
        if (resolved.obj) {
            if (resolved.correction) {
                this.log('[resolved: ' + resolved.correction + ']', 'dim');
            }
            const obj = resolved.obj;
            const objName = resolved.resolvedName;
            const type = this.adapter.getObjectType(obj);
            const pos = this.adapter.getObjectPosition(obj);
            const color = this.adapter.getObjectColor(obj);
            const scale = this.adapter.getObjectScale(obj);

            this.log(objName + ' (' + type + '):', 'cyan');
            // Format position - handle percentages and non-numbers
            const fmtPos = (v) => {
                if (v && typeof v === 'object' && v.percent !== undefined) {
                    return v.percent + '%';
                }
                if (typeof v === 'number') return v.toFixed(1);
                return String(v);
            };
            this.log('  position: [' + fmtPos(pos.x) + ', ' + fmtPos(pos.y) + ', ' + fmtPos(pos.z) + ']');
            if (color !== undefined) {
                this.log('  color: #' + color.toString(16).padStart(6, '0'));
            }
            if (scale !== undefined && scale !== 1) {
                this.log('  scale: ' + scale.toFixed(2));
            }
            // Show custom properties from userData
            if (obj.userData) {
                for (const [key, val] of Object.entries(obj.userData)) {
                    if (!key.startsWith('_')) {  // Skip internal props
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
        if (!typeName) {
            this.log('Total objects: ' + objects.length, 'ok');
            return;
        }
        const singular = this.singularize(typeName);
        let count = 0;
        for (const obj of objects) {
            const type = this.adapter.getObjectType(obj);
            const name = this.adapter.getObjectName(obj);
            if (type === singular || name === singular || name.startsWith(singular + '-')) {
                count++;
            }
        }
        this.log(singular + ': ' + count, 'ok');
    }

    // =========================================================================
    // Utilities
    // =========================================================================

    /**
     * Infer property from value type.
     * Only infers for UNAMBIGUOUS cases - colors and visibility.
     * Returns null if ambiguous (caller should require explicit property).
     */
    inferProperty(valueStr) {
        const v = valueStr.toLowerCase().trim();

        // Color names - unambiguous
        const colorNames = ['red', 'green', 'blue', 'yellow', 'cyan', 'magenta',
            'white', 'black', 'orange', 'purple', 'pink', 'gray', 'grey',
            'gold', 'silver', 'brown', 'lime', 'navy', 'teal', 'coral',
            'crimson', 'violet', 'indigo', 'maroon', 'olive', 'aqua'];
        if (colorNames.includes(v)) return 'color';

        // Hex color - unambiguous
        if (/^#?[0-9a-f]{6}$/i.test(v)) return 'color';

        // Visibility keywords - unambiguous
        if (v === 'visible' || v === 'hidden' || v === 'invisible') {
            return 'visible';
        }

        // Numbers and other values are AMBIGUOUS - return null
        // Caller will ask user to be explicit
        return null;
    }

    /**
     * Smart object resolution - tries multiple interpretations.
     * "red box" -> tries: "red box", "redbox", "red-box", any box with "red" in name
     * Returns { obj, resolvedName, correction } or { obj: null }
     */
    resolveObject(input) {
        if (!input) return { obj: null };

        const original = input.trim();
        const lower = original.toLowerCase();
        const words = lower.split(/\s+/);

        // 1. Try exact match first
        let obj = this.adapter.getObject(original);
        if (obj) return { obj, resolvedName: original, correction: null };

        // 2. Try lowercase
        obj = this.adapter.getObject(lower);
        if (obj) return { obj, resolvedName: lower, correction: null };

        // 3. Try no spaces (e.g., "red box" -> "redbox")
        if (words.length > 1) {
            const noSpaces = words.join('');
            obj = this.adapter.getObject(noSpaces);
            if (obj) return { obj, resolvedName: noSpaces, correction: `"${original}" -> "${noSpaces}"` };

            // 4. Try hyphenated (e.g., "red box" -> "red-box")
            const hyphenated = words.join('-');
            obj = this.adapter.getObject(hyphenated);
            if (obj) return { obj, resolvedName: hyphenated, correction: `"${original}" -> "${hyphenated}"` };
        }

        // 5. Try as type + modifier: find objects of last-word type containing other words
        if (words.length > 1) {
            const typeName = this.singularize(words[words.length - 1]);
            const modifiers = words.slice(0, -1);
            const allObjects = this.adapter.getAllObjects();

            for (const candidate of allObjects) {
                const name = this.adapter.getObjectName(candidate).toLowerCase();
                const type = this.adapter.getObjectType(candidate).toLowerCase();

                // Check if type matches and name contains all modifiers
                if (type === typeName || name.includes(typeName)) {
                    const hasAllModifiers = modifiers.every(mod => name.includes(mod));
                    if (hasAllModifiers) {
                        return {
                            obj: candidate,
                            resolvedName: this.adapter.getObjectName(candidate),
                            correction: `"${original}" -> "${this.adapter.getObjectName(candidate)}"`
                        };
                    }
                }
            }
        }

        // 6. Try partial match on any object
        const allObjects = this.adapter.getAllObjects();
        for (const candidate of allObjects) {
            const name = this.adapter.getObjectName(candidate).toLowerCase();
            if (name.includes(lower) || lower.includes(name)) {
                return {
                    obj: candidate,
                    resolvedName: this.adapter.getObjectName(candidate),
                    correction: `"${original}" -> "${this.adapter.getObjectName(candidate)}"`
                };
            }
        }

        return { obj: null };
    }

    parseValue(str) {
        str = str.trim();
        // Percentage (e.g., "50%") - store as object with normalized value
        const pctMatch = str.match(/^(-?\d+(?:\.\d+)?)\s*%$/);
        if (pctMatch) {
            const pct = parseFloat(pctMatch[1]);
            return { percent: pct, normalized: pct / 100 };
        }
        // Number
        if (/^-?\d+(\.\d+)?$/.test(str)) {
            return parseFloat(str);
        }
        // Boolean
        if (str === 'true') return true;
        if (str === 'false') return false;
        // Visibility keywords
        if (str === 'visible') return true;
        if (str === 'hidden' || str === 'invisible') return false;
        // Color names
        const colors = {
            red: 0xff0000, green: 0x00ff00, blue: 0x0000ff,
            yellow: 0xffff00, cyan: 0x00ffff, magenta: 0xff00ff,
            white: 0xffffff, black: 0x000000, orange: 0xff8800,
            purple: 0x8800ff, pink: 0xff69b4, gray: 0x888888,
            grey: 0x888888, gold: 0xffd700, silver: 0xc0c0c0,
            brown: 0x8b4513, lime: 0x00ff00, navy: 0x000080,
            teal: 0x008080, coral: 0xff7f50, crimson: 0xdc143c,
            violet: 0xee82ee, indigo: 0x4b0082, maroon: 0x800000,
            olive: 0x808000, aqua: 0x00ffff
        };
        if (colors[str.toLowerCase()]) {
            return colors[str.toLowerCase()];
        }
        // Hex color
        if (/^#?[0-9a-f]{6}$/i.test(str)) {
            return parseInt(str.replace('#', ''), 16);
        }
        // String (strip quotes if present)
        if ((str.startsWith('"') && str.endsWith('"')) ||
            (str.startsWith("'") && str.endsWith("'"))) {
            return str.slice(1, -1);
        }
        return str;
    }
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { Rosh3DRuntime, ROSH_3D_VERSION };
}
