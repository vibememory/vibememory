import hashlib
import io
import json
import zipfile
from pathlib import Path

from conftest import KEY_B

CONTRACTS = Path(__file__).parents[1] / "contracts" / "v1"


def state_profile(task_id, status, *, decision_refs=None, evidence_refs=None):
    return {
        "type": "agent_state",
        "version": 1,
        "project_id": "visionflow",
        "task_id": task_id,
        "state_version": 1,
        "status": status,
        "goal": "Complete the shared task",
        "completed": [],
        "next_actions": [],
        "blockers": [],
        "decision_refs": decision_refs or [],
        "evidence_refs": evidence_refs or [],
        "skill_refs": [],
        "reported_harness": {"id": "codex"},
        "observed_at": "2026-11-10T01:00:00Z",
    }


def add_memory(client, content, keywords, metadata):
    response = client.post(
        "/v1/memories",
        json={"content": content, "keywords": keywords, "metadata": metadata},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_state_reconciliation_candidates_and_explicit_resolution(client):
    first = add_memory(
        client,
        "Codex reports task complete",
        ["visionflow", "shared-task", "agent state"],
        {"vibe_memory_agent_state": state_profile("shared-task", "completed")},
    )
    second = add_memory(
        client,
        "Claude Code reports the task blocked",
        ["visionflow", "shared-task", "agent state"],
        {"vibe_memory_agent_state": state_profile("shared-task", "blocked")},
    )

    candidates = client.post(
        "/v1/agent-states/reconciliation/candidates",
        json={"project_id": "visionflow", "task_id": "shared-task"},
    )
    assert candidates.status_code == 200, candidates.text
    payload = candidates.json()
    assert payload["content_included"] is False and payload["llm_calls"] == 0
    assert payload["status_divergence"] is True
    assert payload["distinct_statuses"] == ["blocked", "completed"]
    assert {item["record_id"] for item in payload["candidates"]} == {
        first["id"],
        second["id"],
    }

    hidden = client.post(
        "/v1/agent-states/reconciliation/candidates",
        headers={"Authorization": "Bearer " + KEY_B},
        json={"project_id": "visionflow", "task_id": "shared-task"},
    )
    assert hidden.status_code == 200 and hidden.json()["candidates"] == []

    reconciliation = {
        "type": "state_reconciliation",
        "version": 1,
        "project_id": "visionflow",
        "task_id": "shared-task",
        "status": "resolved",
        "candidate_refs": [
            {"record_id": first["id"], "version": 1},
            {"record_id": second["id"], "version": 1},
        ],
        "selected_ref": {"record_id": second["id"], "version": 1},
        "reported_resolver": "workspace owner",
        "rationale": "The reported blocker was reproduced by the external harness.",
        "observed_at": "2026-11-10T01:05:00Z",
        "resolved_at": "2026-11-10T01:06:00Z",
    }
    resolved = add_memory(
        client,
        "External resolution selected the blocked observation.",
        ["visionflow", "shared-task", "state reconciliation"],
        {"vibe_memory_state_reconciliation": reconciliation},
    )
    assert resolved["metadata"]["vibe_memory_state_reconciliation_status"] == "resolved"

    invalid = json.loads(json.dumps(reconciliation))
    invalid["selected_ref"] = {"record_id": "not-a-candidate", "version": 1}
    rejected = client.post(
        "/v1/memories",
        json={
            "content": "Invalid resolution",
            "keywords": ["state reconciliation"],
            "metadata": {"vibe_memory_state_reconciliation": invalid},
        },
    )
    assert rejected.status_code == 422
    assert "selected_ref must be one of candidate_refs" in rejected.text


def test_capability_manifest_is_declarative_and_not_a_permission_grant(client):
    profile = {
        "type": "agent_capability_manifest",
        "version": 1,
        "manifest_version": 2,
        "agent_id": "codex-worker",
        "harness": {"id": "codex", "version": "6.1"},
        "capabilities": ["code_edit", "test_execution"],
        "skill_refs": [{"id": "python-development", "version": "2.1.0"}],
        "supported_task_types": ["software_change"],
        "required_permissions": ["memory:read", "memory:write"],
        "observed_at": "2026-11-10T01:10:00+01:00",
    }
    stored = add_memory(
        client,
        "Codex worker capability declaration",
        ["codex-worker", "capability manifest"],
        {"vibe_memory_agent_capability_manifest": profile},
    )
    metadata = stored["metadata"]
    assert metadata["vibe_memory_agent_capability_harness"] == "codex"
    assert metadata["vibe_memory_agent_capability_manifest"]["observed_at"] == (
        "2026-11-10T00:10:00Z"
    )

    minimal = client.post(
        "/v1/search",
        json={
            "keywords": ["capability manifest"],
            "match_mode": "exact",
            "projection": "minimal",
        },
    ).json()["hits"][0]
    assert minimal["agent_capability_manifest"]["capability_count"] == 2
    assert "capabilities" not in minimal["agent_capability_manifest"]

    permission = client.post(
        "/v1/permission-check",
        json={"resource": "third_party_service", "operation": "publish"},
    ).json()
    assert permission["authorization"]["status"] == "unknown"


def lifecycle(context_class, retention, policy, *, expires_at=None):
    profile = {
        "type": "context_lifecycle",
        "version": 1,
        "context_class": context_class,
        "retention": retention,
        "context_bundle_policy": policy,
        "observed_at": "2026-11-10T01:15:00Z",
    }
    if expires_at:
        profile["expires_at"] = expires_at
    return profile


def test_context_lifecycle_controls_bundle_selection_without_deletion(client):
    included = add_memory(
        client,
        "Project context included normally",
        ["lifecycle", "included"],
        {"vibe_memory_context_lifecycle": lifecycle("project", "indefinite", "include")},
    )
    explicit = add_memory(
        client,
        "Session context requires an explicit selector",
        ["lifecycle", "explicit"],
        {"vibe_memory_context_lifecycle": lifecycle("session", "manual_archive", "explicit_only")},
    )
    excluded = add_memory(
        client,
        "Ephemeral execution context excluded from normal bundles",
        ["lifecycle", "excluded"],
        {
            "vibe_memory_context_lifecycle": lifecycle(
                "ephemeral_execution", "manual_archive", "exclude"
            )
        },
    )
    expired = add_memory(
        client,
        "Expired session context remains stored",
        ["lifecycle", "expired"],
        {
            "vibe_memory_context_lifecycle": lifecycle(
                "session", "until", "include", expires_at="2020-01-01T00:00:00Z"
            )
        },
    )

    automatic = client.post(
        "/v1/context-bundle",
        json={"kinds": ["memory"], "projection": "minimal", "limit": 100},
    ).json()
    assert {item["id"] for item in automatic["items"]} == {included["id"]}
    assert {item["id"] for item in automatic["lifecycle_excluded"]} == {
        explicit["id"],
        excluded["id"],
        expired["id"],
    }
    assert client.get("/v1/records/" + expired["id"]).status_code == 200

    explicit_bundle = client.post(
        "/v1/context-bundle",
        json={"record_ids": [explicit["id"]], "projection": "minimal"},
    ).json()
    assert explicit_bundle["items"][0]["id"] == explicit["id"]

    excluded_bundle = client.post(
        "/v1/context-bundle",
        json={"record_ids": [excluded["id"]], "projection": "minimal"},
    ).json()
    assert excluded_bundle["items"] == []
    assert excluded_bundle["lifecycle_excluded"] == [{"id": excluded["id"], "reason": "exclude"}]

    override = client.post(
        "/v1/context-bundle",
        json={
            "record_ids": [excluded["id"], expired["id"]],
            "projection": "minimal",
            "include_lifecycle_excluded": True,
        },
    ).json()
    assert {item["id"] for item in override["items"]} == {
        excluded["id"],
        expired["id"],
    }


def test_partial_agent_context_package_and_cross_owner_import(client):
    evidence = add_memory(
        client,
        "Portable observed evidence",
        ["portable", "evidence"],
        {},
    )
    decision = add_memory(
        client,
        "Portable implementation decision",
        ["portable", "decision"],
        {
            "vibe_memory_profile": {
                "type": "decision",
                "version": 1,
                "state": "decided",
                "topic": "Portable task implementation",
                "option": "Use the stable contract",
                "applies_to": {"project": "visionflow", "scope": "portable-task"},
                "reported_decider": "workspace owner",
                "decided_at": "2026-11-10T01:19:00Z",
                "evidence": [{"record_id": evidence["id"], "version": 1}],
            }
        },
    )
    state = add_memory(
        client,
        "Portable task state",
        ["portable", "agent state"],
        {
            "vibe_memory_agent_state": state_profile(
                "portable-task",
                "in_progress",
                decision_refs=[{"record_id": decision["id"], "version": 1}],
                evidence_refs=[
                    {"record_id": evidence["id"], "version": 1},
                    {"record_id": "omitted-evidence", "version": 1},
                ],
            )
        },
    )
    capability = add_memory(
        client,
        "Portable capability declaration",
        ["portable", "capability manifest"],
        {
            "vibe_memory_agent_capability_manifest": {
                "type": "agent_capability_manifest",
                "version": 1,
                "manifest_version": 1,
                "agent_id": "codex-worker",
                "harness": {"id": "codex"},
                "capabilities": ["code_edit"],
                "skill_refs": [{"id": "python-development", "version": "2.1.0"}],
                "supported_task_types": [],
                "required_permissions": [],
                "observed_at": "2026-11-10T01:20:00Z",
            }
        },
    )
    relation = client.post(
        "/v1/relations",
        json={
            "source_id": state["id"],
            "target_id": capability["id"],
            "relation": "RELATED_TO",
            "reason": "The state declares a capability requirement.",
        },
    ).json()

    exported = client.get(
        "/v1/portable-archive",
        params=[
            ("record_id", state["id"]),
            ("record_id", capability["id"]),
            ("record_id", evidence["id"]),
            ("record_id", decision["id"]),
        ],
    )
    assert exported.status_code == 200, exported.text
    with zipfile.ZipFile(io.BytesIO(exported.content)) as archive:
        assert "agent-context-package.json" in archive.namelist()
        context = json.loads(archive.read("agent-context-package.json"))
        manifest = json.loads(archive.read("manifest.json"))
    assert context["selection"] == "partial"
    assert context["profiles"]["agent_state"] == [state["id"]]
    assert context["profiles"]["agent_capability_manifest"] == [capability["id"]]
    assert context["profiles"]["decision"] == [decision["id"]]
    assert context["decision_reference_ids"] == [decision["id"]]
    assert context["evidence_reference_ids"] == [evidence["id"], "omitted-evidence"]
    assert context["skill_refs"] == [{"id": "python-development", "version": "2.1.0"}]
    assert context["dependency_relation_ids"] == [relation["id"]]
    assert context["omitted_reference_ids"] == ["omitted-evidence"]
    assert manifest["extensions"]["agent_context_package"]["version"] == "1.0"

    context["record_ids"] = context["record_ids"][:-1]
    context_bytes = json.dumps(context).encode()
    manifest["files"]["agent-context-package.json"] = {
        "bytes": len(context_bytes),
        "sha256": hashlib.sha256(context_bytes).hexdigest(),
    }
    tampered_buffer = io.BytesIO()
    with (
        zipfile.ZipFile(io.BytesIO(exported.content)) as source,
        zipfile.ZipFile(tampered_buffer, "w", compression=zipfile.ZIP_DEFLATED) as target,
    ):
        for name in source.namelist():
            if name == "manifest.json":
                target.writestr(name, json.dumps(manifest).encode())
            elif name == "agent-context-package.json":
                target.writestr(name, context_bytes)
            else:
                target.writestr(name, source.read(name))
    rejected = client.post(
        "/v1/portable-archive/import",
        headers={"Content-Type": "application/vnd.vibememory.archive+zip"},
        content=tampered_buffer.getvalue(),
    )
    assert rejected.status_code == 422
    assert "record coordinates do not match" in rejected.text

    imported = client.post(
        "/v1/portable-archive/import?apply=true",
        headers={
            "Authorization": "Bearer " + KEY_B,
            "Content-Type": "application/vnd.vibememory.archive+zip",
        },
        content=exported.content,
    )
    assert imported.status_code == 200, imported.text
    report = imported.json()
    assert report["applied"] is True and report["lossless"] is False
    assert report["id_map"][state["id"]] != state["id"]
    imported_records = client.get(
        "/v1/records?include_untrusted=true&include_quarantined=true",
        headers={"Authorization": "Bearer " + KEY_B},
    ).json()["items"]
    imported_state = next(
        item for item in imported_records if item["id"] == report["id_map"][state["id"]]
    )
    assert imported_state["metadata"]["vibe_memory_agent_state"]["task_id"] == "portable-task"
    imported_refs = imported_state["metadata"]["vibe_memory_agent_state"]["evidence_refs"]
    assert imported_refs == [
        {"record_id": report["id_map"][evidence["id"]], "version": 1},
        {"record_id": "omitted-evidence", "version": 1},
    ]
    assert imported_state["metadata"]["vibe_memory_agent_state"]["decision_refs"] == [
        {"record_id": report["id_map"][decision["id"]], "version": 1}
    ]
    imported_decision = next(
        item for item in imported_records if item["id"] == report["id_map"][decision["id"]]
    )
    assert imported_decision["metadata"]["vibe_memory_profile"]["evidence"] == [
        {"record_id": report["id_map"][evidence["id"]], "version": 1}
    ]
    assert imported_state["creator_agent_id"] != state["creator_agent_id"]

    repeated = client.post(
        "/v1/portable-archive/import?apply=true",
        headers={
            "Authorization": "Bearer " + KEY_B,
            "Content-Type": "application/vnd.vibememory.archive+zip",
        },
        content=exported.content,
    ).json()
    assert repeated["id_map"] == report["id_map"]
    after_repeat = client.get(
        "/v1/records?include_untrusted=true&include_quarantined=true",
        headers={"Authorization": "Bearer " + KEY_B},
    ).json()["items"]
    assert len(after_repeat) == len(imported_records)


def test_followup_contracts_are_discoverable(client):
    discovery = client.get("/.well-known/vibe-memory").json()
    names = {
        "state_reconciliation_profile": "state-reconciliation-profile.json",
        "agent_capability_manifest_profile": "agent-capability-manifest-profile.json",
        "context_lifecycle_profile": "context-lifecycle-profile.json",
        "agent_context_package": "agent-context-package.json",
    }
    for name, filename in names.items():
        assert discovery["contracts"][name].endswith("/" + filename)
        schema = json.loads((CONTRACTS / filename).read_text())
        assert schema["$schema"].endswith("2020-12/schema")
