from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from src.app.api.deps import get_tenant_id, require_auth
from src.app.core.response import build_response
from src.app.infra.db.session import get_db
from src.app.schemas.config import (
    LangfuseConfigUpdateRequest,
    TenantSearchConfigUpdateRequest,
    TenantLLMConfigUpsertRequest,
    TenantLLMConfigVerifyRequest,
)
from src.app.services.active_tenant_service import ActiveTenantService
from src.app.services.observability.langfuse_config_service import LangfuseConfigService
from src.app.services.tenant_runtime_config_service import TenantRuntimeConfigService
from src.app.services.tenant_llm_config_service import TenantLLMConfigService

router = APIRouter(prefix="/config", tags=["config"], dependencies=[Depends(require_auth)])


@router.get("/tenant-llm")
def get_tenant_llm_config(
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    data = TenantLLMConfigService(db).get_config(tenant_id)
    return build_response(request, data)


@router.put("/tenant-llm")
def upsert_tenant_llm_config(
    req: TenantLLMConfigUpsertRequest,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    data = TenantLLMConfigService(db).upsert_config(tenant_id, req.model_dump())
    return build_response(request, data)


@router.post("/tenant-llm:verify")
def verify_tenant_llm_config(
    req: TenantLLMConfigVerifyRequest,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    data = TenantLLMConfigService(db).verify_config(tenant_id, req.model_dump(exclude_none=True))
    return build_response(request, data)


@router.get("/observability/langfuse")
def get_langfuse_runtime_config(
    request: Request,
    db: Session = Depends(get_db),
):
    data = LangfuseConfigService(db).get_config(mask_secret_key=True)
    return build_response(request, data)


@router.put("/observability/langfuse")
def update_langfuse_runtime_config(
    req: LangfuseConfigUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    data = LangfuseConfigService(db).upsert_config(req.model_dump(exclude_none=True))
    return build_response(request, data)


@router.get("/tenant-search-config")
def get_tenant_search_config(
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    data = TenantRuntimeConfigService(db).get_search_config(tenant_id)
    return build_response(request, data)


@router.put("/tenant-search-config")
def update_tenant_search_config(
    req: TenantSearchConfigUpdateRequest,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    data = TenantRuntimeConfigService(db).upsert_search_config(tenant_id, req.model_dump(exclude_none=True))
    return build_response(request, data)


@router.get("/active-tenants")
def list_active_tenants(
    request: Request,
    db: Session = Depends(get_db),
):
    data = ActiveTenantService(db).list_active()
    return build_response(request, data)
