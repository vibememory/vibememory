# Security reporting

Do not put passwords, API keys, session cookies, personal memories, or production database dumps in public issues or pull requests.

For a suspected vulnerability, use GitHub's **Security → Report a vulnerability** flow if it is enabled on the repository. Otherwise contact the maintainers privately before publishing exploit details. This project does not currently provide a dedicated security email address or a guaranteed response SLA.

## Deployment model

- Keep PostgreSQL private to the application network, use a unique strong database password, and restrict database backups as sensitive data.
- Place remote deployments behind HTTPS and set `MEMORY_PUBLIC_ORIGIN` to the exact browser origin.
- Protect both PostgreSQL dumps and the app data volume: together they contain user records, password hashes, sessions, agent-key hashes, Vault material, and uploaded originals.
- New agent keys are shown once; revoke a leaked key through the console.
- Remote MCP uses OAuth 2.1 authorization code + S256 PKCE. Codes, access tokens, and rotating refresh tokens are stored only as hashes and can be revoked per connected client in the console.
- Vault access is a separate per-agent permission. Grant it only to agents trusted with every stored Vault value.
- Vault values use AES-256-GCM authenticated encryption. The server-generated `vault.key` is mode 0600 and must remain persistent; losing it loses the values.
- A default `/data` backup contains both Vault ciphertext and its decryption key and must be protected as plaintext-equivalent. Configure `MEMORY_VAULT_KEY_FILE` outside the data backup when operational separation is required.
- `vault exec` avoids printing values but cannot prevent the launched child process from logging or exfiltrating its environment.
- Sessions are HttpOnly and SameSite=Lax; Secure is enabled for HTTPS origins. Browser mutations require a matching Origin.
- Current signup uses email as an unverified login identifier. Email verification, password recovery, and social login are not implemented.

Kuzu is a legacy migration reader, not the production store. Review dependencies and your deployment requirements before operating a public multi-user instance.
