from src.app.domain.retrieval.query_preprocessor import preprocess_query
from src.app.domain.retrieval.scorer import cosine_similarity, hybrid_score, sparse_score
from src.app.services.embedding_service import EmbeddingService


class HybridRetrievalEngine:
    @classmethod
    def score_attributes(cls, query: str, attributes: list[dict]) -> list[dict]:
        normalized_query = preprocess_query(query)
        query_embedding = EmbeddingService.embed(normalized_query)
        scored = []
        for item in attributes:
            sparse = sparse_score(normalized_query, item.get("search_text") or item.get("name") or "")
            dense = cosine_similarity(query_embedding, item.get("embedding") or [])
            score = hybrid_score(sparse, dense)
            scored.append({**item, "score": round(score, 6)})
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored
