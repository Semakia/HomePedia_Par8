"""Application settings, loaded from environment / .env.

Single source of truth for runtime configuration. Mirrors the contract in
`.env.dist`. Import the cached `get_settings()` accessor, never instantiate
`Settings` directly, so the .env is parsed only once per process.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Global ---
    environment: str = "development"
    log_level: str = "INFO"

    # --- API ---
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_cors_origins: str = "http://localhost:3000,http://localhost:8501"

    # --- PostgreSQL (Gold) ---
    database_url: str = (
        "postgresql+psycopg2://homepedia:homepedia@localhost:5432/homepedia"
    )
    # Schema holding the Gold tables. Configurable so the API can target a Gold
    # DB that namespaces them differently (e.g. "market" on the remote dev VPS).
    gold_schema: str = "gold"

    # --- Redis (cache) ---
    redis_url: str = "redis://localhost:6379/0"

    # --- Object storage (Bronze) ---
    s3_endpoint_url: str = "http://localhost:9000"
    aws_access_key_id: str = "minioadmin"
    aws_secret_access_key: str = "minioadmin"
    aws_region: str = "eu-west-3"
    s3_bronze_bucket: str = "homepedia-bronze"
    s3_silver_bucket: str = "homepedia-silver"
    s3_gold_bucket: str = "homepedia-gold"

    @field_validator("gold_schema")
    @classmethod
    def _safe_schema(cls, v: str) -> str:
        # Interpolated into SQL (cannot be bound), so reject anything that is
        # not a bare identifier to keep it injection-safe.
        if not v.isidentifier():
            raise ValueError(f"gold_schema must be a valid SQL identifier, got {v!r}")
        return v

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.api_cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide cached Settings instance."""
    return Settings()
