import io
import zipfile

import pytest
from conftest import SpyEmbedder
from fastapi.testclient import TestClient

from vibe_memory.app import create_app


def test_console_and_api_share_one_origin(settings):
    settings = settings.model_copy(update={"public_origin": "http://testserver"})
    with TestClient(create_app(settings, SpyEmbedder())) as client:
        for route, phrase in [
            ("/", "Vibe Memory"),
            ("/login", "auth-form"),
            ("/console", "console-main"),
            ("/guide", "Vibe Memory"),
        ]:
            response = client.get(route)
            assert response.status_code == 200
            assert phrase in response.text
        console_script = client.get("/assets/console.js")
        assert console_script.status_code == 200
        assert "설치 프롬프트 복사하기" in console_script.text
        assert "location.origin" in console_script.text
        assert "/downloads/vibe-memory-skill.zip" in console_script.text
        assert "login --vault-access --no-browser" in console_script.text
        assert "vault exec" in console_script.text
        assert "relationship-graph-stage" in console_script.text
        assert "prefers-reduced-motion" in client.get("/assets/console.css").text
        console = client.get("/console").text
        assert "topbar-search" in console
        assert "sidebar-backdrop" in console
        assert 'data-view="vault"' in console
        assert "vault-scope" in client.get("/connect").text
        assert client.get("/assets/brands/openclaw.svg").status_code == 200
        assert client.get("/v1/records").status_code == 401
        assert client.get("/.env").status_code == 404
        assert client.get("/../../.env").status_code == 404
        signup = client.post(
            "/auth/signup",
            headers={"Origin": "http://testserver"},
            json={
                "name": "Self host",
                "email": "selfhost@example.invalid",
                "password": "long-enough-password",
            },
        )
        assert signup.status_code == 200, signup.text
        assert client.get("/v1/stats").json()["memory"] == 0
        key = client.post(
            "/auth/api-keys",
            headers={"Origin": "http://testserver"},
            json={"name": "Self-hosted agent"},
        )
        assert key.status_code == 201
        result = client.post(
            "/v1/memories",
            headers={"Authorization": "Bearer " + key.json()["key"]},
            json={"content": "Self-hosted memory", "keywords": ["Python"]},
        )
        assert result.status_code == 201, result.text
        assert client.get("/v1/records").json()["items"][0]["id"] == result.json()["id"]
        archive = client.get("/downloads/vibe-memory-skill.zip")
        with zipfile.ZipFile(io.BytesIO(archive.content)) as skill:
            assert set(skill.namelist()) == {
                "vibe-memory/SKILL.md",
                "vibe-memory/scripts/memory.py",
            }


def test_explicit_web_directory_rejects_missing_index(settings, tmp_path):
    with pytest.raises(ValueError, match="MEMORY_WEB_DIR"):
        create_app(settings.model_copy(update={"web_dir": tmp_path / "missing"}), SpyEmbedder())
