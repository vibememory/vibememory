import json
from pathlib import Path

CONTRACTS = Path(__file__).parents[1] / "contracts" / "v1"


def test_decision_profile_is_validated_normalized_and_preserved(client):
    evidence = client.post(
        "/v1/memories",
        json={"content": "User rejected Redis for Atlas", "keywords": ["Atlas", "Redis"]},
    ).json()
    profile = {
        "type": "decision",
        "version": 1,
        "state": "rejected",
        "topic": "Atlas persistence",
        "option": "Redis",
        "applies_to": {"project": "Atlas", "scope": "persistence layer"},
        "reported_decider": "user",
        "decided_at": "2026-11-07T12:30:00+09:00",
        "evidence": [{"record_id": evidence["id"], "version": 1}],
        "reason": "Restore guarantees are required",
        "reconsider_when": ["Redis persistence requirements change"],
    }
    created = client.post(
        "/v1/memories",
        json={
            "content": "Atlas rejected Redis for its persistence layer.",
            "keywords": ["Atlas", "Redis", "decision"],
            "metadata": {"vibe_memory_profile": profile},
        },
    )
    assert created.status_code == 201
    metadata = created.json()["metadata"]
    assert metadata["vibe_memory_profile"]["decided_at"] == "2026-11-07T03:30:00Z"
    assert metadata["vibe_memory_profile_type"] == "decision"
    assert metadata["vibe_memory_profile_state"] == "rejected"

    result = client.post(
        "/v1/search",
        json={
            "keywords": ["Atlas"],
            "match_mode": "exact",
            "metadata_filters": {
                "vibe_memory_profile_type": "decision",
                "vibe_memory_profile_state": "rejected",
            },
        },
    ).json()
    assert result["hits"][0]["metadata"]["vibe_memory_profile"]["topic"] == "Atlas persistence"

    bundle = client.post(
        "/v1/context-bundle", json={"record_ids": [created.json()["id"]], "limit": 10}
    ).json()
    assert bundle["items"][0]["metadata"]["vibe_memory_profile"]["state"] == "rejected"
    assert bundle["items"][0]["creator_agent_name"]


def test_profile_absence_is_not_automatically_decided(client):
    created = client.post(
        "/v1/memories", json={"content": "Redis was discussed", "keywords": ["Redis"]}
    ).json()
    assert "vibe_memory_profile" not in created["metadata"]
    assert "vibe_memory_profile_state" not in created["metadata"]


def test_decision_profile_rejects_unsubstantiated_terminal_shape(client):
    response = client.post(
        "/v1/memories",
        json={
            "content": "Redis decided",
            "keywords": ["Redis"],
            "metadata": {
                "vibe_memory_profile": {
                    "type": "decision",
                    "version": 1,
                    "state": "decided",
                    "topic": "database",
                    "applies_to": {"scope": "project"},
                }
            },
        },
    )
    assert response.status_code == 422
    assert "reported_decider" in response.text


def test_checkpoint_profile_preserves_claim_and_observation_without_execution(client, tmp_path):
    sentinel = tmp_path / "must-not-exist"
    command = f"touch {sentinel}"
    created = client.post(
        "/v1/memories",
        json={
            "content": "Local tests reported as passing; deployment remains unknown.",
            "keywords": ["checkpoint", "tests"],
            "metadata": {
                "vibe_memory_profile": {
                    "type": "checkpoint",
                    "version": 1,
                    "claimed_stage": "local_tests_passed",
                    "observation_kind": "author_reported",
                    "target": {"project": "Atlas", "scope": "API", "environment": "local"},
                    "observed_at": "2026-11-07T03:40:00Z",
                    "commit": "abc1234",
                    "environment_identity": "python 3.13 / linux",
                    "reproduction": {"command": command, "reported_result": "42 passed"},
                    "remaining_unknowns": ["production deployment not observed"],
                }
            },
        },
    )
    assert created.status_code == 201
    metadata = created.json()["metadata"]
    assert metadata["vibe_memory_profile_state"] == "local_tests_passed"
    assert metadata["vibe_memory_profile_observation"] == "author_reported"
    assert metadata["vibe_memory_profile"]["reproduction"]["command"] == command
    assert not sentinel.exists()

    invalid_update = client.patch(
        "/v1/records/" + created.json()["id"],
        json={
            "expected_version": 1,
            "metadata": {
                "vibe_memory_profile": {
                    "type": "checkpoint",
                    "version": 2,
                    "claimed_stage": "deployed",
                    "observation_kind": "observed",
                    "target": {"scope": "production"},
                    "observed_at": "2026-11-07T03:40:00Z",
                }
            },
        },
    )
    assert invalid_update.status_code == 422


def test_profile_contracts_match_runtime_examples():
    decision_schema = json.loads((CONTRACTS / "decision-profile.json").read_text())
    checkpoint_schema = json.loads((CONTRACTS / "checkpoint-profile.json").read_text())
    assert decision_schema["properties"]["state"]["enum"] == [
        "proposed", "open", "decided", "rejected", "unknown"
    ]
    assert "author_reported" in checkpoint_schema["properties"]["observation_kind"]["enum"]
