# Development Guide

Guide for contributing to and developing Rosh.

## Setup with uv (Recommended)

[uv](https://github.com/astral-sh/uv) is a fast Python package manager from Astral (makers of Ruff).

### Install uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# With pip (if you must)
pip install uv
```

### Initial Setup

```bash
# Clone the repository
git clone https://github.com/rdubar/rosh.git
cd rosh

# Create virtual environment and install all dependencies (including dev and AI)
uv sync --all-extras

# Activate the virtual environment
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows
```

### Daily Workflow

```bash
# Sync dependencies (after pulling changes)
uv sync

# Add a new dependency
uv add package-name

# Add a dev dependency
uv add --dev package-name

# Update dependencies
uv sync --upgrade

# Run tests
uv run pytest tests/

# Run linting
uv run ruff check src/
uv run black --check src/

# Format code
uv run black src/
```

## Setup with pip (Traditional)

If you prefer traditional pip:

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Install package in development mode
pip install -e .

# Install with AI support
pip install -e ".[ai]"

# Install development tools
pip install -e ".[dev]"

# Install everything
pip install -e ".[ai,dev]"
```

## Running Tests

```bash
# With uv
uv run pytest tests/ -v

# With pip (after activating venv)
pytest tests/ -v

# Run specific test file
pytest tests/test_list_iteration.py -v

# Run with coverage
pytest tests/ --cov=src/rosh --cov-report=html

# Run only fast tests
pytest tests/ -m "not slow"
```

## Code Quality

### Linting with Ruff

```bash
# Check for issues
uv run ruff check src/ tests/

# Auto-fix issues
uv run ruff check --fix src/ tests/

# Check specific rules
uv run ruff check --select E,F src/
```

### Formatting with Black

```bash
# Check formatting
uv run black --check src/ tests/

# Format code
uv run black src/ tests/

# Format single file
uv run black src/rosh/interpreter.py
```

### Pre-commit Checks

Before committing:

```bash
# Format code
uv run black src/ tests/

# Check linting
uv run ruff check src/ tests/

# Run tests
uv run pytest tests/ -v

# Or use a single command
uv run black src/ tests/ && uv run ruff check src/ tests/ && uv run pytest tests/ -v
```

## Running Rosh

```bash
# With uv (runs from source)
uv run rosh

# With activated venv
rosh

# Run a script
uv run rosh examples/hello.rosh

# Run ROSH-MANUAL
uv run rosh ROSH-MANUAL.rosh
```

## Dependency Management

### Understanding the Files

- **`pyproject.toml`** - Project metadata and dependencies (source of truth)
- **`uv.lock`** - Exact versions of all dependencies (committed to git)
- **`.venv/`** - Virtual environment (not committed)

### Adding Dependencies

```bash
# Runtime dependency (goes in [project.dependencies])
uv add rich

# AI dependencies (goes in [project.optional-dependencies.ai])
uv add --extra ai anthropic

# Dev dependency (goes in [project.optional-dependencies.dev])
uv add --dev pytest-asyncio

# Check what would be installed
uv tree
```

### Updating Dependencies

```bash
# Update all to latest compatible versions
uv sync --upgrade

# Update specific package
uv add --upgrade package-name

# Check for outdated packages
uv pip list --outdated
```

### Lockfile Management

The `uv.lock` file should be committed to git. It ensures reproducible installs:

```bash
# Regenerate lockfile
uv sync

# Verify lockfile is up to date
uv sync --frozen

# Install exactly what's in lockfile (CI/production)
uv sync --frozen
```

## Project Structure

```
rosh/
├── src/rosh/              # Source code
│   ├── lexer.py           # Tokenization
│   ├── parser.py          # AST generation
│   ├── interpreter.py     # Execution engine
│   ├── ast_nodes.py       # AST definitions
│   └── cli.py             # Command-line interface
├── tests/                 # Test suite
│   ├── test_list_iteration.py
│   ├── test_string_methods.py
│   └── test_manual_extracts.py
├── examples/              # Example programs
├── docs/                  # Documentation
├── ROSH-MANUAL.rosh       # Language manual (executable)
├── pyproject.toml         # Project config
├── uv.lock                # Dependency lockfile
└── pytest.ini             # Test configuration
```

## Development Tips

### Fast Test Iteration

```bash
# Run specific test
uv run pytest tests/test_list_iteration.py::TestListIteration::test_iterate_number_list -v

# Run tests matching pattern
uv run pytest tests/ -k "string" -v

# Run with debug output
uv run pytest tests/ -v -s

# Run last failed tests
uv run pytest tests/ --lf
```

### Debugging

```bash
# Run with debugger
uv run pytest tests/test_file.py --pdb

# Add breakpoint in code
import pdb; pdb.set_trace()

# Or use built-in breakpoint()
breakpoint()
```

### Performance

```bash
# Profile test execution
uv run pytest tests/ --durations=10

# Run tests in parallel (with pytest-xdist)
uv add --dev pytest-xdist
uv run pytest tests/ -n auto
```

## Contributing Workflow

1. **Fork and clone** the repository

2. **Create a branch** for your feature
   ```bash
   git checkout -b feature/my-feature
   ```

3. **Set up development environment**
   ```bash
   uv sync --all-extras
   ```

4. **Make your changes**
   - Write code
   - Add tests
   - Update documentation

5. **Run quality checks**
   ```bash
   uv run black src/ tests/
   uv run ruff check src/ tests/
   uv run pytest tests/ -v
   ```

6. **Commit your changes**
   ```bash
   git add .
   git commit -m "Add feature: description"
   ```

7. **Push and create PR**
   ```bash
   git push origin feature/my-feature
   ```

## Continuous Integration

The CI pipeline runs on every push:

- ✅ Linting (ruff)
- ✅ Formatting check (black)
- ✅ Tests (pytest)
- ✅ Coverage report
- ✅ Package build test

### Local CI Simulation

Run the same checks locally before pushing:

```bash
#!/bin/bash
# ci-check.sh

set -e  # Exit on error

echo "🔍 Checking formatting..."
uv run black --check src/ tests/

echo "🔍 Linting..."
uv run ruff check src/ tests/

echo "🧪 Running tests..."
uv run pytest tests/ --cov=src/rosh --cov-report=term-missing

echo "📦 Testing package build..."
uv build

echo "✅ All checks passed!"
```

## Environment Variables

```bash
# OpenAI API key (for AI features)
export OPENAI_API_KEY=sk-...

# Anthropic API key (for AI features)
export ANTHROPIC_API_KEY=sk-ant-...

# Disable AI features
export ROSH_DISABLE_AI=1
```

## IDE Setup

### VS Code

Recommended extensions:
- Python (ms-python.python)
- Ruff (charliermarsh.ruff)
- Rosh Syntax Highlighting (if available)

Settings (`.vscode/settings.json`):
```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests/"],
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    }
  }
}
```

### PyCharm

1. Open project
2. File → Settings → Project → Python Interpreter
3. Select `.venv/bin/python`
4. Enable pytest as test runner

## Troubleshooting

### uv sync fails

```bash
# Clear cache and retry
rm -rf .venv uv.lock
uv sync --all-extras
```

### Tests fail locally but pass in CI

```bash
# Ensure clean environment
rm -rf .venv
uv sync --all-extras
uv run pytest tests/ -v
```

### Import errors

```bash
# Reinstall in editable mode
uv pip install -e .
```

### Permission denied on uv

```bash
# Fix uv permissions (Unix)
chmod +x ~/.local/bin/uv
```

## Resources

- **uv docs**: https://docs.astral.sh/uv/
- **pytest docs**: https://docs.pytest.org/
- **Ruff docs**: https://docs.astral.sh/ruff/
- **Black docs**: https://black.readthedocs.io/
