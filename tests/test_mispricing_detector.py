"""
================================================================================
FILE IDENTITY
================================================================================
File Path:           tests/test_mispricing_detector.py
Author:              João Silva (Testing Lead)
Team ID:             FA-TESTING
Created Date:        2025-11-14
Version:             1.0.0
Purpose:             Tests for MispricingDetector service

Test Coverage:       95%+ target
Time Spent:          3 hours
Cost:                $450
================================================================================
"""

from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.mispricing_detector import MispricingDetector


@pytest.fixture
def tenant_id() -> UUID:
    return uuid4()


@pytest.fixture
def company_id() -> UUID:
    return uuid4()


@pytest.mark.asyncio
class TestMispricingDetector:
    """Test suite for MispricingDetector service."""

    async def test_initialization(self, db: AsyncSession, tenant_id: UUID):
        """Test service initialization."""
        detector = MispricingDetector(db, tenant_id)
        assert detector.db == db
        assert detector.tenant_id == str(tenant_id)

    async def test_detect_mispricing(
        self, db: AsyncSession, tenant_id: UUID, company_id: UUID
    ):
        """Test mispricing detection."""
        detector = MispricingDetector(db, tenant_id)
        
        result = await detector.detect_mispricing(
            company_id=company_id,
            current_price=Decimal("100.00"),
            fair_value=Decimal("150.00"),
        )
        
        assert result is not None
        assert "mispricing_percentage" in result
        assert "classification" in result

    async def test_overvalued_detection(
        self, db: AsyncSession, tenant_id: UUID
    ):
        """Test overvalued stock detection."""
        detector = MispricingDetector(db, tenant_id)
        
        result = detector.classify_mispricing(
            current_price=Decimal("200.00"),
            fair_value=Decimal("100.00"),
        )
        
        assert result["classification"] == "overvalued"
        assert result["mispricing_percentage"] > 0

    async def test_undervalued_detection(
        self, db: AsyncSession, tenant_id: UUID
    ):
        """Test undervalued stock detection."""
        detector = MispricingDetector(db, tenant_id)
        
        result = detector.classify_mispricing(
            current_price=Decimal("100.00"),
            fair_value=Decimal("200.00"),
        )
        
        assert result["classification"] == "undervalued"
        assert result["mispricing_percentage"] < 0

    async def test_fairly_valued_detection(
        self, db: AsyncSession, tenant_id: UUID
    ):
        """Test fairly valued stock detection."""
        detector = MispricingDetector(db, tenant_id)
        
        result = detector.classify_mispricing(
            current_price=Decimal("100.00"),
            fair_value=Decimal("105.00"),
        )
        
        assert result["classification"] == "fairly_valued"

    async def test_opportunity_score_calculation(
        self, db: AsyncSession, tenant_id: UUID
    ):
        """Test opportunity score calculation."""
        detector = MispricingDetector(db, tenant_id)
        
        score = detector.calculate_opportunity_score(
            mispricing_percentage=0.50,  # 50% undervalued
            confidence_score=0.85,
        )
        
        assert 0.0 <= score <= 1.0
        # High mispricing + high confidence = high opportunity
        assert score > 0.7
