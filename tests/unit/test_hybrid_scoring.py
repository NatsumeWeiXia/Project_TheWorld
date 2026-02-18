from src.app.domain.retrieval.hybrid_engine import HybridRetrievalEngine
from src.app.services.embedding_service import EmbeddingService


def test_hybrid_scoring_order():
    query = "id card customer"
    data = [
        {
            "attribute_id": 1,
            "name": "customer id card",
            "search_text": "customer id card",
            "embedding": EmbeddingService.embed("customer id card"),
        },
        {
            "attribute_id": 2,
            "name": "address",
            "search_text": "address",
            "embedding": EmbeddingService.embed("address"),
        },
    ]
    result = HybridRetrievalEngine.score_attributes(query, data)
    assert result[0]["attribute_id"] == 1


def test_hybrid_scoring_weights_affect_ranking():
    query = "apple"
    data = [
        {
            "attribute_id": 1,
            "name": "apple exact",
            "search_text": "apple",
            "embedding": EmbeddingService.embed("totally unrelated token"),
        },
        {
            "attribute_id": 2,
            "name": "semantic apple",
            "search_text": "banana",
            "embedding": EmbeddingService.embed("apple"),
        },
    ]

    sparse_first = HybridRetrievalEngine.score_attributes(query, data, w_sparse=0.95, w_dense=0.05)
    dense_first = HybridRetrievalEngine.score_attributes(query, data, w_sparse=0.05, w_dense=0.95)

    assert sparse_first[0]["attribute_id"] == 1
    assert dense_first[0]["attribute_id"] == 2


def test_apply_top_n_and_gap_stops_on_score_drop():
    scored = [
        {"id": 1, "score": 0.93},
        {"id": 2, "score": 0.91},
        {"id": 3, "score": 0.52},
        {"id": 4, "score": 0.51},
    ]
    result = HybridRetrievalEngine.apply_top_n_and_gap(scored, top_n=10, score_gap=0.2)
    assert [item["id"] for item in result] == [1, 2]


def test_apply_top_n_and_gap_respects_top_n_limit():
    scored = [
        {"id": 1, "score": 0.93},
        {"id": 2, "score": 0.91},
        {"id": 3, "score": 0.89},
    ]
    result = HybridRetrievalEngine.apply_top_n_and_gap(scored, top_n=2, score_gap=1.0)
    assert [item["id"] for item in result] == [1, 2]


def test_sparse_overrides_take_effect():
    query = "identity"
    data = [
        {"attribute_id": 1, "search_text": "foo", "embedding": EmbeddingService.embed("foo")},
        {"attribute_id": 2, "search_text": "bar", "embedding": EmbeddingService.embed("bar")},
    ]
    result = HybridRetrievalEngine.score_records(query, data, w_sparse=1.0, w_dense=0.0, sparse_overrides=[0.1, 0.9])
    assert result[0]["attribute_id"] == 2
