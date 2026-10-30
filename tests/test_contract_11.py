import io
import zipfile

from conftest import SpyEmbedder
from fastapi.testclient import TestClient

from vibe_memory.app import create_app

ORIGIN = "https://vibememory.io"


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
