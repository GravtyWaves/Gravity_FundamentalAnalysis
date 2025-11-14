"""
================================================================================
FILE IDENTITY CARD (شناسنامه فایل)
================================================================================
File Path:           app/api/v1/endpoints/stock_scoring.py
Author:              Gravity Fundamental Analysis Team
Team ID:             FA-001
Created Date:        2025-01-11
Last Modified:       2025-01-20
Version:             2.0.0
Purpose:             Stock Scoring API endpoints
                     Provides fundamental analysis scoring (0-100) with ML weights

Dependencies:        fastapi>=0.104.1, app.services.stock_scoring_service

Related Files:       app/services/stock_scoring_service.py (business logic)
                     app/services/ml_weight_optimizer.py (ML weights)
                     app/tasks/scoring_tasks.py (Celery tasks)
                     app/api/v1/router.py (routes registration)

Complexity:          5/10 (REST API, validation, error handling)
Lines of Code:       217
Test Coverage:       0% (needs API integration tests - Task 6)
Performance Impact:  HIGH (public API, needs rate limiting)
Time Spent:          6 hours
Cost:                $2,880 (6 × $480/hr)
Review Status:       Production
Notes:               - Endpoints: GET /stocks/{id}/score, POST /stocks/batch-score
                     - Returns: composite_score, dimension_scores, ml_confidence
                     - Supports tenant isolation via x-tenant-id header
                     - Daily auto-calculation via Celery tasks
                     - Needs Redis caching (Task 5)
                     - Needs rate limiting (Task 11)
================================================================================
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.stock_scoring_service import StockScoringService

router = APIRouter()


@router.get("/{company_id}/score")
async def get_stock_score(
    company_id: UUID,
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Calculate comprehensive fundamental score for a stock.

    **Scoring Dimensions (ML-optimized weights):**
    - **Valuation**: P/E, P/B, PEG, EV/EBITDA ratios
    - **Profitability**: ROE, ROA, Net Margin, Operating Margin
    - **Growth**: Revenue, Earnings, Book Value growth
    - **Financial Health**: Current Ratio, Quick Ratio, Debt/Equity, Interest Coverage
    - **Risk**: Altman Z-Score, Beta, Volatility

    **Weights are dynamically optimized using machine learning models** that analyze
    historical stock performance correlation with fundamental factors.

    **Score Range:** 0-100

    **Rating Scale:**
    - A+ (90-100): Excellent fundamental strength
    - A (80-89): Strong fundamentals
    - B+ (70-79): Above average
    - B (60-69): Average
    - C+ (50-59): Below average
    - C (40-49): Weak fundamentals
    - D (30-39): Poor fundamentals
    - F (0-29): Very poor fundamentals

    **Returns:**
    - Composite score (0-100)
    - Letter rating (A+ to F)
    - ML-optimized weights used
    - **ML model confidence score (0.0-1.0)**: Indicates prediction reliability
    - **ML model performance metrics**: R², MSE, cross-validation scores
    - Individual dimension scores and breakdowns
    - Calculation date

    **ML Model Confidence Levels:**
    - 0.9-1.0 (excellent): High reliability, model performs very well
    - 0.7-0.9 (good): Reliable predictions, good model performance
    - 0.5-0.7 (moderate): Moderate reliability, acceptable performance
    - 0.3-0.5 (fair): Lower reliability, use with caution
    - 0.0-0.3 (poor): Low reliability, consider default weights

    **Note:** Scores are calculated daily via scheduled tasks.
    Use GET /health endpoint to check last calculation time.
    """
    try:
        service = StockScoringService(db, x_tenant_id)
        result = await service.calculate_composite_score(company_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating stock score: {str(e)}")


# REMOVED: /rank endpoint - Ranking functionality moved to separate microservice
# This microservice focuses on fundamental analysis and scoring only.
# For stock ranking, use the dedicated Ranking Microservice API.


@router.get("/{company_id}/valuation-score")
async def get_valuation_score(
    company_id: UUID,
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed valuation score breakdown.

    Analyzes:
    - P/E ratio score
    - P/B ratio score
    - PEG ratio score
    - EV/EBITDA score

    Returns score (0-100) and individual metric breakdowns.
    """
    try:
        service = StockScoringService(db, x_tenant_id)
        ratios = await service._get_latest_ratios(company_id)
        score, breakdown = await service.calculate_valuation_score(company_id, ratios)
        return {
            "status": "success",
            "company_id": str(company_id),
            "valuation_score": round(score, 2),
            "breakdown": breakdown,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating valuation score: {str(e)}")


@router.get("/{company_id}/profitability-score")
async def get_profitability_score(
    company_id: UUID,
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed profitability score breakdown.

    Analyzes:
    - ROE score
    - ROA score
    - Net Profit Margin score
    - Operating Margin score

    Returns score (0-100) and individual metric breakdowns.
    """
    try:
        service = StockScoringService(db, x_tenant_id)
        ratios = await service._get_latest_ratios(company_id)
        score, breakdown = await service.calculate_profitability_score(company_id, ratios)
        return {
            "status": "success",
            "company_id": str(company_id),
            "profitability_score": round(score, 2),
            "breakdown": breakdown,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating profitability score: {str(e)}")


@router.get("/{company_id}/growth-score")
async def get_growth_score(
    company_id: UUID,
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed growth score breakdown.

    Analyzes:
    - Revenue growth score
    - Earnings growth score
    - Book value growth score

    Returns score (0-100) and individual metric breakdowns.
    """
    try:
        service = StockScoringService(db, x_tenant_id)
        ratios = await service._get_latest_ratios(company_id)
        score, breakdown = await service.calculate_growth_score(company_id, ratios)
        return {
            "status": "success",
            "company_id": str(company_id),
            "growth_score": round(score, 2),
            "breakdown": breakdown,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating growth score: {str(e)}")


@router.get("/{company_id}/financial-health-score")
async def get_financial_health_score(
    company_id: UUID,
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed financial health score breakdown.

    Analyzes:
    - Current ratio score
    - Quick ratio score
    - Debt-to-equity score
    - Interest coverage score

    Returns score (0-100) and individual metric breakdowns.
    """
    try:
        service = StockScoringService(db, x_tenant_id)
        ratios = await service._get_latest_ratios(company_id)
        score, breakdown = await service.calculate_financial_health_score(company_id, ratios)
        return {
            "status": "success",
            "company_id": str(company_id),
            "financial_health_score": round(score, 2),
            "breakdown": breakdown,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating financial health score: {str(e)}")
