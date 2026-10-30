from conftest import KEY_B

from vibe_memory.deterministic import _wire_size


def add_memory(client, content, keyword, tags=None):
    response = client.post(
        "/v1/memories",
        json={
            "content": content,
            "keywords": [keyword],
            "tags": tags or [],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def add_relation(client, source, target, relation="RELATED_TO", reason="verified edge"):
    response = client.post(
        "/v1/relations",
        json={
            "source_id": source["id"],
            "target_id": target["id"],
            "relation": relation,
            "reason": reason,
            "evidence_record_ids": [source["id"]],
            "extraction_method": "test",
            "extraction_version": "1",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def manifest_item(source, target, request_id="edge-1"):
    return {
        "source_id": source["id"],
        "target_id": target["id"],
        "relation": "CONTEXT_FOR",
        "reason": "agent-approved project context",
        "evidence_record_ids": [source["id"]],
        "evidence_coverage": "selected",
        "extraction_method": "agent manifest",
        "extraction_version": "1",
        "client_request_id": request_id,
    }


def test_context_bundle_is_deterministic_bounded_and_snapshot_checked(client):
    anchor = add_memory(client, "project decision", "project", ["alpha"])
    related = add_memory(client, "implementation note", "implementation", ["alpha"])
    unrelated = add_memory(client, "unrelated private body", "unrelated", ["beta"])
    add_relation(client, anchor, related)

    request = {
        "anchor_id": anchor["id"],
        "depth": 1,
        "limit": 1,
        "byte_limit": 20000,
    }
    first = client.post("/v1/context-bundle", json=request)
    assert first.status_code == 200, first.text
    payload = first.json()
    assert payload["llm_calls"] == 0
    assert payload["generated_summary"] is False
    assert payload["total"] == 2
    assert len(payload["items"]) == 1
    assert "content" not in payload["items"][0]
    assert payload["page_bytes"] <= request["byte_limit"]
    assert payload["page_bytes"] == _wire_size(payload)
    assert payload["next_cursor"]
    assert unrelated["id"] not in {item["id"] for item in payload["items"]}

    repeated = client.post("/v1/context-bundle", json=request)
    assert repeated.status_code == 200
    assert repeated.json() == payload

    second = client.post(
        "/v1/context-bundle", json={**request, "cursor": payload["next_cursor"]}
    )
    assert second.status_code == 200, second.text
    assert {payload["items"][0]["id"], second.json()["items"][0]["id"]} == {
        anchor["id"],
        related["id"],
    }

    update = client.patch(
        "/v1/records/" + related["id"],
        json={"expected_version": 1, "source": "changed after cursor"},
    )
    assert update.status_code == 200, update.text
    stale = client.post(
        "/v1/context-bundle", json={**request, "cursor": payload["next_cursor"]}
    )
    assert stale.status_code == 409


def test_context_bundle_preserves_owner_and_security_boundaries(client):
    record = add_memory(client, "alice record", "alice")
    client.headers["Authorization"] = "Bearer " + KEY_B
    response = client.post(
        "/v1/context-bundle", json={"record_ids": [record["id"]]}
    )
    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["missing_record_ids"] == [record["id"]]


def test_graph_audit_reports_metadata_only_consistency_findings(client):
    a = add_memory(client, "a", "a")
    b = add_memory(client, "b", "b")
    orphan = add_memory(client, "orphan secret body", "orphan")
    first = add_relation(client, a, b, "SUPERSEDES", "same claim")
    duplicate = add_relation(client, a, b, "SUPERSEDES", "same claim")
    reverse = add_relation(client, b, a, "CORRECTS", "cycle")

    response = client.post("/v1/graph/audit", json={"hub_threshold": 2})
    assert response.status_code == 200, response.text
    audit = response.json()
    assert audit["llm_calls"] == 0 and audit["content_included"] is False
    assert audit["relation_distribution"] == {"CORRECTS": 1, "SUPERSEDES": 2}
    assert {item["id"] for item in audit["orphan_records"]} == {orphan["id"]}
    assert set(audit["correction_cycles"]) == {first["id"], duplicate["id"], reverse["id"]}
    assert audit["duplicate_claims"][0]["relation_ids"] == sorted(
        [first["id"], duplicate["id"]]
    )
    assert "orphan secret body" not in str(audit)


def test_graph_diff_requires_exact_approval_before_partial_apply(client):
    a = add_memory(client, "a", "a")
    b = add_memory(client, "b", "b")
    c = add_memory(client, "c", "c")
    old = add_relation(client, a, c, "OLD_CONTEXT", "remove after approval")
    item = manifest_item(a, b)
    dry_run = {
        "items": [item],
        "scope_record_ids": [a["id"], b["id"], c["id"]],
        "include_retract_candidates": True,
    }
    response = client.post("/v1/graph/diff", json=dry_run)
    assert response.status_code == 200, response.text
    diff = response.json()
    assert diff["dry_run"] is True and diff["llm_calls"] == 0
    assert diff["items"][0]["classification"] == "create"
    assert diff["retract_candidates"][0]["id"] == old["id"]

    apply = {
        **dry_run,
        "approved_diff_hash": "0" * 64,
        "approved_create_client_ids": ["edge-1"],
        "approved_retract_ids": [old["id"]],
        "reason": "user approved the exact dry-run",
    }
    assert client.post("/v1/graph/apply", json=apply).status_code == 409
    applied = client.post(
        "/v1/graph/apply", json={**apply, "approved_diff_hash": diff["diff_hash"]}
    )
    assert applied.status_code == 200, applied.text
    assert applied.json()["created"][0]["status"] == "created"
    assert applied.json()["retracted"][0]["status"] == "retracted"

    after = client.post("/v1/graph/diff", json={"items": [item]}).json()
    assert after["items"][0]["classification"] == "unchanged"


def test_graph_diff_preserves_parallel_claim_conflicts(client):
    a = add_memory(client, "a", "a")
    b = add_memory(client, "b", "b")
    add_relation(client, a, b, "CONTEXT_FOR", "first agent claim")
    response = client.post(
        "/v1/graph/diff", json={"items": [manifest_item(a, b)]}
    )
    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["classification"] == "conflicting_claim"
    assert item["matching_relation_ids"]
