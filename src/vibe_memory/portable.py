"""Versioned, deterministic Vibe Memory portable archive helpers.

The archive deliberately excludes credentials, sessions, OTP state and Vault data.
Imported authorship is provenance only; the importing connection remains the creator.
"""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from copy import deepcopy
from uuid import NAMESPACE_URL, uuid5

from .clock import utc_now_iso
from .models import RelationInput
from .security import prepare_record_security
from .store import NotFound

ARCHIVE_VERSION = "1.0"
MAX_ARCHIVE_BYTES = 50 * 1024 * 1024
MAX_ARCHIVE_FILES = 20


def _jsonl(items):
    return b"".join(
        json.dumps(item, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"
        for item in items
    )


def _all_records(store, owner):
    active, offset = [], 0
    while True:
        page = store.list(owner, "", 500, offset, True, True)
        active.extend(page)
        if len(page) < 500:
            break
        offset += len(page)
    archived, offset = [], 0
    while True:
        page = store.archived(owner, 500, offset)
        archived.extend(page)
        if len(page) < 500:
            break
        offset += len(page)
    return [*active, *archived]


def _all_relations(store, owner):
    items, cursor = [], 0
    while True:
        page = store.relations(owner, "all", "", None, "", "", "", "", 500, cursor)
        items.extend(page)
        if len(page) < 500:
            break
        cursor += len(page)
    return items


def _context_reference_ids(item):
    metadata = item.get("metadata") or {}
    references = set()
    core_profile = metadata.get("vibe_memory_profile") or {}
    impact_review = metadata.get("vibe_memory_evidence_impact_review") or {}
    failure = metadata.get("vibe_memory_failure_reproduction") or {}
    state = metadata.get("vibe_memory_agent_state") or {}
    execution = metadata.get("vibe_memory_skill_execution") or {}
    reconciliation = metadata.get("vibe_memory_state_reconciliation") or {}
    if core_profile.get("type") in {"decision", "checkpoint"}:
        references.update(
            reference.get("record_id")
            for reference in core_profile.get("evidence", [])
            if isinstance(reference, dict) and reference.get("record_id")
        )
    impact_evidence = impact_review.get("evidence")
    if isinstance(impact_evidence, dict) and impact_evidence.get("record_id"):
        references.add(impact_evidence["record_id"])
    impact_target = impact_review.get("target")
    if (
        isinstance(impact_target, dict)
        and impact_target.get("kind") == "record"
        and impact_target.get("id")
    ):
        references.add(impact_target["id"])
    failure_sample = failure.get("sample")
    if isinstance(failure_sample, dict) and failure_sample.get("record_id"):
        references.add(failure_sample["record_id"])
    for field in ("decision_refs", "evidence_refs"):
        references.update(
            reference.get("record_id")
            for reference in state.get(field, [])
            if isinstance(reference, dict) and reference.get("record_id")
        )
    for field in ("input_refs", "evidence_refs", "artifact_refs"):
        references.update(
            reference.get("record_id")
            for reference in execution.get(field, [])
            if isinstance(reference, dict) and reference.get("record_id")
        )
    for field in ("task_ref", "environment_ref"):
        reference = execution.get(field)
        if isinstance(reference, dict) and reference.get("record_id"):
            references.add(reference["record_id"])
    references.update(
        reference.get("record_id")
        for reference in reconciliation.get("candidate_refs", [])
        if isinstance(reference, dict) and reference.get("record_id")
    )
    selected = reconciliation.get("selected_ref")
    if isinstance(selected, dict) and selected.get("record_id"):
        references.add(selected["record_id"])
    return references


def _context_reference_roles(item):
    metadata = item.get("metadata") or {}
    state = metadata.get("vibe_memory_agent_state") or {}
    execution = metadata.get("vibe_memory_skill_execution") or {}
    core_profile = metadata.get("vibe_memory_profile") or {}
    impact_review = metadata.get("vibe_memory_evidence_impact_review") or {}
    decision_ids = {
        reference.get("record_id")
        for reference in state.get("decision_refs", [])
        if isinstance(reference, dict) and reference.get("record_id")
    }
    evidence_ids = {
        reference.get("record_id")
        for field in ("evidence_refs", "artifact_refs")
        for reference in execution.get(field, [])
        if isinstance(reference, dict) and reference.get("record_id")
    }
    evidence_ids.update(
        reference.get("record_id")
        for reference in state.get("evidence_refs", [])
        if isinstance(reference, dict) and reference.get("record_id")
    )
    if core_profile.get("type") in {"decision", "checkpoint"}:
        evidence_ids.update(
            reference.get("record_id")
            for reference in core_profile.get("evidence", [])
            if isinstance(reference, dict) and reference.get("record_id")
        )
    impact_evidence = impact_review.get("evidence")
    if isinstance(impact_evidence, dict) and impact_evidence.get("record_id"):
        evidence_ids.add(impact_evidence["record_id"])
    return decision_ids, evidence_ids


def _skill_refs(item):
    metadata = item.get("metadata") or {}
    state = metadata.get("vibe_memory_agent_state") or {}
    execution = metadata.get("vibe_memory_skill_execution") or {}
    capability = metadata.get("vibe_memory_agent_capability_manifest") or {}
    refs = [*state.get("skill_refs", []), *capability.get("skill_refs", [])]
    if isinstance(execution.get("skill"), dict):
        refs.append(execution["skill"])
    return [reference for reference in refs if isinstance(reference, dict)]


def _agent_context_manifest(records, relations, selection):
    ids = {record["id"] for record in records}
    referenced_ids = set()
    profiles = {
        "decision": [],
        "checkpoint": [],
        "failure_reproduction": [],
        "evidence_impact_review": [],
        "agent_state": [],
        "state_reconciliation": [],
        "skill_execution": [],
        "agent_capability_manifest": [],
        "context_lifecycle": [],
    }
    metadata_keys = {
        "failure_reproduction": "vibe_memory_failure_reproduction",
        "evidence_impact_review": "vibe_memory_evidence_impact_review",
        "state_reconciliation": "vibe_memory_state_reconciliation",
        "skill_execution": "vibe_memory_skill_execution",
        "agent_capability_manifest": "vibe_memory_agent_capability_manifest",
        "context_lifecycle": "vibe_memory_context_lifecycle",
        "agent_state": "vibe_memory_agent_state",
    }
    decision_reference_ids = set()
    evidence_reference_ids = set()
    skill_references = {}
    for record in records:
        metadata = record.get("metadata") or {}
        referenced_ids.update(_context_reference_ids(record))
        decision_refs, evidence_refs = _context_reference_roles(record)
        decision_reference_ids.update(decision_refs)
        evidence_reference_ids.update(evidence_refs)
        for reference in _skill_refs(record):
            key = json.dumps(reference, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            skill_references[key] = reference
        core_profile = metadata.get("vibe_memory_profile") or {}
        if core_profile.get("type") in {"decision", "checkpoint"}:
            profiles[core_profile["type"]].append(record["id"])
        for profile, key in metadata_keys.items():
            if isinstance(metadata.get(key), dict):
                profiles[profile].append(record["id"])
    dependency_relations = [
        edge["id"]
        for edge in relations
        if edge.get("relation") in {"DEPENDS_ON", "BLOCKED_BY", "RELATED_TO", "SUPERSEDES"}
    ]
    return {
        "schema_version": "1.0",
        "format": "vibe-memory-agent-context-package",
        "selection": selection,
        "record_ids": sorted(ids),
        "profiles": {key: sorted(value) for key, value in profiles.items()},
        "decision_reference_ids": sorted(decision_reference_ids),
        "evidence_reference_ids": sorted(evidence_reference_ids),
        "skill_refs": [skill_references[key] for key in sorted(skill_references)],
        "dependency_relation_ids": sorted(dependency_relations),
        "omitted_reference_ids": sorted(referenced_ids - ids),
        "secrets_included": False,
        "skill_executables_included": False,
        "permission_grants_included": False,
        "raw_files_included": False,
    }


def _remap_record_ref(reference, id_map):
    if isinstance(reference, dict) and reference.get("record_id") in id_map:
        reference["record_id"] = id_map[reference["record_id"]]


def _remap_context_metadata(metadata, id_map):
    """Remap only references whose records are present in this archive."""

    result = deepcopy(metadata or {})
    core_profile = result.get("vibe_memory_profile") or {}
    if core_profile.get("type") in {"decision", "checkpoint"}:
        for reference in core_profile.get("evidence", []):
            _remap_record_ref(reference, id_map)

    failure = result.get("vibe_memory_failure_reproduction") or {}
    sample = failure.get("sample")
    if isinstance(sample, dict) and sample.get("record_id") in id_map:
        sample["record_id"] = id_map[sample["record_id"]]

    state = result.get("vibe_memory_agent_state") or {}
    for field in ("decision_refs", "evidence_refs"):
        for reference in state.get(field, []):
            _remap_record_ref(reference, id_map)

    execution = result.get("vibe_memory_skill_execution") or {}
    for field in ("task_ref", "environment_ref"):
        _remap_record_ref(execution.get(field), id_map)
    for field in ("input_refs", "evidence_refs", "artifact_refs"):
        for reference in execution.get(field, []):
            _remap_record_ref(reference, id_map)

    reconciliation = result.get("vibe_memory_state_reconciliation") or {}
    for reference in reconciliation.get("candidate_refs", []):
        _remap_record_ref(reference, id_map)
    _remap_record_ref(reconciliation.get("selected_ref"), id_map)

    review = result.get("vibe_memory_evidence_impact_review") or {}
    _remap_record_ref(review.get("evidence"), id_map)
    target = review.get("target")
    if isinstance(target, dict) and target.get("kind") == "record" and target.get("id") in id_map:
        target["id"] = id_map[target["id"]]
    return result


def _validate_context_manifest(context, archive_manifest, records, relations):
    required_false = (
        "secrets_included",
        "skill_executables_included",
        "permission_grants_included",
        "raw_files_included",
    )
    if (
        not isinstance(context, dict)
        or not isinstance(archive_manifest, dict)
        or any(
            not isinstance(record, dict)
            or not isinstance(record.get("metadata") or {}, dict)
            for record in records
        )
        or any(not isinstance(relation, dict) for relation in relations)
    ):
        raise ValueError("invalid agent context package manifest")
    if (
        context.get("format") != "vibe-memory-agent-context-package"
        or context.get("schema_version") != "1.0"
        or context.get("selection") not in {"full", "partial"}
        or context.get("selection") != archive_manifest.get("selection", "full")
        or any(context.get(key) is not False for key in required_false)
    ):
        raise ValueError("invalid agent context package manifest")
    expected = _agent_context_manifest(records, relations, context["selection"])
    if set(context.get("record_ids") or []) != set(expected["record_ids"]):
        raise ValueError("agent context package record coordinates do not match archive")
    if set(context.get("dependency_relation_ids") or []) != set(
        expected["dependency_relation_ids"]
    ):
        raise ValueError("agent context package dependency coordinates do not match archive")
    if set(context.get("omitted_reference_ids") or []) != set(expected["omitted_reference_ids"]):
        raise ValueError("agent context package omitted references do not match archive")
    for field in ("decision_reference_ids", "evidence_reference_ids"):
        if set(context.get(field) or []) != set(expected[field]):
            raise ValueError(f"agent context package {field} do not match archive")
    actual_skill_refs = {
        json.dumps(reference, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        for reference in context.get("skill_refs") or []
        if isinstance(reference, dict)
    }
    expected_skill_refs = {
        json.dumps(reference, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        for reference in expected["skill_refs"]
    }
    if actual_skill_refs != expected_skill_refs or len(actual_skill_refs) != len(
        context.get("skill_refs") or []
    ):
        raise ValueError("agent context package Skill references do not match archive")
    profiles = context.get("profiles")
    if (
        not isinstance(profiles, dict)
        or set(profiles) != set(expected["profiles"])
        or any(
            set(profiles.get(key) or []) != set(value)
            for key, value in expected["profiles"].items()
        )
    ):
        raise ValueError("agent context package profile coordinates do not match archive")
    requested = context.get("requested_record_ids")
    if requested is not None and (
        context["selection"] != "partial"
        or len(requested) != len(set(requested))
        or not set(requested).issubset(set(expected["record_ids"]))
    ):
        raise ValueError("invalid agent context package requested coordinates")


def export_archive(store, owner, namespace_id, record_ids=None):
    all_records = _all_records(store, owner)
    selection = "partial" if record_ids else "full"
    if record_ids:
        requested = list(dict.fromkeys(record_ids))
        by_id = {record["id"]: record for record in all_records}
        missing = [record_id for record_id in requested if record_id not in by_id]
        if missing:
            raise NotFound()
        selected_records = [by_id[record_id] for record_id in requested]
    else:
        requested = []
        selected_records = all_records
    selected_ids = {record["id"] for record in selected_records}
    selected_relations = [
        edge
        for edge in _all_relations(store, owner)
        if edge.get("source_id") in selected_ids and edge.get("target_id") in selected_ids
    ]
    context_manifest = _agent_context_manifest(selected_records, selected_relations, selection)
    if requested:
        context_manifest["requested_record_ids"] = requested
    records = _jsonl(selected_records)
    relations = _jsonl(selected_relations)
    context = json.dumps(context_manifest, ensure_ascii=False, indent=2).encode("utf-8")
    files = {
        "records.jsonl": records,
        "relations.jsonl": relations,
        "agent-context-package.json": context,
    }
    manifest = {
        "format": "vibe-memory-portable-archive",
        "version": ARCHIVE_VERSION,
        "exported_at": utc_now_iso(),
        "time_basis": "UTC",
        "namespace": namespace_id,
        "credentials_included": False,
        "vault_included": False,
        "raw_files_included": False,
        "selection": selection,
        "extensions": {
            "agent_context_package": {
                "version": context_manifest["schema_version"],
                "path": "agent-context-package.json",
            }
        },
        "files": {
            name: {"bytes": len(value), "sha256": hashlib.sha256(value).hexdigest()}
            for name, value in files.items()
        },
    }
    manifest_bytes = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", manifest_bytes)
        for name, value in files.items():
            archive.writestr(name, value)
    return output.getvalue(), manifest


def inspect_archive(body):
    if len(body) > MAX_ARCHIVE_BYTES:
        raise ValueError("archive exceeds 50 MiB")
    try:
        with zipfile.ZipFile(io.BytesIO(body)) as archive:
            listed_names = archive.namelist()
            names = set(listed_names)
            required = {"manifest.json", "records.jsonl", "relations.jsonl"}
            if not required.issubset(names):
                raise ValueError("archive is missing required files")
            if len(listed_names) != len(names) or len(names) > MAX_ARCHIVE_FILES:
                raise ValueError("archive contains duplicate or excessive entries")
            if any(name.startswith("/") or ".." in name.split("/") for name in names):
                raise ValueError("archive contains an unsafe path")
            if sum(info.file_size for info in archive.infolist()) > MAX_ARCHIVE_BYTES:
                raise ValueError("expanded archive exceeds 50 MiB")
            manifest = json.loads(archive.read("manifest.json"))
            if not isinstance(manifest, dict) or manifest.get(
                "format"
            ) != "vibe-memory-portable-archive":
                raise ValueError("unknown archive format")
            if manifest.get("version") != ARCHIVE_VERSION:
                raise ValueError("unsupported archive version")
            if not isinstance(manifest.get("files"), dict):
                raise ValueError("invalid portable archive file manifest")
            payloads = {}
            for name in ("records.jsonl", "relations.jsonl", "agent-context-package.json"):
                if name not in names:
                    continue
                raw = archive.read(name)
                file_info = manifest["files"].get(name)
                if not isinstance(file_info, dict):
                    raise ValueError(f"invalid portable archive manifest for {name}")
                expected = file_info.get("sha256")
                if expected != hashlib.sha256(raw).hexdigest():
                    raise ValueError(f"hash mismatch for {name}")
                payloads[name] = (
                    json.loads(raw)
                    if name == "agent-context-package.json"
                    else [json.loads(line) for line in raw.splitlines() if line.strip()]
                )
    except (zipfile.BadZipFile, KeyError, json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ValueError("invalid portable archive") from error
    context = payloads.get("agent-context-package.json")
    if context is not None:
        _validate_context_manifest(
            context,
            manifest,
            payloads["records.jsonl"],
            payloads["relations.jsonl"],
        )
    return manifest, payloads["records.jsonl"], payloads["relations.jsonl"]


def import_archive(store, embedder, owner, body, agent_id, agent_name, *, apply=False):
    manifest, records, relations = inspect_archive(body)
    collisions, unsupported, broken = [], [], []
    ids = set()
    for item in records:
        if not isinstance(item, dict):
            raise ValueError("archive contains an invalid record")
        record_id = item.get("id")
        keywords = item.get("keywords")
        if (
            not isinstance(record_id, str)
            or not record_id
            or len(record_id) > 100
            or record_id in ids
            or item.get("kind") not in {"memory", "document", "entity", "file"}
            or not isinstance(keywords, list)
            or not isinstance(item.get("metadata") or {}, dict)
            or not 1 <= len(keywords) <= 32
            or any(
                not isinstance(value, str) or not value or len(value) > 100 for value in keywords
            )
        ):
            raise ValueError("archive contains an invalid or duplicate record")
        ids.add(record_id)
        try:
            store.get(owner, record_id, internal=True)
            collisions.append(record_id)
        except NotFound:
            pass
        if item.get("kind") == "file":
            unsupported.append({"id": item.get("id"), "reason": "raw_file_not_in_archive"})
    for edge in relations:
        if not isinstance(edge, dict):
            raise ValueError("archive contains an invalid relationship")
        if edge.get("source_id") not in ids or edge.get("target_id") not in ids:
            broken.append(edge.get("id"))
    report = {
        "format_version": manifest["version"],
        "dry_run": not apply,
        "records": len(records),
        "relations": len(relations),
        "collisions": collisions,
        "unsupported": unsupported,
        "broken_references": broken,
        "lossless": False,
        "limitations": [
            "raw file bytes are not included",
            "record version history is retained as exported provenance but replayed as version 1",
            "imported records are conservatively quarantined until reviewed",
        ],
        "applied": False,
        "id_map": {},
    }
    if not apply or broken:
        return report

    archive_fingerprint = manifest["files"]["records.jsonl"]["sha256"]
    id_map = {
        item["id"]: str(
            uuid5(NAMESPACE_URL, owner + "\0" + item["id"] + "\0" + archive_fingerprint)
        )
        for item in records
        if item.get("kind") != "file"
    }
    existing_imports = set()
    for item in records:
        old_id = item["id"]
        if old_id not in id_map:
            continue
        try:
            existing = store.get(owner, id_map[old_id], internal=True)
        except NotFound:
            continue
        if existing.get("content_hash") == item.get("content_hash"):
            existing_imports.add(old_id)
            continue
        unsupported.append({"id": old_id, "reason": "deterministic_id_conflict"})
        id_map.pop(old_id)

    for item in records:
        if item.get("kind") == "file":
            continue
        old_id = item["id"]
        if old_id not in id_map or old_id in existing_imports:
            continue
        new_id = id_map[old_id]
        keywords = list(item.get("keywords") or [])
        if not keywords:
            unsupported.append({"id": old_id, "reason": "keywords_required"})
            continue
        title = item.get("title") or "Imported record"
        content = item.get("content") or ""
        provenance = {
            "source_type": "imported",
            "origin_agent": item.get("creator_agent_name") or "portable archive",
            "origin_url": "",
            "collected_at": manifest.get("exported_at"),
            "content_type": "application/vnd.vibememory.archive+zip",
            "scan_verdict": "not_scanned",
            "scan_evidence": [],
        }
        metadata = {
            **_remap_context_metadata(item.get("metadata"), id_map),
            "vibe_memory_import": {
                "archive_version": manifest["version"],
                "original_id": old_id,
                "original_creator_agent_id": item.get("creator_agent_id"),
            },
        }
        store.insert(
            owner,
            item.get("kind", "memory"),
            content,
            title,
            item.get("source", ""),
            item.get("tags") or [],
            item.get("subtype", "fact"),
            keywords,
            metadata,
            embedder.keywords(keywords),
            record_id=new_id,
            security=prepare_record_security(title, content, provenance),
            creator_agent_id=agent_id,
            creator_agent_name=agent_name,
        )
    for edge in relations:
        source_id = id_map.get(edge.get("source_id"))
        target_id = id_map.get(edge.get("target_id"))
        if not source_id or not target_id:
            continue
        existing = store.relations(
            owner, "all", "", None, "", edge.get("relation", "RELATED_TO"), source_id, target_id
        )
        if existing:
            continue
        data = RelationInput(
            source_id=source_id,
            target_id=target_id,
            relation=edge.get("relation", "RELATED_TO"),
            reason=edge.get("reason") or "Imported relationship",
            confidence=edge.get("confidence"),
            evidence_record_ids=[
                id_map[value] for value in edge.get("evidence_record_ids", []) if value in id_map
            ],
            evidence_coverage=edge.get("evidence_coverage", "unknown"),
            extraction_method="portable-import",
            extraction_version=ARCHIVE_VERSION,
            correction_scope=edge.get("correction_scope", "unknown"),
        )
        store.link(owner, data, agent_id, agent_name)
    report.update({"applied": True, "id_map": id_map, "unsupported": unsupported})
    report["lossless"] = False
    return report
