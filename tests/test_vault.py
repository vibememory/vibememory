import sqlite3
import stat
from urllib.parse import parse_qs, urlsplit

from conftest import SpyEmbedder
from fastapi.testclient import TestClient

from vibe_memory.app import create_app

ORIGIN = "https://vibememory.io"
PASSWORD = "vault-test-password-123"


def signup(client, email="vault@example.invalid"):
    response = client.post(
        "/auth/signup",
        json={"email": email, "password": PASSWORD, "name": "Vault QA"},
    )
    assert response.status_code == 200, response.text


def test_encrypted_vault_scopes_rotation_and_isolation(settings):
    settings = settings.model_copy(update={"public_origin": ORIGIN, "api_keys": {}})
    with TestClient(create_app(settings, SpyEmbedder()), base_url=ORIGIN) as client:
        client.headers["Origin"] = ORIGIN
        signup(client)
        saved = client.put(
            "/v1/vault/GITHUB_TOKEN",
            json={"value": "github-secret-value", "description": "GitHub automation"},
        )
        assert saved.status_code == 200, saved.text
        assert saved.json()["name"] == "GITHUB_TOKEN"
        assert "value" not in saved.json()
        listed = client.get("/v1/vault").json()["items"]
        assert listed[0]["description"] == "GitHub automation"
        assert "value" not in listed[0]

        unscoped = client.post(
            "/auth/api-keys", json={"name": "ordinary", "vault_access": False}
        ).json()
        scoped = client.post(
            "/auth/api-keys", json={"name": "trusted", "vault_access": True}
        ).json()
        assert client.put(
            "/v1/vault/WHITESPACE", json={"value": "  exact value\n"}
        ).status_code == 200
        keys = {item["name"]: item for item in client.get("/auth/api-keys").json()["items"]}
        assert keys["trusted"]["vault_access"] is True
        assert keys["ordinary"]["vault_access"] is False

        key_path = settings.data_dir / "vault.key"
        assert len(key_path.read_bytes()) == 32
        assert stat.S_IMODE(key_path.stat().st_mode) == 0o600
        with sqlite3.connect(settings.data_dir / "vault.sqlite") as db:
            dump = "\n".join(db.iterdump())
        assert "github-secret-value" not in dump

        client.cookies.clear()
        denied = {"Authorization": "Bearer " + unscoped["key"]}
        allowed = {"Authorization": "Bearer " + scoped["key"]}
        assert client.get("/v1/vault", headers=denied).status_code == 403
        assert client.get("/v1/vault/GITHUB_TOKEN", headers=denied).status_code == 403
        assert client.get("/v1/me", headers=denied).json()["vault_access"] is False
        result = client.get("/v1/vault/GITHUB_TOKEN", headers=allowed)
        assert result.json() == {"name": "GITHUB_TOKEN", "value": "github-secret-value"}
        assert client.get("/v1/vault/WHITESPACE", headers=allowed).json()["value"] == "  exact value\n"
        assert client.get("/v1/vault/MISSING_TOKEN", headers=allowed).status_code == 404
        assert client.get("/v1/me", headers=allowed).json()["vault_access"] is True
        assert (
            client.put(
                "/v1/vault/GITHUB_TOKEN",
                headers=allowed,
                json={"value": "agent-must-not-write"},
            ).status_code
            == 401
        )

        login = client.post(
            "/auth/login",
            json={"email": "vault@example.invalid", "password": PASSWORD},
        )
        assert login.status_code == 200, login.text
        audit = client.get("/v1/vault-access-audit").json()["items"]
        assert {item["outcome"] for item in audit} >= {"success", "denied_scope", "not_found"}
        successful = next(item for item in audit if item["outcome"] == "success")
        denied_item = next(item for item in audit if item["outcome"] == "denied_scope")
        assert successful["client_name"] == "trusted"
        assert successful["client_type"] == "agent-key"
        assert denied_item["client_name"] == "ordinary"
        assert all("value" not in item for item in audit)
        assert "github-secret-value" not in str(audit)
        assert client.post("/auth/logout").status_code == 204

        client.headers.pop("Authorization", None)
        signup(client, "other@example.invalid")
        assert client.get("/v1/vault").json()["items"] == []
        assert client.get("/v1/vault/GITHUB_TOKEN").status_code == 404


def test_vault_restart_rotation_deletion_and_tamper_detection(settings):
    settings = settings.model_copy(update={"public_origin": ORIGIN, "api_keys": {}})
    with TestClient(create_app(settings, SpyEmbedder()), base_url=ORIGIN) as client:
        client.headers["Origin"] = ORIGIN
        signup(client)
        assert client.put("/v1/vault/API_TOKEN", json={"value": "first"}).status_code == 200
        rotated = client.put(
            "/v1/vault/API_TOKEN", json={"value": "second", "description": "rotated"}
        ).json()
        assert rotated["created_at"] <= rotated["updated_at"]
        key = client.post(
            "/auth/api-keys", json={"name": "restart", "vault_access": True}
        ).json()["key"]

    with TestClient(create_app(settings, SpyEmbedder()), base_url=ORIGIN) as client:
        allowed = {"Authorization": "Bearer " + key}
        assert client.get("/v1/vault/API_TOKEN", headers=allowed).json()["value"] == "second"
        with sqlite3.connect(settings.data_dir / "vault.sqlite") as db:
            db.execute(
                "UPDATE vault_secrets SET ciphertext=? WHERE name='API_TOKEN'", (b"tampered",)
            )
        response = client.get("/v1/vault/API_TOKEN", headers=allowed)
        assert response.status_code == 500
        payload = response.json()
        assert payload["detail"] == "Vault entry cannot be decrypted"
        assert payload["error"]["reason_code"] == "VAULT_INTEGRITY_ERROR"
        assert payload["error"]["request_id"] == response.headers["x-request-id"]

        client.headers["Origin"] = ORIGIN
        assert client.post(
            "/auth/login", json={"email": "vault@example.invalid", "password": PASSWORD}
        ).status_code == 200
        assert client.delete("/v1/vault/API_TOKEN").status_code == 204
        assert client.get("/v1/vault").json()["items"] == []


def test_agent_creates_owner_bound_one_time_browser_capture(settings):
    settings = settings.model_copy(update={"public_origin": ORIGIN, "api_keys": {}})
    with TestClient(create_app(settings, SpyEmbedder()), base_url=ORIGIN) as client:
        client.headers["Origin"] = ORIGIN
        signup(client)
        agent_key = client.post(
            "/auth/api-keys", json={"name": "Moltbook agent", "vault_access": True}
        ).json()["key"]

        client.cookies.clear()
        client.headers.pop("Origin")
        created = client.post(
            "/v1/vault/captures",
            headers={"Authorization": "Bearer " + agent_key},
            json={
                "name": "MOLTBOOK_API_KEY",
                "description": "Rotated Moltbook credential",
                "expires_in": 300,
            },
        )
        assert created.status_code == 201, created.text
        capture = created.json()
        assert capture["requester_agent_name"] == "Moltbook agent"
        assert "value" not in capture
        parsed_capture_url = urlsplit(capture["capture_url"])
        assert parsed_capture_url.query == ""
        token = parse_qs(parsed_capture_url.fragment)["token"][0]
        assert len(token) >= 40
        assert client.get(f"/v1/vault/captures/{token}").status_code == 401

        client.headers["Origin"] = ORIGIN
        assert client.post(
            "/auth/login", json={"email": "vault@example.invalid", "password": PASSWORD}
        ).status_code == 200
        inspected = client.get(f"/v1/vault/captures/{token}")
        assert inspected.status_code == 200, inspected.text
        assert inspected.json()["name"] == "MOLTBOOK_API_KEY"

        submitted = client.put(
            f"/v1/vault/captures/{token}", json={"value": "secret-from-browser"}
        )
        assert submitted.status_code == 200, submitted.text
        assert submitted.json()["name"] == "MOLTBOOK_API_KEY"
        assert "value" not in submitted.json()
        assert client.put(
            f"/v1/vault/captures/{token}", json={"value": "replacement"}
        ).status_code == 409
        assert client.get(f"/v1/vault/captures/{token}").status_code == 409

        client.cookies.clear()
        retrieved = client.get(
            "/v1/vault/MOLTBOOK_API_KEY",
            headers={"Authorization": "Bearer " + agent_key},
        )
        assert retrieved.json()["value"] == "secret-from-browser"
        with sqlite3.connect(settings.data_dir / "vault.sqlite") as db:
            dump = "\n".join(db.iterdump())
        assert token not in dump
        assert "secret-from-browser" not in dump


def test_capture_is_hidden_from_other_owner_and_expiry_is_enforced(settings):
    settings = settings.model_copy(update={"public_origin": ORIGIN, "api_keys": {}})
    with TestClient(create_app(settings, SpyEmbedder()), base_url=ORIGIN) as client:
        client.headers["Origin"] = ORIGIN
        signup(client)
        agent_key = client.post(
            "/auth/api-keys", json={"name": "Capture agent", "vault_access": True}
        ).json()["key"]
        client.cookies.clear()
        client.headers.pop("Origin")
        capture_url = client.post(
            "/v1/vault/captures",
            headers={"Authorization": "Bearer " + agent_key},
            json={"name": "SERVICE_TOKEN", "expires_in": 60},
        ).json()["capture_url"]
        token = parse_qs(urlsplit(capture_url).fragment)["token"][0]

        client.headers["Origin"] = ORIGIN
        signup(client, "other@example.invalid")
        assert client.get(f"/v1/vault/captures/{token}").status_code == 404
        client.cookies.clear()
        assert client.post(
            "/auth/login", json={"email": "vault@example.invalid", "password": PASSWORD}
        ).status_code == 200
        with sqlite3.connect(settings.data_dir / "vault.sqlite") as db:
            db.execute("UPDATE vault_captures SET expires_at=0")
        assert client.get(f"/v1/vault/captures/{token}").status_code == 410
        assert client.put(
            f"/v1/vault/captures/{token}", json={"value": "too-late"}
        ).status_code == 410
