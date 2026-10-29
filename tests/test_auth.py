import sqlite3

import pytest
from conftest import SpyEmbedder
from fastapi.testclient import TestClient

from vibe_memory.app import create_app
from vibe_memory.auth import COOKIE, digest

ORIGIN = "https://vibememory.io"
PASSWORD = "a-long-test-password-123"


@pytest.fixture
def web_settings(settings):
    return settings.model_copy(update={"public_origin": ORIGIN, "api_keys": {}})


@pytest.fixture
def web(web_settings):
    with TestClient(create_app(web_settings, SpyEmbedder()), base_url=ORIGIN) as client:
        client.headers["Origin"] = ORIGIN
        yield client


def signup(client, email="person@example.com", name="내 계정"):
    response = client.post(
        "/auth/signup", json={"email": email, "password": PASSWORD, "name": name}
    )
    assert response.status_code == 200, response.text
    return response


def test_signup_cookie_session_user_and_logout(web, web_settings):
    response = signup(web)
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "secure" in cookie and "samesite=lax" in cookie
    assert response.json()["user"]["email"] == "person@example.com"
    assert web.get("/auth/me").json()["user"]["name"] == "내 계정"
    assert web.get("/v1/records").status_code == 200
    assert web.get("/v1/stats").json() == {
        "memory": 0,
        "document": 0,
        "entity": 0,
        "file": 0,
        "relations": 0,
    }
    saved = web.post("/v1/memories", json={"content": "차를 선호한다", "keywords": ["차"]})
    assert saved.status_code == 201
    assert web.get("/v1/stats").json()["memory"] == 1
    token = web.cookies.get(COOKIE)
    assert web.post("/auth/logout").status_code == 204
    assert web.get("/auth/me").status_code == 401
    assert web.get("/v1/records").status_code == 401
    web.cookies.set(COOKIE, token)
    assert web.get("/auth/me").status_code == 401
    with sqlite3.connect(web_settings.data_dir / "auth.sqlite") as db:
        row = db.execute("SELECT password_hash,salt FROM users").fetchone()
        assert PASSWORD not in row and len(row[1]) == 32
        assert db.execute("SELECT count(*) FROM sessions").fetchone()[0] == 0


def test_login_wrong_password_duplicate_and_origin_guard(web):
    signup(web)
    assert (
        web.post(
            "/auth/signup",
            json={"email": "PERSON@example.com", "password": PASSWORD, "name": "duplicate"},
        ).status_code
        == 409
    )
    web.post("/auth/logout")
    assert (
        web.post(
            "/auth/login", json={"email": "person@example.com", "password": "wrong-password-123"}
        ).status_code
        == 401
    )
    response = web.post("/auth/login", json={"email": "PERSON@example.com", "password": PASSWORD})
    assert response.status_code == 200
    for origin in ["", "https://evil.example"]:
        assert (
            web.post(
                "/v1/memories", headers={"Origin": origin}, json={"content": "x", "keywords": ["x"]}
            ).status_code
            == 403
        )
        assert (
            web.post(
                "/auth/api-keys", headers={"Origin": origin}, json={"name": "unsafe"}
            ).status_code
            == 403
        )
        assert web.post("/auth/logout", headers={"Origin": origin}).status_code == 403
        assert (
            web.post(
                "/auth/signup",
                headers={"Origin": origin},
                json={"name": "x", "email": "new@example.com", "password": PASSWORD},
            ).status_code
            == 403
        )
    assert web.get("/v1/records").json()["items"] == []
    assert web.get("/auth/me").headers["cache-control"] == "no-store"


def test_revocable_agent_keys_separate_from_browser_auth(web, web_settings):
    signup(web)
    response = web.post("/auth/api-keys", json={"name": "Claude Code"})
    assert response.status_code == 201, response.text
    key = response.json()
    assert len(key["key"]) >= 32
    listed = web.get("/auth/api-keys").json()["items"][0]
    assert "key" not in listed and listed["vault_access"] is False
    changed = web.patch(
        "/auth/api-keys/" + key["id"], json={"vault_access": True}
    ).json()
    assert changed == {"id": key["id"], "vault_access": True}
    with sqlite3.connect(web_settings.data_dir / "auth.sqlite") as db:
        row = db.execute("SELECT hash FROM api_keys").fetchone()
        assert row[0] == digest(key["key"]) and row[0] != key["key"]
    headers = {"Authorization": "Bearer " + key["key"], "Origin": ""}
    result = web.post(
        "/v1/memories", headers=headers, json={"content": "agent memory", "keywords": ["차"]}
    )
    assert result.status_code == 201, result.text
    assert web.get("/v1/agents").json()["items"][0]["id"] == "key:" + key["id"]
    assert web.get("/v1/records").json()["items"][0]["id"] == result.json()["id"]
    # Invalid explicit keys must not silently fall back to an existing browser session.
    assert web.get("/v1/records", headers={"Authorization": "Bearer invalid"}).status_code == 401
    assert web.delete("/auth/api-keys/" + key["id"]).status_code == 204
    assert web.get("/v1/agents").json()["items"] == []
    assert web.get("/v1/records", headers=headers).status_code == 401
    assert web.get("/v1/records").status_code == 200


def test_accounts_isolated_and_session_expiry(web, web_settings):
    alice = signup(web).json()["user"]
    record = web.post("/v1/memories", json={"content": "private", "keywords": ["차"]}).json()
    key = web.post("/auth/api-keys", json={"name": "private"}).json()
    web.post("/auth/logout")
    bob = signup(web, "bob@example.com", "Bob").json()["user"]
    assert alice["id"] != bob["id"]
    assert web.get("/v1/records").json()["items"] == []
    assert web.get("/v1/records/" + record["id"]).status_code == 404
    assert web.delete("/auth/api-keys/" + key["id"]).status_code == 404
    assert web.get("/auth/api-keys").json()["items"] == []
    with sqlite3.connect(web_settings.data_dir / "auth.sqlite") as db:
        db.execute("UPDATE sessions SET expires_at=0 WHERE user_id=?", (bob["id"],))
    assert web.get("/auth/me").status_code == 401


def test_restart_sessions_and_login_throttle(web_settings):
    for i in range(2):
        with TestClient(create_app(web_settings, SpyEmbedder()), base_url=ORIGIN) as client:
            client.headers["Origin"] = ORIGIN
            if i == 0:
                signup(client)
                token = client.cookies.get(COOKIE)
            else:
                client.cookies.set(COOKIE, token)
                assert client.get("/auth/me").status_code == 200
                for _ in range(12):
                    assert (
                        client.post(
                            "/auth/login",
                            json={"email": "person@example.com", "password": "wrong-password-123"},
                        ).status_code
                        == 401
                    )
                assert (
                    client.post(
                        "/auth/login", json={"email": "person@example.com", "password": PASSWORD}
                    ).status_code
                    == 429
                )


def test_validation_and_disabled_signup(web, web_settings):
    for data in [
        {"name": " ", "email": "a@example.com", "password": PASSWORD},
        {"name": "A", "email": "not-email", "password": PASSWORD},
        {"name": "A", "email": "a@example.com", "password": "short"},
    ]:
        assert web.post("/auth/signup", json=data).status_code == 422
    disabled = web_settings.model_copy(
        update={"data_dir": web_settings.data_dir / "disabled", "signup_enabled": False}
    )
    with TestClient(create_app(disabled, SpyEmbedder()), base_url=ORIGIN) as client:
        client.headers["Origin"] = ORIGIN
        assert (
            client.post(
                "/auth/signup", json={"name": "A", "email": "a@example.com", "password": PASSWORD}
            ).status_code
            == 403
        )
