# Rosh Installation Guide

**Current Version:** v0.0.7

## Quick Install (from rosh-lang directory)

### Option 1: Editable Install (Recommended for Development)
```bash
cd /path/to/rosh/rosh-lang
pip install -e .
```

This installs in "editable" mode - changes to the code take effect immediately without reinstalling.

### Option 2: Regular Install
```bash
cd /path/to/rosh/rosh-lang
pip install .
```

### Option 3: From Parent Directory
```bash
cd /path/to/rosh
pip install -e rosh-lang/
```

## Verify Installation

```bash
# Check version
rosh --version
# Should output: Rosh 0.0.7

# Run a simple test
rosh examples/test-events-simple.rosh

# Run the complete manual
rosh ROSH-MANUAL.rosh
```

## Troubleshooting

### "ModuleNotFoundError: No module named 'rosh'"

**Problem:** Old installation pointing to wrong directory

**Solution:**
```bash
# Uninstall old version
pip uninstall rosh -y

# Navigate to rosh-lang directory
cd /path/to/rosh/rosh-lang

# Reinstall
pip install -e .
```

### "rosh: command not found"

**Problem:** Package not in PATH

**Solution:**
```bash
# Check if Python scripts directory is in PATH
python -m site --user-base

# On macOS/Linux, add to ~/.bashrc or ~/.zshrc:
export PATH="$HOME/.local/bin:$PATH"

# Or use python -m to run:
python -m rosh examples/test-events-simple.rosh
```

### Version shows 0.0.6 instead of 0.0.7

**Problem:** Cached installation or stale files

**Solution:**
```bash
# Clear pip cache and reinstall
pip cache purge
pip uninstall rosh -y
pip install -e .

# Verify
rosh --version
```

## Development Setup

For active development with hot-reload:

```bash
cd /path/to/rosh/rosh-lang

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Install optional AI dependencies (if needed)
pip install -e ".[ai]"

# Run tests
pytest tests/

# Run a specific test
pytest tests/test_events.py -v
```

## Directory Structure

```
rosh/
├── rosh-lang/              ← Install from HERE
│   ├── src/rosh/           ← Python package
│   ├── examples/           ← Example programs
│   ├── tests/              ← Test suite
│   ├── pyproject.toml      ← Package config
│   └── README.md
├── rosh-corporate/         ← Private (not for install)
├── rosh.cloud/             ← Future (placeholder)
└── roshbosh/               ← Future (placeholder)
```

## Updating After Changes

After making code changes:

**If installed with `-e` (editable):**
- Changes take effect immediately
- No need to reinstall
- Just run `rosh` again

**If installed without `-e`:**
```bash
pip install --upgrade --force-reinstall .
```

## Uninstall

```bash
pip uninstall rosh
```

## Version Information

The version is set in two places (keep them in sync):
- `src/rosh/__init__.py` - Runtime version
- `pyproject.toml` - Package metadata version

Current: **v0.0.7** (Event System Release)

## Platform-Specific Notes

### macOS
```bash
# If using Homebrew Python
/usr/local/bin/python3 -m pip install -e .

# If using pyenv
~/.pyenv/versions/3.14.0/bin/python -m pip install -e .
```

### Linux
```bash
# Use pip3 if pip points to Python 2
pip3 install -e .
```

### Windows
```powershell
# Use py launcher
py -m pip install -e .
```

## Requirements

- **Python:** 3.10 or higher
- **Dependencies:**
  - rich >= 13.0.0 (for colored output)
  - Optional: openai, anthropic (for AI features)

## Post-Install Testing

Run the complete test suite to verify everything works:

```bash
# Quick validation (30 seconds)
rosh examples/test-events-simple.rosh

# Full feature test (2 minutes)
rosh ROSH-MANUAL.rosh

# Event system demo (2 minutes)
rosh examples/dungeon-events-demo.rosh

# Unit tests (5 seconds)
pytest tests/ -v
```

All tests should pass (123/123).

## Getting Help

- **Documentation:** See `ROSH-MANUAL.rosh`
- **Examples:** See `examples/` directory
- **Event System Guide:** See `examples/README-EVENTS.md`
- **Issues:** Report at https://github.com/rdubar/rosh/issues

---

**Installation complete!** Try: `rosh examples/test-events-simple.rosh` 🎮✨
