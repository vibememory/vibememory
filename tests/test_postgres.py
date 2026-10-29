from vibe_memory.migration import DESTINATION_TABLES, read_legacy, summary
from vibe_memory.models import SearchInput
from vibe_memory.postgres import vector_from_text, vector_literal
from vibe_memory.retrieval import retrieve


def test_vector_literal_round_trip():
    values = [0.125, -2.5, 3.0]
    assert vector_from_text(vector_literal(values)) == values


def test_empty_legacy_source_is_safe_to_inspect(tmp_path):
    assert summary(read_legacy(tmp_path)) == {table: 0 for table in DESTINATION_TABLES}


def test_postgres_store_owns_vector_search():
    class Embedder:
        model_name = "test-model"

        def keywords(self, keywords):
            assert keywords == ["tea"]
            return [[1.0, 0.0, 0.0]]

    class Store:
        def vector_search(self, owner, request, vectors, model_name):
            assert owner == "alice"
            assert request.keywords == ["tea"]
            assert vectors == [[1.0, 0.0, 0.0]]
            assert model_name == "test-model"
            return {"mode": "keyword_vector", "hits": []}

    result = retrieve(Store(), Embedder(), "alice", SearchInput(keywords=["tea"]))
    assert result == {"mode": "keyword_vector", "hits": []}
