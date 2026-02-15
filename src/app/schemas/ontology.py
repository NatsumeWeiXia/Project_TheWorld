from typing import Literal

from pydantic import BaseModel, Field


class CreateClassRequest(BaseModel):
    code: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=256)
    description: str | None = None


class UpdateClassRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    status: int | None = None


class CreateInheritanceRequest(BaseModel):
    parent_class_id: int


class CreateGlobalAttributeRequest(BaseModel):
    code: str
    name: str
    data_type: Literal["string", "int", "date", "boolean", "json"]
    required: bool = False
    description: str | None = None
    constraints_json: dict = Field(default_factory=dict)


class CreateObjectPropertyRequest(BaseModel):
    code: str
    name: str
    description: str | None = None
    skill_md: str | None = None
    relation_type: Literal["transform", "query"]
    domain_class_ids: list[int] = Field(min_length=1)
    range_class_ids: list[int] = Field(min_length=1)
    mcp_bindings_json: list = Field(default_factory=list)


class CreateGlobalCapabilityRequest(BaseModel):
    code: str
    name: str
    description: str | None = None
    skill_md: str | None = None
    input_schema: dict
    output_schema: dict
    mcp_bindings_json: list = Field(default_factory=list)


class BindDataAttributesRequest(BaseModel):
    data_attribute_ids: list[int] = Field(min_length=1)


class BindCapabilitiesRequest(BaseModel):
    capability_ids: list[int] = Field(min_length=1)


class UpsertClassTableBindingRequest(BaseModel):
    table_name: str
    table_schema: str | None = None
    table_catalog: str | None = None
    config_json: dict = Field(default_factory=dict)


class UpsertClassFieldMappingRequest(BaseModel):
    mappings: list[dict] = Field(
        min_length=1,
        description="[{\"data_attribute_id\": 1, \"field_name\": \"id_card\"}]",
    )


class OWLValidateRequest(BaseModel):
    strict: bool = False
