from __future__ import annotations

import json
import re

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
        llm, model_kwargs = LangChainLLMClient._build_llm(runtime_cfg)
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
        return LangChainLLMClient._invoke_text(
            llm=llm,
            runtime_cfg=runtime_cfg,
            model_kwargs=model_kwargs,
            messages=messages,
            audit_callback=audit_callback,
        )

    @staticmethod
    def invoke_json(
        runtime_cfg: dict,
        system_prompt: str,
        user_payload: dict,
        schema_hint: dict | None = None,
        audit_callback=None,
    ) -> dict:
        LangChainLLMClient.ensure_dependencies()
        llm, model_kwargs = LangChainLLMClient._build_llm(runtime_cfg)
        schema_text = json.dumps(schema_hint or {}, ensure_ascii=False)
        payload_text = json.dumps(user_payload or {}, ensure_ascii=False)
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(
                content=(
                    "请严格返回 JSON 对象，不要输出其他文字。\n"
                    f"SchemaHint: {schema_text}\n"
                    f"Input: {payload_text}"
                )
            ),
        ]
        text = LangChainLLMClient._invoke_text(
            llm=llm,
            runtime_cfg=runtime_cfg,
            model_kwargs=model_kwargs,
            messages=messages,
            audit_callback=audit_callback,
        )
        return LangChainLLMClient._parse_json_text(text)

    @staticmethod
    def _build_llm(runtime_cfg: dict):
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
        return llm, model_kwargs

    @staticmethod
    def _invoke_text(llm, runtime_cfg: dict, model_kwargs: dict, messages: list, audit_callback=None) -> str:
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

    @staticmethod
    def _parse_json_text(text: str) -> dict:
        raw = str(text or "").strip()
        if not raw:
            raise ValueError("llm returned empty text")
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
        fenced = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", raw, re.IGNORECASE)
        if fenced:
            parsed = json.loads(fenced.group(1))
            if isinstance(parsed, dict):
                return parsed
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            parsed = json.loads(raw[start : end + 1])
            if isinstance(parsed, dict):
                return parsed
        raise ValueError("llm output is not valid json object")
