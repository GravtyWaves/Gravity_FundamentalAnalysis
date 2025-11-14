"""
Configuration management using Pydantic Settings.

All environment variables are loaded and validated here.
"""

from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Fundamental Analysis Microservice"
    app_version: str = "1.0.0"
    api_v1_prefix: str = "/api/v1"
    debug: bool = False
    environment: str = "development"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4
    reload: bool = False

    # Database
    database_url: str = Field(..., description="PostgreSQL database URL")
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_password: str | None = None

    # Security
    secret_key: str = Field(..., description="Secret key for JWT encoding")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # CORS
    allowed_origins: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | List[str]) -> List[str]:
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    # Kafka
    kafka_brokers: str = "localhost:9092"
    kafka_topic_prefix: str = "fundamental_analysis"

    # External APIs
    market_data_api_url: str | None = None
    market_data_api_key: str | None = None

    # Rate Limiting
    rate_limit_per_minute: int = 60

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # Multi-Tenancy
    enable_multi_tenancy: bool = True


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Returns:
        Settings: Application settings
    """
    return Settings()


# Convenience instance
settings = get_settings()
