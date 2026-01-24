import asyncio

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.infrastructure.repositories.idempotency_repo import IdempotencyRepository


@pytest.mark.asyncio
async def test_concurrent_store_new_race(db_engine):
    # Only run against Postgres for meaningful concurrency behavior
    if db_engine.dialect.name != "postgresql":
        pytest.skip("Not a Postgres database; skipping idempotency race test")

    Session = async_sessionmaker(db_engine, expire_on_commit=False)
    from uuid import uuid4

    key = f"race-test-key-{uuid4()}"
    scope = "test"
    payload = {"a": 1}

    async def task():
        async with Session() as session:
            repo = IdempotencyRepository(session)
            res = await repo.store_new(
                key=key, scope=scope, payload=payload, response_body=None
            )
            await session.commit()
            return res

    # Run two concurrent tasks that both try to reserve the same idempotency key
    results = await asyncio.gather(task(), task())

    # Normalize results to (record, created_flag)
    created_flags = [r[1] for r in results]
    assert sum(1 for f in created_flags if f) == 1

    # Both returned records should share the same request hash
    r0, r1 = results[0][0], results[1][0]
    assert r0.request_hash == r1.request_hash
