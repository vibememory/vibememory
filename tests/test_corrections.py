from conftest import KEY_A2


def create_memory(client, content, keyword, headers=None):
    response = client.post(
        "/v1/memories",
        headers=headers,
        json={"content": content, "keywords": [keyword]},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_atomic_correction_visibility_authorship_and_search_policy(client):
    old = create_memory(client, "tea preference is green", "tea preference")
    other = {"Authorization": "Bearer " + KEY_A2}
    payload = {
        "previous_id": old["id"],
        "expected_previous_version": old["version"],
        "replacement": {
            "content": "tea preference is black",
            "keywords": ["tea preference"],
        },
        "relation": "SUPERSEDES",
        "correction_scope": "full",
        "reason": "user explicitly replaced the whole preference",
        "client_request_id": "tea-correction-1",
    }
    response = client.post("/v1/corrections/memories", headers=other, json=payload)
    assert response.status_code == 201, response.text
    result = response.json()
    replacement = result["record"]
    assert replacement["creator_agent_id"] != old["creator_agent_id"]
    assert replacement["writer_history"][0]["writer_agent_id"] == replacement["creator_agent_id"]
    assert result["relation"]["correction_scope"] == "full"

    # Same authenticated agent + request ID is idempotent and creates no duplicate.
    repeated = client.post("/v1/corrections/memories", headers=other, json=payload)
    assert repeated.status_code == 201
    assert repeated.json()["record"]["id"] == replacement["id"]

    previous = client.get(f"/v1/records/{old['id']}").json()
    assert previous["correction_status"] == "superseded"
    assert previous["superseded_by_ids"] == [replacement["id"]]
    claim = previous["correction_claims"][0]
    assert claim["creator_agent_id"] == replacement["creator_agent_id"]
    assert claim["reason"] == payload["reason"]
    assert claim["effective_for_exclusion"] is True

    included = client.post(
        "/v1/search",
        json={"keywords": ["tea preference"], "match_mode": "exact", "limit": 10},
    ).json()["hits"]
    assert old["id"] in {hit["id"] for hit in included}
    excluded = client.post(
        "/v1/search",
        json={
            "keywords": ["tea preference"],
            "match_mode": "exact",
            "limit": 10,
            "exclude_resolved_superseded": True,
        },
    ).json()["hits"]
    assert old["id"] not in {hit["id"] for hit in excluded}
    assert replacement["id"] in {hit["id"] for hit in excluded}


def test_competing_corrections_remain_visible_and_stale_operation_rolls_back(client):
    old = create_memory(client, "original decision", "decision")
    base = {
        "previous_id": old["id"],
        "expected_previous_version": 1,
        "relation": "CORRECTS",
        "correction_scope": "full",
        "reason": "explicit correction",
    }
    for index, text in enumerate(("branch one", "branch two"), 1):
        response = client.post(
            "/v1/corrections/memories",
            json={
                **base,
                "replacement": {"content": text, "keywords": ["decision"]},
                "client_request_id": f"branch-{index}",
            },
        )
        assert response.status_code == 201, response.text
    current = client.get(f"/v1/records/{old['id']}").json()
    assert current["correction_status"] == "conflict"
    assert len(current["superseded_by_ids"]) == 2
    hits = client.post(
        "/v1/search",
        json={
            "keywords": ["decision"],
            "match_mode": "exact",
            "exclude_resolved_superseded": True,
            "limit": 10,
        },
    ).json()["hits"]
    assert old["id"] in {hit["id"] for hit in hits}

    before = client.get("/v1/stats").json()["memory"]
    stale = client.post(
        "/v1/corrections/memories",
        json={
            **base,
            "expected_previous_version": 999,
            "replacement": {"content": "must roll back", "keywords": ["rollback"]},
            "client_request_id": "stale-correction",
        },
    )
    assert stale.status_code == 409
    assert client.get("/v1/stats").json()["memory"] == before


def test_archived_or_retracted_replacement_is_visible_but_never_hides_old_record(client):
    old = create_memory(client, "old lifecycle value", "lifecycle")
    correction = client.post(
        "/v1/corrections/memories",
        json={
            "previous_id": old["id"],
            "expected_previous_version": 1,
            "replacement": {"content": "replacement", "keywords": ["lifecycle"]},
            "relation": "SUPERSEDES",
            "correction_scope": "full",
            "reason": "explicit replacement",
            "client_request_id": "lifecycle-correction",
        },
    ).json()
    replacement = correction["record"]
    archived = client.post(
        f"/v1/records/{replacement['id']}/archive",
        json={"expected_version": 1, "reason": "replacement withdrawn"},
    )
    assert archived.status_code == 200
    current = client.get(f"/v1/records/{old['id']}").json()
    assert current["correction_status"] == "unresolved"
    assert current["correction_claims"][0]["replacement_lifecycle"] == "archived"
    assert current["correction_claims"][0]["effective_for_exclusion"] is False

    restored = client.post(
        f"/v1/records/{replacement['id']}/restore",
        json={"expected_version": 2, "reason": "review again"},
    ).json()
    relation = correction["relation"]
    retracted = client.patch(
        f"/v1/relations/{relation['id']}",
        json={"expected_version": relation["version"], "status": "retracted", "reason": "withdrawn"},
    )
    assert restored["version"] == 3 and retracted.status_code == 200
    current = client.get(f"/v1/records/{old['id']}").json()
    assert current["correction_status"] == "unresolved"
    assert current["correction_claims"][0]["relation_status"] == "retracted"
