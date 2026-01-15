# Contributing to Rosh

Thank you for your interest in contributing to Rosh.

## Why Rosh Matters

Rosh lets you say what you want to see and watch it change live. One script can become a web game, a desktop game, or a 3D scene without rewriting it. The aim is to make computers do the heavy lifting so anyone can experiment quickly and show ideas immediately.

## Ways to Contribute

### For Academics and Researchers

- Test Rosh in educational settings and share feedback
- Report usability issues from student perspectives
- Suggest features that would benefit teaching
- Publish research using Rosh (see LICENSE for attribution)

### For Developers

- Report bugs with reproducible examples
- Submit pull requests for bug fixes
- Improve documentation
- Add tests for uncovered functionality

## Getting Started

```bash
# Clone the repository
git clone https://github.com/roshcloud/rosh-lang.git
cd rosh-lang

# Install dependencies
uv sync --all-extras

# Run tests to verify setup
uv run pytest
```

## Development Workflow

### Running Rosh

```bash
# Run a .rosh file
uv run rosh examples/hello.rosh

# Interactive REPL
uv run rosh

# Build for a target platform
uv run rosh build game.rosh --target phaser --output dist/
```

### Testing Changes

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_parser.py -v

# Run tests with coverage
uv run pytest --cov=src/rosh
```

### Code Quality

```bash
# Format code
uv run black src/ tests/

# Lint code
uv run ruff check src/ tests/

# Run all checks before committing
uv run black src/ tests/ && uv run ruff check src/ tests/ && uv run pytest
```

## Commit Message Format

Use conventional commit format: `type: description`

| Type | Purpose |
|------|---------|
| `feat:` | New feature |
| `fix:` | Bug fix |
| `docs:` | Documentation only |
| `refactor:` | Code restructuring (no behavior change) |
| `test:` | Adding or updating tests |
| `chore:` | Build, tooling, or maintenance |

Examples:
- `feat: Add sprite animation support to Pygame emitter`
- `fix: Correct variable scoping in nested loops`
- `docs: Update installation instructions for Windows`

## Reporting Issues

When reporting bugs, please include:

1. **Rosh version:** Run `rosh --version`
2. **Minimal code:** Smallest `.rosh` file that reproduces the issue
3. **Expected behavior:** What you expected to happen
4. **Actual behavior:** What actually happened
5. **Target platform:** If applicable (Phaser/Pygame/Three.js/Godot)
6. **Environment:** OS, Python version

## Pull Request Process

1. Fork the repository and create a feature branch
2. Write tests for your changes
3. Ensure all tests pass (`uv run pytest`)
4. Update documentation if needed
5. Submit PR with clear description of changes

### PR Checklist

- [ ] Tests added/updated
- [ ] Documentation updated (if applicable)
- [ ] Code formatted with Black
- [ ] Linting passes with Ruff
- [ ] Commit messages follow conventions

## Code Style

- Follow PEP 8 for Python code
- Use type hints where practical
- Keep transpiler outputs readable (developers will debug them)
- Prefer clarity over cleverness
- Comment complex logic, but let clear code speak for itself

## Project Structure

```
rosh-lang/
├── src/rosh/           # Core interpreter
│   ├── lexer.py        # Tokenization
│   ├── parser.py       # AST generation
│   ├── interpreter.py  # Execution engine
│   └── emitters/       # Target transpilers
├── tests/              # Test suite
├── examples/           # Learning examples
├── demos/              # Full demo projects
└── docs/               # Documentation
```

## Questions?

- Check existing issues before opening a new one
- For general questions, open a discussion
- For security issues, see [SECURITY.md](SECURITY.md)

## License

By contributing, you agree that your contributions will be licensed under the same terms as the project. See [LICENSE](LICENSE) for details.
