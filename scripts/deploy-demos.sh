#!/bin/bash
# =============================================================================
# Deploy Demos Script
# =============================================================================
#
# Builds all demos for Phaser (web) and Pygame (desktop).
#
# USAGE:
#   cd rosh-lang
#   ./scripts/deploy-demos.sh
#
# WHAT IT DOES:
#   Phaser (browser) → rosh.cloud/demos/*-phaser/  (for web upload)
#   Pygame (desktop) → rosh.cloud/dist/*-pygame/   (local testing only)
#
# AFTER RUNNING:
#   Upload rosh.cloud/demos/ to your web server (not dist/)
#
# =============================================================================

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROSH_LANG="$(dirname "$SCRIPT_DIR")"
ROSH_CLOUD="/Users/rdubar/dev/rosh/rosh.cloud"

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
    --output "$ROSH_CLOUD/demos/rosh-intro-phaser/" \
    --copy-assets

echo ""
echo "📦 Building space-shooter (Phaser)..."
uv run rosh build demos/space-shooter/game.rosh \
    --target phaser \
    --output "$ROSH_CLOUD/demos/space-shooter-phaser/" \
    --copy-assets

echo ""
echo "📦 Building block-pusher (Phaser)..."
uv run rosh build demos/block-pusher/game.rosh \
    --target phaser \
    --output "$ROSH_CLOUD/demos/block-pusher-phaser/" \
    --copy-assets

# =============================================================================
# PYGAME BUILDS (Desktop - local testing only)
# =============================================================================

echo ""
echo "🐍 PYGAME BUILDS (local testing only)"
echo ""

# Create dist directory
mkdir -p "$ROSH_CLOUD/dist"

echo "📦 Building rosh-intro (Pygame)..."
uv run rosh build demos/rosh-intro/game.rosh \
    --target pygame \
    --output "$ROSH_CLOUD/dist/rosh-intro-pygame/" \
    --copy-assets

echo ""
echo "📦 Building space-shooter (Pygame)..."
uv run rosh build demos/space-shooter/game.rosh \
    --target pygame \
    --output "$ROSH_CLOUD/dist/space-shooter-pygame/" \
    --copy-assets

echo ""
echo "📦 Building block-pusher (Pygame)..."
uv run rosh build demos/block-pusher/game.rosh \
    --target pygame \
    --output "$ROSH_CLOUD/dist/block-pusher-pygame/" \
    --copy-assets

echo ""
echo "=== All demos built! ==="
echo ""
echo "Phaser (upload these):"
echo "  $ROSH_CLOUD/demos/rosh-intro-phaser/"
echo "  $ROSH_CLOUD/demos/space-shooter-phaser/"
echo "  $ROSH_CLOUD/demos/block-pusher-phaser/"
echo ""
echo "Pygame (local testing - don't upload):"
echo "  $ROSH_CLOUD/dist/rosh-intro-pygame/"
echo "  $ROSH_CLOUD/dist/space-shooter-pygame/"
echo "  $ROSH_CLOUD/dist/block-pusher-pygame/"
echo ""
echo "To run Pygame demos:"
echo "  python3 $ROSH_CLOUD/dist/space-shooter-pygame/game.py"
