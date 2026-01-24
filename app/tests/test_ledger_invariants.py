from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.accounts import LedgerAccount
from app.domain.exceptions import (
    AccountInactiveError,
    CurrencyMismatchError,
    InvalidTransferError,
)
from app.domain.ledger import Ledger


def make_account(active=True, currency="USD"):
    return LedgerAccount(id=uuid4(), currency=currency, is_active=active)


def test_negative_amount_raises():
    src = make_account()
    dst = make_account()
    with pytest.raises(InvalidTransferError):
        Ledger.transfer(
            source=src,
            destination=dst,
            fee_account=None,
            amount=Decimal("-1"),
            fee_amount=Decimal("0"),
            currency="USD",
        )


def test_negative_fee_raises():
    src = make_account()
    dst = make_account()
    with pytest.raises(InvalidTransferError):
        Ledger.transfer(
            source=src,
            destination=dst,
            fee_account=None,
            amount=Decimal("10"),
            fee_amount=Decimal("-0.01"),
            currency="USD",
        )


def test_fee_requires_fee_account():
    src = make_account()
    dst = make_account()
    with pytest.raises(InvalidTransferError):
        Ledger.transfer(
            source=src,
            destination=dst,
            fee_account=None,
            amount=Decimal("10"),
            fee_amount=Decimal("1"),
            currency="USD",
        )


def test_inactive_account_raises():
    src = make_account(active=False)
    dst = make_account()
    with pytest.raises(AccountInactiveError):
        Ledger.transfer(
            source=src,
            destination=dst,
            fee_account=None,
            amount=Decimal("1"),
            fee_amount=Decimal("0"),
            currency="USD",
        )


def test_currency_mismatch_raises():
    src = make_account(currency="USD")
    dst = make_account(currency="EUR")
    with pytest.raises(CurrencyMismatchError):
        Ledger.transfer(
            source=src,
            destination=dst,
            fee_account=None,
            amount=Decimal("1"),
            fee_amount=Decimal("0"),
            currency="USD",
        )


def test_reversal_is_zero_sum():
    src = make_account()
    dst = make_account()
    tx = Ledger.transfer(
        source=src,
        destination=dst,
        fee_account=None,
        amount=Decimal("5"),
        fee_amount=Decimal("0"),
        currency="USD",
    )
    rev = Ledger.reversal(tx)

    debit = sum(e.amount for e in rev.entries if e.entry_type == "DEBIT")
    credit = sum(e.amount for e in rev.entries if e.entry_type == "CREDIT")

    assert debit == credit
