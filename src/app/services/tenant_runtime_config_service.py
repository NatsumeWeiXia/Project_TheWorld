from __future__ import annotations

from src.app.repositories.config_repo import TenantRuntimeConfigRepository


class TenantRuntimeConfigService:
    def __init__(self, db):
        self.db = db
        self.repo = TenantRuntimeConfigRepository(db)

    @staticmethod
    def default_search_config() -> dict:
        return {
            "word_w_sparse": 0.45,
            "word_w_dense": 0.55,
            "sentence_w_sparse": 0.25,
            "sentence_w_dense": 0.75,
            "top_n": 200,
            "score_gap": 0.0,
            "relative_diff": 0.0,
            "backfill_batch_size": 200,
        }

    def get_search_config(self, tenant_id: str) -> dict:
        obj = self.repo.get(tenant_id)
        defaults = self.default_search_config()
        if not obj:
            return defaults
        payload = obj.config_json or {}
        search = payload.get("search_config") or {}
        out = {**defaults, **search}
        return out

    def upsert_search_config(self, tenant_id: str, payload: dict) -> dict:
        existing = self.repo.get(tenant_id)
        # Use a fresh dict to avoid in-place JSON mutation being ignored by ORM change tracking.
        config_json = dict((existing.config_json if existing else {}) or {})
        defaults = self.default_search_config()
        merged = {**defaults, **(config_json.get("search_config") or {}), **(payload or {})}

        merged["word_w_sparse"] = float(max(0.0, merged["word_w_sparse"]))
        merged["word_w_dense"] = float(max(0.0, merged["word_w_dense"]))
        merged["sentence_w_sparse"] = float(max(0.0, merged["sentence_w_sparse"]))
        merged["sentence_w_dense"] = float(max(0.0, merged["sentence_w_dense"]))
        merged["top_n"] = int(max(1, min(500, int(merged["top_n"]))))
        merged["score_gap"] = float(max(0.0, merged["score_gap"]))
        merged["relative_diff"] = float(max(0.0, merged["relative_diff"]))
        merged["backfill_batch_size"] = int(max(1, min(5000, int(merged["backfill_batch_size"]))))

        config_json["search_config"] = dict(merged)
        self.repo.upsert(tenant_id, config_json)
        self.db.commit()
        return merged
