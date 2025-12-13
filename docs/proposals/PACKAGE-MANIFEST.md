# Rosh Package Manifest Specification

**Version:** 0.1.0
**Status:** Proposal (v0.0.8 milestone)
**Last Updated:** 2024-12-12

> Enable reproducible sharing, remixing, and distribution of Rosh games and modules

---

## Overview

The Rosh package manifest (`*.manifest.json`) provides a standard format for describing Rosh packages, games, and modules. This enables:

- **Reproducible installations** - Lock dependencies to specific versions
- **Integrity verification** - SHA256 checksums ensure files haven't been tampered with
- **Dependency management** - Declare what your game needs to run
- **Discoverability** - Metadata helps users find games
- **Remixing** - Clear licensing and attribution for community creations

## Manifest Format

### File Naming

- **Core packages:** `rosh.manifest.json`
- **Games/modules:** `<package-name>.manifest.json`
- **Location:** Root directory of the package

### Required Fields

```json
{
  "name": "string",           // Package name (lowercase, hyphens)
  "version": "semver",        // Semantic version (e.g., "1.2.3")
  "description": "string",    // One-line description
  "author": "string",         // Author name or organization
  "license": "string",        // SPDX license identifier
  "main": "path/to/file.rosh" // Entry point
}
```

### Optional Fields

```json
{
  "repository": "url",        // Source repository
  "homepage": "url",          // Project homepage
  "bugs": "url",              // Issue tracker

  "bin": {                    // Executable commands
    "command-name": "path/to/script.rosh"
  },

  "dependencies": {           // Runtime dependencies
    "package-name": "version-range"
  },

  "devDependencies": {        // Development dependencies
    "package-name": "version-range"
  },

  "roshVersion": "range",     // Required Rosh interpreter version

  "files": [                  // Files included in package
    "pattern/**/*.rosh"
  ],

  "checksums": {              // File integrity verification
    "algorithm": "sha256",
    "files": {
      "path/to/file.rosh": "hash"
    }
  },

  "metadata": {               // Game-specific metadata
    "genre": "string",
    "players": "string",
    "playtime": "string",
    "tags": ["array"]
  },

  "scripts": {                // Common commands
    "start": "command",
    "test": "command",
    "build": "command"
  }
}
```

## Version Ranges

Following npm/Cargo conventions:

- `"1.2.3"` - Exact version
- `"^1.2.3"` - Compatible with 1.2.3 (>=1.2.3, <2.0.0)
- `"~1.2.3"` - Approximately 1.2.3 (>=1.2.3, <1.3.0)
- `">=1.2.3"` - Greater than or equal
- `"*"` - Any version (not recommended for production)

## Checksums

SHA256 checksums verify file integrity during installation:

```json
{
  "checksums": {
    "algorithm": "sha256",
    "files": {
      "game.rosh": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "rooms/tavern.rosh": "...",
      "items/sword.rosh": "..."
    }
  }
}
```

### Generating Checksums

```bash
# Single file
sha256sum game.rosh

# All .rosh files
find . -name "*.rosh" -type f -exec sha256sum {} \;

# Future: rosh manifest generate-checksums
```

## Usage Examples

### Installing a Package

```bash
# Future syntax (v0.0.8+)
rosh install fantasy-adventure

# With specific version
rosh install fantasy-adventure@1.0.0

# From URL
rosh install https://example.com/packages/fantasy-adventure.tar.gz

# From local directory
rosh install ./my-game/
```

### Publishing a Package

```bash
# Future syntax (v0.0.8+)
rosh publish

# Dry run
rosh publish --dry-run

# With tag
rosh publish --tag beta
```

### Verifying Integrity

```bash
# Check all checksums match
rosh verify

# Verify specific package
rosh verify fantasy-adventure
```

## Example: Simple Game

```json
{
  "name": "hello-mud",
  "version": "1.0.0",
  "description": "A simple introductory MUD",
  "author": "tutorial-creator",
  "license": "MIT",
  "main": "hello.rosh",

  "roshVersion": ">=0.0.5",

  "files": [
    "hello.rosh",
    "README.md"
  ],

  "checksums": {
    "algorithm": "sha256",
    "files": {
      "hello.rosh": "abc123..."
    }
  },

  "scripts": {
    "start": "rosh hello.rosh"
  }
}
```

## Example: Complex Game with Dependencies

```json
{
  "name": "epic-quest",
  "version": "2.1.0",
  "description": "An epic multi-chapter adventure",
  "author": "game-studio",
  "license": "CC-BY-NC-4.0",
  "repository": "https://github.com/studio/epic-quest",

  "main": "quest.rosh",

  "dependencies": {
    "rosh-stdlib-mud": "^1.0.0",
    "combat-engine": "~3.2.0",
    "dialogue-trees": "^2.0.0",
    "inventory-system": "^1.5.0"
  },

  "roshVersion": ">=0.0.6",

  "files": [
    "quest.rosh",
    "chapters/**/*.rosh",
    "npcs/**/*.rosh",
    "items/**/*.rosh",
    "quests/**/*.rosh",
    "assets/**/*"
  ],

  "checksums": {
    "algorithm": "sha256",
    "files": {
      "quest.rosh": "...",
      "chapters/chapter1.rosh": "...",
      "chapters/chapter2.rosh": "..."
    }
  },

  "metadata": {
    "genre": "rpg",
    "players": "single-player",
    "playtime": "20-30 hours",
    "rating": "teen",
    "tags": ["fantasy", "epic", "story-driven", "choices-matter"]
  },

  "scripts": {
    "start": "rosh quest.rosh",
    "test": "rosh test/test-all.rosh",
    "chapter1": "rosh chapters/chapter1.rosh"
  }
}
```

## Security Considerations

### Current State (v0.0.5)

⚠️ **Trust-based only** - No signature verification yet

- Only install packages from sources you trust
- Checksums verify integrity but not authenticity
- No sandboxing of installed packages

### Future (v0.0.8+)

Planned security features:

1. **Package signing** - GPG/cryptographic signatures
2. **Author verification** - Trust chain from known authors
3. **Vulnerability scanning** - Check dependencies for known issues
4. **Sandboxing** - Isolated execution environments (see Milestone 9)
5. **Permission system** - Packages declare required permissions

```json
{
  "permissions": {
    "filesystem": ["read:./save-games/", "write:./save-games/"],
    "network": false,
    "ai": true
  },
  "signature": {
    "algorithm": "gpg",
    "key": "fingerprint",
    "signature": "base64-encoded-signature"
  }
}
```

## Registry

### Planned Registry Features (v0.0.8+)

- **Central registry** - `packages.rosh-lang.org` (placeholder)
- **Search and discovery** - Find games by genre, tags, rating
- **Version history** - Browse all versions of a package
- **Download statistics** - See popular packages
- **User ratings** - Community feedback

### Registry Operations

```bash
# Search for packages
rosh search fantasy

# Show package info
rosh info fantasy-adventure

# List installed packages
rosh list

# Update all packages
rosh update

# Remove package
rosh uninstall fantasy-adventure
```

## Manifest Generation

### Manual Creation

Copy template and fill in details:

```bash
cp examples/adventure-game.manifest.json my-game.manifest.json
# Edit my-game.manifest.json
```

### Future: Automated Generation

```bash
# Interactive manifest creator
rosh init

# Generate checksums for existing files
rosh manifest checksums

# Validate manifest
rosh manifest validate

# Bump version
rosh manifest version patch  # 1.0.0 -> 1.0.1
rosh manifest version minor  # 1.0.0 -> 1.1.0
rosh manifest version major  # 1.0.0 -> 2.0.0
```

## Implementation Roadmap

### v0.0.8 - Basic Package System

- [ ] Manifest parser and validator
- [ ] `rosh install <path>` - Local installation
- [ ] `rosh verify` - Checksum verification
- [ ] `rosh list` - Show installed packages
- [ ] Basic dependency resolution

### v0.0.9 - Package Registry

- [ ] Central package registry
- [ ] `rosh publish` - Upload packages
- [ ] `rosh search` - Find packages
- [ ] `rosh install <name>` - Install from registry
- [ ] Version conflict resolution

### v0.1.0 - Security & Multi-user

- [ ] Package signing and verification
- [ ] Permission system
- [ ] Sandboxed package execution
- [ ] Author reputation/trust system

## Related Documents

- [SECURITY-PLAN.md](SECURITY-PLAN.md) - Overall security strategy
- [PROJECT-PLAN.md](../../PROJECT-PLAN.md) - Milestone 8 details
- [EVAL-SAFETY.md](../EVAL-SAFETY.md) - Code execution safety

## References

- **npm:** https://docs.npmjs.com/cli/v9/configuring-npm/package-json
- **Cargo:** https://doc.rust-lang.org/cargo/reference/manifest.html
- **PyPI:** https://packaging.python.org/en/latest/specifications/
- **SPDX Licenses:** https://spdx.org/licenses/

---

**Status:** This is a proposal. Implementation planned for v0.0.8 (Milestone 8).
