from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Glossy API"
    app_env: str = "local"
    api_v1_prefix: str = "/api/v1"
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:8788"]
    )

    database_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DATABASE_URL", "SUPABASE_DB_URL"),
    )
    database_ssl: bool = True
    database_ssl_mode: str = "require"
    db_min_pool_size: int = 1
    db_max_pool_size: int = 5
    db_statement_cache_size: int = 0

    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    max_input_chars: int = 3000
    max_document_chars: int = 10000
    max_image_bytes: int = 4 * 1024 * 1024
    max_term_suggestions: int = 8

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("database_ssl_mode")
    @classmethod
    def validate_database_ssl_mode(cls, value: str) -> str:
        allowed = {"disable", "allow", "prefer", "require", "verify-ca", "verify-full"}
        if value not in allowed:
            raise ValueError(f"database_ssl_mode must be one of {sorted(allowed)}")
        return value

    @field_validator("openai_api_key", mode="before")
    @classmethod
    def normalize_openai_api_key(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned or cleaned == "replace-with-openai-api-key":
            return None
        return cleaned


@lru_cache
def get_settings() -> Settings:
    return Settings()
