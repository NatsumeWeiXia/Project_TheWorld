import uuid
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

from src.app.api.v1 import knowledge, mcp_metadata, ontology
from src.app.core.config import settings
from src.app.core.errors import AppError, ErrorCodes
from src.app.core.response import build_response
from src.app.infra.db.base import Base
from src.app.infra.db.session import engine

app = FastAPI(title=settings.app_name, version="0.1.0")
console_html_path = Path(__file__).parent / "ui" / "m1_console.html"


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
        <p>Console: <a href="/m1/console">/m1/console</a></p>
      </body>
    </html>
    """


@app.get("/m1/console", response_class=HTMLResponse)
def m1_console() -> str:
    return console_html_path.read_text(encoding="utf-8")


app.include_router(ontology.router, prefix=settings.api_prefix)
app.include_router(knowledge.router, prefix=settings.api_prefix)
app.include_router(mcp_metadata.router, prefix=settings.api_prefix)
