from collections import defaultdict, deque
import json
import re

from fastapi import status
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.app.core.config import settings
from src.app.core.errors import AppError, ErrorCodes
from src.app.repositories.ontology_repo import OntologyRepository
from src.app.services.embedding_service import EmbeddingService


def _is_valid_json_schema(schema: dict) -> bool:
    return isinstance(schema, dict) and isinstance(schema.get("type", "object"), str)


def _normalize_domain_groups(domain_groups: list[list[int]] | None) -> list[list[int]]:
    if domain_groups is None:
        return []
    normalized: list[list[int]] = []
    seen = set()
    for group in domain_groups:
        group_ids = sorted({int(class_id) for class_id in (group or [])})
        if not group_ids:
            continue
        key = tuple(group_ids)
        if key in seen:
            continue
        seen.add(key)
        normalized.append(group_ids)
    return normalized


def _sanitize_identifier(value: str, default_prefix: str = "col") -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_]+", "_", (value or "").strip().lower()).strip("_")
    if not cleaned:
        cleaned = default_prefix
    if cleaned[0].isdigit():
        cleaned = f"{default_prefix}_{cleaned}"
    return cleaned


def _column_type_for_data_type(data_type: str, dialect_name: str) -> str:
    if data_type == "string":
        return "TEXT"
    if data_type == "int":
        return "BIGINT"
    if data_type == "date":
        return "DATE"
    if data_type == "boolean":
        return "BOOLEAN"
    if data_type in {"json", "array"}:
        return "JSONB" if dialect_name == "postgresql" else "TEXT"
    return "TEXT"


def _quote_identifier(name: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name or ""):
        raise AppError(ErrorCodes.VALIDATION, f"invalid identifier: {name}")
    return f'"{name}"'


def _parse_data_value(value, data_type: str):
    if value is None:
        return None
    if data_type == "int":
        return int(value)
    if data_type == "boolean":
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            low = value.strip().lower()
            if low in {"1", "true", "yes", "y"}:
                return True
            if low in {"0", "false", "no", "n"}:
                return False
        raise AppError(ErrorCodes.VALIDATION, f"invalid boolean value: {value}")
    if data_type in {"json", "array"}:
        if isinstance(value, str):
            parsed = json.loads(value)
        else:
            parsed = value
        return parsed
    return value


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
        if not obj or obj.status != 1:
            raise AppError(ErrorCodes.NOT_FOUND, "class not found", status.HTTP_404_NOT_FOUND)
        return obj

    def get_ancestor_ids(self, tenant_id: str, class_id: int) -> list[int]:
        edges = self.repo.list_inheritance_edges(tenant_id)
        parent_map = defaultdict(list)
        for e in edges:
            parent_map[e.child_class_id].append(e.parent_class_id)
        
        ancestors = set()
        queue = deque([class_id])
        while queue:
            curr = queue.popleft()
            for p_id in parent_map.get(curr, []):
                if p_id not in ancestors:
                    ancestors.add(p_id)
                    queue.append(p_id)
        return sorted(list(ancestors))

    def get_class_detail(self, tenant_id: str, class_id: int):
        obj = self.get_class(tenant_id, class_id)
        ancestor_ids = self.get_ancestor_ids(tenant_id, class_id)
        all_ids = [class_id] + ancestor_ids

        # Get direct attributes
        direct_refs = self.repo.list_class_data_attr_refs_by_class_ids(tenant_id, [class_id])
        direct_attrs = sorted(list(set(r.data_attribute_id for r in direct_refs)))

        # Get inherited attributes
        inherited_attrs = []
        if ancestor_ids:
            inherited_refs = self.repo.list_class_data_attr_refs_by_class_ids(tenant_id, ancestor_ids)
            inherited_attrs = sorted(list(set(r.data_attribute_id for r in inherited_refs)))

        # Get bound capabilities (including inherited and domain groups)
        cap_refs = self.repo.list_capability_refs_by_class_ids(tenant_id, all_ids)
        ref_caps = {r.capability_id for r in cap_refs}
        chain_set = set(all_ids)
        domain_caps = {
            cap.id
            for cap in self.repo.list_all_capabilities(tenant_id)
            if any(chain_set.issuperset({int(class_id) for class_id in group or []}) for group in (cap.domain_groups_json or []))
        }
        bound_caps = sorted(list(ref_caps.union(domain_caps)))

        # Get table binding for current class
        binding = self.repo.get_class_table_binding(tenant_id, class_id)
        binding_data = None
        if binding:
            mappings = self.repo.list_field_mappings(tenant_id, binding.id)
            binding_data = {
                "table_name": binding.table_name,
                "table_schema": binding.table_schema,
                "mappings": [{"data_attribute_id": m.data_attribute_id, "field_name": m.field_name} for m in mappings],
            }

        return {
            "id": obj.id,
            "code": obj.code,
            "name": obj.name,
            "description": obj.description,
            "status": obj.status,
            "direct_attrs": direct_attrs,
            "inherited_attrs": inherited_attrs,
            "bound_attrs": sorted(list(set(direct_attrs + inherited_attrs))),
            "bound_caps": bound_caps,
            "table_binding": binding_data,
            "ancestor_ids": ancestor_ids,
        }

    def update_class(self, tenant_id: str, class_id: int, payload: dict):
        obj = self.get_class(tenant_id, class_id)
        self.repo.update_class(obj, payload)
        self.db.commit()
        return obj

    def delete_class(self, tenant_id: str, class_id: int):
        self.get_class(tenant_id, class_id)
        obj = self.repo.delete_class(tenant_id, class_id)
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
        classes = self.repo.list_classes(tenant_id, status=1)
        edges = self.repo.list_inheritance_edges(tenant_id)
        active_ids = {c.id for c in classes}
        parent_by_child = {e.child_class_id: e.parent_class_id for e in edges}
        children = defaultdict(list)
        for e in edges:
            if e.parent_class_id not in active_ids or e.child_class_id not in active_ids:
                continue
            children[e.parent_class_id].append(e.child_class_id)
        by_id = {c.id: c for c in classes}
        roots = [c.id for c in classes if parent_by_child.get(c.id) not in active_ids]

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

    def delete_global_attribute(self, tenant_id: str, attribute_id: int):
        obj = self.repo.get_attribute(tenant_id, attribute_id)
        if not obj:
            raise AppError(ErrorCodes.NOT_FOUND, "attribute not found", status.HTTP_404_NOT_FOUND)
        self.repo.delete_data_attribute(tenant_id, attribute_id)
        self.db.commit()
        return obj

    def get_global_attribute(self, tenant_id: str, attribute_id: int):
        obj = self.repo.get_attribute(tenant_id, attribute_id)
        if not obj:
            raise AppError(ErrorCodes.NOT_FOUND, "attribute not found", status.HTTP_404_NOT_FOUND)
        return obj

    def update_global_attribute(self, tenant_id: str, attribute_id: int, payload: dict):
        obj = self.get_global_attribute(tenant_id, attribute_id)
        update_payload = dict(payload)
        if "name" in update_payload or "description" in update_payload:
            new_name = update_payload.get("name") if update_payload.get("name") is not None else obj.name
            new_desc = update_payload.get("description") if update_payload.get("description") is not None else obj.description
            update_payload["search_text"] = f"{new_name} {new_desc or ''}".strip()
            update_payload["embedding"] = EmbeddingService.embed(update_payload["search_text"])
        self.repo.update_attribute(obj, update_payload)
        self.db.commit()
        return obj

    def bind_data_attributes(self, tenant_id: str, class_id: int, data_attribute_ids: list[int]):
        self.get_class(tenant_id, class_id)
        normalized_ids = sorted(list({int(attr_id) for attr_id in data_attribute_ids}))
        # Clear existing bindings for THIS class
        self.repo.clear_class_data_attribute_bindings(tenant_id, class_id)
        out = []
        for attr_id in normalized_ids:
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
                "relation_type": "query",
                "target_class_id": range_ids[0],
                "mcp_bindings_json": [],
            },
            domain_class_ids=domain_ids,
            range_class_ids=range_ids,
        )
        self.db.commit()
        return obj

    def list_object_properties(self, tenant_id: str):
        return self.repo.list_all_relations(tenant_id)

    def delete_object_property(self, tenant_id: str, relation_id: int):
        obj = self.repo.get_relation(tenant_id, relation_id)
        if not obj:
            raise AppError(ErrorCodes.NOT_FOUND, "object property not found", status.HTTP_404_NOT_FOUND)
        self.repo.delete_relation(tenant_id, relation_id)
        self.db.commit()
        return obj

    def get_object_property_detail(self, tenant_id: str, relation_id: int):
        obj = self.repo.get_relation(tenant_id, relation_id)
        if not obj:
            raise AppError(ErrorCodes.NOT_FOUND, "object property not found", status.HTTP_404_NOT_FOUND)
        domain_refs = self.repo.list_relation_domains(tenant_id, relation_id)
        range_refs = self.repo.list_relation_ranges(tenant_id, relation_id)
        return {
            "id": obj.id,
            "code": obj.code,
            "name": obj.name,
            "description": obj.description,
            "skill_md": obj.skill_md,
            "domain_class_ids": sorted(list({ref.class_id for ref in domain_refs})),
            "range_class_ids": sorted(list({ref.class_id for ref in range_refs})),
        }

    def update_object_property(self, tenant_id: str, relation_id: int, payload: dict):
        obj = self.repo.get_relation(tenant_id, relation_id)
        if not obj:
            raise AppError(ErrorCodes.NOT_FOUND, "object property not found", status.HTTP_404_NOT_FOUND)

        domain_ids = payload.get("domain_class_ids")
        range_ids = payload.get("range_class_ids")

        if domain_ids is not None:
            domain_ids = sorted(list({int(class_id) for class_id in domain_ids}))
            for class_id in domain_ids:
                self.get_class(tenant_id, class_id)
        if range_ids is not None:
            range_ids = sorted(list({int(class_id) for class_id in range_ids}))
            for class_id in range_ids:
                self.get_class(tenant_id, class_id)

        update_payload = dict(payload)
        if domain_ids:
            update_payload["source_class_id"] = domain_ids[0]
        if range_ids:
            update_payload["target_class_id"] = range_ids[0]
        update_payload.pop("domain_class_ids", None)
        update_payload.pop("range_class_ids", None)

        self.repo.update_relation(obj, update_payload)

        if domain_ids is not None:
            self.repo.clear_relation_domains(tenant_id, relation_id)
            for class_id in domain_ids:
                self.repo.bind_relation_domain(tenant_id, relation_id, class_id)
        if range_ids is not None:
            self.repo.clear_relation_ranges(tenant_id, relation_id)
            for class_id in range_ids:
                self.repo.bind_relation_range(tenant_id, relation_id, class_id)

        self.db.commit()
        return obj

    def create_global_capability(self, tenant_id: str, payload: dict):
        if not _is_valid_json_schema(payload["input_schema"]) or not _is_valid_json_schema(payload["output_schema"]):
            raise AppError(ErrorCodes.INVALID_SCHEMA, "input_schema/output_schema invalid")
        normalized_groups = _normalize_domain_groups(payload.get("domain_groups"))
        for group in normalized_groups:
            for class_id in group:
                self.get_class(tenant_id, class_id)
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
                "mcp_bindings_json": [],
                "domain_groups_json": normalized_groups,
            },
        )
        self.db.commit()
        return obj

    def list_capabilities(self, tenant_id: str):
        return self.repo.list_all_capabilities(tenant_id)

    def delete_global_capability(self, tenant_id: str, capability_id: int):
        obj = self.repo.get_capability(tenant_id, capability_id)
        if not obj:
            raise AppError(ErrorCodes.NOT_FOUND, "capability not found", status.HTTP_404_NOT_FOUND)
        self.repo.delete_capability(tenant_id, capability_id)
        self.db.commit()
        return obj

    def get_global_capability(self, tenant_id: str, capability_id: int):
        obj = self.repo.get_capability(tenant_id, capability_id)
        if not obj:
            raise AppError(ErrorCodes.NOT_FOUND, "capability not found", status.HTTP_404_NOT_FOUND)
        return obj

    def update_global_capability(self, tenant_id: str, capability_id: int, payload: dict):
        obj = self.get_global_capability(tenant_id, capability_id)
        if "input_schema" in payload and payload["input_schema"] is not None and not _is_valid_json_schema(payload["input_schema"]):
            raise AppError(ErrorCodes.INVALID_SCHEMA, "input_schema invalid")
        if "output_schema" in payload and payload["output_schema"] is not None and not _is_valid_json_schema(payload["output_schema"]):
            raise AppError(ErrorCodes.INVALID_SCHEMA, "output_schema invalid")
        update_payload = dict(payload)
        if "domain_groups" in update_payload and update_payload["domain_groups"] is not None:
            normalized = _normalize_domain_groups(update_payload["domain_groups"])
            for group in normalized:
                for class_id in group:
                    self.get_class(tenant_id, class_id)
            update_payload["domain_groups_json"] = normalized
        update_payload.pop("domain_groups", None)
        self.repo.update_capability(obj, update_payload)
        self.db.commit()
        return obj

    def bind_capabilities(self, tenant_id: str, class_id: int, capability_ids: list[int]):
        self.get_class(tenant_id, class_id)
        for cap_id in capability_ids:
            cap = self.repo.get_capability(tenant_id, cap_id)
            if not cap:
                raise AppError(ErrorCodes.NOT_FOUND, f"capability not found: {cap_id}", status.HTTP_404_NOT_FOUND)
            domain_groups = _normalize_domain_groups(cap.domain_groups_json or [])
            if [class_id] not in domain_groups:
                domain_groups.append([class_id])
                self.repo.update_capability(cap, {"domain_groups_json": domain_groups})
            self.repo.bind_class_capability(tenant_id, class_id, cap_id)
        self.db.commit()

    def _resolve_entity_database_url(self) -> URL:
        if settings.entity_database_url:
            return make_url(settings.entity_database_url)
        base_url = make_url(settings.database_url)
        # For PostgreSQL, switch to the entity database configured in environment docs: memento.
        if base_url.get_backend_name().startswith("postgresql"):
            return base_url.set(database=settings.entity_database_name)
        return base_url

    def _entity_table_context(self, tenant_id: str, class_id: int):
        binding = self.repo.get_class_table_binding(tenant_id, class_id)
        if not binding or not binding.table_name:
            raise AppError(ErrorCodes.NOT_FOUND, "class table binding not found", status.HTTP_404_NOT_FOUND)
        mappings = self.repo.list_field_mappings(tenant_id, binding.id)
        if not mappings:
            raise AppError(ErrorCodes.VALIDATION, "no field mappings configured for class")
        attrs_by_id = {attr.id: attr for attr in self.repo.list_all_attributes(tenant_id)}
        columns = []
        for mapping in mappings:
            attr = attrs_by_id.get(mapping.data_attribute_id)
            columns.append(
                {
                    "data_attribute_id": mapping.data_attribute_id,
                    "field_name": mapping.field_name,
                    "data_type": (attr.data_type if attr else "string"),
                }
            )
        column_by_name = {item["field_name"]: item for item in columns}
        db_url = self._resolve_entity_database_url()
        return binding, columns, column_by_name, db_url

    def query_entity_data(
        self,
        tenant_id: str,
        class_id: int,
        page: int = 1,
        page_size: int = 20,
        filters: list[dict] | None = None,
        sort_field: str | None = None,
        sort_order: str = "asc",
    ):
        self.get_class(tenant_id, class_id)
        binding, columns, column_by_name, db_url = self._entity_table_context(tenant_id, class_id)
        engine = create_engine(db_url, future=True, pool_pre_ping=True)
        try:
            with engine.connect() as conn:
                dialect_name = conn.dialect.name
                schema_name = (binding.table_schema or "public") if dialect_name == "postgresql" else ""
                table_ref = _quote_identifier(binding.table_name)
                if schema_name:
                    table_ref = f"{_quote_identifier(schema_name)}.{table_ref}"

                conditions = []
                params = {}
                idx = 0
                for item in (filters or []):
                    field = item.get("field")
                    op = (item.get("op") or "eq").lower()
                    if field not in column_by_name:
                        continue
                    field_expr = _quote_identifier(field)
                    param_name = f"p{idx}"
                    if op == "eq":
                        params[param_name] = _parse_data_value(item.get("value"), column_by_name[field]["data_type"])
                        conditions.append(f"{field_expr} = :{param_name}")
                    elif op == "like":
                        params[param_name] = f"%{item.get('value', '')}%"
                        conditions.append(f"{field_expr} LIKE :{param_name}")
                    elif op == "in":
                        raw_values = item.get("value", [])
                        if isinstance(raw_values, str):
                            raw_values = [val.strip() for val in raw_values.split(",") if val.strip()]
                        parsed_values = [
                            _parse_data_value(val, column_by_name[field]["data_type"])
                            for val in (raw_values or [])
                        ]
                        if not parsed_values:
                            continue
                        holders = []
                        for n, parsed in enumerate(parsed_values):
                            in_key = f"{param_name}_{n}"
                            params[in_key] = parsed
                            holders.append(f":{in_key}")
                        conditions.append(f"{field_expr} IN ({', '.join(holders)})")
                    idx += 1
                where_clause = f" WHERE {' AND '.join(conditions)}" if conditions else ""

                order_field = sort_field if sort_field in column_by_name else columns[0]["field_name"]
                order_dir = "DESC" if str(sort_order).lower() == "desc" else "ASC"
                order_clause = f" ORDER BY {_quote_identifier(order_field)} {order_dir}"

                offset = (page - 1) * page_size
                params["limit"] = page_size
                params["offset"] = offset

                row_token_expr = "ctid::text" if dialect_name == "postgresql" else "rowid"
                field_exprs = ", ".join([_quote_identifier(item["field_name"]) for item in columns])
                count_sql = text(f"SELECT COUNT(1) AS total FROM {table_ref}{where_clause}")
                list_sql = text(
                    f"SELECT {row_token_expr} AS __row_token, {field_exprs} "
                    f"FROM {table_ref}{where_clause}{order_clause} LIMIT :limit OFFSET :offset"
                )
                total = int(conn.execute(count_sql, params).scalar() or 0)
                rows = conn.execute(list_sql, params).mappings().all()
                items = [dict(row) for row in rows]
                return {
                    "class_id": class_id,
                    "table_name": binding.table_name,
                    "table_schema": binding.table_schema,
                    "columns": columns,
                    "items": items,
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                }
        finally:
            engine.dispose()

    def create_entity_data(self, tenant_id: str, class_id: int, values: dict):
        self.get_class(tenant_id, class_id)
        binding, _columns, column_by_name, db_url = self._entity_table_context(tenant_id, class_id)
        if not values:
            raise AppError(ErrorCodes.VALIDATION, "values cannot be empty")
        field_names = [name for name in values.keys() if name in column_by_name]
        if not field_names:
            raise AppError(ErrorCodes.VALIDATION, "no valid fields in values")

        engine = create_engine(db_url, future=True, pool_pre_ping=True)
        try:
            with engine.begin() as conn:
                dialect_name = conn.dialect.name
                schema_name = (binding.table_schema or "public") if dialect_name == "postgresql" else ""
                table_ref = _quote_identifier(binding.table_name)
                if schema_name:
                    table_ref = f"{_quote_identifier(schema_name)}.{table_ref}"

                col_exprs = []
                val_exprs = []
                params = {}
                for idx, field_name in enumerate(field_names):
                    col_exprs.append(_quote_identifier(field_name))
                    key = f"v{idx}"
                    data_type = column_by_name[field_name]["data_type"]
                    parsed = _parse_data_value(values[field_name], data_type)
                    params[key] = json.dumps(parsed) if data_type in {"json", "array"} and parsed is not None else parsed
                    if dialect_name == "postgresql" and data_type in {"json", "array"}:
                        val_exprs.append(f":{key}::jsonb")
                    else:
                        val_exprs.append(f":{key}")
                sql = text(
                    f"INSERT INTO {table_ref} ({', '.join(col_exprs)}) VALUES ({', '.join(val_exprs)})"
                )
                conn.execute(sql, params)
        finally:
            engine.dispose()
        return {"created": True}

    def update_entity_data(self, tenant_id: str, class_id: int, row_token: str, values: dict):
        self.get_class(tenant_id, class_id)
        binding, _columns, column_by_name, db_url = self._entity_table_context(tenant_id, class_id)
        if not row_token:
            raise AppError(ErrorCodes.VALIDATION, "row_token is required")
        if not values:
            raise AppError(ErrorCodes.VALIDATION, "values cannot be empty")

        field_names = [name for name in values.keys() if name in column_by_name]
        if not field_names:
            raise AppError(ErrorCodes.VALIDATION, "no valid fields in values")

        engine = create_engine(db_url, future=True, pool_pre_ping=True)
        try:
            with engine.begin() as conn:
                dialect_name = conn.dialect.name
                schema_name = (binding.table_schema or "public") if dialect_name == "postgresql" else ""
                table_ref = _quote_identifier(binding.table_name)
                if schema_name:
                    table_ref = f"{_quote_identifier(schema_name)}.{table_ref}"

                set_exprs = []
                params = {"row_token": row_token}
                for idx, field_name in enumerate(field_names):
                    key = f"v{idx}"
                    data_type = column_by_name[field_name]["data_type"]
                    parsed = _parse_data_value(values[field_name], data_type)
                    params[key] = json.dumps(parsed) if data_type in {"json", "array"} and parsed is not None else parsed
                    if dialect_name == "postgresql" and data_type in {"json", "array"}:
                        set_exprs.append(f'{_quote_identifier(field_name)} = :{key}::jsonb')
                    else:
                        set_exprs.append(f'{_quote_identifier(field_name)} = :{key}')
                row_expr = "ctid::text" if dialect_name == "postgresql" else "rowid"
                sql = text(
                    f"UPDATE {table_ref} SET {', '.join(set_exprs)} WHERE {row_expr} = :row_token"
                )
                result = conn.execute(sql, params)
                if result.rowcount == 0:
                    raise AppError(ErrorCodes.NOT_FOUND, "entity row not found", status.HTTP_404_NOT_FOUND)
        finally:
            engine.dispose()
        return {"updated": True}

    def create_entity_table_for_class(self, tenant_id: str, class_id: int):
        cls = self.get_class(tenant_id, class_id)
        class_detail = self.get_class_detail(tenant_id, class_id)
        bound_attr_ids = class_detail["bound_attrs"]
        if not bound_attr_ids:
            raise AppError(ErrorCodes.VALIDATION, "no bound data attributes for this ontology class")

        attrs_by_id = {attr.id: attr for attr in self.repo.list_all_attributes(tenant_id)}
        bound_attrs = []
        for attr_id in bound_attr_ids:
            attr = attrs_by_id.get(attr_id)
            if attr:
                bound_attrs.append(attr)
        if not bound_attrs:
            raise AppError(ErrorCodes.VALIDATION, "no valid data attributes found for this ontology class")

        table_name = f"t_memento_{_sanitize_identifier(cls.code, default_prefix='cls')}"
        table_schema = "public"
        field_mappings = [
            {
                "data_attribute_id": attr.id,
                "field_name": _sanitize_identifier(attr.code, default_prefix=f"attr_{attr.id}"),
                "data_type": attr.data_type,
            }
            for attr in bound_attrs
        ]

        db_url = self._resolve_entity_database_url()
        engine = create_engine(db_url, future=True, pool_pre_ping=True)
        try:
            with engine.begin() as conn:
                dialect_name = conn.dialect.name
                quoted_table = f'"{table_name}"'
                if dialect_name == "postgresql":
                    quoted_table = f'"{table_schema}".{quoted_table}'
                else:
                    table_schema = None
                column_defs = [
                    f'"{item["field_name"]}" {_column_type_for_data_type(item["data_type"], dialect_name)}'
                    for item in field_mappings
                ]
                create_sql = f"CREATE TABLE IF NOT EXISTS {quoted_table} ({', '.join(column_defs)})"
                conn.execute(text(create_sql))

                # Ensure evolving ontology attributes can be added to an existing table.
                inspector = inspect(conn)
                existing_columns = set()
                if dialect_name == "postgresql":
                    existing_columns = {col["name"] for col in inspector.get_columns(table_name, schema=table_schema)}
                else:
                    existing_columns = {col["name"] for col in inspector.get_columns(table_name)}
                for item in field_mappings:
                    field_name = item["field_name"]
                    if field_name in existing_columns:
                        continue
                    alter_sql = (
                        f'ALTER TABLE {quoted_table} ADD COLUMN "{field_name}" '
                        f'{_column_type_for_data_type(item["data_type"], dialect_name)}'
                    )
                    conn.execute(text(alter_sql))
        finally:
            engine.dispose()

        # Auto-fill Physical Table Mapping and DB Field Name mappings.
        self.repo.upsert_class_table_binding(
            tenant_id,
            class_id,
            {
                "table_name": table_name,
                "table_schema": table_schema,
                "table_catalog": db_url.database,
                "config_json": {},
            },
        )
        self.repo.replace_field_mappings(
            tenant_id,
            self.repo.get_class_table_binding(tenant_id, class_id).id,
            [{"data_attribute_id": item["data_attribute_id"], "field_name": item["field_name"]} for item in field_mappings],
        )
        self.db.commit()
        return {
            "class_id": class_id,
            "table_name": table_name,
            "table_schema": table_schema,
            "table_catalog": db_url.database,
            "field_mappings": [{"data_attribute_id": item["data_attribute_id"], "field_name": item["field_name"]} for item in field_mappings],
        }

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
