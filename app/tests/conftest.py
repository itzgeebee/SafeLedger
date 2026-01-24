import os
from typing import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import get_settings
from app.db.db import create_db_engine, get_db
from app.main import create_app
from app.models import Base

# Load settings
settings = get_settings()

# Determine the test database URL
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
if not TEST_DATABASE_URL:
    db_url = settings.DATABASE_URL
    if db_url and "postgresql" in db_url:
        # Robustly replace the DB name part of the URL
        # URL format: postgresql+asyncpg://user:pass@host:port/dbname
        if "/" in db_url:
            base_url = db_url.rsplit("/", 1)[0]
            TEST_DATABASE_URL = f"{base_url}/safeledger_test"
        else:
            TEST_DATABASE_URL = db_url + "_test"
    else:
        # Fallback to sqlite for tests if not postgres
        TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"


@pytest.fixture(scope="session")
async def db_engine():
    """Session-scoped database engine."""
    engine = create_db_engine(TEST_DATABASE_URL)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Function-scoped session that rolls back all changes after each test.
    This ensures test isolation.
    """
    connection = await db_engine.connect()
    transaction = await connection.begin()

    # Create a session bound to the connection
    SessionLocal = async_sessionmaker(
        bind=connection,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    session = SessionLocal()

    yield session

    await session.close()
    await transaction.rollback()
    await connection.close()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Async HTTP client for testing API endpoints.
    Overwrites the get_db dependency to use the test session.
    """
    app = create_app()

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    # Use ASGITransport for testing
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
