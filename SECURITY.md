# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.2.x   | Yes       |
| < 0.2   | No        |

## Reporting a Vulnerability

If you discover a security vulnerability in Rosh, please report it responsibly:

**Email:** security@rosh.cloud

Please include:

1. Description of the vulnerability
2. Steps to reproduce
3. Potential impact
4. Any suggested fixes (optional)

### What to Expect

- **Acknowledgment:** Within 48 hours
- **Initial Assessment:** Within 1 week
- **Resolution Timeline:** Depends on severity, typically 2-4 weeks

We will keep you informed of progress and credit you in any security advisory (unless you prefer anonymity).

## Security Model

### Current Limitations

Rosh is in active development. The following security features are **not yet implemented**:

| Feature | Status | Notes |
|---------|--------|-------|
| Code sandboxing | Planned | User code runs with interpreter privileges |
| Input sanitization | Partial | Basic checks, not comprehensive |
| Network isolation | Planned | WebSocket connections are trusted |
| File system restrictions | Planned | Scripts can access local files |

### Safe Usage Guidelines

**Do:**
- Run only trusted Rosh scripts
- Use Rosh in controlled environments (development, education)
- Review scripts before running them

**Don't:**
- Run untrusted scripts from the internet
- Expose Rosh interpreters to public networks
- Use Rosh for production systems handling sensitive data

### AI Integration

Rosh supports optional AI features (voice commands, code generation). When using AI:

- API keys are stored locally in `~/.rosh/config.json`
- Keys are never logged or transmitted except to the configured AI provider
- AI-generated code should be reviewed before execution
- See [EVAL-SAFETY.md](docs/EVAL-SAFETY.md) for details

### Multi-User Features

Project Twin (multiplayer features) uses WebSocket connections:

- Connections are currently trusted (no authentication)
- Suitable for demos and controlled environments
- Not suitable for public-facing deployments
- Authentication planned for future releases

## Responsible Disclosure

We follow responsible disclosure practices:

1. Report vulnerabilities privately
2. Allow reasonable time for fixes
3. Coordinate public disclosure

We will not take legal action against researchers who:
- Act in good faith
- Avoid privacy violations
- Do not exploit vulnerabilities beyond proof-of-concept

## Security Roadmap

Planned security enhancements:

- [ ] Sandboxed code execution
- [ ] File system access controls
- [ ] Network permission model
- [ ] WebSocket authentication
- [ ] Rate limiting for AI features

---

*For general questions, see [CONTRIBUTING.md](CONTRIBUTING.md)*
*For licensing, see [LICENSE](LICENSE)*
