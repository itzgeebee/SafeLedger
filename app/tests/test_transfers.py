from decimal import Decimal
from uuid import uuid4

from app.domain.accounts import LedgerAccount
from app.domain.ledger import Ledger


def make_account(currency="USD"):
    return LedgerAccount(id=uuid4(), currency=currency, is_active=True)


def test_transfer_entries_count_without_fee():
    src = make_account()
    dst = make_account()
    tx = Ledger.transfer(
        source=src,
        destination=dst,
        fee_account=None,
        amount=Decimal("10"),
        fee_amount=Decimal("0"),
        currency="USD",
    )
    # Expect 2 entries: debit from source, credit to destination
    assert len(tx.entries) == 2


def test_transfer_entries_count_with_fee():
    src = make_account()
    dst = make_account()
    fee_acc = make_account()
    tx = Ledger.transfer(
        source=src,
        destination=dst,
        fee_account=fee_acc,
        amount=Decimal("10"),
        fee_amount=Decimal("1"),
        currency="USD",
    )
    # Expect 3 entries when fee is present
    assert len(tx.entries) == 3
