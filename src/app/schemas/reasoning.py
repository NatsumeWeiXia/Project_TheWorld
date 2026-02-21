from pydantic import BaseModel, Field


class CreateReasoningSessionRequest(BaseModel):
    user_input: str = Field(min_length=1, max_length=8000)
    metadata: dict = Field(default_factory=dict)


class RunReasoningSessionRequest(BaseModel):
    user_input: str | None = Field(default=None, min_length=1, max_length=8000)


class ClarifyReasoningSessionRequest(BaseModel):
    answer: dict = Field(default_factory=dict)


class CancelReasoningSessionRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)
