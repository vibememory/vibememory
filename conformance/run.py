#!/usr/bin/env python3
"""Black-box core contract smoke test for a disposable Vibe Memory deployment."""

import argparse
import json
import time
import urllib.error
import urllib.request
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path


def call(base, token, path, method="GET", data=None):
    request = urllib.request.Request(
        base.rstrip("/") + path,
        method=method,
        data=None if data is None else json.dumps(data).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return None if response.status == 204 else json.load(response)


def check(name, action):
    started = time.perf_counter()
    try:
        detail = action()
        return {"name": name, "passed": bool(detail), "seconds": time.perf_counter() - started}
    except (AssertionError, KeyError, IndexError, urllib.error.HTTPError) as exc:
        return {
            "name": name,
            "passed": False,
            "seconds": time.perf_counter() - started,
            "error": str(exc),
        }


def write_junit(path, results):
    suite = ET.Element(
        "testsuite",
        name="vibe-memory-core-rest",
        tests=str(len(results)),
        failures=str(sum(not result["passed"] for result in results)),
    )
    for result in results:
        case = ET.SubElement(
            suite,
            "testcase",
            name=result["name"],
            time=f'{result["seconds"]:.6f}',
        )
        if not result["passed"]:
            ET.SubElement(case, "failure", message=result.get("error", "failed"))
    Path(path).write_bytes(ET.tostring(suite, encoding="utf-8", xml_declaration=True))


def main():
    parser = argparse.ArgumentParser(description="Run only against a disposable account")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument("--junit")
    args = parser.parse_args()

    marker = f"conformance-{uuid.uuid4().hex}"
    state = {}

    def create():
        state["record"] = call(
            args.base_url,
            args.token,
            "/v1/memories",
            "POST",
            {
                "content": marker,
                "kind": "fact",
                "keywords": [marker],
                "client_request_id": marker,
            },
        )
        return state["record"]["version"] == 1

    def idempotency():
        repeated = call(
            args.base_url,
            args.token,
            "/v1/memories",
            "POST",
            {
                "content": marker,
                "kind": "fact",
                "keywords": [marker],
                "client_request_id": marker,
            },
        )
        return repeated["id"] == state["record"]["id"]

    def exact_search():
        response = call(
            args.base_url,
            args.token,
            "/v1/search",
            "POST",
            {"keywords": [marker], "match_mode": "exact"},
        )
        return response["hits"][0]["id"] == state["record"]["id"]

    def fetch():
        fetched = call(args.base_url, args.token, f'/v1/records/{state["record"]["id"]}')
        return fetched["id"] == state["record"]["id"] and fetched["version"] == 1

    results = [
        check("create", create),
        check("idempotent-create", idempotency),
        check("exact-search", exact_search),
        check("fetch-version", fetch),
    ]
    if args.junit:
        write_junit(args.junit, results)
    output = {"profile": "core-rest", "passed": all(r["passed"] for r in results), "results": results}
    print(json.dumps(output, indent=2))
    raise SystemExit(0 if output["passed"] else 1)


if __name__ == "__main__":
    main()
