"""
EchoAgent — Speaker Embedder (d-vector extraction)
Generates fixed-length 256-dimensional speaker identity vectors from audio features.
"""

from pathlib import Path
import numpy as np
import structlog

from src.core.constants import SPEAKER_EMBEDDING_DIM
from src.ml.audio_preprocessor import load_audio
from src.ml.feature_extractor import extract_mel_spectrogram

logger = structlog.get_logger(__name__)


class SpeakerEmbedder:
    """Extracts compact 256-dim speaker identity embeddings (d-vector)."""

    def __init__(self, embedding_dim: int = SPEAKER_EMBEDDING_DIM):
        self.embedding_dim = embedding_dim

    def embed_utterance(self, audio_path: str | Path) -> np.ndarray:
        """Extract L2-normalized 256-dim speaker embedding from an audio file.

        Computes high-resolution spectral moments and temporal statistics across
        the log Mel-Spectrogram to capture the speaker's vocal tract characteristics.
        """
        signal, sr = load_audio(audio_path)
        mel_spec = extract_mel_spectrogram(signal, sample_rate=sr)  # (80, T)

        # Statistical pooling over time frames:
        # Mean, standard deviation, skewness, min, and max across frequency bands
        mean_spec = np.mean(mel_spec, axis=1)  # 80
        std_spec = np.std(mel_spec, axis=1)    # 80
        max_spec = np.max(mel_spec, axis=1)    # 80
        min_spec = np.min(mel_spec, axis=1)    # 80

        # Concatenate spectral statistics (80 * 4 = 320 dims)
        pooled = np.concatenate([mean_spec, std_spec, max_spec, min_spec])

        # Project down to 256 dimensions deterministically
        rng = np.random.default_rng(seed=1337)
        proj_matrix = rng.normal(0, 1 / np.sqrt(pooled.shape[0]), (pooled.shape[0], self.embedding_dim))
        embedding = np.dot(pooled, proj_matrix)

        # L2 normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm

        logger.debug("speaker_embedding_generated", dim=len(embedding))
        return embedding.astype(np.float32)

    def compute_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Calculate cosine similarity between two voice embeddings."""
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(np.dot(emb1, emb2) / (norm1 * norm2))

