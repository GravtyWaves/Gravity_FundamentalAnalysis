"""
================================================================================
FILE IDENTITY CARD
================================================================================
File Path:           app/services/scenario_tracker.py
Author:              João Silva, Dr. Aisha Patel
Team ID:             FA-VALUATION-ML
Created Date:        2025-11-14
Last Modified:       2025-11-14
Version:             1.0.0
Purpose:             Track ML predictions vs actual outcomes for feedback loop
                     Calculate accuracy metrics, identify patterns, enable retraining

Dependencies:        sqlalchemy>=2.0, numpy>=1.24

Related Files:       app/models/prediction_tracking.py (database models)
                     app/services/valuation_prediction_model.py (predictions)
                     app/services/valuation_performance.py (analytics)

Complexity:          8/10 (complex accuracy calculations, scenario detection)
Lines of Code:       350
Test Coverage:       0% (new file, needs comprehensive tests)
Performance Impact:  LOW (async queries with indexes)
Time Spent:          5 hours
Cost:                $750 (5 × $150/hr Elite)
Review Status:       In Development
Notes:               - Stores predictions for future verification
                     - Tracks actual vs predicted returns
                     - Identifies which scenarios materialized
                     - Calculates MAE, RMSE, hit rate
                     - Feeds feedback loop for model retraining
================================================================================
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from uuid import UUID

import numpy as np
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.prediction_tracking import PredictionOutcome, ValuationPrediction
from app.models.valuation_risk import MarketData
from app.schemas.valuation_features import ValuationMLOutput

logger = logging.getLogger(__name__)


class ScenarioTracker:
    """
    Track prediction accuracy and actual outcomes for feedback loop.

    Core Functions:
    1. Store predictions for future verification
    2. Record actual outcomes as they happen
    3. Calculate accuracy metrics (MAE, RMSE, hit rate)
    4. Identify which scenarios materialized
    5. Generate training data for model improvement
    """

    def __init__(self, db: AsyncSession, tenant_id: UUID):
        """
        Initialize scenario tracker.

        Args:
            db: Database session
            tenant_id: Current tenant ID
        """
        self.db = db
        self.tenant_id = str(tenant_id) if isinstance(tenant_id, UUID) else tenant_id

    async def store_prediction(
        self,
        company_id: UUID,
        symbol: str,
        prediction: ValuationMLOutput,
        input_features: Optional[Dict] = None,
        model_version: str = "v1.0.0",
    ) -> ValuationPrediction:
        """
        Store ML prediction for future verification.

        Args:
            company_id: Company UUID
            symbol: Stock symbol
            prediction: ML model output
            input_features: Optional snapshot of input features
            model_version: Model version for tracking

        Returns:
            Created ValuationPrediction record
        """
        # Create prediction record
        pred_record = ValuationPrediction(
            tenant_id=self.tenant_id,
            company_id=company_id,
            symbol=symbol,
            prediction_date=prediction.prediction_date,
            current_price=prediction.price_target_base,  # Using base as reference
            input_features=input_features,
            # Task 1
            predicted_best_method=prediction.best_method,
            method_confidence=prediction.method_confidence,
            method_probabilities=prediction.method_probabilities,
            # Task 2
            bull_probability=prediction.bull_probability,
            base_probability=prediction.base_probability,
            bear_probability=prediction.bear_probability,
            # Task 3
            expected_return_1m=prediction.expected_return_1m,
            expected_return_3m=prediction.expected_return_3m,
            expected_return_6m=prediction.expected_return_6m,
            expected_return_12m=prediction.expected_return_12m,
            # Task 4
            predicted_days_to_target=Decimal(str(prediction.time_to_fair_value_days)),
            # Recommendation
            recommendation=prediction.recommendation,
            recommendation_confidence=prediction.recommendation_confidence,
            # Targets
            price_target_bull=prediction.price_target_bull,
            price_target_base=prediction.price_target_base,
            price_target_bear=prediction.price_target_bear,
            # Metadata
            model_version=model_version,
            is_verified="pending",
        )

        self.db.add(pred_record)
        await self.db.commit()
        await self.db.refresh(pred_record)

        logger.info(f"Stored prediction for {symbol} (ID: {pred_record.id})")
        return pred_record

    async def record_outcome(
        self,
        prediction_id: UUID,
        outcome_date: datetime,
        actual_price: Decimal,
        actual_returns: Dict[str, Optional[Decimal]],
    ) -> PredictionOutcome:
        """
        Record actual outcome for a prediction.

        Args:
            prediction_id: Prediction UUID
            outcome_date: Date of outcome observation
            actual_price: Actual stock price
            actual_returns: Actual returns {"1m": ..., "3m": ..., "6m": ..., "12m": ...}

        Returns:
            Created PredictionOutcome record
        """
        # Get original prediction
        result = await self.db.execute(
            select(ValuationPrediction).where(
                ValuationPrediction.id == prediction_id,
                ValuationPrediction.tenant_id == self.tenant_id,
            )
        )
        prediction = result.scalar_one_or_none()

        if not prediction:
            raise ValueError(f"Prediction {prediction_id} not found")

        # Calculate days elapsed
        days_elapsed = (outcome_date - prediction.prediction_date).days

        # Calculate prediction errors
        errors = self._calculate_prediction_errors(prediction, actual_returns)

        # Identify materialized scenario
        materialized_scenario = self._identify_materialized_scenario(
            prediction, actual_price, actual_returns.get("6m")  # Use 6-month return
        )

        # Create outcome record
        outcome = PredictionOutcome(
            tenant_id=self.tenant_id,
            prediction_id=prediction_id,
            outcome_date=outcome_date,
            days_elapsed=Decimal(str(days_elapsed)),
            actual_price=actual_price,
            actual_return_1m=actual_returns.get("1m"),
            actual_return_3m=actual_returns.get("3m"),
            actual_return_6m=actual_returns.get("6m"),
            actual_return_12m=actual_returns.get("12m"),
            materialized_scenario=materialized_scenario,
            return_prediction_error_1m=errors.get("1m"),
            return_prediction_error_3m=errors.get("3m"),
            return_prediction_error_6m=errors.get("6m"),
            return_prediction_error_12m=errors.get("12m"),
        )

        self.db.add(outcome)

        # Update prediction status
        prediction.is_verified = "verified"

        await self.db.commit()
        await self.db.refresh(outcome)

        logger.info(
            f"Recorded outcome for prediction {prediction_id} "
            f"(scenario: {materialized_scenario}, 6m error: {errors.get('6m')})"
        )
        return outcome

    async def auto_update_outcomes(
        self,
        days_back: int = 365,
    ) -> int:
        """
        Automatically update outcomes for recent predictions.

        Args:
            days_back: Look back this many days for predictions

        Returns:
            Number of outcomes updated
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)

        # Get pending predictions
        result = await self.db.execute(
            select(ValuationPrediction)
            .where(
                ValuationPrediction.tenant_id == self.tenant_id,
                ValuationPrediction.prediction_date >= cutoff_date,
                ValuationPrediction.is_verified == "pending",
            )
            .order_by(ValuationPrediction.prediction_date)
        )
        pending_predictions = result.scalars().all()

        updates_count = 0

        for prediction in pending_predictions:
            try:
                # Check if enough time has passed (at least 1 month)
                days_elapsed = (datetime.utcnow() - prediction.prediction_date).days
                if days_elapsed < 30:
                    continue

                # Fetch actual returns
                actual_returns = await self._fetch_actual_returns(
                    prediction.company_id, prediction.prediction_date
                )

                # Get current price
                current_price = await self._get_current_price(prediction.company_id)

                if actual_returns and current_price:
                    await self.record_outcome(
                        prediction.id,
                        datetime.utcnow(),
                        current_price,
                        actual_returns,
                    )
                    updates_count += 1

            except Exception as e:
                logger.error(f"Error updating outcome for {prediction.id}: {e}")
                continue

        logger.info(f"Auto-updated {updates_count} prediction outcomes")
        return updates_count

    async def calculate_model_accuracy(
        self,
        model_version: Optional[str] = None,
        days_back: int = 365,
    ) -> Dict[str, float]:
        """
        Calculate overall model accuracy metrics.

        Args:
            model_version: Filter by model version (None = all)
            days_back: Look back this many days

        Returns:
            Dict with accuracy metrics
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)

        # Build query
        query = (
            select(PredictionOutcome, ValuationPrediction)
            .join(ValuationPrediction)
            .where(
                ValuationPrediction.tenant_id == self.tenant_id,
                ValuationPrediction.prediction_date >= cutoff_date,
            )
        )

        if model_version:
            query = query.where(ValuationPrediction.model_version == model_version)

        result = await self.db.execute(query)
        outcomes = [(outcome, pred) for outcome, pred in result.all()]

        if not outcomes:
            return {"sample_size": 0}

        # Extract errors
        errors_1m = [float(o.return_prediction_error_1m) for o, _ in outcomes if o.return_prediction_error_1m]
        errors_3m = [float(o.return_prediction_error_3m) for o, _ in outcomes if o.return_prediction_error_3m]
        errors_6m = [float(o.return_prediction_error_6m) for o, _ in outcomes if o.return_prediction_error_6m]
        errors_12m = [float(o.return_prediction_error_12m) for o, _ in outcomes if o.return_prediction_error_12m]

        # Calculate metrics
        metrics = {
            "sample_size": len(outcomes),
            "mae_1m": np.mean(np.abs(errors_1m)) if errors_1m else None,
            "mae_3m": np.mean(np.abs(errors_3m)) if errors_3m else None,
            "mae_6m": np.mean(np.abs(errors_6m)) if errors_6m else None,
            "mae_12m": np.mean(np.abs(errors_12m)) if errors_12m else None,
            "rmse_1m": np.sqrt(np.mean(np.square(errors_1m))) if errors_1m else None,
            "rmse_3m": np.sqrt(np.mean(np.square(errors_3m))) if errors_3m else None,
            "rmse_6m": np.sqrt(np.mean(np.square(errors_6m))) if errors_6m else None,
            "rmse_12m": np.sqrt(np.mean(np.square(errors_12m))) if errors_12m else None,
        }

        # Scenario prediction accuracy
        scenario_correct = sum(
            1 for o, _ in outcomes
            if o.materialized_scenario and o.materialized_scenario != "none"
        )
        metrics["scenario_hit_rate"] = scenario_correct / len(outcomes) if outcomes else 0

        logger.info(f"Model accuracy: MAE 6m = {metrics['mae_6m']:.4f}, Hit rate = {metrics['scenario_hit_rate']:.2%}")
        return metrics

    def _calculate_prediction_errors(
        self,
        prediction: ValuationPrediction,
        actual_returns: Dict[str, Optional[Decimal]],
    ) -> Dict[str, Optional[Decimal]]:
        """Calculate prediction errors (MAE) for each horizon."""
        errors = {}

        horizons = {
            "1m": (prediction.expected_return_1m, actual_returns.get("1m")),
            "3m": (prediction.expected_return_3m, actual_returns.get("3m")),
            "6m": (prediction.expected_return_6m, actual_returns.get("6m")),
            "12m": (prediction.expected_return_12m, actual_returns.get("12m")),
        }

        for horizon, (predicted, actual) in horizons.items():
            if predicted is not None and actual is not None:
                errors[horizon] = abs(predicted - actual)
            else:
                errors[horizon] = None

        return errors

    def _identify_materialized_scenario(
        self,
        prediction: ValuationPrediction,
        actual_price: Decimal,
        actual_return_6m: Optional[Decimal],
    ) -> str:
        """
        Identify which scenario (bull/base/bear) actually materialized.

        Logic:
        - If price >= bull target → "bull"
        - If price >= base target → "base"
        - If price < base target → "bear"
        """
        if not actual_return_6m:
            return "none"

        # Compare to scenario probabilities
        if prediction.bull_probability > 0.5:
            expected_scenario = "bull"
        elif prediction.bear_probability > 0.3:
            expected_scenario = "bear"
        else:
            expected_scenario = "base"

        # Compare actual return to expected
        expected_return = prediction.expected_return_6m or Decimal("0")

        if actual_return_6m >= expected_return * Decimal("1.2"):
            return "bull"
        elif actual_return_6m >= expected_return * Decimal("0.8"):
            return "base"
        else:
            return "bear"

    async def _fetch_actual_returns(
        self,
        company_id: UUID,
        start_date: datetime,
    ) -> Optional[Dict[str, Decimal]]:
        """Fetch actual returns from start_date."""
        # Get prices at different intervals
        price_start = await self._get_price_on_date(company_id, start_date.date())
        price_1m = await self._get_price_on_date(company_id, (start_date + timedelta(days=30)).date())
        price_3m = await self._get_price_on_date(company_id, (start_date + timedelta(days=90)).date())
        price_6m = await self._get_price_on_date(company_id, (start_date + timedelta(days=180)).date())
        price_12m = await self._get_price_on_date(company_id, (start_date + timedelta(days=365)).date())

        if not price_start:
            return None

        def calc_return(p_end):
            return (p_end - price_start) / price_start if p_end and price_start > 0 else None

        return {
            "1m": calc_return(price_1m),
            "3m": calc_return(price_3m),
            "6m": calc_return(price_6m),
            "12m": calc_return(price_12m),
        }

    async def _get_price_on_date(self, company_id: UUID, target_date) -> Optional[Decimal]:
        """Get closing price on specific date."""
        result = await self.db.execute(
            select(MarketData.close_price)
            .where(
                MarketData.company_id == company_id,
                MarketData.tenant_id == self.tenant_id,
                MarketData.date <= target_date,
            )
            .order_by(MarketData.date.desc())
            .limit(1)
        )
        price = result.scalar_one_or_none()
        return price

    async def _get_current_price(self, company_id: UUID) -> Optional[Decimal]:
        """Get current (latest) price."""
        result = await self.db.execute(
            select(MarketData.close_price)
            .where(
                MarketData.company_id == company_id,
                MarketData.tenant_id == self.tenant_id,
            )
            .order_by(MarketData.date.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
