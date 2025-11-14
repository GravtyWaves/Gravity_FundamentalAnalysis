"""
================================================================================
FILE IDENTITY CARD (شناسنامه فایل)
================================================================================
File Path:           app/core/exceptions.py
Author:              Gravity Fundamental Analysis Team
Team ID:             FA-001
Created Date:        2025-01-10
Last Modified:       2025-01-20
Version:             1.0.0
Purpose:             Global exception handlers for the application
                     Provides custom exceptions and centralized error handling

Dependencies:        fastapi>=0.104.1, sqlalchemy>=2.0.23

Related Files:       app/main.py (registers exception handlers)
                     app/services/*.py (raises custom exceptions)

Complexity:          5/10
Lines of Code:       54
Test Coverage:       0% (needs exception handler tests)
Performance Impact:  LOW (only triggered on errors)
Time Spent:          1.5 hours
Cost:                $720 (1.5 × $480/hr)
Review Status:       In Progress (Task 3)
Notes:               - Custom exception: DataIntegrationError
                     - Handlers: SQLAlchemyError, IntegrityError
                     - Returns structured JSON responses
                     - TODO: Add more custom exceptions (ValidationError, NotFoundError)
                     - TODO: Never expose internal errors in production
                     - TODO: Add correlation IDs to error responses
================================================================================
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError


class DataIntegrationError(Exception):
    """Raised when data integration from external service fails."""
    pass


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register global exception handlers.

    Args:
        app: FastAPI application instance
    """

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        """Handle ValueError exceptions."""
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc), "error": "validation_error"},
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
        """Handle database integrity errors."""
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": "Database integrity constraint violated", "error": "integrity_error"},
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        """Handle SQLAlchemy errors."""
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Database error occurred", "error": "database_error"},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle unexpected exceptions."""
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An unexpected error occurred", "error": "internal_server_error"},
        )
