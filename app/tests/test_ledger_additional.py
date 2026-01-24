"""
Additional tests for domain/ledger.py to cover remaining lines.
"""

from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.accounts import LedgerAccount
from app.domain.exceptions import InvalidTransferError
from app.domain.ledger import Ledger


class TestLedgerMinAmount:
    def test_amount_below_minimum_raises(self):
        """Amount below MIN_TRANSACTION_AMOUNT should raise."""
        source = LedgerAccount(id=uuid4(), currency="NGN", is_active=True)
        destination = LedgerAccount(id=uuid4(), currency="NGN", is_active=True)

        with pytest.raises(InvalidTransferError) as exc:
            Ledger.transfer(
                source=source,
                destination=destination,
                fee_account=None,
                amount=Decimal("0.001"),  # Below minimum
                fee_amount=Decimal("0"),
                currency="NGN",
            )

        assert "at least" in str(exc.value)


class TestLedgerAccountValidation:
    def test_inactive_source_raises(self):
        """Inactive source account should raise."""
        source = LedgerAccount(id=uuid4(), currency="NGN", is_active=False)
        destination = LedgerAccount(id=uuid4(), currency="NGN", is_active=True)

        with pytest.raises(Exception):  # AccountInactiveError
            Ledger.transfer(
                source=source,
                destination=destination,
                fee_account=None,
                amount=Decimal("100"),
                fee_amount=Decimal("0"),
                currency="NGN",
            )

    def test_inactive_destination_raises(self):
        """Inactive destination account should raise."""
        source = LedgerAccount(id=uuid4(), currency="NGN", is_active=True)
        destination = LedgerAccount(id=uuid4(), currency="NGN", is_active=False)

        with pytest.raises(Exception):
            Ledger.transfer(
                source=source,
                destination=destination,
                fee_account=None,
                amount=Decimal("100"),
                fee_amount=Decimal("0"),
                currency="NGN",
            )


class TestLedgerCurrencyValidation:
    def test_source_currency_mismatch_raises(self):
        """Source with different currency should raise."""
        source = LedgerAccount(id=uuid4(), currency="USD", is_active=True)
        destination = LedgerAccount(id=uuid4(), currency="NGN", is_active=True)

        with pytest.raises(Exception):  # CurrencyMismatchError
            Ledger.transfer(
                source=source,
                destination=destination,
                fee_account=None,
                amount=Decimal("100"),
                fee_amount=Decimal("0"),
                currency="NGN",
            )


class TestLedgerFeeValidation:
    def test_fee_without_fee_account_raises(self):
        """Fee amount > 0 without fee account should raise."""
        source = LedgerAccount(id=uuid4(), currency="NGN", is_active=True)
        destination = LedgerAccount(id=uuid4(), currency="NGN", is_active=True)

        with pytest.raises(InvalidTransferError) as exc:
            Ledger.transfer(
                source=source,
                destination=destination,
                fee_account=None,
                amount=Decimal("100"),
                fee_amount=Decimal("10"),  # Fee without fee account
                currency="NGN",
            )

        assert "Fee account required" in str(exc.value)

    def test_fee_account_currency_mismatch_raises(self):
        """Fee account with different currency should raise."""
        source = LedgerAccount(id=uuid4(), currency="NGN", is_active=True)
        destination = LedgerAccount(id=uuid4(), currency="NGN", is_active=True)
        fee_account = LedgerAccount(id=uuid4(), currency="USD", is_active=True)

        with pytest.raises(Exception):  # CurrencyMismatchError
            Ledger.transfer(
                source=source,
                destination=destination,
                fee_account=fee_account,
                amount=Decimal("100"),
                fee_amount=Decimal("10"),
                currency="NGN",
            )
