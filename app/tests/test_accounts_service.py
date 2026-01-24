"""
Unit tests for AccountsService.
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.domain.exceptions import AccountNotFoundError, InvalidAccountError
from app.services.accounts_service import AccountsService


class TestAccountsServiceGetAccount:
    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.execute = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_get_account_success(self, mock_session):
        """Existing account should be returned."""
        account_id = uuid4()

        mock_account = MagicMock()
        mock_account.id = account_id
        mock_account.owner_id = "user123"
        mock_account.currency = "NGN"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_account
        mock_session.execute.return_value = mock_result

        service = AccountsService(mock_session)

        with patch.object(service, "accounts_repo"):
            account = await service.get_account(account_id)

        assert account.id == account_id

    @pytest.mark.asyncio
    async def test_get_account_not_found(self, mock_session):
        """Non-existent account should raise AccountNotFoundError."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        service = AccountsService(mock_session)

        with pytest.raises(AccountNotFoundError):
            await service.get_account(uuid4())


class TestAccountsServiceGetBalance:
    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_get_account_balance_success(self, mock_session):
        """Should return balance for valid account."""
        account_id = uuid4()

        service = AccountsService(mock_session)

        # Mock the dependencies
        service.accounts_repo = AsyncMock()
        service.accounts_repo.get_ledger_account = AsyncMock()

        service.balance_service = AsyncMock()
        service.balance_service.get_balance = AsyncMock(return_value=Decimal("1000.00"))

        balance = await service.get_account_balance(account_id, "NGN")

        assert balance == Decimal("1000.00")
        service.accounts_repo.get_ledger_account.assert_called_once_with(account_id)
        service.balance_service.get_balance.assert_called_once_with(account_id, "NGN")


class TestAccountsServiceCreateAccount:
    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_create_user_account_success(self, mock_session):
        """USER account with owner_id should be created."""
        service = AccountsService(mock_session)

        account = await service.create_account(
            owner_id="user123",
            currency="ngn",
            account_type="USER",
        )

        assert account.owner_id == "user123"
        assert account.currency == "NGN"  # Should be uppercased
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_system_account_success(self, mock_session):
        """SYSTEM account without owner_id should be created."""
        service = AccountsService(mock_session)

        account = await service.create_account(
            owner_id=None,
            currency="USD",
            account_type="SYSTEM",
        )

        assert account.owner_id is None
        mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_account_invalid_type(self, mock_session):
        """Invalid account type should raise InvalidAccountError."""
        service = AccountsService(mock_session)

        with pytest.raises(InvalidAccountError) as exc:
            await service.create_account(
                owner_id="user123",
                currency="NGN",
                account_type="INVALID_TYPE",
            )

        assert "Invalid account_type" in str(exc.value)

    @pytest.mark.asyncio
    async def test_create_user_account_without_owner_fails(self, mock_session):
        """USER account without owner_id should fail."""
        service = AccountsService(mock_session)

        with pytest.raises(InvalidAccountError) as exc:
            await service.create_account(
                owner_id=None,
                currency="NGN",
                account_type="USER",
            )

        assert "owner_id is required" in str(exc.value)

    @pytest.mark.asyncio
    async def test_create_system_account_with_owner_fails(self, mock_session):
        """SYSTEM account with owner_id should fail."""
        service = AccountsService(mock_session)

        with pytest.raises(InvalidAccountError) as exc:
            await service.create_account(
                owner_id="user123",
                currency="NGN",
                account_type="SYSTEM",
            )

        assert "owner_id must be null" in str(exc.value)


class TestAccountsServiceDeactivate:
    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_deactivate_active_account(self, mock_session):
        """Active account should be deactivated."""
        account_id = uuid4()

        mock_account = MagicMock()
        mock_account.id = account_id
        mock_account.is_active = True

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_account
        mock_session.execute.return_value = mock_result

        service = AccountsService(mock_session)
        account = await service.deactivate_account(account_id)

        assert account.is_active is False
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_deactivate_already_inactive_fails(self, mock_session):
        """Already inactive account should raise error."""
        mock_account = MagicMock()
        mock_account.is_active = False

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_account
        mock_session.execute.return_value = mock_result

        service = AccountsService(mock_session)

        with pytest.raises(InvalidAccountError) as exc:
            await service.deactivate_account(uuid4())

        assert "already inactive" in str(exc.value)


class TestAccountsServiceActivate:
    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_activate_inactive_account(self, mock_session):
        """Inactive account should be activated."""
        account_id = uuid4()

        mock_account = MagicMock()
        mock_account.id = account_id
        mock_account.is_active = False

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_account
        mock_session.execute.return_value = mock_result

        service = AccountsService(mock_session)
        account = await service.activate_account(account_id)

        assert account.is_active is True
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_activate_already_active_fails(self, mock_session):
        """Already active account should raise error."""
        mock_account = MagicMock()
        mock_account.is_active = True

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_account
        mock_session.execute.return_value = mock_result

        service = AccountsService(mock_session)

        with pytest.raises(InvalidAccountError) as exc:
            await service.activate_account(uuid4())

        assert "already active" in str(exc.value)


class TestAccountsServiceGetByOwner:
    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.execute = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_get_accounts_by_owner(self, mock_session):
        """Should return all accounts for owner."""
        mock_accounts = [MagicMock(), MagicMock()]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_accounts
        mock_session.execute.return_value = mock_result

        service = AccountsService(mock_session)
        accounts = await service.get_accounts_by_owner("user123")

        assert len(accounts) == 2

    @pytest.mark.asyncio
    async def test_get_accounts_by_owner_empty(self, mock_session):
        """Owner with no accounts should return empty list."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        service = AccountsService(mock_session)
        accounts = await service.get_accounts_by_owner("nonexistent")

        assert accounts == []
