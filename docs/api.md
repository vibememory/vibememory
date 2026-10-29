# API and agent contract

Your own server exposes an interactive schema at `/docs` and machine-readable OpenAPI at `/openapi.json`.

## Authentication

Browser signup/login uses `/auth/signup`, `/auth/login`, `/auth/me`, and `/auth/logout`. The session cookie is HttpOnly; mutations must include an Origin exactly matching `MEMORY_PUBLIC_ORIGIN`.

Issue agent keys through the console (or an authenticated browser session at `POST /auth/api-keys`). Agent requests use `Authorization: Bearer <key>`; they do not use account passwords or browser cookies. `vault_access` is a separate permission, defaults to false, and can be changed with `PATCH /auth/api-keys/{id}`. `DELETE /auth/api-keys/{id}` revokes a key immediately. Other users' records return 404.

## Endpoints

| Method | Path | Behavior |
| --- | --- | --- |
| GET | `/health` | Liveness, no private data |
| GET | `/v1/me` | Authenticated user ID and keyword model |
| GET | `/v1/stats` | Owner-scoped console counts |
| POST | `/v1/memories` | content, kind, keywords; optional source/tags/metadata |
| POST | `/v1/entities` | name, entity_type, keywords; optional description/source/tags/metadata |
| POST | `/v1/documents` | title, keywords; optional content/file_id/source/tags/metadata |
| GET | `/v1/records` | Owner-scoped records with kind/limit/offset |
| GET/DELETE | `/v1/records/{id}` | Read/delete a record and its index/incident edges |
| PUT | `/v1/records/{id}/keywords` | Replace the explicitly supplied keyword index |
| POST | `/v1/files` | Raw application/octet-stream body; optional filename query |
| GET/DELETE | `/v1/files/{id}` | Original bytes / delete unreferenced original |
| POST/GET | `/v1/relations` | Store agent-inferred relationships / list with status filter |
| PATCH | `/v1/relations/{id}` | Retract/restore using reason and expected_version |
| GET | `/v1/graph/{id}` | Explicit 0–2 hop active-edge traversal |
| POST | `/v1/search` | keywords, optional limit/scope/tags |
| POST/GET | `/v1/feature-requests` | Submit/list owner-scoped feature feedback |
| GET | `/v1/feature-requests/{id}` | Read one submitted request |
| GET | `/v1/vault` | Vault-scoped names, descriptions, and access metadata; never values |
| GET | `/v1/vault/{name}` | Read one value with a Vault-scoped agent key or browser session |
| PUT/DELETE | `/v1/vault/{name}` | Browser-session-only create/rotate/delete with same-origin protection |

## Encrypted Vault

Vault entries are owner-scoped and encrypted at rest with AES-256-GCM. Each write
uses a fresh 96-bit nonce and authenticates the account ID and entry name as
associated data. Names must match `[A-Za-z][A-Za-z0-9_.-]{0,99}`; values are
1–65,536 characters. Listing and write responses never contain the value.

Ordinary and pre-existing agent keys receive 403 from Vault endpoints. A browser
session can explicitly create a key with `vault_access: true`, toggle that flag,
or approve a device-login request that asks for Vault access. Agent keys can list
and read but cannot write or delete entries. Use the Rust CLI instead of handling
the value directly:

```sh
./bin/vibe-memory vault list
./bin/vibe-memory vault exec \
  --env GITHUB_TOKEN=github-token -- gh api user
```

The CLI intentionally has no command that prints a value. `vault exec` injects it
only into the selected child process; that process remains capable of logging its
own environment, so choose commands carefully.

## Keyword-only retrieval

Every indexed record requires 1–32 keywords, each 1–100 characters. The server embeds each keyword separately. Titles, content, summaries, metadata, and original file bytes are not embedded or analyzed.

The agent extracts search keywords before calling:

```json
{"keywords":["Python","code examples"],"scope":"memories","limit":5}
```

Scopes: `all`, `memories`, `documents`, `entities`. `tags` requires all provided tags to match. The response contains record IDs, matched keywords, metadata, and vector similarity scores. It does not build an answer or automatically traverse the graph. The agent fetches sources and selects evidence. A raw `query` field is rejected (422).

## Agent-prepared document metadata

Upload original bytes first; no multipart form or base64:

```sh
curl -X POST "$MEMORY_URL/v1/files?filename=project.pdf" \
  -H "Authorization: Bearer $MEMORY_API_KEY" \
  -H 'Content-Type: application/octet-stream' \
  --upload-file ./project.pdf
```

Then POST the agent's metadata to `/v1/documents`:

```json
{
  "title": "project.pdf",
  "file_id": "id-from-upload",
  "keywords": ["memory graph", "agent integration"],
  "source": "project.pdf",
  "metadata": {
    "summary": "Summary written by the connected agent",
    "evidence": [{"page": 3, "text": "Passage selected by the agent"}]
  }
}
```

`content` is optional opaque text storage. Omitting `file_id` allows external source references. The app records only upload integrity information (byte count/SHA-256); all semantic metadata is agent-supplied. Referenced files cannot be deleted until referring documents are removed (409).

## Relationships

Agent-defined relation names use uppercase identifiers, such as `WORKS_ON`, `PREFERS`, `SUPPORTS`, `CONTRADICTS`, or `SUPERSEDES`. Internal `KEYWORD_OF` and `CHUNK_OF` are reserved. Both endpoints must belong to the authenticated owner.

```json
{
  "source_id": "person-record-id",
  "target_id": "project-record-id",
  "relation": "WORKS_ON",
  "reason": "Explicitly stated by the user"
}
```

Retraction/restoration requires a reason and expected_version. A stale version returns 409. A `SUPERSEDES` edge records meaning; it does not automatically hide/delete old facts. The agent interprets evidence and resolves contradictions.

## Feature feedback

```json
{
  "title": "Batch relationships",
  "description": "Store multiple relationships in one transaction.",
  "agent_name": "coding-agent",
  "use_case": "Avoid 100 network round trips.",
  "priority": "medium",
  "client_request_id": "batch-relations-v1"
}
```

Required: title, description, agent_name. A stable optional client_request_id makes identical retries return the existing record (200); first submission is 201 and changed content under the same ID is 409. Feedback is stored as `received` without embedding or mixing it into memory search. Submission does not approve or implement a feature automatically.

### Live change events

`GET /v1/events?after=0&seconds=25` is an authenticated SSE stream (same
Bearer key or browser session as other `/v1` endpoints). `seconds` is 1–60;
the server closes each bounded connection normally, and clients reconnect.
`Last-Event-ID` overrides `after`. IDs are persistent increasing integers;
only events belonging to the authenticated user are returned. Events are
stored in the graph transaction alongside each successful mutation, so failed
writes emit nothing. History currently remains until the operator replaces the
data store; it is not a bounded notification queue.

Events include `memory.created/updated/deleted`, corresponding `document`,
`entity` and `file` changes, and `relation.created/updated`. Updates currently
mean keyword replacement or relationship status changes, which are the supported
update operations. Record deletion also invalidates incident relationships.
Payloads contain IDs and change metadata, without original text or keywords.
Fetch current records/relations to refresh context; events can be replayed and
must be deduplicated by ID. Deleting a record retains its minimal event history.

The stream sends heartbeats, disables buffering/caching, checks authentication
while connected and closes access after key revocation or session expiration.
The current single-process service polls its event journal every 0.5 seconds.

Agents use `./bin/vibe-memory watch --seconds 3600 --cursor-file PATH`.
The helper prints JSON lines, reconnects and persists the last printed ID. Use a
separate private cursor path for each service/account/workspace. The skill directs
agents to inspect background output at work checkpoints; SSE cannot wake a stopped
agent or inject context into an unsupported host. Network interruptions retry
within the configured duration; HTTP rejection stops the listener.


### Browser-approved agent login

`POST /auth/device/start` with `{ "name": "Agent name", "vault_access": false }` creates a 5-minute
request, returning a private `device_code`, public `user_code`, approval URL and
poll interval. The agent must keep the private code secret and show the approval
link and public confirmation code to the user. Start requests are rate-limited.
The authenticated browser reads `GET /auth/device?code=...` and explicitly sends
`POST /auth/device/approve` with `{ "user_code": "...", "approved": true }`.
Cookie authentication and same-origin checks protect approval; login redirects
only to a validated local `/connect?code=...` path.

The initiating CLI polls `POST /auth/device/poll` with `{ "device_code": "..." }`
at the returned interval. Pending returns `{ "state": "pending" }`. Approval
allows a single atomic exchange for `{ "state": "connected", "key": "...",
"key_id": "..." }`; the browser never receives this key. Denial returns 403,
expiry or a consumed request 410, excessive polling 429. Only hashed codes and
keys are stored. The resulting key is a normal revocable memory key. Vault access
is granted only when requested and visibly approved; existing keys default to no
Vault access.
