#!/bin/bash
# =============================================================================
# Minify Hand-Crafted Demos
# =============================================================================
#
# Minifies JavaScript files in hand-crafted demos that aren't built by the
# Rosh transpiler (and therefore don't get --minify flag from deploy-demos.sh).
#
# USAGE:
#   cd rosh-lang
#   ./scripts/minify-handcrafted.sh
#
# PREREQUISITES:
#   pip install rjsmin   (or: pip install jsmin)
#
# HAND-CRAFTED DEMOS:
#   - rosh-airspace    (Airspace visualization demo)
#   - rosh-world       (Shared creative space demo)
#   - scottish-museum  (Museum demo)
#
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROSH_PORTAL="/Users/rdubar/dev/rosh/rosh-portal/static/demos"

# List of hand-crafted demo directories
HANDCRAFTED_DEMOS=(
    "rosh-airspace"
    "rosh-world"
    "scottish-museum"
)

# Files to minify in each demo
FILES_TO_MINIFY=(
    "game.js"
    "rosh-network.js"
    "rosh-objects.js"
)

echo "=== Minifying Hand-Crafted Demos ==="
echo ""

# Check if rjsmin or jsmin is available
uv run python -c "import rjsmin" 2>/dev/null && MINIFIER="rjsmin" || {
    uv run python -c "import jsmin" 2>/dev/null && MINIFIER="jsmin" || {
        echo "ERROR: No JS minifier found. Install with:"
        echo "  pip install rjsmin   (preferred, faster)"
        echo "  pip install jsmin    (alternative)"
        exit 1
    }
}

echo "Using minifier: $MINIFIER"
echo ""

minify_file() {
    local filepath="$1"
    if [ ! -f "$filepath" ]; then
        return
    fi

    local original_size=$(wc -c < "$filepath" | tr -d ' ')

    if [ "$MINIFIER" = "rjsmin" ]; then
        uv run python -c "
import rjsmin
with open('$filepath', 'r') as f:
    code = f.read()
minified = rjsmin.jsmin(code)
with open('$filepath', 'w') as f:
    f.write(minified)
"
    else
        uv run python -c "
import jsmin
with open('$filepath', 'r') as f:
    code = f.read()
minified = jsmin.jsmin(code)
with open('$filepath', 'w') as f:
    f.write(minified)
"
    fi

    local new_size=$(wc -c < "$filepath" | tr -d ' ')
    local savings=$((original_size - new_size))
    local percent=$((savings * 100 / original_size))

    echo "  $(basename "$filepath"): ${original_size}B → ${new_size}B (-${percent}%)"
}

for demo in "${HANDCRAFTED_DEMOS[@]}"; do
    demo_path="$ROSH_PORTAL/$demo"

    if [ ! -d "$demo_path" ]; then
        echo "⚠️  Skipping $demo (not found)"
        continue
    fi

    echo "📦 Minifying $demo..."

    for file in "${FILES_TO_MINIFY[@]}"; do
        minify_file "$demo_path/$file"
    done

    echo ""
done

echo "=== Done! ==="
echo ""
echo "Hand-crafted demos minified:"
for demo in "${HANDCRAFTED_DEMOS[@]}"; do
    if [ -d "$ROSH_PORTAL/$demo" ]; then
        echo "  $ROSH_PORTAL/$demo/"
    fi
done
