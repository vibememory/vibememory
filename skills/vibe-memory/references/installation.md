# Installation and verified distribution

The compatibility bootstrap separates public software distribution from the account service. On `https://vibememory.io` it reads the checksummed manifest from the official GitHub Release, downloads the exact released Rust binary for the OS/CPU into `VM_SKILL_DIR/bin`, and verifies SHA-256. An explicitly configured self-hosted `MEMORY_URL` uses that deployment's same-origin manifest. Software download does not prove login or Vault access.

Use `"$VM_CLI" check-update` once at the start of a new agent session. It is read-only and credential-free. If only Skill files changed, run `"$VM_CLI" sync`; if the native CLI changed, rerun `python3 "$VM_SKILL_DIR/scripts/memory.py" sync`. Review the reported distribution origin, perform only the indicated explicit action, reread `SKILL.md`, and reload only references needed by the active task. Normal data, login, message, and Vault commands contact only the configured service origin and never update software.

`sync` verifies the content-addressed manifest, every listed Skill/reference checksum, and all downloaded bytes before atomically replacing files. Never combine update traffic with account credentials or data payloads. `network-plan` reports command classes, methods, origins, authentication, and purpose without network access.

Current clients prefer `manifest-v2.json`, which lists the progressive Skill and every reference. The stable `manifest.json` GitHub release asset remains a two-file schema-v1 recovery bridge for pre-3.11 CLIs; self-hosted and hosted web origins select that bridge only for a legacy CLI or compatibility-bootstrap User-Agent. The bridge installs a checksum-pinned recovery `SKILL.md` and bootstrap, then the updated native CLI syncs v2. Do not remove the v1 asset until the documented legacy-support window ends.

If `scripts/memory.py` is absent, replace only the installed Vibe Memory Skill folder using `https://github.com/vibememory/vibememory/releases/latest/download/vibe-memory-skill.zip`. A Cloudflare `1010` on the vanity URL means client-signature policy rejected the request before Vibe Memory; use the official GitHub release asset, not spoofed headers, disabled TLS, or weakened site security.

After bootstrap, use the absolute CLI path. Ask for command detail only when required with `"$VM_CLI" COMMAND --help` or `template TYPE`. The CLI emits compact JSON by default; `--pretty` is only for human debugging.
