"""
===============================================================================
FILE IDENTITY CARD
===============================================================================
Filename    : valuation_ensemble.py
Created     : 2025
Author      : Elite Development Team
Department  : Valuation Services
Project     : Gravity Fundamental Analysis
Module      : Valuation Method Ensemble
Version     : 1.0.0

Purpose     : Ensemble combining all 5 valuation methods using weighted voting
              based on historical accuracy, market regime, and stock characteristics.
              Provides consensus valuation with confidence intervals.

Scope       : Production ensemble system for robust valuation estimates
Components  : Dynamic weighting, market regime detection, consensus calculation

Dependencies:
    - SQLAlchemy (async database operations)
    - NumPy (statistical calculations)
    - app.models.prediction_tracking (ValuationPrediction, PredictionOutcome)
    - app.services.valuation_performance (ValuationPerformanceMonitor)
    - app.core.database (Database session management)

Output      : Ensemble valuation with confidence intervals and method weights

Notes       : Part of Task 8 - Valuation Method Ensemble
              Combines DCF, Comparables, Residual Income, DDM, Asset-Based
              Adapts weights based on historical performance and market conditions
===============================================================================
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import numpy as np
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.prediction_tracking import ValuationPrediction, PredictionOutcome
from app.core.exceptions import ValidationError


class MarketRegime(str, Enum):
    """Market regime classification."""
    BULL = "bull"  # Strong uptrend
    BEAR = "bear"  # Strong downtrend
    SIDEWAYS = "sideways"  # Range-bound
    VOLATILE = "volatile"  # High volatility


@dataclass
class MethodWeight:
    """Weight for a single valuation method."""
    method_name: str
    weight: float  # 0-1
    accuracy_based: float  # Weight from historical accuracy
    regime_adjusted: float  # Adjustment for market regime
    stock_specific: float  # Adjustment for stock characteristics
    final_weight: float  # Combined final weight
    sample_size: int  # Number of historical predictions


@dataclass
class EnsembleValuation:
    """Ensemble valuation combining all methods."""
    company_id: int
    symbol: str
    valuation_date: datetime
    
    # Individual method valuations
    method_valuations: Dict[str, float]  # {method: fair_value}
    
    # Ensemble consensus
    consensus_fair_value: float
    weighted_average: float
    simple_average: float
    median_value: float
    
    # Confidence intervals
    confidence_interval_95: Tuple[float, float]  # (low, high)
    confidence_interval_68: Tuple[float, float]  # (low, high)
    
    # Method weights
    method_weights: List[MethodWeight]
    
    # Disagreement metrics
    method_disagreement: float  # Std dev / mean
    max_deviation: float  # Max deviation from consensus
    min_max_range: Tuple[float, float]  # (min, max) valuations
    
    # Market context
    market_regime: MarketRegime
    regime_confidence: float  # 0-1
    
    # Ensemble confidence
    ensemble_confidence: float  # 0-1, overall confidence
    recommendation_strength: str  # "strong", "moderate", "weak"


class ValuationEnsemble:
    """
    Ensemble combining all 5 valuation methods with dynamic weighting.
    
    Features:
    - Historical accuracy-based weighting
    - Market regime adjustment (bull/bear/sideways)
    - Stock/industry-specific weights
    - Dynamic weight updates
    - Consensus valuation with confidence intervals
    - Method disagreement detection
    """
    
    def __init__(
        self,
        db_session: AsyncSession,
        tenant_id: str,
        lookback_days: int = 365  # Historical performance window
    ):
        """
        Initialize valuation ensemble.
        
        Args:
            db_session: Async database session
            tenant_id: Tenant identifier
            lookback_days: Days of historical data for weight calculation
        """
        self.db = db_session
        self.tenant_id = tenant_id
        self.lookback_days = lookback_days
        
        # Default equal weights (fallback when no historical data)
        self.default_weights = {
            "DCF": 0.25,
            "Comparables": 0.25,
            "Residual Income": 0.20,
            "DDM": 0.15,
            "Asset-Based": 0.15
        }
    
    async def calculate_ensemble_valuation(
        self,
        company_id: int,
        symbol: str,
        method_valuations: Dict[str, float],  # {method: fair_value}
        market_regime: Optional[MarketRegime] = None,
        industry_code: Optional[str] = None
    ) -> EnsembleValuation:
        """
        Calculate ensemble valuation combining all methods.
        
        Args:
            company_id: Company ID
            symbol: Stock symbol
            method_valuations: Dict of {method_name: fair_value}
            market_regime: Current market regime (auto-detected if None)
            industry_code: Industry code for industry-specific weights
        
        Returns:
            EnsembleValuation with consensus and confidence intervals
        """
        # Detect market regime if not provided
        if market_regime is None:
            market_regime, regime_confidence = await self._detect_market_regime()
        else:
            regime_confidence = 0.8  # Assume high confidence if provided
        
        # Calculate method weights
        method_weights = await self._calculate_method_weights(
            company_id,
            market_regime,
            industry_code
        )
        
        # Calculate consensus valuation
        consensus = self._calculate_weighted_consensus(
            method_valuations,
            method_weights
        )
        
        # Calculate alternative consensus measures
        simple_avg = np.mean(list(method_valuations.values()))
        median_val = np.median(list(method_valuations.values()))
        
        # Calculate confidence intervals
        ci_95 = self._calculate_confidence_interval(method_valuations, 0.95)
        ci_68 = self._calculate_confidence_interval(method_valuations, 0.68)
        
        # Calculate disagreement metrics
        disagreement = self._calculate_disagreement(method_valuations, consensus)
        max_dev = max(abs(v - consensus) for v in method_valuations.values())
        min_max = (min(method_valuations.values()), max(method_valuations.values()))
        
        # Calculate ensemble confidence
        ensemble_conf = self._calculate_ensemble_confidence(
            disagreement,
            method_weights,
            regime_confidence
        )
        
        # Determine recommendation strength
        rec_strength = self._determine_recommendation_strength(
            ensemble_conf,
            disagreement
        )
        
        return EnsembleValuation(
            company_id=company_id,
            symbol=symbol,
            valuation_date=datetime.utcnow(),
            method_valuations=method_valuations,
            consensus_fair_value=consensus,
            weighted_average=consensus,
            simple_average=simple_avg,
            median_value=median_val,
            confidence_interval_95=ci_95,
            confidence_interval_68=ci_68,
            method_weights=method_weights,
            method_disagreement=disagreement,
            max_deviation=max_dev,
            min_max_range=min_max,
            market_regime=market_regime,
            regime_confidence=regime_confidence,
            ensemble_confidence=ensemble_conf,
            recommendation_strength=rec_strength
        )
    
    async def _calculate_method_weights(
        self,
        company_id: int,
        market_regime: MarketRegime,
        industry_code: Optional[str]
    ) -> List[MethodWeight]:
        """
        Calculate dynamic weights for each valuation method.
        
        Combines:
        1. Historical accuracy-based weights
        2. Market regime adjustments
        3. Stock/industry-specific adjustments
        """
        methods = ["DCF", "Comparables", "Residual Income", "DDM", "Asset-Based"]
        weights = []
        
        # Get historical accuracy for each method
        accuracy_weights = await self._get_historical_accuracy_weights(company_id)
        
        # Calculate regime-adjusted weights
        for method in methods:
            # Start with accuracy-based weight
            acc_weight = accuracy_weights.get(method, self.default_weights[method])
            
            # Apply market regime adjustment
            regime_adj = self._get_regime_adjustment(method, market_regime)
            
            # Apply stock-specific adjustment
            stock_adj = self._get_stock_specific_adjustment(
                method,
                company_id,
                industry_code
            )
            
            # Combine adjustments
            final_weight = acc_weight * regime_adj * stock_adj
            
            weights.append(MethodWeight(
                method_name=method,
                weight=final_weight,
                accuracy_based=acc_weight,
                regime_adjusted=regime_adj,
                stock_specific=stock_adj,
                final_weight=final_weight,
                sample_size=accuracy_weights.get(f"{method}_samples", 0)
            ))
        
        # Normalize weights to sum to 1.0
        total_weight = sum(w.final_weight for w in weights)
        if total_weight > 0:
            for w in weights:
                w.final_weight = w.final_weight / total_weight
        
        return weights
    
    async def _get_historical_accuracy_weights(
        self,
        company_id: int
    ) -> Dict[str, float]:
        """
        Calculate weights based on historical accuracy of each method.
        
        Returns dict: {method: weight, method_samples: count}
        """
        cutoff_date = datetime.utcnow() - timedelta(days=self.lookback_days)
        
        # Query historical predictions with outcomes
        query = select(ValuationPrediction).where(
            and_(
                ValuationPrediction.tenant_id == self.tenant_id,
                ValuationPrediction.company_id == company_id,
                ValuationPrediction.prediction_date >= cutoff_date,
                ValuationPrediction.is_verified == "verified"
            )
        )
        
        result = await self.db.execute(query)
        predictions = result.scalars().all()
        
        if not predictions:
            # No historical data, use defaults
            return self.default_weights.copy()
        
        # Calculate accuracy for each method
        method_accuracy = {}
        method_samples = {}
        
        methods = ["DCF", "Comparables", "Residual Income", "DDM", "Asset-Based"]
        
        for method in methods:
            method_preds = [p for p in predictions if p.predicted_best_method == method]
            
            if not method_preds:
                method_accuracy[method] = 0.5  # Neutral accuracy
                method_samples[method] = 0
                continue
            
            # Calculate accuracy: MAE of 6M return predictions
            errors = []
            for pred in method_preds:
                if pred.outcomes:
                    outcome = pred.outcomes[0]
                    if outcome.actual_return_6m is not None and pred.expected_return_6m is not None:
                        error = abs(outcome.actual_return_6m - pred.expected_return_6m)
                        errors.append(error)
            
            if errors:
                mae = np.mean(errors)
                # Convert MAE to accuracy score (lower MAE = higher accuracy)
                # MAE of 0.10 (10%) = 0.9 accuracy, MAE of 0.50 (50%) = 0.5 accuracy
                accuracy = max(0.0, 1.0 - mae)
                method_accuracy[method] = accuracy
                method_samples[method] = len(errors)
            else:
                method_accuracy[method] = 0.5
                method_samples[method] = 0
        
        # Convert accuracy to weights
        total_accuracy = sum(method_accuracy.values())
        if total_accuracy > 0:
            weights = {m: acc / total_accuracy for m, acc in method_accuracy.items()}
        else:
            weights = self.default_weights.copy()
        
        # Add sample sizes
        for method in methods:
            weights[f"{method}_samples"] = method_samples.get(method, 0)
        
        return weights
    
    def _get_regime_adjustment(
        self,
        method: str,
        regime: MarketRegime
    ) -> float:
        """
        Get method weight adjustment based on market regime.
        
        Different methods perform better in different regimes:
        - Bull: Comparables, DCF (growth-focused)
        - Bear: Asset-Based, DDM (safety-focused)
        - Sideways: Residual Income, DCF
        - Volatile: Asset-Based (stable floor)
        """
        adjustments = {
            MarketRegime.BULL: {
                "DCF": 1.2,
                "Comparables": 1.3,
                "Residual Income": 1.0,
                "DDM": 0.8,
                "Asset-Based": 0.7
            },
            MarketRegime.BEAR: {
                "DCF": 0.8,
                "Comparables": 0.7,
                "Residual Income": 1.0,
                "DDM": 1.2,
                "Asset-Based": 1.4
            },
            MarketRegime.SIDEWAYS: {
                "DCF": 1.1,
                "Comparables": 1.0,
                "Residual Income": 1.2,
                "DDM": 1.0,
                "Asset-Based": 0.9
            },
            MarketRegime.VOLATILE: {
                "DCF": 0.9,
                "Comparables": 0.8,
                "Residual Income": 1.0,
                "DDM": 1.1,
                "Asset-Based": 1.3
            }
        }
        
        return adjustments.get(regime, {}).get(method, 1.0)
    
    def _get_stock_specific_adjustment(
        self,
        method: str,
        company_id: int,
        industry_code: Optional[str]
    ) -> float:
        """
        Get stock/industry-specific method adjustment.
        
        Different industries favor different methods:
        - Tech/Growth: DCF, Comparables
        - Banks/Insurance: Asset-Based
        - Utilities/Mature: DDM, Residual Income
        """
        # Simplified: return neutral adjustment
        # In production, would query industry characteristics
        return 1.0
    
    def _calculate_weighted_consensus(
        self,
        valuations: Dict[str, float],
        weights: List[MethodWeight]
    ) -> float:
        """Calculate weighted average consensus."""
        total = 0.0
        total_weight = 0.0
        
        for weight in weights:
            if weight.method_name in valuations:
                total += valuations[weight.method_name] * weight.final_weight
                total_weight += weight.final_weight
        
        if total_weight > 0:
            return total / total_weight
        else:
            return np.mean(list(valuations.values()))
    
    def _calculate_confidence_interval(
        self,
        valuations: Dict[str, float],
        confidence_level: float
    ) -> Tuple[float, float]:
        """
        Calculate confidence interval for ensemble valuation.
        
        Uses standard deviation of method valuations.
        """
        values = list(valuations.values())
        mean = np.mean(values)
        std = np.std(values)
        
        # Z-scores for confidence levels
        z_scores = {0.68: 1.0, 0.95: 1.96, 0.99: 2.58}
        z = z_scores.get(confidence_level, 1.96)
        
        margin = z * std
        return (mean - margin, mean + margin)
    
    def _calculate_disagreement(
        self,
        valuations: Dict[str, float],
        consensus: float
    ) -> float:
        """
        Calculate disagreement metric (coefficient of variation).
        
        Lower disagreement = higher confidence in ensemble.
        """
        values = list(valuations.values())
        if not values or consensus == 0:
            return 1.0
        
        std = np.std(values)
        cv = std / abs(consensus)  # Coefficient of variation
        
        return min(1.0, cv)
    
    def _calculate_ensemble_confidence(
        self,
        disagreement: float,
        weights: List[MethodWeight],
        regime_confidence: float
    ) -> float:
        """Calculate overall ensemble confidence (0-1)."""
        # Lower disagreement = higher confidence
        disagreement_conf = max(0.0, 1.0 - disagreement)
        
        # Average weight confidence (sample sizes)
        avg_samples = np.mean([w.sample_size for w in weights])
        sample_conf = min(1.0, avg_samples / 20.0)  # 20+ samples = full confidence
        
        # Combined confidence
        confidence = (
            disagreement_conf * 0.5 +  # Method agreement: 50%
            sample_conf * 0.3 +  # Historical data: 30%
            regime_confidence * 0.2  # Market regime: 20%
        )
        
        return min(1.0, max(0.0, confidence))
    
    def _determine_recommendation_strength(
        self,
        ensemble_confidence: float,
        disagreement: float
    ) -> str:
        """Determine recommendation strength."""
        if ensemble_confidence >= 0.75 and disagreement <= 0.15:
            return "strong"
        elif ensemble_confidence >= 0.60 and disagreement <= 0.25:
            return "moderate"
        else:
            return "weak"
    
    async def _detect_market_regime(self) -> Tuple[MarketRegime, float]:
        """
        Detect current market regime.
        
        Returns (regime, confidence).
        Simplified: returns sideways with medium confidence.
        In production, would analyze market indices, volatility, trends.
        """
        # Placeholder: analyze market data to detect regime
        return MarketRegime.SIDEWAYS, 0.7
