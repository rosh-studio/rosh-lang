# Rosh Quick Start

Get up and running with Rosh in 2 minutes!

## Two Installation Modes

**Users (recommended):** Install globally with `uv tool install .` → Run as `rosh`
**Developers:** Use `uv sync` → Run as `uv run rosh` (editable mode)

---

## Install

```bash
# Install uv (modern Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and install Rosh
git clone https://github.com/rdubar/rosh.git
cd rosh
uv tool install .
```

**Upgrade to latest:**
```bash
cd rosh
git pull
uv tool install --reinstall .
```

## Run

```bash
# Interactive REPL
rosh

# Run a script
rosh examples/hello.rosh

# Run script then enter REPL with state preserved (v0.0.6 new!)
rosh -i examples/hello.rosh

# Run the manual (see all features)
rosh ROSH-MANUAL.rosh
```

## Try It

```rosh
# Create variables
create number x to 42
create string name to "Alice"

# Lists and iteration
create number scores to [95, 87, 92]
for score in scores then
    print score
end

# String methods
create string text to "hello,world,rosh"
create string parts to split text by ","
for part in parts then
    print uppercase of part
end

# String interpolation (v0.0.6 new!)
set name to "Alice"
set score to 100
print "Hello {name}, you have {score} points!"

# Type checking & list slicing (v0.0.6 new!)
set numbers to [10, 20, 30, 40, 50]
if call is_list numbers then
    set slice to numbers[1:3]  # Gets [20, 30]
    print slice
end

# Functions
define function greet name
    create string msg to "Hello, " plus name
    print msg
end

call greet "World"
```

## Development Setup

If you're developing Rosh (not just using it), use the editable install instead:

```bash
# Clone repo
git clone https://github.com/rdubar/rosh.git
cd rosh

# Install dependencies (creates .venv)
uv sync --all-extras

# Now use 'uv run' for development commands
```

## Test

```bash
# Run tests
uv run pytest tests/ -v

# Run specific tests
uv run pytest tests/test_list_iteration.py -v
```

## Develop

```bash
# Format code
uv run black src/

# Lint code
uv run ruff check src/

# All checks
uv run black src/ tests/ && \
uv run ruff check src/ tests/ && \
uv run pytest tests/ -v

# After changes, test with local version
uv run rosh your_test.rosh

# When ready, reinstall globally
uv tool install --reinstall .
```

## Common Commands

```bash
# Update dependencies
uv sync --upgrade

# Add dependency
uv add package-name

# Add dev dependency
uv add --dev package-name

# Run any Python command
uv run python script.py

# Show dependency tree
uv tree

# Check outdated packages
uv pip list --outdated
```

## Next Steps

- 📖 Read `ROSH-MANUAL.rosh` for full tutorial
- 🔧 See `docs/DEVELOPMENT.md` for detailed dev guide
- 🗺️ Check `PROJECT-PLAN.md` for roadmap
- 🧪 Browse `tests/` for examples

## Need Help?

- GitHub: https://github.com/rdubar/rosh
- Issues: https://github.com/rdubar/rosh/issues
- Docs: See `docs/` directory
