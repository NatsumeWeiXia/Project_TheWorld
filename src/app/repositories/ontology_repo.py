from sqlalchemy import and_, delete, or_, select
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

    def delete_class(self, tenant_id: str, class_id: int):
        # Remove inheritance edges first with direct SQL delete to guarantee FK-safe ordering.
        self.db.execute(
            delete(models.OntologyInheritance).where(
                or_(
                    models.OntologyInheritance.parent_class_id == class_id,
                    models.OntologyInheritance.child_class_id == class_id,
                )
            )
        )
        self.db.flush()

        # Remove class bindings and refs.
        class_attr_ref_stmt = select(models.OntologyClassDataAttrRef).where(
            and_(
                models.OntologyClassDataAttrRef.tenant_id == tenant_id,
                models.OntologyClassDataAttrRef.class_id == class_id,
            )
        )
        for item in list(self.db.scalars(class_attr_ref_stmt)):
            self.db.delete(item)

        relation_domain_ref_stmt = select(models.OntologyRelationDomainRef).where(
            and_(
                models.OntologyRelationDomainRef.tenant_id == tenant_id,
                models.OntologyRelationDomainRef.class_id == class_id,
            )
        )
        for item in list(self.db.scalars(relation_domain_ref_stmt)):
            self.db.delete(item)

        relation_range_ref_stmt = select(models.OntologyRelationRangeRef).where(
            and_(
                models.OntologyRelationRangeRef.tenant_id == tenant_id,
                models.OntologyRelationRangeRef.class_id == class_id,
            )
        )
        for item in list(self.db.scalars(relation_range_ref_stmt)):
            self.db.delete(item)

        class_cap_ref_stmt = select(models.OntologyClassCapabilityRef).where(
            and_(
                models.OntologyClassCapabilityRef.tenant_id == tenant_id,
                models.OntologyClassCapabilityRef.class_id == class_id,
            )
        )
        for item in list(self.db.scalars(class_cap_ref_stmt)):
            self.db.delete(item)

        # Remove class knowledge.
        knowledge_class_stmt = select(models.KnowledgeClass).where(
            and_(
                models.KnowledgeClass.tenant_id == tenant_id,
                models.KnowledgeClass.class_id == class_id,
            )
        )
        for item in list(self.db.scalars(knowledge_class_stmt)):
            self.db.delete(item)

        # Remove table bindings and dependent field mappings.
        binding_stmt = select(models.OntologyClassTableBinding).where(
            and_(
                models.OntologyClassTableBinding.tenant_id == tenant_id,
                models.OntologyClassTableBinding.class_id == class_id,
            )
        )
        bindings = list(self.db.scalars(binding_stmt))
        binding_ids = [item.id for item in bindings]
        if binding_ids:
            field_mapping_stmt = select(models.OntologyClassFieldMapping).where(
                and_(
                    models.OntologyClassFieldMapping.tenant_id == tenant_id,
                    models.OntologyClassFieldMapping.binding_id.in_(binding_ids),
                )
            )
            for item in list(self.db.scalars(field_mapping_stmt)):
                self.db.delete(item)
        for item in bindings:
            self.db.delete(item)

        # Detach legacy direct links that point to this class.
        attr_stmt = select(models.OntologyDataAttribute).where(
            and_(
                models.OntologyDataAttribute.tenant_id == tenant_id,
                models.OntologyDataAttribute.class_id == class_id,
            )
        )
        for item in list(self.db.scalars(attr_stmt)):
            item.class_id = None

        capability_stmt = select(models.OntologyCapability).where(
            and_(
                models.OntologyCapability.tenant_id == tenant_id,
                models.OntologyCapability.class_id == class_id,
            )
        )
        for item in list(self.db.scalars(capability_stmt)):
            item.class_id = None

        relation_stmt = select(models.OntologyRelation).where(
            and_(
                models.OntologyRelation.tenant_id == tenant_id,
                or_(
                    models.OntologyRelation.source_class_id == class_id,
                    models.OntologyRelation.target_class_id == class_id,
                ),
            )
        )
        for item in list(self.db.scalars(relation_stmt)):
            if item.source_class_id == class_id:
                item.source_class_id = None
            if item.target_class_id == class_id:
                item.target_class_id = None

        obj = self.get_class(tenant_id, class_id)
        if obj:
            self.db.delete(obj)
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

    def update_attribute(self, obj: models.OntologyDataAttribute, payload: dict):
        for key, value in payload.items():
            if value is not None:
                setattr(obj, key, value)
        self.db.flush()
        return obj

    def delete_data_attribute(self, tenant_id: str, attribute_id: int):
        # Remove class->attribute references
        class_attr_stmt = select(models.OntologyClassDataAttrRef).where(
            and_(
                models.OntologyClassDataAttrRef.tenant_id == tenant_id,
                models.OntologyClassDataAttrRef.data_attribute_id == attribute_id,
            )
        )
        for item in list(self.db.scalars(class_attr_stmt)):
            self.db.delete(item)

        # Remove table field mappings by attribute
        mapping_stmt = select(models.OntologyClassFieldMapping).where(
            and_(
                models.OntologyClassFieldMapping.tenant_id == tenant_id,
                models.OntologyClassFieldMapping.data_attribute_id == attribute_id,
            )
        )
        for item in list(self.db.scalars(mapping_stmt)):
            self.db.delete(item)

        # Remove attribute knowledge
        knowledge_stmt = select(models.KnowledgeAttribute).where(
            and_(
                models.KnowledgeAttribute.tenant_id == tenant_id,
                models.KnowledgeAttribute.attribute_id == attribute_id,
            )
        )
        for item in list(self.db.scalars(knowledge_stmt)):
            self.db.delete(item)

        obj = self.get_attribute(tenant_id, attribute_id)
        if obj:
            self.db.delete(obj)
        self.db.flush()
        return obj

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

    def clear_class_data_attribute_bindings(self, tenant_id: str, class_id: int):
        stmt = select(models.OntologyClassDataAttrRef).where(
            and_(
                models.OntologyClassDataAttrRef.tenant_id == tenant_id,
                models.OntologyClassDataAttrRef.class_id == class_id,
            )
        )
        for obj in list(self.db.scalars(stmt)):
            self.db.delete(obj)
        self.db.flush()

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

    def list_class_data_attr_refs_by_class_ids(self, tenant_id: str, class_ids: list[int]):
        if not class_ids:
            return []
        stmt = select(models.OntologyClassDataAttrRef).where(
            and_(
                models.OntologyClassDataAttrRef.tenant_id == tenant_id,
                models.OntologyClassDataAttrRef.class_id.in_(class_ids),
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

    def clear_relation_domains(self, tenant_id: str, relation_id: int):
        stmt = select(models.OntologyRelationDomainRef).where(
            and_(
                models.OntologyRelationDomainRef.tenant_id == tenant_id,
                models.OntologyRelationDomainRef.relation_id == relation_id,
            )
        )
        for obj in list(self.db.scalars(stmt)):
            self.db.delete(obj)
        self.db.flush()

    def clear_relation_ranges(self, tenant_id: str, relation_id: int):
        stmt = select(models.OntologyRelationRangeRef).where(
            and_(
                models.OntologyRelationRangeRef.tenant_id == tenant_id,
                models.OntologyRelationRangeRef.relation_id == relation_id,
            )
        )
        for obj in list(self.db.scalars(stmt)):
            self.db.delete(obj)
        self.db.flush()

    def get_relation(self, tenant_id: str, relation_id: int):
        stmt = select(models.OntologyRelation).where(
            and_(models.OntologyRelation.tenant_id == tenant_id, models.OntologyRelation.id == relation_id)
        )
        return self.db.scalar(stmt)

    def update_relation(self, obj: models.OntologyRelation, payload: dict):
        for key, value in payload.items():
            if value is not None:
                setattr(obj, key, value)
        self.db.flush()
        return obj

    def delete_relation(self, tenant_id: str, relation_id: int):
        domain_stmt = select(models.OntologyRelationDomainRef).where(
            and_(
                models.OntologyRelationDomainRef.tenant_id == tenant_id,
                models.OntologyRelationDomainRef.relation_id == relation_id,
            )
        )
        for item in list(self.db.scalars(domain_stmt)):
            self.db.delete(item)

        range_stmt = select(models.OntologyRelationRangeRef).where(
            and_(
                models.OntologyRelationRangeRef.tenant_id == tenant_id,
                models.OntologyRelationRangeRef.relation_id == relation_id,
            )
        )
        for item in list(self.db.scalars(range_stmt)):
            self.db.delete(item)

        knowledge_stmt = select(models.KnowledgeRelationTemplate).where(
            and_(
                models.KnowledgeRelationTemplate.tenant_id == tenant_id,
                models.KnowledgeRelationTemplate.relation_id == relation_id,
            )
        )
        for item in list(self.db.scalars(knowledge_stmt)):
            self.db.delete(item)

        obj = self.get_relation(tenant_id, relation_id)
        if obj:
            self.db.delete(obj)
        self.db.flush()
        return obj

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
        class_id_set = {int(class_id) for class_id in class_ids}

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
                    models.OntologyClassCapabilityRef.class_id.in_(class_id_set),
                )
            )
        )
        refs_caps = list(self.db.scalars(stmt))
        out_by_id = {cap.id: cap for cap in refs_caps}

        all_caps = self.list_all_capabilities(tenant_id)
        for cap in all_caps:
            groups = cap.domain_groups_json or []
            if any(class_id_set.intersection({int(class_id) for class_id in group or []}) for group in groups):
                out_by_id[cap.id] = cap
        return list(out_by_id.values())

    def list_all_capabilities(self, tenant_id: str):
        stmt = select(models.OntologyCapability).where(models.OntologyCapability.tenant_id == tenant_id)
        return list(self.db.scalars(stmt))

    def get_capability(self, tenant_id: str, capability_id: int):
        stmt = select(models.OntologyCapability).where(
            and_(models.OntologyCapability.tenant_id == tenant_id, models.OntologyCapability.id == capability_id)
        )
        return self.db.scalar(stmt)

    def update_capability(self, obj: models.OntologyCapability, payload: dict):
        for key, value in payload.items():
            if value is not None:
                setattr(obj, key, value)
        self.db.flush()
        return obj

    def delete_capability(self, tenant_id: str, capability_id: int):
        class_cap_stmt = select(models.OntologyClassCapabilityRef).where(
            and_(
                models.OntologyClassCapabilityRef.tenant_id == tenant_id,
                models.OntologyClassCapabilityRef.capability_id == capability_id,
            )
        )
        for item in list(self.db.scalars(class_cap_stmt)):
            self.db.delete(item)

        knowledge_stmt = select(models.KnowledgeCapabilityTemplate).where(
            and_(
                models.KnowledgeCapabilityTemplate.tenant_id == tenant_id,
                models.KnowledgeCapabilityTemplate.capability_id == capability_id,
            )
        )
        for item in list(self.db.scalars(knowledge_stmt)):
            self.db.delete(item)

        obj = self.get_capability(tenant_id, capability_id)
        if obj:
            self.db.delete(obj)
        self.db.flush()
        return obj

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
