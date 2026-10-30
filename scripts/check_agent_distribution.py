#!/usr/bin/env python3
"""Verify the public agent distribution with a generic non-browser client."""

import argparse
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

DEFAULT_RELEASE = "https://github.com/vibememory/vibememory/releases/latest/download"


def fetch(url, limit):
    """Use urllib's ordinary non-browser identity intentionally."""
    try:
        with urlopen(url, timeout=30) as response:
            data = response.read(limit + 1)
            if len(data) > limit:
                raise ValueError(f"response exceeds {limit} bytes")
            return response.status, response.geturl(), data
    except HTTPError as error:
        body = error.read(1024).decode("utf-8", "replace").strip()
        if error.code == 403 and "error code: 1010" in body.casefold():
            raise RuntimeError(
                "Cloudflare 1010 rejected the generic client signature before the Worker. "
                "Use the official GitHub release mirror or add a path-scoped Browser "
                "Integrity Check exception; do not disable TLS verification or site-wide security."
            ) from error
        raise RuntimeError(f"download failed with HTTP {error.code}: {body}") from error
    except URLError as error:
        raise RuntimeError(f"download failed: {error.reason}") from error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", default=DEFAULT_RELEASE, help="Release asset base URL")
    parser.add_argument(
        "--run-bootstrap",
        action="store_true",
        help="Extract the archive and run its verified native CLI bootstrap",
    )
    args = parser.parse_args()
    release = args.release.rstrip("/")

    _, archive_url, archive = fetch(release + "/vibe-memory-skill.zip", 16 * 1024 * 1024)
    _, manifest_url, manifest_bytes = fetch(release + "/manifest.json", 256 * 1024)
    manifest = json.loads(manifest_bytes)
    archive_digest = hashlib.sha256(archive).hexdigest()
    if archive_digest != manifest.get("archive_sha256"):
        raise RuntimeError("Skill archive SHA-256 does not match manifest.json")

    with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
        expected = {"vibe-memory/SKILL.md", "vibe-memory/scripts/memory.py"}
        if set(bundle.namelist()) != expected:
            raise RuntimeError("Skill archive contains unexpected files")
        for relative, digest in manifest.get("files", {}).items():
            content = bundle.read("vibe-memory/" + relative)
            if hashlib.sha256(content).hexdigest() != digest:
                raise RuntimeError(f"Skill file checksum mismatch: {relative}")

    print(f"PASS generic archive download {archive_url}")
    print(f"PASS generic manifest download {manifest_url}")
    print(f"PASS archive SHA-256 {archive_digest}")
    print("PASS archive contents and per-file SHA-256")

    if args.run_bootstrap:
        with tempfile.TemporaryDirectory(prefix="vibe-memory-distribution-") as directory:
            root = Path(directory)
            with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
                bundle.extractall(root)
            environment = os.environ.copy()
            environment["XDG_CONFIG_HOME"] = str(root / "config")
            result = subprocess.run(
                [sys.executable, str(root / "vibe-memory/scripts/memory.py"), "--version"],
                check=True,
                capture_output=True,
                text=True,
                timeout=180,
                env=environment,
            )
            if "vibe-memory " not in result.stdout:
                raise RuntimeError("native CLI bootstrap returned an unexpected version response")
            cli = root / "vibe-memory/bin/vibe-memory"
            if os.name == "nt":
                cli = cli.with_suffix(".exe")
            login_help = subprocess.run(
                [str(cli), "login", "--help"],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
                env=environment,
            ).stdout
            if "--no-browser" not in login_help or "--approval-timeout" not in login_help:
                raise RuntimeError("native CLI is missing browser-approval login options")
            print("PASS native CLI download, checksum verification, and startup")
            print("PASS browser-approval login command is available")

    return 0


if __name__ == "__main__":
    sys.exit(main())
