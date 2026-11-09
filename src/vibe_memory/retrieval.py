import json
from datetime import datetime

from .corrections import annotate_corrections
from .embeddings import cosine
from .security import record_is_retrievable
from .temporal import recorded_instant

MINIMAL_SEARCH_FIELDS = (
    "id",
    "kind",
    "title",
    "keywords",
    "trust_level",
    "security_state",
    "matched_keywords",
    "score",
    "correction_status",
    "correction_graph_complete",
)


def _wire_size(value):
    return len(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    )


def _with_response_size(value):
    value["response_bytes"] = 0
    for _ in range(8):
        size = _wire_size(value)
        if value["response_bytes"] == size:
            break
        value["response_bytes"] = size
    return value


def _project_search_hit(hit, projection):
    if projection == "standard":
        return hit
    return {key: hit.get(key) for key in MINIMAL_SEARCH_FIELDS}


def _bounded_search_response(result, request):
    candidates = [
        _project_search_hit(hit, request.projection) for hit in result.pop("hits", [])
    ]

    def response(hits):
        payload = {
            **result,
            "projection": request.projection,
            "byte_limit": request.byte_limit,
            "selected_hits": len(candidates),
            "returned": len(hits),
            "truncated": len(hits) < len(candidates),
            "hits": hits,
        }
        return _with_response_size(payload)

    hits = []
    for hit in candidates:
        candidate = response([*hits, hit])
        if candidate["response_bytes"] <= request.byte_limit:
            hits.append(hit)
        else:
            break
    payload = response(hits)
    if payload["response_bytes"] > request.byte_limit:
        raise ValueError("byte_limit is too small for the search response envelope")
    return payload


def record_matches_filters(record, stored_keywords, request):
    if not record_is_retrievable(
        record,
        include_untrusted=request.include_untrusted,
        include_quarantined=request.include_quarantined,
    ):
        return False
    folded = {keyword.casefold() for keyword in stored_keywords}
    if not {keyword.casefold() for keyword in request.must_keywords}.issubset(folded):
        return False
    if folded & {keyword.casefold() for keyword in request.exclude_keywords}:
        return False
    if any(record["metadata"].get(key) != value for key, value in request.metadata_filters.items()):
        return False
    created = datetime.fromisoformat(record["created_at"])
    if request.created_after and created < request.created_after:
        return False
    if request.created_before and created > request.created_before:
        return False
    temporal = record.get("metadata", {}).get("vibe_memory_temporal", {})
    if request.valid_at:
        valid_from = temporal.get("valid_from")
        valid_to = temporal.get("valid_to")
        if valid_from and request.valid_at < datetime.fromisoformat(valid_from):
            return False
        if valid_to and request.valid_at >= datetime.fromisoformat(valid_to):
            return False
    if request.known_at and recorded_instant(record) > request.known_at:
        return False
    return True


def _temporal_hit(hit, request):
    temporal = hit.get("metadata", {}).get("vibe_memory_temporal", {})
    if request.valid_at:
        valid_from = temporal.get("valid_from")
        valid_to = temporal.get("valid_to")
        if valid_from and request.valid_at < datetime.fromisoformat(valid_from):
            return False
        if valid_to and request.valid_at >= datetime.fromisoformat(valid_to):
            return False
    recorded = recorded_instant(hit)
    return not (request.known_at and recorded and recorded > request.known_at)


def retrieve(store, embedder, owner, request):
    # The caller has already extracted these keywords. No question/content/title is embedded.
    query_vectors = (
        [] if request.match_mode == "exact" else embedder.keywords(request.keywords)
    )
    if hasattr(store, "vector_search"):
        result = store.vector_search(owner, request, query_vectors, embedder.model_name)
        result["hits"] = [hit for hit in result["hits"] if _temporal_hit(hit, request)]
        annotate_corrections(store, owner, result["hits"])
        if request.exclude_resolved_superseded:
            result["hits"] = [
                hit for hit in result["hits"] if hit["correction_status"] != "superseded"
            ]
        if request.valid_at or request.known_at:
            result["temporal"] = {
                "valid_at": request.valid_at.isoformat() if request.valid_at else None,
                "known_at": request.known_at.isoformat() if request.known_at else None,
                "completeness": "current_versions_only",
            }
        return _bounded_search_response(result, request)
    candidates = store.candidates(owner, request.scope, request.tags)
    records = {}
    for keyword, parent in candidates:
        entry = records.setdefault(
            parent["id"], {"record": parent, "matches": {}, "stored_keywords": set()}
        )
        entry["stored_keywords"].add(keyword["content"])
        for index, term in enumerate(request.keywords):
            exact = keyword["content"].casefold() == term.casefold()
            if request.match_mode == "exact" and not exact:
                continue
            semantic = 0.0 if request.match_mode == "exact" else cosine(
                query_vectors[index], keyword["embedding"]
            )
            score = 1.0 if exact and request.match_mode in {"exact", "hybrid"} else semantic
            best = entry["matches"].get(term)
            if best is None or score > best["similarity"]:
                entry["matches"][term] = {
                    "query_keyword": term,
                    "stored_keyword": keyword["content"],
                    "similarity": score,
                }
    hits = []
    for entry in records.values():
        record = entry["record"]
        matches = list(entry["matches"].values())
        if not matches or not record_matches_filters(
            record, entry["stored_keywords"], request
        ):
            continue
        score = sum(match["similarity"] for match in matches) / len(request.keywords)
        if score < request.min_score:
            continue
        hits.append(
            {
                "id": record["id"],
                "kind": record["kind"],
                "title": record["title"],
                "source": record["source"],
                "keywords": record["keywords"],
                "metadata": record["metadata"],
                "trust_level": record["trust_level"],
                "security_state": record["security_state"],
                "security_warnings": record["security_warnings"],
                "provenance": record["provenance"],
                "matched_keywords": matches,
                "score": score,
            }
        )
    hits.sort(key=lambda hit: (-hit["score"], hit["id"]))
    annotate_corrections(store, owner, hits)
    if request.exclude_resolved_superseded:
        hits = [hit for hit in hits if hit["correction_status"] != "superseded"]
    # Fetching source records, graph expansion, evidence selection and RAG belong to the agent.
    result = {
        "mode": "keyword_vector",
        "match_mode": request.match_mode,
        "embedding_model": embedder.model_name,
        "keywords": request.keywords,
        "hits": hits[: request.limit],
    }
    if request.valid_at or request.known_at:
        result["temporal"] = {
            "valid_at": request.valid_at.isoformat() if request.valid_at else None,
            "known_at": request.known_at.isoformat() if request.known_at else None,
            "completeness": "current_versions_only",
        }
    return _bounded_search_response(result, request)
