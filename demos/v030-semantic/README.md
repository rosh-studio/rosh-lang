# v0.3.0 Semantic Package Demos

Test demos for v0.3.0 semantic packages (rosh-lights, rosh-scene, rosh-camera).

## Demos

### lighting-test.rosh
Tests all 5 light types:
- Ambient (base illumination)
- Directional (sun-like with shadows)
- Hemisphere (sky/ground gradient)
- Spot (focused beam)
- Point (omnidirectional)

### mini-museum.rosh
Museum scene with:
- 3 spotlights on pedestals
- Fog atmosphere
- Orbit camera controls
- Material properties

### outdoor-scene.rosh
Outdoor environment with:
- Hemisphere sky lighting
- Directional sun with shadows
- Trees, house, rocks

### gallery-enhanced.rosh
Enhanced version of virtual-gallery-simple using semantic packages:
- 5 lights (ambient, 3 spots, directional rim)
- Colored accent lighting (blue main, red/green accents)
- Fog atmosphere
- Orbit camera
- Material properties (metalness, roughness)

## Build

```bash
# Three.js (3D)
rosh build demos/v030-semantic/mini-museum.rosh --target threejs

# Phaser (2D - lights stored as data)
rosh build demos/v030-semantic/mini-museum.rosh --target phaser

# Pygame (2D - lights ignored)
rosh build demos/v030-semantic/mini-museum.rosh --target pygame
```

## Packages Tested

- `rosh-lights` - All 5 light types
- `rosh-scene` - Background, fog
- `rosh-camera` - Position, target, fov, controls

## Known Issues

Floor/ground planes are commented out due to coordinate system ambiguity.
See: `rosh-dev/proposals/SEMANTIC-POSITIONING-PROPOSAL.md`

## Results

All demos compile to all 3 targets (Three.js, Phaser, Pygame).
Emitter fixes applied for shadows and spotlight targets.

See: `rosh-dev/proposals/SEMANTIC-TEST-FINDINGS.md`
