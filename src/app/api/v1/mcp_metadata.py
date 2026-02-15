from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from src.app.api.deps import get_tenant_id, require_auth
from src.app.core.response import build_response
from src.app.infra.db.session import get_db
from src.app.schemas.mcp_metadata import AttributeMatchRequest, OntologiesByAttributesRequest
from src.app.services.mcp_metadata_service import MCPMetadataService

router = APIRouter(prefix="/mcp/metadata", tags=["mcp-metadata"], dependencies=[Depends(require_auth)])


@router.post("/attributes:match")
def match_attributes(
    req: AttributeMatchRequest,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    data = MCPMetadataService(db).match_attributes(tenant_id, req.query, req.top_k, req.page, req.page_size)
    return build_response(request, data)


@router.post("/ontologies:by-attributes")
def ontologies_by_attributes(
    req: OntologiesByAttributesRequest,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    data = MCPMetadataService(db).ontologies_by_attributes(tenant_id, req.attribute_ids, req.top_k)
    return build_response(request, data)


@router.get("/ontologies/{class_id}")
def get_ontology_detail(
    class_id: int,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    data = MCPMetadataService(db).ontology_detail(tenant_id, class_id)
    return build_response(request, data)


@router.get("/execution/{resource_type}/{resource_id}")
def get_execution_detail(
    resource_type: str,
    resource_id: int,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    data = MCPMetadataService(db).execution_detail(tenant_id, resource_type, resource_id)
    return build_response(request, data)
