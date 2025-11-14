"""
Data Collection Service Client.

Client for communicating with the Data Collection microservice.
This service handles fetching and cleaning financial data from external sources.
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import date
from decimal import Decimal

import httpx
from pydantic import BaseModel

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class DataCollectionError(Exception):
    """Raised when data collection service returns an error."""
    pass


class FinancialDataRequest(BaseModel):
    """Request model for fetching financial data."""
    ticker: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    data_type: str  # income_statement, balance_sheet, cash_flow, market_data
    period_type: str = "annual"  # annual or quarterly


class DataCollectionClient:
    """
    Client for Data Collection microservice.
    
    Handles communication with external data collection service
    that fetches and cleans financial data from various sources.
    """

    def __init__(self, base_url: Optional[str] = None, timeout: float = 30.0):
        """
        Initialize Data Collection client.
        
        Args:
            base_url: Base URL of data collection service
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or settings.data_collection_service_url
        self.timeout = timeout
        self.headers = {
            "Content-Type": "application/json",
            "X-Service-Name": "fundamental-analysis",
        }
        
        # Add API key if configured
        if hasattr(settings, 'data_collection_api_key') and settings.data_collection_api_key:
            self.headers["X-API-Key"] = settings.data_collection_api_key

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Make HTTP request to data collection service.
        
        Args:
            method: HTTP method (GET, POST)
            endpoint: API endpoint
            data: Request body data
            params: Query parameters
            
        Returns:
            Response data as dictionary
            
        Raises:
            DataCollectionError: If request fails
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    json=data,
                    params=params,
                    headers=self.headers,
                )
                
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from data collection service: {e}")
            error_detail = e.response.json().get("detail", str(e)) if e.response else str(e)
            raise DataCollectionError(f"Data collection failed: {error_detail}")
        except httpx.RequestError as e:
            logger.error(f"Request error to data collection service: {e}")
            raise DataCollectionError(f"Failed to connect to data collection service: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in data collection: {e}")
            raise DataCollectionError(f"Unexpected error: {str(e)}")

    async def fetch_income_statement(
        self,
        ticker: str,
        period_type: str = "annual",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch income statement data for a company.
        
        Args:
            ticker: Stock ticker symbol
            period_type: "annual" or "quarterly"
            start_date: Start date for historical data
            end_date: End date for historical data
            
        Returns:
            List of income statement records
        """
        params = {
            "ticker": ticker,
            "period_type": period_type,
        }
        
        if start_date:
            params["start_date"] = start_date.isoformat()
        if end_date:
            params["end_date"] = end_date.isoformat()
        
        logger.info(f"Fetching income statement for {ticker} ({period_type})")
        result = await self._make_request("GET", "/api/v1/data/income-statement", params=params)
        return result.get("data", [])

    async def fetch_balance_sheet(
        self,
        ticker: str,
        period_type: str = "annual",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch balance sheet data for a company.
        
        Args:
            ticker: Stock ticker symbol
            period_type: "annual" or "quarterly"
            start_date: Start date for historical data
            end_date: End date for historical data
            
        Returns:
            List of balance sheet records
        """
        params = {
            "ticker": ticker,
            "period_type": period_type,
        }
        
        if start_date:
            params["start_date"] = start_date.isoformat()
        if end_date:
            params["end_date"] = end_date.isoformat()
        
        logger.info(f"Fetching balance sheet for {ticker} ({period_type})")
        result = await self._make_request("GET", "/api/v1/data/balance-sheet", params=params)
        return result.get("data", [])

    async def fetch_cash_flow_statement(
        self,
        ticker: str,
        period_type: str = "annual",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch cash flow statement data for a company.
        
        Args:
            ticker: Stock ticker symbol
            period_type: "annual" or "quarterly"
            start_date: Start date for historical data
            end_date: End date for historical data
            
        Returns:
            List of cash flow statement records
        """
        params = {
            "ticker": ticker,
            "period_type": period_type,
        }
        
        if start_date:
            params["start_date"] = start_date.isoformat()
        if end_date:
            params["end_date"] = end_date.isoformat()
        
        logger.info(f"Fetching cash flow statement for {ticker} ({period_type})")
        result = await self._make_request("GET", "/api/v1/data/cash-flow", params=params)
        return result.get("data", [])

    async def fetch_market_data(
        self,
        ticker: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch market data (prices, volumes) for a company.
        
        Args:
            ticker: Stock ticker symbol
            start_date: Start date for historical data
            end_date: End date for historical data
            
        Returns:
            List of market data records
        """
        params = {"ticker": ticker}
        
        if start_date:
            params["start_date"] = start_date.isoformat()
        if end_date:
            params["end_date"] = end_date.isoformat()
        
        logger.info(f"Fetching market data for {ticker}")
        result = await self._make_request("GET", "/api/v1/data/market-data", params=params)
        return result.get("data", [])

    async def fetch_company_info(self, ticker: str) -> Dict[str, Any]:
        """
        Fetch company information and metadata.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Company information dictionary
        """
        params = {"ticker": ticker}
        
        logger.info(f"Fetching company info for {ticker}")
        result = await self._make_request("GET", "/api/v1/data/company-info", params=params)
        return result.get("data", {})

    async def fetch_all_financial_data(
        self,
        ticker: str,
        period_type: str = "annual",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """
        Fetch all financial data (income, balance, cash flow) in one call.
        
        Args:
            ticker: Stock ticker symbol
            period_type: "annual" or "quarterly"
            start_date: Start date for historical data
            end_date: End date for historical data
            
        Returns:
            Dictionary with all financial statements
        """
        params = {
            "ticker": ticker,
            "period_type": period_type,
        }
        
        if start_date:
            params["start_date"] = start_date.isoformat()
        if end_date:
            params["end_date"] = end_date.isoformat()
        
        logger.info(f"Fetching all financial data for {ticker}")
        result = await self._make_request("GET", "/api/v1/data/financial-statements", params=params)
        return result.get("data", {})

    async def request_data_refresh(self, ticker: str) -> Dict[str, Any]:
        """
        Request data collection service to refresh data for a ticker.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Refresh status
        """
        data = {"ticker": ticker}
        
        logger.info(f"Requesting data refresh for {ticker}")
        result = await self._make_request("POST", "/api/v1/data/refresh", data=data)
        return result

    async def check_data_availability(self, ticker: str) -> Dict[str, Any]:
        """
        Check if data is available for a ticker.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Availability status and last update time
        """
        params = {"ticker": ticker}
        
        logger.info(f"Checking data availability for {ticker}")
        result = await self._make_request("GET", "/api/v1/data/status", params=params)
        return result.get("data", {})

    async def get_supported_tickers(self) -> List[str]:
        """
        Get list of supported ticker symbols.
        
        Returns:
            List of ticker symbols
        """
        logger.info("Fetching supported tickers")
        result = await self._make_request("GET", "/api/v1/data/tickers")
        return result.get("data", [])

    async def health_check(self) -> bool:
        """
        Check if data collection service is healthy.
        
        Returns:
            True if service is healthy, False otherwise
        """
        try:
            result = await self._make_request("GET", "/health")
            return result.get("status") == "ok"
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
