from __future__ import annotations

from datetime import datetime

import httpx


class LLMProviderError(Exception):
    pass


class ProviderChatResult(dict):
    pass


class BaseLLMProvider:
    provider_name = "base"

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        timeout_seconds: float = 30.0,
        extra_options: dict | None = None,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.extra_options = extra_options or {}

    def chat_completion(
        self,
        messages: list[dict],
        *,
        model: str | None = None,
        stream: bool = False,
        tools: list[dict] | None = None,
        response_format: dict | None = None,
        timeout_seconds: float | None = None,
        extra_options: dict | None = None,
    ) -> ProviderChatResult:
        raise NotImplementedError

    def verify(self) -> dict:
        try:
            resp = self.chat_completion(
                messages=[{"role": "user", "content": "ping"}],
                stream=False,
                timeout_seconds=min(self.timeout_seconds, 10.0),
                extra_options={"max_tokens": 8},
            )
            return {
                "ok": True,
                "provider": self.provider_name,
                "model": resp.get("model") or self.model,
                "latency_ms": resp.get("latency_ms"),
            }
        except Exception as exc:
            return {
                "ok": False,
                "provider": self.provider_name,
                "model": self.model,
                "error": str(exc),
            }


class OpenAICompatibleProvider(BaseLLMProvider):
    provider_name = "openai-compatible"

    def chat_completion(
        self,
        messages: list[dict],
        *,
        model: str | None = None,
        stream: bool = False,
        tools: list[dict] | None = None,
        response_format: dict | None = None,
        timeout_seconds: float | None = None,
        extra_options: dict | None = None,
    ) -> ProviderChatResult:
        request_payload = {
            "model": model or self.model,
            "messages": messages,
            "stream": stream,
        }
        if tools:
            request_payload["tools"] = tools
        if response_format:
            request_payload["response_format"] = response_format
        merged_options = {**self.extra_options, **(extra_options or {})}
        request_payload.update(merged_options)

        timeout = timeout_seconds or self.timeout_seconds
        started = datetime.utcnow()
        with httpx.Client(timeout=timeout) as client:
            response = client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=request_payload,
            )
        latency_ms = int((datetime.utcnow() - started).total_seconds() * 1000)
        if response.status_code >= 400:
            raise LLMProviderError(f"provider call failed({response.status_code}): {response.text[:300]}")

        data = response.json()
        first_choice = ((data.get("choices") or [{}])[0] or {})
        message = first_choice.get("message") or {}
        return ProviderChatResult(
            {
                "provider": self.provider_name,
                "model": data.get("model") or (model or self.model),
                "content": message.get("content", ""),
                "reasoning_content": message.get("reasoning_content"),
                "raw": data,
                "latency_ms": latency_ms,
                "usage": data.get("usage") or {},
            }
        )
