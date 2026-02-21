from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from src.app.api.deps import get_tenant_id, require_auth
from src.app.core.response import build_response
from src.app.infra.db.session import get_db
from src.app.schemas.mcp_data import DataQueryRequest, GroupAnalysisRequest
from src.app.services.mcp_data_service import MCPDataService

router = APIRouter(prefix="/mcp/data", tags=["mcp-data"], dependencies=[Depends(require_auth)])


@router.post("/query")
def query_data(
    req: DataQueryRequest,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    data = MCPDataService(db).query(tenant_id=tenant_id, payload=req.model_dump())
    return build_response(request, data)


@router.post("/group-analysis")
def group_analysis(
    req: GroupAnalysisRequest,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    data = MCPDataService(db).group_analysis(tenant_id=tenant_id, payload=req.model_dump())
    return build_response(request, data)
