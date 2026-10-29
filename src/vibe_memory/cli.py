import argparse
import json
import secrets
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Vibe Memory service")
    sub = parser.add_subparsers(dest="command", required=True)
    key = sub.add_parser("keygen", help="Generate configuration for an agent API key")
    key.add_argument("--user", default="personal")
    sub.add_parser("serve", help="Run the authenticated memory service")
    sub.add_parser("warmup", help="Download and initialize the local embedding model")
    migration = sub.add_parser(
        "migrate-postgres", help="Inspect or migrate legacy Kuzu/SQLite data to PostgreSQL"
    )
    migration.add_argument("--database-url")
    migration.add_argument("--data-dir")
    migration.add_argument(
        "--apply",
        action="store_true",
        help="Write to an empty PostgreSQL database; without this flag only inspect the source",
    )
    args = parser.parse_args()
    if args.command == "keygen":
        print(json.dumps({secrets.token_urlsafe(36): args.user}))
    elif args.command == "warmup":
        from .config import Settings
        from .embeddings import Embedder

        settings = Settings()
        model = Embedder(settings.embedding_model, settings.embedding_cache)
        print(f"Ready: {model.model_name} ({len(model.keywords(['기억'])[0])} dimensions)")
    elif args.command == "migrate-postgres":
        from .config import Settings
        from .migration import migrate_legacy, read_legacy, summary

        settings = Settings()
        data_dir = Path(args.data_dir) if args.data_dir else settings.data_dir
        if not args.apply:
            print(json.dumps({"mode": "dry-run", "source": summary(read_legacy(data_dir))}))
            return
        database_url = args.database_url or settings.database_url
        if not database_url:
            parser.error("--database-url or MEMORY_DATABASE_URL is required with --apply")
        result = migrate_legacy(
            data_dir,
            database_url,
            settings.embedding_model,
            settings.embedding_dimension,
            settings.database_pool_size,
        )
        print(json.dumps({"mode": "applied", "migrated": result}))
    else:
        import uvicorn

        from .app import create_app
        from .config import Settings

        settings = Settings()
        uvicorn.run(create_app(settings), host=settings.host, port=settings.port)
