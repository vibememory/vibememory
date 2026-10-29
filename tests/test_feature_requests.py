from concurrent.futures import ThreadPoolExecutor

from conftest import KEY_A, KEY_A2, KEY_B, SpyEmbedder
from fastapi.testclient import TestClient

from vibe_memory.app import create_app

PAYLOAD = {
    "title": "관계 일괄 등록 API",
    "description": "문서에서 추출한 관계를 하나의 요청으로 등록하고 싶습니다.",
    "agent_name": "coding-agent",
    "use_case": "100개 관계를 등록할 때 네트워크 왕복을 줄입니다.",
    "priority": "medium",
    "source": "agent-session",
    "client_request_id": "batch-relations-v1",
}


def submit(client, **changes):
    response = client.post("/v1/feature-requests", json={**PAYLOAD, **changes})
    assert response.status_code in (200, 201), response.text
    return response


def test_submit_read_list_without_embedding_or_memory_pollution(client, embedder):
    response = submit(client)
    assert response.status_code == 201
    record = response.json()
    assert record["status"] == "received" and record["id"] and record["created_at"]
    assert record["result"] == "" and record["result_url"] == ""
    assert record["updated_at"] == record["created_at"] and record["resolved_at"] is None
    assert all(record[key] == value for key, value in PAYLOAD.items())
    assert "owner" not in record
    assert client.get(response.headers["location"]).json() == record
    assert client.get("/v1/feature-requests").json()["items"] == [record]
    assert client.get("/v1/records").json()["items"] == []
    assert client.app.state.store.candidates("alice", "all", []) == []
    assert not embedder.calls


def test_processing_status_result_and_owner_scoping(client):
    record = submit(client).json()
    reviewing = client.patch(
        "/v1/feature-requests/" + record["id"],
        json={
            "status": "reviewing",
            "result": "기술 검토를 시작했습니다.",
            "result_url": "https://github.com/vibememory/vibememory/issues/1",
        },
    )
    assert reviewing.status_code == 200, reviewing.text
    reviewing = reviewing.json()
    assert reviewing["status"] == "reviewing"
    assert reviewing["result"] == "기술 검토를 시작했습니다."
    assert reviewing["result_url"].endswith("/issues/1")
    assert reviewing["updated_at"] >= record["updated_at"]
    assert reviewing["resolved_at"] is None

    completed = client.patch(
        "/v1/feature-requests/" + record["id"],
        json={"status": "completed", "result": "일괄 관계 등록을 구현했습니다."},
    ).json()
    assert completed["status"] == "completed"
    assert completed["result"] == "일괄 관계 등록을 구현했습니다."
    assert completed["resolved_at"] is not None
    assert completed["result_url"] == reviewing["result_url"]

    reopened = client.patch(
        "/v1/feature-requests/" + record["id"], json={"status": "in_progress"}
    ).json()
    assert reopened["resolved_at"] is None
    assert client.app.state.store.events("alice")[-1]["event"] == "feature_request.updated"

    client.headers["Authorization"] = "Bearer " + KEY_B
    assert (
        client.patch(
            "/v1/feature-requests/" + record["id"],
            json={"status": "declined", "result": "not mine"},
        ).status_code
        == 404
    )


def test_same_user_agents_share_requests_other_users_cannot_read(client):
    record = submit(client).json()
    client.headers["Authorization"] = "Bearer " + KEY_A2
    assert client.get("/v1/feature-requests/" + record["id"]).json() == record
    client.headers["Authorization"] = "Bearer " + KEY_B
    assert client.get("/v1/feature-requests").json()["items"] == []
    assert client.get("/v1/feature-requests/" + record["id"]).status_code == 404
    assert submit(client).json()["id"] != record["id"]  # retry IDs are scoped to the user
    for path in ("/v1/feature-requests", "/v1/feature-requests/" + record["id"]):
        assert client.get(path, headers={"Authorization": ""}).status_code == 401
    assert (
        client.post("/v1/feature-requests", json=PAYLOAD, headers={"Authorization": ""}).status_code
        == 401
    )


def test_idempotency_conflict_and_parallel_retries(client):
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(
            pool.map(lambda _: client.post("/v1/feature-requests", json=PAYLOAD), range(4))
        )
    assert sorted(r.status_code for r in responses) == [200, 200, 200, 201]
    assert len({r.json()["id"] for r in responses}) == 1
    assert len(client.get("/v1/feature-requests").json()["items"]) == 1
    conflict = client.post(
        "/v1/feature-requests", json={**PAYLOAD, "description": "different request"}
    )
    assert conflict.status_code == 409
    # Without an optional retry ID the agent is explicitly creating a new request each time.
    assert submit(client, client_request_id=None).status_code == 201
    assert submit(client, client_request_id=None).status_code == 201


def test_validation_and_pagination(client, embedder):
    for changes in (
        {"title": " "},
        {"description": ""},
        {"agent_name": " "},
        {"priority": "urgent"},
        {"title": "x" * 201},
        {"status": "implemented"},
        {"owner": "bob"},
    ):
        assert client.post("/v1/feature-requests", json={**PAYLOAD, **changes}).status_code == 422
    assert not embedder.calls
    ids = [
        submit(client, title=f"Request {i}", client_request_id=f"request-{i}").json()["id"]
        for i in range(3)
    ]
    pages = [
        client.get(f"/v1/feature-requests?limit=1&offset={i}").json()["items"] for i in range(3)
    ]
    assert {page[0]["id"] for page in pages} == set(ids)
    assert client.get("/v1/feature-requests?limit=0").status_code == 422
    assert client.get("/v1/feature-requests?offset=-1").status_code == 422
    record = client.get("/v1/feature-requests").json()["items"][0]
    for payload in (
        {},
        {"status": "done"},
        {"status": None},
        {"result": None},
        {"result_url": "javascript:alert(1)"},
        {"result_url": "https://user:secret@example.com/result"},
        {"result": "x" * 10001},
    ):
        assert (
            client.patch("/v1/feature-requests/" + record["id"], json=payload).status_code
            == 422
        )


def test_persistence_and_available_when_embedding_unavailable(settings):
    class Unavailable(SpyEmbedder):
        def keywords(self, keywords):
            raise AssertionError("Feature requests must not load any embedding model")

    for index in range(2):
        with TestClient(create_app(settings, Unavailable())) as client:
            client.headers["Authorization"] = "Bearer " + KEY_A
            if index == 0:
                record = submit(client).json()
            else:
                assert client.get("/v1/feature-requests/" + record["id"]).json() == record
                assert submit(client).status_code == 200
