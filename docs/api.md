# API and agent contract

Your own server exposes an interactive schema at `/docs` and machine-readable OpenAPI at `/openapi.json`.

## Authentication

Browser signup/login uses `/auth/signup`, `/auth/login`, `/auth/me`, and `/auth/logout`. The session cookie is HttpOnly; mutations must include an Origin exactly matching `MEMORY_PUBLIC_ORIGIN`.

Issue agent keys through the console (or an authenticated browser session at `POST /auth/api-keys`). Agent requests use `Authorization: Bearer <key>`; they do not use account passwords or browser cookies. `DELETE /auth/api-keys/{id}` revokes a key immediately. Other users' records return 404.

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
