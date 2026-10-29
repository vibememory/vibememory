from conftest import KEY_A, KEY_A2, KEY_B


def use_key(client, key):
    client.headers["Authorization"] = "Bearer " + key


def identity(client, key):
    use_key(client, key)
    response = client.get("/v1/me")
    assert response.status_code == 200, response.text
    return response.json()["agent"]


def test_agent_message_delivery_ack_reply_and_isolation(client):
    first = identity(client, KEY_A)
    second = identity(client, KEY_A2)

    agents = client.get("/v1/agents")
    assert agents.status_code == 200
    assert agents.json()["self"]["id"] == second["id"]
    assert {item["id"] for item in agents.json()["items"]} == {first["id"], second["id"]}

    sent = client.post(
        "/v1/agent-messages",
        json={
            "recipient_agent_id": first["id"],
            "kind": "request",
            "subject": "검토 요청",
            "body": "배포 결과를 확인해 주세요.",
            "metadata": {"task": "release"},
            "client_request_id": "release-check-1",
        },
    )
    assert sent.status_code == 201, sent.text
    message = sent.json()
    assert message["status"] == "queued"
    assert message["sender_agent_id"] == second["id"]
    assert message["recipient_agent_id"] == first["id"]

    retry = client.post(
        "/v1/agent-messages",
        json={
            "recipient_agent_id": first["id"],
            "kind": "request",
            "subject": "검토 요청",
            "body": "배포 결과를 확인해 주세요.",
            "metadata": {"task": "release"},
            "client_request_id": "release-check-1",
        },
    )
    assert retry.status_code == 200
    assert retry.json()["id"] == message["id"]

    conflict = client.post(
        "/v1/agent-messages",
        json={
            "recipient_agent_id": first["id"],
            "body": "다른 내용",
            "client_request_id": "release-check-1",
        },
    )
    assert conflict.status_code == 409

    use_key(client, KEY_B)
    assert client.get("/v1/agent-messages/inbox").json()["items"] == []
    assert client.get(f"/v1/agent-messages/{message['id']}").status_code == 404
    assert (
        client.post(
            "/v1/agent-messages",
            json={"recipient_agent_id": first["id"], "body": "cross-owner"},
        ).status_code
        == 404
    )

    use_key(client, KEY_A)
    inbox = client.get("/v1/agent-messages/inbox")
    assert inbox.status_code == 200
    assert [item["id"] for item in inbox.json()["items"]] == [message["id"]]
    assert inbox.json()["cursor"] == message["sequence"]

    read = client.post(
        f"/v1/agent-messages/{message['id']}/ack", json={"status": "read"}
    )
    assert read.status_code == 200
    assert read.json()["status"] == "read"
    assert read.json()["delivered_at"] and read.json()["read_at"]
    assert read.json()["acked_at"] is None

    regressed = client.post(
        f"/v1/agent-messages/{message['id']}/ack", json={"status": "delivered"}
    )
    assert regressed.status_code == 200
    assert regressed.json()["status"] == "read"

    reply = client.post(
        "/v1/agent-messages",
        json={
            "recipient_agent_id": second["id"],
            "kind": "response",
            "body": "확인했습니다.",
            "reply_to": message["id"],
        },
    )
    assert reply.status_code == 201, reply.text
    assert reply.json()["thread_id"] == message["thread_id"]

    use_key(client, KEY_A2)
    assert client.get("/v1/agent-messages/inbox").json()["items"][0]["id"] == reply.json()["id"]
    sent_items = client.get("/v1/agent-messages/sent").json()["items"]
    assert sent_items[0]["id"] == message["id"]
    assert sent_items[0]["status"] == "read"


def test_agent_message_sse_is_recipient_scoped(client):
    first = identity(client, KEY_A)
    identity(client, KEY_A2)
    sent = client.post(
        "/v1/agent-messages",
        json={"recipient_agent_id": first["id"], "body": "실시간 알림"},
    ).json()

    use_key(client, KEY_A)
    stream = client.get("/v1/agent-messages/stream?seconds=1")
    assert stream.status_code == 200
    assert stream.headers["content-type"].startswith("text/event-stream")
    assert f"id: {sent['sequence']}" in stream.text
    assert "event: agent.message" in stream.text
    assert "실시간 알림" in stream.text

    use_key(client, KEY_B)
    other = client.get("/v1/agent-messages/stream?seconds=1")
    assert other.status_code == 200
    assert "event: agent.message" not in other.text
