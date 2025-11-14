"""
===============================================================================
FILE IDENTITY CARD
===============================================================================
Filename    : valuation_scenarios.py
Created     : 2025
Author      : Elite Development Team
Department  : API Endpoints
Project     : Gravity Fundamental Analysis
Module      : Interactive What-If Scenario API
Version     : 1.0.0

Purpose     : FastAPI endpoints for interactive valuation scenario analysis.
              Allows users to modify assumptions (revenue growth, WACC, P/E)
              and see real-time impact across all methods and scenarios.

Scope       : Production API endpoints for sensitivity analysis
Components  : What-if scenarios, sensitivity analysis, tornado charts, Monte Carlo

Dependencies:
    - FastAPI (web framework)
    - Pydantic (request/response models)
    - NumPy (Monte Carlo simulation)
    - app.services (Valuation services)
    - app.core.auth (Authentication/authorization)

Output      : JSON responses with sensitivity analysis results

Notes       : Part of Task 9 - Interactive What-If Scenario API
              Provides real-time assumption modification and impact analysis
              Supports tornado charts and Monte Carlo simulation
===============================================================================
"""

from datetime import datetime
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
import numpy as np

from app.core.database import get_db
from app.core.exceptions import ValidationError, NotFoundError
from app.models.company import Company


def get_current_tenant() -> str:
    """Get current tenant ID - placeholder for multi-tenancy."""
    return "default"  # In production, extract from JWT token


router = APIRouter(prefix="/api/v1/valuations", tags=["What-If Scenarios"])


# ============================================================================
# Request/Response Models
# ============================================================================

class AssumptionModification(BaseModel):
    """Single assumption modification."""
    parameter: str = Field(..., description="Parameter to modify (e.g., 'revenue_growth', 'wacc', 'pe_ratio')")
    value: float = Field(..., description="New value for parameter")
    scenario: Optional[str] = Field(None, description="Scenario to modify (bull/base/bear), None=all")


class WhatIfRequest(BaseModel):
    """Request for what-if scenario analysis."""
    company_id: int = Field(..., description="Company ID")
    modifications: List[AssumptionModification] = Field(..., description="List of assumption modifications")
    base_scenario: str = Field("base", description="Base scenario to start from (bull/base/bear)")


class SensitivityParameter(BaseModel):
    """Parameter for sensitivity analysis."""
    parameter: str = Field(..., description="Parameter name")
    min_value: float = Field(..., description="Minimum value")
    max_value: float = Field(..., description="Maximum value")
    steps: int = Field(10, description="Number of steps", ge=3, le=50)


class SensitivityRequest(BaseModel):
    """Request for sensitivity analysis."""
    company_id: int = Field(..., description="Company ID")
    parameters: List[SensitivityParameter] = Field(..., description="Parameters to analyze")
    target_metric: str = Field("fair_value", description="Target metric to measure (fair_value/expected_return)")


class MonteCarloRequest(BaseModel):
    """Request for Monte Carlo simulation."""
    company_id: int = Field(..., description="Company ID")
    parameter_distributions: Dict[str, Dict[str, float]] = Field(
        ...,
        description="Parameters with distributions {param: {'mean': x, 'std': y}}"
    )
    num_simulations: int = Field(1000, description="Number of simulations", ge=100, le=10000)
    confidence_level: float = Field(0.95, description="Confidence level for intervals", ge=0.8, le=0.99)


class ValuationResult(BaseModel):
    """Valuation result for a single scenario."""
    scenario: str
    dcf_value: Optional[float]
    comparables_value: Optional[float]
    residual_income_value: Optional[float]
    ddm_value: Optional[float]
    asset_based_value: Optional[float]
    consensus_value: float
    expected_return_6m: Optional[float]
    expected_return_12m: Optional[float]


class WhatIfResponse(BaseModel):
    """Response for what-if scenario analysis."""
    company_id: int
    symbol: str
    company_name: str
    analysis_date: datetime
    
    # Original valuations (before modifications)
    original_valuations: List[ValuationResult]
    
    # Modified valuations (after modifications)
    modified_valuations: List[ValuationResult]
    
    # Changes
    absolute_change: float  # Consensus value change
    percentage_change: float  # % change
    
    # Applied modifications
    applied_modifications: List[AssumptionModification]


class SensitivityPoint(BaseModel):
    """Single point in sensitivity analysis."""
    parameter_value: float
    fair_value: float
    percentage_change: float  # From base value


class SensitivityResult(BaseModel):
    """Sensitivity analysis result for one parameter."""
    parameter: str
    base_value: float
    sensitivity_points: List[SensitivityPoint]
    elasticity: float  # % change in output / % change in input


class TornadoChartData(BaseModel):
    """Data for tornado chart visualization."""
    parameter: str
    low_impact: float  # Impact of min value
    high_impact: float  # Impact of max value
    total_range: float  # high - low


class SensitivityResponse(BaseModel):
    """Response for sensitivity analysis."""
    company_id: int
    symbol: str
    analysis_date: datetime
    target_metric: str
    base_value: float
    
    # Sensitivity results
    sensitivity_results: List[SensitivityResult]
    
    # Tornado chart data (sorted by total impact)
    tornado_chart: List[TornadoChartData]


class MonteCarloResult(BaseModel):
    """Monte Carlo simulation result."""
    company_id: int
    symbol: str
    analysis_date: datetime
    num_simulations: int
    
    # Distribution statistics
    mean_value: float
    median_value: float
    std_dev: float
    
    # Confidence intervals
    confidence_level: float
    confidence_interval: tuple[float, float]
    
    # Percentiles
    percentile_5: float
    percentile_25: float
    percentile_75: float
    percentile_95: float
    
    # Distribution shape
    skewness: float
    kurtosis: float
    
    # Risk metrics
    probability_negative_return: float
    value_at_risk_95: float  # VaR at 95%


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/what-if", response_model=WhatIfResponse)
async def what_if_scenario_analysis(
    request: WhatIfRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant)
):
    """
    Perform what-if scenario analysis.
    
    Modify valuation assumptions and see real-time impact across all methods.
    
    **Example modifications:**
    - `revenue_growth`: 0.15 (15% growth)
    - `wacc`: 0.12 (12% discount rate)
    - `pe_ratio`: 15.0 (P/E multiple)
    - `profit_margin`: 0.10 (10% margin)
    - `terminal_growth`: 0.03 (3% terminal growth)
    
    **Returns:**
    - Original valuations (before modifications)
    - Modified valuations (after modifications)
    - Absolute and percentage changes
    """
    # Get company
    company = await db.get(Company, request.company_id)
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company {request.company_id} not found"
        )
    if company.tenant_id != tenant_id:  # type: ignore[comparison-overlap]
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Calculate original valuations
    # (This would call actual valuation services)
    original_valuations = await _calculate_valuations(
        db, tenant_id, request.company_id, {}
    )
    
    # Apply modifications and recalculate
    modifications_dict = {
        mod.parameter: mod.value for mod in request.modifications
    }
    modified_valuations = await _calculate_valuations(
        db, tenant_id, request.company_id, modifications_dict
    )
    
    # Calculate changes
    original_consensus = np.mean([v.consensus_value for v in original_valuations])
    modified_consensus = np.mean([v.consensus_value for v in modified_valuations])
    
    absolute_change = float(modified_consensus - original_consensus)
    percentage_change = float(
        (modified_consensus - original_consensus) / original_consensus
        if original_consensus != 0 else 0.0
    )
    
    # Ensure company.id is not None for type checker
    assert company.id is not None
    
    return WhatIfResponse(
        company_id=company.id,  # type: ignore[arg-type]
        symbol=company.symbol,
        company_name=company.name_fa or company.name_en,
        analysis_date=datetime.utcnow(),
        original_valuations=original_valuations,
        modified_valuations=modified_valuations,
        absolute_change=absolute_change,
        percentage_change=percentage_change,
        applied_modifications=request.modifications
    )


@router.post("/sensitivity", response_model=SensitivityResponse)
async def sensitivity_analysis(
    request: SensitivityRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant)
):
    """
    Perform sensitivity analysis on valuation parameters.
    
    Analyze how changes in key parameters affect valuation across a range.
    
    **Example parameters:**
    - `revenue_growth`: min=0.05, max=0.25 (5% to 25%)
    - `wacc`: min=0.08, max=0.15 (8% to 15%)
    - `pe_ratio`: min=10, max=25
    
    **Returns:**
    - Sensitivity curves for each parameter
    - Tornado chart data showing relative impact
    - Elasticity metrics
    """
    # Get company
    company = await db.get(Company, request.company_id)
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company {request.company_id} not found"
        )
    if company.tenant_id != tenant_id:  # type: ignore[comparison-overlap]
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Calculate base valuation
    base_valuations = await _calculate_valuations(db, tenant_id, request.company_id, {})
    base_value = np.mean([v.consensus_value for v in base_valuations])
    
    # Analyze each parameter
    sensitivity_results = []
    tornado_data = []
    
    for param in request.parameters:
        # Create range of values
        param_values = np.linspace(param.min_value, param.max_value, param.steps)
        
        # Calculate valuation for each value
        sensitivity_points = []
        for value in param_values:
            valuations = await _calculate_valuations(
                db, tenant_id, request.company_id, {param.parameter: value}
            )
            fair_value = float(np.mean([v.consensus_value for v in valuations]))
            pct_change = float((fair_value - base_value) / base_value if base_value != 0 else 0.0)
            
            sensitivity_points.append(SensitivityPoint(
                parameter_value=float(value),
                fair_value=fair_value,
                percentage_change=pct_change
            ))
        
        # Calculate elasticity
        # % change in output / % change in input
        if len(sensitivity_points) >= 2:
            first = sensitivity_points[0]
            last = sensitivity_points[-1]
            input_change = (last.parameter_value - first.parameter_value) / first.parameter_value
            output_change = last.percentage_change - first.percentage_change
            elasticity = float(output_change / input_change if input_change != 0 else 0.0)
        else:
            elasticity = 0.0
        
        sensitivity_results.append(SensitivityResult(
            parameter=param.parameter,
            base_value=float((param.min_value + param.max_value) / 2),
            sensitivity_points=sensitivity_points,
            elasticity=elasticity
        ))
        
        # Tornado chart data
        low_val = sensitivity_points[0].fair_value
        high_val = sensitivity_points[-1].fair_value
        tornado_data.append(TornadoChartData(
            parameter=param.parameter,
            low_impact=float(low_val - base_value),
            high_impact=float(high_val - base_value),
            total_range=float(high_val - low_val)
        ))
    
    # Sort tornado chart by total impact (descending)
    tornado_data.sort(key=lambda x: abs(x.total_range), reverse=True)
    
    # Ensure company.id is not None
    assert company.id is not None
    
    return SensitivityResponse(
        company_id=company.id,  # type: ignore[arg-type]
        symbol=company.symbol,
        analysis_date=datetime.utcnow(),
        target_metric=request.target_metric,
        base_value=float(base_value),
        sensitivity_results=sensitivity_results,
        tornado_chart=tornado_data
    )


@router.post("/monte-carlo", response_model=MonteCarloResult)
async def monte_carlo_simulation(
    request: MonteCarloRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant)
):
    """
    Perform Monte Carlo simulation for valuation uncertainty.
    
    Simulate thousands of scenarios with random parameter variations
    to generate probability distribution of valuations.
    
    **Example parameter distributions:**
    ```json
    {
        "revenue_growth": {"mean": 0.15, "std": 0.05},
        "wacc": {"mean": 0.12, "std": 0.02},
        "profit_margin": {"mean": 0.10, "std": 0.03}
    }
    ```
    
    **Returns:**
    - Distribution statistics (mean, median, std)
    - Confidence intervals
    - Percentiles (5th, 25th, 75th, 95th)
    - Risk metrics (VaR, probability of loss)
    """
    # Get company
    company = await db.get(Company, request.company_id)
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company {request.company_id} not found"
        )
    if company.tenant_id != tenant_id:  # type: ignore[comparison-overlap]
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Run Monte Carlo simulation
    simulation_results = []
    
    for i in range(request.num_simulations):
        # Sample from distributions
        sampled_params = {}
        for param, dist in request.parameter_distributions.items():
            mean = dist.get("mean", 0.0)
            std = dist.get("std", 0.01)
            sampled_value = np.random.normal(mean, std)
            sampled_params[param] = sampled_value
        
        # Calculate valuation with sampled parameters
        valuations = await _calculate_valuations(
            db, tenant_id, request.company_id, sampled_params
        )
        consensus = np.mean([v.consensus_value for v in valuations])
        simulation_results.append(consensus)
    
    # Calculate statistics
    simulation_results = np.array(simulation_results)
    mean_value = np.mean(simulation_results)
    median_value = np.median(simulation_results)
    std_dev = np.std(simulation_results)
    
    # Confidence interval
    alpha = 1 - request.confidence_level
    ci_low = np.percentile(simulation_results, alpha/2 * 100)
    ci_high = np.percentile(simulation_results, (1 - alpha/2) * 100)
    
    # Percentiles
    p5 = np.percentile(simulation_results, 5)
    p25 = np.percentile(simulation_results, 25)
    p75 = np.percentile(simulation_results, 75)
    p95 = np.percentile(simulation_results, 95)
    
    # Distribution shape
    from scipy import stats
    skewness = stats.skew(simulation_results)
    kurtosis = stats.kurtosis(simulation_results)
    
    # Risk metrics
    negative_count = np.sum(simulation_results < 0)
    prob_negative = float(negative_count / len(simulation_results))
    
    var_95 = float(np.percentile(simulation_results, 5))  # VaR at 95%
    
    # Ensure company.id is not None
    assert company.id is not None
    
    return MonteCarloResult(
        company_id=company.id,  # type: ignore[arg-type]
        symbol=company.symbol,
        analysis_date=datetime.utcnow(),
        num_simulations=request.num_simulations,
        mean_value=float(mean_value),
        median_value=float(median_value),
        std_dev=float(std_dev),
        confidence_level=request.confidence_level,
        confidence_interval=(float(ci_low), float(ci_high)),
        percentile_5=float(p5),
        percentile_25=float(p25),
        percentile_75=float(p75),
        percentile_95=float(p95),
        skewness=float(skewness),
        kurtosis=float(kurtosis),
        probability_negative_return=prob_negative,
        value_at_risk_95=var_95
    )


@router.get("/{symbol}/scenarios")
async def get_predefined_scenarios(
    symbol: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant)
):
    """
    Get predefined bull/base/bear scenarios for a company.
    
    Returns valuations under three standard scenarios:
    - **Bull**: Optimistic assumptions
    - **Base**: Most likely assumptions
    - **Bear**: Conservative assumptions
    """
    # Find company by symbol
    from sqlalchemy import select
    query = select(Company).where(
        Company.symbol == symbol,
        Company.tenant_id == tenant_id
    )
    result = await db.execute(query)
    company = result.scalar_one_or_none()
    
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with symbol {symbol} not found"
        )
    
    # Calculate scenarios
    scenarios = ["bull", "base", "bear"]
    scenario_results = {}
    
    for scenario in scenarios:
        valuations = await _calculate_valuations(
            db, tenant_id, company.id, {}, scenario=scenario
        )
        scenario_results[scenario] = valuations
    
    return {
        "company_id": company.id,
        "symbol": company.symbol,
        "company_name": company.name_fa or company.name_en,
        "scenarios": scenario_results
    }


# ============================================================================
# Helper Functions
# ============================================================================

async def _calculate_valuations(
    db: AsyncSession,
    tenant_id: str,
    company_id: int,
    modifications: Dict[str, float],
    scenario: str = "base"
) -> List[ValuationResult]:
    """
    Calculate valuations with optional modifications.
    
    This is a placeholder - in production, would call actual valuation services
    with modified parameters.
    """
    # Placeholder: return mock valuations
    # In production, would:
    # 1. Get company financial data
    # 2. Apply modifications to assumptions
    # 3. Run all 5 valuation methods
    # 4. Return results
    
    base_value = 100000.0  # Mock base value
    
    # Apply simple modification effect
    modifier = 1.0
    for param, value in modifications.items():
        if "growth" in param.lower():
            modifier *= (1 + value)
        elif "wacc" in param.lower():
            modifier *= (1 / (1 + value))
    
    return [
        ValuationResult(
            scenario=scenario,
            dcf_value=base_value * modifier * 1.1,
            comparables_value=base_value * modifier * 1.05,
            residual_income_value=base_value * modifier * 0.95,
            ddm_value=base_value * modifier * 0.90,
            asset_based_value=base_value * modifier * 0.85,
            consensus_value=base_value * modifier,
            expected_return_6m=0.15 * modifier,
            expected_return_12m=0.25 * modifier
        )
    ]
