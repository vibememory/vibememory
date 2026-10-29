# Security reporting

Do not put passwords, API keys, session cookies, personal memories, or production database dumps in public issues or pull requests.

For a suspected vulnerability, use GitHub's **Security → Report a vulnerability** flow if it is enabled on the repository. Otherwise contact the maintainers privately before publishing exploit details. This project does not currently provide a dedicated security email address or a guaranteed response SLA.

## Deployment model

- Run one API process against each embedded graph directory.
- Place remote deployments behind HTTPS and set `MEMORY_PUBLIC_ORIGIN` to the exact browser origin.
- Protect backups: they contain user records, password hashes, sessions, agent-key hashes, and uploaded originals.
- New agent keys are shown once; revoke a leaked key through the console.
- Sessions are HttpOnly and SameSite=Lax; Secure is enabled for HTTPS origins. Browser mutations require a matching Origin.
- Current signup uses email as an unverified login identifier. Email verification, password recovery, and social login are not implemented.

See the maintenance limitations in the README, including the archived Kuzu dependency. Review dependencies and your deployment requirements before operating a public multi-user instance.
