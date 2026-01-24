"""
Unit tests for IdempotencyService.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.idempotency_service import IdempotencyService


class TestIdempotencyService:
    @pytest.fixture
    def mock_repo(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_check_or_fail_found_match(self, mock_repo):
        """Should return existing record from validate_or_reuse."""
        service = IdempotencyService(mock_repo)

        mock_record = MagicMock()
        mock_repo.validate_or_reuse.return_value = mock_record

        result = await service.check_or_fail(
            key="test-key", scope="test-scope", payload={"amount": "100"}
        )

        assert result == mock_record
        mock_repo.validate_or_reuse.assert_called_once_with(
            key="test-key", scope="test-scope", payload={"amount": "100"}
        )

    @pytest.mark.asyncio
    async def test_check_or_fail_not_found(self, mock_repo):
        """Should return None if key not found."""
        service = IdempotencyService(mock_repo)
        mock_repo.validate_or_reuse.return_value = None

        result = await service.check_or_fail(key="key", scope="scope", payload={})
        assert result is None

    @pytest.mark.asyncio
    async def test_record_reservation_new(self, mock_repo):
        """Should return (record, True) for new reservation."""
        service = IdempotencyService(mock_repo)

        mock_record = MagicMock()
        mock_repo.store_new.return_value = (mock_record, True)

        # When response_body is None, it hits the reservation path
        result = await service.record(
            key="new-key", scope="scope", payload={"foo": "bar"}, response_body=None
        )

        assert result == (mock_record, True)
        mock_repo.store_new.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_finalize_existing(self, mock_repo):
        """Should update existing record with response and return it."""
        service = IdempotencyService(mock_repo)

        mock_record = MagicMock()
        mock_repo.get_existing.return_value = mock_record

        # When response_body is provided, it updates existing
        result = await service.record(
            key="existing-key", scope="scope", payload={}, response_body='{"ok": true}'
        )

        assert result == mock_record
        mock_repo.update_response.assert_called_once_with(
            key="existing-key", scope="scope", response_body='{"ok": true}'
        )

    @pytest.mark.asyncio
    async def test_record_finalize_no_reservation(self, mock_repo):
        """Should create new record if no reservation existed (late finalize)."""
        service = IdempotencyService(mock_repo)

        mock_record = MagicMock()
        mock_repo.get_existing.return_value = None
        mock_repo.store_new.return_value = (mock_record, True)

        result = await service.record(
            key="new-key", scope="scope", payload={}, response_body='{"ok": true}'
        )

        assert result == mock_record
        mock_repo.store_new.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_finalize_no_reservation_single_return(self, mock_repo):
        """Should handle store_new returning single record (for line 61 coverage)."""
        service = IdempotencyService(mock_repo)

        mock_record = MagicMock()
        mock_repo.get_existing.return_value = None
        mock_repo.store_new.return_value = mock_record  # Not a tuple

        result = await service.record(
            key="new-key", scope="scope", payload={}, response_body='{"ok": true}'
        )

        assert result == mock_record
        mock_repo.store_new.assert_called_once()
