"""
Unit tests for AuditService.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.audit_service import AuditService


class TestAuditServiceLog:
    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_log_creates_audit_entry(self, mock_session):
        """Should create audit log entry."""
        service = AuditService(mock_session)

        entry = await service.log(
            action="TRANSFER",
            resource_type="TRANSACTION",
            resource_id="tx123",
            actor_id="user123",
            actor_type="USER",
            ip_address="192.168.1.1",
            request_id="req123",
            new_state={"amount": "100.00"},
        )

        assert entry.action == "TRANSFER"
        assert entry.resource_type == "TRANSACTION"
        assert entry.resource_id == "tx123"
        assert entry.actor_id == "user123"
        assert entry.entry_hash is not None
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_generates_hash(self, mock_session):
        """Should generate entry hash for integrity."""
        service = AuditService(mock_session)

        entry = await service.log(
            action="CREATE",
            resource_type="ACCOUNT",
            actor_type="SYSTEM",
        )

        assert entry.entry_hash is not None
        assert len(entry.entry_hash) == 64  # SHA256 hex


class TestAuditServiceLogTransfer:
    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_log_transfer(self, mock_session):
        """Should log transfer with correct fields."""
        service = AuditService(mock_session)

        entry = await service.log_transfer(
            transaction_id="tx123",
            source_account_id="src123",
            destination_account_id="dst123",
            amount="100.00",
            currency="NGN",
            actor_id="user123",
            ip_address="10.0.0.1",
            request_id="req123",
        )

        assert entry.action == "TRANSFER"
        assert entry.resource_type == "TRANSACTION"
        assert entry.resource_id == "tx123"


class TestAuditServiceLogReversal:
    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_log_reversal(self, mock_session):
        """Should log reversal with original transaction reference."""
        service = AuditService(mock_session)

        entry = await service.log_reversal(
            reversal_transaction_id="rev123",
            original_transaction_id="tx123",
            actor_id="user123",
        )

        assert entry.action == "REVERSAL"
        assert entry.resource_id == "rev123"
        assert entry.extra_data["original_transaction_id"] == "tx123"
