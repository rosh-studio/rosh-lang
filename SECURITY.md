# Security

Please do not open public issues for suspected security vulnerabilities.

Report vulnerabilities privately to **info@rosh.cloud** with:

- the affected version and component
- reproduction steps or proof of concept
- the likely impact
- any suggested mitigation

Rosh stores cloud API keys in `~/.rosh/config.json` with user-only permissions.
Keep provider credentials in environment variables and never commit them to
`.rosh` files or repositories.
