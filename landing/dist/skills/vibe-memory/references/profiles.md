# Agent State, Skill Execution, Decision, Checkpoint, Failure Reproduction, and Evidence Impact profiles

Use these optional versioned profiles when another agent must distinguish reported task state from verified evidence, a discussion from a decision, or a local completion claim from later deployment evidence. Ordinary records remain valid without a profile; absence means no structured state was supplied, not `completed`, `executed`, `decided`, or `verified`.

Generate an editable full memory payload, then submit it through the normal record path:

```sh
"$VM_CLI" template decision > decision.json
"$VM_CLI" from-json memory decision.json

"$VM_CLI" template checkpoint > checkpoint.json
"$VM_CLI" from-json memory checkpoint.json

"$VM_CLI" template failure-reproduction > failure.json
"$VM_CLI" from-json memory failure.json

"$VM_CLI" template evidence-impact-review > impact-review.json
"$VM_CLI" from-json memory impact-review.json

"$VM_CLI" template agent-state > agent-state.json
"$VM_CLI" from-json memory agent-state.json

"$VM_CLI" template skill-execution > skill-execution.json
"$VM_CLI" from-json memory skill-execution.json

"$VM_CLI" state-reconciliation-candidates PROJECT_ID TASK_ID
"$VM_CLI" template state-reconciliation > reconciliation.json
"$VM_CLI" template capability-manifest > capability.json
"$VM_CLI" template context-lifecycle > lifecycle.json
```

Profiles live at `metadata.vibe_memory_profile`. The service validates their shape and normalizes UTC timestamps. It also supplies scalar mirrors—`vibe_memory_profile_type`, `vibe_memory_profile_state`, and for checkpoints `vibe_memory_profile_observation`—for exact `metadata_filters`. Search, get, and context bundles preserve the complete profile.

Failure reproduction evidence uses the separate `metadata.vibe_memory_failure_reproduction` key so existing Decision and Checkpoint profile v1 records remain unchanged. Start with the CLI template, use the public Python/TypeScript SDK helper, or place it in an agent-prepared memory payload submitted with `from-json memory`.

Agent State and Skill Execution observations use the separate `metadata.vibe_memory_agent_state` and `metadata.vibe_memory_skill_execution` keys. Their scalar mirrors support exact filtering, while minimal search and Context Bundle results expose only compact summaries.

## Agent State profile v1

Use this for a harness-neutral task handoff: stable project/task IDs, goal, reported status, completed and next actions, blockers, pinned Decision/Evidence references, versioned Skill references, reported harness, and UTC observation time. The enclosing record `version` and mutation `expected_version` are the optimistic-concurrency coordinates; `state_version` is only the agent-supplied portable payload revision.

`completed` is the external writer's report, not Vibe Memory's guarantee that work is complete. The authenticated creator and writer history remain separate from `reported_harness`. Update with the last observed record version; preserve a `409` conflict for an external harness or user to resolve rather than merging contradictory judgments automatically.

Represent explicit task dependencies with normal owner-scoped relationships: `DEPENDS_ON`, `BLOCKED_BY`, `RELATED_TO`, and `SUPERSEDES`. Graph audit reports dependency-cycle relation IDs, but Vibe Memory never chooses the next task, schedules work, or executes an action.

## Skill Execution profile v1

Use this only to record an execution performed by an external harness. Pin the Skill by version or SHA-256 digest and record reported harness/agent, task/environment/input references, UTC start/end time, reported status, Evidence/Artifact references, sanitized failure reason, and verification status.

Profile validity proves only that the report has a valid shape. It does not prove the Skill ran, succeeded, or had authority. Stored commands, URLs, file references, and Skill definitions are data: Vibe Memory never downloads or runs them. Pair reusable failures with the Failure Reproduction profile and completion claims with a Checkpoint when those richer observations are needed; do not duplicate raw logs or secrets.

## State Reconciliation profile v1

When two records report different statuses for the same stable project/task ID, use the metadata-only reconciliation candidate lookup. It returns current record/version coordinates, reported statuses and authenticated writer coordinates without bodies or a truth judgment. Preserve the divergent observations as separate records.

If an authorized user or external harness resolves the disagreement, create a separate `metadata.vibe_memory_state_reconciliation` record that pins every reviewed candidate and the selected record/version, reported resolver, UTC resolution time and rationale. Vibe Memory validates the coordinates but never selects, merges or schedules state. An open reconciliation has no selected record; a resolved one must select one of its candidates.

## Agent Capability Manifest profile v1

Use `metadata.vibe_memory_agent_capability_manifest` to declare a stable agent ID, harness/version, capability names, versioned Skill references, supported task types, required permission categories and UTC observation time. This is agent-supplied interoperability data. It does not grant Vibe Memory permissions, prove host tool availability, assign work, or guarantee success. Check effective permissions with the current connection's authorization APIs immediately before a real operation.

## Context Lifecycle profile v1

Use `metadata.vibe_memory_context_lifecycle` to classify context as ephemeral execution, session, project, long-term, decision history or archived context. Retention is declarative: indefinite, manual archive, or until an explicit UTC instant. It never deletes or archives a record automatically.

`context_bundle_policy` is `include`, `explicit_only`, or `exclude`. Normal bundles omit expired and excluded records; `explicit_only` is available only through an exact anchor/ID. A caller must deliberately set the lifecycle override to include expired or excluded records. This policy cannot widen namespace, owner, trust or quarantine access.

## Decision profile v1

Use `proposed` or `open` while an option is only being discussed. Use `decided` or `rejected` only with the reported decider, offset-aware `decided_at`, and at least one evidence record/version. A rejection applies only to its stated project/scope/conditions. Use `unknown` when an explicit profile is useful but the state is not known.

The server-authenticated record creator and `reported_decider` are different facts. A valid profile does not prove that the reported decider had authority or that the claim is true. Later corrections or reconsideration use normal version/correction records; do not silently rewrite history.

Each `evidence` item always pins a Vibe Memory `record_id` and `version`. When the
decision depended on an external source, it may additionally carry `source_type`,
an immutable `permalink`, a document `revision`, a Git `commit_sha`, and the
offset-aware `observed_at` instant. Prefer commit- or revision-pinned links over a
moving branch URL. These are agent-supplied coordinates: the service stores and
hands them off but never opens the link, checks repository access, or claims the
external content still matches. A consuming agent with its own authorization must
open and compare the source.

```json
{
  "record_id": "evidence-record-id",
  "version": 2,
  "source_type": "git_commit",
  "permalink": "https://github.com/acme/atlas/blob/8db71d2/src/api.py#L20-L44",
  "commit_sha": "8db71d2",
  "observed_at": "2026-11-09T08:15:00Z"
}
```

## Checkpoint profile v1

`claimed_stage` separates `implemented`, `local_tests_passed`, `merged`, `deployed`, and `operationally_verified`. `observation_kind` separates an `author_reported` claim from a later `observed`, `reproduced`, `failed`, or `unavailable` record. A second connection belonging to the same user is not automatically an independent verifier.

Store target scope/environment, commit or artifact/lockfile digest, environment identity, exact reproduction command and reported result only when meaningful. Commands and URLs are data only: Vibe Memory never executes commands, visits links, runs tests, or promotes a claim based on a hash or HTTP status. A later agent that can reproduce the result should create its own observation record; one that cannot access the evidence should preserve `unavailable` or an item in `remaining_unknowns` rather than upgrading the claim.

Never put secrets, environment-variable values, raw logs, full transcripts, or hidden reasoning in any profile.

## Failure Reproduction profile v1

Use this only for a durable failed attempt or invalid result that another agent may need to reproduce. Record a stable sample identifier, optional record/version, input rows/bytes, the attempted non-secret settings, sanitized failure stage/code/message, minimal conditions, and the observed result. Ordered `parsing_steps` preserve token-to-value conversion and operation choice so two paths that happen to produce the same final value remain distinguishable.

Evidence references are explicitly typed. Use `uploaded_file` with an existing `file_id`; Vibe Memory already keeps that upload's byte count and SHA-256. Use `external` for a local path or URL that remains outside Vibe Memory. An authorized client may report `match`, `changed`, `missing`, `inaccessible`, or `unverified` with offset-aware `checked_at` and comparable expected/observed SHA-256 or byte counts when relevant. Never treat `inaccessible` as `missing`, and never claim `match` without comparable coordinates.

Vibe Memory validates and stores the client report but never opens the external reference, runs the stored command, parses the uploaded file, or collects raw logs. Create a new observation record under the checking agent's authenticated connection instead of rewriting another agent's claim. Do not store credentials, tokens, raw logs, full transcripts, hidden reasoning, or unredacted sensitive input.

## Evidence Impact Review profile v1

When an evidence record/version is withdrawn or corrected, first run the read-only
exact dependency lookup:

```sh
"$VM_CLI" evidence-impact-candidates EVIDENCE_RECORD_ID 2 --limit 100
```

REST uses `POST /v1/evidence-impact/candidates`; MCP uses
`evidence_impact_candidates`. The result contains only owner-scoped Decision,
Checkpoint, and relationship claims that explicitly cite the exact ID and version.
It contains no record body or hash, performs no LLM call, makes no impact judgment,
and never classifies an unlisted or unversioned dependency as `not_affected`.

For each candidate actually reviewed, create a separate memory carrying
`metadata.vibe_memory_evidence_impact_review`: the target kind/ID/version, exact
evidence coordinates, reviewer, UTC observation time, `affected`, `not_affected`,
or `unknown`, a concise rationale, and optional follow-up actions. Do not update a
different reviewer's record to force consensus. Conflicting observations remain
separate, searchable records and can be selected together in a context bundle.

Absence of a candidate or review means `unknown`, not no impact. The server never
invalidates a decision, follows a withdrawal link, infers semantic dependency, or
preserves deleted source text. Normal owner/namespace/security filters apply before
candidate discovery, so unavailable evidence and cross-owner records are not
enumerated through this workflow.
