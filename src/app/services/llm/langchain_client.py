from __future__ import annotations

from src.app.core.errors import AppError, ErrorCodes

try:
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_openai import ChatOpenAI

    _LANGCHAIN_IMPORT_ERROR = None
except Exception:
    HumanMessage = None
    SystemMessage = None
    ChatOpenAI = None
    _LANGCHAIN_IMPORT_ERROR = "langchain/langchain-openai dependencies are required"


class LangChainLLMClient:
    @staticmethod
    def ensure_dependencies() -> None:
        if _LANGCHAIN_IMPORT_ERROR:
            raise AppError(ErrorCodes.INTERNAL, _LANGCHAIN_IMPORT_ERROR)

    @staticmethod
    def summarize_with_context(
        runtime_cfg: dict,
        query: str,
        ontology: dict,
        selected_task: dict,
        audit_callback=None,
    ) -> str:
        LangChainLLMClient.ensure_dependencies()

        model_kwargs = dict(runtime_cfg.get("extra_json") or {})
        enable_thinking = runtime_cfg.get("enable_thinking")
        if enable_thinking is not None:
            model_kwargs.setdefault("enable_thinking", bool(enable_thinking))

        llm = ChatOpenAI(
            api_key=runtime_cfg["api_key"],
            model=runtime_cfg["model"],
            base_url=runtime_cfg.get("base_url") or None,
            timeout=max(int(runtime_cfg.get("timeout_ms", 30000)), 1000) / 1000.0,
            model_kwargs=model_kwargs,
        )

        messages = [
            SystemMessage(content="你是本体推理编排助手，请生成简洁的执行摘要。"),
            HumanMessage(
                content=(
                    f"用户输入: {query}\n"
                    f"候选本体: {ontology}\n"
                    f"已选任务: {selected_task}\n"
                    "请输出不超过80字的中文摘要。"
                )
            ),
        ]
        if callable(audit_callback):
            try:
                audit_callback(
                    "llm_prompt_sent",
                    {
                        "provider": runtime_cfg.get("provider"),
                        "model": runtime_cfg.get("model"),
                        "base_url": runtime_cfg.get("base_url"),
                        "timeout_ms": runtime_cfg.get("timeout_ms"),
                        "model_kwargs": model_kwargs,
                        "messages": [
                            {"role": "system", "content": messages[0].content},
                            {"role": "user", "content": messages[1].content},
                        ],
                    },
                )
            except Exception:
                pass
        result = llm.invoke(messages)
        content = result.content if hasattr(result, "content") else ""
        if isinstance(content, list):
            content = "".join(str(item) for item in content)
        final_content = str(content).strip()
        if callable(audit_callback):
            try:
                audit_callback(
                    "llm_response_received",
                    {
                        "model": runtime_cfg.get("model"),
                        "content": final_content,
                        "response_metadata": getattr(result, "response_metadata", None),
                        "usage_metadata": getattr(result, "usage_metadata", None),
                    },
                )
            except Exception:
                pass
        return final_content
