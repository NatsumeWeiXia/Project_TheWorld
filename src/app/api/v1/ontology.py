from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from src.app.api.deps import get_tenant_id, require_auth
from src.app.core.response import build_response
from src.app.infra.db.session import get_db
from src.app.schemas.ontology import (
    BindCapabilitiesRequest,
    BindDataAttributesRequest,
    CreateClassRequest,
    CreateGlobalAttributeRequest,
    CreateGlobalCapabilityRequest,
    CreateInheritanceRequest,
    CreateObjectPropertyRequest,
    OWLValidateRequest,
    UpdateClassRequest,
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
    obj = OntologyService(db).get_class(tenant_id, class_id)
    return build_response(
        request,
        {"id": obj.id, "code": obj.code, "name": obj.name, "description": obj.description, "status": obj.status},
    )


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
    items = OntologyService(db).list_object_properties(tenant_id)
    data = [
        {
            "id": i.id,
            "code": i.code,
            "name": i.name,
            "description": i.description,
            "skill_md": i.skill_md,
            "relation_type": i.relation_type,
            "mcp_bindings_json": i.mcp_bindings_json,
        }
        for i in items
    ]
    return build_response(request, {"items": data, "total": len(data)})


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
        {"id": i.id, "code": i.code, "name": i.name, "description": i.description, "skill_md": i.skill_md, "mcp_bindings_json": i.mcp_bindings_json}
        for i in items
    ]
    return build_response(request, {"items": data, "total": len(data)})


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


@router.get("/owl:export")
def owl_export(
    request: Request,
    format: str = Query("ttl"),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    data = OntologyService(db).owl_export(tenant_id, export_format=format)
    return build_response(request, data)
