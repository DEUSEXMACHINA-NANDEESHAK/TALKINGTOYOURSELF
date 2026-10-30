# 🔊 EchoAgent — Talk To Myself
> **Production-Grade, MLOps-First Agentic Voice-Cloning Platform**

EchoAgent is a decoupled, cloud-ready voice conversation and cloning system built with **FastAPI**, **RabbitMQ**, **Celery**, **Redis**, **PostgreSQL**, **MLflow**, and **PyTorch/Scikit-learn**.

---

## 🌟 Architecture & Features

1. **Session 1 (Real-Time Voice Bot):** A bidirectional WebSocket stream captures the user's speech in real-time over 120 seconds while engaging in a voice conversation designed to elicit acoustic diversity.
2. **Audio Streaming & Concatenation:** High-frequency PCM audio chunks stream via WebSocket, save safely to disk, and automatically assemble into normalized 16kHz WAV recordings upon session termination.
3. **Resilient Message Broker & DLQ:** Asynchronous job dispatch with RabbitMQ exchanges, exponential backoff retries, and dead-letter queue (DLQ) routing.
4. **ML Feature Extraction & Model Registry:**
   - Preprocessing: Peak volume normalization and energy-based silence trimming (Voice Activity Detection).
   - Spectral Features: 80-bin Mel-Spectrograms, 13 MFCC coefficients, and autocorrelation pitch (F0) tracking.
   - 256-dimensional Speaker Embeddings (d-vectors).
   - Side-Model Training: Acoustic pitch regression model ($X=\text{MFCCs}, y=F_0$) logged with hyperparameters, evaluation metrics (MSE, MAE, $R^2$), and validation quality gates inside MLflow.
5. **Real-Time Notification System:** Live background processing progress updates streamed to the frontend via Redis Pub/Sub and Server-Sent Events (SSE).
6. **Session 2 ("Speak to Yourself"):** Interactive cloned voice conversation where the AI speaks back in the user's cloned voice.
7. **Observability & Health:** Prometheus `/metrics` telemetry scrape target, health (`/health`), and readiness (`/ready`) probes.

---

## 🚀 Quick Start (Local Development)

### 1. Prerequisites
- Python 3.11+
- `uv` (recommended) or `pip`
- Docker & Docker Compose (optional for full containerized stack)

### 2. Setup Virtual Environment
```bash
git clone https://github.com/your-username/echoagent-core.git
cd echoagent-core

# Using uv (fastest)
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt -r requirements-dev.txt
```

### 3. Run the Test Suite
```bash
pytest tests/ -v
```
*(All 23 unit and integration tests execute in ~5 seconds)*

---

## 🐳 Docker Stack Deployment

Launch the complete stack (API + Celery Worker + RabbitMQ + Redis + PostgreSQL + MLflow + Caddy):
```bash
docker compose up -d --build
```

- **API Gateway & Swagger UI:** `http://localhost:8000/docs`
- **Prometheus Metrics:** `http://localhost:8000/metrics`
- **MLflow Experiment Dashboard:** `http://localhost:5000`
- **RabbitMQ Management Console:** `http://localhost:15672` (User: `guest`, Pass: `guest`)
- **Frontend Client:** Open `frontend/index.html` in your browser.

---

## ☸️ Kubernetes Deployment

Declarative manifests for Kubernetes (K3s / Minikube / GKE / EKS) are located in `k8s/`:
```bash
kubectl apply -f k8s/namespace.yml
kubectl apply -f k8s/configmap.yml
kubectl apply -f k8s/redis-deployment.yml
kubectl apply -f k8s/rabbitmq-statefulset.yml
kubectl apply -f k8s/postgres-statefulset.yml
kubectl apply -f k8s/api-deployment.yml
kubectl apply -f k8s/worker-deployment.yml
kubectl apply -f k8s/ingress.yml
```

---

## 📂 Project Structure

```
echoagent-core/
├── .github/workflows/
│   └── ci-cd.yml             # GitHub Actions CI/CD (Lint, Pytest, ML Validation, Docker build)
├── frontend/
│   ├── index.html            # Dark-mode responsive UI
│   └── src/
│       ├── app.js            # Frontend state machine & controller
│       ├── audio.js          # Web Audio API mic capture, visualizer & player
│       └── config.js         # Endpoints configuration
├── k8s/                      # Production Kubernetes manifests & HPA
├── monitoring/
│   └── prometheus.yml        # Prometheus scrape configurations
├── src/
│   ├── agent/                # Conversation Agent & RAG question bank
│   ├── api/
│   │   ├── routes/           # REST endpoints (/health, /session, /user)
│   │   ├── sse/              # Server-Sent Events (/sse/status)
│   │   └── websockets/       # WebSockets (/ws/converse, /ws/clone)
│   ├── core/                 # Config, Strategy Pattern Interfaces, Constants
│   ├── db/                   # SQLAlchemy async models & DB session factory
│   ├── ml/                   # Preprocessing, Feature Extractor, Pitch Model, Registry
│   ├── notifications/        # Redis Pub/Sub Publisher & Subscriber
│   ├── utils/                # Audio chunk storage, WAV concatenation, Rate limiter
│   └── workers/              # Celery task queue & RabbitMQ DLQ topology
├── tests/                    # 23 automated unit and integration tests
├── Dockerfile                # Multi-stage container build
├── docker-compose.yml        # Multi-container orchestration stack
└── pyproject.toml            # Project metadata and tooling config
```

