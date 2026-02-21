from src.app.services.llm.provider_factory import LLMProviderFactory
from src.app.services.llm.provider_base import OpenAICompatibleProvider


def test_provider_factory_supports_deepseek_qwen():
    deepseek = LLMProviderFactory.build(
        provider="deepseek",
        api_key="k1",
        model="deepseek-reasoner",
        base_url=None,
        timeout_ms=30000,
        extra_options={},
    )
    assert deepseek.provider_name in {"deepseek", "openai-compatible"}

    qwen = LLMProviderFactory.build(
        provider="qwen",
        api_key="k2",
        model="qwen3.5-plus",
        base_url=None,
        timeout_ms=30000,
        extra_options={},
    )
    assert qwen.provider_name in {"qwen", "openai-compatible"}


def test_provider_factory_custom_base_url_uses_openai_compatible():
    provider = LLMProviderFactory.build(
        provider="deepseek",
        api_key="k",
        model="m",
        base_url="https://example.com/v1",
        timeout_ms=5000,
        extra_options={"temperature": 0.2},
    )
    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider.base_url == "https://example.com/v1"
