#!/bin/bash
# =============================================================================
# Deploy Demos Script
# =============================================================================
#
# Builds all demos for Phaser (web), Three.js (web 3D), Pygame (desktop), and Godot.
#
# USAGE:
#   cd rosh-lang
#   ./scripts/deploy-demos.sh
#
# WHAT IT DOES:
#   Phaser (browser)  → rosh-portal/static/demos/*-phaser/   (served by Flask)
#   Three.js (browser) → rosh-portal/static/demos/*-threejs/ (served by Flask)
#   Pygame (desktop)  → rosh-portal/static/dist/*-pygame/    (local testing only)
#   Godot (desktop)   → rosh-portal/static/dist/*-godot/     (local testing only)
#
# AFTER RUNNING:
#   Commit and push to deploy via Railway
#
# =============================================================================

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROSH_LANG="$(dirname "$SCRIPT_DIR")"
ROSH_PORTAL="/Users/rdubar/dev/rosh/rosh-portal/static"

echo "=== Deploying Rosh Demos ==="
echo ""

cd "$ROSH_LANG"

# =============================================================================
# PHASER BUILDS (Browser - for web upload)
# =============================================================================

echo "🌐 PHASER BUILDS (for web upload)"
echo ""

echo "📦 Building rosh-intro (Phaser)..."
uv run rosh build demos/rosh-intro/game.rosh \
    --target phaser \
    --output "$ROSH_PORTAL/demos/rosh-intro-phaser/" \
    --copy-assets

echo ""
echo "📦 Building space-shooter (Phaser)..."
uv run rosh build demos/space-shooter/game.rosh \
    --target phaser \
    --output "$ROSH_PORTAL/demos/space-shooter-phaser/" \
    --copy-assets

echo ""
echo "📦 Building block-pusher (Phaser)..."
uv run rosh build demos/block-pusher/game.rosh \
    --target phaser \
    --output "$ROSH_PORTAL/demos/block-pusher-phaser/" \
    --copy-assets

# =============================================================================
# THREE.JS BUILDS (Browser 3D - for web upload)
# =============================================================================

echo ""
echo "🌌 THREE.JS BUILDS (for web upload)"
echo ""

echo "📦 Building rosh-intro (Three.js)..."
uv run rosh build demos/rosh-intro/game.rosh \
    --target threejs \
    --output "$ROSH_PORTAL/demos/rosh-intro-threejs/" \
    --copy-assets
cp -r "$ROSH_LANG/assets/3d_glb" "$ROSH_PORTAL/demos/rosh-intro-threejs/"

echo ""
echo "📦 Building space-shooter (Three.js)..."
uv run rosh build demos/space-shooter/game.rosh \
    --target threejs \
    --output "$ROSH_PORTAL/demos/space-shooter-threejs/" \
    --copy-assets
cp -r "$ROSH_LANG/assets/3d_glb" "$ROSH_PORTAL/demos/space-shooter-threejs/"

echo ""
echo "📦 Building block-pusher (Three.js)..."
uv run rosh build demos/block-pusher/game.rosh \
    --target threejs \
    --output "$ROSH_PORTAL/demos/block-pusher-threejs/" \
    --copy-assets
cp -r "$ROSH_LANG/assets/3d_glb" "$ROSH_PORTAL/demos/block-pusher-threejs/"

# =============================================================================
# PYGAME BUILDS (Desktop - local testing only)
# =============================================================================

echo ""
echo "🐍 PYGAME BUILDS (local testing only)"
echo ""

# Create dist directory
mkdir -p "$ROSH_PORTAL/dist"

echo "📦 Building rosh-intro (Pygame)..."
uv run rosh build demos/rosh-intro/game.rosh \
    --target pygame \
    --output "$ROSH_PORTAL/dist/rosh-intro-pygame/" \
    --copy-assets

echo ""
echo "📦 Building space-shooter (Pygame)..."
uv run rosh build demos/space-shooter/game.rosh \
    --target pygame \
    --output "$ROSH_PORTAL/dist/space-shooter-pygame/" \
    --copy-assets

echo ""
echo "📦 Building block-pusher (Pygame)..."
uv run rosh build demos/block-pusher/game.rosh \
    --target pygame \
    --output "$ROSH_PORTAL/dist/block-pusher-pygame/" \
    --copy-assets

# =============================================================================
# GODOT BUILDS (Desktop - local testing only)
# =============================================================================

echo ""
echo "🎮 GODOT BUILDS (local testing only)"
echo ""

GODOT_INTRO_DIR="$ROSH_PORTAL/dist/rosh-intro-godot"
mkdir -p "$GODOT_INTRO_DIR"

echo "📦 Building rosh-intro (Godot)..."
uv run python -c "
from rosh.parser import Parser
from rosh.lexer import Lexer
from rosh.ir_transformer import transform_ast_to_ir
from rosh.emitters.godot import GodotEmitter

# Read the source
with open('demos/rosh-intro/game.rosh', 'r') as f:
    source = f.read()

# Parse and transform
lexer = Lexer(source)
tokens = lexer.tokenize()
parser = Parser(tokens)
ast = parser.parse()
ir = transform_ast_to_ir(ast)

# Emit Godot
emitter = GodotEmitter(ir)
gd_code = emitter.emit()

# Write outputs
with open('$GODOT_INTRO_DIR/main.gd', 'w') as f:
    f.write(gd_code)

with open('$GODOT_INTRO_DIR/main.tscn', 'w') as f:
    f.write('''[gd_scene load_steps=2 format=3]

[ext_resource type=\"Script\" path=\"res://main.gd\" id=\"1\"]

[node name=\"Main\" type=\"Node3D\"]
script = ExtResource(\"1\")
''')

with open('$GODOT_INTRO_DIR/project.godot', 'w') as f:
    f.write('''[gd_resource type=\"ProjectSettings\" format=3]

config_version=5

[application]
config/name=\"Rosh Intro\"
run/main_scene=\"res://main.tscn\"
config/features=PackedStringArray(\"4.2\")

[display]
window/size/viewport_width=1280
window/size/viewport_height=720

[rendering]
renderer/rendering_method=\"forward_plus\"
''')

print('  Created: main.gd, main.tscn, project.godot')
"

# Space Shooter (Godot) - 2D Arcade with sprites
GODOT_SHOOTER_DIR="$ROSH_PORTAL/projects/space-shooter-godot"
mkdir -p "$GODOT_SHOOTER_DIR"

echo "📦 Building space-shooter (Godot)..."
uv run python -c "
from rosh.parser import Parser
from rosh.lexer import Lexer
from rosh.ir_transformer import transform_ast_to_ir
from rosh.emitters.godot import GodotEmitter
import shutil

# Read the source
with open('demos/space-shooter/game.rosh', 'r') as f:
    source = f.read()

# Parse and transform
lexer = Lexer(source)
tokens = lexer.tokenize()
parser = Parser(tokens)
ast = parser.parse()
ir = transform_ast_to_ir(ast)

# Emit Godot
emitter = GodotEmitter(ir)
gd_code = emitter.emit()

# Write outputs
with open('$GODOT_SHOOTER_DIR/main.gd', 'w') as f:
    f.write(gd_code)

with open('$GODOT_SHOOTER_DIR/main.tscn', 'w') as f:
    f.write('''[gd_scene load_steps=2 format=3]

[ext_resource type=\"Script\" path=\"res://main.gd\" id=\"1\"]

[node name=\"Main\" type=\"Node2D\"]
script = ExtResource(\"1\")
''')

with open('$GODOT_SHOOTER_DIR/project.godot', 'w') as f:
    f.write('''config_version=5

[application]
config/name=\"Space Shooter\"
run/main_scene=\"res://main.tscn\"
config/features=PackedStringArray(\"4.5\")

[display]
window/size/viewport_width=800
window/size/viewport_height=600

[rendering]
renderer/rendering_method=\"gl_compatibility\"
''')

print('  Created: main.gd, main.tscn, project.godot')
"

# Copy sprite assets
echo "  Copying sprite assets..."
cp "$ROSH_PORTAL/demos/space-shooter-phaser/assets/player.png" "$GODOT_SHOOTER_DIR/"
cp "$ROSH_PORTAL/demos/space-shooter-phaser/assets/enemyShip.png" "$GODOT_SHOOTER_DIR/"
cp "$ROSH_PORTAL/demos/space-shooter-phaser/assets/laserGreen.png" "$GODOT_SHOOTER_DIR/"
cp "$ROSH_PORTAL/demos/space-shooter-phaser/assets/laser1.ogg" "$GODOT_SHOOTER_DIR/"
cp "$ROSH_PORTAL/demos/space-shooter-phaser/assets/lose1.ogg" "$GODOT_SHOOTER_DIR/"
cp "$ROSH_PORTAL/demos/space-shooter-phaser/assets/lose3.ogg" "$GODOT_SHOOTER_DIR/"
echo "  Assets copied!"

echo ""
echo "=== All demos built! ==="
echo ""
echo "Phaser (upload these):"
echo "  $ROSH_PORTAL/demos/rosh-intro-phaser/"
echo "  $ROSH_PORTAL/demos/space-shooter-phaser/"
echo "  $ROSH_PORTAL/demos/block-pusher-phaser/"
echo ""
echo "Three.js (upload these):"
echo "  $ROSH_PORTAL/demos/rosh-intro-threejs/"
echo "  $ROSH_PORTAL/demos/space-shooter-threejs/"
echo "  $ROSH_PORTAL/demos/block-pusher-threejs/"
echo ""
echo "Pygame (local testing - don't upload):"
echo "  $ROSH_PORTAL/dist/rosh-intro-pygame/"
echo "  $ROSH_PORTAL/dist/space-shooter-pygame/"
echo "  $ROSH_PORTAL/dist/block-pusher-pygame/"
echo ""
echo "Godot projects (require Godot to run):"
echo "  $ROSH_PORTAL/dist/rosh-intro-godot/"
echo "  $ROSH_PORTAL/projects/space-shooter-godot/"
echo ""
echo "To run Pygame demos:"
echo "  python3 $ROSH_PORTAL/dist/space-shooter-pygame/game.py"
echo ""
echo "To run Godot projects:"
echo "  open -a Godot $ROSH_PORTAL/projects/space-shooter-godot/project.godot"
