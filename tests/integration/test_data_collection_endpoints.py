"""
Integration tests for Data Collection API endpoints.

Tests API contract, error handling, and external service communication.
"""

import pytest
from datetime import date, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.services.data_collection_client import DataCollectionError


@pytest.fixture
def mock_data_client():
    """Mock DataCollectionClient for testing."""
    with patch("app.api.v1.endpoints.data_collection.DataCollectionClient") as mock:
        client_instance = AsyncMock()
        mock.return_value = client_instance
        yield client_instance


class TestDataCollectionHealthEndpoint:
    """Test suite for /data-collection/health endpoint."""

    def test_health_check_success(self, client: TestClient, mock_data_client):
        """Test successful health check when service is healthy."""
        # Arrange
        mock_data_client.health_check.return_value = True

        # Act
        response = client.get("/api/v1/data-collection/health")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["service"] == "data-collection"
        assert data["status"] == "healthy"
        assert "timestamp" in data
        mock_data_client.health_check.assert_called_once()

    def test_health_check_unhealthy(self, client: TestClient, mock_data_client):
        """Test health check when service is unhealthy."""
        # Arrange
        mock_data_client.health_check.return_value = False

        # Act
        response = client.get("/api/v1/data-collection/health")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "unhealthy"

    def test_health_check_service_unavailable(self, client: TestClient, mock_data_client):
        """Test health check when service raises exception."""
        # Arrange
        mock_data_client.health_check.side_effect = Exception("Connection refused")

        # Act
        response = client.get("/api/v1/data-collection/health")

        # Assert
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert "unavailable" in response.json()["detail"]


class TestGetSupportedTickers:
    """Test suite for /data-collection/tickers endpoint."""

    def test_get_tickers_success(self, client: TestClient, mock_data_client):
        """Test successful retrieval of supported tickers."""
        # Arrange
        expected_tickers = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN"]
        mock_data_client.get_supported_tickers.return_value = expected_tickers

        # Act
        response = client.get("/api/v1/data-collection/tickers")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == expected_tickers
        mock_data_client.get_supported_tickers.assert_called_once()

    def test_get_tickers_empty_list(self, client: TestClient, mock_data_client):
        """Test when no tickers are available."""
        # Arrange
        mock_data_client.get_supported_tickers.return_value = []

        # Act
        response = client.get("/api/v1/data-collection/tickers")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    def test_get_tickers_service_error(self, client: TestClient, mock_data_client):
        """Test when data collection service returns error."""
        # Arrange
        mock_data_client.get_supported_tickers.side_effect = DataCollectionError(
            "Service temporarily unavailable"
        )

        # Act
        response = client.get("/api/v1/data-collection/tickers")

        # Assert
        assert response.status_code == status.HTTP_502_BAD_GATEWAY
        assert "Service temporarily unavailable" in response.json()["detail"]


class TestCheckTickerDataStatus:
    """Test suite for /data-collection/status/{ticker} endpoint."""

    def test_check_status_success(self, client: TestClient, mock_data_client):
        """Test successful status check for ticker."""
        # Arrange
        ticker = "AAPL"
        expected_status = {
            "ticker": ticker,
            "available": True,
            "last_updated": "2025-11-14",
            "data_sources": ["yahoo_finance", "sec_edgar"],
        }
        mock_data_client.check_data_availability.return_value = expected_status

        # Act
        response = client.get(f"/api/v1/data-collection/status/{ticker}")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == expected_status
        mock_data_client.check_data_availability.assert_called_once_with(ticker)

    def test_check_status_unavailable_ticker(self, client: TestClient, mock_data_client):
        """Test status check for unavailable ticker."""
        # Arrange
        ticker = "INVALID"
        expected_status = {
            "ticker": ticker,
            "available": False,
            "last_updated": None,
            "data_sources": [],
        }
        mock_data_client.check_data_availability.return_value = expected_status

        # Act
        response = client.get(f"/api/v1/data-collection/status/{ticker}")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["available"] is False

    def test_check_status_service_error(self, client: TestClient, mock_data_client):
        """Test status check when service fails."""
        # Arrange
        ticker = "AAPL"
        mock_data_client.check_data_availability.side_effect = DataCollectionError(
            "Database connection error"
        )

        # Act
        response = client.get(f"/api/v1/data-collection/status/{ticker}")

        # Assert
        assert response.status_code == status.HTTP_502_BAD_GATEWAY


class TestFetchIncomeStatement:
    """Test suite for /data-collection/income-statement/{ticker} endpoint."""

    def test_fetch_income_statement_annual_success(self, client: TestClient, mock_data_client):
        """Test successful fetch of annual income statement."""
        # Arrange
        ticker = "AAPL"
        mock_data = [
            {
                "period_end_date": "2024-12-31",
                "revenue": 394000000000,
                "cost_of_revenue": 223000000000,
                "gross_profit": 171000000000,
                "operating_expenses": 55000000000,
                "operating_income": 116000000000,
                "net_income": 97000000000,
            },
            {
                "period_end_date": "2023-12-31",
                "revenue": 383000000000,
                "cost_of_revenue": 215000000000,
                "gross_profit": 168000000000,
                "operating_expenses": 52000000000,
                "operating_income": 116000000000,
                "net_income": 96000000000,
            },
        ]
        mock_data_client.fetch_income_statement.return_value = mock_data

        # Act
        response = client.get(f"/api/v1/data-collection/income-statement/{ticker}")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["ticker"] == ticker
        assert data["period_type"] == "annual"
        assert data["data_type"] == "income_statement"
        assert data["count"] == 2
        assert len(data["records"]) == 2
        mock_data_client.fetch_income_statement.assert_called_once()

    def test_fetch_income_statement_quarterly(self, client: TestClient, mock_data_client):
        """Test fetch of quarterly income statement."""
        # Arrange
        ticker = "GOOGL"
        mock_data = [
            {
                "period_end_date": "2024-09-30",
                "revenue": 88000000000,
                "net_income": 26000000000,
            }
        ]
        mock_data_client.fetch_income_statement.return_value = mock_data

        # Act
        response = client.get(
            f"/api/v1/data-collection/income-statement/{ticker}",
            params={"period_type": "quarterly"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["period_type"] == "quarterly"
        assert data["count"] == 1

    def test_fetch_income_statement_with_date_range(self, client: TestClient, mock_data_client):
        """Test fetch with date range parameters."""
        # Arrange
        ticker = "MSFT"
        start_date = date(2023, 1, 1)
        end_date = date(2024, 12, 31)
        mock_data_client.fetch_income_statement.return_value = []

        # Act
        response = client.get(
            f"/api/v1/data-collection/income-statement/{ticker}",
            params={
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        mock_data_client.fetch_income_statement.assert_called_once_with(
            ticker=ticker,
            period_type="annual",
            start_date=start_date,
            end_date=end_date,
        )

    def test_fetch_income_statement_invalid_period_type(self, client: TestClient, mock_data_client):
        """Test with invalid period_type parameter."""
        # Arrange
        ticker = "AAPL"

        # Act
        response = client.get(
            f"/api/v1/data-collection/income-statement/{ticker}",
            params={"period_type": "invalid"},
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_fetch_income_statement_service_error(self, client: TestClient, mock_data_client):
        """Test when service fails to fetch data."""
        # Arrange
        ticker = "AAPL"
        mock_data_client.fetch_income_statement.side_effect = DataCollectionError(
            "External API rate limit exceeded"
        )

        # Act
        response = client.get(f"/api/v1/data-collection/income-statement/{ticker}")

        # Assert
        assert response.status_code == status.HTTP_502_BAD_GATEWAY
        assert "rate limit" in response.json()["detail"].lower()


class TestFetchBalanceSheet:
    """Test suite for /data-collection/balance-sheet/{ticker} endpoint."""

    def test_fetch_balance_sheet_success(self, client: TestClient, mock_data_client):
        """Test successful fetch of balance sheet."""
        # Arrange
        ticker = "TSLA"
        mock_data = [
            {
                "period_end_date": "2024-12-31",
                "total_assets": 106000000000,
                "total_liabilities": 43000000000,
                "total_equity": 63000000000,
                "cash_and_equivalents": 29000000000,
                "current_assets": 45000000000,
                "current_liabilities": 28000000000,
            }
        ]
        mock_data_client.fetch_balance_sheet.return_value = mock_data

        # Act
        response = client.get(f"/api/v1/data-collection/balance-sheet/{ticker}")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["ticker"] == ticker
        assert data["data_type"] == "balance_sheet"
        assert data["count"] == 1
        assert len(data["records"]) == 1

    def test_fetch_balance_sheet_empty_result(self, client: TestClient, mock_data_client):
        """Test when no balance sheet data is available."""
        # Arrange
        ticker = "UNKNOWN"
        mock_data_client.fetch_balance_sheet.return_value = []

        # Act
        response = client.get(f"/api/v1/data-collection/balance-sheet/{ticker}")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["count"] == 0
        assert data["records"] == []

    def test_fetch_balance_sheet_service_error(self, client: TestClient, mock_data_client):
        """Test service error during balance sheet fetch."""
        # Arrange
        ticker = "AAPL"
        mock_data_client.fetch_balance_sheet.side_effect = DataCollectionError(
            "Timeout while fetching data"
        )

        # Act
        response = client.get(f"/api/v1/data-collection/balance-sheet/{ticker}")

        # Assert
        assert response.status_code == status.HTTP_502_BAD_GATEWAY


class TestFetchCashFlowStatement:
    """Test suite for /data-collection/cash-flow/{ticker} endpoint."""

    def test_fetch_cash_flow_success(self, client: TestClient, mock_data_client):
        """Test successful fetch of cash flow statement."""
        # Arrange
        ticker = "AMZN"
        mock_data = [
            {
                "period_end_date": "2024-12-31",
                "operating_cash_flow": 84000000000,
                "investing_cash_flow": -51000000000,
                "financing_cash_flow": -10000000000,
                "free_cash_flow": 33000000000,
            }
        ]
        mock_data_client.fetch_cash_flow_statement.return_value = mock_data

        # Act
        response = client.get(f"/api/v1/data-collection/cash-flow/{ticker}")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["ticker"] == ticker
        assert data["data_type"] == "cash_flow"
        assert data["count"] == 1

    def test_fetch_cash_flow_quarterly(self, client: TestClient, mock_data_client):
        """Test fetch quarterly cash flow."""
        # Arrange
        ticker = "NFLX"
        mock_data_client.fetch_cash_flow_statement.return_value = []

        # Act
        response = client.get(
            f"/api/v1/data-collection/cash-flow/{ticker}",
            params={"period_type": "quarterly"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        mock_data_client.fetch_cash_flow_statement.assert_called_once()

    def test_fetch_cash_flow_service_error(self, client: TestClient, mock_data_client):
        """Test service error during cash flow fetch."""
        # Arrange
        ticker = "AAPL"
        mock_data_client.fetch_cash_flow_statement.side_effect = DataCollectionError(
            "Data source unavailable"
        )

        # Act
        response = client.get(f"/api/v1/data-collection/cash-flow/{ticker}")

        # Assert
        assert response.status_code == status.HTTP_502_BAD_GATEWAY


class TestFetchMarketData:
    """Test suite for /data-collection/market-data/{ticker} endpoint."""

    def test_fetch_market_data_success(self, client: TestClient, mock_data_client):
        """Test successful fetch of market data."""
        # Arrange
        ticker = "AAPL"
        mock_data = [
            {
                "date": "2024-11-14",
                "open": 225.50,
                "high": 228.75,
                "low": 224.20,
                "close": 227.85,
                "volume": 52000000,
            },
            {
                "date": "2024-11-13",
                "open": 223.00,
                "high": 226.10,
                "low": 222.50,
                "close": 225.50,
                "volume": 48000000,
            },
        ]
        mock_data_client.fetch_market_data.return_value = mock_data

        # Act
        response = client.get(f"/api/v1/data-collection/market-data/{ticker}")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["ticker"] == ticker
        assert data["data_type"] == "market_data"
        assert data["count"] == 2

    def test_fetch_market_data_with_date_range(self, client: TestClient, mock_data_client):
        """Test market data fetch with date range."""
        # Arrange
        ticker = "GOOGL"
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()
        mock_data_client.fetch_market_data.return_value = []

        # Act
        response = client.get(
            f"/api/v1/data-collection/market-data/{ticker}",
            params={
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        mock_data_client.fetch_market_data.assert_called_once_with(
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
        )

    def test_fetch_market_data_service_error(self, client: TestClient, mock_data_client):
        """Test service error during market data fetch."""
        # Arrange
        ticker = "MSFT"
        mock_data_client.fetch_market_data.side_effect = DataCollectionError(
            "Market closed"
        )

        # Act
        response = client.get(f"/api/v1/data-collection/market-data/{ticker}")

        # Assert
        assert response.status_code == status.HTTP_502_BAD_GATEWAY


class TestEdgeCasesAndValidation:
    """Test suite for edge cases and input validation."""

    def test_ticker_special_characters(self, client: TestClient, mock_data_client):
        """Test ticker with special characters."""
        # Arrange
        ticker = "BRK.B"  # Berkshire Hathaway Class B
        mock_data_client.check_data_availability.return_value = {
            "ticker": ticker,
            "available": True,
        }

        # Act
        response = client.get(f"/api/v1/data-collection/status/{ticker}")

        # Assert
        assert response.status_code == status.HTTP_200_OK

    def test_date_format_validation(self, client: TestClient, mock_data_client):
        """Test invalid date format."""
        # Arrange
        ticker = "AAPL"

        # Act
        response = client.get(
            f"/api/v1/data-collection/income-statement/{ticker}",
            params={"start_date": "invalid-date"},
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_end_date_before_start_date(self, client: TestClient, mock_data_client):
        """Test when end_date is before start_date (business logic validation)."""
        # Arrange
        ticker = "AAPL"
        start_date = date(2024, 12, 31)
        end_date = date(2023, 1, 1)
        mock_data_client.fetch_income_statement.return_value = []

        # Act - API accepts it, service should handle validation
        response = client.get(
            f"/api/v1/data-collection/income-statement/{ticker}",
            params={
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        )

        # Assert - Should still call service (service validates business logic)
        assert response.status_code == status.HTTP_200_OK
        mock_data_client.fetch_income_statement.assert_called_once()

    def test_long_ticker_symbol(self, client: TestClient, mock_data_client):
        """Test very long ticker symbol."""
        # Arrange
        ticker = "A" * 100  # Extremely long ticker
        mock_data_client.check_data_availability.return_value = {
            "ticker": ticker,
            "available": False,
        }

        # Act
        response = client.get(f"/api/v1/data-collection/status/{ticker}")

        # Assert
        assert response.status_code == status.HTTP_200_OK

    def test_concurrent_requests_same_ticker(self, client: TestClient, mock_data_client):
        """Test multiple concurrent requests for same ticker."""
        # Arrange
        ticker = "AAPL"
        mock_data_client.fetch_income_statement.return_value = []

        # Act - Simulate concurrent requests
        responses = [
            client.get(f"/api/v1/data-collection/income-statement/{ticker}")
            for _ in range(5)
        ]

        # Assert
        assert all(r.status_code == status.HTTP_200_OK for r in responses)
        assert mock_data_client.fetch_income_statement.call_count == 5


class TestErrorHandlingAndRecovery:
    """Test suite for error handling and recovery scenarios."""

    def test_network_timeout_error(self, client: TestClient, mock_data_client):
        """Test handling of network timeout."""
        # Arrange
        ticker = "AAPL"
        mock_data_client.fetch_income_statement.side_effect = DataCollectionError(
            "Request timeout after 30 seconds"
        )

        # Act
        response = client.get(f"/api/v1/data-collection/income-statement/{ticker}")

        # Assert
        assert response.status_code == status.HTTP_502_BAD_GATEWAY
        assert "timeout" in response.json()["detail"].lower()

    def test_malformed_response_from_service(self, client: TestClient, mock_data_client):
        """Test handling of malformed response."""
        # Arrange
        ticker = "AAPL"
        mock_data_client.fetch_income_statement.side_effect = DataCollectionError(
            "Invalid JSON response"
        )

        # Act
        response = client.get(f"/api/v1/data-collection/income-statement/{ticker}")

        # Assert
        assert response.status_code == status.HTTP_502_BAD_GATEWAY

    def test_service_authentication_failure(self, client: TestClient, mock_data_client):
        """Test handling of authentication failure with data service."""
        # Arrange
        ticker = "AAPL"
        mock_data_client.get_supported_tickers.side_effect = DataCollectionError(
            "Authentication failed: Invalid API key"
        )

        # Act
        response = client.get("/api/v1/data-collection/tickers")

        # Assert
        assert response.status_code == status.HTTP_502_BAD_GATEWAY
        assert "Authentication failed" in response.json()["detail"]


class TestResponseStructure:
    """Test suite for validating response structure and schema."""

    def test_income_statement_response_structure(self, client: TestClient, mock_data_client):
        """Validate income statement response has all required fields."""
        # Arrange
        ticker = "AAPL"
        mock_data_client.fetch_income_statement.return_value = [{"test": "data"}]

        # Act
        response = client.get(f"/api/v1/data-collection/income-statement/{ticker}")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "ticker" in data
        assert "period_type" in data
        assert "data_type" in data
        assert "records" in data
        assert "count" in data
        assert isinstance(data["records"], list)
        assert isinstance(data["count"], int)

    def test_health_response_structure(self, client: TestClient, mock_data_client):
        """Validate health endpoint response structure."""
        # Arrange
        mock_data_client.health_check.return_value = True

        # Act
        response = client.get("/api/v1/data-collection/health")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "service" in data
        assert "status" in data
        assert "timestamp" in data
        assert data["service"] == "data-collection"
        assert data["status"] in ["healthy", "unhealthy"]

    def test_status_response_contains_required_fields(self, client: TestClient, mock_data_client):
        """Validate status endpoint returns required fields."""
        # Arrange
        ticker = "AAPL"
        mock_data_client.check_data_availability.return_value = {
            "ticker": ticker,
            "available": True,
            "last_updated": "2024-11-14",
        }

        # Act
        response = client.get(f"/api/v1/data-collection/status/{ticker}")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "ticker" in data
        assert "available" in data
        assert isinstance(data["available"], bool)
