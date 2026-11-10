import io
import json
import zipfile
from pathlib import Path

from conftest import SpyEmbedder
from fastapi.testclient import TestClient

from vibe_memory.app import create_app

ORIGIN = "https://vibememory.io"
CONTRACTS = Path(__file__).parents[1] / "contracts"


def test_namespace_grants_hard_isolate_records(settings):
    configured = settings.model_copy(update={"public_origin": ORIGIN, "api_keys": {}})
    with TestClient(create_app(configured, SpyEmbedder()), base_url=ORIGIN) as client:
        client.headers["Origin"] = ORIGIN
        client.post(
            "/auth/signup",
            json={"name": "Namespace", "email": "namespace@example.com", "password": "long-password-123"},
        )
        namespace = client.post("/auth/namespaces", json={"name": "Project Atlas"}).json()
        key = client.post("/auth/api-keys", json={"name": "Scoped"}).json()
        client.put(
            f"/auth/api-keys/{key['id']}/namespaces",
            json={"grants": [{"namespace_id": namespace["id"], "can_read": True, "can_write": True}]},
        )
        auth = {"Authorization": "Bearer " + key["key"], "Origin": ""}
        assert client.get("/v1/records", headers=auth).status_code == 404
        scoped = {**auth, "X-Vibe-Memory-Namespace": namespace["id"]}
        record = client.post(
            "/v1/memories", headers=scoped, json={"content": "Atlas decision", "keywords": ["Atlas"]}
        ).json()
        assert client.get("/v1/records/" + record["id"], headers=scoped).status_code == 200
        assert client.get("/v1/records/" + record["id"], headers=auth).status_code == 404
        denied = client.put(f"/auth/api-keys/{key['id']}/namespaces", json={"grants": []})
        assert denied.json()["grants"] == [
            {"namespace_id": "default", "can_read": False, "can_write": False}
        ]
        assert client.get("/v1/records/" + record["id"], headers=scoped).status_code == 404


def test_valid_time_and_portable_archive(client):
    record = client.post(
        "/v1/memories",
        json={
            "content": "Release window",
            "keywords": ["release"],
            "valid_from": "2026-10-01T00:00:00Z",
            "valid_to": "2026-11-01T00:00:00Z",
        },
    ).json()
    active = client.post(
        "/v1/search",
        json={"keywords": ["release"], "match_mode": "exact", "valid_at": "2026-10-30T00:00:00Z"},
    ).json()
    expired = client.post(
        "/v1/search",
        json={"keywords": ["release"], "match_mode": "exact", "valid_at": "2026-12-01T00:00:00Z"},
    ).json()
    assert active["hits"][0]["id"] == record["id"]
    assert active["temporal"]["completeness"] == "current_versions_only"
    assert expired["hits"] == []

    updated = client.patch(
        "/v1/records/" + record["id"],
        json={"expected_version": 1, "content": "Updated release window"},
    ).json()
    assert updated["version"] == 2
    historical = client.get("/v1/records", params={"known_at": record["created_at"]}).json()
    assert historical["items"] == []
    current = client.get("/v1/records").json()["items"][0]
    assert current["recorded_at"] != current["created_at"]

    exported = client.get("/v1/portable-archive")
    assert exported.status_code == 200
    with zipfile.ZipFile(io.BytesIO(exported.content)) as archive:
        assert {"manifest.json", "records.jsonl", "relations.jsonl"}.issubset(archive.namelist())
    dry_run = client.post(
        "/v1/portable-archive/import",
        headers={"Content-Type": "application/vnd.vibememory.archive+zip"},
        content=exported.content,
    )
    assert dry_run.status_code == 200
    assert dry_run.json()["dry_run"] is True
    assert record["id"] in dry_run.json()["collisions"]


def test_public_contract_and_admin_metrics(settings):
    configured = settings.model_copy(
        update={"public_origin": ORIGIN, "api_keys": {}, "admin_emails": {"admin@example.com"}}
    )
    with TestClient(create_app(configured, SpyEmbedder()), base_url=ORIGIN) as client:
        contract = client.get("/.well-known/vibe-memory").json()
        assert contract["time_basis"] == "UTC"
        client.headers["Origin"] = ORIGIN
        client.post(
            "/auth/signup",
            json={"name": "Admin", "email": "admin@example.com", "password": "long-password-123"},
        )
        metrics = client.get("/v1/admin/metrics").json()
        assert metrics["privacy"] == "fixed-cardinality metadata only"
        assert all("user" not in item for item in metrics["requests"])


def test_contract_documents_and_version_negotiation(client):
    discovery = client.get("/.well-known/vibe-memory").json()
    assert discovery["contract_version"] == "1.1"
    assert discovery["supported_contract_versions"] == ["1.0", "1.1"]
    assert discovery["contracts"] == {
        "record": "/contracts/v1/memory-contract.json",
        "relationship": "/contracts/v1/relationship-contract.json",
        "error": "/contracts/v1/error-contract.json",
        "openapi_profile": "/contracts/v1/openapi-profile.json",
        "decision_profile": "/contracts/v1/decision-profile.json",
        "checkpoint_profile": "/contracts/v1/checkpoint-profile.json",
        "failure_reproduction_profile":
            "/contracts/v1/failure-reproduction-profile.json",
        "evidence_impact_review_profile":
            "/contracts/v1/evidence-impact-review-profile.json",
        "governance": "/contracts/GOVERNANCE.md",
        "ump_mapping": "/contracts/ump-mapping.md",
    }

    for name, title in (
        ("memory-contract.json", "Vibe Memory Contract 1.1"),
        ("relationship-contract.json", "Vibe Memory Relationship Contract 1.1"),
        ("error-contract.json", "Vibe Memory Error Contract 1.1"),
    ):
        schema = json.loads((CONTRACTS / "v1" / name).read_text(encoding="utf-8"))
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["title"] == title
        assert schema["additionalProperties"] is True

    profile = json.loads(
        (CONTRACTS / "v1" / "openapi-profile.json").read_text(encoding="utf-8")
    )
    assert profile["openapi"] == "3.1.0"
    assert profile["x-vibe-memory-profile"]["server_inference"] is False
    assert {"/v1/memories", "/v1/records/{id}", "/v1/search", "/v1/relations"} <= set(
        profile["paths"]
    )

    decision = json.loads((CONTRACTS / "v1" / "decision-profile.json").read_text())
    checkpoint = json.loads((CONTRACTS / "v1" / "checkpoint-profile.json").read_text())
    failure = json.loads(
        (CONTRACTS / "v1" / "failure-reproduction-profile.json").read_text()
    )
    impact = json.loads(
        (CONTRACTS / "v1" / "evidence-impact-review-profile.json").read_text()
    )
    assert decision["additionalProperties"] is False
    assert checkpoint["additionalProperties"] is False
    assert failure["additionalProperties"] is False
    assert impact["additionalProperties"] is False
    assert "truth" in decision["description"]
    assert "never executed" in checkpoint["description"]
    assert "never opens external references" in failure["description"]
    assert "Conflicting observations" in impact["description"]

    legacy = client.get("/v1/capabilities", headers={"Vibe-Memory-Contract-Version": "1.0"})
    assert legacy.status_code == 200
    assert legacy.headers["vibe-memory-contract-version"] == "1.0"
    assert legacy.headers["vibe-memory-contract-supported"] == "1.0, 1.1"
    assert legacy.json()["negotiated_contract_version"] == "1.0"
    assert legacy.json()["supported_contract_versions"] == ["1.0", "1.1"]

    current = client.get("/v1/capabilities")
    assert current.headers["vibe-memory-contract-version"] == "1.1"
    assert current.json()["negotiated_contract_version"] == "1.1"

    unsupported = client.get(
        "/v1/capabilities", headers={"Vibe-Memory-Contract-Version": "9.0"}
    )
    assert unsupported.status_code == 406
    assert unsupported.json()["supported_contract_versions"] == ["1.0", "1.1"]
    assert unsupported.json()["error"]["reason_code"] == "UNSUPPORTED_CONTRACT_VERSION"


def test_idempotency_conflict_uses_public_error_contract(client):
    payload = {
        "content": "First idempotent value",
        "keywords": ["contract-idempotency"],
        "client_request_id": "contract-idempotency-v1",
    }
    assert client.post("/v1/memories", json=payload).status_code == 201
    conflict = client.post(
        "/v1/memories", json={**payload, "content": "Different idempotent value"}
    )
    assert conflict.status_code == 409
    error = conflict.json()["error"]
    assert error["schema_version"] == "1.1"
    assert error["reason_code"] == "IDEMPOTENCY_CONFLICT"
    assert error["retryable"] is False
    assert error["request_id"] == conflict.headers["x-request-id"]
