#!/usr/bin/env python3
"""Write SHA-256 checksums for an already-created backup directory."""
import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument(
        "--verify", action="store_true", help="verify the existing manifest without changing it"
    )
    args = parser.parse_args()
    files = {
        str(path.relative_to(args.directory)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(args.directory.rglob("*"))
        if path.is_file() and path.name != "manifest.json"
    }
    manifest_path = args.directory / "manifest.json"
    if args.verify:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected = manifest.get("files")
        if manifest.get("format") != "vibe-memory-backup-manifest" or expected != files:
            raise SystemExit("Backup manifest verification failed")
        print(json.dumps({"verified": True, "files": len(files)}, indent=2))
        return
    manifest = {
        "format": "vibe-memory-backup-manifest",
        "version": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "files": files,
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
