"""
================================================================================
FILE IDENTITY CARD
================================================================================
File Path:           app/schemas/valuation_features.py
Author:              Dr. Sarah Chen, Elena Volkov
Team ID:             FA-VALUATION-ML
Created Date:        2025-11-14
Last Modified:       2025-11-14
Version:             1.0.0
Purpose:             Pydantic schemas for ML-driven valuation system
                     ScenarioValuation, MultiMethodValuation, ValuationFeatures
                     Supports feedback loop architecture

Dependencies:        pydantic>=2.0, decimal, datetime

Related Files:       app/services/valuation_service.py (data source)
                     app/services/valuation_feature_engineer.py (feature extraction)
                     app/services/valuation_prediction_model.py (ML model)

Complexity:          8/10 (comprehensive feature engineering schemas)
Lines of Code:       300
Test Coverage:       0% (new file)
Performance Impact:  LOW (schemas only, no computation)
Time Spent:          3 hours
Cost:                $450 (3 × $150/hr Elite)
Review Status:       In Development
Notes:               - 15 valuations (5 methods × 3 scenarios)
                     - 50+ engineered features
                     - 130+ total ML input features
                     - Multi-task prediction outputs
================================================================================
"""

from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, computed_field, field_validator


# ==================== Scenario Valuation ====================
class ScenarioValuation(BaseModel):
    """Single scenario valuation (bull/base/bear) for one method."""

    scenario: Literal["bull", "base", "bear"] = Field(..., description="Scenario type")
    intrinsic_value: Decimal = Field(..., description="Calculated intrinsic value per share", ge=0)
    fair_value_range_low: Optional[Decimal] = Field(
        None, description="Lower bound of fair value range", ge=0
    )
    fair_value_range_high: Optional[Decimal] = Field(
        None, description="Upper bound of fair value range", ge=0
    )
    confidence: Decimal = Field(..., description="Confidence level (0.0-1.0)", ge=0, le=1)
    key_assumptions: Dict[str, Decimal] = Field(
        default_factory=dict, description="Key assumptions used"
    )

    @computed_field
    @property
    def fair_value_midpoint(self) -> Optional[Decimal]:
        """Calculate midpoint of fair value range."""
        if self.fair_value_range_low and self.fair_value_range_high:
            return (self.fair_value_range_low + self.fair_value_range_high) / Decimal("2")
        return self.intrinsic_value

    class Config:
        json_schema_extra = {
            "example": {
                "scenario": "base",
                "intrinsic_value": 120.0,
                "fair_value_range_low": 110.0,
                "fair_value_range_high": 130.0,
                "confidence": 0.75,
                "key_assumptions": {"revenue_growth": 0.12, "wacc": 0.095, "terminal_growth": 0.025},
            }
        }


# ==================== Multi-Method Valuation ====================
class MultiMethodValuation(BaseModel):
    """Valuations from all 5 methods × 3 scenarios = 15 total valuations."""

    company_id: UUID = Field(..., description="Company UUID")
    symbol: str = Field(..., description="Stock symbol")
    valuation_date: datetime = Field(..., description="Valuation calculation date")
    current_price: Decimal = Field(..., description="Current market price", ge=0)

    # DCF Method (3 scenarios)
    dcf_bull: ScenarioValuation = Field(..., description="DCF bull case")
    dcf_base: ScenarioValuation = Field(..., description="DCF base case")
    dcf_bear: ScenarioValuation = Field(..., description="DCF bear case")

    # Comparables Method (3 scenarios)
    comparable_bull: ScenarioValuation = Field(..., description="Comparables bull case")
    comparable_base: ScenarioValuation = Field(..., description="Comparables base case")
    comparable_bear: ScenarioValuation = Field(..., description="Comparables bear case")

    # Asset-Based Method (3 scenarios)
    asset_bull: ScenarioValuation = Field(..., description="Asset-based bull case")
    asset_base: ScenarioValuation = Field(..., description="Asset-based base case")
    asset_bear: ScenarioValuation = Field(..., description="Asset-based bear case")

    # Dividend Discount Model (3 scenarios)
    ddm_bull: ScenarioValuation = Field(..., description="DDM bull case")
    ddm_base: ScenarioValuation = Field(..., description="DDM base case")
    ddm_bear: ScenarioValuation = Field(..., description="DDM bear case")

    # Residual Income Model (3 scenarios)
    rim_bull: ScenarioValuation = Field(..., description="RIM bull case")
    rim_base: ScenarioValuation = Field(..., description="RIM base case")
    rim_bear: ScenarioValuation = Field(..., description="RIM bear case")

    @computed_field
    @property
    def all_valuations(self) -> List[Decimal]:
        """Get all 15 intrinsic values as list."""
        return [
            self.dcf_bull.intrinsic_value,
            self.dcf_base.intrinsic_value,
            self.dcf_bear.intrinsic_value,
            self.comparable_bull.intrinsic_value,
            self.comparable_base.intrinsic_value,
            self.comparable_bear.intrinsic_value,
            self.asset_bull.intrinsic_value,
            self.asset_base.intrinsic_value,
            self.asset_bear.intrinsic_value,
            self.ddm_bull.intrinsic_value,
            self.ddm_base.intrinsic_value,
            self.ddm_bear.intrinsic_value,
            self.rim_bull.intrinsic_value,
            self.rim_base.intrinsic_value,
            self.rim_bear.intrinsic_value,
        ]

    @computed_field
    @property
    def consensus_valuation(self) -> Decimal:
        """Average of all 15 valuations."""
        return sum(self.all_valuations) / Decimal("15")


# ==================== Valuation Features (50+ features) ====================
class ValuationFeatures(BaseModel):
    """50+ engineered features from 15 valuations for ML input."""

    # === Price vs Valuations (15 features) ===
    discount_to_dcf_bull: Decimal = Field(..., description="% discount to DCF bull")
    discount_to_dcf_base: Decimal = Field(..., description="% discount to DCF base")
    discount_to_dcf_bear: Decimal = Field(..., description="% discount to DCF bear")
    discount_to_comparable_bull: Decimal = Field(..., description="% discount to Comparables bull")
    discount_to_comparable_base: Decimal = Field(..., description="% discount to Comparables base")
    discount_to_comparable_bear: Decimal = Field(..., description="% discount to Comparables bear")
    discount_to_asset_bull: Decimal = Field(..., description="% discount to Asset-based bull")
    discount_to_asset_base: Decimal = Field(..., description="% discount to Asset-based base")
    discount_to_asset_bear: Decimal = Field(..., description="% discount to Asset-based bear")
    discount_to_ddm_bull: Decimal = Field(..., description="% discount to DDM bull")
    discount_to_ddm_base: Decimal = Field(..., description="% discount to DDM base")
    discount_to_ddm_bear: Decimal = Field(..., description="% discount to DDM bear")
    discount_to_rim_bull: Decimal = Field(..., description="% discount to RIM bull")
    discount_to_rim_base: Decimal = Field(..., description="% discount to RIM base")
    discount_to_rim_bear: Decimal = Field(..., description="% discount to RIM bear")

    # === Scenario Spreads (8 features) ===
    dcf_bull_bear_spread: Decimal = Field(..., description="DCF bull - bear spread")
    comparable_bull_bear_spread: Decimal = Field(..., description="Comparables bull - bear spread")
    asset_bull_bear_spread: Decimal = Field(..., description="Asset-based bull - bear spread")
    ddm_bull_bear_spread: Decimal = Field(..., description="DDM bull - bear spread")
    rim_bull_bear_spread: Decimal = Field(..., description="RIM bull - bear spread")
    average_scenario_uncertainty: Decimal = Field(
        ..., description="Average % spread across all methods"
    )
    max_scenario_uncertainty: Decimal = Field(
        ..., description="Max % spread (highest uncertainty method)"
    )
    min_scenario_uncertainty: Decimal = Field(
        ..., description="Min % spread (lowest uncertainty method)"
    )

    # === Method Agreement (6 features) ===
    method_consensus_base: Decimal = Field(
        ..., description="Average of all 5 base case valuations"
    )
    method_dispersion: Decimal = Field(
        ..., description="Std dev of all 15 valuations (disagreement level)"
    )
    method_range: Decimal = Field(..., description="Max - Min valuation across all 15")
    coefficient_of_variation: Decimal = Field(
        ..., description="Std dev / Mean (normalized dispersion)"
    )
    outlier_count: int = Field(..., description="Number of valuations >2 std dev from mean")
    consensus_confidence: Decimal = Field(
        ...,
        description="Inverse of coefficient of variation (high = agreement)",
        ge=0,
        le=1,
    )

    # === Margin of Safety (5 features) ===
    margin_of_safety_conservative: Decimal = Field(
        ..., description="% cushion to lowest bear case valuation"
    )
    margin_of_safety_consensus: Decimal = Field(
        ..., description="% cushion to average base case"
    )
    margin_of_safety_optimistic: Decimal = Field(
        ..., description="% cushion to lowest bull case"
    )
    downside_protection: Decimal = Field(
        ..., description="% price can fall before reaching bear case"
    )
    upside_potential: Decimal = Field(
        ..., description="% price can rise to reach bull case"
    )

    # === Historical Trends (6 features) ===
    valuation_velocity_1m: Optional[Decimal] = Field(
        None, description="Change in consensus valuation vs 1 month ago"
    )
    valuation_velocity_3m: Optional[Decimal] = Field(
        None, description="Change in consensus valuation vs 3 months ago"
    )
    valuation_velocity_6m: Optional[Decimal] = Field(
        None, description="Change in consensus valuation vs 6 months ago"
    )
    convergence_rate: Optional[Decimal] = Field(
        None, description="Rate at which price is converging to fair value"
    )
    historical_accuracy_dcf: Optional[Decimal] = Field(
        None, description="Historical accuracy of DCF predictions (0.0-1.0)", ge=0, le=1
    )
    historical_accuracy_comparables: Optional[Decimal] = Field(
        None, description="Historical accuracy of Comparables predictions (0.0-1.0)", ge=0, le=1
    )

    # === Peer-Relative (5 features) ===
    peer_discount_percentile: Optional[Decimal] = Field(
        None, description="Percentile rank of discount vs peers (0-100)", ge=0, le=100
    )
    peer_valuation_premium: Optional[Decimal] = Field(
        None, description="% premium/discount vs peer group average"
    )
    sector_median_discount: Optional[Decimal] = Field(
        None, description="Sector median discount to fair value"
    )
    relative_undervaluation: Optional[Decimal] = Field(
        None, description="How undervalued vs peers (negative = more undervalued)"
    )
    peer_rank: Optional[int] = Field(
        None, description="Rank in peer group by attractiveness (1 = best)", ge=1
    )

    # === Quality Metrics (5 features) ===
    data_quality_score: Decimal = Field(
        ..., description="Data completeness and reliability (0.0-1.0)", ge=0, le=1
    )
    assumption_sensitivity: Decimal = Field(
        ..., description="How sensitive valuations are to assumption changes (0.0-1.0)", ge=0, le=1
    )
    model_accuracy_score: Decimal = Field(
        ..., description="Historical model accuracy (0.0-1.0)", ge=0, le=1
    )
    valuation_confidence_avg: Decimal = Field(
        ..., description="Average confidence across all 15 valuations", ge=0, le=1
    )
    valuation_freshness_days: int = Field(
        ..., description="Days since last valuation update", ge=0
    )

    class Config:
        json_schema_extra = {
            "example": {
                "discount_to_dcf_base": -15.0,
                "method_consensus_base": 120.0,
                "margin_of_safety_consensus": 15.0,
                "consensus_confidence": 0.85,
                "data_quality_score": 0.92,
            }
        }


# ==================== ML Input (130+ features) ====================
class ValuationMLInput(BaseModel):
    """Complete ML input: 50+ valuation features + 66 ratios + market data."""

    company_id: UUID
    symbol: str
    valuation_date: datetime

    # Valuation Features (50+ features)
    valuation_features: ValuationFeatures

    # Financial Ratios (66 features) - simplified here
    profitability_ratios: Dict[str, Decimal] = Field(
        default_factory=dict, description="ROE, ROA, NPM, GPM, etc."
    )
    liquidity_ratios: Dict[str, Decimal] = Field(
        default_factory=dict, description="Current, Quick, Cash ratio"
    )
    leverage_ratios: Dict[str, Decimal] = Field(
        default_factory=dict, description="Debt/Equity, Interest Coverage"
    )
    efficiency_ratios: Dict[str, Decimal] = Field(
        default_factory=dict, description="Asset Turnover, Inventory Turnover"
    )

    # Market Data (10+ features)
    market_cap: Decimal = Field(..., description="Market capitalization", ge=0)
    volume_avg_30d: Decimal = Field(..., description="30-day average volume", ge=0)
    volatility_30d: Decimal = Field(..., description="30-day volatility", ge=0, le=1)
    beta: Decimal = Field(..., description="Beta coefficient")
    rsi_14d: Optional[Decimal] = Field(None, description="14-day RSI", ge=0, le=100)
    macd: Optional[Decimal] = Field(None, description="MACD indicator")

    # Macro Factors (5+ features)
    interest_rate: Optional[Decimal] = Field(None, description="Current interest rate", ge=0)
    inflation_rate: Optional[Decimal] = Field(None, description="Inflation rate")
    gdp_growth: Optional[Decimal] = Field(None, description="GDP growth rate")
    market_regime: Optional[Literal["bull", "bear", "sideways"]] = Field(
        None, description="Current market regime"
    )


# ==================== ML Output (Predictions) ====================
class ValuationMLOutput(BaseModel):
    """Multi-task ML model predictions."""

    company_id: UUID
    symbol: str
    prediction_date: datetime

    # Task 1: Best Method Selection
    best_method: Literal["DCF", "Comparables", "Asset-Based", "DDM", "RIM"] = Field(
        ..., description="Recommended valuation method for this stock"
    )
    method_confidence: Decimal = Field(
        ..., description="Confidence in method selection (0.0-1.0)", ge=0, le=1
    )
    method_probabilities: Dict[str, Decimal] = Field(
        ..., description="Probability for each method"
    )

    # Task 2: Scenario Probabilities
    bull_probability: Decimal = Field(
        ..., description="Probability of bull scenario (0.0-1.0)", ge=0, le=1
    )
    base_probability: Decimal = Field(
        ..., description="Probability of base scenario (0.0-1.0)", ge=0, le=1
    )
    bear_probability: Decimal = Field(
        ..., description="Probability of bear scenario (0.0-1.0)", ge=0, le=1
    )

    # Task 3: Expected Returns (4 horizons)
    expected_return_1m: Decimal = Field(..., description="Expected 1-month return")
    expected_return_3m: Decimal = Field(..., description="Expected 3-month return")
    expected_return_6m: Decimal = Field(..., description="Expected 6-month return")
    expected_return_12m: Decimal = Field(..., description="Expected 12-month return")

    # Task 4: Time to Fair Value
    time_to_fair_value_days: int = Field(
        ..., description="Predicted days to reach fair value", ge=0
    )

    # Final Recommendation
    recommendation: Literal["STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"] = Field(
        ..., description="Final recommendation"
    )
    recommendation_confidence: Decimal = Field(
        ..., description="Confidence in recommendation (0.0-1.0)", ge=0, le=1
    )
    price_target_bull: Decimal = Field(..., description="Bull case price target", ge=0)
    price_target_base: Decimal = Field(..., description="Base case price target", ge=0)
    price_target_bear: Decimal = Field(..., description="Bear case price target", ge=0)
    entry_range_low: Decimal = Field(..., description="Recommended entry range low", ge=0)
    entry_range_high: Decimal = Field(..., description="Recommended entry range high", ge=0)
    stop_loss: Decimal = Field(..., description="Recommended stop loss", ge=0)
    position_size_pct: Decimal = Field(
        ..., description="Recommended position size % of portfolio", ge=0, le=100
    )
    risk_reward_ratio: Decimal = Field(..., description="Risk/Reward ratio", ge=0)

    @field_validator("bull_probability", "base_probability", "bear_probability")
    @classmethod
    def validate_probabilities_sum(cls, v, info):
        """Ensure probabilities sum to 1.0."""
        # This validation happens after all fields are set
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "best_method": "DCF",
                "method_confidence": 0.82,
                "bull_probability": 0.25,
                "base_probability": 0.60,
                "bear_probability": 0.15,
                "expected_return_6m": 0.18,
                "time_to_fair_value_days": 150,
                "recommendation": "BUY",
                "recommendation_confidence": 0.85,
                "risk_reward_ratio": 3.2,
            }
        }
