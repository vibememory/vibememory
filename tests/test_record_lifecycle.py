def memory(client, content, keywords, metadata=None):
    response = client.post(
        "/v1/memories",
        json={"content": content, "keywords": keywords, "metadata": metadata or {}},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_search_relevance_controls_do_not_embed_exact_filters(client, embedder):
    exact = memory(client, "Exact project", ["Project Alpha", "active"], {"project": "alpha"})
    memory(client, "Excluded project", ["Project Alpha", "archived"], {"project": "alpha"})
    memory(client, "Other project", ["Project Beta", "active"], {"project": "beta"})
    calls = len(embedder.calls)

    result = client.post(
        "/v1/search",
        json={
            "keywords": ["project alpha"],
            "match_mode": "exact",
            "must_keywords": ["active"],
            "exclude_keywords": ["archived"],
            "metadata_filters": {"project": "alpha"},
            "min_score": 1.0,
        },
    )
    assert result.status_code == 200, result.text
    assert [hit["id"] for hit in result.json()["hits"]] == [exact["id"]]
    assert result.json()["match_mode"] == "exact"
    assert len(embedder.calls) == calls


def test_versioned_update_archive_restore_and_merge(client, embedder):
    canonical = memory(client, "Canonical", ["project"])
    duplicate = memory(client, "Duplicate", ["project", "duplicate"])
    entity = client.post(
        "/v1/entities",
        json={"name": "Owner", "entity_type": "Person", "keywords": ["owner"]},
    ).json()
    relation = client.post(
        "/v1/relations",
        json={
            "source_id": duplicate["id"],
            "target_id": entity["id"],
            "relation": "OWNED_BY",
            "reason": "Agent-confirmed duplicate relation",
        },
    )
    assert relation.status_code == 201, relation.text

    updated = client.patch(
        "/v1/records/" + canonical["id"],
        json={
            "expected_version": 1,
            "content": "Canonical with unique information",
            "keywords": ["project", "owner"],
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["version"] == 2
    assert client.patch(
        "/v1/records/" + canonical["id"],
        json={"expected_version": 1, "content": "stale update"},
    ).status_code == 409

    merged = client.post(
        "/v1/records/merge",
        json={
            "canonical_id": canonical["id"],
            "duplicate_ids": [duplicate["id"]],
            "expected_versions": {canonical["id"]: 2, duplicate["id"]: 1},
            "reason": "Same project confirmed",
        },
    )
    assert merged.status_code == 200, merged.text
    assert merged.json()["canonical"]["version"] == 3
    assert merged.json()["archived_ids"] == [duplicate["id"]]
    assert client.get("/v1/records/" + duplicate["id"]).status_code == 404
    trash = client.get("/v1/trash").json()["items"]
    archived = next(item for item in trash if item["id"] == duplicate["id"])
    assert archived["version"] == 2
    graph = client.get("/v1/graph/" + canonical["id"]).json()
    assert entity["id"] in {node["id"] for node in graph["nodes"]}

    restored = client.post(
        "/v1/records/" + duplicate["id"] + "/restore",
        json={"expected_version": 2, "reason": "Need the original record again"},
    )
    assert restored.status_code == 200, restored.text
    assert restored.json()["version"] == 3
    assert embedder.calls[-1] == ["project", "owner"]
