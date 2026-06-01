"""
Central configuration for bubble (pydantic-settings).

All secrets come from environment / .env. Never hardcode.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class BubbleSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # LLM
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    xai_api_key: str | None = Field(default=None, alias="XAI_API_KEY")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")

    # Neo4j
    neo4j_uri: str = Field(default="bolt://localhost:7687", alias="NEO4J_URI")
    neo4j_user: str = Field(default="neo4j", alias="NEO4J_USER")
    neo4j_password: str = Field(
        default="change-this-secure-password-in-prod-123!", alias="NEO4J_PASSWORD"
    )
    neo4j_database: str = Field(default="neo4j", alias="NEO4J_DATABASE")

    # MinIO
    minio_endpoint: str = Field(default="localhost:9000", alias="MINIO_ENDPOINT")
    minio_access_key: str = Field(default="minioadmin", alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(default="minioadmin", alias="MINIO_SECRET_KEY")
    minio_bucket_raw: str = Field(default="bubble-raw", alias="MINIO_BUCKET_RAW")
    minio_secure: bool = Field(default=False, alias="MINIO_SECURE")

    # Postgres
    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_db: str = Field(default="bubble", alias="POSTGRES_DB")
    postgres_user: str = Field(default="bubble", alias="POSTGRES_USER")
    postgres_password: str = Field(default="change-this-too", alias="POSTGRES_PASSWORD")

    # Behavior
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO", alias="BUBBLE_LOG_LEVEL"
    )
    watchlist_ciks: list[str] = Field(
        default_factory=lambda: ["0000789019", "0001018724", "0001326801", "0001045810"],
        alias="BUBBLE_WATCHLIST_CIKS",
    )
    llm_adjudication_threshold: float = Field(
        default=0.75, alias="BUBBLE_LLM_ADJUDICATION_THRESHOLD", ge=0.0, le=1.0
    )
    max_llm_cost_per_run_usd: float = Field(default=25.0, alias="BUBBLE_MAX_LLM_COST_PER_RUN_USD")

    @field_validator("watchlist_ciks", mode="before")
    @classmethod
    def parse_ciks(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [c.strip() for c in v.split(",") if c.strip()]
        return v

    @property
    def has_llm_keys(self) -> bool:
        return bool(self.anthropic_api_key or self.xai_api_key or self.openai_api_key)


settings = BubbleSettings()

# Convenience re-exports
__all__ = ["BubbleSettings", "settings"]
