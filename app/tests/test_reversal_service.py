"""
Unit tests for Reversal Services.
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.domain.entry_type import EntryType
from app.domain.exceptions import (
    InvalidReversalError,
)
from app.domain.ledger import LedgerEntrySpec, LedgerTransaction
from app.services.reversal_services import ReversalService


class TestReversalServiceExecute:
    @pytest.fixture
    def mock_session(self, mock_session_internal):
        return mock_session_internal

    @pytest.fixture
    def mock_session_internal(self):
        session = AsyncMock()
        # session.begin is a regular method returning an async context manager
        session.begin = MagicMock()
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock()
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        session.begin.return_value = mock_cm
        return session

    @pytest.fixture
    def mock_original_transaction(self):
        """Create a mock original transaction with entries."""
        tx_id = uuid4()
        return LedgerTransaction(
            transaction_id=tx_id,
            entries=[
                LedgerEntrySpec(
                    account_id=uuid4(),
                    amount=Decimal("110.00"),
                    entry_type=EntryType.DEBIT,
                    currency="NGN",
                ),
                LedgerEntrySpec(
                    account_id=uuid4(),
                    amount=Decimal("100.00"),
                    entry_type=EntryType.CREDIT,
                    currency="NGN",
                ),
                LedgerEntrySpec(
                    account_id=uuid4(),
                    amount=Decimal("10.00"),
                    entry_type=EntryType.CREDIT,
                    currency="NGN",
                ),
            ],
        )

    @pytest.mark.asyncio
    async def test_execute_reversal_success(
        self, mock_session, mock_original_transaction
    ):
        """Successful reversal should persist entries and return response."""
        service = ReversalService(mock_session)

        # Mock all internal dependencies
        service.idempotency_service = AsyncMock()
        service.idempotency_service.check_or_fail.return_value = None
        service.idempotency_service.record.return_value = (
            MagicMock(response_body=None),
            True,
        )

        service.query_repo = AsyncMock()
        service.query_repo.get_transaction.return_value = mock_original_transaction

        service.idempotency_repo = AsyncMock()
        service.idempotency_repo.get_existing.return_value = None

        service.accounts_repo = AsyncMock()
        service.balance_service = AsyncMock()
        service.ledger_repo = AsyncMock()

        response = await service.execute(
            original_transaction_id=mock_original_transaction.transaction_id,
            idempotency_key="test-reversal-key",
        )

        assert response.status == "REVERSED"
        # The service currently returns the total credited amount as 'amount'
        assert response.amount == Decimal("110.00")
        assert response.fee_amount == Decimal("0.00")

        service.ledger_repo.persist_transaction.assert_called_once()
        service.idempotency_repo.store_new.assert_called_once()  # For reversal_check

    @pytest.mark.asyncio
    async def test_execute_already_reversed_raises(
        self, mock_session, mock_original_transaction
    ):
        """Should raise InvalidReversalError if already reversed."""
        service = ReversalService(mock_session)

        service.idempotency_service = AsyncMock()
        service.idempotency_service.check_or_fail.return_value = None

        service.query_repo = AsyncMock()
        service.query_repo.get_transaction.return_value = mock_original_transaction

        service.idempotency_repo = AsyncMock()
        service.idempotency_repo.get_existing.return_value = MagicMock()  # Exists

        with pytest.raises(InvalidReversalError) as exc:
            await service.execute(
                original_transaction_id=mock_original_transaction.transaction_id,
                idempotency_key="test-key",
            )

        assert "already been reversed" in str(exc.value)

    @pytest.mark.asyncio
    async def test_execute_replays_idempotent_response(self, mock_session):
        """Should return existing response for same idempotency key."""
        service = ReversalService(mock_session)

        source_id = "00000000-0000-0000-0000-000000000001"
        dest_id = "00000000-0000-0000-0000-000000000002"
        mock_existing = MagicMock()
        mock_existing.response_body = (
            f'{{"transaction_id": "8f8f8f8f-8f8f-8f8f-8f8f-8f8f8f8f8f8f", '
            f'"status": "REVERSED", "amount": "100.00", "fee_amount": "0.00", '
            f'"currency": "USD", "source_account_id": "{source_id}", '
            f'"destination_account_id": "{dest_id}", "created_at": "2024-01-01T00:00:00Z"}}'
        )

        service.idempotency_service = AsyncMock()
        service.idempotency_service.check_or_fail.return_value = mock_existing

        response = await service.execute(
            original_transaction_id=uuid4(), idempotency_key="existing-key"
        )

        assert response.status == "REVERSED"
        assert response.amount == Decimal("100.00")
        assert str(response.transaction_id) == "8f8f8f8f-8f8f-8f8f-8f8f-8f8f8f8f8f8f"

    @pytest.mark.asyncio
    async def test_execute_handles_concurrent_reservation(
        self, mock_session, mock_original_transaction
    ):
        """Should raise DuplicateTransactionError if reservation fails."""
        from app.domain.exceptions import DuplicateTransactionError

        service = ReversalService(mock_session)

        service.idempotency_service = AsyncMock()
        service.idempotency_service.check_or_fail.return_value = None
        service.idempotency_service.record.return_value = (
            MagicMock(response_body=None),
            False,
        )  # Not created

        service.query_repo = AsyncMock()
        service.query_repo.get_transaction.return_value = mock_original_transaction
        service.idempotency_repo = AsyncMock()
        service.idempotency_repo.get_existing.return_value = None
        service.accounts_repo = AsyncMock()
        service.balance_service = AsyncMock()

        with pytest.raises(DuplicateTransactionError):
            await service.execute(
                original_transaction_id=mock_original_transaction.transaction_id,
                idempotency_key="tx-key",
            )


class TestReversalValidation:
    def test_reversal_creates_opposite_entries(self):
        """Reversal should invert all entry types."""
        from app.domain.ledger import Ledger

        original = LedgerTransaction(
            transaction_id=uuid4(),
            entries=[
                LedgerEntrySpec(
                    account_id=uuid4(),
                    amount=Decimal("100.00"),
                    entry_type=EntryType.DEBIT,
                    currency="NGN",
                ),
                LedgerEntrySpec(
                    account_id=uuid4(),
                    amount=Decimal("100.00"),
                    entry_type=EntryType.CREDIT,
                    currency="NGN",
                ),
            ],
        )

        reversed_tx = Ledger.reversal(original)

        # Should have same number of entries
        assert len(reversed_tx.entries) == len(original.entries)

        # Entry types should be inverted
        for orig_entry, rev_entry in zip(original.entries, reversed_tx.entries):
            assert rev_entry.entry_type == orig_entry.entry_type.opposite()
            assert rev_entry.amount == orig_entry.amount
            assert rev_entry.account_id == orig_entry.account_id

    def test_reversal_maintains_zero_sum(self):
        """Reversed transaction should still be zero-sum."""
        from app.domain.ledger import Ledger

        original = LedgerTransaction(
            transaction_id=uuid4(),
            entries=[
                LedgerEntrySpec(
                    account_id=uuid4(),
                    amount=Decimal("100.00"),
                    entry_type=EntryType.DEBIT,
                    currency="NGN",
                ),
                LedgerEntrySpec(
                    account_id=uuid4(),
                    amount=Decimal("100.00"),
                    entry_type=EntryType.CREDIT,
                    currency="NGN",
                ),
            ],
        )

        reversed_tx = Ledger.reversal(original)

        # Calculate sums
        debits = sum(
            e.amount for e in reversed_tx.entries if e.entry_type == EntryType.DEBIT
        )
        credits = sum(
            e.amount for e in reversed_tx.entries if e.entry_type == EntryType.CREDIT
        )

        assert debits == credits

    def test_reversal_has_new_transaction_id(self):
        """Reversed transaction should have new ID."""
        from app.domain.ledger import Ledger

        original = LedgerTransaction(
            transaction_id=uuid4(),
            entries=[
                LedgerEntrySpec(
                    account_id=uuid4(),
                    amount=Decimal("50.00"),
                    entry_type=EntryType.DEBIT,
                    currency="USD",
                ),
                LedgerEntrySpec(
                    account_id=uuid4(),
                    amount=Decimal("50.00"),
                    entry_type=EntryType.CREDIT,
                    currency="USD",
                ),
            ],
        )

        reversed_tx = Ledger.reversal(original)

        assert reversed_tx.transaction_id != original.transaction_id
