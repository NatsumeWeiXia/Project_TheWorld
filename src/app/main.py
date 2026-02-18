import uuid
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import inspect, text

from src.app.api.v1 import knowledge, mcp_graph, mcp_metadata, ontology
from src.app.core.config import settings
from src.app.core.errors import AppError, ErrorCodes
from src.app.core.response import build_response
from src.app.infra.db.base import Base
from src.app.infra.db.session import engine

app = FastAPI(title=settings.app_name, version="0.1.0")
console_html_path = Path(__file__).parent / "ui" / "m1_console.html"
graph_workspace_html_path = Path(__file__).parent / "ui" / "graph_workspace.html"


def _ensure_runtime_schema() -> None:
    with engine.begin() as conn:
        inspector = inspect(conn)
        table_names = set(inspector.get_table_names())
        dialect = conn.dialect.name

        def ensure_text_and_embedding(table_name: str):
            if table_name not in table_names:
                return
            columns = {col["name"] for col in inspector.get_columns(table_name)}
            if "search_text" not in columns:
                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN search_text TEXT"))
            if "embedding" not in columns:
                embedding_sql = "JSONB" if dialect == "postgresql" else "JSON"
                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN embedding {embedding_sql}"))

        ensure_text_and_embedding("ontology_class")
        ensure_text_and_embedding("ontology_relation")
        ensure_text_and_embedding("ontology_capability")

        if "ontology_capability" in table_names:
            cap_columns = {col["name"] for col in inspector.get_columns("ontology_capability")}
            if "domain_groups_json" not in cap_columns:
                if dialect == "postgresql":
                    conn.execute(
                        text(
                            "ALTER TABLE ontology_capability "
                            "ADD COLUMN domain_groups_json JSON NOT NULL DEFAULT '[]'::json"
                        )
                    )
                else:
                    conn.execute(
                        text(
                            "ALTER TABLE ontology_capability "
                            "ADD COLUMN domain_groups_json JSON NOT NULL DEFAULT '[]'"
                        )
                    )


@app.middleware("http")
async def trace_middleware(request: Request, call_next):
    request.state.trace_id = request.headers.get("X-Trace-Id", f"trace_{uuid.uuid4().hex[:16]}")
    response = await call_next(request)
    response.headers["X-Trace-Id"] = request.state.trace_id
    return response


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    payload = build_response(request, code=exc.code, message=exc.message)
    return JSONResponse(payload, status_code=exc.http_status)


@app.exception_handler(Exception)
async def unknown_error_handler(request: Request, exc: Exception):
    payload = build_response(request, code=ErrorCodes.INTERNAL, message=f"internal error: {exc}")
    return JSONResponse(payload, status_code=500)


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    _ensure_runtime_schema()


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return """
    <html>
      <head><title>Project_TheWorld M1</title></head>
      <body>
        <h1>Project_TheWorld M1</h1>
        <p>M1 capabilities are online.</p>
        <ul>
          <li>Ontology management APIs</li>
          <li>Knowledge framework APIs</li>
          <li>Metadata MCP APIs (4 core endpoints)</li>
          <li>Hybrid search for attributes/few-shot</li>
          <li>M1 management console page</li>
        </ul>
        <p>OpenAPI: <a href="/docs">/docs</a></p>
        <p>Console: <a href="/theworld/v1/console">/theworld/v1/console</a></p>
        <p>Graph Workspace: <a href="/theworld/v1/console/graph">/theworld/v1/console/graph</a></p>
      </body>
    </html>
    """


@app.get("/theworld/v1/console", response_class=HTMLResponse)
def m1_console() -> str:
    return console_html_path.read_text(encoding="utf-8")


@app.get("/theworld/v1/console/graph", response_class=HTMLResponse)
def graph_workspace() -> str:
    return graph_workspace_html_path.read_text(encoding="utf-8")


app.include_router(ontology.router, prefix=settings.api_prefix)
app.include_router(knowledge.router, prefix=settings.api_prefix)
app.include_router(mcp_metadata.router, prefix=settings.api_prefix)
app.include_router(mcp_graph.router, prefix=settings.api_prefix)
