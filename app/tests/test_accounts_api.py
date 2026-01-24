"""
Integration tests for Accounts API endpoints.
"""

from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4

from fastapi import status


class TestAccountsResponseModels:
    """Tests for response models."""

    def test_account_response_model(self):
        """AccountResponse should serialize correctly."""
        from app.schemas.account import AccountResponse

        response = AccountResponse(
            id=uuid4(),
            owner_id="user123",
            currency="NGN",
            account_type="USER",
            is_active=True,
        )

        assert response.currency == "NGN"
        assert response.is_active is True

    def test_balance_response_model(self):
        """BalanceResponse should handle Decimal."""
        from app.schemas.account import BalanceResponse

        response = BalanceResponse(
            account_id=uuid4(),
            currency="NGN",
            balance=Decimal("1234.56"),
        )

        assert response.balance == Decimal("1234.56")

    def test_create_account_request_model(self):
        """CreateAccountRequest should validate fields."""
        from app.schemas.account import CreateAccountRequest

        request = CreateAccountRequest(
            owner_id="user123",
            currency="NGN",
            account_type="USER",
        )

        assert request.owner_id == "user123"
        assert len(request.currency) == 3

    def test_account_list_response_model(self):
        """AccountListResponse should contain list of accounts."""
        from app.schemas.account import AccountListResponse, AccountResponse

        accounts = [
            AccountResponse(
                id=uuid4(),
                owner_id="user123",
                currency="NGN",
                account_type="USER",
                is_active=True,
            ),
            AccountResponse(
                id=uuid4(),
                owner_id="user123",
                currency="USD",
                account_type="USER",
                is_active=True,
            ),
        ]

        response = AccountListResponse(accounts=accounts)
        assert len(response.accounts) == 2


class TestAccountsExceptionMapping:
    """Tests for exception to HTTP mapping."""

    def test_map_account_not_found(self):
        """AccountNotFoundError should map to 404."""
        from app.api.v1.errors import map_account_exception
        from app.domain.exceptions import AccountNotFoundError

        exc = AccountNotFoundError()
        http_exc = map_account_exception(exc)

        assert http_exc.status_code == status.HTTP_404_NOT_FOUND

    def test_map_invalid_account(self):
        """InvalidAccountError should map to 400."""
        from app.api.v1.errors import map_account_exception
        from app.domain.exceptions import InvalidAccountError

        exc = InvalidAccountError("Invalid type")
        http_exc = map_account_exception(exc)

        assert http_exc.status_code == status.HTTP_400_BAD_REQUEST

    def test_map_generic_safeledger_error(self):
        """SafeLedgerError should map to 400."""
        from app.api.v1.errors import map_account_exception
        from app.domain.exceptions import SafeLedgerError

        exc = SafeLedgerError("Something went wrong")
        http_exc = map_account_exception(exc)

        assert http_exc.status_code == status.HTTP_400_BAD_REQUEST

    def test_map_unknown_exception(self):
        """Unknown exception should map to 500."""
        from app.api.v1.errors import map_account_exception

        exc = ValueError("Unexpected error")
        http_exc = map_account_exception(exc)

        assert http_exc.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestAccountToResponse:
    """Tests for account model to response conversion."""

    def test_account_to_response_conversion(self):
        """Should convert Account model to AccountResponse."""
        from enum import Enum

        from app.schemas.account import account_to_response

        class MockAccountType(str, Enum):
            USER = "USER"

        mock_account = MagicMock()
        mock_account.id = uuid4()
        mock_account.owner_id = "user123"
        mock_account.currency = "NGN"
        mock_account.account_type = MockAccountType.USER
        mock_account.is_active = True

        response = account_to_response(mock_account)

        assert response.owner_id == "user123"
        assert response.account_type == "USER"
