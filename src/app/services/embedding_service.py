import hashlib
import math


class EmbeddingService:
    dim = 16

    @classmethod
    def embed(cls, text: str) -> list[float]:
        seed = hashlib.sha256(text.encode("utf-8")).digest()
        values = [seed[i] / 255.0 for i in range(cls.dim)]
        norm = math.sqrt(sum(v * v for v in values)) or 1.0
        return [v / norm for v in values]
