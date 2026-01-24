from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.balance import Balance


class BalanceRepository:
    """
    Repository for managing cached balance records.
    All operations are designed to be called within an existing transaction.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_balance(
        self,
        account_id: UUID,
        currency: str,
    ) -> Decimal | None:
        """
        Get cached balance for an account. Returns None if no cache exists.
        """
        stmt = select(Balance.balance).where(
            Balance.account_id == account_id,
            Balance.currency == currency,
        )
        result = await self.session.execute(stmt)
        row = result.scalar_one_or_none()
        return row

    async def adjust(
        self,
        account_id: UUID,
        currency: str,
        delta: Decimal,
    ) -> None:
        """
        Atomically adjust the balance by delta (positive or negative).
        Creates the balance record if it doesn't exist (upsert).
        """
        # Use PostgreSQL's INSERT ... ON CONFLICT for atomic upsert
        stmt = (
            pg_insert(Balance)
            .values(
                account_id=account_id,
                currency=currency,
                balance=delta,
            )
            .on_conflict_do_update(
                constraint="uq_balance_account_currency",
                set_={
                    "balance": Balance.balance + delta,
                },
            )
        )

        await self.session.execute(stmt)

    async def get_balance_for_update(
        self,
        account_id: UUID,
        currency: str,
    ) -> Decimal:
        """
        Get balance with row-level lock for update.
        Creates the record with 0 balance if it doesn't exist.
        Returns the current balance.
        """
        # Try to get existing balance with lock
        stmt = (
            select(Balance)
            .where(
                Balance.account_id == account_id,
                Balance.currency == currency,
            )
            .with_for_update()
        )
        result = await self.session.execute(stmt)
        balance_row = result.scalar_one_or_none()

        if balance_row is None:
            # Create new balance record
            new_balance = Balance(
                account_id=account_id,
                currency=currency,
                balance=Decimal("0"),
            )
            self.session.add(new_balance)
            await self.session.flush()
            return Decimal("0")

        return balance_row.balance
