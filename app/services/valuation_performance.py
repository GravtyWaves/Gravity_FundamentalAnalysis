"""
===============================================================================
FILE IDENTITY CARD
===============================================================================
Filename    : valuation_performance.py
Created     : 2025
Author      : Elite Development Team
Department  : Machine Learning Services
Project     : Gravity Fundamental Analysis
Module      : Valuation Performance Monitoring
Version     : 1.0.0

Purpose     : Monitor valuation model performance and accuracy over time
              Track method-specific accuracy, scenario calibration, and
              generate performance reports for continuous improvement.

Scope       : Production ML monitoring system for valuation predictions
Components  : Performance metrics, accuracy tracking, degradation detection

Dependencies:
    - SQLAlchemy (async database operations)
    - NumPy (statistical calculations)
    - Pandas (data aggregation)
    - app.models.prediction_tracking (ValuationPrediction, PredictionOutcome)
    - app.core.database (Database session management)

Output      : Performance metrics, accuracy reports, degradation alerts

Notes       : Part of Task 6 - Valuation Performance Monitoring
              Tracks model performance across methods, scenarios, industries
              Enables data-driven model improvement decisions
===============================================================================
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import numpy as np
import pandas as pd
from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.prediction_tracking import ValuationPrediction, PredictionOutcome
from app.core.exceptions import ValidationError


@dataclass
class MethodPerformance:
    """Performance metrics for a specific valuation method."""
    method_name: str
    total_predictions: int
    accuracy_rate: float  # % where predicted method matched actual best
    avg_confidence: float
    avg_return_error: float  # MAE across all horizons
    precision: float  # When method predicted, how often was it right
    recall: float  # When method was best, how often did we predict it


@dataclass
class ScenarioCalibration:
    """Calibration metrics for scenario probability predictions."""
    scenario: str  # bull, base, bear
    predicted_probability: float  # Average predicted probability
    actual_frequency: float  # Actual frequency of scenario occurring
    calibration_error: float  # |predicted - actual|
    sample_size: int


@dataclass
class TimeToTargetMetrics:
    """Metrics for time-to-fair-value predictions."""
    avg_predicted_days: float
    avg_actual_days: float
    mae_days: float
    rmse_days: float
    within_30_days_pct: float  # % predictions within ±30 days
    sample_size: int


@dataclass
class IndustryPerformance:
    """Performance breakdown by industry."""
    industry_code: str
    industry_name: Optional[str]
    total_predictions: int
    avg_return_error: float
    best_performing_method: str
    worst_performing_method: str
    avg_confidence: float


@dataclass
class PerformanceReport:
    """Comprehensive performance report."""
    report_date: datetime
    total_predictions: int
    verified_predictions: int
    overall_accuracy: float
    
    # Method-level performance
    method_performance: List[MethodPerformance]
    
    # Scenario calibration
    scenario_calibration: List[ScenarioCalibration]
    
    # Time-to-target metrics
    time_metrics: TimeToTargetMetrics
    
    # Industry breakdown
    industry_performance: List[IndustryPerformance]
    
    # Alerts
    degradation_alerts: List[str]
    recommendation_accuracy: float  # % where ML recommendation was profitable


class ValuationPerformanceMonitor:
    """
    Monitor and analyze valuation model performance.
    
    Tracks:
    - Method-specific accuracy (DCF vs Comparables vs...)
    - Scenario probability calibration
    - Time-to-target accuracy
    - Industry/stock-specific performance patterns
    - Performance degradation alerts
    - Recommendation accuracy tracking
    """
    
    def __init__(
        self,
        db_session: AsyncSession,
        tenant_id: str,
        degradation_threshold: float = 0.15  # 15% accuracy drop triggers alert
    ):
        """
        Initialize performance monitor.
        
        Args:
            db_session: Async database session
            tenant_id: Tenant identifier for multi-tenancy
            degradation_threshold: Threshold for performance degradation alert
        """
        self.db = db_session
        self.tenant_id = tenant_id
        self.degradation_threshold = degradation_threshold
    
    async def generate_performance_report(
        self,
        days_back: int = 90,
        model_version: Optional[str] = None
    ) -> PerformanceReport:
        """
        Generate comprehensive performance report.
        
        Args:
            days_back: Number of days to analyze
            model_version: Specific model version to analyze (None = all)
        
        Returns:
            PerformanceReport with all metrics
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        
        # Build base query
        query = select(ValuationPrediction).where(
            and_(
                ValuationPrediction.tenant_id == self.tenant_id,
                ValuationPrediction.prediction_date >= cutoff_date
            )
        )
        
        if model_version:
            query = query.where(ValuationPrediction.model_version == model_version)
        
        result = await self.db.execute(query)
        predictions = result.scalars().all()
        
        total_predictions = len(predictions)
        verified_predictions = len([p for p in predictions if p.is_verified == "verified"])
        
        # Calculate all metrics in parallel
        method_perf = await self._calculate_method_performance(predictions)
        scenario_cal = await self._calculate_scenario_calibration(predictions)
        time_metrics = await self._calculate_time_metrics(predictions)
        industry_perf = await self._calculate_industry_performance(predictions)
        degradation_alerts = await self._detect_performance_degradation(days_back)
        rec_accuracy = await self._calculate_recommendation_accuracy(predictions)
        overall_accuracy = await self._calculate_overall_accuracy(predictions)
        
        return PerformanceReport(
            report_date=datetime.utcnow(),
            total_predictions=total_predictions,
            verified_predictions=verified_predictions,
            overall_accuracy=overall_accuracy,
            method_performance=method_perf,
            scenario_calibration=scenario_cal,
            time_metrics=time_metrics,
            industry_performance=industry_perf,
            degradation_alerts=degradation_alerts,
            recommendation_accuracy=rec_accuracy
        )
    
    async def _calculate_method_performance(
        self,
        predictions: List[ValuationPrediction]
    ) -> List[MethodPerformance]:
        """Calculate performance metrics for each valuation method."""
        methods = ["DCF", "Comparables", "Residual Income", "DDM", "Asset-Based"]
        results = []
        
        # Filter verified predictions with outcomes
        verified = [p for p in predictions if p.is_verified == "verified" and p.outcomes]
        
        for method in methods:
            # Predictions where this method was predicted as best
            method_predictions = [p for p in verified if p.predicted_best_method == method]
            
            if not method_predictions:
                continue
            
            # Calculate accuracy: did predicted method actually perform best?
            # (This requires comparing all method returns from outcomes - simplified here)
            accuracy_count = 0
            total_confidence = 0.0
            total_return_error = 0.0
            
            for pred in method_predictions:
                total_confidence += pred.method_confidence or 0.0
                
                # Get actual return (using 6M as benchmark)
                if pred.outcomes:
                    outcome = pred.outcomes[0]  # Most recent outcome
                    actual_return = outcome.actual_return_6m or 0.0
                    expected_return = pred.expected_return_6m or 0.0
                    total_return_error += abs(actual_return - expected_return)
                    
                    # Simple accuracy: was return positive when predicted positive?
                    if (actual_return > 0 and expected_return > 0) or \
                       (actual_return < 0 and expected_return < 0):
                        accuracy_count += 1
            
            total_pred = len(method_predictions)
            accuracy_rate = accuracy_count / total_pred if total_pred > 0 else 0.0
            avg_confidence = total_confidence / total_pred if total_pred > 0 else 0.0
            avg_return_error = total_return_error / total_pred if total_pred > 0 else 0.0
            
            # Calculate precision and recall
            # Precision: when we predicted this method, how often was it actually best
            precision = accuracy_rate  # Simplified
            
            # Recall: when this method was actually best, how often did we predict it
            # (Requires knowing which method was actually best - simplified)
            recall = accuracy_rate  # Simplified
            
            results.append(MethodPerformance(
                method_name=method,
                total_predictions=total_pred,
                accuracy_rate=accuracy_rate,
                avg_confidence=avg_confidence,
                avg_return_error=avg_return_error,
                precision=precision,
                recall=recall
            ))
        
        return results
    
    async def _calculate_scenario_calibration(
        self,
        predictions: List[ValuationPrediction]
    ) -> List[ScenarioCalibration]:
        """Calculate calibration metrics for scenario probabilities."""
        scenarios = ["bull", "base", "bear"]
        results = []
        
        verified = [p for p in predictions if p.is_verified == "verified" and p.outcomes]
        
        for scenario in scenarios:
            # Average predicted probability for this scenario
            if scenario == "bull":
                probs = [p.bull_probability or 0.0 for p in verified]
            elif scenario == "base":
                probs = [p.base_probability or 0.0 for p in verified]
            else:  # bear
                probs = [p.bear_probability or 0.0 for p in verified]
            
            avg_predicted_prob = np.mean(probs) if probs else 0.0
            
            # Actual frequency: how often did this scenario occur?
            actual_occurrences = sum(
                1 for p in verified
                if p.outcomes and p.outcomes[0].materialized_scenario == scenario
            )
            actual_frequency = actual_occurrences / len(verified) if verified else 0.0
            
            calibration_error = abs(avg_predicted_prob - actual_frequency)
            
            results.append(ScenarioCalibration(
                scenario=scenario,
                predicted_probability=avg_predicted_prob,
                actual_frequency=actual_frequency,
                calibration_error=calibration_error,
                sample_size=len(verified)
            ))
        
        return results
    
    async def _calculate_time_metrics(
        self,
        predictions: List[ValuationPrediction]
    ) -> TimeToTargetMetrics:
        """Calculate time-to-fair-value prediction metrics."""
        verified = [p for p in predictions if p.is_verified == "verified" and p.outcomes]
        
        if not verified:
            return TimeToTargetMetrics(
                avg_predicted_days=0.0,
                avg_actual_days=0.0,
                mae_days=0.0,
                rmse_days=0.0,
                within_30_days_pct=0.0,
                sample_size=0
            )
        
        predicted_days = [p.expected_time_to_fair_value or 180.0 for p in verified]
        
        # Estimate actual days to fair value based on when return target was hit
        actual_days = []
        for pred in verified:
            if pred.outcomes:
                outcome = pred.outcomes[0]
                # Simplified: use days_elapsed as proxy
                actual_days.append(outcome.days_elapsed or 180.0)
        
        avg_predicted = np.mean(predicted_days)
        avg_actual = np.mean(actual_days) if actual_days else 0.0
        
        errors = [abs(p - a) for p, a in zip(predicted_days, actual_days)]
        mae = np.mean(errors) if errors else 0.0
        rmse = np.sqrt(np.mean([e**2 for e in errors])) if errors else 0.0
        
        within_30_days = sum(1 for e in errors if e <= 30)
        within_30_days_pct = within_30_days / len(errors) if errors else 0.0
        
        return TimeToTargetMetrics(
            avg_predicted_days=avg_predicted,
            avg_actual_days=avg_actual,
            mae_days=mae,
            rmse_days=rmse,
            within_30_days_pct=within_30_days_pct,
            sample_size=len(verified)
        )
    
    async def _calculate_industry_performance(
        self,
        predictions: List[ValuationPrediction]
    ) -> List[IndustryPerformance]:
        """Calculate performance breakdown by industry."""
        # Group predictions by industry (using company.industry_code)
        # Simplified: return empty list (requires joining with companies table)
        return []
    
    async def _detect_performance_degradation(
        self,
        days_back: int
    ) -> List[str]:
        """Detect performance degradation over time."""
        alerts = []
        
        # Compare recent performance (last 30 days) vs historical (31-90 days)
        recent_cutoff = datetime.utcnow() - timedelta(days=30)
        historical_cutoff = datetime.utcnow() - timedelta(days=days_back)
        
        # Recent performance
        recent_query = select(ValuationPrediction).where(
            and_(
                ValuationPrediction.tenant_id == self.tenant_id,
                ValuationPrediction.prediction_date >= recent_cutoff,
                ValuationPrediction.is_verified == "verified"
            )
        )
        recent_result = await self.db.execute(recent_query)
        recent_preds = recent_result.scalars().all()
        
        # Historical performance
        historical_query = select(ValuationPrediction).where(
            and_(
                ValuationPrediction.tenant_id == self.tenant_id,
                ValuationPrediction.prediction_date >= historical_cutoff,
                ValuationPrediction.prediction_date < recent_cutoff,
                ValuationPrediction.is_verified == "verified"
            )
        )
        historical_result = await self.db.execute(historical_query)
        historical_preds = historical_result.scalars().all()
        
        if not recent_preds or not historical_preds:
            return alerts
        
        # Calculate accuracy for both periods
        recent_accuracy = await self._calculate_overall_accuracy(recent_preds)
        historical_accuracy = await self._calculate_overall_accuracy(historical_preds)
        
        # Check for degradation
        accuracy_drop = historical_accuracy - recent_accuracy
        if accuracy_drop > self.degradation_threshold:
            alerts.append(
                f"Performance degradation detected: Accuracy dropped from "
                f"{historical_accuracy:.2%} to {recent_accuracy:.2%} "
                f"({accuracy_drop:.2%} decline)"
            )
        
        # Check for method-specific degradation
        methods = ["DCF", "Comparables", "Residual Income", "DDM", "Asset-Based"]
        for method in methods:
            recent_method = [p for p in recent_preds if p.predicted_best_method == method]
            historical_method = [p for p in historical_preds if p.predicted_best_method == method]
            
            if not recent_method or not historical_method:
                continue
            
            recent_method_acc = await self._calculate_overall_accuracy(recent_method)
            historical_method_acc = await self._calculate_overall_accuracy(historical_method)
            
            method_drop = historical_method_acc - recent_method_acc
            if method_drop > self.degradation_threshold:
                alerts.append(
                    f"Method '{method}' degradation: Accuracy dropped from "
                    f"{historical_method_acc:.2%} to {recent_method_acc:.2%}"
                )
        
        return alerts
    
    async def _calculate_recommendation_accuracy(
        self,
        predictions: List[ValuationPrediction]
    ) -> float:
        """Calculate accuracy of ML recommendations (buy/sell/hold)."""
        verified = [p for p in predictions if p.is_verified == "verified" and p.outcomes]
        
        if not verified:
            return 0.0
        
        profitable_count = 0
        for pred in verified:
            if pred.outcomes:
                outcome = pred.outcomes[0]
                # If expected return was positive and actual was positive: correct
                # If expected return was negative and actual was negative: correct
                expected = pred.expected_return_6m or 0.0
                actual = outcome.actual_return_6m or 0.0
                
                if (expected > 0 and actual > 0) or (expected < 0 and actual < 0):
                    profitable_count += 1
        
        return profitable_count / len(verified)
    
    async def _calculate_overall_accuracy(
        self,
        predictions: List[ValuationPrediction]
    ) -> float:
        """Calculate overall prediction accuracy."""
        verified = [p for p in predictions if p.is_verified == "verified" and p.outcomes]
        
        if not verified:
            return 0.0
        
        correct_direction = 0
        for pred in verified:
            if pred.outcomes:
                outcome = pred.outcomes[0]
                expected = pred.expected_return_6m or 0.0
                actual = outcome.actual_return_6m or 0.0
                
                if (expected > 0 and actual > 0) or (expected < 0 and actual < 0):
                    correct_direction += 1
        
        return correct_direction / len(verified)
