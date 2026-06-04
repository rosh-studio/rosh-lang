#!/bin/sh
set -eu

command -v code >/dev/null 2>&1 || {
  echo "VS Code command-line tool 'code' was not found." >&2
  exit 1
}

output="${TMPDIR:-/tmp}/rosh-vscode-0.8.0.vsix"
npx --yes @vscode/vsce package --out "$output"
code --install-extension "$output" --force
