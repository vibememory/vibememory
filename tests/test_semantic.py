"""Real local keyword embeddings; raw contents are not the search index."""

from pathlib import Path

from conftest import KEY_A, KEY_A2
from fastapi.testclient import TestClient

from vibe_memory.app import create_app
from vibe_memory.config import Settings
from vibe_memory.embeddings import Embedder


def test_real_keyword_search(tmp_path):
    settings = Settings(
        data_dir=tmp_path, database_url=None, api_keys={KEY_A: "me", KEY_A2: "me"}
    )
    embedder = Embedder(settings.embedding_model, Path(".data/models"))
    with TestClient(create_app(settings, embedder)) as client:
        client.headers["Authorization"] = "Bearer " + KEY_A
        # Deliberately conflicting content proves the index follows agent keywords only.
        tea = client.post(
            "/v1/memories",
            json={
                "content": "Python programming and software development",
                "keywords": ["녹차", "음료"],
                "kind": "preference",
            },
        ).json()
        code = client.post(
            "/v1/documents",
            json={
                "title": "Green tea beverages",
                "content": "green tea green tea green tea",
                "keywords": ["Python", "프로그래밍"],
                "metadata": {"summary": "agent classified as software"},
            },
        ).json()
        assert "id" in tea and "id" in code
        client.headers["Authorization"] = "Bearer " + KEY_A2
        result = client.post("/v1/search", json={"keywords": ["green tea"], "limit": 1})
        assert result.status_code == 200, result.text
        assert result.json()["hits"][0]["id"] == tea["id"], result.json()
        result = client.post("/v1/search", json={"keywords": ["software programming"], "limit": 1})
        assert result.json()["hits"][0]["id"] == code["id"], result.json()
        assert result.json()["hits"][0]["metadata"]["summary"] == "agent classified as software"
