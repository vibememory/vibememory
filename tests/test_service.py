import pytest
from conftest import KEY_A, KEY_A2, KEY_B, SpyEmbedder
from fastapi.testclient import TestClient

from vibe_memory.app import create_app
from vibe_memory.store import Store


def memory(client, text="나는 차를 선호한다", **fields):
    response = client.post("/v1/memories", json={"content": text, "keywords": ["차"], **fields})
    assert response.status_code == 201, response.text
    return response.json()


def relation(client, a, b):
    response = client.post(
        "/v1/relations",
        json={
            "source_id": a["id"],
            "target_id": b["id"],
            "relation": "CUSTOM_AGENT_RELATION",
            "reason": "agent inferred from evidence",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_only_supplied_keywords_embedded(client, embedder):
    a = memory(
        client,
        "PRIVATE RAW CONTENT",
        keywords=[" tea ", "TEA", "녹차"],
        metadata={"agent": "alpha", "summary": "PRIVATE SUMMARY"},
    )
    assert embedder.calls == [["tea", "녹차"]]
    assert a["keywords"] == ["tea", "녹차"]
    response = client.post(
        "/v1/documents",
        json={
            "title": "PRIVATE TITLE",
            "content": "PRIVATE FILE CONTENT",
            "keywords": ["Python"],
            "metadata": {"summary": "PRIVATE FILE SUMMARY", "mime_type": "text/markdown"},
        },
    )
    assert response.status_code == 201, response.text
    assert embedder.calls[-1] == ["Python"]
    result = client.post("/v1/search", json={"keywords": ["tea"]}).json()
    assert embedder.calls[-1] == ["tea"]
    assert result["hits"][0]["id"] == a["id"]
    assert not {"context", "graph", "query"} & result.keys()
    assert result["mode"] == "keyword_vector"
    assert result["hits"][0]["matched_keywords"][0]["stored_keyword"] == "tea"
    assert len(embedder.calls) == 3


def test_auth_multiagent_isolation(client, embedder):
    assert client.get("/v1/records", headers={"Authorization": ""}).status_code == 401
    assert (
        client.post(
            "/v1/search", json={"keywords": ["tea"]}, headers={"Authorization": "Bearer invalid"}
        ).status_code
        == 401
    )
    assert not embedder.calls
    a = memory(client)
    client.headers["Authorization"] = "Bearer " + KEY_A2
    assert client.get("/v1/records/" + a["id"]).json()["content"] == a["content"]
    assert client.post("/v1/search", json={"keywords": ["tea"]}).json()["hits"][0]["id"] == a["id"]
    client.headers["Authorization"] = "Bearer " + KEY_B
    assert client.get("/v1/records/" + a["id"]).status_code == 404
    assert client.delete("/v1/records/" + a["id"]).status_code == 404
    assert (
        client.put("/v1/records/" + a["id"] + "/keywords", json={"keywords": ["x"]}).status_code
        == 404
    )
    assert client.post("/v1/search", json={"keywords": ["tea"]}).json()["hits"] == []
    b = memory(client)
    assert (
        client.post(
            "/v1/relations",
            json={
                "source_id": b["id"],
                "target_id": a["id"],
                "relation": "RELATED_TO",
                "reason": "invalid",
            },
        ).status_code
        == 404
    )
    assert client.get("/v1/graph/" + a["id"]).status_code == 404


def test_agent_entities_metadata_graph_and_retraction(client):
    entity = client.post(
        "/v1/entities",
        json={
            "name": "김개발",
            "entity_type": "Person",
            "description": "에이전트가 식별한 사람",
            "keywords": ["개발자"],
            "metadata": {"confidence": 0.9, "evidence": "message-12"},
        },
    )
    assert entity.status_code == 201, entity.text
    a, b = entity.json(), memory(client)
    edge = relation(client, a, b)
    graph = client.get("/v1/graph/" + a["id"]).json()
    assert len(graph["nodes"]) == 2
    assert graph["nodes"][0]["subtype"] == "Person"
    assert graph["nodes"][0]["metadata"]["confidence"] == 0.9
    change = {"status": "retracted", "reason": "agent revised inference", "expected_version": 1}
    response = client.patch("/v1/relations/" + edge["id"], json=change)
    assert response.status_code == 200 and len(response.json()["history"]) == 2
    assert client.patch("/v1/relations/" + edge["id"], json=change).status_code == 409
    assert len(client.get("/v1/graph/" + a["id"]).json()["nodes"]) == 1
    assert client.delete("/v1/records/" + b["id"]).status_code == 204
    assert client.get("/v1/relations?status=all").json()["items"] == []


def test_metadata_only_file_and_reindex(client, embedder):
    response = client.post(
        "/v1/documents",
        json={
            "title": "binary.pdf",
            "keywords": ["차"],
            "source": "file:///notes/binary.pdf",
            "metadata": {
                "sha256": "agent-supplied",
                "summary": "agent parsed the PDF",
                "pages": 10,
            },
        },
    )
    assert response.status_code == 201, response.text
    doc = response.json()
    assert doc["content"] == ""
    result = client.put("/v1/records/" + doc["id"] + "/keywords", json={"keywords": ["코딩"]})
    assert result.status_code == 200, result.text
    assert embedder.calls == [["차"], ["코딩"]]
    candidates = client.app.state.store.candidates("alice", "documents", [])
    assert [k["content"] for k, _ in candidates] == ["코딩"]
    assert result.json()["metadata"] == doc["metadata"]
    assert client.delete("/v1/records/" + doc["id"]).status_code == 204
    assert client.app.state.store.candidates("alice", "all", []) == []


def test_reject_raw_questions_missing_keywords_and_reserved_relations(client, embedder):
    for body in [
        {"query": "내 취향은?"},
        {"keywords": []},
        {"keywords": [" "]},
        {"keywords": ["tea"], "query": "question"},
        {"keywords": ["x" * 101]},
    ]:
        assert client.post("/v1/search", json=body).status_code == 422
    assert client.post("/v1/memories", json={"content": "raw only"}).status_code == 422
    assert (
        client.post("/v1/documents", json={"title": "raw only", "content": "raw"}).status_code
        == 422
    )
    assert not embedder.calls
    a = memory(client)
    assert (
        client.post(
            "/v1/relations",
            json={
                "source_id": a["id"],
                "target_id": a["id"],
                "relation": "KEYWORD_OF",
                "reason": "reserved",
            },
        ).status_code
        == 422
    )


def test_restart(settings):
    for index in range(2):
        with TestClient(create_app(settings, SpyEmbedder())) as c:
            c.headers["Authorization"] = "Bearer " + KEY_A
            if index == 0:
                a, b = memory(c), memory(c)
                edge = relation(c, a, b)
            else:
                assert c.get("/v1/records/" + a["id"]).json()["keywords"] == ["차"]
                assert c.get("/v1/relations").json()["items"][0]["id"] == edge["id"]
                assert len(c.post("/v1/search", json={"keywords": ["tea"]}).json()["hits"]) == 2


def test_failed_embedding_saves_nothing(settings):
    class Broken(SpyEmbedder):
        def keywords(self, keywords):
            raise RuntimeError("unavailable")

    with TestClient(create_app(settings, Broken())) as c:
        c.headers["Authorization"] = "Bearer " + KEY_A
        assert c.post("/v1/memories", json={"content": "x", "keywords": ["x"]}).status_code == 503
        assert c.get("/v1/records").json()["items"] == []


def test_transaction_rolls_back(settings):
    store = Store(settings.data_dir / "rollback", "test")
    with pytest.raises(RuntimeError), store.transaction():
        store.query("CREATE (:Meta {key: 'rollback-test', value: 'x'})")
        raise RuntimeError("abort")
    assert store.query("MATCH (m:Meta {key: 'rollback-test'}) RETURN m") == []
    store.close()


def test_old_fulltext_index_migration_preserves_records_and_relations(settings):
    from vibe_memory.models import RelationInput

    db = Store(settings.data_dir / "graph", SpyEmbedder.model_name)
    a = db.insert(
        "alice", "memory", "original body", "original title", "agent-a", [], "fact", [], {}, []
    )
    b = db.insert(
        "alice", "document", "original file", "file.pdf", "source", [], "text", [], {}, []
    )
    edge = db.link(
        "alice",
        RelationInput(
            source_id=a["id"], target_id=b["id"], relation="RELATED_TO", reason="original evidence"
        ),
    )
    db.query("MATCH (n:Item {id: $id}) SET n.embedding = [1.0, 0.0]", {"id": a["id"]})
    db.query(
        "CREATE (:Item {id: 'old-chunk', owner: 'alice', kind: 'chunk', parent_id: $id, embedding: [1.0, 0.0]})",
        {"id": a["id"]},
    )
    # Reproduce the previous schema: no agent keyword/metadata columns.
    db.query("ALTER TABLE Item DROP keywords")
    db.query("ALTER TABLE Item DROP metadata")
    db.close()
    embedder = SpyEmbedder()
    with TestClient(create_app(settings, embedder)) as c:
        c.headers["Authorization"] = "Bearer " + KEY_A
        assert not embedder.calls  # Migration never extracts/embeds the old original.
        assert c.get("/v1/records/" + a["id"]).json()["content"] == "original body"
        assert c.get("/v1/records/" + b["id"]).json()["content"] == "original file"
        assert c.get("/v1/relations").json()["items"][0]["id"] == edge["id"]
        assert c.app.state.store.query("MATCH (n:Item {kind: 'chunk'}) RETURN n") == []
        assert c.app.state.store.get("alice", a["id"], True)["embedding"] == []
        assert c.post("/v1/search", json={"keywords": ["tea"]}).json()["hits"] == []
        response = c.put("/v1/records/" + a["id"] + "/keywords", json={"keywords": ["차"]})
        assert response.status_code == 200
        assert c.post("/v1/search", json={"keywords": ["tea"]}).json()["hits"][0]["id"] == a["id"]
