from __future__ import annotations

from abc import ABC, abstractmethod

from src.app.core.errors import AppError, ErrorCodes


class CapabilityExecutor(ABC):
    @abstractmethod
    def execute(self, context: dict) -> dict:
        raise NotImplementedError


class ObjectPropertyExecutor(ABC):
    @abstractmethod
    def execute(self, context: dict) -> dict:
        raise NotImplementedError


class _LLMDataExecutorMixin:
    @staticmethod
    def _normalize_mode(value: str | None) -> str:
        mode = str(value or "query").strip().lower()
        return "group-analysis" if mode in {"group-analysis", "group_analysis"} else "query"

    @staticmethod
    def _normalize_filters(filters: list[dict] | None) -> list[dict]:
        output = []
        for item in filters or []:
            if not isinstance(item, dict):
                continue
            field = str(item.get("field") or "").strip()
            if not field:
                continue
            op = str(item.get("op") or "eq").strip().lower()
            if op not in {"eq", "like", "in"}:
                op = "eq"
            output.append({"field": field, "op": op, "value": item.get("value")})
        return output

    def _execute_data_plan(self, context: dict, plan: dict) -> dict:
        mode = self._normalize_mode(plan.get("mode"))
        class_id = plan.get("class_id") or context["class_id"]
        if not class_id:
            raise AppError(ErrorCodes.VALIDATION, "execution planning missing class_id")

        filters = self._normalize_filters(plan.get("filters"))
        page = max(int(plan.get("page") or 1), 1)
        page_size = max(int(plan.get("page_size") or 20), 1)

        if mode == "group-analysis":
            group_by = [str(item).strip() for item in (plan.get("group_by") or []) if str(item).strip()]
            if not group_by and context.get("attribute_catalog"):
                first_field = str((context["attribute_catalog"][0] or {}).get("field_name") or "").strip()
                if first_field:
                    group_by = [first_field]
            if not group_by:
                raise AppError(ErrorCodes.VALIDATION, "group-analysis planning missing group_by")
            metrics = plan.get("metrics") or [{"agg": "count", "alias": "count"}]
            payload = {
                "class_id": int(class_id),
                "group_by": group_by,
                "metrics": metrics,
                "filters": filters,
                "page": page,
                "page_size": page_size,
                "sort_by": plan.get("sort_by"),
                "sort_order": str(plan.get("sort_order") or "desc").lower(),
            }
            data = context["mcp_data_call"](
                tenant_id=context["tenant_id"],
                session_id=context["session_id"],
                turn_id=context["turn_id"],
                trace_id=context.get("trace_id"),
                method="mcp.data.group-analysis",
                payload=payload,
            )
            return {"mode": "group-analysis", "payload": payload, "data": data}

        payload = {
            "class_id": int(class_id),
            "filters": filters,
            "page": page,
            "page_size": page_size,
            "sort_field": plan.get("sort_field"),
            "sort_order": str(plan.get("sort_order") or "asc").lower(),
        }
        data = context["mcp_data_call"](
            tenant_id=context["tenant_id"],
            session_id=context["session_id"],
            turn_id=context["turn_id"],
            trace_id=context.get("trace_id"),
            method="mcp.data.query",
            payload=payload,
        )
        return {"mode": "query", "payload": payload, "data": data}


class LLMCapabilityExecutor(_LLMDataExecutorMixin, CapabilityExecutor):
    def execute(self, context: dict) -> dict:
        decision = context["llm_json_decision"](
            tenant_id=context["tenant_id"],
            session_id=context["session_id"],
            turn_id=context["turn_id"],
            trace_id=context.get("trace_id"),
            step="executing",
            task="capability_execution_planning",
            system_prompt=(
                "你是能力执行规划器。"
                "请基于 capability 详情与用户意图，规划 mcp.data.query 或 mcp.data.group-analysis 参数。"
                "若用户输入携带明确值（如手机号15101330234），需写入 filters。"
            ),
            user_payload={
                "query": context.get("query"),
                "intent": context.get("intent") or {},
                "ontology": context.get("top_ontology") or {},
                "capability": context.get("selection") or {},
                "capability_detail": context.get("selection_detail") or {},
                "attribute_catalog": context.get("attribute_catalog") or [],
            },
            schema_hint={
                "mode": "query",
                "class_id": context.get("class_id"),
                "filters": [{"field": "mobile", "op": "eq", "value": "15101330234"}],
                "group_by": [],
                "metrics": [{"agg": "count", "alias": "count"}],
                "page": 1,
                "page_size": 20,
                "sort_field": None,
                "sort_order": "asc",
                "reason": "按手机号过滤并查询自然人",
            },
        )
        exec_result = self._execute_data_plan(context, decision)
        return {
            "executor_type": "capability",
            "execution_mode": exec_result["mode"],
            "executor_plan": decision,
            "data_request": exec_result["payload"],
            "data_execution": exec_result["data"],
        }


class LLMObjectPropertyExecutor(_LLMDataExecutorMixin, ObjectPropertyExecutor):
    def execute(self, context: dict) -> dict:
        relation_detail = context.get("selection_detail") or {}
        current_code = str((context.get("top_ontology") or {}).get("code") or "").strip()
        domain_codes = [str((item or {}).get("code") or "").strip() for item in (relation_detail.get("domain") or [])]
        range_codes = [str((item or {}).get("code") or "").strip() for item in (relation_detail.get("range") or [])]
        domain_codes = [code for code in domain_codes if code]
        range_codes = [code for code in range_codes if code]

        if current_code in domain_codes:
            target_options = [code for code in range_codes if code != current_code]
        elif current_code in range_codes:
            target_options = [code for code in domain_codes if code != current_code]
        else:
            target_options = [code for code in (domain_codes + range_codes) if code and code != current_code]
        target_options = list(dict.fromkeys(target_options))
        if not target_options:
            raise AppError(ErrorCodes.VALIDATION, "object_property has no resolvable target ontology")

        decision = context["llm_json_decision"](
            tenant_id=context["tenant_id"],
            session_id=context["session_id"],
            turn_id=context["turn_id"],
            trace_id=context.get("trace_id"),
            step="executing",
            task="object_property_execution_planning",
            system_prompt=(
                "你是对象属性执行规划器。"
                "请先选择目标本体，再规划 mcp.data.query 或 mcp.data.group-analysis 参数。"
                "filters 中 field 必须来自目标本体 attribute_catalog。"
            ),
            user_payload={
                "query": context.get("query"),
                "intent": context.get("intent") or {},
                "current_ontology": context.get("top_ontology") or {},
                "object_property": context.get("selection") or {},
                "object_property_detail": relation_detail,
                "target_ontology_options": target_options,
                "target_attribute_catalogs": context.get("target_attribute_catalogs") or {},
            },
            schema_hint={
                "target_ontology_code": target_options[0],
                "mode": "query",
                "filters": [{"field": "mobile", "op": "eq", "value": "15101330234"}],
                "group_by": [],
                "metrics": [{"agg": "count", "alias": "count"}],
                "page": 1,
                "page_size": 20,
                "sort_field": None,
                "sort_order": "asc",
                "reason": "通过对象属性跳转到目标本体并取数",
            },
        )

        target_code = str(decision.get("target_ontology_code") or "").strip()
        if target_code not in target_options:
            target_code = target_options[0]
        target = context["resolve_ontology"](target_code)
        if not target:
            raise AppError(ErrorCodes.VALIDATION, f"target ontology not found: {target_code}")

        target_catalog = context["build_attribute_catalog"](target["class_id"])
        exec_context = {
            **context,
            "class_id": target["class_id"],
            "attribute_catalog": target_catalog,
        }
        exec_result = self._execute_data_plan(exec_context, decision)
        return {
            "executor_type": "object_property",
            "target_ontology": target,
            "execution_mode": exec_result["mode"],
            "executor_plan": decision,
            "data_request": exec_result["payload"],
            "data_execution": exec_result["data"],
        }
