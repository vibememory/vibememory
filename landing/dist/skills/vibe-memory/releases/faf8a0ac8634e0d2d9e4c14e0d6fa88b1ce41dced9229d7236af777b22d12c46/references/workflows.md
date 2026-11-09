# Authoring, checkpoints, and memory hygiene

## Authoring records that can be found again

Write conclusions, not diary entries. Put stable subjects and likely retrieval terms in `keywords`; keep identifiers, conditions, evidence, result, and next unresolved action in content.

- Project context — good: `Project Atlas uses PostgreSQL 16; repo atlas-api; migration 2026-11-08 UTC.` Keywords: `Project Atlas`, `PostgreSQL`, `atlas-api`, `migration`. Bad: `We discussed the database.`
- Decision — good: `Atlas chose PostgreSQL over Redis because restore operations and relational constraints are required; revisit above 80 ms p95 writes.` Bad: `Use Postgres.`
- Failure — good: `Redis prototype lost unflushed state in restore-2026-10-29; next test PostgreSQL PITR.` Bad: `Redis failed.`
- Checkpoint — good: `Goal | Done with evidence | Blocker | Next | branch/commit.` Bad: transcripts, raw logs, or unverified completion.
- Correction — good: state exactly what changed and link the new record to the expected old version using `SUPERSEDES` or `CORRECTS`, a reason, and `full` or `partial` scope. Never silently rewrite history. Bad: silently overwrite history or mark a partial correction as full.

For an important decision, correction, or handoff, optionally verify retrieval once with one exact/hybrid `recall` using 1–2 natural keywords, confirm ID/version, then stop. Do not add verification calls to every save, retry noisy queries, or treat rank as truth.

## Session checkpoints

Proactively maintain compact append-only checkpoints for active projects. Use stable project/repository name, `session checkpoint`, and specific topics as keywords; use source `agent-session` and tag `session-checkpoint`. Include goal, accepted decisions, verified work/evidence, blocker/current state, next action, and useful record/file IDs. For Git work include verified repo, branch, abbreviated commit, and whether uncommitted changes remain without copying files.

Recall the latest checkpoint before writing. Skip an equivalent state. Relate a newer checkpoint to the prior one with `SUPERSEDES`, expected version, reason, and `--correction-scope full`. If another record is only refined, use `partial`. Conflicts, cycles, and partial claims stay visible.

## Periodic memory hygiene prompt

At a natural checkpoint with a concrete signal—several changed entities/relations, orphans, duplicates, conflicts, obsolete records, a substantial milestone, or an aging graph—ask in the user's language: “Would you like me to refresh the relationship graph and optimize the memories now?” Korean: “관계 그래프를 최신화하고 기억을 한 번 최적화할까요?”

Use the latest `graph maintenance checkpoint` as freshness evidence. A practical default is to offer when that checkpoint is missing or older than 30 days **and** durable records or relationships changed after it. In a high-change workspace, several meaningful graph-relevant changes can justify an earlier offer. Time alone is not a maintenance signal for an inactive workspace, and a recent checkpoint with no later changes is fresh. Do not run broad reads merely to compute freshness: use the checkpoint found during normal recall, event/change evidence already available, and a bounded metadata-only audit only when needed.

Do not impose a once-per-session quota. In long work, ask again whenever later accumulated changes create a new maintenance signal. A decline or no reply applies only to that moment and is not a lasting preference; after further meaningful work, the agent may offer again. Avoid immediate repeated prompts and never interrupt active work. This prompt is separate from ordinary proactive recall and checkpointing, which continue without asking.

If accepted, inspect first with `maintenance-audit` and `graph-audit`, then use targeted `recall/get/graph`. Fetch only the candidates needed to decide; the audit contains metadata, not a server recommendation. Present exact record updates/merges/archives and preview `graph-diff` before `graph-apply`. Refresh means evidence-backed agent-authored repair. Optimize means confirmed deduplication, improved keywords, a canonical record, and recoverable archival—not server inference, blanket rewriting, or irreversible deletion. Require explicit authorization for `forget` or destructive expansion. Read [portability.md](portability.md) for the approval boundary.

After an accepted pass completes, save one compact `graph maintenance checkpoint` with the UTC completion time, inspected scope, audit counts, applied record/relation IDs, and unresolved items. Use stable keywords including the project or workspace name, `graph maintenance checkpoint`, and `relationship graph refresh`. Do not store raw audit output. This checkpoint is the freshness marker future agents should recall before offering again.
