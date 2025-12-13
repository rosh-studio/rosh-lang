#!/bin/bash
# Install Rosh VS Code extension

EXTENSION_DIR="$HOME/.vscode/extensions/rosh-0.1.0"

echo "Installing Rosh VS Code extension..."

# Create extension directory
mkdir -p "$EXTENSION_DIR"

# Copy extension files
cp -r "$(dirname "$0")"/* "$EXTENSION_DIR/"

echo "✓ Extension installed to $EXTENSION_DIR"
echo ""
echo "Next steps:"
echo "1. Reload VS Code (Cmd+Shift+P > 'Reload Window')"
echo "2. Open any .rosh file"
echo "3. Enjoy syntax highlighting and snippets!"
