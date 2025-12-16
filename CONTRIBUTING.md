# Contributing to Rosh

> **Note:** This guide will be expanded before public release.

## Why Rosh matters (plain English)
Rosh lets you say what you want to see and watch it change live. One script can become a web game, a desktop game, or a 3D scene without rewriting it. The aim is to make computers do the heavy lifting so anyone can experiment quickly and show ideas immediately.

## Getting Started

1. Clone the repository
2. Install dependencies: `uv sync`
3. Run tests: `uv run pytest`

## Development

### Running Rosh

```bash
# Run a .rosh file
rosh examples/hello.rosh

# Build for a target platform
rosh build game.rosh --target phaser --output dist/
```

### Testing Changes

```bash
# Run all tests
uv run pytest

# Run specific test
uv run pytest tests/test_parser.py -v
```

## Commit Messages

Format: `type: description`

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `refactor:` Code restructuring
- `test:` Test changes

## Reporting Issues

Please include:
- Rosh version (`rosh --version`)
- Minimal `.rosh` code to reproduce
- Expected vs actual behavior
- Target platform if applicable (Phaser/Pygame/Three.js)

## Code Style

- Python code follows standard conventions
- Use type hints where practical
- Keep transpiler outputs readable

---

*More detailed contribution guidelines coming soon.*
