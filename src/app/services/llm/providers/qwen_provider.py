from src.app.services.llm.provider_base import OpenAICompatibleProvider


class QwenProvider(OpenAICompatibleProvider):
    provider_name = "qwen"

    def __init__(self, api_key: str, model: str, timeout_seconds: float = 30.0, extra_options: dict | None = None):
        super().__init__(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            model=model,
            timeout_seconds=timeout_seconds,
            extra_options=extra_options,
        )
