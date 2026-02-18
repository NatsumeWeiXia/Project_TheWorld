from src.app.domain.retrieval.query_preprocessor import preprocess_query
from src.app.domain.retrieval.scorer import cosine_similarity, hybrid_score, sparse_score
from src.app.services.embedding_service import EmbeddingService


class HybridRetrievalEngine:
    @classmethod
    def score_records(
        cls,
        query: str,
        records: list[dict],
        w_sparse: float = 0.45,
        w_dense: float = 0.55,
    ) -> list[dict]:
        normalized_query = preprocess_query(query)
        query_embedding = EmbeddingService.embed(normalized_query)

        scored = []
        for item in records:
            text = item.get("search_text") or item.get("name") or ""
            embedding = item.get("embedding") or []
            sparse = sparse_score(normalized_query, text)
            dense = cosine_similarity(query_embedding, embedding)
            score = hybrid_score(sparse, dense, w_sparse=w_sparse, w_dense=w_dense)
            scored.append({**item, "score": round(score, 6)})
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored

    @classmethod
    def score_attributes(
        cls,
        query: str,
        attributes: list[dict],
        w_sparse: float = 0.45,
        w_dense: float = 0.55,
    ) -> list[dict]:
        return cls.score_records(query, attributes, w_sparse=w_sparse, w_dense=w_dense)
