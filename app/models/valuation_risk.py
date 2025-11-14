"""
Valuation and risk assessment models.
"""

from sqlalchemy import Column, Date, ForeignKey, JSON, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel

# Use JSON for SQLite compatibility, JSONB for PostgreSQL
JSONType = JSON().with_variant(JSONB(), "postgresql")


class Valuation(BaseModel):
    """
    Valuation model for storing company valuation results.
    """

    __tablename__ = "valuations"

    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)
    valuation_date = Column(Date, nullable=False, index=True)
    method = Column(String(50), nullable=False)  # DCF, Comparables, Asset-Based, etc.

    # Valuation results
    fair_value_per_share = Column(Numeric(10, 2))
    current_price = Column(Numeric(10, 2))
    upside_downside_percent = Column(Numeric(10, 2))
    enterprise_value = Column(Numeric(20, 2))
    equity_value = Column(Numeric(20, 2))

    # Parameters and assumptions (stored as JSON)
    parameters = Column(JSONType)
    assumptions = Column(JSONType)
    sensitivity_analysis = Column(JSONType)

    # Created by (for audit trail)
    created_by_user_id = Column(UUID(as_uuid=True))

    # Relationships
    company = relationship("Company", back_populates="valuations")

    def __repr__(self) -> str:
        return f"<Valuation(company_id={self.company_id}, method={self.method}, date={self.valuation_date})>"


class RiskAssessment(BaseModel):
    """
    Risk Assessment model for storing comprehensive risk scores.
    """

    __tablename__ = "risk_assessments"

    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)
    assessment_date = Column(Date, nullable=False, index=True)

    # Overall risk score (0-100)
    overall_risk_score = Column(Numeric(5, 2))
    risk_rating = Column(String(20))  # Low, Medium, High, Very High

    # Component risk scores
    business_risk_score = Column(Numeric(5, 2))
    financial_risk_score = Column(Numeric(5, 2))
    operational_risk_score = Column(Numeric(5, 2))
    market_risk_score = Column(Numeric(5, 2))
    esg_risk_score = Column(Numeric(5, 2))

    # Specific risk metrics
    altman_z_score = Column(Numeric(10, 4))
    credit_rating = Column(String(10))
    default_probability = Column(Numeric(10, 6))

    # Beta and volatility
    beta = Column(Numeric(10, 4))
    volatility_30d = Column(Numeric(10, 4))
    volatility_90d = Column(Numeric(10, 4))
    value_at_risk_95 = Column(Numeric(10, 4))

    # Detailed risk factors (stored as JSON)
    risk_factors = Column(JSONType)
    risk_details = Column(JSONType)

    # Relationships
    company = relationship("Company", back_populates="risk_assessments")

    def __repr__(self) -> str:
        return f"<RiskAssessment(company_id={self.company_id}, score={self.overall_risk_score}, date={self.assessment_date})>"


class MarketData(BaseModel):
    """
    Market Data model for storing daily price and volume data.
    """

    __tablename__ = "market_data"

    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)

    # Price data
    open_price = Column(Numeric(10, 2))
    high_price = Column(Numeric(10, 2))
    low_price = Column(Numeric(10, 2))
    close_price = Column(Numeric(10, 2), nullable=False)
    adjusted_close = Column(Numeric(10, 2))

    # Volume
    volume = Column(Numeric(15, 0))

    # Additional metrics
    market_cap = Column(Numeric(20, 2))
    shares_outstanding = Column(Numeric(15, 0))

    # Relationships
    company = relationship("Company", back_populates="market_data")

    def __repr__(self) -> str:
        return f"<MarketData(company_id={self.company_id}, date={self.date}, close={self.close_price})>"
