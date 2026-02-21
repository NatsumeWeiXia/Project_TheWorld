from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from src.app.api.deps import get_tenant_id, require_auth
from src.app.core.response import build_response
from src.app.infra.db.session import get_db
from src.app.schemas.reasoning import (
    CancelReasoningSessionRequest,
    ClarifyReasoningSessionRequest,
    CreateReasoningSessionRequest,
    RunReasoningSessionRequest,
)
from src.app.services.reasoning_service import ReasoningService

router = APIRouter(prefix="/reasoning", tags=["reasoning"], dependencies=[Depends(require_auth)])


@router.post("/sessions")
def create_session(
    req: CreateReasoningSessionRequest,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    data = ReasoningService(db).create_session(
        tenant_id=tenant_id,
        user_input=req.user_input,
        metadata=req.metadata,
        trace_id=getattr(request.state, "trace_id", None),
    )
    return build_response(request, data)


@router.get("/sessions/{session_id}")
def get_session(
    session_id: str,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    data = ReasoningService(db).get_session(tenant_id=tenant_id, session_id=session_id)
    return build_response(request, data)


@router.post("/sessions/{session_id}/run")
def run_session(
    session_id: str,
    req: RunReasoningSessionRequest,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    data = ReasoningService(db).run_session(
        tenant_id=tenant_id,
        session_id=session_id,
        user_input=req.user_input,
        trace_id=getattr(request.state, "trace_id", None),
    )
    return build_response(request, data)


@router.post("/sessions/{session_id}/clarify")
def clarify_session(
    session_id: str,
    req: ClarifyReasoningSessionRequest,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    data = ReasoningService(db).clarify(
        tenant_id=tenant_id,
        session_id=session_id,
        answer=req.answer,
        trace_id=getattr(request.state, "trace_id", None),
    )
    return build_response(request, data)


@router.get("/sessions/{session_id}/trace")
def get_trace(
    session_id: str,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    data = ReasoningService(db).list_trace(tenant_id=tenant_id, session_id=session_id)
    return build_response(request, data)


@router.post("/sessions/{session_id}/cancel")
def cancel_session(
    session_id: str,
    req: CancelReasoningSessionRequest,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    data = ReasoningService(db).cancel(
        tenant_id=tenant_id,
        session_id=session_id,
        reason=req.reason,
        trace_id=getattr(request.state, "trace_id", None),
    )
    return build_response(request, data)
