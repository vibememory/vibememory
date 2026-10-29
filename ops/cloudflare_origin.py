"""Provision/run the dedicated private API tunnel without public origin DNS or logged tokens."""

import argparse
import json
import os
import subprocess
import tomllib
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
config_path = ROOT / "landing/wrangler.jsonc"
_local_config = json.loads(config_path.read_text()) if config_path.exists() else {}
ACCOUNT = os.environ.get("CLOUDFLARE_ACCOUNT_ID") or _local_config.get("account_id")
STATE = ROOT / "ops/cloudflare-origin.json"


def call(path, method="GET", body=None):
    config = tomllib.loads((Path.home() / ".config/.wrangler/config/default.toml").read_text())
    request = urllib.request.Request(
        "https://api.cloudflare.com/client/v4" + path,
        headers={
            "Authorization": "Bearer " + config["oauth_token"],
            "Content-Type": "application/json",
            "User-Agent": "VibeMemoryDeploy/1.0",
        },
        method=method,
        data=None if body is None else json.dumps(body).encode(),
    )
    try:
        response = urllib.request.urlopen(request, timeout=30)
    except urllib.error.HTTPError as error:
        if error.code not in (401, 403):
            raise
        node = Path.home() / ".local/share/vibe-memory/node/bin/node"
        cli = ROOT / "landing/node_modules/wrangler/bin/wrangler.js"
        subprocess.run(
            [str(node), str(cli), "whoami"],
            cwd=ROOT / "landing",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
            env={**os.environ, "PATH": str(node.parent) + os.pathsep + os.environ.get("PATH", "")},
        )
        fresh = tomllib.loads((Path.home() / ".config/.wrangler/config/default.toml").read_text())
        request.add_header("Authorization", "Bearer " + fresh["oauth_token"])
        response = urllib.request.urlopen(request, timeout=30)
    with response:
        data = json.load(response)
    if not data.get("success"):
        raise RuntimeError("Cloudflare API request failed")
    return data["result"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["setup", "run"])
    parser.add_argument("--cloudflared", default=str(Path.home() / ".local/bin/cloudflared"))
    args = parser.parse_args()
    if not ACCOUNT:
        parser.error("Set CLOUDFLARE_ACCOUNT_ID or account_id in landing/wrangler.jsonc")
    base = f"/accounts/{ACCOUNT}/cfd_tunnel"
    if args.command == "setup":
        tunnels = call(base + "?is_deleted=false")
        tunnel = next((item for item in tunnels if item["name"] == "vibe-memory-api"), None)
        if tunnel is None:
            tunnel = call(base, "POST", {"name": "vibe-memory-api", "config_src": "cloudflare"})
        call(
            base + "/" + tunnel["id"] + "/configurations",
            "PUT",
            {
                "config": {
                    "ingress": [{"service": "http_status:404"}],
                    "warp_routing": {"enabled": True},
                }
            },
        )
        STATE.write_text(
            json.dumps(
                {
                    "tunnel_id": tunnel["id"],
                    "name": "vibe-memory-api",
                    "origin": "http://127.0.0.1:8080",
                },
                indent=2,
            )
            + "\n"
        )
        config_path = ROOT / "landing/wrangler.jsonc"
        config = json.loads(config_path.read_text())
        config["main"] = "src/worker.js"
        config["assets"]["binding"] = "ASSETS"
        config["assets"]["run_worker_first"] = ["/auth/*", "/v1/*", "/health", "/openapi.json"]
        config["vpc_networks"] = [
            {"binding": "MEMORY_ORIGIN", "tunnel_id": tunnel["id"], "remote": True}
        ]
        config_path.write_text(json.dumps(config, indent=2) + "\n")
        print("Dedicated private API tunnel provisioned:", tunnel["id"])
    else:
        id = json.loads(STATE.read_text())["tunnel_id"]
        token = call(base + "/" + id + "/token")
        subprocess.run(
            [args.cloudflared, "tunnel", "--no-autoupdate", "run"],
            env={**os.environ, "TUNNEL_TOKEN": token},
            check=True,
        )


if __name__ == "__main__":
    main()
