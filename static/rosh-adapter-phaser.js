/**
 * Rosh Phaser Adapter
 *
 * Implements the RoshAdapter interface for Phaser 3 games.
 * This adapter connects the shared Rosh runtime to Phaser-specific operations.
 *
 * Usage:
 *   const adapter = createPhaserAdapter(scene, gameObjects);
 *   RoshRuntime.init(adapter);
 *
 * Version: 0.1.0
 */

'use strict';

function createPhaserAdapter(phaserScene, options = {}) {

  // Object registry: name -> Phaser.GameObjects
  const objects = {};

  // Supported primitive types for this engine (2D shapes)
  // Includes 3D type aliases (sphere->circle, square->rectangle) for cross-engine compatibility
  const PRIMITIVE_TYPES = ['rectangle', 'rect', 'square', 'circle', 'ellipse', 'triangle', 'sprite', 'text', 'box', 'cube', 'ball', 'sphere'];

  // Scene registry for multi-scene support
  const scenes = new Set();
  let currentScene = options.defaultScene || null;

  // Type counters for auto-naming
  const typeCounters = {};

  // Known object presets (use RoshObjects if available, else options, else empty)
  const KNOWN_OBJECTS = options.knownObjects ||
    (typeof RoshObjects !== 'undefined' ? RoshObjects.KNOWN_OBJECTS_2D : {});

  // Asset base path for sprites
  const assetPath = options.assetPath || '';

  // Default size in pixels
  const DEFAULT_SIZE = 50;

  // Edit mode state
  let editMode = false;
  let selectedObject = null;
  let selectedOriginalTint = null;

  // Color mappings - use RoshColors if available, otherwise fallback
  const COLOR_MAP = (typeof RoshColors !== 'undefined') ? RoshColors.COLOR_MAP : {
    red: 0xff0000, green: 0x00ff00, blue: 0x0000ff,
    yellow: 0xffff00, cyan: 0x00ffff, magenta: 0xff00ff,
    white: 0xffffff, black: 0x111111, orange: 0xff8800,
    purple: 0x8800ff, pink: 0xff88ff, gray: 0x888888,
    grey: 0x888888, gold: 0xffd700, silver: 0xc0c0c0
  };

  // ==========================================================================
  // HELPERS
  // ==========================================================================

  function generateUUID() {
    if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
      return crypto.randomUUID();
    }
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
      var r = Math.random() * 16 | 0, v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  }

  function generateName(typeName) {
    if (!typeCounters[typeName]) typeCounters[typeName] = 0;
    typeCounters[typeName]++;
    return typeName + '-' + typeCounters[typeName];
  }

  function parseColor(str) {
    // Delegate to RoshColors if available
    if (typeof RoshColors !== 'undefined') {
      return RoshColors.parse(str);
    }
    // Fallback
    if (typeof str === 'number') return str;
    const lower = str.toLowerCase();
    if (COLOR_MAP[lower] !== undefined) return COLOR_MAP[lower];
    if (str.startsWith('#')) return parseInt(str.slice(1), 16);
    if (str.startsWith('0x')) return parseInt(str, 16);
    return null;
  }

  function findObject(name) {
    // Direct lookup
    if (objects[name]) return objects[name];

    // Case-insensitive lookup
    const lower = name.toLowerCase();
    for (const [key, obj] of Object.entries(objects)) {
      if (key.toLowerCase() === lower) return obj;
    }

    return null;
  }

  function getTypeName(obj) {
    if (obj.getData && obj.getData('_type')) {
      return obj.getData('_type');
    }
    // Infer from Phaser type
    if (obj.type === 'Sprite') return 'sprite';
    if (obj.type === 'Image') return 'image';
    if (obj.type === 'Rectangle') return 'rect';
    if (obj.type === 'Circle') return 'circle';
    if (obj.type === 'Text') return 'text';
    return 'object';
  }

  function getColorName(obj) {
    if (obj.getData && obj.getData('_color')) {
      return obj.getData('_color');
    }
    return '';
  }

  // Create a shape by type
  function createShape(typeName, x, y, size, colorHex, preset2d) {
    let obj;
    const w = preset2d && preset2d.width ? preset2d.width * size : size;
    const h = preset2d && preset2d.height ? preset2d.height * size : size;

    switch (typeName) {
      case 'circle':
      case 'ball':
      case 'sphere':  // 3D sphere -> 2D circle
        const radius = (preset2d && preset2d.scale ? preset2d.scale : 1) * size / 2;
        obj = phaserScene.add.circle(x, y, radius, colorHex);
        break;
      case 'ellipse':
        obj = phaserScene.add.ellipse(x, y, w, h, colorHex);
        break;
      case 'triangle':
        obj = phaserScene.add.triangle(x, y, 0, size, size/2, 0, size, size, colorHex);
        break;
      case 'text':
        obj = phaserScene.add.text(x, y, 'text', {
          fontSize: '24px',
          color: '#' + colorHex.toString(16).padStart(6, '0')
        });
        obj.setOrigin(0.5);
        break;
      case 'rect':
      case 'rectangle':
      case 'square':  // 3D square -> 2D rectangle
      case 'cube':
      case 'box':
      default:
        obj = phaserScene.add.rectangle(x, y, w, h, colorHex);
    }

    return obj;
  }

  // ==========================================================================
  // ADAPTER INTERFACE
  // ==========================================================================

  const adapter = {
    // Platform identifier for welcome message
    platform: 'Phaser',

    // Supported types for this engine
    getSupportedTypes: function() {
      return PRIMITIVE_TYPES.slice();
    },

    // Registry management
    registerObject: function(name, obj) {
      objects[name] = obj;
      if (obj.getData && obj.getData('_scene')) {
        scenes.add(obj.getData('_scene'));
      }
    },

    // Object list
    getObjectNames: function() {
      return Object.keys(objects);
    },

    getObjects: function() {
      return Object.entries(objects).map(([name, obj]) => ({
        name,
        object: obj,
        type: getTypeName(obj),
        visible: obj.visible
      }));
    },

    getObject: function(name) {
      const obj = findObject(name);
      if (!obj) return null;
      return {
        name: obj.name || name,
        object: obj,
        type: getTypeName(obj)
      };
    },

    getObjectsByType: function(typeName) {
      const results = [];
      for (const [name, obj] of Object.entries(objects)) {
        const t = getTypeName(obj);
        if (t === typeName || name.startsWith(typeName + '-')) {
          results.push({ name, object: obj, type: t });
        }
      }
      return results;
    },

    // Get all objects (for query syntax)
    getAllObjects: function(options) {
      const sceneOnly = options && options.sceneOnly;
      return Object.entries(objects)
        .filter(([name, obj]) => {
          if (!obj) return false;
          if (sceneOnly) {
            const objScene = obj.getData ? obj.getData('_scene') : null;
            if (objScene !== currentScene && (objScene || currentScene)) return false;
          }
          return true;
        })
        .map(([name, obj]) => {
          const scene = obj.getData ? obj.getData('_scene') : null;
          return {
            name,
            object: obj,
            type: getTypeName(obj),
            userData: {
              _scene: scene,
              _type: getTypeName(obj),
              _name: name,
              color: getColorName(obj)
            }
          };
        });
    },

    // Object accessor methods (used by RoshRuntime)
    getObjectName: function(obj) {
      if (typeof obj === 'string') return obj;
      if (obj && obj.name) return obj.name;
      return 'unknown';
    },

    getObjectType: function(obj) {
      if (typeof obj === 'string') {
        const found = findObject(obj);
        return found ? getTypeName(found) : 'unknown';
      }
      if (obj && obj.type) return obj.type;
      if (obj && obj.object) return getTypeName(obj.object);
      return getTypeName(obj) || 'unknown';
    },

    getObjectPosition: function(obj) {
      const sprite = (typeof obj === 'string') ? findObject(obj) : (obj && obj.object) || obj;
      if (sprite && typeof sprite.x !== 'undefined') return { x: sprite.x, y: sprite.y, z: 0 };
      return { x: 0, y: 0, z: 0 };
    },

    getObjectColor: function(obj) {
      const sprite = (typeof obj === 'string') ? findObject(obj) : (obj && obj.object) || obj;
      if (sprite && sprite.getData) {
        const colorName = sprite.getData('_color');
        if (colorName && COLOR_MAP[colorName]) return COLOR_MAP[colorName];
      }
      if (sprite && sprite.tintTopLeft !== undefined && sprite.tintTopLeft !== 0xffffff) return sprite.tintTopLeft;
      return undefined;
    },

    // Deep search
    deepSearch: function(args) {
      const results = [];
      const searchTerms = args.map(a => a.toLowerCase());

      const colorTerms = Object.keys(COLOR_MAP);
      const sizeTerms = ['big', 'large', 'small', 'tiny', 'huge'];

      let targetColor = null;
      let targetSize = null;
      let targetType = null;

      for (const term of searchTerms) {
        if (colorTerms.includes(term)) targetColor = term;
        else if (sizeTerms.includes(term)) targetSize = term;
        else targetType = term;
      }

      for (const [name, obj] of Object.entries(objects)) {
        const objType = getTypeName(obj);
        const objColor = getColorName(obj);

        if (targetType && objType !== targetType && !name.startsWith(targetType)) continue;
        if (targetColor && objColor !== targetColor) continue;

        if (targetSize) {
          const scale = Math.max(obj.scaleX || 1, obj.scaleY || 1);
          if ((targetSize === 'big' || targetSize === 'large') && scale < 1.5) continue;
          if ((targetSize === 'small' || targetSize === 'tiny') && scale > 0.7) continue;
        }

        results.push({ name, object: obj, type: objType, color: objColor });
      }

      return { success: true, objects: results };
    },

    // Object creation
    createObject: function(typeName, name, options = {}) {
      const objName = (typeof name === 'string' ? name : options.name) || generateName(typeName);
      const modifiers = options.modifiers || [];

      // Size modifiers (semantic name -> scale multiplier)
      const SIZE_MAP = { tiny: 0.25, small: 0.5, medium: 1, big: 2, large: 2, huge: 4 };

      // Get color from options, modifiers, or default
      const userSpecifiedColor = options.color || modifiers.find(m => COLOR_MAP[m]);
      const color = userSpecifiedColor || 'gray';
      const colorHex = COLOR_MAP[color] || 0x888888;
      console.log('[Adapter] createObject:', typeName, 'modifiers:', modifiers, 'userSpecifiedColor:', userSpecifiedColor, 'color:', color, 'colorHex:', colorHex.toString(16));

      // Get size from options or modifiers
      // Handle: string name ("big"), numeric scale (2), or modifiers array
      const sizeModifier = modifiers.find(m => SIZE_MAP[m]);
      const scale = SIZE_MAP[options.size] ||
                    (typeof options.size === 'number' ? options.size :
                     (sizeModifier ? SIZE_MAP[sizeModifier] : 1));

      // Position
      const gameWidth = phaserScene.sys.game.config.width;
      const gameHeight = phaserScene.sys.game.config.height;

      // Convert 3D world coordinates to 2D screen coordinates if needed
      // Three.js uses world units (typically -10 to 10), Phaser uses pixels
      // Detect 3D coords: small values that look like world units, not pixels
      let x, y;
      if (options.x !== undefined) {
        // If x is small (world units), convert to screen coords
        // Three.js X maps to Phaser X, Three.js Z maps to Phaser Y
        if (Math.abs(options.x) < 20 && options.z !== undefined) {
          // 3D world coords detected - convert to 2D screen
          // Map world X (-5..5) to screen X (0..width)
          // Map world Z (-5..5) to screen Y (0..height)
          x = ((options.x + 5) / 10) * gameWidth;
          y = ((options.z + 5) / 10) * gameHeight;
          console.log('[Adapter] Converted 3D coords (' + options.x + ', ' + options.z + ') to 2D (' + x.toFixed(0) + ', ' + y.toFixed(0) + ')');
        } else {
          // Already pixel coords or no z - use as-is
          x = options.x;
          y = options.y !== undefined ? options.y : gameHeight / 2;
        }
      } else {
        // No position specified - center with random offset
        x = gameWidth / 2 + (Math.random() - 0.5) * 200;
        y = gameHeight / 2 + (Math.random() - 0.5) * 200;
      }

      // Check known objects preset
      // KNOWN_OBJECTS can be flat (from RoshObjects) or nested (from emitter)
      const preset = KNOWN_OBJECTS[typeName];
      const preset2d = preset ? (preset['2d'] || preset) : null;  // Support both formats
      const description = preset ? (preset.description || null) : null;
      const isKnownType = PRIMITIVE_TYPES.includes(typeName) || !!preset;

      let obj;
      const size = DEFAULT_SIZE * scale;

      // Try sprite from preset first
      if (preset2d && preset2d.sprite) {
        const spritePath = assetPath + preset2d.sprite;
        const spriteKey = 'rosh_' + typeName;

        if (phaserScene.textures.exists(spriteKey)) {
          // Texture already loaded
          obj = phaserScene.add.sprite(x, y, spriteKey);
          obj.setScale(scale * 0.5);  // Sprites often need scaling down
        } else {
          // Create shape placeholder while sprite loads
          // User/network color takes precedence over preset color
          const presetColor = userSpecifiedColor ? colorHex : (preset2d.color ? parseColor(preset2d.color) : colorHex);
          obj = createShape(preset2d.shape || 'rectangle', x, y, size, presetColor, preset2d);
          obj.setAlpha(0.6);

          // Load sprite asynchronously
          phaserScene.load.image(spriteKey, spritePath);
          phaserScene.load.once('complete', () => {
            if (phaserScene.textures.exists(spriteKey)) {
              const sprite = phaserScene.add.sprite(obj.x, obj.y, spriteKey);
              sprite.name = objName;
              sprite.setData('_uuid', obj.getData('_uuid'));
              sprite.setData('_created_at', obj.getData('_created_at'));
              sprite.setData('_type', typeName);
              sprite.setData('_color', color);
              sprite.setData('_roshId', objName);
              sprite.setData('_description', description);
              sprite.setScale(scale * 0.5);

              obj.destroy();
              objects[objName] = sprite;

              if (typeof RoshRuntime !== 'undefined') {
                RoshRuntime.log('   [sprite loaded]', 'dim');
              }
            }
          });
          phaserScene.load.start();
        }
      } else if (preset2d) {
        // Use shape from preset
        // User/network color takes precedence over preset color
        const presetColor = userSpecifiedColor ? colorHex : (preset2d.color ? parseColor(preset2d.color) : colorHex);
        obj = createShape(preset2d.shape || 'rectangle', x, y, size, presetColor, preset2d);
      } else {
        // Primitive shapes
        obj = createShape(typeName, x, y, size, colorHex);
      }

      if (!obj) {
        return { success: false, error: 'Failed to create object' };
      }

      // Set common properties
      obj.name = objName;
      obj.setData('_uuid', generateUUID());
      obj.setData('_created_at', new Date().toISOString());
      obj.setData('_type', typeName);
      obj.setData('_color', color);
      obj.setData('_roshId', objName);
      if (description) obj.setData('_description', description);
      if (preset && preset.credit) obj.setData('_credit', preset.credit);

      objects[objName] = obj;

      return { success: true, name: objName, object: obj, color: color, size: scale, knownType: isKnownType, description };
    },

    // Helper: create a shape
    _createShape: createShape,

    // Object deletion
    deleteObject: function(name) {
      const obj = findObject(name);
      if (!obj) return { success: false, error: 'Object not found: ' + name };

      obj.destroy();
      delete objects[name];

      return { success: true };
    },

    // Object restoration
    restoreObject: function(name, savedState) {
      // Phaser objects can't be easily restored - would need to recreate
      return { success: false, error: 'Restore not supported in Phaser' };
    },

    // Object cloning
    cloneObject: function(name) {
      const obj = findObject(name);
      if (!obj) return { success: false, error: 'Object not found: ' + name };

      const typeName = getTypeName(obj);
      const color = getColorName(obj);
      const result = adapter.createObject(typeName, null, { modifiers: [color] });

      if (result.success) {
        result.object.x = obj.x + 30;
        result.object.y = obj.y + 30;
        // Track lineage: link clone to its parent
        const parentUUID = obj.getData ? obj.getData('_uuid') : null;
        if (parentUUID && result.object.setData) {
          result.object.setData('_parent_uuid', parentUUID);
        }
      }

      return result;
    },

    // Property access
    getProperty: function(name, prop) {
      const obj = findObject(name);
      if (!obj) return undefined;

      switch (prop.toLowerCase()) {
        case 'x': return obj.x;
        case 'y': return obj.y;
        case 'visible': return obj.visible;
        case 'scale': return obj.scaleX;
        default:
          return obj.getData ? obj.getData(prop) : undefined;
      }
    },

    setProperty: function(name, prop, value) {
      const obj = findObject(name);
      if (!obj) return { success: false, error: 'Object not found: ' + name };

      switch (prop.toLowerCase()) {
        case 'x':
          obj.x = parseFloat(value);
          break;
        case 'y':
          obj.y = parseFloat(value);
          break;
        case 'visible':
          obj.visible = value === 'true' || value === true;
          break;
        case 'color':
          const c = parseColor(value);
          if (c !== null && obj.setFillStyle) {
            obj.setFillStyle(c);
            obj.setData('_color', value);
          }
          break;
        case 'scale':
          const s = parseFloat(value);
          obj.setScale(s, s);
          break;
        case 'scene':
          obj.setData('_scene', value);
          scenes.add(value);
          break;
        case 'text':
          // Update displayed text for Phaser text objects
          if (typeof obj.setText === 'function') {
            obj.setText(String(value));
          } else {
            obj.text = String(value);
          }
          break;
        default:
          if (obj.setData) obj.setData(prop, value);
      }

      return { success: true };
    },

    // Visibility
    setVisible: function(name, visible) {
      const obj = findObject(name);
      if (!obj) return { success: false, error: 'Object not found: ' + name };
      obj.visible = visible;
      return { success: true };
    },

    // Position
    getPosition: function(name) {
      const obj = findObject(name);
      if (!obj) return null;
      return { x: obj.x, y: obj.y };
    },

    moveObject: function(name, pos) {
      const obj = findObject(name);
      if (!obj) return { success: false, error: 'Object not found: ' + name };
      if (pos.x !== undefined) obj.x = pos.x;
      if (pos.y !== undefined) obj.y = pos.y;
      return { success: true };
    },

    moveObjectRelative: function(name, direction, amount) {
      const obj = findObject(name);
      if (!obj) return { success: false, error: 'Object not found: ' + name };

      switch (direction) {
        case 'left': obj.x -= amount; break;
        case 'right': obj.x += amount; break;
        case 'up': obj.y -= amount; break;
        case 'down': obj.y += amount; break;
        case 'forward': obj.y -= amount; break;  // 2D: forward = up
        case 'back':
        case 'backward': obj.y += amount; break;
      }

      return { success: true };
    },

    // Object details
    getObjectDetails: function(name) {
      const obj = findObject(name);
      if (!obj) return null;

      return {
        type: getTypeName(obj),
        color: getColorName(obj),
        position: { x: obj.x.toFixed(0), y: obj.y.toFixed(0) },
        scale: { x: (obj.scaleX || 1).toFixed(2), y: (obj.scaleY || 1).toFixed(2) },
        visible: obj.visible,
        description: obj.getData ? obj.getData('_description') : null,
        credit: obj.getData ? obj.getData('_credit') : null
      };
    },

    // Scene management
    getScenes: function() {
      return Array.from(scenes);
    },

    getCurrentScene: function() {
      return currentScene;
    },

    gotoScene: function(sceneName) {
      if (!scenes.has(sceneName)) {
        const lower = sceneName.toLowerCase();
        let match = null;
        for (const s of scenes) {
          if (s.toLowerCase() === lower) {
            match = s;
            break;
          }
        }
        if (!match) {
          return { success: false, error: 'Scene not found: ' + sceneName };
        }
        sceneName = match;
      }

      currentScene = sceneName;

      // Update Phaser scene's currentScene property for static visibility
      if (phaserScene && phaserScene.currentScene !== undefined) {
        phaserScene.currentScene = sceneName;
      }

      // Update visibility for dynamically registered objects (have _scene data)
      for (const [name, obj] of Object.entries(objects)) {
        if (obj.getData) {
          const objScene = obj.getData('_scene');
          if (objScene) {
            obj.visible = (objScene === currentScene);
          }
        }
      }

      // Call updateSceneVisibility() for static objects (emitter-generated method)
      if (phaserScene && typeof phaserScene.updateSceneVisibility === 'function') {
        phaserScene.updateSceneVisibility();
      }

      return { success: true, scene: currentScene };
    },

    // Object counting
    countObjects: function(typeName) {
      if (!typeName) return Object.keys(objects).length;
      let count = 0;
      for (const [name, obj] of Object.entries(objects)) {
        const t = getTypeName(obj);
        if (t === typeName || name.startsWith(typeName + '-')) count++;
      }
      return count;
    },

    // Save/Load
    saveGame: function(slot) {
      const state = {};
      for (const [name, obj] of Object.entries(objects)) {
        state[name] = {
          type: getTypeName(obj),
          color: getColorName(obj),
          x: obj.x,
          y: obj.y,
          scaleX: obj.scaleX || 1,
          scaleY: obj.scaleY || 1,
          visible: obj.visible
        };
      }
      localStorage.setItem('rosh-save-' + slot, JSON.stringify(state));
      return true;
    },

    loadGame: function(slot) {
      const json = localStorage.getItem('rosh-save-' + slot);
      if (!json) return false;

      try {
        const state = JSON.parse(json);
        // Clear and recreate
        for (const name of Object.keys(objects)) {
          adapter.deleteObject(name);
        }
        for (const [name, data] of Object.entries(state)) {
          adapter.createObject(data.type, name, { modifiers: [data.color] });
          const obj = objects[name];
          if (obj) {
            obj.x = data.x;
            obj.y = data.y;
            obj.setScale(data.scaleX, data.scaleY);
            obj.visible = data.visible;
          }
        }
        return true;
      } catch (e) {
        console.error('Failed to load:', e);
        return false;
      }
    },

    // ========================================================================
    // SELECTION (click-to-select)
    // ========================================================================

    getSelectedObject: function() {
      return selectedObject ? selectedObject.name : null;
    },

    getSelectedObjectData: function() {
      if (!selectedObject) return null;
      return {
        name: selectedObject.name,
        type: getTypeName(selectedObject),
        color: getColorName(selectedObject),
        position: { x: selectedObject.x, y: selectedObject.y }
      };
    },

    selectByName: function(name) {
      const obj = findObject(name);
      if (obj) {
        // Deselect previous
        if (selectedObject && selectedObject !== obj) {
          if (selectedOriginalTint !== null && selectedObject.clearTint) {
            selectedObject.clearTint();
          }
        }
        // Select new
        selectedObject = obj;
        window.selectedObject = obj;  // Export globally for parity with ThreeJS
        if (obj.setTint) {
          selectedOriginalTint = obj.tintTopLeft || null;
          obj.setTint(0x00ff00);  // Green highlight
        }
        return { name: obj.name, type: getTypeName(obj) };
      }
      return null;
    },

    deselect: function() {
      if (selectedObject) {
        if (selectedObject.clearTint) {
          selectedObject.clearTint();
        }
        selectedObject = null;
        window.selectedObject = null;  // Export globally for parity with ThreeJS
        selectedOriginalTint = null;
      }
      return { success: true };
    },

    // ========================================================================
    // EDIT MODE (enables selection and object control)
    // ========================================================================

    enableEditMode: function() {
      editMode = true;
      // Set up click handler for selection
      if (phaserScene.input && !phaserScene._roshEditClickHandler) {
        phaserScene._roshEditClickHandler = phaserScene.input.on('pointerdown', (pointer) => {
          if (!editMode) return;

          // Find object under click
          const hitObjects = [];
          for (const [name, obj] of Object.entries(objects)) {
            if (obj.getBounds && obj.visible) {
              const bounds = obj.getBounds();
              if (bounds.contains(pointer.x, pointer.y)) {
                hitObjects.push(obj);
              }
            }
          }

          if (hitObjects.length > 0) {
            // Select the first hit object
            adapter.selectByName(hitObjects[0].name);
            console.log('[Edit] Selected:', hitObjects[0].name);
          } else {
            // Click on empty space - deselect
            adapter.deselect();
          }
        });

        // Set up keyboard handler for moving selected object
        if (!phaserScene._roshEditKeyHandler) {
          phaserScene._roshEditKeyHandler = phaserScene.input.keyboard.on('keydown', (event) => {
            if (!editMode || !selectedObject) return;

            const step = event.shiftKey ? 50 : 10;
            switch (event.code) {
              case 'ArrowLeft':
              case 'KeyA':
                selectedObject.x -= step;
                break;
              case 'ArrowRight':
              case 'KeyD':
                selectedObject.x += step;
                break;
              case 'ArrowUp':
              case 'KeyW':
                selectedObject.y -= step;
                break;
              case 'ArrowDown':
              case 'KeyS':
                selectedObject.y += step;
                break;
            }
          });
        }
      }
      return { success: true, editMode: true };
    },

    disableEditMode: function() {
      editMode = false;
      adapter.deselect();
      return { success: true, editMode: false };
    },

    isEditMode: function() {
      return editMode;
    },

    // ========================================================================
    // CAPABILITIES (pulse, spin, bounce) - via Phaser tweens
    // ========================================================================

    applyCapability: function(name, capability, value) {
      const obj = findObject(name);
      if (!obj) return { success: false, error: 'Object not found: ' + name };

      // Stop any existing tween on this object for this capability
      const tweenKey = '_tween_' + capability;
      if (obj.getData && obj.getData(tweenKey)) {
        obj.getData(tweenKey).stop();
      }

      // If value is falsy/off, just stop the tween
      if (!value || value === 'off' || value === false || value === 0) {
        if (obj.setData) obj.setData(tweenKey, null);
        return { success: true, stopped: true };
      }

      // Parse value - can be number, boolean, or "on"
      const intensity = (typeof value === 'number') ? value : 1;

      let tween;
      switch (capability) {
        case 'pulse':
          const pulseScale = 1 + (0.2 * intensity);  // 1.2x at intensity 1
          tween = phaserScene.tweens.add({
            targets: obj,
            scaleX: obj.scaleX * pulseScale,
            scaleY: obj.scaleY * pulseScale,
            duration: 500 / intensity,
            yoyo: true,
            repeat: -1,
            ease: 'Sine.easeInOut'
          });
          break;

        case 'spin':
          const spinSpeed = 360 * intensity;  // degrees per second
          tween = phaserScene.tweens.add({
            targets: obj,
            angle: obj.angle + 360,
            duration: 1000 / intensity,
            repeat: -1,
            ease: 'Linear'
          });
          break;

        case 'bounce':
          const bounceHeight = 20 * intensity;
          const baseY = obj.y;
          tween = phaserScene.tweens.add({
            targets: obj,
            y: baseY - bounceHeight,
            duration: 400 / intensity,
            yoyo: true,
            repeat: -1,
            ease: 'Sine.easeOut'
          });
          break;

        default:
          return { success: false, error: 'Unknown capability: ' + capability };
      }

      if (obj.setData) obj.setData(tweenKey, tween);
      console.log('[Adapter] Applied ' + capability + ' to ' + name + ' (intensity: ' + intensity + ')');
      return { success: true, capability, intensity };
    },

    stopCapability: function(name, capability) {
      return this.applyCapability(name, capability, false);
    },

    // ========================================================================
    // SPOTLIGHT (2D stub for network parity with Three.js)
    // ========================================================================

    toggleSpotlight: function(visible, targetName) {
      // 2D games don't have spotlights, but we implement the interface
      // for network parity so spotlight commands from 3D twins are handled
      console.log('[Adapter] Spotlight ' + (visible ? 'on' : 'off') +
                  (targetName ? ' targeting ' + targetName : '') +
                  ' (no-op in 2D)');
      return { success: true, note: 'Spotlight not available in 2D mode' };
    }
  };

  return adapter;
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = createPhaserAdapter;
}
