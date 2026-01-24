from decimal import Decimal
from uuid import uuid4

from hypothesis import given
from hypothesis import strategies as st

from app.domain.accounts import LedgerAccount
from app.domain.ledger import Ledger


@given(
    amount=st.decimals(min_value=Decimal("0.01"), max_value=Decimal("100000")).map(
        lambda d: d.quantize(Decimal("1.00000000"))
    ),
    fee=st.decimals(min_value=Decimal("0.00"), max_value=Decimal("1000")).map(
        lambda d: d.quantize(Decimal("1.00000000"))
    ),
)
def test_transfer_is_zero_sum(amount, fee):
    source = LedgerAccount(id=uuid4(), currency="NGN", is_active=True)
    dest = LedgerAccount(id=uuid4(), currency="NGN", is_active=True)
    fee_account = LedgerAccount(id=uuid4(), currency="NGN", is_active=True)

    tx = Ledger.transfer(
        source=source,
        destination=dest,
        fee_account=fee_account,
        amount=amount,
        fee_amount=fee,
        currency="NGN",
    )

    debit = sum(e.amount for e in tx.entries if e.entry_type == "DEBIT")
    credit = sum(e.amount for e in tx.entries if e.entry_type == "CREDIT")

    assert debit == credit
