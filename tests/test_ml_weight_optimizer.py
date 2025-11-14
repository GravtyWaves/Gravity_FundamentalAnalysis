"""
Unit tests for MLWeightOptimizer.

Tests ML-based weight optimization system covering:
- Default weight fallback
- Model training with synthetic data
- Weight optimization and caching
- Model persistence (save/load)
- Weight validation
- Feature importance extraction
- Sector-specific weights
"""

import pytest
from datetime import date
from pathlib import Path
from uuid import uuid4
import numpy as np

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ml_weight_optimizer import MLWeightOptimizer
from app.models.company import Company


@pytest.fixture
async def optimizer(test_db: AsyncSession, test_tenant_id: str) -> MLWeightOptimizer:
    """Create test ML weight optimizer."""
    return MLWeightOptimizer(test_db, test_tenant_id)


@pytest.fixture
def clean_model_file(optimizer: MLWeightOptimizer):
    """Clean up model file after test."""
    yield
    if optimizer.MODEL_PATH.exists():
        optimizer.MODEL_PATH.unlink()


class TestDefaultWeights:
    """Test default weight fallback behavior."""

    @pytest.mark.asyncio
    async def test_default_weights_returned_when_no_model(
        self,
        optimizer: MLWeightOptimizer
    ):
        """Test that default weights are returned when ML model not trained."""
        # Set min training samples impossibly high to prevent training
        optimizer.MIN_TRAINING_SAMPLES = 999999
        
        # Get weights (should not train due to insufficient data)
        weights = await optimizer.get_optimized_weights()

        # Should return default weights
        assert weights == optimizer.DEFAULT_WEIGHTS
        assert sum(weights.values()) == pytest.approx(1.0)
        assert weights["valuation"] == 0.25
        assert weights["profitability"] == 0.20

    @pytest.mark.asyncio
    async def test_default_weights_sum_to_one(self, optimizer: MLWeightOptimizer):
        """Test that default weights sum to 1.0."""
        weights = optimizer.DEFAULT_WEIGHTS
        assert sum(weights.values()) == pytest.approx(1.0, abs=0.001)

    @pytest.mark.asyncio
    async def test_default_weights_all_positive(self, optimizer: MLWeightOptimizer):
        """Test that all default weights are positive."""
        weights = optimizer.DEFAULT_WEIGHTS
        assert all(w > 0 for w in weights.values())


class TestModelTraining:
    """Test ML model training functionality."""

    @pytest.mark.asyncio
    async def test_train_model_with_sufficient_data(
        self,
        optimizer: MLWeightOptimizer,
        clean_model_file
    ):
        """Test successful model training with sufficient data."""
        # Force training
        await optimizer._train_model()

        # Model should be trained
        assert optimizer.model is not None
        assert optimizer.weights_cache is not None
        assert optimizer.last_training_date == date.today()

    @pytest.mark.asyncio
    async def test_trained_weights_sum_to_one(
        self,
        optimizer: MLWeightOptimizer,
        clean_model_file
    ):
        """Test that trained weights sum to 1.0."""
        await optimizer._train_model()

        weights = optimizer.weights_cache
        assert sum(weights.values()) == pytest.approx(1.0, abs=0.001)

    @pytest.mark.asyncio
    async def test_trained_weights_all_positive(
        self,
        optimizer: MLWeightOptimizer,
        clean_model_file
    ):
        """Test that all trained weights are positive."""
        await optimizer._train_model()

        weights = optimizer.weights_cache
        assert all(w > 0 for w in weights.values())

    @pytest.mark.asyncio
    async def test_training_date_updated(
        self,
        optimizer: MLWeightOptimizer,
        clean_model_file
    ):
        """Test that training date is updated after training."""
        assert optimizer.last_training_date is None

        await optimizer._train_model()

        assert optimizer.last_training_date is not None
        assert optimizer.last_training_date == date.today()


class TestWeightOptimization:
    """Test weight optimization and caching."""

    @pytest.mark.asyncio
    async def test_get_optimized_weights_triggers_training(
        self,
        optimizer: MLWeightOptimizer,
        clean_model_file
    ):
        """Test that get_optimized_weights triggers training if needed."""
        weights = await optimizer.get_optimized_weights()

        # Should have trained model
        assert optimizer.model is not None
        assert optimizer.weights_cache is not None
        assert weights == optimizer.weights_cache

    @pytest.mark.asyncio
    async def test_weights_cached_after_training(
        self,
        optimizer: MLWeightOptimizer,
        clean_model_file
    ):
        """Test that weights are cached after first training."""
        weights1 = await optimizer.get_optimized_weights()
        weights2 = await optimizer.get_optimized_weights()

        # Should return same cached weights
        assert weights1 == weights2

    @pytest.mark.asyncio
    async def test_force_retrain_updates_weights(
        self,
        optimizer: MLWeightOptimizer,
        clean_model_file
    ):
        """Test that force_retrain=True triggers retraining."""
        weights1 = await optimizer.get_optimized_weights()

        # Clear cache to force retrain
        optimizer.weights_cache = None
        weights2 = await optimizer.get_optimized_weights(force_retrain=True)

        # Weights should be recalculated
        assert optimizer.weights_cache is not None


class TestModelPersistence:
    """Test model save/load functionality."""

    @pytest.mark.asyncio
    async def test_save_model_creates_file(
        self,
        optimizer: MLWeightOptimizer,
        clean_model_file
    ):
        """Test that model is saved to disk."""
        await optimizer._train_model()
        await optimizer._save_model()

        assert optimizer.MODEL_PATH.exists()

    @pytest.mark.asyncio
    async def test_load_model_from_disk(
        self,
        test_db: AsyncSession,
        test_tenant_id: str,
        clean_model_file
    ):
        """Test loading model from disk."""
        # Train and save model
        optimizer1 = MLWeightOptimizer(test_db, test_tenant_id)
        await optimizer1._train_model()
        await optimizer1._save_model()

        # Create new optimizer and load model
        optimizer2 = MLWeightOptimizer(test_db, test_tenant_id)
        loaded = await optimizer2.load_model()

        assert loaded is True
        assert optimizer2.model is not None
        assert optimizer2.weights_cache is not None
        assert optimizer2.weights_cache == optimizer1.weights_cache

    @pytest.mark.asyncio
    async def test_load_model_fails_when_file_missing(
        self,
        optimizer: MLWeightOptimizer
    ):
        """Test load_model returns False when file doesn't exist."""
        loaded = await optimizer.load_model()
        assert loaded is False


class TestFeatureImportance:
    """Test feature importance extraction."""

    @pytest.mark.asyncio
    async def test_get_dimension_importance_after_training(
        self,
        optimizer: MLWeightOptimizer,
        clean_model_file
    ):
        """Test extracting feature importances from trained model."""
        await optimizer._train_model()

        importances = await optimizer.get_dimension_importance()

        # Should have 5 dimensions
        assert len(importances) == 5
        assert "valuation" in importances
        assert "profitability" in importances
        assert "growth" in importances
        assert "financial_health" in importances
        assert "risk" in importances

    @pytest.mark.asyncio
    async def test_dimension_importance_all_positive(
        self,
        optimizer: MLWeightOptimizer,
        clean_model_file
    ):
        """Test that all feature importances are positive."""
        await optimizer._train_model()

        importances = await optimizer.get_dimension_importance()
        assert all(imp >= 0 for imp in importances.values())

    @pytest.mark.asyncio
    async def test_dimension_importance_before_training(
        self,
        optimizer: MLWeightOptimizer
    ):
        """Test feature importances before training (equal importance)."""
        importances = await optimizer.get_dimension_importance()

        # Should return equal importance (0.20 each)
        assert all(imp == 0.20 for imp in importances.values())


class TestWeightValidation:
    """Test weight validation functionality."""

    @pytest.mark.asyncio
    async def test_validate_valid_weights(
        self,
        optimizer: MLWeightOptimizer
    ):
        """Test validation of valid weights."""
        valid_weights = {
            "valuation": 0.25,
            "profitability": 0.20,
            "growth": 0.20,
            "financial_health": 0.20,
            "risk": 0.15,
        }

        is_valid = await optimizer.validate_weights(valid_weights)
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_validate_weights_missing_dimension(
        self,
        optimizer: MLWeightOptimizer
    ):
        """Test validation fails when dimension missing."""
        invalid_weights = {
            "valuation": 0.25,
            "profitability": 0.25,
            # Missing: growth, financial_health, risk
        }

        is_valid = await optimizer.validate_weights(invalid_weights)
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_validate_weights_negative_value(
        self,
        optimizer: MLWeightOptimizer
    ):
        """Test validation fails with negative weights."""
        invalid_weights = {
            "valuation": 0.25,
            "profitability": -0.10,  # Negative!
            "growth": 0.30,
            "financial_health": 0.30,
            "risk": 0.25,
        }

        is_valid = await optimizer.validate_weights(invalid_weights)
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_validate_weights_not_sum_to_one(
        self,
        optimizer: MLWeightOptimizer
    ):
        """Test validation fails when weights don't sum to 1.0."""
        invalid_weights = {
            "valuation": 0.25,
            "profitability": 0.25,
            "growth": 0.25,
            "financial_health": 0.25,
            "risk": 0.25,  # Sum = 1.25, not 1.0
        }

        is_valid = await optimizer.validate_weights(invalid_weights)
        assert is_valid is False


class TestSectorSpecificWeights:
    """Test sector-specific weight optimization."""

    @pytest.mark.asyncio
    async def test_get_weights_with_sector_filter(
        self,
        optimizer: MLWeightOptimizer,
        clean_model_file
    ):
        """Test getting sector-specific weights."""
        # Get weights for technology sector
        tech_weights = await optimizer.get_optimized_weights(sector="Technology")

        # Should return weights (may be same as default if not enough sector data)
        assert tech_weights is not None
        assert sum(tech_weights.values()) == pytest.approx(1.0, abs=0.001)


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_get_weights_returns_default_on_error(
        self,
        optimizer: MLWeightOptimizer
    ):
        """Test that errors during optimization return default weights."""
        # Simulate error by breaking model
        optimizer.model = None
        optimizer.MIN_TRAINING_SAMPLES = 999999  # Impossibly high

        weights = await optimizer.get_optimized_weights()

        # Should fallback to default weights
        assert weights == optimizer.DEFAULT_WEIGHTS

    @pytest.mark.asyncio
    async def test_training_with_insufficient_data_logs_warning(
        self,
        optimizer: MLWeightOptimizer,
        caplog
    ):
        """Test warning logged when insufficient training data."""
        optimizer.MIN_TRAINING_SAMPLES = 999999  # Set impossibly high

        await optimizer._train_model()

        # Should log warning about insufficient data
        assert "Insufficient training data" in caplog.text
        assert optimizer.model is None
