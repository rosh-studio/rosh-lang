// Auto-generated from Rosh code
// Transpiled with Rosh Three.js Transpiler v0.1.0
// Three.js and OrbitControls loaded via HTML template

// Scene Setup
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x1a1a2e);

// Camera (auto-generated, use OrbitControls to navigate)
const camera = new THREE.PerspectiveCamera(50, 800 / 600, 0.1, 1000);
camera.position.set(0, 5, 150);  // Start far for zoom-in effect
camera.lookAt(0, 0, 0);
let cameraZoomTarget = 50;  // Target z position
let cameraZooming = true;

// Renderer
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(window.devicePixelRatio);
document.body.appendChild(renderer.domElement);

// OrbitControls - drag to rotate, scroll to zoom
const controls = new THREE.OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.05;

// WASD movement controls + arrow key rotation
const moveState = { forward: false, backward: false, left: false, right: false, up: false, down: false, rotateLeft: false, rotateRight: false };
document.addEventListener('keydown', (e) => {
    if (e.key === 'w' || e.key === 'W') moveState.forward = true;
    if (e.key === 's' || e.key === 'S') moveState.backward = true;
    if (e.key === 'a' || e.key === 'A') moveState.left = true;
    if (e.key === 'd' || e.key === 'D') moveState.right = true;
    if (e.key === 'q' || e.key === 'Q') moveState.down = true;
    if (e.key === 'e' || e.key === 'E') moveState.up = true;
    if (e.key === 'ArrowLeft') moveState.rotateLeft = true;
    if (e.key === 'ArrowRight') moveState.rotateRight = true;
});
document.addEventListener('keyup', (e) => {
    if (e.key === 'w' || e.key === 'W') moveState.forward = false;
    if (e.key === 's' || e.key === 'S') moveState.backward = false;
    if (e.key === 'a' || e.key === 'A') moveState.left = false;
    if (e.key === 'd' || e.key === 'D') moveState.right = false;
    if (e.key === 'q' || e.key === 'Q') moveState.down = false;
    if (e.key === 'e' || e.key === 'E') moveState.up = false;
    if (e.key === 'ArrowLeft') moveState.rotateLeft = false;
    if (e.key === 'ArrowRight') moveState.rotateRight = false;
});

// Lighting (auto-generated)
const ambientLight = new THREE.AmbientLight(0x404040, 0.5);
scene.add(ambientLight);

const directionalLight = new THREE.DirectionalLight(0xffffff, 1);
directionalLight.position.set(5, 10, 7);
scene.add(directionalLight);

// Ground grid for depth perception
const gridHelper = new THREE.GridHelper(100, 50, 0x444466, 0x333355);
gridHelper.position.y = -1;
scene.add(gridHelper);

let consoleVisible = false;

// Game Objects
// Object: logo
// Text sprite: logo
const logoCanvas = document.createElement('canvas');
const logoCtx = logoCanvas.getContext('2d');
logoCanvas.width = 1024;
logoCanvas.height = 256;
logoCtx.fillStyle = '#00ffff';
logoCtx.font = 'bold 72px Arial';
logoCtx.textAlign = 'center';
logoCtx.textBaseline = 'middle';
logoCtx.fillText('rosh', 512, 128);

const logoTexture = new THREE.CanvasTexture(logoCanvas);
const logoMaterial = new THREE.SpriteMaterial({ map: logoTexture, transparent: true });
const logo = new THREE.Sprite(logoMaterial);
logo.position.set(0.0, 2.0, 0);
logo.scale.set(20, 5, 1);
logo.name = 'logo';
logo._canvas = logoCanvas;
logo._ctx = logoCtx;
logo._text = 'rosh';
logo._fontSize = 72;
logo._color = '#00ffff';
scene.add(logo);

// Object: tagline
// Text sprite: tagline
const taglineCanvas = document.createElement('canvas');
const taglineCtx = taglineCanvas.getContext('2d');
taglineCanvas.width = 1024;
taglineCanvas.height = 256;
taglineCtx.fillStyle = '#888888';
taglineCtx.font = 'bold 48px Arial';
taglineCtx.textAlign = 'center';
taglineCtx.textBaseline = 'middle';
taglineCtx.fillText('one language. many worlds.', 512, 128);

const taglineTexture = new THREE.CanvasTexture(taglineCanvas);
const taglineMaterial = new THREE.SpriteMaterial({ map: taglineTexture, transparent: true });
const tagline = new THREE.Sprite(taglineMaterial);
tagline.position.set(0.0, 0.3999999999999999, 0);
tagline.scale.set(20, 5, 1);
tagline.name = 'tagline';
tagline._canvas = taglineCanvas;
tagline._ctx = taglineCtx;
tagline._text = 'one language. many worlds.';
tagline._fontSize = 18;
tagline._color = '#888888';
scene.add(tagline);


// Animation Loop
function animate() {
    requestAnimationFrame(animate);

    if (cameraZooming) {
        const zoomSpeed = 0.02;
        camera.position.z += (cameraZoomTarget - camera.position.z) * zoomSpeed;
        if (Math.abs(camera.position.z - cameraZoomTarget) < 0.1) cameraZooming = false;
    }

    // WASD movement + arrow key rotation (disabled when console open)
    if (!consoleVisible) {
        const moveSpeed = 0.5;
        const rotateSpeed = 0.02;
        if (moveState.forward) { camera.position.z -= moveSpeed; controls.target.z -= moveSpeed; }
        if (moveState.backward) { camera.position.z += moveSpeed; controls.target.z += moveSpeed; }
        if (moveState.left) { camera.position.x -= moveSpeed; controls.target.x -= moveSpeed; }
        if (moveState.right) { camera.position.x += moveSpeed; controls.target.x += moveSpeed; }
        if (moveState.up) { camera.position.y += moveSpeed; controls.target.y += moveSpeed; }
        if (moveState.down) { camera.position.y -= moveSpeed; controls.target.y -= moveSpeed; }

        // Arrow key rotation around target (orbit)
        if (moveState.rotateLeft || moveState.rotateRight) {
            const angle = moveState.rotateLeft ? 0.03 : -0.03;
            const offset = camera.position.clone().sub(controls.target);
            offset.applyAxisAngle(new THREE.Vector3(0, 1, 0), angle);
            camera.position.copy(controls.target).add(offset);
            camera.lookAt(controls.target);
        }

        // Prevent going through floor
        if (camera.position.y < 1) { camera.position.y = 1; controls.target.y = Math.max(controls.target.y, 0); }
    }

    controls.update();
    renderer.render(scene, camera);
}

animate();

// Resize Handler
window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
});

// ============================================================
// ROSH CONSOLE - Press ` (backtick) to toggle
// ============================================================

// Console CSS
const consoleStyle = document.createElement('style');
consoleStyle.textContent = `
#rosh-console {
    position: fixed;
    bottom: 0;
    left: 0;
    width: 100%;
    height: 250px;
    background: rgba(0, 0, 0, 0.95);
    color: #00ff00;
    font-family: 'Courier New', monospace;
    font-size: 14px;
    border-top: 2px solid #00ff00;
    display: none;
    flex-direction: column;
    z-index: 10000;
}
#rosh-console.visible { display: flex; }
#rosh-output {
    flex: 1;
    overflow-y: auto;
    padding: 10px;
}
#rosh-output .cmd { color: #ffff00; }
#rosh-output .ok { color: #33ff33; }
#rosh-output .err { color: #ff3333; }
#rosh-output .info { color: #00ffff; }
#rosh-input-line {
    padding: 10px;
    border-top: 1px solid #00ff00;
    display: flex;
    gap: 8px;
}
#rosh-input-line input {
    flex: 1;
    background: #111;
    border: 1px solid #00ff00;
    color: #00ff00;
    padding: 8px;
    font-family: inherit;
    font-size: 14px;
}
`;
document.head.appendChild(consoleStyle);

// Console HTML
const consoleDiv = document.createElement('div');
consoleDiv.id = 'rosh-console';
consoleDiv.innerHTML = `
    <div style='padding:8px;background:#111;border-bottom:1px solid #00ff00'>
        <strong>🎮 ROSH CONSOLE</strong> <small style='color:#888'>Press \` to toggle | Commands: list, set, inspect, help</small>
    </div>
    <div id='rosh-output'></div>
    <div id='rosh-input-line'>
        <span style='color:#00ff00'>rosh></span>
        <input type='text' id='rosh-input' placeholder='Enter command...' autocomplete='off'>
    </div>
`;
document.body.appendChild(consoleDiv);

// Console logic
const output = document.getElementById('rosh-output');
const input = document.getElementById('rosh-input');
const commandHistory = [];
let historyIndex = -1;

function log(msg, cls = '') {
    const div = document.createElement('div');
    div.className = cls;
    div.textContent = msg;
    output.appendChild(div);
    output.scrollTop = output.scrollHeight;
}

function toggleConsole() {
    consoleVisible = !consoleVisible;
    consoleDiv.classList.toggle('visible', consoleVisible);
    if (consoleVisible) input.focus();
}

function execCommand(cmd) {
    log('> ' + cmd, 'cmd');
    try {
        const parts = cmd.trim().toLowerCase().split(/\s+/);

        if (parts[0] === 'help') {
            log('Commands:', 'info');
            log('  list objects     - Show all objects in scene');
            log('  inspect <name>   - Show object properties');
            log('  set <obj>.<prop> to <value>  - Change property');
            log('  camera reset     - Reset camera to default view');
            log('  camera <x> <y> <z> - Move camera to position');
            log('  clear            - Clear console');
        }

        else if (parts[0] === 'list') {
            log('Objects in scene:', 'info');
            scene.traverse(obj => {
                if (obj.name && !obj.name.startsWith('_')) {
                    const type = obj.isMesh ? 'mesh' : obj.isSprite ? 'sprite' : obj.isLight ? 'light' : 'object';
                    const pos = obj.position;
                    log(`  ${obj.name} (${type}) at [${pos.x.toFixed(1)}, ${pos.y.toFixed(1)}, ${pos.z.toFixed(1)}]`);
                }
            });
        }

        else if (parts[0] === 'camera') {
            if (parts[1] === 'reset') {
                camera.position.set(0, 5, 50);
                camera.lookAt(0, 0, 0);
                controls.target.set(0, 0, 0);
                log('✓ Camera reset to default view', 'ok');
            } else if (parts.length >= 4) {
                const x = parseFloat(parts[1]), y = parseFloat(parts[2]), z = parseFloat(parts[3]);
                camera.position.set(x, y, z);
                log(`✓ Camera moved to [${x}, ${y}, ${z}]`, 'ok');
            } else {
                log(`Camera at [${camera.position.x.toFixed(1)}, ${camera.position.y.toFixed(1)}, ${camera.position.z.toFixed(1)}]`, 'info');
            }
        }

        else if (parts[0] === 'inspect' && parts[1]) {
            const obj = scene.getObjectByName(parts[1]);
            if (obj) {
                log(`${parts[1]}:`, 'info');
                log(`  position: [${obj.position.x.toFixed(2)}, ${obj.position.y.toFixed(2)}, ${obj.position.z.toFixed(2)}]`);
                log(`  visible: ${obj.visible}`);
                if (obj.material && obj.material.color) {
                    log(`  color: #${obj.material.color.getHexString()}`);
                }
                // Show text sprite properties
                if (obj._fontSize) log(`  font_size: ${obj._fontSize}`);
                if (obj._text) log(`  text: "${obj._text}"`);
                if (obj._color) log(`  text_color: ${obj._color}`);
                if (obj.scale) log(`  scale: [${obj.scale.x.toFixed(1)}, ${obj.scale.y.toFixed(1)}, ${obj.scale.z.toFixed(1)}]`);
                if (obj.userData) {
                    for (const [k, v] of Object.entries(obj.userData)) {
                        log(`  ${k}: ${v}`);
                    }
                }
            } else {
                log(`Object '${parts[1]}' not found`, 'err');
            }
        }

        else if (parts[0] === 'set' && cmd.includes(' to ')) {
            // Match both dot syntax (logo.color) and natural language (logo color)
            const match = cmd.match(/set\s+(\w+)(?:\.|\s+)(\w+)\s+to\s+(.+)/i);
            if (match) {
                const [_, objName, prop, valueStr] = match;
                const obj = scene.getObjectByName(objName);
                if (!obj) { log(`Object '${objName}' not found`, 'err'); return; }
                // Security: check if object is locked
                if (obj.userData && obj.userData.locked) {
                    log(`🔒 Security: '${objName}' is locked and cannot be modified`, 'err');
                    return;
                }

                let value = valueStr.trim();
                // Parse value
                if (value === 'true') value = true;
                else if (value === 'false') value = false;
                else if (!isNaN(value)) value = parseFloat(value);

                // Apply property
                if (prop === 'x') { obj.position.x = value; log(`✓ ${objName}.x = ${value}`, 'ok'); }
                else if (prop === 'y') { obj.position.y = value; log(`✓ ${objName}.y = ${value}`, 'ok'); }
                else if (prop === 'z') { obj.position.z = value; log(`✓ ${objName}.z = ${value}`, 'ok'); }
                else if (prop === 'visible') { obj.visible = value; log(`✓ ${objName}.visible = ${value}`, 'ok'); }
                else if (prop === 'scale') { obj.scale.set(value, value, value); log(`✓ ${objName}.scale = ${value}`, 'ok'); }
                else if (prop === 'font_size') {
                    if (obj._ctx) {
                        obj._fontSize = value;
                        obj._ctx.clearRect(0, 0, obj._canvas.width, obj._canvas.height);
                        obj._ctx.fillStyle = obj._color || '#ffffff';
                        obj._ctx.font = 'bold ' + value + 'px Arial';
                        obj._ctx.textAlign = 'center';
                        obj._ctx.textBaseline = 'middle';
                        obj._ctx.fillText(obj._text || '', obj._canvas.width/2, obj._canvas.height/2);
                        obj.material.map.needsUpdate = true;
                        log(`✓ ${objName}.font_size = ${value}`, 'ok');
                    } else {
                        log(`Cannot set font_size on ${objName} (not a text object)`, 'err');
                    }
                }
                else if (prop === 'color') {
                    // Handle text sprites (canvas-based)
                    if (obj._ctx && obj._canvas) {
                        obj._color = value;
                        obj._ctx.clearRect(0, 0, obj._canvas.width, obj._canvas.height);
                        obj._ctx.fillStyle = value;
                        obj._ctx.font = 'bold ' + (obj._fontSize || 48) + 'px Arial';
                        obj._ctx.textAlign = 'center';
                        obj._ctx.textBaseline = 'middle';
                        obj._ctx.fillText(obj._text || objName, obj._canvas.width/2, obj._canvas.height/2);
                        obj.material.map.needsUpdate = true;
                        log(`✓ ${objName}.color = ${value}`, 'ok');
                    }
                    // Handle meshes with material
                    else if (obj.material && obj.material.color) {
                        obj.material.color.set(value);
                        log(`✓ ${objName}.color = ${value}`, 'ok');
                    }
                    else { log(`Cannot set color on ${objName}`, 'err'); }
                }
                else {
                    const knownProps = ['x', 'y', 'z', 'visible', 'scale', 'color', 'font_size', 'text'];
                    if (knownProps.some(p => prop.toLowerCase().includes(p.replace('_','')))) {
                        log(`Unknown property '${prop}'. Did you mean: ${knownProps.join(', ')}?`, 'err');
                    } else {
                        log(`Unknown property '${prop}' on ${objName}`, 'err');
                    }
                }
            } else {
                log('Usage: set <object>.<property> to <value>', 'err');
            }
        }

        else if (parts[0] === 'clear') {
            output.innerHTML = '';
        }

        else if (cmd.trim()) {
            log(`Unknown command: ${parts[0]}. Type 'help' for commands.`, 'err');
        }
    } catch (e) {
        log(`Error: ${e.message}`, 'err');
    }
}

// Toggle with backtick
document.addEventListener('keydown', e => {
    if (e.key === '`') { e.preventDefault(); toggleConsole(); }
});

// Execute on Enter, history with up/down arrows
input.addEventListener('keydown', e => {
    if (e.key === 'Enter' && input.value.trim()) {
        commandHistory.push(input.value);
        historyIndex = commandHistory.length;
        execCommand(input.value);
        input.value = '';
    } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        if (historyIndex > 0) {
            historyIndex--;
            input.value = commandHistory[historyIndex];
        }
    } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        if (historyIndex < commandHistory.length - 1) {
            historyIndex++;
            input.value = commandHistory[historyIndex];
        } else {
            historyIndex = commandHistory.length;
            input.value = '';
        }
    }
});

log('🎮 Rosh Console ready! Press ` to toggle.', 'info');