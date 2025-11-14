"""
Dynamic Model Weights Manager.

Manages reading/writing of ML model weights from database.
Provides daily updated weights instead of static values.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Dict, Optional
from uuid import UUID
import logging

from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ml_model_weights import MLModelWeights, MLModelPerformance

logger = logging.getLogger(__name__)


class DynamicWeightsManager:
    """
    Manager for dynamic model weights.
    
    Fetches latest weights from database instead of using hardcoded values.
    Weights are updated daily by ModelWeightTrainer.
    """
    
    # Fallback weights if database is empty
    DEFAULT_WEIGHTS = {
        'dcf': 0.20,
        'rim': 0.18,
        'eva': 0.15,
        'graham': 0.12,
        'peter_lynch': 0.10,
        'ncav': 0.08,
        'ps_ratio': 0.09,
        'pcf_ratio': 0.08,
    }
    
    def __init__(self, db: AsyncSession):
        """Initialize manager."""
        self.db = db
    
    async def get_current_weights(
        self,
        effective_date: Optional[date] = None,
    ) -> Dict[str, float]:
        """
        Get current active model weights.
        
        Args:
            effective_date: Date for which to get weights (default: today)
            
        Returns:
            Dictionary of model weights (sum = 1.0)
        """
        if effective_date is None:
            effective_date = date.today()
        
        try:
            # Query most recent active weights
            query = (
                select(MLModelWeights)
                .where(
                    and_(
                        MLModelWeights.is_active == True,
                        MLModelWeights.effective_date <= effective_date,
                    )
                )
                .order_by(desc(MLModelWeights.effective_date))
                .limit(1)
            )
            
            result = await self.db.execute(query)
            weights_row = result.scalar_one_or_none()
            
            if weights_row:
                weights = {
                    'dcf': float(weights_row.dcf_weight),
                    'rim': float(weights_row.rim_weight),
                    'eva': float(weights_row.eva_weight),
                    'graham': float(weights_row.graham_weight),
                    'peter_lynch': float(weights_row.peter_lynch_weight),
                    'ncav': float(weights_row.ncav_weight),
                    'ps_ratio': float(weights_row.ps_ratio_weight),
                    'pcf_ratio': float(weights_row.pcf_ratio_weight),
                }
                
                logger.info(f"✅ Loaded dynamic weights from DB (date: {weights_row.effective_date})")
                return weights
            else:
                logger.warning(f"⚠️ No weights found in DB, using defaults")
                return self.DEFAULT_WEIGHTS.copy()
        
        except Exception as e:
            logger.error(f"❌ Error loading weights from DB: {e}")
            return self.DEFAULT_WEIGHTS.copy()
    
    async def save_new_weights(
        self,
        weights: Dict[str, float],
        training_metrics: Optional[Dict] = None,
        deployed_by: str = "system",
    ) -> MLModelWeights:
        """
        Save new weights to database.
        
        Args:
            weights: Model weights dictionary
            training_metrics: Training performance metrics
            deployed_by: Who deployed these weights
            
        Returns:
            Created MLModelWeights record
        """
        # Deactivate old weights
        await self._deactivate_old_weights()
        
        # Create new weights record
        new_weights = MLModelWeights(
            effective_date=datetime.utcnow(),
            is_active=True,
            dcf_weight=Decimal(str(weights['dcf'])),
            rim_weight=Decimal(str(weights['rim'])),
            eva_weight=Decimal(str(weights['eva'])),
            graham_weight=Decimal(str(weights['graham'])),
            peter_lynch_weight=Decimal(str(weights['peter_lynch'])),
            ncav_weight=Decimal(str(weights['ncav'])),
            ps_ratio_weight=Decimal(str(weights['ps_ratio'])),
            pcf_ratio_weight=Decimal(str(weights['pcf_ratio'])),
            deployed_at=datetime.utcnow(),
            deployed_by=deployed_by,
            training_accuracy=Decimal(str(training_metrics.get('training_accuracy', 0))) if training_metrics else None,
            validation_accuracy=Decimal(str(training_metrics.get('validation_accuracy', 0))) if training_metrics else None,
            backtest_mape=Decimal(str(training_metrics.get('backtest_mape', 0))) if training_metrics else None,
            improvement_vs_previous=Decimal(str(training_metrics.get('improvement', 0))) if training_metrics else None,
            training_samples=training_metrics.get('training_samples', 0) if training_metrics else None,
            ab_test_passed=training_metrics.get('ab_test_passed', False) if training_metrics else None,
            ab_test_p_value=Decimal(str(training_metrics.get('ab_test_p_value', 1.0))) if training_metrics else None,
        )
        
        self.db.add(new_weights)
        await self.db.commit()
        await self.db.refresh(new_weights)
        
        logger.info(f"💾 Saved new weights to DB: {weights}")
        return new_weights
    
    async def _deactivate_old_weights(self):
        """Deactivate all currently active weights."""
        query = (
            select(MLModelWeights)
            .where(MLModelWeights.is_active == True)
        )
        
        result = await self.db.execute(query)
        old_weights = result.scalars().all()
        
        for weight_record in old_weights:
            weight_record.is_active = False
        
        if old_weights:
            await self.db.commit()
            logger.info(f"🔄 Deactivated {len(old_weights)} old weight records")
    
    async def get_weights_history(
        self,
        limit: int = 10,
    ) -> list[MLModelWeights]:
        """
        Get historical weights.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of MLModelWeights records
        """
        query = (
            select(MLModelWeights)
            .order_by(desc(MLModelWeights.effective_date))
            .limit(limit)
        )
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def record_model_performance(
        self,
        company_id: UUID,
        valuation_date: datetime,
        predictions: Dict[str, float],
        actual_price: float,
        weights_used: Dict[str, float],
    ) -> MLModelPerformance:
        """
        Record performance of models vs actual price.
        
        Args:
            company_id: Company UUID
            valuation_date: When valuation was made
            predictions: Model predictions {'dcf': 100, 'rim': 110, ...}
            actual_price: Actual market price
            weights_used: Weights that were used
            
        Returns:
            Created performance record
        """
        # Calculate errors
        errors = {}
        for model, pred in predictions.items():
            if pred > 0:
                error = abs(pred - actual_price) / actual_price * 100
                errors[model] = error
        
        # Find best/worst
        best_model = min(errors.keys(), key=lambda m: errors[m]) if errors else None
        worst_model = max(errors.keys(), key=lambda m: errors[m]) if errors else None
        
        # Calculate ensemble prediction
        ensemble_pred = sum(
            weights_used.get(model, 0) * predictions.get(model, 0)
            for model in weights_used.keys()
        )
        ensemble_error = abs(ensemble_pred - actual_price) / actual_price * 100 if actual_price > 0 else 0
        
        # Create performance record
        perf = MLModelPerformance(
            company_id=company_id,
            valuation_date=valuation_date,
            measurement_date=datetime.utcnow(),
            dcf_prediction=Decimal(str(predictions.get('dcf', 0))),
            rim_prediction=Decimal(str(predictions.get('rim', 0))),
            eva_prediction=Decimal(str(predictions.get('eva', 0))),
            graham_prediction=Decimal(str(predictions.get('graham', 0))),
            peter_lynch_prediction=Decimal(str(predictions.get('peter_lynch', 0))),
            ncav_prediction=Decimal(str(predictions.get('ncav', 0))),
            ps_ratio_prediction=Decimal(str(predictions.get('ps_ratio', 0))),
            pcf_ratio_prediction=Decimal(str(predictions.get('pcf_ratio', 0))),
            ensemble_prediction=Decimal(str(ensemble_pred)),
            actual_price=Decimal(str(actual_price)),
            dcf_error=Decimal(str(errors.get('dcf', 0))),
            rim_error=Decimal(str(errors.get('rim', 0))),
            eva_error=Decimal(str(errors.get('eva', 0))),
            graham_error=Decimal(str(errors.get('graham', 0))),
            peter_lynch_error=Decimal(str(errors.get('peter_lynch', 0))),
            ncav_error=Decimal(str(errors.get('ncav', 0))),
            ps_ratio_error=Decimal(str(errors.get('ps_ratio', 0))),
            pcf_ratio_error=Decimal(str(errors.get('pcf_ratio', 0))),
            ensemble_error=Decimal(str(ensemble_error)),
            best_model=best_model,
            worst_model=worst_model,
            weights_snapshot=weights_used,
        )
        
        self.db.add(perf)
        await self.db.commit()
        await self.db.refresh(perf)
        
        logger.info(f"📊 Recorded performance: Ensemble error={ensemble_error:.2f}%, Best={best_model}")
        return perf
    
    async def get_model_accuracy_stats(
        self,
        days_lookback: int = 90,
    ) -> Dict[str, Dict[str, float]]:
        """
        Get accuracy statistics for each model over time.
        
        Args:
            days_lookback: Number of days to look back
            
        Returns:
            {
                'dcf': {'mean_error': 8.5, 'std': 3.2, 'count': 50},
                'rim': {'mean_error': 10.2, 'std': 4.1, 'count': 50},
                ...
            }
        """
        from datetime import timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_lookback)
        
        query = (
            select(MLModelPerformance)
            .where(MLModelPerformance.measurement_date >= cutoff_date)
        )
        
        result = await self.db.execute(query)
        records = result.scalars().all()
        
        if not records:
            return {}
        
        # Collect errors per model
        model_errors = {
            'dcf': [],
            'rim': [],
            'eva': [],
            'graham': [],
            'peter_lynch': [],
            'ncav': [],
            'ps_ratio': [],
            'pcf_ratio': [],
            'ensemble': [],
        }
        
        for record in records:
            model_errors['dcf'].append(float(record.dcf_error or 0))
            model_errors['rim'].append(float(record.rim_error or 0))
            model_errors['eva'].append(float(record.eva_error or 0))
            model_errors['graham'].append(float(record.graham_error or 0))
            model_errors['peter_lynch'].append(float(record.peter_lynch_error or 0))
            model_errors['ncav'].append(float(record.ncav_error or 0))
            model_errors['ps_ratio'].append(float(record.ps_ratio_error or 0))
            model_errors['pcf_ratio'].append(float(record.pcf_ratio_error or 0))
            model_errors['ensemble'].append(float(record.ensemble_error or 0))
        
        # Calculate stats
        import numpy as np
        
        stats = {}
        for model, errors in model_errors.items():
            if errors:
                stats[model] = {
                    'mean_error': float(np.mean(errors)),
                    'std_error': float(np.std(errors)),
                    'median_error': float(np.median(errors)),
                    'min_error': float(np.min(errors)),
                    'max_error': float(np.max(errors)),
                    'count': len(errors),
                }
        
        return stats
