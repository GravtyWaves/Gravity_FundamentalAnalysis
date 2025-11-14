"""
Value Drivers Analysis API endpoints.
"""

from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.value_drivers_service import ValueDriversService

router = APIRouter()


@router.get("/{company_id}/dupont")
async def dupont_analysis(
    company_id: UUID,
    period_end_date: Optional[date] = Query(None),
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    DuPont Analysis - decompose ROE into fundamental drivers.

    **Formula:**
    ```
    ROE = Net Profit Margin × Asset Turnover × Equity Multiplier
    ROE = (Net Income/Revenue) × (Revenue/Assets) × (Assets/Equity)
    ```

    **Purpose:**
    Reveals whether ROE is driven by:
    - **Profitability** (Net Profit Margin): How much profit per dollar of sales
    - **Efficiency** (Asset Turnover): How efficiently assets generate sales
    - **Leverage** (Equity Multiplier): Financial leverage usage

    **Query Parameters:**
    - `period_end_date` (optional): Specific period to analyze. If not provided, uses latest available.

    **Returns:**
    - 3-Level DuPont decomposition
    - Component values and interpretation
    - Raw financial values
    - Driver categorization (High/Low for each component)

    **Example Response:**
    ```json
    {
        "three_level_dupont": {
            "roe": 0.1524,
            "components": {
                "net_profit_margin": 0.12,
                "asset_turnover": 1.05,
                "equity_multiplier": 1.21
            },
            "interpretation": {
                "profitability_driver": "High",
                "efficiency_driver": "High",
                "leverage_driver": "Low"
            }
        }
    }
    ```
    """
    try:
        service = ValueDriversService(db, x_tenant_id)
        result = await service.dupont_analysis(company_id, period_end_date)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in DuPont analysis: {str(e)}")


@router.get("/{company_id}/revenue-drivers")
async def revenue_drivers_analysis(
    company_id: UUID,
    num_periods: int = Query(5, ge=2, le=20, description="Number of periods to analyze"),
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Revenue growth drivers analysis.

    Analyzes historical revenue growth across multiple periods to identify:
    - Revenue CAGR (Compound Annual Growth Rate)
    - Period-over-period growth rates
    - Revenue trends and patterns

    **Use Cases:**
    - Identify revenue acceleration/deceleration
    - Forecast future revenue based on historical growth
    - Compare revenue growth to industry benchmarks

    **Returns:**
    - Revenue CAGR over the analysis period
    - Period-by-period analysis with:
      - Revenue value
      - Previous period revenue
      - Growth percentage
      - Absolute revenue change
    """
    try:
        service = ValueDriversService(db, x_tenant_id)
        result = await service.revenue_drivers(company_id, num_periods)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in revenue drivers analysis: {str(e)}")


@router.get("/{company_id}/margin-drivers")
async def margin_drivers_analysis(
    company_id: UUID,
    num_periods: int = Query(5, ge=2, le=20, description="Number of periods to analyze"),
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Margin drivers analysis (waterfall from gross to net margin).

    Tracks margin evolution through income statement levels:
    - **Gross Margin**: Revenue - COGS
    - **Operating Margin**: Gross Profit - Operating Expenses
    - **Net Margin**: Operating Income - Taxes & Interest

    **Margin Compression Analysis:**
    Shows how much margin is lost at each level:
    - Gross → Operating: Impact of operating expenses
    - Operating → Net: Impact of taxes, interest, non-operating items
    - Total compression: Full margin erosion from gross to net

    **Use Cases:**
    - Identify margin expansion/compression trends
    - Pinpoint which expense category is affecting profitability
    - Compare margins to competitors

    **Returns:**
    - Historical margin trends (gross, operating, net)
    - Margin compression breakdown
    - Period-by-period comparison
    """
    try:
        service = ValueDriversService(db, x_tenant_id)
        result = await service.margin_drivers(company_id, num_periods)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in margin drivers analysis: {str(e)}")


@router.get("/{company_id}/capital-efficiency")
async def capital_efficiency_analysis(
    company_id: UUID,
    period_end_date: Optional[date] = Query(None),
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Capital efficiency drivers analysis.

    Measures how efficiently the company uses its capital to generate revenue:

    **Key Metrics:**
    - **Asset Turnover** = Revenue / Total Assets
      - Measures overall asset efficiency
      - Higher = better utilization
      - Benchmark: >1.0 is generally good

    - **Fixed Asset Turnover** = Revenue / PP&E
      - Measures efficiency of fixed assets (plant, equipment)
      - Important for capital-intensive industries
      - Benchmark: >2.0 is generally good

    - **Working Capital Turnover** = Revenue / Working Capital
      - Measures efficiency of working capital usage
      - Higher = better working capital management
      - Benchmark: >5.0 is generally efficient

    **Use Cases:**
    - Assess operational efficiency
    - Compare to industry peers
    - Identify over/under-investment in assets

    **Returns:**
    - Efficiency metrics with benchmarks
    - Interpretation (High/Low efficiency)
    - Raw financial values
    """
    try:
        service = ValueDriversService(db, x_tenant_id)
        result = await service.capital_efficiency_drivers(company_id, period_end_date)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in capital efficiency analysis: {str(e)}")


@router.get("/{company_id}/waterfall")
async def waterfall_analysis(
    company_id: UUID,
    metric: str = Query("net_income", description="Metric to analyze (net_income, revenue, ebitda)"),
    num_periods: int = Query(2, ge=2, le=5),
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Waterfall analysis - period-over-period changes breakdown.

    Visualizes how a metric changed from one period to another,
    showing the contribution of each component.

    **Supported Metrics:**
    - `net_income`: Shows how net income changed (revenue, COGS, OpEx impacts)
    - `revenue`: Shows revenue growth components
    - `ebitda`: Shows EBITDA changes

    **Example (Net Income Waterfall):**
    ```
    Starting Net Income: 100
    + Revenue Change: +20
    - COGS Change: -8
    - OpEx Change: -5
    = Ending Net Income: 107
    ```

    **Use Cases:**
    - Explain earnings changes to stakeholders
    - Identify which components drove performance
    - Create waterfall charts for presentations

    **Returns:**
    - Total change (absolute and percentage)
    - Component breakdown
    - Starting and ending values
    - Period comparison
    """
    try:
        service = ValueDriversService(db, x_tenant_id)
        result = await service.waterfall_analysis(company_id, metric, num_periods)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in waterfall analysis: {str(e)}")
