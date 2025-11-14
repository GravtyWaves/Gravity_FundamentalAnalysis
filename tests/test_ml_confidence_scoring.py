"""
Unit tests for ML model confidence scoring.

Tests confidence score calculation based on:
- R² score (model accuracy)
- Cross-validation consistency
- Training data size
- Confidence level categorization
"""

import pytest
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ml_weight_optimizer import MLWeightOptimizer


@pytest.fixture
async def optimizer_with_metrics(
    test_db: AsyncSession,
    test_tenant_id: str
) -> MLWeightOptimizer:
    """Create optimizer with trained model and metrics."""
    optimizer = MLWeightOptimizer(test_db, test_tenant_id)
    await optimizer._train_model()
    return optimizer


class TestConfidenceScore:
    """Test ML model confidence score calculation."""

    @pytest.mark.asyncio
    async def test_confidence_score_excellent_model(
        self,
        test_db: AsyncSession,
        test_tenant_id: str
    ):
        """Test confidence score for excellent model (R² > 0.9)."""
        optimizer = MLWeightOptimizer(test_db, test_tenant_id)
        optimizer.model_metrics = {
            "r2_score": 0.95,
            "mse": 0.05,
            "cv_mean": 0.93,
            "cv_std": 0.02,
            "training_samples": 200,
            "test_samples": 50,
        }

        confidence = await optimizer.get_model_confidence_score()

        # Excellent model should have high confidence (>0.9)
        assert confidence >= 0.9
        assert confidence <= 1.0

    @pytest.mark.asyncio
    async def test_confidence_score_good_model(
        self,
        test_db: AsyncSession,
        test_tenant_id: str
    ):
        """Test confidence score for good model (R² = 0.7-0.9)."""
        optimizer = MLWeightOptimizer(test_db, test_tenant_id)
        optimizer.model_metrics = {
            "r2_score": 0.8,
            "mse": 0.15,
            "cv_mean": 0.78,
            "cv_std": 0.05,
            "training_samples": 150,
            "test_samples": 50,
        }

        confidence = await optimizer.get_model_confidence_score()

        # Good model should have 0.7-0.9 confidence
        assert 0.7 <= confidence < 0.9

    @pytest.mark.asyncio
    async def test_confidence_score_moderate_model(
        self,
        test_db: AsyncSession,
        test_tenant_id: str
    ):
        """Test confidence score for moderate model (R² = 0.5-0.7)."""
        optimizer = MLWeightOptimizer(test_db, test_tenant_id)
        optimizer.model_metrics = {
            "r2_score": 0.6,
            "mse": 0.25,
            "cv_mean": 0.58,
            "cv_std": 0.08,
            "training_samples": 120,
            "test_samples": 30,
        }

        confidence = await optimizer.get_model_confidence_score()

        # Moderate model should have 0.5-0.7 confidence
        assert 0.5 <= confidence < 0.7

    @pytest.mark.asyncio
    async def test_confidence_score_poor_model(
        self,
        test_db: AsyncSession,
        test_tenant_id: str
    ):
        """Test confidence score for poor model (R² < 0.3)."""
        optimizer = MLWeightOptimizer(test_db, test_tenant_id)
        optimizer.model_metrics = {
            "r2_score": 0.2,
            "mse": 0.5,
            "cv_mean": 0.18,
            "cv_std": 0.15,
            "training_samples": 80,
            "test_samples": 20,
        }

        confidence = await optimizer.get_model_confidence_score()

        # Poor model should have low confidence (<0.4)
        assert confidence < 0.4

    @pytest.mark.asyncio
    async def test_confidence_penalty_for_high_cv_std(
        self,
        test_db: AsyncSession,
        test_tenant_id: str
    ):
        """Test that high CV std reduces confidence (inconsistent model)."""
        optimizer = MLWeightOptimizer(test_db, test_tenant_id)
        
        # Good model with low CV std
        optimizer.model_metrics = {
            "r2_score": 0.8,
            "cv_mean": 0.78,
            "cv_std": 0.02,  # Low std = consistent
            "training_samples": 150,
            "test_samples": 50,
        }
        confidence_low_std = await optimizer.get_model_confidence_score()

        # Same model but high CV std
        optimizer.model_metrics["cv_std"] = 0.3  # High std = inconsistent
        confidence_high_std = await optimizer.get_model_confidence_score()

        # High CV std should reduce confidence
        assert confidence_high_std < confidence_low_std

    @pytest.mark.asyncio
    async def test_confidence_penalty_for_insufficient_data(
        self,
        test_db: AsyncSession,
        test_tenant_id: str
    ):
        """Test that insufficient training data reduces confidence."""
        optimizer = MLWeightOptimizer(test_db, test_tenant_id)
        
        # Good model with sufficient data
        optimizer.model_metrics = {
            "r2_score": 0.8,
            "cv_mean": 0.78,
            "cv_std": 0.05,
            "training_samples": 200,  # Above MIN_TRAINING_SAMPLES
            "test_samples": 50,
        }
        confidence_sufficient = await optimizer.get_model_confidence_score()

        # Same model but insufficient data
        optimizer.model_metrics["training_samples"] = 50  # Below MIN_TRAINING_SAMPLES (100)
        confidence_insufficient = await optimizer.get_model_confidence_score()

        # Insufficient data should reduce confidence
        assert confidence_insufficient < confidence_sufficient

    @pytest.mark.asyncio
    async def test_confidence_score_no_metrics(
        self,
        test_db: AsyncSession,
        test_tenant_id: str
    ):
        """Test default confidence when no metrics available."""
        optimizer = MLWeightOptimizer(test_db, test_tenant_id)
        optimizer.model_metrics = None

        confidence = await optimizer.get_model_confidence_score()

        # Should return default confidence (0.5)
        assert confidence == 0.5


class TestModelMetrics:
    """Test get_model_metrics functionality."""

    @pytest.mark.asyncio
    async def test_get_metrics_trained_model(
        self,
        optimizer_with_metrics: MLWeightOptimizer
    ):
        """Test getting metrics from trained model."""
        metrics = await optimizer_with_metrics.get_model_metrics()

        assert metrics["status"] == "trained"
        assert "training_date" in metrics
        assert "performance" in metrics
        assert "r2_score" in metrics["performance"]
        assert "mse" in metrics["performance"]
        assert "cv_mean" in metrics["performance"]
        assert "cv_std" in metrics["performance"]
        assert "training_data" in metrics
        assert "confidence_score" in metrics
        assert "confidence_level" in metrics

    @pytest.mark.asyncio
    async def test_get_metrics_untrained_model(
        self,
        test_db: AsyncSession,
        test_tenant_id: str
    ):
        """Test getting metrics from untrained model."""
        optimizer = MLWeightOptimizer(test_db, test_tenant_id)
        optimizer.model_metrics = None

        metrics = await optimizer.get_model_metrics()

        assert metrics["status"] == "untrained"
        assert "message" in metrics
        assert metrics["confidence_score"] == 0.5

    @pytest.mark.asyncio
    async def test_metrics_include_training_data_info(
        self,
        optimizer_with_metrics: MLWeightOptimizer
    ):
        """Test that metrics include training data information."""
        metrics = await optimizer_with_metrics.get_model_metrics()

        training_data = metrics["training_data"]
        assert "training_samples" in training_data
        assert "test_samples" in training_data
        assert "total_samples" in training_data
        assert training_data["total_samples"] == (
            training_data["training_samples"] + training_data["test_samples"]
        )

    @pytest.mark.asyncio
    async def test_metrics_include_confidence_level(
        self,
        optimizer_with_metrics: MLWeightOptimizer
    ):
        """Test that metrics include human-readable confidence level."""
        metrics = await optimizer_with_metrics.get_model_metrics()

        confidence_level = metrics["confidence_level"]
        assert confidence_level in [
            "excellent", "good", "moderate", "fair", "poor"
        ]


class TestConfidenceLevel:
    """Test confidence level categorization."""

    @pytest.mark.asyncio
    async def test_excellent_confidence_level(
        self,
        test_db: AsyncSession,
        test_tenant_id: str
    ):
        """Test excellent confidence level (0.9-1.0)."""
        optimizer = MLWeightOptimizer(test_db, test_tenant_id)
        
        level = optimizer._get_confidence_level(0.95)
        assert level == "excellent"

    @pytest.mark.asyncio
    async def test_good_confidence_level(
        self,
        test_db: AsyncSession,
        test_tenant_id: str
    ):
        """Test good confidence level (0.7-0.9)."""
        optimizer = MLWeightOptimizer(test_db, test_tenant_id)
        
        level = optimizer._get_confidence_level(0.8)
        assert level == "good"

    @pytest.mark.asyncio
    async def test_moderate_confidence_level(
        self,
        test_db: AsyncSession,
        test_tenant_id: str
    ):
        """Test moderate confidence level (0.5-0.7)."""
        optimizer = MLWeightOptimizer(test_db, test_tenant_id)
        
        level = optimizer._get_confidence_level(0.6)
        assert level == "moderate"

    @pytest.mark.asyncio
    async def test_fair_confidence_level(
        self,
        test_db: AsyncSession,
        test_tenant_id: str
    ):
        """Test fair confidence level (0.3-0.5)."""
        optimizer = MLWeightOptimizer(test_db, test_tenant_id)
        
        level = optimizer._get_confidence_level(0.4)
        assert level == "fair"

    @pytest.mark.asyncio
    async def test_poor_confidence_level(
        self,
        test_db: AsyncSession,
        test_tenant_id: str
    ):
        """Test poor confidence level (<0.3)."""
        optimizer = MLWeightOptimizer(test_db, test_tenant_id)
        
        level = optimizer._get_confidence_level(0.2)
        assert level == "poor"


class TestIntegrationWithScoring:
    """Test integration of confidence metrics with scoring service."""

    @pytest.mark.asyncio
    async def test_scoring_includes_confidence(
        self,
        test_db: AsyncSession,
        test_tenant_id: str,
        optimizer_with_metrics: MLWeightOptimizer
    ):
        """Test that scoring service includes ML confidence."""
        # This would require full integration test with StockScoringService
        # For now, verify optimizer provides the data
        confidence = await optimizer_with_metrics.get_model_confidence_score()
        metrics = await optimizer_with_metrics.get_model_metrics()

        assert confidence is not None
        assert 0.0 <= confidence <= 1.0
        assert metrics["confidence_score"] == confidence
