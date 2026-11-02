# Vault

Vault values are encrypted service credentials, not memory. Use them only when stored by the user in the console, the current exact connection has Vault permission, the named entry is explicitly granted, and the active task requires it. `status` reports `vault_access`; if false, link to the configured service `/console` and ask the user to enable permission or reconnect with `login --vault-access`. Never request a secret in chat.

`vault list` returns names/descriptions, never values. When an entry is absent, use `vault capture ENTRY --description "WHY" --expires-in 300`; show the owner-bound, one-use, expiring `capture_url` and explain requester/replacement. Wait for the user to submit it, then confirm with `vault list`. Never open or submit the capture form for them.

Use `vault exec --env VARIABLE=ENTRY -- PROGRAM...` to inject minimum selected entries into exactly one trusted child process. Do not persist values in shell variables, `.env`, arguments, memory, messages, or logs. Never run `env`, `printenv`, shell tracing, debug dumps, or wrappers likely to expose the child environment. The CLI intentionally cannot print a Vault value; do not bypass it with HTTP. If capture cannot complete, stop the credential-dependent action.

