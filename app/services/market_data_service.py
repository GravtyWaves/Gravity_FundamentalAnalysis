"""
Market Data Service.

Service for fetching and storing market data (prices, volumes) from external sources.
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional
from uuid import UUID
import logging

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.valuation_risk import MarketData
from app.services.data_collection_client import DataCollectionClient, DataCollectionError

logger = logging.getLogger(__name__)


class MarketDataService:
    """Service for managing market data."""

    def __init__(self, db: AsyncSession, tenant_id: str):
        """
        Initialize market data service.

        Args:
            db: Database session
            tenant_id: Current tenant ID
        """
        self.db = db
        self.tenant_id = str(tenant_id) if isinstance(tenant_id, UUID) else tenant_id
        self.data_client = DataCollectionClient()

    async def sync_market_data(
        self,
        company_id: UUID,
        ticker: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[MarketData]:
        """
        Sync market data from Data Collection service.

        Args:
            company_id: Company UUID
            ticker: Stock ticker symbol
            start_date: Start date (default: 1 year ago)
            end_date: End date (default: today)

        Returns:
            List of created/updated market data records
        """
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=365)

        try:
            logger.info(f"Syncing market data for {ticker} from {start_date} to {end_date}")

            # Fetch from Data Collection service
            market_data_list = await self.data_client.fetch_market_data(
                ticker=ticker,
                start_date=start_date,
                end_date=end_date,
            )

            created_records = []

            for data_point in market_data_list:
                record_date = data_point.get("date")
                if isinstance(record_date, str):
                    from datetime import datetime
                    record_date = datetime.fromisoformat(record_date).date()

                # Check if already exists
                existing_query = select(MarketData).where(
                    and_(
                        MarketData.company_id == company_id,
                        MarketData.date == record_date,
                        MarketData.tenant_id == self.tenant_id,
                    )
                )
                result = await self.db.execute(existing_query)
                existing = result.scalar_one_or_none()

                if existing:
                    # Update existing
                    existing.open_price = data_point.get("open")
                    existing.high_price = data_point.get("high")
                    existing.low_price = data_point.get("low")
                    existing.close_price = data_point.get("close")
                    existing.adjusted_close = data_point.get("adjusted_close")
                    existing.volume = data_point.get("volume")
                    existing.market_cap = data_point.get("market_cap")
                    existing.shares_outstanding = data_point.get("shares_outstanding")
                    created_records.append(existing)
                else:
                    # Create new
                    market_data = MarketData(
                        company_id=company_id,
                        tenant_id=self.tenant_id,
                        date=record_date,
                        open_price=data_point.get("open"),
                        high_price=data_point.get("high"),
                        low_price=data_point.get("low"),
                        close_price=data_point.get("close"),
                        adjusted_close=data_point.get("adjusted_close"),
                        volume=data_point.get("volume"),
                        market_cap=data_point.get("market_cap"),
                        shares_outstanding=data_point.get("shares_outstanding"),
                    )
                    self.db.add(market_data)
                    created_records.append(market_data)

            await self.db.commit()

            logger.info(f"Synced {len(created_records)} market data records for {ticker}")
            return created_records

        except DataCollectionError as e:
            logger.error(f"Failed to sync market data for {ticker}: {e}")
            await self.db.rollback()
            raise
        except Exception as e:
            logger.error(f"Unexpected error syncing market data for {ticker}: {e}")
            await self.db.rollback()
            raise

    async def get_market_data(
        self,
        company_id: UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: Optional[int] = None,
    ) -> List[MarketData]:
        """
        Get market data for a company.

        Args:
            company_id: Company UUID
            start_date: Start date filter
            end_date: End date filter
            limit: Maximum number of records

        Returns:
            List of market data records
        """
        query = select(MarketData).where(
            and_(
                MarketData.company_id == company_id,
                MarketData.tenant_id == self.tenant_id,
            )
        )

        if start_date:
            query = query.where(MarketData.date >= start_date)
        if end_date:
            query = query.where(MarketData.date <= end_date)

        query = query.order_by(MarketData.date.desc())

        if limit:
            query = query.limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_latest_market_data(
        self,
        company_id: UUID,
    ) -> Optional[MarketData]:
        """
        Get latest market data for a company.

        Args:
            company_id: Company UUID

        Returns:
            Latest MarketData or None
        """
        query = select(MarketData).where(
            and_(
                MarketData.company_id == company_id,
                MarketData.tenant_id == self.tenant_id,
            )
        ).order_by(MarketData.date.desc()).limit(1)

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def calculate_returns(
        self,
        company_id: UUID,
        period_days: int = 30,
    ) -> Optional[List[float]]:
        """
        Calculate daily returns for a period.

        Args:
            company_id: Company UUID
            period_days: Number of days

        Returns:
            List of daily returns or None
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=period_days * 2)

        market_data_list = await self.get_market_data(
            company_id=company_id,
            start_date=start_date,
            end_date=end_date,
        )

        if len(market_data_list) < 2:
            return None

        # Sort by date ascending
        market_data_list.sort(key=lambda x: x.date)

        returns = []
        for i in range(1, len(market_data_list)):
            prev_price = float(market_data_list[i-1].close_price)
            curr_price = float(market_data_list[i].close_price)

            if prev_price > 0:
                daily_return = (curr_price - prev_price) / prev_price
                returns.append(daily_return)

        return returns if len(returns) > 0 else None

    async def get_price_statistics(
        self,
        company_id: UUID,
        period_days: int = 30,
    ) -> Optional[dict]:
        """
        Calculate price statistics for a period.

        Args:
            company_id: Company UUID
            period_days: Number of days

        Returns:
            Dictionary with statistics or None
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=period_days)

        market_data_list = await self.get_market_data(
            company_id=company_id,
            start_date=start_date,
            end_date=end_date,
        )

        if len(market_data_list) == 0:
            return None

        prices = [float(md.close_price) for md in market_data_list]
        volumes = [float(md.volume) for md in market_data_list if md.volume]

        import numpy as np

        return {
            "period_days": period_days,
            "current_price": prices[0] if prices else None,  # Latest (first in desc order)
            "high": max(prices),
            "low": min(prices),
            "average": float(np.mean(prices)),
            "median": float(np.median(prices)),
            "std_dev": float(np.std(prices)),
            "volume_average": float(np.mean(volumes)) if volumes else None,
            "total_return": ((prices[0] - prices[-1]) / prices[-1]) if len(prices) > 1 and prices[-1] > 0 else None,
        }
