from fastapi import Header, HTTPException, status

from src.app.core.config import settings


def get_tenant_id(x_tenant_id: str = Header(..., alias="X-Tenant-Id")) -> str:
    if not x_tenant_id.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Tenant-Id is required")
    return x_tenant_id


def require_auth(authorization: str = Header(..., alias="Authorization")) -> None:
    if not settings.auth_enabled:
        return
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Authorization header")
