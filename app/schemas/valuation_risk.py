"""
Valuation and risk assessment schemas.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ==================== Valuation ====================
class ValuationBase(BaseModel):
    """Base schema for company valuation."""

    company_id: UUID
    valuation_date: date
    method: Literal["DCF", "Comparables", "Asset-Based", "SOTP", "LBO", "Liquidation"] = Field(
        ..., description="Valuation method"
    )

    # Results
    fair_value_per_share: Optional[Decimal] = Field(None, description="Calculated fair value per share")
    current_price: Optional[Decimal] = Field(None, description="Current market price")
    upside_downside_percent: Optional[Decimal] = Field(None, description="% upside/downside from current price")
    enterprise_value: Optional[Decimal] = Field(None, description="Enterprise value")
    equity_value: Optional[Decimal] = Field(None, description="Equity value")

    # Parameters and assumptions (stored as JSON in database)
    parameters: Optional[dict[str, Any]] = Field(None, description="Valuation parameters")
    assumptions: Optional[dict[str, Any]] = Field(None, description="Key assumptions")
    sensitivity_analysis: Optional[dict[str, Any]] = Field(None, description="Sensitivity analysis results")


class ValuationCreate(ValuationBase):
    """Schema for creating a valuation."""

    pass


class ValuationResponse(ValuationBase):
    """Schema for valuation response."""

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by_user_id: Optional[UUID] = None

    class Config:
        from_attributes = True


class DCFValuationRequest(BaseModel):
    """Schema for DCF valuation request."""

    company_id: UUID
    valuation_date: date

    # Forecast parameters
    forecast_years: int = Field(5, ge=3, le=10, description="Number of years to forecast")
    revenue_growth_rates: list[Decimal] = Field(..., description="Revenue growth rate for each forecast year")
    terminal_growth_rate: Decimal = Field(..., description="Perpetual growth rate")

    # Margin assumptions
    ebitda_margin: Optional[Decimal] = Field(None, description="Target EBITDA margin")
    tax_rate: Decimal = Field(..., description="Tax rate assumption")

    # WACC components
    risk_free_rate: Decimal = Field(..., description="Risk-free rate")
    market_risk_premium: Decimal = Field(..., description="Market risk premium")
    beta: Decimal = Field(..., description="Beta coefficient")
    cost_of_debt: Optional[Decimal] = Field(None, description="After-tax cost of debt")
    debt_to_equity: Optional[Decimal] = Field(None, description="Target debt-to-equity ratio")


class ComparablesValuationRequest(BaseModel):
    """Schema for comparables valuation request."""

    company_id: UUID
    valuation_date: date
    peer_company_ids: list[UUID] = Field(..., description="IDs of comparable companies")
    valuation_multiples: list[str] = Field(
        ..., description="Multiples to use (e.g., ['P/E', 'EV/EBITDA', 'P/B'])"
    )
    weights: Optional[dict[str, Decimal]] = Field(None, description="Weights for each multiple")


# ==================== Risk Assessment ====================
class RiskAssessmentBase(BaseModel):
    """Base schema for risk assessment."""

    company_id: UUID
    assessment_date: date

    # Overall risk
    overall_risk_score: Optional[Decimal] = Field(None, ge=0, le=100, description="Overall risk score (0-100)")
    risk_rating: Optional[Literal["Low", "Medium", "High", "Very High"]] = Field(None, description="Risk rating")

    # Component scores
    business_risk_score: Optional[Decimal] = Field(None, ge=0, le=100, description="Business risk score")
    financial_risk_score: Optional[Decimal] = Field(None, ge=0, le=100, description="Financial risk score")
    operational_risk_score: Optional[Decimal] = Field(None, ge=0, le=100, description="Operational risk score")
    market_risk_score: Optional[Decimal] = Field(None, ge=0, le=100, description="Market risk score")
    esg_risk_score: Optional[Decimal] = Field(None, ge=0, le=100, description="ESG risk score")

    # Specific metrics
    altman_z_score: Optional[Decimal] = Field(None, description="Altman Z-Score for bankruptcy prediction")
    credit_rating: Optional[str] = Field(None, max_length=10, description="Credit rating")
    default_probability: Optional[Decimal] = Field(None, ge=0, le=1, description="Probability of default")

    # Market risk
    beta: Optional[Decimal] = Field(None, description="Beta coefficient")
    volatility_30d: Optional[Decimal] = Field(None, description="30-day volatility")
    volatility_90d: Optional[Decimal] = Field(None, description="90-day volatility")
    value_at_risk_95: Optional[Decimal] = Field(None, description="Value at Risk (95% confidence)")

    # Detailed factors (stored as JSON)
    risk_factors: Optional[dict[str, Any]] = Field(None, description="Detailed risk factors")
    risk_details: Optional[dict[str, Any]] = Field(None, description="Additional risk details")


class RiskAssessmentCreate(RiskAssessmentBase):
    """Schema for creating risk assessment."""

    pass


class RiskAssessmentResponse(RiskAssessmentBase):
    """Schema for risk assessment response."""

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RiskCalculationRequest(BaseModel):
    """Schema for requesting risk calculation."""

    company_id: UUID
    assessment_date: date
    include_components: Optional[list[str]] = Field(
        None,
        description="Specific risk components to calculate (business, financial, operational, market, esg)",
    )


# ==================== Market Data ====================
class MarketDataBase(BaseModel):
    """Base schema for market data."""

    company_id: UUID
    date: date

    # Price data
    open_price: Optional[Decimal] = None
    high_price: Optional[Decimal] = None
    low_price: Optional[Decimal] = None
    close_price: Decimal = Field(..., description="Closing price (required)")
    adjusted_close: Optional[Decimal] = None

    # Volume
    volume: Optional[Decimal] = None
    market_cap: Optional[Decimal] = None
    shares_outstanding: Optional[Decimal] = None


class MarketDataCreate(MarketDataBase):
    """Schema for creating market data."""

    pass


class MarketDataResponse(MarketDataBase):
    """Schema for market data response."""

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MarketDataBulkCreate(BaseModel):
    """Schema for bulk creating market data."""

    company_id: UUID
    data: list[MarketDataBase] = Field(..., description="List of market data entries")
