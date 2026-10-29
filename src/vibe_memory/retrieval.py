from .embeddings import cosine


def retrieve(store, embedder, owner, request):
    # The caller has already extracted these keywords. No question/content/title is embedded.
    query_vectors = embedder.keywords(request.keywords)
    candidates = store.candidates(owner, request.scope, request.tags)
    records = {}
    for keyword, parent in candidates:
        entry = records.setdefault(parent["id"], {"record": parent, "matches": {}})
        for term, vector in zip(request.keywords, query_vectors, strict=True):
            score = cosine(vector, keyword["embedding"])
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
        hits.append(
            {
                "id": record["id"],
                "kind": record["kind"],
                "title": record["title"],
                "source": record["source"],
                "keywords": record["keywords"],
                "metadata": record["metadata"],
                "matched_keywords": matches,
                "score": sum(m["similarity"] for m in matches) / len(query_vectors),
            }
        )
    hits.sort(key=lambda hit: (-hit["score"], hit["id"]))
    # Fetching source records, graph expansion, evidence selection and RAG belong to the agent.
    return {
        "mode": "keyword_vector",
        "embedding_model": embedder.model_name,
        "keywords": request.keywords,
        "hits": hits[: request.limit],
    }
