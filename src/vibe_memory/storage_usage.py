"""Owner storage usage helpers shared by both database backends.

The reported number is a deterministic logical payload size, not the database's
on-disk allocation. This keeps the console value comparable between Kuzu and
PostgreSQL while original file bytes are reported separately.
"""

import json
from collections.abc import Mapping

RECORD_FIELDS = (
    "subtype",
    "title",
    "content",
    "source",
    "tags",
    "keywords",
    "metadata",
    "file_id",
    "provenance",
    "security_warnings",
    "security_history",
)

RELATION_FIELDS = (
    "source_id",
    "target_id",
    "relation",
    "reason",
    "status",
    "history",
    "creator_agent_id",
    "creator_agent_name",
    "confidence",
    "evidence_record_ids",
    "extraction_method",
    "extraction_version",
)

JSON_FIELDS = {"metadata", "provenance", "security_history", "history"}


def value_bytes(value) -> int:
    """Return the UTF-8 byte size of a logical stored value."""

    if value is None:
        return 0
    if isinstance(value, str):
        return len(value.encode("utf-8"))
    return len(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        ).encode("utf-8")
    )


def payload_bytes(item: Mapping, fields: tuple[str, ...]) -> int:
    total = 0
    for field in fields:
        value = item.get(field)
        if field in JSON_FIELDS and isinstance(value, str):
            try:
                value = json.loads(value)
            except (TypeError, ValueError):
                pass
        total += value_bytes(value)
    return total


def file_payload_bytes(metadata) -> int:
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except (TypeError, ValueError):
            return 0
    if not isinstance(metadata, Mapping):
        return 0
    try:
        return max(0, int(metadata.get("size_bytes", 0)))
    except (TypeError, ValueError):
        return 0
