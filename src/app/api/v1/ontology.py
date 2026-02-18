from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from src.app.api.deps import get_tenant_id, require_auth
from src.app.core.response import build_response
from src.app.infra.db.session import get_db
from src.app.schemas.ontology import (
    BindCapabilitiesRequest,
    BackfillEmbeddingsRequest,
    BindDataAttributesRequest,
    CreateEntityDataRequest,
    CreateClassRequest,
    CreateGlobalAttributeRequest,
    CreateGlobalCapabilityRequest,
    CreateInheritanceRequest,
    CreateObjectPropertyRequest,
    OWLValidateRequest,
    QueryEntityDataRequest,
    UpdateClassRequest,
    UpdateEntityDataRequest,
    UpdateGlobalAttributeRequest,
    UpdateGlobalCapabilityRequest,
    UpdateObjectPropertyRequest,
    UpsertClassFieldMappingRequest,
    UpsertClassTableBindingRequest,
)
from src.app.services.ontology_service import OntologyService

router = APIRouter(prefix="/ontology", tags=["ontology"], dependencies=[Depends(require_auth)])


@router.post("/classes")
def create_class(req: CreateClassRequest, request: Request, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db)):
    obj = OntologyService(db).create_class(tenant_id, req.model_dump())
    return build_response(request, {"id": obj.id, "code": obj.code, "name": obj.name, "version": obj.version})


@router.get("/classes")
def list_classes(
    request: Request,
    status: int | None = Query(1),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    items = OntologyService(db).list_classes(tenant_id, status)
    data = [
        {"id": item.id, "code": item.code, "name": item.name, "description": item.description, "status": item.status}
        for item in items
    ]
    return build_response(request, {"items": data, "total": len(data)})


@router.get("/classes/{class_id}")
def get_class(class_id: int, request: Request, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db)):
    data = OntologyService(db).get_class_detail(tenant_id, class_id)
    return build_response(request, data)


@router.put("/classes/{class_id}")
def update_class(
    class_id: int, req: UpdateClassRequest, request: Request, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db)
):
    OntologyService(db).update_class(tenant_id, class_id, req.model_dump())
    return build_response(request, {"id": class_id, "updated": True})


@router.delete("/classes/{class_id}")
def delete_class(class_id: int, request: Request, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db)):
    OntologyService(db).delete_class(tenant_id, class_id)
    return build_response(request, {"id": class_id, "deleted": True})


@router.get("/tree")
def get_tree(request: Request, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db)):
    data = OntologyService(db).get_class_tree(tenant_id)
    return build_response(request, {"items": data})


@router.get("/hybrid-search")
def hybrid_search(
    request: Request,
    q: str = Query(""),
    types: str = Query("ontology,data-attr,obj-prop,capability"),
    top_k: int = Query(80, ge=1, le=500),
    score_gap: float = Query(0.0, ge=0.0),
    relative_diff: float = Query(0.0, ge=0.0),
    w_sparse: float = Query(0.45, ge=0.0),
    w_dense: float = Query(0.55, ge=0.0),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    allowed = {"ontology", "data-attr", "obj-prop", "capability"}
    wanted = [item.strip() for item in (types or "").split(",") if item.strip() in allowed]
    data = OntologyService(db).hybrid_search_resources(
        tenant_id,
        q,
        wanted or list(allowed),
        top_k=top_k,
        score_gap=score_gap,
        relative_diff=relative_diff,
        w_sparse=w_sparse,
        w_dense=w_dense,
    )
    return build_response(request, data)


@router.post("/classes/{class_id}/inheritance")
def create_inheritance(
    class_id: int,
    req: CreateInheritanceRequest,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    obj = OntologyService(db).add_inheritance(tenant_id, class_id, req.parent_class_id)
    return build_response(
        request,
        {"child_class_id": obj.child_class_id, "parent_class_id": obj.parent_class_id, "created": True},
    )


@router.post("/data-attributes")
def create_global_attribute(
    req: CreateGlobalAttributeRequest,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    obj = OntologyService(db).create_global_attribute(tenant_id, req.model_dump())
    return build_response(request, {"attribute_id": obj.id})


@router.get("/data-attributes")
def list_global_attributes(request: Request, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db)):
    items = OntologyService(db).list_global_attributes(tenant_id)
    data = [{"id": i.id, "code": i.code, "name": i.name, "data_type": i.data_type, "description": i.description} for i in items]
    return build_response(request, {"items": data, "total": len(data)})


@router.get("/data-attributes/{attribute_id}")
def get_global_attribute(
    attribute_id: int, request: Request, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db)
):
    obj = OntologyService(db).get_global_attribute(tenant_id, attribute_id)
    return build_response(
        request,
        {"id": obj.id, "code": obj.code, "name": obj.name, "data_type": obj.data_type, "description": obj.description},
    )


@router.put("/data-attributes/{attribute_id}")
def update_global_attribute(
    attribute_id: int,
    req: UpdateGlobalAttributeRequest,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    OntologyService(db).update_global_attribute(tenant_id, attribute_id, req.model_dump())
    return build_response(request, {"id": attribute_id, "updated": True})


@router.delete("/data-attributes/{attribute_id}")
def delete_global_attribute(
    attribute_id: int, request: Request, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db)
):
    OntologyService(db).delete_global_attribute(tenant_id, attribute_id)
    return build_response(request, {"id": attribute_id, "deleted": True})


@router.post("/classes/{class_id}/data-attributes:bind")
def bind_data_attributes(
    class_id: int,
    req: BindDataAttributesRequest,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    OntologyService(db).bind_data_attributes(tenant_id, class_id, req.data_attribute_ids)
    return build_response(request, {"class_id": class_id, "bound": len(req.data_attribute_ids)})


@router.post("/object-properties")
def create_object_property(
    req: CreateObjectPropertyRequest,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    obj = OntologyService(db).create_object_property(tenant_id, req.model_dump())
    return build_response(request, {"object_property_id": obj.id})


@router.get("/object-properties")
def list_object_properties(request: Request, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db)):
    svc = OntologyService(db)
    items = svc.list_object_properties(tenant_id)
    repo = svc.repo
    data = [
        {
            "id": i.id,
            "code": i.code,
            "name": i.name,
            "description": i.description,
            "skill_md": i.skill_md,
            "domain_class_ids": sorted({item.class_id for item in repo.list_relation_domains(tenant_id, i.id)}),
            "range_class_ids": sorted({item.class_id for item in repo.list_relation_ranges(tenant_id, i.id)}),
        }
        for i in items
    ]
    return build_response(request, {"items": data, "total": len(data)})


@router.get("/object-properties/{relation_id}")
def get_object_property(
    relation_id: int, request: Request, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db)
):
    data = OntologyService(db).get_object_property_detail(tenant_id, relation_id)
    return build_response(request, data)


@router.put("/object-properties/{relation_id}")
def update_object_property(
    relation_id: int,
    req: UpdateObjectPropertyRequest,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    OntologyService(db).update_object_property(tenant_id, relation_id, req.model_dump())
    return build_response(request, {"id": relation_id, "updated": True})


@router.delete("/object-properties/{relation_id}")
def delete_object_property(
    relation_id: int, request: Request, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db)
):
    OntologyService(db).delete_object_property(tenant_id, relation_id)
    return build_response(request, {"id": relation_id, "deleted": True})


@router.post("/capabilities")
def create_global_capability(
    req: CreateGlobalCapabilityRequest,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    obj = OntologyService(db).create_global_capability(tenant_id, req.model_dump())
    return build_response(request, {"capability_id": obj.id})


@router.get("/capabilities")
def list_capabilities(request: Request, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db)):
    items = OntologyService(db).list_capabilities(tenant_id)
    data = [
        {
            "id": i.id,
            "code": i.code,
            "name": i.name,
            "description": i.description,
            "skill_md": i.skill_md,
            "domain_groups": i.domain_groups_json or [],
            "domain_class_ids": sorted({int(class_id) for g in (i.domain_groups_json or []) for class_id in (g or [])}),
        }
        for i in items
    ]
    return build_response(request, {"items": data, "total": len(data)})


@router.get("/capabilities/{capability_id}")
def get_capability(
    capability_id: int, request: Request, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db)
):
    obj = OntologyService(db).get_global_capability(tenant_id, capability_id)
    domain_groups = obj.domain_groups_json or []
    return build_response(
        request,
        {
            "id": obj.id,
            "code": obj.code,
            "name": obj.name,
            "description": obj.description,
            "skill_md": obj.skill_md,
            "input_schema": obj.input_schema,
            "output_schema": obj.output_schema,
            "domain_groups": domain_groups,
            "domain_class_ids": sorted({int(class_id) for g in domain_groups for class_id in (g or [])}),
        },
    )


@router.put("/capabilities/{capability_id}")
def update_capability(
    capability_id: int,
    req: UpdateGlobalCapabilityRequest,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    OntologyService(db).update_global_capability(tenant_id, capability_id, req.model_dump())
    return build_response(request, {"id": capability_id, "updated": True})


@router.delete("/capabilities/{capability_id}")
def delete_capability(
    capability_id: int, request: Request, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db)
):
    OntologyService(db).delete_global_capability(tenant_id, capability_id)
    return build_response(request, {"id": capability_id, "deleted": True})


@router.post("/classes/{class_id}/capabilities:bind")
def bind_capabilities(
    class_id: int,
    req: BindCapabilitiesRequest,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    OntologyService(db).bind_capabilities(tenant_id, class_id, req.capability_ids)
    return build_response(request, {"class_id": class_id, "bound": len(req.capability_ids)})


@router.put("/classes/{class_id}/table-binding")
def upsert_class_table_binding(
    class_id: int,
    req: UpsertClassTableBindingRequest,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    obj = OntologyService(db).upsert_class_table_binding(tenant_id, class_id, req.model_dump())
    return build_response(request, {"binding_id": obj.id, "class_id": obj.class_id, "table_name": obj.table_name})


@router.post("/classes/{class_id}/table-binding:create-table")
def create_table_by_ontology(
    class_id: int,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    data = OntologyService(db).create_entity_table_for_class(tenant_id, class_id)
    return build_response(request, data)


@router.post("/classes/{class_id}/table-binding:data:query")
def query_table_data_by_ontology(
    class_id: int,
    req: QueryEntityDataRequest,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    data = OntologyService(db).query_entity_data(
        tenant_id=tenant_id,
        class_id=class_id,
        page=req.page,
        page_size=req.page_size,
        filters=req.filters,
        sort_field=req.sort_field,
        sort_order=req.sort_order,
    )
    return build_response(request, data)


@router.post("/classes/{class_id}/table-binding:data")
def create_table_data_by_ontology(
    class_id: int,
    req: CreateEntityDataRequest,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    data = OntologyService(db).create_entity_data(tenant_id=tenant_id, class_id=class_id, values=req.values)
    return build_response(request, data)


@router.put("/classes/{class_id}/table-binding:data/{row_token}")
def update_table_data_by_ontology(
    class_id: int,
    row_token: str,
    req: UpdateEntityDataRequest,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    data = OntologyService(db).update_entity_data(
        tenant_id=tenant_id,
        class_id=class_id,
        row_token=row_token,
        values=req.values,
    )
    return build_response(request, data)


@router.put("/classes/{class_id}/table-binding/field-mapping")
def upsert_class_field_mapping(
    class_id: int,
    req: UpsertClassFieldMappingRequest,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    items = OntologyService(db).upsert_class_field_mapping(tenant_id, class_id, req.mappings)
    return build_response(request, {"class_id": class_id, "updated": len(items)})


@router.post("/owl:validate")
def owl_validate(
    req: OWLValidateRequest,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    data = OntologyService(db).owl_validate(tenant_id, strict=req.strict)
    return build_response(request, data)


@router.post("/embeddings:backfill")
def backfill_embeddings(
    req: BackfillEmbeddingsRequest,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    data = OntologyService(db).backfill_search_embeddings(
        tenant_id=tenant_id,
        resource_types=req.resource_types,
        batch_size=req.batch_size,
    )
    return build_response(request, data)


@router.get("/owl:export")
def owl_export(
    request: Request,
    format: str = Query("ttl"),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    data = OntologyService(db).owl_export(tenant_id, export_format=format)
    return build_response(request, data)
