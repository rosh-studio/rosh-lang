# Known Limitations

Honest assessment of what Rosh can and cannot do as of v0.2.6.

---

## Platform Support

### What Works

| Platform | Status | Notes |
|----------|--------|-------|
| **Three.js (Web 3D)** | Full support | Reference implementation |
| **Phaser (Web 2D)** | Full support | Shared runtime |
| **Pygame (Desktop 2D)** | Working | Some features lag behind |
| **Godot (Desktop 2D/3D)** | Working | Some features lag behind |

### ThreeJS-Only Features

These features are currently **only available in Three.js**:

| Feature | Status in Other Emitters |
|---------|--------------------------|
| Edit mode (`edit on/off`) | Not implemented |
| Click-to-select | Not implemented |
| Object control (arrow keys) | Not implemented |
| Gravity system | Not implemented |
| Click-to-move | Not implemented |
| Shared worlds (Project Twin) | CLI only, not graphical |
| Voice input | Browser-only |
| AI prompt | Browser-only |

**Recommendation:** For demos and client work, use the Three.js target.

---

## Shared Worlds (Project Twin)

### Working
- Connect/disconnect from shared worlds
- Real-time object creation sync
- Real-time object deletion sync
- Chat between users
- Server-side persistence

### Limitations
- **No authentication** - Anyone can connect to any world
- **No permissions** - Anyone can delete anyone's objects
- **No position sync** - Moving objects doesn't broadcast (yet)
- **No player avatars** - Can't see other users
- **Server downtime** - rosh.cloud server may be offline

### Graceful Degradation
If connect fails, you see:
```
Connection failed - server may be offline
You can still work offline. Use "save" to keep your work.
```

---

## Persistence

### Browser Storage
- `save`/`load` uses browser localStorage
- Data is per-browser, per-device
- Clearing browser data loses saves
- ~5MB limit per origin

### No Cloud Sync (Yet)
- Saves don't sync between devices
- No user accounts
- Planned for future release

---

## Objects & Types

### Supported Shapes
- sphere, ball
- cube, box
- cylinder
- cone
- torus
- plane

### 3D Models
- GLB format only
- Must be pre-registered in known-objects.toml
- Current models: castle, orc, dragon, tree, etc.

### Not Supported
- Custom 3D model upload at runtime
- Importing arbitrary files
- Image textures on basic shapes
- Video textures

---

## Physics

### What Works
- Gravity on/off
- Ground collision
- Fixed property (immunity to gravity)
- Per-object gravity enable/disable

### Not Implemented
- Object-to-object collision
- Bouncing/elasticity
- Friction
- Mass/weight
- Forces/impulses
- Joints/constraints

**Note:** This is a creative tool, not a physics simulator. Full physics would require a dedicated engine (Cannon.js, Rapier, etc.).

---

## Performance

### Tested With
- ~100 objects: smooth
- ~500 objects: acceptable
- 1000+ objects: slowdown likely

### Recommendations
- Keep object count reasonable for demos
- Use `delete` to remove unused objects
- Scene transitions don't unload objects

---

## Browser Compatibility

### Recommended
- Chrome 90+
- Edge 90+
- Safari 15+
- Firefox 90+

### Voice Input
- Chrome: full support
- Edge: full support
- Safari: partial (may require permission)
- Firefox: not supported

### Mobile
- Works on tablets
- Phones: small screen, awkward typing
- Touch controls: limited (no virtual keyboard for console)

---

## Security

### Current State
- **Single-user sandbox** - no multi-user security
- **No authentication** - shared worlds are public
- **No permissions** - anyone can modify anything
- **No rate limiting** - could be abused
- **No audit logging** - can't track who did what

### What This Means
- Fine for demos and development
- Not ready for public-facing deployments
- Not ready for sensitive content

### Planned (v0.3+)
- Trust levels (guest/member/developer/admin)
- Object ownership
- Audit trails
- Rate limits

---

## Language Limitations

### No Programming Constructs in Console
The console is for commands, not programming. These don't work:
- Variables (`set x to 5`)
- Loops (`for each ball...`)
- Conditionals (`if x > 5...`)
- Functions

**For programming, use .rosh source files**, which support full language features.

### No Import in Console
- Can't load external files
- Can't import libraries
- All objects must be created at runtime

---

## What's Coming

### Short Term (Q1 2026)
- Position sync in shared worlds
- Better mobile experience
- More 3D models

### Medium Term (2026)
- Cloud persistence
- User accounts
- Edit mode for other emitters

### Long Term (2027+)
- Unity emitter (VR support)
- Physics engine integration
- Authentication and permissions

---

## Reporting Issues

If you find bugs or limitations not listed here:

1. Check [github.com/rdubar/rosh/issues](https://github.com/rdubar/rosh/issues)
2. Create a new issue with:
   - What you tried
   - What happened
   - What you expected
   - Browser/platform info

---

*Rosh v0.2.6 - "Changing Worlds"*
