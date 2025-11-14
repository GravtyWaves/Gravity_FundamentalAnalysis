"""
Market Data API endpoints.

Endpoints for fetching and managing market data (prices, volumes).
"""

from datetime import date, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID
import logging

from fastapi import APIRouter, Depends, HTTPException, Header, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.market_data_service import MarketDataService
from app.services.company_service import CompanyService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/market-data", tags=["Market Data"])


@router.post("/sync/{ticker}", status_code=status.HTTP_201_CREATED)
async def sync_market_data(
    ticker: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
) -> Dict[str, Any]:
    """
    Sync market data from Data Collection service.

    Fetches historical price and volume data and stores locally.

    Args:
        ticker: Stock ticker symbol
        start_date: Start date (default: 1 year ago)
        end_date: End date (default: today)
        tenant_id: Tenant identifier from header

    Returns:
        Sync results
    """
    try:
        # Get company
        company_service = CompanyService(db, tenant_id)
        company = await company_service.get_by_ticker(ticker)

        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company with ticker {ticker} not found",
            )

        # Type assertion for Pylance - company is an ORM instance
        assert company.id is not None
        
        # Sync market data
        market_data_service = MarketDataService(db, tenant_id)
        records = await market_data_service.sync_market_data(
            company_id=company.id,  # type: ignore[arg-type]
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
        )

        return {
            "status": "success",
            "message": f"Market data for {ticker} synced successfully",
            "company_id": str(company.id),
            "records_synced": len(records),
            "date_range": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error syncing market data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to sync market data",
        )


@router.get("/{company_id}")
async def get_market_data(
    company_id: UUID,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: Optional[int] = Query(None, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
) -> Dict[str, Any]:
    """
    Get market data for a company.

    Args:
        company_id: Company UUID
        start_date: Start date filter
        end_date: End date filter
        limit: Maximum number of records (1-1000)
        tenant_id: Tenant identifier from header

    Returns:
        List of market data records
    """
    try:
        service = MarketDataService(db, tenant_id)
        records = await service.get_market_data(
            company_id=company_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )

        return {
            "status": "success",
            "company_id": str(company_id),
            "count": len(records),
            "data": [
                {
                    "date": record.date.isoformat(),
                    "open": float(record.open_price) if record.open_price is not None else None,
                    "high": float(record.high_price) if record.high_price is not None else None,
                    "low": float(record.low_price) if record.low_price is not None else None,
                    "close": float(record.close_price) if record.close_price is not None else None,
                    "adjusted_close": float(record.adjusted_close) if record.adjusted_close is not None else None,
                    "volume": float(record.volume) if record.volume is not None else None,
                    "market_cap": float(record.market_cap) if record.market_cap is not None else None,
                }
                for record in records
            ],
        }

    except Exception as e:
        logger.error(f"Error fetching market data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch market data",
        )


@router.get("/{company_id}/latest")
async def get_latest_market_data(
    company_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
) -> Dict[str, Any]:
    """
    Get latest market data for a company.

    Args:
        company_id: Company UUID
        tenant_id: Tenant identifier from header

    Returns:
        Latest market data
    """
    try:
        service = MarketDataService(db, tenant_id)
        record = await service.get_latest_market_data(company_id)

        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No market data found for this company",
            )

        return {
            "status": "success",
            "data": {
                "date": record.date.isoformat(),
                "open": float(record.open_price) if record.open_price is not None else None,
                "high": float(record.high_price) if record.high_price is not None else None,
                "low": float(record.low_price) if record.low_price is not None else None,
                "close": float(record.close_price) if record.close_price is not None else None,
                "adjusted_close": float(record.adjusted_close) if record.adjusted_close is not None else None,
                "volume": float(record.volume) if record.volume is not None else None,
                "market_cap": float(record.market_cap) if record.market_cap is not None else None,
                "shares_outstanding": float(record.shares_outstanding) if record.shares_outstanding is not None else None,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching latest market data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch latest market data",
        )


@router.get("/{company_id}/statistics")
async def get_price_statistics(
    company_id: UUID,
    period_days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
) -> Dict[str, Any]:
    """
    Get price statistics for a period.

    Includes:
    - Current price
    - High/Low
    - Average/Median
    - Standard deviation
    - Total return

    Args:
        company_id: Company UUID
        period_days: Number of days (1-365)
        tenant_id: Tenant identifier from header

    Returns:
        Price statistics
    """
    try:
        service = MarketDataService(db, tenant_id)
        stats = await service.get_price_statistics(company_id, period_days)

        if not stats:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No market data available for statistics",
            )

        return {
            "status": "success",
            "company_id": str(company_id),
            "statistics": stats,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate statistics",
        )


@router.get("/{company_id}/returns")
async def get_returns(
    company_id: UUID,
    period_days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
) -> Dict[str, Any]:
    """
    Calculate daily returns for a period.

    Args:
        company_id: Company UUID
        period_days: Number of days (1-365)
        tenant_id: Tenant identifier from header

    Returns:
        List of daily returns
    """
    try:
        service = MarketDataService(db, tenant_id)
        returns = await service.calculate_returns(company_id, period_days)

        if returns is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Insufficient market data for returns calculation",
            )

        import numpy as np

        return {
            "status": "success",
            "company_id": str(company_id),
            "period_days": period_days,
            "returns": {
                "daily_returns": returns,
                "count": len(returns),
                "mean": float(np.mean(returns)),
                "std_dev": float(np.std(returns)),
                "min": float(min(returns)),
                "max": float(max(returns)),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating returns: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate returns",
        )
