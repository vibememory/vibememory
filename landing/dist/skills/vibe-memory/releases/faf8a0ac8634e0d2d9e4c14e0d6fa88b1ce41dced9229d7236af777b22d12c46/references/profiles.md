# Decision, Checkpoint, and Failure Reproduction metadata profiles

Use these optional versioned profiles when another agent must distinguish a discussion from a decision, or a local completion claim from later deployment evidence. Ordinary records remain valid without a profile; absence means no structured state was supplied, not `decided` or `verified`.

Generate an editable full memory payload, then submit it through the normal record path:

```sh
"$VM_CLI" template decision > decision.json
"$VM_CLI" from-json memory decision.json

"$VM_CLI" template checkpoint > checkpoint.json
"$VM_CLI" from-json memory checkpoint.json

"$VM_CLI" template failure-reproduction > failure.json
"$VM_CLI" from-json memory failure.json
```

Profiles live at `metadata.vibe_memory_profile`. The service validates their shape and normalizes UTC timestamps. It also supplies scalar mirrors—`vibe_memory_profile_type`, `vibe_memory_profile_state`, and for checkpoints `vibe_memory_profile_observation`—for exact `metadata_filters`. Search, get, and context bundles preserve the complete profile.

Failure reproduction evidence uses the separate `metadata.vibe_memory_failure_reproduction` key so existing Decision and Checkpoint profile v1 records remain unchanged. Start with the CLI template, use the public Python/TypeScript SDK helper, or place it in an agent-prepared memory payload submitted with `from-json memory`.

## Decision profile v1

Use `proposed` or `open` while an option is only being discussed. Use `decided` or `rejected` only with the reported decider, offset-aware `decided_at`, and at least one evidence record/version. A rejection applies only to its stated project/scope/conditions. Use `unknown` when an explicit profile is useful but the state is not known.

The server-authenticated record creator and `reported_decider` are different facts. A valid profile does not prove that the reported decider had authority or that the claim is true. Later corrections or reconsideration use normal version/correction records; do not silently rewrite history.

## Checkpoint profile v1

`claimed_stage` separates `implemented`, `local_tests_passed`, `merged`, `deployed`, and `operationally_verified`. `observation_kind` separates an `author_reported` claim from a later `observed`, `reproduced`, `failed`, or `unavailable` record. A second connection belonging to the same user is not automatically an independent verifier.

Store target scope/environment, commit or artifact/lockfile digest, environment identity, exact reproduction command and reported result only when meaningful. Commands and URLs are data only: Vibe Memory never executes commands, visits links, runs tests, or promotes a claim based on a hash or HTTP status. A later agent that can reproduce the result should create its own observation record; one that cannot access the evidence should preserve `unavailable` or an item in `remaining_unknowns` rather than upgrading the claim.

Never put secrets, environment-variable values, raw logs, full transcripts, or hidden reasoning in any profile.

## Failure Reproduction profile v1

Use this only for a durable failed attempt or invalid result that another agent may need to reproduce. Record a stable sample identifier, optional record/version, input rows/bytes, the attempted non-secret settings, sanitized failure stage/code/message, minimal conditions, and the observed result. Ordered `parsing_steps` preserve token-to-value conversion and operation choice so two paths that happen to produce the same final value remain distinguishable.

Evidence references are explicitly typed. Use `uploaded_file` with an existing `file_id`; Vibe Memory already keeps that upload's byte count and SHA-256. Use `external` for a local path or URL that remains outside Vibe Memory. An authorized client may report `match`, `changed`, `missing`, `inaccessible`, or `unverified` with offset-aware `checked_at` and comparable expected/observed SHA-256 or byte counts when relevant. Never treat `inaccessible` as `missing`, and never claim `match` without comparable coordinates.

Vibe Memory validates and stores the client report but never opens the external reference, runs the stored command, parses the uploaded file, or collects raw logs. Create a new observation record under the checking agent's authenticated connection instead of rewriting another agent's claim. Do not store credentials, tokens, raw logs, full transcripts, hidden reasoning, or unredacted sensitive input.
