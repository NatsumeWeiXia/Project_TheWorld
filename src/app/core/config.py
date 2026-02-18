from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TW_", env_file=".env", extra="ignore")

    app_name: str = "Project_TheWorld M1"
    api_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://akyuu:akyuu@192.168.1.6:5432/gensokyo"
    entity_database_url: str | None = None
    entity_database_name: str = "memento"
    redis_url: str = "redis://:akyuu@192.168.1.6:6379/0"
    auth_enabled: bool = True
    embedding_service_url: str = "http://192.168.1.6:8081"
    embedding_timeout_seconds: float = 8.0
    embedding_fallback_dim: int = 16


settings = Settings()
