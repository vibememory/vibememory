"""Copy pinned browser dependencies into the self-hosted static asset bundle."""

import shutil
import re
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

thai_font_package = root / "node_modules" / "@fontsource" / "noto-sans-thai"
thai_font_destination = root / "public" / "assets" / "fonts"
thai_font_files = (
    "noto-sans-thai-thai-400-normal.woff2",
    "noto-sans-thai-thai-700-normal.woff2",
)
thai_font_license = thai_font_package / "LICENSE"
for filename in thai_font_files:
    if not (thai_font_package / "files" / filename).is_file():
        raise RuntimeError("Noto Sans Thai is missing; run the dependency installer first")
if not thai_font_license.is_file():
    raise RuntimeError("Noto Sans Thai license is missing")

thai_font_destination.mkdir(parents=True, exist_ok=True)
for filename in thai_font_files:
    shutil.copy2(thai_font_package / "files" / filename, thai_font_destination / filename)
shutil.copy2(thai_font_license, thai_font_destination / "noto-sans-thai-LICENSE.txt")


def package_cjk_font(package_name: str, css_name: str) -> None:
    font_package = root / "node_modules" / "@fontsource-variable" / package_name
    css_source = font_package / "index.css"
    font_license = font_package / "LICENSE"
    if not css_source.is_file() or not font_license.is_file():
        raise RuntimeError(f"{package_name} is missing; run the dependency installer first")

    css = css_source.read_text(encoding="utf-8")
    filenames = sorted(set(re.findall(r"url\(\./files/([^)]*\.woff2)\)", css)))
    if not filenames:
        raise RuntimeError(f"{package_name} did not expose any browser font files")

    files_destination = thai_font_destination / "files"
    files_destination.mkdir(parents=True, exist_ok=True)
    for filename in filenames:
        source_file = font_package / "files" / filename
        if not source_file.is_file():
            raise RuntimeError(f"{package_name} font file is missing: {filename}")
        shutil.copy2(source_file, files_destination / filename)
    shutil.copy2(css_source, thai_font_destination / f"{css_name}.css")
    shutil.copy2(font_license, thai_font_destination / f"{css_name}-LICENSE.txt")


package_cjk_font("noto-sans-jp", "noto-sans-jp")
package_cjk_font("noto-sans-sc", "noto-sans-sc")

print("Packaged Cytoscape.js and multilingual browser font assets")
