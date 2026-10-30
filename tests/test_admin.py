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
            "title": "관리자가 정리한 요청 제목",
            "description": "다른 사용자가 등록한 요구사항을 관리자가 명확하게 정리했습니다.",
            "use_case": "운영자가 요청을 재현하고 구현 범위를 기록합니다.",
            "priority": "medium",
            "status": "reviewing",
            "result": "기술 검토를 시작했습니다.",
            "result_url": "https://github.com/vibememory/vibememory/issues/1",
        },
    )
    assert reviewing.status_code == 200, reviewing.text
    reviewing = reviewing.json()
    assert reviewing["status"] == "reviewing"
    assert reviewing["title"] == "관리자가 정리한 요청 제목"
    assert reviewing["description"].startswith("다른 사용자가 등록한")
    assert reviewing["use_case"].startswith("운영자가 요청을")
    assert reviewing["priority"] == "medium"
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
        {"title": " "},
        {"description": " "},
        {"priority": "urgent"},
        {"agent_name": "forged-agent"},
        {"owner_id": "another-user"},
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
    assert visible["title"] == "관리자가 정리한 요청 제목"
    assert visible["description"].startswith("다른 사용자가 등록한")
    assert visible["result"] == "요청한 기능을 구현했습니다."


def test_admin_user_directory_exposes_operational_counts_without_credentials(admin_web):
    person = signup(admin_web, "person2@example.com", "사용자 둘")
    owner_id = person["user"]["id"]
    key = admin_web.post(
        "/auth/api-keys", json={"name": "Agent", "vault_access": False}
    )
    assert key.status_code == 201
    assert admin_web.post(
        "/v1/memories", json={"content": "admin listing", "keywords": ["admin"]}
    ).status_code == 201
    assert admin_web.get("/v1/admin/users").status_code == 403
    admin_web.post("/auth/logout")

    signup(admin_web, "admin@example.com", "운영자")
    response = admin_web.get("/v1/admin/users?q=person2")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["total"] == 1
    user = payload["items"][0]
    assert user["id"] == owner_id
    assert user["name"] == "사용자 둘"
    assert user["email"] == "person2@example.com"
    assert user["is_admin"] is False
    assert user["api_key_count"] == 1
    assert user["active_session_count"] == 0
    assert user["totp_enabled"] is False
    assert user["record_count"] == 1
    assert user["storage_bytes"] >= user["memory_bytes"] > 0
    assert "password_hash" not in str(payload)
    assert "salt" not in str(payload)
    assert "hash" not in str(payload)


def test_admin_can_grant_and_revoke_scoped_feature_request_operator(admin_web):
    normal = signup(admin_web, "operator-requester@example.com", "요청 사용자")
    owner_id = normal["user"]["id"]
    feature = admin_web.post(
        "/v1/feature-requests",
        json={
            "title": "운영 에이전트 테스트",
            "description": "관리자가 승인한 에이전트만 처리해야 합니다.",
            "agent_name": "requester-agent",
        },
    ).json()
    assert admin_web.get("/v1/admin/operator-agents").status_code == 403
    admin_web.post("/auth/logout")

    signup(admin_web, "admin@example.com", "운영자")
    key = admin_web.post(
        "/auth/api-keys", json={"name": "Codex operator", "vault_access": False}
    ).json()
    agent_headers = {"Authorization": "Bearer " + key["key"], "Origin": ""}
    assert admin_web.get("/v1/admin/feature-requests", headers=agent_headers).status_code == 403
    listed = admin_web.get("/v1/admin/operator-agents").json()["items"]
    assert listed[0]["id"] == key["id"]
    assert listed[0]["feature_request_operator"] is False
    grant_path = "/v1/admin/operator-agents/" + key["id"]
    assert (
        admin_web.patch(
            grant_path,
            headers={"Origin": "https://evil.example"},
            json={"feature_request_operator": True},
        ).status_code
        == 403
    )
    granted = admin_web.patch(grant_path, json={"feature_request_operator": True})
    assert granted.json() == {"id": key["id"], "feature_request_operator": True}
    assert admin_web.get("/v1/me", headers=agent_headers).json()[
        "feature_request_operator"
    ] is True

    admin_web.post("/auth/logout")
    queue = admin_web.get("/v1/admin/feature-requests", headers=agent_headers)
    assert queue.status_code == 200
    assert queue.json()["items"][0]["owner_id"] == owner_id
    path = f"/v1/admin/feature-requests/{owner_id}/{feature['id']}"
    updated = admin_web.patch(
        path,
        headers=agent_headers,
        json={"status": "reviewing", "result": "운영 에이전트가 검토 중입니다."},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["result"].startswith("운영 에이전트가")
    assert admin_web.get("/v1/admin/users", headers=agent_headers).status_code == 401

    login = admin_web.post(
        "/auth/login", json={"email": "admin@example.com", "password": PASSWORD}
    )
    assert login.status_code == 200
    revoked = admin_web.patch(grant_path, json={"feature_request_operator": False})
    assert revoked.json()["feature_request_operator"] is False
    admin_web.post("/auth/logout")
    assert admin_web.get("/v1/admin/feature-requests", headers=agent_headers).status_code == 403
