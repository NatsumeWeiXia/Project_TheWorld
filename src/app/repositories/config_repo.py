from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from src.app.infra.db import models


class TenantLLMConfigRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, tenant_id: str):
        stmt = select(models.TenantLLMConfig).where(models.TenantLLMConfig.tenant_id == tenant_id)
        return self.db.scalar(stmt)

    def upsert(self, tenant_id: str, payload: dict):
        obj = self.get(tenant_id)
        if not obj:
            obj = models.TenantLLMConfig(tenant_id=tenant_id, **payload)
            self.db.add(obj)
            self.db.flush()
            return obj

        for key, value in payload.items():
            setattr(obj, key, value)
        self.db.flush()
        return obj


class TenantRuntimeConfigRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, tenant_id: str):
        stmt = select(models.TenantRuntimeConfig).where(models.TenantRuntimeConfig.tenant_id == tenant_id)
        return self.db.scalar(stmt)

    def upsert(self, tenant_id: str, config_json: dict):
        obj = self.get(tenant_id)
        if not obj:
            obj = models.TenantRuntimeConfig(tenant_id=tenant_id, config_json=config_json or {})
            self.db.add(obj)
            self.db.flush()
            return obj
        obj.config_json = config_json or {}
        self.db.flush()
        return obj


class SystemRuntimeConfigRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, config_key: str):
        stmt = select(models.SystemRuntimeConfig).where(models.SystemRuntimeConfig.config_key == config_key)
        return self.db.scalar(stmt)

    def upsert(self, config_key: str, config_json: dict):
        obj = self.get(config_key)
        if not obj:
            obj = models.SystemRuntimeConfig(config_key=config_key, config_json=config_json or {})
            self.db.add(obj)
            self.db.flush()
            return obj
        obj.config_json = config_json or {}
        self.db.flush()
        return obj


class ActiveTenantRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, tenant_id: str):
        stmt = select(models.ActiveTenant).where(models.ActiveTenant.tenant_id == tenant_id)
        return self.db.scalar(stmt)

    def touch(self, tenant_id: str):
        obj = self.get(tenant_id)
        if not obj:
            obj = models.ActiveTenant(tenant_id=tenant_id, is_active=True)
            self.db.add(obj)
            self.db.flush()
            return obj
        obj.is_active = True
        obj.last_seen_at = models.now()
        self.db.flush()
        return obj

    def list_active(self, limit: int = 200):
        stmt = (
            select(models.ActiveTenant)
            .where(models.ActiveTenant.is_active.is_(True))
            .order_by(models.ActiveTenant.last_seen_at.desc(), models.ActiveTenant.id.desc())
            .limit(limit)
        )
        return self.db.scalars(stmt).all()
