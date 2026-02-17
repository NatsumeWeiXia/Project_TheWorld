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
    data_type: Literal["string", "int", "date", "boolean", "json", "array"]
    required: bool = False
    description: str | None = None
    constraints_json: dict = Field(default_factory=dict)


class UpdateGlobalAttributeRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    data_type: Literal["string", "int", "date", "boolean", "json", "array"] | None = None
    required: bool | None = None
    constraints_json: dict | None = None


class CreateObjectPropertyRequest(BaseModel):
    code: str
    name: str
    description: str | None = None
    skill_md: str | None = None
    domain_class_ids: list[int] = Field(min_length=1)
    range_class_ids: list[int] = Field(min_length=1)


class UpdateObjectPropertyRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    skill_md: str | None = None
    domain_class_ids: list[int] | None = Field(default=None, min_length=1)
    range_class_ids: list[int] | None = Field(default=None, min_length=1)


class CreateGlobalCapabilityRequest(BaseModel):
    code: str
    name: str
    description: str | None = None
    skill_md: str | None = None
    input_schema: dict
    output_schema: dict
    domain_groups: list[list[int]] = Field(default_factory=list)


class UpdateGlobalCapabilityRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    skill_md: str | None = None
    input_schema: dict | None = None
    output_schema: dict | None = None
    domain_groups: list[list[int]] | None = None


class BindDataAttributesRequest(BaseModel):
    data_attribute_ids: list[int] = Field(default_factory=list)


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


class QueryEntityDataRequest(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)
    filters: list[dict] = Field(default_factory=list)
    sort_field: str | None = None
    sort_order: Literal["asc", "desc"] = "asc"


class CreateEntityDataRequest(BaseModel):
    values: dict = Field(default_factory=dict)


class UpdateEntityDataRequest(BaseModel):
    values: dict = Field(default_factory=dict)
