"""
Pytest configuration and fixtures.
"""

import asyncio
from typing import AsyncGenerator, Generator
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.database import get_db
from app.main import app
from app.models.base import BaseModel

# Import all models to register them with SQLAlchemy metadata
from app.models.company import Company  # noqa: F401
from app.models.financial_statements import IncomeStatement, BalanceSheet, CashFlowStatement  # noqa: F401
from app.models.ratios import FinancialRatio  # noqa: F401
from app.models.valuation_risk import Valuation, RiskAssessment, MarketData  # noqa: F401

# Test database URL (use in-memory SQLite for fast tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_db_engine():
    """Create a test database engine (session scope to reuse across tests)."""
    # Use file-based SQLite for session scope (in-memory doesn't work well across connections)
    TEST_DB_FILE = "sqlite+aiosqlite:///./test.db"
    engine = create_async_engine(
        TEST_DB_FILE,
        poolclass=NullPool,
        echo=False
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)

    yield engine

    # Drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.drop_all)

    await engine.dispose()
    
    # Clean up the test database file
    import os
    try:
        os.remove("./test.db")
    except:
        pass


@pytest_asyncio.fixture(scope="function")
async def test_db(test_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session = sessionmaker(
        test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture(scope="function")
def test_tenant_id() -> str:
    """Generate a test tenant ID."""
    return str(uuid4())


@pytest.fixture(scope="function")
def client(test_db: AsyncSession, test_tenant_id: str) -> TestClient:
    """Create a test client with database override."""

    async def override_get_db():
        yield test_db

    async def override_get_tenant_id():
        return test_tenant_id

    app.dependency_overrides[get_db] = override_get_db
    from app.core.security import get_tenant_id

    app.dependency_overrides[get_tenant_id] = override_get_tenant_id

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def mock_current_user():
    """Mock current user for authentication."""
    return {
        "sub": "test-user-id",
        "email": "test@example.com",
        "tenant_id": str(uuid4()),
    }


@pytest.fixture(scope="function")
def auth_headers(mock_current_user) -> dict:
    """Generate authentication headers."""
    from app.core.security import create_access_token

    token = create_access_token(data={"sub": mock_current_user["sub"]})
    return {"Authorization": f"Bearer {token}"}
