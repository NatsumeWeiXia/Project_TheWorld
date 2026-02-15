from sqlalchemy import and_, desc, select
from sqlalchemy.orm import Session

from src.app.infra.db import models


class KnowledgeRepository:
    def __init__(self, db: Session):
        self.db = db

    def _next_version(self, model, tenant_id: str, field_name: str, field_value: int) -> int:
        stmt = (
            select(model)
            .where(and_(model.tenant_id == tenant_id, getattr(model, field_name) == field_value))
            .order_by(desc(model.version))
        )
        latest = self.db.scalars(stmt).first()
        return (latest.version + 1) if latest else 1

    def create_class_knowledge(self, tenant_id: str, class_id: int, payload: dict):
        version = self._next_version(models.KnowledgeClass, tenant_id, "class_id", class_id)
        obj = models.KnowledgeClass(tenant_id=tenant_id, class_id=class_id, version=version, **payload)
        self.db.add(obj)
        self.db.flush()
        return obj

    def latest_class_knowledge(self, tenant_id: str, class_id: int):
        stmt = (
            select(models.KnowledgeClass)
            .where(and_(models.KnowledgeClass.tenant_id == tenant_id, models.KnowledgeClass.class_id == class_id))
            .order_by(desc(models.KnowledgeClass.version))
        )
        return self.db.scalars(stmt).first()

    def create_attribute_knowledge(self, tenant_id: str, attribute_id: int, payload: dict):
        version = self._next_version(models.KnowledgeAttribute, tenant_id, "attribute_id", attribute_id)
        obj = models.KnowledgeAttribute(tenant_id=tenant_id, attribute_id=attribute_id, version=version, **payload)
        self.db.add(obj)
        self.db.flush()
        return obj

    def latest_attribute_knowledge(self, tenant_id: str, attribute_id: int):
        stmt = (
            select(models.KnowledgeAttribute)
            .where(and_(models.KnowledgeAttribute.tenant_id == tenant_id, models.KnowledgeAttribute.attribute_id == attribute_id))
            .order_by(desc(models.KnowledgeAttribute.version))
        )
        return self.db.scalars(stmt).first()

    def create_relation_template(self, tenant_id: str, relation_id: int, payload: dict):
        version = self._next_version(models.KnowledgeRelationTemplate, tenant_id, "relation_id", relation_id)
        obj = models.KnowledgeRelationTemplate(tenant_id=tenant_id, relation_id=relation_id, version=version, **payload)
        self.db.add(obj)
        self.db.flush()
        return obj

    def latest_relation_template(self, tenant_id: str, relation_id: int):
        stmt = (
            select(models.KnowledgeRelationTemplate)
            .where(
                and_(
                    models.KnowledgeRelationTemplate.tenant_id == tenant_id,
                    models.KnowledgeRelationTemplate.relation_id == relation_id,
                )
            )
            .order_by(desc(models.KnowledgeRelationTemplate.version))
        )
        return self.db.scalars(stmt).first()

    def create_capability_template(self, tenant_id: str, capability_id: int, payload: dict):
        version = self._next_version(models.KnowledgeCapabilityTemplate, tenant_id, "capability_id", capability_id)
        obj = models.KnowledgeCapabilityTemplate(
            tenant_id=tenant_id, capability_id=capability_id, version=version, **payload
        )
        self.db.add(obj)
        self.db.flush()
        return obj

    def latest_capability_template(self, tenant_id: str, capability_id: int):
        stmt = (
            select(models.KnowledgeCapabilityTemplate)
            .where(
                and_(
                    models.KnowledgeCapabilityTemplate.tenant_id == tenant_id,
                    models.KnowledgeCapabilityTemplate.capability_id == capability_id,
                )
            )
            .order_by(desc(models.KnowledgeCapabilityTemplate.version))
        )
        return self.db.scalars(stmt).first()

    def create_fewshot(self, tenant_id: str, payload: dict):
        obj = models.KnowledgeFewshotExample(tenant_id=tenant_id, **payload)
        self.db.add(obj)
        self.db.flush()
        return obj

    def list_fewshots(self, tenant_id: str, scope_type: str, scope_id: int):
        stmt = select(models.KnowledgeFewshotExample).where(
            and_(
                models.KnowledgeFewshotExample.tenant_id == tenant_id,
                models.KnowledgeFewshotExample.scope_type == scope_type,
                models.KnowledgeFewshotExample.scope_id == scope_id,
            )
        )
        return list(self.db.scalars(stmt))
