from pydantic import BaseModel, Field


class AttributeMatchRequest(BaseModel):
    query: str
    filters: dict = Field(default_factory=dict)
    top_k: int = 20
    page: int = 1
    page_size: int = 20


class OntologiesByAttributesRequest(BaseModel):
    attribute_ids: list[int]
    top_k: int = 20
