"""Deterministic summaries for explicit correction relationships."""

from .security import record_is_retrievable

CORRECTION_RELATIONS = {"SUPERSEDES", "CORRECTS"}
MAX_CORRECTION_NODES = 256
MAX_CORRECTION_EDGES = 512


def _correction_closure(store, owner, seed_ids):
    """Load a bounded connected correction graph around the requested records."""
    seen_ids = set(seed_ids)
    expanded = set()
    edges_by_id = {}
    truncated = False
    while frontier := seen_ids - expanded:
        remaining = MAX_CORRECTION_EDGES - len(edges_by_id)
        if remaining <= 0:
            truncated = True
            break
        fetched = store.correction_relations(owner, frontier, limit=remaining + 1)
        expanded.update(frontier)
        if len(fetched) > remaining:
            fetched = fetched[:remaining]
            truncated = True
        for edge in fetched:
            edges_by_id[edge["id"]] = edge
        connected = {
            record_id
            for edge in fetched
            for record_id in (edge["source_id"], edge["target_id"])
        }
        new_ids = connected - seen_ids
        if len(seen_ids) + len(new_ids) > MAX_CORRECTION_NODES:
            truncated = True
            break
        seen_ids.update(new_ids)
        if truncated:
            break
    return list(edges_by_id.values()), not truncated


def _cycle_edge_ids(edges):
    """Return active correction edges that participate in any directed cycle."""
    active = [edge for edge in edges if edge["status"] == "active"]
    adjacency = {}
    for edge in active:
        adjacency.setdefault(edge["source_id"], set()).add(edge["target_id"])

    def reaches(start, target):
        pending, visited = [start], set()
        while pending:
            node = pending.pop()
            if node == target:
                return True
            if node in visited:
                continue
            visited.add(node)
            pending.extend(adjacency.get(node, set()) - visited)
        return False

    return {
        edge["id"]
        for edge in active
        if reaches(edge["target_id"], edge["source_id"])
    }


def annotate_corrections(store, owner, records):
    """Attach correction claims without inferring truth or choosing by timestamp."""
    if not records:
        return records
    ids = {record["id"] for record in records}
    edges, graph_complete = (
        _correction_closure(store, owner, ids)
        if hasattr(store, "correction_relations")
        else (
            [
                edge
                for edge in store.relations(owner, "all")
                if edge["relation"] in CORRECTION_RELATIONS
            ],
            True,
        )
    )
    cycle_edge_ids = _cycle_edge_ids(edges)
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
            cycle = edge["id"] in cycle_edge_ids
            effective = bool(
                edge["status"] == "active"
                and trusted
                and not cycle
                and graph_complete
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
                    "cycle_check_complete": graph_complete,
                    "effective_for_exclusion": effective,
                }
            )
        effective = [claim for claim in claims if claim["effective_for_exclusion"]]
        if not graph_complete and claims:
            status = "unresolved"
        elif any(claim["cycle"] for claim in claims):
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
        record["correction_graph_complete"] = graph_complete
    return records
