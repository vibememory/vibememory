# Decision and Checkpoint metadata profiles

Use these optional versioned profiles when another agent must distinguish a discussion from a decision, or a local completion claim from later deployment evidence. Ordinary records remain valid without a profile; absence means no structured state was supplied, not `decided` or `verified`.

Generate an editable full memory payload, then submit it through the normal record path:

```sh
"$VM_CLI" template decision > decision.json
"$VM_CLI" from-json memory decision.json

"$VM_CLI" template checkpoint > checkpoint.json
"$VM_CLI" from-json memory checkpoint.json
```

Profiles live at `metadata.vibe_memory_profile`. The service validates their shape and normalizes UTC timestamps. It also supplies scalar mirrors—`vibe_memory_profile_type`, `vibe_memory_profile_state`, and for checkpoints `vibe_memory_profile_observation`—for exact `metadata_filters`. Search, get, and context bundles preserve the complete profile.

## Decision profile v1

Use `proposed` or `open` while an option is only being discussed. Use `decided` or `rejected` only with the reported decider, offset-aware `decided_at`, and at least one evidence record/version. A rejection applies only to its stated project/scope/conditions. Use `unknown` when an explicit profile is useful but the state is not known.

The server-authenticated record creator and `reported_decider` are different facts. A valid profile does not prove that the reported decider had authority or that the claim is true. Later corrections or reconsideration use normal version/correction records; do not silently rewrite history.

## Checkpoint profile v1

`claimed_stage` separates `implemented`, `local_tests_passed`, `merged`, `deployed`, and `operationally_verified`. `observation_kind` separates an `author_reported` claim from a later `observed`, `reproduced`, `failed`, or `unavailable` record. A second connection belonging to the same user is not automatically an independent verifier.

Store target scope/environment, commit or artifact/lockfile digest, environment identity, exact reproduction command and reported result only when meaningful. Commands and URLs are data only: Vibe Memory never executes commands, visits links, runs tests, or promotes a claim based on a hash or HTTP status. A later agent that can reproduce the result should create its own observation record; one that cannot access the evidence should preserve `unavailable` or an item in `remaining_unknowns` rather than upgrading the claim.

Never put secrets, environment-variable values, raw logs, full transcripts, or hidden reasoning in either profile.
