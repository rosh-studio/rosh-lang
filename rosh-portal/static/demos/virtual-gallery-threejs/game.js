// Auto-generated from Rosh IR
// Emitter: Three.js v0.2.0
// Three.js and OrbitControls loaded via HTML template

// Scene Setup
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x1a1a2e);

// Meta object for game state
const meta = { userData: {}, modelScale: 2, useModels: true, floor: true, floorColor: null, confirm: true };
// meta.modelScale: global multiplier for all 3D model sizes (default 2)
// meta.useModels: if false, use primitive shapes instead of GLB models
// meta.floor: show/hide the ground grid (default true)
// meta.floorColor: solid floor color (null = grid only, hex = solid floor)
// meta.confirm: require confirmation for bulk ops >= 10 (default true)

// Camera
const camera = new THREE.PerspectiveCamera(50, 800 / 600, 0.1, 1000);
camera.position.set(0, 5, 50);
camera.lookAt(0, 0, 0);

// Renderer
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(window.devicePixelRatio);
document.body.appendChild(renderer.domElement);

// Scene transition overlay
const transitionOverlay = document.createElement('div');
transitionOverlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:#000;opacity:0;pointer-events:none;transition:opacity 0.3s ease;z-index:999';
document.body.appendChild(transitionOverlay);
function transitionToScene(newScene) {
    transitionOverlay.style.opacity = '1';
    setTimeout(() => {
        currentScene = newScene;
        updateSceneVisibility();
        setTimeout(() => { transitionOverlay.style.opacity = '0'; }, 50);
    }, 300);
}

// OrbitControls
const controls = new THREE.OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.05;

// GLTFLoader for 3D models
const gltfLoader = new THREE.GLTFLoader();

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

// Ground grid and floor
const gridHelper = new THREE.GridHelper(100, 50, 0x444466, 0x333355);
gridHelper.name = '_grid';
gridHelper.position.y = -1;
scene.add(gridHelper);
// Solid floor plane (initially hidden, shown when meta.floorColor is set)
const floorGeom = new THREE.PlaneGeometry(100, 100);
const floorMat = new THREE.MeshStandardMaterial({ color: 0x333333, side: THREE.DoubleSide });
const floorMesh = new THREE.Mesh(floorGeom, floorMat);
floorMesh.name = '_floor';
floorMesh.rotation.x = -Math.PI / 2;
floorMesh.position.y = -1.01;
floorMesh.visible = false;
scene.add(floorMesh);

let consoleVisible = false;
let pendingOp = null;
// pendingOp = { type: 'delete'|'create', count: N, execute: () => {...} }
let pendingScene = null;
let pendingAction = null;
let currentScene = 'Lobby';
let currentLevel = 1;

// Game Objects
// Object: lobby_title
const lobby_titleCanvas = document.createElement('canvas');
const lobby_titleCtx = lobby_titleCanvas.getContext('2d');
lobby_titleCanvas.width = 1024;
lobby_titleCanvas.height = 256;
lobby_titleCtx.fillStyle = '#ffffff';
lobby_titleCtx.font = 'bold 72px Arial';
lobby_titleCtx.textAlign = 'center';
lobby_titleCtx.textBaseline = 'middle';
lobby_titleCtx.fillText('Rosh Virtual Gallery', 512, 128);
const lobby_titleTexture = new THREE.CanvasTexture(lobby_titleCanvas);
const lobby_titleMaterial = new THREE.SpriteMaterial({ map: lobby_titleTexture, transparent: true });
const lobby_title = new THREE.Sprite(lobby_titleMaterial);
lobby_title.position.set(0.00, 5.20, -8.00);
lobby_title.scale.set(20.00, 5.00, 1);
lobby_title.name = 'lobby_title';
lobby_title._canvas = lobby_titleCanvas;
lobby_title._ctx = lobby_titleCtx;
lobby_title._text = 'Rosh Virtual Gallery';
lobby_title._color = '#ffffff';
lobby_title._font = 'Inter';
scene.add(lobby_title);
lobby_title.userData.font_size = 72;
lobby_title.userData._rosh_kind = 'text';
lobby_title.userData.font_size = 72;
lobby_title.userData._scene = 'Lobby';
lobby_title.userData._rosh_uuid = crypto.randomUUID();

// Object: lobby_subtitle
const lobby_subtitleCanvas = document.createElement('canvas');
const lobby_subtitleCtx = lobby_subtitleCanvas.getContext('2d');
lobby_subtitleCanvas.width = 1024;
lobby_subtitleCanvas.height = 256;
lobby_subtitleCtx.fillStyle = '#888888';
lobby_subtitleCtx.font = 'bold 48px Arial';
lobby_subtitleCtx.textAlign = 'center';
lobby_subtitleCtx.textBaseline = 'middle';
lobby_subtitleCtx.fillText('Interactive Museum Experience', 512, 128);
const lobby_subtitleTexture = new THREE.CanvasTexture(lobby_subtitleCanvas);
const lobby_subtitleMaterial = new THREE.SpriteMaterial({ map: lobby_subtitleTexture, transparent: true });
const lobby_subtitle = new THREE.Sprite(lobby_subtitleMaterial);
lobby_subtitle.position.set(0.00, 3.60, -8.00);
lobby_subtitle.scale.set(20.00, 5.00, 1);
lobby_subtitle.name = 'lobby_subtitle';
lobby_subtitle._canvas = lobby_subtitleCanvas;
lobby_subtitle._ctx = lobby_subtitleCtx;
lobby_subtitle._text = 'Interactive Museum Experience';
lobby_subtitle._color = '#888888';
lobby_subtitle._font = 'Inter';
scene.add(lobby_subtitle);
lobby_subtitle.userData.font_size = 48;
lobby_subtitle.userData._rosh_kind = 'text';
lobby_subtitle.userData.font_size = 48;
lobby_subtitle.userData._scene = 'Lobby';
lobby_subtitle.userData._rosh_uuid = crypto.randomUUID();

// Object: lobby_instruction1
const lobby_instruction1Canvas = document.createElement('canvas');
const lobby_instruction1Ctx = lobby_instruction1Canvas.getContext('2d');
lobby_instruction1Canvas.width = 1024;
lobby_instruction1Canvas.height = 256;
lobby_instruction1Ctx.fillStyle = '#00ffff';
lobby_instruction1Ctx.font = 'bold 36px Arial';
lobby_instruction1Ctx.textAlign = 'center';
lobby_instruction1Ctx.textBaseline = 'middle';
lobby_instruction1Ctx.fillText('Press backtick ` key to open the console', 512, 128);
const lobby_instruction1Texture = new THREE.CanvasTexture(lobby_instruction1Canvas);
const lobby_instruction1Material = new THREE.SpriteMaterial({ map: lobby_instruction1Texture, transparent: true });
const lobby_instruction1 = new THREE.Sprite(lobby_instruction1Material);
lobby_instruction1.position.set(0.00, 2.00, -8.00);
lobby_instruction1.scale.set(20.00, 5.00, 1);
lobby_instruction1.name = 'lobby_instruction1';
lobby_instruction1._canvas = lobby_instruction1Canvas;
lobby_instruction1._ctx = lobby_instruction1Ctx;
lobby_instruction1._text = 'Press backtick ` key to open the console';
lobby_instruction1._color = '#00ffff';
lobby_instruction1._font = 'Inter';
scene.add(lobby_instruction1);
lobby_instruction1.userData.font_size = 36;
lobby_instruction1.userData._rosh_kind = 'text';
lobby_instruction1.userData.font_size = 36;
lobby_instruction1.userData._scene = 'Lobby';
lobby_instruction1.userData._rosh_uuid = crypto.randomUUID();

// Object: lobby_instruction2
const lobby_instruction2Canvas = document.createElement('canvas');
const lobby_instruction2Ctx = lobby_instruction2Canvas.getContext('2d');
lobby_instruction2Canvas.width = 1024;
lobby_instruction2Canvas.height = 256;
lobby_instruction2Ctx.fillStyle = '#00ffff';
lobby_instruction2Ctx.font = 'bold 32px Arial';
lobby_instruction2Ctx.textAlign = 'center';
lobby_instruction2Ctx.textBaseline = 'middle';
lobby_instruction2Ctx.fillText('Type: go glasgow | go abstract | go sculpture | go creative', 512, 128);
const lobby_instruction2Texture = new THREE.CanvasTexture(lobby_instruction2Canvas);
const lobby_instruction2Material = new THREE.SpriteMaterial({ map: lobby_instruction2Texture, transparent: true });
const lobby_instruction2 = new THREE.Sprite(lobby_instruction2Material);
lobby_instruction2.position.set(0.00, 1.36, -8.00);
lobby_instruction2.scale.set(20.00, 5.00, 1);
lobby_instruction2.name = 'lobby_instruction2';
lobby_instruction2._canvas = lobby_instruction2Canvas;
lobby_instruction2._ctx = lobby_instruction2Ctx;
lobby_instruction2._text = 'Type: go glasgow | go abstract | go sculpture | go creative';
lobby_instruction2._color = '#00ffff';
lobby_instruction2._font = 'Inter';
scene.add(lobby_instruction2);
lobby_instruction2.userData.font_size = 32;
lobby_instruction2.userData._rosh_kind = 'text';
lobby_instruction2.userData.font_size = 32;
lobby_instruction2.userData._scene = 'Lobby';
lobby_instruction2.userData._rosh_uuid = crypto.randomUUID();

// Object: lobby_instruction3
const lobby_instruction3Canvas = document.createElement('canvas');
const lobby_instruction3Ctx = lobby_instruction3Canvas.getContext('2d');
lobby_instruction3Canvas.width = 1024;
lobby_instruction3Canvas.height = 256;
lobby_instruction3Ctx.fillStyle = '#888888';
lobby_instruction3Ctx.font = 'bold 32px Arial';
lobby_instruction3Ctx.textAlign = 'center';
lobby_instruction3Ctx.textBaseline = 'middle';
lobby_instruction3Ctx.fillText('Reload page to restart', 512, 128);
const lobby_instruction3Texture = new THREE.CanvasTexture(lobby_instruction3Canvas);
const lobby_instruction3Material = new THREE.SpriteMaterial({ map: lobby_instruction3Texture, transparent: true });
const lobby_instruction3 = new THREE.Sprite(lobby_instruction3Material);
lobby_instruction3.position.set(0.00, 0.00, -8.00);
lobby_instruction3.scale.set(20.00, 5.00, 1);
lobby_instruction3.name = 'lobby_instruction3';
lobby_instruction3._canvas = lobby_instruction3Canvas;
lobby_instruction3._ctx = lobby_instruction3Ctx;
lobby_instruction3._text = 'Reload page to restart';
lobby_instruction3._color = '#888888';
lobby_instruction3._font = 'Inter';
scene.add(lobby_instruction3);
lobby_instruction3.userData.font_size = 32;
lobby_instruction3.userData._rosh_kind = 'text';
lobby_instruction3.userData.font_size = 32;
lobby_instruction3.userData._scene = 'Lobby';
lobby_instruction3.userData._rosh_uuid = crypto.randomUUID();

// Object: lobby_cube
const lobby_cubeGeometry = new THREE.BoxGeometry(0.80, 0.80, 0.80);
const lobby_cubeMaterial = new THREE.MeshStandardMaterial({ color: 0x8800ff });
const lobby_cube = new THREE.Mesh(lobby_cubeGeometry, lobby_cubeMaterial);
lobby_cube.position.set(0.00, 7.60, 2.00);
lobby_cube.name = 'lobby_cube';
scene.add(lobby_cube);
lobby_cube.userData._rosh_kind = 'mesh';
lobby_cube.userData._type = 'cube';
lobby_cube.userData._needsModelLoad = true;
lobby_cube.userData.size = 1.5;
lobby_cube.userData._spin = [10.0, 20.0, 5.0];
lobby_cube.userData._scene = 'Lobby';
lobby_cube.userData._rosh_uuid = crypto.randomUUID();

// Object: abstract_title
const abstract_titleCanvas = document.createElement('canvas');
const abstract_titleCtx = abstract_titleCanvas.getContext('2d');
abstract_titleCanvas.width = 1024;
abstract_titleCanvas.height = 256;
abstract_titleCtx.fillStyle = '#ffffff';
abstract_titleCtx.font = 'bold 72px Arial';
abstract_titleCtx.textAlign = 'center';
abstract_titleCtx.textBaseline = 'middle';
abstract_titleCtx.fillText('Abstract Gallery', 512, 128);
const abstract_titleTexture = new THREE.CanvasTexture(abstract_titleCanvas);
const abstract_titleMaterial = new THREE.SpriteMaterial({ map: abstract_titleTexture, transparent: true });
const abstract_title = new THREE.Sprite(abstract_titleMaterial);
abstract_title.position.set(0.00, 5.20, -12.00);
abstract_title.scale.set(20.00, 5.00, 1);
abstract_title.name = 'abstract_title';
abstract_title._canvas = abstract_titleCanvas;
abstract_title._ctx = abstract_titleCtx;
abstract_title._text = 'Abstract Gallery';
abstract_title._color = '#ffffff';
abstract_title._font = 'Inter';
scene.add(abstract_title);
abstract_title.userData.font_size = 72;
abstract_title.userData._rosh_kind = 'text';
abstract_title.userData.font_size = 72;
abstract_title.userData._scene = 'Abstract';
abstract_title.userData._rosh_uuid = crypto.randomUUID();

// Object: abstract_hint
const abstract_hintCanvas = document.createElement('canvas');
const abstract_hintCtx = abstract_hintCanvas.getContext('2d');
abstract_hintCanvas.width = 1024;
abstract_hintCanvas.height = 256;
abstract_hintCtx.fillStyle = '#00ffff';
abstract_hintCtx.font = 'bold 24px Arial';
abstract_hintCtx.textAlign = 'center';
abstract_hintCtx.textBaseline = 'middle';
abstract_hintCtx.fillText('go lobby | go glasgow | go sculpture | go creative', 512, 128);
const abstract_hintTexture = new THREE.CanvasTexture(abstract_hintCanvas);
const abstract_hintMaterial = new THREE.SpriteMaterial({ map: abstract_hintTexture, transparent: true });
const abstract_hint = new THREE.Sprite(abstract_hintMaterial);
abstract_hint.position.set(0.00, 3.60, -12.00);
abstract_hint.scale.set(20.00, 5.00, 1);
abstract_hint.name = 'abstract_hint';
abstract_hint._canvas = abstract_hintCanvas;
abstract_hint._ctx = abstract_hintCtx;
abstract_hint._text = 'go lobby | go glasgow | go sculpture | go creative';
abstract_hint._color = '#00ffff';
abstract_hint._font = 'Inter';
scene.add(abstract_hint);
abstract_hint.userData.font_size = 24;
abstract_hint.userData._rosh_kind = 'text';
abstract_hint.userData.font_size = 24;
abstract_hint.userData._scene = 'Abstract';
abstract_hint.userData._rosh_uuid = crypto.randomUUID();

// Object: sculpture
const sculptureGeometry = new THREE.SphereGeometry(0.5, 32, 32);
const sculptureMaterial = new THREE.MeshStandardMaterial({ color: 0x0000ff });
const sculpture = new THREE.Mesh(sculptureGeometry, sculptureMaterial);
sculpture.position.set(0.00, 2.00, 0.00);
sculpture.name = 'sculpture';
scene.add(sculpture);
sculpture.userData._rosh_kind = 'mesh';
sculpture.userData._type = 'sphere';
sculpture.userData._needsModelLoad = true;
sculpture.userData.size = 2;
sculpture.userData._spin = [0.0, 20.0, 0.0];
sculpture.userData._scene = 'Abstract';
sculpture.userData._rosh_uuid = crypto.randomUUID();

// Object: orbiter1
const orbiter1Geometry = new THREE.SphereGeometry(0.5, 32, 32);
const orbiter1Material = new THREE.MeshStandardMaterial({ color: 0xff0000 });
const orbiter1 = new THREE.Mesh(orbiter1Geometry, orbiter1Material);
orbiter1.position.set(3.20, 2.00, 0.00);
orbiter1.name = 'orbiter1';
scene.add(orbiter1);
orbiter1.userData._rosh_kind = 'mesh';
orbiter1.userData._type = 'sphere';
orbiter1.userData._needsModelLoad = true;
orbiter1.userData.size = 0.5;
orbiter1.userData._orbit = [3.0, 30.0, 2.0];
orbiter1.userData._scene = 'Abstract';
orbiter1.userData._rosh_uuid = crypto.randomUUID();

// Object: orbiter2
const orbiter2Geometry = new THREE.SphereGeometry(0.5, 32, 32);
const orbiter2Material = new THREE.MeshStandardMaterial({ color: 0x00ff00 });
const orbiter2 = new THREE.Mesh(orbiter2Geometry, orbiter2Material);
orbiter2.position.set(-3.20, 2.00, 0.00);
orbiter2.name = 'orbiter2';
scene.add(orbiter2);
orbiter2.userData._rosh_kind = 'mesh';
orbiter2.userData._type = 'sphere';
orbiter2.userData._needsModelLoad = true;
orbiter2.userData.size = 0.5;
orbiter2.userData._orbit = [3.0, -30.0, 2.0];
orbiter2.userData._scene = 'Abstract';
orbiter2.userData._rosh_uuid = crypto.randomUUID();

// Object: orbiter3
const orbiter3Geometry = new THREE.SphereGeometry(0.5, 32, 32);
const orbiter3Material = new THREE.MeshStandardMaterial({ color: 0xffff00 });
const orbiter3 = new THREE.Mesh(orbiter3Geometry, orbiter3Material);
orbiter3.position.set(0.00, 2.00, 3.00);
orbiter3.name = 'orbiter3';
scene.add(orbiter3);
orbiter3.userData._rosh_kind = 'mesh';
orbiter3.userData._type = 'sphere';
orbiter3.userData._needsModelLoad = true;
orbiter3.userData.size = 0.5;
orbiter3.userData._orbit = [3.0, 45.0, 2.0];
orbiter3.userData._scene = 'Abstract';
orbiter3.userData._rosh_uuid = crypto.randomUUID();

// Object: sculpture_title
const sculpture_titleCanvas = document.createElement('canvas');
const sculpture_titleCtx = sculpture_titleCanvas.getContext('2d');
sculpture_titleCanvas.width = 1024;
sculpture_titleCanvas.height = 256;
sculpture_titleCtx.fillStyle = '#ffffff';
sculpture_titleCtx.font = 'bold 72px Arial';
sculpture_titleCtx.textAlign = 'center';
sculpture_titleCtx.textBaseline = 'middle';
sculpture_titleCtx.fillText('Sculpture Garden', 512, 128);
const sculpture_titleTexture = new THREE.CanvasTexture(sculpture_titleCanvas);
const sculpture_titleMaterial = new THREE.SpriteMaterial({ map: sculpture_titleTexture, transparent: true });
const sculpture_title = new THREE.Sprite(sculpture_titleMaterial);
sculpture_title.position.set(0.00, 5.20, -12.00);
sculpture_title.scale.set(20.00, 5.00, 1);
sculpture_title.name = 'sculpture_title';
sculpture_title._canvas = sculpture_titleCanvas;
sculpture_title._ctx = sculpture_titleCtx;
sculpture_title._text = 'Sculpture Garden';
sculpture_title._color = '#ffffff';
sculpture_title._font = 'Inter';
scene.add(sculpture_title);
sculpture_title.userData.font_size = 72;
sculpture_title.userData._rosh_kind = 'text';
sculpture_title.userData.font_size = 72;
sculpture_title.userData._scene = 'Sculpture';
sculpture_title.userData._rosh_uuid = crypto.randomUUID();

// Object: sculpture_hint
const sculpture_hintCanvas = document.createElement('canvas');
const sculpture_hintCtx = sculpture_hintCanvas.getContext('2d');
sculpture_hintCanvas.width = 1024;
sculpture_hintCanvas.height = 256;
sculpture_hintCtx.fillStyle = '#00ffff';
sculpture_hintCtx.font = 'bold 24px Arial';
sculpture_hintCtx.textAlign = 'center';
sculpture_hintCtx.textBaseline = 'middle';
sculpture_hintCtx.fillText('go lobby | go glasgow | go abstract | go creative', 512, 128);
const sculpture_hintTexture = new THREE.CanvasTexture(sculpture_hintCanvas);
const sculpture_hintMaterial = new THREE.SpriteMaterial({ map: sculpture_hintTexture, transparent: true });
const sculpture_hint = new THREE.Sprite(sculpture_hintMaterial);
sculpture_hint.position.set(0.00, 3.60, -12.00);
sculpture_hint.scale.set(20.00, 5.00, 1);
sculpture_hint.name = 'sculpture_hint';
sculpture_hint._canvas = sculpture_hintCanvas;
sculpture_hint._ctx = sculpture_hintCtx;
sculpture_hint._text = 'go lobby | go glasgow | go abstract | go creative';
sculpture_hint._color = '#00ffff';
sculpture_hint._font = 'Inter';
scene.add(sculpture_hint);
sculpture_hint.userData.font_size = 24;
sculpture_hint.userData._rosh_kind = 'text';
sculpture_hint.userData.font_size = 24;
sculpture_hint.userData._scene = 'Sculpture';
sculpture_hint.userData._rosh_uuid = crypto.randomUUID();

// Object: pedestal1
const pedestal1Geometry = new THREE.BoxGeometry(0.80, 0.80, 0.80);
const pedestal1Material = new THREE.MeshStandardMaterial({ color: 0xffffff });
const pedestal1 = new THREE.Mesh(pedestal1Geometry, pedestal1Material);
pedestal1.position.set(-3.20, 0.80, -2.00);
pedestal1.name = 'pedestal1';
scene.add(pedestal1);
pedestal1.userData._rosh_kind = 'mesh';
pedestal1.userData._type = 'cube';
pedestal1.userData._needsModelLoad = true;
pedestal1.userData.scale = '2 0.5 2';
pedestal1.userData._scene = 'Sculpture';
pedestal1.userData._rosh_uuid = crypto.randomUUID();

// Object: statue1
const statue1Geometry = new THREE.CylinderGeometry(0.5, 0.5, 0.80, 32);
const statue1Material = new THREE.MeshStandardMaterial({ color: 0x8800ff });
const statue1 = new THREE.Mesh(statue1Geometry, statue1Material);
statue1.position.set(-3.20, 2.00, -2.00);
statue1.name = 'statue1';
scene.add(statue1);
statue1.userData._rosh_kind = 'mesh';
statue1.userData._type = 'cylinder';
statue1.userData._needsModelLoad = true;
statue1.userData.size = 1.5;
statue1.userData._bounce = [0.3, 0.5];
statue1.userData._scene = 'Sculpture';
statue1.userData._rosh_uuid = crypto.randomUUID();

// Object: pedestal2
const pedestal2Geometry = new THREE.BoxGeometry(0.80, 0.80, 0.80);
const pedestal2Material = new THREE.MeshStandardMaterial({ color: 0xffffff });
const pedestal2 = new THREE.Mesh(pedestal2Geometry, pedestal2Material);
pedestal2.position.set(3.20, 0.80, -2.00);
pedestal2.name = 'pedestal2';
scene.add(pedestal2);
pedestal2.userData._rosh_kind = 'mesh';
pedestal2.userData._type = 'cube';
pedestal2.userData._needsModelLoad = true;
pedestal2.userData.scale = '2 0.5 2';
pedestal2.userData._scene = 'Sculpture';
pedestal2.userData._rosh_uuid = crypto.randomUUID();

// Object: statue2
const statue2Geometry = new THREE.SphereGeometry(0.5, 32, 32);
const statue2Material = new THREE.MeshStandardMaterial({ color: 0xff8800 });
const statue2 = new THREE.Mesh(statue2Geometry, statue2Material);
statue2.position.set(3.20, 2.00, -2.00);
statue2.name = 'statue2';
scene.add(statue2);
statue2.userData._rosh_kind = 'mesh';
statue2.userData._type = 'sphere';
statue2.userData._needsModelLoad = true;
statue2.userData.size = 1.5;
statue2.userData._pulse = [0.15, 0.3];
statue2.userData._scene = 'Sculpture';
statue2.userData._rosh_uuid = crypto.randomUUID();

// Object: pedestal3
const pedestal3Geometry = new THREE.BoxGeometry(0.80, 0.80, 0.80);
const pedestal3Material = new THREE.MeshStandardMaterial({ color: 0xffffff });
const pedestal3 = new THREE.Mesh(pedestal3Geometry, pedestal3Material);
pedestal3.position.set(0.00, 0.80, 3.00);
pedestal3.name = 'pedestal3';
scene.add(pedestal3);
pedestal3.userData._rosh_kind = 'mesh';
pedestal3.userData._type = 'cube';
pedestal3.userData._needsModelLoad = true;
pedestal3.userData.scale = '2 0.5 2';
pedestal3.userData._scene = 'Sculpture';
pedestal3.userData._rosh_uuid = crypto.randomUUID();

// Object: statue3
const statue3Geometry = new THREE.BoxGeometry(0.80, 0.80, 0.80);
const statue3Material = new THREE.MeshStandardMaterial({ color: 0x00ffff });
const statue3 = new THREE.Mesh(statue3Geometry, statue3Material);
statue3.position.set(0.00, 2.00, 3.00);
statue3.name = 'statue3';
scene.add(statue3);
statue3.userData._rosh_kind = 'mesh';
statue3.userData._type = 'cube';
statue3.userData._needsModelLoad = true;
statue3.userData.size = 2;
statue3.userData._spin = [0.0, 5.0, 0.0];
statue3.userData._scene = 'Sculpture';
statue3.userData._rosh_uuid = crypto.randomUUID();

// Object: creative_title
const creative_titleCanvas = document.createElement('canvas');
const creative_titleCtx = creative_titleCanvas.getContext('2d');
creative_titleCanvas.width = 1024;
creative_titleCanvas.height = 256;
creative_titleCtx.fillStyle = '#ffffff';
creative_titleCtx.font = 'bold 72px Arial';
creative_titleCtx.textAlign = 'center';
creative_titleCtx.textBaseline = 'middle';
creative_titleCtx.fillText('Creative Studio', 512, 128);
const creative_titleTexture = new THREE.CanvasTexture(creative_titleCanvas);
const creative_titleMaterial = new THREE.SpriteMaterial({ map: creative_titleTexture, transparent: true });
const creative_title = new THREE.Sprite(creative_titleMaterial);
creative_title.position.set(0.00, 5.20, -12.00);
creative_title.scale.set(20.00, 5.00, 1);
creative_title.name = 'creative_title';
creative_title._canvas = creative_titleCanvas;
creative_title._ctx = creative_titleCtx;
creative_title._text = 'Creative Studio';
creative_title._color = '#ffffff';
creative_title._font = 'Inter';
scene.add(creative_title);
creative_title.userData.font_size = 72;
creative_title.userData._rosh_kind = 'text';
creative_title.userData.font_size = 72;
creative_title.userData._scene = 'Creative';
creative_title.userData._rosh_uuid = crypto.randomUUID();

// Object: creative_subtitle
const creative_subtitleCanvas = document.createElement('canvas');
const creative_subtitleCtx = creative_subtitleCanvas.getContext('2d');
creative_subtitleCanvas.width = 1024;
creative_subtitleCanvas.height = 256;
creative_subtitleCtx.fillStyle = '#888888';
creative_subtitleCtx.font = 'bold 36px Arial';
creative_subtitleCtx.textAlign = 'center';
creative_subtitleCtx.textBaseline = 'middle';
creative_subtitleCtx.fillText('Your space to create', 512, 128);
const creative_subtitleTexture = new THREE.CanvasTexture(creative_subtitleCanvas);
const creative_subtitleMaterial = new THREE.SpriteMaterial({ map: creative_subtitleTexture, transparent: true });
const creative_subtitle = new THREE.Sprite(creative_subtitleMaterial);
creative_subtitle.position.set(0.00, 3.60, -12.00);
creative_subtitle.scale.set(20.00, 5.00, 1);
creative_subtitle.name = 'creative_subtitle';
creative_subtitle._canvas = creative_subtitleCanvas;
creative_subtitle._ctx = creative_subtitleCtx;
creative_subtitle._text = 'Your space to create';
creative_subtitle._color = '#888888';
creative_subtitle._font = 'Inter';
scene.add(creative_subtitle);
creative_subtitle.userData.font_size = 36;
creative_subtitle.userData._rosh_kind = 'text';
creative_subtitle.userData.font_size = 36;
creative_subtitle.userData._scene = 'Creative';
creative_subtitle.userData._rosh_uuid = crypto.randomUUID();

// Object: creative_hint
const creative_hintCanvas = document.createElement('canvas');
const creative_hintCtx = creative_hintCanvas.getContext('2d');
creative_hintCanvas.width = 1024;
creative_hintCanvas.height = 256;
creative_hintCtx.fillStyle = '#00ffff';
creative_hintCtx.font = 'bold 24px Arial';
creative_hintCtx.textAlign = 'center';
creative_hintCtx.textBaseline = 'middle';
creative_hintCtx.fillText('try: create big red sphere | go lobby | go glasgow', 512, 128);
const creative_hintTexture = new THREE.CanvasTexture(creative_hintCanvas);
const creative_hintMaterial = new THREE.SpriteMaterial({ map: creative_hintTexture, transparent: true });
const creative_hint = new THREE.Sprite(creative_hintMaterial);
creative_hint.position.set(0.00, 2.64, -12.00);
creative_hint.scale.set(20.00, 5.00, 1);
creative_hint.name = 'creative_hint';
creative_hint._canvas = creative_hintCanvas;
creative_hint._ctx = creative_hintCtx;
creative_hint._text = 'try: create big red sphere | go lobby | go glasgow';
creative_hint._color = '#00ffff';
creative_hint._font = 'Inter';
scene.add(creative_hint);
creative_hint.userData.font_size = 24;
creative_hint.userData._rosh_kind = 'text';
creative_hint.userData.font_size = 24;
creative_hint.userData._scene = 'Creative';
creative_hint.userData._rosh_uuid = crypto.randomUUID();

// Object: easel
const easelGeometry = new THREE.BoxGeometry(0.80, 0.80, 0.80);
const easelMaterial = new THREE.MeshStandardMaterial({ color: 0x888888 });
const easel = new THREE.Mesh(easelGeometry, easelMaterial);
easel.position.set(-3.20, 1.60, 0.00);
easel.name = 'easel';
scene.add(easel);
easel.userData._rosh_kind = 'mesh';
easel.userData._type = 'cube';
easel.userData._needsModelLoad = true;
easel.userData.scale = '0.2 3 2';
easel.userData._scene = 'Creative';
easel.userData._rosh_uuid = crypto.randomUUID();

// Object: canvas
const canvasGeometry = new THREE.BoxGeometry(0.80, 0.80, 0.80);
const canvasMaterial = new THREE.MeshStandardMaterial({ color: 0xffffff });
const canvas = new THREE.Mesh(canvasGeometry, canvasMaterial);
canvas.position.set(-3.20, 2.80, 0.30);
canvas.name = 'canvas';
scene.add(canvas);
canvas.userData._rosh_kind = 'mesh';
canvas.userData._type = 'cube';
canvas.userData._needsModelLoad = true;
canvas.userData.scale = '0.1 2 1.5';
canvas.userData._scene = 'Creative';
canvas.userData._rosh_uuid = crypto.randomUUID();

// Object: glasgow_title
const glasgow_titleCanvas = document.createElement('canvas');
const glasgow_titleCtx = glasgow_titleCanvas.getContext('2d');
glasgow_titleCanvas.width = 1024;
glasgow_titleCanvas.height = 256;
glasgow_titleCtx.fillStyle = '#ffffff';
glasgow_titleCtx.font = 'bold 72px Arial';
glasgow_titleCtx.textAlign = 'center';
glasgow_titleCtx.textBaseline = 'middle';
glasgow_titleCtx.fillText('Glasgow Heritage', 512, 128);
const glasgow_titleTexture = new THREE.CanvasTexture(glasgow_titleCanvas);
const glasgow_titleMaterial = new THREE.SpriteMaterial({ map: glasgow_titleTexture, transparent: true });
const glasgow_title = new THREE.Sprite(glasgow_titleMaterial);
glasgow_title.position.set(0.00, 5.20, -12.00);
glasgow_title.scale.set(20.00, 5.00, 1);
glasgow_title.name = 'glasgow_title';
glasgow_title._canvas = glasgow_titleCanvas;
glasgow_title._ctx = glasgow_titleCtx;
glasgow_title._text = 'Glasgow Heritage';
glasgow_title._color = '#ffffff';
glasgow_title._font = 'Inter';
scene.add(glasgow_title);
glasgow_title.userData.font_size = 72;
glasgow_title.userData._rosh_kind = 'text';
glasgow_title.userData.font_size = 72;
glasgow_title.userData._scene = 'Glasgow';
glasgow_title.userData._rosh_uuid = crypto.randomUUID();

// Object: glasgow_subtitle
const glasgow_subtitleCanvas = document.createElement('canvas');
const glasgow_subtitleCtx = glasgow_subtitleCanvas.getContext('2d');
glasgow_subtitleCanvas.width = 1024;
glasgow_subtitleCanvas.height = 256;
glasgow_subtitleCtx.fillStyle = '#888888';
glasgow_subtitleCtx.font = 'bold 28px Arial';
glasgow_subtitleCtx.textAlign = 'center';
glasgow_subtitleCtx.textBaseline = 'middle';
glasgow_subtitleCtx.fillText('Historical artifacts from Glasgow and surrounding areas', 512, 128);
const glasgow_subtitleTexture = new THREE.CanvasTexture(glasgow_subtitleCanvas);
const glasgow_subtitleMaterial = new THREE.SpriteMaterial({ map: glasgow_subtitleTexture, transparent: true });
const glasgow_subtitle = new THREE.Sprite(glasgow_subtitleMaterial);
glasgow_subtitle.position.set(0.00, 4.00, -12.00);
glasgow_subtitle.scale.set(20.00, 5.00, 1);
glasgow_subtitle.name = 'glasgow_subtitle';
glasgow_subtitle._canvas = glasgow_subtitleCanvas;
glasgow_subtitle._ctx = glasgow_subtitleCtx;
glasgow_subtitle._text = 'Historical artifacts from Glasgow and surrounding areas';
glasgow_subtitle._color = '#888888';
glasgow_subtitle._font = 'Inter';
scene.add(glasgow_subtitle);
glasgow_subtitle.userData.font_size = 28;
glasgow_subtitle.userData._rosh_kind = 'text';
glasgow_subtitle.userData.font_size = 28;
glasgow_subtitle.userData._scene = 'Glasgow';
glasgow_subtitle.userData._rosh_uuid = crypto.randomUUID();

// Object: glasgow_hint
const glasgow_hintCanvas = document.createElement('canvas');
const glasgow_hintCtx = glasgow_hintCanvas.getContext('2d');
glasgow_hintCanvas.width = 1024;
glasgow_hintCanvas.height = 256;
glasgow_hintCtx.fillStyle = '#00ffff';
glasgow_hintCtx.font = 'bold 24px Arial';
glasgow_hintCtx.textAlign = 'center';
glasgow_hintCtx.textBaseline = 'middle';
glasgow_hintCtx.fillText('go lobby | go abstract | go sculpture | go creative', 512, 128);
const glasgow_hintTexture = new THREE.CanvasTexture(glasgow_hintCanvas);
const glasgow_hintMaterial = new THREE.SpriteMaterial({ map: glasgow_hintTexture, transparent: true });
const glasgow_hint = new THREE.Sprite(glasgow_hintMaterial);
glasgow_hint.position.set(0.00, 2.96, -12.00);
glasgow_hint.scale.set(20.00, 5.00, 1);
glasgow_hint.name = 'glasgow_hint';
glasgow_hint._canvas = glasgow_hintCanvas;
glasgow_hint._ctx = glasgow_hintCtx;
glasgow_hint._text = 'go lobby | go abstract | go sculpture | go creative';
glasgow_hint._color = '#00ffff';
glasgow_hint._font = 'Inter';
scene.add(glasgow_hint);
glasgow_hint.userData.font_size = 24;
glasgow_hint.userData._rosh_kind = 'text';
glasgow_hint.userData.font_size = 24;
glasgow_hint.userData._scene = 'Glasgow';
glasgow_hint.userData._rosh_uuid = crypto.randomUUID();

// Object: linen_bank
const linen_bankGeometry = new THREE.BoxGeometry(0.80, 0.80, 0.80);
const linen_bankMaterial = new THREE.MeshStandardMaterial({ color: 0xff00ff });
const linen_bank = new THREE.Mesh(linen_bankGeometry, linen_bankMaterial);
linen_bank.position.set(-4.80, 0.80, 0.00);
linen_bank.name = 'linen_bank';
scene.add(linen_bank);
linen_bank.userData._rosh_kind = 'mesh';
linen_bank.userData._type = 'linen_bank';
linen_bank.userData._needsModelLoad = true;
linen_bank.userData.size = 2.5;
linen_bank.userData._spin = [0.0, 5.0, 0.0];
linen_bank.userData._scene = 'Glasgow';
linen_bank.userData._rosh_uuid = crypto.randomUUID();

// Object: linen_bank_label
const linen_bank_labelCanvas = document.createElement('canvas');
const linen_bank_labelCtx = linen_bank_labelCanvas.getContext('2d');
linen_bank_labelCanvas.width = 1024;
linen_bank_labelCanvas.height = 256;
linen_bank_labelCtx.fillStyle = '#ffffff';
linen_bank_labelCtx.font = 'bold 24px Arial';
linen_bank_labelCtx.textAlign = 'center';
linen_bank_labelCtx.textBaseline = 'middle';
linen_bank_labelCtx.fillText('Linen Bank', 512, 128);
const linen_bank_labelTexture = new THREE.CanvasTexture(linen_bank_labelCanvas);
const linen_bank_labelMaterial = new THREE.SpriteMaterial({ map: linen_bank_labelTexture, transparent: true });
const linen_bank_label = new THREE.Sprite(linen_bank_labelMaterial);
linen_bank_label.position.set(-7.68, 1.60, 0.00);
linen_bank_label.scale.set(20.00, 5.00, 1);
linen_bank_label.name = 'linen_bank_label';
linen_bank_label._canvas = linen_bank_labelCanvas;
linen_bank_label._ctx = linen_bank_labelCtx;
linen_bank_label._text = 'Linen Bank';
linen_bank_label._color = '#ffffff';
linen_bank_label._font = 'Inter';
scene.add(linen_bank_label);
linen_bank_label.userData.font_size = 24;
linen_bank_label.userData._rosh_kind = 'text';
linen_bank_label.userData.font_size = 24;
linen_bank_label.userData._scene = 'Glasgow';
linen_bank_label.userData._rosh_uuid = crypto.randomUUID();

// Object: linen_bank_info
const linen_bank_infoCanvas = document.createElement('canvas');
const linen_bank_infoCtx = linen_bank_infoCanvas.getContext('2d');
linen_bank_infoCanvas.width = 1024;
linen_bank_infoCanvas.height = 256;
linen_bank_infoCtx.fillStyle = '#888888';
linen_bank_infoCtx.font = 'bold 16px Arial';
linen_bank_infoCtx.textAlign = 'center';
linen_bank_infoCtx.textBaseline = 'middle';
linen_bank_infoCtx.fillText('Historic building', 512, 128);
const linen_bank_infoTexture = new THREE.CanvasTexture(linen_bank_infoCanvas);
const linen_bank_infoMaterial = new THREE.SpriteMaterial({ map: linen_bank_infoTexture, transparent: true });
const linen_bank_info = new THREE.Sprite(linen_bank_infoMaterial);
linen_bank_info.position.set(-7.68, 1.20, 0.00);
linen_bank_info.scale.set(20.00, 5.00, 1);
linen_bank_info.name = 'linen_bank_info';
linen_bank_info._canvas = linen_bank_infoCanvas;
linen_bank_info._ctx = linen_bank_infoCtx;
linen_bank_info._text = 'Historic building';
linen_bank_info._color = '#888888';
linen_bank_info._font = 'Inter';
scene.add(linen_bank_info);
linen_bank_info.userData.font_size = 16;
linen_bank_info.userData._rosh_kind = 'text';
linen_bank_info.userData.font_size = 16;
linen_bank_info.userData._scene = 'Glasgow';
linen_bank_info.userData._rosh_uuid = crypto.randomUUID();

// Object: linen_bank_credit
const linen_bank_creditCanvas = document.createElement('canvas');
const linen_bank_creditCtx = linen_bank_creditCanvas.getContext('2d');
linen_bank_creditCanvas.width = 1024;
linen_bank_creditCanvas.height = 256;
linen_bank_creditCtx.fillStyle = '#00ffff';
linen_bank_creditCtx.font = 'bold 14px Arial';
linen_bank_creditCtx.textAlign = 'center';
linen_bank_creditCtx.textBaseline = 'middle';
linen_bank_creditCtx.fillText('CheriePotter (CC BY)', 512, 128);
const linen_bank_creditTexture = new THREE.CanvasTexture(linen_bank_creditCanvas);
const linen_bank_creditMaterial = new THREE.SpriteMaterial({ map: linen_bank_creditTexture, transparent: true });
const linen_bank_credit = new THREE.Sprite(linen_bank_creditMaterial);
linen_bank_credit.position.set(-7.68, 0.80, 0.00);
linen_bank_credit.scale.set(20.00, 5.00, 1);
linen_bank_credit.name = 'linen_bank_credit';
linen_bank_credit._canvas = linen_bank_creditCanvas;
linen_bank_credit._ctx = linen_bank_creditCtx;
linen_bank_credit._text = 'CheriePotter (CC BY)';
linen_bank_credit._color = '#00ffff';
linen_bank_credit._font = 'Inter';
scene.add(linen_bank_credit);
linen_bank_credit.userData.font_size = 14;
linen_bank_credit.userData._rosh_kind = 'text';
linen_bank_credit.userData.font_size = 14;
linen_bank_credit.userData._scene = 'Glasgow';
linen_bank_credit.userData._rosh_uuid = crypto.randomUUID();

// Object: baillie_monument
const baillie_monumentGeometry = new THREE.BoxGeometry(0.80, 0.80, 0.80);
const baillie_monumentMaterial = new THREE.MeshStandardMaterial({ color: 0x00ff00 });
const baillie_monument = new THREE.Mesh(baillie_monumentGeometry, baillie_monumentMaterial);
baillie_monument.position.set(4.80, 0.80, 0.00);
baillie_monument.name = 'baillie_monument';
scene.add(baillie_monument);
baillie_monument.userData._rosh_kind = 'mesh';
baillie_monument.userData._type = 'joanna_baillie_monument';
baillie_monument.userData._needsModelLoad = true;
baillie_monument.userData.size = 2.5;
baillie_monument.userData._spin = [0.0, 5.0, 0.0];
baillie_monument.userData._scene = 'Glasgow';
baillie_monument.userData._rosh_uuid = crypto.randomUUID();

// Object: baillie_label
const baillie_labelCanvas = document.createElement('canvas');
const baillie_labelCtx = baillie_labelCanvas.getContext('2d');
baillie_labelCanvas.width = 1024;
baillie_labelCanvas.height = 256;
baillie_labelCtx.fillStyle = '#ffffff';
baillie_labelCtx.font = 'bold 24px Arial';
baillie_labelCtx.textAlign = 'center';
baillie_labelCtx.textBaseline = 'middle';
baillie_labelCtx.fillText('Joanna Baillie', 512, 128);
const baillie_labelTexture = new THREE.CanvasTexture(baillie_labelCanvas);
const baillie_labelMaterial = new THREE.SpriteMaterial({ map: baillie_labelTexture, transparent: true });
const baillie_label = new THREE.Sprite(baillie_labelMaterial);
baillie_label.position.set(7.68, 2.00, 0.00);
baillie_label.scale.set(20.00, 5.00, 1);
baillie_label.name = 'baillie_label';
baillie_label._canvas = baillie_labelCanvas;
baillie_label._ctx = baillie_labelCtx;
baillie_label._text = 'Joanna Baillie';
baillie_label._color = '#ffffff';
baillie_label._font = 'Inter';
scene.add(baillie_label);
baillie_label.userData.font_size = 24;
baillie_label.userData._rosh_kind = 'text';
baillie_label.userData.font_size = 24;
baillie_label.userData._scene = 'Glasgow';
baillie_label.userData._rosh_uuid = crypto.randomUUID();

// Object: baillie_info
const baillie_infoCanvas = document.createElement('canvas');
const baillie_infoCtx = baillie_infoCanvas.getContext('2d');
baillie_infoCanvas.width = 1024;
baillie_infoCanvas.height = 256;
baillie_infoCtx.fillStyle = '#ffffff';
baillie_infoCtx.font = 'bold 24px Arial';
baillie_infoCtx.textAlign = 'center';
baillie_infoCtx.textBaseline = 'middle';
baillie_infoCtx.fillText('Monument', 512, 128);
const baillie_infoTexture = new THREE.CanvasTexture(baillie_infoCanvas);
const baillie_infoMaterial = new THREE.SpriteMaterial({ map: baillie_infoTexture, transparent: true });
const baillie_info = new THREE.Sprite(baillie_infoMaterial);
baillie_info.position.set(7.68, 1.60, 0.00);
baillie_info.scale.set(20.00, 5.00, 1);
baillie_info.name = 'baillie_info';
baillie_info._canvas = baillie_infoCanvas;
baillie_info._ctx = baillie_infoCtx;
baillie_info._text = 'Monument';
baillie_info._color = '#ffffff';
baillie_info._font = 'Inter';
scene.add(baillie_info);
baillie_info.userData.font_size = 24;
baillie_info.userData._rosh_kind = 'text';
baillie_info.userData.font_size = 24;
baillie_info.userData._scene = 'Glasgow';
baillie_info.userData._rosh_uuid = crypto.randomUUID();

// Object: baillie_desc
const baillie_descCanvas = document.createElement('canvas');
const baillie_descCtx = baillie_descCanvas.getContext('2d');
baillie_descCanvas.width = 1024;
baillie_descCanvas.height = 256;
baillie_descCtx.fillStyle = '#888888';
baillie_descCtx.font = 'bold 16px Arial';
baillie_descCtx.textAlign = 'center';
baillie_descCtx.textBaseline = 'middle';
baillie_descCtx.fillText('Bothwell, Scotland', 512, 128);
const baillie_descTexture = new THREE.CanvasTexture(baillie_descCanvas);
const baillie_descMaterial = new THREE.SpriteMaterial({ map: baillie_descTexture, transparent: true });
const baillie_desc = new THREE.Sprite(baillie_descMaterial);
baillie_desc.position.set(7.68, 1.04, 0.00);
baillie_desc.scale.set(20.00, 5.00, 1);
baillie_desc.name = 'baillie_desc';
baillie_desc._canvas = baillie_descCanvas;
baillie_desc._ctx = baillie_descCtx;
baillie_desc._text = 'Bothwell, Scotland';
baillie_desc._color = '#888888';
baillie_desc._font = 'Inter';
scene.add(baillie_desc);
baillie_desc.userData.font_size = 16;
baillie_desc.userData._rosh_kind = 'text';
baillie_desc.userData.font_size = 16;
baillie_desc.userData._scene = 'Glasgow';
baillie_desc.userData._rosh_uuid = crypto.randomUUID();

// Object: baillie_poet
const baillie_poetCanvas = document.createElement('canvas');
const baillie_poetCtx = baillie_poetCanvas.getContext('2d');
baillie_poetCanvas.width = 1024;
baillie_poetCanvas.height = 256;
baillie_poetCtx.fillStyle = '#888888';
baillie_poetCtx.font = 'bold 14px Arial';
baillie_poetCtx.textAlign = 'center';
baillie_poetCtx.textBaseline = 'middle';
baillie_poetCtx.fillText('Poet (1762-1851)', 512, 128);
const baillie_poetTexture = new THREE.CanvasTexture(baillie_poetCanvas);
const baillie_poetMaterial = new THREE.SpriteMaterial({ map: baillie_poetTexture, transparent: true });
const baillie_poet = new THREE.Sprite(baillie_poetMaterial);
baillie_poet.position.set(7.68, 0.64, 0.00);
baillie_poet.scale.set(20.00, 5.00, 1);
baillie_poet.name = 'baillie_poet';
baillie_poet._canvas = baillie_poetCanvas;
baillie_poet._ctx = baillie_poetCtx;
baillie_poet._text = 'Poet (1762-1851)';
baillie_poet._color = '#888888';
baillie_poet._font = 'Inter';
scene.add(baillie_poet);
baillie_poet.userData.font_size = 14;
baillie_poet.userData._rosh_kind = 'text';
baillie_poet.userData.font_size = 14;
baillie_poet.userData._scene = 'Glasgow';
baillie_poet.userData._rosh_uuid = crypto.randomUUID();

// Object: baillie_credit
const baillie_creditCanvas = document.createElement('canvas');
const baillie_creditCtx = baillie_creditCanvas.getContext('2d');
baillie_creditCanvas.width = 1024;
baillie_creditCanvas.height = 256;
baillie_creditCtx.fillStyle = '#00ffff';
baillie_creditCtx.font = 'bold 12px Arial';
baillie_creditCtx.textAlign = 'center';
baillie_creditCtx.textBaseline = 'middle';
baillie_creditCtx.fillText('Andras Sandor (CC BY)', 512, 128);
const baillie_creditTexture = new THREE.CanvasTexture(baillie_creditCanvas);
const baillie_creditMaterial = new THREE.SpriteMaterial({ map: baillie_creditTexture, transparent: true });
const baillie_credit = new THREE.Sprite(baillie_creditMaterial);
baillie_credit.position.set(7.68, 0.24, 0.00);
baillie_credit.scale.set(20.00, 5.00, 1);
baillie_credit.name = 'baillie_credit';
baillie_credit._canvas = baillie_creditCanvas;
baillie_credit._ctx = baillie_creditCtx;
baillie_credit._text = 'Andras Sandor (CC BY)';
baillie_credit._color = '#00ffff';
baillie_credit._font = 'Inter';
scene.add(baillie_credit);
baillie_credit.userData.font_size = 12;
baillie_credit.userData._rosh_kind = 'text';
baillie_credit.userData.font_size = 12;
baillie_credit.userData._scene = 'Glasgow';
baillie_credit.userData._rosh_uuid = crypto.randomUUID();

// Object: floor
const floorGeometry = new THREE.BoxGeometry(0.80, 0.80, 0.80);
const floorMaterial = new THREE.MeshStandardMaterial({ color: 0xffffff });
const floor = new THREE.Mesh(floorGeometry, floorMaterial);
floor.position.set(0.00, -0.80, 0.00);
floor.name = 'floor';
scene.add(floor);
floor.userData._rosh_kind = 'mesh';
floor.userData._type = 'cube';
floor.userData._needsModelLoad = true;
floor.userData.scale = '20 0.1 20';
floor.userData._rosh_uuid = crypto.randomUUID();


// Scene/Level Visibility - Roshonic "Dimensions, Not Modes"
function updateSceneVisibility() {
    if (lobby_title) lobby_title.visible = (currentScene === 'Lobby');
    if (lobby_subtitle) lobby_subtitle.visible = (currentScene === 'Lobby');
    if (lobby_instruction1) lobby_instruction1.visible = (currentScene === 'Lobby');
    if (lobby_instruction2) lobby_instruction2.visible = (currentScene === 'Lobby');
    if (lobby_instruction3) lobby_instruction3.visible = (currentScene === 'Lobby');
    if (lobby_cube) lobby_cube.visible = (currentScene === 'Lobby');
    if (abstract_title) abstract_title.visible = (currentScene === 'Abstract');
    if (abstract_hint) abstract_hint.visible = (currentScene === 'Abstract');
    if (sculpture) sculpture.visible = (currentScene === 'Abstract');
    if (orbiter1) orbiter1.visible = (currentScene === 'Abstract');
    if (orbiter2) orbiter2.visible = (currentScene === 'Abstract');
    if (orbiter3) orbiter3.visible = (currentScene === 'Abstract');
    if (sculpture_title) sculpture_title.visible = (currentScene === 'Sculpture');
    if (sculpture_hint) sculpture_hint.visible = (currentScene === 'Sculpture');
    if (pedestal1) pedestal1.visible = (currentScene === 'Sculpture');
    if (statue1) statue1.visible = (currentScene === 'Sculpture');
    if (pedestal2) pedestal2.visible = (currentScene === 'Sculpture');
    if (statue2) statue2.visible = (currentScene === 'Sculpture');
    if (pedestal3) pedestal3.visible = (currentScene === 'Sculpture');
    if (statue3) statue3.visible = (currentScene === 'Sculpture');
    if (creative_title) creative_title.visible = (currentScene === 'Creative');
    if (creative_subtitle) creative_subtitle.visible = (currentScene === 'Creative');
    if (creative_hint) creative_hint.visible = (currentScene === 'Creative');
    if (easel) easel.visible = (currentScene === 'Creative');
    if (canvas) canvas.visible = (currentScene === 'Creative');
    if (glasgow_title) glasgow_title.visible = (currentScene === 'Glasgow');
    if (glasgow_subtitle) glasgow_subtitle.visible = (currentScene === 'Glasgow');
    if (glasgow_hint) glasgow_hint.visible = (currentScene === 'Glasgow');
    if (linen_bank) linen_bank.visible = (currentScene === 'Glasgow');
    if (linen_bank_label) linen_bank_label.visible = (currentScene === 'Glasgow');
    if (linen_bank_info) linen_bank_info.visible = (currentScene === 'Glasgow');
    if (linen_bank_credit) linen_bank_credit.visible = (currentScene === 'Glasgow');
    if (baillie_monument) baillie_monument.visible = (currentScene === 'Glasgow');
    if (baillie_label) baillie_label.visible = (currentScene === 'Glasgow');
    if (baillie_info) baillie_info.visible = (currentScene === 'Glasgow');
    if (baillie_desc) baillie_desc.visible = (currentScene === 'Glasgow');
    if (baillie_poet) baillie_poet.visible = (currentScene === 'Glasgow');
    if (baillie_credit) baillie_credit.visible = (currentScene === 'Glasgow');
    // Handle dynamically created objects
    scene.traverse((obj) => {
        if (obj.userData && obj.userData._scene) {
            obj.visible = (obj.userData._scene === currentScene);
        }
    });
}

// Set initial scene/level visibility
updateSceneVisibility();

// Engine capability manifest + runtime bridge
let CAPABILITY_MANIFEST = {"schema_version": 1, "capabilities": [{"name": "color", "handler": "color", "applies_to": ["mesh", "text", "sprite", "hud"], "tags": ["safe"], "args": ["css_or_hex"], "doc": "Change mesh or text color."}, {"name": "font_size", "handler": "font_size", "applies_to": ["text", "hud"], "tags": ["safe"], "args": ["pixels"], "doc": "Adjust text sprite font size."}, {"name": "font", "handler": "font", "applies_to": ["text", "hud"], "tags": ["safe"], "args": ["font_family"], "doc": "Set font family (default: Inter). Examples: 'Arial', 'Georgia', 'Courier New'."}, {"name": "text", "handler": "text", "applies_to": ["text", "hud"], "tags": ["safe"], "args": ["value"], "doc": "Update HUD/text sprite contents."}, {"name": "scale", "handler": "scale", "applies_to": ["mesh", "sprite"], "tags": ["safe"], "args": ["uniform|x y z"], "doc": "Scale objects uniformly or per-axis."}, {"name": "spin", "handler": "spin", "applies_to": ["mesh", "sprite"], "tags": ["safe"], "args": ["xSpeed ySpeed zSpeed"], "doc": "Rotate objects continuously (degrees per second)."}, {"name": "bounce", "handler": "bounce", "applies_to": ["mesh", "sprite"], "tags": ["safe"], "args": ["amplitude frequency"], "doc": "Apply vertical bounce animation (frequency per second)."}, {"name": "pulse", "handler": "pulse", "applies_to": ["mesh", "sprite", "text", "hud"], "tags": ["safe"], "args": ["amplitude frequency"], "doc": "Scale object in/out with a sine wave (amplitude multiplier, frequency in Hz)."}, {"name": "orbit", "handler": "orbit", "applies_to": ["mesh", "sprite"], "tags": ["safe"], "args": ["radius speed [height]"], "doc": "Orbit around the object's starting point (radius in world units, speed in degrees/sec, optional height override)."}]};
const CAPABILITY_INDEX = {};
const CAPABILITY_RUNTIME = {};
const CAPABILITY_POLICY = {"allow_tags": ["safe"], "deny_tags": [], "allow_capabilities": [], "deny_capabilities": [], "allow_passthrough": false};
CAPABILITY_POLICY.allowTags = new Set(CAPABILITY_POLICY.allow_tags || []);
CAPABILITY_POLICY.denyTags = new Set(CAPABILITY_POLICY.deny_tags || []);
CAPABILITY_POLICY.allowCapabilities = new Set(CAPABILITY_POLICY.allow_capabilities || []);
CAPABILITY_POLICY.denyCapabilities = new Set(CAPABILITY_POLICY.deny_capabilities || []);
const capabilityState = { spin: new Map(), bounce: new Map(), pulse: new Map(), orbit: new Map() };

function rebuildCapabilityIndex() {
    for (const key of Object.keys(CAPABILITY_INDEX)) delete CAPABILITY_INDEX[key];
    for (const cap of CAPABILITY_MANIFEST.capabilities || []) { CAPABILITY_INDEX[cap.name] = cap; }
}
rebuildCapabilityIndex();
if (typeof window !== 'undefined' && window.fetch) {
    fetch('capabilities.json').then(r => r.json()).then(data => {
        if (data && data.capabilities) { CAPABILITY_MANIFEST = data; rebuildCapabilityIndex(); }
    }).catch(() => { console.warn('Capability manifest not found (capabilities.json)'); });
}

function getObjectKind(obj) {
    if (!obj || !obj.userData) return 'mesh';
    return obj.userData._rosh_kind || 'mesh';
}
function capabilityAllowed(cap) {
    if (CAPABILITY_POLICY.denyCapabilities.has(cap.name)) return false;
    if (CAPABILITY_POLICY.allowCapabilities.size && !CAPABILITY_POLICY.allowCapabilities.has(cap.name)) return false;
    for (const tag of cap.tags || []) { if (CAPABILITY_POLICY.denyTags.has(tag)) return false; }
    if (!cap.tags || !cap.tags.length) return true;
    return cap.tags.some(tag => CAPABILITY_POLICY.allowTags.has(tag));
}
function capabilityAppliesTo(cap, obj) {
    if (!cap.applies_to || !cap.applies_to.length) return true;
    const kind = getObjectKind(obj);
    return cap.applies_to.includes(kind);
}
function describeCapability(cap) {
    if (!cap) return '';
    const args = cap.args && cap.args.length ? ' (' + cap.args.join(', ') + ')' : '';
    const doc = cap.doc ? ' - ' + cap.doc : '';
    return cap.name + args + doc;
}
function logCapabilityHelp(cap) {
    if (!cap) { log('Unknown capability.', 'err'); return; }
    const status = capabilityAllowed(cap) ? 'enabled' : 'disabled by policy';
    log(describeCapability(cap), capabilityAllowed(cap) ? 'cyan' : 'err');
    if (cap.tags && cap.tags.length) log('  Tags: ' + cap.tags.join(', '), 'dim');
    log('  Status: ' + status, capabilityAllowed(cap) ? 'dim' : 'err');
    if (cap.args && cap.args.length) log('  Usage: ' + cap.name + ' ' + cap.args.join(' '), 'dim');
    if (!capabilityAllowed(cap) && cap.tags && cap.tags.length) {
        const tagHint = cap.tags.map(t => '"' + t + '"').join(', ');
        log('  Enable via _meta/threejs.toml [engine_capabilities] allow = [' + tagHint + ']', 'dim');
    }
}
function availableCapabilitiesFor(obj) {
    const kind = getObjectKind(obj);
    return (CAPABILITY_MANIFEST.capabilities || []).filter(cap => capabilityAllowed(cap) && (!cap.applies_to || cap.applies_to.includes(kind)));
}
function coerceSingleValue(tokens) {
    if (!tokens || !tokens.length) return null;
    if (tokens.length === 1) {
        const raw = tokens[0];
        if (raw === 'true') return true;
        if (raw === 'false') return false;
        const n = parseFloat(raw);
        if (!Number.isNaN(n)) return n;
        return raw;
    }
    return tokens.join(' ');
}
function coerceNumbers(tokens) {
    if (!tokens || !tokens.length) return [];
    return tokens.map(t => parseFloat(t)).filter(v => !Number.isNaN(v));
}
function handleCoreSet(obj, prop, tokens) {
    const value = coerceSingleValue(tokens);
    if (value === null || value === undefined) return { ok: false };
    const name = obj && obj.name ? obj.name : '(object)';
    const numVal = typeof value === 'number' ? value : parseFloat(value);
    if (prop === 'x' && !Number.isNaN(numVal)) {
        const prev = obj.position.x;
        obj.position.x = numVal;
        return { ok: true, description: `${name}.x`, undo: () => { obj.position.x = prev; }, redo: () => { obj.position.x = numVal; } };
    }
    if (prop === 'y' && !Number.isNaN(numVal)) {
        const prev = obj.position.y;
        obj.position.y = numVal;
        return { ok: true, description: `${name}.y`, undo: () => { obj.position.y = prev; }, redo: () => { obj.position.y = numVal; } };
    }
    if (prop === 'z' && !Number.isNaN(numVal)) {
        const prev = obj.position.z;
        obj.position.z = numVal;
        return { ok: true, description: `${name}.z`, undo: () => { obj.position.z = prev; }, redo: () => { obj.position.z = numVal; } };
    }
    if (prop === 'visible') {
        const prev = obj.visible;
        const next = value === true || value === 'true';
        obj.visible = next;
        return { ok: true, description: `${name}.visible`, undo: () => { obj.visible = prev; }, redo: () => { obj.visible = next; } };
    }
    return { ok: false };
}
function redrawTextSprite(obj, textOverride) {
    if (!obj || !obj._ctx) return;
    const fontSize = obj.userData.font_size || 48;
    const fontFamily = obj._font || 'Inter';
    obj._ctx.clearRect(0, 0, obj._canvas.width, obj._canvas.height);
    obj._ctx.font = 'bold ' + fontSize + 'px ' + fontFamily;
    obj._ctx.textAlign = 'center';
    obj._ctx.textBaseline = 'middle';
    obj._ctx.fillStyle = obj._color || '#ffffff';
    obj._ctx.fillText(textOverride || obj._text || '', obj._canvas.width / 2, obj._canvas.height / 2);
    if (obj.material && obj.material.map) obj.material.map.needsUpdate = true;
}
function applyCapabilityBridge(obj, prop, tokens) {
    const cap = CAPABILITY_INDEX[prop];
    if (!cap) {
        const options = availableCapabilitiesFor(obj).map(entry => entry.name).join(', ') || null;
        return { ok: false, reason: 'unknown', message: "Unknown property '" + prop + "'.", suggestion: options };
    }
    if (!capabilityAllowed(cap)) { return { ok: false, reason: 'denied', message: "Capability '" + prop + "' is disabled." }; }
    if (!capabilityAppliesTo(cap, obj)) { return { ok: false, reason: 'not_applicable', message: "'" + prop + "' not supported for this object." }; }
    const handler = CAPABILITY_RUNTIME[prop];
    if (!handler) { return { ok: false, reason: 'missing_handler', message: "No handler for '" + prop + "'." }; }
    try {
        const result = handler({ object: obj, tokens, raw: tokens.join(' '), numbers: coerceNumbers(tokens) });
        if (result && typeof result === 'object' && typeof result.undo === 'function') {
            return { ok: true, undo: result.undo, redo: typeof result.redo === 'function' ? result.redo : null, description: result.description || `${obj.name || '(object)'}.${prop}` };
        }
        return { ok: true, description: `${obj.name || '(object)'}.${prop}` };
    } catch (err) {
        const msg = err && err.message ? err.message : String(err);
        return { ok: false, reason: 'error', message: msg };
    }
}
CAPABILITY_RUNTIME['color'] = function(ctx) {
    const target = ctx.object;
    if (!target) throw new Error('No object to color');
    const val = ctx.raw && ctx.raw.trim() ? ctx.raw.trim() : '#ffffff';
    const description = `${target.name || '(object)'}.color`;
    if (target._ctx) {
        const prev = target._color;
        const apply = (color) => {
            if (color === undefined) delete target._color; else target._color = color;
            redrawTextSprite(target);
        };
        apply(val);
        return { description, undo: () => apply(prev), redo: () => apply(val) };
    } else if (target.material && target.material.color) {
        const prev = target.material.color.getHex();
        target.material.color.set(val);
        return { description, undo: () => { if (target.material && target.material.color) target.material.color.setHex(prev); }, redo: () => { if (target.material && target.material.color) target.material.color.set(val); } };
    } else { throw new Error('Color not supported for this object'); }
};
CAPABILITY_RUNTIME['font_size'] = function(ctx) {
    const target = ctx.object;
    if (!target || !target._ctx) throw new Error('Only text sprites support font_size');
    const n = parseFloat(ctx.tokens[0]);
    if (Number.isNaN(n)) throw new Error('Provide a numeric font size');
    const prev = target.userData.font_size;
    const description = `${target.name || '(object)'}.font_size`;
    const apply = (size) => {
        if (size === undefined) delete target.userData.font_size; else target.userData.font_size = size;
        redrawTextSprite(target);
    };
    apply(n);
    return { description, undo: () => apply(prev), redo: () => apply(n) };
};
CAPABILITY_RUNTIME['font'] = function(ctx) {
    const target = ctx.object;
    if (!target || !target._ctx) throw new Error('Only text sprites support font');
    if (!ctx.raw || !ctx.raw.trim()) throw new Error('Provide a font family name');
    const prev = target._font;
    const description = `${target.name || '(object)'}.font`;
    const apply = (fontName) => {
        if (fontName === undefined) delete target._font; else target._font = fontName;
        redrawTextSprite(target);
    };
    const nextFont = ctx.raw.trim();
    apply(nextFont);
    return { description, undo: () => apply(prev), redo: () => apply(nextFont) };
};
CAPABILITY_RUNTIME['text'] = function(ctx) {
    const target = ctx.object;
    if (!target || !target._ctx) throw new Error('Only text sprites support text updates');
    const prev = target._text;
    const description = `${target.name || '(object)'}.text`;
    const apply = (textValue) => { target._text = textValue; redrawTextSprite(target, textValue); };
    apply(ctx.raw);
    return { description, undo: () => apply(prev), redo: () => apply(ctx.raw) };
};
CAPABILITY_RUNTIME['scale'] = function(ctx) {
    const target = ctx.object;
    if (!target || !target.scale) throw new Error('Scale not supported');
    const nums = ctx.numbers;
    if (!nums.length) throw new Error('Provide numeric scale values');
    const prev = { x: target.scale.x, y: target.scale.y, z: target.scale.z };
    const description = `${target.name || '(object)'}.scale`;
    const apply = (vals) => { if (target.scale) target.scale.set(vals.x, vals.y, vals.z); };
    const next = nums.length === 1 ? { x: nums[0], y: nums[0], z: nums[0] } : { x: nums[0], y: nums[1] ?? nums[0], z: nums[2] ?? nums[0] };
    apply(next);
    return { description, undo: () => apply(prev), redo: () => apply(next) };
};
CAPABILITY_RUNTIME['spin'] = function(ctx) {
    const target = ctx.object;
    if (!target) throw new Error('No object to spin');
    const prevState = capabilityState.spin.get(target);
    const prevSnapshot = prevState ? { x: prevState.x, y: prevState.y, z: prevState.z } : null;
    const prevUserData = Array.isArray(target.userData._spin) ? target.userData._spin.slice() : null;
    const description = `${target.name || '(object)'}.spin`;
    const restorePrev = () => {
        if (prevSnapshot) {
            capabilityState.spin.set(target, { x: prevSnapshot.x, y: prevSnapshot.y, z: prevSnapshot.z });
            if (prevUserData) target.userData._spin = prevUserData.slice(); else delete target.userData._spin;
        } else {
            capabilityState.spin.delete(target);
            delete target.userData._spin;
        }
    };
    const raw = (ctx.raw || '').trim();
    const applyOff = () => { capabilityState.spin.delete(target); delete target.userData._spin; };
    if (!raw || raw === 'off') {
        const hadPrev = !!prevSnapshot || !!prevUserData;
        applyOff();
        if (!hadPrev) return { description };
        return { description, undo: restorePrev, redo: applyOff };
    }
    const nums = ctx.numbers;
    if (!nums.length) throw new Error('Provide rotation speed(s)');
    const speeds = [nums[0] || 0, nums[1] ?? nums[0] ?? 0, nums[2] ?? 0].map(v => v * Math.PI / 180);
    const applySpin = () => { capabilityState.spin.set(target, { x: speeds[0], y: speeds[1], z: speeds[2] }); target.userData._spin = speeds.slice(); };
    if (speeds.every(v => v === 0)) {
        const hadPrev = !!prevSnapshot || !!prevUserData;
        applyOff();
        if (!hadPrev) return { description };
        return { description, undo: restorePrev, redo: applyOff };
    }
    applySpin();
    return { description, undo: restorePrev, redo: applySpin };
};
CAPABILITY_RUNTIME['bounce'] = function(ctx) {
    const target = ctx.object;
    if (!target) throw new Error('No object to bounce');
    const prevState = capabilityState.bounce.get(target);
    const prevSnapshot = prevState ? { amplitude: prevState.amplitude, frequency: prevState.frequency, base: prevState.base, elapsed: prevState.elapsed } : null;
    const prevUserData = target.userData._bounce ? { amplitude: target.userData._bounce.amplitude, freq: target.userData._bounce.freq } : null;
    const description = `${target.name || '(object)'}.bounce`;
    const restorePrev = () => {
        if (prevSnapshot) {
            capabilityState.bounce.set(target, { amplitude: prevSnapshot.amplitude, frequency: prevSnapshot.frequency, base: prevSnapshot.base, elapsed: prevSnapshot.elapsed || 0 });
            if (prevUserData) target.userData._bounce = { amplitude: prevUserData.amplitude, freq: prevUserData.freq }; else delete target.userData._bounce;
        } else {
            capabilityState.bounce.delete(target);
            delete target.userData._bounce;
        }
    };
    const raw = (ctx.raw || '').trim();
    const applyOff = () => { capabilityState.bounce.delete(target); delete target.userData._bounce; };
    if (!raw || raw === 'off') {
        const hadPrev = !!prevSnapshot || !!prevUserData;
        applyOff();
        if (!hadPrev) return { description };
        return { description, undo: restorePrev, redo: applyOff };
    }
    const nums = ctx.numbers;
    if (!nums.length) throw new Error('Provide amplitude and optional frequency');
    const amplitude = nums[0];
    const freq = nums[1] || 1;
    if (amplitude === 0) {
        const hadPrev = !!prevSnapshot || !!prevUserData;
        applyOff();
        if (!hadPrev) return { description };
        return { description, undo: restorePrev, redo: applyOff };
    }
    const applyBounce = () => { capabilityState.bounce.set(target, { amplitude, frequency: freq * Math.PI * 2, base: target.position.y, elapsed: 0 }); target.userData._bounce = { amplitude, freq }; };
    applyBounce();
    return { description, undo: restorePrev, redo: applyBounce };
};
CAPABILITY_RUNTIME['pulse'] = function(ctx) {
    const target = ctx.object;
    if (!target || !target.scale) throw new Error('Pulse requires scale support');
    const prevState = capabilityState.pulse.get(target);
    const prevSnapshot = prevState ? {
        amplitude: prevState.amplitude,
        frequency: prevState.frequency,
        elapsed: prevState.elapsed || 0,
        base: prevState.base ? { x: prevState.base.x, y: prevState.base.y, z: prevState.base.z } : null
    } : null;
    const prevUserData = target.userData._pulse ? { amplitude: target.userData._pulse.amplitude, freq: target.userData._pulse.freq } : null;
    const description = `${target.name || '(object)'}.pulse`;
    const restorePrev = () => {
        if (prevSnapshot) {
            capabilityState.pulse.set(target, {
                amplitude: prevSnapshot.amplitude,
                frequency: prevSnapshot.frequency,
                elapsed: prevSnapshot.elapsed || 0,
                base: prevSnapshot.base ? { x: prevSnapshot.base.x, y: prevSnapshot.base.y, z: prevSnapshot.base.z } : null
            });
            if (prevSnapshot.base && target.scale) target.scale.set(prevSnapshot.base.x, prevSnapshot.base.y, prevSnapshot.base.z);
            if (prevUserData) target.userData._pulse = { amplitude: prevUserData.amplitude, freq: prevUserData.freq }; else delete target.userData._pulse;
        } else {
            capabilityState.pulse.delete(target);
            delete target.userData._pulse;
        }
    };
    const raw = (ctx.raw || '').trim();
    const clearPulse = () => {
        const active = capabilityState.pulse.get(target);
        if (active && active.base && target.scale) target.scale.set(active.base.x, active.base.y, active.base.z);
        capabilityState.pulse.delete(target);
        delete target.userData._pulse;
    };
    if (!raw || raw === 'off') {
        const hadPrev = !!prevSnapshot || !!prevUserData;
        clearPulse();
        if (!hadPrev) return { description };
        return { description, undo: restorePrev, redo: clearPulse };
    }
    const nums = ctx.numbers;
    if (!nums.length) throw new Error('Provide amplitude (scale delta) and optional frequency');
    const amplitude = nums[0];
    const freq = nums[1] || 1;
    if (amplitude === 0) {
        const hadPrev = !!prevSnapshot || !!prevUserData;
        clearPulse();
        if (!hadPrev) return { description };
        return { description, undo: restorePrev, redo: clearPulse };
    }
    const applyPulse = () => {
        capabilityState.pulse.set(target, { amplitude, frequency: freq * Math.PI * 2, elapsed: 0, base: { x: target.scale.x, y: target.scale.y, z: target.scale.z } });
        target.userData._pulse = { amplitude, freq };
    };
    applyPulse();
    return { description, undo: restorePrev, redo: applyPulse };
};
CAPABILITY_RUNTIME['orbit'] = function(ctx) {
    const target = ctx.object;
    if (!target) throw new Error('No object to orbit');
    const prevState = capabilityState.orbit.get(target);
    const prevSnapshot = prevState ? {
        center: prevState.center ? { x: prevState.center.x, z: prevState.center.z } : null,
        radius: prevState.radius,
        speed: prevState.speed,
        angle: prevState.angle || 0,
        height: prevState.height
    } : null;
    const prevUserData = target.userData._orbit ? {
        radius: target.userData._orbit.radius,
        speed: target.userData._orbit.speed,
        height: target.userData._orbit.height,
        centerX: target.userData._orbit.centerX,
        centerZ: target.userData._orbit.centerZ
    } : null;
    const description = `${target.name || '(object)'}.orbit`;
    const restorePrev = () => {
        if (prevSnapshot) {
            const center = prevSnapshot.center ? { x: prevSnapshot.center.x, z: prevSnapshot.center.z } : { x: target.position.x, z: target.position.z };
            capabilityState.orbit.set(target, { center, radius: prevSnapshot.radius, speed: prevSnapshot.speed, angle: prevSnapshot.angle || 0, height: prevSnapshot.height });
            if (prevUserData) {
                target.userData._orbit = { radius: prevUserData.radius, speed: prevUserData.speed, height: prevUserData.height, centerX: prevUserData.centerX, centerZ: prevUserData.centerZ };
            } else delete target.userData._orbit;
        } else {
            capabilityState.orbit.delete(target);
            delete target.userData._orbit;
        }
    };
    const raw = (ctx.raw || '').trim();
    const clearOrbit = () => { capabilityState.orbit.delete(target); delete target.userData._orbit; };
    if (!raw || raw === 'off') {
        const hadPrev = !!prevSnapshot || !!prevUserData;
        clearOrbit();
        if (!hadPrev) return { description };
        return { description, undo: restorePrev, redo: clearOrbit };
    }
    const nums = ctx.numbers;
    if (!nums.length) throw new Error('Provide radius and optional speed/height');
    const radius = nums[0];
    if (radius <= 0) throw new Error('Radius must be positive');
    const speedDeg = nums[1] || 30;
    const height = nums[2];
    const center = { x: target.position.x, z: target.position.z };
    const applyOrbit = () => {
        capabilityState.orbit.set(target, {
            center,
            radius,
            speed: speedDeg * Math.PI / 180,
            angle: 0,
            height: Number.isFinite(height) ? height : target.position.y
        });
        target.userData._orbit = { radius, speed: speedDeg, height: Number.isFinite(height) ? height : target.position.y, centerX: center.x, centerZ: center.z };
    };
    applyOrbit();
    return { description, undo: restorePrev, redo: applyOrbit };
};

function restoreCapabilityState(obj) {
    if (!obj || !obj.userData) return;
    const spin = obj.userData._spin;
    if (Array.isArray(spin) && spin.length >= 3) {
        capabilityState.spin.set(obj, { x: spin[0], y: spin[1], z: spin[2] });
        obj.userData._spin = spin;
    } else { capabilityState.spin.delete(obj); delete obj.userData._spin; }
    const bounce = obj.userData._bounce;
    if (bounce && typeof bounce.amplitude === 'number') {
        const freq = (bounce.freq || bounce.frequency || 1) * Math.PI * 2;
        capabilityState.bounce.set(obj, { amplitude: bounce.amplitude, frequency: freq, base: obj.position.y, elapsed: 0 });
        obj.userData._bounce = { amplitude: bounce.amplitude, freq: bounce.freq || bounce.frequency || 1 };
    } else { capabilityState.bounce.delete(obj); delete obj.userData._bounce; }
    const pulse = obj.userData._pulse;
    if (pulse && typeof pulse.amplitude === 'number' && obj.scale) {
        capabilityState.pulse.set(obj, { amplitude: pulse.amplitude, frequency: (pulse.freq || 1) * Math.PI * 2, elapsed: 0, base: { x: obj.scale.x, y: obj.scale.y, z: obj.scale.z } });
        obj.userData._pulse = { amplitude: pulse.amplitude, freq: pulse.freq || 1 };
    } else { capabilityState.pulse.delete(obj); delete obj.userData._pulse; }
    const orbit = obj.userData._orbit;
    if (orbit && typeof orbit.radius === 'number' && orbit.radius > 0) {
        const center = { x: orbit.centerX ?? obj.position.x, z: orbit.centerZ ?? obj.position.z };
        capabilityState.orbit.set(obj, { center, radius: orbit.radius, speed: (orbit.speed || 30) * Math.PI / 180, angle: 0, height: orbit.height ?? obj.position.y });
        obj.userData._orbit = { radius: orbit.radius, speed: orbit.speed || 30, height: orbit.height ?? obj.position.y, centerX: center.x, centerZ: center.z };
    } else { capabilityState.orbit.delete(obj); delete obj.userData._orbit; }
}
let _roshLastFrame = performance.now();
// Animation Loop
function animate() {
    requestAnimationFrame(animate);
    const now = performance.now();
    const delta = (now - _roshLastFrame) / 1000;
    _roshLastFrame = now;

    // Engine capability-driven transforms
    capabilityState.spin.forEach((state, target) => {
        if (!target) return;
        target.rotation.x += state.x * delta;
        target.rotation.y += state.y * delta;
        target.rotation.z += state.z * delta;
    });
    capabilityState.bounce.forEach((state, target) => {
        if (!target) return;
        state.elapsed = (state.elapsed || 0) + delta;
        const offset = Math.sin(state.elapsed * state.frequency) * state.amplitude;
        target.position.y = state.base + offset;
    });
    capabilityState.pulse.forEach((state, target) => {
        if (!target || !target.scale || !state.base) return;
        state.elapsed = (state.elapsed || 0) + delta;
        const factor = 1 + Math.sin(state.elapsed * state.frequency) * state.amplitude;
        target.scale.set(state.base.x * factor, state.base.y * factor, state.base.z * factor);
    });
    capabilityState.orbit.forEach((state, target) => {
        if (!target) return;
        state.angle = (state.angle || 0) + state.speed * delta;
        target.position.x = state.center.x + Math.cos(state.angle) * state.radius;
        target.position.z = state.center.z + Math.sin(state.angle) * state.radius;
        target.position.y = state.height;
    });

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

// Initialize capability states from userData
scene.traverse(obj => {
    if (!obj.userData) return;
    if (Array.isArray(obj.userData._spin) && obj.userData._spin.length >= 3) {
        const s = obj.userData._spin;
        capabilityState.spin.set(obj, { x: s[0], y: s[1], z: s[2] });
    }
    if (Array.isArray(obj.userData._bounce) && obj.userData._bounce.length >= 2) {
        const b = obj.userData._bounce;
        capabilityState.bounce.set(obj, { amplitude: b[0], frequency: b[1] * Math.PI * 2, baseY: obj.position.y, phase: 0 });
    }
    if (Array.isArray(obj.userData._pulse) && obj.userData._pulse.length >= 2) {
        const p = obj.userData._pulse;
        capabilityState.pulse.set(obj, { amount: p[0], frequency: p[1] * Math.PI * 2, baseScale: obj.scale.x, phase: 0 });
    }
    if (Array.isArray(obj.userData._orbit) && obj.userData._orbit.length >= 3) {
        const o = obj.userData._orbit;
        capabilityState.orbit.set(obj, { center: new THREE.Vector3(0, obj.position.y, 0), radius: o[0], speed: o[1] * Math.PI / 180, angle: 0, height: o[2] || obj.position.y });
    }
});

const KNOWN_OBJECTS = {
    banana: { shape: 'cylinder', color: 0xffe135, scaleX: 0.3, scaleY: 1.2, scaleZ: 0.3, model: '3d_glb/banana.glb', credit: 'Banana by Batuhan13 (CC BY 4.0)' },
    apple: { shape: 'sphere', color: 0xff0000, scaleX: 1.0, scaleY: 1.0, scaleZ: 1.0, model: '3d_glb/apple.glb', credit: 'Apple by elements (CC BY 4.0)' },
    orange: { shape: 'sphere', color: 0xff8800, scaleX: 1.0, scaleY: 1.0, scaleZ: 1.0 },
    lemon: { shape: 'sphere', color: 0xffff00, scaleX: 1.0, scaleY: 1.2, scaleZ: 1.0 },
    grape: { shape: 'sphere', color: 0x800080, scaleX: 0.5, scaleY: 0.5, scaleZ: 0.5 },
    cherry: { shape: 'sphere', color: 0xdc143c, scaleX: 0.4, scaleY: 0.4, scaleZ: 0.4 },
    watermelon: { shape: 'sphere', color: 0x228b22, scaleX: 1.5, scaleY: 1.0, scaleZ: 1.2 },
    tree: { shape: 'cylinder', color: 0x228b22, scaleX: 1.0, scaleY: 2.0, scaleZ: 1.0, model: '3d_glb/pine_tree.glb', credit: 'Pine tree by Andriy Shekh (CC BY 4.0)' },
    rock: { shape: 'box', color: 0x808080, scaleX: 1.0, scaleY: 0.6, scaleZ: 1.0 },
    flower: { shape: 'sphere', color: 0xff69b4, scaleX: 0.5, scaleY: 0.8, scaleZ: 0.5 },
    bush: { shape: 'sphere', color: 0x228b22, scaleX: 1.0, scaleY: 0.7, scaleZ: 1.0 },
    mushroom: { shape: 'sphere', color: 0xff0000, scaleX: 0.6, scaleY: 0.5, scaleZ: 0.6 },
    coin: { shape: 'cylinder', color: 0xffd700, scaleX: 1.0, scaleY: 0.1, scaleZ: 1.0 },
    gem: { shape: 'sphere', color: 0xffff, scaleX: 0.5, scaleY: 0.7, scaleZ: 0.5 },
    star: { shape: 'sphere', color: 0xffff00, scaleX: 0.8, scaleY: 0.8, scaleZ: 0.8 },
    heart: { shape: 'sphere', color: 0xff69b4, scaleX: 1.0, scaleY: 1.0, scaleZ: 1.0 },
    key: { shape: 'box', color: 0xffd700, scaleX: 0.2, scaleY: 0.8, scaleZ: 0.1 },
    treasure: { shape: 'box', color: 0x8b4513, scaleX: 1.0, scaleY: 0.7, scaleZ: 1.0 },
    player: { shape: 'box', color: 0x4169e1, scaleX: 1.0, scaleY: 1.8, scaleZ: 1.0 },
    enemy: { shape: 'box', color: 0xff4500, scaleX: 1.0, scaleY: 1.5, scaleZ: 1.0 },
    npc: { shape: 'box', color: 0x32cd32, scaleX: 1.0, scaleY: 1.6, scaleZ: 1.0 },
    ghost: { shape: 'sphere', color: 0xffffff, scaleX: 1.0, scaleY: 1.0, scaleZ: 1.0, opacity: 0.6 },
    monster: { shape: 'box', color: 0x800080, scaleX: 1.3, scaleY: 1.8, scaleZ: 1.3 },
    orc: { shape: 'box', color: 0x228b22, scaleX: 2.5, scaleY: 2.5, scaleZ: 2.5, model: '3d_glb/orc_warrior.glb', credit: 'Orc_Warrior by EvgeshQa (CC BY 4.0)' },
    ball: { shape: 'sphere', color: 0xff0000, scaleX: 1.0, scaleY: 1.0, scaleZ: 1.0 },
    football: { shape: 'sphere', color: 0xffffff, scaleX: 1.0, scaleY: 1.0, scaleZ: 1.0, model: '3d_glb/cheap_soccer_ball.glb', credit: 'Cheap Soccer Ball by Blender3D (CC BY 4.0)' },
    cube: { shape: 'box', color: 0xff, scaleX: 1.0, scaleY: 1.0, scaleZ: 1.0 },
    cylinder: { shape: 'cylinder', color: 0xff00, scaleX: 1.0, scaleY: 1.0, scaleZ: 1.0 },
    sphere: { shape: 'sphere', color: 0xffffff, scaleX: 1.0, scaleY: 1.0, scaleZ: 1.0 },
    box: { shape: 'box', color: 0x808080, scaleX: 1.0, scaleY: 1.0, scaleZ: 1.0 },
    wall: { shape: 'box', color: 0x8b4513, scaleX: 0.2, scaleY: 2.0, scaleZ: 1.0 },
    platform: { shape: 'box', color: 0x8b4513, scaleX: 2.0, scaleY: 0.2, scaleZ: 2.0 },
    door: { shape: 'box', color: 0x8b4513, scaleX: 0.8, scaleY: 1.8, scaleZ: 0.1 },
    crate: { shape: 'box', color: 0xdeb887, scaleX: 1.0, scaleY: 1.0, scaleZ: 1.0, model: '3d_glb/crate_box.glb', credit: 'Crate box by KloWorks (CC BY 4.0)' },
    barrel: { shape: 'cylinder', color: 0x8b4513, scaleX: 1.0, scaleY: 1.2, scaleZ: 1.0, model: '3d_glb/stylized_low_poly_wooden_barrell.glb', credit: 'Stylized low poly wooden barrell by pgonarg (CC BY 4.0)' },
    car: { shape: 'box', color: 0xff0000, scaleX: 1.5, scaleY: 0.6, scaleZ: 0.8 },
    ship: { shape: 'box', color: 0x8b4513, scaleX: 0.8, scaleY: 1.0, scaleZ: 2.0 },
    rocket: { shape: 'cylinder', color: 0xc0c0c0, scaleX: 0.4, scaleY: 2.0, scaleZ: 0.4 },
    castle: { shape: 'box', color: 0x808080, scaleX: 1.0, scaleY: 1.0, scaleZ: 1.0, model: '3d_glb/castle.glb', credit: 'Castle by hamidkhan224 (CC BY 4.0)' },
    linen_bank: { shape: 'box', color: 0x808080, scaleX: 1.0, scaleY: 1.0, scaleZ: 1.0, model: '3d_glb/linen_bank.glb', credit: 'Linen Bank by CheriePotter (CC BY 4.0)' },
    joanna_baillie_monument: { shape: 'box', color: 0x808080, scaleX: 1.0, scaleY: 1.0, scaleZ: 1.0, model: '3d_glb/joanna_baillie_monument.glb', credit: 'Joanna Baillie Monument by Andras Sandor (CC BY 4.0)' },
    explosion: { shape: 'sphere', color: 0xff4500, scaleX: 1.5, scaleY: 1.5, scaleZ: 1.5 },
    spark: { shape: 'sphere', color: 0xffff00, scaleX: 0.2, scaleY: 0.2, scaleZ: 0.2 },
    cloud: { shape: 'sphere', color: 0xffffff, scaleX: 2.0, scaleY: 0.8, scaleZ: 1.5, opacity: 0.8 },
};

// Load 3D models for pre-placed objects with known types
scene.traverse(obj => {
    if (obj.userData && obj.userData._needsModelLoad && obj.userData._type) {
        const typeName = obj.userData._type;
        const preset = KNOWN_OBJECTS[typeName];
        if (preset && preset.model && meta.useModels) {
            const pos = obj.position.clone();
            const size = obj.userData.size || 1;
            const spin = obj.userData._spin;
            const objScene = obj.userData._scene;
            const objName = obj.name;
            gltfLoader.load(preset.model, (gltf) => {
                const model = gltf.scene;
                model.name = objName;
                model.userData._type = typeName;
                model.userData._rosh_kind = 'model';
                if (objScene) model.userData._scene = objScene;
                if (spin) model.userData._spin = spin;
                if (preset.credit) model.userData._credit = preset.credit;
                const box = new THREE.Box3().setFromObject(model);
                const modelSize = box.getSize(new THREE.Vector3());
                const maxDim = Math.max(modelSize.x, modelSize.y, modelSize.z);
                const normalizeScale = 1 / maxDim;
                const gs = meta.modelScale || 2;
                model.scale.set(normalizeScale * size * gs, normalizeScale * size * gs, normalizeScale * size * gs);
                // Center the model based on its bounding box (fixes models with offset origins)
                const scaledBox = new THREE.Box3().setFromObject(model);
                const center = scaledBox.getCenter(new THREE.Vector3());
                model.position.set(pos.x - center.x, pos.y - center.y, pos.z - center.z);
                scene.remove(obj);
                scene.add(model);
                if (objScene && objScene !== currentScene) model.visible = false;
            });
        }
    }
});

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
#rosh-input-line { padding: 10px; border-top: 1px solid #0f0; display: flex; gap: 8px; align-items: center; }
#rosh-input-line input { flex: 1; background: #111; border: 1px solid #0f0;
  color: #0f0; padding: 8px; font-family: inherit; }
#rosh-voice { width: 24px; height: 24px; cursor: pointer; opacity: 0.5; transition: all 0.2s; }
#rosh-voice:hover { opacity: 0.8; }
#rosh-voice.listening { opacity: 1; animation: pulse 1s infinite; }
@keyframes pulse { 0%,100% { transform: scale(1); } 50% { transform: scale(1.2); } }
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
    <input type='text' id='rosh-input' placeholder='type or Ctrl+Space for voice' autocomplete='off'>
    <svg id='rosh-voice' viewBox='0 0 24 24' fill='#0f0' title='Click or Ctrl+Space to speak'>
      <path d='M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm-1-9c0-.55.45-1 1-1s1 .45 1 1v6c0 .55-.45 1-1 1s-1-.45-1-1V5zm6 6c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z'/>
    </svg>
  </div>`;
document.body.appendChild(consoleDiv);

const output = document.getElementById('rosh-output');
const input = document.getElementById('rosh-input');
let currentObject = null, currentObjectName = null;
let currentSelection = [], currentSelectionType = null;
const cmdHistory = []; let historyIdx = -1;
const undoStack = [];
const redoStack = [];
let undoGroup = 0;
let lastUserCommand = null;
let bulkCreateMode = false;
let bulkCreateCount = 0;
const BULK_LOG_LIMIT = 10;
let twinSocket = null, twinUserId = null, twinWorldId = null;
const TWIN_SERVER = 'wss://rosh.cloud/ws/world/';

function log(msg, cls='') {
    const div = document.createElement('div'); div.className = cls;
    div.textContent = msg; output.appendChild(div); output.scrollTop = output.scrollHeight;
}

function twinCreateObject(id, data, announce = true) {
    const colors = {red:0xff0000, green:0x00ff00, blue:0x0000ff, yellow:0xffff00, cyan:0x00ffff, magenta:0xff00ff, white:0xffffff, orange:0xff8800, purple:0x8800ff, pink:0xff88ff, gray:0x888888, black:0x111111};
    let color = colors[data.color] || (typeof data.color === 'string' && data.color.startsWith('#') ? parseInt(data.color.slice(1), 16) : 0x00ff00);
    const size = data.size || 1;
    let geom, mesh;
    const shapeType = data.type || 'cube';
    if (shapeType === 'sphere' || shapeType === 'ball') geom = new THREE.SphereGeometry(size);
    else if (shapeType === 'cylinder') geom = new THREE.CylinderGeometry(size*0.5, size*0.5, size);
    else geom = new THREE.BoxGeometry(size, size, size);
    mesh = new THREE.Mesh(geom, new THREE.MeshStandardMaterial({ color: color }));
    mesh.name = id;
    mesh.userData._type = shapeType;
    mesh.userData._twin = true;
    mesh.position.set(data.x || 0, data.y || 1, data.z || 0);
    scene.add(mesh);
    gameObjects[id] = mesh;
    if (announce) log('Shared: ' + id + ' created by ' + (data.created_by || 'remote'), 'cyan');
}

function twinBroadcastCreate(name, type, x, y, z, color, size) {
    if (twinSocket && twinSocket.readyState === WebSocket.OPEN) {
        const colorStr = typeof color === 'number' ? '#' + color.toString(16).padStart(6, '0') : color;
        twinSocket.send(JSON.stringify({ type: 'CREATE', id: name, object_type: type, x, y, z, color: colorStr, size }));
    }
}

function pushUndo(description, undoFn, redoFn) {
    if (typeof undoFn !== 'function') return;
    undoStack.push({ description: description || 'change', undo: undoFn, redo: typeof redoFn === 'function' ? redoFn : null, group: undoGroup });
    if (undoStack.length > 100) undoStack.shift();
    redoStack.length = 0;
}

function performUndo(count = 1) {
    if (!undoStack.length) { log('Nothing to undo', 'err'); return; }
    // Undo by group: pop all entries with the same group as the most recent
    for (let step = 0; step < count; step++) {
        if (!undoStack.length) break;
        const targetGroup = undoStack[undoStack.length - 1].group;
        const groupEntries = [];
        // Collect all entries in this group (they should be contiguous at the end)
        while (undoStack.length && undoStack[undoStack.length - 1].group === targetGroup) {
            groupEntries.push(undoStack.pop());
        }
        // Execute undos in reverse order (most recent first)
        let undoCount = 0;
        for (const entry of groupEntries) {
            try {
                entry.undo();
                undoCount++;
                if (entry.redo) redoStack.push(entry);
            } catch (err) {
                log('Undo failed: ' + (err && err.message ? err.message : err), 'err');
            }
        }
        if (undoCount > 1) log('Undo: ' + groupEntries[0].description + ' (' + undoCount + ' operations)', 'ok');
        else if (undoCount === 1) log('Undo: ' + groupEntries[0].description, 'ok');
    }
}

function performRedo(count = 1) {
    if (!redoStack.length) { log('Nothing to redo', 'err'); return; }
    const steps = Math.min(Math.max(1, count), redoStack.length);
    for (let i = 0; i < steps; i++) {
        const entry = redoStack.pop();
        if (!entry || typeof entry.redo !== 'function') continue;
        try {
            entry.redo();
            log('Redo: ' + entry.description, 'ok');
            undoStack.push(entry);
        } catch (err) {
            log('Redo failed: ' + (err && err.message ? err.message : err), 'err');
            break;
        }
    }
}

function describeUndoStack(limit = 5) {
    if (!undoStack.length) { log('Undo stack is empty', 'dim'); return; }
    log('Recent undo entries:', 'cyan');
    const entries = undoStack.slice(-limit).reverse();
    entries.forEach((entry, idx) => log('  #' + (idx + 1) + ' ' + entry.description, 'dim'));
}

function describeRedoStack(limit = 5) {
    if (!redoStack.length) { log('Redo stack is empty', 'dim'); return; }
    log('Pending redo entries:', 'cyan');
    const entries = redoStack.slice(-limit).reverse();
    entries.forEach((entry, idx) => log('  #' + (idx + 1) + ' ' + entry.description, 'dim'));
}

function toggleConsole() {
    consoleVisible = !consoleVisible;
    consoleDiv.classList.toggle('visible', consoleVisible);
    if (consoleVisible) input.focus();
}

// Fuzzy Matching - typo and voice tolerance
function levenshtein(a, b) {
    if (!a.length) return b.length;
    if (!b.length) return a.length;
    const matrix = [];
    for (let i = 0; i <= b.length; i++) matrix[i] = [i];
    for (let j = 0; j <= a.length; j++) matrix[0][j] = j;
    for (let i = 1; i <= b.length; i++) {
        for (let j = 1; j <= a.length; j++) {
            const cost = b[i-1] === a[j-1] ? 0 : 1;
            matrix[i][j] = Math.min(matrix[i-1][j] + 1, matrix[i][j-1] + 1, matrix[i-1][j-1] + cost);
        }
    }
    return matrix[b.length][a.length];
}

function fuzzyMatch(input, candidates, threshold = 0.6) {
    if (!input || !candidates.length) return null;
    const inputLower = input.toLowerCase();
    // Exact match first
    const exact = candidates.find(c => c.toLowerCase() === inputLower);
    if (exact) return { match: exact, confidence: 1.0, corrected: false };
    // Prefix match (e.g. 'col' matches 'color')
    const prefix = candidates.find(c => c.toLowerCase().startsWith(inputLower));
    if (prefix && inputLower.length >= 2) return { match: prefix, confidence: 0.95, corrected: true };
    // Levenshtein distance match
    let best = null;
    for (const c of candidates) {
        const dist = levenshtein(inputLower, c.toLowerCase());
        const maxLen = Math.max(input.length, c.length);
        const confidence = 1 - (dist / maxLen);
        if (confidence >= threshold && (!best || confidence > best.confidence)) {
            best = { match: c, confidence, corrected: true };
        }
    }
    return best;
}

function singularize(word) {
    if (!word || word.length < 2) return word;
    const w = word.toLowerCase();
    // Handle special plural endings
    if (w.endsWith('ies') && w.length > 3) return w.slice(0, -3) + 'y';  // berries → berry
    if (w.endsWith('xes') || w.endsWith('shes') || w.endsWith('ches')) return w.slice(0, -2);  // boxes → box
    if (w.endsWith('ses') || w.endsWith('zes')) return w.slice(0, -2);  // buses → bus
    if (w.endsWith('s') && !w.endsWith('ss')) return w.slice(0, -1);  // balls → ball
    return w;
}

const VOICE_CORRECTIONS = {
    'enter': 'Inter', 'inter': 'Inter', 'inner': 'Inter',
    'aerial': 'Arial', 'arial': 'Arial', 'area': 'Arial',
    'read': 'red', 'reed': 'red',
    'grey': 'gray',
    'blew': 'blue', 'blow': 'blue',
    'wait': 'white', 'weight': 'white', 'wet': 'white',
    'lack': 'black', 'block': 'black',
    'screen': 'green', 'grain': 'green',
    'fellow': 'yellow', 'yell': 'yellow',
    'science': 'cyan', 'sign': 'cyan',
    'orange': 'orange', 'arrange': 'orange',
    'pink': 'pink', 'ping': 'pink',
    'perple': 'purple', 'people': 'purple',
    'collar': 'color', 'colour': 'color', 'cooler': 'color',
    'fund': 'font', 'front': 'font', 'funt': 'font',
    'ex': 'x', 'eggs': 'x',
    'why': 'y', 'wie': 'y',
    'see': 'z', 'zee': 'z', 'zed': 'z',
    'with': 'width', 'whith': 'width',
    'height': 'height', 'hight': 'height',
    'visible': 'visible', 'fizzy ball': 'visible',
    'scale': 'scale', 'skill': 'scale',
    'polls': 'pulse', 'pulls': 'pulse', 'pals': 'pulse',
    'logo': 'logo', 'lego': 'logo', 'local': 'logo',
    'rush': 'rosh', 'rash': 'rosh', 'ross': 'rosh', 'roush': 'rosh',
};

function applyVoiceCorrections(text) {
    let corrected = text;
    let changes = [];
    for (const [wrong, right] of Object.entries(VOICE_CORRECTIONS)) {
        const regex = new RegExp('\\b' + wrong + '\\b', 'gi');
        if (regex.test(corrected)) {
            changes.push(wrong + ' → ' + right);
            corrected = corrected.replace(regex, right);
        }
    }
    return { text: corrected, changes };
}

function getObjectNames() {
    const names = [];
    scene.traverse(o => { if (o.name && !o.name.startsWith('_')) names.push(o.name); });
    return names;
}

const KNOWN_PROPERTIES = ['x', 'y', 'z', 'color', 'text', 'font', 'font_size', 'scale', 'visible', 'pulse', 'width', 'height', 'rotation', 'opacity', 'active'];
const KNOWN_COLORS = ['red', 'green', 'blue', 'yellow', 'cyan', 'magenta', 'white', 'black', 'orange', 'purple', 'pink', 'gray'];
const KNOWN_FONTS = ['Inter', 'Arial', 'Helvetica', 'Times', 'Georgia', 'Courier', 'Verdana', 'Roboto'];
const KNOWN_COMMANDS = ['set', 'get', 'list', 'create', 'delete', 'remove', 'reset', 'hide', 'show', 'clone', 'look', 'examine', 'inspect', 'x', 'ex', 'help', 'prompt', 'save', 'load', 'capabilities', 'camera', 'undo', 'redo', 'count', 'move', 'make', 'credits', 'clear', 'redraw', 'repeat', ':repeat', ':r', 'go', 'goto', 'scene', 'scenes', 'rooms', 'galleries', 'connect', 'disconnect', 'twin', 'sync'];
const SCENE_LIST = ['Lobby', 'Abstract', 'Sculpture', 'Creative', 'Glasgow'];

function fuzzyCorrectCommand(cmd) {
    // Apply voice corrections first
    const voiceResult = applyVoiceCorrections(cmd);
    let corrected = voiceResult.text;
    let corrections = voiceResult.changes.slice();

    // Split and correct each part
    const parts = corrected.split(/\s+/);
    if (!parts.length) return { cmd: corrected, corrections };

    // Correct command verb
    const cmdMatch = fuzzyMatch(parts[0], KNOWN_COMMANDS, 0.7);
    if (cmdMatch && cmdMatch.corrected) {
        corrections.push(parts[0] + ' → ' + cmdMatch.match);
        parts[0] = cmdMatch.match;
    }

    // For set/get commands, try to correct object and property names
    // Skip fuzzy matching for keywords: all, meta (they have special handlers)
    const skipFuzzy = ['all', 'meta'];
    if ((parts[0] === 'set' || parts[0] === 'get' || parts[0] === 'look' || parts[0] === 'examine' || parts[0] === 'x' || parts[0] === 'ex' || parts[0] === 'delete' || parts[0] === 'remove' || parts[0] === 'reset' || parts[0] === 'hide' || parts[0] === 'show' || parts[0] === 'clone') && parts.length > 1 && !skipFuzzy.includes(parts[1])) {
        const objNames = getObjectNames();
        const objMatch = fuzzyMatch(parts[1], objNames, 0.6);
        if (objMatch && objMatch.corrected) {
            corrections.push(parts[1] + ' → ' + objMatch.match);
            parts[1] = objMatch.match;
        }
    }

    // For set commands, try to correct property name
    if (parts[0] === 'set' && parts.length > 2) {
        const propIdx = parts[2] === 'to' ? 1 : 2;
        if (propIdx < parts.length) {
            const propMatch = fuzzyMatch(parts[propIdx], KNOWN_PROPERTIES, 0.7);
            if (propMatch && propMatch.corrected) {
                corrections.push(parts[propIdx] + ' → ' + propMatch.match);
                parts[propIdx] = propMatch.match;
            }
        }
    }

    // For color values, try to correct
    const toIdx = parts.indexOf('to');
    if (toIdx > 0 && toIdx < parts.length - 1) {
        const valueIdx = toIdx + 1;
        // Check if property is color-related
        const propName = parts.slice(1, toIdx).find(p => KNOWN_PROPERTIES.includes(p.toLowerCase()));
        if (propName === 'color') {
            const colorMatch = fuzzyMatch(parts[valueIdx], KNOWN_COLORS, 0.7);
            if (colorMatch && colorMatch.corrected) {
                corrections.push(parts[valueIdx] + ' → ' + colorMatch.match);
                parts[valueIdx] = colorMatch.match;
            }
        } else if (propName === 'font') {
            const fontMatch = fuzzyMatch(parts[valueIdx], KNOWN_FONTS, 0.6);
            if (fontMatch && fontMatch.corrected) {
                corrections.push(parts[valueIdx] + ' → ' + fontMatch.match);
                parts[valueIdx] = fontMatch.match;
            }
        }
    }

    return { cmd: parts.join(' '), corrections };
}

function execCommand(cmd, isUserCommand = true) {
    // Increment undo group for each user command (not internal calls)
    if (isUserCommand) undoGroup++;

    // Apply fuzzy matching to correct typos and voice errors
    const fuzzyResult = fuzzyCorrectCommand(cmd);
    const originalCmd = cmd;
    cmd = fuzzyResult.cmd;
    if (fuzzyResult.corrections.length > 0) {
        log('[corrected: ' + fuzzyResult.corrections.join(', ') + ']', 'dim');
    }
    log('> ' + cmd, 'cmd');
    cmd = cmd.replace(/colour/gi, 'color').replace(/centre/gi, 'center');

    // Resolve 'it' and 'this' to current object (stack top)
    if (currentObjectName && /\b(it|this)\b/i.test(cmd)) {
        cmd = cmd.replace(/\b(it|this)\b/gi, currentObjectName);
        log('[resolved: it/this → ' + currentObjectName + ']', 'dim');
    }

    // Track last substantive command for :repeat (skip undo/redo/help/meta)
    const nonSubstantive = /^(undo|redo|help|:repeat|\?|history)/i;
    if (isUserCommand && !nonSubstantive.test(cmd.trim())) lastUserCommand = originalCmd;

    // Deep search helpers
    const colorHexMap = {0xff0000:'red', 0x00ff00:'green', 0x0000ff:'blue', 0xffff00:'yellow', 0x00ffff:'cyan', 0xff00ff:'magenta', 0xffffff:'white', 0x000000:'black', 0x111111:'black', 0xff8800:'orange', 0x8800ff:'purple', 0xff88ff:'pink', 0xff88cc:'pink', 0x888888:'gray', 0xffd700:'gold', 0xc0c0c0:'silver'};
    const getColorName = (mesh) => {
        if (mesh.userData && mesh.userData._color) return mesh.userData._color.toLowerCase();
        if (mesh.material && mesh.material.color) {
            const hex = mesh.material.color.getHex();
            if (colorHexMap[hex]) return colorHexMap[hex];
            const r = (hex >> 16) & 0xff, g = (hex >> 8) & 0xff, b = hex & 0xff;
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
            if (Math.abs(r-g) < 30 && Math.abs(g-b) < 30) return 'gray';
        }
        return '';
    };
    const getTypeName = (mesh) => {
        if (mesh.userData && mesh.userData._type) return mesh.userData._type.toLowerCase();
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
    };

    // Bulk create expansion: create 100 balls, create 50 angry orcs
    const bulkCreateMatch = cmd.match(/^create\s+(\d+)\s+(.+)$/i);
    if (bulkCreateMatch) {
        const count = parseInt(bulkCreateMatch[1], 10);
        let words = bulkCreateMatch[2].trim().split(/\s+/);
        // Check for trailing go/confirm for auto-execution
        let autoConfirm = false;
        if (words.length > 1 && ['go', 'confirm', 'yes'].includes(words[words.length - 1].toLowerCase())) {
            autoConfirm = true;
            words = words.slice(0, -1);
        }
        if (words.length > 0 && count > 0) {
            let typeName = singularize(words[words.length - 1]);
            const modifiers = words.slice(0, -1).map(w => w.toLowerCase());
            const createCmd = 'create ' + (modifiers.length ? modifiers.join(' ') + ' ' : '') + typeName;
            if (count >= 10 && meta.confirm && !autoConfirm) {
                pendingOp = {
                    type: 'create',
                    execute: () => {
                        bulkCreateMode = true; bulkCreateCount = 0;
                        for (let i = 0; i < count; i++) execCommand(createCmd, false);
                        if (count > BULK_LOG_LIMIT) log('  ... and ' + (count - BULK_LOG_LIMIT) + ' more', 'dim');
                        bulkCreateMode = false;
                        log('Created ' + count + ' ' + typeName + '(s)', 'ok');
                        const preset = KNOWN_OBJECTS[typeName];
                        if (preset && preset.credit) log('Credit: ' + preset.credit, 'dim');
                    }
                };
                log('⚠ Create ' + count + ' ' + (modifiers.length ? modifiers.join(' ') + ' ' : '') + typeName + '(s)?', 'warn');
                log("Type 'go' or 'confirm' to execute", 'dim');
            } else {
                bulkCreateMode = true; bulkCreateCount = 0;
                for (let i = 0; i < count; i++) execCommand(createCmd, false);
                if (count > BULK_LOG_LIMIT) log('  ... and ' + (count - BULK_LOG_LIMIT) + ' more', 'dim');
                bulkCreateMode = false;
                log('Created ' + count + ' ' + typeName + '(s)', 'ok');
                const preset = KNOWN_OBJECTS[typeName];
                if (preset && preset.credit) log('Credit: ' + preset.credit, 'dim');
            }
            return;
        }
    }
    // Bulk set expansion: set 20 balls color to blue
    const bulkSetMatch = cmd.match(/^set\s+(\d+)\s+(\w+)\s+(\w+)\s+to\s+(.+)$/i);
    if (bulkSetMatch) {
        const count = parseInt(bulkSetMatch[1], 10);
        let typeName = singularize(bulkSetMatch[2]);
        const prop = bulkSetMatch[3].toLowerCase();
        const value = bulkSetMatch[4].trim();
        const typeObjs = [];
        scene.traverse(o => { if (o.name === typeName || o.name.startsWith(typeName + '-') || o.userData._type === typeName) typeObjs.push(o); });
        const targets = typeObjs.slice(0, count);
        if (targets.length === 0) { log('No ' + typeName + ' objects found', 'err'); }
        else {
            for (const obj of targets) execCommand('set ' + obj.name + ' ' + prop + ' to ' + value, false);
            log('Set ' + prop + ' on ' + targets.length + ' ' + typeName + '(s)', 'ok');
        }
        return;
    }
    // Bulk get expansion: get 5 balls
    const bulkGetMatch = cmd.match(/^get\s+(\d+)\s+(\w+)$/i);
    if (bulkGetMatch) {
        const count = parseInt(bulkGetMatch[1], 10);
        let typeName = singularize(bulkGetMatch[2]);
        const typeObjs = [];
        scene.traverse(o => { if (o.name === typeName || o.name.startsWith(typeName + '-') || o.userData._type === typeName) typeObjs.push(o); });
        const targets = typeObjs.slice(0, count);
        if (targets.length === 0) { log('No ' + typeName + ' objects found', 'err'); }
        else {
            currentSelection = targets;
            currentSelectionType = typeName;
            log('Selected ' + targets.length + ' ' + typeName + '(s)', 'ok');
        }
        return;
    }
    const parts = cmd.trim().toLowerCase().split(/\s+/);
    try {
        // Handle confirmation for pending operations
        if ((parts[0] === 'go' || parts[0] === 'confirm' || parts[0] === 'yes') && pendingOp) {
            pendingOp.execute();
            pendingOp = null;
            return;
        }
        // Cancel pending op on any other command
        if (pendingOp && parts[0] !== 'go' && parts[0] !== 'confirm' && parts[0] !== 'yes') {
            log('Cancelled pending operation', 'dim');
            pendingOp = null;
        }

        if (parts[0] === 'help' && (parts[1] === 'create' || parts[1] === 'clone')) {
            log('create - Create objects', 'cyan');
            log('');
            log('You can create any object:');
            log('  create thing           - Create empty object');
            log('  create car porsche     - Create "porsche" of type "car"');
            log('  create big red ball    - Create with modifiers');
            log('  clone ball             - Clone existing object');
            log('');
            log('Known object types (with pre-defined properties):', 'cyan');
            const names = Object.keys(KNOWN_OBJECTS).sort();
            const perLine = 6;
            for (let i = 0; i < names.length; i += perLine) {
                log('  ' + names.slice(i, i + perLine).join(', '));
            }
        }
        else if (parts[0] === 'help' && parts[1] === 'make') {
            log('make - Adjust object properties (REPL only)', 'cyan');
            log('');
            log('Usage:');
            log('  make <obj> bigger    - Scale up by 1.5x');
            log('  make <obj> smaller   - Scale down by 1.5x');
            log('  make <obj> visible   - Show the object');
            log('  make <obj> hidden    - Hide the object');
            log('  make <obj> <color>   - Change color (red, blue, etc.)');
            log('  make all <type> <modifier> - Apply to all of type');
            log('    Example: make all orcs bigger');
            log('');
            log('Note: "make" is a REPL convenience command.', 'dim');
        }
        else if (parts[0] === 'help' && parts[1] === 'undo') {
            log('undo - Undo recent changes', 'cyan');
            log('Usage:', 'dim');
            log('  undo           - Undo last change');
            log('  undo 3         - Undo last 3 changes');
            log('  undo stack     - Show undo history');
            log('  oops           - Same as undo');
        }
        else if (parts[0] === 'help' && parts[1] === 'redo') {
            log('redo - Redo undone changes', 'cyan');
            log('Usage:', 'dim');
            log('  redo           - Redo last undo');
            log('  redo 3         - Redo last 3 undos');
            log('  redo stack     - Show redo history');
        }
        else if (parts[0] === 'help' && parts[1] === 'list') {
            log('list - List all objects in scene', 'cyan');
            log('Usage:', 'dim');
            log('  list           - Show all objects');
        }
        else if (parts[0] === 'help' && parts[1] === 'count') {
            log('count - Count objects', 'cyan');
            log('Usage:', 'dim');
            log('  count          - Count all objects');
            log('  count ball     - Count objects of type "ball"');
        }
        else if (parts[0] === 'help' && (parts[1] === 'hide' || parts[1] === 'show')) {
            log('hide/show - Toggle object visibility', 'cyan');
            log('Usage:', 'dim');
            log('  hide <object>  - Make object invisible');
            log('  show <object>  - Make object visible');
        }
        else if (parts[0] === 'help' && parts[1] === 'prompt') {
            log('prompt - AI-assisted commands', 'cyan');
            log('Usage:', 'dim');
            log('  prompt create a big blue ball');
            log('  prompt move the logo to the right');
        }
        else if (parts[0] === 'help' && (parts[1] === 'save' || parts[1] === 'load')) {
            log('save/load - Persist game state', 'cyan');
            log('Usage:', 'dim');
            log('  save <slot>    - Save to slot (1-9)');
            log('  load <slot>    - Load from slot');
        }
        else if (parts[0] === 'help' && parts[1] === 'camera') {
            log('camera - Camera controls', 'cyan');
            log('Usage:', 'dim');
            log('  camera reset   - Reset camera to default position');
        }
        else if (parts[0] === 'help' && parts[1] === 'redraw') {
            log('redraw - Recreate all typed objects', 'cyan');
            log('Usage:', 'dim');
            log('  redraw         - Recreate objects with current meta settings');
            log('  (useful after changing meta.modelScale or meta.useModels)');
        }
        else if (parts[0] === 'help' && parts[1] === 'reset') {
            log('reset - Reset object to default state', 'cyan');
            log('Usage:', 'dim');
            log('  reset <object> - Reset position, scale, rotation');
        }
        else if (parts[0] === 'help' && (parts[1] === 'delete' || parts[1] === 'remove')) {
            log('delete/remove - Remove objects from scene', 'cyan');
            log('Usage:', 'dim');
            log('  delete <object>');
            log('  remove <object>');
        }
        else if (parts[0] === 'help' && parts[1] === 'credits') {
            log('credits - Show Rosh credits', 'cyan');
        }
        else if (parts[0] === 'help' && parts[1] === 'move') {
            log('move - Move object to coordinates', 'cyan');
            log('Usage:', 'dim');
            log('  move <object> to x, y, z');
            log('  move ball to 0, 5, 0');
        }
        else if (parts[0] === 'help' && (parts[1] === 'look' || parts[1] === 'examine' || parts[1] === 'inspect' || parts[1] === 'x' || parts[1] === 'ex')) {
            log('look/examine/inspect/x/ex - Inspect an object', 'cyan');
            log('Usage:', 'dim');
            log('  look <object>  - Show object properties');
            log('  examine ball   - Same as look');
            log('  x ball         - Shorthand');
            log('  ex ball        - Shorthand');
        }
        else if (parts[0] === 'help' && parts[1] === 'get') {
            log('get - Get object or property value', 'cyan');
            log('Usage:', 'dim');
            log('  get <object>           - Select object');
            log('  get <object> <prop>    - Get property value');
            log('  get all <type>         - Select all of type');
            log('  get meta scale         - Get model scale setting');
        }
        else if (parts[0] === 'help' && parts[1] === 'set') {
            log('set - Set object properties', 'cyan');
            log('Usage:', 'dim');
            log('  set <object> <prop> to <value>');
            log('  set ball color to red');
            log('  set all ball color to blue');
            log('  set meta scale to 3     - Set model scale');
            log('  set meta models off     - Disable 3D models');
            log('  set meta floor off      - Hide floor/grid');
            log('  set meta floor to green - Solid color floor');
            log('  set meta confirm off    - Disable bulk op confirmation');
        }
        else if (parts[0] === 'help' && parts[1]) {
            // Generic help <object> or help <capability>
            const obj = scene.getObjectByName(parts[1]);
            if (obj) {
                const caps = availableCapabilitiesFor(obj);
                if (caps.length) {
                    log('Capabilities for ' + parts[1] + ':', 'cyan');
                    caps.forEach(cap => log('  ' + describeCapability(cap), 'cyan'));
                } else log('No engine capabilities for ' + parts[1], 'dim');
            } else {
                const cap = CAPABILITY_INDEX[parts[1]];
                if (cap) logCapabilityHelp(cap); else log('Not found: ' + parts[1], 'err');
            }
        }
        else if (parts[0] === 'help') {
            log('Commands: list, get, set, make, look/examine, create, delete/remove', 'cyan');
            log('          reset, hide, show, clone, count, move', 'cyan');
            log('          prompt, save, load, undo, redo, camera reset', 'cyan');
            if (SCENE_LIST.length > 0) log('Scenes:   go <scene>, scenes - navigate between scenes', 'cyan');
            log('Natural: make <obj> red, make <obj> big, make <obj> visible', 'dim');
            log('Type "help create" to see available object types', 'dim');
        }
        else if (parts[0] === 'undo' && parts[1] === 'stack') {
            const count = parts[2] ? parseInt(parts[2], 10) : 5;
            describeUndoStack(Number.isFinite(count) && count > 0 ? count : 5);
        }
        else if (parts[0] === 'undo') {
            const steps = parts[1] ? parseInt(parts[1], 10) : 1;
            performUndo(Number.isFinite(steps) && steps > 0 ? steps : 1);
        }
        else if (parts[0] === 'redo' && parts[1] === 'stack') {
            const count = parts[2] ? parseInt(parts[2], 10) : 5;
            describeRedoStack(Number.isFinite(count) && count > 0 ? count : 5);
        }
        else if (parts[0] === 'redo') {
            const steps = parts[1] ? parseInt(parts[1], 10) : 1;
            performRedo(Number.isFinite(steps) && steps > 0 ? steps : 1);
        }
        else if (parts[0] === ':repeat' || parts[0] === 'repeat' || parts[0] === ':r') {
            if (lastUserCommand) {
                log('Repeating: ' + lastUserCommand, 'dim');
                execCommand(lastUserCommand);
            } else {
                log('No command to repeat', 'err');
            }
        }
        else if ((parts[0] === 'go' || parts[0] === 'goto' || parts[0] === 'scene') && parts[1]) {
            const targetScene = parts.slice(1).join(' ').toLowerCase().replace(/^(to\s+)?the\s+/, '').replace(/\s+room$/, '').replace(/\s+gallery$/, '').replace(/\s+scene$/, '');
            if (typeof SCENE_LIST !== 'undefined' && SCENE_LIST.length > 0) {
                // Try exact match first
                const exactMatch = SCENE_LIST.find(s => s.toLowerCase() === targetScene);
                if (exactMatch) {
                    pendingScene = null;
                    if (typeof transitionToScene === 'function') { transitionToScene(exactMatch); } else { currentScene = exactMatch; updateSceneVisibility(); }
                    log('Entered: ' + exactMatch, 'ok');
                } else {
                    // Try fuzzy match
                    const fuzzyMatch = SCENE_LIST.find(s => s.toLowerCase().includes(targetScene) || targetScene.includes(s.toLowerCase()));
                    if (fuzzyMatch) {
                        pendingScene = fuzzyMatch;
                        log('Did you mean: ' + fuzzyMatch + '?', 'warn');
                        log('Type go to confirm', 'dim');
                    } else {
                        log('Scene not found: ' + targetScene, 'err');
                        log('Available: ' + SCENE_LIST.join(', '), 'dim');
                    }
                }
            } else {
                log('No scenes defined in this demo', 'err');
            }
        }
        else if (parts[0] === 'go' || parts[0] === 'goto' || parts[0] === 'scene') {
            if (pendingScene) {
                const target = pendingScene;
                pendingScene = null;
                if (typeof transitionToScene === 'function') { transitionToScene(target); } else { currentScene = target; updateSceneVisibility(); }
                log('Entered: ' + target, 'ok');
            } else if (pendingAction) {
                pendingAction(); pendingAction = null;
            } else {
                log('go - Move to a scene or confirm a pending command', 'cyan');
                if (typeof SCENE_LIST !== 'undefined' && SCENE_LIST.length > 0) {
                    log('Scenes: ' + SCENE_LIST.join(', '), 'dim');
                    log('Usage: go <scene>', 'dim');
                }
            }
        }
        else if (parts[0] === 'scenes' || parts[0] === 'rooms' || parts[0] === 'galleries') {
            if (typeof SCENE_LIST !== 'undefined' && SCENE_LIST.length > 0) {
                log('Scenes: ' + SCENE_LIST.join(', '), 'cyan');
                log('Current: ' + currentScene, 'dim');
                log('Type "go <scene>" to change', 'dim');
            } else {
                log('No scenes defined in this demo', 'dim');
            }
        }
        else if (parts[0] === 'connect' || parts[0] === 'twin') {
            const worldId = parts[1] || 'default';
            if (twinSocket && twinSocket.readyState === WebSocket.OPEN) {
                log('Already connected to world: ' + twinWorldId, 'warn');
                log('Use "disconnect" first to leave current world', 'dim');
            } else {
                log('Connecting to shared world: ' + worldId + '...', 'cyan');
                try {
                    twinSocket = new WebSocket(TWIN_SERVER + worldId);
                    twinWorldId = worldId;
                    twinSocket.onopen = () => log('WebSocket connected', 'dim');
                    twinSocket.onclose = () => { log('Disconnected from shared world', 'warn'); twinSocket = null; twinUserId = null; };
                    twinSocket.onerror = (e) => log('Connection error: ' + e.message, 'err');
                    twinSocket.onmessage = (event) => {
                        const msg = JSON.parse(event.data);
                        if (msg.type === 'CONNECTED') {
                            twinUserId = msg.user_id;
                            log('Connected to "' + worldId + '" as user ' + msg.user_id, 'ok');
                            log('Users online: ' + msg.user_count, 'dim');
                            // Restore existing objects from server state
                            if (msg.state && msg.state.objects) {
                                const objCount = Object.keys(msg.state.objects).length;
                                if (objCount > 0) {
                                    log('Loading ' + objCount + ' shared object(s)...', 'dim');
                                    for (const [id, data] of Object.entries(msg.state.objects)) {
                                        twinCreateObject(id, data, false);
                                    }
                                }
                            }
                        } else if (msg.type === 'USER_JOINED') {
                            log('User ' + msg.user_id + ' joined (total: ' + msg.user_count + ')', 'cyan');
                        } else if (msg.type === 'USER_LEFT') {
                            log('User ' + msg.user_id + ' left (total: ' + msg.user_count + ')', 'dim');
                        } else if (msg.type === 'OBJECT_CREATED' && msg.by !== twinUserId) {
                            twinCreateObject(msg.id, msg.data, true);
                        } else if (msg.type === 'OBJECT_MOVED' && msg.by !== twinUserId) {
                            const obj = scene.getObjectByName(msg.id);
                            if (obj) { obj.position.set(msg.x, msg.y, msg.z); }
                        } else if (msg.type === 'OBJECT_DELETED' && msg.by !== twinUserId) {
                            const obj = scene.getObjectByName(msg.id);
                            if (obj) { scene.remove(obj); log('Object ' + msg.id + ' deleted by ' + msg.by, 'dim'); }
                        } else if (msg.type === 'CHAT') {
                            log('[' + msg.user_id + '] ' + msg.message, 'cyan');
                        } else if (msg.type === 'ERROR') {
                            log('Error: ' + msg.message, 'err');
                        } else if (msg.type === 'WORLD_RESET') {
                            // Remove all twin-created objects from scene
                            Object.keys(gameObjects).forEach(name => {
                                const obj = gameObjects[name];
                                if (obj && obj.userData && obj.userData._twin) {
                                    scene.remove(obj);
                                    delete gameObjects[name];
                                }
                            });
                            log('⚠️ World reset by ' + msg.by + ' (' + msg.deleted_count + ' objects cleared)', 'warn');
                        }
                    };
                } catch (e) { log('Failed to connect: ' + e.message, 'err'); }
            }
        }
        else if (parts[0] === 'disconnect') {
            if (twinSocket) {
                twinSocket.close();
                log('Disconnected from shared world: ' + twinWorldId, 'ok');
                twinSocket = null; twinUserId = null; twinWorldId = null;
            } else {
                log('Not connected to any shared world', 'dim');
            }
        }
        else if (parts[0] === 'sync' && parts[1]) {
            if (!twinSocket || twinSocket.readyState !== WebSocket.OPEN) {
                log('Not connected. Use "connect" first.', 'err');
            } else {
                const objName = parts.slice(1).join(' ');
                const obj = scene.getObjectByName(objName);
                if (!obj) { log('Object not found: ' + objName, 'err'); }
                else {
                    const data = { object_type: obj.userData._type || 'cube', x: obj.position.x, y: obj.position.y, z: obj.position.z, color: obj.material?.color?.getHexString() || 'ffffff', size: obj.scale?.x || 1 };
                    twinSocket.send(JSON.stringify({ type: 'CREATE', id: objName, ...data }));
                    log('Synced ' + objName + ' to shared world', 'ok');
                }
            }
        }
        else if (parts[0] === 'reset' && parts[1] === 'world') {
            if (!twinSocket || twinSocket.readyState !== WebSocket.OPEN) {
                log('Not connected. Use "connect" first.', 'err');
            } else {
                twinSocket.send(JSON.stringify({ type: 'RESET' }));
                log('Reset command sent to world: ' + twinWorldId, 'ok');
            }
        }
        else if (parts[0] === 'create' && parts[1]) {
            const desc = parts.slice(1).join(' ').toLowerCase();
            const words = desc.split(/\s+/);
            const colors = {red:0xff0000, green:0x00ff00, blue:0x0000ff, yellow:0xffff00, cyan:0x00ffff, magenta:0xff00ff, white:0xffffff, orange:0xff8800, purple:0x8800ff, pink:0xff88ff, gray:0x888888, black:0x111111};
            const shapeWords = ['ball', 'sphere', 'cube', 'box', 'cylinder', 'tube'];
            const articles = ['a', 'an', 'the'];
            const knownMods = ['big', 'large', 'small', 'tiny', ...Object.keys(colors), ...articles];
            let name = singularize(words[words.length - 1] || 'object');
            const descWords = words.slice(0, -1).filter(w => !knownMods.includes(w) && !shapeWords.includes(w));
            const objDescription = descWords.length > 0 ? descWords.join(' ') + ' ' + name : null;
            let color = null, size = 1, shape = 'box';
            let userSize = null;
            for (const [c, hex] of Object.entries(colors)) if (desc.includes(c)) color = hex;
            const userColor = color;
            if (desc.includes('big') || desc.includes('large')) { size = 2; userSize = 2; }
            if (desc.includes('small') || desc.includes('tiny')) { size = 0.5; userSize = 0.5; }
            if (desc.includes('ball') || desc.includes('sphere')) shape = 'sphere';
            else if (desc.includes('cylinder') || desc.includes('tube')) shape = 'cylinder';
            const existing = scene.getObjectByName(name);
            const hasModifiers = userColor !== null || userSize !== null;
            if (existing && !hasModifiers) {
                // Clone existing object (no modifiers specified)
                let n = 1; while (scene.getObjectByName(name + '-' + n)) n++;
                const clone = existing.clone();
                clone.name = name + '-' + n;
                clone.position.x += 2;
                scene.add(clone);
                pushUndo('create ' + clone.name, () => { scene.remove(clone); }, () => { scene.add(clone); });
                if (!bulkCreateMode || bulkCreateCount < BULK_LOG_LIMIT) log('Created ' + clone.name + ' (cloned from ' + name + ')', 'ok');
                if (!bulkCreateMode) { currentObject = clone; currentObjectName = clone.name; }
                bulkCreateCount++;
            } else {
                // Create new object - check KNOWN_OBJECTS for presets
                const preset = KNOWN_OBJECTS[name];
                if (preset) { shape = preset.shape; color = userColor !== null ? userColor : preset.color; } else { color = userColor !== null ? userColor : 0x00ff00; }
                // Check if preset has a 3D model to load (and meta.useModels is true)
                if (preset && preset.model && meta.useModels) {
                    log('Loading 3D model for ' + name + '...', 'dim');
                    gltfLoader.load(preset.model, (gltf) => {
                        const model = gltf.scene;
                        model.name = name;
                        model.userData._type = name;
                        if (objDescription) model.userData._description = objDescription;
                        if (preset.credit) model.userData._credit = preset.credit;
                        // Auto-normalize: compute bounding box and scale to fit 1 unit
                        const box = new THREE.Box3().setFromObject(model);
                        const modelSize = box.getSize(new THREE.Vector3());
                        const maxDim = Math.max(modelSize.x, modelSize.y, modelSize.z);
                        const normalizeScale = maxDim > 0 ? 1 / maxDim : 1;
                        // Apply normalize + preset scale + global meta.modelScale
                        const sx = preset.scaleX || 1, sy = preset.scaleY || 1, sz = preset.scaleZ || 1;
                        const gs = meta.modelScale || 2;
                        model.scale.set(normalizeScale * sx * size * gs, normalizeScale * sy * size * gs, normalizeScale * sz * size * gs);
                        model.position.set((Math.random()-0.5)*10, size, (Math.random()-0.5)*10);
                        scene.add(model);
                        pushUndo('create ' + model.name, () => { scene.remove(model); }, () => { scene.add(model); });
                        if (!bulkCreateMode || bulkCreateCount < BULK_LOG_LIMIT) {
                        log('Created ' + name + ' (3D model)', 'ok');
                        if (preset.credit && !bulkCreateMode) log('Credit: ' + preset.credit, 'dim');
                        }
                        if (!bulkCreateMode) { currentObject = model; currentObjectName = name; }
                        bulkCreateCount++;
                    }, undefined, (err) => {
                        console.error('GLTF load error:', err);
                        log('Failed to load ' + preset.model + ': ' + (err.message || err), 'warn');
                        // Fallback to primitive shape
                        let geom = shape === 'sphere' ? new THREE.SphereGeometry(size) : shape === 'cylinder' ? new THREE.CylinderGeometry(size*0.5, size*0.5, size) : new THREE.BoxGeometry(size, size, size);
                        const mat = new THREE.MeshStandardMaterial({color: color});
                        const mesh = new THREE.Mesh(geom, mat);
                        mesh.name = name;
                        mesh.userData._type = name;
                        mesh.userData._consoleTemplate = { type: 'mesh', shape: shape, size: size, color: color };
                        if (objDescription) mesh.userData._description = objDescription;
                        if (currentScene) mesh.userData._scene = currentScene;
                        if (preset.scaleX || preset.scaleY || preset.scaleZ) mesh.scale.set(preset.scaleX || 1, preset.scaleY || 1, preset.scaleZ || 1);
                        mesh.position.set((Math.random()-0.5)*10, size, (Math.random()-0.5)*10);
                        scene.add(mesh);
                        pushUndo('create ' + mesh.name, () => { scene.remove(mesh); }, () => { scene.add(mesh); });
                        twinBroadcastCreate(mesh.name, shape, mesh.position.x, mesh.position.y, mesh.position.z, color, size);
                        if (!bulkCreateMode || bulkCreateCount < BULK_LOG_LIMIT) log('Created ' + name + ' (fallback)', 'ok');
                        bulkCreateCount++;
                    });
                } else {
                    // No model - create primitive shape
                    let geom = shape === 'sphere' ? new THREE.SphereGeometry(size) : shape === 'cylinder' ? new THREE.CylinderGeometry(size*0.5, size*0.5, size) : new THREE.BoxGeometry(size, size, size);
                    const mat = new THREE.MeshStandardMaterial({color: color});
                    const mesh = new THREE.Mesh(geom, mat);
                    mesh.name = name;
                    if (preset && (preset.scaleX || preset.scaleY || preset.scaleZ)) mesh.scale.set(preset.scaleX || 1, preset.scaleY || 1, preset.scaleZ || 1);
                    mesh.position.set((Math.random()-0.5)*10, size, (Math.random()-0.5)*10);
                    mesh.userData._type = name;
                    mesh.userData._consoleTemplate = { type: 'mesh', shape: shape, size: size, color: color };
                    if (objDescription) mesh.userData._description = objDescription;
                    if (currentScene) mesh.userData._scene = currentScene;
                    scene.add(mesh);
                    pushUndo('create ' + mesh.name, () => { scene.remove(mesh); }, () => { scene.add(mesh); });
                    twinBroadcastCreate(mesh.name, shape, mesh.position.x, mesh.position.y, mesh.position.z, color, size);
                    if (!bulkCreateMode || bulkCreateCount < BULK_LOG_LIMIT) log('Created ' + name, 'ok');
                    if (!bulkCreateMode) { currentObject = mesh; currentObjectName = name; }
                    bulkCreateCount++;
                }
            }
        }
        else if (parts[0] === 'prompt') {
            const desc = parts.slice(1).join(' ').toLowerCase();
            // Simple pattern matching for common requests
            if (desc.includes('create')) { execCommand('create ' + desc.replace('create', ''), false); }
            else if (desc.match(/set\s+(\w+)\s+(\w+)\s+to\s+(\w+)/)) {
                const m = desc.match(/set\s+(\w+)\s+(\w+)\s+to\s+(\w+)/);
                execCommand('set ' + m[1] + ' ' + m[2] + ' to ' + m[3], false);
            }
            else if (desc.match(/move\s+(\w+)/)) {
                const obj = desc.match(/move\s+(\w+)/)[1];
                const x = desc.includes('left') ? -2 : desc.includes('right') ? 2 : 0;
                const y = desc.includes('up') ? 2 : desc.includes('down') ? -2 : 0;
                execCommand('set ' + obj + ' x to ' + x, false);
                if (y !== 0) execCommand('set ' + obj + ' y to ' + y, false);
            }
            else { log('Could not interpret: ' + desc, 'err'); log('Try: create big yellow ball, set logo color to red', 'cyan'); }
        }
        else if (parts[0] === 'list') {
            const arg = parts.slice(1).join(' ').toLowerCase();
            if (arg === 'all') {
                // List all Rosh objects grouped by scene
                const byScene = {};
                Object.keys(gameObjects).forEach(name => {
                    const o = gameObjects[name];
                    const s = (o.userData && o.userData._scene) || 'Global';
                    if (!byScene[s]) byScene[s] = [];
                    byScene[s].push(name);
                });
                Object.keys(byScene).forEach(s => {
                    log(s + ' (' + byScene[s].length + '):', 'cyan');
                    byScene[s].slice(0, 10).forEach(n => log('  ' + n));
                    if (byScene[s].length > 10) log('  ...' + (byScene[s].length - 10) + ' more', 'dim');
                });
            } else if (arg && typeof SCENE_LIST !== 'undefined') {
                // List Rosh objects for specific scene
                const match = SCENE_LIST.find(s => s.toLowerCase() === arg || s.toLowerCase().includes(arg));
                if (match) {
                    const objs = [];
                    Object.keys(gameObjects).forEach(name => {
                        const o = gameObjects[name];
                        const objScene = o.userData && o.userData._scene;
                        if (objScene === match || (!objScene && match === 'Global')) objs.push(name);
                    });
                    log('Scene: ' + match + ' (' + objs.length + ' objects)', 'cyan');
                    objs.slice(0, 15).forEach(n => log('  ' + n));
                    if (objs.length > 15) log('  ...' + (objs.length - 15) + ' more', 'dim');
                } else {
                    log('Scene not found: ' + arg, 'err');
                    log('Available: ' + SCENE_LIST.join(', '), 'dim');
                }
            } else {
                // List Rosh objects in current scene
                const objs = [];
                Object.keys(gameObjects).forEach(name => {
                    const o = gameObjects[name];
                    const objScene = o.userData && o.userData._scene;
                    if (currentScene && objScene && objScene !== currentScene) return;
                    objs.push(name);
                });
                if (currentScene) log('Scene: ' + currentScene, 'cyan');
                log(objs.length + ' objects:', 'cyan');
                objs.slice(0, 15).forEach(n => log('  ' + n));
                if (objs.length > 15) log('  ...' + (objs.length - 15) + ' more', 'dim');
            }
        }
        else if (parts[0] === 'delete' && parts[1]) {
            function findByType(typeName) {
                const matches = [];
                scene.traverse(o => {
                    if (o.name === typeName || o.name.startsWith(typeName + '-') || o.userData._type === typeName) matches.push(o);
                });
                return matches;
            }

            // Check for trailing go/confirm for auto-execution
            let autoConfirm = false;
            let delParts = [...parts];
            const lastPart = delParts[delParts.length - 1]?.toLowerCase();
            if (['go', 'confirm', 'yes'].includes(lastPart)) {
                autoConfirm = true;
                delParts = delParts.slice(0, -1);
            }

            const count = parseInt(delParts[1]);
            if (!isNaN(count) && delParts[2]) {
                const typeName = singularize(delParts[2]);
                const matches = findByType(typeName);
                if (matches.length === 0) { log('No ' + typeName + ' objects found', 'err'); }
                else {
                    const toDelete = matches.slice(0, count);
                    const actualCount = toDelete.length;
                    const doBulkDelete = () => {
                        toDelete.forEach(o => {
                            const parent = o.parent || scene;
                            const removeObj = () => { if (o.parent) o.parent.remove(o); else scene.remove(o); };
                            removeObj();
                            pushUndo('delete ' + typeName + ' ' + o.name, () => { parent.add(o); }, removeObj);
                        });
                        log('Deleted ' + actualCount + ' ' + typeName + '(s)', 'ok');
                    };
                    if (actualCount >= 10 && meta.confirm && !autoConfirm) {
                        pendingOp = {
                            type: 'delete',
                            execute: doBulkDelete
                        };
                        log('⚠ Delete ' + actualCount + ' ' + typeName + '(s)?', 'warn');
                        log("Type 'go' or 'confirm' to execute", 'dim');
                    } else {
                        doBulkDelete();
                    }
                }
            }
            else if (delParts[1] === 'all' && delParts[2]) {
                const typeName = singularize(delParts[2]);
                const matches = findByType(typeName);
                if (matches.length === 0) { log('No ' + typeName + ' objects found', 'err'); }
                else {
                    const actualCount = matches.length;
                    const doDeleteAll = () => {
                        matches.forEach(o => {
                            const parent = o.parent || scene;
                            const removeObj = () => { if (o.parent) o.parent.remove(o); else scene.remove(o); };
                            removeObj();
                            pushUndo('delete ' + typeName + ' ' + o.name, () => { parent.add(o); }, removeObj);
                        });
                        log('Deleted all ' + actualCount + ' ' + typeName + '(s)', 'ok');
                    };
                    if (actualCount >= 10 && meta.confirm && !autoConfirm) {
                        pendingOp = {
                            type: 'delete',
                            execute: doDeleteAll
                        };
                        log('⚠ Delete all ' + actualCount + ' ' + typeName + '(s)?', 'warn');
                        log("Type 'go' or 'confirm' to execute", 'dim');
                    } else {
                        doDeleteAll();
                    }
                }
            }
            else {
                let objName = delParts[1];
                let obj = scene.getObjectByName(objName);
                // Try singularizing if not found
                if (!obj) {
                    const singular = singularize(objName);
                    if (singular !== objName) { obj = scene.getObjectByName(singular); if (obj) objName = singular; }
                }
                if (obj) {
                    const parent = obj.parent;
                    const removeObj = () => { if (obj.parent) obj.parent.remove(obj); else scene.remove(obj); };
                    removeObj();
                    pushUndo("delete '" + objName + "'", () => { (parent || scene).add(obj); }, removeObj);
                    log("Deleted '" + objName + "'", 'ok');
                }
                else log('Not found: ' + parts[1], 'err');
            }
        }
        else if (parts[0] === 'remove' && parts[1]) {
            const obj = scene.getObjectByName(parts[1]);
            if (obj) {
                const parent = obj.parent;
                const removeObj = () => { if (obj.parent) obj.parent.remove(obj); else scene.remove(obj); };
                removeObj();
                pushUndo("remove '" + parts[1] + "'", () => { (parent || scene).add(obj); }, removeObj);
                log("Removed '" + parts[1] + "'", 'ok');
            }
            else log('Not found: ' + parts[1], 'err');
        }
        else if (parts[0] === 'reset' && (parts[1] === 'scene' || parts[1] === 'all')) {
            log('Clearing saved data and reloading...', 'warn');
            // Clear all rosh saves from localStorage
            Object.keys(localStorage).filter(k => k.startsWith('rosh_save_')).forEach(k => localStorage.removeItem(k));
            setTimeout(() => location.reload(), 500);
        }
        else if (parts[0] === 'reset' && parts[1]) {
            const obj = scene.getObjectByName(parts[1]);
            if (obj) {
                const prevUserData = JSON.parse(JSON.stringify(obj.userData || {}));
                obj.userData = {};
                pushUndo("reset '" + parts[1] + "'", () => { obj.userData = prevUserData; }, () => { obj.userData = {}; });
                log("Reset '" + parts[1] + "' to defaults", 'ok');
            }
            else log('Not found: ' + parts[1], 'err');
        }
        else if (parts[0] === 'hide' && parts[1]) {
            if (parts[1] === 'all') {
                const typeName = parts[2] ? singularize(parts[2]) : null;
                let count = 0;
                const undoStates = [];
                scene.traverse(o => {
                    if (!o.name || o.name.startsWith('_') || o.type === 'AmbientLight' || o.type === 'DirectionalLight') return;
                    if (typeName) {
                        const oType = getTypeName(o);
                        const oColor = getColorName(o);
                        if (oType !== typeName && oColor !== typeName && !o.name.startsWith(typeName)) return;
                    }
                    if (o.visible !== false) { undoStates.push({obj: o, was: o.visible}); o.visible = false; count++; }
                });
                if (count > 0) {
                    pushUndo('hide all' + (typeName ? ' ' + typeName : ''), () => { undoStates.forEach(s => s.obj.visible = s.was); }, () => { undoStates.forEach(s => s.obj.visible = false); });
                    log('Hid ' + count + ' object' + (count > 1 ? 's' : '') + (typeName ? ' (' + typeName + ')' : ''), 'ok');
                } else log('No ' + (typeName || 'visible') + ' objects to hide', 'dim');
            } else {
                const obj = scene.getObjectByName(parts[1]);
                if (obj) {
                    const wasVisible = obj.visible;
                    obj.visible = false;
                    pushUndo("hide '" + parts[1] + "'", () => { obj.visible = wasVisible; }, () => { obj.visible = false; });
                    log("Hid '" + parts[1] + "'", 'ok');
                }
                else log('Not found: ' + parts[1], 'err');
            }
        }
        else if (parts[0] === 'show' && parts[1]) {
            if (parts[1] === 'all') {
                const typeName = parts[2] ? singularize(parts[2]) : null;
                let count = 0;
                const undoStates = [];
                scene.traverse(o => {
                    if (!o.name || o.name.startsWith('_') || o.type === 'AmbientLight' || o.type === 'DirectionalLight') return;
                    if (typeName) {
                        const oType = getTypeName(o);
                        const oColor = getColorName(o);
                        if (oType !== typeName && oColor !== typeName && !o.name.startsWith(typeName)) return;
                    }
                    if (o.visible !== true) { undoStates.push({obj: o, was: o.visible}); o.visible = true; count++; }
                });
                if (count > 0) {
                    pushUndo('show all' + (typeName ? ' ' + typeName : ''), () => { undoStates.forEach(s => s.obj.visible = s.was); }, () => { undoStates.forEach(s => s.obj.visible = true); });
                    log('Showed ' + count + ' object' + (count > 1 ? 's' : '') + (typeName ? ' (' + typeName + ')' : ''), 'ok');
                } else log('No ' + (typeName || 'hidden') + ' objects to show', 'dim');
            } else {
                const obj = scene.getObjectByName(parts[1]);
                if (obj) {
                    const wasVisible = obj.visible;
                    obj.visible = true;
                    pushUndo("show '" + parts[1] + "'", () => { obj.visible = wasVisible; }, () => { obj.visible = true; });
                    log("Showed '" + parts[1] + "'", 'ok');
                }
                else log('Not found: ' + parts[1], 'err');
            }
        }
        else if (parts[0] === 'count' && parts[1]) {
            let typeName = singularize(parts[1]);
            let count = 0;
            const matches = [];
            scene.traverse(o => {
                if (!o.name || o.name.startsWith('_')) return;
                const oType = (o.userData && o.userData._type) || o.name.replace(/-\d+$/, '');
                if (oType === typeName || o.name === typeName) { count++; matches.push(o.name); }
            });
            if (count === 0) log('No ' + typeName + ' objects found', 'dim');
            else {
                log(count + ' ' + typeName + (count > 1 ? ' objects:' : ' object:'), 'cyan');
                // Show first 10, then '...N more'
                matches.slice(0, 10).forEach(n => log('  ' + n));
                if (count > 10) log('  ...' + (count - 10) + ' more', 'dim');
            }
        }
        else if (parts[0] === 'count') {
            let count = 0;
            scene.traverse(o => { if (o.name && !o.name.startsWith('_')) count++; });
            log(count + ' objects in scene', 'cyan');
        }
        else if (parts[0] === 'move' && parts[1]) {
            const obj = scene.getObjectByName(parts[1]);
            if (!obj) { log('Not found: ' + parts[1], 'err'); }
            else {
                let rest = parts.slice(2).join(' ').replace(/^to\s+/, '').replace(/^the\s+/, '');
                const namedPositions = { 'center': [0, obj.position.y, 0], 'origin': [0, 0, 0], 'ground': [obj.position.x, 0, obj.position.z] };
                let coords;
                if (namedPositions[rest.toLowerCase()]) {
                    coords = namedPositions[rest.toLowerCase()];
                    log('[resolved: ' + rest + ' → ' + coords.join(', ') + ']', 'dim');
                } else {
                    coords = rest.split(/[,\s]+/).map(Number).filter(n => !isNaN(n));
                }
                if (coords.length === 0) { log('Usage: move <obj> to x,y,z or center/origin/ground', 'err'); }
                else {
                    const oldPos = obj.position.clone();
                    const newX = coords[0] !== undefined ? coords[0] : obj.position.x;
                    const newY = coords[1] !== undefined ? coords[1] : obj.position.y;
                    const newZ = coords[2] !== undefined ? coords[2] : obj.position.z;
                    obj.position.set(newX, newY, newZ);
                    pushUndo('move ' + parts[1], () => { obj.position.copy(oldPos); }, () => { obj.position.set(newX, newY, newZ); });
                    log('Moved ' + parts[1] + ' to (' + newX.toFixed(1) + ', ' + newY.toFixed(1) + ', ' + newZ.toFixed(1) + ')', 'ok');
                }
            }
        }
        else if (parts[0] === 'make' && !isNaN(parseInt(parts[1])) && parts[2]) {
            const count = parseInt(parts[1]);
            let autoConfirm = false;
            let words = parts.slice(2);
            if (['go', 'confirm', 'yes'].includes(words[words.length - 1]?.toLowerCase())) {
                autoConfirm = true;
                words = words.slice(0, -1);
            }
            if (words.length === 0) { log('Usage: make <count> [adjectives] <type> [modifier]', 'err'); }
            else {
                const actionModifiers = ['big', 'bigger', 'large', 'larger', 'small', 'smaller', 'tiny', 'visible', 'shown', 'invisible', 'hidden'];
                const knownColors = {red:1, green:1, blue:1, yellow:1, cyan:1, magenta:1, white:1, black:1, orange:1, purple:1, pink:1, gray:1};
                const lastWord = words[words.length - 1].toLowerCase();
                const isActionModifier = actionModifiers.includes(lastWord);
                const isColorModifier = knownColors[lastWord] && words.length > 1;

                if (isActionModifier || isColorModifier) {
                    // Action modifier: make N [adj] type bigger
                    const modifier = lastWord;
                    const typeName = singularize(words.length > 1 ? words[words.length - 2] : words[0]);
                    if (!modifier) { log('Usage: make <count> <type> <modifier>', 'err'); }
                    else {
                        const knownColors = {red:0xff0000, green:0x00ff00, blue:0x0000ff, yellow:0xffff00, cyan:0x00ffff, magenta:0xff00ff, white:0xffffff, black:0x111111, orange:0xff8800, purple:0x8800ff, pink:0xff88ff, gray:0x888888};
                        const allTargets = [];
                        scene.traverse(o => { if (o.name === typeName || o.name.startsWith(typeName + '-') || o.userData._type === typeName) allTargets.push(o); });
                        if (allTargets.length === 0) { log('No ' + typeName + 's found', 'err'); }
                        else {
                            const targets = allTargets.slice(0, count);
                            function applyModifier() {
                                let modified = 0;
                                const colorMatch = modifier.match(/^colou?r\s+(\w+)$/i);
                                const effectiveModifier = colorMatch ? colorMatch[1].toLowerCase() : modifier;
                                let failures = 0;
                                for (const obj of targets) {
                                    if (['big', 'bigger', 'large', 'larger'].includes(effectiveModifier)) { obj.scale.multiplyScalar(1.5); modified++; }
                                    else if (['small', 'smaller', 'tiny'].includes(effectiveModifier)) { obj.scale.multiplyScalar(1/1.5); modified++; }
                                    else if (effectiveModifier === 'visible' || effectiveModifier === 'shown') { obj.visible = true; modified++; }
                                    else if (effectiveModifier === 'invisible' || effectiveModifier === 'hidden') { obj.visible = false; modified++; }
                                    else if (knownColors[effectiveModifier]) {
                                        const result = applyCapabilityBridge(obj, 'color', [effectiveModifier]);
                                        if (result.ok) modified++; else failures++;
                                    }
                                }
                                if (modified > 0) log('Modified ' + modified + ' ' + typeName + '(s): ' + modifier, 'ok');
                                else if (failures > 0) log('Color not supported for ' + typeName + ' (3D models need direct material access)', 'err');
                                else log('Unknown modifier: ' + modifier, 'err');
                            }
                            if (targets.length >= 10 && meta.confirm && !autoConfirm) {
                                pendingOp = { type: 'make', execute: applyModifier };
                                log('⚠ Modify ' + targets.length + ' ' + typeName + '(s)?', 'warn');
                                log("Type 'go' or 'confirm' to execute", 'dim');
                            } else applyModifier();
                        }
                    }
                } else {
                    // No action modifier - treat as 'create N [adjectives] type'
                    const createCmd = 'create ' + count + ' ' + words.join(' ');
                    log('→ ' + createCmd, 'dim');
                    execCommand(createCmd, false);
                }
            }
        }
        else if (parts[0] === 'make' && parts[1] === 'all' && parts[2] && parts[3]) {
            // Check for trailing go/confirm for auto-execution
            let autoConfirm = false;
            let modParts = parts.slice(3);
            if (['go', 'confirm', 'yes'].includes(modParts[modParts.length - 1]?.toLowerCase())) {
                autoConfirm = true;
                modParts = modParts.slice(0, -1);
            }
            const typeName = singularize(parts[2]);
            const modifier = modParts.join(' ');
            if (!modifier) { log('Usage: make all <type> <modifier>', 'err'); }
            else {
                const knownColors = {red:0xff0000, green:0x00ff00, blue:0x0000ff, yellow:0xffff00, cyan:0x00ffff, magenta:0xff00ff, white:0xffffff, black:0x111111, orange:0xff8800, purple:0x8800ff, pink:0xff88ff, gray:0x888888};
                const targets = [];
                scene.traverse(o => { if (o.name === typeName || o.name.startsWith(typeName + '-') || o.userData._type === typeName) targets.push(o); });
                if (targets.length === 0) { log('No ' + typeName + 's found', 'err'); }
                else {
                    function applyModifier() {
                        let count = 0;
                        let failures = 0;
                        // Handle 'color <name>' or 'colour <name>' patterns
                        const colorMatch = modifier.match(/^colou?r\s+(\w+)$/i);
                        const effectiveModifier = colorMatch ? colorMatch[1].toLowerCase() : modifier;
                        for (const obj of targets) {
                            if (['big', 'bigger', 'large', 'larger'].includes(effectiveModifier)) { obj.scale.multiplyScalar(1.5); count++; }
                            else if (['small', 'smaller', 'tiny'].includes(effectiveModifier)) { obj.scale.multiplyScalar(1/1.5); count++; }
                            else if (effectiveModifier === 'visible' || effectiveModifier === 'shown') { obj.visible = true; count++; }
                            else if (effectiveModifier === 'invisible' || effectiveModifier === 'hidden') { obj.visible = false; count++; }
                            else if (knownColors[effectiveModifier]) {
                                const result = applyCapabilityBridge(obj, 'color', [effectiveModifier]);
                                if (result.ok) count++; else failures++;
                            }
                        }
                        if (count > 0) log('Modified ' + count + ' ' + typeName + '(s): ' + modifier, 'ok');
                        else if (failures > 0) log('Color not supported for ' + typeName + ' (3D models need direct material access)', 'err');
                        else log('Unknown modifier: ' + modifier, 'err');
                    }
                    if (targets.length >= 10 && meta.confirm && !autoConfirm) {
                        pendingOp = { type: 'make', execute: applyModifier };
                        log('⚠ Modify ' + targets.length + ' ' + typeName + '(s)?', 'warn');
                        log("Type 'go' or 'confirm' to execute", 'dim');
                    } else applyModifier();
                }
            }
        }
        else if (parts[0] === 'make' && parts[1] && parts[2]) {
            let objName = parts[1];
            const rest = parts.slice(2);
            const knownColors = {red:0xff0000, green:0x00ff00, blue:0x0000ff, yellow:0xffff00, cyan:0x00ffff, magenta:0xff00ff, white:0xffffff, black:0x111111, orange:0xff8800, purple:0x8800ff, pink:0xff88ff, gray:0x888888};
            let obj = scene.getObjectByName(objName);
            // Try singularizing if not found
            if (!obj) {
                const singular = singularize(objName);
                if (singular !== objName) { obj = scene.getObjectByName(singular); if (obj) objName = singular; }
            }
            if (!obj) {
                // Check if user means 'create' - articles, colors, sizes suggest creation
                const articles = ['a', 'an', 'the'];
                const colors = ['red', 'green', 'blue', 'yellow', 'cyan', 'magenta', 'white', 'black', 'orange', 'purple', 'pink', 'gray'];
                const sizes = ['big', 'small', 'large', 'tiny', 'huge'];
                const firstWord = parts[1].toLowerCase();
                if (articles.includes(firstWord) || colors.includes(firstWord) || sizes.includes(firstWord)) {
                    const createParts = parts.slice(1).filter(w => !articles.includes(w.toLowerCase()));
                    const createCmd = 'create ' + createParts.join(' ');
                    log('→ ' + createCmd, 'dim');
                    execCommand(createCmd, false);
                }
                else { log('Not found: ' + parts[1] + '. Did you mean: create ' + parts.slice(1).join(' ') + '?', 'err'); }
            }
            else {
                if (rest[0] === 'visible' || rest[0] === 'shown') {
                    const was = obj.visible;
                    obj.visible = true;
                    pushUndo('make ' + objName + ' visible', () => { obj.visible = was; }, () => { obj.visible = true; });
                    log('Showed ' + objName, 'ok');
                }
                else if (rest[0] === 'invisible' || rest[0] === 'hidden') {
                    const was = obj.visible;
                    obj.visible = false;
                    pushUndo('make ' + objName + ' hidden', () => { obj.visible = was; }, () => { obj.visible = false; });
                    log('Hid ' + objName, 'ok');
                }
                else if (knownColors[rest[0]]) {
                    log('→ set ' + objName + ' color to ' + rest[0], 'dim');
                    const result = applyCapabilityBridge(obj, 'color', [rest[0]]);
                    if (result.ok) log(result.message, 'ok'); else log(result.message, 'err');
                }
                else if (['big', 'bigger', 'large', 'larger'].includes(rest[0])) {
                    const oldScale = obj.scale.clone();
                    const factor = 1.5;
                    obj.scale.multiplyScalar(factor);
                    const newScale = obj.scale.x.toFixed(2);
                    pushUndo('make ' + objName + ' bigger', () => { obj.scale.copy(oldScale); }, () => { obj.scale.copy(oldScale).multiplyScalar(factor); });
                    log(objName + '.scale = ' + newScale, 'ok');
                }
                else if (['small', 'smaller', 'tiny'].includes(rest[0])) {
                    const oldScale = obj.scale.clone();
                    const factor = 1/1.5;
                    obj.scale.multiplyScalar(factor);
                    const newScale = obj.scale.x.toFixed(2);
                    pushUndo('make ' + objName + ' smaller', () => { obj.scale.copy(oldScale); }, () => { obj.scale.copy(oldScale).multiplyScalar(factor); });
                    log(objName + '.scale = ' + newScale, 'ok');
                }
                else if (rest.length >= 2) {
                    const prop = rest[0];
                    const valueTokens = rest.slice(1);
                    log('→ set ' + objName + ' ' + prop + ' to ' + valueTokens.join(' '), 'dim');
                    let result = handleCoreSet(obj, prop, valueTokens);
                    if (!result.ok) result = applyCapabilityBridge(obj, prop, valueTokens);
                    if (result.ok) log(result.message, 'ok'); else log(result.message, 'err');
                }
                else { log('Usage: make <obj> <color|visible|big|prop value>', 'err'); }
            }
        }
        else if (parts[0] === 'make' && parts[1] && !parts[2]) {
            // 'make ball' or 'make yellow' -> create it
            const createCmd = 'create ' + parts[1];
            log('→ ' + createCmd, 'dim');
            execCommand(createCmd, false);
        }
        else if (parts[0] === 'clone' && parts[1]) {
            let src = scene.getObjectByName(parts[1]);
            if (!src) {
                // Smart default: create if doesn't exist (just create, don't clone)
                const preset = KNOWN_OBJECTS[parts[1]] || { shape: 'box', color: 0x00ff00 };
                // Check if preset has a 3D model to load (and meta.useModels is true)
                if (preset.model && meta.useModels) {
                    log('Loading 3D model for ' + parts[1] + '...', 'dim');
                    gltfLoader.load(preset.model, (gltf) => {
                        const model = gltf.scene;
                        model.name = parts[1];
                        model.userData._type = parts[1];
                        if (preset.credit) model.userData._credit = preset.credit;
                        // Auto-normalize: compute bounding box and scale to fit 1 unit
                        const box = new THREE.Box3().setFromObject(model);
                        const modelSize = box.getSize(new THREE.Vector3());
                        const maxDim = Math.max(modelSize.x, modelSize.y, modelSize.z);
                        const normalizeScale = maxDim > 0 ? 1 / maxDim : 1;
                        // Apply normalize + preset scale + global meta.modelScale
                        const sx = preset.scaleX || 1, sy = preset.scaleY || 1, sz = preset.scaleZ || 1;
                        const gs = meta.modelScale || 2;
                        model.scale.set(normalizeScale * sx * gs, normalizeScale * sy * gs, normalizeScale * sz * gs);
                        model.position.set((Math.random()-0.5)*10, 1, (Math.random()-0.5)*10);
                        scene.add(model);
                        pushUndo('create ' + model.name, () => { scene.remove(model); }, () => { scene.add(model); });
                        log('Created ' + parts[1] + ' (3D model)', 'ok');
                        if (preset.credit) log('Credit: ' + preset.credit, 'dim');
                    }, undefined, (err) => {
                        console.error('GLTF load error:', err);
                        log('Failed to load ' + preset.model + ': ' + (err.message || err), 'warn');
                        let geom = preset.shape === 'sphere' ? new THREE.SphereGeometry(1) : preset.shape === 'cylinder' ? new THREE.CylinderGeometry(0.5, 0.5, 1) : new THREE.BoxGeometry(1, 1, 1);
                        const mat = new THREE.MeshStandardMaterial({color: preset.color});
                        const mesh = new THREE.Mesh(geom, mat);
                        mesh.name = parts[1];
                        mesh.userData._type = parts[1];
                        if (preset.scaleX || preset.scaleY || preset.scaleZ) mesh.scale.set(preset.scaleX || 1, preset.scaleY || 1, preset.scaleZ || 1);
                        mesh.position.set((Math.random()-0.5)*10, 1, (Math.random()-0.5)*10);
                        scene.add(mesh);
                        pushUndo('create ' + mesh.name, () => { scene.remove(mesh); }, () => { scene.add(mesh); });
                        log('Created ' + parts[1] + ' (fallback)', 'ok');
                    });
                    return;
                }
                // No model - create primitive shape
                let geom;
                if (preset.shape === 'sphere') geom = new THREE.SphereGeometry(1);
                else if (preset.shape === 'cylinder') geom = new THREE.CylinderGeometry(0.5, 0.5, 1);
                else geom = new THREE.BoxGeometry(1, 1, 1);
                const mat = new THREE.MeshStandardMaterial({color: preset.color});
                src = new THREE.Mesh(geom, mat);
                src.name = parts[1];
                if (preset.scaleX || preset.scaleY || preset.scaleZ) src.scale.set(preset.scaleX || 1, preset.scaleY || 1, preset.scaleZ || 1);
                src.position.set((Math.random()-0.5)*10, 1, (Math.random()-0.5)*10);
                src.userData._type = parts[1];
                scene.add(src);
                pushUndo('create ' + parts[1], () => { scene.remove(src); }, () => { scene.add(src); });
                log('Created ' + parts[1], 'ok');
                return;
            }
            let targetName = parts[3] && (parts[2] === 'as' || parts[2] === 'to') ? parts[3] : null;
            if (!targetName) { let n = 1; while (scene.getObjectByName(parts[1] + '-' + n)) n++; targetName = parts[1] + '-' + n; }
            const clone = src.clone();
            clone.name = targetName;
            clone.userData._type = parts[1];
            clone.position.x += 2;
            scene.add(clone);
            const cloneParent = scene;
            pushUndo("clone '" + parts[1] + "'", () => { cloneParent.remove(clone); }, () => { cloneParent.add(clone); });
            log("Cloned '" + parts[1] + "' as '" + targetName + "'", 'ok');
        }
        else if (parts[0] === 'get' && parts[1] === 'meta' && !parts[2]) {
            log('meta settings:', 'cyan');
            log('  modelScale = ' + meta.modelScale);
            log('  useModels = ' + meta.useModels);
            log('  floor = ' + meta.floor);
            log('  floorColor = ' + (meta.floorColor !== null ? '#' + meta.floorColor.toString(16).padStart(6, '0') : 'none'));
            log('  confirm = ' + meta.confirm);
        }
        else if (parts[0] === 'get' && parts[1] === 'meta' && parts[2] === 'scale') {
            log('meta.modelScale = ' + meta.modelScale, 'cyan');
        }
        else if (parts[0] === 'get' && parts[1] === 'meta' && parts[2] === 'floor') {
            log('meta.floor = ' + meta.floor, 'cyan');
            log('meta.floorColor = ' + (meta.floorColor !== null ? '#' + meta.floorColor.toString(16).padStart(6, '0') : 'none'), 'cyan');
        }
        else if (parts[0] === 'get' && parts[1] === 'all' && parts[2]) {
            let typeName = parts[2];
            let corrected = false;
            function findMatches(name) {
                const m = [];
                scene.traverse(o => {
                    if (!o.name || o.name.startsWith('_')) return;
                    if (o.userData._type === name || o.name === name || o.name.startsWith(name + '-')) m.push(o);
                });
                return m;
            }
            let matches = findMatches(typeName);
            if (matches.length === 0) {
                const singular = typeName.endsWith('ies') ? typeName.slice(0,-3)+'y' : typeName.endsWith('es') ? typeName.slice(0,-2) : typeName.endsWith('s') ? typeName.slice(0,-1) : null;
                if (singular) { matches = findMatches(singular); if (matches.length > 0) { corrected = true; typeName = singular; } }
            }
            if (matches.length === 0) { log('No ' + parts[2] + ' objects found', 'warn'); }
            else {
                if (corrected) log('[corrected: ' + parts[2] + ' → ' + typeName + ']', 'dim');
                currentSelection = matches;
                currentSelectionType = typeName;
                log('Selected ' + matches.length + ' ' + typeName + '(s):', 'ok');
                // Show first 10, then '...N more'
                matches.slice(0, 10).forEach(o => log('  ' + o.name));
                if (matches.length > 10) log('  ...' + (matches.length - 10) + ' more', 'dim');
                log('Use "set all <prop> to <value>" to modify all', 'dim');
            }
        }
        else if (parts[0] === 'get' && parts[1]) {
            const queryParts = parts.slice(1);
            const queryJoined = queryParts.join('-');
            let obj = scene.getObjectByName(queryParts[0]) || scene.getObjectByName(queryJoined);
            if (obj) { currentObject = obj; currentObjectName = obj.name; log('<object: ' + obj.name + '>', 'ok'); }
            else {
                // Deep search by attributes (color, shape type)
                const knownColors = {red:1, green:1, blue:1, yellow:1, cyan:1, magenta:1, white:1, black:1, orange:1, purple:1, pink:1, gray:1, grey:1, gold:1, silver:1};
                const shapeSynonyms = {box:'cube', cube:'cube', ball:'sphere', sphere:'sphere', cylinder:'cylinder', tube:'cylinder', cone:'cone', torus:'torus', ring:'torus'};
                let targetColor = null, targetShape = null;
                for (const w of queryParts) {
                    const wl = w.toLowerCase();
                    if (knownColors[wl]) targetColor = wl;
                    if (shapeSynonyms[wl]) targetShape = shapeSynonyms[wl];
                }
                if (!targetColor && !targetShape) {
                    log('Not found: ' + queryParts[0], 'err');
                } else {
                    const matches = [];
                    scene.traverse(child => {
                        if (child.isMesh && child.name && !child.name.startsWith('_')) {
                            const cType = getTypeName(child);
                            const cColor = getColorName(child);
                            const typeMatch = !targetShape || cType.includes(targetShape);
                            const colorMatch = !targetColor || cColor === targetColor || (targetColor === 'grey' && cColor === 'gray');
                            if (typeMatch && colorMatch) matches.push(child.name);
                        }
                    });
                    if (matches.length === 0) {
                        log('Not found: no ' + (targetColor || '') + ' ' + (targetShape || 'objects'), 'err');
                    } else if (matches.length === 1) {
                        const found = scene.getObjectByName(matches[0]);
                        currentObject = found; currentObjectName = matches[0];
                        log('[deep search] <object: ' + matches[0] + '>', 'ok');
                    } else {
                        log('[deep search] Found ' + matches.length + ': ' + matches.join(', '), 'ok');
                        const found = scene.getObjectByName(matches[0]);
                        currentObject = found; currentObjectName = matches[0];
                        log('Selected: ' + matches[0], 'ok');
                    }
                }
            }
        }
        else if (parts[0] === 'set' && parts[1] === 'meta' && parts[2] === 'scale') {
            const filtered = parts.filter(x => x !== 'to');
            const val = parseFloat(filtered[3]);
            if (!isNaN(val) && val > 0) {
                const prev = meta.modelScale;
                meta.modelScale = val;
                pushUndo('set meta scale', () => { meta.modelScale = prev; }, () => { meta.modelScale = val; });
                log('Model scale set to ' + val + ' (affects new models)', 'ok');
            } else log('Usage: set meta scale to <number>', 'err');
        }
        else if (parts[0] === 'set' && parts[1] === 'meta' && parts[2] === 'models') {
            const filtered = parts.filter(x => x !== 'to');
            const val = filtered[3];
            if (val === 'on' || val === 'true' || val === '1') {
                meta.useModels = true;
                log('3D models enabled (affects new objects)', 'ok');
            } else if (val === 'off' || val === 'false' || val === '0') {
                meta.useModels = false;
                log('3D models disabled - using primitive shapes (affects new objects)', 'ok');
            } else log('Usage: set meta models to on/off', 'err');
        }
        else if (parts[0] === 'set' && parts[1] === 'meta' && parts[2] === 'floor') {
            const filtered = parts.filter(x => x !== 'to');
            const val = filtered[3];
            const grid = scene.getObjectByName('_grid');
            const floor = scene.getObjectByName('_floor');
            const prevFloor = meta.floor;
            const prevFloorColor = meta.floorColor;
            const prevGridVis = grid ? grid.visible : false;
            const prevFloorVis = floor ? floor.visible : false;
            const prevFloorHex = floor && floor.material ? floor.material.color.getHex() : 0x333333;
            if (val === 'on' || val === 'true' || val === '1') {
                meta.floor = true;
                if (grid) grid.visible = true;
                pushUndo('set meta floor on', () => { meta.floor = prevFloor; if (grid) grid.visible = prevGridVis; if (floor) floor.visible = prevFloorVis; }, () => { meta.floor = true; if (grid) grid.visible = true; });
                log('Floor grid visible', 'ok');
            } else if (val === 'off' || val === 'false' || val === '0') {
                meta.floor = false;
                if (grid) grid.visible = false;
                if (floor) floor.visible = false;
                pushUndo('set meta floor off', () => { meta.floor = prevFloor; if (grid) grid.visible = prevGridVis; if (floor) floor.visible = prevFloorVis; }, () => { meta.floor = false; if (grid) grid.visible = false; if (floor) floor.visible = false; });
                log('Floor hidden', 'ok');
            } else {
                // Treat as color: set meta floor to red/blue/#ff0000
                const knownColors = {red:0xff0000, green:0x00ff00, blue:0x0000ff, yellow:0xffff00, cyan:0x00ffff, magenta:0xff00ff, white:0xffffff, black:0x111111, orange:0xff8800, purple:0x8800ff, pink:0xff88ff, gray:0x888888, brown:0x8b4513};
                let color = knownColors[val];
                if (!color && val && val.startsWith('#')) color = parseInt(val.slice(1), 16);
                if (color !== undefined) {
                    meta.floorColor = color;
                    meta.floor = true;
                    if (grid) grid.visible = false;
                    if (floor) { floor.material.color.setHex(color); floor.visible = true; }
                    pushUndo('set meta floor ' + val, () => { meta.floor = prevFloor; meta.floorColor = prevFloorColor; if (grid) grid.visible = prevGridVis; if (floor) { floor.material.color.setHex(prevFloorHex); floor.visible = prevFloorVis; } }, () => { meta.floor = true; meta.floorColor = color; if (grid) grid.visible = false; if (floor) { floor.material.color.setHex(color); floor.visible = true; } });
                    log('Floor color: #' + color.toString(16).padStart(6, '0'), 'ok');
                } else log('Usage: set meta floor to on/off/<color>', 'err');
            }
        }
        else if (parts[0] === 'set' && parts[1] === 'meta' && parts[2] === 'confirm') {
            const filtered = parts.filter(x => x !== 'to');
            const val = filtered[3];
            if (val === 'on' || val === 'true' || val === '1') {
                meta.confirm = true;
                log('Confirmation enabled for bulk operations (>= 10)', 'ok');
            } else if (val === 'off' || val === 'false' || val === '0') {
                meta.confirm = false;
                log('Confirmation disabled - bulk ops execute immediately', 'ok');
            } else log('Usage: set meta confirm to on/off', 'err');
        }
        else if (parts[0] === 'set' && parts[1] === 'all' && parts.length >= 4) {
            if (currentSelection.length === 0) { log('No objects selected. Use "get all <type>" first', 'warn'); return; }
            const filtered = parts.slice(2).filter(x => x !== 'to');
            const prop = filtered[0];
            const valueTokens = filtered.slice(1);
            if (!prop || !valueTokens.length) { log('Usage: set all <property> to <value>', 'err'); return; }
            let count = 0;
            const undoOps = [];
            for (const obj of currentSelection) {
                let result = handleCoreSet(obj, prop, valueTokens);
                if (!result.ok) result = applyCapabilityBridge(obj, prop, valueTokens);
                if (result.ok) { undoOps.push({ undo: result.undo, redo: result.redo }); count++; }
            }
            if (count > 0) {
                pushUndo('set all ' + currentSelectionType + ' ' + prop, () => undoOps.forEach(op => op.undo()), () => undoOps.forEach(op => op.redo()));
                log('Set ' + prop + ' on ' + count + ' ' + currentSelectionType + '(s)', 'ok');
            } else log('No objects modified', 'warn');
        }
        else if (parts[0] === 'set' && parts.length >= 3) {
            const filtered = parts.filter(x => x !== 'to');
            let obj = null;
            let prop = null;
            let valueTokens = [];
            if (filtered.length >= 4) {
                const candidate = scene.getObjectByName(filtered[1]);
                if (candidate) {
                    obj = candidate;
                    prop = filtered[2];
                    valueTokens = filtered.slice(3);
                } else if (filtered.length >= 5) {
                    // Deep search for 'color shape' pattern
                    const knownColors = {red:1, green:1, blue:1, yellow:1, cyan:1, magenta:1, white:1, black:1, orange:1, purple:1, pink:1, gray:1, grey:1};
                    const shapeSynonyms = {box:'cube', cube:'cube', ball:'sphere', sphere:'sphere', cylinder:'cylinder', tube:'cylinder', cone:'cone', torus:'torus'};
                    const w1 = filtered[1].toLowerCase(), w2 = filtered[2].toLowerCase();
                    if ((knownColors[w1] && shapeSynonyms[w2]) || (shapeSynonyms[w1] && knownColors[w2])) {
                        const targetColor = knownColors[w1] ? w1 : w2;
                        const targetShape = shapeSynonyms[w1] ? shapeSynonyms[w1] : shapeSynonyms[w2];
                        let found = null;
                        scene.traverse(child => {
                            if (found || !child.isMesh || !child.name || child.name.startsWith('_')) return;
                            const cType = getTypeName(child), cColor = getColorName(child);
                            if (cType.includes(targetShape) && cColor === targetColor) found = child;
                        });
                        if (found) {
                            obj = found;
                            prop = filtered[3];
                            valueTokens = filtered.slice(4);
                            log('[deep search] Using ' + found.name, 'ok');
                        }
                    }
                }
                if (!obj && currentObject) {
                    obj = currentObject;
                    prop = filtered[1];
                    valueTokens = filtered.slice(2);
                }
            } else if (currentObject && filtered.length >= 3) {
                obj = currentObject;
                prop = filtered[1];
                valueTokens = filtered.slice(2);
            }
            if (!obj || !prop || !valueTokens.length) { log('Usage: set <object> <property> to <value>', 'err'); return; }
            const coreResult = handleCoreSet(obj, prop, valueTokens);
            if (coreResult.ok) {
                pushUndo(coreResult.description, coreResult.undo, coreResult.redo);
                log('OK', 'ok');
                return;
            }
            const capResult = applyCapabilityBridge(obj, prop, valueTokens);
            if (capResult.ok) {
                pushUndo(capResult.description, capResult.undo, capResult.redo);
                log('OK', 'ok');
                return;
            }
            if (capResult.reason === 'unknown' && CAPABILITY_POLICY.allow_passthrough) {
                const passthroughValue = coerceSingleValue(valueTokens);
                if (!obj.userData) obj.userData = {};
                const hadPrev = Object.prototype.hasOwnProperty.call(obj.userData, prop);
                const prev = hadPrev ? obj.userData[prop] : undefined;
                const next = passthroughValue;
                obj.userData[prop] = next;
                const desc = `${obj.name || '(object)'}.userData.${prop}`;
                pushUndo(desc, () => {
                    if (!obj || !obj.userData) return;
                    if (hadPrev) obj.userData[prop] = prev; else delete obj.userData[prop];
                }, () => { obj.userData[prop] = next; });
                log('Stored on userData.' + prop, 'ok');
            } else {
                log(capResult.message || ('Could not set ' + prop), 'err');
                if (capResult.suggestion) log('Try: ' + capResult.suggestion, 'cyan');
            }
        }
        else if ((parts[0] === 'inspect' || parts[0] === 'look' || parts[0] === 'examine' || parts[0] === 'x' || parts[0] === 'ex') && parts[1]) {
            const obj = scene.getObjectByName(parts[1]);
            if (obj) {
                log(parts[1] + ':', 'cyan');
                log('  pos: [' + obj.position.x.toFixed(1) + ',' + obj.position.y.toFixed(1) + ',' + obj.position.z.toFixed(1) + ']');
                if (obj._color) log('  color: ' + obj._color);
                else if (obj.material && obj.material.color) log('  color: #' + obj.material.color.getHexString());
                if (obj._text) log('  text: ' + obj._text);
                log('  visible: ' + obj.visible);
                if (obj.userData._description) log('  description: ' + obj.userData._description);
                for (const [k, v] of Object.entries(obj.userData)) { if (!k.startsWith('_')) log('  ' + k + ': ' + v); }
                const caps = availableCapabilitiesFor(obj);
                if (caps.length) {
                    log('  capabilities:', 'cyan');
                    caps.forEach(cap => log('    ' + describeCapability(cap), 'cyan'));
                }
                // Show 3D model credit if available
                if (obj.userData._credit) log('  credit: ' + obj.userData._credit, 'dim');
            } else log('Not found', 'err');
        }
        else if (parts[0] === 'camera' && parts[1] === 'reset') {
            camera.position.set(0, 5, 50); controls.target.set(0, 0, 0); log('Camera reset', 'ok');
        }
        else if (parts[0] === 'redraw') {
            // Collect all objects with _type (user-created known objects)
            const toRedraw = [];
            scene.traverse(o => {
                if (o.userData && o.userData._type) {
                    toRedraw.push({ name: o.name, type: o.userData._type, pos: o.position.clone() });
                }
            });
            if (toRedraw.length === 0) { log('No typed objects to redraw', 'warn'); return; }
            log('Redrawing ' + toRedraw.length + ' object(s) with current settings...', 'dim');
            // Delete old objects
            toRedraw.forEach(item => {
                const old = scene.getObjectByName(item.name);
                if (old) scene.remove(old);
            });
            // Recreate with current meta settings
            toRedraw.forEach(item => {
                const preset = KNOWN_OBJECTS[item.type] || { shape: 'box', color: 0x00ff00 };
                if (preset.model && meta.useModels) {
                    gltfLoader.load(preset.model, (gltf) => {
                        const model = gltf.scene;
                        model.name = item.name;
                        model.userData._type = item.type;
                        if (preset.credit) model.userData._credit = preset.credit;
                        const box = new THREE.Box3().setFromObject(model);
                        const modelSize = box.getSize(new THREE.Vector3());
                        const maxDim = Math.max(modelSize.x, modelSize.y, modelSize.z);
                        const normalizeScale = maxDim > 0 ? 1 / maxDim : 1;
                        const sx = preset.scaleX || 1, sy = preset.scaleY || 1, sz = preset.scaleZ || 1;
                        const gs = meta.modelScale || 2;
                        model.scale.set(normalizeScale * sx * gs, normalizeScale * sy * gs, normalizeScale * sz * gs);
                        model.position.copy(item.pos);
                        scene.add(model);
                    });
                } else {
                    let geom = preset.shape === 'sphere' ? new THREE.SphereGeometry(1) : preset.shape === 'cylinder' ? new THREE.CylinderGeometry(0.5, 0.5, 1) : new THREE.BoxGeometry(1, 1, 1);
                    const mat = new THREE.MeshStandardMaterial({color: preset.color});
                    const mesh = new THREE.Mesh(geom, mat);
                    mesh.name = item.name;
                    mesh.userData._type = item.type;
                    if (preset.scaleX || preset.scaleY || preset.scaleZ) mesh.scale.set(preset.scaleX || 1, preset.scaleY || 1, preset.scaleZ || 1);
                    mesh.position.copy(item.pos);
                    scene.add(mesh);
                }
            });
            log('Redrawn ' + toRedraw.length + ' object(s)', 'ok');
        }
        else if (parts[0] === 'save') {
            const slot = parts[1] || 'default';
            const saveData = {};
            scene.traverse(o => {
                if (o.name && !o.name.startsWith('_')) {
                    const data = { x: o.position.x, y: o.position.y, z: o.position.z, ...o.userData };
                    if (o._color) data._textColor = o._color;
                    else if (o.material && o.material.color) data._color = o.material.color.getHex();
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
                let obj = scene.getObjectByName(name);
                if (!obj && data._consoleTemplate && data._consoleTemplate.type === 'mesh') {
                    const tpl = data._consoleTemplate;
                    let geom = null;
                    const size = tpl.size || 1;
                    if (tpl.shape === 'sphere') geom = new THREE.SphereGeometry(size, 32, 32);
                    else if (tpl.shape === 'cylinder') geom = new THREE.CylinderGeometry(size, size, size * 2);
                    else geom = new THREE.BoxGeometry(size, size, size);
                    const mat = new THREE.MeshStandardMaterial({ color: tpl.color ?? 0x00ff00 });
                    const mesh = new THREE.Mesh(geom, mat);
                    mesh.name = name;
                    mesh.userData = Object.assign({}, tpl);
                    scene.add(mesh);
                    obj = mesh;
                }
                if (obj) {
                    if (data.x !== undefined) obj.position.x = data.x;
                    if (data.y !== undefined) obj.position.y = data.y;
                    if (data.z !== undefined) obj.position.z = data.z;
                    const fontSize = data.font_size || (obj.userData && obj.userData.font_size) || 48;
                    if (data._textColor !== undefined && obj._ctx) {
                        obj._color = data._textColor; obj._ctx.clearRect(0, 0, obj._canvas.width, obj._canvas.height);
                        obj._ctx.font = 'bold ' + fontSize + 'px Arial'; obj._ctx.textAlign = 'center'; obj._ctx.textBaseline = 'middle';
                        obj._ctx.fillStyle = data._textColor; obj._ctx.fillText(obj._text, obj._canvas.width/2, obj._canvas.height/2);
                        obj.material.map.needsUpdate = true;
                    } else if (data._color !== undefined && obj.material && obj.material.color) obj.material.color.setHex(data._color);
                    if (data._sx !== undefined && obj.scale) { obj.scale.x = data._sx; obj.scale.y = data._sy; obj.scale.z = data._sz; }
                    if (data._visible !== undefined) obj.visible = data._visible;
                    Object.assign(obj.userData, data);
                    restoreCapabilityState(obj);
                }
            }
            log('Game loaded from slot: ' + slot, 'ok');
        }
        else if (parts[0] === 'clear') { output.innerHTML = ''; }
        else if (parts[0] === 'credits') {
            log('Rosh v0.2.3', 'cyan');
            log('Copyright (c) 2025 Roger Dubar');
            log('https://rosh.cloud', 'dim');
        }
        else if (parts[0] === 'set' && parts.length < 3) {
            log('set - Set object properties', 'cyan');
            log('Usage:', 'dim');
            log('  set <object> <property> to <value>');
            log('  set ball color to red');
            log('  set logo x to 100');
        }
        else if (parts[0] === 'get' && parts.length < 2) {
            log('get - Get object properties or select objects', 'cyan');
            log('Usage:', 'dim');
            log('  get <object> <property>');
            log('  get all <type>  # select all of type');
        }
        else if (parts[0] === 'create' && parts.length < 2) {
            log('create - Create objects', 'cyan');
            log('Usage:', 'dim');
            log('  create <name>           # create object');
            log('  create <type> <name>    # create named object of type');
            log('  create big red ball     # create with modifiers');
            log('Type "help create" for known object types', 'dim');
        }
        else if (parts[0] === 'clone' && parts.length < 2) {
            log('clone - Clone existing objects', 'cyan');
            log('Usage:', 'dim');
            log('  clone <object>          # auto-named copy');
            log('  clone <object> as <name>');
        }
        else if (parts[0] === 'delete' && parts.length < 2) {
            log('delete - Remove objects', 'cyan');
            log('Usage:', 'dim');
            log('  delete <object>');
        }
        else if (parts[0] === 'move' && parts.length < 2) {
            log('move - Move objects to coordinates', 'cyan');
            log('Usage:', 'dim');
            log('  move <object> to x, y, z');
            log('  move ball to 0, 5, 0');
        }
        else if (parts[0] === 'make' && parts.length < 2) {
            log('make - Adjust object properties naturally', 'cyan');
            log('Usage:', 'dim');
            log('  make <object> bigger/smaller');
            log('  make <object> <color>');
            log('  make <object> visible/hidden');
        }
        else if ((parts[0] === 'look' || parts[0] === 'examine' || parts[0] === 'x' || parts[0] === 'ex') && parts.length < 2) {
            log('look/examine/x/ex - Inspect objects', 'cyan');
            log('Usage:', 'dim');
            log('  look <object>');
            log('  examine ball');
            log('  x ball   (shorthand)');
            log('  ex ball  (shorthand)');
        }
        else if (parts[0] === 'save' && parts.length < 2) {
            log('save - Save game state', 'cyan');
            log('Usage:', 'dim');
            log('  save <slot>');
            log('  save 1');
        }
        else if (parts[0] === 'load' && parts.length < 2) {
            log('load - Load game state', 'cyan');
            log('Usage:', 'dim');
            log('  load <slot>');
            log('  load 1');
        }
        else if (cmd.trim()) log('Unknown: ' + parts[0], 'err');
    } catch(e) { log('Error: ' + e.message, 'err'); }
}

document.addEventListener('keydown', e => {
    if (e.key === '`') { e.preventDefault(); toggleConsole(); }
});

input.addEventListener('keydown', e => {
    if (e.key === 'Enter' && input.value.trim()) {
        cmdHistory.unshift(input.value); historyIdx = -1;
        execCommand(input.value); input.value = '';
    } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        if (historyIdx < cmdHistory.length - 1) { historyIdx++; input.value = cmdHistory[historyIdx]; }
    } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        if (historyIdx > 0) { historyIdx--; input.value = cmdHistory[historyIdx]; }
        else if (historyIdx === 0) { historyIdx = -1; input.value = ''; }
    }
});

// Voice Input - Hold Ctrl+Space to speak (Chrome/Edge)
const voiceBtn = document.getElementById('rosh-voice');
let recognition = null;
let isListening = false;

const isSafari = /^((?!chrome|android).)*safari/i.test(navigator.userAgent);
if (isSafari) log('[note] Voice works best in Chrome. Safari support is limited.', 'warn');
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onresult = (event) => {
        let cmd = event.results[0][0].transcript.toLowerCase();
        cmd = cmd.replace(/colour/gi, 'color').replace(/centre/gi, 'center').replace(/rodger/gi, 'roger');
        const numWords = {zero:0,one:1,two:2,three:3,four:4,five:5,six:6,seven:7,eight:8,nine:9,ten:10};
        cmd = cmd.replace(/\b(zero|one|two|three|four|five|six|seven|eight|nine|ten)\b/gi, m => numWords[m.toLowerCase()]);
        log('[voice] ' + cmd, 'cyan');
        const corrected = fuzzyCorrectCommand(cmd);
        cmdHistory.unshift(corrected.cmd); historyIdx = -1;
        execCommand(cmd);
    };

    recognition.onend = () => {
        isListening = false;
        voiceBtn.classList.remove('listening');
    };

    recognition.onerror = (event) => {
        log('[voice error] ' + event.error, 'err');
        isListening = false;
        voiceBtn.classList.remove('listening');
    };
} else {
    voiceBtn.style.display = 'none';
    log('[voice] Not supported in this browser', 'dim');
}

function startVoice() {
    if (!recognition || isListening) return;
    try {
        recognition.start();
        isListening = true;
        voiceBtn.classList.add('listening');
        log('[voice] Listening...', 'dim');
    } catch(e) { log('[voice] ' + e.message, 'err'); }
}

function stopVoice() {
    if (!recognition || !isListening) return;
    recognition.stop();
}

document.addEventListener('keydown', e => {
    if (e.ctrlKey && e.code === 'Space' && consoleVisible && !e.repeat) {
        e.preventDefault();
        startVoice();
    }
});

document.addEventListener('keyup', e => {
    if (e.code === 'Space' && isListening) {
        stopVoice();
    }
});

voiceBtn.addEventListener('click', () => {
    if (isListening) stopVoice(); else startVoice();
});

log('Rosh v0.2.3 | Three.js', 'cyan');
log('Type help for commands. Press ` to toggle console.', 'dim');