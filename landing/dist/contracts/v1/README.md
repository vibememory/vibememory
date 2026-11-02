# Vibe Memory Contract 1.1

Core profile: records, agent-supplied keywords, stable IDs, optimistic versions, provenance, corrections, pagination and owner isolation. Extensions are discoverable at `/.well-known/vibe-memory` and `/v1/capabilities`.

Normative machine-readable documents:

- `memory-contract.json`: current record representation.
- `relationship-contract.json`: agent-authored edge, evidence, correction scope and lifecycle.
- `error-contract.json`: shared REST/MCP reason code and retry contract.
- `openapi-profile.json`: minimum REST compatibility surface without implementation internals.

Time is UTC. `valid_from`/`valid_to` describe when an agent says a claim applies. `created_at`/`recorded_at` describe when the server recorded the current version. Historical `known_at` reconstruction is reported as `current_versions_only` until a server advertises that extension.

Namespaces are authorization boundaries selected with `X-Vibe-Memory-Namespace`; project metadata is only classification. Unsupported capabilities remain explicit instead of being silently emulated. Additive fields are backward compatible; removals or semantic changes require a new major contract version and a deprecation period.

Clients may request `1.0` or `1.1` with the `Vibe-Memory-Contract-Version` header. The server returns the negotiated version in the same response header and all accepted versions in `Vibe-Memory-Contract-Supported`. Unknown versions fail with HTTP 406 and the `UNSUPPORTED_CONTRACT_VERSION` reason code. A 1.0 client must ignore additive 1.1 fields; it does not gain optional extensions by requesting an older version.

See `../GOVERNANCE.md` for compatibility and change rules and `../ump-mapping.md` for explicit mapping limits. Contract and conformance materials are MIT licensed. See the repository `LICENSE`.
