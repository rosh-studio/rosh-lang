# Contributing to Rosh

Thanks for your interest in contributing to Rosh.

## Licence

Rosh is released under the [Rosh Business Source License (Rosh-BSL)](LICENSE). By contributing, you agree that your contributions will be licensed under the same terms.

## Getting Started

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Setup

```bash
git clone https://github.com/rosh-studio/rosh-lang.git
cd rosh-lang
uv sync --all-extras
```

### Running Tests

```bash
uv run pytest -q
```

All tests must pass before submitting a pull request.

The standalone public repository also builds wheel and source-distribution
artifacts in CI to prevent local caches or generated files entering a release.

### Installing Locally

```bash
uv tool install --from . rosh-lang --force
```

Then run with `rosh`.

## What You Can Contribute

- **Bug reports** — open an issue with reproduction steps
- **Example programs** — new `.rosh` files in `examples/`
- **Widget improvements** — enhancements to existing widgets in `src/rosh_lang/library/`
- **Documentation** — improvements to README, inline comments, or examples
- **Test coverage** — new test cases for edge cases or uncovered paths
- **Editor support** — syntax and snippet updates in `editor/vscode/`

## What Requires Discussion First

- **New keywords** — language additions must be discussed and documented in the public syntax reference before implementation
- **New targets** — adding a new compilation target (e.g. Unity, Godot) is a significant change
- **Architecture changes** — changes to the parser, model, or code generation pipeline

Please open an issue to discuss before submitting a PR for these.

## Code Style

- Use `pathlib.Path` over `os.path`
- Use f-strings over `.format()` or `%`
- Use type hints
- Keep it simple — no over-engineering

## Commit Messages

```
type: Short description

Co-Authored-By: Your Name <your@email.com>
```

Types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`.

## Questions?

- Discord: https://discord.gg/gevBPucznD
- Email: info@rosh.cloud
