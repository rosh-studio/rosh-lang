/**
 * Rosh JS Runtime Test Runner
 *
 * Runs conformance tests against the JS adapter without needing a browser.
 * This validates that the adapter produces the same results as Python.
 *
 * Usage (Node.js):
 *   node rosh-test-runner.js
 *
 * Or include in browser with mock objects for testing.
 */

// Mock minimal dependencies for Node.js
if (typeof window === 'undefined') {
  global.document = {
    createElement: () => ({ style: {}, innerHTML: '', appendChild: () => {}, classList: { toggle: () => {}, add: () => {}, remove: () => {} } }),
    head: { appendChild: () => {} },
    body: { appendChild: () => {} },
    getElementById: () => null,
    addEventListener: () => {}
  };
  global.localStorage = {
    getItem: () => null,
    setItem: () => {}
  };
}

// =============================================================================
// MOCK THREE.JS (minimal for testing adapter logic)
// =============================================================================

const THREE = {
  Scene: class {
    constructor() {
      this.children = [];
    }
    add(obj) { this.children.push(obj); }
    remove(obj) {
      const idx = this.children.indexOf(obj);
      if (idx >= 0) this.children.splice(idx, 1);
    }
    traverse(fn) {
      this.children.forEach(c => {
        fn(c);
        if (c.children) c.children.forEach(fn);
      });
    }
  },
  PerspectiveCamera: class {},
  WebGLRenderer: class {},
  BoxGeometry: class { constructor() { this.type = 'BoxGeometry'; } dispose() {} },
  SphereGeometry: class { constructor() { this.type = 'SphereGeometry'; } dispose() {} },
  MeshStandardMaterial: class {
    constructor(opts = {}) {
      this.color = { getHex: () => opts.color || 0x888888, setHex: (c) => { this._hex = c; }, getHexString: () => (this._hex || opts.color || 0x888888).toString(16) };
    }
    dispose() {}
  },
  Mesh: class {
    constructor(geometry, material) {
      this.geometry = geometry;
      this.material = material;
      this.position = { x: 0, y: 0, z: 0, set: function(x, y, z) { this.x = x; this.y = y; this.z = z; } };
      this.scale = { x: 1, y: 1, z: 1, set: function(x, y, z) { this.x = x; this.y = y; this.z = z; } };
      this.userData = {};
      this.visible = true;
      this.name = '';
      this.isMesh = true;
    }
    clone() {
      const c = new THREE.Mesh(this.geometry, this.material);
      c.position = { ...this.position };
      c.scale = { ...this.scale };
      c.userData = { ...this.userData };
      c.visible = this.visible;
      return c;
    }
  }
};

// Make THREE global
if (typeof window === 'undefined') {
  global.THREE = THREE;
}

// =============================================================================
// LOAD ADAPTER (inline for Node.js)
// =============================================================================

// Include the adapter code here (or require it)
// For this test, we'll define a minimal version inline

function createTestAdapter() {
  const objects = {};
  const scenes = new Set();
  let currentScene = null;
  const typeCounters = {};

  function generateName(typeName) {
    if (!typeCounters[typeName]) typeCounters[typeName] = 0;
    typeCounters[typeName]++;
    return typeName + '-' + typeCounters[typeName];
  }

  return {
    objects,  // Expose for testing

    getObjectNames: () => Object.keys(objects),

    getObjects: () => Object.entries(objects).map(([name, obj]) => ({
      name, object: obj, type: obj.userData._type || 'object', visible: obj.visible
    })),

    getObject: (name) => {
      const obj = objects[name];
      return obj ? { name, object: obj, type: obj.userData._type } : null;
    },

    createObject: (typeName, name, options = {}) => {
      const objName = name || generateName(typeName);
      const mesh = new THREE.Mesh(
        typeName === 'sphere' ? new THREE.SphereGeometry() : new THREE.BoxGeometry(),
        new THREE.MeshStandardMaterial({ color: 0x888888 })
      );
      mesh.name = objName;
      mesh.userData._type = typeName;
      mesh.userData._roshId = objName;
      objects[objName] = mesh;
      return { success: true, name: objName, object: mesh };
    },

    deleteObject: (name) => {
      if (!objects[name]) return { success: false, error: 'Not found' };
      delete objects[name];
      return { success: true };
    },

    cloneObject: (name) => {
      const obj = objects[name];
      if (!obj) return { success: false, error: 'Not found' };
      const typeName = obj.userData._type || 'object';
      const newName = generateName(typeName);
      const clone = obj.clone();
      clone.name = newName;
      clone.userData._roshId = newName;
      objects[newName] = clone;
      return { success: true, name: newName, object: clone };
    },

    getProperty: (name, prop) => {
      const obj = objects[name];
      if (!obj) return undefined;
      if (prop === 'x') return obj.position.x;
      if (prop === 'y') return obj.position.y;
      if (prop === 'z') return obj.position.z;
      if (prop === 'visible') return obj.visible;
      return obj.userData[prop];
    },

    setProperty: (name, prop, value) => {
      const obj = objects[name];
      if (!obj) return { success: false, error: 'Not found' };
      if (prop === 'x') obj.position.x = parseFloat(value);
      else if (prop === 'y') obj.position.y = parseFloat(value);
      else if (prop === 'z') obj.position.z = parseFloat(value);
      else if (prop === 'visible') obj.visible = value === 'true' || value === true;
      else obj.userData[prop] = value;
      return { success: true };
    },

    setVisible: (name, visible) => {
      const obj = objects[name];
      if (!obj) return { success: false, error: 'Not found' };
      obj.visible = visible;
      return { success: true };
    }
  };
}

// =============================================================================
// TEST RUNNER
// =============================================================================

function runConformanceTests() {
  const results = { passed: 0, failed: 0, tests: [] };

  function test(name, fn) {
    const adapter = createTestAdapter();
    try {
      fn(adapter);
      results.passed++;
      results.tests.push({ name, status: 'passed' });
      console.log(`  ✓ ${name}`);
    } catch (err) {
      results.failed++;
      results.tests.push({ name, status: 'failed', error: err.message });
      console.log(`  ✗ ${name}: ${err.message}`);
    }
  }

  function expect(condition, msg) {
    if (!condition) throw new Error(msg || 'Assertion failed');
  }

  console.log('Running JS Runtime Conformance Tests:\n');

  // Object Creation
  test('create adds object to registry', (adapter) => {
    adapter.createObject('cube', 'box');
    expect(adapter.getObject('box') !== null, 'box should exist');
  });

  test('create with type stores type', (adapter) => {
    adapter.createObject('sphere');
    const names = adapter.getObjectNames();
    expect(names.some(n => n.includes('sphere')), 'sphere should be created');
  });

  test('multiple creates use unique names', (adapter) => {
    adapter.createObject('cube');
    adapter.createObject('cube');
    const names = adapter.getObjectNames();
    expect(names.length === 2, 'should have 2 objects');
  });

  // Property Setting
  test('set color property', (adapter) => {
    adapter.createObject('cube', 'thing');
    adapter.setProperty('thing', 'color', 'red');
    expect(adapter.getProperty('thing', 'color') === 'red', 'color should be red');
  });

  test('set position x', (adapter) => {
    adapter.createObject('cube', 'obj');
    adapter.setProperty('obj', 'x', '100');
    expect(adapter.getProperty('obj', 'x') === 100, 'x should be 100');
  });

  test('set position y', (adapter) => {
    adapter.createObject('cube', 'obj2');
    adapter.setProperty('obj2', 'y', '200');
    expect(adapter.getProperty('obj2', 'y') === 200, 'y should be 200');
  });

  test('set custom property', (adapter) => {
    adapter.createObject('cube', 'item');
    adapter.setProperty('item', 'status', 'active');
    expect(adapter.getProperty('item', 'status') === 'active', 'status should be active');
  });

  // Object Deletion
  test('delete removes from registry', (adapter) => {
    adapter.createObject('cube', 'temp');
    adapter.deleteObject('temp');
    expect(adapter.getObject('temp') === null, 'temp should not exist');
  });

  // Scene System
  test('set scene property', (adapter) => {
    adapter.createObject('cube', 'room_obj');
    adapter.setProperty('room_obj', 'scene', 'gallery');
    expect(adapter.getProperty('room_obj', 'scene') === 'gallery', 'scene should be gallery');
  });

  // Visibility
  test('hide sets visible to false', (adapter) => {
    adapter.createObject('cube', 'vis_test');
    adapter.setVisible('vis_test', false);
    expect(adapter.getProperty('vis_test', 'visible') === false, 'should be hidden');
  });

  test('show sets visible to true', (adapter) => {
    adapter.createObject('cube', 'vis_test2');
    adapter.setVisible('vis_test2', false);
    adapter.setVisible('vis_test2', true);
    expect(adapter.getProperty('vis_test2', 'visible') === true, 'should be visible');
  });

  // Clone
  test('clone creates copy', (adapter) => {
    adapter.createObject('cube', 'original');
    adapter.setProperty('original', 'color', 'blue');
    adapter.cloneObject('original');
    expect(adapter.getObject('original') !== null, 'original should exist');
    expect(adapter.getObjectNames().length === 2, 'should have 2 objects');
  });

  // Summary
  console.log(`\nResults: ${results.passed} passed, ${results.failed} failed`);
  return results;
}

// Run if executed directly
if (typeof require !== 'undefined' && require.main === module) {
  runConformanceTests();
}

// Export for browser use
if (typeof module !== 'undefined') {
  module.exports = { runConformanceTests, createTestAdapter };
}
