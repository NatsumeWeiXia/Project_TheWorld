from pydantic import BaseModel, Field


class TenantLLMConfigUpsertRequest(BaseModel):
    provider: str = Field(min_length=1, max_length=32)
    model: str = Field(min_length=1, max_length=128)
    api_key: str | None = Field(default=None, min_length=1, max_length=4096)
    base_url: str | None = Field(default=None, max_length=512)
    timeout_ms: int = Field(default=30000, ge=1000, le=180000)
    enable_thinking: bool = True
    fallback_provider: str | None = Field(default=None, max_length=32)
    fallback_model: str | None = Field(default=None, max_length=128)
    extra_json: dict = Field(default_factory=dict)
    status: int = Field(default=1, ge=0, le=1)


class TenantLLMConfigVerifyRequest(BaseModel):
    provider: str | None = Field(default=None, max_length=32)
    model: str | None = Field(default=None, max_length=128)
    api_key: str | None = Field(default=None, max_length=4096)
    base_url: str | None = Field(default=None, max_length=512)
    timeout_ms: int | None = Field(default=None, ge=1000, le=180000)
    extra_json: dict = Field(default_factory=dict)


class LangfuseConfigUpdateRequest(BaseModel):
    enabled: bool | None = None
    public_key: str | None = Field(default=None, max_length=512)
    secret_key: str | None = Field(default=None, max_length=512)
    host: str | None = Field(default=None, max_length=1024)
    environment: str | None = Field(default=None, max_length=64)
    release: str | None = Field(default=None, max_length=128)
    audit_payload_max_chars: int | None = Field(default=None, ge=2000, le=200000)


class TenantSearchConfigUpdateRequest(BaseModel):
    word_w_sparse: float | None = Field(default=None, ge=0)
    word_w_dense: float | None = Field(default=None, ge=0)
    sentence_w_sparse: float | None = Field(default=None, ge=0)
    sentence_w_dense: float | None = Field(default=None, ge=0)
    top_n: int | None = Field(default=None, ge=1, le=500)
    score_gap: float | None = Field(default=None, ge=0)
    relative_diff: float | None = Field(default=None, ge=0)
    backfill_batch_size: int | None = Field(default=None, ge=1, le=5000)
