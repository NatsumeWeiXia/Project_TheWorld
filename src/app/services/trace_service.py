from src.app.repositories.reasoning_repo import ReasoningRepository
from src.app.services.observability.langfuse_sink import LangfuseSink


ALLOWED_EVENTS = {
    "intent_parsed",
    "attributes_matched",
    "ontologies_located",
    "task_planned",
    "task_executed",
    "clarification_asked",
    "recovery_triggered",
    "session_completed",
    "session_failed",
    "session_started",
    "mcp_call_requested",
    "mcp_call_completed",
    "llm_prompt_sent",
    "llm_response_received",
}


class TraceService:
    def __init__(self, db):
        self.repo = ReasoningRepository(db)
        self.langfuse = LangfuseSink()

    def emit(
        self,
        session_id: str,
        turn_id: int | None,
        step: str,
        event_type: str,
        payload: dict,
        trace_id: str | None,
        tenant_id: str | None = None,
    ):
        raw_event_type = event_type
        if event_type not in ALLOWED_EVENTS:
            event_type = "session_failed"
            payload = {
                "reason": "unknown_event_type",
                "raw_event_type": raw_event_type,
                **(payload or {}),
            }
        self.repo.create_trace_event(
            session_id=session_id,
            turn_id=turn_id,
            step=step,
            event_type=event_type,
            payload_json=payload or {},
            trace_id=trace_id,
        )
        self.langfuse.emit_event(
            tenant_id=tenant_id,
            session_id=session_id,
            trace_id=trace_id,
            step=step,
            event_type=event_type,
            payload=payload or {},
        )

    def list_events(self, session_id: str):
        items = self.repo.list_trace_events(session_id)
        return [
            {
                "id": item.id,
                "session_id": item.session_id,
                "turn_id": item.turn_id,
                "step": item.step,
                "event_type": item.event_type,
                "payload": item.payload_json,
                "trace_id": item.trace_id,
                "created_at": item.created_at.isoformat(),
            }
            for item in items
        ]
