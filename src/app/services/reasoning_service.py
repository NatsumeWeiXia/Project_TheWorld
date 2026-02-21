from __future__ import annotations

import re

from src.app.core.errors import AppError, ErrorCodes
from src.app.repositories.ontology_repo import OntologyRepository
from src.app.repositories.reasoning_repo import ReasoningRepository
from src.app.services.context_service import ContextService
from src.app.services.graph_tool_agent import GraphToolAgent
from src.app.services.llm.langchain_client import LangChainLLMClient
from src.app.services.mcp_data_service import MCPDataService
from src.app.services.reasoning_executors import (
    LLMCapabilityExecutor,
    LLMObjectPropertyExecutor,
)
from src.app.services.tenant_llm_config_service import TenantLLMConfigService
from src.app.services.trace_service import TraceService

try:
    from langgraph.graph import END, StateGraph

    _LANGGRAPH_IMPORT_ERROR = None
except Exception:
    END = None
    StateGraph = None
    _LANGGRAPH_IMPORT_ERROR = "langgraph dependency is required"


class ReasoningService:
    def __init__(self, db):
        if _LANGGRAPH_IMPORT_ERROR:
            raise AppError(ErrorCodes.INTERNAL, _LANGGRAPH_IMPORT_ERROR)
        LangChainLLMClient.ensure_dependencies()

        self.db = db
        self.repo = ReasoningRepository(db)
        self.ontology_repo = OntologyRepository(db)
        self.graph_agent = GraphToolAgent(db)
        self.mcp_data_service = MCPDataService(db)
        self.context_service = ContextService(db)
        self.trace_service = TraceService(db)
        self.tenant_llm_service = TenantLLMConfigService(db)
        self.capability_executor = LLMCapabilityExecutor()
        self.object_property_executor = LLMObjectPropertyExecutor()
        self._compiled_graph = None

    @staticmethod
    def _extract_keywords(query: str) -> list[str]:
        raw_tokens = re.split(r"[\s,，。；;、\n\t]+", query or "")
        tokens = []
        for token in raw_tokens:
            t = token.strip()
            if not t or len(t) <= 1:
                continue
            tokens.append(t)
        seen = set()
        deduped = []
        for token in tokens:
            if token in seen:
                continue
            seen.add(token)
            deduped.append(token)
        return deduped[:8]

    @staticmethod
    def _merge_scored_items(items: list[dict], score_key: str = "score") -> list[dict]:
        by_code: dict[str, dict] = {}
        for item in items:
            code = str(item.get("code") or "").strip()
            if not code:
                continue
            score = item.get(score_key)
            if code not in by_code:
                by_code[code] = dict(item)
                continue
            existing = by_code[code]
            existing_score = existing.get(score_key)
            if isinstance(score, (int, float)) and (not isinstance(existing_score, (int, float)) or score > existing_score):
                by_code[code] = dict(item)
        output = list(by_code.values())
        output.sort(key=lambda x: (x.get(score_key) if isinstance(x.get(score_key), (int, float)) else -1), reverse=True)
        return output

    def _read_latest_context_value(self, session_id: str, key: str, scopes: list[str] | None = None):
        items = self.repo.list_context(session_id, scopes or ["session", "artifact", "global"])
        for item in reversed(items):
            if item.key == key:
                return item.value_json or {}
        return {}

    def _graph_call(
        self,
        tenant_id: str,
        session_id: str,
        turn_id: int,
        trace_id: str | None,
        tool_name: str,
        arguments: dict,
        step: str,
    ):
        self.trace_service.emit(
            session_id=session_id,
            turn_id=turn_id,
            step=step,
            event_type="mcp_call_requested",
            payload={"method": "mcp.graph.tools:call", "tool": tool_name, "arguments": arguments},
            trace_id=trace_id,
            tenant_id=tenant_id,
        )
        result = self.graph_agent.call(tenant_id, tool_name, arguments)
        self.trace_service.emit(
            session_id=session_id,
            turn_id=turn_id,
            step=step,
            event_type="mcp_call_completed",
            payload={"method": "mcp.graph.tools:call", "tool": tool_name, "result": result},
            trace_id=trace_id,
            tenant_id=tenant_id,
        )
        return result

    def _mcp_data_call(
        self,
        tenant_id: str,
        session_id: str,
        turn_id: int,
        trace_id: str | None,
        method: str,
        payload: dict,
        step: str = "executing",
    ):
        self.trace_service.emit(
            session_id=session_id,
            turn_id=turn_id,
            step=step,
            event_type="mcp_call_requested",
            payload={"method": method, "arguments": payload},
            trace_id=trace_id,
            tenant_id=tenant_id,
        )
        if method == "mcp.data.query":
            result = self.mcp_data_service.query(tenant_id=tenant_id, payload=payload)
        elif method == "mcp.data.group-analysis":
            result = self.mcp_data_service.group_analysis(tenant_id=tenant_id, payload=payload)
        else:
            raise AppError(ErrorCodes.VALIDATION, f"unsupported mcp data method: {method}")
        self.trace_service.emit(
            session_id=session_id,
            turn_id=turn_id,
            step=step,
            event_type="mcp_call_completed",
            payload={"method": method, "result": result},
            trace_id=trace_id,
            tenant_id=tenant_id,
        )
        return result

    def _build_llm_audit_callback(
        self,
        tenant_id: str,
        session_id: str,
        turn_id: int,
        trace_id: str | None,
        step: str,
        task: str,
    ):
        def _callback(event_type: str, payload: dict) -> None:
            data = dict(payload or {})
            data["task"] = task
            self.trace_service.emit(
                session_id=session_id,
                turn_id=turn_id,
                step=step,
                event_type=event_type,
                payload=data,
                trace_id=trace_id,
                tenant_id=tenant_id,
            )

        return _callback

    def _llm_json_decision(
        self,
        tenant_id: str,
        session_id: str,
        turn_id: int,
        trace_id: str | None,
        step: str,
        task: str,
        system_prompt: str,
        user_payload: dict,
        schema_hint: dict,
    ) -> dict:
        callback = self._build_llm_audit_callback(
            tenant_id=tenant_id,
            session_id=session_id,
            turn_id=turn_id,
            trace_id=trace_id,
            step=step,
            task=task,
        )
        try:
            runtime_cfg = self.tenant_llm_service.get_runtime_config(tenant_id)
            return LangChainLLMClient.invoke_json(
                runtime_cfg=runtime_cfg,
                system_prompt=system_prompt,
                user_payload=user_payload,
                schema_hint=schema_hint,
                audit_callback=callback,
            )
        except Exception as exc:
            self.trace_service.emit(
                session_id=session_id,
                turn_id=turn_id,
                step=step,
                event_type="llm_response_received",
                payload={
                    "task": task,
                    "error": str(exc),
                    "fallback_used": False,
                },
                trace_id=trace_id,
                tenant_id=tenant_id,
            )
            raise AppError(ErrorCodes.INTERNAL, f"llm decision failed ({task}): {exc}")

    def _resolve_ontology(self, tenant_id: str, ontology_code: str) -> dict | None:
        code = str(ontology_code or "").strip()
        if not code:
            return None
        class_obj = self.ontology_repo.get_class_by_code(tenant_id, code)
        if not class_obj:
            return None
        return {"class_id": class_obj.id, "name": class_obj.name, "code": class_obj.code}

    def _build_attribute_catalog(self, tenant_id: str, class_id: int) -> list[dict]:
        binding = self.ontology_repo.get_class_table_binding(tenant_id, class_id)
        mapping_by_attr_id = {}
        if binding:
            for mapping in self.ontology_repo.list_field_mappings(tenant_id, binding.id):
                mapping_by_attr_id[mapping.data_attribute_id] = mapping.field_name
        attrs_by_id = {item.id: item for item in self.ontology_repo.list_all_attributes(tenant_id)}
        refs = self.ontology_repo.list_class_data_attr_refs_by_class_ids(tenant_id, [class_id])
        output = []
        for ref in refs:
            attr = attrs_by_id.get(ref.data_attribute_id)
            if not attr:
                continue
            output.append(
                {
                    "attribute_id": attr.id,
                    "code": attr.code,
                    "name": attr.name,
                    "data_type": attr.data_type,
                    "description": attr.description,
                    "field_name": mapping_by_attr_id.get(attr.id),
                }
            )
        output.sort(key=lambda x: (x.get("name") or "", x.get("code") or ""))
        return output

    @staticmethod
    def _normalize_code_list(values) -> list[str]:
        items = []
        for value in values or []:
            code = str(value or "").strip()
            if code:
                items.append(code)
        out = []
        seen = set()
        for code in items:
            if code in seen:
                continue
            seen.add(code)
            out.append(code)
        return out

    def create_session(self, tenant_id: str, user_input: str, metadata: dict, trace_id: str | None = None):
        session = self.repo.create_session(tenant_id=tenant_id, status="created")
        turn = self.repo.create_turn(
            session_id=session.id,
            user_input=user_input,
            turn_no=1,
            status="created",
        )
        self.context_service.write(session.id, "session", "initial_input", {"text": user_input})
        if metadata:
            self.context_service.write(session.id, "global", "session_metadata", metadata)

        self.trace_service.emit(
            session_id=session.id,
            turn_id=turn.id,
            step="session_create",
            event_type="intent_parsed",
            payload={"input": user_input},
            trace_id=trace_id,
            tenant_id=tenant_id,
        )
        self.db.commit()
        return {
            "session_id": session.id,
            "status": session.status,
            "turn": {
                "turn_id": turn.id,
                "turn_no": turn.turn_no,
                "status": turn.status,
                "user_input": turn.user_input,
            },
        }

    def get_session(self, tenant_id: str, session_id: str):
        session = self.repo.get_session(tenant_id=tenant_id, session_id=session_id)
        if not session:
            raise AppError(ErrorCodes.NOT_FOUND, "reasoning session not found")

        latest_turn = self.repo.latest_turn(session_id)
        pending_clarification = self.repo.latest_pending_clarification(session_id)
        tasks = self.repo.list_tasks(session_id=session_id, turn_id=latest_turn.id if latest_turn else None)

        return {
            "session_id": session.id,
            "status": session.status,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "ended_at": session.ended_at.isoformat() if session.ended_at else None,
            "latest_turn": (
                {
                    "turn_id": latest_turn.id,
                    "turn_no": latest_turn.turn_no,
                    "status": latest_turn.status,
                    "user_input": latest_turn.user_input,
                    "model_output": latest_turn.model_output,
                }
                if latest_turn
                else None
            ),
            "pending_clarification": (
                {
                    "clarification_id": pending_clarification.id,
                    "question": pending_clarification.question_json,
                }
                if pending_clarification
                else None
            ),
            "tasks": [
                {
                    "task_id": item.id,
                    "task_type": item.task_type,
                    "status": item.status,
                    "retry_count": item.retry_count,
                    "payload": item.task_payload,
                }
                for item in tasks
            ],
        }

    def _create_waiting_clarification(
        self,
        tenant_id: str,
        session_id: str,
        turn_id: int,
        question_json: dict,
        trace_id: str | None,
        waiting_status: str = "waiting_clarification",
    ):
        clarification = self.repo.create_clarification(
            session_id=session_id,
            turn_id=turn_id,
            question_json=question_json,
        )
        session = self.repo.get_session(tenant_id=tenant_id, session_id=session_id)
        if session:
            self.repo.update_session_status(session, waiting_status)

        turn = self.repo.get_turn(turn_id)
        if turn:
            self.repo.update_turn(turn, {"status": waiting_status})

        event_type = "clarification_asked" if waiting_status == "waiting_clarification" else "traversal_confirmation_requested"
        self.trace_service.emit(
            session_id=session_id,
            turn_id=turn_id,
            step="clarification",
            event_type=event_type,
            payload=question_json,
            trace_id=trace_id,
            tenant_id=tenant_id,
        )
        return clarification

    def _node_understand_intent(self, state: dict) -> dict:
        next_state = dict(state)
        query = state["query"]
        llm_result = self._llm_json_decision(
            tenant_id=state["tenant_id"],
            session_id=state["session_id"],
            turn_id=state["turn_id"],
            trace_id=state.get("trace_id"),
            step="understanding",
            task="intent_extraction",
            system_prompt=(
                "你是本体推理助手。"
                "请从用户输入中抽取关键词与业务要素，并返回结构化 JSON。"
                "不要输出解释，只输出 JSON。"
            ),
            user_payload={"query": query},
            schema_hint={
                "keywords": ["手机号", "人", "综合分析"],
                "business_elements": [{"name": "手机号", "value": "15191445006", "role": "filter"}],
                "goal_actions": ["综合分析"],
                "intent_summary": "先定位人，再执行综合分析",
            },
        )
        keywords = self._normalize_code_list(llm_result.get("keywords")) or self._extract_keywords(query)
        business_elements = llm_result.get("business_elements")
        if not isinstance(business_elements, list):
            business_elements = []
        goal_actions = llm_result.get("goal_actions")
        if not isinstance(goal_actions, list):
            goal_actions = []
        next_state["intent"] = {
            "query": query,
            "keywords": keywords,
            "business_elements": business_elements,
            "goal_actions": goal_actions,
            "intent_summary": str(llm_result.get("intent_summary") or query),
        }
        self.trace_service.emit(
            session_id=state["session_id"],
            turn_id=state["turn_id"],
            step="understanding",
            event_type="intent_parsed",
            payload={"query": query, "keywords": keywords, "business_elements_count": len(business_elements)},
            trace_id=state.get("trace_id"),
            tenant_id=state["tenant_id"],
        )
        self.trace_service.emit(
            session_id=state["session_id"],
            turn_id=state["turn_id"],
            step="planning",
            event_type="plan_generated",
            payload={"keywords": keywords, "goal_actions": goal_actions},
            trace_id=state.get("trace_id"),
            tenant_id=state["tenant_id"],
        )
        return next_state

    def _node_discover_candidates(self, state: dict) -> dict:
        next_state = dict(state)
        tenant_id = state["tenant_id"]
        session_id = state["session_id"]
        turn_id = state["turn_id"]
        trace_id = state.get("trace_id")

        intent = state.get("intent") or {}
        keywords = intent.get("keywords") or []
        business_elements = intent.get("business_elements") or []
        business_tokens = []
        for item in business_elements:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            value = str(item.get("value") or "").strip()
            if name:
                business_tokens.append(name)
            if value:
                business_tokens.append(value)
        queries = [state.get("query") or ""] + keywords[:4] + business_tokens[:4]
        attr_candidates: list[dict] = []
        for query in queries:
            query_text = str(query or "").strip()
            if not query_text:
                continue
            result = self._graph_call(
                tenant_id,
                session_id,
                turn_id,
                trace_id,
                "graph.list_data_attributes",
                {
                    "query": query_text,
                    "top_n": 20,
                    "score_gap": 0.0,
                    "relative_diff": 0.0,
                    "w_sparse": 0.45,
                    "w_dense": 0.55,
                },
                "discovery",
            )
            attr_candidates.extend(result.get("items") or [])

        attr_candidates = self._merge_scored_items(attr_candidates)
        next_state["candidate_attributes"] = attr_candidates[:20]

        if not next_state["candidate_attributes"]:
            next_state["status"] = "waiting_clarification"
            next_state["clarification_question"] = {
                "tenant_id": tenant_id,
                "type": "no_attribute_match",
                "question": "未定位到关键数据属性，请补充更具体的业务要素或字段。",
            }
            self.trace_service.emit(
                session_id=session_id,
                turn_id=turn_id,
                step="attributes",
                event_type="attributes_matched",
                payload={"count": 0},
                trace_id=trace_id,
                tenant_id=tenant_id,
            )
            return next_state

        attribute_codes = [item.get("code") for item in next_state["candidate_attributes"] if item.get("code")][:8]
        related = self._graph_call(
            tenant_id,
            session_id,
            turn_id,
            trace_id,
            "graph.get_data_attribute_related_ontologies",
            {"attributeCodes": attribute_codes},
            "locating",
        )

        ontology_hit_count: dict[str, int] = {}
        ontology_by_code: dict[str, dict] = {}
        for row in related or []:
            for ontology in row.get("ontologies") or []:
                code = str(ontology.get("code") or "").strip()
                if not code:
                    continue
                ontology_hit_count[code] = int(ontology_hit_count.get(code) or 0) + 1
                ontology_by_code[code] = dict(ontology)
        related_ontologies = []
        for code, count in ontology_hit_count.items():
            score = round(float(count) * 0.1, 4)
            related_ontologies.append({**ontology_by_code[code], "score": score})

        ontology_candidates: list[dict] = []
        for query in [state.get("query") or "", " ".join((keywords + business_tokens)[:6])]:
            query_text = str(query or "").strip()
            if not query_text:
                continue
            result = self._graph_call(
                tenant_id,
                session_id,
                turn_id,
                trace_id,
                "graph.list_ontologies",
                {
                    "query": query_text,
                    "top_n": 20,
                    "score_gap": 0.0,
                    "relative_diff": 0.0,
                    "w_sparse": 0.45,
                    "w_dense": 0.55,
                },
                "locating",
            )
            ontology_candidates.extend(result.get("items") or [])
        ontology_candidates.extend(related_ontologies)
        ontology_candidates = self._merge_scored_items(ontology_candidates)

        self.trace_service.emit(
            session_id=session_id,
            turn_id=turn_id,
            step="attributes",
            event_type="attributes_matched",
            payload={"count": len(next_state["candidate_attributes"])},
            trace_id=trace_id,
            tenant_id=tenant_id,
        )
        self.trace_service.emit(
            session_id=session_id,
            turn_id=turn_id,
            step="locating",
            event_type="ontologies_located",
            payload={"count": len(ontology_candidates)},
            trace_id=trace_id,
            tenant_id=tenant_id,
        )

        if not ontology_candidates:
            next_state["status"] = "waiting_clarification"
            next_state["clarification_question"] = {
                "tenant_id": tenant_id,
                "type": "no_ontology_match",
                "question": "已匹配到数据属性，但未定位到可执行本体，请补充业务对象。",
            }
            return next_state

        next_state["ontology_candidates"] = ontology_candidates[:20]
        return next_state

    def _node_select_anchor_ontologies(self, state: dict) -> dict:
        next_state = dict(state)
        tenant_id = state["tenant_id"]
        session_id = state["session_id"]
        turn_id = state["turn_id"]
        trace_id = state.get("trace_id")

        candidates = state.get("ontology_candidates") or []
        preferred_code = (state.get("resume_target_ontology_code") or "").strip()
        candidate_payload = []
        for item in candidates[:20]:
            candidate_payload.append(
                {
                    "code": item.get("code"),
                    "name": item.get("name"),
                    "description": item.get("description"),
                    "score": item.get("score"),
                }
            )

        llm_selection = self._llm_json_decision(
            tenant_id=tenant_id,
            session_id=session_id,
            turn_id=turn_id,
            trace_id=trace_id,
            step="planning",
            task="anchor_ontology_selection",
            system_prompt=(
                "你是本体推理助手。"
                "请根据用户意图，从候选本体中选择输入锚点本体（至少1个）和目标本体（可为空）。"
                "输入锚点必须来自候选 code。"
            ),
            user_payload={
                "query": state.get("query"),
                "intent": state.get("intent") or {},
                "preferred_code": preferred_code or None,
                "candidates": candidate_payload,
            },
            schema_hint={
                "input_ontology_codes": ["natural_person"],
                "target_ontology_codes": ["message_service"],
                "reason": "手机号映射自然人，自然人可关联消息服务",
            },
        )
        input_codes = self._normalize_code_list(llm_selection.get("input_ontology_codes"))
        target_codes = self._normalize_code_list(llm_selection.get("target_ontology_codes"))
        if not input_codes and preferred_code:
            input_codes = [preferred_code]
        if not input_codes and candidates:
            input_codes = [str(candidates[0].get("code") or "").strip()]
        input_codes = [code for code in input_codes if code]

        if not input_codes:
            next_state["status"] = "waiting_clarification"
            next_state["clarification_question"] = {
                "tenant_id": tenant_id,
                "type": "anchor_ontology_missing",
                "question": "未能确定起点本体，请补充业务对象。",
            }
            return next_state

        candidate_by_code = {str(item.get("code") or "").strip(): item for item in candidates}
        selected_code = input_codes[0]
        detail_rows = self._graph_call(
            tenant_id,
            session_id,
            turn_id,
            trace_id,
            "graph.get_ontology_details",
            {"ontologyCodes": [selected_code]},
            "planning",
        )
        detail = (detail_rows or [None])[0] or {}

        class_obj = self.ontology_repo.get_class_by_code(tenant_id, selected_code)
        if not class_obj:
            next_state["status"] = "waiting_clarification"
            next_state["clarification_question"] = {
                "tenant_id": tenant_id,
                "type": "anchor_ontology_missing",
                "question": "定位到的本体在当前租户不可用，请确认后重试。",
            }
            return next_state

        top_ontology = {
            "class_id": class_obj.id,
            "name": detail.get("name") or class_obj.name,
            "code": selected_code,
        }
        input_ontologies = []
        for code in input_codes:
            item = candidate_by_code.get(code, {})
            input_ontologies.append({"code": code, "name": item.get("name") or code})
        target_ontologies = []
        for code in target_codes:
            item = candidate_by_code.get(code, {})
            target_ontologies.append({"code": code, "name": item.get("name") or code})

        next_state["top_ontology"] = top_ontology
        next_state["selected_ontology_detail"] = detail
        next_state["plan_state"] = {
            "input_ontologies": input_ontologies or [top_ontology],
            "target_ontologies": target_ontologies,
            "pending_steps": [],
            "selection_reason": str(llm_selection.get("reason") or ""),
        }
        self.trace_service.emit(
            session_id=session_id,
            turn_id=turn_id,
            step="planning",
            event_type="ontology_selected",
            payload={
                "input_ontology": top_ontology,
                "input_codes": input_codes,
                "target_codes": target_codes,
                "resume": bool(preferred_code),
            },
            trace_id=trace_id,
            tenant_id=tenant_id,
        )
        return next_state

    def _node_inspect_ontology(self, state: dict) -> dict:
        next_state = dict(state)
        top_ontology = state.get("top_ontology") or {}
        detail = state.get("selected_ontology_detail") or {}
        capabilities = detail.get("capabilities") or []
        object_properties = detail.get("objectProperties") or []
        capability_candidates = [
            {"code": item.get("code"), "name": item.get("name"), "description": item.get("description")}
            for item in capabilities
            if str(item.get("code") or "").strip()
        ]
        object_property_candidates = [
            {"code": item.get("code"), "name": item.get("name"), "description": item.get("description")}
            for item in object_properties
            if str(item.get("code") or "").strip()
        ]

        if not capability_candidates and not object_property_candidates:
            next_state["status"] = "waiting_clarification"
            next_state["clarification_question"] = {
                "tenant_id": state["tenant_id"],
                "type": "no_executable_resource",
                "class_id": top_ontology.get("class_id"),
                "question": "当前本体没有可执行 capability 或 object property，请补充业务目标。",
            }
            return next_state

        decision = self._llm_json_decision(
            tenant_id=state["tenant_id"],
            session_id=state["session_id"],
            turn_id=state["turn_id"],
            trace_id=state.get("trace_id"),
            step="planning",
            task="capability_or_object_property_selection",
            system_prompt=(
                "你是本体推理助手。"
                "请在 capability 和 object_property 中选择一个执行目标。"
                "判断依据只能使用它们的 name/description。"
            ),
            user_payload={
                "query": state.get("query"),
                "intent": state.get("intent") or {},
                "current_ontology": top_ontology,
                "capabilities": capability_candidates,
                "object_properties": object_property_candidates,
            },
            schema_hint={
                "action": "execute_capability",
                "capability_code": "query_user",
                "object_property_code": "",
                "reason": "当前 capability 能直接满足用户意图",
            },
        )
        action = str(decision.get("action") or "").strip().lower()
        capability_by_code = {str(item.get("code") or "").strip(): dict(item) for item in capabilities}
        relation_by_code = {str(item.get("code") or "").strip(): dict(item) for item in object_properties}

        selected_capability_code = str(decision.get("capability_code") or "").strip()
        selected_relation_code = str(decision.get("object_property_code") or "").strip()

        if action == "execute_capability" and capability_by_code:
            if selected_capability_code not in capability_by_code:
                selected_capability_code = next(iter(capability_by_code.keys()))
            selected_capability = capability_by_code[selected_capability_code]
            capability_details = self._graph_call(
                state["tenant_id"],
                state["session_id"],
                state["turn_id"],
                state.get("trace_id"),
                "graph.get_capability_details",
                {"capabilityCodes": [selected_capability_code]},
                "planning",
            )
            selected_capability_detail = (capability_details or [None])[0] or {}
            selected_capability["_detail"] = selected_capability_detail
            next_state["candidate_capabilities"] = [selected_capability]
            next_state["selected_capability"] = selected_capability
            next_state["selected_capability_detail"] = selected_capability_detail
            next_state["selected_object_property"] = {}
            next_state["selected_object_property_detail"] = {}
            next_state["plan_state"] = {
                **(state.get("plan_state") or {}),
                "execution_decision": {
                    "action": "execute_capability",
                    "capability_code": selected_capability_code,
                    "reason": str(decision.get("reason") or ""),
                },
            }
            self.trace_service.emit(
                session_id=state["session_id"],
                turn_id=state["turn_id"],
                step="planning",
                event_type="task_planned",
                payload={"task_count": 1, "selected_capability_code": selected_capability_code},
                trace_id=state.get("trace_id"),
                tenant_id=state["tenant_id"],
            )
            return next_state

        if relation_by_code:
            if selected_relation_code not in relation_by_code:
                selected_relation_code = next(iter(relation_by_code.keys()))
            selected_relation = relation_by_code[selected_relation_code]
            relation_details = self._graph_call(
                state["tenant_id"],
                state["session_id"],
                state["turn_id"],
                state.get("trace_id"),
                "graph.get_object_property_details",
                {"objectPropertyCodes": [selected_relation_code]},
                "planning",
            )
            selected_relation_detail = (relation_details or [None])[0] or {}
            selected_relation["_detail"] = selected_relation_detail
            next_state["candidate_capabilities"] = []
            next_state["selected_capability"] = {}
            next_state["selected_capability_detail"] = {}
            next_state["selected_object_property"] = selected_relation
            next_state["selected_object_property_detail"] = selected_relation_detail
            next_state["plan_state"] = {
                **(state.get("plan_state") or {}),
                "execution_decision": {
                    "action": "execute_object_property",
                    "object_property_code": selected_relation_code,
                    "reason": str(decision.get("reason") or ""),
                },
            }
            self.trace_service.emit(
                session_id=state["session_id"],
                turn_id=state["turn_id"],
                step="planning",
                event_type="task_planned",
                payload={"task_count": 1, "selected_object_property_code": selected_relation_code},
                trace_id=state.get("trace_id"),
                tenant_id=state["tenant_id"],
            )
            return next_state

        next_state["status"] = "waiting_clarification"
        next_state["clarification_question"] = {
            "tenant_id": state["tenant_id"],
            "type": "execution_target_missing",
            "question": "未能确定可执行的 capability 或 object_property，请补充目标。",
        }
        return next_state

    def _node_execute(self, state: dict) -> dict:
        next_state = dict(state)
        selected_capability = state.get("selected_capability") or {}
        selected_object_property = state.get("selected_object_property") or {}
        top_ontology = state.get("top_ontology") or {}
        ontology_id = top_ontology.get("class_id")
        if not ontology_id:
            next_state["status"] = "waiting_clarification"
            next_state["clarification_question"] = {
                "tenant_id": state["tenant_id"],
                "type": "ontology_id_missing",
                "question": "目标本体缺少实体映射信息，请先确认本体配置。",
            }
            return next_state

        if not selected_capability and not selected_object_property:
            next_state["status"] = "waiting_clarification"
            next_state["clarification_question"] = {
                "tenant_id": state["tenant_id"],
                "type": "task_planning_empty",
                "question": "未生成可执行任务，请补充更具体的执行目标。",
            }
            return next_state

        task_type = "capability" if selected_capability else "object_property"
        selected_resource = selected_capability if selected_capability else selected_object_property
        resource_code = str(selected_resource.get("code") or "").strip()
        resource_name = selected_resource.get("name")
        task_payload = {
            "resource_code": resource_code,
            "resource_name": resource_name,
            "ontology_id": ontology_id,
            "ontology_name": top_ontology.get("name"),
            "ontology_code": top_ontology.get("code"),
        }
        if task_type == "capability":
            task_payload["capability_code"] = resource_code
            task_payload["capability_name"] = resource_name
        else:
            task_payload["object_property_code"] = resource_code
            task_payload["object_property_name"] = resource_name
        task = self.repo.create_task(
            session_id=state["session_id"],
            turn_id=state["turn_id"],
            task_type=task_type,
            task_payload=task_payload,
            status="pending",
        )

        selected_task = {
            "task_id": task.id,
            "task_type": task.task_type,
            "status": task.status,
            "payload": task.task_payload,
        }

        attribute_catalog = self._build_attribute_catalog(state["tenant_id"], ontology_id)
        execution_context = {
            "tenant_id": state["tenant_id"],
            "session_id": state["session_id"],
            "turn_id": state["turn_id"],
            "trace_id": state.get("trace_id"),
            "query": state.get("query"),
            "intent": state.get("intent") or {},
            "top_ontology": top_ontology,
            "class_id": ontology_id,
            "attribute_catalog": attribute_catalog,
            "selection": selected_resource,
            "selection_detail": (
                state.get("selected_capability_detail") if task_type == "capability" else state.get("selected_object_property_detail")
            )
            or {},
            "llm_json_decision": self._llm_json_decision,
            "mcp_data_call": self._mcp_data_call,
            "resolve_ontology": lambda ontology_code: self._resolve_ontology(state["tenant_id"], ontology_code),
            "build_attribute_catalog": lambda class_id: self._build_attribute_catalog(state["tenant_id"], class_id),
        }
        if task_type == "object_property":
            relation_detail = execution_context["selection_detail"] or {}
            target_codes = []
            for item in (relation_detail.get("domain") or []) + (relation_detail.get("range") or []):
                code = str((item or {}).get("code") or "").strip()
                if code:
                    target_codes.append(code)
            target_codes = list(dict.fromkeys(target_codes))
            target_catalogs = {}
            for code in target_codes:
                target = self._resolve_ontology(state["tenant_id"], code)
                if not target:
                    continue
                target_catalogs[code] = self._build_attribute_catalog(state["tenant_id"], target["class_id"])
            execution_context["target_attribute_catalogs"] = target_catalogs

        execution_result = (
            self.capability_executor.execute(execution_context)
            if task_type == "capability"
            else self.object_property_executor.execute(execution_context)
        )
        if task_type == "object_property":
            target_ontology = execution_result.get("target_ontology")
            if target_ontology:
                selected_task["payload"]["target_ontology"] = target_ontology

        task_obj = self.repo.get_task_by_id(task.id)
        if task_obj:
            self.repo.update_task(task_obj, {"status": "completed"})
        selected_task["status"] = "completed"

        self.trace_service.emit(
            session_id=state["session_id"],
            turn_id=state["turn_id"],
            step="executing",
            event_type="task_executed",
            payload={
                "task_id": selected_task["task_id"],
                "task_type": selected_task["task_type"],
                "selected_resource": selected_task["payload"],
                "mode": "langgraph",
                "data_mode": execution_result["execution_mode"],
            },
            trace_id=state.get("trace_id"),
            tenant_id=state["tenant_id"],
        )
        next_state["created_tasks"] = [selected_task]
        next_state["selected_task"] = selected_task
        next_state["data_execution"] = execution_result["data_execution"]
        next_state["data_mode"] = execution_result["execution_mode"]
        next_state["plan_state"] = {
            **(state.get("plan_state") or {}),
            "executor": {
                "type": execution_result["executor_type"],
                "plan": execution_result.get("executor_plan") or {},
                "data_request": execution_result.get("data_request") or {},
            },
        }
        return next_state

    def _build_summary(
        self,
        tenant_id: str,
        query: str,
        top_ontology: dict,
        selected_task: dict,
        session_id: str | None = None,
        turn_id: int | None = None,
        trace_id: str | None = None,
    ) -> str:
        runtime_cfg = self.tenant_llm_service.get_runtime_config(tenant_id)

        def _audit_callback(event_type: str, payload: dict) -> None:
            if not session_id:
                return
            self.trace_service.emit(
                session_id=session_id,
                turn_id=turn_id,
                step="llm",
                event_type=event_type,
                payload=payload or {},
                trace_id=trace_id,
                tenant_id=tenant_id,
            )

        try:
            return LangChainLLMClient.summarize_with_context(
                runtime_cfg=runtime_cfg,
                query=query,
                ontology=top_ontology,
                selected_task=selected_task,
                audit_callback=_audit_callback,
            )
        except Exception as exc:
            if session_id:
                self.trace_service.emit(
                    session_id=session_id,
                    turn_id=turn_id,
                    step="llm",
                    event_type="llm_response_received",
                    payload={
                        "task": "summary_generation",
                        "error": str(exc),
                        "fallback_used": False,
                    },
                    trace_id=trace_id,
                    tenant_id=tenant_id,
                )
            raise AppError(ErrorCodes.INTERNAL, f"llm summary failed: {exc}")

    def _node_finalize(self, state: dict) -> dict:
        next_state = dict(state)
        top_ontology = state.get("top_ontology") or {}
        selected_task = state.get("selected_task", {})

        model_output = {
            "summary": self._build_summary(
                tenant_id=state["tenant_id"],
                query=state["query"],
                top_ontology=top_ontology,
                selected_task=selected_task,
                session_id=state["session_id"],
                turn_id=state["turn_id"],
                trace_id=state.get("trace_id"),
            ),
            "selected_ontology": top_ontology,
            "selected_task": selected_task.get("payload", selected_task),
            "candidate_attributes": state.get("candidate_attributes") or [],
            "orchestration_framework": "langgraph",
            "llm_framework": "langchain",
            "data_execution_mode": state.get("data_mode"),
            "data_execution": state.get("data_execution"),
            "planning": state.get("plan_state") or {},
        }

        llm_bundle = self.tenant_llm_service.get_runtime_provider_bundle(state["tenant_id"])
        model_output["llm_route"] = {
            "provider": llm_bundle["provider"],
            "model": llm_bundle["model"],
            "has_fallback": llm_bundle["fallback"] is not None,
        }
        next_state["status"] = "completed"
        next_state["model_output"] = model_output
        return next_state

    @staticmethod
    def _route_general(state: dict) -> str:
        status = state.get("status")
        if status in {"waiting_clarification", "waiting_confirmation"}:
            return status
        return "continue"

    @staticmethod
    def _route_after_inspect(state: dict) -> str:
        status = state.get("status")
        if status == "waiting_clarification":
            return "waiting_clarification"
        return "continue"

    def _get_compiled_graph(self):
        if self._compiled_graph is not None:
            return self._compiled_graph

        builder = StateGraph(dict)
        builder.add_node("understand_intent", self._node_understand_intent)
        builder.add_node("discover_candidates", self._node_discover_candidates)
        builder.add_node("select_anchor_ontologies", self._node_select_anchor_ontologies)
        builder.add_node("inspect_ontology", self._node_inspect_ontology)
        builder.add_node("execute", self._node_execute)
        builder.add_node("finalize", self._node_finalize)

        builder.set_entry_point("understand_intent")
        builder.add_edge("understand_intent", "discover_candidates")
        builder.add_conditional_edges(
            "discover_candidates",
            self._route_general,
            {
                "waiting_clarification": END,
                "waiting_confirmation": END,
                "continue": "select_anchor_ontologies",
            },
        )
        builder.add_conditional_edges(
            "select_anchor_ontologies",
            self._route_general,
            {
                "waiting_clarification": END,
                "waiting_confirmation": END,
                "continue": "inspect_ontology",
            },
        )
        builder.add_conditional_edges(
            "inspect_ontology",
            self._route_after_inspect,
            {
                "waiting_clarification": END,
                "continue": "execute",
            },
        )
        builder.add_conditional_edges(
            "execute",
            self._route_general,
            {
                "waiting_clarification": END,
                "waiting_confirmation": END,
                "continue": "finalize",
            },
        )
        builder.add_edge("finalize", END)

        self._compiled_graph = builder.compile()
        return self._compiled_graph

    def _build_waiting_response(self, session_id: str, pending, status: str):
        key = "confirmation" if status == "waiting_confirmation" else "clarification"
        question = pending.question_json
        return {
            "session_id": session_id,
            "status": status,
            key: {
                "clarification_id": pending.id,
                "question": question,
            },
            "clarification": {
                "clarification_id": pending.id,
                "question": question,
            },
        }

    def run_session(
        self,
        tenant_id: str,
        session_id: str,
        user_input: str | None = None,
        trace_id: str | None = None,
    ):
        session = self.repo.get_session(tenant_id=tenant_id, session_id=session_id)
        if not session:
            raise AppError(ErrorCodes.NOT_FOUND, "reasoning session not found")

        pending_clarification = self.repo.latest_pending_clarification(session_id)
        if pending_clarification:
            question_type = (pending_clarification.question_json or {}).get("type")
            status = "waiting_confirmation" if question_type == "traversal_confirmation" else "waiting_clarification"
            return self._build_waiting_response(session.id, pending_clarification, status)

        latest_turn = self.repo.latest_turn(session_id)
        if not latest_turn:
            raise AppError(ErrorCodes.NOT_FOUND, "reasoning turn not found")

        if user_input:
            latest_turn = self.repo.create_turn(
                session_id=session_id,
                user_input=user_input,
                turn_no=self.repo.next_turn_no(session_id),
                status="created",
            )

        self.repo.update_session_status(session, "running")
        self.repo.update_turn(latest_turn, {"status": "understanding"})

        try:
            traversal_state = self._read_latest_context_value(session_id, "traversal_state", ["session"])
            if not traversal_state:
                traversal_state = {
                    "depth": 0,
                    "max_depth": 2,
                    "branch_budget": 3,
                    "visited_ontology_codes": [],
                }

            resume_target = str(traversal_state.get("approved_target_ontology_code") or "").strip()

            init_state = {
                "tenant_id": tenant_id,
                "session_id": session_id,
                "turn_id": latest_turn.id,
                "query": latest_turn.user_input.strip(),
                "trace_id": trace_id,
                "status": "running",
                "intent": {},
                "candidate_attributes": [],
                "ontology_candidates": [],
                "top_ontology": {},
                "selected_ontology_detail": {},
                "candidate_capabilities": [],
                "created_tasks": [],
                "selected_task": {},
                "selected_capability": {},
                "selected_capability_detail": {},
                "selected_object_property": {},
                "selected_object_property_detail": {},
                "data_execution": None,
                "data_mode": None,
                "model_output": {},
                "clarification_question": None,
                "pending_traversal": None,
                "plan_state": {},
                "traversal_state": traversal_state,
                "resume_target_ontology_code": resume_target,
            }

            final_state = self._get_compiled_graph().invoke(init_state)

            if final_state.get("status") in {"waiting_clarification", "waiting_confirmation"}:
                waiting_status = final_state["status"]
                question_json = final_state.get("clarification_question") or {
                    "tenant_id": tenant_id,
                    "type": "unknown",
                    "question": "当前任务需要更多信息，请补充说明。",
                }
                clarification = self._create_waiting_clarification(
                    tenant_id=tenant_id,
                    session_id=session_id,
                    turn_id=latest_turn.id,
                    question_json=question_json,
                    trace_id=trace_id,
                    waiting_status=waiting_status,
                )

                if waiting_status == "waiting_confirmation":
                    traversal_state = dict(final_state.get("traversal_state") or traversal_state)
                    pending = final_state.get("pending_traversal") or {}
                    traversal_state["pending_traversal"] = pending
                    self.context_service.write(session_id, "session", "traversal_state", traversal_state)

                self.db.commit()
                return self._build_waiting_response(session_id, clarification, waiting_status)

            model_output = final_state.get("model_output") or {}
            self.repo.update_turn(
                latest_turn,
                {
                    "status": "completed",
                    "model_output": model_output,
                },
            )
            self.repo.update_session_status(session, "completed", ended=True)

            top_ontology = final_state.get("top_ontology") or {}
            self.context_service.write(
                session_id,
                "session",
                "selected_ontology",
                {
                    "class_id": top_ontology.get("class_id"),
                    "name": top_ontology.get("name"),
                    "code": top_ontology.get("code"),
                },
            )
            self.context_service.write(
                session_id,
                "artifact",
                "latest_result",
                model_output,
            )
            self.context_service.write(
                session_id,
                "session",
                "plan_state",
                final_state.get("plan_state") or {},
            )

            next_traversal_state = dict(final_state.get("traversal_state") or traversal_state)
            next_traversal_state.pop("approved_target_ontology_code", None)
            next_traversal_state.pop("pending_traversal", None)
            self.context_service.write(session_id, "session", "traversal_state", next_traversal_state)

            self.trace_service.emit(
                session_id=session_id,
                turn_id=latest_turn.id,
                step="completed",
                event_type="session_completed",
                payload={"turn_id": latest_turn.id},
                trace_id=trace_id,
                tenant_id=tenant_id,
            )
            self.db.commit()

            return {
                "session_id": session.id,
                "status": "completed",
                "turn": {
                    "turn_id": latest_turn.id,
                    "turn_no": latest_turn.turn_no,
                    "status": "completed",
                },
                "result": model_output,
                "tasks": final_state.get("created_tasks") or [],
            }
        except AppError:
            self.repo.update_turn(latest_turn, {"status": "failed"})
            self.repo.update_session_status(session, "failed", ended=True)
            self.trace_service.emit(
                session_id=session.id,
                turn_id=latest_turn.id,
                step="failed",
                event_type="session_failed",
                payload={"error": "app_error"},
                trace_id=trace_id,
                tenant_id=tenant_id,
            )
            self.db.commit()
            raise
        except Exception as exc:
            self.repo.update_turn(latest_turn, {"status": "failed"})
            self.repo.update_session_status(session, "failed", ended=True)
            self.trace_service.emit(
                session_id=session.id,
                turn_id=latest_turn.id,
                step="failed",
                event_type="session_failed",
                payload={"error": str(exc)},
                trace_id=trace_id,
                tenant_id=tenant_id,
            )
            self.db.commit()
            raise AppError(ErrorCodes.INTERNAL, f"reasoning execution failed: {exc}")

    def clarify(self, tenant_id: str, session_id: str, answer: dict, trace_id: str | None = None):
        session = self.repo.get_session(tenant_id=tenant_id, session_id=session_id)
        if not session:
            raise AppError(ErrorCodes.NOT_FOUND, "reasoning session not found")

        clarification = self.repo.latest_pending_clarification(session_id)
        if not clarification:
            raise AppError(ErrorCodes.VALIDATION, "no pending clarification")

        self.repo.answer_clarification(clarification, answer)
        turn = self.repo.get_turn(clarification.turn_id) if clarification.turn_id else self.repo.latest_turn(session_id)

        question = clarification.question_json or {}
        question_type = question.get("type")
        answer_type = str((answer or {}).get("type") or "").strip()
        if turn:
            if question_type == "traversal_confirmation" or answer_type == "confirmation":
                decision = str((answer or {}).get("decision") or "approve").strip().lower()
                note = str((answer or {}).get("note") or (answer or {}).get("text") or "").strip()
                merged_input = f"{turn.user_input}\n[confirmation] decision={decision}; note={note}"
                self.repo.update_turn(turn, {"user_input": merged_input, "status": "created"})

                traversal_state = self._read_latest_context_value(session_id, "traversal_state", ["session"]) or {}
                visited = list(traversal_state.get("visited_ontology_codes") or [])
                from_code = question.get("from_ontology_code")
                to_code = question.get("to_ontology_code")
                if from_code and from_code not in visited:
                    visited.append(from_code)
                if decision == "approve" and to_code and to_code not in visited:
                    visited.append(to_code)
                traversal_state["visited_ontology_codes"] = visited
                traversal_state["depth"] = int(question.get("next_depth") or traversal_state.get("depth") or 0)
                traversal_state["branch_budget"] = max(int(traversal_state.get("branch_budget") or 3) - 1, 0)
                traversal_state.pop("pending_traversal", None)
                if decision == "approve":
                    traversal_state["approved_target_ontology_code"] = to_code
                else:
                    traversal_state.pop("approved_target_ontology_code", None)
                self.context_service.write(session_id, "session", "traversal_state", traversal_state)

                self.trace_service.emit(
                    session_id=session_id,
                    turn_id=turn.id if turn else None,
                    step="clarification",
                    event_type="traversal_confirmation_received",
                    payload={"clarification_id": clarification.id, "decision": decision, "to": to_code},
                    trace_id=trace_id,
                    tenant_id=tenant_id,
                )
                if decision == "approve":
                    self.trace_service.emit(
                        session_id=session_id,
                        turn_id=turn.id if turn else None,
                        step="planning",
                        event_type="traversal_step_completed",
                        payload={"from": from_code, "to": to_code},
                        trace_id=trace_id,
                        tenant_id=tenant_id,
                    )
            else:
                merged_input = f"{turn.user_input}\n[clarification] {answer}"
                self.repo.update_turn(turn, {"user_input": merged_input, "status": "created"})

        self.repo.update_session_status(session, "created")
        self.trace_service.emit(
            session_id=session_id,
            turn_id=turn.id if turn else None,
            step="clarification",
            event_type="recovery_triggered",
            payload={"clarification_id": clarification.id},
            trace_id=trace_id,
            tenant_id=tenant_id,
        )
        self.db.commit()

        return {
            "session_id": session_id,
            "status": "created",
            "clarification": {
                "clarification_id": clarification.id,
                "status": "answered",
            },
        }

    def list_trace(self, tenant_id: str, session_id: str):
        session = self.repo.get_session(tenant_id=tenant_id, session_id=session_id)
        if not session:
            raise AppError(ErrorCodes.NOT_FOUND, "reasoning session not found")
        return {"items": self.trace_service.list_events(session_id)}

    def cancel(self, tenant_id: str, session_id: str, reason: str | None, trace_id: str | None = None):
        session = self.repo.get_session(tenant_id=tenant_id, session_id=session_id)
        if not session:
            raise AppError(ErrorCodes.NOT_FOUND, "reasoning session not found")

        self.repo.update_session_status(session, "cancelled", ended=True)
        latest_turn = self.repo.latest_turn(session_id)
        self.trace_service.emit(
            session_id=session_id,
            turn_id=latest_turn.id if latest_turn else None,
            step="cancel",
            event_type="session_failed",
            payload={"reason": reason or "cancelled_by_user"},
            trace_id=trace_id,
            tenant_id=tenant_id,
        )
        self.db.commit()
        return {"session_id": session_id, "status": "cancelled"}
