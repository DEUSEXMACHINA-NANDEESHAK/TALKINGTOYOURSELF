"""
EchoAgent — Abstract Interfaces (Strategy Pattern)
Base classes for pluggable ML components. The API layer never imports a
concrete model directly — it depends on these abstractions.

To swap a TTS engine or voice processor, implement the interface and
change the binding in config. Zero code changes in the API layer.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import numpy as np


class BaseVoiceProcessor(ABC):
    """Interface for audio preprocessing pipelines."""

    @abstractmethod
    def clean_audio(self, audio_path: Path) -> Path:
        """Remove noise, trim silence, normalize volume.

        Args:
            audio_path: Path to raw audio file.

        Returns:
            Path to cleaned audio file.
        """
        ...

    @abstractmethod
    def extract_features(self, audio_path: Path) -> dict[str, Any]:
        """Extract mel-spectrogram, MFCCs, F0, and other features.

        Args:
            audio_path: Path to cleaned audio file.

        Returns:
            Dictionary of feature tensors/arrays.
        """
        ...

    @abstractmethod
    def generate_embedding(self, audio_path: Path) -> np.ndarray:
        """Generate a speaker embedding vector (d-vector).

        Args:
            audio_path: Path to cleaned audio file.

        Returns:
            Numpy array of shape (embedding_dim,), typically (256,).
        """
        ...


class BaseTTSEngine(ABC):
    """Interface for Text-to-Speech engines."""

    @abstractmethod
    def synthesize(self, text: str, speaker_embedding: np.ndarray | None = None) -> bytes:
        """Convert text to speech audio bytes.

        Args:
            text: Text to synthesize.
            speaker_embedding: Optional speaker embedding for voice cloning.

        Returns:
            Raw audio bytes (PCM 16-bit, target sample rate).
        """
        ...

    @abstractmethod
    def load_voice_model(self, model_uri: str) -> None:
        """Load a trained voice model from MLflow registry.

        Args:
            model_uri: MLflow model URI (e.g., 'models:/voice-clone-abc/Production').
        """
        ...


class BaseASREngine(ABC):
    """Interface for Automatic Speech Recognition engines."""

    @abstractmethod
    def transcribe(self, audio_bytes: bytes) -> str:
        """Transcribe audio bytes to text.

        Args:
            audio_bytes: Raw audio bytes.

        Returns:
            Transcribed text string.
        """
        ...


class BaseModelTrainer(ABC):
    """Interface for ML model training pipelines."""

    @abstractmethod
    def train(
        self,
        features: dict[str, Any],
        embedding: np.ndarray,
        experiment_name: str,
    ) -> str:
        """Train a voice model and register it.

        Args:
            features: Dictionary of extracted audio features.
            embedding: Speaker embedding vector.
            experiment_name: MLflow experiment name.

        Returns:
            MLflow model URI of the registered model.
        """
        ...

    @abstractmethod
    def validate(self, model_uri: str) -> dict[str, float]:
        """Run validation checks on a trained model.

        Args:
            model_uri: MLflow model URI to validate.

        Returns:
            Dictionary of validation metrics.
        """
        ...

