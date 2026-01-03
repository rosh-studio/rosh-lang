/**
 * Rosh Three.js Adapter
 *
 * Implements the RoshAdapter interface for Three.js scenes.
 * This adapter connects the shared Rosh runtime to Three.js-specific operations.
 *
 * Usage:
 *   const adapter = createThreeJSAdapter(scene, camera, renderer);
 *   RoshRuntime.init(adapter);
 *
 * Version: 0.1.0
 */

function createThreeJSAdapter(scene, camera, renderer, options = {}) {
  // Object registry: name -> THREE.Object3D
  const objects = {};

  // Scene registry for multi-scene support
  const scenes = new Set();
  let currentScene = options.defaultScene || null;

  // Type counters for auto-naming
  const typeCounters = {};

  // Known object presets (can be extended by emitter)
  const KNOWN_OBJECTS = options.knownObjects || {};

  // ==========================================================================
  // PHYSICS STATE (ThreeJS-first features)
  // ==========================================================================

  let gravityEnabled = false;
  let gravityStrength = 9.8;  // Units per second squared
  let groundLevel = 0;        // Y position of ground
  const objectVelocities = new Map();  // Track vertical velocity per object

  // Click-to-move state
  let clickToMoveEnabled = false;
  let playerObjectName = null;  // Name of object to move on click
  let moveSpeed = 5;            // Units per second
  let moveTarget = null;        // Current target position {x, z}
  const raycaster = new THREE.Raycaster();
  const mouse = new THREE.Vector2();
  let groundPlane = null;       // Invisible ground for raycasting

  // Player keyboard movement state
  let playerKeyboardEnabled = false;
  const playerKeyState = { left: false, right: false, forward: false, back: false, up: false, down: false };

  // Edit mode - must be enabled for selection/control
  let editMode = false;

  // Click-to-select state
  let selectedObject = null;
  let selectedOriginalEmissive = null;  // Store original emissive to restore on deselect

  // Color mappings
  const COLOR_MAP = {
    red: 0xff0000, green: 0x00ff00, blue: 0x0000ff,
    yellow: 0xffff00, cyan: 0x00ffff, magenta: 0xff00ff,
    white: 0xffffff, black: 0x111111, orange: 0xff8800,
    purple: 0x8800ff, pink: 0xff88ff, gray: 0x888888,
    grey: 0x888888, gold: 0xffd700, silver: 0xc0c0c0
  };

  // Reverse color lookup for getColorName
  const HEX_TO_COLOR = {
    0xff0000: 'red', 0x00ff00: 'green', 0x0000ff: 'blue',
    0xffff00: 'yellow', 0x00ffff: 'cyan', 0xff00ff: 'magenta',
    0xffffff: 'white', 0x000000: 'black', 0x111111: 'black',
    0xff8800: 'orange', 0x8800ff: 'purple', 0xff88ff: 'pink',
    0x888888: 'gray', 0xffd700: 'gold', 0xc0c0c0: 'silver'
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

  function getColorName(mesh) {
    if (mesh.userData && mesh.userData._color) {
      return mesh.userData._color.toLowerCase();
    }
    if (mesh.material && mesh.material.color) {
      const hex = mesh.material.color.getHex();
      if (HEX_TO_COLOR[hex]) return HEX_TO_COLOR[hex];

      // Approximate color detection
      const r = (hex >> 16) & 0xff;
      const g = (hex >> 8) & 0xff;
      const b = hex & 0xff;

      if (r > 200 && g < 100 && b < 100) return 'red';
      if (r < 100 && g > 200 && b < 100) return 'green';
      if (r < 100 && g < 100 && b > 200) return 'blue';
      if (r > 200 && g > 200 && b < 100) return 'yellow';
      if (r < 100 && g > 200 && b > 200) return 'cyan';
      if (r > 200 && g < 100 && b > 200) return 'magenta';
      if (r > 200 && g > 100 && b < 100) return 'orange';
      if (r > 100 && g < 100 && b > 200) return 'purple';
      if (r > 200 && g > 100 && b > 150) return 'pink';
      if (r > 220 && g > 220 && b > 220) return 'white';
      if (r < 50 && g < 50 && b < 50) return 'black';
      if (Math.abs(r - g) < 30 && Math.abs(g - b) < 30) return 'gray';
    }
    return '';
  }

  function getTypeName(mesh) {
    if (mesh.userData && mesh.userData._type) {
      return mesh.userData._type.toLowerCase();
    }
    if (mesh.geometry) {
      const gt = mesh.geometry.type.toLowerCase();
      if (gt.includes('box')) return 'cube';
      if (gt.includes('sphere')) return 'sphere';
      if (gt.includes('cylinder')) return 'cylinder';
      if (gt.includes('cone')) return 'cone';
      if (gt.includes('torus')) return 'torus';
      if (gt.includes('plane')) return 'plane';
    }
    return '';
  }

  function findObject(name) {
    // Direct lookup
    if (objects[name]) return objects[name];

    // Case-insensitive lookup
    const lower = name.toLowerCase();
    for (const [key, obj] of Object.entries(objects)) {
      if (key.toLowerCase() === lower) return obj;
    }

    // Scene traversal fallback
    let found = null;
    scene.traverse(o => {
      if (o.name && o.name.toLowerCase() === lower) {
        found = o;
      }
    });
    return found;
  }

  // ==========================================================================
  // ADAPTER INTERFACE
  // ==========================================================================

  const adapter = {
    // Registry management
    registerObject: function(name, obj) {
      objects[name] = obj;
      if (obj.userData && obj.userData._scene) {
        scenes.add(obj.userData._scene);
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
        name: obj.name,
        object: obj,
        type: getTypeName(obj)
      };
    },

    getObjectsByType: function(typeName) {
      const results = [];
      scene.traverse(o => {
        if (o.isMesh || o.isSprite || o.isGroup) {
          const t = getTypeName(o);
          if (t === typeName || o.name === typeName || o.name.startsWith(typeName + '-')) {
            results.push({ name: o.name, object: o, type: t });
          }
        }
      });
      return results;
    },

    // Get all objects (for query syntax: get all where ...)
    getAllObjects: function() {
      const results = [];
      scene.traverse(o => {
        if ((o.isMesh || o.isSprite || o.isGroup) && o.name && !o.name.startsWith('_')) {
          results.push({ name: o.name, object: o, type: getTypeName(o) });
        }
      });
      return results;
    },

    // Deep search: find by color, size, type
    deepSearch: function(args) {
      const results = [];
      const searchTerms = args.map(a => a.toLowerCase());

      // Identify modifiers vs type
      const colorTerms = ['red', 'green', 'blue', 'yellow', 'cyan', 'magenta', 'white', 'black', 'orange', 'purple', 'pink', 'gray', 'grey', 'gold', 'silver'];
      const sizeTerms = ['big', 'large', 'small', 'tiny', 'huge'];
      const typeTerms = ['cube', 'sphere', 'cylinder', 'cone', 'torus', 'plane', 'box', 'ball'];

      let targetColor = null;
      let targetSize = null;
      let targetType = null;

      for (const term of searchTerms) {
        if (colorTerms.includes(term)) targetColor = term;
        else if (sizeTerms.includes(term)) targetSize = term;
        else if (typeTerms.includes(term)) targetType = term === 'ball' ? 'sphere' : term === 'box' ? 'cube' : term;
        else targetType = term; // Assume unknown terms are type names
      }

      scene.traverse(o => {
        if (!o.isMesh && !o.isSprite) return;

        const objType = getTypeName(o);
        const objColor = getColorName(o);

        // Type match
        if (targetType && objType !== targetType && !o.name.startsWith(targetType)) return;

        // Color match
        if (targetColor && objColor !== targetColor) return;

        // Size match (based on scale)
        if (targetSize) {
          const scale = Math.max(o.scale.x, o.scale.y, o.scale.z);
          if (targetSize === 'big' || targetSize === 'large' || targetSize === 'huge') {
            if (scale < 1.5) return;
          } else if (targetSize === 'small' || targetSize === 'tiny') {
            if (scale > 0.7) return;
          }
        }

        results.push({ name: o.name, object: o, type: objType, color: objColor });
      });

      return { success: true, objects: results };
    },

    // Object creation
    createObject: function(typeName, name, options = {}) {
      const objName = name || generateName(typeName);
      const modifiers = options.modifiers || [];

      // Determine geometry
      let geometry, material;
      const color = modifiers.find(m => COLOR_MAP[m]) || 'gray';
      const colorHex = COLOR_MAP[color] || 0x888888;

      switch (typeName) {
        case 'sphere':
        case 'ball':
          geometry = new THREE.SphereGeometry(0.5, 32, 32);
          break;
        case 'cylinder':
          geometry = new THREE.CylinderGeometry(0.5, 0.5, 1, 32);
          break;
        case 'cone':
          geometry = new THREE.ConeGeometry(0.5, 1, 32);
          break;
        case 'torus':
          geometry = new THREE.TorusGeometry(0.4, 0.15, 16, 48);
          break;
        case 'plane':
          geometry = new THREE.PlaneGeometry(1, 1);
          break;
        case 'cube':
        case 'box':
        default:
          geometry = new THREE.BoxGeometry(1, 1, 1);
          typeName = 'cube';
      }

      material = new THREE.MeshStandardMaterial({ color: colorHex });
      const mesh = new THREE.Mesh(geometry, material);

      mesh.name = objName;
      mesh.userData._type = typeName;
      mesh.userData._color = color;
      mesh.userData._roshId = objName;
      mesh.userData.fixed = false;  // Console-created objects affected by physics

      // Random position to avoid stacking
      mesh.position.set(
        (Math.random() - 0.5) * 4,
        0.5,
        (Math.random() - 0.5) * 4
      );

      scene.add(mesh);
      objects[objName] = mesh;

      return { success: true, name: objName, object: mesh };
    },

    // Object deletion
    deleteObject: function(name) {
      const obj = findObject(name);
      if (!obj) return { success: false, error: 'Object not found: ' + name };

      scene.remove(obj);
      delete objects[name];

      // Dispose geometry and material
      if (obj.geometry) obj.geometry.dispose();
      if (obj.material) {
        if (Array.isArray(obj.material)) {
          obj.material.forEach(m => m.dispose());
        } else {
          obj.material.dispose();
        }
      }

      return { success: true };
    },

    // Object restoration (for undo)
    restoreObject: function(name, savedState) {
      // Re-add to scene
      if (savedState.object) {
        scene.add(savedState.object);
        objects[name] = savedState.object;
        return { success: true };
      }
      return { success: false, error: 'Cannot restore object' };
    },

    // Object cloning
    cloneObject: function(name) {
      const obj = findObject(name);
      if (!obj) return { success: false, error: 'Object not found: ' + name };

      const typeName = getTypeName(obj) || 'object';
      const newName = generateName(typeName);
      const clone = obj.clone();

      clone.name = newName;
      clone.userData._roshId = newName;

      // Offset position
      clone.position.x += 1;

      scene.add(clone);
      objects[newName] = clone;

      return { success: true, name: newName, object: clone };
    },

    // Property access
    getProperty: function(name, prop) {
      const obj = findObject(name);
      if (!obj) return undefined;

      switch (prop.toLowerCase()) {
        case 'x': return obj.position.x;
        case 'y': return obj.position.y;
        case 'z': return obj.position.z;
        case 'visible': return obj.visible;
        case 'color':
          return obj.material && obj.material.color
            ? '#' + obj.material.color.getHexString()
            : undefined;
        case 'scale':
          return obj.scale.x;
        default:
          return obj.userData[prop];
      }
    },

    setProperty: function(name, prop, value) {
      const obj = findObject(name);
      if (!obj) return { success: false, error: 'Object not found: ' + name };

      const lower = prop.toLowerCase();

      switch (lower) {
        case 'x':
          obj.position.x = parseFloat(value);
          break;
        case 'y':
          obj.position.y = parseFloat(value);
          break;
        case 'z':
          obj.position.z = parseFloat(value);
          break;
        case 'visible':
          obj.visible = value === 'true' || value === true || value === '1';
          break;
        case 'color':
          if (obj.material && obj.material.color) {
            const c = parseColor(value);
            if (c !== null) {
              obj.material.color.setHex(c);
              obj.userData._color = value;
            }
          }
          break;
        case 'scale':
          const s = parseFloat(value);
          obj.scale.set(s, s, s);
          break;
        case 'scene':
          obj.userData._scene = value;
          scenes.add(value);
          break;
        case 'font_size':
          const fontSize = parseFloat(value);
          obj.userData.font_size = fontSize;
          // Re-render canvas texture if this is a text sprite
          if (obj._ctx && obj._canvas && obj.material && obj.material.map) {
            obj._ctx.clearRect(0, 0, obj._canvas.width, obj._canvas.height);
            obj._ctx.font = 'bold ' + fontSize + 'px ' + (obj._font || 'Arial');
            obj._ctx.fillStyle = obj._color || '#ffffff';
            obj._ctx.textAlign = 'center';
            obj._ctx.textBaseline = 'middle';
            obj._ctx.fillText(obj._text || '', obj._canvas.width / 2, obj._canvas.height / 2);
            obj.material.map.needsUpdate = true;
          }
          break;
        case 'text':
          obj._text = value;
          // Re-render canvas texture
          if (obj._ctx && obj._canvas && obj.material && obj.material.map) {
            const fs = obj.userData.font_size || 48;
            obj._ctx.clearRect(0, 0, obj._canvas.width, obj._canvas.height);
            obj._ctx.font = 'bold ' + fs + 'px ' + (obj._font || 'Arial');
            obj._ctx.fillStyle = obj._color || '#ffffff';
            obj._ctx.textAlign = 'center';
            obj._ctx.textBaseline = 'middle';
            obj._ctx.fillText(value, obj._canvas.width / 2, obj._canvas.height / 2);
            obj.material.map.needsUpdate = true;
          }
          break;
        default:
          obj.userData[lower] = value;
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
      return { x: obj.position.x, y: obj.position.y, z: obj.position.z };
    },

    moveObject: function(name, pos) {
      const obj = findObject(name);
      if (!obj) return { success: false, error: 'Object not found: ' + name };
      if (pos.x !== undefined) obj.position.x = pos.x;
      if (pos.y !== undefined) obj.position.y = pos.y;
      if (pos.z !== undefined) obj.position.z = pos.z;
      return { success: true };
    },

    moveObjectRelative: function(name, direction, amount) {
      const obj = findObject(name);
      if (!obj) return { success: false, error: 'Object not found: ' + name };

      switch (direction) {
        case 'forward': obj.position.z -= amount; break;
        case 'back':
        case 'backward': obj.position.z += amount; break;
        case 'left': obj.position.x -= amount; break;
        case 'right': obj.position.x += amount; break;
        case 'up': obj.position.y += amount; break;
        case 'down': obj.position.y -= amount; break;
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
        position: { x: obj.position.x.toFixed(2), y: obj.position.y.toFixed(2), z: obj.position.z.toFixed(2) },
        scale: { x: obj.scale.x.toFixed(2), y: obj.scale.y.toFixed(2), z: obj.scale.z.toFixed(2) },
        visible: obj.visible,
        scene: obj.userData._scene || '(default)'
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
      // Check if scene exists
      if (!scenes.has(sceneName)) {
        // Fuzzy match
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

      // Update visibility based on scene
      scene.traverse(o => {
        if (o.userData && o.userData._scene) {
          o.visible = (o.userData._scene === currentScene);
        }
      });

      return { success: true, scene: currentScene };
    },

    // Object counting
    countObjects: function(typeName) {
      if (!typeName) {
        return Object.keys(objects).length;
      }
      let count = 0;
      scene.traverse(o => {
        const t = getTypeName(o);
        if (t === typeName || o.name === typeName || o.name.startsWith(typeName + '-')) {
          count++;
        }
      });
      return count;
    },

    // Save/Load
    saveGame: function(slot) {
      const state = {};
      for (const [name, obj] of Object.entries(objects)) {
        state[name] = {
          type: getTypeName(obj),
          color: getColorName(obj),
          position: { x: obj.position.x, y: obj.position.y, z: obj.position.z },
          scale: { x: obj.scale.x, y: obj.scale.y, z: obj.scale.z },
          visible: obj.visible,
          userData: { ...obj.userData }
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
        // Clear current objects
        for (const name of Object.keys(objects)) {
          adapter.deleteObject(name);
        }
        // Recreate objects
        for (const [name, data] of Object.entries(state)) {
          adapter.createObject(data.type, name, { modifiers: [data.color] });
          const obj = objects[name];
          if (obj) {
            obj.position.set(data.position.x, data.position.y, data.position.z);
            obj.scale.set(data.scale.x, data.scale.y, data.scale.z);
            obj.visible = data.visible;
            Object.assign(obj.userData, data.userData);
          }
        }
        return true;
      } catch (e) {
        console.error('Failed to load game:', e);
        return false;
      }
    },

    // ========================================================================
    // GRAVITY SYSTEM (ThreeJS-first)
    // ========================================================================

    enableGravity: function(strength) {
      gravityEnabled = true;
      if (strength !== undefined) gravityStrength = strength;
      return { success: true, gravity: gravityStrength };
    },

    disableGravity: function() {
      gravityEnabled = false;
      objectVelocities.clear();
      return { success: true };
    },

    isGravityEnabled: function() {
      return gravityEnabled;
    },

    setGroundLevel: function(level) {
      groundLevel = level;
      return { success: true, ground: groundLevel };
    },

    // Set gravity on specific object (userData.gravity = true/false)
    setObjectGravity: function(name, enabled) {
      const obj = findObject(name);
      if (!obj) return { success: false, error: 'Object not found: ' + name };
      obj.userData.gravity = enabled;
      if (!enabled) objectVelocities.delete(name);
      return { success: true };
    },

    // ========================================================================
    // CLICK-TO-MOVE SYSTEM (ThreeJS-first)
    // ========================================================================

    enableClickToMove: function(playerName) {
      clickToMoveEnabled = true;
      playerObjectName = playerName || null;

      // Create invisible ground plane for raycasting if needed
      if (!groundPlane) {
        const groundGeo = new THREE.PlaneGeometry(1000, 1000);
        const groundMat = new THREE.MeshBasicMaterial({ visible: false });
        groundPlane = new THREE.Mesh(groundGeo, groundMat);
        groundPlane.rotation.x = -Math.PI / 2;
        groundPlane.position.y = groundLevel;
        groundPlane.name = '_rosh_ground_plane';
        scene.add(groundPlane);
      }

      return { success: true, player: playerObjectName };
    },

    disableClickToMove: function() {
      clickToMoveEnabled = false;
      moveTarget = null;
      return { success: true };
    },

    isClickToMoveEnabled: function() {
      return clickToMoveEnabled;
    },

    setMoveSpeed: function(speed) {
      moveSpeed = speed;
      return { success: true, speed: moveSpeed };
    },

    setPlayer: function(name) {
      playerObjectName = name;
      return { success: true, player: playerObjectName };
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
        position: { x: selectedObject.position.x, y: selectedObject.position.y, z: selectedObject.position.z },
        fixed: selectedObject.userData.fixed || false
      };
    },

    selectByName: function(name) {
      const obj = findObject(name);
      if (obj) {
        return selectObject(obj);
      }
      return null;
    },

    deselect: function() {
      deselectObject();
      return { success: true };
    },

    // ========================================================================
    // EDIT MODE (enables selection and object control)
    // ========================================================================

    enableEditMode: function() {
      editMode = true;
      window.editMode = true;  // Sync with global for animate loop
      return { success: true, editMode: true };
    },

    disableEditMode: function() {
      editMode = false;
      window.editMode = false;  // Sync with global for animate loop
      deselectObject();  // Clear selection when leaving edit mode
      return { success: true, editMode: false };
    },

    isEditMode: function() {
      return editMode;
    },

    // ========================================================================
    // PHYSICS UPDATE (call from animation loop)
    // ========================================================================

    update: function(deltaTime) {
      if (!deltaTime) deltaTime = 1/60;  // Default 60fps

      // Apply gravity to objects
      if (gravityEnabled) {
        for (const [name, obj] of Object.entries(objects)) {
          // Skip text/hud/sprites (never affected by gravity)
          const kind = obj.userData._rosh_kind;
          if (kind === 'text' || kind === 'hud' || kind === 'sprite') continue;
          // Skip fixed objects or objects with gravity disabled
          if (obj.userData.fixed === true) continue;
          if (obj.userData.gravity === false) continue;

          // Get or initialize velocity
          let vel = objectVelocities.get(name) || 0;

          // Apply gravity
          vel -= gravityStrength * deltaTime;

          // Update position
          obj.position.y += vel * deltaTime;

          // Ground collision
          const objHeight = obj.geometry ? (obj.geometry.parameters?.height || 1) / 2 : 0.5;
          const minY = groundLevel + objHeight;
          if (obj.position.y < minY) {
            obj.position.y = minY;
            vel = 0;  // Stop falling
          }

          objectVelocities.set(name, vel);
        }
      }

      // Move player toward target
      if (clickToMoveEnabled && moveTarget && playerObjectName) {
        const player = findObject(playerObjectName);
        if (player) {
          const dx = moveTarget.x - player.position.x;
          const dz = moveTarget.z - player.position.z;
          const dist = Math.sqrt(dx * dx + dz * dz);

          if (dist > 0.1) {
            // Move toward target
            const step = moveSpeed * deltaTime;
            if (step >= dist) {
              // Reached target
              player.position.x = moveTarget.x;
              player.position.z = moveTarget.z;
              moveTarget = null;
            } else {
              // Move proportionally
              player.position.x += (dx / dist) * step;
              player.position.z += (dz / dist) * step;
            }
          } else {
            moveTarget = null;
          }
        }
      }

      // Arrow key movement for player (when keyboard enabled)
      if (playerKeyboardEnabled && playerObjectName) {
        const player = findObject(playerObjectName);
        if (player) {
          const step = moveSpeed * deltaTime;
          if (playerKeyState.left) player.position.x -= step;
          if (playerKeyState.right) player.position.x += step;
          if (playerKeyState.forward) player.position.z -= step;
          if (playerKeyState.back) player.position.z += step;
          if (playerKeyState.up) player.position.y += step;      // Space = up
          if (playerKeyState.down) player.position.y -= step;    // Shift = down
        }
      }
    }
  };

  // ========================================================================
  // CLICK HANDLER (internal)
  // ========================================================================

  function selectObject(obj) {
    // Deselect previous
    if (selectedObject && selectedObject !== obj) {
      deselectObject();
    }

    if (!obj) return;

    selectedObject = obj;
    window.selectedObject = obj;  // Sync with global for animate loop

    // Visual highlight - add emissive glow
    if (obj.material) {
      selectedOriginalEmissive = obj.material.emissive ? obj.material.emissive.getHex() : 0;
      if (obj.material.emissive) {
        obj.material.emissive.setHex(0x333333);
      }
    }

    return obj.name;
  }

  function deselectObject() {
    if (selectedObject && selectedObject.material && selectedObject.material.emissive) {
      selectedObject.material.emissive.setHex(selectedOriginalEmissive || 0);
    }
    selectedObject = null;
    window.selectedObject = null;  // Sync with global for animate loop
    selectedOriginalEmissive = null;
  }

  function handleClick(event) {
    // Don't handle clicks when console is open or edit mode is off
    if (window.consoleVisible) return;
    if (!editMode) return;

    // Calculate mouse position in normalized device coordinates
    const rect = renderer.domElement.getBoundingClientRect();
    mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

    // Cast ray from camera
    raycaster.setFromCamera(mouse, camera);

    // First, check for object intersection (click-to-select)
    const clickableObjects = Object.values(objects).filter(o => o.visible);
    const objectIntersects = raycaster.intersectObjects(clickableObjects, false);

    if (objectIntersects.length > 0) {
      const hitObject = objectIntersects[0].object;
      const name = selectObject(hitObject);
      // Log selection to console if available
      if (window.roshLog) {
        window.roshLog('Selected: ' + name, 'ok');
      }
      return;  // Don't process ground click if we hit an object
    }

    // If no object hit, deselect current
    if (selectedObject) {
      deselectObject();
      if (window.roshLog) {
        window.roshLog('Deselected', 'dim');
      }
    }

    // Check intersection with ground plane (click-to-move)
    if (clickToMoveEnabled && groundPlane) {
      const intersects = raycaster.intersectObject(groundPlane);
      if (intersects.length > 0) {
        const point = intersects[0].point;
        moveTarget = { x: point.x, z: point.z };
      }
    }
  }

  // Register click handler immediately
  renderer.domElement.addEventListener('click', handleClick);

  // ========================================================================
  // PLAYER KEYBOARD MOVEMENT (internal)
  // ========================================================================

  function setupPlayerKeyboard() {
    window.addEventListener('keydown', (e) => {
      // Don't capture keys when console is open
      if (window.consoleVisible) return;

      switch (e.key) {
        case 'ArrowLeft': playerKeyState.left = true; break;
        case 'ArrowRight': playerKeyState.right = true; break;
        case 'ArrowUp': playerKeyState.forward = true; break;
        case 'ArrowDown': playerKeyState.back = true; break;
        case '/': playerKeyState.up = true; e.preventDefault(); break;    // / = up
        case '.': playerKeyState.down = true; break;                      // . = down
      }
    });

    window.addEventListener('keyup', (e) => {
      switch (e.key) {
        case 'ArrowLeft': playerKeyState.left = false; break;
        case 'ArrowRight': playerKeyState.right = false; break;
        case 'ArrowUp': playerKeyState.forward = false; break;
        case 'ArrowDown': playerKeyState.back = false; break;
        case '/': playerKeyState.up = false; break;
        case '.': playerKeyState.down = false; break;
      }
    });
  }

  // Add enablePlayerKeyboard method to adapter
  adapter.enablePlayerKeyboard = function(playerName) {
    playerKeyboardEnabled = true;
    if (playerName) playerObjectName = playerName;
    setupPlayerKeyboard();
    return { success: true, player: playerObjectName };
  };

  adapter.disablePlayerKeyboard = function() {
    playerKeyboardEnabled = false;
    playerKeyState.left = playerKeyState.right = playerKeyState.forward = playerKeyState.back = false;
    return { success: true };
  };

  return adapter;
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = createThreeJSAdapter;
}
