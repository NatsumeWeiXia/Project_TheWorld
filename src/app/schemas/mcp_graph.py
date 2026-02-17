from pydantic import BaseModel, Field


class MCPGraphToolCallRequest(BaseModel):
    name: str
    arguments: dict = Field(default_factory=dict)

