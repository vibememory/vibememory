# UMP comparison and mapping notes

This document records a conservative comparison surface for public memory proposals such as UMP. It does not claim certification, require another protocol, or map fields that have not been verified.

| Vibe Memory concept | Portable meaning | Mapping limit |
| --- | --- | --- |
| `id` | Stable owner-scoped record identifier | Other systems may require a namespace-qualified portable ID. |
| `kind` | Memory, document, entity or opaque file | Provider-specific memory categories remain extension data. |
| `content` | Agent-authored original text | The server does not create a summary or inferred canonical form. |
| `keywords` | Agent-supplied retrieval keys | They are not equivalent to full-text content or model-generated tags. |
| `provenance` | Original source separate from authenticated writer | Imported authorship never becomes local authenticated authorship. |
| `valid_from` / `valid_to` | Agent-asserted valid time in UTC | Historical recorded-time reconstruction is a separate capability. |
| relationship contract | Agent-inferred typed edge with evidence | Unknown relation vocabularies are preserved, not semantically merged. |
| correction relationship | Supersession/correction claim with explicit scope | Parallel claims and incomplete evidence must not be silently collapsed. |
| Agent State profile | Harness-neutral reported project/task state, blockers, next actions and pinned references | `completed` remains a writer claim; record `version`/`expected_version` is the concurrency coordinate. |
| Skill Execution profile | Data-only report of a Skill run performed by an external harness | Profile validity does not prove execution, success, authority or verification. |
| task dependency relationships | Explicit `DEPENDS_ON`, `BLOCKED_BY`, `RELATED_TO` and `SUPERSEDES` claims | Structural cycles are reported; the service never schedules or executes tasks. |
| State Reconciliation profile | Explicit external resolution observation over competing Agent State coordinates | Candidate discovery reports structural status divergence only; it does not determine truth or merge meaning. |
| Agent Capability Manifest | Agent-reported capability, task-type, Skill and required-permission declaration | The declaration never becomes an effective Vibe Memory grant, availability probe, assignment, or success guarantee. |
| Context Lifecycle profile | Retention assertion and Context Bundle inclusion hint for a record | Expiry and exclusion affect bundle selection only; they do not delete data or override access control. |
| Agent Context Package | Permission-scoped portable subset with explicit profile/dependency coordinates and omitted-reference reporting | The current archive excludes raw file bytes and version replay, remains `lossless=false`, and carries no secrets, permissions, or executable Skills. |
| trust/quarantine | Local retrieval safety state | Import never promotes external trust automatically. |

Lossless interchange requires both implementations to advertise the relevant extensions. Search ranking, embedding vectors, LLM reasoning and hidden prompts are intentionally outside the compatibility contract.
