"""
EchoAgent — Pitch Predictor (MLOps Linear Regression Model)
Lightweight ML model predicting fundamental frequency (F0) from MFCC coefficients.
Used to practice the complete MLOps experiment tracking, registry, and validation cycle.
"""

from pathlib import Path
from typing import Any
import joblib
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
import structlog

logger = structlog.get_logger(__name__)


class PitchPredictorModel:
    """Predicts acoustic pitch (F0) from spectral MFCC features."""

    def __init__(self, alpha: float = 1.0):
        self.alpha = alpha
        self.model = Ridge(alpha=alpha)
        self.is_trained = False

    def train(
        self,
        mfccs: np.ndarray,
        f0: np.ndarray,
        test_size: float = 0.2,
        random_state: int = 42,
    ) -> dict[str, float]:
        """Train regression model and calculate evaluation metrics.

        Args:
            mfccs: Feature matrix of shape (num_frames, num_mfcc)
            f0: Target pitch vector of shape (num_frames,)
            test_size: Ratio of validation set
            random_state: Reproducibility seed

        Returns:
            Dictionary of metrics: mse, mae, r2, train_samples, test_samples
        """
        # Ensure 2D input
        if mfccs.ndim == 1:
            mfccs = mfccs.reshape(-1, 1)

        X_train, X_test, y_train, y_test = train_test_split(
            mfccs, f0, test_size=test_size, random_state=random_state
        )

        self.model.fit(X_train, y_train)
        self.is_trained = True

        y_pred = self.model.predict(X_test)

        mse = float(mean_squared_error(y_test, y_pred))
        mae = float(mean_absolute_error(y_test, y_pred))
        r2 = float(r2_score(y_test, y_pred))

        metrics = {
            "mse": round(mse, 4),
            "mae": round(mae, 4),
            "r2": round(r2, 4),
            "train_samples": len(X_train),
            "test_samples": len(X_test),
        }

        logger.info("pitch_predictor_trained", metrics=metrics)
        return metrics

    def predict(self, mfccs: np.ndarray) -> np.ndarray:
        """Predict F0 pitch for incoming MFCC frames."""
        if not self.is_trained:
            raise RuntimeError("Model is not trained yet. Call train() first.")
        if mfccs.ndim == 1:
            mfccs = mfccs.reshape(1, -1)
        return self.model.predict(mfccs)

    def save(self, filepath: str | Path) -> Path:
        """Serialize model to disk."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.model, str(path))
        return path

    @classmethod
    def load(cls, filepath: str | Path) -> "PitchPredictorModel":
        """Deserialize model from disk."""
        instance = cls()
        instance.model = joblib.load(str(filepath))
        instance.is_trained = True
        return instance

