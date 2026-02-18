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
