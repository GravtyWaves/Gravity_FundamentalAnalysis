"""
Unit tests for MarketDataService.

Tests market data management:
- Market data sync from external source
- Duplicate prevention (upsert logic)
- Returns calculation
- Price statistics
- Multi-tenancy isolation
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4
from unittest.mock import AsyncMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.market_data_service import MarketDataService
from app.models.company import Company
from app.models.valuation_risk import MarketData


@pytest.fixture
async def company(test_db: AsyncSession, test_tenant_id: str) -> Company:
    """Create a test company."""
    company = Company(
        id=uuid4(),
        ticker="MARKET",
        name_en="Market Data Test Company",
        name_fa="شرکت تست داده بازار",
        sector_en="Technology",
        sector_fa="فناوری",
        industry_en="Software",
        industry_fa="نرم‌افزار",
        tenant_id=test_tenant_id,
        is_active=True
    )
    test_db.add(company)
    await test_db.commit()
    await test_db.refresh(company)
    return company


@pytest.fixture
async def market_data_records(
    test_db: AsyncSession,
    company: Company,
    test_tenant_id: str
) -> list[MarketData]:
    """Create test market data records."""
    records = []
    base_date = date(2023, 12, 1)
    base_price = 100.0
    
    for i in range(30):  # 30 days of data
        record_date = base_date + timedelta(days=i)
        # Simulate price movement (+/- 2% random)
        price = base_price * (1 + (i % 5 - 2) * 0.02)
        
        record = MarketData(
            id=uuid4(),
            company_id=company.id,
            tenant_id=test_tenant_id,
            date=record_date,
            open_price=Decimal(str(price * 0.99)),
            high_price=Decimal(str(price * 1.02)),
            low_price=Decimal(str(price * 0.98)),
            close_price=Decimal(str(price)),
            adjusted_close=Decimal(str(price)),
            volume=Decimal("1000000"),
            market_cap=Decimal("10000000000"),
            shares_outstanding=Decimal("100000000")
        )
        test_db.add(record)
        records.append(record)
    
    await test_db.commit()
    for record in records:
        await test_db.refresh(record)
    
    return records


@pytest.fixture
def market_data_service(test_db: AsyncSession, test_tenant_id: str) -> MarketDataService:
    """Create market data service instance."""
    return MarketDataService(db=test_db, tenant_id=test_tenant_id)


@pytest.fixture
def mock_external_data():
    """Mock external market data."""
    base_date = date(2024, 1, 1)
    return [
        {
            "date": (base_date + timedelta(days=i)).isoformat(),
            "open": 100.0 + i,
            "high": 105.0 + i,
            "low": 95.0 + i,
            "close": 102.0 + i,
            "adjusted_close": 102.0 + i,
            "volume": 1000000,
            "market_cap": 10000000000,
            "shares_outstanding": 100000000
        }
        for i in range(5)
    ]


@pytest.mark.asyncio
class TestMarketDataSync:
    """Test market data synchronization."""

    async def test_sync_market_data_new_records(
        self,
        market_data_service: MarketDataService,
        company: Company,
        mock_external_data: list
    ):
        """Test syncing new market data records."""
        with patch.object(
            market_data_service.data_client,
            'fetch_market_data',
            new=AsyncMock(return_value=mock_external_data)
        ):
            records = await market_data_service.sync_market_data(
                company_id=company.id,
                ticker="MARKET",
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 5)
            )
            
            # Should create 5 new records
            assert len(records) == 5
            assert all(r.company_id == company.id for r in records)

    async def test_sync_market_data_update_existing(
        self,
        test_db: AsyncSession,
        market_data_service: MarketDataService,
        company: Company,
        test_tenant_id: str
    ):
        """Test updating existing market data records."""
        # Create existing record
        existing_date = date(2024, 1, 1)
        existing = MarketData(
            id=uuid4(),
            company_id=company.id,
            tenant_id=test_tenant_id,
            date=existing_date,
            close_price=Decimal("100.00"),
            volume=Decimal("500000")
        )
        test_db.add(existing)
        await test_db.commit()
        
        # Mock updated data
        updated_data = [{
            "date": existing_date.isoformat(),
            "open": 100.0,
            "high": 105.0,
            "low": 95.0,
            "close": 102.0,  # Updated price
            "adjusted_close": 102.0,
            "volume": 1000000,  # Updated volume
            "market_cap": 10000000000,
            "shares_outstanding": 100000000
        }]
        
        with patch.object(
            market_data_service.data_client,
            'fetch_market_data',
            new=AsyncMock(return_value=updated_data)
        ):
            records = await market_data_service.sync_market_data(
                company_id=company.id,
                ticker="MARKET",
                start_date=existing_date,
                end_date=existing_date
            )
            
            # Should update existing record
            assert len(records) == 1
            assert float(records[0].close_price) == 102.0
            assert float(records[0].volume) == 1000000

    async def test_sync_market_data_duplicate_prevention(
        self,
        test_db: AsyncSession,
        market_data_service: MarketDataService,
        company: Company,
        test_tenant_id: str
    ):
        """Test duplicate prevention (upsert logic)."""
        record_date = date(2024, 1, 1)
        
        # First sync
        data1 = [{
            "date": record_date.isoformat(),
            "open": 100.0,
            "close": 102.0,
            "volume": 1000000
        }]
        
        with patch.object(
            market_data_service.data_client,
            'fetch_market_data',
            new=AsyncMock(return_value=data1)
        ):
            await market_data_service.sync_market_data(
                company_id=company.id,
                ticker="MARKET",
                start_date=record_date,
                end_date=record_date
            )
        
        # Second sync (should update, not duplicate)
        data2 = [{
            "date": record_date.isoformat(),
            "open": 100.0,
            "close": 105.0,  # Different price
            "volume": 1200000  # Different volume
        }]
        
        with patch.object(
            market_data_service.data_client,
            'fetch_market_data',
            new=AsyncMock(return_value=data2)
        ):
            await market_data_service.sync_market_data(
                company_id=company.id,
                ticker="MARKET",
                start_date=record_date,
                end_date=record_date
            )
        
        # Verify only 1 record exists
        from sqlalchemy import select, and_
        query = select(MarketData).where(
            and_(
                MarketData.company_id == company.id,
                MarketData.date == record_date
            )
        )
        result = await test_db.execute(query)
        records = result.scalars().all()
        
        assert len(records) == 1
        assert float(records[0].close_price) == 105.0


@pytest.mark.asyncio
class TestMarketDataRetrieval:
    """Test market data retrieval."""

    async def test_get_market_data_all(
        self,
        market_data_service: MarketDataService,
        company: Company,
        market_data_records: list[MarketData]
    ):
        """Test getting all market data for a company."""
        records = await market_data_service.get_market_data(company.id)
        
        # Should return all 30 records
        assert len(records) == 30
        assert all(r.company_id == company.id for r in records)

    async def test_get_market_data_date_range(
        self,
        market_data_service: MarketDataService,
        company: Company,
        market_data_records: list[MarketData]
    ):
        """Test getting market data within date range."""
        start_date = date(2023, 12, 10)
        end_date = date(2023, 12, 20)
        
        records = await market_data_service.get_market_data(
            company_id=company.id,
            start_date=start_date,
            end_date=end_date
        )
        
        # Should return ~11 days
        assert len(records) == 11
        assert all(start_date <= r.date <= end_date for r in records)

    async def test_get_market_data_with_limit(
        self,
        market_data_service: MarketDataService,
        company: Company,
        market_data_records: list[MarketData]
    ):
        """Test getting limited number of market data records."""
        records = await market_data_service.get_market_data(
            company_id=company.id,
            limit=10
        )
        
        # Should return exactly 10 records
        assert len(records) == 10

    async def test_get_latest_market_data(
        self,
        market_data_service: MarketDataService,
        company: Company,
        market_data_records: list[MarketData]
    ):
        """Test getting latest market data."""
        latest = await market_data_service.get_latest_market_data(company.id)
        
        # Should return most recent record
        assert latest is not None
        assert latest.date == max(r.date for r in market_data_records)

    async def test_get_latest_market_data_none(
        self,
        market_data_service: MarketDataService,
        company: Company
    ):
        """Test getting latest market data when none exists."""
        latest = await market_data_service.get_latest_market_data(company.id)
        
        # Should return None
        assert latest is None


@pytest.mark.asyncio
class TestReturnsCalculation:
    """Test returns calculation."""

    async def test_calculate_returns_basic(
        self,
        market_data_service: MarketDataService,
        company: Company,
        market_data_records: list[MarketData]
    ):
        """Test basic returns calculation."""
        returns = await market_data_service.calculate_returns(
            company_id=company.id,
            period_days=30
        )
        
        # Should return list of daily returns
        assert returns is not None
        assert len(returns) > 0
        assert all(isinstance(r, float) for r in returns)

    async def test_calculate_returns_positive_growth(
        self,
        test_db: AsyncSession,
        market_data_service: MarketDataService,
        company: Company,
        test_tenant_id: str
    ):
        """Test returns calculation with positive growth."""
        # Create data with consistent 1% daily growth
        base_date = date(2024, 1, 1)
        base_price = 100.0
        
        for i in range(10):
            price = base_price * (1.01 ** i)
            record = MarketData(
                id=uuid4(),
                company_id=company.id,
                tenant_id=test_tenant_id,
                date=base_date + timedelta(days=i),
                close_price=Decimal(str(price)),
                volume=Decimal("1000000")
            )
            test_db.add(record)
        
        await test_db.commit()
        
        returns = await market_data_service.calculate_returns(
            company_id=company.id,
            period_days=10
        )
        
        # Each daily return should be approximately 1%
        assert returns is not None
        assert all(0.009 <= r <= 0.011 for r in returns)  # ~1% with tolerance

    async def test_calculate_returns_insufficient_data(
        self,
        test_db: AsyncSession,
        market_data_service: MarketDataService,
        company: Company,
        test_tenant_id: str
    ):
        """Test returns calculation with insufficient data."""
        # Create only 1 record
        record = MarketData(
            id=uuid4(),
            company_id=company.id,
            tenant_id=test_tenant_id,
            date=date(2024, 1, 1),
            close_price=Decimal("100.00"),
            volume=Decimal("1000000")
        )
        test_db.add(record)
        await test_db.commit()
        
        returns = await market_data_service.calculate_returns(
            company_id=company.id,
            period_days=30
        )
        
        # Should return None (need at least 2 data points)
        assert returns is None


@pytest.mark.asyncio
class TestPriceStatistics:
    """Test price statistics calculation."""

    async def test_price_statistics_basic(
        self,
        market_data_service: MarketDataService,
        company: Company,
        market_data_records: list[MarketData]
    ):
        """Test basic price statistics calculation."""
        stats = await market_data_service.get_price_statistics(
            company_id=company.id,
            period_days=30
        )
        
        # Verify structure
        assert stats is not None
        assert "period_days" in stats
        assert "current_price" in stats
        assert "high" in stats
        assert "low" in stats
        assert "average" in stats
        assert "median" in stats
        assert "std_dev" in stats
        assert "volume_average" in stats
        assert "total_return" in stats

    async def test_price_statistics_calculations(
        self,
        test_db: AsyncSession,
        market_data_service: MarketDataService,
        company: Company,
        test_tenant_id: str
    ):
        """Test accuracy of price statistics calculations."""
        # Create known data
        prices = [100.0, 110.0, 105.0, 115.0, 120.0]
        base_date = date(2024, 1, 1)
        
        for i, price in enumerate(prices):
            record = MarketData(
                id=uuid4(),
                company_id=company.id,
                tenant_id=test_tenant_id,
                date=base_date + timedelta(days=i),
                close_price=Decimal(str(price)),
                volume=Decimal("1000000")
            )
            test_db.add(record)
        
        await test_db.commit()
        
        stats = await market_data_service.get_price_statistics(
            company_id=company.id,
            period_days=5
        )
        
        # Verify calculations
        assert stats["current_price"] == 120.0  # Latest price
        assert stats["high"] == 120.0
        assert stats["low"] == 100.0
        assert stats["average"] == 110.0  # Mean
        assert stats["median"] == 110.0  # Median
        
        # Total return: (120 - 100) / 100 = 20%
        assert abs(stats["total_return"] - 0.20) < 0.01

    async def test_price_statistics_no_data(
        self,
        market_data_service: MarketDataService,
        company: Company
    ):
        """Test price statistics with no data."""
        stats = await market_data_service.get_price_statistics(
            company_id=company.id,
            period_days=30
        )
        
        # Should return None
        assert stats is None


@pytest.mark.asyncio
class TestMultiTenancy:
    """Test multi-tenancy isolation."""

    async def test_sync_tenant_isolation(
        self,
        test_db: AsyncSession,
        company: Company,
        test_tenant_id: str,
        mock_external_data: list
    ):
        """Test sync respects tenant isolation."""
        # Service for different tenant
        different_tenant = str(uuid4())
        service_other_tenant = MarketDataService(
            db=test_db,
            tenant_id=different_tenant
        )
        
        with patch.object(
            service_other_tenant.data_client,
            'fetch_market_data',
            new=AsyncMock(return_value=mock_external_data)
        ):
            # Sync for different tenant
            await service_other_tenant.sync_market_data(
                company_id=company.id,
                ticker="MARKET",
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 5)
            )
        
        # Original tenant service should not see data
        service_original = MarketDataService(
            db=test_db,
            tenant_id=test_tenant_id
        )
        
        records = await service_original.get_market_data(company.id)
        
        # Should return empty (different tenant)
        assert len(records) == 0

    async def test_get_market_data_tenant_isolation(
        self,
        test_db: AsyncSession,
        company: Company,
        market_data_records: list[MarketData],
        test_tenant_id: str
    ):
        """Test get market data respects tenant isolation."""
        # Service for different tenant
        different_tenant = str(uuid4())
        service_other_tenant = MarketDataService(
            db=test_db,
            tenant_id=different_tenant
        )
        
        # Should not retrieve data from original tenant
        records = await service_other_tenant.get_market_data(company.id)
        
        assert len(records) == 0

    async def test_latest_market_data_tenant_isolation(
        self,
        test_db: AsyncSession,
        company: Company,
        market_data_records: list[MarketData],
        test_tenant_id: str
    ):
        """Test get latest market data respects tenant isolation."""
        # Service for different tenant
        different_tenant = str(uuid4())
        service_other_tenant = MarketDataService(
            db=test_db,
            tenant_id=different_tenant
        )
        
        # Should not retrieve data from original tenant
        latest = await service_other_tenant.get_latest_market_data(company.id)
        
        assert latest is None
