from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from src.app.infra.db import models


class OntologyRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_class(self, tenant_id: str, code: str, name: str, description: str | None):
        obj = models.OntologyClass(tenant_id=tenant_id, code=code, name=name, description=description)
        self.db.add(obj)
        self.db.flush()
        return obj

    def get_class(self, tenant_id: str, class_id: int):
        stmt = select(models.OntologyClass).where(
            and_(models.OntologyClass.tenant_id == tenant_id, models.OntologyClass.id == class_id)
        )
        return self.db.scalar(stmt)

    def get_class_by_code(self, tenant_id: str, code: str):
        stmt = select(models.OntologyClass).where(
            and_(models.OntologyClass.tenant_id == tenant_id, models.OntologyClass.code == code)
        )
        return self.db.scalar(stmt)

    def list_classes(self, tenant_id: str, status: int | None = 1):
        stmt = select(models.OntologyClass).where(models.OntologyClass.tenant_id == tenant_id)
        if status is not None:
            stmt = stmt.where(models.OntologyClass.status == status)
        stmt = stmt.order_by(models.OntologyClass.id.desc())
        return list(self.db.scalars(stmt))

    def update_class(self, obj: models.OntologyClass, payload: dict):
        for key, value in payload.items():
            if value is not None:
                setattr(obj, key, value)
        self.db.flush()
        return obj

    def add_inheritance(self, tenant_id: str, parent_class_id: int, child_class_id: int):
        obj = models.OntologyInheritance(
            tenant_id=tenant_id, parent_class_id=parent_class_id, child_class_id=child_class_id
        )
        self.db.add(obj)
        self.db.flush()
        return obj

    def list_inheritance_edges(self, tenant_id: str):
        stmt = select(models.OntologyInheritance).where(models.OntologyInheritance.tenant_id == tenant_id)
        return list(self.db.scalars(stmt))

    def create_attribute(self, tenant_id: str, class_id: int | None, payload: dict):
        obj = models.OntologyDataAttribute(tenant_id=tenant_id, class_id=class_id, **payload)
        self.db.add(obj)
        self.db.flush()
        return obj

    def list_attributes_by_class_ids(self, tenant_id: str, class_ids: list[int]):
        if not class_ids:
            return []
        stmt = (
            select(models.OntologyDataAttribute)
            .join(
                models.OntologyClassDataAttrRef,
                and_(
                    models.OntologyClassDataAttrRef.tenant_id == tenant_id,
                    models.OntologyClassDataAttrRef.data_attribute_id == models.OntologyDataAttribute.id,
                ),
            )
            .where(
                and_(
                    models.OntologyDataAttribute.tenant_id == tenant_id,
                    models.OntologyClassDataAttrRef.class_id.in_(class_ids),
                )
            )
        )
        return list(self.db.scalars(stmt))

    def list_all_attributes(self, tenant_id: str):
        stmt = select(models.OntologyDataAttribute).where(models.OntologyDataAttribute.tenant_id == tenant_id)
        return list(self.db.scalars(stmt))

    def get_attribute(self, tenant_id: str, attribute_id: int):
        stmt = select(models.OntologyDataAttribute).where(
            and_(models.OntologyDataAttribute.tenant_id == tenant_id, models.OntologyDataAttribute.id == attribute_id)
        )
        return self.db.scalar(stmt)

    def bind_class_data_attribute(self, tenant_id: str, class_id: int, data_attribute_id: int):
        stmt = select(models.OntologyClassDataAttrRef).where(
            and_(
                models.OntologyClassDataAttrRef.tenant_id == tenant_id,
                models.OntologyClassDataAttrRef.class_id == class_id,
                models.OntologyClassDataAttrRef.data_attribute_id == data_attribute_id,
            )
        )
        exists = self.db.scalar(stmt)
        if exists:
            return exists
        obj = models.OntologyClassDataAttrRef(
            tenant_id=tenant_id,
            class_id=class_id,
            data_attribute_id=data_attribute_id,
        )
        self.db.add(obj)
        self.db.flush()
        return obj

    def list_class_refs_by_attribute_ids(self, tenant_id: str, attribute_ids: list[int]):
        if not attribute_ids:
            return []
        stmt = select(models.OntologyClassDataAttrRef).where(
            and_(
                models.OntologyClassDataAttrRef.tenant_id == tenant_id,
                models.OntologyClassDataAttrRef.data_attribute_id.in_(attribute_ids),
            )
        )
        return list(self.db.scalars(stmt))

    def create_relation(
        self,
        tenant_id: str,
        source_class_id: int | None,
        payload: dict,
        domain_class_ids: list[int] | None = None,
        range_class_ids: list[int] | None = None,
    ):
        obj = models.OntologyRelation(
            tenant_id=tenant_id,
            source_class_id=source_class_id,
            target_class_id=payload.get("target_class_id"),
            code=payload["code"],
            name=payload["name"],
            description=payload.get("description"),
            skill_md=payload.get("skill_md"),
            relation_type=payload["relation_type"],
            mcp_bindings_json=payload.get("mcp_bindings_json", []),
        )
        self.db.add(obj)
        self.db.flush()

        for class_id in (domain_class_ids or []):
            self.bind_relation_domain(tenant_id, obj.id, class_id)
        for class_id in (range_class_ids or []):
            self.bind_relation_range(tenant_id, obj.id, class_id)
        return obj

    def bind_relation_domain(self, tenant_id: str, relation_id: int, class_id: int):
        stmt = select(models.OntologyRelationDomainRef).where(
            and_(
                models.OntologyRelationDomainRef.tenant_id == tenant_id,
                models.OntologyRelationDomainRef.relation_id == relation_id,
                models.OntologyRelationDomainRef.class_id == class_id,
            )
        )
        exists = self.db.scalar(stmt)
        if exists:
            return exists
        obj = models.OntologyRelationDomainRef(tenant_id=tenant_id, relation_id=relation_id, class_id=class_id)
        self.db.add(obj)
        self.db.flush()
        return obj

    def bind_relation_range(self, tenant_id: str, relation_id: int, class_id: int):
        stmt = select(models.OntologyRelationRangeRef).where(
            and_(
                models.OntologyRelationRangeRef.tenant_id == tenant_id,
                models.OntologyRelationRangeRef.relation_id == relation_id,
                models.OntologyRelationRangeRef.class_id == class_id,
            )
        )
        exists = self.db.scalar(stmt)
        if exists:
            return exists
        obj = models.OntologyRelationRangeRef(tenant_id=tenant_id, relation_id=relation_id, class_id=class_id)
        self.db.add(obj)
        self.db.flush()
        return obj

    def list_relations_by_source_ids(self, tenant_id: str, source_ids: list[int]):
        if not source_ids:
            return []
        stmt = (
            select(models.OntologyRelation)
            .join(
                models.OntologyRelationDomainRef,
                and_(
                    models.OntologyRelationDomainRef.tenant_id == tenant_id,
                    models.OntologyRelationDomainRef.relation_id == models.OntologyRelation.id,
                ),
            )
            .where(
                and_(
                    models.OntologyRelation.tenant_id == tenant_id,
                    models.OntologyRelationDomainRef.class_id.in_(source_ids),
                )
            )
        )
        return list(self.db.scalars(stmt))

    def list_all_relations(self, tenant_id: str):
        stmt = select(models.OntologyRelation).where(models.OntologyRelation.tenant_id == tenant_id)
        return list(self.db.scalars(stmt))

    def list_relation_domains(self, tenant_id: str, relation_id: int):
        stmt = select(models.OntologyRelationDomainRef).where(
            and_(
                models.OntologyRelationDomainRef.tenant_id == tenant_id,
                models.OntologyRelationDomainRef.relation_id == relation_id,
            )
        )
        return list(self.db.scalars(stmt))

    def list_relation_ranges(self, tenant_id: str, relation_id: int):
        stmt = select(models.OntologyRelationRangeRef).where(
            and_(
                models.OntologyRelationRangeRef.tenant_id == tenant_id,
                models.OntologyRelationRangeRef.relation_id == relation_id,
            )
        )
        return list(self.db.scalars(stmt))

    def get_relation(self, tenant_id: str, relation_id: int):
        stmt = select(models.OntologyRelation).where(
            and_(models.OntologyRelation.tenant_id == tenant_id, models.OntologyRelation.id == relation_id)
        )
        return self.db.scalar(stmt)

    def create_capability(self, tenant_id: str, class_id: int | None, payload: dict):
        obj = models.OntologyCapability(tenant_id=tenant_id, class_id=class_id, **payload)
        self.db.add(obj)
        self.db.flush()
        if class_id is not None:
            self.bind_class_capability(tenant_id, class_id, obj.id)
        return obj

    def bind_class_capability(self, tenant_id: str, class_id: int, capability_id: int):
        stmt = select(models.OntologyClassCapabilityRef).where(
            and_(
                models.OntologyClassCapabilityRef.tenant_id == tenant_id,
                models.OntologyClassCapabilityRef.class_id == class_id,
                models.OntologyClassCapabilityRef.capability_id == capability_id,
            )
        )
        exists = self.db.scalar(stmt)
        if exists:
            return exists
        obj = models.OntologyClassCapabilityRef(
            tenant_id=tenant_id,
            class_id=class_id,
            capability_id=capability_id,
            enabled=True,
        )
        self.db.add(obj)
        self.db.flush()
        return obj

    def list_capabilities_by_class_ids(self, tenant_id: str, class_ids: list[int]):
        if not class_ids:
            return []
        stmt = (
            select(models.OntologyCapability)
            .join(
                models.OntologyClassCapabilityRef,
                and_(
                    models.OntologyClassCapabilityRef.tenant_id == tenant_id,
                    models.OntologyClassCapabilityRef.capability_id == models.OntologyCapability.id,
                    models.OntologyClassCapabilityRef.enabled.is_(True),
                ),
            )
            .where(
                and_(
                    models.OntologyCapability.tenant_id == tenant_id,
                    models.OntologyClassCapabilityRef.class_id.in_(class_ids),
                )
            )
        )
        return list(self.db.scalars(stmt))

    def list_all_capabilities(self, tenant_id: str):
        stmt = select(models.OntologyCapability).where(models.OntologyCapability.tenant_id == tenant_id)
        return list(self.db.scalars(stmt))

    def get_capability(self, tenant_id: str, capability_id: int):
        stmt = select(models.OntologyCapability).where(
            and_(models.OntologyCapability.tenant_id == tenant_id, models.OntologyCapability.id == capability_id)
        )
        return self.db.scalar(stmt)

    def upsert_class_table_binding(self, tenant_id: str, class_id: int, payload: dict):
        stmt = select(models.OntologyClassTableBinding).where(
            and_(
                models.OntologyClassTableBinding.tenant_id == tenant_id,
                models.OntologyClassTableBinding.class_id == class_id,
            )
        )
        obj = self.db.scalar(stmt)
        if obj:
            obj.table_name = payload["table_name"]
            obj.table_schema = payload.get("table_schema")
            obj.table_catalog = payload.get("table_catalog")
            obj.config_json = payload.get("config_json", {})
        else:
            obj = models.OntologyClassTableBinding(
                tenant_id=tenant_id,
                class_id=class_id,
                table_name=payload["table_name"],
                table_schema=payload.get("table_schema"),
                table_catalog=payload.get("table_catalog"),
                config_json=payload.get("config_json", {}),
            )
            self.db.add(obj)
            self.db.flush()
        self.db.flush()
        return obj

    def get_class_table_binding(self, tenant_id: str, class_id: int):
        stmt = select(models.OntologyClassTableBinding).where(
            and_(
                models.OntologyClassTableBinding.tenant_id == tenant_id,
                models.OntologyClassTableBinding.class_id == class_id,
            )
        )
        return self.db.scalar(stmt)

    def replace_field_mappings(self, tenant_id: str, binding_id: int, mappings: list[dict]):
        delete_stmt = select(models.OntologyClassFieldMapping).where(
            and_(
                models.OntologyClassFieldMapping.tenant_id == tenant_id,
                models.OntologyClassFieldMapping.binding_id == binding_id,
            )
        )
        for item in list(self.db.scalars(delete_stmt)):
            self.db.delete(item)
        self.db.flush()

        out = []
        for mapping in mappings:
            obj = models.OntologyClassFieldMapping(
                tenant_id=tenant_id,
                binding_id=binding_id,
                data_attribute_id=mapping["data_attribute_id"],
                field_name=mapping["field_name"],
            )
            self.db.add(obj)
            out.append(obj)
        self.db.flush()
        return out

    def list_field_mappings(self, tenant_id: str, binding_id: int):
        stmt = select(models.OntologyClassFieldMapping).where(
            and_(
                models.OntologyClassFieldMapping.tenant_id == tenant_id,
                models.OntologyClassFieldMapping.binding_id == binding_id,
            )
        )
        return list(self.db.scalars(stmt))

    def create_export_task(self, tenant_id: str, export_format: str, output_text: str):
        obj = models.OntologyExportTask(
            tenant_id=tenant_id,
            export_format=export_format,
            output_text=output_text,
            status="completed",
        )
        self.db.add(obj)
        self.db.flush()
        return obj

    def list_relation_domain_refs_by_class_ids(self, tenant_id: str, class_ids: list[int]):
        if not class_ids:
            return []
        stmt = select(models.OntologyRelationDomainRef).where(
            and_(
                models.OntologyRelationDomainRef.tenant_id == tenant_id,
                models.OntologyRelationDomainRef.class_id.in_(class_ids),
            )
        )
        return list(self.db.scalars(stmt))

    def list_capability_refs_by_class_ids(self, tenant_id: str, class_ids: list[int]):
        if not class_ids:
            return []
        stmt = select(models.OntologyClassCapabilityRef).where(
            and_(
                models.OntologyClassCapabilityRef.tenant_id == tenant_id,
                models.OntologyClassCapabilityRef.class_id.in_(class_ids),
                models.OntologyClassCapabilityRef.enabled.is_(True),
            )
        )
        return list(self.db.scalars(stmt))
