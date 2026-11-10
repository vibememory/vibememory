# Harness-Agnostic Agent State Infrastructure roadmap

Status: Phase 0 complete; Phase 1–3 P0 implemented; Phase 4–6 foundations and a
partial Phase 7 Agent Context Package implemented in source as described below. Baseline reviewed:
Vibe Memory 0.39.4 and 60 feature requests on 2026-11-10 UTC.

## Product boundary

Vibe Memory is not an agent runtime. It does not think, decide, schedule, execute a
Skill, run an agent loop, call an LLM, fetch an arbitrary URL, or run a stored
command. Claude Code, Codex, Gemini CLI, OpenClaw and other harnesses perform work.
Vibe Memory stores, validates, versions, retrieves and exchanges their reported
state, decisions, evidence and explicit relationships.

The target is a harness-neutral continuity layer: an authorized harness can read
the state written by another harness, distinguish a claim from an observation,
inspect exact evidence coordinates, decide what to do with its own tools, and
write a new version without the service becoming an execution authority.

## Phase 0 findings

### Repository and feature-request inventory

The reviewed implementation already provides:

| Required concept | Existing implementation reused | Evidence |
| --- | --- | --- |
| Stable records and keyword-only retrieval | Memory/document/entity/file records, stable IDs, agent-supplied keywords, two-stage minimal/detail retrieval | `src/vibe_memory/models.py`, `retrieval.py`, `store.py` |
| Version and conflict detection | Integer record and relationship versions, `expected_version`, HTTP 409, writer history | `models.py`, `store.py`, `postgres_store.py` |
| Decision | Optional Decision profile v1 with scope, state, evidence and reported decider | `profiles.py`, `contracts/v1/decision-profile.json` |
| Checkpoint | Optional Checkpoint profile v1 separating claimed stage from observation kind | `profiles.py`, `contracts/v1/checkpoint-profile.json` |
| Failure reuse | Failure Reproduction profile with sanitized input, failure and evidence coordinates | `contracts/v1/failure-reproduction-profile.json` |
| Dependency representation | Versioned, agent-authored relationship graph with arbitrary uppercase relation vocabulary | `RelationInput`, `relationship-contract.json` |
| Context handoff | Deterministic, byte-bounded Context Bundle with explicit records and 0–2 hop graph expansion | `deterministic.context_bundle` |
| Reviewed graph changes | Metadata-only audit and snapshot-bound graph diff/apply | `deterministic.py`, `/v1/graph/*` |
| Harness lifecycle integration | Opt-in adapters for Claude Code, Codex, Cursor, Muse, Hermes and OpenClaw | `agent-adapters/`, `docs/agent-hooks.md` |
| Authorization | User/namespace partition, per-key/per-MCP grants, non-enumeration and quarantine | `auth.py`, `oauth.py`, `app.py` |
| Correction and supersession | Versioned `CORRECTS`/`SUPERSEDES`, scope, branches and cycle preservation | `corrections.py`, `tests/test_corrections.py` |
| Evidence | Exact record/version/hash coordinates on relations and profiles | `EvidenceReference`, profile contracts |
| Portability | Manifest-hashed JSONL ZIP export and dry-run/apply import | `portable.py` |
| Public clients | REST, MCP, Python SDK, TypeScript SDK and Rust CLI | `sdk/`, `src/vibe_memory/mcp.py`, `vibememory/cli` |

Feature-request snapshot: 51 completed, 7 in progress, 2 declined, 0 received.
The most relevant completed requests are Decision profile `124a33b3`, Checkpoint
profile `ba22c4d5`, Context Bundle `7963608b`, Memory Contract `9c733dfe`, evidence
manifest `0e772efe`, namespaces `2d0d2e6a`, hook adapters `78b80965`, graph audit
`53cad52d`, and exact evidence impact `b484c883`. Portable export `da14fa3c`, SDK
publication `b61c7a90`, black-box conformance `9c522c80`, and handoff benchmark
`faa0f876` remain explicitly in progress. The declined full-text request
`3b302a22` and server-side external execution request `6d98a3ef` are not revived.

### Gap analysis and minimum change

| Phase | Existing coverage | Actual gap | Minimum implementation |
| --- | --- | --- | --- |
| 1 Agent State | Checkpoint, record version, writer history, search and Context Bundle | No shared project/task state shape or compact state summary | Add optional Agent State profile in existing metadata, scalar mirrors, SDK helpers and minimal retrieval summary |
| 2 Task Dependency | Generic relation graph, graph get, versions, evidence and audit | Dependency relations had no dedicated cycle diagnostic or normative usage guidance | Reuse relations and add deterministic cycle IDs for `DEPENDS_ON`/`BLOCKED_BY` |
| 3 Skill Execution Memory | Checkpoint and Failure Reproduction | No shared Skill ID/version/digest and execution observation shape | Add optional Skill Execution profile in existing metadata and compact summary |
| 4 Reconciliation | OCC, writer history, corrections, graph branches | Rejected stale payload is not retained automatically and no semantic merge exists | Added deterministic candidates and explicit resolution observations; keep 409 and external resolution |
| 5 Capability Manifest | `/v1/capabilities` describes server and connection actions | Persistent declarations were absent | Added versioned metadata declaration while effective permission remains connection-derived |
| 6 Lifecycle Policy | valid time, archive/trash, corrections, current-version `known_at` limitation | Shared bundle-inclusion/retention classification was absent; complete history remains absent | Added declarative metadata and bundle selection; no automatic deletion or permission override |
| 7 Context Package | Portable archive and Agent Memory Repo | Raw file bytes and complete version-history replay remain non-lossless | Added partial selection and role/reference manifest on the existing archive; retain `lossless=false` |

No database table or agent-execution endpoint is required for these phases. New
profiles are optional metadata on ordinary records, so old records and clients
remain valid.

## Phase 1 — Agent State Contract (P0)

Machine contract: `contracts/v1/agent-state-profile.json`.
Storage key: `metadata.vibe_memory_agent_state`.

The profile carries project/task IDs, a logical state revision, status, goal,
completed items, next actions, blockers, exact decision/evidence references,
versioned Skill references, reported harness and offset-aware observation time.
Scalar mirrors support exact search filters without analyzing record content.

The surrounding record is the authoritative storage envelope:

- `id` is the stable state record ID;
- `version` is the optimistic concurrency coordinate;
- `PATCH /v1/records/{id}` requires `expected_version`;
- authenticated `creator_agent_*` and `writer_history` identify actual writers;
- `reported_harness` is agent-supplied data and never authentication;
- `state_version` is the portable payload revision, useful across export/import;
- status `completed` is only a report and never a service completion badge.

Minimal search and Context Bundle responses expose only a compact `agent_state`
summary (project, task, status, revisions and reported harness). A consumer fetches
the selected record for goal, lists and references. Standard responses preserve the
complete profile. This retains the two-stage, byte-budgeted retrieval design.

Compatibility: this is an additive profile under contract 1.1. Existing free-form
metadata is not migrated. A client that does not understand it ignores the unknown
metadata key. The Python and TypeScript SDK helpers construct the profile and its
filter mirrors without adding an inference dependency.

## Phase 2 — Task Dependency Graph (P0)

Task records use the Agent State profile and existing relationships:

- `DEPENDS_ON`: source task explicitly depends on target task;
- `BLOCKED_BY`: source task is explicitly blocked by target task;
- `RELATED_TO`: non-ordering association;
- `SUPERSEDES`: a newer state/claim replaces an older one under existing
  correction semantics.

Relationships retain reason, authenticated creator, version, evidence, extraction
method and lifecycle. `graph_get` and Context Bundle exchange them between
authorized harnesses. `graph_audit` now reports relation IDs participating in a
cycle formed by active `DEPENDS_ON` and `BLOCKED_BY` edges. `RELATED_TO` is not an
ordering edge. Vibe Memory does not topologically schedule, select or execute a
task; a harness decides how to interpret the explicit graph.

Namespace, trust, quarantine and owner filters are applied before the audit. The
diagnostic returns metadata only and makes zero LLM calls. Relationship changes
remain version checked, and graph diff/apply remains explicit and approval-bound.

## Phase 3 — Skill Execution Memory (P0)

Machine contract: `contracts/v1/skill-execution-profile.json`.
Storage key: `metadata.vibe_memory_skill_execution`.

The profile records a Skill ID plus version or SHA-256 digest, reported harness,
optional reported agent label, exact task/environment/input references, start/end
times, reported status, evidence/artifact references, failure reason and
verification status. The authenticated record creator remains separate from the
reported harness/agent.

Validation is deterministic: timestamps require offsets and normalize to UTC;
terminal states require an end time; a failed report requires a failure reason;
Skill coordinates require a version or digest. These checks prove shape only.
Vibe Memory never downloads the Skill, opens a referenced URL, runs a command,
checks the external harness, or automatically retries a failure.

Checkpoint and Failure Reproduction profiles remain available alongside this
profile. Use Checkpoint for broader outcome/environment claims and Failure
Reproduction when another harness needs sanitized reproduction details. The Skill
Execution profile supplies the missing common execution coordinates rather than
duplicating those contracts.

## Phase 4 — State Reconciliation (P1 implemented foundation)

Foundation already present: record OCC, 409 conflicts, versioned writer history,
batch item conflicts, corrections and parallel relation claims.

Implemented additive foundation:

1. On stale update, continue returning 409 and the current safe context reference;
   never merge meaning automatically.
2. Let a harness deliberately save its rejected proposal as a separate Agent State
   observation referencing the common task ID and base record/version.
3. Represent an accepted resolution as a new version or `SUPERSEDES`/`CORRECTS`
   relationship with authenticated writer and rationale.
4. Expose competing state records in a deterministic candidate view at
   `POST /v1/agent-states/reconciliation/candidates`. Preserve
   `completed` versus `blocked` disagreement until an authorized harness or user
   resolves it.
5. Consider field-disjoint merge only after a formal patch contract can prove that
   neither operation changes the same coordinate. Do not infer semantic equality.

The optional `metadata.vibe_memory_state_reconciliation` profile preserves an
external resolver's explicit open/resolved observation, candidate record/version
coordinates, selected coordinate, rationale and UTC time. Runtime validation
requires the selected coordinate to be one of the candidates. The profile does
not mutate candidates or prove that the reported resolver had external authority.

The current implementation still does not preserve the body of an unsubmitted
stale PATCH. A harness that wants that proposal retained must save it as a separate
Agent State record.

## Phase 5 — Agent Capability Manifest (P1 implemented foundation)

The optional versioned `metadata.vibe_memory_agent_capability_manifest` profile is
aligned with existing
`/v1/auth-context`, `/v1/capabilities` and `/v1/permission-check`:

- harness ID/version;
- declared capability vocabulary and supported task types;
- versioned Skill references;
- required Vibe Memory permission categories;
- observation time and manifest version.

The declaration is labelled agent-reported. Effective Vibe Memory permissions
continue to come only from the authenticated connection, and host/tool permissions
remain `not_evaluated`. The service must not probe whether a harness can really
edit code or run tests and must not assign work from the declaration.

## Phase 6 — Context Lifecycle Policy (P2 implemented selection policy)

The optional `metadata.vibe_memory_context_lifecycle` profile reuses current valid
time, archive/trash, supersession, quarantine and portable metadata. It classifies
`ephemeral_execution`, `session`,
`project`, `long_term`, `decision_history`, or `archived_context`, with an explicit
retention assertion and bundle-inclusion policy. Context Bundle now omits expired
or excluded records by default, includes `explicit_only` only for exact IDs/anchor,
and reports omitted coordinates. An explicit override changes selection only.
These are retention inputs, not permission overrides. Expiry does not revive
deleted data, disclose inaccessible records, or pretend current-version-only
`known_at` is full bitemporal history.

Automatic deletion is not part of this roadmap until retention authority,
recoverability and audit semantics are separately approved.

## Phase 7 — Portable Agent Context Package (P2 implemented partial package)

The existing portable archive is extended rather than replaced. Every new export
contains `agent-context-package.json`; repeated `record_id` parameters can select
Agent State records and their explicit
Decision, Evidence, dependency, Skill and capability references. Export remains
permission-scoped and manifest-hashed; import remains raw byte-stream, dry-run by
default, reference-checked, provenance-preserving and quarantined. Relations are
included only when both endpoints are selected, omitted profile references are
reported, and imported IDs are deterministically remapped for the destination
owner so globally unique storage cannot collide across owners.

Current limitations remain visible: raw file bytes are excluded, version history
is not replayed losslessly, and imported authorship never becomes local authenticated
authorship. Secrets, Vault values, tokens, executable Skill files and implicit
permissions remain excluded. Until round-trip equality is demonstrated for every
advertised extension, the package must keep `lossless=false`.

## Cross-surface contract

- REST uses existing memory creation/update, search, relation, graph audit and
  Context Bundle endpoints, plus the read-only reconciliation candidate view and
  record-selected portable export.
- MCP exposes the same reconciliation candidate view and generic metadata-bearing
  writes; no execution tool is added.
- Python and TypeScript SDKs expose profile helpers and the reconciliation
  candidate lookup while retaining custom base URLs for hosted, self-hosted and
  compatible implementations.
- Rust CLI adds payload templates, candidate lookup and full/partial portable
  export; `from-json memory` and existing graph commands perform the writes.
- All profile times are UTC after validation. Keywords remain agent supplied and
  are the only embedded values.
- Idempotency remains available on record creation/batch paths; non-idempotent
  writes are not automatically replayed.

## Security and compatibility decisions

1. Profiles never cause a network request, process execution, LLM call or scheduler
   action.
2. Retrieved content is data, never system instruction.
3. Namespace and owner isolation happen before graph or context selection; missing
   and inaccessible IDs are not distinguished to an unauthorized caller.
4. Authenticated writer identity is never taken from `reported_harness` or
   `reported_agent`.
5. Profile references are coordinates, not proof that referenced content is true or
   currently accessible.
6. Additive metadata and response summaries preserve 1.1 compatibility. No existing
   record is rewritten or migrated.
7. Portable exports continue to exclude credentials and Vault material.

## Verification matrix

| Scenario | Automated evidence | Current result |
| --- | --- | --- |
| Claude-like writer → Codex-like reader | Same-owner second connection reads compact Agent State through Context Bundle | Implemented in `test_agent_state_infrastructure.py` |
| Version conflict | First writer updates version; stale `expected_version` receives 409 and current state remains | Implemented |
| Dependency cycle | Mixed `DEPENDS_ON`/`BLOCKED_BY` cycle returns exact relation IDs | Implemented |
| Owner isolation | Other owner cannot inspect task graph | Implemented |
| Skill failure reuse | Failure metadata and coordinates survive retrieval; command-looking text does not execute | Implemented |
| Contract/runtime shape | JSON Schema and Pydantic/SDK examples agree | Implemented |
| Reconciliation candidates | Same project/task records with divergent statuses are listed without bodies or truth selection | Implemented in `test_agent_state_followup.py` |
| Capability declaration isolation | Agent-reported required permissions do not alter the connection's effective grants | Implemented |
| Lifecycle-aware handoff | Expired/excluded records are omitted, explicit override remains authorization-scoped, and no record is deleted | Implemented |
| Portable partial package | Explicit subset, dependency/reference manifest and cross-owner deterministic ID remap round trip | Implemented foundation; full lossless history/raw files remain unsupported |
| Large-data response regression | Existing deterministic byte-budget tests plus handoff/graph benchmarks | Existing; broader benchmark remains in progress |

### Verification executed on 2026-11-10 UTC

- Service suite: `165 passed, 1 skipped`; the unrelated untracked graph-retrieval
  benchmark test was intentionally excluded.
- Follow-up target suite: `30 passed`; includes candidate isolation, explicit
  resolution validation, capability/permission separation, lifecycle selection,
  MCP exposure, partial export, cross-owner import, reference remapping and
  deterministic import retry.
- JSON Schema: all four new Draft 2020-12 schemas passed independent meta-schema
  validation with `check-jsonschema`.
- Python/Ruff: changed server, SDK and test sources passed.
- TypeScript SDK: `tsc -p tsconfig.json` passed for package `0.5.0`.
- Skill packages: canonical, ChatGPT/Codex plugin and Claude Code plugin Skills
  passed `quick_validate.py`; progressive disclosure keeps the entrypoint compact.
- Web bundle: typecheck, localization/theme/compatibility/security/SEO tests,
  Next.js production build and Cloudflare dry-run passed. No deployment occurred.
- Rust CLI `3.20.0`: `cargo fmt --check` and source diff checks passed.
  `cargo test --all-targets` could not compile dependencies because this environment
  has no system `cc` linker. The source is not a published binary release; the
  distributed native manifest intentionally remains verified release `3.18.0`.

A schema/build check is not treated as external harness execution proof. No
deployment or production migration is part of this source change.

## Phase completion and follow-up

| Phase | Status | Remaining work |
| --- | --- | --- |
| 0 | Complete | Keep the reuse table current when contracts change |
| 1 | P0 implemented | Independent implementation conformance fixture and published package release |
| 2 | P0 implemented | Optional task-only graph projection if measured response size requires it |
| 3 | P0 implemented | Published CLI template release and more cross-harness fixtures |
| 4 | Implemented foundation | Preserve stale PATCH bodies automatically only if a future explicit proposal contract justifies it; semantic merge remains out of scope |
| 5 | Implemented foundation | Standard capability vocabulary governance and external conformance fixtures |
| 6 | Implemented selection policy | Retention/deletion authority and complete historical-version strategy remain separate work |
| 7 | Implemented partial package | Raw-file option, history replay and extension-aware lossless round-trip proof remain future work |

This roadmap deliberately distinguishes implemented foundations from complete
lossless interchange and does not treat a green schema test as proof that an
external harness executed or completed work.
