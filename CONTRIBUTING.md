# Contributing

Vibe Memory welcomes bug reports, documentation improvements, tests, and focused pull requests.

## Local setup

```sh
uv sync --frozen
cp .env.example .env
uv run vibe-memory serve
```

Open http://localhost:8080. Keep your local `.env`, databases, uploaded files, and generated API keys out of commits. Tests use temporary directories; do not run ad hoc test writes against another person's service.

## Design contract

- The connected agent performs entity/relationship inference, file analysis, keyword extraction, and RAG construction.
- The server embeds only explicitly supplied keywords, never raw documents, titles, or summaries.
- Every data read and write is scoped to the authenticated owner. Invalid explicit Bearer keys never fall back to a browser session.
- Uploads are opaque byte streams, not multipart forms or base64 JSON.
- Retries and failure paths must not silently duplicate or partially persist data.
- The default self-hosted console and API work on one origin without Cloudflare.

## Checks

```sh
uv run ruff check src ops tests scripts skills/vibe-memory/scripts
uv run pytest -q
uv build
```

Changes to container/runtime packaging should also pass:

```sh
docker compose build
docker compose up -d
uv run python scripts/selfhost_smoke.py
```

The smoke test creates isolated QA users on its target service; use a disposable development volume. Never use `docker compose down -v` on a volume containing data you want to keep.

For frontend changes, edit the Next.js App Router source in `landing/app/`, its shared components, or the browser assets in `landing/public/`. The preserved page bodies live in `landing/templates/` while the interface is migrated incrementally. Run `npm --prefix landing run build`; it creates the static export in `landing/dist/` for both self-hosting and Cloudflare. Do not edit generated files in `landing/dist/` directly. `python3 landing/scripts/package_skill.py` refreshes the downloadable skill. `landing/scripts/verify_site.py` checks the public presentation; `verify_console.py` creates QA accounts and exercises real data operations. Browser tests require Playwright Chromium and OS libraries.

## Pull requests

Explain the user-visible change, link any related issue, and list checks you actually ran. Keep changes focused and document migrations or changed API behavior. Do not claim that a deployment, container build, or test passed without observing its result.
