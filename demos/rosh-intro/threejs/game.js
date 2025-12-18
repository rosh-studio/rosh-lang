// Auto-generated from Rosh IR
// Emitter: Three.js v0.2.0
// Three.js and OrbitControls loaded via HTML template

// Scene Setup
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x1a1a2e);

// Camera
const camera = new THREE.PerspectiveCamera(50, 800 / 600, 0.1, 1000);
camera.position.set(0, 5, 50);
camera.lookAt(0, 0, 0);

// Renderer
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(window.devicePixelRatio);
document.body.appendChild(renderer.domElement);

// OrbitControls
const controls = new THREE.OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.05;

// Keyboard controls
const moveState = { forward: false, backward: false, left: false, right: false, up: false, down: false };
const arrowState = { left: false, right: false, up: false, down: false, rise: false, fall: false };
document.addEventListener('keydown', (e) => {
    if (consoleVisible) return;
    // WASD + QE for camera
    if (e.key === 'w' || e.key === 'W') moveState.forward = true;
    if (e.key === 's' || e.key === 'S') moveState.backward = true;
    if (e.key === 'a' || e.key === 'A') moveState.left = true;
    if (e.key === 'd' || e.key === 'D') moveState.right = true;
    if (e.key === 'q' || e.key === 'Q') moveState.down = true;
    if (e.key === 'e' || e.key === 'E') moveState.up = true;
    // Arrow keys + ./  for player objects
    if (e.key === 'ArrowLeft') arrowState.left = true;
    if (e.key === 'ArrowRight') arrowState.right = true;
    if (e.key === 'ArrowUp') arrowState.up = true;
    if (e.key === 'ArrowDown') arrowState.down = true;
    if (e.key === '.') arrowState.rise = true;
    if (e.key === '/') arrowState.fall = true;
});
document.addEventListener('keyup', (e) => {
    if (e.key === 'w' || e.key === 'W') moveState.forward = false;
    if (e.key === 's' || e.key === 'S') moveState.backward = false;
    if (e.key === 'a' || e.key === 'A') moveState.left = false;
    if (e.key === 'd' || e.key === 'D') moveState.right = false;
    if (e.key === 'q' || e.key === 'Q') moveState.down = false;
    if (e.key === 'e' || e.key === 'E') moveState.up = false;
    if (e.key === 'ArrowLeft') arrowState.left = false;
    if (e.key === 'ArrowRight') arrowState.right = false;
    if (e.key === 'ArrowUp') arrowState.up = false;
    if (e.key === 'ArrowDown') arrowState.down = false;
    if (e.key === '.') arrowState.rise = false;
    if (e.key === '/') arrowState.fall = false;
});

// Lighting
const ambientLight = new THREE.AmbientLight(0x404040, 0.5);
scene.add(ambientLight);
const directionalLight = new THREE.DirectionalLight(0xffffff, 1);
directionalLight.position.set(5, 10, 7);
scene.add(directionalLight);

// Ground grid
const gridHelper = new THREE.GridHelper(100, 50, 0x444466, 0x333355);
gridHelper.position.y = -1;
scene.add(gridHelper);

let consoleVisible = false;

// Game Objects
// Object: logo
const logoCanvas = document.createElement('canvas');
const logoCtx = logoCanvas.getContext('2d');
logoCanvas.width = 1024;
logoCanvas.height = 256;
logoCtx.fillStyle = '#00ffff';
logoCtx.font = 'bold 48px Arial';
logoCtx.textAlign = 'center';
logoCtx.textBaseline = 'middle';
logoCtx.fillText('rosh', 512, 128);
const logoTexture = new THREE.CanvasTexture(logoCanvas);
const logoMaterial = new THREE.SpriteMaterial({ map: logoTexture, transparent: true });
const logo = new THREE.Sprite(logoMaterial);
logo.position.set(0.00, 2.64, 0.00);
logo.scale.set(20, 5, 1);
logo.name = 'logo';
logo._canvas = logoCanvas;
logo._ctx = logoCtx;
logo._text = 'rosh';
logo._color = '#00ffff';
scene.add(logo);
logo.userData.font_size = 8;
logo.userData._rosh_uuid = crypto.randomUUID();

// Object: tagline
const taglineCanvas = document.createElement('canvas');
const taglineCtx = taglineCanvas.getContext('2d');
taglineCanvas.width = 1024;
taglineCanvas.height = 256;
taglineCtx.fillStyle = '#888888';
taglineCtx.font = 'bold 48px Arial';
taglineCtx.textAlign = 'center';
taglineCtx.textBaseline = 'middle';
taglineCtx.fillText('happy coding', 512, 128);
const taglineTexture = new THREE.CanvasTexture(taglineCanvas);
const taglineMaterial = new THREE.SpriteMaterial({ map: taglineTexture, transparent: true });
const tagline = new THREE.Sprite(taglineMaterial);
tagline.position.set(0.00, 0.96, 0.00);
tagline.scale.set(20, 5, 1);
tagline.name = 'tagline';
tagline._canvas = taglineCanvas;
tagline._ctx = taglineCtx;
tagline._text = 'happy coding';
tagline._color = '#888888';
scene.add(tagline);
tagline.userData.font_size = 1;
tagline.userData._rosh_uuid = crypto.randomUUID();

// Object: state
const stateGeometry = new THREE.BoxGeometry(0.80, 0.80, 0.80);
const stateMaterial = new THREE.MeshStandardMaterial({ color: 0xff0000 });
const state = new THREE.Mesh(stateGeometry, stateMaterial);
state.position.set(0.00, 2.00, 0.00);
state.name = 'state';
scene.add(state);
state.userData.phase = 1;
state.userData.logo_done = false;
state.userData.tagline_done = false;
state.userData._rosh_uuid = crypto.randomUUID();


// Event Handlers
function handle_update() {
    if (state.userData.phase == 1) {
    if (logo.userData.font_size < 128) {
    logo.userData.font_size = (logo.userData.font_size + 3);
} else {
    state.userData.phase = 2;
    tagline.visible = true;
}
}
    if (state.userData.phase == 2) {
    if (tagline.userData.font_size < 28) {
    tagline.userData.font_size = (tagline.userData.font_size + 1);
} else {
    state.userData.phase = 3;
}
}
}

// Animation Loop
function animate() {
    requestAnimationFrame(animate);

    handle_update();

    // WASD camera movement (disabled when console open)
    if (!consoleVisible) {
        const moveSpeed = 0.5;
        if (moveState.forward) { camera.position.z -= moveSpeed; controls.target.z -= moveSpeed; }
        if (moveState.backward) { camera.position.z += moveSpeed; controls.target.z += moveSpeed; }
        if (moveState.left) { camera.position.x -= moveSpeed; controls.target.x -= moveSpeed; }
        if (moveState.right) { camera.position.x += moveSpeed; controls.target.x += moveSpeed; }
        if (moveState.up) { camera.position.y += moveSpeed; controls.target.y += moveSpeed; }
        if (moveState.down) { camera.position.y -= moveSpeed; controls.target.y -= moveSpeed; }
        if (camera.position.y < 1) { camera.position.y = 1; }
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

// ==================================================
// ROSH CONSOLE - Press ` to toggle
// ==================================================

const consoleStyle = document.createElement('style');
consoleStyle.textContent = `
#rosh-console { position: fixed; bottom: 0; left: 0; width: 100%; height: 250px;
  background: rgba(0,0,0,0.95); color: #0f0; font-family: monospace; font-size: 14px;
  border-top: 2px solid #0f0; display: none; flex-direction: column; z-index: 10000; }
#rosh-console.visible { display: flex; }
#rosh-output { flex: 1; overflow-y: auto; padding: 10px; }
#rosh-output .cmd { color: #ff0; } #rosh-output .ok { color: #3f3; }
#rosh-output .err { color: #f33; } #rosh-output .cyan { color: #0ff; }
#rosh-input-line { padding: 10px; border-top: 1px solid #0f0; display: flex; gap: 8px; }
#rosh-input-line input { flex: 1; background: #111; border: 1px solid #0f0;
  color: #0f0; padding: 8px; font-family: inherit; }
`;
document.head.appendChild(consoleStyle);

const consoleDiv = document.createElement('div');
consoleDiv.id = 'rosh-console';
consoleDiv.innerHTML = `
  <div style='padding:8px;background:#111;border-bottom:1px solid #0f0'>
    <strong>ROSH CONSOLE</strong> <small style='color:#888'>Press \` to toggle</small>
  </div>
  <div id='rosh-output'></div>
  <div id='rosh-input-line'>
    <span style='color:#0f0'>rosh></span>
    <input type='text' id='rosh-input' placeholder='help for commands' autocomplete='off'>
  </div>`;
document.body.appendChild(consoleDiv);

const output = document.getElementById('rosh-output');
const input = document.getElementById('rosh-input');
let currentObject = null, currentObjectName = null;

function log(msg, cls='') {
    const div = document.createElement('div'); div.className = cls;
    div.textContent = msg; output.appendChild(div); output.scrollTop = output.scrollHeight;
}

function toggleConsole() {
    consoleVisible = !consoleVisible;
    consoleDiv.classList.toggle('visible', consoleVisible);
    if (consoleVisible) input.focus();
}

function execCommand(cmd) {
    log('> ' + cmd, 'cmd');
    const parts = cmd.trim().toLowerCase().split(/\s+/);
    try {
        if (parts[0] === 'help') {
            log('Commands: list, get, set, inspect, save, load, camera reset', 'cyan');
        }
        else if (parts[0] === 'list') {
            log('Objects:', 'cyan');
            scene.traverse(o => { if (o.name && !o.name.startsWith('_')) log('  ' + o.name); });
        }
        else if (parts[0] === 'get' && parts[1]) {
            const obj = scene.getObjectByName(parts[1]);
            if (obj) { currentObject = obj; currentObjectName = parts[1]; log('<object: ' + parts[1] + '>', 'ok'); }
            else log('Not found: ' + parts[1], 'err');
        }
        else if (parts[0] === 'set' && parts.length >= 3) {
            let obj, prop, val;
            if (parts.length === 3 && currentObject) { obj = currentObject; prop = parts[1]; val = parts[2]; }
            else { obj = scene.getObjectByName(parts[1]); prop = parts[2]; val = parts[3]; }
            if (!obj) { log('No object', 'err'); return; }
            if (!isNaN(val)) val = parseFloat(val);
            if (prop === 'x') obj.position.x = val;
            else if (prop === 'y') obj.position.y = val;
            else if (prop === 'z') obj.position.z = val;
            else if (prop === 'visible') obj.visible = val === 'true';
            else if (prop === 'color' && obj.material) obj.material.color.set(val);
            else obj.userData[prop] = val;
            log('OK', 'ok');
        }
        else if ((parts[0] === 'inspect' || parts[0] === 'look') && parts[1]) {
            const obj = scene.getObjectByName(parts[1]);
            if (obj) {
                log(parts[1] + ':', 'cyan');
                log('  pos: [' + obj.position.x.toFixed(1) + ',' + obj.position.y.toFixed(1) + ',' + obj.position.z.toFixed(1) + ']');
                if (obj.material && obj.material.color) log('  color: #' + obj.material.color.getHexString());
            } else log('Not found', 'err');
        }
        else if (parts[0] === 'camera' && parts[1] === 'reset') {
            camera.position.set(0, 5, 50); controls.target.set(0, 0, 0); log('Camera reset', 'ok');
        }
        else if (parts[0] === 'save') {
            const slot = parts[1] || 'default';
            const saveData = {};
            scene.traverse(o => {
                if (o.name && !o.name.startsWith('_')) {
                    const data = { x: o.position.x, y: o.position.y, z: o.position.z, ...o.userData };
                    if (o.material && o.material.color) data._color = o.material.color.getHex();
                    if (o.scale) { data._sx = o.scale.x; data._sy = o.scale.y; data._sz = o.scale.z; }
                    if (o.visible !== undefined) data._visible = o.visible;
                    saveData[o.name] = data;
                }
            });
            localStorage.setItem('rosh_save_' + slot, JSON.stringify(saveData));
            log('Game saved to slot: ' + slot, 'ok');
        }
        else if (parts[0] === 'load') {
            const slot = parts[1] || 'default';
            const json = localStorage.getItem('rosh_save_' + slot);
            if (!json) { log('No save found in slot: ' + slot, 'err'); return; }
            const saveData = JSON.parse(json);
            for (const [name, data] of Object.entries(saveData)) {
                const obj = scene.getObjectByName(name);
                if (obj) {
                    if (data.x !== undefined) obj.position.x = data.x;
                    if (data.y !== undefined) obj.position.y = data.y;
                    if (data.z !== undefined) obj.position.z = data.z;
                    if (data._color !== undefined && obj.material) obj.material.color.setHex(data._color);
                    if (data._sx !== undefined && obj.scale) { obj.scale.x = data._sx; obj.scale.y = data._sy; obj.scale.z = data._sz; }
                    if (data._visible !== undefined) obj.visible = data._visible;
                    Object.assign(obj.userData, data);
                }
            }
            log('Game loaded from slot: ' + slot, 'ok');
        }
        else if (parts[0] === 'clear') { output.innerHTML = ''; }
        else if (cmd.trim()) log('Unknown: ' + parts[0], 'err');
    } catch(e) { log('Error: ' + e.message, 'err'); }
}

document.addEventListener('keydown', e => {
    if (e.key === '`') { e.preventDefault(); toggleConsole(); }
});

input.addEventListener('keydown', e => {
    if (e.key === 'Enter' && input.value.trim()) {
        execCommand(input.value); input.value = '';
    }
});

log('Rosh Console ready! Type help for commands.', 'cyan');