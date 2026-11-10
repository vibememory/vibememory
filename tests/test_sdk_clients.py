import importlib.util
import json
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]


def load_python_client():
    path = ROOT / "sdk" / "python" / "vibememory" / "client.py"
    spec = importlib.util.spec_from_file_location("vibememory_public_client", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_python_sdk_structured_error_cancellation_and_pages():
    module = load_python_client()
    decision = module.decision_profile_metadata(
        {
            "type": "checkpoint",
            "version": 99,
            "state": "open",
            "topic": "database",
            "applies_to": {"scope": "project"},
        }
    )
    assert decision["vibe_memory_profile"]["type"] == "decision"
    assert decision["vibe_memory_profile"]["version"] == 1
    checkpoint = module.checkpoint_profile_metadata(
        {
            "claimed_stage": "implemented",
            "observation_kind": "author_reported",
            "target": {"scope": "API"},
            "observed_at": "2026-11-07T00:00:00Z",
        }
    )
    assert checkpoint["vibe_memory_profile_observation"] == "author_reported"
    failure = module.failure_reproduction_profile_metadata(
        {
            "outcome": "failed",
            "observed_at": "2026-11-09T05:00:00Z",
            "sample": {"identifier": "two-row-csv", "input_rows": 2},
            "failure": {"stage": "parse", "message_redacted": "invalid number"},
            "minimal_reproduction": {
                "conditions": ["strict mode"],
                "observed_result": "parse failed",
            },
            "evidence_references": [
                {
                    "kind": "external",
                    "reference": "/tmp/sample.csv",
                    "verification": {"status": "missing"},
                }
            ],
        }
    )
    assert failure["vibe_memory_failure_reproduction"]["type"] == "failure_reproduction"
    assert failure["vibe_memory_failure_reference_status"] == "missing"
    impact = module.evidence_impact_review_profile_metadata(
        {
            "target": {"kind": "record", "id": "decision-a", "version": 3},
            "evidence": {"record_id": "evidence-a", "version": 2},
            "reviewer": "reviewer",
            "observed_at": "2026-11-09T09:00:00Z",
            "impact": "affected",
            "rationale": "Exact dependency was confirmed.",
        }
    )
    assert impact["vibe_memory_evidence_impact_review"]["version"] == 1
    assert impact["vibe_memory_evidence_impact"] == "affected"
    body = json.dumps(
        {
            "error": {
                "reason_code": "VERSION_CONFLICT",
                "retryable": False,
                "request_id": "request-1",
            }
        }
    )
    error = module.VibeMemoryError(409, body)
    assert error.code == "VERSION_CONFLICT"
    assert error.retryable is False
    assert error.request_id == "request-1"

    client = module.VibeMemoryClient("https://example.test", "test-token")
    with pytest.raises(module.VibeMemoryCancelled):
        client.get("record", cancelled=lambda: True)

    pages = iter(
        [
            {"items": [{"id": "one"}, {"id": "two"}], "limit": 2, "offset": 0},
            {"items": [{"id": "three"}], "limit": 2, "offset": 2},
        ]
    )
    def list_page(limit, offset, cancelled=None):
        return next(pages)

    client.list = list_page
    assert [page["offset"] for page in client.iter_records(limit=2)] == [0, 2]

    captured = []

    def capture(path, method="GET", payload=None, retry=False, **kwargs):
        captured.append((path, payload))
        return payload

    client._request = capture
    client.search(["project"])
    assert captured[-1] == (
        "/v1/search",
        {
            "keywords": ["project"],
            "match_mode": "hybrid",
            "projection": "minimal",
            "byte_limit": 16384,
            "limit": 8,
        },
    )
    client.context_bundle(record_ids=["record-1"])
    assert captured[-1][1]["projection"] == "minimal"
    assert captured[-1][1]["byte_limit"] == 32768
    client.evidence_impact_candidates("evidence-a", 2)
    assert captured[-1] == (
        "/v1/evidence-impact/candidates",
        {
            "evidence_record_id": "evidence-a",
            "evidence_version": 2,
            "candidate_limit": 100,
        },
    )


def test_sdk_package_versions_and_typescript_contract():
    python_package = tomllib.loads(
        (ROOT / "sdk" / "python" / "pyproject.toml").read_text(encoding="utf-8")
    )
    typescript_package = json.loads(
        (ROOT / "sdk" / "typescript" / "package.json").read_text(encoding="utf-8")
    )
    typescript_source = (ROOT / "sdk" / "typescript" / "src" / "index.ts").read_text(
        encoding="utf-8"
    )
    assert python_package["project"]["version"] == "0.3.1"
    assert typescript_package["version"] == "0.3.1"
    for exported in (
        "VibeMemoryError",
        "RequestOptions",
        "BatchResult",
        "async *records",
        "decisionProfileMetadata",
        "checkpointProfileMetadata",
        "failureReproductionProfileMetadata",
        "evidenceImpactReviewProfileMetadata",
        "evidenceImpactCandidates",
        "createWithMetadata",
        "SearchResponse",
        "SearchRetrievalOptions",
    ):
        assert exported in typescript_source
