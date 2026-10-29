import pytest
from conftest import KEY_A, SpyEmbedder
from fastapi.testclient import TestClient

from vibe_memory.app import create_app

ORIGIN = "https://vibememory.example"
PASSWORD = "a-long-test-password-123"


@pytest.fixture
def admin_web(settings):
    configured = settings.model_copy(
        update={
            "public_origin": ORIGIN,
            "admin_emails": {"admin@example.com"},
        }
    )
    with TestClient(create_app(configured, SpyEmbedder()), base_url=ORIGIN) as client:
        client.headers["Origin"] = ORIGIN
        yield client


def signup(client, email, name):
    response = client.post(
        "/auth/signup", json={"email": email, "password": PASSWORD, "name": name}
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_admin_feature_request_queue_permissions_and_results(admin_web):
    normal = signup(admin_web, "person@example.com", "요청자")
    assert normal["is_admin"] is False
    owner_id = normal["user"]["id"]
    request = admin_web.post(
        "/v1/feature-requests",
        json={
            "title": "관리자 처리 테스트",
            "description": "처리 결과가 요청자에게 보여야 합니다.",
            "agent_name": "web-console",
            "priority": "high",
        },
    ).json()
    assert admin_web.get("/v1/admin/feature-requests").status_code == 403
    assert admin_web.patch("/v1/feature-requests/" + request["id"], json={}).status_code == 405
    admin_web.post("/auth/logout")

    admin = signup(admin_web, "ADMIN@example.com", "운영자")
    assert admin["is_admin"] is True
    assert admin_web.get("/auth/me").json()["is_admin"] is True
    queue = admin_web.get("/v1/admin/feature-requests").json()
    assert queue["total"] == 1 and queue["counts"]["received"] == 1
    queued = queue["items"][0]
    assert queued["owner_id"] == owner_id
    assert queued["requester"] == {"name": "요청자", "email": "person@example.com"}

    path = f"/v1/admin/feature-requests/{owner_id}/{request['id']}"
    assert (
        admin_web.patch(path, headers={"Origin": ""}, json={"status": "reviewing"}).status_code
        == 403
    )
    reviewing = admin_web.patch(
        path,
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
    assert reviewing["resolved_at"] is None

    completed = admin_web.patch(
        path, json={"status": "completed", "result": "요청한 기능을 구현했습니다."}
    ).json()
    assert completed["resolved_at"] is not None
    assert completed["result_url"] == reviewing["result_url"]
    assert admin_web.get("/v1/admin/feature-requests?status=completed").json()["items"][0][
        "id"
    ] == request["id"]
    assert admin_web.app.state.store.events(owner_id)[-1]["event"] == "feature_request.updated"

    for payload in (
        {},
        {"status": "done"},
        {"status": None},
        {"result": None},
        {"result_url": "javascript:alert(1)"},
        {"result_url": "https://user:secret@example.com/result"},
        {"result": "x" * 10001},
    ):
        assert admin_web.patch(path, json=payload).status_code == 422

    admin_web.post("/auth/logout")
    assert (
        admin_web.get(
            "/v1/admin/feature-requests", headers={"Authorization": "Bearer " + KEY_A}
        ).status_code
        == 401
    )
    login = admin_web.post(
        "/auth/login", json={"email": "person@example.com", "password": PASSWORD}
    )
    assert login.status_code == 200 and login.json()["is_admin"] is False
    visible = admin_web.get("/v1/feature-requests/" + request["id"]).json()
    assert visible["status"] == "completed"
    assert visible["result"] == "요청한 기능을 구현했습니다."
