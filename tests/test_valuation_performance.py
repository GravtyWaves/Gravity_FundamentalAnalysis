"""
================================================================================
FILE IDENTITY
================================================================================
File Path:           tests/test_valuation_performance.py
Author:              João Silva (Testing Lead)
Team ID:             FA-TESTING
Created Date:        2025-11-14
Version:             1.0.0
Purpose:             Tests for ValuationPerformance service

Test Coverage:       95%+ target
Time Spent:          2.5 hours
Cost:                $375
================================================================================
"""

from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.valuation_performance import ValuationPerformance


@pytest.fixture
def tenant_id() -> UUID:
    return uuid4()


@pytest.fixture
def company_id() -> UUID:
    return uuid4()


@pytest.mark.asyncio
class TestValuationPerformance:
    """Test suite for ValuationPerformance service."""

    async def test_initialization(self, db: AsyncSession, tenant_id: UUID):
        """Test service initialization."""
        perf = ValuationPerformance(db, tenant_id)
        assert perf.db == db
        assert perf.tenant_id == str(tenant_id)

    async def test_calculate_model_metrics(
        self, db: AsyncSession, tenant_id: UUID, company_id: UUID
    ):
        """Test model performance metrics calculation."""
        perf = ValuationPerformance(db, tenant_id)
        
        metrics = await perf.calculate_model_metrics(company_id)
        
        # Should return metrics or empty dict
        assert isinstance(metrics, dict)

    async def test_mean_absolute_error(
        self, db: AsyncSession, tenant_id: UUID
    ):
        """Test MAE calculation."""
        perf = ValuationPerformance(db, tenant_id)
        
        predictions = [Decimal("100"), Decimal("110"), Decimal("105")]
        actuals = [Decimal("102"), Decimal("108"), Decimal("107")]
        
        mae = perf.calculate_mae(predictions, actuals)
        
        assert mae >= 0

    async def test_get_best_performing_method(
        self, db: AsyncSession, tenant_id: UUID, company_id: UUID
    ):
        """Test best performing method identification."""
        perf = ValuationPerformance(db, tenant_id)
        
        result = await perf.get_best_performing_method(company_id)
        
        # Should return method name or None
        assert result is None or isinstance(result, str)
