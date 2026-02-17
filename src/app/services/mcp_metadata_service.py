from collections import defaultdict

from sqlalchemy.orm import Session

from src.app.core.errors import AppError, ErrorCodes
from src.app.domain.retrieval.hybrid_engine import HybridRetrievalEngine
from src.app.repositories.knowledge_repo import KnowledgeRepository
from src.app.repositories.ontology_repo import OntologyRepository


class MCPMetadataService:
    def __init__(self, db: Session):
        self.db = db
        self.ontology_repo = OntologyRepository(db)
        self.knowledge_repo = KnowledgeRepository(db)

    def match_attributes(self, tenant_id: str, query: str, top_k: int, page: int, page_size: int):
        attrs = self.ontology_repo.list_all_attributes(tenant_id)
        attr_records = [
            {
                "attribute_id": item.id,
                "name": item.name,
                "search_text": item.search_text or item.name,
                "embedding": item.embedding or [],
            }
            for item in attrs
        ]
        scored = HybridRetrievalEngine.score_attributes(query, attr_records)
        attr_ids = [item["attribute_id"] for item in scored[:top_k]]
        refs = self.ontology_repo.list_class_refs_by_attribute_ids(tenant_id, attr_ids)
        class_ref_map = defaultdict(list)
        for ref in refs:
            class_ref_map[ref.data_attribute_id].append(ref.class_id)

        start = (page - 1) * page_size
        end = start + page_size
        output = []
        for item in scored[:top_k][start:end]:
            k = self.knowledge_repo.latest_attribute_knowledge(tenant_id, item["attribute_id"])
            output.append(
                {
                    "attribute_id": item["attribute_id"],
                    "name": item["name"],
                    "score": item["score"],
                    "class_refs": sorted(class_ref_map.get(item["attribute_id"], [])),
                    "knowledge_summary": (k.definition if k else ""),
                }
            )
        return {"items": output, "page": page, "page_size": page_size}

    def ontologies_by_attributes(self, tenant_id: str, attribute_ids: list[int], top_k: int):
        refs = self.ontology_repo.list_class_refs_by_attribute_ids(tenant_id, attribute_ids)
        counters = defaultdict(list)
        for ref in refs:
            counters[ref.class_id].append(ref.data_attribute_id)
        scored = []
        total = max(len(attribute_ids), 1)
        for class_id, matched in counters.items():
            cls = self.ontology_repo.get_class(tenant_id, class_id)
            if not cls:
                continue
            knowledge = self.knowledge_repo.latest_class_knowledge(tenant_id, class_id)
            scored.append(
                {
                    "class_id": class_id,
                    "name": cls.name,
                    "match_strength": round(len(set(matched)) / total, 6),
                    "matched_attributes": sorted(set(matched)),
                    "knowledge_summary": knowledge.overview if knowledge else "",
                }
            )
        scored.sort(key=lambda x: x["match_strength"], reverse=True)
        return {"items": scored[:top_k]}

    def _inherited_chain(self, tenant_id: str, class_id: int) -> list[int]:
        edges = self.ontology_repo.list_inheritance_edges(tenant_id)
        parent_by_child = {e.child_class_id: e.parent_class_id for e in edges}
        chain = [class_id]
        cur = class_id
        visited = {cur}
        while cur in parent_by_child:
            nxt = parent_by_child[cur]
            if nxt in visited:
                break
            chain.append(nxt)
            visited.add(nxt)
            cur = nxt
        return chain

    def ontology_detail(self, tenant_id: str, class_id: int):
        cls = self.ontology_repo.get_class(tenant_id, class_id)
        if not cls:
            raise AppError(ErrorCodes.NOT_FOUND, "class not found")
        chain = self._inherited_chain(tenant_id, class_id)
        attrs = self.ontology_repo.list_attributes_by_class_ids(tenant_id, chain)
        relations = self.ontology_repo.list_relations_by_source_ids(tenant_id, chain)
        capabilities = self.ontology_repo.list_capabilities_by_class_ids(tenant_id, chain)
        direct_attr_ids = {
            ref.data_attribute_id
            for ref in self.ontology_repo.list_class_refs_by_attribute_ids(tenant_id, [a.id for a in attrs])
            if ref.class_id == class_id
        }
        direct_relation_ids = {
            ref.relation_id
            for ref in self.ontology_repo.list_relation_domain_refs_by_class_ids(tenant_id, [class_id])
        }
        direct_capability_ids = {
            ref.capability_id
            for ref in self.ontology_repo.list_capability_refs_by_class_ids(tenant_id, [class_id])
        }
        for cap in capabilities:
            groups = cap.domain_groups_json or []
            if any(class_id in {int(class_item_id) for class_item_id in (group or [])} for group in groups):
                direct_capability_ids.add(cap.id)
        table_binding = self.ontology_repo.get_class_table_binding(tenant_id, class_id)
        field_mappings = (
            self.ontology_repo.list_field_mappings(tenant_id, table_binding.id) if table_binding else []
        )
        class_knowledge = self.knowledge_repo.latest_class_knowledge(tenant_id, class_id)
        return {
            "class": {"id": cls.id, "name": cls.name, "knowledge_summary": class_knowledge.overview if class_knowledge else ""},
            "attributes": [{"id": a.id, "name": a.name, "inherited": a.id not in direct_attr_ids} for a in attrs],
            "relations": [{"id": r.id, "name": r.name, "inherited": r.id not in direct_relation_ids} for r in relations],
            "capabilities": [{"id": c.id, "name": c.name, "inherited": c.id not in direct_capability_ids} for c in capabilities],
            "table_binding": (
                {
                    "id": table_binding.id,
                    "table_name": table_binding.table_name,
                    "table_schema": table_binding.table_schema,
                    "table_catalog": table_binding.table_catalog,
                    "config_json": table_binding.config_json,
                }
                if table_binding
                else None
            ),
            "field_mappings": [
                {"data_attribute_id": m.data_attribute_id, "field_name": m.field_name} for m in field_mappings
            ],
        }

    def execution_detail(self, tenant_id: str, resource_type: str, resource_id: int):
        if resource_type == "relation":
            relation = self.ontology_repo.get_relation(tenant_id, resource_id)
            if not relation:
                raise AppError(ErrorCodes.NOT_FOUND, "relation not found")
            template = self.knowledge_repo.latest_relation_template(tenant_id, relation.id)
            return {
                "id": relation.id,
                "type": "relation",
                "execution_desc": relation.description or relation.name,
                "prompt_template": template.prompt_template if template else "",
                "mcp_bindings": relation.mcp_bindings_json,
                "intent_desc": template.intent_desc if template else "",
                "few_shot_examples": template.few_shot_examples if template else [],
                "json_schema": template.json_schema if template else {},
                "skill_md": template.skill_md if template else (relation.skill_md or ""),
                "input_schema": {},
                "output_schema": {},
            }
        if resource_type == "capability":
            cap = self.ontology_repo.get_capability(tenant_id, resource_id)
            if not cap:
                raise AppError(ErrorCodes.NOT_FOUND, "capability not found")
            template = self.knowledge_repo.latest_capability_template(tenant_id, cap.id)
            return {
                "id": cap.id,
                "type": "capability",
                "execution_desc": cap.description or cap.name,
                "prompt_template": template.prompt_template if template else "",
                "mcp_bindings": cap.mcp_bindings_json,
                "intent_desc": template.intent_desc if template else "",
                "few_shot_examples": template.few_shot_examples if template else [],
                "json_schema": template.json_schema if template else {},
                "skill_md": template.skill_md if template else (cap.skill_md or ""),
                "input_schema": cap.input_schema,
                "output_schema": cap.output_schema,
            }
        raise AppError(ErrorCodes.VALIDATION, "type must be relation/capability")
