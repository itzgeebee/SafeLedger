import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.infrastructure.advisory_lock import pg_advisory_lock


@pytest.mark.asyncio
async def test_pg_advisory_lock_acquires_lock(db_engine):
    # Skip if not Postgres dialect
    if db_engine.dialect.name != "postgresql":
        pytest.skip("Not a Postgres database; skipping advisory lock test")

    async_session = async_sessionmaker(db_engine, expire_on_commit=False)

    async with async_session() as session:
        async with session.begin():
            # Should not raise and should acquire the transaction-scoped locks
            await pg_advisory_lock(session, ["test-key-1", "test-key-2"])
            # Basic DB roundtrip to ensure session is usable
            res = await session.execute(text("SELECT 1 as one"))
            assert res.scalar_one() == 1
