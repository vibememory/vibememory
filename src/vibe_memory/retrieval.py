from datetime import datetime

from .embeddings import cosine


def record_matches_filters(record, stored_keywords, request):
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
    return True


def retrieve(store, embedder, owner, request):
    # The caller has already extracted these keywords. No question/content/title is embedded.
    query_vectors = (
        [] if request.match_mode == "exact" else embedder.keywords(request.keywords)
    )
    if hasattr(store, "vector_search"):
        return store.vector_search(owner, request, query_vectors, embedder.model_name)
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
                "matched_keywords": matches,
                "score": score,
            }
        )
    hits.sort(key=lambda hit: (-hit["score"], hit["id"]))
    # Fetching source records, graph expansion, evidence selection and RAG belong to the agent.
    return {
        "mode": "keyword_vector",
        "match_mode": request.match_mode,
        "embedding_model": embedder.model_name,
        "keywords": request.keywords,
        "hits": hits[: request.limit],
    }
