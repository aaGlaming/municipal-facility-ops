from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    mysql_url: str = Field("mysql+pymysql://municipal:municipal_dev@mysql:3306/municipal_ops", validation_alias="MYSQL_URL")
    chroma_persist_directory: str = Field("./.chroma", validation_alias="CHROMA_PERSIST_DIRECTORY")
    llm_base_url: str = Field("http://localhost:11434/v1", validation_alias="LLM_BASE_URL")
    llm_api_key: str = Field("replace_me", validation_alias="LLM_API_KEY")
    llm_model: str = Field("replace_me", validation_alias="LLM_MODEL")
    embedding_model: str = Field("replace_me", validation_alias="EMBEDDING_MODEL")
    open311_base_url: str = Field("https://data.cityofnewyork.us", validation_alias="OPEN311_BASE_URL")
    agent_max_model_calls: int = Field(8, ge=1, le=8, validation_alias="AGENT_MAX_MODEL_CALLS")
    agent_max_tool_calls: int = Field(16, ge=1, le=16, validation_alias="AGENT_MAX_TOOL_CALLS")
    agent_timeout_seconds: int = Field(90, ge=1, le=900, validation_alias="AGENT_TIMEOUT_SECONDS")
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)


@lru_cache
def get_settings() -> Settings:
    return Settings()
