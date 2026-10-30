"""
EchoAgent — Audio Preprocessing and Feature Extraction Tests
"""

from pathlib import Path
import numpy as np
import soundfile as sf
import pytest

from src.core.constants import DEFAULT_SAMPLE_RATE, MEL_N_MELS, MFCC_N_MFCC
from src.ml.audio_preprocessor import clean_and_normalize_audio, peak_normalize, trim_silence
from src.ml.feature_extractor import (
    estimate_f0,
    extract_all_features,
    extract_mel_spectrogram,
    extract_mfcc,
)


@pytest.fixture
def sample_wav_path(tmp_path):
    """Generate a clean 2-second sine wave audio file for tests."""
    sr = DEFAULT_SAMPLE_RATE
    duration = 2.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    # 220Hz tone (A3) with silence prefix/suffix
    tone = 0.5 * np.sin(2 * np.pi * 220 * t)
    silence = np.zeros(int(sr * 0.5))
    signal = np.concatenate([silence, tone, silence]).astype(np.float32)

    wav_file = tmp_path / "test_tone.wav"
    sf.write(str(wav_file), signal, sr, subtype="PCM_16")
    return wav_file


def test_audio_preprocessing_pipeline(sample_wav_path):
    """Audio preprocessor normalizes peak volume and trims silence."""
    cleaned_path, duration = clean_and_normalize_audio(sample_wav_path)

    assert cleaned_path.exists()
    assert duration > 0.0

    # Load cleaned signal and verify properties
    data, sr = sf.read(str(cleaned_path))
    assert sr == DEFAULT_SAMPLE_RATE
    # Peak amplitude should be normalized near 0.95
    assert np.isclose(np.max(np.abs(data)), 0.95, atol=0.05)


def test_feature_extraction_shapes(sample_wav_path):
    """Feature extraction extracts correct tensor shapes for Mel-Spec, MFCC, and F0."""
    features = extract_all_features(sample_wav_path)

    mel_spec = features["mel_spectrogram"]
    mfccs = features["mfccs"]
    f0 = features["f0"]

    # Mel-Spectrogram must have MEL_N_MELS (80) frequency bins
    assert mel_spec.shape[0] == MEL_N_MELS
    # MFCCs must have MFCC_N_MFCC (13) coefficients
    assert mfccs.shape[1] == MFCC_N_MFCC
    # MFCCs and F0 should share identical frame counts
    assert len(mfccs) == len(f0)
    assert features["sample_rate"] == DEFAULT_SAMPLE_RATE
    assert features["duration_seconds"] > 0

