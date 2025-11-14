"""
Scenario Analysis Service.

Comprehensive scenario-based analysis with three scenarios:
- Optimistic (Bull Case): Best case assumptions
- Neutral (Base Case): Current/realistic assumptions  
- Pessimistic (Bear Case): Worst case assumptions

Applied to:
- Valuation (DCF, Comparables)
- Risk Assessment
- Financial Projections
"""

from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.valuation_risk import Valuation
from app.services.valuation_service import ValuationService
from app.services.risk_assessment_service import RiskAssessmentService

logger = logging.getLogger(__name__)


class ScenarioAnalysisService:
    """Service for scenario-based analysis."""

    def __init__(self, db: AsyncSession, tenant_id: str):
        """
        Initialize scenario analysis service.

        Args:
            db: Database session
            tenant_id: Current tenant ID
        """
        self.db = db
        self.tenant_id = str(tenant_id) if isinstance(tenant_id, UUID) else tenant_id
        self.valuation_service = ValuationService(db, tenant_id)
        self.risk_service = RiskAssessmentService(db, tenant_id)

    def generate_scenario_assumptions(
        self,
        base_assumptions: Dict[str, any],
        scenario_type: str,
    ) -> Dict[str, any]:
        """
        Generate assumptions for different scenarios.

        Args:
            base_assumptions: Base case assumptions
            scenario_type: "optimistic", "neutral", or "pessimistic"

        Returns:
            Scenario-specific assumptions
        """
        assumptions = base_assumptions.copy()

        if scenario_type == "optimistic":
            # Optimistic: 20-30% better assumptions
            multipliers = {
                "revenue_growth": 1.25,  # 25% higher growth
                "ebitda_margin": 1.15,   # 15% margin expansion
                "wacc": 0.90,            # 10% lower discount rate
                "terminal_growth": 1.20, # 20% higher terminal growth
                "capex_pct": 0.85,       # 15% lower capex needs
            }
        elif scenario_type == "pessimistic":
            # Pessimistic: 25-35% worse assumptions
            multipliers = {
                "revenue_growth": 0.70,  # 30% lower growth
                "ebitda_margin": 0.85,   # 15% margin compression
                "wacc": 1.15,            # 15% higher discount rate
                "terminal_growth": 0.75, # 25% lower terminal growth
                "capex_pct": 1.20,       # 20% higher capex needs
            }
        else:  # neutral
            # No changes for base case
            multipliers = {
                "revenue_growth": 1.0,
                "ebitda_margin": 1.0,
                "wacc": 1.0,
                "terminal_growth": 1.0,
                "capex_pct": 1.0,
            }

        # Apply multipliers
        for key, multiplier in multipliers.items():
            if key in assumptions:
                if isinstance(assumptions[key], (int, float, Decimal)):
                    assumptions[key] = Decimal(str(float(assumptions[key]) * multiplier))
                elif isinstance(assumptions[key], list):
                    assumptions[key] = [
                        Decimal(str(float(v) * multiplier)) if isinstance(v, (int, float, Decimal)) else v
                        for v in assumptions[key]
                    ]

        return assumptions

    async def analyze_valuation_scenarios(
        self,
        company_id: UUID,
        base_dcf_params: Dict[str, any],
    ) -> Dict[str, any]:
        """
        Perform DCF valuation under three scenarios.

        Args:
            company_id: Company UUID
            base_dcf_params: Base case DCF parameters

        Returns:
            Valuation results for all three scenarios
        """
        try:
            results = {}

            for scenario in ["optimistic", "neutral", "pessimistic"]:
                logger.info(f"Calculating {scenario} scenario valuation")

                # Generate scenario assumptions
                scenario_params = self.generate_scenario_assumptions(
                    base_dcf_params,
                    scenario
                )

                # Perform DCF valuation
                # Note: Would call actual DCF valuation method with scenario params
                # For now, placeholder logic
                fair_value_neutral = base_dcf_params.get("expected_fair_value", Decimal("100"))

                if scenario == "optimistic":
                    fair_value = fair_value_neutral * Decimal("1.30")  # 30% upside
                    probability = Decimal("0.25")
                elif scenario == "pessimistic":
                    fair_value = fair_value_neutral * Decimal("0.75")  # 25% downside
                    probability = Decimal("0.20")
                else:  # neutral
                    fair_value = fair_value_neutral
                    probability = Decimal("0.55")

                current_price = base_dcf_params.get("current_price", Decimal("100"))
                upside = ((fair_value - current_price) / current_price) * Decimal("100")

                results[scenario] = {
                    "fair_value_per_share": float(fair_value),
                    "current_price": float(current_price),
                    "upside_downside_pct": float(upside),
                    "probability": float(probability),
                    "assumptions": scenario_params,
                }

            # Calculate probability-weighted expected value
            expected_value = sum(
                Decimal(str(results[s]["fair_value_per_share"])) * Decimal(str(results[s]["probability"]))
                for s in ["optimistic", "neutral", "pessimistic"]
            )

            return {
                "status": "success",
                "company_id": str(company_id),
                "scenarios": results,
                "expected_value": {
                    "fair_value_per_share": float(expected_value),
                    "current_price": float(current_price),
                    "expected_upside_pct": float(((expected_value - current_price) / current_price) * Decimal("100")),
                },
                "risk_reward": {
                    "upside_potential": float(results["optimistic"]["upside_downside_pct"]),
                    "downside_risk": float(results["pessimistic"]["upside_downside_pct"]),
                    "risk_reward_ratio": float(
                        abs(results["optimistic"]["upside_downside_pct"] / results["pessimistic"]["upside_downside_pct"])
                        if results["pessimistic"]["upside_downside_pct"] != 0 else 0
                    ),
                },
            }

        except Exception as e:
            logger.error(f"Error in valuation scenario analysis: {e}")
            raise

    async def analyze_comprehensive_scenarios(
        self,
        company_id: UUID,
        dcf_params: Optional[Dict[str, any]] = None,
    ) -> Dict[str, any]:
        """
        Comprehensive scenario analysis including valuation, risk, and projections.

        Args:
            company_id: Company UUID
            dcf_params: Optional DCF parameters (uses defaults if not provided)

        Returns:
            Complete scenario analysis
        """
        try:
            # Default DCF parameters if not provided
            if dcf_params is None:
                dcf_params = {
                    "expected_fair_value": Decimal("100"),
                    "current_price": Decimal("90"),
                    "revenue_growth": [Decimal("0.10"), Decimal("0.08"), Decimal("0.06")],
                    "ebitda_margin": Decimal("0.20"),
                    "wacc": Decimal("0.10"),
                    "terminal_growth": Decimal("0.025"),
                    "capex_pct": Decimal("0.05"),
                }

            # Valuation scenarios
            valuation_scenarios = await self.analyze_valuation_scenarios(
                company_id,
                dcf_params
            )

            # Risk scenarios (already implemented in risk service)
            risk_scenarios = await self.risk_service.assess_risk_with_scenarios(company_id)

            return {
                "status": "success",
                "company_id": str(company_id),
                "analysis_date": date.today().isoformat(),
                "valuation_scenarios": valuation_scenarios,
                "risk_scenarios": risk_scenarios,
                "recommendation": self._generate_recommendation(valuation_scenarios, risk_scenarios),
            }

        except Exception as e:
            logger.error(f"Error in comprehensive scenario analysis: {e}")
            raise

    def _generate_recommendation(
        self,
        valuation_scenarios: Dict[str, any],
        risk_scenarios: Dict[str, any],
    ) -> Dict[str, any]:
        """
        Generate investment recommendation based on scenarios.

        Args:
            valuation_scenarios: Valuation scenario results
            risk_scenarios: Risk scenario results

        Returns:
            Investment recommendation
        """
        # Extract key metrics
        expected_upside = valuation_scenarios.get("expected_value", {}).get("expected_upside_pct", 0)
        risk_rating = risk_scenarios.get("scenarios", {}).get("neutral", {}).get("risk_rating", "Medium")

        # Determine recommendation
        if expected_upside > 20 and risk_rating in ["Low", "Medium"]:
            recommendation = "Strong Buy"
            confidence = "High"
        elif expected_upside > 10 and risk_rating in ["Low", "Medium"]:
            recommendation = "Buy"
            confidence = "Medium"
        elif expected_upside > 0:
            recommendation = "Hold"
            confidence = "Medium"
        elif expected_upside > -10:
            recommendation = "Sell"
            confidence = "Medium"
        else:
            recommendation = "Strong Sell"
            confidence = "High"

        return {
            "recommendation": recommendation,
            "confidence": confidence,
            "expected_return": expected_upside,
            "risk_level": risk_rating,
            "rationale": f"Expected upside of {expected_upside:.1f}% with {risk_rating} risk",
        }
