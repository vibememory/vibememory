#!/usr/bin/env python3
"""Black-box Vibe Memory contract checks for a disposable deployment."""

import argparse
import hashlib
import json
import time
import urllib.error
import urllib.request
import uuid
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

PROFILE_FIXTURE = {
    "profile": "vibe-memory-core-rest-1.1",
    "checks": [
        "contract-discovery",
        "capability-negotiation",
        "create",
        "idempotent-create",
        "idempotency-conflict",
        "exact-search",
        "fetch-version",
        "optimistic-version-conflict",
        "authenticated-writer",
        "quarantine-default",
        "correction",
        "batch-partial-success",
        "pagination-basic",
        "mcp-capability-mapping",
    ],
}


class Unsupported(RuntimeError):
    """A profile extension was explicitly not exercised."""


def fixture_hash():
    encoded = json.dumps(PROFILE_FIXTURE, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def call(base, token, path, method="GET", data=None, *, headers=None, timeout=20):
    request_headers = {"Accept": "application/json"}
    if token:
        request_headers["Authorization"] = f"Bearer {token}"
    if data is not None:
        request_headers["Content-Type"] = "application/json"
    request_headers.update(headers or {})
    request = urllib.request.Request(
        base.rstrip("/") + path,
        method=method,
        data=None if data is None else json.dumps(data).encode(),
        headers=request_headers,
    )
    try:
        response = urllib.request.urlopen(request, timeout=timeout)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        raw = response.read()
        payload = json.loads(raw) if raw else None
        return response.status, payload, {
            name.casefold(): value for name, value in response.headers.items()
        }


def require_status(response, expected):
    status, payload, headers = response
    assert status == expected, f"expected HTTP {expected}, got {status}: {payload}"
    return payload, headers


def check(name, action, *, capability="core"):
    started = time.perf_counter()
    try:
        detail = action()
        assert detail is not False
        return {
            "name": name,
            "capability": capability,
            "status": "passed",
            "seconds": time.perf_counter() - started,
        }
    except Unsupported as error:
        return {
            "name": name,
            "capability": capability,
            "status": "unsupported",
            "seconds": time.perf_counter() - started,
            "reason": str(error),
        }
    except (AssertionError, KeyError, IndexError, TypeError, urllib.error.URLError) as error:
        return {
            "name": name,
            "capability": capability,
            "status": "failed",
            "seconds": time.perf_counter() - started,
            "error": str(error),
        }


def write_junit(path, results):
    suite = ET.Element(
        "testsuite",
        name="vibe-memory-black-box",
        tests=str(len(results)),
        failures=str(sum(result["status"] == "failed" for result in results)),
        skipped=str(sum(result["status"] == "unsupported" for result in results)),
    )
    for result in results:
        case = ET.SubElement(
            suite,
            "testcase",
            name=result["name"],
            classname=result["capability"],
            time=f'{result["seconds"]:.6f}',
        )
        if result["status"] == "failed":
            ET.SubElement(case, "failure", message=result.get("error", "failed"))
        elif result["status"] == "unsupported":
            ET.SubElement(case, "skipped", message=result.get("reason", "unsupported"))
    Path(path).write_bytes(ET.tostring(suite, encoding="utf-8", xml_declaration=True))


def run(args):
    marker = f"conformance-{uuid.uuid4().hex}"
    state = {}

    def discovery():
        payload, _ = require_status(call(args.base_url, None, "/.well-known/vibe-memory"), 200)
        state["discovery"] = payload
        return (
            payload["time_basis"] == "UTC"
            and payload["contract_version"] == "1.1"
            and {"1.0", "1.1"}.issubset(payload["supported_contract_versions"])
            and {"record", "relationship", "error", "openapi_profile"}.issubset(
                payload["contracts"]
            )
        )

    def capabilities():
        payload, headers = require_status(
            call(
                args.base_url,
                args.token,
                "/v1/capabilities",
                headers={"Vibe-Memory-Contract-Version": args.contract_version},
            ),
            200,
        )
        state["capabilities"] = payload
        return (
            headers.get("vibe-memory-contract-version") == args.contract_version
            and payload["negotiated_contract_version"] == args.contract_version
            and payload["contract_version"] == "1.1"
        )

    def create():
        state["record"], _ = require_status(
            call(
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
            ),
            201,
        )
        return state["record"]["version"] == 1

    def idempotency():
        repeated, _ = require_status(
            call(
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
            ),
            201,
        )
        return repeated["id"] == state["record"]["id"]

    def idempotency_conflict():
        payload, _ = require_status(
            call(
                args.base_url,
                args.token,
                "/v1/memories",
                "POST",
                {
                    "content": marker + " changed",
                    "kind": "fact",
                    "keywords": [marker],
                    "client_request_id": marker,
                },
            ),
            409,
        )
        return payload["error"]["reason_code"] == "IDEMPOTENCY_CONFLICT"

    def exact_search():
        payload, _ = require_status(
            call(
                args.base_url,
                args.token,
                "/v1/search",
                "POST",
                {"keywords": [marker], "match_mode": "exact"},
            ),
            200,
        )
        return payload["hits"][0]["id"] == state["record"]["id"]

    def fetch():
        payload, _ = require_status(
            call(args.base_url, args.token, f'/v1/records/{state["record"]["id"]}'), 200
        )
        return payload["id"] == state["record"]["id"] and payload["version"] == 1

    def version_conflict():
        updated, _ = require_status(
            call(
                args.base_url,
                args.token,
                f'/v1/records/{state["record"]["id"]}',
                "PATCH",
                {"expected_version": 1, "content": marker + " updated"},
            ),
            200,
        )
        state["record"] = updated
        conflict, _ = require_status(
            call(
                args.base_url,
                args.token,
                f'/v1/records/{updated["id"]}',
                "PATCH",
                {"expected_version": 1, "content": marker + " stale"},
            ),
            409,
        )
        return updated["version"] == 2 and conflict["error"]["reason_code"] == "VERSION_CONFLICT"

    def authenticated_writer():
        payload, _ = require_status(
            call(
                args.base_url,
                args.token,
                "/v1/memories",
                "POST",
                {
                    "content": marker + " spoof",
                    "keywords": [marker + "-spoof"],
                    "creator_agent_id": "forged-agent",
                },
            ),
            422,
        )
        return payload["error"]["reason_code"] == "INVALID_ARGUMENT"

    def quarantine_default():
        keyword = marker + "-external"
        external, _ = require_status(
            call(
                args.base_url,
                args.token,
                "/v1/memories",
                "POST",
                {
                    "content": "Quoted external compatibility fixture",
                    "keywords": [keyword],
                    "provenance": {
                        "source_type": "external",
                        "origin_agent": "conformance-runner",
                        "collected_at": datetime.now(UTC).isoformat(),
                    },
                },
            ),
            201,
        )
        hidden, _ = require_status(
            call(
                args.base_url,
                args.token,
                "/v1/search",
                "POST",
                {"keywords": [keyword], "match_mode": "exact"},
            ),
            200,
        )
        explicit, _ = require_status(
            call(
                args.base_url,
                args.token,
                "/v1/search",
                "POST",
                {
                    "keywords": [keyword],
                    "match_mode": "exact",
                    "include_untrusted": True,
                    "include_quarantined": True,
                },
            ),
            200,
        )
        state["external"] = external
        return (
            external["security_state"] == "quarantined"
            and hidden["hits"] == []
            and explicit["hits"][0]["id"] == external["id"]
        )

    def correction():
        previous, _ = require_status(
            call(
                args.base_url,
                args.token,
                "/v1/memories",
                "POST",
                {"content": marker + " old", "keywords": [marker + "-correction"]},
            ),
            201,
        )
        result, _ = require_status(
            call(
                args.base_url,
                args.token,
                "/v1/corrections/memories",
                "POST",
                {
                    "previous_id": previous["id"],
                    "expected_previous_version": previous["version"],
                    "replacement": {
                        "content": marker + " current",
                        "keywords": [marker + "-correction"],
                    },
                    "relation": "SUPERSEDES",
                    "correction_scope": "full",
                    "reason": "Conformance replacement",
                    "client_request_id": marker + "-correction",
                },
            ),
            201,
        )
        refreshed, _ = require_status(
            call(args.base_url, args.token, f'/v1/records/{previous["id"]}'), 200
        )
        state["replacement"] = result["record"]
        return (
            result["relation"]["relation"] == "SUPERSEDES"
            and refreshed["correction_status"] == "superseded"
        )

    def batch_partial_success():
        payload, _ = require_status(
            call(
                args.base_url,
                args.token,
                "/v1/relations/batch",
                "POST",
                {
                    "items": [
                        {
                            "client_request_id": marker + "-relation-ok",
                            "source_id": state["record"]["id"],
                            "target_id": state["external"]["id"],
                            "relation": "MENTIONED_IN",
                            "reason": "Conformance valid edge",
                        },
                        {
                            "client_request_id": marker + "-relation-missing",
                            "source_id": state["record"]["id"],
                            "target_id": str(uuid.uuid4()),
                            "relation": "MENTIONED_IN",
                            "reason": "Conformance missing target",
                        },
                    ],
                    "return": "minimal",
                    "atomic": False,
                },
            ),
            200,
        )
        return payload["counts"] == {"created": 1, "failed": 1} and (
            payload["items"][1]["error"]["retryable"] is False
        )

    def pagination_basic():
        first, _ = require_status(
            call(args.base_url, args.token, "/v1/records?limit=1&offset=0"), 200
        )
        second, _ = require_status(
            call(args.base_url, args.token, "/v1/records?limit=1&offset=1"), 200
        )
        return first["items"] and second["items"] and (
            first["items"][0]["id"] != second["items"][0]["id"]
        )

    def mcp_mapping():
        if not args.mcp_token:
            raise Unsupported("pass --mcp-token for an OAuth-scoped MCP connection")
        initialize, _ = require_status(
            call(
                args.base_url,
                args.mcp_token,
                "/mcp",
                "POST",
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-06-18",
                        "capabilities": {},
                        "clientInfo": {"name": "vibe-conformance", "version": "1.1"},
                    },
                },
                headers={"MCP-Protocol-Version": "2025-06-18"},
            ),
            200,
        )
        tools, _ = require_status(
            call(
                args.base_url,
                args.mcp_token,
                "/mcp",
                "POST",
                {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
                headers={"MCP-Protocol-Version": "2025-06-18"},
            ),
            200,
        )
        names = {item["name"] for item in tools["result"]["tools"]}
        return initialize["result"]["protocolVersion"] == "2025-06-18" and {
            "auth_context",
            "capabilities_get",
            "permission_check",
        }.issubset(names)

    checks = [
        ("contract-discovery", discovery, "core"),
        ("capability-negotiation", capabilities, "core"),
        ("create", create, "core"),
        ("idempotent-create", idempotency, "core"),
        ("idempotency-conflict", idempotency_conflict, "core"),
        ("exact-search", exact_search, "core"),
        ("fetch-version", fetch, "core"),
        ("optimistic-version-conflict", version_conflict, "core"),
        ("authenticated-writer", authenticated_writer, "core"),
        ("quarantine-default", quarantine_default, "security"),
        ("correction", correction, "corrections"),
        ("batch-partial-success", batch_partial_success, "batch"),
        ("pagination-basic", pagination_basic, "pagination"),
        ("mcp-capability-mapping", mcp_mapping, "mcp"),
    ]
    results = [check(name, action, capability=capability) for name, action, capability in checks]
    server_status, server, _ = call(args.base_url, None, "/openapi.json")
    output = {
        "profile": PROFILE_FIXTURE["profile"],
        "contract_version": "1.1",
        "requested_contract_version": args.contract_version,
        "server_version": server.get("info", {}).get("version") if server_status == 200 else None,
        "time_basis": "UTC",
        "run_at": datetime.now(UTC).isoformat(),
        "fixture_sha256": fixture_hash(),
        "passed": all(result["status"] != "failed" for result in results),
        "complete": all(result["status"] == "passed" for result in results),
        "counts": {
            status: sum(result["status"] == status for result in results)
            for status in ("passed", "failed", "unsupported")
        },
        "results": results,
        "limitations": [
            "Run only against a disposable account because fixtures are retained.",
            "An MCP OAuth token is separate from the REST token and is opt-in.",
            "Basic offset pagination is checked; historical snapshot reconstruction is capability-gated.",
        ],
    }
    return output


def main():
    parser = argparse.ArgumentParser(description="Run only against a disposable account")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument("--mcp-token")
    parser.add_argument("--contract-version", choices=["1.0", "1.1"], default="1.1")
    parser.add_argument("--junit")
    parser.add_argument("--output")
    args = parser.parse_args()
    output = run(args)
    if args.junit:
        write_junit(args.junit, output["results"])
    encoded = json.dumps(output, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    raise SystemExit(0 if output["passed"] else 1)


if __name__ == "__main__":
    main()
