"""
EchoAgent — Database Session and Engine
Asynchronous PostgreSQL session management via SQLAlchemy 2.0.
"""

from typing import AsyncGenerator
import structlog
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import get_settings

logger = structlog.get_logger(__name__)

_engine = None
_sessionmaker = None


def get_engine():
    """Return singleton async SQLAlchemy engine."""
    global _engine
    if _engine is None:
        settings = get_settings()
        # Fall back to sqlite+aiosqlite for local dev or tests if postgres isn't running
        db_url = settings.database_url
        _engine = create_async_engine(
            db_url,
            pool_pre_ping=True,
            echo=settings.debug,
        )
    return _engine


def get_sessionmaker():
    """Return singleton session factory."""
    global _sessionmaker
    if _sessionmaker is None:
        engine = get_engine()
        _sessionmaker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _sessionmaker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency to yield an async database session."""
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

