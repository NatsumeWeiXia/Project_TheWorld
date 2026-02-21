from src.app.core.config import settings
from src.app.core.errors import AppError, ErrorCodes
from src.app.core.secrets import SecretCipher, mask_secret
from src.app.repositories.config_repo import TenantLLMConfigRepository
from src.app.services.llm.provider_factory import LLMProviderFactory


ALLOWED_PROVIDERS = {"deepseek", "qwen"}
INTERNAL_API_KEY_MAP_KEY = "__api_key_cipher_by_provider"


class TenantLLMConfigService:
    def __init__(self, db):
        self.db = db
        self.repo = TenantLLMConfigRepository(db)
        self.cipher = SecretCipher(settings.secret_cipher_key)

    def _validate_provider(self, provider: str) -> str:
        value = (provider or "").strip().lower()
        if value not in ALLOWED_PROVIDERS:
            raise AppError(ErrorCodes.VALIDATION, "provider must be deepseek or qwen")
        return value

    def _extract_api_key_cipher_by_provider(self, extra_json: dict | None) -> dict[str, str]:
        if not isinstance(extra_json, dict):
            return {}
        raw = extra_json.get(INTERNAL_API_KEY_MAP_KEY)
        if not isinstance(raw, dict):
            return {}
        out: dict[str, str] = {}
        for key, value in raw.items():
            provider = str(key or "").strip().lower()
            if provider in ALLOWED_PROVIDERS and isinstance(value, str) and value.strip():
                out[provider] = value
        return out

    def _sanitize_extra_json(self, extra_json: dict | None) -> dict:
        if not isinstance(extra_json, dict):
            return {}
        return {k: v for k, v in extra_json.items() if k != INTERNAL_API_KEY_MAP_KEY}

    def _resolve_provider_api_key_plain(self, obj, provider: str) -> str:
        key_map = self._extract_api_key_cipher_by_provider(obj.extra_json or {})
        cipher = key_map.get(provider)
        if not cipher and provider == obj.provider and obj.api_key_cipher:
            cipher = obj.api_key_cipher
        if not cipher:
            return ""
        return self.cipher.decrypt(cipher)

    def _build_api_key_masked_by_provider(self, obj) -> dict[str, str]:
        out: dict[str, str] = {}
        for provider in ALLOWED_PROVIDERS:
            plain = self._resolve_provider_api_key_plain(obj, provider)
            if plain:
                out[provider] = mask_secret(plain)
        return out

    def get_config(self, tenant_id: str):
        obj = self.repo.get(tenant_id)
        if not obj:
            return {
                "tenant_id": tenant_id,
                "provider": settings.default_llm_provider,
                "model": settings.default_llm_model,
                "base_url": settings.default_llm_base_url,
                "timeout_ms": settings.default_llm_timeout_ms,
                "enable_thinking": True,
                "fallback_provider": None,
                "fallback_model": None,
                "extra_json": {},
                "status": 0,
                "api_key_masked": "",
                "api_key_masked_by_provider": {},
                "updated_at": None,
            }
        key_map_masked = self._build_api_key_masked_by_provider(obj)
        return {
            "tenant_id": tenant_id,
            "provider": obj.provider,
            "model": obj.model,
            "base_url": obj.base_url,
            "timeout_ms": obj.timeout_ms,
            "enable_thinking": obj.enable_thinking,
            "fallback_provider": obj.fallback_provider,
            "fallback_model": obj.fallback_model,
            "extra_json": self._sanitize_extra_json(obj.extra_json or {}),
            "status": obj.status,
            "api_key_masked": key_map_masked.get(obj.provider, ""),
            "api_key_masked_by_provider": key_map_masked,
            "updated_at": obj.updated_at.isoformat() if obj.updated_at else None,
        }

    def upsert_config(self, tenant_id: str, payload: dict):
        provider = self._validate_provider(payload["provider"])
        fallback_provider = payload.get("fallback_provider")
        if fallback_provider:
            fallback_provider = self._validate_provider(fallback_provider)

        existing = self.repo.get(tenant_id)
        existing_extra = existing.extra_json or {} if existing else {}
        existing_key_map = self._extract_api_key_cipher_by_provider(existing_extra)
        incoming_extra = self._sanitize_extra_json(payload.get("extra_json") or {})
        merged_extra = {**self._sanitize_extra_json(existing_extra), **incoming_extra}
        incoming_api_key = (payload.get("api_key") or "").strip()
        if incoming_api_key:
            existing_key_map[provider] = self.cipher.encrypt(incoming_api_key)
        active_api_key_cipher = existing_key_map.get(provider)
        if not active_api_key_cipher and existing and existing.provider == provider and existing.api_key_cipher:
            active_api_key_cipher = existing.api_key_cipher
            existing_key_map[provider] = active_api_key_cipher

        if active_api_key_cipher:
            api_key_cipher = active_api_key_cipher
        else:
            raise AppError(ErrorCodes.VALIDATION, f"api_key is required for provider '{provider}'")
        merged_extra[INTERNAL_API_KEY_MAP_KEY] = existing_key_map
        obj = self.repo.upsert(
            tenant_id,
            {
                "provider": provider,
                "model": payload["model"].strip(),
                "api_key_cipher": api_key_cipher,
                "base_url": (payload.get("base_url") or "").strip() or None,
                "timeout_ms": int(payload.get("timeout_ms") or settings.default_llm_timeout_ms),
                "enable_thinking": bool(payload.get("enable_thinking", True)),
                "fallback_provider": fallback_provider,
                "fallback_model": (payload.get("fallback_model") or "").strip() or None,
                "extra_json": merged_extra,
                "status": int(payload.get("status", 1)),
            },
        )
        self.db.commit()
        return self.get_config(obj.tenant_id)

    def _resolve_runtime_config(self, tenant_id: str):
        obj = self.repo.get(tenant_id)
        if not obj:
            raise AppError(ErrorCodes.NOT_FOUND, "tenant llm config not found")
        return {
            "provider": obj.provider,
            "model": obj.model,
            "api_key": self._resolve_provider_api_key_plain(obj, obj.provider),
            "base_url": obj.base_url,
            "timeout_ms": obj.timeout_ms,
            "extra_json": self._sanitize_extra_json(obj.extra_json or {}),
            "fallback_provider": obj.fallback_provider,
            "fallback_model": obj.fallback_model,
            "fallback_api_key": self._resolve_provider_api_key_plain(obj, (obj.fallback_provider or "").strip().lower()),
            "status": obj.status,
        }

    def get_runtime_config(self, tenant_id: str) -> dict:
        cfg = self._resolve_runtime_config(tenant_id)
        if int(cfg["status"]) != 1:
            raise AppError(ErrorCodes.VALIDATION, "tenant llm config disabled")
        return cfg

    def get_runtime_provider_bundle(self, tenant_id: str):
        cfg = self._resolve_runtime_config(tenant_id)
        if int(cfg["status"]) != 1:
            raise AppError(ErrorCodes.VALIDATION, "tenant llm config disabled")
        primary = LLMProviderFactory.build(
            provider=cfg["provider"],
            api_key=cfg["api_key"],
            model=cfg["model"],
            base_url=cfg["base_url"],
            timeout_ms=cfg["timeout_ms"],
            extra_options=cfg["extra_json"],
        )
        fallback = None
        if cfg.get("fallback_provider") and cfg.get("fallback_model"):
            fallback = LLMProviderFactory.build(
                provider=cfg["fallback_provider"],
                api_key=cfg.get("fallback_api_key") or cfg["api_key"],
                model=cfg["fallback_model"],
                base_url=cfg["base_url"],
                timeout_ms=cfg["timeout_ms"],
                extra_options=cfg["extra_json"],
            )
        return {
            "primary": primary,
            "fallback": fallback,
            "provider": cfg["provider"],
            "model": cfg["model"],
        }

    def verify_config(self, tenant_id: str, payload: dict):
        obj = self.repo.get(tenant_id)
        if not obj:
            raise AppError(ErrorCodes.NOT_FOUND, "tenant llm config not found")
        provider = self._validate_provider(payload.get("provider") or obj.provider)
        model = (payload.get("model") or obj.model).strip()
        api_key = (payload.get("api_key") or self._resolve_provider_api_key_plain(obj, provider)).strip()
        if not api_key:
            raise AppError(ErrorCodes.VALIDATION, f"api_key is required for provider '{provider}'")
        base_url = payload.get("base_url") if payload.get("base_url") is not None else obj.base_url
        timeout_ms = int(payload.get("timeout_ms") or obj.timeout_ms)
        extra_json = self._sanitize_extra_json(obj.extra_json or {}).copy()
        extra_json.update(payload.get("extra_json") or {})

        provider_client = LLMProviderFactory.build(
            provider=provider,
            api_key=api_key,
            model=model,
            base_url=base_url,
            timeout_ms=timeout_ms,
            extra_options=extra_json,
        )
        return provider_client.verify()
