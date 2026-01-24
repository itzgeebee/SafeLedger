from hashlib import sha256
from typing import Iterable

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def _hash_to_bigint(value: str) -> int:
    """Deterministically hash a string into a 64-bit signed integer for pg advisory locks."""
    h = sha256(value.encode()).digest()[:8]
    # Interpret as signed 64-bit big-endian (postgre expects signed bigint)
    return int.from_bytes(h, byteorder="big", signed=True)


async def pg_advisory_lock(session: AsyncSession, keys: Iterable[str]):
    """Acquire transaction-scoped advisory locks for the given key strings.

    Uses `pg_advisory_xact_lock` which is released at transaction end.
    No-op on non-Postgres dialects (caller must ensure Postgres engine).
    """
    # Detect Postgres by checking dialect name
    try:
        dialect = session.bind.dialect.name
    except Exception:
        return

    if dialect != "postgresql":
        return

    async with session.begin_nested():
        for k in keys:
            bigint = _hash_to_bigint(str(k))
            # Use SQLAlchemy text() with a bound parameter to avoid
            # emitting a plain string SQL expression error.
            await session.execute(
                text("SELECT pg_advisory_xact_lock(:lock)"), {"lock": bigint}
            )
