from functools import lru_cache
from urllib.parse import urlparse

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    mysql_url: str = Field(
        "mysql+pymysql://municipal:municipal_dev@mysql:3306/municipal_ops", validation_alias="MYSQL_URL"
    )
    chroma_persist_directory: str = Field("./.chroma", validation_alias="CHROMA_PERSIST_DIRECTORY")
    chroma_host: str = Field("127.0.0.1", validation_alias="CHROMA_HOST")
    chroma_port: int = Field(8001, ge=1, le=65535, validation_alias="CHROMA_PORT")
    llm_base_url: str = Field("http://localhost:11434/v1", validation_alias="LLM_BASE_URL")
    llm_api_key: str = Field("replace_me", validation_alias="LLM_API_KEY")
    llm_model: str = Field("replace_me", validation_alias="LLM_MODEL")
    embedding_model: str = Field("replace_me", validation_alias="EMBEDDING_MODEL")
    open311_base_url: str = Field("https://data.cityofnewyork.us", validation_alias="OPEN311_BASE_URL")
    agent_max_model_calls: int = Field(8, ge=1, le=8, validation_alias="AGENT_MAX_MODEL_CALLS")
    agent_max_tool_calls: int = Field(16, ge=1, le=16, validation_alias="AGENT_MAX_TOOL_CALLS")
    agent_timeout_seconds: int = Field(90, ge=1, le=900, validation_alias="AGENT_TIMEOUT_SECONDS")
    log_level: str = "INFO"
    cors_origins: str = Field("http://localhost:5173", validation_alias="CORS_ORIGINS")
    db_connect_timeout_seconds: int = Field(5, ge=1, le=60, validation_alias="DB_CONNECT_TIMEOUT_SECONDS")
    db_pool_recycle_seconds: int = Field(1800, ge=60, le=86400, validation_alias="DB_POOL_RECYCLE_SECONDS")
    auth_secret: str = Field("dev-only-change-this-secret", validation_alias="AUTH_SECRET")
    auth_token_ttl_seconds: int = Field(900, ge=60, le=86400, validation_alias="AUTH_TOKEN_TTL_SECONDS")
    auth_bootstrap_username: str = Field("", validation_alias="AUTH_BOOTSTRAP_USERNAME")
    auth_bootstrap_password: str = Field("", validation_alias="AUTH_BOOTSTRAP_PASSWORD")
    auth_bootstrap_roles: str = Field("admin", validation_alias="AUTH_BOOTSTRAP_ROLES")
    auth_bootstrap_permissions: str = Field("*", validation_alias="AUTH_BOOTSTRAP_PERMISSIONS")
    rag_storage_directory: str = Field("uploads/documents", validation_alias="RAG_STORAGE_DIRECTORY")
    rag_max_upload_bytes: int = Field(
        10 * 1024 * 1024, ge=1024, le=100 * 1024 * 1024, validation_alias="RAG_MAX_UPLOAD_BYTES"
    )
    rag_chunk_target_tokens: int = Field(800, ge=20, le=4000, validation_alias="RAG_CHUNK_TARGET_TOKENS")
    rag_chunk_overlap_tokens: int = Field(120, ge=0, le=1000, validation_alias="RAG_CHUNK_OVERLAP_TOKENS")

    model_config = SettingsConfigDict(
        env_file=("backend/.env", ".env"), extra="ignore", case_sensitive=False, populate_by_name=True
    )

    @field_validator("mysql_url")
    @classmethod
    def validate_mysql_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme not in {"mysql+pymysql", "mysql+mysqlconnector"} or not parsed.hostname or not parsed.path:
            raise ValueError("MYSQL_URL must be a valid mysql+pymysql URL")
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def llm_configured(self) -> bool:
        return self.llm_api_key not in {"", "replace_me"} and self.llm_model not in {"", "replace_me"}


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
