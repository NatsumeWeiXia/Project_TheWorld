from typing import Literal

from pydantic import BaseModel, Field


class UpsertClassKnowledgeRequest(BaseModel):
    overview: str
    constraints_desc: str | None = None
    relation_desc: str | None = None
    capability_desc: str | None = None
    object_property_skill_desc: str | None = None
    capability_skill_desc: str | None = None


class UpsertAttributeKnowledgeRequest(BaseModel):
    definition: str
    synonyms_json: list[str] = Field(default_factory=list)
    constraints_desc: str | None = None


class CreateRelationTemplateRequest(BaseModel):
    intent_desc: str | None = None
    few_shot_examples: list = Field(default_factory=list)
    json_schema: dict = Field(default_factory=dict)
    skill_md: str | None = None
    prompt_template: str
    template_schema: dict
    mcp_slots_json: list = Field(default_factory=list)


class CreateCapabilityTemplateRequest(BaseModel):
    intent_desc: str | None = None
    few_shot_examples: list = Field(default_factory=list)
    json_schema: dict = Field(default_factory=dict)
    skill_md: str | None = None
    prompt_template: str
    template_schema: dict
    mcp_slots_json: list = Field(default_factory=list)


class CreateFewshotRequest(BaseModel):
    scope_type: Literal["class", "attr", "relation", "capability"]
    scope_id: int
    input_text: str
    output_text: str
    tags_json: list = Field(default_factory=list)
