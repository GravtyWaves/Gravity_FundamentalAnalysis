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

    Returns:
        JSONResponse: Service readiness status
    """
    # TODO: Add database and Redis connection checks
    return JSONResponse(
        content={
            "status": "ready",
            "service": settings.app_name,
        }
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
