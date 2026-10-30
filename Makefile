.PHONY: help dev up down build test lint format check clean logs

# ── Colors ───────────────────────────────────────
CYAN  := \033[36m
GREEN := \033[32m
RESET := \033[0m

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(CYAN)%-15s$(RESET) %s\n", $$1, $$2}'

# ── Development ──────────────────────────────────
dev: ## Start dev stack (docker-compose + hot reload)
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

up: ## Start production stack
	docker compose up -d --build

down: ## Stop all containers
	docker compose down

build: ## Build Docker image
	docker compose build

logs: ## Tail container logs
	docker compose logs -f

# ── Code Quality ─────────────────────────────────
lint: ## Run linter (ruff)
	ruff check src/ tests/

format: ## Format code (black + ruff)
	black src/ tests/
	ruff check --fix src/ tests/

check: lint ## Run all checks (lint + type check)
	mypy src/ --ignore-missing-imports

# ── Testing ──────────────────────────────────────
test: ## Run test suite
	pytest tests/ -v --tb=short

test-cov: ## Run tests with coverage
	pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=html

test-fast: ## Run fast tests only (skip slow/integration)
	pytest tests/ -v -m "not slow and not integration"

# ── Database ─────────────────────────────────────
db-migrate: ## Create new migration
	alembic revision --autogenerate -m "$(msg)"

db-upgrade: ## Run migrations
	alembic upgrade head

db-downgrade: ## Rollback last migration
	alembic downgrade -1

# ── Cleanup ──────────────────────────────────────
clean: ## Remove generated files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -f .coverage

