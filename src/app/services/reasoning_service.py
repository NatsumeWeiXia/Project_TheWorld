from __future__ import annotations

from src.app.core.errors import AppError, ErrorCodes
from src.app.repositories.reasoning_repo import ReasoningRepository
from src.app.services.context_service import ContextService
from src.app.services.llm.langchain_client import LangChainLLMClient
from src.app.services.mcp_data_service import MCPDataService
from src.app.services.mcp_metadata_service import MCPMetadataService
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
        self.mcp_service = MCPMetadataService(db)
        self.mcp_data_service = MCPDataService(db)
        self.context_service = ContextService(db)
        self.trace_service = TraceService(db)
        self.tenant_llm_service = TenantLLMConfigService(db)
        self._compiled_graph = None

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
    ):
        clarification = self.repo.create_clarification(
            session_id=session_id,
            turn_id=turn_id,
            question_json=question_json,
        )
        session = self.repo.get_session(tenant_id=tenant_id, session_id=session_id)
        if session:
            self.repo.update_session_status(session, "waiting_clarification")

        turn = self.repo.get_turn(turn_id)
        if turn:
            self.repo.update_turn(turn, {"status": "waiting_clarification"})

        self.trace_service.emit(
            session_id=session_id,
            turn_id=turn_id,
            step="clarification",
            event_type="clarification_asked",
            payload=question_json,
            trace_id=trace_id,
            tenant_id=tenant_id,
        )
        return clarification

    def _node_parse_intent(self, state: dict) -> dict:
        self.trace_service.emit(
            session_id=state["session_id"],
            turn_id=state["turn_id"],
            step="understanding",
            event_type="intent_parsed",
            payload={"query": state["query"]},
            trace_id=state.get("trace_id"),
            tenant_id=state["tenant_id"],
        )
        return dict(state)

    def _node_match_attributes(self, state: dict) -> dict:
        next_state = dict(state)
        self.trace_service.emit(
            session_id=state["session_id"],
            turn_id=state["turn_id"],
            step="attributes",
            event_type="mcp_call_requested",
            payload={
                "method": "mcp.metadata.attributes_match",
                "arguments": {
                    "query": state["query"],
                    "top_k": 10,
                    "page": 1,
                    "page_size": 10,
                },
            },
            trace_id=state.get("trace_id"),
            tenant_id=state["tenant_id"],
        )
        match_result = self.mcp_service.match_attributes(
            tenant_id=state["tenant_id"],
            query=state["query"],
            top_k=10,
            page=1,
            page_size=10,
        )
        attributes = match_result.get("items", [])
        self.trace_service.emit(
            session_id=state["session_id"],
            turn_id=state["turn_id"],
            step="attributes",
            event_type="mcp_call_completed",
            payload={
                "method": "mcp.metadata.attributes_match",
                "result_count": len(attributes),
                "result": match_result,
            },
            trace_id=state.get("trace_id"),
            tenant_id=state["tenant_id"],
        )
        self.trace_service.emit(
            session_id=state["session_id"],
            turn_id=state["turn_id"],
            step="attributes",
            event_type="attributes_matched",
            payload={"count": len(attributes)},
            trace_id=state.get("trace_id"),
            tenant_id=state["tenant_id"],
        )
        if not attributes:
            next_state["status"] = "waiting_clarification"
            next_state["clarification_question"] = {
                "tenant_id": state["tenant_id"],
                "type": "no_attribute_match",
                "question": "未匹配到数据属性，请补充更具体的业务关键词或字段名。",
            }
            next_state["attributes"] = []
            return next_state
        next_state["attributes"] = attributes
        return next_state

    def _node_locate_ontologies(self, state: dict) -> dict:
        next_state = dict(state)
        attr_ids = [item["attribute_id"] for item in (state.get("attributes") or [])[:5]]
        self.trace_service.emit(
            session_id=state["session_id"],
            turn_id=state["turn_id"],
            step="locating",
            event_type="mcp_call_requested",
            payload={
                "method": "mcp.metadata.ontologies_by_attributes",
                "arguments": {"attribute_ids": attr_ids, "top_k": 5},
            },
            trace_id=state.get("trace_id"),
            tenant_id=state["tenant_id"],
        )
        ontology_result = self.mcp_service.ontologies_by_attributes(
            tenant_id=state["tenant_id"],
            attribute_ids=attr_ids,
            top_k=5,
        )
        ontologies = ontology_result.get("items", [])
        self.trace_service.emit(
            session_id=state["session_id"],
            turn_id=state["turn_id"],
            step="locating",
            event_type="mcp_call_completed",
            payload={
                "method": "mcp.metadata.ontologies_by_attributes",
                "result_count": len(ontologies),
                "result": ontology_result,
            },
            trace_id=state.get("trace_id"),
            tenant_id=state["tenant_id"],
        )
        self.trace_service.emit(
            session_id=state["session_id"],
            turn_id=state["turn_id"],
            step="locating",
            event_type="ontologies_located",
            payload={"count": len(ontologies)},
            trace_id=state.get("trace_id"),
            tenant_id=state["tenant_id"],
        )
        if not ontologies:
            next_state["status"] = "waiting_clarification"
            next_state["clarification_question"] = {
                "tenant_id": state["tenant_id"],
                "type": "no_ontology_match",
                "question": "已识别数据属性，但未定位到可执行本体，请补充业务对象。",
            }
            next_state["ontologies"] = []
            return next_state
        next_state["ontologies"] = ontologies
        next_state["top_ontology"] = ontologies[0]
        return next_state

    def _node_plan_tasks(self, state: dict) -> dict:
        next_state = dict(state)
        top_ontology = state["top_ontology"]
        self.trace_service.emit(
            session_id=state["session_id"],
            turn_id=state["turn_id"],
            step="planning",
            event_type="mcp_call_requested",
            payload={
                "method": "mcp.metadata.ontology_detail",
                "arguments": {"class_id": top_ontology["class_id"]},
            },
            trace_id=state.get("trace_id"),
            tenant_id=state["tenant_id"],
        )
        ontology_detail = self.mcp_service.ontology_detail(
            tenant_id=state["tenant_id"],
            class_id=top_ontology["class_id"],
        )
        candidate_capabilities = ontology_detail.get("capabilities", [])
        self.trace_service.emit(
            session_id=state["session_id"],
            turn_id=state["turn_id"],
            step="planning",
            event_type="mcp_call_completed",
            payload={
                "method": "mcp.metadata.ontology_detail",
                "result_capability_count": len(candidate_capabilities),
                "result": ontology_detail,
            },
            trace_id=state.get("trace_id"),
            tenant_id=state["tenant_id"],
        )
        if not candidate_capabilities:
            next_state["status"] = "waiting_clarification"
            next_state["clarification_question"] = {
                "tenant_id": state["tenant_id"],
                "type": "no_capability_match",
                "class_id": top_ontology["class_id"],
                "question": "已定位本体但未匹配到能力，请确认目标动作（查询/分析/转换）。",
            }
            next_state["candidate_capabilities"] = []
            return next_state

        created_tasks = []
        for capability in candidate_capabilities[:5]:
            task = self.repo.create_task(
                session_id=state["session_id"],
                turn_id=state["turn_id"],
                task_type="capability",
                task_payload={
                    "capability_id": capability["id"],
                    "capability_name": capability["name"],
                    "ontology_id": top_ontology["class_id"],
                    "ontology_name": top_ontology["name"],
                },
                status="pending",
            )
            created_tasks.append(
                {
                    "task_id": task.id,
                    "task_type": task.task_type,
                    "status": task.status,
                    "payload": task.task_payload,
                }
            )

        self.trace_service.emit(
            session_id=state["session_id"],
            turn_id=state["turn_id"],
            step="planning",
            event_type="task_planned",
            payload={"task_count": len(created_tasks)},
            trace_id=state.get("trace_id"),
            tenant_id=state["tenant_id"],
        )
        next_state["created_tasks"] = created_tasks
        next_state["candidate_capabilities"] = candidate_capabilities
        return next_state

    def _node_execute(self, state: dict) -> dict:
        next_state = dict(state)
        tasks = state.get("created_tasks") or []
        if not tasks:
            next_state["status"] = "waiting_clarification"
            next_state["clarification_question"] = {
                "tenant_id": state["tenant_id"],
                "type": "task_planning_empty",
                "question": "未生成可执行任务，请补充更具体的执行目标。",
            }
            return next_state

        selected_task = tasks[0]
        task_obj = self.repo.get_task_by_id(selected_task["task_id"])
        if task_obj:
            self.repo.update_task(task_obj, {"status": "completed"})
            selected_task["status"] = "completed"

        ontology_id = selected_task["payload"]["ontology_id"]
        query_text = (state.get("query") or "").lower()
        use_group_analysis = any(token in query_text for token in ["分组", "统计", "group", "count", "sum", "avg", "平均"])

        data_execution = None
        if use_group_analysis:
            ontology_detail = self.mcp_service.ontology_detail(state["tenant_id"], ontology_id)
            first_mapping = ((ontology_detail.get("field_mappings") or [None])[0] or {})
            group_field = first_mapping.get("field_name")
            if not group_field:
                raise AppError(ErrorCodes.VALIDATION, "group analysis requires field mapping")
            mcp_payload = {
                "class_id": ontology_id,
                "group_by": [group_field],
                "metrics": [{"agg": "count", "alias": "count"}],
                "filters": [],
                "page": 1,
                "page_size": 20,
                "sort_by": "count",
                "sort_order": "desc",
            }
            self.trace_service.emit(
                session_id=state["session_id"],
                turn_id=state["turn_id"],
                step="executing",
                event_type="mcp_call_requested",
                payload={"method": "mcp.data.group_analysis", "arguments": mcp_payload},
                trace_id=state.get("trace_id"),
                tenant_id=state["tenant_id"],
            )
            data_execution = self.mcp_data_service.group_analysis(
                tenant_id=state["tenant_id"],
                payload=mcp_payload,
            )
            self.trace_service.emit(
                session_id=state["session_id"],
                turn_id=state["turn_id"],
                step="executing",
                event_type="mcp_call_completed",
                payload={"method": "mcp.data.group_analysis", "result": data_execution},
                trace_id=state.get("trace_id"),
                tenant_id=state["tenant_id"],
            )
            execution_mode = "group-analysis"
        else:
            mcp_payload = {
                "class_id": ontology_id,
                "filters": [],
                "page": 1,
                "page_size": 20,
                "sort_field": None,
                "sort_order": "asc",
            }
            self.trace_service.emit(
                session_id=state["session_id"],
                turn_id=state["turn_id"],
                step="executing",
                event_type="mcp_call_requested",
                payload={"method": "mcp.data.query", "arguments": mcp_payload},
                trace_id=state.get("trace_id"),
                tenant_id=state["tenant_id"],
            )
            data_execution = self.mcp_data_service.query(
                tenant_id=state["tenant_id"],
                payload=mcp_payload,
            )
            self.trace_service.emit(
                session_id=state["session_id"],
                turn_id=state["turn_id"],
                step="executing",
                event_type="mcp_call_completed",
                payload={"method": "mcp.data.query", "result": data_execution},
                trace_id=state.get("trace_id"),
                tenant_id=state["tenant_id"],
            )
            execution_mode = "query"

        self.trace_service.emit(
            session_id=state["session_id"],
            turn_id=state["turn_id"],
            step="executing",
            event_type="task_executed",
            payload={
                "task_id": selected_task["task_id"],
                "task_type": selected_task["task_type"],
                "selected_capability": selected_task["payload"],
                "mode": "langgraph",
                "data_mode": execution_mode,
            },
            trace_id=state.get("trace_id"),
            tenant_id=state["tenant_id"],
        )
        next_state["selected_task"] = selected_task
        next_state["data_execution"] = data_execution
        next_state["data_mode"] = execution_mode
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
        except Exception:
            return "M2 推理链路已完成属性匹配、本体定位、任务规划和执行。"

    def _node_finalize(self, state: dict) -> dict:
        next_state = dict(state)
        top_ontology = state.get("top_ontology") or {}
        selected_task = state.get("selected_task", {})
        attributes = state.get("attributes") or []

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
            "candidate_attributes": attributes,
            "orchestration_framework": "langgraph",
            "llm_framework": "langchain",
            "data_execution_mode": state.get("data_mode"),
            "data_execution": state.get("data_execution"),
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

    def _use_clarification_path(self, state: dict) -> str:
        return "need_clarification" if state.get("status") == "waiting_clarification" else "continue"

    def _get_compiled_graph(self):
        if self._compiled_graph is not None:
            return self._compiled_graph

        builder = StateGraph(dict)
        builder.add_node("parse_intent", self._node_parse_intent)
        builder.add_node("match_attributes", self._node_match_attributes)
        builder.add_node("locate_ontologies", self._node_locate_ontologies)
        builder.add_node("plan_tasks", self._node_plan_tasks)
        builder.add_node("execute", self._node_execute)
        builder.add_node("finalize", self._node_finalize)

        builder.set_entry_point("parse_intent")
        builder.add_edge("parse_intent", "match_attributes")
        builder.add_conditional_edges(
            "match_attributes",
            self._use_clarification_path,
            {"need_clarification": END, "continue": "locate_ontologies"},
        )
        builder.add_conditional_edges(
            "locate_ontologies",
            self._use_clarification_path,
            {"need_clarification": END, "continue": "plan_tasks"},
        )
        builder.add_conditional_edges(
            "plan_tasks",
            self._use_clarification_path,
            {"need_clarification": END, "continue": "execute"},
        )
        builder.add_conditional_edges(
            "execute",
            self._use_clarification_path,
            {"need_clarification": END, "continue": "finalize"},
        )
        builder.add_edge("finalize", END)

        self._compiled_graph = builder.compile()
        return self._compiled_graph

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
            return {
                "session_id": session.id,
                "status": "waiting_clarification",
                "clarification": {
                    "clarification_id": pending_clarification.id,
                    "question": pending_clarification.question_json,
                },
            }

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

        self.repo.update_session_status(session, "understanding")
        self.repo.update_turn(latest_turn, {"status": "understanding"})

        try:
            init_state = {
                "tenant_id": tenant_id,
                "session_id": session_id,
                "turn_id": latest_turn.id,
                "query": latest_turn.user_input.strip(),
                "trace_id": trace_id,
                "status": "running",
                "attributes": [],
                "ontologies": [],
                "top_ontology": {},
                "candidate_capabilities": [],
                "created_tasks": [],
                "selected_task": {},
                "data_execution": None,
                "data_mode": None,
                "model_output": {},
                "clarification_question": None,
            }

            final_state = self._get_compiled_graph().invoke(init_state)

            if final_state.get("status") == "waiting_clarification":
                clarification = self._create_waiting_clarification(
                    tenant_id=tenant_id,
                    session_id=session_id,
                    turn_id=latest_turn.id,
                    question_json=final_state.get("clarification_question")
                    or {
                        "tenant_id": tenant_id,
                        "type": "unknown",
                        "question": "当前任务需要更多信息，请补充说明。",
                    },
                    trace_id=trace_id,
                )
                self.db.commit()
                return {
                    "session_id": session_id,
                    "status": "waiting_clarification",
                    "clarification": {
                        "clarification_id": clarification.id,
                        "question": clarification.question_json,
                    },
                }

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
                    "matched_attributes": top_ontology.get("matched_attributes", []),
                },
            )
            self.context_service.write(
                session_id,
                "artifact",
                "latest_result",
                model_output,
            )

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
        if turn:
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
