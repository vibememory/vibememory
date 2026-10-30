"""Overlay the Next.js static export onto the self-hosted and Cloudflare web bundle."""

import shutil
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
exported = root / "out"
destination = root / "dist"

required = [
    "index.html",
    "login.html",
    "connect.html",
    "console.html",
    "guide.html",
    "support.html",
    "404.html",
]
missing = [name for name in required if not (exported / name).is_file()]
if missing:
    raise RuntimeError("Next.js export is incomplete: " + ", ".join(missing))

next_assets = destination / "_next"
if next_assets.exists():
    shutil.rmtree(next_assets)
shutil.copytree(exported, destination, dirs_exist_ok=True)

subprocess.run([sys.executable, str(root / "scripts/package_skill.py")], check=True)
print("Finalized Next.js export in " + str(destination))
