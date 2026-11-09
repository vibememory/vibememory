from conftest import KEY_A, KEY_A2, KEY_B


def use_key(client, key):
    client.headers["Authorization"] = "Bearer " + key


def identity(client, key):
    use_key(client, key)
    response = client.get("/v1/me")
    assert response.status_code == 200, response.text
    return response.json()["agent"]


def test_agent_audit_logs_are_append_only_idempotent_and_agent_scoped(client):
    first = identity(client, KEY_A)
    second = identity(client, KEY_A2)

    use_key(client, KEY_A)
    payload = {
        "action": "release.verify",
        "outcome": "success",
        "summary": "Production health and version were verified.",
        "resource_type": "deployment",
        "resource_id": "v0.37.0",
        "metadata": {"environment": "production", "checks": 3},
        "occurred_at": "2026-11-09T10:30:00+09:00",
        "client_request_id": "release-verify-v037",
    }
    created = client.post("/v1/agent-audit-logs", json=payload)
    assert created.status_code == 201, created.text
    record = created.json()
    assert record["agent_id"] == first["id"]
    assert record["agent_name"] == first["name"]
    assert record["occurred_at"] == "2026-11-09T01:30:00+00:00"
    assert record["received_at"].endswith("+00:00")
    assert record["metadata"] == payload["metadata"]

    retry = client.post("/v1/agent-audit-logs", json=payload)
    assert retry.status_code == 200
    assert retry.json()["id"] == record["id"]

    conflict = client.post(
        "/v1/agent-audit-logs", json={**payload, "summary": "Different result"}
    )
    assert conflict.status_code == 409

    mine = client.get("/v1/agent-audit-logs").json()
    assert mine["visibility"] == "self"
    assert [item["id"] for item in mine["items"]] == [record["id"]]
    assert client.get(f"/v1/agent-audit-logs/{record['id']}").status_code == 200
    events = client.get("/v1/events/recent?limit=5").json()["items"]
    audit_events = [item for item in events if item["event"] == "agent_audit_log.created"]
    assert len(audit_events) == 1
    assert audit_events[0]["data"] == {
        "audit_log_id": record["id"],
        "agent_id": first["id"],
        "action": "release.verify",
    }

    use_key(client, KEY_A2)
    assert second["id"] != first["id"]
    assert client.get("/v1/agent-audit-logs").json()["items"] == []
    assert client.get(f"/v1/agent-audit-logs/{record['id']}").status_code == 404

    use_key(client, KEY_B)
    assert client.get("/v1/agent-audit-logs").json()["items"] == []


def test_agent_audit_log_rejects_sensitive_or_unbounded_metadata(client):
    assert (
        client.post(
            "/v1/agent-audit-logs",
            json={
                "action": "vault.read",
                "outcome": "success",
                "summary": "Read an approved Vault item without recording its value.",
                "metadata": {"nested": {"access_token": "must-not-be-stored"}},
            },
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/v1/agent-audit-logs",
            json={
                "action": "tool.call",
                "outcome": "success",
                "summary": "Invalid oversized metadata.",
                "metadata": {"details": "x" * 12000},
            },
        ).status_code
        == 422
    )
