# Self-hosting Vibe Memory

The console, login, REST endpoints, graph, local keyword embeddings, and file storage run together. Cloudflare is optional and is not part of the Docker Compose quick start.

## Requirements

- Linux amd64 with Docker Engine and Compose v2, or Python 3.12/3.13 with uv for source installs.
- Persistent disk for PostgreSQL, uploaded files, the Vault/OTP encryption key, and the model cache; about 220 MB is downloaded for the default model.
- Network access for dependencies during build and for the first embedding-model download. After the model is cached, keyword embeddings run locally.

Other OS/CPU combinations are not claimed as container-tested. PostgreSQL/pgvector, ONNX wheels, and container base images must support the target architecture.

## Docker Compose

```sh
git clone https://github.com/vibememory/vibememory.git
cd vibememory
cp .env.example .env
docker compose up -d --build
```

Open http://localhost:8080, create an account, and issue an agent key in the console. There is no default account or password. Browser credentials and agent Bearer keys are separate.

Compose starts `pgvector/pgvector:0.8.7-pg17` and waits for it to become healthy before starting the app. Change `POSTGRES_PASSWORD` in `.env` before exposing the deployment; use URL-safe random characters because Compose also places it in the application connection URL.

For ChatGPT or Claude remote MCP connections, expose the deployment through HTTPS and add `https://your-domain.example/mcp` as a custom MCP server/connector. The client follows the server's OAuth discovery metadata and redirects the user back to the Vibe Memory login and consent screen. Local plain-HTTP MCP development is limited to explicit localhost loopback redirect URIs; hosted clients require a publicly reachable HTTPS origin.

`docker compose exec app vibe-memory warmup` downloads/initializes the model before the first memory write. Until it is needed, authentication, lists, file byte uploads, and feature requests do not load an embedding model.

## Configuration

| Variable | Default | Meaning |
| --- | --- | --- |
| `MEMORY_PUBLIC_ORIGIN` | `http://localhost:8080` in Compose | Exact browser origin for cookie security and CSRF checks |
| `MEMORY_HSTS_ENABLED` | `true` | Send HSTS when the request is HTTPS or arrived through an HTTPS proxy |
| `MEMORY_HSTS_MAX_AGE` | `31536000` | HSTS max-age in seconds (`0` explicitly clears it) |
| `MEMORY_HSTS_INCLUDE_SUBDOMAINS` | `true` | Add `includeSubDomains`; make every subdomain HTTPS-ready first |
| `MEMORY_HSTS_PRELOAD` | `false` | Add the preload token; only enable after meeting browser preload requirements |
| `MEMORY_PUBLIC_OPENAPI_INCLUDE_ADMIN` | `false` | Include browser-admin routes in OpenAPI; routes still require an admin session either way |
| `MEMORY_BIND_ADDRESS` | `127.0.0.1` | Compose host-side bind address |
| `MEMORY_HTTP_PORT` | `8080` | Compose host-side port |
| `MEMORY_SIGNUP_ENABLED` | `true` | Accept new accounts; set `false` after creating your accounts if desired |
| `MEMORY_ADMIN_EMAILS` | `[]` | JSON array of browser-login emails allowed to access `/admin`; agent keys are never administrators |
| `MEMORY_UPLOAD_MAX_BYTES` | `104857600` | Raw upload size limit (100 MiB) |
| `POSTGRES_DB` | `vibe_memory` | Compose PostgreSQL database name |
| `POSTGRES_USER` | `vibe_memory` | Compose PostgreSQL role |
| `POSTGRES_PASSWORD` | required | Compose PostgreSQL password; replace the example value |
| `MEMORY_DATABASE_URL` | set by Compose | PostgreSQL connection URL for source installations |
| `MEMORY_DATABASE_POOL_SIZE` | `10` | Maximum application database connections |
| `MEMORY_EMBEDDING_DIMENSION` | `384` | pgvector dimension; must match the configured model |
| `MEMORY_API_KEYS` | `{}` | Optional source-install legacy key-to-user mapping; not required for console-issued keys |
| `MEMORY_DATA_DIR` | `/data` in Docker | Uploaded files, Vault key, and model/cache data |
| `MEMORY_VAULT_KEY_FILE` | `<data dir>/vault.key` | Persistent 32-byte Vault and TOTP encryption-key file; generated with mode 0600 |
| `MEMORY_EMBEDDING_CACHE` | `/data/models` in Docker | Persistent local model cache |
| `MEMORY_EMBEDDING_MODEL` | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | Local keyword model |
| `MEMORY_WEB_DIR` | bundled assets | Optional explicit directory containing index.html and console assets |

When using `http://127.0.0.1:8080`, set `MEMORY_PUBLIC_ORIGIN` to that value; it differs from `http://localhost:8080`. A mismatched origin causes 403 on browser writes. Remote deployments should use HTTPS, which enables Secure session cookies. Changing `MEMORY_HTTP_PORT` also requires updating the public origin.

To enable the feature-request operations page, configure an existing login email and restart the app:

```dotenv
MEMORY_ADMIN_EMAILS=["owner@example.com"]
```

That browser account can open `/admin` and process requests across workspaces. Normal browser accounts can only read their own requests, and API keys, CLI agents, and MCP clients never receive administrator access.

Compose intentionally passes only the supported application configuration and persists PostgreSQL and app files in separate named volumes. It does not pass arbitrary host credentials into the container. The image runs as UID/GID 10001 with a read-only root filesystem and writable data/tmp locations. If replacing the app named volume with a host bind mount, make that directory writable by UID/GID 10001.

## HTTPS with Caddy

Point a domain you control to the host and allow inbound ports 80/443. Set in `.env`:

```dotenv
MEMORY_PUBLIC_ORIGIN=https://memory.example.com
CADDY_DOMAIN=memory.example.com
```

Then run:

```sh
docker compose -f compose.yaml -f compose.https.yaml up -d --build
```

The included Caddy configuration terminates TLS and forwards requests to `app:8080`. The application's direct port remains bound to localhost by default. No Cloudflare login is involved.

Run the local posture check after every deployment. It makes direct HTTP/DNS
queries and sends no data to a scanner service:

```sh
python scripts/check_deployment.py https://memory.example.com
```

It verifies HSTS, the `www` (or `--www-host`) response/redirect, absence of
admin routes from public OpenAPI, and DMARC when `dig` is installed. Configure
the secondary hostname before enabling `includeSubDomains`. For mail DNS, start
with a monitored `v=DMARC1; p=none` policy, then raise it to `quarantine` or
`reject` after validating legitimate senders.

## Source installation

Create an empty PostgreSQL database, install the `vector` extension as a privileged database user, and set its connection URL. The application creates its own tables but does not create database roles or databases.

```sh
uv sync --frozen
cp .env.example .env
# In .env:
# MEMORY_DATABASE_URL=postgresql://vibe_memory:password@127.0.0.1:5432/vibe_memory
uv run vibe-memory serve
```

The website and console use the Next.js App Router under `landing/app/`. `npm --prefix landing run build` creates the static export in `landing/dist/`; the server never needs a Node.js process at runtime. Built wheels bundle that export under the Python package, so an installed wheel also includes login and the console. A normal self-hosted installation uses the prebuilt assets and does not need Node.js.

For an explicit directory, set `MEMORY_WEB_DIR=/absolute/path/to/web-assets`; startup rejects an invalid directory instead of silently serving a broken console.

## Data and backups

PostgreSQL is the source of truth for accounts, sessions, API keys, OAuth/MCP state, records, keyword vectors, relationships, change events, feature requests, and Vault ciphertext. The `postgres_data` named volume holds that database.

The separate `memory_data` named volume contains:

- `vault.key`: the 32-byte Vault and TOTP encryption key, created with mode 0600.
- `files/`: uploaded originals.
- `models/` and `cache/`: embedding model/download cache.

Old `graph`, `auth.sqlite`, and `vault.sqlite` entries can remain after a verified legacy migration, but the PostgreSQL-enabled app does not read them during normal operation.

Back up PostgreSQL with `pg_dump`, then archive the app volume. Stopping the app gives the dump and files one clear application-level cut point:

```sh
docker compose stop app
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' \
  > vibe-memory-postgres.dump
docker compose run --rm -T --no-deps --entrypoint python app -c \
  "import sys,tarfile; t=tarfile.open(fileobj=sys.stdout.buffer,mode='w|gz'); t.add('/data',arcname='data'); t.close()" \
  > vibe-memory-files.tar.gz
docker compose start app
```

Keep both files private and together for recovery. The database dump contains personal records, authentication data, encrypted TOTP secrets, and Vault ciphertext; the file archive contains uploaded originals and the key capable of decrypting Vault entries and TOTP secrets. If `MEMORY_VAULT_KEY_FILE` points outside `/data`, back up that key separately and restore the exact same key. Losing the key makes Vault values unrecoverable and prevents TOTP verification unless a recovery code remains; obtaining both the key and ciphertext reveals the encrypted values.

Restore into an **empty deployment**, with its app stopped. Start only PostgreSQL, restore its dump, then restore the app volume:

```sh
docker compose up -d db
docker compose exec -T db sh -c \
  'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists' \
  < vibe-memory-postgres.dump
docker compose run --rm -T --no-deps --entrypoint python app -c \
  "import sys,tarfile; t=tarfile.open(fileobj=sys.stdin.buffer,mode='r|gz'); t.extractall('/',filter='data')" \
  < vibe-memory-files.tar.gz
docker compose up -d
```

Do not restore over a running app. Keep the previous data volume until the restored deployment is verified.

## Upgrade and maintenance

Back up first, then:

```sh
git pull --ff-only
docker compose up -d --build
```

`docker compose down` preserves the named volume. **`docker compose down -v` deletes it.** Do not use `-v` for a normal upgrade.

The embedding model and dimension are recorded in PostgreSQL. Changing either without rebuilding the keyword index is rejected. Search currently performs exact owner-scoped cosine distance with pgvector; no HNSW/IVFFlat index is created by default.

## Legacy Kuzu/SQLite migration

Version 0.9 moves all structured data from the embedded Kuzu/SQLite layout to PostgreSQL. This is an offline, one-time migration into an empty destination. Keep the old data volume and a backup until verification is complete.

First inspect the source without writing anything:

```sh
vibe-memory migrate-postgres --data-dir /path/to/legacy/data
```

Then stop every old API process so Kuzu and SQLite are no longer changing. Create an empty pgvector database, back up the source, and apply:

```sh
vibe-memory migrate-postgres \
  --data-dir /path/to/legacy/data \
  --database-url 'postgresql://vibe_memory:password@127.0.0.1:5432/vibe_memory' \
  --apply
```

The command imports accounts, sessions, keys, OTP state and recovery-code hashes, OAuth state, records, keyword embeddings, relations, events, feature requests, and Vault ciphertext in one PostgreSQL transaction. It rejects a non-empty destination, a locked Kuzu database, embedding model/dimension mismatches, or count differences. Raw `files/`, `vault.key`, and model caches stay in the same app data directory and are not copied into PostgreSQL.

For an existing Compose installation, pull the new code, set the PostgreSQL variables in `.env`, and run:

```sh
docker compose stop app
docker compose build app
docker compose up -d db
docker compose run --rm app vibe-memory migrate-postgres --data-dir /data --apply
docker compose up -d app
```

Start the normal app only after the migration command reports verified counts. If verification fails, the PostgreSQL transaction rolls back; keep serving the prior version from the untouched legacy volume until the cause is resolved.

## Hosted Cloudflare bridge (optional)

The public `vibememory.io` deployment uses a Worker and a private Tunnel/VPC binding. Its account IDs, actual route configuration, tunnel state, and credentials are not distributed in the repository.

To configure your own deployment, copy `landing/wrangler.example.jsonc` to `landing/wrangler.jsonc`, set your own account/domain configuration, authenticate Wrangler, then run `python3 ops/cloudflare_origin.py setup`. The setup helper reuses or creates only the dedicated `vibe-memory-api` tunnel and adds the private binding. `run` reads a tunnel execution token through native Cloudflare auth without printing it. Those operations need the relevant account permissions and a continuously running API host.

For most self-hosters, the single container plus an HTTPS reverse proxy is sufficient.

### Live skill distribution

Every installation serves its current skill at `/skills/vibe-memory/SKILL.md`,
its SHA-256 revision manifest at `/skills/vibe-memory/manifest.json`, and the
install ZIP at `/downloads/vibe-memory-skill.zip`. These public endpoints send
`Cache-Control: no-store`; they contain no account data or credentials.

Agents run `python3 scripts/memory.py sync` at the beginning of each task. This
small compatibility bootstrap selects and verifies the current native Rust binary,
then executes its `sync` command. Agents reread the instructions after an update.
The compact CLI wraps API details and emits compact JSON by default. Every data
operation checks the Skill revision and stops before the operation if instructions
changed. A failed update check stops the operation. Updating the service deployment
publishes the Skill manifest immediately; existing installations pick it up on
their next check.
Self-hosted installations serve their own deployed Skill rather than fetching
instructions from the hosted service. The default manifest pins native binaries
to the public GitHub release; operators can replace those `native_cli` targets
with their own HTTPS release mirror before packaging.

`python3 scripts/memory.py ...` remains a compatibility bootstrap. It downloads
the matching Linux, macOS or Windows release binary, verifies its SHA-256 digest,
and forwards the command. All data API operations execute in Rust.
Standalone CLI source and releases are published at
[`vibememory/cli`](https://github.com/vibememory/cli); the server repository
retains the Skill instructions, compatibility bootstrap and pinned release hashes.

After editing `skills/vibe-memory`, run `python3 landing/scripts/package_skill.py`
and commit the generated web files with the source. CI rejects stale artifacts.
`npm --prefix landing run deploy` regenerates these artifacts before publishing.

### Browser approval for agent authentication

The agent runs `./bin/vibe-memory login --vault-access --no-browser --url https://YOUR_HOST
--name "Agent name"` in a background tool process and presents the generated link
and code to the user. The user signs in on the web, returns to the approval page,
and explicitly approves. The waiting CLI receives and saves a one-time agent key;
users do not copy keys or run terminal commands. On a local machine `login` can
open a browser automatically. The authorization request expires after 5 minutes.
Only the CLI holds the private polling code; the browser URL contains a separate
public confirmation code. Denial/expiry stops login. No arbitrary callback URLs
are accepted. This polling flow also works when the agent is on a remote host.
`--vault-access` is optional and appears as a separate sensitive permission on
the approval page. Existing and ordinary keys do not receive it automatically.

### Encrypted Vault

Users add, rotate, and delete values in the web console. Secret names and access
metadata are visible; stored values are never listed again. The server encrypts
each value with AES-256-GCM using a fresh 96-bit nonce and binds the ciphertext to
its account and name as authenticated data. Agent keys require an independent
Vault permission. Agent API calls can list metadata and retrieve a selected value,
but cannot create, replace, or delete entries.

Agents should use `vault exec --env VARIABLE=ENTRY -- PROGRAM ...`. The Rust CLI
retrieves the selected value, injects it into that one child process, and never
prints it. The child process can still expose its own environment or arguments,
so do not run diagnostic commands that print credentials. The CLI has no command
that prints a Vault value directly.

Client configuration is plaintext JSON at `$XDG_CONFIG_HOME/vibe-memory/client.json`
(default `~/.config/vibe-memory/client.json`) or `%APPDATA%/vibe-memory/client.json`
on Windows; Unix files have mode 0600. Run `status` to verify and `sync` to update
the skill. Environment variables override saved settings; a saved key is never
sent to another origin selected by `MEMORY_URL` alone. `logout` removes local
settings; revoke keys in the console to terminate server access. `configure` is
an optional manual-key fallback, not required for browser approval.
