import argparse
import json
import secrets


def main():
    parser = argparse.ArgumentParser(description="Vibe Memory service")
    sub = parser.add_subparsers(dest="command", required=True)
    key = sub.add_parser("keygen", help="Generate configuration for an agent API key")
    key.add_argument("--user", default="personal")
    sub.add_parser("serve", help="Run the authenticated memory service")
    sub.add_parser("warmup", help="Download and initialize the local embedding model")
    args = parser.parse_args()
    if args.command == "keygen":
        print(json.dumps({secrets.token_urlsafe(36): args.user}))
    elif args.command == "warmup":
        from .config import Settings
        from .embeddings import Embedder

        settings = Settings()
        model = Embedder(settings.embedding_model, settings.embedding_cache)
        print(f"Ready: {model.model_name} ({len(model.keywords(['기억'])[0])} dimensions)")
    else:
        import uvicorn

        from .app import create_app
        from .config import Settings

        settings = Settings()
        uvicorn.run(create_app(settings), host=settings.host, port=settings.port)
