# Operations and recovery

`GET /v1/admin/metrics` is admin-authenticated and exposes only fixed-cardinality route templates, status classes, request counts, p50/p95/p99 latency and database-pool metadata. It never uses user IDs, keywords, filenames, tokens or Vault names as metric labels.

Backups must include PostgreSQL plus the byte-stream file volume. Run `scripts/backup_manifest.py BACKUP_DIR` after backup and `scripts/backup_manifest.py BACKUP_DIR --verify` before restore. Restore drills are opt-in and must target a disposable, empty deployment; confirm counts, sample content hashes, relation references and file hashes before recording success. Suggested objectives: RPO 24 hours and recovery-drill RTO 60 minutes, adjusted by the operator. Never run a restore test against production.
