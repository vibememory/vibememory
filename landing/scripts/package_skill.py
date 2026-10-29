"""Publish a reproducible, content-addressed skill release without credentials."""
import hashlib
import json
from pathlib import Path
import zipfile

root = Path(__file__).resolve().parents[2]
source = root / 'skills/vibe-memory'
web = root / 'landing/dist'
allowed = ['SKILL.md', 'scripts/memory.py']
contents = {name: (source / name).read_bytes() for name in allowed}
files = {name: hashlib.sha256(data).hexdigest() for name, data in contents.items()}
revision = hashlib.sha256(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
release = web / 'skills/vibe-memory/releases' / revision
for name, data in contents.items():
    for directory in (web / 'skills/vibe-memory', release):
        destination = directory / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
manifest = {'schema_version': 1, 'revision': revision, 'files': files,
            'archive': '/downloads/vibe-memory-skill.zip'}
(web / 'skills/vibe-memory/manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
output = web / 'downloads/vibe-memory-skill.zip'
output.parent.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
    for name, data in contents.items():
        info = zipfile.ZipInfo('vibe-memory/' + name, date_time=(2026, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o100644 << 16
        archive.writestr(info, data)
print('Published skill revision ' + revision)
