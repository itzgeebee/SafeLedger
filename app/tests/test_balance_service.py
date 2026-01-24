"""
Unit tests for BalanceService.
"""

from decimal import Decimal
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.domain.exceptions import InsufficientFundsError
from app.services.balance_service import BalanceService


class TestBalanceServiceGetBalance:
    @pytest.mark.asyncio
    async def test_get_balance_from_cache(self):
        """Should return cached balance if available."""
        account_id = uuid4()
        mock_session = AsyncMock()

        service = BalanceService(mock_session)

        # Mock the balance_repo
        service.balance_repo = AsyncMock()
        service.balance_repo.get_balance = AsyncMock(return_value=Decimal("500.00"))

        balance = await service.get_balance(account_id, "NGN")

        assert balance == Decimal("500.00")
        service.balance_repo.get_balance.assert_called_once_with(account_id, "NGN")

    @pytest.mark.asyncio
    async def test_get_balance_falls_back_to_ledger(self):
        """Should calculate from ledger when no cache."""
        account_id = uuid4()
        mock_session = AsyncMock()

        service = BalanceService(mock_session)

        # Mock the balance_repo to return None (cache miss)
        service.balance_repo = AsyncMock()
        service.balance_repo.get_balance = AsyncMock(return_value=None)

        # Mock the ledger calculation
        with patch.object(
            service, "_calculate_from_ledger", return_value=Decimal("750.00")
        ) as mock_calc:
            balance = await service.get_balance(account_id, "NGN")

            assert balance == Decimal("750.00")
            mock_calc.assert_called_once_with(account_id, "NGN")


class TestBalanceServiceEnsureSufficientFunds:
    @pytest.mark.asyncio
    async def test_sufficient_funds_passes(self):
        """Should not raise when funds are sufficient."""
        account_id = uuid4()
        mock_session = AsyncMock()

        service = BalanceService(mock_session)

        # Mock get_balance
        with patch.object(service, "get_balance", return_value=Decimal("1000.00")):
            # Should not raise
            await service.ensure_sufficient_funds(
                account_id=account_id,
                currency="NGN",
                required_amount=Decimal("500.00"),
            )

    @pytest.mark.asyncio
    async def test_insufficient_funds_raises(self):
        """Should raise when funds are insufficient."""
        account_id = uuid4()
        mock_session = AsyncMock()

        service = BalanceService(mock_session)

        # Mock get_balance to return low balance
        with patch.object(service, "get_balance", return_value=Decimal("100.00")):
            with pytest.raises(InsufficientFundsError):
                await service.ensure_sufficient_funds(
                    account_id=account_id,
                    currency="NGN",
                    required_amount=Decimal("500.00"),
                )

    @pytest.mark.asyncio
    async def test_exact_balance_passes(self):
        """Exact balance should pass (not raise)."""
        account_id = uuid4()
        mock_session = AsyncMock()

        service = BalanceService(mock_session)

        with patch.object(service, "get_balance", return_value=Decimal("500.00")):
            # Should not raise
            await service.ensure_sufficient_funds(
                account_id=account_id,
                currency="NGN",
                required_amount=Decimal("500.00"),
            )

    @pytest.mark.asyncio
    async def test_zero_balance_with_zero_required(self):
        """Zero balance with zero required should pass."""
        account_id = uuid4()
        mock_session = AsyncMock()

        service = BalanceService(mock_session)

        with patch.object(service, "get_balance", return_value=Decimal("0.00")):
            # Should not raise
            await service.ensure_sufficient_funds(
                account_id=account_id,
                currency="NGN",
                required_amount=Decimal("0.00"),
            )
