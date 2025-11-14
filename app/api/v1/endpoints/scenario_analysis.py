"""
Scenario Analysis API endpoints.
"""

from typing import Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Header, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.scenario_analysis_service import ScenarioAnalysisService

router = APIRouter()


@router.post("/{company_id}/valuation-scenarios")
async def analyze_valuation_scenarios(
    company_id: UUID,
    dcf_params: Dict = Body(...),
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Perform DCF valuation analysis under three scenarios.

    **Scenarios:**
    - **Optimistic (Bull Case)**: 25% higher growth, 15% margin expansion, 10% lower WACC
    - **Neutral (Base Case)**: Current/realistic assumptions
    - **Pessimistic (Bear Case)**: 30% lower growth, 15% margin compression, 15% higher WACC

    **Request Body:**
    ```json
    {
        "expected_fair_value": 100.0,
        "current_price": 90.0,
        "revenue_growth": [0.10, 0.08, 0.06],
        "ebitda_margin": 0.20,
        "wacc": 0.10,
        "terminal_growth": 0.025,
        "capex_pct": 0.05
    }
    ```

    **Returns:**
    - Fair value per share for each scenario
    - Upside/downside percentages
    - Probability-weighted expected value
    - Risk-reward ratio
    """
    try:
        service = ScenarioAnalysisService(db, x_tenant_id)
        result = await service.analyze_valuation_scenarios(company_id, dcf_params)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in valuation scenario analysis: {str(e)}")


@router.post("/{company_id}/comprehensive-scenarios")
async def analyze_comprehensive_scenarios(
    company_id: UUID,
    dcf_params: Optional[Dict] = Body(None),
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Comprehensive scenario analysis including valuation, risk, and projections.

    Combines:
    - Valuation scenarios (DCF with three scenarios)
    - Risk scenarios (financial, operational, market risk)
    - Investment recommendation

    **Request Body (optional):**
    ```json
    {
        "expected_fair_value": 100.0,
        "current_price": 90.0,
        "revenue_growth": [0.10, 0.08, 0.06],
        "ebitda_margin": 0.20,
        "wacc": 0.10,
        "terminal_growth": 0.025
    }
    ```

    If not provided, uses default assumptions.

    **Returns:**
    - Complete scenario analysis across all dimensions
    - Investment recommendation (Strong Buy/Buy/Hold/Sell/Strong Sell)
    - Confidence level and rationale
    """
    try:
        service = ScenarioAnalysisService(db, x_tenant_id)
        result = await service.analyze_comprehensive_scenarios(company_id, dcf_params)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in comprehensive scenario analysis: {str(e)}")
