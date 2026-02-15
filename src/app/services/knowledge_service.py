from sqlalchemy.orm import Session

from src.app.core.errors import AppError, ErrorCodes
from src.app.domain.retrieval.hybrid_engine import HybridRetrievalEngine
from src.app.repositories.knowledge_repo import KnowledgeRepository
from src.app.repositories.ontology_repo import OntologyRepository
from src.app.services.embedding_service import EmbeddingService


class KnowledgeService:
    def __init__(self, db: Session):
        self.db = db
        self.knowledge_repo = KnowledgeRepository(db)
        self.ontology_repo = OntologyRepository(db)

    def upsert_class_knowledge(self, tenant_id: str, class_id: int, payload: dict):
        if not self.ontology_repo.get_class(tenant_id, class_id):
            raise AppError(ErrorCodes.NOT_FOUND, "class not found")
        obj = self.knowledge_repo.create_class_knowledge(tenant_id, class_id, payload)
        self.db.commit()
        return obj

    def get_latest_class_knowledge(self, tenant_id: str, class_id: int):
        if not self.ontology_repo.get_class(tenant_id, class_id):
            raise AppError(ErrorCodes.NOT_FOUND, "class not found")
        return self.knowledge_repo.latest_class_knowledge(tenant_id, class_id)

    def upsert_attribute_knowledge(self, tenant_id: str, attribute_id: int, payload: dict):
        if not self.ontology_repo.get_attribute(tenant_id, attribute_id):
            raise AppError(ErrorCodes.NOT_FOUND, "attribute not found")
        obj = self.knowledge_repo.create_attribute_knowledge(tenant_id, attribute_id, payload)
        self.db.commit()
        return obj

    def get_latest_attribute_knowledge(self, tenant_id: str, attribute_id: int):
        if not self.ontology_repo.get_attribute(tenant_id, attribute_id):
            raise AppError(ErrorCodes.NOT_FOUND, "attribute not found")
        return self.knowledge_repo.latest_attribute_knowledge(tenant_id, attribute_id)

    def create_relation_template(self, tenant_id: str, relation_id: int, payload: dict):
        if not self.ontology_repo.get_relation(tenant_id, relation_id):
            raise AppError(ErrorCodes.NOT_FOUND, "relation not found")
        obj = self.knowledge_repo.create_relation_template(tenant_id, relation_id, payload)
        self.db.commit()
        return obj

    def get_latest_relation_template(self, tenant_id: str, relation_id: int):
        if not self.ontology_repo.get_relation(tenant_id, relation_id):
            raise AppError(ErrorCodes.NOT_FOUND, "relation not found")
        return self.knowledge_repo.latest_relation_template(tenant_id, relation_id)

    def create_capability_template(self, tenant_id: str, capability_id: int, payload: dict):
        if not self.ontology_repo.get_capability(tenant_id, capability_id):
            raise AppError(ErrorCodes.NOT_FOUND, "capability not found")
        obj = self.knowledge_repo.create_capability_template(tenant_id, capability_id, payload)
        self.db.commit()
        return obj

    def get_latest_capability_template(self, tenant_id: str, capability_id: int):
        if not self.ontology_repo.get_capability(tenant_id, capability_id):
            raise AppError(ErrorCodes.NOT_FOUND, "capability not found")
        return self.knowledge_repo.latest_capability_template(tenant_id, capability_id)

    def create_fewshot(self, tenant_id: str, payload: dict):
        payload["embedding"] = EmbeddingService.embed(payload["input_text"])
        obj = self.knowledge_repo.create_fewshot(tenant_id, payload)
        self.db.commit()
        return obj

    def search_fewshot(self, tenant_id: str, scope_type: str, scope_id: int, query: str, top_k: int):
        items = self.knowledge_repo.list_fewshots(tenant_id, scope_type, scope_id)
        data = [
            {"example_id": i.id, "input_text": i.input_text, "output_text": i.output_text, "embedding": i.embedding or []}
            for i in items
        ]
        scored = HybridRetrievalEngine.score_attributes(query, data)
        return scored[:top_k]

    def list_fewshots(self, tenant_id: str, scope_type: str, scope_id: int):
        items = self.knowledge_repo.list_fewshots(tenant_id, scope_type, scope_id)
        return [{"example_id": i.id, "input_text": i.input_text, "output_text": i.output_text, "tags_json": i.tags_json} for i in items]
