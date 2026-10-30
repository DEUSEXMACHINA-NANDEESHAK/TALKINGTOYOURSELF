"""
EchoAgent — API Middleware
Request correlation ID, timing headers, and unified error handling.
"""

import time
import uuid
import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.exceptions import EchoAgentError

logger = structlog.get_logger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Adds correlation ID and measures request execution time."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        start_time = time.perf_counter()
        try:
            response: Response = await call_next(request)
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "unhandled_exception",
                request_id=request_id,
                path=request.url.path,
                method=request.method,
                duration_ms=round(duration_ms, 2),
                error=str(exc),
            )
            raise exc

        duration_ms = (time.perf_counter() - start_time) * 1000
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-Ms"] = f"{duration_ms:.2f}"
        return response


def setup_middleware(app: FastAPI) -> None:
    """Register all middleware on the application."""
    # CORS setup
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Restrict to frontend origin in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Correlation ID & Timing
    app.add_middleware(RequestContextMiddleware)

    # Domain Exception Handler
    @app.exception_handler(EchoAgentError)
    async def echoagent_exception_handler(request: Request, exc: EchoAgentError):
        request_id = getattr(request.state, "request_id", "unknown")
        status_code = 400
        if "NOT_FOUND" in exc.code:
            status_code = 404
        elif "RATE_LIMIT" in exc.code:
            status_code = 429
        elif "INTERNAL" in exc.code:
            status_code = 500

        return JSONResponse(
            status_code=status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "request_id": request_id,
                }
            },
        )

