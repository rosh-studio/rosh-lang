# Contributing to Rosh

**Status:** Internal development only
**When public:** Contributions welcome after v0.1.0

---

## 🏗 Language Design Principles

1. **Spoken-first** - Optimize for dictation
2. **Natural English** - Sounds like talking to a person
3. **Minimal punctuation** - Voice-friendly
4. **AI-native** - `prompt` command as first-class citizen
5. **Educational** - Teaching programming through storytelling

---

## 📝 Feature Addition Rules

Every new feature must:

1. ✅ Be documented in `ROSH-MANUAL.rosh`
2. ✅ Have natural language syntax
3. ✅ Work with voice input
4. ✅ Include help documentation
5. ✅ Pass all tests after addition

**After each update:**
- Run all tests (manual + unit tests)
- Update `ROSH-MANUAL.rosh` with examples
- Update command help text in interpreter
- Update `CHANGELOG.md`
- Verify nothing broke

---

## 🧪 Testing Policy

### Test File Organization
- **scratches/** - Temporary testing during development
- Never commit test files to root directory
- Test file patterns: `test_*.rosh`, `demo_*.rosh`, `scratch_*.rosh`
- Use `trash` CLI for cleanup (not `rm`)

### After Feature Documentation
1. Verify feature added to `ROSH-MANUAL.rosh`
2. Run `rosh ROSH-MANUAL.rosh` successfully
3. Trash all scratch files: `trash scratches/*.rosh`
4. Commit only documented feature

### Test Suite
- `ROSH-MANUAL.rosh` IS the integration test suite
- Unit tests in `tests/` directory (pytest)
- All tests must pass before merge
- Target: 100+ automated tests by v1.0

---

## 📦 Version Numbering

**Semantic Versioning (v0.x.y)**
- `v0.x.0` - Major feature additions (milestones)
- `v0.0.y` - Minor features, bug fixes
- `v1.0.0` - Production-ready, stable syntax
- `v2.0.0` - Major architectural changes (e.g., Rust core)

---

## 🔤 Naming Conventions

### Project Names
- **Rosh** - Always capitalize (proper noun)
- **rosh** - Lowercase only in code/commands (`rosh compile`)
- **ROSH-MANUAL.rosh** - All caps for emphasis (file name)

### Technology Names
- **JavaScript** (not Javascript, JS in casual context)
- **TypeScript** (not Typescript)
- **VS Code** (not VSCode)
- **GitHub** (not Github)

### File Extensions
- `.rosh` - Rosh source files
- `.md` - Markdown documentation
- `.json` - Configuration files

### Command Naming
- Use natural language: `create`, `set`, `print`
- Avoid abbreviations unless standard: `props` (properties)
- Aliases documented clearly: `exit` = `stop`

---

## 🔀 Git Workflow

### Branch Strategy
- **main** - Stable, tagged releases
- Feature branches: `feature/event-system`
- Hotfix branches: `hotfix/parser-bug`

### Commit Messages
Follow conventional commits:
```
feat: Add event system (when/trigger syntax)
fix: Parser error on nested if statements
docs: Update ROSH-MANUAL with Section 28
test: Add tests for list slicing
chore: Clean up test files
```

### Pull Requests
- One feature per PR
- Include tests and documentation
- Update `CHANGELOG.md`
- Ensure `ROSH-MANUAL.rosh` runs successfully

---

## 🚀 Release Process

1. Update version in `pyproject.toml`
2. Run `rosh ROSH-MANUAL.rosh` successfully
3. Run all unit tests: `pytest`
4. Update `CHANGELOG.md` with release notes
5. Tag release: `git tag v0.0.X`
6. Push tag: `git push --tags`
7. Update `ROADMAP.md` status

---

## 📊 Documentation Standards

### Markdown Style
- Use GitHub-flavored Markdown
- Headers: `#` for H1, `##` for H2, etc.
- Code blocks: Triple backticks with language
- Links: Descriptive text, not raw URLs
- Lists: `-` for unordered, `1.` for ordered

### Code Examples
- Always include working examples
- Show input and expected output
- Use realistic scenarios (MUD/game contexts)
- Test examples before publishing

### Date Format
- ISO 8601: YYYY-MM-DD (2025-12-13)
- Consistency across all documents

---

## 🔐 Security

**Current Status (v0.0.x):**
- ⚠️ Single-user, local development only
- No sandboxing yet
- Full filesystem access
- AI code requires confirmation but runs unrestricted

**Before Multi-User (v0.1.0) MUST implement:**
1. Complete sandboxing for all code execution
2. User space isolation
3. Code verification (hash/signature)
4. Professional security audit
5. Safe mode by default

---

## 🏃 Development Setup

See `docs/DEVELOPMENT.md` for complete setup instructions.

**Quick Start:**
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and setup
git clone <repo>
cd rosh-lang
uv sync

# Run tests
uv run pytest
uv run rosh ROSH-MANUAL.rosh
```

---

## 💡 Getting Help

- **Technical questions:** Check `ROSH-MANUAL.rosh`
- **Setup issues:** See `docs/DEVELOPMENT.md`
- **Feature proposals:** Create issue with proposal template
- **Bug reports:** Create issue with reproduction steps

---

## 📄 License

MIT License - See `LICENSE` file for details.

Free for commercial use. Modify and distribute freely.

---

*For complete project policies including business strategy, see `../rosh-corporate/docs/POLICIES.md` (private repo only)*
