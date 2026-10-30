"""Publish a reproducible, content-addressed skill release without credentials."""

import hashlib
import json
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parents[2]
source = root / "skills/vibe-memory"
web = root / "landing/dist"
tracked = ["SKILL.md", "scripts/memory.py"]  # Kept stable for v1 updater compatibility.
contents = {name: (source / name).read_bytes() for name in tracked}
files = {name: hashlib.sha256(contents[name]).hexdigest() for name in tracked}
native_cli = json.loads((source / "native-cli.json").read_text())
legacy_cli = {
    "path": "bin/vibe-memory",
    "sha256": "3b63ccadfdde76a6af0c2de4389f23af8ef181fe3f03f8d63989ed0f3482b126",
    "url": "/skills/vibe-memory/cli/3b63ccadfdde76a6af0c2de4389f23af8ef181fe3f03f8d63989ed0f3482b126/vibe-memory",
}
legacy_path = web / legacy_cli["url"].removeprefix("/")
if hashlib.sha256(legacy_path.read_bytes()).hexdigest() != legacy_cli["sha256"]:
    raise ValueError("Legacy CLI artifact is missing or corrupt")
revision = hashlib.sha256(
    json.dumps(files, sort_keys=True, separators=(",", ":")).encode()
).hexdigest()
release = web / "skills/vibe-memory/releases" / revision
for name, data in contents.items():
    for directory in (web / "skills/vibe-memory", release):
        destination = directory / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
output = web / "downloads/vibe-memory-skill.zip"
output.parent.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
    for name, data in contents.items():
        info = zipfile.ZipInfo("vibe-memory/" + name, date_time=(2026, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o100644 << 16
        archive.writestr(info, data)
archive_sha256 = hashlib.sha256(output.read_bytes()).hexdigest()
manifest = {
    "schema_version": 1,
    "revision": revision,
    "files": files,
    "release_assets": {
        "SKILL.md": "SKILL.md",
        "scripts/memory.py": "memory.py",
    },
    "cli": legacy_cli,
    "native_cli": native_cli,
    "archive": "/downloads/vibe-memory-skill.zip",
    "archive_sha256": archive_sha256,
    "official_archive_mirror": (
        "https://github.com/vibememory/vibememory/releases/latest/download/"
        "vibe-memory-skill.zip"
    ),
    "official_manifest_mirror": (
        "https://github.com/vibememory/vibememory/releases/latest/download/manifest.json"
    ),
}
(web / "skills/vibe-memory/manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("Published skill revision " + revision)
