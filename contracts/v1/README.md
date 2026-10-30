# Vibe Memory Contract 1.1

Core profile: records, agent-supplied keywords, stable IDs, optimistic versions, provenance, corrections, pagination and owner isolation. Extensions are discoverable at `/.well-known/vibe-memory` and `/v1/capabilities`.

Time is UTC. `valid_from`/`valid_to` describe when an agent says a claim applies. `created_at`/`recorded_at` describe when the server recorded the current version. Historical `known_at` reconstruction is reported as `current_versions_only` until a server advertises that extension.

Namespaces are authorization boundaries selected with `X-Vibe-Memory-Namespace`; project metadata is only classification. Unsupported capabilities remain explicit instead of being silently emulated. Additive fields are backward compatible; removals or semantic changes require a new major contract version and a deprecation period.

Apache-2.0 licensed. See the repository `LICENSE`.
