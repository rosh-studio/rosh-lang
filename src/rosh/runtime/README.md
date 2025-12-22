# Rosh Runtime

Shared JavaScript runtime for Rosh across all browser-based targets.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  rosh-runtime.js (SHARED)                                   │
│  ├── Console UI (CSS, HTML)                                 │
│  ├── Undo/redo system                                       │
│  ├── Command parsing                                        │
│  ├── Fuzzy matching                                         │
│  └── Core commands: create, set, get, delete, list, etc.   │
└─────────────────────────┬───────────────────────────────────┘
                          │
            ┌─────────────┴─────────────┐
            │    Adapter Interface      │
            │    (engine must implement)│
            └─────────────┬─────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ threejs-     │  │ phaser-      │  │ (future)     │
│ adapter.js   │  │ adapter.js   │  │ adapters     │
│ (~200 lines) │  │ (~200 lines) │  │              │
└──────────────┘  └──────────────┘  └──────────────┘
```

## Adapter Interface

Each engine adapter must implement these methods:

```javascript
// Object management
getObject(name: string): Object | null
getAllObjects(): Object[]
createObject(type: string, name: string, props: object): Object
deleteObject(obj: Object): void

// Properties
setProperty(obj: Object, prop: string, value: any): void
getProperty(obj: Object, prop: string): any
getObjectName(obj: Object): string
getObjectType(obj: Object): string

// Position
getObjectPosition(obj: Object): {x, y, z}
setObjectPosition(obj: Object, x, y, z): void

// Appearance
setObjectVisible(obj: Object, visible: boolean): void
setObjectColor(obj: Object, color: number): void
getObjectColor(obj: Object): number
setObjectScale(obj: Object, scale: number): void
getObjectScale(obj: Object): number
```

## Usage

```javascript
// 1. Set up your engine (Three.js, Phaser, etc.)
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(...);
const renderer = new THREE.WebGLRenderer();

// 2. Create adapter
const adapter = new ThreeJSAdapter(scene, camera, renderer);

// 3. Create and initialize runtime
const rosh = new RoshRuntime(adapter, { confirmThreshold: 10 });
rosh.init();

// 4. Console opens with backtick key
```

## Testing

Open `test-runtime.html` in a browser to test the runtime standalone.

```bash
cd src/rosh/runtime
python -m http.server 8000
# Open http://localhost:8000/test-runtime.html
```

## Files

| File | Size | Purpose |
|------|------|---------|
| `rosh-runtime.js` | ~600 lines | Shared runtime core |
| `threejs-adapter.js` | ~200 lines | Three.js integration |
| `phaser-adapter.js` | ~200 lines | Phaser integration (TODO) |
| `test-runtime.html` | ~100 lines | Browser test harness |

## Version

- Runtime: 0.1.0
- Implements IR: 0.1.0
