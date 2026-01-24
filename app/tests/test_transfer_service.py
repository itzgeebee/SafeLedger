"""
Unit tests for TransferService.
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.domain.exceptions import (
    DuplicateTransactionError,
    InvalidTransferError,
)
from app.schemas.transfer import TransferRequest
from app.services.transfer_service import TransferService


class TestTransferServiceExecute:
    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        # Mocking context manager for session.begin()
        session.begin = MagicMock()
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock()
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        session.begin.return_value = mock_cm
        return session

    @pytest.fixture
    def mock_payload(self):
        return TransferRequest(
            source_account_id=uuid4(),
            destination_account_id=uuid4(),
            amount=Decimal("100.00"),
            fee_amount=Decimal("10.00"),
            currency="NGN",
        )

    @pytest.mark.asyncio
    async def test_execute_success_internal(self, mock_session, mock_payload):
        """Should successfully execute internal transfer."""
        service = TransferService(mock_session)

        # Mock dependencies
        service.idempotency_service = AsyncMock()
        service.idempotency_service.check_or_fail.return_value = None
        service.idempotency_service.record.return_value = (
            MagicMock(response_body=None),
            True,
        )

        service.accounts_repo = AsyncMock()
        mock_source = MagicMock(id=mock_payload.source_account_id, currency="NGN")
        mock_dest = MagicMock(id=mock_payload.destination_account_id, currency="NGN")
        service.accounts_repo.get_accounts_for_update.return_value = {
            mock_payload.source_account_id: mock_source,
            mock_payload.destination_account_id: mock_dest,
        }

        # System account for fees
        mock_fee_acc = MagicMock(id=uuid4(), currency="NGN")
        service.accounts_repo.get_system_account.return_value = mock_fee_acc
        service.accounts_repo.get_accounts_for_update.return_value[mock_fee_acc.id] = (
            mock_fee_acc
        )

        service.balance_service = AsyncMock()
        service.ledger_repo = AsyncMock()

        with patch("app.services.transfer_service.get_settings") as mock_settings:
            mock_settings.return_value.MAX_TRANSACTION_AMOUNT = 1000000
            response = await service.execute(
                payload=mock_payload, idempotency_key="tx-123", is_external=False
            )

        assert response.status == "SUCCESS"
        assert response.amount == mock_payload.amount
        service.ledger_repo.persist_transaction.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_success_external(self, mock_session, mock_payload):
        """Should use settlement account for external transfers."""
        service = TransferService(mock_session)

        service.idempotency_service = AsyncMock()
        service.idempotency_service.check_or_fail.return_value = None
        service.idempotency_service.record.return_value = (
            MagicMock(response_body=None),
            True,
        )

        service.accounts_repo = AsyncMock()
        mock_settlement = MagicMock(id=uuid4(), currency="NGN")
        service.accounts_repo.get_settlement_account.return_value = mock_settlement

        mock_source = MagicMock(id=mock_payload.source_account_id, currency="NGN")
        service.accounts_repo.get_accounts_for_update.return_value = {
            mock_payload.source_account_id: mock_source,
            mock_settlement.id: mock_settlement,
        }

        service.balance_service = AsyncMock()
        service.ledger_repo = AsyncMock()

        with patch("app.services.transfer_service.get_settings") as mock_settings:
            mock_settings.return_value.MAX_TRANSACTION_AMOUNT = 1000000
            # Set fee_amount to 0 for this test to avoid needing system account mock
            mock_payload.fee_amount = Decimal("0")
            response = await service.execute(
                payload=mock_payload, idempotency_key="tx-123", is_external=True
            )

        assert response.status == "SUCCESS"
        assert response.destination_account_id == mock_settlement.id
        service.accounts_repo.get_settlement_account.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_amount_exceeds_limit(self, mock_session, mock_payload):
        """Should raise InvalidTransferError if limit exceeded."""
        service = TransferService(mock_session)

        with patch("app.services.transfer_service.get_settings") as mock_settings:
            mock_settings.return_value.MAX_TRANSACTION_AMOUNT = 50
            with pytest.raises(InvalidTransferError) as exc:
                await service.execute(payload=mock_payload, idempotency_key="tx-123")

        assert "exceeds maximum" in str(exc.value)

    @pytest.mark.asyncio
    async def test_execute_replays_idempotent_response(
        self, mock_session, mock_payload
    ):
        """Should return existing response for same idempotency key."""
        service = TransferService(mock_session)

        mock_existing = MagicMock()
        mock_existing.response_body = f'{{"transaction_id": "{uuid4()}", "source_account_id": "{uuid4()}", "destination_account_id": "{uuid4()}", "amount": "100.00", "fee_amount": "0.00", "currency": "NGN", "status": "SUCCESS", "created_at": "2024-01-01T00:00:00Z"}}'

        service.idempotency_service = AsyncMock()
        service.idempotency_service.check_or_fail.return_value = mock_existing

        with patch("app.services.transfer_service.get_settings") as mock_settings:
            mock_settings.return_value.MAX_TRANSACTION_AMOUNT = 1000
            response = await service.execute(
                payload=mock_payload, idempotency_key="existing-key"
            )

        assert response.status == "SUCCESS"
        assert response.amount == Decimal("100.00")

    @pytest.mark.asyncio
    async def test_execute_handles_inflight_conflict(self, mock_session, mock_payload):
        """Should raise DuplicateTransactionError if reservation fail."""
        service = TransferService(mock_session)

        service.idempotency_service = AsyncMock()
        service.idempotency_service.check_or_fail.return_value = None
        service.idempotency_service.record.return_value = (
            MagicMock(response_body=None),
            False,
        )

        service.accounts_repo = AsyncMock()
        service.accounts_repo.get_accounts_for_update.return_value = {
            mock_payload.source_account_id: MagicMock(
                id=mock_payload.source_account_id, currency="NGN"
            ),
            mock_payload.destination_account_id: MagicMock(
                id=mock_payload.destination_account_id, currency="NGN"
            ),
        }

        service.balance_service = AsyncMock()

        with patch("app.services.transfer_service.get_settings") as mock_settings:
            mock_settings.return_value.MAX_TRANSACTION_AMOUNT = 1000
            with pytest.raises(DuplicateTransactionError):
                await service.execute(payload=mock_payload, idempotency_key="tx-key")

    @pytest.mark.asyncio
    async def test_execute_handles_late_idempotency_replay(
        self, mock_session, mock_payload
    ):
        """Should replay response if found during reservation check."""
        service = TransferService(mock_session)

        service.idempotency_service = AsyncMock()
        service.idempotency_service.check_or_fail.return_value = None

        mock_resp_json = f'{{"transaction_id": "{uuid4()}", "source_account_id": "{uuid4()}", "destination_account_id": "{uuid4()}", "amount": "100.00", "fee_amount": "0.00", "currency": "NGN", "status": "SUCCESS", "created_at": "2024-01-01T00:00:00Z"}}'
        service.idempotency_service.record.return_value = (
            MagicMock(response_body=mock_resp_json),
            False,
        )

        service.accounts_repo = AsyncMock()
        service.accounts_repo.get_accounts_for_update.return_value = {
            mock_payload.source_account_id: MagicMock(
                id=mock_payload.source_account_id, currency="NGN"
            ),
            mock_payload.destination_account_id: MagicMock(
                id=mock_payload.destination_account_id, currency="NGN"
            ),
        }

        service.balance_service = AsyncMock()

        with patch("app.services.transfer_service.get_settings") as mock_settings:
            mock_settings.return_value.MAX_TRANSACTION_AMOUNT = 1000
            response = await service.execute(
                payload=mock_payload, idempotency_key="tx-key"
            )

        assert response.status == "SUCCESS"
        assert response.amount == Decimal("100.00")
