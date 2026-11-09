# Installation and verified distribution

The compatibility bootstrap separates public software distribution from the account service. On `https://vibememory.io` it reads the checksummed manifest from the official GitHub Release, downloads the exact released Rust binary for the OS/CPU into `VM_SKILL_DIR/bin`, and verifies SHA-256. An explicitly configured self-hosted `MEMORY_URL` uses that deployment's same-origin manifest. Software download does not prove login or Vault access.

Use `"$VM_CLI" check-update` once at the start of a new agent session. It is read-only and credential-free. If only Skill files changed, run `"$VM_CLI" sync`; if the native CLI changed, rerun `python3 "$VM_SKILL_DIR/scripts/memory.py" sync`. Review the reported distribution origin, perform only the indicated explicit action, reread `SKILL.md`, and reload only references needed by the active task. Normal data, login, message, and Vault commands contact only the configured service origin and never update software.

`sync` verifies the content-addressed manifest, every listed Skill/reference checksum, and all downloaded bytes before atomically replacing files. Never combine update traffic with account credentials or data payloads. `network-plan` reports command classes, methods, origins, authentication, and purpose without network access.

Current clients prefer `manifest-v2.json`, which lists the progressive Skill and every reference. The stable `manifest.json` GitHub release asset remains a two-file schema-v1 recovery bridge for pre-3.11 CLIs; self-hosted and hosted web origins select that bridge only for a legacy CLI or compatibility-bootstrap User-Agent. The bridge installs a checksum-pinned recovery `SKILL.md` and bootstrap, then the updated native CLI syncs v2. Do not remove the v1 asset until the documented legacy-support window ends.

If `scripts/memory.py` is absent, replace only the installed Vibe Memory Skill folder using `https://github.com/vibememory/vibememory/releases/latest/download/vibe-memory-skill.zip`. A Cloudflare `1010` on the vanity URL means client-signature policy rejected the request before Vibe Memory; use the official GitHub release asset, not spoofed headers, disabled TLS, or weakened site security.

After bootstrap, use the absolute CLI path. Ask for command detail only when required with `"$VM_CLI" COMMAND --help` or `template TYPE`. The CLI emits compact JSON by default; `--pretty` is only for human debugging.

## Failure reporting for browser login and setup

When connection is requested, execute the flow instead of merely reciting commands: bootstrap only if the binary is missing, run `status`, and if disconnected run `login --approval-timeout 600 --name "AGENT NAME"`. `login` attempts to open the default browser. `--no-browser` explicitly disables that behavior; use it only when browser launch is unavailable, then give the user the exact CLI-issued approval URL and code. Never invent a device URL or ask for credentials in chat.

Do not collapse a failed flow into “installation failed” or “network access is blocked.” Report a concise causal breakdown in the user's language:

- **Failed stage:** Skill installation, CLI bootstrap/update, status, login-link issuance, browser launch, user approval, token exchange, or permission check.
- **Evidence:** the sanitized tool error, structured reason code, or blocked origin actually observed. Do not expose credentials, tokens, cookies, or Vault values.
- **Cause:** `confirmed` only when the evidence identifies it; otherwise `likely` with the supporting evidence or `unknown`. Never present inference as a confirmed root cause.
- **Completed / not completed / not attempted:** distinguish installed Skill files from a downloaded CLI, issued approval link, approved connection, and granted permission. A bootstrap failure means login and browser approval were not attempted.
- **Next action:** the smallest concrete user or environment action, including the exact non-secret origin or permission when known. Do not claim a retry will work unless the blocker changed.

For a distribution failure, identify distribution egress separately from account-service access. Official bootstrap uses `github.com` and may redirect to `release-assets.githubusercontent.com` or `objects.githubusercontent.com`; later login uses `https://vibememory.io`. If the native CLI exists, `network-plan` provides this separation without network access. If the host tool reports only a generic sandbox denial, say that the exact blocked hostname is unknown rather than guessing it.
