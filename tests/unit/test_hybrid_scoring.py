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
