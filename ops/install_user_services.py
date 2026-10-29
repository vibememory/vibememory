"""Install user services for the existing API and its private Cloudflare connector."""

import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
units = Path.home() / ".config/systemd/user"
units.mkdir(parents=True, exist_ok=True)
for name, description, command in [
    ("vibe-memory-api", "Vibe Memory API", f"{root}/.venv/bin/vibe-memory serve"),
    (
        "vibe-memory-tunnel",
        "Vibe Memory private Cloudflare connector",
        f"{root}/.venv/bin/python {root}/ops/cloudflare_origin.py run",
    ),
]:
    (units / (name + ".service")).write_text(f"""[Unit]
Description={description}
After=network-online.target

[Service]
Type=simple
WorkingDirectory={root}
ExecStart={command}
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=default.target
""")
subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
subprocess.run(
    ["systemctl", "--user", "enable", "vibe-memory-api", "vibe-memory-tunnel"], check=True
)
print("Installed user API and tunnel services; start/restart them with systemctl --user.")
