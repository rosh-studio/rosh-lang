/**
 * Three.js Adapter for Rosh Runtime
 *
 * =============================================================================
 * LAYER 3: Engine-Specific Adapter (of 3 layers)
 * =============================================================================
 *
 * Implements the adapter interface for Three.js scenes.
 * This is the thin layer between Rosh 3D Runtime and Three.js.
 *
 * Requires: rosh-core.js, rosh-3d.js loaded first
 * Usage: const runtime = new Rosh3DRuntime(new ThreeJSAdapter(scene, camera, renderer));
 *
 * =============================================================================
 * KEY DOCUMENTS - READ BEFORE MODIFYING
 * =============================================================================
 * - rosh-dev/proposals/IR-VERSIONING-POLICY.md - Python is source of truth
 * - rosh-dev/proposals/JS-RUNTIME-ARCHITECTURE.md - This three-layer design
 * - src/rosh/runtime/PYTHON-SYNC.md - Feature sync tracking
 *
 * THREE-LAYER ARCHITECTURE:
 *   Layer 1: rosh-core.js - Base REPL shell
 *   Layer 2: rosh-3d.js - 3D object commands
 *   Layer 3: threejs-adapter.js (this file) - Three.js rendering
 *
 * This adapter should be THIN (~200-400 lines). All REPL logic belongs in
 * rosh-core.js or rosh-3d.js, NOT here.
 * =============================================================================
 *
 * @version 0.1.1
 * @implements IR 0.1.1
 */

const THREEJS_ADAPTER_VERSION = "0.1.1";

class ThreeJSAdapter {
    constructor(scene, camera, renderer) {
        this.scene = scene;
        this.camera = camera;
        this.renderer = renderer;

        // Track objects by name for fast lookup
        this.objectsByName = new Map();

        // Default colors for new objects
        this.colorIndex = 0;
        this.defaultColors = [
            0x00ff00, 0x0000ff, 0xff0000, 0xffff00,
            0xff00ff, 0x00ffff, 0xff8800, 0x8800ff,
        ];
    }

    // =========================================================================
    // Required Adapter Interface
    // =========================================================================

    getObject(name) {
        // Try direct lookup first
        if (this.objectsByName.has(name)) {
            return this.objectsByName.get(name);
        }
        // Fall back to scene search
        return this.scene.getObjectByName(name) || null;
    }

    getAllObjects() {
        const objects = [];
        this.scene.traverse((obj) => {
            // Include meshes AND sprites with names (not internal objects)
            if ((obj.isMesh || obj.isSprite) && obj.name && !obj.name.startsWith('_')) {
                objects.push(obj);
            }
        });
        return objects;
    }

    createObject(type, name, props = {}) {
        // Get next default color
        const color = props.color || this.defaultColors[this.colorIndex++ % this.defaultColors.length];

        // Check if this should be a text object
        const isText = type.toLowerCase() === 'text' || type.toLowerCase() === 'label' || props.text !== undefined;

        let obj;
        if (isText) {
            // Create text sprite
            obj = this.createTextSprite(props.text || name, props);
        } else {
            // Default geometry based on type
            let geometry;
            switch (type.toLowerCase()) {
                case 'sphere':
                case 'ball':
                    geometry = new THREE.SphereGeometry(25, 32, 32);
                    break;
                case 'plane':
                case 'floor':
                case 'ground':
                    geometry = new THREE.PlaneGeometry(100, 100);
                    break;
                case 'cylinder':
                    geometry = new THREE.CylinderGeometry(25, 25, 50, 32);
                    break;
                default:
                    // Default to box/cube
                    geometry = new THREE.BoxGeometry(50, 50, 50);
            }

            const material = new THREE.MeshStandardMaterial({ color });
            obj = new THREE.Mesh(geometry, material);
        }

        obj.name = name;
        obj.userData._type = type;
        obj.userData._created = Date.now();
        obj.userData._isText = isText;

        // Default position: center of scene, above ground
        // (ground is at y=0, camera looks at origin)
        obj.position.set(0, 50, 0);

        // Apply position if provided
        if (props.x !== undefined) this.setProperty(obj, 'x', props.x);
        if (props.y !== undefined) this.setProperty(obj, 'y', props.y);
        if (props.z !== undefined) this.setProperty(obj, 'z', props.z);

        this.scene.add(obj);
        this.objectsByName.set(name, obj);

        return obj;
    }

    createTextSprite(text, props = {}) {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');

        // Font settings
        const fontSize = props.font_size || 48;
        const fontFamily = props.font || 'Arial, sans-serif';
        ctx.font = `bold ${fontSize}px ${fontFamily}`;

        // Measure text
        const metrics = ctx.measureText(text);
        const textWidth = metrics.width;
        const textHeight = fontSize * 1.2;

        // Size canvas to fit text with padding
        canvas.width = Math.ceil(textWidth + 20);
        canvas.height = Math.ceil(textHeight + 10);

        // Re-set font after resize
        ctx.font = `bold ${fontSize}px ${fontFamily}`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';

        // Draw text
        const colorHex = props.color || 0x00ff00;
        const colorStr = '#' + (typeof colorHex === 'number' ? colorHex.toString(16).padStart(6, '0') : 'ffffff');
        ctx.fillStyle = colorStr;
        ctx.fillText(text, canvas.width / 2, canvas.height / 2);

        // Create sprite
        const texture = new THREE.CanvasTexture(canvas);
        texture.needsUpdate = true;
        const material = new THREE.SpriteMaterial({ map: texture, transparent: true });
        const sprite = new THREE.Sprite(material);

        // Scale sprite based on text size
        const scale = fontSize / 10;
        sprite.scale.set(canvas.width / 10 * scale / fontSize * 10, canvas.height / 10 * scale / fontSize * 10, 1);

        // Store text properties for updates
        sprite.userData._text = text;
        sprite.userData._fontSize = fontSize;
        sprite.userData._canvas = canvas;
        sprite.userData._ctx = ctx;

        return sprite;
    }

    updateTextSprite(sprite, text, props = {}) {
        if (!sprite.userData._canvas) return;

        const canvas = sprite.userData._canvas;
        const ctx = sprite.userData._ctx;
        const fontSize = props.font_size || sprite.userData._fontSize || 48;

        // Clear and redraw
        ctx.font = `bold ${fontSize}px Arial, sans-serif`;
        const metrics = ctx.measureText(text);
        canvas.width = Math.ceil(metrics.width + 20);
        canvas.height = Math.ceil(fontSize * 1.2 + 10);

        ctx.font = `bold ${fontSize}px Arial, sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';

        const colorHex = props.color || sprite.material.map?.userData?._color || 0x00ff00;
        const colorStr = '#' + (typeof colorHex === 'number' ? colorHex.toString(16).padStart(6, '0') : 'ffffff');
        ctx.fillStyle = colorStr;
        ctx.fillText(text, canvas.width / 2, canvas.height / 2);

        // Update texture
        sprite.material.map.needsUpdate = true;

        // Update scale
        const scale = fontSize / 10;
        sprite.scale.set(canvas.width / 10 * scale / fontSize * 10, canvas.height / 10 * scale / fontSize * 10, 1);

        sprite.userData._text = text;
        sprite.userData._fontSize = fontSize;
    }

    deleteObject(obj) {
        if (!obj) return;
        const name = obj.name;
        if (obj.parent) {
            obj.parent.remove(obj);
        } else {
            this.scene.remove(obj);
        }
        this.objectsByName.delete(name);

        // Dispose geometry and material
        if (obj.geometry) obj.geometry.dispose();
        if (obj.material) {
            if (Array.isArray(obj.material)) {
                obj.material.forEach(m => m.dispose());
            } else {
                obj.material.dispose();
            }
        }
    }

    setProperty(obj, prop, value) {
        if (!obj) return;

        // Helper to resolve percentage values
        const resolveValue = (v, axis) => {
            if (v && typeof v === 'object' && v.percent !== undefined) {
                // Store original percentage intent
                obj.userData['_' + axis + '_pct'] = v.percent;
                // For 3D, treat percentage as fraction of scene bounds (±250)
                return (v.normalized - 0.5) * 500;
            }
            return v;
        };

        switch (prop) {
            case 'x':
                obj.position.x = resolveValue(value, 'x');
                break;
            case 'y':
                obj.position.y = resolveValue(value, 'y');
                break;
            case 'z':
                obj.position.z = resolveValue(value, 'z');
                break;
            case 'color':
                obj.userData._color = value;
                if (obj.userData._isText && obj.userData._text) {
                    // Update text sprite with new color
                    this.updateTextSprite(obj, obj.userData._text, {
                        font_size: obj.userData._fontSize,
                        color: value
                    });
                } else if (obj.material && obj.material.color) {
                    obj.material.color.setHex(value);
                }
                break;
            case 'scale':
                obj.scale.setScalar(value);
                break;
            case 'visible':
                obj.visible = !!value;
                break;
            case 'rotation':
            case 'rotation_y':
                obj.rotation.y = value;
                break;
            case 'rotation_x':
                obj.rotation.x = value;
                break;
            case 'rotation_z':
                obj.rotation.z = value;
                break;
            case 'text':
                obj.userData.text = value;
                if (obj.userData._isText) {
                    this.updateTextSprite(obj, value, {
                        font_size: obj.userData._fontSize,
                        color: obj.userData._color
                    });
                }
                break;
            case 'font_size':
                obj.userData.font_size = value;
                obj.userData._fontSize = value;
                if (obj.userData._isText && obj.userData._text) {
                    this.updateTextSprite(obj, obj.userData._text, {
                        font_size: value,
                        color: obj.userData._color
                    });
                }
                break;
            default:
                // Store in userData for custom properties
                obj.userData[prop] = value;
        }
    }

    getProperty(obj, prop) {
        if (!obj) return undefined;

        // Check for stored percentage values first
        const pctKey = '_' + prop + '_pct';
        if (obj.userData[pctKey] !== undefined) {
            return { percent: obj.userData[pctKey], normalized: obj.userData[pctKey] / 100 };
        }

        switch (prop) {
            case 'x':
                return obj.position.x;
            case 'y':
                return obj.position.y;
            case 'z':
                return obj.position.z;
            case 'color':
                return obj.material?.color?.getHex();
            case 'scale':
                return obj.scale.x;
            case 'visible':
                return obj.visible;
            case 'rotation':
            case 'rotation_y':
                return obj.rotation.y;
            case 'rotation_x':
                return obj.rotation.x;
            case 'rotation_z':
                return obj.rotation.z;
            default:
                return obj.userData?.[prop];
        }
    }

    getObjectName(obj) {
        return obj?.name || 'unnamed';
    }

    getObjectType(obj) {
        return obj?.userData?._type || obj?.geometry?.type?.replace('Geometry', '').toLowerCase() || 'object';
    }

    getObjectPosition(obj) {
        if (!obj) return { x: 0, y: 0, z: 0 };
        // Return percentages if stored, otherwise actual values
        const getVal = (axis) => {
            const pctKey = '_' + axis + '_pct';
            if (obj.userData[pctKey] !== undefined) {
                return { percent: obj.userData[pctKey], normalized: obj.userData[pctKey] / 100 };
            }
            return obj.position[axis];
        };
        return {
            x: getVal('x'),
            y: getVal('y'),
            z: getVal('z')
        };
    }

    setObjectPosition(obj, x, y, z) {
        if (!obj) return;
        obj.position.set(x, y, z);
    }

    setObjectVisible(obj, visible) {
        if (!obj) return;
        obj.visible = visible;
    }

    setObjectColor(obj, color) {
        if (!obj || !obj.material || !obj.material.color) return;
        obj.material.color.setHex(color);
    }

    getObjectColor(obj) {
        if (!obj || !obj.material || !obj.material.color) return undefined;
        return obj.material.color.getHex();
    }

    setObjectScale(obj, scale) {
        if (!obj) return;
        obj.scale.setScalar(scale);
    }

    getObjectScale(obj) {
        if (!obj) return 1;
        return obj.scale.x;
    }

    // =========================================================================
    // Three.js Specific Helpers
    // =========================================================================

    findByType(typeName) {
        const results = [];
        this.scene.traverse((obj) => {
            if (obj.isMesh) {
                const type = this.getObjectType(obj);
                const name = obj.name;
                if (type === typeName || name === typeName || name.startsWith(typeName + '-')) {
                    results.push(obj);
                }
            }
        });
        return results;
    }

    resetCamera() {
        this.camera.position.set(0, 100, 300);
        this.camera.lookAt(0, 0, 0);
    }
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { ThreeJSAdapter, THREEJS_ADAPTER_VERSION };
}
