"""
================================================================================
FILE IDENTITY
================================================================================
File Path:           tests/test_scenario_tracker.py
Author:              João Silva (Testing Lead)
Team ID:             FA-TESTING
Created Date:        2025-11-14
Version:             1.0.0
Purpose:             Tests for ScenarioTracker service

Test Coverage:       95%+ target
Time Spent:          2.5 hours
Cost:                $375
================================================================================
"""

from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.scenario_tracker import ScenarioTracker


@pytest.fixture
def tenant_id() -> UUID:
    return uuid4()


@pytest.fixture
def company_id() -> UUID:
    return uuid4()


@pytest.mark.asyncio
class TestScenarioTracker:
    """Test suite for ScenarioTracker service."""

    async def test_initialization(self, db: AsyncSession, tenant_id: UUID):
        """Test service initialization."""
        tracker = ScenarioTracker(db, tenant_id)
        assert tracker.db == db
        assert tracker.tenant_id == str(tenant_id)

    async def test_track_prediction_outcome(
        self, db: AsyncSession, tenant_id: UUID, company_id: UUID
    ):
        """Test tracking prediction outcomes."""
        tracker = ScenarioTracker(db, tenant_id)
        
        result = await tracker.track_prediction_outcome(
            company_id=company_id,
            predicted_method="dcf",
            actual_best_method="dcf",
            predicted_return=Decimal("0.25"),
            actual_return=Decimal("0.23"),
        )
        
        assert result is not None
        assert "accuracy" in result

    async def test_calculate_method_accuracy(
        self, db: AsyncSession, tenant_id: UUID
    ):
        """Test method accuracy calculation."""
        tracker = ScenarioTracker(db, tenant_id)
        
        accuracy = tracker.calculate_accuracy(
            predicted_value=Decimal("150.00"),
            actual_value=Decimal("148.00"),
        )
        
        assert 0.0 <= accuracy <= 1.0

    async def test_get_performance_metrics(
        self, db: AsyncSession, tenant_id: UUID, company_id: UUID
    ):
        """Test performance metrics retrieval."""
        tracker = ScenarioTracker(db, tenant_id)
        
        metrics = await tracker.get_performance_metrics(company_id)
        
        assert metrics is not None
        assert "total_predictions" in metrics or metrics == {}
