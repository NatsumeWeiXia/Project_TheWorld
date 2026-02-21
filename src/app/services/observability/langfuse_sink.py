from __future__ import annotations

import json
import uuid
from threading import Lock

from src.app.core.config import settings
from src.app.services.observability.runtime_config import get_langfuse_runtime_config

try:
    from langfuse import Langfuse

    _LANGFUSE_IMPORT_ERROR = None
except Exception as exc:  # pragma: no cover
    Langfuse = None
    _LANGFUSE_IMPORT_ERROR = str(exc)


class LangfuseSink:
    _instance = None
    _lock = Lock()

    def __new__(cls):
        # Reuse one SDK client for process lifetime.
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._client = None
                    cls._instance._disabled = False
                    cls._instance._fingerprint = None
                    cls._instance._init_client()
        return cls._instance

    def _init_client(self) -> None:
        cfg = get_langfuse_runtime_config()
        if not cfg.get("enabled"):
            self._disabled = True
            self._client = None
            return
        if _LANGFUSE_IMPORT_ERROR or Langfuse is None:
            self._disabled = True
            self._client = None
            return
        if not cfg.get("public_key") or not cfg.get("secret_key"):
            self._disabled = True
            self._client = None
            return
        try:
            kwargs = {
                "public_key": cfg.get("public_key"),
                "secret_key": cfg.get("secret_key"),
            }
            if cfg.get("host"):
                kwargs["host"] = cfg.get("host")
            # Keep compatibility across different SDK minor versions.
            extra_kwargs = {}
            if cfg.get("release"):
                extra_kwargs["release"] = cfg.get("release")
            if cfg.get("environment"):
                extra_kwargs["environment"] = cfg.get("environment")
            try:
                self._client = Langfuse(**kwargs, **extra_kwargs)
            except TypeError:
                self._client = Langfuse(**kwargs)
            self._disabled = False
        except Exception:
            self._disabled = True
            self._client = None

    def _ensure_client(self) -> None:
        cfg = get_langfuse_runtime_config()
        fingerprint = (
            bool(cfg.get("enabled")),
            str(cfg.get("public_key") or ""),
            str(cfg.get("secret_key") or ""),
            str(cfg.get("host") or ""),
            str(cfg.get("environment") or ""),
            str(cfg.get("release") or ""),
        )
        if fingerprint != self._fingerprint:
            self._fingerprint = fingerprint
            self._init_client()

    @staticmethod
    def _trim_payload(payload: dict) -> dict:
        runtime_cfg = get_langfuse_runtime_config()
        max_chars = max(int(runtime_cfg.get("audit_payload_max_chars") or settings.audit_payload_max_chars or 0), 2000)
        try:
            text = json.dumps(payload or {}, ensure_ascii=False, default=str)
        except Exception:
            text = str(payload)
        if len(text) <= max_chars:
            return payload or {}
        return {
            "truncated": True,
            "size": len(text),
            "preview": text[:max_chars],
        }

    def emit_event(
        self,
        *,
        tenant_id: str | None,
        session_id: str,
        trace_id: str | None,
        step: str,
        event_type: str,
        payload: dict,
    ) -> None:
        self._ensure_client()
        if self._disabled or self._client is None:
            return
        safe_payload = self._trim_payload(payload or {})
        effective_trace_id = (str(trace_id or "").strip() or f"trace_{uuid.uuid4().hex}")
        try:
            # SDK API may vary by version; keep best-effort and never block request path.
            self._client.trace(
                id=effective_trace_id,
                name="theworld_reasoning_audit",
                session_id=session_id,
                user_id=tenant_id,
                metadata={
                    "step": step,
                    "event_type": event_type,
                    "payload": safe_payload,
                },
                tags=["theworld", "audit"],
            )

            # Add a concrete observation under trace to improve visibility in UI across SDK versions.
            event_payload = {
                "step": step,
                "event_type": event_type,
                "session_id": session_id,
                "payload": safe_payload,
            }
            if hasattr(self._client, "event"):
                self._client.event(
                    trace_id=effective_trace_id,
                    name=f"theworld.{event_type}",
                    metadata=event_payload,
                )

            if hasattr(self._client, "flush"):
                self._client.flush()
        except Exception:
            return
