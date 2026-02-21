from src.app.services.llm.provider_base import OpenAICompatibleProvider
from src.app.services.llm.providers.deepseek_provider import DeepseekProvider
from src.app.services.llm.providers.qwen_provider import QwenProvider


class LLMProviderFactory:
    @staticmethod
    def build(provider: str, api_key: str, model: str, base_url: str | None, timeout_ms: int, extra_options: dict | None = None):
        provider = (provider or "").strip().lower()
        timeout_seconds = max(timeout_ms, 1000) / 1000.0
        if provider == "deepseek":
            if base_url:
                return OpenAICompatibleProvider(
                    api_key=api_key,
                    base_url=base_url,
                    model=model,
                    timeout_seconds=timeout_seconds,
                    extra_options=extra_options,
                )
            return DeepseekProvider(
                api_key=api_key,
                model=model,
                timeout_seconds=timeout_seconds,
                extra_options=extra_options,
            )
        if provider == "qwen":
            if base_url:
                return OpenAICompatibleProvider(
                    api_key=api_key,
                    base_url=base_url,
                    model=model,
                    timeout_seconds=timeout_seconds,
                    extra_options=extra_options,
                )
            return QwenProvider(
                api_key=api_key,
                model=model,
                timeout_seconds=timeout_seconds,
                extra_options=extra_options,
            )
        if base_url:
            return OpenAICompatibleProvider(
                api_key=api_key,
                base_url=base_url,
                model=model,
                timeout_seconds=timeout_seconds,
                extra_options=extra_options,
            )
        raise ValueError("unsupported provider, expected deepseek or qwen")
