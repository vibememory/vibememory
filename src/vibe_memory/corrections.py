"""Deterministic summaries for explicit correction relationships."""

from .security import record_is_retrievable

CORRECTION_RELATIONS = {"SUPERSEDES", "CORRECTS"}


def annotate_corrections(store, owner, records):
    """Attach correction claims without inferring truth or choosing by timestamp."""
    if not records:
        return records
    ids = {record["id"] for record in records}
    edges = (
        store.correction_relations(owner, ids)
        if hasattr(store, "correction_relations")
        else [
            edge
            for edge in store.relations(owner, "all")
            if edge["relation"] in CORRECTION_RELATIONS
            and (edge["source_id"] in ids or edge["target_id"] in ids)
        ]
    )
    edge_pairs = {
        (edge["source_id"], edge["target_id"])
        for edge in edges
        if edge["status"] == "active"
    }
    sources = {edge["source_id"] for edge in edges}
    source_records = {}
    for source_id in sources:
        try:
            source_records[source_id] = store.get(owner, source_id)
        except Exception:
            source_records[source_id] = None

    for record in records:
        outgoing = [edge for edge in edges if edge["source_id"] == record["id"]]
        incoming = [edge for edge in edges if edge["target_id"] == record["id"]]
        claims = []
        for edge in incoming:
            replacement = source_records.get(edge["source_id"])
            lifecycle = edge.get("source_lifecycle", "active")
            trusted = bool(
                replacement and lifecycle == "active" and record_is_retrievable(replacement)
            )
            cycle = (edge["target_id"], edge["source_id"]) in edge_pairs
            effective = bool(
                edge["status"] == "active"
                and trusted
                and not cycle
                and edge.get("correction_scope", "unknown") == "full"
            )
            claims.append(
                {
                    "relation_id": edge["id"],
                    "replacement_id": edge["source_id"],
                    "relation": edge["relation"],
                    "relation_status": edge["status"],
                    "scope": edge.get("correction_scope", "unknown"),
                    "reason": edge["reason"],
                    "created_at": edge["created_at"],
                    "creator_agent_id": edge["creator_agent_id"],
                    "creator_agent_name": edge["creator_agent_name"],
                    "replacement_trusted_and_active": trusted,
                    "replacement_lifecycle": lifecycle,
                    "cycle": cycle,
                    "effective_for_exclusion": effective,
                }
            )
        effective = [claim for claim in claims if claim["effective_for_exclusion"]]
        if any(claim["cycle"] for claim in claims):
            status = "cycle"
        elif len(effective) > 1:
            status = "conflict"
        elif len(effective) == 1 and len(claims) == 1:
            status = "superseded"
        elif claims:
            status = "unresolved"
        else:
            status = "current"
        record["supersedes_ids"] = [edge["target_id"] for edge in outgoing]
        record["superseded_by_ids"] = [edge["source_id"] for edge in incoming]
        record["correction_claims"] = claims
        record["correction_status"] = status
    return records
