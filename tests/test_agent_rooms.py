from conftest import KEY_A, KEY_A2, KEY_B
from fastapi.testclient import TestClient

from vibe_memory.app import create_app

ORIGIN = "https://vibememory.io"


def use_key(client, key):
    client.headers["Authorization"] = "Bearer " + key


def identity(client, key):
    use_key(client, key)
    response = client.get("/v1/me")
    assert response.status_code == 200, response.text
    return response.json()["agent"]


def test_agent_room_membership_messages_read_cursor_and_isolation(client):
    first = identity(client, KEY_A)
    second = identity(client, KEY_A2)

    use_key(client, KEY_A)
    created = client.post(
        "/v1/agent-rooms",
        json={
            "name": "Release room",
            "description": "Coordinate one release",
            "member_agent_ids": [second["id"]],
            "client_request_id": "room-release-1",
        },
    )
    assert created.status_code == 201, created.text
    room = created.json()
    assert room["member_count"] == 2
    assert {item["agent_id"] for item in room["members"]} == {
        first["id"],
        second["id"],
    }
    assert (
        client.patch(f"/v1/agent-rooms/{room['id']}", json={"name": None}).status_code
        == 422
    )

    retry = client.post(
        "/v1/agent-rooms",
        json={
            "name": "Release room",
            "description": "Coordinate one release",
            "member_agent_ids": [second["id"]],
            "client_request_id": "room-release-1",
        },
    )
    assert retry.status_code == 200
    assert retry.json()["id"] == room["id"]
    assert (
        client.post(
            "/v1/agent-rooms",
            json={"name": "Different", "client_request_id": "room-release-1"},
        ).status_code
        == 409
    )

    posted = client.post(
        f"/v1/agent-rooms/{room['id']}/messages",
        json={
            "body": "Please verify production.",
            "metadata": {"stage": "deploy"},
            "client_request_id": "room-message-1",
        },
    )
    assert posted.status_code == 201, posted.text
    first_message = posted.json()

    use_key(client, KEY_A2)
    listed = client.get("/v1/agent-rooms").json()["items"]
    assert listed[0]["id"] == room["id"]
    assert listed[0]["unread_count"] == 1
    messages = client.get(f"/v1/agent-rooms/{room['id']}/messages").json()
    assert messages["items"][0]["body"] == "Please verify production."
    marked = client.post(
        f"/v1/agent-rooms/{room['id']}/read",
        json={"sequence": first_message["sequence"]},
    )
    assert marked.status_code == 200
    assert marked.json()["unread_count"] == 0

    reply = client.post(
        f"/v1/agent-rooms/{room['id']}/messages",
        json={"body": "Production verified.", "reply_to": first_message["id"]},
    )
    assert reply.status_code == 201, reply.text
    previous = client.get(
        f"/v1/agent-rooms/{room['id']}/messages",
        params={"before": reply.json()["sequence"], "limit": 100},
    ).json()
    assert [item["id"] for item in previous["items"]] == [first_message["id"]]
    assert previous["previous_cursor"] == first_message["sequence"]

    use_key(client, KEY_A)
    detail = client.get(f"/v1/agent-rooms/{room['id']}").json()
    assert detail["unread_count"] == 1
    assert detail["last_sequence"] == reply.json()["sequence"]

    use_key(client, KEY_B)
    assert client.get("/v1/agent-rooms").json()["items"] == []
    assert client.get(f"/v1/agent-rooms/{room['id']}").status_code == 404
    assert (
        client.post(
            f"/v1/agent-rooms/{room['id']}/messages", json={"body": "cross owner"}
        ).status_code
        == 404
    )

    use_key(client, KEY_A)
    removed = client.delete(f"/v1/agent-rooms/{room['id']}/members/{second['id']}")
    assert removed.status_code == 200
    assert removed.json()["member_count"] == 1
    use_key(client, KEY_A2)
    assert client.get(f"/v1/agent-rooms/{room['id']}").status_code == 404

    use_key(client, KEY_A)
    another = client.post(
        "/v1/agent-rooms",
        json={"name": "Self leave", "member_agent_ids": [second["id"]]},
    ).json()
    use_key(client, KEY_A2)
    left = client.delete(f"/v1/agent-rooms/{another['id']}/members/{second['id']}")
    assert left.status_code == 200
    assert left.json() == {"id": another["id"], "left": True}
    assert client.get(f"/v1/agent-rooms/{another['id']}").status_code == 404


def test_agent_room_sse_is_membership_scoped(client):
    identity(client, KEY_A)
    second = identity(client, KEY_A2)
    use_key(client, KEY_A)
    room = client.post(
        "/v1/agent-rooms",
        json={"name": "Live", "member_agent_ids": [second["id"]]},
    ).json()
    message = client.post(
        f"/v1/agent-rooms/{room['id']}/messages", json={"body": "room live event"}
    ).json()

    use_key(client, KEY_A2)
    stream = client.get("/v1/agent-rooms/stream?seconds=1")
    assert stream.status_code == 200
    assert f"id: {message['sequence']}" in stream.text
    assert "event: agent.room.message" in stream.text
    assert "room live event" in stream.text

    use_key(client, KEY_B)
    other = client.get("/v1/agent-rooms/stream?seconds=1")
    assert other.status_code == 200
    assert "event: agent.room.message" not in other.text


def test_browser_console_can_create_and_use_a_room(settings, embedder):
    web_settings = settings.model_copy(update={"public_origin": ORIGIN, "api_keys": {}})
    with TestClient(create_app(web_settings, embedder), base_url=ORIGIN) as web:
        web.headers["Origin"] = ORIGIN
        signed_up = web.post(
            "/auth/signup",
            json={
                "email": "rooms@example.com",
                "password": "a-long-test-password-123",
                "name": "Room owner",
            },
        )
        assert signed_up.status_code == 200, signed_up.text
        room = web.post("/v1/agent-rooms", json={"name": "Console room"})
        assert room.status_code == 201, room.text
        browser_id = "browser:" + signed_up.json()["user"]["id"]
        assert room.json()["members"][0]["agent_id"] == browser_id
        sent = web.post(
            f"/v1/agent-rooms/{room.json()['id']}/messages",
            json={"body": "Created from the console."},
        )
        assert sent.status_code == 201, sent.text
        assert web.get("/v1/agent-rooms").json()["items"][0]["last_sequence"] == sent.json()[
            "sequence"
        ]
