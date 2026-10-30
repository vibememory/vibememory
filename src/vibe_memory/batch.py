"""Batch idempotency and compact response helpers."""

import hashlib
import json

from .temporal import recorded_at

RECORD_FIELDS = {
    "id",
    "kind",
    "subtype",
    "title",
    "content",
    "source",
    "tags",
    "created_at",
    "recorded_at",
    "valid_from",
    "valid_to",
    "temporal_completeness",
    "keywords",
    "metadata",
    "file_id",
    "version",
    "trust_level",
    "security_state",
    "provenance",
    "content_hash",
    "security_warnings",
    "security_history",
    "creator_agent_id",
    "creator_agent_name",
    "writer_history",
    "supersedes_ids",
    "superseded_by_ids",
    "correction_claims",
    "correction_status",
    "correction_graph_complete",
}

RELATION_FIELDS = {
    "id",
    "source_id",
    "target_id",
    "relation",
    "reason",
    "status",
    "version",
    "created_at",
    "history",
    "creator_agent_id",
    "creator_agent_name",
    "confidence",
    "evidence_record_ids",
    "evidence",
    "evidence_status",
    "evidence_coverage",
    "input_manifest_id",
    "extraction_method",
    "extraction_version",
    "correction_scope",
    "claim_group",
    "parallel_claim_ids",
}


def request_hash(item):
    payload = item.model_dump(mode="json", exclude={"client_request_id"}, by_alias=True)
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def parse_fields(value, allowed):
    if value is None:
        return None
    raw = value if isinstance(value, list) else value.split(",")
    fields = []
    for item in raw:
        name = item.strip()
        if name and name not in fields:
            fields.append(name)
    unknown = set(fields) - allowed
    if unknown:
        raise ValueError("unknown response fields: " + ", ".join(sorted(unknown)))
    return fields


def project_record(
    record,
    *,
    summary=False,
    fields=None,
    include_content=True,
    include_history=True,
):
    if fields is not None:
        selected = ["id", *(field for field in fields if field != "id")]
        result = {field: record[field] for field in selected if field in record}
    elif summary:
        selected = (
            "id",
            "kind",
            "subtype",
            "title",
            "keywords",
            "tags",
            "created_at",
            "version",
            "trust_level",
            "security_state",
        )
        result = {field: record[field] for field in selected if field in record}
    else:
        result = dict(record)
    if not include_content:
        result.pop("content", None)
    if not include_history:
        result.pop("security_history", None)
        result.pop("writer_history", None)
    temporal = record.get("metadata", {}).get("vibe_memory_temporal", {})
    result["recorded_at"] = recorded_at(record)
    result["valid_from"] = temporal.get("valid_from")
    result["valid_to"] = temporal.get("valid_to")
    result["temporal_completeness"] = "current_versions_only"
    return result


def project_relation(relation, *, fields=None, include_history=True):
    if fields is not None:
        selected = ["id", *(field for field in fields if field != "id")]
        result = {field: relation[field] for field in selected if field in relation}
    else:
        result = dict(relation)
    if not include_history:
        result.pop("history", None)
    return result


def minimal_resource(resource):
    result = {field: resource[field] for field in ("id", "version", "kind") if field in resource}
    if "status" in resource:
        result["resource_status"] = resource["status"]
    return result


def batch_response(items):
    counts = {}
    for item in items:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    return {
        "items": items,
        "counts": counts,
        "total": len(items),
        "atomic": False,
    }
