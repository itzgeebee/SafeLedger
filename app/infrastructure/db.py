import os

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Try to read structured settings, but avoid hard failure at import time so local
# development and tests can run without environment variables. If `get_settings()`
# raises (missing env vars or ValidationError), fall back to a local sqlite DB.
try:
    from app.config import get_settings

    settings = get_settings()
    database_url = settings.DATABASE_URL
    db_echo = settings.DB_ECHO
except Exception:
    database_url = os.getenv("DATABASE_URL") or "sqlite+aiosqlite:///./dev.db"
    db_echo = False

# -------------------------
# Engine
# -------------------------


def create_db_engine(url: str, echo: bool = False) -> AsyncEngine:
    return create_async_engine(
        url,
        echo=echo,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )


engine: AsyncEngine = create_db_engine(database_url, db_echo)

# -------------------------
# Session factory
# -------------------------

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# -------------------------
# Dependency (FastAPI)
# -------------------------


async def get_db() -> AsyncSession:
    """
    FastAPI dependency that provides a DB session.

    - One session per request
    - Automatic rollback on error
    - Explicit commit handled by service layer
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
