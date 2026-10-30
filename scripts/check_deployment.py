#!/usr/bin/env python3
"""Local deployment posture check without a third-party scanner."""

import argparse
import json
import shutil
import subprocess
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen


def fetch(url):
    request = Request(url, headers={"User-Agent": "vibe-memory-deployment-check/1"})
    try:
        with urlopen(request, timeout=15) as response:
            return response.status, dict(response.headers), response.read()
    except HTTPError as error:
        return error.code, dict(error.headers), error.read()
    except URLError as error:
        return 0, {}, str(error.reason).encode()


def dmarc(hostname):
    if not shutil.which("dig"):
        return None
    result = subprocess.run(
        ["dig", "+short", "TXT", "_dmarc." + hostname],
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )
    return result.stdout.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("origin", help="HTTPS origin, for example https://memory.example.com")
    parser.add_argument("--www-host", help="Optional secondary hostname; defaults to www.<host>")
    args = parser.parse_args()
    origin = args.origin.rstrip("/")
    parsed = urlsplit(origin)
    if parsed.scheme != "https" or not parsed.hostname:
        parser.error("origin must be an HTTPS URL with a hostname")

    failed = False
    status, headers, _ = fetch(origin + "/health")
    hsts = headers.get("Strict-Transport-Security", "")
    hsts_ok = status == 200 and "max-age=" in hsts.casefold()
    print(("PASS" if hsts_ok else "FAIL") + f" HSTS /health status={status} value={hsts!r}")
    failed |= not hsts_ok

    status, _, body = fetch(origin + "/openapi.json")
    try:
        paths = json.loads(body).get("paths", {}) if status == 200 else {}
    except json.JSONDecodeError:
        paths = {}
    exposed = sorted(path for path in paths if path.startswith("/v1/admin/"))
    schema_ok = status == 200 and not exposed
    print(("PASS" if schema_ok else "FAIL") + f" public OpenAPI admin_paths={exposed}")
    failed |= not schema_ok

    www_host = args.www_host or "www." + parsed.hostname
    www_url = urlunsplit((parsed.scheme, www_host, parsed.path or "/", "", ""))
    status, _, _ = fetch(www_url)
    www_ok = status in {200, 301, 302, 307, 308}
    print(("PASS" if www_ok else "FAIL") + f" secondary host {www_url} status={status}")
    failed |= not www_ok

    record = dmarc(parsed.hostname)
    if record is None:
        print("SKIP DMARC (install dig to check DNS locally)")
    else:
        dmarc_ok = "v=DMARC1" in record.upper() and "p=" in record.lower()
        print(("PASS" if dmarc_ok else "WARN") + f" DMARC {record or 'missing'}")
        if not dmarc_ok:
            print("     Start with p=none and monitoring, then raise to quarantine/reject.")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
