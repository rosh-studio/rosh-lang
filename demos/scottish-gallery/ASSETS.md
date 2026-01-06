# Scottish Heritage Gallery - Asset Tracking

## Status Summary

| Object | 3D Model | 2D Fallback | Credits | Status |
|--------|----------|-------------|---------|--------|
| Lewis Chess King | ✅ GLB | ✅ Rectangle | British Museum CC BY-NC-SA | ✅ Ready |
| Lewis Chess Queen | ✅ GLB | ✅ Rectangle | British Museum CC BY-NC-SA | ✅ Ready |
| Pictish Stone | ✅ GLB | ✅ Rectangle | Douglas Ledingham CC BY-NC | ✅ Ready |
| Cutty Sark Cat | ✅ GLB | ✅ Ellipse | Royal Museums Greenwich CC0 | ✅ Ready |
| Dolly the Sheep | Premium | ✅ Ellipse | NMS | Shape fallback |
| Stirling Torc | N/A | ✅ Torus shape | NMS | ✅ Ready (built-in) |

## 3D Models Downloaded

### Lewis Chess King & Queen
- **Source**: The British Museum (Sketchfab)
- **License**: CC BY-NC-SA
- **Files**: `assets/3d_glb/lewis_chess_king.glb`, `lewis_chess_queen.glb`

### Pictish Stone
- **Source**: Douglas Ledingham (Sketchfab)
- **License**: CC BY-NC
- **File**: `assets/3d_glb/pictish_stone.glb` (77MB - detailed scan)

### Cutty Sark Cat
- **Source**: Royal Museums Greenwich (Sketchfab)
- **License**: CC0 Public Domain
- **File**: `assets/3d_glb/cutty_sark_cat.glb`

## Objects Using Shape Fallbacks

### Dolly the Sheep
- **Reason**: 3D model is premium on Sketchfab
- **Fallback**: White ellipse (2D), sphere (3D)
- **Alternative**: Could photograph/scan a model or find another CC source

### Stirling Torc
- **Reason**: Simple geometric form works well as torus
- **Fallback**: Built-in torus shape with gold color
- **Note**: Real model would be nice but shape captures essence

## Demo Commands

```bash
# Build for Three.js (3D)
uv run rosh build demos/scottish-gallery/gallery.rosh --target threejs --output demos/scottish-gallery/threejs/ --copy-assets

# Build for Phaser (2D)
uv run rosh build demos/scottish-gallery/gallery.rosh --target phaser --output demos/scottish-gallery/phaser/ --copy-assets

# Run in CLI
uv run rosh run demos/scottish-gallery/gallery.rosh
```

## Gallery Layout

```
+------------------------------------------+
|                                          |
|   [King]    [Queen]    [Stone]           |  North Wall (Medieval)
|   -3,-4      -1,-4      1,-4             |
|                                          |
|              [Torc]                      |  Center (Iron Age Gold)
|               0,0                        |
|                                          |
|   [Cat]                [Dolly]           |  South Wall (Maritime/Science)
|   -2,4                  2,4              |
|                                          |
+------------------------------------------+
```

## Credits File
All credits are recorded in `assets/3d_glb/3d Model Credits.txt`
