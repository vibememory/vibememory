import pytest
from fastapi.testclient import TestClient

from vibe_memory.app import create_app
from vibe_memory.config import Settings

KEY_A = "a" * 40
KEY_A2 = "c" * 40
KEY_B = "b" * 40


class SpyEmbedder:
    model_name = "test-keyword-vectors-v1"

    def __init__(self):
        self.calls = []

    def keywords(self, keywords):
        self.calls.append(list(keywords))
        return [
            [float(word in {"차", "녹차", "tea"}), float(word in {"Python", "코딩"}), 0.1]
            for word in keywords
        ]


@pytest.fixture
def settings(tmp_path):
    return Settings(
        data_dir=tmp_path,
        database_url=None,
        api_keys={KEY_A: "alice", KEY_A2: "alice", KEY_B: "bob"},
    )


@pytest.fixture
def embedder():
    return SpyEmbedder()


@pytest.fixture
def client(settings, embedder):
    with TestClient(create_app(settings, embedder)) as c:
        c.headers["Authorization"] = "Bearer " + KEY_A
        yield c
