# Vibe Memory Contract governance

The public contract describes data and error semantics, not a new transport protocol. REST, MCP and CLI map to the same capability model. The service stores agent-authored data and performs no LLM inference, summarization, keyword extraction or relationship inference.

## Compatibility

- A major version changes only when an existing field or operation is removed or its meaning changes incompatibly.
- A minor version may add optional fields, operations, reason codes or extensions. Clients must ignore unknown additive fields and must not treat an unknown optional extension as supported.
- Servers advertise every accepted version at `/.well-known/vibe-memory`. Clients may send `Vibe-Memory-Contract-Version`; an unsupported version returns HTTP 406 with `UNSUPPORTED_CONTRACT_VERSION` and the supported set.
- Deprecations remain documented for at least one minor release and are listed in discovery before removal. A major release must publish a migration note and retain the previous stable contract documents.
- Core behavior and optional extensions are reported separately by `/v1/capabilities`. Unsupported operations return an explicit unsupported/denied result and are never silently emulated.

## Changes

Contract changes use a public GitHub issue or pull request in `vibememory/vibememory`. A proposal states the use case, compatibility impact, security/privacy impact, server-inference impact, fixtures and conformance changes. At least one maintainer reviews a change before merge. Security reports follow `SECURITY.md` instead of a public issue.

The contract documents and conformance fixtures are MIT licensed under the repository `LICENSE`, so independent implementations may use, modify, and redistribute them.
