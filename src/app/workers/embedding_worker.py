from src.app.services.embedding_service import EmbeddingService


def run_embedding_task(text: str) -> list[float]:
    return EmbeddingService.embed(text)
