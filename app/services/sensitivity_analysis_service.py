"""
Sensitivity Analysis Service.

Analyzes how changes in key assumptions affect valuation and financial metrics.

Types of sensitivity analysis:
- One-way sensitivity (Tornado charts)
- Two-way sensitivity tables
- Monte Carlo simulation
- DCF sensitivity to WACC and growth rate
"""

from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from uuid import UUID
import logging
import numpy as np

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class SensitivityAnalysisService:
    """Service for sensitivity analysis."""

    def __init__(self, db: AsyncSession, tenant_id: str):
        """
        Initialize sensitivity analysis service.

        Args:
            db: Database session
            tenant_id: Current tenant ID
        """
        self.db = db
        self.tenant_id = str(tenant_id) if isinstance(tenant_id, UUID) else tenant_id

    def dcf_valuation_simple(
        self,
        fcf: float,
        wacc: float,
        terminal_growth: float,
        years: int = 5,
    ) -> float:
        """
        Simple DCF valuation calculation.

        Args:
            fcf: Free cash flow (current year)
            wacc: Weighted Average Cost of Capital (as decimal, e.g., 0.10 for 10%)
            terminal_growth: Terminal growth rate (as decimal)
            years: Projection years

        Returns:
            Enterprise value
        """
        pv_fcf = 0
        current_fcf = fcf

        # Present value of projected FCF
        for year in range(1, years + 1):
            current_fcf *= (1 + terminal_growth)
            discount_factor = (1 + wacc) ** year
            pv_fcf += current_fcf / discount_factor

        # Terminal value
        terminal_fcf = current_fcf * (1 + terminal_growth)
        terminal_value = terminal_fcf / (wacc - terminal_growth)
        pv_terminal = terminal_value / ((1 + wacc) ** years)

        enterprise_value = pv_fcf + pv_terminal
        return enterprise_value

    async def one_way_sensitivity(
        self,
        company_id: UUID,
        base_params: Dict[str, float],
        variable: str,
        variation_range: Tuple[float, float] = (-0.30, 0.30),
        num_points: int = 11,
    ) -> Dict[str, any]:
        """
        One-way sensitivity analysis (Tornado chart data).

        Varies one input variable while keeping others constant.

        Args:
            company_id: Company UUID
            base_params: Base case parameters (fcf, wacc, terminal_growth, etc.)
            variable: Variable to analyze ("wacc", "terminal_growth", "fcf")
            variation_range: Percentage range to vary (e.g., -30% to +30%)
            num_points: Number of data points

        Returns:
            Sensitivity results with values at different input levels
        """
        try:
            base_value = base_params.get(variable)
            if base_value is None:
                raise ValueError(f"Variable '{variable}' not found in base parameters")

            # Generate variation points
            variations = np.linspace(
                base_value * (1 + variation_range[0]),
                base_value * (1 + variation_range[1]),
                num_points
            )

            results = []
            for varied_value in variations:
                # Update parameters with varied value
                params = base_params.copy()
                params[variable] = varied_value

                # Calculate valuation
                enterprise_value = self.dcf_valuation_simple(
                    fcf=params.get("fcf", 100),
                    wacc=params.get("wacc", 0.10),
                    terminal_growth=params.get("terminal_growth", 0.025),
                    years=params.get("years", 5),
                )

                # Calculate change from base
                base_ev = self.dcf_valuation_simple(
                    fcf=base_params.get("fcf", 100),
                    wacc=base_params.get("wacc", 0.10),
                    terminal_growth=base_params.get("terminal_growth", 0.025),
                    years=base_params.get("years", 5),
                )
                
                change_pct = ((enterprise_value - base_ev) / base_ev) * 100

                results.append({
                    f"{variable}_value": round(float(varied_value), 4),
                    f"{variable}_change_pct": round(((varied_value - base_value) / base_value) * 100, 2),
                    "enterprise_value": round(enterprise_value, 2),
                    "ev_change_pct": round(change_pct, 2),
                })

            return {
                "status": "success",
                "company_id": str(company_id),
                "analysis_type": "one_way_sensitivity",
                "variable": variable,
                "base_value": base_value,
                "base_enterprise_value": round(base_ev, 2),
                "sensitivity_data": results,
            }

        except Exception as e:
            logger.error(f"Error in one-way sensitivity analysis: {e}")
            raise

    async def two_way_sensitivity(
        self,
        company_id: UUID,
        base_params: Dict[str, float],
        variable_x: str,
        variable_y: str,
        variation_range: Tuple[float, float] = (-0.20, 0.20),
        num_points: int = 7,
    ) -> Dict[str, any]:
        """
        Two-way sensitivity analysis (sensitivity table).

        Varies two input variables simultaneously.

        Args:
            company_id: Company UUID
            base_params: Base case parameters
            variable_x: First variable (e.g., "wacc")
            variable_y: Second variable (e.g., "terminal_growth")
            variation_range: Percentage range to vary
            num_points: Number of points for each variable

        Returns:
            2D sensitivity table
        """
        try:
            base_x = base_params.get(variable_x)
            base_y = base_params.get(variable_y)

            if base_x is None or base_y is None:
                raise ValueError(f"Variables not found in base parameters")

            # Generate variations
            variations_x = np.linspace(
                base_x * (1 + variation_range[0]),
                base_x * (1 + variation_range[1]),
                num_points
            )
            variations_y = np.linspace(
                base_y * (1 + variation_range[0]),
                base_y * (1 + variation_range[1]),
                num_points
            )

            # Build sensitivity table
            table = []
            for val_y in variations_y:
                row = {f"{variable_y}": round(float(val_y), 4)}
                row["values"] = []
                
                for val_x in variations_x:
                    params = base_params.copy()
                    params[variable_x] = val_x
                    params[variable_y] = val_y

                    enterprise_value = self.dcf_valuation_simple(
                        fcf=params.get("fcf", 100),
                        wacc=params.get("wacc", 0.10),
                        terminal_growth=params.get("terminal_growth", 0.025),
                        years=params.get("years", 5),
                    )
                    
                    row["values"].append(round(enterprise_value, 2))
                
                table.append(row)

            # Base case valuation
            base_ev = self.dcf_valuation_simple(
                fcf=base_params.get("fcf", 100),
                wacc=base_params.get("wacc", 0.10),
                terminal_growth=base_params.get("terminal_growth", 0.025),
                years=base_params.get("years", 5),
            )

            return {
                "status": "success",
                "company_id": str(company_id),
                "analysis_type": "two_way_sensitivity",
                "variable_x": variable_x,
                "variable_y": variable_y,
                "base_x": base_x,
                "base_y": base_y,
                "base_enterprise_value": round(base_ev, 2),
                "x_values": [round(float(v), 4) for v in variations_x],
                "sensitivity_table": table,
            }

        except Exception as e:
            logger.error(f"Error in two-way sensitivity analysis: {e}")
            raise

    async def monte_carlo_simulation(
        self,
        company_id: UUID,
        base_params: Dict[str, float],
        variable_distributions: Dict[str, Dict[str, float]],
        num_simulations: int = 10000,
    ) -> Dict[str, any]:
        """
        Monte Carlo simulation for valuation.

        Simulates thousands of scenarios with random variations in key inputs.

        Args:
            company_id: Company UUID
            base_params: Base case parameters
            variable_distributions: Distribution parameters for each variable
                Example: {
                    "wacc": {"mean": 0.10, "std": 0.02},
                    "terminal_growth": {"mean": 0.025, "std": 0.01}
                }
            num_simulations: Number of Monte Carlo iterations

        Returns:
            Distribution of valuation outcomes with percentiles
        """
        try:
            np.random.seed(42)  # For reproducibility

            simulated_values = []

            for _ in range(num_simulations):
                # Generate random parameters based on distributions
                params = base_params.copy()
                
                for var_name, distribution in variable_distributions.items():
                    mean = distribution.get("mean", base_params.get(var_name, 0))
                    std = distribution.get("std", mean * 0.1)  # Default 10% std
                    
                    # Generate random value from normal distribution
                    random_value = np.random.normal(mean, std)
                    
                    # Apply bounds to prevent unrealistic values
                    if var_name == "wacc":
                        random_value = max(0.01, min(0.30, random_value))  # 1% to 30%
                    elif var_name == "terminal_growth":
                        random_value = max(0.0, min(0.10, random_value))  # 0% to 10%
                    
                    params[var_name] = random_value

                # Calculate valuation for this iteration
                enterprise_value = self.dcf_valuation_simple(
                    fcf=params.get("fcf", 100),
                    wacc=params.get("wacc", 0.10),
                    terminal_growth=params.get("terminal_growth", 0.025),
                    years=params.get("years", 5),
                )
                
                simulated_values.append(enterprise_value)

            # Calculate statistics
            simulated_array = np.array(simulated_values)
            
            percentiles = {
                "p5": float(np.percentile(simulated_array, 5)),
                "p10": float(np.percentile(simulated_array, 10)),
                "p25": float(np.percentile(simulated_array, 25)),
                "p50": float(np.percentile(simulated_array, 50)),  # Median
                "p75": float(np.percentile(simulated_array, 75)),
                "p90": float(np.percentile(simulated_array, 90)),
                "p95": float(np.percentile(simulated_array, 95)),
            }

            return {
                "status": "success",
                "company_id": str(company_id),
                "analysis_type": "monte_carlo_simulation",
                "num_simulations": num_simulations,
                "statistics": {
                    "mean": round(float(np.mean(simulated_array)), 2),
                    "median": round(percentiles["p50"], 2),
                    "std_dev": round(float(np.std(simulated_array)), 2),
                    "min": round(float(np.min(simulated_array)), 2),
                    "max": round(float(np.max(simulated_array)), 2),
                },
                "percentiles": {k: round(v, 2) for k, v in percentiles.items()},
                "confidence_intervals": {
                    "80_percent": {
                        "lower": round(percentiles["p10"], 2),
                        "upper": round(percentiles["p90"], 2),
                    },
                    "90_percent": {
                        "lower": round(percentiles["p5"], 2),
                        "upper": round(percentiles["p95"], 2),
                    },
                },
            }

        except Exception as e:
            logger.error(f"Error in Monte Carlo simulation: {e}")
            raise

    async def tornado_chart_data(
        self,
        company_id: UUID,
        base_params: Dict[str, float],
        variables: List[str],
        variation_pct: float = 0.20,
    ) -> Dict[str, any]:
        """
        Generate data for Tornado chart (ranked sensitivity).

        Analyzes multiple variables and ranks by impact on valuation.

        Args:
            company_id: Company UUID
            base_params: Base case parameters
            variables: List of variables to analyze
            variation_pct: Percentage to vary each variable (+/-)

        Returns:
            Ranked sensitivity impacts (for tornado chart visualization)
        """
        try:
            base_ev = self.dcf_valuation_simple(
                fcf=base_params.get("fcf", 100),
                wacc=base_params.get("wacc", 0.10),
                terminal_growth=base_params.get("terminal_growth", 0.025),
                years=base_params.get("years", 5),
            )

            impacts = []

            for variable in variables:
                base_value = base_params.get(variable)
                if base_value is None:
                    continue

                # Calculate at +variation%
                params_high = base_params.copy()
                params_high[variable] = base_value * (1 + variation_pct)
                ev_high = self.dcf_valuation_simple(
                    fcf=params_high.get("fcf", 100),
                    wacc=params_high.get("wacc", 0.10),
                    terminal_growth=params_high.get("terminal_growth", 0.025),
                    years=params_high.get("years", 5),
                )

                # Calculate at -variation%
                params_low = base_params.copy()
                params_low[variable] = base_value * (1 - variation_pct)
                ev_low = self.dcf_valuation_simple(
                    fcf=params_low.get("fcf", 100),
                    wacc=params_low.get("wacc", 0.10),
                    terminal_growth=params_low.get("terminal_growth", 0.025),
                    years=params_low.get("years", 5),
                )

                # Calculate impact range
                impact_range = abs(ev_high - ev_low)
                upside = ((ev_high - base_ev) / base_ev) * 100
                downside = ((ev_low - base_ev) / base_ev) * 100

                impacts.append({
                    "variable": variable,
                    "base_value": base_value,
                    "impact_range": round(impact_range, 2),
                    "upside_pct": round(upside, 2),
                    "downside_pct": round(downside, 2),
                    "ev_at_high": round(ev_high, 2),
                    "ev_at_low": round(ev_low, 2),
                })

            # Sort by impact (descending)
            impacts.sort(key=lambda x: x["impact_range"], reverse=True)

            # Add rank
            for idx, item in enumerate(impacts, start=1):
                item["rank"] = idx

            return {
                "status": "success",
                "company_id": str(company_id),
                "analysis_type": "tornado_chart",
                "base_enterprise_value": round(base_ev, 2),
                "variation_pct": variation_pct * 100,
                "ranked_impacts": impacts,
            }

        except Exception as e:
            logger.error(f"Error generating tornado chart data: {e}")
            raise
