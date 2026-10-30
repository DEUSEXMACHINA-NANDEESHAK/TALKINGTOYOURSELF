"""
EchoAgent — Custom Exception Hierarchy
Structured exceptions for clean error handling across the stack.
"""


class EchoAgentError(Exception):
    """Base exception for all EchoAgent errors."""

    def __init__(self, message: str, code: str = "INTERNAL_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)


# ── API Errors ───────────────────────────────────
class SessionNotFoundError(EchoAgentError):
    """Raised when a session ID does not exist."""

    def __init__(self, session_id: str):
        super().__init__(f"Session not found: {session_id}", code="SESSION_NOT_FOUND")


class UserNotFoundError(EchoAgentError):
    """Raised when a user ID does not exist."""

    def __init__(self, user_id: str):
        super().__init__(f"User not found: {user_id}", code="USER_NOT_FOUND")


class RateLimitExceededError(EchoAgentError):
    """Raised when client exceeds rate limits."""

    def __init__(self, limit: int, window: str):
        super().__init__(
            f"Rate limit exceeded: {limit} requests per {window}",
            code="RATE_LIMIT_EXCEEDED",
        )


class SessionExpiredError(EchoAgentError):
    """Raised when a session has timed out."""

    def __init__(self, session_id: str):
        super().__init__(f"Session expired: {session_id}", code="SESSION_EXPIRED")


# ── Audio Errors ─────────────────────────────────
class AudioChunkTooLargeError(EchoAgentError):
    """Raised when an audio chunk exceeds max size."""

    def __init__(self, size: int, max_size: int):
        super().__init__(
            f"Audio chunk too large: {size} bytes (max: {max_size})",
            code="CHUNK_TOO_LARGE",
        )


class AudioProcessingError(EchoAgentError):
    """Raised when audio preprocessing fails."""

    def __init__(self, detail: str):
        super().__init__(f"Audio processing failed: {detail}", code="AUDIO_PROCESSING_ERROR")


# ── ML Errors ────────────────────────────────────
class ModelTrainingError(EchoAgentError):
    """Raised when model training fails."""

    def __init__(self, detail: str):
        super().__init__(f"Model training failed: {detail}", code="MODEL_TRAINING_ERROR")


class ModelNotReadyError(EchoAgentError):
    """Raised when attempting to use a model that isn't trained yet."""

    def __init__(self, user_id: str):
        super().__init__(
            f"Voice model not ready for user: {user_id}",
            code="MODEL_NOT_READY",
        )


class ModelValidationError(EchoAgentError):
    """Raised when a trained model fails validation gates."""

    def __init__(self, model_uri: str, failures: list[str]):
        detail = ", ".join(failures)
        super().__init__(
            f"Model validation failed for {model_uri}: {detail}",
            code="MODEL_VALIDATION_ERROR",
        )


# ── Queue/Worker Errors ──────────────────────────
class QueueConnectionError(EchoAgentError):
    """Raised when RabbitMQ connection fails."""

    def __init__(self, detail: str):
        super().__init__(f"Queue connection error: {detail}", code="QUEUE_CONNECTION_ERROR")


class TaskTimeoutError(EchoAgentError):
    """Raised when a Celery task exceeds its time limit."""

    def __init__(self, task_id: str, timeout: int):
        super().__init__(
            f"Task {task_id} exceeded timeout of {timeout}s",
            code="TASK_TIMEOUT",
        )

