#!/usr/bin/env python3
"""Run the deterministic, model-free Agent A to Agent B handoff benchmark."""

import argparse
import json
import statistics
import time
import urllib.request
import uuid
from pathlib import Path


def call(base_url, token, path, method="GET", data=None):
    body = None if data is None else json.dumps(data).encode()
    request = urllib.request.Request(
        base_url.rstrip("/") + path,
        method=method,
        data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=20) as response:
        raw = response.read()
    return json.loads(raw), time.perf_counter() - started, len(raw)


def percentile(values, rank):
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round((len(ordered) - 1) * rank))]


def main():
    parser = argparse.ArgumentParser(description="Use a disposable Vibe Memory account")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument(
        "--fixture",
        type=Path,
        default=Path(__file__).parent / "fixtures" / "handoff.json",
    )
    args = parser.parse_args()
    fixture = json.loads(args.fixture.read_text(encoding="utf-8"))
    run_id = uuid.uuid4().hex
    created = []
    latencies = []
    response_bytes = 0

    for index, item in enumerate(fixture["records"]):
        payload = {
            **item,
            "kind": "fact",
            "keywords": [*item["keywords"], run_id],
            "client_request_id": f"benchmark-{run_id}-{index}",
        }
        response, latency, size = call(args.base_url, args.token, "/v1/memories", "POST", payload)
        created.append(response["id"])
        latencies.append(latency)
        response_bytes += size

    expected_total = 0
    found_total = 0
    query_results = []
    for query in fixture["queries"]:
        payload = {"keywords": [*query["keywords"], run_id], "match_mode": "hybrid"}
        response, latency, size = call(args.base_url, args.token, "/v1/search", "POST", payload)
        latencies.append(latency)
        response_bytes += size
        hit_ids = {hit["id"] for hit in response["hits"]}
        expected_ids = {created[index] for index in query["expected"]}
        found = len(hit_ids & expected_ids)
        expected_total += len(expected_ids)
        found_total += found
        query_results.append({"keywords": query["keywords"], "expected": len(expected_ids), "found": found})

    recall = found_total / expected_total if expected_total else 1.0
    output = {
        "profile": "deterministic-handoff-v1",
        "passed": recall == 1.0,
        "recall": recall,
        "queries": query_results,
        "latency_ms": {
            "mean": round(statistics.mean(latencies) * 1000, 2),
            "p95": round(percentile(latencies, 0.95) * 1000, 2),
        },
        "response_bytes": response_bytes,
        "limitations": [
            "Synthetic fixture; it does not measure model keyword extraction.",
            "Use only with a disposable account because benchmark records are retained.",
        ],
    }
    print(json.dumps(output, indent=2))
    raise SystemExit(0 if output["passed"] else 1)


if __name__ == "__main__":
    main()
