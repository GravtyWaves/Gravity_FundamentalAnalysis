"""
================================================================================
FILE IDENTITY CARD
================================================================================
File Path:           app/models/prediction_tracking.py
Author:              Dr. Aisha Patel
Team ID:             FA-VALUATION-ML
Created Date:        2025-11-14
Last Modified:       2025-11-14
Version:             1.0.0
Purpose:             Database models for prediction tracking and feedback loop
                     Stores ML predictions and actual outcomes for retraining

Dependencies:        sqlalchemy>=2.0

Related Files:       app/services/scenario_tracker.py (service layer)
                     app/services/valuation_prediction_model.py (predictions)

Complexity:          6/10 (standard SQLAlchemy models with JSON fields)
Lines of Code:       150
Test Coverage:       0% (new file)
Performance Impact:  LOW (indexed queries)
Time Spent:          2 hours
Cost:                $300 (2 × $150/hr Elite)
Review Status:       In Development
================================================================================
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column, DateTime, Decimal as SQLDecimal, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class ValuationPrediction(Base):
    """Store ML predictions for later comparison with actual outcomes."""

    __tablename__ = "valuation_predictions"
    __table_args__ = (
        Index("idx_prediction_company_date", "company_id", "prediction_date"),
        Index("idx_prediction_symbol", "symbol"),
        {"schema": "tse"},
    )

    # Primary key
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PGUUID(as_uuid=True), nullable=False)

    # Identifiers
    company_id = Column(PGUUID(as_uuid=True), ForeignKey("tse.companies.id"), nullable=False)
    symbol = Column(String(20), nullable=False)
    prediction_date = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Input data snapshot (for reproducibility)
    current_price = Column(SQLDecimal(20, 4), nullable=False)
    input_features = Column(JSON, nullable=True)  # Snapshot of 130+ features

    # Task 1: Best Method Prediction
    predicted_best_method = Column(String(20), nullable=False)  # DCF/Comparables/Asset/DDM/RIM
    method_confidence = Column(SQLDecimal(5, 4), nullable=False)  # 0.0-1.0
    method_probabilities = Column(JSON, nullable=True)  # {"DCF": 0.45, "Comparables": 0.30, ...}

    # Task 2: Scenario Probabilities
    bull_probability = Column(SQLDecimal(5, 4), nullable=False)
    base_probability = Column(SQLDecimal(5, 4), nullable=False)
    bear_probability = Column(SQLDecimal(5, 4), nullable=False)

    # Task 3: Expected Returns
    expected_return_1m = Column(SQLDecimal(10, 6), nullable=True)
    expected_return_3m = Column(SQLDecimal(10, 6), nullable=True)
    expected_return_6m = Column(SQLDecimal(10, 6), nullable=True)
    expected_return_12m = Column(SQLDecimal(10, 6), nullable=True)

    # Task 4: Time to Fair Value
    predicted_days_to_target = Column(SQLDecimal(10, 2), nullable=True)

    # Recommendation
    recommendation = Column(String(20), nullable=True)  # STRONG_BUY/BUY/HOLD/SELL/STRONG_SELL
    recommendation_confidence = Column(SQLDecimal(5, 4), nullable=True)

    # Price targets
    price_target_bull = Column(SQLDecimal(20, 4), nullable=True)
    price_target_base = Column(SQLDecimal(20, 4), nullable=True)
    price_target_bear = Column(SQLDecimal(20, 4), nullable=True)

    # Tracking metadata
    model_version = Column(String(50), nullable=True)  # e.g., "v1.2.0"
    is_verified = Column(String(10), default="pending")  # pending/verified/outdated

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    company = relationship("Company", back_populates="predictions")
    outcomes = relationship("PredictionOutcome", back_populates="prediction", cascade="all, delete-orphan")


class PredictionOutcome(Base):
    """Store actual outcomes for each prediction to measure accuracy."""

    __tablename__ = "prediction_outcomes"
    __table_args__ = (
        Index("idx_outcome_prediction", "prediction_id"),
        Index("idx_outcome_date", "outcome_date"),
        {"schema": "tse"},
    )

    # Primary key
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PGUUID(as_uuid=True), nullable=False)

    # Link to prediction
    prediction_id = Column(PGUUID(as_uuid=True), ForeignKey("tse.valuation_predictions.id"), nullable=False)

    # Outcome metadata
    outcome_date = Column(DateTime, nullable=False)  # When outcome was recorded
    days_elapsed = Column(SQLDecimal(10, 2), nullable=False)  # Days since prediction

    # Actual price movements
    actual_price = Column(SQLDecimal(20, 4), nullable=False)
    actual_return_1m = Column(SQLDecimal(10, 6), nullable=True)
    actual_return_3m = Column(SQLDecimal(10, 6), nullable=True)
    actual_return_6m = Column(SQLDecimal(10, 6), nullable=True)
    actual_return_12m = Column(SQLDecimal(10, 6), nullable=True)

    # Which scenario materialized
    materialized_scenario = Column(String(10), nullable=True)  # bull/base/bear/none

    # Accuracy metrics
    method_was_correct = Column(String(10), nullable=True)  # true/false/unknown
    return_prediction_error_1m = Column(SQLDecimal(10, 6), nullable=True)  # MAE
    return_prediction_error_3m = Column(SQLDecimal(10, 6), nullable=True)
    return_prediction_error_6m = Column(SQLDecimal(10, 6), nullable=True)
    return_prediction_error_12m = Column(SQLDecimal(10, 6), nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    prediction = relationship("ValuationPrediction", back_populates="outcomes")
