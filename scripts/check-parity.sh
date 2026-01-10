#!/bin/bash
# Check parity between JS and Python implementations
# Compares @parity tags in both files to find version mismatches

JS_FILE="static/rosh-runtime.js"
PY_FILE="src/rosh/interpreter.py"

echo "=== Rosh Parity Check ==="
echo ""

# Extract parity tags from both files
echo "JS parity tags ($JS_FILE):"
grep -n "@parity" "$JS_FILE" | sed 's/.*@parity/  @parity/' | sort

echo ""
echo "Python parity tags ($PY_FILE):"
grep -n "@parity" "$PY_FILE" | sed 's/.*@parity/  @parity/' | sort

echo ""
echo "=== Comparing versions ==="

# Extract just the tag names and versions for comparison
js_tags=$(grep -o "@parity [a-z_]* v[0-9]*" "$JS_FILE" | sort)
py_tags=$(grep -o "@parity [a-z_]* v[0-9]*" "$PY_FILE" | sort)

# Find tags only in JS
echo ""
echo "Tags only in JS:"
comm -23 <(echo "$js_tags") <(echo "$py_tags") | sed 's/^/  /' || echo "  (none)"

# Find tags only in Python
echo ""
echo "Tags only in Python:"
comm -13 <(echo "$js_tags") <(echo "$py_tags") | sed 's/^/  /' || echo "  (none)"

# Find matching tags
echo ""
echo "Matching tags (in sync):"
comm -12 <(echo "$js_tags") <(echo "$py_tags") | sed 's/^/  /' || echo "  (none)"

echo ""
echo "=== Summary ==="
js_count=$(echo "$js_tags" | grep -c "@parity" || echo 0)
py_count=$(echo "$py_tags" | grep -c "@parity" || echo 0)
matching=$(comm -12 <(echo "$js_tags") <(echo "$py_tags") | grep -c "@parity" || echo 0)

echo "JS tags: $js_count"
echo "Python tags: $py_count"
echo "In sync: $matching"

if [ "$js_count" -eq "$py_count" ] && [ "$matching" -eq "$js_count" ]; then
    echo ""
    echo "✅ All parity tags are in sync!"
    exit 0
else
    echo ""
    echo "⚠️  Some parity tags may be out of sync"
    exit 1
fi
