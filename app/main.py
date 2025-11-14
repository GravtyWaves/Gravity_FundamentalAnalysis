"""
FastAPI main application entry point.

This module initializes the FastAPI app with all middleware, routers, and handlers.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import settings

# Configure structured logging
import logging

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer() if settings.log_format == "json"
        else structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        getattr(logging, settings.log_level.upper(), logging.INFO)
    ),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=False,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.

    Handles startup and shutdown events.
    """
    # Startup
    logger.info("application_startup", version=settings.app_version)

    yield

    # Shutdown
    logger.info("application_shutdown")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Comprehensive fundamental analysis microservice for financial markets",
    docs_url=f"{settings.api_v1_prefix}/docs",
    redoc_url=f"{settings.api_v1_prefix}/redoc",
    openapi_url=f"{settings.api_v1_prefix}/openapi.json",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add trusted host middleware (security)
if not settings.debug:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

# Include API routers
from app.api.v1.router import api_router

app.include_router(api_router, prefix=settings.api_v1_prefix)

# Register exception handlers
from app.core.exceptions import register_exception_handlers

register_exception_handlers(app)


@app.get("/health", tags=["Health"])
async def health_check() -> JSONResponse:
    """
    Health check endpoint.

    Returns:
        JSONResponse: Service health status
    """
    return JSONResponse(
        content={
            "status": "healthy",
            "service": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
        }
    )


@app.get("/health/ready", tags=["Health"])
async def readiness_check() -> JSONResponse:
    """
    Readiness check endpoint.

    Checks if the service is ready to accept traffic.
    Validates database, Redis connectivity, and ML model status.

    Returns:
        JSONResponse: Service readiness status with dependency checks
    """
    from app.core.database import engine
    from app.core.redis_client import get_redis_client
    from app.services.ml_weight_optimizer import MLWeightOptimizer
    from app.core.database import AsyncSessionLocal

    checks = {
        "database": "unknown",
        "redis": "unknown",
        "ml_model": "unknown",
    }

    # Check database connection
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        checks["database"] = "unhealthy"

    # Check Redis connection
    try:
        redis_client = await get_redis_client()
        await redis_client.ping()
        checks["redis"] = "healthy"
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        checks["redis"] = "unhealthy"

    # Check ML model status
    ml_metrics = None
    try:
        async with AsyncSessionLocal() as db:
            optimizer = MLWeightOptimizer(db, "default_tenant")
            await optimizer.load_model()
            ml_metrics = await optimizer.get_model_metrics()
            checks["ml_model"] = ml_metrics["status"]
    except Exception as e:
        logger.error(f"ML model health check failed: {e}")
        checks["ml_model"] = "error"

    all_healthy = (
        checks["database"] == "healthy" and 
        checks["redis"] == "healthy"
    )
    status_code = 200 if all_healthy else 503

    response_content = {
        "status": "ready" if all_healthy else "not_ready",
        "service": settings.app_name,
        "checks": checks,
    }
    
    # Include ML model metrics if available
    if ml_metrics:
        response_content["ml_model_info"] = ml_metrics

    return JSONResponse(
        status_code=status_code,
        content=response_content,
    )


@app.get("/", tags=["Root"])
async def root() -> JSONResponse:
    """
    Root endpoint.

    Returns:
        JSONResponse: Welcome message
    """
    return JSONResponse(
        content={
            "message": "Welcome to Gravity Fundamental Analysis Microservice",
            "version": settings.app_version,
            "docs": f"{settings.api_v1_prefix}/docs",
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower(),
    )
