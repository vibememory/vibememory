"""Copy pinned browser dependencies into the self-hosted static asset bundle."""

import shutil
from pathlib import Path


root = Path(__file__).resolve().parents[1]
package = root / "node_modules" / "cytoscape"
destination = root / "public" / "assets" / "vendor"

source = package / "dist" / "cytoscape.min.js"
license_file = package / "LICENSE"
if not source.is_file() or not license_file.is_file():
    raise RuntimeError("Cytoscape.js is missing; run the dependency installer first")

destination.mkdir(parents=True, exist_ok=True)
shutil.copy2(source, destination / "cytoscape.min.js")
shutil.copy2(license_file, destination / "cytoscape-LICENSE.txt")
print("Packaged Cytoscape.js browser runtime")
