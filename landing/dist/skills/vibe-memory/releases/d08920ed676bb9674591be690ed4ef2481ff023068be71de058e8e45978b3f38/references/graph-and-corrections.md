# Relationships, corrections, and graph workflows

Infer entities and relationships yourself. Search first, use uppercase identifiers such as `WORKS_ON`, `MENTIONED_IN`, `PREFERS`, `CORRECTS`, or `SUPERSEDES`, and include an evidence-based reason. Parallel/conflicting edges are separate claims, not facts to collapse. Never select truth by timestamp alone.

For explicit replacement, prefer MCP `memory_correct` so the new record and version-checked edge commit atomically. Use correction scope `full` only when the entire old record is replaced; use `partial` when any old facts remain; `unknown` means not reviewed. CLI `relate --correction-scope`, `relation-scope`, and graph JSON expose the same field. Fetch the current relation version before scope/status mutation.

For consequential claims, fetch each selected evidence record and pin its `record_id`, version, content hash, offset-aware UTC `observed_at`, and optional page/section/range. Set evidence coverage only to `selected` or `partial` when true; otherwise `unknown`. If the input set matters, store a concise normal record manifest and reference it with `input_manifest_id`. Never include full prompts, hidden reasoning, secrets, or unrelated text. Inspect `evidence_status` for current coordinates, lifecycle, and `current|changed|unavailable` comparison.

Active correction cycles remain visible. If `correction_graph_complete` or `cycle_check_complete` is false, treat the claim as unresolved and never hide the older record.

For deterministic bulk repair, prepare `template graph-diff`, run `graph-diff`, review every `create`, `unchanged`, `conflicting_claim`, `unknown`, and scoped retract candidate. For `graph-apply`, copy the returned diff hash and approve only exact reviewed create client IDs/retract relation IDs. Never approve unknown/conflicting items or infer an omitted edge should be removed. Use stable client request IDs across retries.

For task-state handoffs, reuse ordinary relation claims: `DEPENDS_ON`, `BLOCKED_BY`, `RELATED_TO`, and `SUPERSEDES`. `graph-audit` reports active `DEPENDS_ON`/`BLOCKED_BY` cycle relation IDs. A cycle is deterministic structural evidence, not permission for the server to schedule, reorder, merge, or execute tasks; preserve it for an external harness or user to resolve.
