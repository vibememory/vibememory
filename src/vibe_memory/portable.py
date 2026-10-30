"""Versioned, deterministic Vibe Memory portable archive helpers.

The archive deliberately excludes credentials, sessions, OTP state and Vault data.
Imported authorship is provenance only; the importing connection remains the creator.
"""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
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


def export_archive(store, owner, namespace_id):
    records = _jsonl(_all_records(store, owner))
    relations = _jsonl(_all_relations(store, owner))
    files = {"records.jsonl": records, "relations.jsonl": relations}
    manifest = {
        "format": "vibe-memory-portable-archive",
        "version": ARCHIVE_VERSION,
        "exported_at": utc_now_iso(),
        "time_basis": "UTC",
        "namespace": namespace_id,
        "credentials_included": False,
        "vault_included": False,
        "raw_files_included": False,
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
            if manifest.get("format") != "vibe-memory-portable-archive":
                raise ValueError("unknown archive format")
            if manifest.get("version") != ARCHIVE_VERSION:
                raise ValueError("unsupported archive version")
            payloads = {}
            for name in ("records.jsonl", "relations.jsonl"):
                raw = archive.read(name)
                expected = (manifest.get("files") or {}).get(name, {}).get("sha256")
                if expected != hashlib.sha256(raw).hexdigest():
                    raise ValueError(f"hash mismatch for {name}")
                payloads[name] = [json.loads(line) for line in raw.splitlines() if line.strip()]
    except (zipfile.BadZipFile, KeyError, json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ValueError("invalid portable archive") from error
    return manifest, payloads["records.jsonl"], payloads["relations.jsonl"]


def import_archive(store, embedder, owner, body, agent_id, agent_name, *, apply=False):
    manifest, records, relations = inspect_archive(body)
    collisions, unsupported, broken = [], [], []
    ids = set()
    for item in records:
        record_id = item.get("id")
        keywords = item.get("keywords")
        if (
            not isinstance(record_id, str)
            or not record_id
            or len(record_id) > 100
            or record_id in ids
            or item.get("kind") not in {"memory", "document", "entity", "file"}
            or not isinstance(keywords, list)
            or not 1 <= len(keywords) <= 32
            or any(not isinstance(value, str) or not value or len(value) > 100 for value in keywords)
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

    id_map = {}
    for item in records:
        if item.get("kind") == "file":
            continue
        old_id = item["id"]
        new_id = (
            str(
                uuid5(
                    NAMESPACE_URL,
                    owner
                    + "\0"
                    + old_id
                    + "\0"
                    + manifest["files"]["records.jsonl"]["sha256"],
                )
            )
            if old_id in collisions
            else old_id
        )
        id_map[old_id] = new_id
        try:
            existing = store.get(owner, new_id, internal=True)
            if existing.get("content_hash") == item.get("content_hash"):
                continue
            unsupported.append({"id": old_id, "reason": "deterministic_id_conflict"})
            continue
        except NotFound:
            pass
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
            **(item.get("metadata") or {}),
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
        source_id, target_id = id_map.get(edge.get("source_id")), id_map.get(edge.get("target_id"))
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
            evidence_record_ids=[id_map[value] for value in edge.get("evidence_record_ids", []) if value in id_map],
            evidence_coverage=edge.get("evidence_coverage", "unknown"),
            extraction_method="portable-import",
            extraction_version=ARCHIVE_VERSION,
            correction_scope=edge.get("correction_scope", "unknown"),
        )
        store.link(owner, data, agent_id, agent_name)
    report.update({"applied": True, "id_map": id_map, "unsupported": unsupported})
    report["lossless"] = False
    return report
