from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from src.app.api.deps import get_tenant_id, require_auth
from src.app.core.response import build_response
from src.app.infra.db.session import get_db
from src.app.schemas.knowledge import (
    CreateCapabilityTemplateRequest,
    CreateFewshotRequest,
    CreateRelationTemplateRequest,
    UpsertAttributeKnowledgeRequest,
    UpsertClassKnowledgeRequest,
)
from src.app.services.knowledge_service import KnowledgeService

router = APIRouter(prefix="/knowledge", tags=["knowledge"], dependencies=[Depends(require_auth)])


@router.post("/classes/{class_id}")
def upsert_class_knowledge(
    class_id: int,
    req: UpsertClassKnowledgeRequest,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    obj = KnowledgeService(db).upsert_class_knowledge(tenant_id, class_id, req.model_dump())
    return build_response(request, {"knowledge_class_id": obj.id, "class_id": obj.class_id, "version": obj.version})


@router.get("/classes/{class_id}/latest")
def get_latest_class_knowledge(
    class_id: int,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    obj = KnowledgeService(db).get_latest_class_knowledge(tenant_id, class_id)
    data = (
        {
            "knowledge_class_id": obj.id,
            "class_id": obj.class_id,
            "overview": obj.overview,
            "constraints_desc": obj.constraints_desc,
            "relation_desc": obj.relation_desc,
            "capability_desc": obj.capability_desc,
            "object_property_skill_desc": obj.object_property_skill_desc,
            "capability_skill_desc": obj.capability_skill_desc,
            "version": obj.version,
        }
        if obj
        else None
    )
    return build_response(request, data if data else {})


@router.post("/attributes/{attribute_id}")
def upsert_attribute_knowledge(
    attribute_id: int,
    req: UpsertAttributeKnowledgeRequest,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    obj = KnowledgeService(db).upsert_attribute_knowledge(tenant_id, attribute_id, req.model_dump())
    return build_response(
        request, {"knowledge_attribute_id": obj.id, "attribute_id": obj.attribute_id, "version": obj.version}
    )


@router.get("/attributes/{attribute_id}/latest")
def get_latest_attribute_knowledge(
    attribute_id: int,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    obj = KnowledgeService(db).get_latest_attribute_knowledge(tenant_id, attribute_id)
    data = (
        {
            "knowledge_attribute_id": obj.id,
            "attribute_id": obj.attribute_id,
            "definition": obj.definition,
            "synonyms_json": obj.synonyms_json,
            "constraints_desc": obj.constraints_desc,
            "version": obj.version,
        }
        if obj
        else None
    )
    return build_response(request, data if data else {})


@router.post("/relations/{relation_id}/templates")
def create_relation_template(
    relation_id: int,
    req: CreateRelationTemplateRequest,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    obj = KnowledgeService(db).create_relation_template(tenant_id, relation_id, req.model_dump())
    return build_response(request, {"template_id": obj.id, "relation_id": obj.relation_id, "version": obj.version})


@router.get("/relations/{relation_id}/templates/latest")
def get_latest_relation_template(
    relation_id: int,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    obj = KnowledgeService(db).get_latest_relation_template(tenant_id, relation_id)
    data = (
        {
            "template_id": obj.id,
            "relation_id": obj.relation_id,
            "prompt_template": obj.prompt_template,
            "template_schema": obj.template_schema,
            "mcp_slots_json": obj.mcp_slots_json,
            "intent_desc": obj.intent_desc,
            "few_shot_examples": obj.few_shot_examples,
            "json_schema": obj.json_schema,
            "skill_md": obj.skill_md,
            "version": obj.version,
        }
        if obj
        else None
    )
    return build_response(request, data if data else {})


@router.post("/capabilities/{capability_id}/templates")
def create_capability_template(
    capability_id: int,
    req: CreateCapabilityTemplateRequest,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    obj = KnowledgeService(db).create_capability_template(tenant_id, capability_id, req.model_dump())
    return build_response(
        request, {"template_id": obj.id, "capability_id": obj.capability_id, "version": obj.version}
    )


@router.get("/capabilities/{capability_id}/templates/latest")
def get_latest_capability_template(
    capability_id: int,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    obj = KnowledgeService(db).get_latest_capability_template(tenant_id, capability_id)
    data = (
        {
            "template_id": obj.id,
            "capability_id": obj.capability_id,
            "prompt_template": obj.prompt_template,
            "template_schema": obj.template_schema,
            "mcp_slots_json": obj.mcp_slots_json,
            "intent_desc": obj.intent_desc,
            "few_shot_examples": obj.few_shot_examples,
            "json_schema": obj.json_schema,
            "skill_md": obj.skill_md,
            "version": obj.version,
        }
        if obj
        else None
    )
    return build_response(request, data if data else {})


@router.post("/fewshot/examples")
def create_fewshot(
    req: CreateFewshotRequest,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    obj = KnowledgeService(db).create_fewshot(tenant_id, req.model_dump())
    return build_response(request, {"example_id": obj.id, "queued_for_embedding": True})


@router.get("/fewshot/examples")
def list_fewshot(
    request: Request,
    scope_type: str = Query(...),
    scope_id: int = Query(...),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    items = KnowledgeService(db).list_fewshots(tenant_id, scope_type, scope_id)
    return build_response(request, {"items": items, "total": len(items)})


@router.get("/fewshot/examples/search")
def search_fewshot(
    request: Request,
    scope_type: str = Query(...),
    scope_id: int = Query(...),
    query: str = Query(...),
    top_k: int = Query(5),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    items = KnowledgeService(db).search_fewshot(tenant_id, scope_type, scope_id, query, top_k)
    return build_response(request, {"items": items})
