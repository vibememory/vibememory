import sqlite3
import stat

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
        assert client.get("/v1/me", headers=denied).json()["vault_access"] is False
        result = client.get("/v1/vault/GITHUB_TOKEN", headers=allowed)
        assert result.json() == {"name": "GITHUB_TOKEN", "value": "github-secret-value"}
        assert client.get("/v1/vault/WHITESPACE", headers=allowed).json()["value"] == "  exact value\n"
        assert client.get("/v1/me", headers=allowed).json()["vault_access"] is True
        assert (
            client.put(
                "/v1/vault/GITHUB_TOKEN",
                headers=allowed,
                json={"value": "agent-must-not-write"},
            ).status_code
            == 401
        )

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
        assert response.json() == {"detail": "Vault entry cannot be decrypted"}

        client.headers["Origin"] = ORIGIN
        assert client.post(
            "/auth/login", json={"email": "vault@example.invalid", "password": PASSWORD}
        ).status_code == 200
        assert client.delete("/v1/vault/API_TOKEN").status_code == 204
        assert client.get("/v1/vault").json()["items"] == []
