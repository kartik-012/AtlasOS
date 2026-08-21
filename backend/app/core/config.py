"""
AtlasOS Application Configuration.

Centralizes all environment-driven settings using Pydantic v2 BaseSettings.
Settings are loaded from environment variables and .env files, validated at
startup, and cached for the application lifetime.

Why pydantic-settings:
  - Type-safe configuration with automatic validation at startup.
  - Fails fast on misconfiguration instead of silently using wrong values.
  - Single source of truth for all configurable parameters.
  - Supports .env files for local development, env vars for production.

Design decision — @lru_cache for get_settings():
  Settings are immutable after application startup. Caching avoids
  re-parsing environment variables on every dependency injection call.
  This is safe because settings never change during a process lifecycle.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All settings have sensible defaults for local development.
    Production deployments MUST override security-sensitive values
    (SECRET_KEY, JWT_SECRET_KEY, POSTGRES_PASSWORD, etc.) via
    environment variables or a secrets manager.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",  # Ignore unexpected env vars without raising errors
    )

    # --------------------------------------------------------------------------
    # PostgreSQL
    # --------------------------------------------------------------------------
    DATABASE_URL: str = "postgresql+asyncpg://atlas:atlas_secret@localhost:5432/atlasos"
    DATABASE_URL_SYNC: str = "postgresql+psycopg2://atlas:atlas_secret@localhost:5432/atlasos"

    # --------------------------------------------------------------------------
    # Redis
    # --------------------------------------------------------------------------
    REDIS_URL: str = "redis://localhost:6379/0"

    # --------------------------------------------------------------------------
    # Qdrant
    # --------------------------------------------------------------------------
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_GRPC_PORT: int = 6334

    @property
    def QDRANT_URL(self) -> str:
        """Construct the Qdrant REST URL from host and port."""
        return f"http://{self.QDRANT_HOST}:{self.QDRANT_PORT}"

    # --------------------------------------------------------------------------
    # Security & Authentication
    # --------------------------------------------------------------------------
    SECRET_KEY: str = "change-me-to-a-random-64-char-string"
    JWT_SECRET_KEY: str = "change-me-to-another-random-string"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --------------------------------------------------------------------------
    # Embedding Provider
    # Abstraction supports: bge-large, openai, gemini, voyageai, jina, custom
    # --------------------------------------------------------------------------
    EMBEDDING_PROVIDER: str = "bge-large"
    EMBEDDING_MODEL: str = "BAAI/bge-large-en-v1.5"
    EMBEDDING_DIMENSION: int = 1024
    EMBEDDING_SERVICE_URL: str = "http://inference:8080"
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    VOYAGEAI_API_KEY: str = ""
    JINA_API_KEY: str = ""
    CUSTOM_EMBEDDING_URL: str = ""

    # --------------------------------------------------------------------------
    # NLI (Natural Language Inference) Service
    # --------------------------------------------------------------------------
    NLI_SERVICE_URL: str = "http://inference:8080"
    NLI_MODEL: str = "roberta-large-mnli"

    @property
    def INFERENCE_SERVICE_URL(self) -> str:
        """Construct the base AI Inference Service URL."""
        return self.EMBEDDING_SERVICE_URL

    # --------------------------------------------------------------------------
    # Celery Task Queue
    # --------------------------------------------------------------------------
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # --------------------------------------------------------------------------
    # CORS
    # --------------------------------------------------------------------------
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # --------------------------------------------------------------------------
    # Application
    # --------------------------------------------------------------------------
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # --------------------------------------------------------------------------
    # OAuth2 Providers
    # --------------------------------------------------------------------------
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""

    @field_validator("EMBEDDING_PROVIDER")
    @classmethod
    def validate_embedding_provider(cls, v: str) -> str:
        """Validate that the embedding provider is one of the supported options."""
        allowed = {"bge-large", "openai", "gemini", "voyageai", "jina", "custom"}
        if v not in allowed:
            msg = f"Invalid EMBEDDING_PROVIDER '{v}'. Must be one of: {', '.join(sorted(allowed))}"
            raise ValueError(msg)
        return v

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate the runtime environment identifier."""
        allowed = {"development", "staging", "production", "testing"}
        if v not in allowed:
            msg = f"Invalid ENVIRONMENT '{v}'. Must be one of: {', '.join(sorted(allowed))}"
            raise ValueError(msg)
        return v

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate the log level string."""
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in allowed:
            msg = f"Invalid LOG_LEVEL '{v}'. Must be one of: {', '.join(sorted(allowed))}"
            raise ValueError(msg)
        return upper

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.ENVIRONMENT == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.ENVIRONMENT == "production"

    @property
    def is_testing(self) -> bool:
        """Check if running in testing mode."""
        return self.ENVIRONMENT == "testing"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return the cached application settings singleton.

    Uses @lru_cache to ensure settings are parsed from environment
    variables exactly once per process lifetime. This is safe because
    environment variables are immutable after process start.

    Returns:
        Settings: The validated application settings instance.
    """
    return Settings()
