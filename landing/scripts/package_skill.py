"""Publish a reproducible, content-addressed skill release without credentials."""

import hashlib
import json
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parents[2]
source = root / "skills/vibe-memory"
web = root / "landing/dist"
tracked = ["SKILL.md", "scripts/memory.py"]  # Kept stable for v1 updater compatibility.
cli_name = "bin/vibe-memory"
allowed = [*tracked, cli_name]
contents = {name: (source / name).read_bytes() for name in allowed}
files = {name: hashlib.sha256(contents[name]).hexdigest() for name in tracked}
cli_digest = hashlib.sha256(contents[cli_name]).hexdigest()
revision = hashlib.sha256(
    json.dumps(files, sort_keys=True, separators=(",", ":")).encode()
).hexdigest()
release = web / "skills/vibe-memory/releases" / revision
for name, data in contents.items():
    for directory in (web / "skills/vibe-memory", release):
        destination = directory / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
cli_url = "/skills/vibe-memory/cli/" + cli_digest + "/vibe-memory"
cli_output = web / cli_url.removeprefix("/")
cli_output.parent.mkdir(parents=True, exist_ok=True)
cli_output.write_bytes(contents[cli_name])
manifest = {
    "schema_version": 1,
    "revision": revision,
    "files": files,
    "cli": {"path": cli_name, "sha256": cli_digest, "url": cli_url},
    "archive": "/downloads/vibe-memory-skill.zip",
}
(web / "skills/vibe-memory/manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
output = web / "downloads/vibe-memory-skill.zip"
output.parent.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
    for name, data in contents.items():
        info = zipfile.ZipInfo("vibe-memory/" + name, date_time=(2026, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = (0o100755 if name == cli_name else 0o100644) << 16
        archive.writestr(info, data)
print("Published skill revision " + revision)
