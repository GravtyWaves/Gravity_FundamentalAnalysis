"""
Trend Analysis API endpoints.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.trend_analysis_service import TrendAnalysisService

router = APIRouter()


@router.get("/{company_id}/revenue-trend")
async def get_revenue_trend(
    company_id: UUID,
    num_years: int = 5,
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Analyze revenue trend for a company.

    - **company_id**: Company UUID
    - **num_years**: Number of years to analyze (default: 5)
    
    Returns:
    - CAGR (Compound Annual Growth Rate)
    - Year-over-year growth rates
    - Linear regression analysis (slope, R², p-value)
    - Trend direction and strength
    - Anomalies detected
    """
    try:
        service = TrendAnalysisService(db, x_tenant_id)
        result = await service.analyze_revenue_trend(company_id, num_years)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing revenue trend: {str(e)}")


@router.get("/{company_id}/profitability-trends")
async def get_profitability_trends(
    company_id: UUID,
    num_years: int = 5,
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Analyze profitability trends for a company.

    Analyzes trends for:
    - Gross margin
    - Operating margin
    - Net profit margin
    - ROE (Return on Equity)
    - ROA (Return on Assets)

    Returns regression analysis, moving averages, and anomaly detection for each metric.
    """
    try:
        service = TrendAnalysisService(db, x_tenant_id)
        result = await service.analyze_profitability_trends(company_id, num_years)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing profitability trends: {str(e)}")


@router.get("/{company_id}/ratio-trend/{ratio_name}")
async def get_ratio_trend(
    company_id: UUID,
    ratio_name: str,
    num_periods: int = 8,
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Analyze trend for a specific financial ratio.

    - **company_id**: Company UUID
    - **ratio_name**: Name of the ratio to analyze
    - **num_periods**: Number of periods to analyze (default: 8)

    Returns:
    - Trend direction (improving, stable, declining)
    - Regression analysis (slope, R², p-value)
    - Moving averages
    - Anomalies
    - Volatility (coefficient of variation)
    """
    try:
        service = TrendAnalysisService(db, x_tenant_id)
        result = await service.analyze_ratio_trend(company_id, ratio_name, num_periods)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing ratio trend: {str(e)}")
