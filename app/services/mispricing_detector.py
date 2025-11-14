"""
===============================================================================
FILE IDENTITY CARD
===============================================================================
Filename    : mispricing_detector.py
Created     : 2025
Author      : Elite Development Team
Department  : Machine Learning Services
Project     : Gravity Fundamental Analysis
Module      : Real-Time Mispricing Detection
Version     : 1.0.0

Purpose     : Detect undervalued/overvalued stocks in real-time using ML
              predictions and multi-method valuation consensus. Generate
              high-confidence investment opportunities with risk/reward analysis.

Scope       : Production mispricing detection for investment decision support
Components  : Mispricing score, confidence levels, opportunity ranking

Dependencies:
    - SQLAlchemy (async database operations)
    - NumPy (statistical calculations)
    - app.services.valuation_prediction_model (ValuationPredictor)
    - app.services.valuation_feature_engineer (ValuationFeatureEngineer)
    - app.models.company (Company)
    - app.core.database (Database session management)

Output      : Mispricing opportunities with scoring and ranking

Notes       : Part of Task 7 - Real-Time Mispricing Detection
              Combines ML predictions with multi-method consensus
              Provides actionable investment signals with confidence levels
===============================================================================
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.core.exceptions import ValidationError, NotFoundError


class MispricingType(str, Enum):
    """Type of mispricing detected."""
    UNDERVALUED = "undervalued"
    OVERVALUED = "overvalued"
    FAIRLY_VALUED = "fairly_valued"


class OpportunityLevel(str, Enum):
    """Investment opportunity confidence level."""
    EXTREME = "extreme"  # >30% mispricing, high confidence
    HIGH = "high"  # 20-30% mispricing, high confidence
    MEDIUM = "medium"  # 10-20% mispricing, medium confidence
    LOW = "low"  # 5-10% mispricing, low confidence
    NONE = "none"  # <5% mispricing or low confidence


@dataclass
class MispricingScore:
    """
    Mispricing score for a single stock.
    
    Combines ML predictions, multi-method consensus, and market data
    to generate actionable mispricing signal.
    """
    company_id: int
    symbol: str
    company_name: str
    
    # Current market data
    current_price: float
    market_cap: Optional[float]
    
    # Valuation-based fair values
    consensus_fair_value: float  # Weighted average across methods
    fair_value_range: Tuple[float, float]  # (min, max) from all methods
    
    # Mispricing metrics
    mispricing_type: MispricingType
    mispricing_pct: float  # (fair_value - price) / price
    absolute_mispricing: float  # fair_value - price
    
    # ML prediction data
    ml_expected_return_6m: float
    ml_expected_return_12m: float
    ml_predicted_method: str
    ml_method_confidence: float
    
    # Scenario probabilities
    bull_probability: float
    base_probability: float
    bear_probability: float
    
    # Risk/reward analysis
    upside_potential: float  # Max fair value vs price
    downside_risk: float  # Min fair value vs price
    risk_reward_ratio: float  # upside / max(downside, 0.01)
    
    # Consensus strength
    method_agreement: float  # 0-1, how much methods agree
    valuation_confidence: float  # Combined confidence score
    
    # Opportunity classification
    opportunity_level: OpportunityLevel
    conviction_score: float  # 0-100, overall conviction
    
    # Timing
    expected_time_to_fair_value: Optional[float]  # Days
    detection_date: datetime = field(default_factory=datetime.utcnow)
    
    # Additional context
    industry_code: Optional[str] = None
    metadata: Dict = field(default_factory=dict)


@dataclass
class MispricingAlert:
    """Alert for high-conviction mispricing opportunity."""
    alert_id: str
    mispricing: MispricingScore
    alert_type: str  # "buy", "sell", "watch"
    urgency: str  # "immediate", "short_term", "long_term"
    reason: str  # Human-readable explanation
    action: str  # Recommended action
    price_target: float
    stop_loss: Optional[float]
    created_at: datetime = field(default_factory=datetime.utcnow)


class MispricingDetector:
    """
    Detect undervalued/overvalued stocks in real-time.
    
    Uses ML predictions combined with multi-method valuation consensus
    to identify high-confidence mispricing opportunities.
    """
    
    def __init__(
        self,
        db_session: AsyncSession,
        tenant_id: str,
        min_conviction: float = 70.0,  # Minimum conviction score for alerts
        min_mispricing: float = 0.10  # Minimum 10% mispricing
    ):
        """
        Initialize mispricing detector.
        
        Args:
            db_session: Async database session
            tenant_id: Tenant identifier
            min_conviction: Minimum conviction score for opportunities
            min_mispricing: Minimum mispricing percentage threshold
        """
        self.db = db_session
        self.tenant_id = tenant_id
        self.min_conviction = min_conviction
        self.min_mispricing = min_mispricing
    
    async def detect_mispricing(
        self,
        company_id: int,
        current_price: float,
        valuation_outputs: Dict,  # 15 valuation values from all methods
        ml_prediction: Dict,  # ML model prediction output
        features: Dict  # Valuation features
    ) -> MispricingScore:
        """
        Detect mispricing for a single company.
        
        Args:
            company_id: Company ID
            current_price: Current market price
            valuation_outputs: Dict with all 15 valuation values
            ml_prediction: ML model prediction
            features: Valuation features dict
        
        Returns:
            MispricingScore object
        """
        # Get company info
        company_query = select(Company).where(
            and_(
                Company.id == company_id,
                Company.tenant_id == self.tenant_id
            )
        )
        result = await self.db.execute(company_query)
        company = result.scalar_one_or_none()
        
        if not company:
            raise NotFoundError(f"Company {company_id} not found")
        
        # Calculate consensus fair value (weighted by method confidence)
        fair_values = self._extract_fair_values(valuation_outputs)
        consensus_fair_value = self._calculate_consensus_fair_value(
            fair_values,
            ml_prediction
        )
        
        # Calculate fair value range
        fair_value_range = (min(fair_values.values()), max(fair_values.values()))
        
        # Calculate mispricing metrics
        mispricing_pct = (consensus_fair_value - current_price) / current_price
        absolute_mispricing = consensus_fair_value - current_price
        
        mispricing_type = self._classify_mispricing(mispricing_pct)
        
        # Calculate risk/reward
        upside = (fair_value_range[1] - current_price) / current_price
        downside = (fair_value_range[0] - current_price) / current_price
        risk_reward_ratio = upside / max(abs(downside), 0.01) if downside < 0 else upside / 0.01
        
        # Calculate method agreement
        method_agreement = self._calculate_method_agreement(fair_values, consensus_fair_value)
        
        # Calculate valuation confidence
        valuation_confidence = self._calculate_valuation_confidence(
            method_agreement,
            ml_prediction.get("method_confidence", 0.5),
            features
        )
        
        # Calculate conviction score
        conviction_score = self._calculate_conviction_score(
            abs(mispricing_pct),
            valuation_confidence,
            ml_prediction.get("method_confidence", 0.5),
            method_agreement,
            risk_reward_ratio
        )
        
        # Classify opportunity level
        opportunity_level = self._classify_opportunity(
            abs(mispricing_pct),
            conviction_score
        )
        
        return MispricingScore(
            company_id=company_id,
            symbol=company.symbol,
            company_name=company.name_fa or company.name_en,
            current_price=current_price,
            market_cap=company.market_cap,
            consensus_fair_value=consensus_fair_value,
            fair_value_range=fair_value_range,
            mispricing_type=mispricing_type,
            mispricing_pct=mispricing_pct,
            absolute_mispricing=absolute_mispricing,
            ml_expected_return_6m=ml_prediction.get("expected_return_6m", 0.0),
            ml_expected_return_12m=ml_prediction.get("expected_return_12m", 0.0),
            ml_predicted_method=ml_prediction.get("predicted_method", "Unknown"),
            ml_method_confidence=ml_prediction.get("method_confidence", 0.0),
            bull_probability=ml_prediction.get("bull_probability", 0.33),
            base_probability=ml_prediction.get("base_probability", 0.34),
            bear_probability=ml_prediction.get("bear_probability", 0.33),
            upside_potential=upside,
            downside_risk=downside,
            risk_reward_ratio=risk_reward_ratio,
            method_agreement=method_agreement,
            valuation_confidence=valuation_confidence,
            opportunity_level=opportunity_level,
            conviction_score=conviction_score,
            expected_time_to_fair_value=ml_prediction.get("time_to_fair_value"),
            industry_code=company.industry_code,
            metadata={
                "fair_values": fair_values,
                "features": features
            }
        )
    
    async def scan_market_opportunities(
        self,
        top_n: int = 20,
        mispricing_type: Optional[MispricingType] = None
    ) -> List[MispricingScore]:
        """
        Scan entire market for mispricing opportunities.
        
        Args:
            top_n: Number of top opportunities to return
            mispricing_type: Filter by type (undervalued/overvalued/None=all)
        
        Returns:
            List of top mispricing opportunities, sorted by conviction
        """
        # This would iterate through all companies and detect mispricing
        # Simplified: return empty list (requires full implementation)
        return []
    
    async def generate_alert(
        self,
        mispricing: MispricingScore,
        force: bool = False
    ) -> Optional[MispricingAlert]:
        """
        Generate alert for high-conviction mispricing.
        
        Args:
            mispricing: MispricingScore object
            force: Force alert generation even if conviction is low
        
        Returns:
            MispricingAlert if conviction >= threshold, else None
        """
        if not force and mispricing.conviction_score < self.min_conviction:
            return None
        
        if not force and abs(mispricing.mispricing_pct) < self.min_mispricing:
            return None
        
        # Determine alert type and action
        if mispricing.mispricing_type == MispricingType.UNDERVALUED:
            alert_type = "buy"
            action = f"Consider buying {mispricing.symbol} at current levels"
            price_target = mispricing.consensus_fair_value
            stop_loss = mispricing.current_price * 0.92  # 8% stop loss
        elif mispricing.mispricing_type == MispricingType.OVERVALUED:
            alert_type = "sell"
            action = f"Consider selling/avoiding {mispricing.symbol}"
            price_target = mispricing.consensus_fair_value
            stop_loss = None
        else:
            alert_type = "watch"
            action = f"Monitor {mispricing.symbol} for entry opportunity"
            price_target = mispricing.current_price
            stop_loss = None
        
        # Determine urgency
        if mispricing.opportunity_level == OpportunityLevel.EXTREME:
            urgency = "immediate"
        elif mispricing.opportunity_level == OpportunityLevel.HIGH:
            urgency = "short_term"
        else:
            urgency = "long_term"
        
        # Generate reason
        reason = self._generate_alert_reason(mispricing)
        
        alert_id = f"{mispricing.symbol}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        return MispricingAlert(
            alert_id=alert_id,
            mispricing=mispricing,
            alert_type=alert_type,
            urgency=urgency,
            reason=reason,
            action=action,
            price_target=price_target,
            stop_loss=stop_loss
        )
    
    def _extract_fair_values(self, valuation_outputs: Dict) -> Dict[str, float]:
        """Extract fair values from all methods and scenarios."""
        fair_values = {}
        
        methods = ["DCF", "Comparables", "Residual_Income", "DDM", "Asset_Based"]
        scenarios = ["bull", "base", "bear"]
        
        for method in methods:
            # Use base scenario as primary fair value for each method
            key = f"{method}_base"
            if key in valuation_outputs:
                fair_values[method] = valuation_outputs[key]
        
        return fair_values
    
    def _calculate_consensus_fair_value(
        self,
        fair_values: Dict[str, float],
        ml_prediction: Dict
    ) -> float:
        """
        Calculate consensus fair value using weighted average.
        
        Weights based on ML predicted method and historical accuracy.
        """
        if not fair_values:
            return 0.0
        
        # Get ML predicted best method
        predicted_method = ml_prediction.get("predicted_method", "")
        method_confidence = ml_prediction.get("method_confidence", 0.5)
        
        # Calculate weights
        weights = {}
        total_weight = 0.0
        
        for method, value in fair_values.items():
            if method == predicted_method:
                # Give higher weight to ML predicted method
                weight = method_confidence
            else:
                # Equal weight to other methods
                weight = (1.0 - method_confidence) / max(len(fair_values) - 1, 1)
            
            weights[method] = weight
            total_weight += weight
        
        # Normalize weights
        if total_weight > 0:
            weights = {k: v / total_weight for k, v in weights.items()}
        
        # Calculate weighted average
        consensus = sum(fair_values[m] * weights.get(m, 0.2) for m in fair_values)
        
        return consensus
    
    def _classify_mispricing(self, mispricing_pct: float) -> MispricingType:
        """Classify mispricing type based on percentage."""
        if mispricing_pct > 0.05:  # >5% undervalued
            return MispricingType.UNDERVALUED
        elif mispricing_pct < -0.05:  # >5% overvalued
            return MispricingType.OVERVALUED
        else:
            return MispricingType.FAIRLY_VALUED
    
    def _calculate_method_agreement(
        self,
        fair_values: Dict[str, float],
        consensus: float
    ) -> float:
        """
        Calculate how much methods agree (0-1).
        
        Higher agreement = lower variance in fair values.
        """
        if not fair_values or len(fair_values) < 2:
            return 0.5
        
        values = list(fair_values.values())
        
        # Calculate coefficient of variation
        mean_val = np.mean(values)
        std_val = np.std(values)
        
        if mean_val == 0:
            return 0.0
        
        cv = std_val / mean_val  # Coefficient of variation
        
        # Convert CV to agreement score (lower CV = higher agreement)
        # CV of 0.10 (10%) = 0.9 agreement
        # CV of 0.30 (30%) = 0.7 agreement
        agreement = max(0.0, min(1.0, 1.0 - cv))
        
        return agreement
    
    def _calculate_valuation_confidence(
        self,
        method_agreement: float,
        ml_confidence: float,
        features: Dict
    ) -> float:
        """Calculate overall valuation confidence score (0-1)."""
        # Combine multiple confidence signals
        confidence = (
            method_agreement * 0.4 +  # Method agreement: 40%
            ml_confidence * 0.4 +  # ML confidence: 40%
            0.2  # Base confidence: 20%
        )
        
        return min(1.0, max(0.0, confidence))
    
    def _calculate_conviction_score(
        self,
        mispricing_magnitude: float,
        valuation_confidence: float,
        ml_confidence: float,
        method_agreement: float,
        risk_reward_ratio: float
    ) -> float:
        """
        Calculate overall conviction score (0-100).
        
        Combines:
        - Mispricing magnitude (larger = higher conviction)
        - Valuation confidence (higher = higher conviction)
        - ML confidence (higher = higher conviction)
        - Method agreement (higher = higher conviction)
        - Risk/reward ratio (higher = higher conviction)
        """
        # Normalize mispricing to 0-1 scale (30% mispricing = 1.0)
        mispricing_score = min(1.0, mispricing_magnitude / 0.30)
        
        # Normalize risk/reward ratio (3.0 = 1.0)
        rr_score = min(1.0, risk_reward_ratio / 3.0)
        
        # Weighted combination
        conviction = (
            mispricing_score * 0.30 +  # Mispricing magnitude: 30%
            valuation_confidence * 0.25 +  # Valuation confidence: 25%
            ml_confidence * 0.20 +  # ML confidence: 20%
            method_agreement * 0.15 +  # Method agreement: 15%
            rr_score * 0.10  # Risk/reward: 10%
        )
        
        return conviction * 100.0  # Convert to 0-100 scale
    
    def _classify_opportunity(
        self,
        mispricing_magnitude: float,
        conviction_score: float
    ) -> OpportunityLevel:
        """Classify opportunity level based on mispricing and conviction."""
        if mispricing_magnitude >= 0.30 and conviction_score >= 80:
            return OpportunityLevel.EXTREME
        elif mispricing_magnitude >= 0.20 and conviction_score >= 70:
            return OpportunityLevel.HIGH
        elif mispricing_magnitude >= 0.10 and conviction_score >= 60:
            return OpportunityLevel.MEDIUM
        elif mispricing_magnitude >= 0.05 and conviction_score >= 50:
            return OpportunityLevel.LOW
        else:
            return OpportunityLevel.NONE
    
    def _generate_alert_reason(self, mispricing: MispricingScore) -> str:
        """Generate human-readable alert reason."""
        direction = "undervalued" if mispricing.mispricing_type == MispricingType.UNDERVALUED else "overvalued"
        
        reason = (
            f"{mispricing.symbol} appears {direction} by {abs(mispricing.mispricing_pct):.1%}. "
            f"Consensus fair value: {mispricing.consensus_fair_value:.0f} vs "
            f"current price: {mispricing.current_price:.0f}. "
            f"ML predicts {mispricing.ml_expected_return_6m:.1%} return in 6M "
            f"using {mispricing.ml_predicted_method} method "
            f"(confidence: {mispricing.ml_method_confidence:.0%}). "
            f"Conviction score: {mispricing.conviction_score:.0f}/100."
        )
        
        return reason
