from typing import Literal

from pydantic import BaseModel, Field


class DataQueryRequest(BaseModel):
    class_id: int
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=500)
    filters: list[dict] = Field(default_factory=list)
    sort_field: str | None = None
    sort_order: Literal["asc", "desc"] = "asc"


class GroupMetric(BaseModel):
    agg: Literal["count", "sum", "avg", "min", "max"]
    field: str | None = None
    alias: str | None = None


class GroupAnalysisRequest(BaseModel):
    class_id: int
    group_by: list[str] = Field(min_length=1)
    metrics: list[GroupMetric] = Field(default_factory=lambda: [GroupMetric(agg="count", alias="count")])
    filters: list[dict] = Field(default_factory=list)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=500)
    sort_by: str | None = None
    sort_order: Literal["asc", "desc"] = "desc"
