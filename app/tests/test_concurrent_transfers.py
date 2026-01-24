import asyncio
import os
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.domain.exceptions import InsufficientFundsError
from app.models.account import Account, AccountType
from app.models.ledger_entry import LedgerEntry
from app.schemas.transfer import TransferRequest
from app.services.transfer_service import TransferService

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///:memory:")


@pytest.mark.asyncio
async def test_concurrent_transfers_one_fails_due_to_insufficient_funds(db_engine):
    async_session = async_sessionmaker(db_engine, expire_on_commit=False)

    # seed accounts and initial credit
    async with async_session() as session:
        # create two accounts
        src_id = uuid4()
        dst1_id = uuid4()
        dst2_id = uuid4()

        session.add_all(
            [
                Account(
                    id=src_id,
                    owner_id="user1",
                    currency="USD",
                    account_type=AccountType.USER,
                ),
                Account(
                    id=dst1_id,
                    owner_id="user2",
                    currency="USD",
                    account_type=AccountType.USER,
                ),
                Account(
                    id=dst2_id,
                    owner_id="user3",
                    currency="USD",
                    account_type=AccountType.USER,
                ),
            ]
        )

        # credit source with 100 USD (single CREDIT entry)
        tx_id = uuid4()
        session.add(
            LedgerEntry(
                transaction_id=tx_id,
                account_id=src_id,
                amount=Decimal("100.00"),
                entry_type="CREDIT",
                currency="USD",
            )
        )
        await session.commit()

    async def run_transfer(session_maker, source, dest, amount, key):
        async with session_maker() as s:
            svc = TransferService(s)
            req = TransferRequest(
                source_account_id=source,
                destination_account_id=dest,
                amount=Decimal(amount),
                currency="USD",
                fee_amount=Decimal("0.00"),
            )
            return await svc.execute(payload=req, idempotency_key=key)

    # Run two transfers concurrently that together exceed balance
    task1 = asyncio.create_task(
        run_transfer(async_session, src_id, dst1_id, "60", "k1")
    )
    task2 = asyncio.create_task(
        run_transfer(async_session, src_id, dst2_id, "60", "k2")
    )

    results = await asyncio.gather(task1, task2, return_exceptions=True)

    successes = [r for r in results if not isinstance(r, Exception)]
    failures = [r for r in results if isinstance(r, Exception)]

    if failures:
        for f in failures:
            print(f"DEBUG: Failure: {type(f).__name__}: {str(f)}")

    # Exactly one should succeed and at least one should fail with InsufficientFundsError
    assert len(successes) == 1
    assert any(isinstance(f, InsufficientFundsError) for f in failures)
