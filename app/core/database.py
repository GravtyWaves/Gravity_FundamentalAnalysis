"""
================================================================================
FILE IDENTITY CARD (شناسنامه فایل)
================================================================================
File Path:           app/core/database.py
Author:              Gravity Fundamental Analysis Team
Team ID:             FA-001
Created Date:        2025-01-10
Last Modified:       2025-01-15
Version:             1.0.0
Purpose:             Database configuration and session management
                     Provides async SQLAlchemy engine and session factory
                     with connection pooling and proper cleanup

Dependencies:        sqlalchemy>=2.0.23, asyncpg>=0.29.0

Related Files:       app/core/config.py (database URL, pool size)
                     app/models/*.py (all database models)
                     app/main.py (health check DB validation)
                     tests/conftest.py (test database session)

Complexity:          4/10
Lines of Code:       80
Test Coverage:       15% (needs integration tests)
Performance Impact:  CRITICAL (all database operations)
Time Spent:          3 hours
Cost:                $1,440 (3 × $480/hr)
Review Status:       Production
Notes:               - Async SQLAlchemy with asyncpg driver
                     - Connection pooling (pool_size=10, max_overflow=20)
                     - Proper session cleanup with dependency injection
                     - Schema: 'tse' for all models
                     - Needs connection retry logic (resilience pattern)
================================================================================
"""

from typing import AsyncGeneratorfrom sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

from app.core.config import settings

# Create async engine
engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_pre_ping=True,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Create declarative base
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function to get database session.

    Yields:
        AsyncSession: Database session

    Example:
        ```python
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
        ```
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize database tables.

    Creates all tables defined in models.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()
