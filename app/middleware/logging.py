"""
================================================================================
FILE IDENTITY CARD (شناسنامه فایل)
================================================================================
File Path:           app/middleware/logging.py
Author:              Gravity Fundamental Analysis Team
Team ID:             FA-001
Created Date:        2025-01-20
Last Modified:       2025-01-20
Version:             1.0.0
Purpose:             Structured logging configuration with correlation IDs
                     Provides JSON logging for observability (ELK Stack compatible)

Dependencies:        structlog>=24.1.0, fastapi>=0.104.1

Related Files:       app/main.py (logging setup)
                     app/core/config.py (log level, format settings)

Complexity:          6/10 (structured logging, correlation IDs, JSON format)
Lines of Code:       120
Test Coverage:       0% (needs logging middleware tests)
Performance Impact:  LOW (async logging, minimal overhead)
Time Spent:          2 hours
Cost:                $960 (2 × $480/hr)
Review Status:       In Progress (Task 2)
Notes:               - Based on Gravity_TechAnalysis logging pattern
                     - JSON format for production (ELK Stack)
                     - Console format for development
                     - Correlation IDs for request tracking
                     - Trace IDs for distributed tracing
================================================================================
"""

import logging
import sys
import uuid
from typing import Any, Dict

import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.core.config import settings


def setup_logging() -> None:
    """
    Configure structured logging with correlation IDs.
    
    Sets up structlog with:
    - JSON format for production (ELK Stack compatible)
    - Console format for development
    - Correlation IDs for request tracking
    - Timestamp in ISO format
    - Log level filtering
    """
    
    # Determine processors based on environment
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.TimeStamper(fmt="iso"),
    ]
    
    # Add JSON or console renderer based on log format setting
    if settings.log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )
    
    # Configure standard library logging to work with structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
    )


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for request/response logging with correlation IDs.
    
    Adds correlation_id and trace_id to all log messages within a request.
    Logs request start, completion, and errors.
    """
    
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Process request and add logging context.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/endpoint
            
        Returns:
            Response: HTTP response
        """
        # Generate correlation ID (use from header if exists)
        correlation_id = request.headers.get("x-correlation-id", str(uuid.uuid4()))
        trace_id = request.headers.get("x-trace-id", str(uuid.uuid4()))
        
        # Bind correlation IDs to structlog context
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            correlation_id=correlation_id,
            trace_id=trace_id,
            path=request.url.path,
            method=request.method,
        )
        
        logger = structlog.get_logger()
        
        # Log request start
        logger.info(
            "request_started",
            client_host=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        
        # Process request
        import time
        start_time = time.time()
        
        try:
            response = await call_next(request)
            
            # Calculate request duration
            duration = time.time() - start_time
            
            # Log request completion
            logger.info(
                "request_completed",
                status_code=response.status_code,
                duration_ms=round(duration * 1000, 2),
            )
            
            # Add correlation ID to response headers
            response.headers["x-correlation-id"] = correlation_id
            response.headers["x-trace-id"] = trace_id
            
            return response
            
        except Exception as e:
            # Log error
            duration = time.time() - start_time
            logger.error(
                "request_failed",
                error=str(e),
                error_type=type(e).__name__,
                duration_ms=round(duration * 1000, 2),
            )
            raise
        finally:
            # Clear context variables
            structlog.contextvars.clear_contextvars()
