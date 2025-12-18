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
    // TODO: call
}
        if (state.userData.level > 0) {
    // TODO: call
}
    }
    if (e.key === 'r' || e.key === 'R') {
        if (state.userData.level == 0) {
    if (game_over_text.userData.visible == true) {
    // TODO: call
}
}
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

// Texture loader
const textureLoader = new THREE.TextureLoader();

// Audio
const audioListener = new THREE.AudioListener();
camera.add(audioListener);
const audioLoader = new THREE.AudioLoader();
const sounds = {};
audioLoader.load('assets/lose1.ogg', (buffer) => {
    sounds['lose1_ogg'] = new THREE.Audio(audioListener);
    sounds['lose1_ogg'].setBuffer(buffer);
});
audioLoader.load('assets/lose3.ogg', (buffer) => {
    sounds['lose3_ogg'] = new THREE.Audio(audioListener);
    sounds['lose3_ogg'].setBuffer(buffer);
});

// Game Objects
// Object: title
const titleCanvas = document.createElement('canvas');
const titleCtx = titleCanvas.getContext('2d');
titleCanvas.width = 1024;
titleCanvas.height = 256;
titleCtx.fillStyle = '#00ffff';
titleCtx.font = 'bold 48px Arial';
titleCtx.textAlign = 'center';
titleCtx.textBaseline = 'middle';
titleCtx.fillText('Space Shooter', 512, 128);
const titleTexture = new THREE.CanvasTexture(titleCanvas);
const titleMaterial = new THREE.SpriteMaterial({ map: titleTexture, transparent: true });
const title = new THREE.Sprite(titleMaterial);
title.position.set(0.00, 4.00, 0.00);
title.scale.set(20, 5, 1);
title.name = 'title';
title._canvas = titleCanvas;
title._ctx = titleCtx;
title._text = 'Space Shooter';
title._color = '#00ffff';
scene.add(title);
title.userData.font_size = 48;
title.userData._rosh_uuid = crypto.randomUUID();

// Object: instructions
const instructionsCanvas = document.createElement('canvas');
const instructionsCtx = instructionsCanvas.getContext('2d');
instructionsCanvas.width = 1024;
instructionsCanvas.height = 256;
instructionsCtx.fillStyle = '#ffffff';
instructionsCtx.font = 'bold 48px Arial';
instructionsCtx.textAlign = 'center';
instructionsCtx.textBaseline = 'middle';
instructionsCtx.fillText('Arrow keys to move, SPACE to fire', 512, 128);
const instructionsTexture = new THREE.CanvasTexture(instructionsCanvas);
const instructionsMaterial = new THREE.SpriteMaterial({ map: instructionsTexture, transparent: true });
const instructions = new THREE.Sprite(instructionsMaterial);
instructions.position.set(0.00, 2.40, 0.00);
instructions.scale.set(20, 5, 1);
instructions.name = 'instructions';
instructions._canvas = instructionsCanvas;
instructions._ctx = instructionsCtx;
instructions._text = 'Arrow keys to move, SPACE to fire';
instructions._color = '#ffffff';
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
start_text.position.set(0.00, 0.40, 0.00);
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
const playerGeometry = new THREE.PlaneGeometry(1.00, 1.33);
const playerMaterial = new THREE.MeshBasicMaterial({ map: playerTexture, transparent: true, side: THREE.DoubleSide });
const player = new THREE.Mesh(playerGeometry, playerMaterial);
player.position.set(0.00, -1.20, 0.00);
player.name = 'player';
scene.add(player);
player.userData.speed = 8;
player.userData._rosh_uuid = crypto.randomUUID();

// Object: bullet1
const bullet1Texture = textureLoader.load('assets/laserGreen.png');
const bullet1Geometry = new THREE.PlaneGeometry(0.18, 0.88);
const bullet1Material = new THREE.MeshBasicMaterial({ map: bullet1Texture, transparent: true, side: THREE.DoubleSide });
const bullet1 = new THREE.Mesh(bullet1Geometry, bullet1Material);
bullet1.position.set(-8.00, 6.00, 0.00);
bullet1.name = 'bullet1';
scene.add(bullet1);
bullet1.userData.active = 0;
bullet1.userData._rosh_uuid = crypto.randomUUID();

// Object: bullet2
const bullet2Texture = textureLoader.load('assets/laserGreen.png');
const bullet2Geometry = new THREE.PlaneGeometry(0.18, 0.88);
const bullet2Material = new THREE.MeshBasicMaterial({ map: bullet2Texture, transparent: true, side: THREE.DoubleSide });
const bullet2 = new THREE.Mesh(bullet2Geometry, bullet2Material);
bullet2.position.set(-8.00, 6.00, 0.00);
bullet2.name = 'bullet2';
scene.add(bullet2);
bullet2.userData.active = 0;
bullet2.userData._rosh_uuid = crypto.randomUUID();

// Object: bullet3
const bullet3Texture = textureLoader.load('assets/laserGreen.png');
const bullet3Geometry = new THREE.PlaneGeometry(0.18, 0.88);
const bullet3Material = new THREE.MeshBasicMaterial({ map: bullet3Texture, transparent: true, side: THREE.DoubleSide });
const bullet3 = new THREE.Mesh(bullet3Geometry, bullet3Material);
bullet3.position.set(-8.00, 6.00, 0.00);
bullet3.name = 'bullet3';
scene.add(bullet3);
bullet3.userData.active = 0;
bullet3.userData._rosh_uuid = crypto.randomUUID();

// Object: bullet4
const bullet4Texture = textureLoader.load('assets/laserGreen.png');
const bullet4Geometry = new THREE.PlaneGeometry(0.18, 0.88);
const bullet4Material = new THREE.MeshBasicMaterial({ map: bullet4Texture, transparent: true, side: THREE.DoubleSide });
const bullet4 = new THREE.Mesh(bullet4Geometry, bullet4Material);
bullet4.position.set(-8.00, 6.00, 0.00);
bullet4.name = 'bullet4';
scene.add(bullet4);
bullet4.userData.active = 0;
bullet4.userData._rosh_uuid = crypto.randomUUID();

// Object: bullet5
const bullet5Texture = textureLoader.load('assets/laserGreen.png');
const bullet5Geometry = new THREE.PlaneGeometry(0.18, 0.88);
const bullet5Material = new THREE.MeshBasicMaterial({ map: bullet5Texture, transparent: true, side: THREE.DoubleSide });
const bullet5 = new THREE.Mesh(bullet5Geometry, bullet5Material);
bullet5.position.set(-8.00, 6.00, 0.00);
bullet5.name = 'bullet5';
scene.add(bullet5);
bullet5.userData.active = 0;
bullet5.userData._rosh_uuid = crypto.randomUUID();

// Object: enemy1
const enemy1Texture = textureLoader.load('assets/enemyShip.png');
const enemy1Geometry = new THREE.PlaneGeometry(0.80, 1.07);
const enemy1Material = new THREE.MeshBasicMaterial({ map: enemy1Texture, transparent: true, side: THREE.DoubleSide });
const enemy1 = new THREE.Mesh(enemy1Geometry, enemy1Material);
enemy1.position.set(-6.00, 2.00, 0.00);
enemy1.name = 'enemy1';
scene.add(enemy1);
enemy1.userData.active = 0;
enemy1.userData.speed = 2;
enemy1.userData._rosh_uuid = crypto.randomUUID();

// Object: enemy2
const enemy2Texture = textureLoader.load('assets/enemyShip.png');
const enemy2Geometry = new THREE.PlaneGeometry(0.80, 1.07);
const enemy2Material = new THREE.MeshBasicMaterial({ map: enemy2Texture, transparent: true, side: THREE.DoubleSide });
const enemy2 = new THREE.Mesh(enemy2Geometry, enemy2Material);
enemy2.position.set(-2.00, 2.00, 0.00);
enemy2.name = 'enemy2';
scene.add(enemy2);
enemy2.userData.active = 0;
enemy2.userData.speed = 2;
enemy2.userData._rosh_uuid = crypto.randomUUID();

// Object: enemy3
const enemy3Texture = textureLoader.load('assets/enemyShip.png');
const enemy3Geometry = new THREE.PlaneGeometry(0.80, 1.07);
const enemy3Material = new THREE.MeshBasicMaterial({ map: enemy3Texture, transparent: true, side: THREE.DoubleSide });
const enemy3 = new THREE.Mesh(enemy3Geometry, enemy3Material);
enemy3.position.set(2.00, 2.00, 0.00);
enemy3.name = 'enemy3';
scene.add(enemy3);
enemy3.userData.active = 0;
enemy3.userData.speed = 2;
enemy3.userData._rosh_uuid = crypto.randomUUID();

// Object: enemy4
const enemy4Texture = textureLoader.load('assets/enemyShip.png');
const enemy4Geometry = new THREE.PlaneGeometry(0.80, 1.07);
const enemy4Material = new THREE.MeshBasicMaterial({ map: enemy4Texture, transparent: true, side: THREE.DoubleSide });
const enemy4 = new THREE.Mesh(enemy4Geometry, enemy4Material);
enemy4.position.set(6.00, 2.00, 0.00);
enemy4.name = 'enemy4';
scene.add(enemy4);
enemy4.userData.active = 0;
enemy4.userData.speed = 2;
enemy4.userData._rosh_uuid = crypto.randomUUID();

// Object: score_text
const score_textCanvas = document.createElement('canvas');
const score_textCtx = score_textCanvas.getContext('2d');
score_textCanvas.width = 1024;
score_textCanvas.height = 256;
score_textCtx.fillStyle = '#ffffff';
score_textCtx.font = 'bold 48px Arial';
score_textCtx.textAlign = 'center';
score_textCtx.textBaseline = 'middle';
score_textCtx.fillText('Score: 0', 512, 128);
const score_textTexture = new THREE.CanvasTexture(score_textCanvas);
const score_textMaterial = new THREE.SpriteMaterial({ map: score_textTexture, transparent: true });
const score_text = new THREE.Sprite(score_textMaterial);
score_text.position.set(-6.60, 5.60, 0.00);
score_text.scale.set(20, 5, 1);
score_text.name = 'score_text';
score_text._canvas = score_textCanvas;
score_text._ctx = score_textCtx;
score_text._text = 'Score: 0';
score_text._color = '#ffffff';
scene.add(score_text);
score_text.userData.font_size = 20;
score_text.userData._rosh_uuid = crypto.randomUUID();

// Object: lives_text
const lives_textCanvas = document.createElement('canvas');
const lives_textCtx = lives_textCanvas.getContext('2d');
lives_textCanvas.width = 1024;
lives_textCanvas.height = 256;
lives_textCtx.fillStyle = '#00ff00';
lives_textCtx.font = 'bold 48px Arial';
lives_textCtx.textAlign = 'center';
lives_textCtx.textBaseline = 'middle';
lives_textCtx.fillText('Lives: 3', 512, 128);
const lives_textTexture = new THREE.CanvasTexture(lives_textCanvas);
const lives_textMaterial = new THREE.SpriteMaterial({ map: lives_textTexture, transparent: true });
const lives_text = new THREE.Sprite(lives_textMaterial);
lives_text.position.set(6.60, 5.60, 0.00);
lives_text.scale.set(20, 5, 1);
lives_text.name = 'lives_text';
lives_text._canvas = lives_textCanvas;
lives_text._ctx = lives_textCtx;
lives_text._text = 'Lives: 3';
lives_text._color = '#00ff00';
scene.add(lives_text);
lives_text.userData.font_size = 20;
lives_text.userData._rosh_uuid = crypto.randomUUID();

// Object: game_over_text
const game_over_textCanvas = document.createElement('canvas');
const game_over_textCtx = game_over_textCanvas.getContext('2d');
game_over_textCanvas.width = 1024;
game_over_textCanvas.height = 256;
game_over_textCtx.fillStyle = '#ff0000';
game_over_textCtx.font = 'bold 48px Arial';
game_over_textCtx.textAlign = 'center';
game_over_textCtx.textBaseline = 'middle';
game_over_textCtx.fillText('GAME OVER', 512, 128);
const game_over_textTexture = new THREE.CanvasTexture(game_over_textCanvas);
const game_over_textMaterial = new THREE.SpriteMaterial({ map: game_over_textTexture, transparent: true });
const game_over_text = new THREE.Sprite(game_over_textMaterial);
game_over_text.position.set(0.00, 2.40, 0.00);
game_over_text.scale.set(20, 5, 1);
game_over_text.name = 'game_over_text';
game_over_text._canvas = game_over_textCanvas;
game_over_text._ctx = game_over_textCtx;
game_over_text._text = 'GAME OVER';
game_over_text._color = '#ff0000';
scene.add(game_over_text);
game_over_text.userData.font_size = 48;
game_over_text.userData._rosh_uuid = crypto.randomUUID();

// Object: final_score_text
const final_score_textCanvas = document.createElement('canvas');
const final_score_textCtx = final_score_textCanvas.getContext('2d');
final_score_textCanvas.width = 1024;
final_score_textCanvas.height = 256;
final_score_textCtx.fillStyle = '#ffffff';
final_score_textCtx.font = 'bold 48px Arial';
final_score_textCtx.textAlign = 'center';
final_score_textCtx.textBaseline = 'middle';
final_score_textCtx.fillText('Final Score: 0', 512, 128);
const final_score_textTexture = new THREE.CanvasTexture(final_score_textCanvas);
const final_score_textMaterial = new THREE.SpriteMaterial({ map: final_score_textTexture, transparent: true });
const final_score_text = new THREE.Sprite(final_score_textMaterial);
final_score_text.position.set(0.00, 1.20, 0.00);
final_score_text.scale.set(20, 5, 1);
final_score_text.name = 'final_score_text';
final_score_text._canvas = final_score_textCanvas;
final_score_text._ctx = final_score_textCtx;
final_score_text._text = 'Final Score: 0';
final_score_text._color = '#ffffff';
scene.add(final_score_text);
final_score_text.userData.font_size = 24;
final_score_text.userData._rosh_uuid = crypto.randomUUID();

// Object: restart_text
const restart_textCanvas = document.createElement('canvas');
const restart_textCtx = restart_textCanvas.getContext('2d');
restart_textCanvas.width = 1024;
restart_textCanvas.height = 256;
restart_textCtx.fillStyle = '#ffff00';
restart_textCtx.font = 'bold 48px Arial';
restart_textCtx.textAlign = 'center';
restart_textCtx.textBaseline = 'middle';
restart_textCtx.fillText('Press R to restart', 512, 128);
const restart_textTexture = new THREE.CanvasTexture(restart_textCanvas);
const restart_textMaterial = new THREE.SpriteMaterial({ map: restart_textTexture, transparent: true });
const restart_text = new THREE.Sprite(restart_textMaterial);
restart_text.position.set(0.00, 0.00, 0.00);
restart_text.scale.set(20, 5, 1);
restart_text.name = 'restart_text';
restart_text._canvas = restart_textCanvas;
restart_text._ctx = restart_textCtx;
restart_text._text = 'Press R to restart';
restart_text._color = '#ffff00';
scene.add(restart_text);
restart_text.userData.font_size = 20;
restart_text.userData._rosh_uuid = crypto.randomUUID();

// Object: state
const stateGeometry = new THREE.BoxGeometry(0.02, 0.03, 0.80);
const stateMaterial = new THREE.MeshStandardMaterial({ color: 0xff0000 });
const state = new THREE.Mesh(stateGeometry, stateMaterial);
state.position.set(-8.00, 6.00, 0.00);
state.name = 'state';
scene.add(state);
state.userData.level = 0;
state.userData.score = 0;
state.userData.lives = 3;
state.userData.spawn_timer = 0;
state.userData.next_bullet = 1;
state.userData._rosh_uuid = crypto.randomUUID();


// User Functions
function start_game() {
    title.visible = false;
    instructions.visible = false;
    start_text.visible = false;
    player.visible = true;
    score_text.visible = true;
    lives_text.visible = true;
    state.userData.level = 1;
    state.userData.score = 0;
    state.userData.lives = 3;
    state.userData.spawn_timer = 0;
    player.position.x = 0.5;
    score_text.userData.text = 'Score: 0';
    lives_text.userData.text = 'Lives: 3';
    // TODO: call
}

function spawn_enemy_wave() {
    enemy1.position.x = 0.125;
    enemy1.position.y = IR_Expr(unary_op: None - IR_Expr(literal: IR_Value(number, 50)));
    enemy1.userData.active = 1;
    enemy1.visible = true;
    enemy2.position.x = 0.375;
    enemy2.position.y = IR_Expr(unary_op: None - IR_Expr(literal: IR_Value(number, 100)));
    enemy2.userData.active = 1;
    enemy2.visible = true;
    enemy3.position.x = 0.625;
    enemy3.position.y = IR_Expr(unary_op: None - IR_Expr(literal: IR_Value(number, 150)));
    enemy3.userData.active = 1;
    enemy3.visible = true;
    enemy4.position.x = 0.875;
    enemy4.position.y = IR_Expr(unary_op: None - IR_Expr(literal: IR_Value(number, 200)));
    enemy4.userData.active = 1;
    enemy4.visible = true;
}

function fire_bullet() {
    if (sounds['laser1_ogg']) { sounds['laser1_ogg'].stop(); sounds['laser1_ogg'].play(); }
    if (state.userData.next_bullet == 1) {
    if (bullet1.userData.active == 0) {
    bullet1.position.x = player.position.x;
    bullet1.position.y = (player.position.y - 30);
    bullet1.userData.active = 1;
    bullet1.visible = true;
}
    state.userData.next_bullet = 2;
}
    if (state.userData.next_bullet == 2) {
    if (bullet2.userData.active == 0) {
    bullet2.position.x = player.position.x;
    bullet2.position.y = (player.position.y - 30);
    bullet2.userData.active = 1;
    bullet2.visible = true;
}
    state.userData.next_bullet = 3;
}
    if (state.userData.next_bullet == 3) {
    if (bullet3.userData.active == 0) {
    bullet3.position.x = player.position.x;
    bullet3.position.y = (player.position.y - 30);
    bullet3.userData.active = 1;
    bullet3.visible = true;
}
    state.userData.next_bullet = 4;
}
    if (state.userData.next_bullet == 4) {
    if (bullet4.userData.active == 0) {
    bullet4.position.x = player.position.x;
    bullet4.position.y = (player.position.y - 30);
    bullet4.userData.active = 1;
    bullet4.visible = true;
}
    state.userData.next_bullet = 5;
}
    if (state.userData.next_bullet == 5) {
    if (bullet5.userData.active == 0) {
    bullet5.position.x = player.position.x;
    bullet5.position.y = (player.position.y - 30);
    bullet5.userData.active = 1;
    bullet5.visible = true;
}
    state.userData.next_bullet = 1;
}
}

function update_score() {
    score_text.userData.text = `Score: ${state.userData.score}`;
}

function update_lives() {
    lives_text.userData.text = `Lives: ${state.userData.lives}`;
    if (state.userData.lives == 0) {
    // TODO: call
}
}

function game_over() {
    state.userData.level = 0;
    player.visible = false;
    score_text.visible = false;
    lives_text.visible = false;
    bullet1.visible = false;
    bullet2.visible = false;
    bullet3.visible = false;
    bullet4.visible = false;
    bullet5.visible = false;
    enemy1.visible = false;
    enemy2.visible = false;
    enemy3.visible = false;
    enemy4.visible = false;
    game_over_text.visible = true;
    final_score_text.userData.text = `Final Score: ${state.userData.score}`;
    final_score_text.visible = true;
    restart_text.visible = true;
}

function restart_game() {
    game_over_text.visible = false;
    final_score_text.visible = false;
    restart_text.visible = false;
    bullet1.userData.active = 0;
    bullet2.userData.active = 0;
    bullet3.userData.active = 0;
    bullet4.userData.active = 0;
    bullet5.userData.active = 0;
    enemy1.userData.active = 0;
    enemy2.userData.active = 0;
    enemy3.userData.active = 0;
    enemy4.userData.active = 0;
    // TODO: call
}

// Event Handlers
function handle_update() {
    if (state.userData.level > 0) {
    if (bullet1.userData.active == 1) {
    bullet1.position.y = (bullet1.position.y - 10);
    if (bullet1.position.y < 0) {
    bullet1.userData.active = 0;
    bullet1.visible = false;
}
}
    if (bullet2.userData.active == 1) {
    bullet2.position.y = (bullet2.position.y - 10);
    if (bullet2.position.y < 0) {
    bullet2.userData.active = 0;
    bullet2.visible = false;
}
}
    if (bullet3.userData.active == 1) {
    bullet3.position.y = (bullet3.position.y - 10);
    if (bullet3.position.y < 0) {
    bullet3.userData.active = 0;
    bullet3.visible = false;
}
}
    if (bullet4.userData.active == 1) {
    bullet4.position.y = (bullet4.position.y - 10);
    if (bullet4.position.y < 0) {
    bullet4.userData.active = 0;
    bullet4.visible = false;
}
}
    if (bullet5.userData.active == 1) {
    bullet5.position.y = (bullet5.position.y - 10);
    if (bullet5.position.y < 0) {
    bullet5.userData.active = 0;
    bullet5.visible = false;
}
}
    if (enemy1.userData.active == 1) {
    enemy1.position.y = (enemy1.position.y + 2);
    if (enemy1.position.y > 650) {
    enemy1.position.y = IR_Expr(unary_op: None - IR_Expr(literal: IR_Value(number, 50)));
}
}
    if (enemy2.userData.active == 1) {
    enemy2.position.y = (enemy2.position.y + 2);
    if (enemy2.position.y > 650) {
    enemy2.position.y = IR_Expr(unary_op: None - IR_Expr(literal: IR_Value(number, 50)));
}
}
    if (enemy3.userData.active == 1) {
    enemy3.position.y = (enemy3.position.y + 2);
    if (enemy3.position.y > 650) {
    enemy3.position.y = IR_Expr(unary_op: None - IR_Expr(literal: IR_Value(number, 50)));
}
}
    if (enemy4.userData.active == 1) {
    enemy4.position.y = (enemy4.position.y + 2);
    if (enemy4.position.y > 650) {
    enemy4.position.y = IR_Expr(unary_op: None - IR_Expr(literal: IR_Value(number, 50)));
}
}
    if (bullet1.userData.active == 1) {
    if (enemy1.userData.active == 1) {
    if (bullet1.position.x > (enemy1.position.x - 20)) {
    if (bullet1.position.x < (enemy1.position.x + 20)) {
    if (bullet1.position.y > (enemy1.position.y - 20)) {
    if (bullet1.position.y < (enemy1.position.y + 20)) {
    if (sounds['lose1_ogg']) { sounds['lose1_ogg'].stop(); sounds['lose1_ogg'].play(); }
    enemy1.position.y = IR_Expr(unary_op: None - IR_Expr(literal: IR_Value(number, 50)));
    bullet1.userData.active = 0;
    bullet1.visible = false;
    state.userData.score = (state.userData.score + 10);
    // TODO: call
}
}
}
}
}
    if (enemy2.userData.active == 1) {
    if (bullet1.position.x > (enemy2.position.x - 20)) {
    if (bullet1.position.x < (enemy2.position.x + 20)) {
    if (bullet1.position.y > (enemy2.position.y - 20)) {
    if (bullet1.position.y < (enemy2.position.y + 20)) {
    if (sounds['lose1_ogg']) { sounds['lose1_ogg'].stop(); sounds['lose1_ogg'].play(); }
    enemy2.position.y = IR_Expr(unary_op: None - IR_Expr(literal: IR_Value(number, 50)));
    bullet1.userData.active = 0;
    bullet1.visible = false;
    state.userData.score = (state.userData.score + 10);
    // TODO: call
}
}
}
}
}
    if (enemy3.userData.active == 1) {
    if (bullet1.position.x > (enemy3.position.x - 20)) {
    if (bullet1.position.x < (enemy3.position.x + 20)) {
    if (bullet1.position.y > (enemy3.position.y - 20)) {
    if (bullet1.position.y < (enemy3.position.y + 20)) {
    if (sounds['lose1_ogg']) { sounds['lose1_ogg'].stop(); sounds['lose1_ogg'].play(); }
    enemy3.position.y = IR_Expr(unary_op: None - IR_Expr(literal: IR_Value(number, 50)));
    bullet1.userData.active = 0;
    bullet1.visible = false;
    state.userData.score = (state.userData.score + 10);
    // TODO: call
}
}
}
}
}
    if (enemy4.userData.active == 1) {
    if (bullet1.position.x > (enemy4.position.x - 20)) {
    if (bullet1.position.x < (enemy4.position.x + 20)) {
    if (bullet1.position.y > (enemy4.position.y - 20)) {
    if (bullet1.position.y < (enemy4.position.y + 20)) {
    if (sounds['lose1_ogg']) { sounds['lose1_ogg'].stop(); sounds['lose1_ogg'].play(); }
    enemy4.position.y = IR_Expr(unary_op: None - IR_Expr(literal: IR_Value(number, 50)));
    bullet1.userData.active = 0;
    bullet1.visible = false;
    state.userData.score = (state.userData.score + 10);
    // TODO: call
}
}
}
}
}
}
    if (bullet2.userData.active == 1) {
    if (enemy1.userData.active == 1) {
    if (bullet2.position.x > (enemy1.position.x - 20)) {
    if (bullet2.position.x < (enemy1.position.x + 20)) {
    if (bullet2.position.y > (enemy1.position.y - 20)) {
    if (bullet2.position.y < (enemy1.position.y + 20)) {
    if (sounds['lose1_ogg']) { sounds['lose1_ogg'].stop(); sounds['lose1_ogg'].play(); }
    enemy1.position.y = IR_Expr(unary_op: None - IR_Expr(literal: IR_Value(number, 50)));
    bullet2.userData.active = 0;
    bullet2.visible = false;
    state.userData.score = (state.userData.score + 10);
    // TODO: call
}
}
}
}
}
    if (enemy2.userData.active == 1) {
    if (bullet2.position.x > (enemy2.position.x - 20)) {
    if (bullet2.position.x < (enemy2.position.x + 20)) {
    if (bullet2.position.y > (enemy2.position.y - 20)) {
    if (bullet2.position.y < (enemy2.position.y + 20)) {
    if (sounds['lose1_ogg']) { sounds['lose1_ogg'].stop(); sounds['lose1_ogg'].play(); }
    enemy2.position.y = IR_Expr(unary_op: None - IR_Expr(literal: IR_Value(number, 50)));
    bullet2.userData.active = 0;
    bullet2.visible = false;
    state.userData.score = (state.userData.score + 10);
    // TODO: call
}
}
}
}
}
    if (enemy3.userData.active == 1) {
    if (bullet2.position.x > (enemy3.position.x - 20)) {
    if (bullet2.position.x < (enemy3.position.x + 20)) {
    if (bullet2.position.y > (enemy3.position.y - 20)) {
    if (bullet2.position.y < (enemy3.position.y + 20)) {
    if (sounds['lose1_ogg']) { sounds['lose1_ogg'].stop(); sounds['lose1_ogg'].play(); }
    enemy3.position.y = IR_Expr(unary_op: None - IR_Expr(literal: IR_Value(number, 50)));
    bullet2.userData.active = 0;
    bullet2.visible = false;
    state.userData.score = (state.userData.score + 10);
    // TODO: call
}
}
}
}
}
    if (enemy4.userData.active == 1) {
    if (bullet2.position.x > (enemy4.position.x - 20)) {
    if (bullet2.position.x < (enemy4.position.x + 20)) {
    if (bullet2.position.y > (enemy4.position.y - 20)) {
    if (bullet2.position.y < (enemy4.position.y + 20)) {
    if (sounds['lose1_ogg']) { sounds['lose1_ogg'].stop(); sounds['lose1_ogg'].play(); }
    enemy4.position.y = IR_Expr(unary_op: None - IR_Expr(literal: IR_Value(number, 50)));
    bullet2.userData.active = 0;
    bullet2.visible = false;
    state.userData.score = (state.userData.score + 10);
    // TODO: call
}
}
}
}
}
}
    if (bullet3.userData.active == 1) {
    if (enemy1.userData.active == 1) {
    if (bullet3.position.x > (enemy1.position.x - 20)) {
    if (bullet3.position.x < (enemy1.position.x + 20)) {
    if (bullet3.position.y > (enemy1.position.y - 20)) {
    if (bullet3.position.y < (enemy1.position.y + 20)) {
    if (sounds['lose1_ogg']) { sounds['lose1_ogg'].stop(); sounds['lose1_ogg'].play(); }
    enemy1.position.y = IR_Expr(unary_op: None - IR_Expr(literal: IR_Value(number, 50)));
    bullet3.userData.active = 0;
    bullet3.visible = false;
    state.userData.score = (state.userData.score + 10);
    // TODO: call
}
}
}
}
}
    if (enemy2.userData.active == 1) {
    if (bullet3.position.x > (enemy2.position.x - 20)) {
    if (bullet3.position.x < (enemy2.position.x + 20)) {
    if (bullet3.position.y > (enemy2.position.y - 20)) {
    if (bullet3.position.y < (enemy2.position.y + 20)) {
    if (sounds['lose1_ogg']) { sounds['lose1_ogg'].stop(); sounds['lose1_ogg'].play(); }
    enemy2.position.y = IR_Expr(unary_op: None - IR_Expr(literal: IR_Value(number, 50)));
    bullet3.userData.active = 0;
    bullet3.visible = false;
    state.userData.score = (state.userData.score + 10);
    // TODO: call
}
}
}
}
}
    if (enemy3.userData.active == 1) {
    if (bullet3.position.x > (enemy3.position.x - 20)) {
    if (bullet3.position.x < (enemy3.position.x + 20)) {
    if (bullet3.position.y > (enemy3.position.y - 20)) {
    if (bullet3.position.y < (enemy3.position.y + 20)) {
    if (sounds['lose1_ogg']) { sounds['lose1_ogg'].stop(); sounds['lose1_ogg'].play(); }
    enemy3.position.y = IR_Expr(unary_op: None - IR_Expr(literal: IR_Value(number, 50)));
    bullet3.userData.active = 0;
    bullet3.visible = false;
    state.userData.score = (state.userData.score + 10);
    // TODO: call
}
}
}
}
}
    if (enemy4.userData.active == 1) {
    if (bullet3.position.x > (enemy4.position.x - 20)) {
    if (bullet3.position.x < (enemy4.position.x + 20)) {
    if (bullet3.position.y > (enemy4.position.y - 20)) {
    if (bullet3.position.y < (enemy4.position.y + 20)) {
    if (sounds['lose1_ogg']) { sounds['lose1_ogg'].stop(); sounds['lose1_ogg'].play(); }
    enemy4.position.y = IR_Expr(unary_op: None - IR_Expr(literal: IR_Value(number, 50)));
    bullet3.userData.active = 0;
    bullet3.visible = false;
    state.userData.score = (state.userData.score + 10);
    // TODO: call
}
}
}
}
}
}
    if (bullet4.userData.active == 1) {
    if (enemy1.userData.active == 1) {
    if (bullet4.position.x > (enemy1.position.x - 20)) {
    if (bullet4.position.x < (enemy1.position.x + 20)) {
    if (bullet4.position.y > (enemy1.position.y - 20)) {
    if (bullet4.position.y < (enemy1.position.y + 20)) {
    if (sounds['lose1_ogg']) { sounds['lose1_ogg'].stop(); sounds['lose1_ogg'].play(); }
    enemy1.position.y = IR_Expr(unary_op: None - IR_Expr(literal: IR_Value(number, 50)));
    bullet4.userData.active = 0;
    bullet4.visible = false;
    state.userData.score = (state.userData.score + 10);
    // TODO: call
}
}
}
}
}
    if (enemy2.userData.active == 1) {
    if (bullet4.position.x > (enemy2.position.x - 20)) {
    if (bullet4.position.x < (enemy2.position.x + 20)) {
    if (bullet4.position.y > (enemy2.position.y - 20)) {
    if (bullet4.position.y < (enemy2.position.y + 20)) {
    if (sounds['lose1_ogg']) { sounds['lose1_ogg'].stop(); sounds['lose1_ogg'].play(); }
    enemy2.position.y = IR_Expr(unary_op: None - IR_Expr(literal: IR_Value(number, 50)));
    bullet4.userData.active = 0;
    bullet4.visible = false;
    state.userData.score = (state.userData.score + 10);
    // TODO: call
}
}
}
}
}
    if (enemy3.userData.active == 1) {
    if (bullet4.position.x > (enemy3.position.x - 20)) {
    if (bullet4.position.x < (enemy3.position.x + 20)) {
    if (bullet4.position.y > (enemy3.position.y - 20)) {
    if (bullet4.position.y < (enemy3.position.y + 20)) {
    if (sounds['lose1_ogg']) { sounds['lose1_ogg'].stop(); sounds['lose1_ogg'].play(); }
    enemy3.position.y = IR_Expr(unary_op: None - IR_Expr(literal: IR_Value(number, 50)));
    bullet4.userData.active = 0;
    bullet4.visible = false;
    state.userData.score = (state.userData.score + 10);
    // TODO: call
}
}
}
}
}
    if (enemy4.userData.active == 1) {
    if (bullet4.position.x > (enemy4.position.x - 20)) {
    if (bullet4.position.x < (enemy4.position.x + 20)) {
    if (bullet4.position.y > (enemy4.position.y - 20)) {
    if (bullet4.position.y < (enemy4.position.y + 20)) {
    if (sounds['lose1_ogg']) { sounds['lose1_ogg'].stop(); sounds['lose1_ogg'].play(); }
    enemy4.position.y = IR_Expr(unary_op: None - IR_Expr(literal: IR_Value(number, 50)));
    bullet4.userData.active = 0;
    bullet4.visible = false;
    state.userData.score = (state.userData.score + 10);
    // TODO: call
}
}
}
}
}
}
    if (bullet5.userData.active == 1) {
    if (enemy1.userData.active == 1) {
    if (bullet5.position.x > (enemy1.position.x - 20)) {
    if (bullet5.position.x < (enemy1.position.x + 20)) {
    if (bullet5.position.y > (enemy1.position.y - 20)) {
    if (bullet5.position.y < (enemy1.position.y + 20)) {
    if (sounds['lose1_ogg']) { sounds['lose1_ogg'].stop(); sounds['lose1_ogg'].play(); }
    enemy1.position.y = IR_Expr(unary_op: None - IR_Expr(literal: IR_Value(number, 50)));
    bullet5.userData.active = 0;
    bullet5.visible = false;
    state.userData.score = (state.userData.score + 10);
    // TODO: call
}
}
}
}
}
    if (enemy2.userData.active == 1) {
    if (bullet5.position.x > (enemy2.position.x - 20)) {
    if (bullet5.position.x < (enemy2.position.x + 20)) {
    if (bullet5.position.y > (enemy2.position.y - 20)) {
    if (bullet5.position.y < (enemy2.position.y + 20)) {
    if (sounds['lose1_ogg']) { sounds['lose1_ogg'].stop(); sounds['lose1_ogg'].play(); }
    enemy2.position.y = IR_Expr(unary_op: None - IR_Expr(literal: IR_Value(number, 50)));
    bullet5.userData.active = 0;
    bullet5.visible = false;
    state.userData.score = (state.userData.score + 10);
    // TODO: call
}
}
}
}
}
    if (enemy3.userData.active == 1) {
    if (bullet5.position.x > (enemy3.position.x - 20)) {
    if (bullet5.position.x < (enemy3.position.x + 20)) {
    if (bullet5.position.y > (enemy3.position.y - 20)) {
    if (bullet5.position.y < (enemy3.position.y + 20)) {
    if (sounds['lose1_ogg']) { sounds['lose1_ogg'].stop(); sounds['lose1_ogg'].play(); }
    enemy3.position.y = IR_Expr(unary_op: None - IR_Expr(literal: IR_Value(number, 50)));
    bullet5.userData.active = 0;
    bullet5.visible = false;
    state.userData.score = (state.userData.score + 10);
    // TODO: call
}
}
}
}
}
    if (enemy4.userData.active == 1) {
    if (bullet5.position.x > (enemy4.position.x - 20)) {
    if (bullet5.position.x < (enemy4.position.x + 20)) {
    if (bullet5.position.y > (enemy4.position.y - 20)) {
    if (bullet5.position.y < (enemy4.position.y + 20)) {
    if (sounds['lose1_ogg']) { sounds['lose1_ogg'].stop(); sounds['lose1_ogg'].play(); }
    enemy4.position.y = IR_Expr(unary_op: None - IR_Expr(literal: IR_Value(number, 50)));
    bullet5.userData.active = 0;
    bullet5.visible = false;
    state.userData.score = (state.userData.score + 10);
    // TODO: call
}
}
}
}
}
}
    if (enemy1.userData.active == 1) {
    if (enemy1.position.y > (player.position.y - 25)) {
    if (enemy1.position.y < (player.position.y + 25)) {
    if (enemy1.position.x > (player.position.x - 30)) {
    if (enemy1.position.x < (player.position.x + 30)) {
    if (sounds['lose3_ogg']) { sounds['lose3_ogg'].stop(); sounds['lose3_ogg'].play(); }
    enemy1.position.y = IR_Expr(unary_op: None - IR_Expr(literal: IR_Value(number, 50)));
    state.userData.lives = (state.userData.lives - 1);
    // TODO: call
}
}
}
}
}
    if (enemy2.userData.active == 1) {
    if (enemy2.position.y > (player.position.y - 25)) {
    if (enemy2.position.y < (player.position.y + 25)) {
    if (enemy2.position.x > (player.position.x - 30)) {
    if (enemy2.position.x < (player.position.x + 30)) {
    if (sounds['lose3_ogg']) { sounds['lose3_ogg'].stop(); sounds['lose3_ogg'].play(); }
    enemy2.position.y = IR_Expr(unary_op: None - IR_Expr(literal: IR_Value(number, 50)));
    state.userData.lives = (state.userData.lives - 1);
    // TODO: call
}
}
}
}
}
    if (enemy3.userData.active == 1) {
    if (enemy3.position.y > (player.position.y - 25)) {
    if (enemy3.position.y < (player.position.y + 25)) {
    if (enemy3.position.x > (player.position.x - 30)) {
    if (enemy3.position.x < (player.position.x + 30)) {
    if (sounds['lose3_ogg']) { sounds['lose3_ogg'].stop(); sounds['lose3_ogg'].play(); }
    enemy3.position.y = IR_Expr(unary_op: None - IR_Expr(literal: IR_Value(number, 50)));
    state.userData.lives = (state.userData.lives - 1);
    // TODO: call
}
}
}
}
}
    if (enemy4.userData.active == 1) {
    if (enemy4.position.y > (player.position.y - 25)) {
    if (enemy4.position.y < (player.position.y + 25)) {
    if (enemy4.position.x > (player.position.x - 30)) {
    if (enemy4.position.x < (player.position.x + 30)) {
    if (sounds['lose3_ogg']) { sounds['lose3_ogg'].stop(); sounds['lose3_ogg'].play(); }
    enemy4.position.y = IR_Expr(unary_op: None - IR_Expr(literal: IR_Value(number, 50)));
    state.userData.lives = (state.userData.lives - 1);
    // TODO: call
}
}
}
}
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
                    saveData[o.name] = { x: o.position.x, y: o.position.y, z: o.position.z, ...o.userData };
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