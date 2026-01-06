# Scottish Heritage Gallery - Asset Tracking

## Status Summary

| Object | 3D Model | 2D Fallback | Credits | Status |
|--------|----------|-------------|---------|--------|
| Lewis Chess King | Need GLB | ✅ Shape | British Museum CC BY-NC-SA | **NEED 3D** |
| Lewis Chess Queen | Need GLB | ✅ Shape | British Museum CC BY-NC-SA | **NEED 3D** |
| Dolly the Sheep | Need GLB | ✅ Shape | NMS (check license) | **NEED 3D** |
| Stirling Torc | N/A | ✅ Torus shape | NMS | ✅ Ready |
| Hunterston Brooch | N/A | Need PNG | NMS | **NEED PNG** |

## 3D Models to Download (Manual - Sketchfab)

### 1. Lewis Chess King
- **URL**: https://sketchfab.com/3d-models/a-king-from-the-lewis-chessmen-504da084a1cd47f3af2aea97280d3fee
- **License**: CC BY-NC-SA (The British Museum)
- **Download**: Click "Download 3D Model" → Select glTF format
- **Save as**: `assets/3d_glb/lewis_chess_king.glb`

### 2. Lewis Chess Queen
- **URL**: https://sketchfab.com/3d-models/a-queen-from-the-lewis-chessmen-af096aa7ca934f84b6d64c89a8e312d4
- **License**: CC BY-NC-SA (The British Museum)
- **Download**: Click "Download 3D Model" → Select glTF format
- **Save as**: `assets/3d_glb/lewis_chess_queen.glb`

### 3. Dolly the Sheep
- **URL**: https://sketchfab.com/3d-models/dolly-the-sheep-24f946d5b36a40239c222a6e3a5f4414
- **License**: Check on Sketchfab (National Museums Scotland)
- **Download**: Click "Download 3D Model" → Select glTF format
- **Save as**: `assets/3d_glb/dolly_the_sheep.glb`

## 2D Sprites Needed

### Hunterston Brooch
- **Source**: National Museums Scotland collection
- **URL**: https://www.nms.ac.uk/explore-our-collections/collection-search-results/brooch/142912
- **Task**: Find/screenshot a good image, crop to PNG with transparency
- **Save as**: `assets/sprites/hunterston_brooch.png`

## Already Defined in known_objects.toml

All five Scottish heritage objects are now defined:
- `lewis_chess_king` - with 3D model path, 2D rectangle fallback
- `lewis_chess_queen` - with 3D model path, 2D rectangle fallback
- `dolly_the_sheep` - with 3D model path, 2D ellipse fallback
- `stirling_torc` - 3D torus shape, 2D gold circle (no external model needed)
- `hunterston_brooch` - sprite fallback (billboard in 3D)

## After Downloads

1. Copy GLB files to `rosh-lang/assets/3d_glb/`
2. Test with: `rosh build demos/scottish-gallery/gallery.rosh --target threejs`
3. Objects will use shape fallbacks until models are in place

## Demo Commands

```bash
# Build for Three.js
rosh build demos/scottish-gallery/gallery.rosh --target threejs --output demos/scottish-gallery/threejs/

# Build for Phaser
rosh build demos/scottish-gallery/gallery.rosh --target phaser --output demos/scottish-gallery/phaser/

# Run in CLI
rosh run demos/scottish-gallery/gallery.rosh
```
