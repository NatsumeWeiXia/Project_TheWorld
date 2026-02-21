from __future__ import annotations

from src.app.core.config import settings
from src.app.core.secrets import mask_secret
from src.app.repositories.config_repo import SystemRuntimeConfigRepository
from src.app.services.observability.runtime_config import replace_langfuse_runtime_config

LANGFUSE_CONFIG_KEY = "langfuse"


class LangfuseConfigService:
    def __init__(self, db):
        self.db = db
        self.repo = SystemRuntimeConfigRepository(db)

    @staticmethod
    def _defaults() -> dict:
        return {
            "enabled": bool(settings.langfuse_enabled),
            "public_key": settings.langfuse_public_key or "",
            "secret_key": settings.langfuse_secret_key or "",
            "host": settings.langfuse_host or "",
            "environment": settings.langfuse_environment or "",
            "release": settings.langfuse_release or "",
            "audit_payload_max_chars": int(settings.audit_payload_max_chars or 24000),
        }

    @staticmethod
    def _sanitize(payload: dict) -> dict:
        out = {
            "enabled": bool(payload.get("enabled")),
            "public_key": str(payload.get("public_key") or "").strip(),
            "secret_key": str(payload.get("secret_key") or "").strip(),
            "host": str(payload.get("host") or "").strip(),
            "environment": str(payload.get("environment") or "").strip(),
            "release": str(payload.get("release") or "").strip(),
            "audit_payload_max_chars": int(payload.get("audit_payload_max_chars") or 24000),
        }
        out["audit_payload_max_chars"] = max(2000, min(out["audit_payload_max_chars"], 200000))
        return out

    def _get_stored_or_default(self) -> dict:
        obj = self.repo.get(LANGFUSE_CONFIG_KEY)
        defaults = self._defaults()
        if not obj:
            return defaults
        return self._sanitize({**defaults, **(obj.config_json or {})})

    def get_config(self, mask_secret_key: bool = True) -> dict:
        payload = self._get_stored_or_default()
        replace_langfuse_runtime_config(payload)
        if mask_secret_key:
            return {
                **payload,
                "secret_key_masked": mask_secret(payload.get("secret_key") or ""),
                "secret_key": "",
            }
        return payload

    def upsert_config(self, payload: dict) -> dict:
        current = self._get_stored_or_default()
        merged = {**current, **(payload or {})}
        if "secret_key" in payload and not str(payload.get("secret_key") or "").strip():
            merged["secret_key"] = current.get("secret_key") or ""
        sanitized = self._sanitize(merged)
        self.repo.upsert(LANGFUSE_CONFIG_KEY, sanitized)
        self.db.commit()
        replace_langfuse_runtime_config(sanitized)
        return {
            **sanitized,
            "secret_key_masked": mask_secret(sanitized.get("secret_key") or ""),
            "secret_key": "",
        }

    def bootstrap_runtime_from_db(self) -> dict:
        payload = self._get_stored_or_default()
        replace_langfuse_runtime_config(payload)
        return payload
