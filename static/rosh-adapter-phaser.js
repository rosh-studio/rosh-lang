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
  const PRIMITIVE_TYPES = ['rectangle', 'rect', 'circle', 'ellipse', 'triangle', 'sprite', 'text', 'box', 'cube', 'ball'];

  // Scene registry for multi-scene support
  const scenes = new Set();
  let currentScene = options.defaultScene || null;

  // Type counters for auto-naming
  const typeCounters = {};

  // Known object presets (passed from emitter or page)
  const KNOWN_OBJECTS = options.knownObjects || {};

  // Asset base path for sprites
  const assetPath = options.assetPath || '';

  // Default size in pixels
  const DEFAULT_SIZE = 50;

  // Color mappings (Phaser uses hex numbers)
  const COLOR_MAP = {
    red: 0xff0000, green: 0x00ff00, blue: 0x0000ff,
    yellow: 0xffff00, cyan: 0x00ffff, magenta: 0xff00ff,
    white: 0xffffff, black: 0x111111, orange: 0xff8800,
    purple: 0x8800ff, pink: 0xff88ff, gray: 0x888888,
    grey: 0x888888, gold: 0xffd700, silver: 0xc0c0c0
  };

  // ==========================================================================
  // HELPERS
  // ==========================================================================

  function generateName(typeName) {
    if (!typeCounters[typeName]) typeCounters[typeName] = 0;
    typeCounters[typeName]++;
    return typeName + '-' + typeCounters[typeName];
  }

  function parseColor(str) {
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
    getAllObjects: function() {
      return Object.entries(objects).map(([name, obj]) => ({
        name,
        object: obj,
        type: getTypeName(obj)
      }));
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

      // Size modifiers
      const SIZE_MAP = { tiny: 0.25, small: 0.5, big: 2, large: 2, huge: 4 };

      // Get color from options, modifiers, or default
      const color = options.color || modifiers.find(m => COLOR_MAP[m]) || 'gray';
      const colorHex = COLOR_MAP[color] || 0x888888;

      // Get size from options or modifiers
      const sizeModifier = modifiers.find(m => SIZE_MAP[m]);
      const scale = options.size || (sizeModifier ? SIZE_MAP[sizeModifier] : 1);

      // Position
      const gameWidth = phaserScene.sys.game.config.width;
      const gameHeight = phaserScene.sys.game.config.height;
      const x = options.x !== undefined ? options.x : gameWidth / 2 + (Math.random() - 0.5) * 200;
      const y = options.y !== undefined ? options.y : gameHeight / 2 + (Math.random() - 0.5) * 200;

      // Check known objects preset
      const preset = KNOWN_OBJECTS[typeName];
      const preset2d = preset ? preset['2d'] : null;
      const description = preset ? preset.description : null;
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
          const presetColor = preset2d.color ? parseColor(preset2d.color) : colorHex;
          obj = createShape(preset2d.shape || 'rectangle', x, y, size, presetColor, preset2d);
          obj.setAlpha(0.6);

          // Load sprite asynchronously
          phaserScene.load.image(spriteKey, spritePath);
          phaserScene.load.once('complete', () => {
            if (phaserScene.textures.exists(spriteKey)) {
              const sprite = phaserScene.add.sprite(obj.x, obj.y, spriteKey);
              sprite.name = objName;
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
        const presetColor = preset2d.color ? parseColor(preset2d.color) : colorHex;
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

      // Update visibility
      for (const [name, obj] of Object.entries(objects)) {
        if (obj.getData) {
          const objScene = obj.getData('_scene');
          if (objScene) {
            obj.visible = (objScene === currentScene);
          }
        }
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
    }
  };

  return adapter;
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = createPhaserAdapter;
}
