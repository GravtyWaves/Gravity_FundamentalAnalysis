"""
Risk Assessment API endpoints.

Endpoints for comprehensive risk analysis including:
- Altman Z-Score
- Beta, Volatility, VaR
- Component risk scores
- Three-scenario analysis (Optimistic, Neutral, Pessimistic)
"""

from datetime import date
from typing import Any, Dict
from uuid import UUID
import logging

from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.risk_assessment_service import RiskAssessmentService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/risk-assessments", tags=["Risk Assessment"])


@router.post("/{company_id}", status_code=status.HTTP_201_CREATED)
async def assess_company_risk(
    company_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
) -> Dict[str, Any]:
    """
    Perform comprehensive risk assessment with three scenarios.

    Scenarios:
    - **Optimistic**: 20% improvement in risk metrics (best case)
    - **Neutral**: Current market conditions (base case)
    - **Pessimistic**: 30% deterioration in risk metrics (worst case)

    Includes:
    - Altman Z-Score (bankruptcy prediction)
    - Beta (market risk)
    - Volatility (30-day, 90-day)
    - Value at Risk (VaR 95%)
    - Component risk scores (Financial, Operational, Business, Market, ESG)

    Args:
        company_id: Company UUID
        tenant_id: Tenant identifier from header

    Returns:
        Risk assessment results for all three scenarios
    """
    try:
        service = RiskAssessmentService(db, tenant_id)
        result = await service.assess_risk_with_scenarios(company_id)

        return {
            "status": "success",
            "message": "Risk assessment completed successfully",
            "data": result,
        }

    except ValueError as e:
        logger.error(f"Validation error in risk assessment: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error in risk assessment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Risk assessment failed",
        )


@router.get("/{company_id}/latest")
async def get_latest_risk_assessment(
    company_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
) -> Dict[str, Any]:
    """
    Get latest risk assessment for a company.

    Args:
        company_id: Company UUID
        tenant_id: Tenant identifier from header

    Returns:
        Latest risk assessment data
    """
    try:
        service = RiskAssessmentService(db, tenant_id)
        assessment = await service.get_latest_risk_assessment(company_id)

        if not assessment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No risk assessment found for this company",
            )

        return {
            "status": "success",
            "data": {
                "id": str(assessment.id),
                "company_id": str(assessment.company_id),
                "assessment_date": assessment.assessment_date.isoformat(),
                "overall_risk_score": float(assessment.overall_risk_score) if assessment.overall_risk_score else None,
                "risk_rating": assessment.risk_rating,
                "component_risks": {
                    "business_risk": float(assessment.business_risk_score) if assessment.business_risk_score else None,
                    "financial_risk": float(assessment.financial_risk_score) if assessment.financial_risk_score else None,
                    "operational_risk": float(assessment.operational_risk_score) if assessment.operational_risk_score else None,
                    "market_risk": float(assessment.market_risk_score) if assessment.market_risk_score else None,
                    "esg_risk": float(assessment.esg_risk_score) if assessment.esg_risk_score else None,
                },
                "metrics": {
                    "altman_z_score": float(assessment.altman_z_score) if assessment.altman_z_score else None,
                    "beta": float(assessment.beta) if assessment.beta else None,
                    "volatility_30d": float(assessment.volatility_30d) if assessment.volatility_30d else None,
                    "volatility_90d": float(assessment.volatility_90d) if assessment.volatility_90d else None,
                    "value_at_risk_95": float(assessment.value_at_risk_95) if assessment.value_at_risk_95 else None,
                },
                "risk_factors": assessment.risk_factors,
                "risk_details": assessment.risk_details,
                "created_at": assessment.created_at.isoformat(),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching risk assessment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch risk assessment",
        )


@router.get("/{company_id}/altman-z-score")
async def calculate_altman_z_score(
    company_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
) -> Dict[str, Any]:
    """
    Calculate Altman Z-Score for bankruptcy prediction.

    **Interpretation:**
    - Z > 2.99: Safe Zone (low bankruptcy risk)
    - 1.81 < Z < 2.99: Grey Zone (moderate risk)
    - Z < 1.81: Distress Zone (high bankruptcy risk)

    Args:
        company_id: Company UUID
        tenant_id: Tenant identifier from header

    Returns:
        Altman Z-Score and interpretation
    """
    try:
        from app.models.financial_statements import BalanceSheet, IncomeStatement
        from app.models.valuation_risk import MarketData
        from sqlalchemy import select, and_

        service = RiskAssessmentService(db, tenant_id)

        # Get latest financial data
        bs_query = select(BalanceSheet).where(
            and_(
                BalanceSheet.company_id == company_id,
                BalanceSheet.tenant_id == tenant_id,
            )
        ).order_by(BalanceSheet.fiscal_year.desc()).limit(1)

        is_query = select(IncomeStatement).where(
            and_(
                IncomeStatement.company_id == company_id,
                IncomeStatement.tenant_id == tenant_id,
            )
        ).order_by(IncomeStatement.fiscal_year.desc()).limit(1)

        md_query = select(MarketData).where(
            and_(
                MarketData.company_id == company_id,
                MarketData.tenant_id == tenant_id,
            )
        ).order_by(MarketData.date.desc()).limit(1)

        bs_result = await db.execute(bs_query)
        is_result = await db.execute(is_query)
        md_result = await db.execute(md_query)

        balance_sheet = bs_result.scalar_one_or_none()
        income_statement = is_result.scalar_one_or_none()
        market_data = md_result.scalar_one_or_none()

        if not balance_sheet or not income_statement:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Insufficient financial data",
            )

        market_cap = market_data.market_cap if market_data else None

        result = await service.calculate_altman_z_score(
            company_id, balance_sheet, income_statement, market_cap
        )

        return {
            "status": "success",
            "data": {
                "z_score": float(result["z_score"]),
                "interpretation": result["interpretation"],
                "risk_level": result["risk_level"],
                "components": {
                    k: float(v) for k, v in result.get("components", {}).items()
                } if "components" in result else None,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating Altman Z-Score: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate Altman Z-Score",
        )


@router.get("/{company_id}/beta")
async def calculate_beta(
    company_id: UUID,
    period_days: int = 252,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
) -> Dict[str, Any]:
    """
    Calculate Beta (market risk measure).

    Beta measures the volatility of a stock relative to the market:
    - Beta = 1.0: Stock moves with the market
    - Beta > 1.0: Stock is more volatile than market
    - Beta < 1.0: Stock is less volatile than market

    Args:
        company_id: Company UUID
        period_days: Number of trading days (default: 252 = 1 year)
        tenant_id: Tenant identifier from header

    Returns:
        Beta value
    """
    try:
        service = RiskAssessmentService(db, tenant_id)
        beta = await service.calculate_beta(company_id, period_days)

        if beta is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Insufficient market data for beta calculation",
            )

        return {
            "status": "success",
            "data": {
                "beta": float(beta),
                "period_days": period_days,
                "interpretation": (
                    "High volatility (more risky than market)" if beta > 1.2 else
                    "Market volatility" if beta > 0.8 else
                    "Low volatility (less risky than market)"
                ),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating beta: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate beta",
        )


@router.get("/{company_id}/volatility")
async def calculate_volatility(
    company_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
) -> Dict[str, Any]:
    """
    Calculate historical volatility.

    Returns both 30-day and 90-day annualized volatility.

    Args:
        company_id: Company UUID
        tenant_id: Tenant identifier from header

    Returns:
        Volatility metrics
    """
    try:
        service = RiskAssessmentService(db, tenant_id)

        volatility_30d = await service.calculate_volatility(company_id, 30)
        volatility_90d = await service.calculate_volatility(company_id, 90)

        return {
            "status": "success",
            "data": {
                "volatility_30d": float(volatility_30d) if volatility_30d else None,
                "volatility_90d": float(volatility_90d) if volatility_90d else None,
                "interpretation": {
                    "30d": (
                        "High volatility" if volatility_30d and volatility_30d > 0.4 else
                        "Moderate volatility" if volatility_30d and volatility_30d > 0.2 else
                        "Low volatility" if volatility_30d else
                        "Insufficient data"
                    ),
                    "90d": (
                        "High volatility" if volatility_90d and volatility_90d > 0.4 else
                        "Moderate volatility" if volatility_90d and volatility_90d > 0.2 else
                        "Low volatility" if volatility_90d else
                        "Insufficient data"
                    ),
                },
            },
        }

    except Exception as e:
        logger.error(f"Error calculating volatility: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate volatility",
        )


@router.get("/{company_id}/value-at-risk")
async def calculate_value_at_risk(
    company_id: UUID,
    confidence_level: float = 0.95,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
) -> Dict[str, Any]:
    """
    Calculate Value at Risk (VaR).

    VaR estimates the maximum loss over a given period at a specified confidence level.

    Args:
        company_id: Company UUID
        confidence_level: Confidence level (0.95 or 0.99)
        tenant_id: Tenant identifier from header

    Returns:
        VaR value and interpretation
    """
    try:
        if confidence_level not in [0.95, 0.99]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Confidence level must be 0.95 or 0.99",
            )

        service = RiskAssessmentService(db, tenant_id)
        var = await service.calculate_value_at_risk(company_id, confidence_level, 30)

        if var is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Insufficient market data for VaR calculation",
            )

        return {
            "status": "success",
            "data": {
                "value_at_risk": float(var),
                "confidence_level": confidence_level,
                "interpretation": (
                    f"With {confidence_level*100}% confidence, "
                    f"the maximum daily loss is {abs(float(var))*100:.2f}%"
                ),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating VaR: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate VaR",
        )
