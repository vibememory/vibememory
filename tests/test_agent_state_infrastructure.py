import io
import json
import zipfile
from pathlib import Path

from conftest import KEY_A2, KEY_B

CONTRACTS = Path(__file__).parents[1] / "contracts" / "v1"


def state_profile(task_id, status="in_progress", state_version=1, harness="claude-code"):
    return {
        "type": "agent_state",
        "version": 1,
        "project_id": "visionflow",
        "task_id": task_id,
        "state_version": state_version,
        "status": status,
        "goal": f"Complete {task_id}",
        "completed": ["Inference interface implemented"] if state_version > 1 else [],
        "next_actions": ["Run integration tests"] if status != "completed" else [],
        "blockers": [],
        "decision_refs": [],
        "evidence_refs": [],
        "skill_refs": [{"id": "python-development", "version": "2.1.0"}],
        "reported_harness": {"id": harness, "version": "1.0"},
        "observed_at": "2026-11-10T09:00:00+09:00",
    }


def add_state(client, task_id, status="in_progress"):
    response = client.post(
        "/v1/memories",
        json={
            "content": f"Task state for {task_id}",
            "kind": "event",
            "keywords": ["visionflow", task_id, "agent state"],
            "tags": ["agent-state"],
            "metadata": {"vibe_memory_agent_state": state_profile(task_id, status)},
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_agent_state_handoff_uses_existing_record_version_and_context_bundle(client):
    state = add_state(client, "inspection-node")
    metadata = state["metadata"]
    assert metadata["vibe_memory_agent_state_status"] == "in_progress"
    assert metadata["vibe_memory_agent_state_project_id"] == "visionflow"
    assert metadata["vibe_memory_agent_state"]["observed_at"] == "2026-11-10T00:00:00Z"
    assert state["version"] == 1

    minimal = client.post(
        "/v1/search",
        json={
            "keywords": ["inspection-node"],
            "match_mode": "exact",
            "projection": "minimal",
            "metadata_filters": {
                "vibe_memory_agent_state_project_id": "visionflow",
                "vibe_memory_agent_state_status": "in_progress",
            },
        },
    ).json()["hits"][0]
    assert minimal["agent_state"] == {
        "profile_version": 1,
        "project_id": "visionflow",
        "task_id": "inspection-node",
        "state_version": 1,
        "status": "in_progress",
        "reported_harness": "claude-code",
    }
    assert "metadata" not in minimal

    handoff = client.post(
        "/v1/context-bundle",
        headers={"Authorization": "Bearer " + KEY_A2},
        json={"record_ids": [state["id"]], "projection": "minimal"},
    )
    assert handoff.status_code == 200, handoff.text
    assert handoff.json()["items"][0]["agent_state"]["status"] == "in_progress"

    completed_profile = state_profile(
        "inspection-node", "completed", state_version=2, harness="codex"
    )
    completed = client.patch(
        "/v1/records/" + state["id"],
        headers={"Authorization": "Bearer " + KEY_A2},
        json={
            "expected_version": 1,
            "metadata": {"vibe_memory_agent_state": completed_profile},
        },
    )
    assert completed.status_code == 200, completed.text
    updated = completed.json()
    assert updated["version"] == 2
    assert updated["metadata"]["vibe_memory_agent_state_status"] == "completed"
    assert updated["metadata"]["vibe_memory_agent_state_harness"] == "codex"
    assert updated["creator_agent_id"] != updated["writer_history"][-1]["writer_agent_id"]

    stale = client.patch(
        "/v1/records/" + state["id"],
        json={"expected_version": 1, "source": "stale Claude Code update"},
    )
    assert stale.status_code == 409
    current = client.get("/v1/records/" + state["id"]).json()
    assert current["metadata"]["vibe_memory_agent_state_status"] == "completed"
    assert "vibe_memory_profile" not in current["metadata"]


def test_task_dependency_graph_reuses_relations_and_reports_cycles(client):
    training = add_state(client, "model-training")
    export = add_state(client, "onnx-export")
    deployment = add_state(client, "edge-deployment", "blocked")

    def relate(source, target, relation):
        response = client.post(
            "/v1/relations",
            json={
                "source_id": source["id"],
                "target_id": target["id"],
                "relation": relation,
                "reason": "Agent-authored task dependency",
                "evidence_record_ids": [source["id"]],
                "extraction_method": "agent-state-contract",
                "extraction_version": "1",
            },
        )
        assert response.status_code == 201, response.text
        return response.json()

    first = relate(export, training, "DEPENDS_ON")
    second = relate(deployment, export, "DEPENDS_ON")
    third = relate(training, deployment, "BLOCKED_BY")
    relate(training, export, "RELATED_TO")

    audit = client.post("/v1/graph/audit", json={}).json()
    assert audit["llm_calls"] == 0 and audit["content_included"] is False
    assert set(audit["dependency_cycles"]) == {first["id"], second["id"], third["id"]}
    assert audit["stats"]["dependency_cycles"] == 3

    shared = client.get(
        "/v1/graph/" + deployment["id"],
        headers={"Authorization": "Bearer " + KEY_A2},
    )
    assert shared.status_code == 200
    assert second["id"] in {edge["id"] for edge in shared.json()["relations"]}

    hidden = client.get(
        "/v1/graph/" + deployment["id"],
        headers={"Authorization": "Bearer " + KEY_B},
    )
    assert hidden.status_code == 404


def test_skill_execution_profile_is_data_only_and_preserved_in_minimal_handoff(
    client, tmp_path
):
    task = add_state(client, "inspection-node")
    sentinel = tmp_path / "must-not-run"
    profile = {
        "type": "skill_execution",
        "version": 1,
        "skill": {"id": "python-development", "digest": "sha256:" + "A" * 64},
        "reported_harness": {"id": "codex", "version": "6.1"},
        "reported_agent": "codex-worker",
        "task_ref": {"record_id": task["id"], "version": 1},
        "input_refs": [{"record_id": task["id"], "version": 1}],
        "started_at": "2026-11-10T00:10:00Z",
        "finished_at": "2026-11-10T00:11:00Z",
        "reported_status": "failed",
        "failure_reason": f"External harness reported: touch {sentinel}",
        "verification_status": "author_reported",
        "evidence_refs": [],
        "artifact_refs": [],
    }
    response = client.post(
        "/v1/memories",
        json={
            "content": "The external harness reported a failed Skill execution.",
            "kind": "event",
            "keywords": ["python-development", "skill execution", "inspection-node"],
            "metadata": {"vibe_memory_skill_execution": profile},
        },
    )
    assert response.status_code == 201, response.text
    stored = response.json()
    execution = stored["metadata"]["vibe_memory_skill_execution"]
    assert execution["skill"]["digest"] == "sha256:" + "a" * 64
    assert stored["metadata"]["vibe_memory_skill_execution_status"] == "failed"
    assert not sentinel.exists()

    bundle = client.post(
        "/v1/context-bundle",
        json={"record_ids": [stored["id"]], "projection": "minimal"},
    ).json()
    assert bundle["items"][0]["skill_execution"] == {
        "profile_version": 1,
        "skill_id": "python-development",
        "skill_version": None,
        "reported_status": "failed",
        "verification_status": "author_reported",
        "reported_harness": "codex",
    }
    assert "failure_reason" not in json.dumps(bundle["items"][0])

    exported = client.get("/v1/portable-archive")
    with zipfile.ZipFile(io.BytesIO(exported.content)) as archive:
        records = [json.loads(line) for line in archive.read("records.jsonl").splitlines()]
    portable_execution = next(item for item in records if item["id"] == stored["id"])
    assert portable_execution["metadata"]["vibe_memory_skill_execution"] == execution
    portable_task = next(item for item in records if item["id"] == task["id"])
    assert portable_task["metadata"]["vibe_memory_agent_state"]["task_id"] == (
        "inspection-node"
    )

    no_version = json.loads(json.dumps(profile))
    no_version["skill"] = {"id": "python-development"}
    invalid = client.post(
        "/v1/memories",
        json={
            "content": "Invalid Skill execution",
            "keywords": ["skill execution"],
            "metadata": {"vibe_memory_skill_execution": no_version},
        },
    )
    assert invalid.status_code == 422
    assert "version or digest" in invalid.text


def test_agent_state_and_skill_contracts_match_runtime_shape():
    state = json.loads((CONTRACTS / "agent-state-profile.json").read_text())
    execution = json.loads((CONTRACTS / "skill-execution-profile.json").read_text())
    assert state["properties"]["status"]["enum"] == [
        "unknown",
        "planned",
        "in_progress",
        "blocked",
        "completed",
        "cancelled",
    ]
    assert state["properties"]["state_version"]["minimum"] == 1
    assert execution["properties"]["type"]["const"] == "skill_execution"
    assert "never downloads or runs" in execution["description"]
