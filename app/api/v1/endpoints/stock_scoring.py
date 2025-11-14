"""
Stock Scoring and Ranking API endpoints.
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

    **Scoring Dimensions (weighted):**
    - **Valuation (25%)**: P/E, P/B, PEG, EV/EBITDA ratios
    - **Profitability (20%)**: ROE, ROA, Net Margin, Operating Margin
    - **Growth (20%)**: Revenue, Earnings, Book Value growth
    - **Financial Health (20%)**: Current Ratio, Quick Ratio, Debt/Equity, Interest Coverage
    - **Risk (15%)**: Altman Z-Score, Beta, Volatility

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
    - Individual dimension scores and breakdowns
    - Calculation date
    """
    try:
        service = StockScoringService(db, x_tenant_id)
        result = await service.calculate_composite_score(company_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating stock score: {str(e)}")


@router.post("/rank")
async def rank_stocks(
    company_ids: Optional[List[UUID]] = Query(None),
    min_score: Optional[float] = Query(None, ge=0, le=100),
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Rank stocks by fundamental score.

    **Query Parameters:**
    - **company_ids** (optional): List of company UUIDs to rank. If not provided, ranks all companies in tenant.
    - **min_score** (optional): Minimum score filter (0-100). Only stocks with score >= min_score are returned.

    **Returns:**
    - List of stocks sorted by composite score (descending)
    - Each stock includes:
      - Rank (1 = highest score)
      - Company ID, ticker, name
      - Composite score and rating
      - Individual dimension scores

    **Example:**
    ```
    GET /api/v1/stock-scoring/rank?min_score=60
    ```
    Returns only stocks with score >= 60, ranked from highest to lowest.
    """
    try:
        service = StockScoringService(db, x_tenant_id)
        result = await service.rank_stocks(company_ids, min_score)
        return {
            "status": "success",
            "total_stocks": len(result),
            "rankings": result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error ranking stocks: {str(e)}")


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
