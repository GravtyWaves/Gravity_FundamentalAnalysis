"""
================================================================================
FILE IDENTITY CARD (شناسنامه فایل)
================================================================================
File Path:           app/core/config.py
Author:              Gravity Fundamental Analysis Team
Team ID:             FA-001
Created Date:        2025-01-10
Last Modified:       2025-01-18
Version:             1.0.0
Purpose:             Configuration management using Pydantic Settings
                     Loads and validates all environment variables for the application

Dependencies:        pydantic>=2.5.0, pydantic-settings>=2.1.0

Related Files:       .env (environment variables)
                     app/main.py (settings consumer)
                     app/core/database.py (database config)
                     app/core/redis_client.py (Redis config)
                     app/core/celery_config.py (Celery config)

Complexity:          3/10
Lines of Code:       113
Test Coverage:       0% (needs unit tests for validators)
Performance Impact:  LOW (loaded once at startup, cached with lru_cache)
Time Spent:          2 hours
Cost:                $960 (2 × $480/hr)
Review Status:       Production
Notes:               - Uses Pydantic BaseSettings for type validation
                     - Automatic .env file loading
                     - Field validators for allowed_origins parsing
                     - Cached with @lru_cache for performance
                     - Includes: app, database, Redis, API, security, logging configs
                     - Environment-aware (development/staging/production)
================================================================================
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

    # Database (OPTIONAL - service works without it)
    database_url: str | None = Field(None, description="PostgreSQL database URL (optional)")
    database_enabled: bool = Field(True, description="Enable database features")
    database_pool_size: int = 20
    database_max_overflow: int = 10
    use_in_memory_storage: bool = Field(False, description="Use in-memory storage when DB unavailable")

    # Redis (OPTIONAL)
    redis_url: str = "redis://localhost:6379/0"
    redis_password: str | None = None
    redis_enabled: bool = Field(True, description="Enable Redis caching")

    # Celery (scheduled tasks)
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    default_tenant_id: str = "default_tenant"

    # Security
    secret_key: str = Field(..., description="Secret key for JWT encoding")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # CORS
    allowed_origins: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    # External Microservices URLs (OPTIONAL - for data fetching)
    market_data_service_url: str | None = Field(None, description="Market Data Service URL")
    company_info_service_url: str | None = Field(None, description="Company Info Service URL")
    industry_benchmarks_service_url: str | None = Field(None, description="Industry Benchmarks Service URL")
    economic_indicators_service_url: str | None = Field(None, description="Economic Indicators Service URL")
    news_sentiment_service_url: str | None = Field(None, description="News & Sentiment Service URL")

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | List[str]) -> List[str]:
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    # Make external service URLs accessible as uppercase attributes for backward compatibility
    @property
    def MARKET_DATA_SERVICE_URL(self) -> str | None:
        return self.market_data_service_url
    
    @property
    def COMPANY_INFO_SERVICE_URL(self) -> str | None:
        return self.company_info_service_url
    
    @property
    def INDUSTRY_BENCHMARKS_SERVICE_URL(self) -> str | None:
        return self.industry_benchmarks_service_url
    
    @property
    def ECONOMIC_INDICATORS_SERVICE_URL(self) -> str | None:
        return self.economic_indicators_service_url
    
    @property
    def NEWS_SENTIMENT_SERVICE_URL(self) -> str | None:
        return self.news_sentiment_service_url

    # Kafka
    kafka_brokers: str = "localhost:9092"
    kafka_topic_prefix: str = "fundamental_analysis"

    # External APIs
    market_data_api_url: str | None = None
    market_data_api_key: str | None = None

    # Data Collection Microservice
    data_collection_service_url: str = Field(
        default="http://localhost:8001",
        description="URL of the Data Collection microservice"
    )
    data_collection_api_key: str | None = Field(
        default=None,
        description="API key for Data Collection microservice"
    )
    data_collection_timeout: float = Field(
        default=30.0,
        description="Timeout for Data Collection API calls in seconds"
    )

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
