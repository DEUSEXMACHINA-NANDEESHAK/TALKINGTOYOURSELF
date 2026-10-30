"""
EchoAgent — Constants
All magic numbers and fixed values live here. Never hardcode them in logic.
"""

# ── Audio ────────────────────────────────────────
DEFAULT_SAMPLE_RATE: int = 16000
DEFAULT_CHANNELS: int = 1  # Mono
DEFAULT_BIT_DEPTH: int = 16  # PCM 16-bit
CHUNK_DURATION_SECONDS: float = 2.0
MAX_SESSION_DURATION_SECONDS: int = 120
MAX_CHUNK_SIZE_BYTES: int = 131072  # 128KB
AUDIO_FORMAT: str = "wav"

# ── ML Features ──────────────────────────────────
MEL_N_MELS: int = 80
MEL_HOP_LENGTH: int = 256
MEL_N_FFT: int = 1024
MFCC_N_MFCC: int = 13
SPEAKER_EMBEDDING_DIM: int = 256

# ── Model Training ───────────────────────────────
DEFAULT_LEARNING_RATE: float = 0.001
DEFAULT_EPOCHS: int = 50
DEFAULT_BATCH_SIZE: int = 8
MODEL_QUALITY_THRESHOLD: float = 2.0  # Max mel-spectrogram distance
EMBEDDING_SIMILARITY_THRESHOLD: float = 0.7  # Min cosine similarity
INFERENCE_LATENCY_THRESHOLD_MS: int = 500

# ── Session & Rate Limiting ──────────────────────
SESSION_TTL_SECONDS: int = 7200  # 2 hours
JOB_STATUS_TTL_SECONDS: int = 3600  # 1 hour
MODEL_READY_TTL_SECONDS: int = 86400  # 24 hours
RATE_LIMIT_WINDOW_SECONDS: int = 60
RATE_LIMIT_MAX_REQUESTS: int = 100
MAX_SESSIONS_PER_IP_PER_HOUR: int = 3
MAX_WEBSOCKETS_PER_IP: int = 5

# ── Queue ────────────────────────────────────────
VOICE_PROCESS_QUEUE: str = "voice_process_queue"
VOICE_CLONE_QUEUE: str = "voice_clone_queue"
NOTIFICATION_QUEUE: str = "notification_queue"
DEAD_LETTER_QUEUE: str = "dead_letter_queue"
MAX_RETRIES: int = 3
RETRY_DELAYS: list[int] = [30, 120, 480]  # Exponential backoff (seconds)
MESSAGE_TTL_MS: int = 3_600_000  # 1 hour
QUEUE_MAX_LENGTH: int = 10_000

# ── Redis Key Prefixes ───────────────────────────
REDIS_SESSION_PREFIX: str = "session:"
REDIS_JOB_PREFIX: str = "job:"
REDIS_USER_PREFIX: str = "user:"
REDIS_RATELIMIT_PREFIX: str = "ratelimit:"
REDIS_AUDIO_CHUNKS_PREFIX: str = "audio_chunks:"
REDIS_PROGRESS_CHANNEL_PREFIX: str = "progress:"

# ── Processing Steps ─────────────────────────────
PROCESSING_STEPS: list[dict[str, str]] = [
    {"step": "1", "label": "Cleaning audio & trimming silence"},
    {"step": "2", "label": "Extracting mel-spectrogram & features"},
    {"step": "3", "label": "Generating speaker embedding"},
    {"step": "4", "label": "Training voice model"},
    {"step": "5", "label": "Validating & registering model"},
]
TOTAL_PROCESSING_STEPS: int = len(PROCESSING_STEPS)

# ── MLflow ───────────────────────────────────────
MLFLOW_VOICE_CLONE_EXPERIMENT: str = "echoagent-voice-cloning"
MLFLOW_PITCH_PREDICTOR_EXPERIMENT: str = "echoagent-pitch-predictor"
MLFLOW_EMBEDDING_EXPERIMENT: str = "echoagent-embedding-quality"

# ── WebSocket Message Types ──────────────────────
WS_TYPE_AUDIO: str = "audio"
WS_TYPE_TRANSCRIPT: str = "transcript"
WS_TYPE_TIMER: str = "timer"
WS_TYPE_SESSION_END: str = "session_end"
WS_TYPE_ERROR: str = "error"
WS_TYPE_SLOW_DOWN: str = "slow_down"

