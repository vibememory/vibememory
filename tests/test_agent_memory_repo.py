import io
import zipfile


def add_memory(client, content, keywords=None):
    response = client.post(
        "/v1/memories",
        json={"content": content, "keywords": keywords or ["portable"]},
    )
    assert response.status_code == 201, response.text
    return response.json()


def repo_payload(content="Use UTC for stored timestamps"):
    return {
        "repository": "https://example.com/private/memory.git",
        "revision": "abc123",
        "entries": [
            {
                "client_request_id": "repo-entry-1",
                "content": content,
                "title": "Time basis",
                "kind": "instruction",
                "keywords": ["UTC", "time basis"],
                "source": "MEMORY.md",
                "tags": ["architecture"],
                "path": "MEMORY.md",
                "line": 4,
                "added_at": "2026-11-06T00:00:00Z",
                "links": ["topics/architecture"],
            }
        ],
    }


def test_agent_memory_repo_export_is_human_readable_and_excludes_secrets(client):
    record = add_memory(client, "Keep server inference disabled", ["server", "inference"])
    response = client.get("/v1/agent-memory-repo/export")
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["content-type"].startswith("application/zip")
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        names = set(archive.namelist())
        assert {"MEMORY.md", "topics/memory.md", "vibe-memory-export.json"} <= names
        assert f"records/{record['id']}.md" in names
        root = archive.read("MEMORY.md").decode()
        topic = archive.read("topics/memory.md").decode()
        detail = archive.read(f"records/{record['id']}.md").decode()
    assert "[[topics/memory]]" in root
    assert f"[[records/{record['id']}]]" in topic
    assert "Keep server inference disabled" in detail
    assert "vault" not in " ".join(names).lower()


def test_agent_memory_repo_import_requires_unchanged_explicit_approval(client):
    payload = repo_payload()
    diff = client.post("/v1/agent-memory-repo/diff", json=payload)
    assert diff.status_code == 200, diff.text
    dry_run = diff.json()
    assert dry_run["llm_calls"] == 0
    assert dry_run["server_parsed_repository"] is False
    assert dry_run["items"][0]["classification"] == "create"

    wrong = client.post(
        "/v1/agent-memory-repo/apply",
        json={
            **payload,
            "approved_diff_hash": "0" * 64,
            "approved_client_request_ids": ["repo-entry-1"],
            "reason": "User approved this exact imported entry",
        },
    )
    assert wrong.status_code == 409

    applied = client.post(
        "/v1/agent-memory-repo/apply",
        json={
            **payload,
            "approved_diff_hash": dry_run["diff_hash"],
            "approved_client_request_ids": ["repo-entry-1"],
            "reason": "User approved this exact imported entry",
        },
    )
    assert applied.status_code == 200, applied.text
    created = applied.json()["created"][0]["record"]
    assert created["trust_level"] == "untrusted"
    assert created["security_state"] == "quarantined"
    assert created["keywords"] == ["UTC", "time basis"]
    assert created["metadata"]["agent_memory_repo"]["path"] == "MEMORY.md"

    repeated = client.post("/v1/agent-memory-repo/diff", json=payload).json()
    assert repeated["items"][0]["classification"] == "unchanged"
    assert client.get("/v1/records").json()["items"] == []
    quarantined = client.get("/v1/quarantine").json()["items"]
    assert quarantined[0]["id"] == created["id"]


def test_agent_memory_repo_import_rejects_unsafe_paths(client):
    payload = repo_payload()
    payload["entries"][0]["path"] = "../MEMORY.md"
    response = client.post("/v1/agent-memory-repo/diff", json=payload)
    assert response.status_code == 422


def test_memory_maintenance_audit_is_content_free_and_metadata_only(client):
    first = add_memory(client, "private duplicate body", ["duplicate"])
    second = add_memory(client, "private duplicate body", ["duplicate"])
    response = client.post(
        "/v1/memory-maintenance/audit",
        json={
            "stale_before": "2100-01-01T00:00:00Z",
            "minimum_keywords": 2,
            "candidate_limit": 20,
        },
    )
    assert response.status_code == 200, response.text
    audit = response.json()
    assert audit["llm_calls"] == 0
    assert audit["content_included"] is False
    assert audit["server_recommendations"] is False
    assert audit["stats"]["exact_duplicate_groups"] == 1
    assert {item["id"] for item in audit["exact_duplicate_groups"][0]["records"]} == {
        first["id"],
        second["id"],
    }
    assert audit["stats"]["stale_candidates"] == 2
    assert audit["stats"]["weak_index_candidates"] == 2
    assert "private duplicate body" not in response.text


def test_memory_maintenance_audit_requires_offset_timestamp(client):
    response = client.post(
        "/v1/memory-maintenance/audit",
        json={"stale_before": "2026-11-06T00:00:00"},
    )
    assert response.status_code == 422
