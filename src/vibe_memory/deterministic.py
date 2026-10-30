"""Deterministic, LLM-free context handoff and graph maintenance helpers."""

import base64
import hashlib
import json
from collections import Counter, defaultdict, deque
from datetime import datetime

from .clock import utc_now_iso
from .corrections import annotate_corrections
from .store import NotFound


class SnapshotConflict(Exception):
    """The graph changed after an opaque cursor or approved diff was issued."""


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value):
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def _wire_size(value):
    return len(_canonical(value).encode())


def _with_wire_size(value):
    value["page_bytes"] = 0
    for _ in range(8):
        size = _wire_size(value)
        if value["page_bytes"] == size:
            break
        value["page_bytes"] = size
    return value


def _updated_at(record):
    history = record.get("writer_history") or []
    values = [item.get("at", "") for item in history if item.get("at")]
    return max(values, default=record["created_at"])


def _all_records(store, owner, include_untrusted=False, include_quarantined=False):
    records, offset = [], 0
    while True:
        page = store.list(
            owner,
            limit=100,
            offset=offset,
            include_untrusted=include_untrusted,
            include_quarantined=include_quarantined,
        )
        records.extend(page)
        if len(page) < 100:
            return records
        offset += len(page)
        if offset >= 10000:
            return records


def _all_relations(store, owner, status="active"):
    relations, cursor = [], 0
    while True:
        page = store.relations(owner, status=status, limit=100, cursor=cursor)
        relations.extend(page)
        if len(page) < 100:
            return relations
        cursor += len(page)
        if cursor >= 50000:
            return relations


def _cursor_encode(selector_hash, snapshot, offset):
    raw = _canonical({"selector": selector_hash, "snapshot": snapshot, "offset": offset})
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def _cursor_decode(value):
    try:
        padding = "=" * (-len(value) % 4)
        payload = json.loads(base64.urlsafe_b64decode(value + padding))
        if (
            set(payload) != {"selector", "snapshot", "offset"}
            or not isinstance(payload["selector"], str)
            or not isinstance(payload["snapshot"], str)
            or not isinstance(payload["offset"], int)
            or payload["offset"] < 0
        ):
            raise ValueError()
        return payload
    except (ValueError, TypeError, json.JSONDecodeError):
        raise ValueError("cursor is invalid") from None


def _record_matches_context(record, data):
    if data.kinds and record["kind"] not in data.kinds:
        return False
    if data.tags and not set(data.tags).issubset(record.get("tags") or []):
        return False
    if data.created_after and datetime.fromisoformat(record["created_at"]) < data.created_after:
        return False
    if data.updated_after and datetime.fromisoformat(_updated_at(record)) < data.updated_after:
        return False
    return True


def _context_record(record, reasons, include_content):
    projected = {
        key: record.get(key)
        for key in (
            "id",
            "kind",
            "subtype",
            "title",
            "source",
            "tags",
            "created_at",
            "keywords",
            "metadata",
            "file_id",
            "version",
            "trust_level",
            "security_state",
            "security_warnings",
            "provenance",
            "content_hash",
            "creator_agent_id",
            "creator_agent_name",
            "supersedes_ids",
            "superseded_by_ids",
            "correction_claims",
            "correction_status",
            "correction_graph_complete",
        )
    }
    projected["updated_at"] = _updated_at(record)
    projected["latest_writer"] = (record.get("writer_history") or [None])[-1]
    projected["retrieval_reason"] = sorted(reasons)
    projected["content_included"] = bool(include_content)
    if include_content:
        projected["content"] = record.get("content", "")
    return projected


def _context_relation(edge):
    return {
        key: edge.get(key)
        for key in (
            "id",
            "source_id",
            "target_id",
            "relation",
            "reason",
            "status",
            "version",
            "created_at",
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
        )
    }


def context_bundle(store, owner, data):
    records = _all_records(
        store, owner, data.include_untrusted, data.include_quarantined
    )
    by_id = {record["id"]: record for record in records}
    relations = [
        edge
        for edge in _all_relations(store, owner)
        if not data.relations or edge["relation"] in data.relations
    ]
    reasons = defaultdict(set)
    selected_ids = set()
    missing = []

    for record_id in data.record_ids:
        if record_id in by_id:
            selected_ids.add(record_id)
            reasons[record_id].add("explicit_id")
        else:
            missing.append(record_id)

    if data.anchor_id:
        if data.anchor_id not in by_id:
            raise NotFound()
        selected_ids.add(data.anchor_id)
        reasons[data.anchor_id].add("anchor")
        adjacency = defaultdict(set)
        for edge in relations:
            if edge["source_id"] in by_id and edge["target_id"] in by_id:
                adjacency[edge["source_id"]].add(edge["target_id"])
                adjacency[edge["target_id"]].add(edge["source_id"])
        queue = deque([(data.anchor_id, 0)])
        visited = {data.anchor_id}
        while queue:
            current, distance = queue.popleft()
            if distance >= data.depth:
                continue
            for related in sorted(adjacency[current]):
                if related in visited:
                    continue
                visited.add(related)
                selected_ids.add(related)
                reasons[related].add(f"relation_path:{distance + 1}")
                queue.append((related, distance + 1))

    has_explicit_seed = bool(data.anchor_id or data.record_ids)
    if not has_explicit_seed:
        selected_ids.update(by_id)
        for record_id in selected_ids:
            reasons[record_id].add("selector_filter")

    selected = []
    for record_id in selected_ids:
        record = by_id[record_id]
        if record_id != data.anchor_id and not _record_matches_context(record, data):
            continue
        if record_id in data.record_ids and not reasons[record_id]:
            reasons[record_id].add("explicit_id")
        selected.append(record)

    annotate_corrections(store, owner, selected)
    selected.sort(key=lambda item: (_updated_at(item), item["id"]), reverse=True)
    selected_set = {record["id"] for record in selected}
    relevant_edges = [
        edge
        for edge in relations
        if edge["source_id"] in selected_set and edge["target_id"] in selected_set
    ]
    relevant_edges.sort(key=lambda edge: (edge["created_at"], edge["id"]))

    selector = data.model_dump(
        mode="json", exclude={"cursor", "limit", "byte_limit"}
    )
    selector_hash = _digest(selector)
    snapshot = _digest(
        {
            "records": [
                (record["id"], record["version"], record.get("content_hash"), _updated_at(record))
                for record in selected
            ],
            "relations": [
                (edge["id"], edge["version"], edge["status"]) for edge in relevant_edges
            ],
        }
    )
    offset = 0
    if data.cursor:
        cursor = _cursor_decode(data.cursor)
        if cursor["selector"] != selector_hash or cursor["snapshot"] != snapshot:
            raise SnapshotConflict()
        offset = cursor["offset"]
    if offset > len(selected):
        raise ValueError("cursor offset is outside the selection")

    def response(page):
        page_ids = {record["id"] for record in page}
        next_offset = offset + len(page)
        payload = {
            "snapshot": snapshot,
            "selector_hash": selector_hash,
            "llm_calls": 0,
            "generated_summary": False,
            "items": page,
            "relations": [
                _context_relation(edge)
                for edge in relevant_edges
                if edge["source_id"] in page_ids or edge["target_id"] in page_ids
            ],
            "missing_record_ids": missing,
            "total": len(selected),
            "next_cursor": (
                _cursor_encode(selector_hash, snapshot, next_offset)
                if next_offset < len(selected)
                else None
            ),
        }
        return _with_wire_size(payload)

    page = []
    for record in selected[offset : offset + data.limit]:
        projected = _context_record(
            record, reasons[record["id"]], data.include_content
        )
        candidate = response([*page, projected])
        if _wire_size(candidate) <= data.byte_limit:
            page.append(projected)
            continue
        if not page and data.include_content:
            projected = _context_record(record, reasons[record["id"]], False)
            projected["content_omitted_due_to_byte_limit"] = True
            candidate = response([projected])
            if _wire_size(candidate) <= data.byte_limit:
                page.append(projected)
                break
        if not page:
            raise ValueError("byte_limit is too small for one metadata record")
        break
    return response(page)


def _cycle_relation_ids(edges):
    adjacency = defaultdict(set)
    for edge in edges:
        adjacency[edge["source_id"]].add(edge["target_id"])

    def reaches(start, target):
        pending, visited = [start], set()
        while pending:
            current = pending.pop()
            if current == target:
                return True
            if current in visited:
                continue
            visited.add(current)
            pending.extend(adjacency[current] - visited)
        return False

    return sorted(
        edge["id"]
        for edge in edges
        if reaches(edge["target_id"], edge["source_id"])
    )


def _relation_claim(edge):
    return {
        key: edge.get(key)
        for key in (
            "source_id",
            "target_id",
            "relation",
            "reason",
            "confidence",
            "evidence_record_ids",
            "evidence",
            "evidence_coverage",
            "input_manifest_id",
            "extraction_method",
            "extraction_version",
            "correction_scope",
        )
    }


def graph_audit(store, owner, data):
    records = _all_records(
        store, owner, data.include_untrusted, data.include_quarantined
    )
    by_id = {record["id"]: record for record in records}
    relations = [
        edge
        for edge in _all_relations(store, owner)
        if not data.relation or edge["relation"] == data.relation
    ]
    valid, missing_endpoints = [], []
    for edge in relations:
        missing = [
            record_id
            for record_id in (edge["source_id"], edge["target_id"])
            if record_id not in by_id
        ]
        if missing:
            missing_endpoints.append({"relation_id": edge["id"], "record_ids": missing})
        else:
            valid.append(edge)
    degree = Counter()
    relation_types = defaultdict(Counter)
    for edge in valid:
        degree[edge["source_id"]] += 1
        degree[edge["target_id"]] += 1
        relation_types[edge["source_id"]][edge["relation"]] += 1
        relation_types[edge["target_id"]][edge["relation"]] += 1
    fingerprints = defaultdict(list)
    for edge in valid:
        fingerprints[_digest(_relation_claim(edge))].append(edge["id"])
    corrections = [
        edge for edge in valid if edge["relation"] in {"SUPERSEDES", "CORRECTS"}
    ]
    incoming = defaultdict(list)
    for edge in corrections:
        incoming[edge["target_id"]].append(edge["id"])
    return {
        "generated_at": utc_now_iso(),
        "llm_calls": 0,
        "content_included": False,
        "stats": {
            "records": len(records),
            "relations": len(valid),
            "orphans": sum(1 for record in records if not degree[record["id"]]),
            "missing_endpoints": len(missing_endpoints),
            "duplicate_claim_groups": sum(1 for ids in fingerprints.values() if len(ids) > 1),
            "correction_cycles": len(_cycle_relation_ids(corrections)),
        },
        "relation_distribution": dict(sorted(Counter(edge["relation"] for edge in valid).items())),
        "orphan_records": [
            {
                "id": record["id"],
                "kind": record["kind"],
                "version": record["version"],
                "tags": record.get("tags") or [],
                "trust_level": record.get("trust_level"),
                "security_state": record.get("security_state"),
            }
            for record in records
            if not degree[record["id"]]
        ],
        "entity_coverage": [
            {
                "id": record["id"],
                "version": record["version"],
                "degree": degree[record["id"]],
                "relations": dict(sorted(relation_types[record["id"]].items())),
            }
            for record in records
            if record["kind"] == "entity"
        ],
        "hub_overflow": [
            {"id": record_id, "degree": value, "kind": by_id[record_id]["kind"]}
            for record_id, value in sorted(degree.items(), key=lambda item: (-item[1], item[0]))
            if value >= data.hub_threshold
        ],
        "correction_cycles": _cycle_relation_ids(corrections),
        "correction_branches": [
            {"record_id": record_id, "incoming_relation_ids": sorted(ids)}
            for record_id, ids in sorted(incoming.items())
            if len(ids) > 1
        ],
        "duplicate_claims": [
            {"fingerprint": fingerprint, "relation_ids": sorted(ids)}
            for fingerprint, ids in sorted(fingerprints.items())
            if len(ids) > 1
        ],
        "missing_endpoints": missing_endpoints,
    }


def _manifest_claim(item):
    claim = item.model_dump(mode="json", exclude={"client_request_id"})
    claim["input_manifest_id"] = claim.get("input_manifest_id") or ""
    return claim


def graph_diff(store, owner, data):
    existing = _all_relations(store, owner)
    existing_by_fingerprint = defaultdict(list)
    existing_by_triple = defaultdict(list)
    for edge in existing:
        existing_by_fingerprint[_digest(_relation_claim(edge))].append(edge)
        existing_by_triple[(edge["source_id"], edge["target_id"], edge["relation"])].append(edge)
    referenced_ids = set(data.scope_record_ids)
    for item in data.items:
        referenced_ids.update((item.source_id, item.target_id))
        referenced_ids.update(item.evidence_record_ids)
        if item.input_manifest_id:
            referenced_ids.add(item.input_manifest_id)
    records = {}
    for record_id in sorted(referenced_ids):
        try:
            records[record_id] = store.get(owner, record_id)
        except NotFound:
            pass

    items, desired_fingerprints, desired_triples = [], set(), set()
    for item in data.items:
        claim = _manifest_claim(item)
        fingerprint = _digest(claim)
        triple = (item.source_id, item.target_id, item.relation)
        desired_fingerprints.add(fingerprint)
        desired_triples.add(triple)
        missing = sorted(
            {
                item.source_id,
                item.target_id,
                *item.evidence_record_ids,
                *([item.input_manifest_id] if item.input_manifest_id else []),
            }
            - set(records)
        )
        if missing:
            classification = "unknown"
            matching = []
        elif existing_by_fingerprint[fingerprint]:
            classification = "unchanged"
            matching = [edge["id"] for edge in existing_by_fingerprint[fingerprint]]
        elif existing_by_triple[triple]:
            classification = "conflicting_claim"
            matching = [edge["id"] for edge in existing_by_triple[triple]]
        else:
            classification = "create"
            matching = []
        items.append(
            {
                "client_request_id": item.client_request_id,
                "source_id": item.source_id,
                "target_id": item.target_id,
                "relation": item.relation,
                "fingerprint": fingerprint,
                "classification": classification,
                "matching_relation_ids": sorted(matching),
                "missing_record_ids": missing,
            }
        )

    retract_candidates = []
    if data.include_retract_candidates:
        scope = set(data.scope_record_ids)
        for edge in existing:
            triple = (edge["source_id"], edge["target_id"], edge["relation"])
            fingerprint = _digest(_relation_claim(edge))
            if (
                edge["source_id"] in scope
                and edge["target_id"] in scope
                and fingerprint not in desired_fingerprints
                and triple not in desired_triples
            ):
                retract_candidates.append(
                    {
                        "id": edge["id"],
                        "source_id": edge["source_id"],
                        "target_id": edge["target_id"],
                        "relation": edge["relation"],
                        "version": edge["version"],
                    }
                )
    retract_candidates.sort(key=lambda edge: edge["id"])
    snapshot = _digest(
        {
            "records": sorted((key, value["version"]) for key, value in records.items()),
            "relations": sorted((edge["id"], edge["version"]) for edge in existing),
        }
    )
    diff_body = {
        "snapshot": snapshot,
        "items": items,
        "retract_candidates": retract_candidates,
        "scope_record_ids": sorted(data.scope_record_ids),
    }
    return {
        **diff_body,
        "diff_hash": _digest(diff_body),
        "generated_at": utc_now_iso(),
        "llm_calls": 0,
        "dry_run": True,
        "summary": dict(Counter(item["classification"] for item in items)),
    }
