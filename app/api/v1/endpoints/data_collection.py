"""
Data Collection API endpoints.

Endpoints for fetching financial data from the Data Collection microservice.
"""

from datetime import date
from typing import Any, Dict, List, Optional
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.data_collection_client import DataCollectionClient, DataCollectionError
from app.services.data_integration_service import DataIntegrationService
from app.core.exceptions import DataIntegrationError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/data-collection", tags=["Data Collection"])


def get_data_client() -> DataCollectionClient:
    """Get data collection client instance."""
    return DataCollectionClient()


@router.get("/health", status_code=status.HTTP_200_OK)
async def check_data_service_health(
    client: DataCollectionClient = Depends(get_data_client),
) -> Dict[str, Any]:
    """
    Check health of data collection service.
    
    Returns:
        Health status of data collection service
    """
    try:
        is_healthy = await client.health_check()
        return {
            "service": "data-collection",
            "status": "healthy" if is_healthy else "unhealthy",
            "timestamp": date.today().isoformat(),
        }
    except Exception as e:
        logger.error(f"Health check error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Data collection service is unavailable",
        )


@router.get("/tickers", response_model=List[str])
async def get_supported_tickers(
    client: DataCollectionClient = Depends(get_data_client),
) -> List[str]:
    """
    Get list of supported ticker symbols from data collection service.
    
    Returns:
        List of available ticker symbols
    """
    try:
        tickers = await client.get_supported_tickers()
        return tickers
    except DataCollectionError as e:
        logger.error(f"Failed to fetch tickers: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        )


@router.get("/status/{ticker}")
async def check_ticker_data_status(
    ticker: str,
    client: DataCollectionClient = Depends(get_data_client),
) -> Dict[str, Any]:
    """
    Check data availability status for a specific ticker.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        Data availability and last update information
    """
    try:
        status_info = await client.check_data_availability(ticker)
        return status_info
    except DataCollectionError as e:
        logger.error(f"Failed to check status for {ticker}: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        )


@router.get("/income-statement/{ticker}")
async def fetch_income_statement(
    ticker: str,
    period_type: str = Query("annual", regex="^(annual|quarterly)$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    client: DataCollectionClient = Depends(get_data_client),
) -> Dict[str, Any]:
    """
    Fetch income statement data from data collection service.
    
    Args:
        ticker: Stock ticker symbol
        period_type: "annual" or "quarterly"
        start_date: Optional start date for historical data
        end_date: Optional end date for historical data
        
    Returns:
        Income statement data
    """
    try:
        data = await client.fetch_income_statement(
            ticker=ticker,
            period_type=period_type,
            start_date=start_date,
            end_date=end_date,
        )
        
        return {
            "ticker": ticker,
            "period_type": period_type,
            "data_type": "income_statement",
            "records": data,
            "count": len(data),
        }
    except DataCollectionError as e:
        logger.error(f"Failed to fetch income statement for {ticker}: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        )


@router.get("/balance-sheet/{ticker}")
async def fetch_balance_sheet(
    ticker: str,
    period_type: str = Query("annual", regex="^(annual|quarterly)$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    client: DataCollectionClient = Depends(get_data_client),
) -> Dict[str, Any]:
    """
    Fetch balance sheet data from data collection service.
    
    Args:
        ticker: Stock ticker symbol
        period_type: "annual" or "quarterly"
        start_date: Optional start date for historical data
        end_date: Optional end date for historical data
        
    Returns:
        Balance sheet data
    """
    try:
        data = await client.fetch_balance_sheet(
            ticker=ticker,
            period_type=period_type,
            start_date=start_date,
            end_date=end_date,
        )
        
        return {
            "ticker": ticker,
            "period_type": period_type,
            "data_type": "balance_sheet",
            "records": data,
            "count": len(data),
        }
    except DataCollectionError as e:
        logger.error(f"Failed to fetch balance sheet for {ticker}: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        )


@router.get("/cash-flow/{ticker}")
async def fetch_cash_flow_statement(
    ticker: str,
    period_type: str = Query("annual", regex="^(annual|quarterly)$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    client: DataCollectionClient = Depends(get_data_client),
) -> Dict[str, Any]:
    """
    Fetch cash flow statement data from data collection service.
    
    Args:
        ticker: Stock ticker symbol
        period_type: "annual" or "quarterly"
        start_date: Optional start date for historical data
        end_date: Optional end date for historical data
        
    Returns:
        Cash flow statement data
    """
    try:
        data = await client.fetch_cash_flow_statement(
            ticker=ticker,
            period_type=period_type,
            start_date=start_date,
            end_date=end_date,
        )
        
        return {
            "ticker": ticker,
            "period_type": period_type,
            "data_type": "cash_flow",
            "records": data,
            "count": len(data),
        }
    except DataCollectionError as e:
        logger.error(f"Failed to fetch cash flow for {ticker}: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        )


@router.get("/market-data/{ticker}")
async def fetch_market_data(
    ticker: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    client: DataCollectionClient = Depends(get_data_client),
) -> Dict[str, Any]:
    """
    Fetch market data (prices, volumes) from data collection service.
    
    Args:
        ticker: Stock ticker symbol
        start_date: Optional start date for historical data
        end_date: Optional end date for historical data
        
    Returns:
        Market data
    """
    try:
        data = await client.fetch_market_data(
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
        )
        
        return {
            "ticker": ticker,
            "data_type": "market_data",
            "records": data,
            "count": len(data),
        }
    except DataCollectionError as e:
        logger.error(f"Failed to fetch market data for {ticker}: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        )


@router.get("/company-info/{ticker}")
async def fetch_company_info(
    ticker: str,
    client: DataCollectionClient = Depends(get_data_client),
) -> Dict[str, Any]:
    """
    Fetch company information from data collection service.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        Company information
    """
    try:
        data = await client.fetch_company_info(ticker)
        return data
    except DataCollectionError as e:
        logger.error(f"Failed to fetch company info for {ticker}: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        )


@router.get("/financial-statements/{ticker}")
async def fetch_all_financial_statements(
    ticker: str,
    period_type: str = Query("annual", regex="^(annual|quarterly)$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    client: DataCollectionClient = Depends(get_data_client),
) -> Dict[str, Any]:
    """
    Fetch all financial statements (income, balance, cash flow) in one call.
    
    Args:
        ticker: Stock ticker symbol
        period_type: "annual" or "quarterly"
        start_date: Optional start date for historical data
        end_date: Optional end date for historical data
        
    Returns:
        All financial statements data
    """
    try:
        data = await client.fetch_all_financial_data(
            ticker=ticker,
            period_type=period_type,
            start_date=start_date,
            end_date=end_date,
        )
        
        return {
            "ticker": ticker,
            "period_type": period_type,
            "data": data,
        }
    except DataCollectionError as e:
        logger.error(f"Failed to fetch financial statements for {ticker}: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        )


@router.post("/refresh/{ticker}", status_code=status.HTTP_202_ACCEPTED)
async def request_data_refresh(
    ticker: str,
    client: DataCollectionClient = Depends(get_data_client),
) -> Dict[str, Any]:
    """
    Request data collection service to refresh data for a ticker.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        Refresh request status
    """
    try:
        result = await client.request_data_refresh(ticker)
        return {
            "ticker": ticker,
            "status": "refresh_requested",
            "details": result,
        }
    except DataCollectionError as e:
        logger.error(f"Failed to request refresh for {ticker}: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        )


# ================= Data Integration Endpoints =================


@router.post("/sync/company/{ticker}", status_code=status.HTTP_201_CREATED)
async def sync_company_data(
    ticker: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
) -> Dict[str, Any]:
    """
    Sync company data from Data Collection service to local database.
    
    Fetches company information and creates/updates local record.
    
    Args:
        ticker: Stock ticker symbol
        tenant_id: Tenant identifier from header
        
    Returns:
        Created/updated company information
    """
    try:
        integration_service = DataIntegrationService(db, tenant_id)
        company = await integration_service.sync_company_data(ticker)
        
        return {
            "status": "success",
            "message": f"Company {ticker} synced successfully",
            "company": {
                "id": company.id,
                "ticker": company.ticker,
                "name": company.name,
                "sector": company.sector,
                "industry": company.industry,
            },
        }
    except DataIntegrationError as e:
        logger.error(f"Company sync failed for {ticker}: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        )


@router.post("/sync/financial-statements/{ticker}", status_code=status.HTTP_201_CREATED)
async def sync_all_financial_statements(
    ticker: str,
    period_type: str = Query("annual", regex="^(annual|quarterly)$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
) -> Dict[str, Any]:
    """
    Sync all financial statements for a company.
    
    Fetches income statements, balance sheets, and cash flow statements
    from Data Collection service and stores them locally.
    
    Args:
        ticker: Stock ticker symbol
        period_type: "annual" or "quarterly"
        start_date: Optional start date for historical data
        end_date: Optional end date for historical data
        tenant_id: Tenant identifier from header
        
    Returns:
        Sync results summary
    """
    try:
        integration_service = DataIntegrationService(db, tenant_id)
        result = await integration_service.sync_all_financial_data(
            ticker=ticker,
            period_type=period_type,
            start_date=start_date,
            end_date=end_date,
        )
        
        return {
            "status": "success",
            "message": f"Financial data for {ticker} synced successfully",
            "company_id": result["company"].id,
            "company_name": result["company"].name,
            "records_synced": {
                "income_statements": result["income_statements"],
                "balance_sheets": result["balance_sheets"],
                "cash_flow_statements": result["cash_flow_statements"],
                "total": result["total_records"],
            },
        }
    except DataIntegrationError as e:
        logger.error(f"Financial statements sync failed for {ticker}: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        )


@router.post("/sync/income-statements/{ticker}", status_code=status.HTTP_201_CREATED)
async def sync_income_statements_only(
    ticker: str,
    period_type: str = Query("annual", regex="^(annual|quarterly)$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
) -> Dict[str, Any]:
    """
    Sync only income statements for a company.
    
    Args:
        ticker: Stock ticker symbol
        period_type: "annual" or "quarterly"
        start_date: Optional start date
        end_date: Optional end date
        tenant_id: Tenant identifier from header
        
    Returns:
        Sync results
    """
    try:
        integration_service = DataIntegrationService(db, tenant_id)
        
        # Get company first
        company = await integration_service.sync_company_data(ticker)
        
        # Sync income statements
        statements = await integration_service.sync_income_statements(
            company_id=company.id,
            ticker=ticker,
            period_type=period_type,
            start_date=start_date,
            end_date=end_date,
        )
        
        return {
            "status": "success",
            "message": f"Income statements for {ticker} synced successfully",
            "company_id": company.id,
            "records_synced": len(statements),
        }
    except DataIntegrationError as e:
        logger.error(f"Income statements sync failed for {ticker}: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        )
