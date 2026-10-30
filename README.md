<div align="center">
  <img src="landing/dist/assets/favicon.svg" width="64" alt="Vibe Memory">
  <h1>Vibe Memory</h1>
  <p><strong>One memory. All your agents. Your infrastructure.</strong></p>
  <p>A self-hosted memory graph and keyword index for Claude Code, Codex, OpenClaw, Hermes, and any REST-capable agent.</p>
  <p><a href="https://vibememory.io">Website</a> · <a href="docs/self-hosting.md">Self-hosting</a> · <a href="docs/api.md">API</a> · <a href="README.ko.md">한국어</a></p>
</div>

## What it does

Vibe Memory stores the data your agents prepare. It does **not call an LLM**, infer entities or relationships, parse files, extract keywords, chunk documents, or assemble RAG context.

| Agent | Vibe Memory |
| --- | --- |
| Extract facts, entities, relationships, and file metadata | Validate and persist the submitted data |
| Supply storage keywords | Embed only those keywords locally |
| Extract search keywords from the user's question | Compare keyword vectors and return matching records |
| Select evidence and build an answer | Provide source records and explicit graph traversal |

- **Durable relationship graph:** memories, entities, documents, provenance, and relationship history in PostgreSQL.
- **Efficient graph refreshes:** idempotent 100-item entity/relation/update batches and compact paginated reads.
- **Agent mailboxes:** same-account persistent handoffs with recipient-scoped SSE and explicit acknowledgements.
- **Keyword-only pgvector search:** local multilingual embeddings; raw content, titles, and summaries are never embedded.
- **Provenance quarantine:** external/imported text is untrusted and excluded from normal search and graph traversal until an agent explicitly reviews it.
- **Web console:** signup/login, account isolation, memory management, raw file uploads, relationships, and feature requests.
- **Account security:** optional authenticator-app TOTP with one-time recovery codes; OTP secrets are encrypted and recovery codes are stored only as hashes.
- **Remote MCP:** one OAuth 2.1 + PKCE Streamable HTTP server for ChatGPT, Codex, Claude, and other MCP clients.
- **Agent keys:** independently revocable keys share the same account's memory; keys are shown once and stored as hashes.
- **Encrypted Vault:** store service secrets with AES-256-GCM and grant Vault use separately per agent connection; agents can create owner-bound, one-time browser capture links so values never need to pass through chat.
- **Byte streams:** upload originals as `application/octet-stream`, then attach agent-prepared JSON using `file_id`.
- **Portable skill:** a compact `SKILL.md`, native Rust CLI, and verified compatibility bootstrap, with no vendor SDK requirement.

## Quick start: Docker Compose

Requires Docker Engine with Compose v2 on Linux amd64. Compose starts PostgreSQL 17 with pgvector, so no separately managed database, Cloudflare account, Node.js, or LLM API key is required.

```sh
git clone https://github.com/vibememory/vibememory.git
cd vibememory
cp .env.example .env
docker compose up -d --build
```

Open **http://localhost:8080**, create an account, then open the **Console → Agent API keys** page.

The app container serves the website, console, and REST API. Separate named volumes preserve PostgreSQL data and uploaded files, the Vault key, and model cache. The first keyword embedding downloads the multilingual model (about 220 MB); signup and the console do not require this download.

```sh
docker compose logs -f app
docker compose exec app vibe-memory warmup  # optional: download the model ahead of time
```

For another domain or port, set `MEMORY_PUBLIC_ORIGIN` to the **exact browser origin** before starting. It controls session cookies and CSRF validation. See [configuration, HTTPS, backups, and upgrades](docs/self-hosting.md).

## Connect an agent

Copy [`skills/vibe-memory`](skills/vibe-memory) into your agent's skill directory, install the native CLI, and use browser approval. Request Vault access only for agents you trust with every stored secret:

```sh
# Download and verify the current native Rust CLI, then refresh the Skill.
MEMORY_URL=http://localhost:8080 python3 skills/vibe-memory/scripts/memory.py sync
skills/vibe-memory/bin/vibe-memory login --url http://localhost:8080 \
  --name 'My agent' --vault-access

skills/vibe-memory/bin/vibe-memory remember 'I prefer Python examples' \
  --kind preference --keyword Python --keyword 'code examples' --source coding-agent

# The agent extracts these keywords before sending the request.
skills/vibe-memory/bin/vibe-memory recall Python 'code examples'

# Secret values stay out of chat and persistent shell configuration.
skills/vibe-memory/bin/vibe-memory vault exec \
  --env GITHUB_TOKEN=github-token -- gh api user
```

The native Rust CLI wraps browser authentication, persistent agent messages, storage, search, byte-stream files, secure Vault capture and execution, live events, and Skill updates so agents do not need to load API schemas into context. Browser login reports the permissions actually granted, supports 60–900 second approval links, and can elevate an existing connection to Vault access. Relationship claims can preserve version/hash/UTC-pinned evidence references, explicit coverage and an agent-authored input-manifest record without storing prompts or reasoning. `vault capture NAME` returns an expiring signed-in browser link that writes directly to Vault, `vault list` exposes names and metadata only, and `vault exec` injects selected values into one child process without printing them. Its standalone source and platform releases live at [`vibememory/cli`](https://github.com/vibememory/cli); this repository keeps the Skill instructions and verified compatibility bootstrap. All reasoning happens in the connected agent. Remote agent connections require HTTPS.

Claude Code users can also install the repository's marketplace plugin after the
native CLI is available on `PATH`:

```text
/plugin install vibe-memory --marketplace vibememory/vibememory
```

It adds non-blocking session recall and deduplicated checkpoint hooks. See
[agent lifecycle hooks](docs/agent-hooks.md) for behavior, privacy boundaries,
older Claude Code installation steps, and equivalent workflows for Codex,
OpenClaw, Hermes, and other hosts.

## Connect ChatGPT or Claude with MCP

Add your deployment's public MCP URL as a custom MCP server or custom connector:

```text
https://memory.example.com/mcp
```

The client discovers OAuth metadata, dynamically registers as a public client, and redirects the user to Vibe Memory for login and explicit consent. Authorization code + PKCE tokens are user-scoped, stored only as hashes, refresh-token rotation is enabled, and connections can be revoked from **Console → Agent connections**. The MCP tool set supports keyword search, record/graph/event reads, persistent same-account agent messages, agent-authored memory/entity/document/relation writes, feature requests, and optional Vault reads. Vault requires both the sensitive `vault:read` scope and explicit per-entry browser grants; returned values enter client/model context, are audited, and are never used by the server to execute external calls. MCP deliberately excludes deletion and base64 file uploads; original files keep using the raw byte-stream endpoint.

## Run from source

Requires Python 3.12/3.13, [uv](https://docs.astral.sh/uv/), and PostgreSQL with the pgvector extension. The web assets are already included; no frontend build step is needed.

```sh
uv sync --frozen
cp .env.example .env
# Set MEMORY_DATABASE_URL to your empty PostgreSQL/pgvector database.
uv run vibe-memory serve
```

Open http://localhost:8080. To use `127.0.0.1` instead, change `MEMORY_PUBLIC_ORIGIN` accordingly. `MEMORY_API_KEYS` is optional; registered accounts can issue keys without changing server configuration.

## API example

All `/v1` operations require an agent Bearer key or an authenticated console session. Browser mutations also require a matching Origin.

```sh
curl "$MEMORY_URL/v1/search" \
  -H "Authorization: Bearer $MEMORY_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"keywords":["Python","code examples"],"limit":5}'

curl -X POST "$MEMORY_URL/v1/files?filename=notes.pdf" \
  -H "Authorization: Bearer $MEMORY_API_KEY" \
  -H 'Content-Type: application/octet-stream' \
  --upload-file ./notes.pdf
```

Use `/docs` and `/openapi.json` on your own server for exact schemas. See the [API guide](docs/api.md) for document metadata, entities, relations, and agent feature requests.

## Development

```sh
uv sync --frozen
uv run ruff check src ops tests scripts skills/vibe-memory/scripts
uv run pytest -q
uv build
```

Tests use temporary data. Semantic integration tests download the actual embedding model on their first run; API invariant tests use a spy embedder to prove that only supplied keywords are embedded. CI also builds and smoke-tests the Docker Compose installation, including restart persistence.

## Architecture and current limits

```text
Browser console / REST agent / remote MCP client
            │
         FastAPI
            │
            ├── PostgreSQL: accounts, OAuth, records, relationships, agent mailboxes, feedback, Vault ciphertext
            ├── pgvector: agent-supplied keyword embeddings and exact cosine search
            ├── local multilingual keyword model (FastEmbed / ONNX)
            └── persistent volume: opaque byte-stream files and Vault/OTP encryption key
```

This is a **personal/small-team deployment**. PostgreSQL is the source of truth for structured data; raw uploaded bytes remain on the app volume. Search uses exact, owner-scoped pgvector cosine distance, so it favors perfect recall over an approximate ANN index. Horizontal file-storage replication, email verification, password recovery, and social login are not currently included.

Kuzu remains pinned only to read legacy installations during the offline migration. Run `vibe-memory migrate-postgres` before enabling PostgreSQL on an existing deployment; see the [migration procedure](docs/self-hosting.md#legacy-kuzusqlite-migration). No Cloudflare service is required for self-hosting; the hosted website uses an optional private Worker/Tunnel bridge.

## Contributing and license

See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), and the [issue templates](.github/ISSUE_TEMPLATE).

Project code is licensed under [MIT](LICENSE). Third-party brand assets and the bundled Noto font retain their original rights; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
