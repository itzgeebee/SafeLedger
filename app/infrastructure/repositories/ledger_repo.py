from sqlalchemy import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entry_type import EntryType
from app.domain.exceptions import DatabaseError
from app.domain.ledger import LedgerTransaction
from app.infrastructure.repositories.balance_repo import BalanceRepository
from app.models.ledger_entry import LedgerEntry


class LedgerRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.balance_repo = BalanceRepository(session)

    async def persist_transaction(
        self,
        transaction: LedgerTransaction,
    ) -> list[dict]:
        """
        Persist all ledger entries atomically and update balance cache.
        Caller controls the DB transaction boundary.
        """

        entries = [
            {
                "transaction_id": transaction.transaction_id,
                "account_id": entry.account_id,
                "amount": entry.amount,
                "entry_type": entry.entry_type,
                "currency": entry.currency,
            }
            for entry in transaction.entries
        ]

        await self.session.execute(
            insert(LedgerEntry),
            entries,
        )

        try:
            # Flush to ensure DB constraints are checked within caller's transaction
            await self.session.flush()
        except IntegrityError as exc:
            raise DatabaseError(str(exc))

        # Update balance cache for each affected account
        for entry in transaction.entries:
            # CREDIT increases balance, DEBIT decreases balance
            delta = (
                entry.amount if entry.entry_type == EntryType.CREDIT else -entry.amount
            )
            await self.balance_repo.adjust(
                account_id=entry.account_id,
                currency=entry.currency,
                delta=delta,
            )

        return entries
