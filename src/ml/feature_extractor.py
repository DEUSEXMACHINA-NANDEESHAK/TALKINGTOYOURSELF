"""
EchoAgent — Audio Feature Extractor
Extracts Mel-Spectrogram, MFCCs, and F0 pitch contours for voice modeling.
"""

from pathlib import Path
from typing import Any
import numpy as np
from scipy.fftpack import dct
import soundfile as sf
import structlog

from src.core.constants import (
    DEFAULT_SAMPLE_RATE,
    MEL_HOP_LENGTH,
    MEL_N_FFT,
    MEL_N_MELS,
    MFCC_N_MFCC,
)
from src.core.exceptions import AudioProcessingError
from src.ml.audio_preprocessor import load_audio

logger = structlog.get_logger(__name__)


def compute_mel_filterbanks(
    n_mels: int = MEL_N_MELS,
    n_fft: int = MEL_N_FFT,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
) -> np.ndarray:
    """Compute triangular mel filterbank matrix."""
    low_freq_mel = 0
    high_freq_mel = 2595 * np.log10(1 + (sample_rate / 2) / 700)
    mel_points = np.linspace(low_freq_mel, high_freq_mel, n_mels + 2)
    hz_points = 700 * (10 ** (mel_points / 2595) - 1)
    bin_points = np.floor((n_fft + 1) * hz_points / sample_rate).astype(int)

    fbank = np.zeros((n_mels, int(np.floor(n_fft / 2 + 1))))
    for m in range(1, n_mels + 1):
        f_m_minus = bin_points[m - 1]
        f_m = bin_points[m]
        f_m_plus = bin_points[m + 1]

        for k in range(f_m_minus, f_m):
            if f_m != f_m_minus:
                fbank[m - 1, k] = (k - bin_points[m - 1]) / (f_m - f_m_minus)
        for k in range(f_m, f_m_plus):
            if f_m_plus != f_m:
                fbank[m - 1, k] = (bin_points[m + 1] - k) / (f_m_plus - f_m)

    return fbank


def extract_mel_spectrogram(
    signal: np.ndarray,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    n_mels: int = MEL_N_MELS,
    n_fft: int = MEL_N_FFT,
    hop_length: int = MEL_HOP_LENGTH,
) -> np.ndarray:
    """Compute log Mel-Spectrogram [n_mels, time_frames]."""
    if len(signal) < n_fft:
        signal = np.pad(signal, (0, n_fft - len(signal)), mode="constant")

    # Framing with Hanning window
    num_frames = 1 + int((len(signal) - n_fft) / hop_length)
    frames = np.lib.stride_tricks.sliding_window_view(signal, n_fft)[::hop_length]
    windowed = frames * np.hanning(n_fft)

    # Magnitude FFT
    mag_fft = np.absolute(np.fft.rfft(windowed, n_fft))
    pow_frames = (1.0 / n_fft) * (mag_fft ** 2)

    # Filterbank dot product
    fbank = compute_mel_filterbanks(n_mels, n_fft, sample_rate)
    mel_spec = np.dot(pow_frames, fbank.T)
    mel_spec = np.where(mel_spec == 0, np.finfo(float).eps, mel_spec)
    log_mel_spec = 20 * np.log10(mel_spec)  # dB scale

    return log_mel_spec.T  # Shape: (n_mels, num_frames)


def extract_mfcc(
    mel_spectrogram: np.ndarray,
    num_ceps: int = MFCC_N_MFCC,
) -> np.ndarray:
    """Compute MFCC coefficients using Discrete Cosine Transform on log Mel-Spec."""
    # mel_spectrogram: shape (n_mels, time_frames)
    mfcc = dct(mel_spectrogram.T, type=2, axis=1, norm="ortho")[:, :num_ceps]
    return mfcc  # Shape: (time_frames, num_ceps)


def estimate_f0(
    signal: np.ndarray,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    hop_length: int = MEL_HOP_LENGTH,
    frame_size: int = MEL_N_FFT,
) -> np.ndarray:
    """Autocorrelation-based pitch (F0) tracking."""
    if len(signal) < frame_size:
        return np.array([0.0])

    num_frames = 1 + int((len(signal) - frame_size) / hop_length)
    f0 = np.zeros(num_frames)

    min_period = int(sample_rate / 400)  # max pitch: 400 Hz
    max_period = int(sample_rate / 60)   # min pitch: 60 Hz

    for i in range(num_frames):
        start = i * hop_length
        frame = signal[start : start + frame_size] * np.hanning(frame_size)
        corr = np.correlate(frame, frame, mode="full")[frame_size - 1 :]

        if len(corr) > max_period:
            search_window = corr[min_period:max_period]
            peak_idx = np.argmax(search_window) + min_period
            if corr[0] > 0 and (corr[peak_idx] / corr[0]) > 0.3:  # Periodic threshold
                f0[i] = sample_rate / peak_idx
            else:
                f0[i] = 0.0  # Unvoiced

    return f0


def extract_all_features(audio_path: str | Path) -> dict[str, Any]:
    """Complete extraction pipeline for training and voice modeling."""
    signal, sr = load_audio(audio_path)
    mel_spec = extract_mel_spectrogram(signal, sample_rate=sr)
    mfccs = extract_mfcc(mel_spec)
    f0 = estimate_f0(signal, sample_rate=sr)

    # Align frame count between MFCCs and F0
    min_len = min(len(mfccs), len(f0))
    mfccs_aligned = mfccs[:min_len]
    f0_aligned = f0[:min_len]

    return {
        "mel_spectrogram": mel_spec,
        "mfccs": mfccs_aligned,
        "f0": f0_aligned,
        "sample_rate": sr,
        "duration_seconds": len(signal) / sr,
        "frame_count": min_len,
    }

