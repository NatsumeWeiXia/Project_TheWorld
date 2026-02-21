from src.app.core.errors import AppError, ErrorCodes
from src.app.repositories.reasoning_repo import ReasoningRepository


ALLOWED_SCOPES = {"global", "session", "local", "artifact"}


class ContextService:
    def __init__(self, db):
        self.db = db
        self.repo = ReasoningRepository(db)

    def write(self, session_id: str, scope: str, key: str, value: dict):
        if scope not in ALLOWED_SCOPES:
            raise AppError(ErrorCodes.VALIDATION, "invalid context scope")
        return self.repo.set_context(session_id, scope, key, value)

    def read(self, session_id: str, scopes: list[str] | None = None):
        scopes = scopes or ["session", "artifact"]
        for scope in scopes:
            if scope not in ALLOWED_SCOPES:
                raise AppError(ErrorCodes.VALIDATION, "invalid context scope")
        items = self.repo.list_context(session_id, scopes)
        return [
            {
                "id": item.id,
                "scope": item.scope,
                "key": item.key,
                "value": item.value_json,
                "version": item.version,
                "created_at": item.created_at.isoformat(),
            }
            for item in items
        ]
