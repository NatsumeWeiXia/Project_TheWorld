from collections import defaultdict

from sqlalchemy.orm import Session

from src.app.core.errors import AppError, ErrorCodes
from src.app.domain.retrieval.hybrid_engine import HybridRetrievalEngine
from src.app.repositories.ontology_repo import OntologyRepository


class MCPGraphService:
    def __init__(self, db: Session):
        self.repo = OntologyRepository(db)

    @staticmethod
    def _normalize_codes(codes: list[str] | None) -> set[str]:
        return {str(code).strip() for code in (codes or []) if str(code).strip()}

    @staticmethod
    def _as_non_negative_float(value, default: float) -> float:
        try:
            parsed = float(value)
            return parsed if parsed >= 0 else default
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _as_positive_int(value, default: int) -> int:
        try:
            parsed = int(value)
            return parsed if parsed > 0 else default
        except (TypeError, ValueError):
            return default

    def _class_context(self, tenant_id: str):
        classes = self.repo.list_classes(tenant_id, status=1)
        class_by_id = {item.id: item for item in classes}
        class_by_code = {item.code: item for item in classes}
        edges = self.repo.list_inheritance_edges(tenant_id)
        parent_ids_by_child_id: dict[int, list[int]] = defaultdict(list)
        child_ids_by_parent_id: dict[int, list[int]] = defaultdict(list)
        parent_codes_by_child_id: dict[int, list[str]] = defaultdict(list)
        for edge in edges:
            child = class_by_id.get(edge.child_class_id)
            parent = class_by_id.get(edge.parent_class_id)
            if not child or not parent:
                continue
            parent_ids_by_child_id[child.id].append(parent.id)
            child_ids_by_parent_id[parent.id].append(child.id)
            parent_codes_by_child_id[child.id].append(parent.code)
        parent_code_by_class_id: dict[int, str | None] = {}
        for class_id, parent_codes in parent_codes_by_child_id.items():
            parent_code_by_class_id[class_id] = sorted(set(parent_codes))[0] if parent_codes else None
        return classes, class_by_id, class_by_code, parent_code_by_class_id, parent_ids_by_child_id, child_ids_by_parent_id

    @staticmethod
    def _collect_ancestors(class_id: int, parent_ids_by_child_id: dict[int, list[int]]) -> list[int]:
        ordered: list[int] = []
        visited = set()
        stack = list(parent_ids_by_child_id.get(class_id, []))
        while stack:
            current = stack.pop(0)
            if current in visited:
                continue
            visited.add(current)
            ordered.append(current)
            stack.extend(parent_ids_by_child_id.get(current, []))
        return ordered

    @staticmethod
    def _build_data_attribute_basic(item) -> dict:
        return {
            "name": item.name,
            "code": item.code,
            "dataType": item.data_type,
            "description": item.description,
        }

    def _build_ontology_basic(self, item, parent_code_by_class_id: dict[int, str | None]) -> dict:
        return {
            "name": item.name,
            "code": item.code,
            "parentCode": parent_code_by_class_id.get(item.id),
            "description": item.description,
        }

    @staticmethod
    def _build_object_property_basic(item) -> dict:
        return {
            "name": item.name,
            "code": item.code,
            "description": item.description,
        }

    @staticmethod
    def _build_capability_basic(item) -> dict:
        return {
            "name": item.name,
            "code": item.code,
            "description": item.description,
        }

    @staticmethod
    def _to_search_text(name: str | None, code: str | None, description: str | None) -> str:
        return " ".join([name or "", code or "", description or ""]).strip()

    def list_data_attributes(
        self,
        tenant_id: str,
        query: str | None = None,
        codes: list[str] | None = None,
        top_n: int = 200,
        score_gap: float = 0.0,
        w_sparse: float = 0.45,
        w_dense: float = 0.55,
    ):
        code_filter = self._normalize_codes(codes)
        attrs = self.repo.list_all_attributes(tenant_id)
        filtered_attrs = [item for item in attrs if not code_filter or item.code in code_filter]
        output = [{**self._build_data_attribute_basic(item), "score": None} for item in filtered_attrs]
        q = (query or "").strip()
        if q:
            search_records = [
                {
                    "code": item.code,
                    "search_text": item.search_text or self._to_search_text(item.name, item.code, item.description),
                    "embedding": item.embedding or [],
                }
                for item in filtered_attrs
            ]
            trigram_sparse = HybridRetrievalEngine.build_pg_trgm_sparse_scores(self.repo.db, q, search_records)
            scored = HybridRetrievalEngine.score_records(
                q,
                search_records,
                w_sparse=w_sparse,
                w_dense=w_dense,
                sparse_overrides=trigram_sparse,
            )
            scored = HybridRetrievalEngine.apply_top_n_and_gap(scored, top_n=top_n, score_gap=score_gap)
            item_by_code = {item["code"]: item for item in output}
            ordered = []
            for row in scored:
                item = item_by_code.get(row["code"])
                if not item:
                    continue
                item["score"] = row["score"]
                ordered.append(item)
            return ordered
        output.sort(key=lambda x: (x["name"] or "", x["code"] or ""))
        return output

    def list_ontologies(
        self,
        tenant_id: str,
        query: str | None = None,
        codes: list[str] | None = None,
        top_n: int = 200,
        score_gap: float = 0.0,
        w_sparse: float = 0.45,
        w_dense: float = 0.55,
    ):
        code_filter = self._normalize_codes(codes)
        classes, _class_by_id, _class_by_code, parent_code_by_class_id, _parent_ids_by_child_id, _child_ids_by_parent_id = self._class_context(tenant_id)
        output = [
            {**self._build_ontology_basic(item, parent_code_by_class_id), "score": None}
            for item in classes
            if not code_filter or item.code in code_filter
        ]
        q = (query or "").strip()
        if q:
            search_records = [
                {
                    "code": item.code,
                    "search_text": item.search_text or self._to_search_text(item.name, item.code, item.description),
                    "embedding": item.embedding or [],
                }
                for item in classes
                if not code_filter or item.code in code_filter
            ]
            trigram_sparse = HybridRetrievalEngine.build_pg_trgm_sparse_scores(self.repo.db, q, search_records)
            scored = HybridRetrievalEngine.score_records(
                q,
                search_records,
                w_sparse=w_sparse,
                w_dense=w_dense,
                sparse_overrides=trigram_sparse,
            )
            scored = HybridRetrievalEngine.apply_top_n_and_gap(scored, top_n=top_n, score_gap=score_gap)
            item_by_code = {item["code"]: item for item in output}
            ordered = []
            for row in scored:
                item = item_by_code.get(row["code"])
                if not item:
                    continue
                item["score"] = row["score"]
                ordered.append(item)
            return ordered
        output.sort(key=lambda x: (x["name"] or "", x["code"] or ""))
        return output

    def data_attribute_related_ontologies(self, tenant_id: str, attribute_codes: list[str]):
        target_codes = self._normalize_codes(attribute_codes)
        if not target_codes:
            return []

        attrs = self.repo.list_all_attributes(tenant_id)
        attr_by_id = {item.id: item for item in attrs}
        attr_by_code = {item.code: item for item in attrs}
        target_attr_ids = [attr_by_code[code].id for code in target_codes if code in attr_by_code]
        refs = self.repo.list_class_refs_by_attribute_ids(tenant_id, target_attr_ids)

        classes, class_by_id, _class_by_code, parent_code_by_class_id, _parent_ids_by_child_id, _child_ids_by_parent_id = self._class_context(tenant_id)
        _ = classes
        class_ids = sorted({item.class_id for item in refs})
        _ = class_ids
        ontology_codes_by_attr_id: dict[int, set[int]] = defaultdict(set)
        for ref in refs:
            ontology_codes_by_attr_id[ref.data_attribute_id].add(ref.class_id)

        output = []
        for code in sorted(target_codes):
            attr = attr_by_code.get(code)
            if not attr:
                output.append({"dataAttribute": {"code": code}, "ontologies": []})
                continue
            ontologies = []
            for class_id in sorted(ontology_codes_by_attr_id.get(attr.id, set())):
                class_item = class_by_id.get(class_id)
                if not class_item:
                    continue
                ontologies.append(self._build_ontology_basic(class_item, parent_code_by_class_id))
            output.append({"dataAttribute": self._build_data_attribute_basic(attr_by_id[attr.id]), "ontologies": ontologies})
        return output

    def ontology_related_resources(self, tenant_id: str, ontology_codes: list[str]):
        target_codes = self._normalize_codes(ontology_codes)
        if not target_codes:
            return []

        classes, class_by_id, class_by_code, parent_code_by_class_id, parent_ids_by_child_id, child_ids_by_parent_id = self._class_context(tenant_id)
        _ = classes
        attrs = self.repo.list_all_attributes(tenant_id)
        attr_by_id = {item.id: item for item in attrs}
        relations = self.repo.list_all_relations(tenant_id)
        relation_by_code = {item.code: item for item in relations}
        _ = relation_by_code
        capabilities = self.repo.list_all_capabilities(tenant_id)

        output = []
        for ontology_code in sorted(target_codes):
            cls = class_by_code.get(ontology_code)
            if not cls:
                output.append(
                    {
                        "ontology": {"code": ontology_code},
                        "dataAttributes": [],
                        "objectProperties": [],
                        "capabilities": [],
                    }
                )
                continue

            ancestor_ids = self._collect_ancestors(cls.id, parent_ids_by_child_id)
            parent_scope_ids = [cls.id] + ancestor_ids
            scope_id_set = set(parent_scope_ids)

            direct_attr_refs = self.repo.list_class_data_attr_refs_by_class_ids(tenant_id, [cls.id])
            inherited_attr_refs = self.repo.list_class_data_attr_refs_by_class_ids(tenant_id, ancestor_ids)
            direct_attr_ids = {ref.data_attribute_id for ref in direct_attr_refs}
            inherited_attr_ids = {ref.data_attribute_id for ref in inherited_attr_refs}
            all_attr_ids = sorted(direct_attr_ids.union(inherited_attr_ids))
            attr_items = []
            for attr_id in all_attr_ids:
                attr = attr_by_id.get(attr_id)
                if not attr:
                    continue
                row = self._build_data_attribute_basic(attr)
                row["bindingSource"] = "self" if attr_id in direct_attr_ids else "inherited"
                attr_items.append(row)
            attr_items.sort(key=lambda x: (x["name"] or "", x["code"] or ""))

            direct_relations = self.repo.list_relations_by_source_ids(tenant_id, [cls.id])
            inherited_relations = self.repo.list_relations_by_source_ids(tenant_id, ancestor_ids)
            direct_relation_ids = {item.id for item in direct_relations}
            relation_by_id = {item.id: item for item in direct_relations}
            for item in inherited_relations:
                relation_by_id.setdefault(item.id, item)
            object_props = []
            for rel in relation_by_id.values():
                row = self._build_object_property_basic(rel)
                row["bindingSource"] = "self" if rel.id in direct_relation_ids else "inherited"
                domain_ids = {ref.class_id for ref in self.repo.list_relation_domains(tenant_id, rel.id)}
                range_ids = {ref.class_id for ref in self.repo.list_relation_ranges(tenant_id, rel.id)}
                roles = []
                if domain_ids.intersection(scope_id_set):
                    roles.append("domain")
                if range_ids.intersection(scope_id_set):
                    roles.append("range")
                row["roles"] = roles
                object_props.append(row)
            object_props = sorted(object_props, key=lambda x: (x["name"] or "", x["code"] or ""))

            direct_caps = self.repo.list_capabilities_by_class_ids(tenant_id, [cls.id])
            inherited_caps = self.repo.list_capabilities_by_class_ids(tenant_id, ancestor_ids)
            direct_cap_ids = {item.id for item in direct_caps}
            cap_by_id = {item.id: item for item in direct_caps}
            for item in inherited_caps:
                cap_by_id.setdefault(item.id, item)
            caps = []
            for cap in cap_by_id.values():
                row = self._build_capability_basic(cap)
                row["bindingSource"] = "self" if cap.id in direct_cap_ids else "inherited"
                caps.append(row)
            caps = sorted(caps, key=lambda x: (x["name"] or "", x["code"] or ""))

            output.append(
                {
                    "ontology": self._build_ontology_basic(class_by_id[cls.id], parent_code_by_class_id),
                    "parentOntologies": [
                        self._build_ontology_basic(class_by_id[parent_id], parent_code_by_class_id)
                        for parent_id in sorted(set(parent_ids_by_child_id.get(cls.id, [])))
                        if parent_id in class_by_id
                    ],
                    "childOntologies": [
                        self._build_ontology_basic(class_by_id[child_id], parent_code_by_class_id)
                        for child_id in sorted(set(child_ids_by_parent_id.get(cls.id, [])))
                        if child_id in class_by_id
                    ],
                    "dataAttributes": attr_items,
                    "objectProperties": object_props,
                    "capabilities": caps,
                }
            )
        return output

    def ontology_details(self, tenant_id: str, ontology_codes: list[str]):
        items = self.ontology_related_resources(tenant_id, ontology_codes)
        output = []
        for item in items:
            ontology = item["ontology"]
            output.append(
                {
                    "name": ontology.get("name"),
                    "code": ontology.get("code"),
                    "parentCode": ontology.get("parentCode"),
                    "description": ontology.get("description"),
                    "parentOntologies": item.get("parentOntologies", []),
                    "childOntologies": item.get("childOntologies", []),
                    "dataAttributes": item.get("dataAttributes", []),
                    "objectProperties": item.get("objectProperties", []),
                    "capabilities": item.get("capabilities", []),
                }
            )
        return output

    def data_attribute_details(self, tenant_id: str, attribute_codes: list[str]):
        return self.list_data_attributes(tenant_id, query=None, codes=attribute_codes)

    def object_property_details(self, tenant_id: str, object_property_codes: list[str]):
        target_codes = self._normalize_codes(object_property_codes)
        if not target_codes:
            return []

        _classes, class_by_id, _class_by_code, _parent_code_by_class_id, _parent_ids_by_child_id, _child_ids_by_parent_id = self._class_context(tenant_id)
        relations = self.repo.list_all_relations(tenant_id)
        output = []
        for rel in relations:
            if rel.code not in target_codes:
                continue
            domain_refs = self.repo.list_relation_domains(tenant_id, rel.id)
            range_refs = self.repo.list_relation_ranges(tenant_id, rel.id)
            domains = []
            ranges = []
            for ref in domain_refs:
                cls = class_by_id.get(ref.class_id)
                if cls:
                    domains.append({"name": cls.name, "code": cls.code})
            for ref in range_refs:
                cls = class_by_id.get(ref.class_id)
                if cls:
                    ranges.append({"name": cls.name, "code": cls.code})
            domains = sorted(domains, key=lambda x: (x["name"] or "", x["code"] or ""))
            ranges = sorted(ranges, key=lambda x: (x["name"] or "", x["code"] or ""))
            output.append(
                {
                    "name": rel.name,
                    "code": rel.code,
                    "description": rel.description,
                    "domain": domains,
                    "range": ranges,
                    "skill": rel.skill_md or "",
                }
            )
        output.sort(key=lambda x: (x["name"] or "", x["code"] or ""))
        return output

    def capability_details(self, tenant_id: str, capability_codes: list[str]):
        target_codes = self._normalize_codes(capability_codes)
        if not target_codes:
            return []

        _classes, class_by_id, _class_by_code, _parent_code_by_class_id, _parent_ids_by_child_id, _child_ids_by_parent_id = self._class_context(tenant_id)
        caps = self.repo.list_all_capabilities(tenant_id)
        output = []
        for cap in caps:
            if cap.code not in target_codes:
                continue
            domain_groups = []
            for idx, group in enumerate(cap.domain_groups_json or []):
                ontologies = []
                for class_id in group or []:
                    cls = class_by_id.get(int(class_id))
                    if cls:
                        ontologies.append({"name": cls.name, "code": cls.code})
                ontologies = sorted(ontologies, key=lambda x: (x["name"] or "", x["code"] or ""))
                domain_groups.append({"groupName": f"Group {idx + 1}", "ontologies": ontologies})
            output.append(
                {
                    "name": cap.name,
                    "code": cap.code,
                    "description": cap.description,
                    "domain": domain_groups,
                    "skill": cap.skill_md or "",
                }
            )
        output.sort(key=lambda x: (x["name"] or "", x["code"] or ""))
        return output

    @staticmethod
    def list_tools() -> list[dict]:
        return [
            {
                "name": "graph.list_data_attributes",
                "description": "Hybrid search Data Attributes by keyword + vector over name/code/description.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "codes": {"type": "array", "items": {"type": "string"}},
                        "top_n": {"type": "integer", "minimum": 1},
                        "score_gap": {"type": "number", "minimum": 0},
                        "w_sparse": {"type": "number", "minimum": 0},
                        "w_dense": {"type": "number", "minimum": 0},
                    },
                },
            },
            {
                "name": "graph.list_ontologies",
                "description": "Hybrid search Ontologies by keyword + vector over name/code/description.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "codes": {"type": "array", "items": {"type": "string"}},
                        "top_n": {"type": "integer", "minimum": 1},
                        "score_gap": {"type": "number", "minimum": 0},
                        "w_sparse": {"type": "number", "minimum": 0},
                        "w_dense": {"type": "number", "minimum": 0},
                    },
                },
            },
            {
                "name": "graph.get_data_attribute_related_ontologies",
                "description": "Query Ontologies associated with one or more Data Attributes.",
                "inputSchema": {"type": "object", "required": ["attributeCodes"], "properties": {"attributeCodes": {"type": "array", "items": {"type": "string"}}}},
            },
            {
                "name": "graph.get_ontology_related_resources",
                "description": "Query Data Attributes/Object Properties/Capabilities associated with Ontologies.",
                "inputSchema": {"type": "object", "required": ["ontologyCodes"], "properties": {"ontologyCodes": {"type": "array", "items": {"type": "string"}}}},
            },
            {
                "name": "graph.get_ontology_details",
                "description": "Query ontology details by one or more codes.",
                "inputSchema": {"type": "object", "required": ["ontologyCodes"], "properties": {"ontologyCodes": {"type": "array", "items": {"type": "string"}}}},
            },
            {
                "name": "graph.get_data_attribute_details",
                "description": "Query data attribute details by one or more codes.",
                "inputSchema": {"type": "object", "required": ["attributeCodes"], "properties": {"attributeCodes": {"type": "array", "items": {"type": "string"}}}},
            },
            {
                "name": "graph.get_object_property_details",
                "description": "Query object property details by one or more codes.",
                "inputSchema": {"type": "object", "required": ["objectPropertyCodes"], "properties": {"objectPropertyCodes": {"type": "array", "items": {"type": "string"}}}},
            },
            {
                "name": "graph.get_capability_details",
                "description": "Query capability details by one or more codes.",
                "inputSchema": {"type": "object", "required": ["capabilityCodes"], "properties": {"capabilityCodes": {"type": "array", "items": {"type": "string"}}}},
            },
        ]

    def call_tool(self, tenant_id: str, tool_name: str, arguments: dict):
        args = arguments or {}
        if tool_name == "graph.list_data_attributes":
            return self.list_data_attributes(
                tenant_id,
                query=args.get("query"),
                codes=args.get("codes"),
                top_n=self._as_positive_int(args.get("top_n"), 200),
                score_gap=self._as_non_negative_float(args.get("score_gap"), 0.0),
                w_sparse=self._as_non_negative_float(args.get("w_sparse"), 0.45),
                w_dense=self._as_non_negative_float(args.get("w_dense"), 0.55),
            )
        if tool_name == "graph.list_ontologies":
            return self.list_ontologies(
                tenant_id,
                query=args.get("query"),
                codes=args.get("codes"),
                top_n=self._as_positive_int(args.get("top_n"), 200),
                score_gap=self._as_non_negative_float(args.get("score_gap"), 0.0),
                w_sparse=self._as_non_negative_float(args.get("w_sparse"), 0.45),
                w_dense=self._as_non_negative_float(args.get("w_dense"), 0.55),
            )
        if tool_name == "graph.get_data_attribute_related_ontologies":
            return self.data_attribute_related_ontologies(tenant_id, attribute_codes=args.get("attributeCodes") or [])
        if tool_name == "graph.get_ontology_related_resources":
            return self.ontology_related_resources(tenant_id, ontology_codes=args.get("ontologyCodes") or [])
        if tool_name == "graph.get_ontology_details":
            return self.ontology_details(tenant_id, ontology_codes=args.get("ontologyCodes") or [])
        if tool_name == "graph.get_data_attribute_details":
            return self.data_attribute_details(tenant_id, attribute_codes=args.get("attributeCodes") or [])
        if tool_name == "graph.get_object_property_details":
            return self.object_property_details(tenant_id, object_property_codes=args.get("objectPropertyCodes") or [])
        if tool_name == "graph.get_capability_details":
            return self.capability_details(tenant_id, capability_codes=args.get("capabilityCodes") or [])
        raise AppError(ErrorCodes.VALIDATION, f"unknown tool name: {tool_name}")
