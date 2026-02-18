from sqlalchemy import Text as SAText, bindparam, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.exc import SQLAlchemyError

from src.app.domain.retrieval.query_preprocessor import preprocess_query
from src.app.domain.retrieval.scorer import cosine_similarity, hybrid_score, sparse_score
from src.app.services.embedding_service import EmbeddingService


class HybridRetrievalEngine:
    @classmethod
    def build_pg_trgm_sparse_scores(
        cls,
        db,
        query: str,
        records: list[dict],
    ) -> list[float] | None:
        if not db or not records:
            return None
        bind = getattr(db, "bind", None)
        dialect_name = getattr(getattr(bind, "dialect", None), "name", "")
        if dialect_name != "postgresql":
            return None

        docs = [(item.get("search_text") or item.get("name") or "") for item in records]
        stmt = text(
            "SELECT similarity(:query, doc) AS sparse "
            "FROM unnest(:docs) AS t(doc)"
        ).bindparams(
            bindparam("query", type_=SAText()),
            bindparam("docs", type_=ARRAY(SAText())),
        )
        try:
            rows = db.execute(stmt, {"query": preprocess_query(query), "docs": docs}).all()
        except SQLAlchemyError:
            # Fallback when pg_trgm is unavailable or current DB user lacks permissions.
            return None
        return [max(float(row.sparse or 0.0), 0.0) for row in rows]

    @classmethod
    def apply_top_n_and_gap(
        cls,
        scored: list[dict],
        top_n: int,
        score_gap: float = 0.0,
    ) -> list[dict]:
        limit = max(1, int(top_n))
        gap = max(0.0, float(score_gap))
        if not scored:
            return []

        output: list[dict] = []
        prev_score = None
        for item in scored:
            if len(output) >= limit:
                break
            cur_score = float(item.get("score", 0.0))
            if prev_score is not None and gap > 0 and (prev_score - cur_score) >= gap:
                break
            output.append(item)
            prev_score = cur_score
        return output

    @classmethod
    def score_records(
        cls,
        query: str,
        records: list[dict],
        w_sparse: float = 0.45,
        w_dense: float = 0.55,
        sparse_overrides: list[float] | None = None,
    ) -> list[dict]:
        normalized_query = preprocess_query(query)
        query_embedding = EmbeddingService.embed(normalized_query)

        scored = []
        for idx, item in enumerate(records):
            text = item.get("search_text") or item.get("name") or ""
            embedding = item.get("embedding") or []
            sparse = (
                max(float(sparse_overrides[idx]), 0.0)
                if sparse_overrides is not None and idx < len(sparse_overrides)
                else sparse_score(normalized_query, text)
            )
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
