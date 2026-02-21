from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, SmallInteger, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.app.infra.db.base import Base


def now() -> datetime:
    return datetime.utcnow()


class OntologyClass(Base):
    __tablename__ = "ontology_class"
    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uk_ontology_class_tenant_code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    code: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    search_text: Mapped[str | None] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(JSON)
    status: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now, nullable=False)


class OntologyInheritance(Base):
    __tablename__ = "ontology_inheritance"
    __table_args__ = (UniqueConstraint("tenant_id", "parent_class_id", "child_class_id", name="uk_inherit"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    parent_class_id: Mapped[int] = mapped_column(ForeignKey("ontology_class.id"), nullable=False)
    child_class_id: Mapped[int] = mapped_column(ForeignKey("ontology_class.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, nullable=False)


class OntologyDataAttribute(Base):
    __tablename__ = "ontology_data_attribute"
    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uk_attr_tenant_code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    class_id: Mapped[int | None] = mapped_column(ForeignKey("ontology_class.id"))
    code: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    data_type: Mapped[str] = mapped_column(String(32), nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    constraints_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    search_text: Mapped[str | None] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now, nullable=False)


class OntologyRelation(Base):
    __tablename__ = "ontology_relation"
    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uk_relation_tenant_code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    source_class_id: Mapped[int | None] = mapped_column(ForeignKey("ontology_class.id"))
    target_class_id: Mapped[int | None] = mapped_column(ForeignKey("ontology_class.id"))
    code: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    search_text: Mapped[str | None] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(JSON)
    skill_md: Mapped[str | None] = mapped_column(Text)
    relation_type: Mapped[str] = mapped_column(String(32), nullable=False)
    mcp_bindings_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now, nullable=False)


class OntologyCapability(Base):
    __tablename__ = "ontology_capability"
    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uk_capability_tenant_code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    class_id: Mapped[int | None] = mapped_column(ForeignKey("ontology_class.id"))
    code: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    search_text: Mapped[str | None] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(JSON)
    skill_md: Mapped[str | None] = mapped_column(Text)
    input_schema: Mapped[dict] = mapped_column(JSON, nullable=False)
    output_schema: Mapped[dict] = mapped_column(JSON, nullable=False)
    mcp_bindings_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    domain_groups_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now, nullable=False)


class OntologyClassDataAttrRef(Base):
    __tablename__ = "ontology_class_data_attr_ref"
    __table_args__ = (UniqueConstraint("tenant_id", "class_id", "data_attribute_id", name="uk_class_attr_ref"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    class_id: Mapped[int] = mapped_column(ForeignKey("ontology_class.id"), nullable=False)
    data_attribute_id: Mapped[int] = mapped_column(ForeignKey("ontology_data_attribute.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, nullable=False)


class OntologyRelationDomainRef(Base):
    __tablename__ = "ontology_relation_domain_ref"
    __table_args__ = (UniqueConstraint("tenant_id", "relation_id", "class_id", name="uk_relation_domain_ref"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    relation_id: Mapped[int] = mapped_column(ForeignKey("ontology_relation.id"), nullable=False)
    class_id: Mapped[int] = mapped_column(ForeignKey("ontology_class.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, nullable=False)


class OntologyRelationRangeRef(Base):
    __tablename__ = "ontology_relation_range_ref"
    __table_args__ = (UniqueConstraint("tenant_id", "relation_id", "class_id", name="uk_relation_range_ref"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    relation_id: Mapped[int] = mapped_column(ForeignKey("ontology_relation.id"), nullable=False)
    class_id: Mapped[int] = mapped_column(ForeignKey("ontology_class.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, nullable=False)


class OntologyClassCapabilityRef(Base):
    __tablename__ = "ontology_class_capability_ref"
    __table_args__ = (UniqueConstraint("tenant_id", "class_id", "capability_id", name="uk_class_capability_ref"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    class_id: Mapped[int] = mapped_column(ForeignKey("ontology_class.id"), nullable=False)
    capability_id: Mapped[int] = mapped_column(ForeignKey("ontology_capability.id"), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, nullable=False)


class OntologyClassTableBinding(Base):
    __tablename__ = "ontology_class_table_binding"
    __table_args__ = (UniqueConstraint("tenant_id", "class_id", name="uk_class_table_binding"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    class_id: Mapped[int] = mapped_column(ForeignKey("ontology_class.id"), nullable=False)
    table_name: Mapped[str] = mapped_column(String(256), nullable=False)
    table_schema: Mapped[str | None] = mapped_column(String(128))
    table_catalog: Mapped[str | None] = mapped_column(String(128))
    config_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now, nullable=False)


class OntologyClassFieldMapping(Base):
    __tablename__ = "ontology_class_field_mapping"
    __table_args__ = (UniqueConstraint("tenant_id", "binding_id", "data_attribute_id", name="uk_field_mapping"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    binding_id: Mapped[int] = mapped_column(ForeignKey("ontology_class_table_binding.id"), nullable=False)
    data_attribute_id: Mapped[int] = mapped_column(ForeignKey("ontology_data_attribute.id"), nullable=False)
    field_name: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, nullable=False)


class OntologyExportTask(Base):
    __tablename__ = "ontology_export_task"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    export_format: Mapped[str] = mapped_column(String(16), nullable=False, default="ttl")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="completed")
    output_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, nullable=False)


class KnowledgeClass(Base):
    __tablename__ = "knowledge_class"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    class_id: Mapped[int] = mapped_column(ForeignKey("ontology_class.id"), nullable=False)
    overview: Mapped[str] = mapped_column(Text, nullable=False)
    constraints_desc: Mapped[str | None] = mapped_column(Text)
    relation_desc: Mapped[str | None] = mapped_column(Text)
    capability_desc: Mapped[str | None] = mapped_column(Text)
    object_property_skill_desc: Mapped[str | None] = mapped_column(Text)
    capability_skill_desc: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, nullable=False)


class KnowledgeAttribute(Base):
    __tablename__ = "knowledge_attribute"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    attribute_id: Mapped[int] = mapped_column(ForeignKey("ontology_data_attribute.id"), nullable=False)
    definition: Mapped[str] = mapped_column(Text, nullable=False)
    synonyms_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    constraints_desc: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class KnowledgeRelationTemplate(Base):
    __tablename__ = "knowledge_relation_template"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    relation_id: Mapped[int] = mapped_column(ForeignKey("ontology_relation.id"), nullable=False)
    prompt_template: Mapped[str] = mapped_column(Text, nullable=False)
    template_schema: Mapped[dict] = mapped_column(JSON, nullable=False)
    mcp_slots_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    intent_desc: Mapped[str | None] = mapped_column(Text)
    few_shot_examples: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    json_schema: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    skill_md: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class KnowledgeCapabilityTemplate(Base):
    __tablename__ = "knowledge_capability_template"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    capability_id: Mapped[int] = mapped_column(ForeignKey("ontology_capability.id"), nullable=False)
    prompt_template: Mapped[str] = mapped_column(Text, nullable=False)
    template_schema: Mapped[dict] = mapped_column(JSON, nullable=False)
    mcp_slots_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    intent_desc: Mapped[str | None] = mapped_column(Text)
    few_shot_examples: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    json_schema: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    skill_md: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class KnowledgeFewshotExample(Base):
    __tablename__ = "knowledge_fewshot_example"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    scope_type: Mapped[str] = mapped_column(String(16), nullable=False)
    scope_id: Mapped[int] = mapped_column(Integer, nullable=False)
    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    output_text: Mapped[str] = mapped_column(Text, nullable=False)
    tags_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, nullable=False)


class ReasoningSession(Base):
    __tablename__ = "reasoning_session"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="created")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now, nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime)


class ReasoningTurn(Base):
    __tablename__ = "reasoning_turn"
    __table_args__ = (UniqueConstraint("session_id", "turn_no", name="uk_reasoning_turn_session_no"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("reasoning_session.id"), nullable=False, index=True)
    turn_no: Mapped[int] = mapped_column(Integer, nullable=False)
    user_input: Mapped[str] = mapped_column(Text, nullable=False)
    model_output: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="created")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now, nullable=False)


class ReasoningTask(Base):
    __tablename__ = "reasoning_task"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("reasoning_session.id"), nullable=False, index=True)
    turn_id: Mapped[int] = mapped_column(ForeignKey("reasoning_turn.id"), nullable=False, index=True)
    task_type: Mapped[str] = mapped_column(String(64), nullable=False)
    task_payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now, nullable=False)


class ReasoningContext(Base):
    __tablename__ = "reasoning_context"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("reasoning_session.id"), nullable=False, index=True)
    scope: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    value_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, nullable=False)


class ReasoningTraceEvent(Base):
    __tablename__ = "reasoning_trace_event"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("reasoning_session.id"), nullable=False, index=True)
    turn_id: Mapped[int | None] = mapped_column(ForeignKey("reasoning_turn.id"), index=True)
    step: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    trace_id: Mapped[str | None] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, nullable=False)


class ReasoningClarification(Base):
    __tablename__ = "reasoning_clarification"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("reasoning_session.id"), nullable=False, index=True)
    turn_id: Mapped[int | None] = mapped_column(ForeignKey("reasoning_turn.id"), index=True)
    question_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    answer_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now, nullable=False)


class TenantLLMConfig(Base):
    __tablename__ = "tenant_llm_config"
    __table_args__ = (UniqueConstraint("tenant_id", name="uk_tenant_llm_config_tenant"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    api_key_cipher: Mapped[str] = mapped_column(Text, nullable=False)
    base_url: Mapped[str | None] = mapped_column(String(512))
    timeout_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=30000)
    enable_thinking: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    fallback_provider: Mapped[str | None] = mapped_column(String(32))
    fallback_model: Mapped[str | None] = mapped_column(String(128))
    extra_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    updated_by: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now, nullable=False)


class TenantRuntimeConfig(Base):
    __tablename__ = "tenant_runtime_config"
    __table_args__ = (UniqueConstraint("tenant_id", name="uk_tenant_runtime_config_tenant"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    config_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now, nullable=False)


class SystemRuntimeConfig(Base):
    __tablename__ = "system_runtime_config"
    __table_args__ = (UniqueConstraint("config_key", name="uk_system_runtime_config_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    config_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    config_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now, nullable=False)


class ActiveTenant(Base):
    __tablename__ = "active_tenant"
    __table_args__ = (UniqueConstraint("tenant_id", name="uk_active_tenant_tenant"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=now, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now, nullable=False)
