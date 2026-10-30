"""
EchoAgent — API Gateway Entrypoint
Stateless FastAPI application factory.
"""

from contextlib import asynccontextmanager
import structlog
from fastapi import FastAPI

from src.api.middleware import setup_middleware
from src.api.routes import health, session, user
from src.api.sse import progress
from src.api.websockets import clone, converse
from src.core.config import get_settings

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup & shutdown tasks."""
    settings = get_settings()
    logger.info(
        "app_startup",
        app_name=settings.app_name,
        env=settings.app_env,
        debug=settings.debug,
    )
    yield
    logger.info("app_shutdown", app_name=settings.app_name)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    settings = get_settings()

    app = FastAPI(
        title="EchoAgent Core API",
        description="Production-grade, MLOps-first agentic voice-cloning platform.",
        version="0.1.0",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # Middleware
    setup_middleware(app)

    # Routers
    app.include_router(health.router)
    app.include_router(session.router)
    app.include_router(user.router)
    app.include_router(converse.router)
    app.include_router(clone.router)
    app.include_router(progress.router)

    return app


app = create_app()
