"""
EchoAgent — Audio Preprocessor
Peak volume normalization, noise filtering, and energy-based silence trimming (VAD).
"""

from pathlib import Path
import numpy as np
import soundfile as sf
import structlog

from src.core.constants import DEFAULT_SAMPLE_RATE
from src.core.exceptions import AudioProcessingError

logger = structlog.get_logger(__name__)


def load_audio(audio_path: str | Path, target_sr: int = DEFAULT_SAMPLE_RATE) -> tuple[np.ndarray, int]:
    """Load an audio file as a mono float32 numpy array normalized to [-1.0, 1.0]."""
    try:
        data, sr = sf.read(str(audio_path), dtype="float32")
        # Convert stereo to mono if needed
        if data.ndim > 1:
            data = np.mean(data, axis=1)

        # Simple resample check if needed
        if sr != target_sr:
            # Linear interpolation resampling for lightweight execution
            num_target_samples = int(len(data) * target_sr / sr)
            data = np.interp(
                np.linspace(0, len(data), num_target_samples, endpoint=False),
                np.arange(len(data)),
                data,
            ).astype(np.float32)
            sr = target_sr

        return data, sr
    except Exception as exc:
        raise AudioProcessingError(f"Failed to read audio file {audio_path}: {exc}") from exc


def peak_normalize(signal: np.ndarray, target_peak: float = 0.95) -> np.ndarray:
    """Normalize audio amplitude to prevent clipping and ensure consistent levels."""
    max_val = np.max(np.abs(signal))
    if max_val > 0:
        return (signal / max_val) * target_peak
    return signal


def trim_silence(
    signal: np.ndarray,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    frame_length_ms: int = 30,
    energy_threshold_db: float = -40.0,
) -> np.ndarray:
    """Energy-based Voice Activity Detection (VAD) to trim leading and trailing silence."""
    frame_size = int(sample_rate * (frame_length_ms / 1000.0))
    if len(signal) < frame_size:
        return signal

    # Calculate frame energies
    num_frames = len(signal) // frame_size
    frames = signal[: num_frames * frame_size].reshape(num_frames, frame_size)
    energies = np.sum(frames ** 2, axis=1) / frame_size
    # Avoid log(0)
    energies = np.maximum(energies, 1e-10)
    db_energies = 10 * np.log10(energies)

    # Find active voice frames above threshold
    active_indices = np.where(db_energies > energy_threshold_db)[0]
    if len(active_indices) == 0:
        return signal  # Return whole signal if no clear voice activity detected

    start_idx = max(0, active_indices[0] * frame_size)
    end_idx = min(len(signal), (active_indices[-1] + 1) * frame_size)

    return signal[start_idx:end_idx]


def clean_and_normalize_audio(
    input_path: str | Path,
    output_path: str | Path | None = None,
    target_sr: int = DEFAULT_SAMPLE_RATE,
) -> tuple[Path, float]:
    """Execute complete cleaning pipeline: load -> trim silence -> normalize -> save.

    Returns:
        Tuple of (saved_file_path: Path, cleaned_duration_seconds: float)
    """
    in_file = Path(input_path)
    if not in_file.exists():
        raise AudioProcessingError(f"Audio file does not exist: {input_path}")

    signal, sr = load_audio(in_file, target_sr=target_sr)
    trimmed = trim_silence(signal, sample_rate=sr)
    normalized = peak_normalize(trimmed)

    out_file = Path(output_path) if output_path else in_file.with_name(f"{in_file.stem}_cleaned.wav")
    sf.write(str(out_file), normalized, sr, subtype="PCM_16")

    duration_s = len(normalized) / sr
    logger.info(
        "audio_cleaning_complete",
        input=str(in_file),
        output=str(out_file),
        duration_s=round(duration_s, 2),
    )
    return out_file, duration_s

