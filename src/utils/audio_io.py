"""
EchoAgent — Audio I/O Utilities
Streaming chunk storage, concatenation into standardized WAV format, and metadata writing.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import struct
import wave
import structlog

from src.core.constants import (
    DEFAULT_BIT_DEPTH,
    DEFAULT_CHANNELS,
    DEFAULT_SAMPLE_RATE,
)
from src.core.exceptions import AudioProcessingError

logger = structlog.get_logger(__name__)


def get_session_audio_dir(base_path: str | Path, session_id: str) -> Path:
    """Ensure and return the session audio directory."""
    path = Path(base_path) / str(session_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_audio_chunk(
    session_dir: Path,
    sequence: int,
    raw_bytes: bytes,
) -> Path:
    """Save an individual incoming audio chunk to disk.

    Args:
        session_dir: Directory for this session
        sequence: Sequence index (0-based or 1-based)
        raw_bytes: Binary payload (PCM 16-bit or WAV bytes)

    Returns:
        Path to the saved chunk file
    """
    chunk_filename = f"chunk_{sequence:04d}.raw"
    chunk_path = session_dir / chunk_filename
    with open(chunk_path, "wb") as f:
        f.write(raw_bytes)
    return chunk_path


def concatenate_chunks_to_wav(
    session_dir: Path,
    output_filename: str = "full_recording.wav",
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    channels: int = DEFAULT_CHANNELS,
    bit_depth: int = DEFAULT_BIT_DEPTH,
) -> tuple[Path, int, float]:
    """Concatenate all raw/pcm chunks in session_dir into a standardized WAV file.

    Args:
        session_dir: Directory holding chunk_*.raw files
        output_filename: Name of the output WAV file
        sample_rate: Target sample rate (default: 16000 Hz)
        channels: Number of channels (default: 1 mono)
        bit_depth: Sample bit depth (default: 16-bit)

    Returns:
        Tuple of (output_wav_path: Path, total_bytes: int, duration_seconds: float)
    """
    raw_files = sorted(session_dir.glob("chunk_*.raw"))
    if not raw_files:
        raise AudioProcessingError(f"No audio chunks found in {session_dir}")

    output_path = session_dir / output_filename
    sample_width = bit_depth // 8  # 16-bit = 2 bytes
    total_audio_bytes = 0

    try:
        with wave.open(str(output_path), "wb") as wav_out:
            wav_out.setnchannels(channels)
            wav_out.setsampwidth(sample_width)
            wav_out.setframerate(sample_rate)

            for chunk_file in raw_files:
                data = chunk_file.read_bytes()
                # Ensure data alignment with sample width
                aligned_len = len(data) - (len(data) % (channels * sample_width))
                if aligned_len > 0:
                    wav_out.writeframes(data[:aligned_len])
                    total_audio_bytes += aligned_len

        bytes_per_second = sample_rate * channels * sample_width
        duration_seconds = total_audio_bytes / bytes_per_second if bytes_per_second else 0.0

        # Write metadata.json alongside the WAV
        metadata = {
            "output_file": output_filename,
            "sample_rate": sample_rate,
            "channels": channels,
            "bit_depth": bit_depth,
            "chunk_count": len(raw_files),
            "total_bytes": total_audio_bytes,
            "duration_seconds": round(duration_seconds, 2),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        (session_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))

        logger.info(
            "audio_concatenation_complete",
            session_dir=str(session_dir),
            chunks=len(raw_files),
            duration_s=round(duration_seconds, 2),
        )

        return output_path, total_audio_bytes, duration_seconds

    except Exception as exc:
        logger.error("audio_concatenation_failed", session_dir=str(session_dir), error=str(exc))
        raise AudioProcessingError(f"Failed to concatenate audio: {exc}") from exc


def create_mock_wav_bytes(duration_seconds: float = 1.0, sample_rate: int = DEFAULT_SAMPLE_RATE) -> bytes:
    """Utility to generate valid silence/synthetic WAV bytes for tests."""
    import io
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(DEFAULT_CHANNELS)
        wav_file.setsampwidth(DEFAULT_BIT_DEPTH // 8)
        wav_file.setframerate(sample_rate)
        # 16-bit zero samples (silence)
        num_samples = int(sample_rate * duration_seconds)
        data = struct.pack(f"<{num_samples}h", *([0] * num_samples))
        wav_file.writeframes(data)
    return buffer.getvalue()

