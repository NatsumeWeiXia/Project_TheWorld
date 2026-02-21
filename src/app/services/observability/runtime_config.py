from __future__ import annotations

from copy import deepcopy
from threading import Lock

from src.app.core.config import settings
from src.app.core.secrets import mask_secret

_lock = Lock()
_state = {
    "enabled": bool(settings.langfuse_enabled),
    "public_key": settings.langfuse_public_key or "",
    "secret_key": settings.langfuse_secret_key or "",
    "host": settings.langfuse_host or "",
    "environment": settings.langfuse_environment or "",
    "release": settings.langfuse_release or "",
    "audit_payload_max_chars": int(settings.audit_payload_max_chars or 24000),
}


def get_langfuse_config(mask_secret_key: bool = True) -> dict:
    with _lock:
        payload = deepcopy(_state)
    if mask_secret_key:
        payload["secret_key_masked"] = mask_secret(payload.get("secret_key") or "")
        payload["secret_key"] = ""
    return payload


def update_langfuse_config(payload: dict) -> dict:
    with _lock:
        if "enabled" in payload:
            _state["enabled"] = bool(payload.get("enabled"))
        for key in ("public_key", "host", "environment", "release"):
            if key in payload and payload.get(key) is not None:
                _state[key] = str(payload.get(key) or "").strip()
        if "audit_payload_max_chars" in payload and payload.get("audit_payload_max_chars") is not None:
            value = int(payload.get("audit_payload_max_chars") or 24000)
            _state["audit_payload_max_chars"] = max(2000, min(value, 200000))
        if "secret_key" in payload:
            secret = str(payload.get("secret_key") or "").strip()
            if secret:
                _state["secret_key"] = secret
        return deepcopy(_state)


def get_langfuse_runtime_config() -> dict:
    with _lock:
        return deepcopy(_state)


def replace_langfuse_runtime_config(payload: dict) -> dict:
    with _lock:
        _state["enabled"] = bool(payload.get("enabled"))
        _state["public_key"] = str(payload.get("public_key") or "").strip()
        _state["secret_key"] = str(payload.get("secret_key") or "").strip()
        _state["host"] = str(payload.get("host") or "").strip()
        _state["environment"] = str(payload.get("environment") or "").strip()
        _state["release"] = str(payload.get("release") or "").strip()
        value = int(payload.get("audit_payload_max_chars") or 24000)
        _state["audit_payload_max_chars"] = max(2000, min(value, 200000))
        return deepcopy(_state)
