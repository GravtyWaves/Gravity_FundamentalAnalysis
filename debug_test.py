"""Debug script to test database table creation."""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

# Import all models
from app.models.base import BaseModel
from app.models.company import Company
from app.models.financial_statements import IncomeStatement, BalanceSheet, CashFlowStatement
from app.models.ratios import FinancialRatio
from app.models.valuation_risk import Valuation, RiskAssessment, MarketData


async def test_table_creation():
    """Test if tables can be created."""
    TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
    
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
        echo=True,  # Enable SQL logging
        connect_args={"check_same_thread": False}
    )
    
    print("=" * 80)
    print("Creating tables...")
    print("=" * 80)
    
    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)
    
    print("=" * 80)
    print("Tables created successfully!")
    print(f"Tables: {list(BaseModel.metadata.tables.keys())}")
    print("=" * 80)
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(test_table_creation())
