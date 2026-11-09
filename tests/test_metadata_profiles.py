import copy
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


def failure_profile(**overrides):
    profile = {
        "type": "failure_reproduction",
        "version": 1,
        "outcome": "failed",
        "observed_at": "2026-11-09T14:00:00+09:00",
        "sample": {
            "identifier": "synthetic-two-row-csv",
            "input_rows": 2,
            "input_bytes": 25,
            "input_excerpt_redacted": "name,value\nalpha,not-a-number",
        },
        "attempted_settings": [
            {"name": "delimiter", "value_redacted": ","},
            {"name": "number_mode", "value_redacted": "strict"},
        ],
        "failure": {
            "stage": "number-coercion",
            "code": "INVALID_NUMBER",
            "message_redacted": "row 2 value could not be parsed as a number",
        },
        "minimal_reproduction": {
            "conditions": ["use the two-row synthetic sample", "enable strict number mode"],
            "command": "parser --delimiter , synthetic.csv",
            "expected_result": "two parsed rows",
            "observed_result": "INVALID_NUMBER at row 2",
        },
        "parsing_steps": [
            {
                "order": 1,
                "stage": "tokenize",
                "operation": "split comma-delimited row",
                "input_summary": "row 2",
                "output_summary": "tokens alpha and not-a-number",
            },
            {
                "order": 2,
                "stage": "number-coercion",
                "operation": "strict decimal conversion",
                "input_summary": "token not-a-number",
                "output_summary": "INVALID_NUMBER",
            },
        ],
        "evidence_references": [
            {"kind": "uploaded_file", "file_id": "file-synthetic", "file_version": 1},
            {
                "kind": "external",
                "reference": "/private/fixtures/synthetic.csv",
                "expected_sha256": "a" * 64,
                "expected_bytes": 25,
                "verification": {"status": "unverified"},
            },
        ],
    }
    profile.update(overrides)
    return profile


def test_failure_reproduction_profile_preserves_path_and_never_executes(client, tmp_path):
    sentinel = tmp_path / "must-not-run"
    profile = failure_profile()
    profile["minimal_reproduction"]["command"] = f"touch {sentinel}"
    profile["evidence_references"][1]["reference"] = str(sentinel)
    created = client.post(
        "/v1/memories",
        json={
            "content": "Strict parsing failed on the synthetic CSV sample.",
            "keywords": ["synthetic CSV", "INVALID_NUMBER", "failure reproduction"],
            "metadata": {"vibe_memory_failure_reproduction": profile},
        },
    )
    assert created.status_code == 201
    metadata = created.json()["metadata"]
    stored = metadata["vibe_memory_failure_reproduction"]
    assert stored["observed_at"] == "2026-11-09T05:00:00Z"
    assert stored["sample"]["input_rows"] == 2
    assert [step["operation"] for step in stored["parsing_steps"]] == [
        "split comma-delimited row",
        "strict decimal conversion",
    ]
    assert metadata["vibe_memory_failure_outcome"] == "failed"
    assert metadata["vibe_memory_failure_stage"] == "number-coercion"
    assert metadata["vibe_memory_failure_reference_status"] == "unverified"
    assert not sentinel.exists()

    bundle = client.post(
        "/v1/context-bundle", json={"record_ids": [created.json()["id"]], "limit": 10}
    ).json()
    assert bundle["items"][0]["metadata"]["vibe_memory_failure_reproduction"] == stored

    alternate = copy.deepcopy(profile)
    alternate["parsing_steps"][0]["operation"] = "quoted-field CSV tokenizer"
    alternate["parsing_steps"][0]["output_summary"] = "same tokens through a different path"
    second = client.post(
        "/v1/memories",
        json={
            "content": "The same final error occurred through an alternate tokenization path.",
            "keywords": ["synthetic CSV", "alternate parsing path"],
            "metadata": {"vibe_memory_failure_reproduction": alternate},
        },
    )
    assert second.status_code == 201
    assert second.json()["id"] != created.json()["id"]
    assert (
        second.json()["metadata"]["vibe_memory_failure_reproduction"]["parsing_steps"][0][
            "operation"
        ]
        == "quoted-field CSV tokenizer"
    )


def test_external_reference_states_distinguish_changed_missing_and_inaccessible(client):
    statuses = {
        "changed": {
            "status": "changed",
            "checked_at": "2026-11-09T05:01:00Z",
            "observed_sha256": "b" * 64,
            "observed_bytes": 25,
        },
        "missing": {
            "status": "missing",
            "checked_at": "2026-11-09T05:02:00Z",
            "detail_redacted": "path did not exist",
        },
        "inaccessible": {
            "status": "inaccessible",
            "checked_at": "2026-11-09T05:03:00Z",
            "detail_redacted": "client lacked read permission",
        },
    }
    for status, verification in statuses.items():
        profile = failure_profile()
        profile["evidence_references"] = [
            {
                "kind": "external",
                "reference": "/fixtures/synthetic.csv",
                "expected_sha256": "a" * 64,
                "expected_bytes": 25,
                "verification": verification,
            }
        ]
        response = client.post(
            "/v1/memories",
            json={
                "content": f"External evidence was {status}.",
                "keywords": ["external evidence", status],
                "metadata": {"vibe_memory_failure_reproduction": profile},
            },
        )
        assert response.status_code == 201
        assert response.json()["metadata"]["vibe_memory_failure_reference_status"] == status


def test_failure_profile_rejects_secret_setting_and_false_comparison(client):
    secret_profile = failure_profile()
    secret_profile["attempted_settings"] = [
        {"name": "api_token", "value_redacted": "must-not-store"}
    ]
    secret = client.post(
        "/v1/memories",
        json={
            "content": "invalid sensitive setting",
            "keywords": ["failure"],
            "metadata": {"vibe_memory_failure_reproduction": secret_profile},
        },
    )
    assert secret.status_code == 422
    assert "must not identify secrets" in secret.text

    false_match = failure_profile()
    false_match["evidence_references"] = [
        {
            "kind": "external",
            "reference": "/fixtures/synthetic.csv",
            "expected_sha256": "a" * 64,
            "verification": {
                "status": "match",
                "checked_at": "2026-11-09T05:04:00Z",
                "observed_sha256": "b" * 64,
            },
        }
    ]
    mismatch = client.post(
        "/v1/memories",
        json={
            "content": "invalid match claim",
            "keywords": ["failure"],
            "metadata": {"vibe_memory_failure_reproduction": false_match},
        },
    )
    assert mismatch.status_code == 422
    assert "match coordinates must be equal" in mismatch.text


def test_profile_contracts_match_runtime_examples():
    decision_schema = json.loads((CONTRACTS / "decision-profile.json").read_text())
    checkpoint_schema = json.loads((CONTRACTS / "checkpoint-profile.json").read_text())
    failure_schema = json.loads(
        (CONTRACTS / "failure-reproduction-profile.json").read_text()
    )
    assert decision_schema["properties"]["state"]["enum"] == [
        "proposed", "open", "decided", "rejected", "unknown"
    ]
    assert "author_reported" in checkpoint_schema["properties"]["observation_kind"]["enum"]
    assert failure_schema["properties"]["type"]["const"] == "failure_reproduction"
    assert {"uploaded_file", "external"} == {
        item["$ref"].split("/")[-1]
        for item in failure_schema["properties"]["evidence_references"]["items"]["oneOf"]
    }
