from src.app.services.ontology_service import OntologyService


class MCPDataService:
    def __init__(self, db):
        self.ontology_service = OntologyService(db)

    def query(self, tenant_id: str, payload: dict):
        return self.ontology_service.query_entity_data(
            tenant_id=tenant_id,
            class_id=payload["class_id"],
            page=payload.get("page", 1),
            page_size=payload.get("page_size", 20),
            filters=payload.get("filters") or [],
            sort_field=payload.get("sort_field"),
            sort_order=payload.get("sort_order", "asc"),
        )

    def group_analysis(self, tenant_id: str, payload: dict):
        return self.ontology_service.group_analyze_entity_data(
            tenant_id=tenant_id,
            class_id=payload["class_id"],
            group_by=payload.get("group_by") or [],
            metrics=payload.get("metrics") or [],
            filters=payload.get("filters") or [],
            page=payload.get("page", 1),
            page_size=payload.get("page_size", 50),
            sort_by=payload.get("sort_by"),
            sort_order=payload.get("sort_order", "desc"),
        )
