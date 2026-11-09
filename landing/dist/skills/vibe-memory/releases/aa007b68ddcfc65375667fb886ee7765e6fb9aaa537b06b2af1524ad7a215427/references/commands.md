# Native CLI command map

Use the absolute `VM_CLI` path. Ask `COMMAND --help` or `template TYPE` only when needed.

- Connection/distribution: `status`, `login`, `logout`, `network-plan`, `check-update`, `sync`
- Retrieval: `recall`, `get`, `list`, `graph`, `relations`, `context-bundle`, `events`, `watch`, `quarantine`, `trash`
- Creation: `remember`, `entity`, `document`, `upload`, `relate`, `from-json`
- Versioned maintenance: `keywords`, `update`, `security`, `archive`, `restore`, `merge`, `relation-status`, `relation-scope`; `forget` only with explicit irreversible authority
- Deterministic graph repair: `graph-audit`, `template graph-diff`, `graph-diff`, `template graph-apply`, `graph-apply`
- Memory maintenance: `maintenance-audit`; fetch selected candidates, then use versioned `update`, `merge`, `archive`, and graph diff/apply only after approval
- Agent Memory Repo: `agent-memory-export OUTPUT`, `template agent-memory-diff`, `agent-memory-diff FILE`, `template agent-memory-apply`, `agent-memory-apply FILE`
- Collaboration: `agents`, direct `message send|inbox|sent|get|ack|watch`, persistent `room create|list|get|update|invite|remove|messages|send|read|watch`
- Vault: `vault list|capture|exec`
- Product requests: `feedback`, `feedback-list`, `feedback-get`; operator-only `feedback-admin-list`, `feedback-admin-update`

For structured writes, inspect `template memory|entity|document|relation|feedback|context-bundle|graph-diff|graph-apply`, prepare JSON in a private temporary file, then use `from-json` or the command-specific file argument. Use `--metadata '@file.json'` and `--provenance '@file.json'` when appropriate. The CLI owns endpoint paths, authentication, raw byte upload, bounded retries, field names, and compact output.
