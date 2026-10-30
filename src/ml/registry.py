"""
EchoAgent — MLflow Model Registry & Validation Gates
Handles experiment tracking, artifact persistence, validation quality gates, and model registration.
"""

import os
from pathlib import Path
from typing import Any
import mlflow
from mlflow.tracking import MlflowClient
import structlog

from src.core.config import get_settings
from src.core.constants import MLFLOW_PITCH_PREDICTOR_EXPERIMENT
from src.core.exceptions import ModelValidationError

logger = structlog.get_logger(__name__)


class ModelRegistryService:
    """Manages MLflow experiment runs, validation checks, and registry promotions."""

    def __init__(self, tracking_uri: str | None = None):
        settings = get_settings()
        self.tracking_uri = tracking_uri or os.getenv("MLFLOW_TRACKING_URI") or settings.mlflow_tracking_uri
        mlflow.set_tracking_uri(self.tracking_uri)
        self.client = MlflowClient(tracking_uri=self.tracking_uri)

    def log_and_register_run(
        self,
        experiment_name: str,
        run_name: str,
        params: dict[str, Any],
        metrics: dict[str, float],
        artifacts: list[Path | str],
        model_name: str | None = None,
        tags: dict[str, str] | None = None,
    ) -> str:
        """Execute a full MLflow experiment run and register artifact."""
        mlflow.set_experiment(experiment_name)

        with mlflow.start_run(run_name=run_name) as run:
            run_id = run.info.run_id

            # 1. Log Parameters
            mlflow.log_params(params)

            # 2. Log Metrics
            mlflow.log_metrics(metrics)

            # 3. Log Artifacts
            for artifact in artifacts:
                art_path = Path(artifact)
                if art_path.is_file():
                    mlflow.log_artifact(str(art_path))
                elif art_path.is_dir():
                    mlflow.log_artifacts(str(art_path))

            # 4. Set Tags
            if tags:
                mlflow.set_tags(tags)

            logger.info("mlflow_run_logged", run_id=run_id, experiment=experiment_name)

            model_uri = f"runs:/{run_id}/model"

            # 5. Register in MLflow Registry if requested
            if model_name:
                try:
                    registered_model = mlflow.register_model(
                        model_uri=model_uri,
                        name=model_name,
                    )
                    logger.info("model_registered", model_name=model_name, version=registered_model.version)
                    return f"models:/{model_name}/{registered_model.version}"
                except Exception as reg_exc:
                    logger.warning("model_registration_skipped", reason=str(reg_exc))

            return f"runs:/{run_id}"

    def validate_pitch_predictor(self, model, test_features: Any) -> dict[str, bool]:
        """Automated quality gate checks for pitch predictor models."""
        failures = []

        # Gate 1: Check model is marked trained
        if not getattr(model, "is_trained", False):
            failures.append("Model is not flagged as trained")

        # Gate 2: Check prediction execution without crashing
        try:
            preds = model.predict(test_features)
            if len(preds) != len(test_features):
                failures.append(f"Output shape mismatch: expected {len(test_features)}, got {len(preds)}")
        except Exception as exc:
            failures.append(f"Inference threw error: {exc}")

        if failures:
            raise ModelValidationError("pitch_predictor", failures)

        return {"load_valid": True, "inference_valid": True}
