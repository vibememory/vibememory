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
| trust/quarantine | Local retrieval safety state | Import never promotes external trust automatically. |

Lossless interchange requires both implementations to advertise the relevant extensions. Search ranking, embedding vectors, LLM reasoning and hidden prompts are intentionally outside the compatibility contract.
