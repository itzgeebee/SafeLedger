from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entry_type import EntryType
from app.domain.exceptions import TransactionNotFoundError
from app.domain.ledger import LedgerEntrySpec, LedgerTransaction
from app.models.ledger_entry import LedgerEntry


class LedgerQueryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_transaction(
        self,
        transaction_id: UUID,
    ) -> LedgerTransaction:
        stmt = select(LedgerEntry).where(LedgerEntry.transaction_id == transaction_id)
        result = await self.session.execute(stmt)
        entries = result.scalars().all()

        if not entries:
            raise TransactionNotFoundError(f"Transaction {transaction_id} not found")

        return LedgerTransaction(
            transaction_id=transaction_id,
            entries=[
                LedgerEntrySpec(
                    account_id=e.account_id,
                    amount=e.amount,
                    entry_type=EntryType(e.entry_type),
                    currency=e.currency,
                )
                for e in entries
            ],
        )
