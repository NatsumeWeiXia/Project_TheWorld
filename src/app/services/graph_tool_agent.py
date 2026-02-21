from __future__ import annotations

from sqlalchemy.orm import Session

from src.app.services.mcp_graph_service import MCPGraphService


class GraphToolAgent:
    def __init__(self, db: Session):
        self.graph_service = MCPGraphService(db)

    def call(self, tenant_id: str, tool_name: str, arguments: dict | None = None):
        return self.graph_service.call_tool(tenant_id, tool_name, arguments or {})
