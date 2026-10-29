"""Package only the distributable agent skill, never server data or credentials."""
from pathlib import Path
import zipfile

root = Path(__file__).resolve().parents[2]
source = root / 'skills/vibe-memory'
output = root / 'landing/dist/downloads/vibe-memory-skill.zip'
output.parent.mkdir(parents=True, exist_ok=True)
allowed = [source / 'SKILL.md', source / 'scripts/memory.py']
with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
    for path in allowed:
        archive.write(path, arcname=str(Path('vibe-memory') / path.relative_to(source)))
print('Packaged Vibe Memory skill (2 source files, no credentials).')
