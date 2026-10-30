#!/usr/bin/env python3
"""Compatibility bootstrap for the native Rust Vibe Memory CLI."""

import hashlib
import json
import os
import platform
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "https://github.com/vibememory/cli"


def config_path():
    base = os.environ.get("APPDATA") if os.name == "nt" else os.environ.get("XDG_CONFIG_HOME")
    return (Path(base) if base else Path.home() / ".config") / "vibe-memory" / "client.json"


def origin():
    saved = {}
    path = config_path()
    if path.is_file():
        saved = json.loads(path.read_text(encoding="utf-8"))
    base = (os.environ.get("MEMORY_URL") or saved.get("url") or "https://vibememory.io").rstrip("/")
    parsed = urlsplit(base)
    if (
        parsed.scheme not in ("http", "https")
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path
    ):
        raise ValueError("Invalid Vibe Memory service origin")
    if parsed.scheme == "http" and parsed.hostname not in ("127.0.0.1", "localhost", "::1"):
        raise ValueError("HTTPS is required except on localhost")
    return base


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def read_response(response, limit):
    length = response.headers.get("Content-Length")
    if length and int(length) > limit:
        raise ValueError("CLI distribution exceeds size limit")
    data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError("CLI distribution exceeds size limit")
    return data


def fetch_manifest(base):
    request = urllib.request.Request(
        base + "/skills/vibe-memory/manifest.json",
        headers={"Cache-Control": "no-cache", "User-Agent": "VibeMemoryBootstrap/3.0"},
    )
    with urllib.request.build_opener(NoRedirect).open(request, timeout=20) as response:
        return json.loads(read_response(response, 65536))


def fetch_release(url):
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "github.com"
        or parsed.username
        or parsed.password
        or not parsed.path.startswith("/vibememory/cli/releases/download/")
    ):
        raise ValueError("Unsupported native CLI URL")
    request = urllib.request.Request(url, headers={"User-Agent": "VibeMemoryBootstrap/3.0"})
    with urllib.request.urlopen(request, timeout=120) as response:
        final = urlsplit(response.geturl())
        if final.scheme != "https" or final.hostname not in (
            "github.com",
            "release-assets.githubusercontent.com",
        ):
            raise ValueError("Native CLI download redirected to an unsupported origin")
        return read_response(response, 64 * 1024 * 1024)


def platform_target():
    machine = platform.machine().lower()
    architecture = {
        "amd64": "x86_64",
        "x86_64": "x86_64",
        "arm64": "aarch64",
        "aarch64": "aarch64",
    }.get(machine)
    if not architecture:
        raise ValueError("Unsupported CPU architecture: " + machine)
    if sys.platform.startswith("linux"):
        system = "linux"
    elif sys.platform == "darwin":
        system = "macos"
    elif sys.platform == "win32":
        system = "windows"
    else:
        raise ValueError("Unsupported operating system: " + sys.platform)
    return system + "-" + architecture


def executable_path():
    return ROOT / "bin" / ("vibe-memory.exe" if os.name == "nt" else "vibe-memory")


def validate_native(manifest):
    native = manifest.get("native_cli", {})
    version = native.get("version", "")
    if (
        native.get("repository") != REPOSITORY
        or not version
        or any(character not in "0123456789." for character in version)
    ):
        raise ValueError("Unsupported native CLI manifest")
    target_name = platform_target()
    target = native.get("targets", {}).get(target_name)
    if not isinstance(target, dict):
        raise ValueError(
            "No prebuilt CLI for "
            + target_name
            + "; build https://github.com/vibememory/cli from source"
        )
    digest = target.get("sha256", "")
    url = target.get("url", "")
    prefix = REPOSITORY + "/releases/download/v" + version + "/vibe-memory-"
    if (
        len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
        or not url.startswith(prefix)
        or "/" in url.removeprefix(prefix)
    ):
        raise ValueError("Invalid native CLI target")
    return digest, url


def ensure_cli():
    manifest = fetch_manifest(origin())
    digest, url = validate_native(manifest)
    target = executable_path()
    if target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest() == digest:
        return target
    data = fetch_release(url)
    if hashlib.sha256(data).hexdigest() != digest:
        raise ValueError("Native CLI checksum mismatch; existing CLI preserved")
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as temporary:
        temporary.write(data)
        temporary_path = Path(temporary.name)
    try:
        temporary_path.chmod(0o755)
        if os.name == "nt" and target.exists():
            target.unlink()
        temporary_path.replace(target)
    finally:
        temporary_path.unlink(missing_ok=True)
    return target


def main():
    cli = ensure_cli()
    os.execv(str(cli), [str(cli), *sys.argv[1:]])


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, urllib.error.URLError, json.JSONDecodeError) as error:
        print(f"Vibe Memory: {error}", file=sys.stderr)
        sys.exit(1)
