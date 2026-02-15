from collections import defaultdict, deque

from fastapi import status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.app.core.errors import AppError, ErrorCodes
from src.app.repositories.ontology_repo import OntologyRepository
from src.app.services.embedding_service import EmbeddingService


def _is_valid_json_schema(schema: dict) -> bool:
    return isinstance(schema, dict) and isinstance(schema.get("type", "object"), str)


class OntologyService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = OntologyRepository(db)

    def create_class(self, tenant_id: str, payload: dict):
        if self.repo.get_class_by_code(tenant_id, payload["code"]):
            raise AppError(ErrorCodes.CONFLICT, "ontology class code duplicated", status.HTTP_409_CONFLICT)
        try:
            obj = self.repo.create_class(tenant_id, payload["code"], payload["name"], payload.get("description"))
            self.db.commit()
            return obj
        except IntegrityError as exc:
            self.db.rollback()
            raise AppError(ErrorCodes.CONFLICT, "create class conflict", status.HTTP_409_CONFLICT) from exc

    def list_classes(self, tenant_id: str, status_filter: int | None = 1):
        return self.repo.list_classes(tenant_id, status_filter)

    def get_class(self, tenant_id: str, class_id: int):
        obj = self.repo.get_class(tenant_id, class_id)
        if not obj:
            raise AppError(ErrorCodes.NOT_FOUND, "class not found", status.HTTP_404_NOT_FOUND)
        return obj

    def update_class(self, tenant_id: str, class_id: int, payload: dict):
        obj = self.get_class(tenant_id, class_id)
        self.repo.update_class(obj, payload)
        self.db.commit()
        return obj

    def delete_class(self, tenant_id: str, class_id: int):
        obj = self.get_class(tenant_id, class_id)
        obj.status = 0
        self.db.commit()
        return obj

    def _detect_cycle_if_add(self, tenant_id: str, parent_id: int, child_id: int) -> bool:
        edges = self.repo.list_inheritance_edges(tenant_id)
        graph = defaultdict(list)
        indeg = defaultdict(int)
        nodes = set()
        for edge in edges:
            graph[edge.parent_class_id].append(edge.child_class_id)
            indeg[edge.child_class_id] += 1
            nodes.add(edge.parent_class_id)
            nodes.add(edge.child_class_id)
        graph[parent_id].append(child_id)
        indeg[child_id] += 1
        nodes.add(parent_id)
        nodes.add(child_id)
        q = deque([node for node in nodes if indeg[node] == 0])
        visited = 0
        while q:
            node = q.popleft()
            visited += 1
            for nxt in graph[node]:
                indeg[nxt] -= 1
                if indeg[nxt] == 0:
                    q.append(nxt)
        return visited != len(nodes)

    def add_inheritance(self, tenant_id: str, child_class_id: int, parent_class_id: int):
        if child_class_id == parent_class_id:
            raise AppError(ErrorCodes.INHERITANCE_CYCLE, "parent cannot equal child")
        self.get_class(tenant_id, child_class_id)
        self.get_class(tenant_id, parent_class_id)
        if self._detect_cycle_if_add(tenant_id, parent_class_id, child_class_id):
            raise AppError(ErrorCodes.INHERITANCE_CYCLE, "inheritance cycle detected")
        obj = self.repo.add_inheritance(tenant_id, parent_class_id, child_class_id)
        self.db.commit()
        return obj

    def get_class_tree(self, tenant_id: str):
        classes = self.repo.list_classes(tenant_id, status=None)
        edges = self.repo.list_inheritance_edges(tenant_id)
        parent_by_child = {e.child_class_id: e.parent_class_id for e in edges}
        children = defaultdict(list)
        for e in edges:
            children[e.parent_class_id].append(e.child_class_id)
        by_id = {c.id: c for c in classes}
        roots = [c.id for c in classes if c.id not in parent_by_child]

        def _node(class_id: int):
            c = by_id[class_id]
            return {
                "id": c.id,
                "code": c.code,
                "name": c.name,
                "children": [_node(cid) for cid in sorted(children.get(class_id, [])) if cid in by_id],
            }

        return [_node(root_id) for root_id in sorted(roots)]

    def create_global_attribute(self, tenant_id: str, payload: dict):
        payload["search_text"] = f"{payload['name']} {payload.get('description') or ''}".strip()
        payload["embedding"] = EmbeddingService.embed(payload["search_text"])
        obj = self.repo.create_attribute(tenant_id, None, payload)
        self.db.commit()
        return obj

    def list_global_attributes(self, tenant_id: str):
        return self.repo.list_all_attributes(tenant_id)

    def bind_data_attributes(self, tenant_id: str, class_id: int, data_attribute_ids: list[int]):
        self.get_class(tenant_id, class_id)
        out = []
        for attr_id in data_attribute_ids:
            attr = self.repo.get_attribute(tenant_id, attr_id)
            if not attr:
                raise AppError(ErrorCodes.NOT_FOUND, f"attribute not found: {attr_id}", status.HTTP_404_NOT_FOUND)
            out.append(self.repo.bind_class_data_attribute(tenant_id, class_id, attr_id))
        self.db.commit()
        return out

    def create_object_property(self, tenant_id: str, payload: dict):
        domain_ids = payload["domain_class_ids"]
        range_ids = payload["range_class_ids"]
        for class_id in set(domain_ids + range_ids):
            self.get_class(tenant_id, class_id)
        obj = self.repo.create_relation(
            tenant_id=tenant_id,
            source_class_id=domain_ids[0],
            payload={
                "code": payload["code"],
                "name": payload["name"],
                "description": payload.get("description"),
                "skill_md": payload.get("skill_md"),
                "relation_type": payload["relation_type"],
                "target_class_id": range_ids[0],
                "mcp_bindings_json": payload.get("mcp_bindings_json", []),
            },
            domain_class_ids=domain_ids,
            range_class_ids=range_ids,
        )
        self.db.commit()
        return obj

    def list_object_properties(self, tenant_id: str):
        return self.repo.list_all_relations(tenant_id)

    def create_global_capability(self, tenant_id: str, payload: dict):
        if not _is_valid_json_schema(payload["input_schema"]) or not _is_valid_json_schema(payload["output_schema"]):
            raise AppError(ErrorCodes.INVALID_SCHEMA, "input_schema/output_schema invalid")
        obj = self.repo.create_capability(
            tenant_id,
            None,
            {
                "code": payload["code"],
                "name": payload["name"],
                "description": payload.get("description"),
                "skill_md": payload.get("skill_md"),
                "input_schema": payload["input_schema"],
                "output_schema": payload["output_schema"],
                "mcp_bindings_json": payload.get("mcp_bindings_json", []),
            },
        )
        self.db.commit()
        return obj

    def list_capabilities(self, tenant_id: str):
        return self.repo.list_all_capabilities(tenant_id)

    def bind_capabilities(self, tenant_id: str, class_id: int, capability_ids: list[int]):
        self.get_class(tenant_id, class_id)
        for cap_id in capability_ids:
            cap = self.repo.get_capability(tenant_id, cap_id)
            if not cap:
                raise AppError(ErrorCodes.NOT_FOUND, f"capability not found: {cap_id}", status.HTTP_404_NOT_FOUND)
            self.repo.bind_class_capability(tenant_id, class_id, cap_id)
        self.db.commit()

    def upsert_class_table_binding(self, tenant_id: str, class_id: int, payload: dict):
        self.get_class(tenant_id, class_id)
        obj = self.repo.upsert_class_table_binding(tenant_id, class_id, payload)
        self.db.commit()
        return obj

    def upsert_class_field_mapping(self, tenant_id: str, class_id: int, mappings: list[dict]):
        binding = self.repo.get_class_table_binding(tenant_id, class_id)
        if not binding:
            raise AppError(ErrorCodes.NOT_FOUND, "class table binding not found", status.HTTP_404_NOT_FOUND)
        for mapping in mappings:
            attr = self.repo.get_attribute(tenant_id, mapping["data_attribute_id"])
            if not attr:
                raise AppError(
                    ErrorCodes.NOT_FOUND,
                    f"attribute not found: {mapping['data_attribute_id']}",
                    status.HTTP_404_NOT_FOUND,
                )
        out = self.repo.replace_field_mappings(tenant_id, binding.id, mappings)
        self.db.commit()
        return out

    def owl_validate(self, tenant_id: str, strict: bool = False):
        classes = self.repo.list_classes(tenant_id, status=1)
        errors = []
        if not classes:
            errors.append("No active owl:Class found.")
        for cls in classes:
            binding = self.repo.get_class_table_binding(tenant_id, cls.id)
            if strict and not binding:
                errors.append(f"class {cls.id} missing table binding")
        return {"valid": len(errors) == 0, "errors": errors}

    def owl_export(self, tenant_id: str, export_format: str = "ttl"):
        classes = self.repo.list_classes(tenant_id, status=1)
        attrs = self.repo.list_all_attributes(tenant_id)
        relations = self.repo.list_all_relations(tenant_id)
        caps = self.repo.list_all_capabilities(tenant_id)

        lines = [
            "@prefix owl: <http://www.w3.org/2002/07/owl#> .",
            "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
            "@prefix tw: <http://theworld.local/ontology#> .",
            "",
        ]
        for c in classes:
            lines.append(f"tw:class_{c.id} a owl:Class ; rdfs:label \"{c.name}\" .")
        for a in attrs:
            lines.append(f"tw:data_attr_{a.id} a owl:DatatypeProperty ; rdfs:label \"{a.name}\" .")
        for r in relations:
            lines.append(f"tw:obj_prop_{r.id} a owl:ObjectProperty ; rdfs:label \"{r.name}\" .")
        for cap in caps:
            lines.append(f"tw:cap_{cap.id} a tw:Capability ; rdfs:label \"{cap.name}\" .")
        output_text = "\n".join(lines)
        task = self.repo.create_export_task(tenant_id, export_format, output_text)
        self.db.commit()
        return {"task_id": task.id, "format": export_format, "content": output_text}
