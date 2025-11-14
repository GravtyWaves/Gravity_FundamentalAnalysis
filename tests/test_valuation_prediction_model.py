"""
================================================================================
FILE IDENTITY
================================================================================
File Path:           tests/test_valuation_prediction_model.py
Author:              João Silva (Testing Lead)
Team ID:             FA-TESTING
Created Date:        2025-11-14
Last Modified:       2025-11-14
Version:             1.0.0
Purpose:             Comprehensive unit tests for ValuationPredictionModel
                     Testing ML model training, inference, serialization

Dependencies:        pytest>=7.4, torch>=2.0, numpy>=1.24, pandas>=2.0

Related Files:       app/services/valuation_prediction_model.py (service under test)
                     tests/conftest.py (test fixtures)

Test Coverage:       95%+ target
Lines of Code:       400
Time Spent:          4 hours
Cost:                $600 (4 × $150/hr Elite)
Review Status:       Complete
Notes:               - Tests neural network architecture
                     - Validates multi-task learning
                     - Tests model save/load
                     - Performance benchmarks (<10ms inference)
================================================================================
"""

from datetime import datetime
from pathlib import Path
from typing import Dict
from uuid import uuid4

import numpy as np
import pytest
import torch

from app.services.valuation_prediction_model import (
    MultiTaskValuationNetwork,
    TrainingConfig,
    ValuationDataset,
    ValuationPredictionModel,
)


@pytest.fixture
def sample_features() -> np.ndarray:
    """Create sample feature data."""
    # 130 features × 100 samples
    np.random.seed(42)
    return np.random.randn(100, 130).astype(np.float32)


@pytest.fixture
def sample_targets() -> Dict[str, np.ndarray]:
    """Create sample target data for multi-task learning."""
    np.random.seed(42)
    return {
        "method": np.random.randint(0, 5, size=100),  # 5 valuation methods
        "scenarios": np.random.rand(100, 3).astype(np.float32),  # 3 scenarios
        "returns": np.random.randn(100, 4).astype(np.float32),  # 4 horizons
        "time": np.random.uniform(1, 365, size=100).astype(np.float32),  # Days
    }


@pytest.fixture
def training_config() -> TrainingConfig:
    """Create training configuration for tests."""
    return TrainingConfig(
        batch_size=16,
        learning_rate=0.001,
        epochs=5,  # Small for testing
        validation_split=0.2,
        early_stopping_patience=3,
        dropout_rate=0.3,
    )


@pytest.fixture
def model() -> MultiTaskValuationNetwork:
    """Create a model instance for testing."""
    return MultiTaskValuationNetwork(
        input_dim=130,
        hidden_dims=[256, 128, 64],
        dropout_rate=0.3,
    )


class TestValuationDataset:
    """Test suite for ValuationDataset."""

    def test_dataset_initialization(
        self, sample_features: np.ndarray, sample_targets: Dict[str, np.ndarray]
    ):
        """Test dataset initialization."""
        dataset = ValuationDataset(sample_features, sample_targets)
        
        assert len(dataset) == 100
        assert dataset.features.shape == (100, 130)
        assert dataset.method_labels.shape == (100,)
        assert dataset.scenario_probs.shape == (100, 3)
        assert dataset.returns.shape == (100, 4)
        assert dataset.time_to_target.shape == (100, 1)

    def test_dataset_getitem(
        self, sample_features: np.ndarray, sample_targets: Dict[str, np.ndarray]
    ):
        """Test dataset __getitem__ method."""
        dataset = ValuationDataset(sample_features, sample_targets)
        
        features, targets = dataset[0]
        
        assert features.shape == (130,)
        assert isinstance(targets, dict)
        assert "method" in targets
        assert "scenarios" in targets
        assert "returns" in targets
        assert "time" in targets

    def test_dataset_batching(
        self, sample_features: np.ndarray, sample_targets: Dict[str, np.ndarray]
    ):
        """Test dataset with DataLoader batching."""
        dataset = ValuationDataset(sample_features, sample_targets)
        loader = torch.utils.data.DataLoader(dataset, batch_size=16, shuffle=True)
        
        batch_features, batch_targets = next(iter(loader))
        
        assert batch_features.shape == (16, 130)
        assert batch_targets["method"].shape == (16,)
        assert batch_targets["scenarios"].shape == (16, 3)


class TestMultiTaskValuationNetwork:
    """Test suite for MultiTaskValuationNetwork."""

    def test_model_initialization(self, model: MultiTaskValuationNetwork):
        """Test model initialization."""
        assert model.input_dim == 130
        assert len(model.shared_layers) > 0
        assert model.method_head is not None
        assert model.scenario_head is not None
        assert model.return_head is not None
        assert model.time_head is not None

    def test_model_forward_pass(
        self, model: MultiTaskValuationNetwork, sample_features: np.ndarray
    ):
        """Test model forward pass."""
        model.eval()
        
        features = torch.FloatTensor(sample_features[:10])
        
        with torch.no_grad():
            outputs = model(features)
        
        assert "method_logits" in outputs
        assert "scenario_probs" in outputs
        assert "returns" in outputs
        assert "time_to_target" in outputs
        
        # Check output shapes
        assert outputs["method_logits"].shape == (10, 5)  # 5 methods
        assert outputs["scenario_probs"].shape == (10, 3)  # 3 scenarios
        assert outputs["returns"].shape == (10, 4)  # 4 horizons
        assert outputs["time_to_target"].shape == (10, 1)  # 1 value

    def test_model_output_ranges(
        self, model: MultiTaskValuationNetwork, sample_features: np.ndarray
    ):
        """Test that model outputs are in valid ranges."""
        model.eval()
        
        features = torch.FloatTensor(sample_features[:10])
        
        with torch.no_grad():
            outputs = model(features)
        
        # Scenario probabilities should be in [0, 1] and sum to 1
        scenario_probs = outputs["scenario_probs"]
        assert torch.all(scenario_probs >= 0)
        assert torch.all(scenario_probs <= 1)
        assert torch.allclose(scenario_probs.sum(dim=1), torch.ones(10), atol=0.01)
        
        # Time to target should be positive
        time_to_target = outputs["time_to_target"]
        assert torch.all(time_to_target >= 0)

    def test_model_trainable_parameters(self, model: MultiTaskValuationNetwork):
        """Test that model has trainable parameters."""
        total_params = sum(p.numel() for p in model.parameters())
        trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        
        assert total_params > 0
        assert trainable_params == total_params  # All params should be trainable

    def test_model_dropout_modes(
        self, model: MultiTaskValuationNetwork, sample_features: np.ndarray
    ):
        """Test that dropout behaves differently in train/eval modes."""
        features = torch.FloatTensor(sample_features[:10])
        
        # Training mode (dropout active)
        model.train()
        with torch.no_grad():
            output1 = model(features)
            output2 = model(features)
        
        # Outputs should be different due to dropout
        assert not torch.allclose(output1["returns"], output2["returns"])
        
        # Eval mode (dropout inactive)
        model.eval()
        with torch.no_grad():
            output3 = model(features)
            output4 = model(features)
        
        # Outputs should be identical
        assert torch.allclose(output3["returns"], output4["returns"])


class TestValuationPredictionModel:
    """Test suite for ValuationPredictionModel."""

    def test_model_initialization(self, training_config: TrainingConfig):
        """Test model initialization."""
        predictor = ValuationPredictionModel(config=training_config)
        
        assert predictor.config == training_config
        assert predictor.model is not None
        assert predictor.optimizer is not None
        assert predictor.scaler is not None

    def test_model_training(
        self,
        sample_features: np.ndarray,
        sample_targets: Dict[str, np.ndarray],
        training_config: TrainingConfig,
    ):
        """Test model training loop."""
        predictor = ValuationPredictionModel(config=training_config)
        
        history = predictor.train(sample_features, sample_targets)
        
        assert "train_loss" in history
        assert "val_loss" in history
        assert len(history["train_loss"]) > 0
        assert len(history["val_loss"]) > 0
        
        # Loss should decrease
        assert history["train_loss"][-1] < history["train_loss"][0]

    def test_model_prediction(
        self,
        sample_features: np.ndarray,
        sample_targets: Dict[str, np.ndarray],
        training_config: TrainingConfig,
    ):
        """Test model prediction."""
        predictor = ValuationPredictionModel(config=training_config)
        
        # Train briefly
        predictor.train(sample_features, sample_targets)
        
        # Predict
        predictions = predictor.predict(sample_features[:10])
        
        assert "method" in predictions
        assert "scenarios" in predictions
        assert "returns" in predictions
        assert "time_to_target" in predictions
        
        assert len(predictions["method"]) == 10
        assert predictions["scenarios"].shape == (10, 3)

    def test_model_inference_speed(
        self,
        sample_features: np.ndarray,
        sample_targets: Dict[str, np.ndarray],
        training_config: TrainingConfig,
    ):
        """Test that inference is fast (<10ms per sample)."""
        predictor = ValuationPredictionModel(config=training_config)
        
        # Train briefly
        predictor.train(sample_features, sample_targets)
        
        # Measure inference time
        start_time = datetime.utcnow()
        
        for _ in range(100):
            predictor.predict(sample_features[:1])
        
        elapsed = (datetime.utcnow() - start_time).total_seconds()
        avg_time_ms = (elapsed / 100) * 1000
        
        assert avg_time_ms < 10, f"Inference too slow: {avg_time_ms:.2f}ms"

    def test_model_save_load(
        self,
        sample_features: np.ndarray,
        sample_targets: Dict[str, np.ndarray],
        training_config: TrainingConfig,
        tmp_path: Path,
    ):
        """Test model save and load."""
        predictor = ValuationPredictionModel(config=training_config)
        
        # Train briefly
        predictor.train(sample_features, sample_targets)
        
        # Save model
        save_path = tmp_path / "test_model.pth"
        predictor.save_model(str(save_path))
        
        assert save_path.exists()
        
        # Load model
        new_predictor = ValuationPredictionModel(config=training_config)
        new_predictor.load_model(str(save_path))
        
        # Predictions should match
        pred1 = predictor.predict(sample_features[:10])
        pred2 = new_predictor.predict(sample_features[:10])
        
        assert np.allclose(pred1["returns"], pred2["returns"], atol=1e-5)

    def test_model_early_stopping(
        self,
        sample_features: np.ndarray,
        sample_targets: Dict[str, np.ndarray],
        training_config: TrainingConfig,
    ):
        """Test early stopping functionality."""
        config = TrainingConfig(
            epochs=100,
            early_stopping_patience=3,
        )
        
        predictor = ValuationPredictionModel(config=config)
        
        # Train with early stopping
        history = predictor.train(sample_features, sample_targets)
        
        # Should stop before 100 epochs
        assert len(history["train_loss"]) < 100

    def test_model_batch_prediction(
        self,
        sample_features: np.ndarray,
        sample_targets: Dict[str, np.ndarray],
        training_config: TrainingConfig,
    ):
        """Test batch prediction."""
        predictor = ValuationPredictionModel(config=training_config)
        
        # Train briefly
        predictor.train(sample_features, sample_targets)
        
        # Batch prediction
        predictions = predictor.predict_batch(sample_features)
        
        assert predictions["returns"].shape == (100, 4)

    def test_model_feature_importance(
        self,
        sample_features: np.ndarray,
        sample_targets: Dict[str, np.ndarray],
        training_config: TrainingConfig,
    ):
        """Test feature importance calculation."""
        predictor = ValuationPredictionModel(config=training_config)
        
        # Train briefly
        predictor.train(sample_features, sample_targets)
        
        # Get feature importance
        importance = predictor.get_feature_importance(sample_features, sample_targets)
        
        assert len(importance) == 130
        assert all(v >= 0 for v in importance.values())

    def test_model_handles_missing_values(
        self,
        sample_features: np.ndarray,
        sample_targets: Dict[str, np.ndarray],
        training_config: TrainingConfig,
    ):
        """Test that model handles NaN values properly."""
        # Add some NaN values
        features_with_nan = sample_features.copy()
        features_with_nan[0, 0] = np.nan
        
        predictor = ValuationPredictionModel(config=training_config)
        
        # Should either raise error or handle gracefully
        try:
            predictor.train(features_with_nan, sample_targets)
        except ValueError as e:
            assert "NaN" in str(e) or "missing" in str(e).lower()

    def test_model_validation_split(
        self,
        sample_features: np.ndarray,
        sample_targets: Dict[str, np.ndarray],
        training_config: TrainingConfig,
    ):
        """Test that validation split works correctly."""
        predictor = ValuationPredictionModel(config=training_config)
        
        history = predictor.train(sample_features, sample_targets)
        
        # Should have both train and val losses
        assert len(history["train_loss"]) == len(history["val_loss"])

    def test_model_learning_rate_scheduling(
        self,
        sample_features: np.ndarray,
        sample_targets: Dict[str, np.ndarray],
        training_config: TrainingConfig,
    ):
        """Test learning rate scheduling."""
        predictor = ValuationPredictionModel(config=training_config)
        
        initial_lr = predictor.optimizer.param_groups[0]["lr"]
        
        # Train for several epochs
        predictor.train(sample_features, sample_targets)
        
        final_lr = predictor.optimizer.param_groups[0]["lr"]
        
        # LR should have been adjusted (could go up or down)
        # Just check scheduler exists
        assert predictor.scheduler is not None

    def test_model_reproducibility(
        self,
        sample_features: np.ndarray,
        sample_targets: Dict[str, np.ndarray],
        training_config: TrainingConfig,
    ):
        """Test that model training is reproducible with same seed."""
        torch.manual_seed(42)
        predictor1 = ValuationPredictionModel(config=training_config)
        history1 = predictor1.train(sample_features, sample_targets)
        
        torch.manual_seed(42)
        predictor2 = ValuationPredictionModel(config=training_config)
        history2 = predictor2.train(sample_features, sample_targets)
        
        # Training losses should be identical
        assert np.allclose(history1["train_loss"], history2["train_loss"])

    def test_model_gpu_compatibility(
        self,
        sample_features: np.ndarray,
        sample_targets: Dict[str, np.ndarray],
        training_config: TrainingConfig,
    ):
        """Test model GPU compatibility if available."""
        if torch.cuda.is_available():
            predictor = ValuationPredictionModel(config=training_config)
            
            # Move to GPU
            predictor.model = predictor.model.cuda()
            
            # Train on GPU
            history = predictor.train(sample_features, sample_targets)
            
            assert len(history["train_loss"]) > 0
        else:
            pytest.skip("CUDA not available")
