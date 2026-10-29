# Self-hosting Vibe Memory

The console, login, REST endpoints, graph, local keyword embeddings, and file storage run together. Cloudflare is optional and is not part of the Docker Compose quick start.

## Requirements

- Linux amd64 with Docker Engine and Compose v2, or Python 3.12/3.13 with uv for source installs.
- Persistent disk for user data and the model cache; about 220 MB is downloaded for the default model.
- Network access for dependencies during build and for the first embedding-model download. After the model is cached, keyword embeddings run locally.

Other OS/CPU combinations are not claimed as container-tested. Embedded Kuzu/ONNX wheels and container base images must support the target architecture.

## Docker Compose

```sh
git clone https://github.com/vibememory/vibememory.git
cd vibememory
cp .env.example .env
docker compose up -d --build
```

Open http://localhost:8080, create an account, and issue an agent key in the console. There is no default account or password. Browser credentials and agent Bearer keys are separate.

`docker compose exec app vibe-memory warmup` downloads/initializes the model before the first memory write. Until it is needed, authentication, lists, file byte uploads, and feature requests do not load an embedding model.

## Configuration

| Variable | Default | Meaning |
| --- | --- | --- |
| `MEMORY_PUBLIC_ORIGIN` | `http://localhost:8080` in Compose | Exact browser origin for cookie security and CSRF checks |
| `MEMORY_BIND_ADDRESS` | `127.0.0.1` | Compose host-side bind address |
| `MEMORY_HTTP_PORT` | `8080` | Compose host-side port |
| `MEMORY_SIGNUP_ENABLED` | `true` | Accept new accounts; set `false` after creating your accounts if desired |
| `MEMORY_UPLOAD_MAX_BYTES` | `104857600` | Raw upload size limit (100 MiB) |
| `MEMORY_API_KEYS` | `{}` | Optional source-install legacy key-to-user mapping; not required for console-issued keys |
| `MEMORY_DATA_DIR` | `/data` in Docker | Graph, auth DB, and uploads |
| `MEMORY_EMBEDDING_CACHE` | `/data/models` in Docker | Persistent local model cache |
| `MEMORY_EMBEDDING_MODEL` | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | Local keyword model |
| `MEMORY_WEB_DIR` | bundled assets | Optional explicit directory containing index.html and console assets |

When using `http://127.0.0.1:8080`, set `MEMORY_PUBLIC_ORIGIN` to that value; it differs from `http://localhost:8080`. A mismatched origin causes 403 on browser writes. Remote deployments should use HTTPS, which enables Secure session cookies. Changing `MEMORY_HTTP_PORT` also requires updating the public origin.

Compose intentionally passes only the supported application configuration and persists data in one named volume. It does not pass arbitrary host credentials into the container. The image runs as UID/GID 10001 with a read-only root filesystem and writable data/tmp locations. If replacing the named volume with a host bind mount, make that directory writable by UID/GID 10001.

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

## Source installation

```sh
uv sync --frozen
cp .env.example .env
uv run vibe-memory serve
```

The maintained `landing/dist/` assets are served directly. Built wheels bundle those same assets under the Python package, so an installed wheel also includes login and the console. Node.js is only needed for optional Cloudflare deployment tooling, not for serving the self-hosted app.

For an explicit directory, set `MEMORY_WEB_DIR=/absolute/path/to/web-assets`; startup rejects an invalid directory instead of silently serving a broken console.

## Data and backups

The `memory_data` named volume contains:

- `graph`: Kuzu graph, keyword vectors, relation history, and feature requests.
- `auth.sqlite` and SQLite WAL files: accounts, sessions, and hashed agent keys.
- `files/`: uploaded originals.
- `models/` and `cache/`: embedding model/download cache.

Stop the app before taking a filesystem backup so the embedded databases are consistent:

```sh
docker compose stop app
docker compose run --rm -T --no-deps --entrypoint python app -c \
  "import sys,tarfile; t=tarfile.open(fileobj=sys.stdout.buffer,mode='w|gz'); t.add('/data',arcname='data'); t.close()" \
  > vibe-memory-backup.tar.gz
docker compose start app
```

Keep the backup private; it contains personal records and authentication data. If the backup command fails, restart the app and resolve the failure rather than treating a partial archive as a backup.

Restore into an **empty deployment's data volume**, with its app stopped:

```sh
docker compose run --rm -T --no-deps --entrypoint python app -c \
  "import sys,tarfile; t=tarfile.open(fileobj=sys.stdin.buffer,mode='r|gz'); t.extractall('/',filter='data')" \
  < vibe-memory-backup.tar.gz
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

Run only one API process per graph directory; do not add `--workers` or scale the app service. The embedding model is recorded in the graph: changing it without rebuilding the keyword index is rejected. The first import of old full-content indexes removes derived chunk vectors, preserves source records and semantic relationships, and waits for agent-supplied keywords to reindex them.

## Hosted Cloudflare bridge (optional)

The public `vibememory.io` deployment uses a Worker and a private Tunnel/VPC binding. Its account IDs, actual route configuration, tunnel state, and credentials are not distributed in the repository.

To configure your own deployment, copy `landing/wrangler.example.jsonc` to `landing/wrangler.jsonc`, set your own account/domain configuration, authenticate Wrangler, then run `python3 ops/cloudflare_origin.py setup`. The setup helper reuses or creates only the dedicated `vibe-memory-api` tunnel and adds the private binding. `run` reads a tunnel execution token through native Cloudflare auth without printing it. Those operations need the relevant account permissions and a continuously running API host.

For most self-hosters, the single container plus an HTTPS reverse proxy is sufficient.

### Live skill distribution

Every installation serves its current skill at `/skills/vibe-memory/SKILL.md`,
its SHA-256 revision manifest at `/skills/vibe-memory/manifest.json`, and the
install ZIP at `/downloads/vibe-memory-skill.zip`. These public endpoints send
`Cache-Control: no-store`; they contain no account data or credentials.

Agents run `python3 scripts/memory.py sync` at the beginning of each task and
reread the instructions after an update. Every helper operation also checks for
updates and stops before the operation if instructions changed. A failed update
check stops the operation. Updating the service deployment publishes the skill
immediately; existing agent installations pick it up on their next check.
Self-hosted installations distribute their own deployed version, without
fetching instructions from the hosted service or GitHub at runtime.

After editing `skills/vibe-memory`, run `python3 landing/scripts/package_skill.py`
and commit the generated web files with the source. CI rejects stale artifacts.
`npm --prefix landing run deploy` regenerates these artifacts before publishing.

### Agent CLI authentication

The skill ZIP bundles a standalone standard-library Python CLI. Run
`python3 scripts/memory.py configure` in your interactive terminal, enter this
installation's origin and paste the API key into the hidden prompt. It verifies
`/v1/me` before saving credentials outside the skill directory. Run `status` to
verify access, `sync` to refresh the skill, and `logout` to remove local settings.
On Windows use `py scripts/memory.py` if appropriate. Server dependencies and
embedding models are not needed on the agent machine.

Configuration is plaintext JSON at `$XDG_CONFIG_HOME/vibe-memory/client.json`
(default `~/.config/vibe-memory/client.json`) or `%APPDATA%/vibe-memory/client.json`
on Windows; Unix files have mode 0600. Use environment-injected credentials if
local persistence is unsuitable. Environment variables override saved settings;
a saved key is never sent to a different origin selected by `MEMORY_URL` alone.
Local logout does not revoke a server key or remove environment variables.
