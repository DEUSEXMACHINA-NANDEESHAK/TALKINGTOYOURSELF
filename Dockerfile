# ── Stage 1: Base ──────────────────────────────────
FROM python:3.11-slim AS base

WORKDIR /app

# System dependencies for audio processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Stage 2: API Server ───────────────────────────
FROM base AS api

COPY src/ ./src/

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ── Stage 3: Celery Worker ────────────────────────
FROM base AS worker

COPY src/ ./src/

CMD ["celery", "-A", "src.workers.celery_app", "worker", "-l", "info", "-c", "1"]

