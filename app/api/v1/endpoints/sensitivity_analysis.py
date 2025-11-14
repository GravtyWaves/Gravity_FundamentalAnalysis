"""
Sensitivity Analysis API endpoints.
"""

from typing import Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Header, Body, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.sensitivity_analysis_service import SensitivityAnalysisService

router = APIRouter()


@router.post("/{company_id}/one-way")
async def one_way_sensitivity_analysis(
    company_id: UUID,
    base_params: Dict = Body(...),
    variable: str = Query(...),
    variation_min: float = Query(-0.30, description="Minimum variation (-30% = -0.30)"),
    variation_max: float = Query(0.30, description="Maximum variation (+30% = 0.30)"),
    num_points: int = Query(11, ge=5, le=50, description="Number of data points"),
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    One-way sensitivity analysis (Tornado chart data).

    Analyzes how changes in ONE variable affect valuation while keeping others constant.

    **Common Variables:**
    - `wacc`: Weighted Average Cost of Capital
    - `terminal_growth`: Terminal growth rate
    - `fcf`: Free Cash Flow

    **Request Body (base_params):**
    ```json
    {
        "fcf": 100.0,
        "wacc": 0.10,
        "terminal_growth": 0.025,
        "years": 5
    }
    ```

    **Query Parameters:**
    - `variable`: Variable to analyze (e.g., "wacc")
    - `variation_min`: Minimum variation as decimal (default: -0.30 for -30%)
    - `variation_max`: Maximum variation as decimal (default: 0.30 for +30%)
    - `num_points`: Number of data points (default: 11)

    **Returns:**
    - Sensitivity data showing enterprise value at different variable levels
    - Percentage change from base case
    - Useful for creating Tornado charts
    """
    try:
        service = SensitivityAnalysisService(db, x_tenant_id)
        result = await service.one_way_sensitivity(
            company_id,
            base_params,
            variable,
            (variation_min, variation_max),
            num_points,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in one-way sensitivity: {str(e)}")


@router.post("/{company_id}/two-way")
async def two_way_sensitivity_analysis(
    company_id: UUID,
    base_params: Dict = Body(...),
    variable_x: str = Query(..., description="First variable (e.g., 'wacc')"),
    variable_y: str = Query(..., description="Second variable (e.g., 'terminal_growth')"),
    variation_min: float = Query(-0.20, description="Minimum variation"),
    variation_max: float = Query(0.20, description="Maximum variation"),
    num_points: int = Query(7, ge=3, le=15, description="Points per variable"),
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Two-way sensitivity analysis (sensitivity table).

    Analyzes how changes in TWO variables simultaneously affect valuation.

    **Example Use Case:**
    Analyze how different combinations of WACC and terminal growth rate affect fair value.

    **Request Body (base_params):**
    ```json
    {
        "fcf": 100.0,
        "wacc": 0.10,
        "terminal_growth": 0.025,
        "years": 5
    }
    ```

    **Query Parameters:**
    - `variable_x`: First variable (e.g., "wacc")
    - `variable_y`: Second variable (e.g., "terminal_growth")
    - `variation_min`: Minimum variation (default: -20%)
    - `variation_max`: Maximum variation (default: +20%)
    - `num_points`: Points per variable (default: 7, creates 7x7 table)

    **Returns:**
    - 2D sensitivity table
    - Enterprise value for each combination of variable_x and variable_y
    - Useful for data tables in Excel or heatmaps
    """
    try:
        service = SensitivityAnalysisService(db, x_tenant_id)
        result = await service.two_way_sensitivity(
            company_id,
            base_params,
            variable_x,
            variable_y,
            (variation_min, variation_max),
            num_points,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in two-way sensitivity: {str(e)}")


@router.post("/{company_id}/monte-carlo")
async def monte_carlo_simulation(
    company_id: UUID,
    base_params: Dict = Body(...),
    variable_distributions: Dict = Body(...),
    num_simulations: int = Query(10000, ge=1000, le=100000),
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Monte Carlo simulation for valuation uncertainty.

    Runs thousands of simulations with random variations in key inputs
    to generate a distribution of possible valuation outcomes.

    **Request Body:**
    ```json
    {
        "base_params": {
            "fcf": 100.0,
            "wacc": 0.10,
            "terminal_growth": 0.025,
            "years": 5
        },
        "variable_distributions": {
            "wacc": {"mean": 0.10, "std": 0.02},
            "terminal_growth": {"mean": 0.025, "std": 0.01}
        }
    }
    ```

    **Query Parameters:**
    - `num_simulations`: Number of Monte Carlo iterations (default: 10,000)

    **Returns:**
    - Statistical distribution (mean, median, std dev)
    - Percentiles (P5, P10, P25, P50, P75, P90, P95)
    - Confidence intervals (80%, 90%)
    - Min/max values

    **Use Cases:**
    - Risk analysis: What's the probability of achieving target valuation?
    - Confidence intervals: "90% confident value is between X and Y"
    - Stress testing: Understanding downside scenarios
    """
    try:
        service = SensitivityAnalysisService(db, x_tenant_id)
        result = await service.monte_carlo_simulation(
            company_id,
            base_params,
            variable_distributions,
            num_simulations,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in Monte Carlo simulation: {str(e)}")


@router.post("/{company_id}/tornado-chart")
async def tornado_chart_analysis(
    company_id: UUID,
    base_params: Dict = Body(...),
    variables: List[str] = Body(...),
    variation_pct: float = Query(0.20, ge=0.05, le=0.50, description="Variation percentage"),
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Tornado chart data - ranked sensitivity analysis.

    Analyzes multiple variables and ranks them by their impact on valuation.
    Most impactful variables appear at the top (like a tornado shape).

    **Request Body:**
    ```json
    {
        "base_params": {
            "fcf": 100.0,
            "wacc": 0.10,
            "terminal_growth": 0.025,
            "years": 5
        },
        "variables": ["wacc", "terminal_growth", "fcf"]
    }
    ```

    **Query Parameters:**
    - `variation_pct`: How much to vary each variable (default: 0.20 for ±20%)

    **Returns:**
    - Ranked list of variables by impact
    - For each variable:
      - Impact range (difference between high and low scenarios)
      - Upside/downside percentages
      - Enterprise value at high/low scenarios
    - Sorted from most impactful to least impactful

    **Use Cases:**
    - Identify key value drivers
    - Focus analysis on most impactful assumptions
    - Visualize as Tornado chart for presentations
    """
    try:
        service = SensitivityAnalysisService(db, x_tenant_id)
        result = await service.tornado_chart_data(
            company_id,
            base_params,
            variables,
            variation_pct,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in tornado chart analysis: {str(e)}")
