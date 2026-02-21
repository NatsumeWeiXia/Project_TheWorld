import uuid
from datetime import datetime

from sqlalchemy import and_, desc, func, select
from sqlalchemy.orm import Session

from src.app.infra.db import models


class ReasoningRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_session(self, tenant_id: str, status: str = "created"):
        obj = models.ReasoningSession(id=f"rs_{uuid.uuid4().hex}", tenant_id=tenant_id, status=status)
        self.db.add(obj)
        self.db.flush()
        return obj

    def get_session(self, tenant_id: str, session_id: str):
        stmt = select(models.ReasoningSession).where(
            and_(
                models.ReasoningSession.tenant_id == tenant_id,
                models.ReasoningSession.id == session_id,
            )
        )
        return self.db.scalar(stmt)

    def update_session_status(self, session_obj: models.ReasoningSession, status: str, ended: bool = False):
        session_obj.status = status
        if ended:
            session_obj.ended_at = datetime.utcnow()
        self.db.flush()
        return session_obj

    def create_turn(self, session_id: str, user_input: str, turn_no: int, status: str = "created"):
        obj = models.ReasoningTurn(
            session_id=session_id,
            turn_no=turn_no,
            user_input=user_input,
            status=status,
        )
        self.db.add(obj)
        self.db.flush()
        return obj

    def get_turn(self, turn_id: int):
        stmt = select(models.ReasoningTurn).where(models.ReasoningTurn.id == turn_id)
        return self.db.scalar(stmt)

    def update_turn(self, turn_obj: models.ReasoningTurn, payload: dict):
        for key, value in payload.items():
            setattr(turn_obj, key, value)
        self.db.flush()
        return turn_obj

    def latest_turn(self, session_id: str):
        stmt = (
            select(models.ReasoningTurn)
            .where(models.ReasoningTurn.session_id == session_id)
            .order_by(desc(models.ReasoningTurn.turn_no))
            .limit(1)
        )
        return self.db.scalar(stmt)

    def next_turn_no(self, session_id: str) -> int:
        stmt = select(func.max(models.ReasoningTurn.turn_no)).where(models.ReasoningTurn.session_id == session_id)
        value = self.db.scalar(stmt)
        return int(value or 0) + 1

    def create_task(self, session_id: str, turn_id: int, task_type: str, task_payload: dict, status: str = "pending"):
        obj = models.ReasoningTask(
            session_id=session_id,
            turn_id=turn_id,
            task_type=task_type,
            task_payload=task_payload,
            status=status,
        )
        self.db.add(obj)
        self.db.flush()
        return obj

    def list_tasks(self, session_id: str, turn_id: int | None = None):
        stmt = select(models.ReasoningTask).where(models.ReasoningTask.session_id == session_id)
        if turn_id is not None:
            stmt = stmt.where(models.ReasoningTask.turn_id == turn_id)
        stmt = stmt.order_by(models.ReasoningTask.id.asc())
        return list(self.db.scalars(stmt))

    def get_task_by_id(self, task_id: int):
        stmt = select(models.ReasoningTask).where(models.ReasoningTask.id == task_id)
        return self.db.scalar(stmt)

    def update_task(self, task_obj: models.ReasoningTask, payload: dict):
        for key, value in payload.items():
            setattr(task_obj, key, value)
        self.db.flush()
        return task_obj

    def set_context(self, session_id: str, scope: str, key: str, value_json: dict):
        obj = models.ReasoningContext(
            session_id=session_id,
            scope=scope,
            key=key,
            value_json=value_json,
        )
        self.db.add(obj)
        self.db.flush()
        return obj

    def list_context(self, session_id: str, scopes: list[str] | None = None):
        stmt = select(models.ReasoningContext).where(models.ReasoningContext.session_id == session_id)
        if scopes:
            stmt = stmt.where(models.ReasoningContext.scope.in_(scopes))
        stmt = stmt.order_by(models.ReasoningContext.id.asc())
        return list(self.db.scalars(stmt))

    def create_trace_event(
        self,
        session_id: str,
        turn_id: int | None,
        step: str,
        event_type: str,
        payload_json: dict,
        trace_id: str | None,
    ):
        obj = models.ReasoningTraceEvent(
            session_id=session_id,
            turn_id=turn_id,
            step=step,
            event_type=event_type,
            payload_json=payload_json,
            trace_id=trace_id,
        )
        self.db.add(obj)
        self.db.flush()
        return obj

    def list_trace_events(self, session_id: str):
        stmt = (
            select(models.ReasoningTraceEvent)
            .where(models.ReasoningTraceEvent.session_id == session_id)
            .order_by(models.ReasoningTraceEvent.id.asc())
        )
        return list(self.db.scalars(stmt))

    def create_clarification(self, session_id: str, turn_id: int | None, question_json: dict):
        obj = models.ReasoningClarification(
            session_id=session_id,
            turn_id=turn_id,
            question_json=question_json,
            status="pending",
        )
        self.db.add(obj)
        self.db.flush()
        return obj

    def latest_pending_clarification(self, session_id: str):
        stmt = (
            select(models.ReasoningClarification)
            .where(
                and_(
                    models.ReasoningClarification.session_id == session_id,
                    models.ReasoningClarification.status == "pending",
                )
            )
            .order_by(desc(models.ReasoningClarification.id))
            .limit(1)
        )
        return self.db.scalar(stmt)

    def answer_clarification(self, clarification_obj: models.ReasoningClarification, answer_json: dict):
        clarification_obj.answer_json = answer_json
        clarification_obj.status = "answered"
        self.db.flush()
        return clarification_obj
