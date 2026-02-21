from __future__ import annotations

from src.app.repositories.config_repo import ActiveTenantRepository


class ActiveTenantService:
    def __init__(self, db):
        self.db = db
        self.repo = ActiveTenantRepository(db)

    def touch(self, tenant_id: str) -> None:
        value = str(tenant_id or "").strip()
        if not value:
            return
        self.repo.touch(value)
        self.db.commit()

    def list_active(self, limit: int = 200) -> dict:
        size = max(1, min(int(limit or 200), 2000))
        rows = self.repo.list_active(limit=size)
        return {
            "items": [
                {
                    "tenant_id": row.tenant_id,
                    "is_active": bool(row.is_active),
                    "first_seen_at": row.first_seen_at.isoformat() if row.first_seen_at else None,
                    "last_seen_at": row.last_seen_at.isoformat() if row.last_seen_at else None,
                }
                for row in rows
            ]
        }
