import hashlib
import math

import httpx

from src.app.core.config import settings


class EmbeddingService:
    @classmethod
    def _fallback_embed(cls, text: str) -> list[float]:
        dim = max(int(settings.embedding_fallback_dim or 16), 4)
        seed = hashlib.sha256((text or "").encode("utf-8")).digest()
        values = [seed[i % len(seed)] / 255.0 for i in range(dim)]
        norm = math.sqrt(sum(v * v for v in values)) or 1.0
        return [v / norm for v in values]

    @classmethod
    def embed_batch(cls, texts: list[str]) -> list[list[float]]:
        normalized = [(text or "").strip() for text in (texts or [])]
        if not normalized:
            return []

        endpoint = (settings.embedding_service_url or "").rstrip("/")
        if not endpoint:
            return [cls._fallback_embed(text) for text in normalized]

        try:
            with httpx.Client(timeout=settings.embedding_timeout_seconds) as client:
                resp = client.post(f"{endpoint}/embed", json={"texts": normalized})
                resp.raise_for_status()
                payload = resp.json()
            embeddings = payload.get("embeddings") or []
            if not isinstance(embeddings, list) or len(embeddings) != len(normalized):
                raise ValueError("invalid embeddings response length")
            return [[float(v) for v in (item or [])] for item in embeddings]
        except Exception:
            return [cls._fallback_embed(text) for text in normalized]

    @classmethod
    def embed(cls, text: str) -> list[float]:
        vectors = cls.embed_batch([text])
        return vectors[0] if vectors else cls._fallback_embed(text or "")
