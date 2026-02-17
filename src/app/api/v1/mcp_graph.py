from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from src.app.api.deps import get_tenant_id, require_auth
from src.app.core.response import build_response
from src.app.infra.db.session import get_db
from src.app.schemas.mcp_graph import MCPGraphToolCallRequest
from src.app.services.mcp_graph_service import MCPGraphService

router = APIRouter(prefix="/mcp/graph", tags=["mcp-graph"], dependencies=[Depends(require_auth)])


@router.post("/tools:list")
def list_tools(request: Request, _tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db)):
    data = {"tools": MCPGraphService(db).list_tools()}
    return build_response(request, data)


@router.post("/tools:call")
def call_tool(
    req: MCPGraphToolCallRequest,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    result = MCPGraphService(db).call_tool(tenant_id, req.name, req.arguments)
    data = {
        "toolName": req.name,
        "content": [{"type": "json", "json": result}],
        "isError": False,
    }
    return build_response(request, data)

