"""
Unit tests for infrastructure and repository logic.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.infrastructure.advisory_lock import _hash_to_bigint, pg_advisory_lock
from app.infrastructure.repositories.idempotency_repo import IdempotencyRepository


class TestHashToBigInt:
    def test_hash_is_deterministic(self):
        """Should produce same bigint for same string."""
        val = "test-key"
        h1 = _hash_to_bigint(val)
        h2 = _hash_to_bigint(val)
        assert h1 == h2
        assert isinstance(h1, int)

    def test_different_hashes_for_different_strings(self):
        assert _hash_to_bigint("a") != _hash_to_bigint("b")


class TestPgAdvisoryLock:
    @pytest.mark.asyncio
    async def test_pg_advisory_lock_ignores_non_postgres(self):
        """Should return early if not postgres."""
        mock_session = MagicMock()
        mock_session.bind.dialect.name = "sqlite"
        mock_session.begin_nested = MagicMock()

        await pg_advisory_lock(mock_session, ["key1"])
        mock_session.begin_nested.assert_not_called()

    @pytest.mark.asyncio
    async def test_pg_advisory_lock_handles_missing_dialect(self):
        """Should handle cases where dialect check fails."""
        mock_session = MagicMock()
        mock_session.bind = None  # Will raise on access

        await pg_advisory_lock(mock_session, ["key1"])
        # Should just return gracefully


class TestIdempotencyRepoLogic:
    def test_hash_payload_logic(self):
        """Should produce deterministic hash for payload."""
        repo = IdempotencyRepository(AsyncMock())
        payload = {"b": 2, "a": 1}
        payload2 = {"a": 1, "b": 2}

        h1 = repo._hash_payload(payload)
        h2 = repo._hash_payload(payload2)

        assert h1 == h2
        assert len(h1) == 64  # SHA256 hex
