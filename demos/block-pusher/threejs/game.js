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
    // Game key events
    if (e.key === ' ' || e.code === 'Space') {
        if (state.userData.level == 0) {
    title.visible = false;
    subtitle.visible = false;
    instructions.visible = false;
    start_text.visible = false;
    player.visible = true;
    box1.visible = true;
    goal1.visible = true;
    level_text.visible = true;
    moves_text.visible = true;
    // TODO: call
}
        if (state.userData.level == 1) {
    if (win_text.userData.visible == true) {
    // TODO: call
}
}
    }
    if (e.key === 'ArrowLeft') {
        if (state.userData.level > 0) {
    if (state.userData.level < 3) {
    if (win_text.userData.visible == false) {
    if (player.position.x > 250) {
    state.userData.can_move = 1;
    if ((player.position.x - 50) == wall1.position.x) {
    if (player.position.y == wall1.position.y) {
    state.userData.can_move = 0;
}
}
    if (state.userData.can_move == 1) {
    if (player.position.x == (box1.position.x + 50)) {
    if (player.position.y == box1.position.y) {
    state.userData.can_move = 1;
    if ((box1.position.x - 50) == wall1.position.x) {
    if (box1.position.y == wall1.position.y) {
    state.userData.can_move = 0;
}
}
    if (state.userData.can_move == 1) {
    if (box1.position.x > 250) {
    box1.position.x = (box1.position.x - 50);
    player.position.x = (player.position.x - 50);
    state.userData.moves = (state.userData.moves + 1);
}
}
} else {
    player.position.x = (player.position.x - 50);
    state.userData.moves = (state.userData.moves + 1);
}
} else {
    player.position.x = (player.position.x - 50);
    state.userData.moves = (state.userData.moves + 1);
}
}
}
}
}
}
        // TODO: call
        // TODO: call
    }
    if (e.key === 'ArrowRight') {
        if (state.userData.level > 0) {
    if (state.userData.level < 3) {
    if (win_text.userData.visible == false) {
    if (player.position.x < 550) {
    state.userData.can_move = 1;
    if ((player.position.x + 50) == wall1.position.x) {
    if (player.position.y == wall1.position.y) {
    state.userData.can_move = 0;
}
}
    if (state.userData.can_move == 1) {
    if (player.position.x == (box1.position.x - 50)) {
    if (player.position.y == box1.position.y) {
    state.userData.can_move = 1;
    if ((box1.position.x + 50) == wall1.position.x) {
    if (box1.position.y == wall1.position.y) {
    state.userData.can_move = 0;
}
}
    if (state.userData.can_move == 1) {
    if (box1.position.x < 550) {
    box1.position.x = (box1.position.x + 50);
    player.position.x = (player.position.x + 50);
    state.userData.moves = (state.userData.moves + 1);
}
}
} else {
    player.position.x = (player.position.x + 50);
    state.userData.moves = (state.userData.moves + 1);
}
} else {
    player.position.x = (player.position.x + 50);
    state.userData.moves = (state.userData.moves + 1);
}
}
}
}
}
}
        // TODO: call
        // TODO: call
    }
    if (e.key === 'ArrowUp') {
        if (state.userData.level > 0) {
    if (state.userData.level < 3) {
    if (win_text.userData.visible == false) {
    if (player.position.y > 200) {
    state.userData.can_move = 1;
    if ((player.position.y - 50) == wall1.position.y) {
    if (player.position.x == wall1.position.x) {
    state.userData.can_move = 0;
}
}
    if (state.userData.can_move == 1) {
    if (player.position.y == (box1.position.y + 50)) {
    if (player.position.x == box1.position.x) {
    state.userData.can_move = 1;
    if ((box1.position.y - 50) == wall1.position.y) {
    if (box1.position.x == wall1.position.x) {
    state.userData.can_move = 0;
}
}
    if (state.userData.can_move == 1) {
    if (box1.position.y > 200) {
    box1.position.y = (box1.position.y - 50);
    player.position.y = (player.position.y - 50);
    state.userData.moves = (state.userData.moves + 1);
}
}
} else {
    player.position.y = (player.position.y - 50);
    state.userData.moves = (state.userData.moves + 1);
}
} else {
    player.position.y = (player.position.y - 50);
    state.userData.moves = (state.userData.moves + 1);
}
}
}
}
}
}
        // TODO: call
        // TODO: call
    }
    if (e.key === 'ArrowDown') {
        if (state.userData.level > 0) {
    if (state.userData.level < 3) {
    if (win_text.userData.visible == false) {
    if (player.position.y < 400) {
    state.userData.can_move = 1;
    if ((player.position.y + 50) == wall1.position.y) {
    if (player.position.x == wall1.position.x) {
    state.userData.can_move = 0;
}
}
    if (state.userData.can_move == 1) {
    if (player.position.y == (box1.position.y - 50)) {
    if (player.position.x == box1.position.x) {
    state.userData.can_move = 1;
    if ((box1.position.y + 50) == wall1.position.y) {
    if (box1.position.x == wall1.position.x) {
    state.userData.can_move = 0;
}
}
    if (state.userData.can_move == 1) {
    if (box1.position.y < 400) {
    box1.position.y = (box1.position.y + 50);
    player.position.y = (player.position.y + 50);
    state.userData.moves = (state.userData.moves + 1);
}
}
} else {
    player.position.y = (player.position.y + 50);
    state.userData.moves = (state.userData.moves + 1);
}
} else {
    player.position.y = (player.position.y + 50);
    state.userData.moves = (state.userData.moves + 1);
}
}
}
}
}
}
        // TODO: call
        // TODO: call
    }
    if (e.key === 'r' || e.key === 'R') {
        // TODO: call
    }
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
let currentScene = null;
let currentLevel = 1;

// Texture loader
const textureLoader = new THREE.TextureLoader();

// Game Objects
// Object: title
const titleCanvas = document.createElement('canvas');
const titleCtx = titleCanvas.getContext('2d');
titleCanvas.width = 1024;
titleCanvas.height = 256;
titleCtx.fillStyle = '#ffffff';
titleCtx.font = 'bold 48px Arial';
titleCtx.textAlign = 'center';
titleCtx.textBaseline = 'middle';
titleCtx.fillText('Block Pusher', 512, 128);
const titleTexture = new THREE.CanvasTexture(titleCanvas);
const titleMaterial = new THREE.SpriteMaterial({ map: titleTexture, transparent: true });
const title = new THREE.Sprite(titleMaterial);
title.position.set(0.00, 4.00, 0.00);
title.scale.set(20, 5, 1);
title.name = 'title';
title._canvas = titleCanvas;
title._ctx = titleCtx;
title._text = 'Block Pusher';
title._color = '#ffffff';
scene.add(title);
title.userData.font_size = 48;
title.userData._rosh_uuid = crypto.randomUUID();

// Object: subtitle
const subtitleCanvas = document.createElement('canvas');
const subtitleCtx = subtitleCanvas.getContext('2d');
subtitleCanvas.width = 1024;
subtitleCanvas.height = 256;
subtitleCtx.fillStyle = '#888888';
subtitleCtx.font = 'bold 48px Arial';
subtitleCtx.textAlign = 'center';
subtitleCtx.textBaseline = 'middle';
subtitleCtx.fillText('A Sokoban Puzzle Game', 512, 128);
const subtitleTexture = new THREE.CanvasTexture(subtitleCanvas);
const subtitleMaterial = new THREE.SpriteMaterial({ map: subtitleTexture, transparent: true });
const subtitle = new THREE.Sprite(subtitleMaterial);
subtitle.position.set(0.00, 2.96, 0.00);
subtitle.scale.set(20, 5, 1);
subtitle.name = 'subtitle';
subtitle._canvas = subtitleCanvas;
subtitle._ctx = subtitleCtx;
subtitle._text = 'A Sokoban Puzzle Game';
subtitle._color = '#888888';
scene.add(subtitle);
subtitle.userData.font_size = 24;
subtitle.userData._rosh_uuid = crypto.randomUUID();

// Object: instructions
const instructionsCanvas = document.createElement('canvas');
const instructionsCtx = instructionsCanvas.getContext('2d');
instructionsCanvas.width = 1024;
instructionsCanvas.height = 256;
instructionsCtx.fillStyle = '#00ffff';
instructionsCtx.font = 'bold 48px Arial';
instructionsCtx.textAlign = 'center';
instructionsCtx.textBaseline = 'middle';
instructionsCtx.fillText('Push all boxes onto the circles', 512, 128);
const instructionsTexture = new THREE.CanvasTexture(instructionsCanvas);
const instructionsMaterial = new THREE.SpriteMaterial({ map: instructionsTexture, transparent: true });
const instructions = new THREE.Sprite(instructionsMaterial);
instructions.position.set(0.00, 1.60, 0.00);
instructions.scale.set(20, 5, 1);
instructions.name = 'instructions';
instructions._canvas = instructionsCanvas;
instructions._ctx = instructionsCtx;
instructions._text = 'Push all boxes onto the circles';
instructions._color = '#00ffff';
scene.add(instructions);
instructions.userData.font_size = 18;
instructions.userData._rosh_uuid = crypto.randomUUID();

// Object: start_text
const start_textCanvas = document.createElement('canvas');
const start_textCtx = start_textCanvas.getContext('2d');
start_textCanvas.width = 1024;
start_textCanvas.height = 256;
start_textCtx.fillStyle = '#ffff00';
start_textCtx.font = 'bold 48px Arial';
start_textCtx.textAlign = 'center';
start_textCtx.textBaseline = 'middle';
start_textCtx.fillText('Press SPACE to start', 512, 128);
const start_textTexture = new THREE.CanvasTexture(start_textCanvas);
const start_textMaterial = new THREE.SpriteMaterial({ map: start_textTexture, transparent: true });
const start_text = new THREE.Sprite(start_textMaterial);
start_text.position.set(0.00, -0.40, 0.00);
start_text.scale.set(20, 5, 1);
start_text.name = 'start_text';
start_text._canvas = start_textCanvas;
start_text._ctx = start_textCtx;
start_text._text = 'Press SPACE to start';
start_text._color = '#ffff00';
scene.add(start_text);
start_text.userData.font_size = 20;
start_text.userData._rosh_uuid = crypto.randomUUID();

// Object: player
const playerTexture = textureLoader.load('assets/player.png');
const playerGeometry = new THREE.PlaneGeometry(0.80, 1.07);
const playerMaterial = new THREE.MeshBasicMaterial({ map: playerTexture, transparent: true, side: THREE.DoubleSide });
const player = new THREE.Mesh(playerGeometry, playerMaterial);
player.position.set(-2.50, 2.33, 0.00);
player.name = 'player';
scene.add(player);
player.userData._rosh_uuid = crypto.randomUUID();

// Object: box1
const box1Geometry = new THREE.BoxGeometry(0.80, 1.07, 0.80);
const box1Material = new THREE.MeshStandardMaterial({ color: 0x00ffff });
const box1 = new THREE.Mesh(box1Geometry, box1Material);
box1.position.set(-0.50, 2.33, 0.00);
box1.name = 'box1';
scene.add(box1);
box1.userData._rosh_uuid = crypto.randomUUID();

// Object: goal1
const goal1Geometry = new THREE.BoxGeometry(0.88, 1.17, 0.80);
const goal1Material = new THREE.MeshStandardMaterial({ color: 0xff8800 });
const goal1 = new THREE.Mesh(goal1Geometry, goal1Material);
goal1.position.set(1.50, 2.33, 0.00);
goal1.name = 'goal1';
scene.add(goal1);
goal1.userData._rosh_uuid = crypto.randomUUID();

// Object: wall1
const wall1Geometry = new THREE.BoxGeometry(0.80, 1.07, 0.80);
const wall1Material = new THREE.MeshStandardMaterial({ color: 0x8800ff });
const wall1 = new THREE.Mesh(wall1Geometry, wall1Material);
wall1.position.set(1.50, 1.67, 0.00);
wall1.name = 'wall1';
scene.add(wall1);
wall1.userData._rosh_uuid = crypto.randomUUID();

// Object: level_text
const level_textCanvas = document.createElement('canvas');
const level_textCtx = level_textCanvas.getContext('2d');
level_textCanvas.width = 1024;
level_textCanvas.height = 256;
level_textCtx.fillStyle = '#ffffff';
level_textCtx.font = 'bold 48px Arial';
level_textCtx.textAlign = 'center';
level_textCtx.textBaseline = 'middle';
level_textCtx.fillText('Level 1', 512, 128);
const level_textTexture = new THREE.CanvasTexture(level_textCanvas);
const level_textMaterial = new THREE.SpriteMaterial({ map: level_textTexture, transparent: true });
const level_text = new THREE.Sprite(level_textMaterial);
level_text.position.set(0.00, 5.36, 0.00);
level_text.scale.set(20, 5, 1);
level_text.name = 'level_text';
level_text._canvas = level_textCanvas;
level_text._ctx = level_textCtx;
level_text._text = 'Level 1';
level_text._color = '#ffffff';
scene.add(level_text);
level_text.userData.font_size = 24;
level_text.userData._rosh_uuid = crypto.randomUUID();

// Object: moves_text
const moves_textCanvas = document.createElement('canvas');
const moves_textCtx = moves_textCanvas.getContext('2d');
moves_textCanvas.width = 1024;
moves_textCanvas.height = 256;
moves_textCtx.fillStyle = '#888888';
moves_textCtx.font = 'bold 48px Arial';
moves_textCtx.textAlign = 'center';
moves_textCtx.textBaseline = 'middle';
moves_textCtx.fillText('Moves: 0', 512, 128);
const moves_textTexture = new THREE.CanvasTexture(moves_textCanvas);
const moves_textMaterial = new THREE.SpriteMaterial({ map: moves_textTexture, transparent: true });
const moves_text = new THREE.Sprite(moves_textMaterial);
moves_text.position.set(0.00, -1.36, 0.00);
moves_text.scale.set(20, 5, 1);
moves_text.name = 'moves_text';
moves_text._canvas = moves_textCanvas;
moves_text._ctx = moves_textCtx;
moves_text._text = 'Moves: 0';
moves_text._color = '#888888';
scene.add(moves_text);
moves_text.userData.font_size = 16;
moves_text.userData._rosh_uuid = crypto.randomUUID();

// Object: win_text
const win_textCanvas = document.createElement('canvas');
const win_textCtx = win_textCanvas.getContext('2d');
win_textCanvas.width = 1024;
win_textCanvas.height = 256;
win_textCtx.fillStyle = '#ffd700';
win_textCtx.font = 'bold 48px Arial';
win_textCtx.textAlign = 'center';
win_textCtx.textBaseline = 'middle';
win_textCtx.fillText('You Win!', 512, 128);
const win_textTexture = new THREE.CanvasTexture(win_textCanvas);
const win_textMaterial = new THREE.SpriteMaterial({ map: win_textTexture, transparent: true });
const win_text = new THREE.Sprite(win_textMaterial);
win_text.position.set(0.00, 2.00, 0.00);
win_text.scale.set(20, 5, 1);
win_text.name = 'win_text';
win_text._canvas = win_textCanvas;
win_text._ctx = win_textCtx;
win_text._text = 'You Win!';
win_text._color = '#ffd700';
scene.add(win_text);
win_text.userData.font_size = 64;
win_text.userData._rosh_uuid = crypto.randomUUID();

// Object: next_level_text
const next_level_textCanvas = document.createElement('canvas');
const next_level_textCtx = next_level_textCanvas.getContext('2d');
next_level_textCanvas.width = 1024;
next_level_textCanvas.height = 256;
next_level_textCtx.fillStyle = '#ffff00';
next_level_textCtx.font = 'bold 48px Arial';
next_level_textCtx.textAlign = 'center';
next_level_textCtx.textBaseline = 'middle';
next_level_textCtx.fillText('Press SPACE for next level', 512, 128);
const next_level_textTexture = new THREE.CanvasTexture(next_level_textCanvas);
const next_level_textMaterial = new THREE.SpriteMaterial({ map: next_level_textTexture, transparent: true });
const next_level_text = new THREE.Sprite(next_level_textMaterial);
next_level_text.position.set(0.00, 0.80, 0.00);
next_level_text.scale.set(20, 5, 1);
next_level_text.name = 'next_level_text';
next_level_text._canvas = next_level_textCanvas;
next_level_text._ctx = next_level_textCtx;
next_level_text._text = 'Press SPACE for next level';
next_level_text._color = '#ffff00';
scene.add(next_level_text);
next_level_text.userData.font_size = 20;
next_level_text.userData._rosh_uuid = crypto.randomUUID();

// Object: state
const stateGeometry = new THREE.BoxGeometry(0.02, 0.03, 0.80);
const stateMaterial = new THREE.MeshStandardMaterial({ color: 0xff00ff });
const state = new THREE.Mesh(stateGeometry, stateMaterial);
state.position.set(-8.00, 6.00, 0.00);
state.name = 'state';
scene.add(state);
state.userData.moves = 0;
state.userData.can_move = 1;
state.userData._level = 0;
state.userData._rosh_uuid = crypto.randomUUID();


// Scene/Level Visibility - Roshonic "Dimensions, Not Modes"
function updateSceneVisibility() {
    if (state) state.visible = (currentLevel === 0);
}

// Set initial scene/level visibility
updateSceneVisibility();

// User Functions
function start_level_1() {
    player.position.x = 0.34375;
    player.position.y = 0.4583333333333333;
    box1.position.x = 0.46875;
    box1.position.y = 0.4583333333333333;
    goal1.position.x = 0.59375;
    goal1.position.y = 0.4583333333333333;
    wall1.visible = false;
    level_text.userData.text = 'Level 1';
    state.userData.level = 1;
    state.userData.moves = 0;
    moves_text.userData.text = 'Moves: 0';
}

function start_level_2() {
    player.position.x = 0.34375;
    player.position.y = 0.5416666666666666;
    box1.position.x = 0.46875;
    box1.position.y = 0.5416666666666666;
    wall1.position.x = 0.59375;
    wall1.position.y = 0.5416666666666666;
    wall1.visible = true;
    goal1.position.x = 0.65625;
    goal1.position.y = 0.375;
    level_text.userData.text = 'Level 2';
    state.userData.level = 2;
    state.userData.moves = 0;
    moves_text.userData.text = 'Moves: 0';
    win_text.visible = false;
    next_level_text.visible = false;
}

function show_victory() {
    win_text.userData.text = 'You Win!';
    win_text.visible = true;
    next_level_text.userData.text = 'Press R to play again';
    next_level_text.visible = true;
    state.userData.level = 3;
}

function restart_level() {
    win_text.visible = false;
    next_level_text.visible = false;
    if (state.userData.level == 1) {
    // TODO: call
}
    if (state.userData.level == 2) {
    // TODO: call
}
    if (state.userData.level == 3) {
    // TODO: call
}
}

function check_win() {
    if (box1.position.x == goal1.position.x) {
    if (box1.position.y == goal1.position.y) {
    if (state.userData.level == 1) {
    win_text.userData.text = 'Level Complete!';
    win_text.visible = true;
    next_level_text.visible = true;
}
    if (state.userData.level == 2) {
    // TODO: call
}
}
}
}

function update_display() {
    moves_text.userData.text = `Moves: ${state.userData.moves}`;
}

// Animation Loop
function animate() {
    requestAnimationFrame(animate);

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
            log('Commands: list, get <obj>, set <obj> <prop> <val>, inspect <obj>, camera reset', 'cyan');
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