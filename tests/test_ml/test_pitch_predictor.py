"""
EchoAgent — Pitch Predictor & MLflow Registry Tests
"""

from pathlib import Path
import numpy as np
import pytest

from src.ml.pitch_predictor import PitchPredictorModel
from src.ml.registry import ModelRegistryService


@pytest.fixture
def synthetic_data():
    """Generate synthetic MFCCs (X) and F0 targets (y)."""
    np.random.seed(42)
    num_frames = 200
    num_mfcc = 13
    X = np.random.randn(num_frames, num_mfcc)
    # Linear relationship with noise
    weights = np.linspace(10, 50, num_mfcc)
    y = np.dot(X, weights) + 120.0 + np.random.randn(num_frames) * 2.0
    return X, y


def test_pitch_predictor_training_and_serialization(synthetic_data, tmp_path):
    """Model fits regression, produces metrics, and deserializes cleanly."""
    X, y = synthetic_data
    model = PitchPredictorModel(alpha=1.0)

    metrics = model.train(X, y)
    assert "mse" in metrics
    assert "mae" in metrics
    assert "r2" in metrics
    assert metrics["r2"] > 0.8  # Strong linear fit on synthetic data

    # Predictions
    preds = model.predict(X[:10])
    assert len(preds) == 10

    # Save and Load
    saved_path = model.save(tmp_path / "pitch_model.joblib")
    assert saved_path.exists()

    loaded_model = PitchPredictorModel.load(saved_path)
    loaded_preds = loaded_model.predict(X[:10])
    assert np.allclose(preds, loaded_preds)


def test_mlflow_registry_and_validation(synthetic_data, tmp_path):
    """MLflow registry logs run, artifacts, and passes quality gates."""
    X, y = synthetic_data
    model = PitchPredictorModel()
    metrics = model.train(X, y)
    model_artifact = model.save(tmp_path / "model.joblib")

    # Local file-based MLflow tracking URI
    tracking_uri = f"sqlite:///{tmp_path}/mlflow_test.db"
    registry = ModelRegistryService(tracking_uri=tracking_uri)

    # Validate model through quality gates
    gate_results = registry.validate_pitch_predictor(model, test_features=X[:5])
    assert gate_results["load_valid"] is True
    assert gate_results["inference_valid"] is True

    # Log run
    run_uri = registry.log_and_register_run(
        experiment_name="test-pitch-predictor",
        run_name="unit-test-run-001",
        params={"alpha": 1.0, "algorithm": "Ridge"},
        metrics=metrics,
        artifacts=[model_artifact],
        tags={"env": "test"},
    )
    assert run_uri.startswith("runs:/")

