"""
Integration tests for Transfers API endpoints.
"""

from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4


class TestTransfersExceptionMapping:
    """Tests for exception to HTTP mapping."""

    def test_map_account_not_found(self):
        """AccountNotFoundError should map to 404."""
        from app.api.v1.errors import map_transfer_exception
        from app.domain.exceptions import AccountNotFoundError

        exc = AccountNotFoundError("Account xyz not found")
        http_exc = map_transfer_exception(exc)

        assert http_exc.status_code == 404

    def test_map_transaction_not_found(self):
        """TransactionNotFoundError should map to 404."""
        from app.api.v1.errors import map_transfer_exception
        from app.domain.exceptions import TransactionNotFoundError

        exc = TransactionNotFoundError()
        http_exc = map_transfer_exception(exc)

        assert http_exc.status_code == 404

    def test_map_duplicate_transaction(self):
        """DuplicateTransactionError should map to 409."""
        from app.api.v1.errors import map_transfer_exception
        from app.domain.exceptions import DuplicateTransactionError

        exc = DuplicateTransactionError()
        http_exc = map_transfer_exception(exc)

        assert http_exc.status_code == 409

    def test_map_idempotency_key_conflict(self):
        """IdempotencyKeyConflictError should map to 409."""
        from app.api.v1.errors import map_transfer_exception
        from app.domain.exceptions import IdempotencyKeyConflictError

        exc = IdempotencyKeyConflictError()
        http_exc = map_transfer_exception(exc)

        assert http_exc.status_code == 409

    def test_map_insufficient_funds(self):
        """InsufficientFundsError should map to 400."""
        from app.api.v1.errors import map_transfer_exception
        from app.domain.exceptions import InsufficientFundsError

        exc = InsufficientFundsError("Not enough balance")
        http_exc = map_transfer_exception(exc)

        assert http_exc.status_code == 400

    def test_map_generic_safeledger_error(self):
        """SafeLedgerError should map to 400."""
        from app.api.v1.errors import map_transfer_exception
        from app.domain.exceptions import SafeLedgerError

        exc = SafeLedgerError("Generic error")
        http_exc = map_transfer_exception(exc)

        assert http_exc.status_code == 400

    def test_map_unknown_exception(self):
        """Unknown exception should map to 500."""
        from app.api.v1.errors import map_transfer_exception

        exc = RuntimeError("Unexpected")
        http_exc = map_transfer_exception(exc)

        assert http_exc.status_code == 500


class TestTransfersRequestHelpers:
    """Tests for request helper functions."""

    def test_get_request_id_present(self):
        """Should extract X-Request-ID from headers."""
        from app.api.v1.utils import get_request_id

        mock_request = MagicMock()
        mock_request.headers = {"X-Request-ID": "req-123"}

        assert get_request_id(mock_request) == "req-123"

    def test_get_request_id_missing(self):
        """Should return None when X-Request-ID missing."""
        from app.api.v1.utils import get_request_id

        mock_request = MagicMock()
        mock_request.headers = {}

        assert get_request_id(mock_request) is None

    def test_get_client_ip_from_forwarded(self):
        """Should extract IP from X-Forwarded-For."""
        from app.api.v1.utils import get_client_ip

        mock_request = MagicMock()
        mock_request.headers = {"X-Forwarded-For": "10.0.0.1, 192.168.1.1"}

        assert get_client_ip(mock_request) == "10.0.0.1"

    def test_get_client_ip_from_client(self):
        """Should fall back to client.host."""
        from app.api.v1.utils import get_client_ip

        mock_request = MagicMock()
        mock_request.headers = {}
        mock_request.client.host = "127.0.0.1"

        assert get_client_ip(mock_request) == "127.0.0.1"

    def test_get_client_ip_no_client(self):
        """Should return None when no client info."""
        from app.api.v1.utils import get_client_ip

        mock_request = MagicMock()
        mock_request.headers = {}
        mock_request.client = None

        assert get_client_ip(mock_request) is None


class TestTransferSchemas:
    """Tests for transfer request/response schemas."""

    def test_transfer_request_schema(self):
        """TransferRequest should validate fields."""
        from app.schemas.transfer import TransferRequest

        request = TransferRequest(
            source_account_id=uuid4(),
            destination_account_id=uuid4(),
            amount=Decimal("100.00"),
            fee_amount=Decimal("5.00"),
            currency="NGN",
        )

        assert request.amount == Decimal("100.00")
        assert request.currency == "NGN"

    def test_transfer_response_schema(self):
        """TransferResponse should include transaction details."""
        from datetime import UTC, datetime

        from app.schemas.transfer import TransferResponse

        response = TransferResponse(
            transaction_id=uuid4(),
            source_account_id=uuid4(),
            destination_account_id=uuid4(),
            amount=Decimal("100.00"),
            fee_amount=Decimal("5.00"),
            currency="NGN",
            status="SUCCESS",
            created_at=datetime.now(UTC),
        )

        assert response.status == "SUCCESS"
